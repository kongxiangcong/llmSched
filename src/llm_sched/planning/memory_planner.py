"""Static VMEM / KV memory planner foundation."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Literal, cast

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.memory_plan import (
    AddressBindingDiagnostic,
    BackingStoreKind,
    KVAddressFormula,
    LifetimeBucket,
    MemoryPlanArtifact,
    PlannedAllocation,
    RegionSummary,
    StorageBindingDescriptor,
    VMEMFitDiagnostic,
)
from llm_sched.ir.nig import NIGIR, NIGNode, TensorMemoryClass


_GEMM_LIKE_MACROS = frozenset({"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"})
_STREAMING_VECTOR_MACROS = frozenset({"GEGLU", "ROPE", "SDPA", "SDPA_DECODE", "RMSNORM", "ELEM_ADD"})
_VPU_TEMP_MACROS = frozenset(
    {
        "RMSNORM",
        "GEGLU",
        "ROPE",
        "SDPA",
        "SDPA_DECODE",
        "ELEM_ADD",
        "ATTENTION_MASK_PREP",
        "LAYOUT_FALLBACK",
        "SHAPE_HELPER",
    }
)
_LAYER_PATTERNS = (
    re.compile(r"layers\.(\d+)"),
    re.compile(r"layers_(\d+)"),
)
_LIFETIME_BUCKETS: tuple[LifetimeBucket, ...] = ("preload", "compute", "store", "persist")
_MEMORY_CLASSES: tuple[TensorMemoryClass, ...] = ("ACTIVATION", "WEIGHT", "KV_CACHE", "QUANT_PARAM", "METADATA")
_BACKING_STORES: tuple[BackingStoreKind, ...] = ("vmem-local", "ddr-backed-staged", "ddr-persistent")


def plan_memory_artifact(
    bound_nig_ir: NIGIR,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> MemoryPlanArtifact:
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("memory planner requires bound NIGIR input")

    capabilities = (
        hardware
        if isinstance(hardware, ArchitectureCapabilities)
        else ArchitectureCapabilities.from_target_profile(hardware)
    )
    region_capacities = {
        region_name: region_kb * 1024 for region_name, region_kb in capabilities.vmem.regions.items()
    }

    allocations: list[PlannedAllocation] = []
    storage_bindings_by_id: dict[str, StorageBindingDescriptor] = {}
    kv_formulas: list[KVAddressFormula] = []
    address_diagnostics: list[AddressBindingDiagnostic] = []
    peak_bytes_by_region = defaultdict(int)
    peak_lifetime_bucket_by_region: dict[str, LifetimeBucket | None] = {}
    peak_bytes_by_region_and_bucket: dict[str, dict[LifetimeBucket, int]] = defaultdict(
        _empty_lifetime_bucket_map
    )
    peak_bytes_by_memory_class_by_region: dict[str, dict[TensorMemoryClass, int]] = defaultdict(
        _empty_memory_class_map
    )
    peak_bytes_by_backing_store_by_region: dict[str, dict[BackingStoreKind, int]] = defaultdict(
        _empty_backing_store_map
    )
    peak_allocation_ids_by_region: dict[str, list[str]] = {}
    offending_node_ids_by_region: dict[str, list[str]] = defaultdict(list)

    for node_index, node in enumerate(bound_nig_ir.nodes):
        if not isinstance(node, NIGNode):
            continue
        node_allocations = _plan_node_allocations(
            node,
            node_index=node_index,
            scenario=scenario,
            region_capacities=region_capacities,
        )
        allocations.extend(node_allocations)
        _register_storage_bindings(storage_bindings_by_id, node, node_allocations)
        address_diagnostics.extend(_build_non_kv_address_diagnostics(node_allocations))

        region_bytes_by_bucket = defaultdict(_empty_lifetime_bucket_map)
        region_allocation_ids_by_bucket = defaultdict(lambda: defaultdict(list))
        region_bytes_by_bucket_and_memory_class = defaultdict(
            lambda: defaultdict(_empty_memory_class_map)
        )
        region_bytes_by_bucket_and_backing_store = defaultdict(
            lambda: defaultdict(_empty_backing_store_map)
        )
        for allocation in node_allocations:
            if allocation.region_name is None:
                continue
            region_bytes_by_bucket[allocation.region_name][allocation.lifetime_bucket] += allocation.size_bytes
            region_allocation_ids_by_bucket[allocation.region_name][allocation.lifetime_bucket].append(
                allocation.allocation_id
            )
            region_bytes_by_bucket_and_memory_class[allocation.region_name][allocation.lifetime_bucket][
                allocation.memory_class
            ] += allocation.size_bytes
            region_bytes_by_bucket_and_backing_store[allocation.region_name][allocation.lifetime_bucket][
                allocation.backing_store
            ] += allocation.size_bytes

        for region_name, bucket_bytes in region_bytes_by_bucket.items():
            for lifetime_bucket, required_bytes in bucket_bytes.items():
                peak_bytes_by_region_and_bucket[region_name][lifetime_bucket] = max(
                    peak_bytes_by_region_and_bucket[region_name][lifetime_bucket],
                    required_bytes,
                )
                if required_bytes > peak_bytes_by_region[region_name]:
                    peak_bytes_by_region[region_name] = required_bytes
                    peak_lifetime_bucket_by_region[region_name] = lifetime_bucket
                    peak_bytes_by_memory_class_by_region[region_name] = dict(
                        region_bytes_by_bucket_and_memory_class[region_name][lifetime_bucket]
                    )
                    peak_bytes_by_backing_store_by_region[region_name] = dict(
                        region_bytes_by_bucket_and_backing_store[region_name][lifetime_bucket]
                    )
                    peak_allocation_ids_by_region[region_name] = list(
                        region_allocation_ids_by_bucket[region_name][lifetime_bucket]
                    )
                    offending_node_ids_by_region[region_name] = [node.node_id]
                elif required_bytes == peak_bytes_by_region[region_name] and required_bytes > 0:
                    offending_node_ids_by_region[region_name].append(node.node_id)

        kv_formula = _build_kv_formula(node)
        if kv_formula is not None:
            kv_formulas.append(kv_formula)
            address_diagnostics.append(
                _build_kv_address_diagnostic(
                    kv_formula,
                    storage_binding_id=_kv_storage_binding_id(
                        node,
                        tensor_kind=kv_formula.tensor_kind,
                    ),
                )
            )

    region_summaries: dict[str, RegionSummary] = {}
    diagnostics: list[VMEMFitDiagnostic] = []
    for region_name, capacity_bytes in sorted(region_capacities.items()):
        required_bytes = peak_bytes_by_region.get(region_name, 0)
        fits = required_bytes <= capacity_bytes
        region_summaries[region_name] = RegionSummary(
            region_name=region_name,
            capacity_bytes=capacity_bytes,
            peak_bytes=required_bytes,
            peak_lifetime_bucket=peak_lifetime_bucket_by_region.get(region_name),
            peak_bytes_by_lifetime_bucket=peak_bytes_by_region_and_bucket.get(
                region_name,
                _empty_lifetime_bucket_map(),
            ),
            peak_bytes_by_memory_class=peak_bytes_by_memory_class_by_region.get(
                region_name,
                _empty_memory_class_map(),
            ),
            peak_bytes_by_backing_store=peak_bytes_by_backing_store_by_region.get(
                region_name,
                _empty_backing_store_map(),
            ),
            fits=fits,
            allocation_ids=peak_allocation_ids_by_region.get(region_name, []),
        )
        diagnostics.append(
            VMEMFitDiagnostic(
                diagnostic_id=f"vmem-fit.{region_name}",
                region_name=region_name,
                status="fit" if fits else "overflow",
                required_bytes=required_bytes,
                required_bytes_by_memory_class=peak_bytes_by_memory_class_by_region.get(
                    region_name,
                    _empty_memory_class_map(),
                ),
                required_bytes_by_backing_store=peak_bytes_by_backing_store_by_region.get(
                    region_name,
                    _empty_backing_store_map(),
                ),
                capacity_bytes=capacity_bytes,
                offending_node_ids=sorted(set(offending_node_ids_by_region.get(region_name, []))),
                message=_diagnostic_message(region_name, required_bytes, capacity_bytes, fits),
            )
        )

    return MemoryPlanArtifact(
        graph_id=bound_nig_ir.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode=capabilities.core_mode,
        allocations=allocations,
        storage_bindings=list(storage_bindings_by_id.values()),
        region_summaries=region_summaries,
        kv_formulas=kv_formulas,
        diagnostics=diagnostics,
        address_diagnostics=address_diagnostics,
    )


def _plan_node_allocations(
    node: NIGNode,
    *,
    node_index: int,
    scenario: ScenarioProfile,
    region_capacities: dict[str, int],
) -> list[PlannedAllocation]:
    if node.binding is None:
        raise ValueError(f"bound node {node.node_id} is missing binding payload")

    allocations: list[PlannedAllocation] = []
    input_region, output_region = ("ping", "pong") if node_index % 2 == 0 else ("pong", "ping")
    m_tile, n_tile, k_tile = _planning_tile_shape(
        node,
        scenario,
        region_capacities=region_capacities,
        input_region=input_region,
        output_region=output_region,
    )

    for tensor_name in node.inputs:
        memory_class = node.binding.input_memory_classes.get(tensor_name)
        if memory_class is None:
            continue
        allocations.extend(
            _build_input_allocations(
                node,
                tensor_name=tensor_name,
                memory_class=memory_class,
                input_region=input_region,
                m_tile=m_tile,
                n_tile=n_tile,
                k_tile=k_tile,
                scenario=scenario,
            )
        )

    for tensor_name in node.outputs:
        memory_class = node.binding.output_memory_classes.get(tensor_name)
        if memory_class is None:
            continue
        allocations.extend(
            _build_output_allocations(
                node,
                tensor_name=tensor_name,
                memory_class=memory_class,
                output_region=output_region,
                m_tile=m_tile,
                n_tile=n_tile,
                k_tile=k_tile,
                scenario=scenario,
            )
        )

    if node.macro_op in _GEMM_LIKE_MACROS:
        allocations.append(
            PlannedAllocation(
                allocation_id=f"{node.node_id}.temp.accum",
                node_id=node.node_id,
                tensor_name="accum",
                tensor_role="temp",
                lifetime_bucket="compute",
                backing_store="vmem-local",
                memory_class="ACTIVATION",
                address_space="VMEM",
                region_name="accum",
                offset_bytes=0,
                size_bytes=max(1, m_tile * n_tile * 4),
                alignment_bytes=64,
            )
        )

    if node.quant.quant_mode != "none":
        allocations.append(
            PlannedAllocation(
                allocation_id=f"{node.node_id}.temp.wdq",
                node_id=node.node_id,
                tensor_name="wdq_reserved",
                tensor_role="temp",
                lifetime_bucket="compute",
                backing_store="vmem-local",
                memory_class="QUANT_PARAM",
                address_space="VMEM",
                region_name="wdq_reserved",
                offset_bytes=0,
                size_bytes=1024,
                alignment_bytes=64,
            )
        )

    if node.macro_op in _VPU_TEMP_MACROS:
        allocations.append(
            PlannedAllocation(
                allocation_id=f"{node.node_id}.temp.misc",
                node_id=node.node_id,
                tensor_name="misc",
                tensor_role="temp",
                lifetime_bucket="compute",
                backing_store="vmem-local",
                memory_class="METADATA",
                address_space="VMEM",
                region_name="misc",
                offset_bytes=0,
                size_bytes=_misc_temp_bytes(node, m_tile=m_tile, n_tile=n_tile),
                alignment_bytes=64,
            )
        )

    return allocations


def _build_input_allocations(
    node: NIGNode,
    *,
    tensor_name: str,
    memory_class: TensorMemoryClass,
    input_region: str,
    m_tile: int,
    n_tile: int,
    k_tile: int,
    scenario: ScenarioProfile,
) -> list[PlannedAllocation]:
    if memory_class == "ACTIVATION":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.input.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="input",
                lifetime_bucket="preload",
                backing_store="vmem-local",
                memory_class=memory_class,
                address_space="VMEM",
                region_name=input_region,
                offset_bytes=0,
                size_bytes=_activation_input_bytes(node, m_tile, n_tile, k_tile, scenario=scenario),
                alignment_bytes=64,
            )
        ]
    if memory_class == "WEIGHT":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.weight.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="weight",
                lifetime_bucket="preload",
                backing_store="ddr-backed-staged",
                backing_symbol=_weight_backing_symbol(tensor_name),
                storage_binding_id=_weight_storage_binding_id(node, tensor_name=tensor_name),
                memory_class=memory_class,
                address_space="VMEM",
                region_name=_weight_region_name(node, tensor_name),
                offset_bytes=0,
                size_bytes=_weight_input_bytes(
                    node,
                    tensor_name=tensor_name,
                    m_tile=m_tile,
                    n_tile=n_tile,
                    k_tile=k_tile,
                ),
                alignment_bytes=64,
            )
        ]
    if memory_class == "QUANT_PARAM":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.quant.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="quant_param",
                lifetime_bucket="preload",
                backing_store="ddr-backed-staged",
                backing_symbol=_quant_backing_symbol(tensor_name),
                storage_binding_id=_quant_storage_binding_id(node, tensor_name=tensor_name),
                memory_class=memory_class,
                address_space="VMEM",
                region_name="quant",
                offset_bytes=0,
                size_bytes=_quant_param_bytes(node, tensor_name=tensor_name, k_tile=k_tile),
                alignment_bytes=64,
            )
        ]
    if memory_class == "KV_CACHE":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.kv.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="kv_cache",
                lifetime_bucket="persist",
                backing_store="ddr-persistent",
                backing_symbol="KV_BASE",
                storage_binding_id=_kv_storage_binding_id(
                    node,
                    tensor_kind=_kv_tensor_kind(node, tensor_name=tensor_name),
                ),
                memory_class=memory_class,
                address_space="DDR",
                region_name=None,
                offset_bytes=0,
                size_bytes=_kv_tensor_bytes(node),
                alignment_bytes=64,
            )
        ]
    return [
        PlannedAllocation(
            allocation_id=f"{node.node_id}.meta.{tensor_name}",
            node_id=node.node_id,
            tensor_name=tensor_name,
            tensor_role="metadata",
            lifetime_bucket="preload",
            backing_store="vmem-local",
            memory_class="METADATA",
            address_space="VMEM",
            region_name="misc",
            offset_bytes=0,
            size_bytes=256,
            alignment_bytes=64,
        )
    ]


def _build_output_allocations(
    node: NIGNode,
    *,
    tensor_name: str,
    memory_class: TensorMemoryClass,
    output_region: str,
    m_tile: int,
    n_tile: int,
    k_tile: int,
    scenario: ScenarioProfile,
) -> list[PlannedAllocation]:
    if memory_class == "ACTIVATION":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.output.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="output",
                lifetime_bucket="store",
                backing_store="vmem-local",
                memory_class=memory_class,
                address_space="VMEM",
                region_name=output_region,
                offset_bytes=0,
                size_bytes=_output_bytes(node, m_tile, n_tile, k_tile, scenario=scenario),
                alignment_bytes=64,
            )
        ]
    if memory_class == "KV_CACHE":
        return [
            PlannedAllocation(
                allocation_id=f"{node.node_id}.output.{tensor_name}",
                node_id=node.node_id,
                tensor_name=tensor_name,
                tensor_role="kv_cache",
                lifetime_bucket="persist",
                backing_store="ddr-persistent",
                backing_symbol="KV_BASE",
                storage_binding_id=_kv_storage_binding_id(
                    node,
                    tensor_kind=_kv_tensor_kind(node, tensor_name=tensor_name),
                ),
                memory_class=memory_class,
                address_space="DDR",
                region_name=None,
                offset_bytes=0,
                size_bytes=_kv_tensor_bytes(node),
                alignment_bytes=64,
            )
        ]
    return [
        PlannedAllocation(
            allocation_id=f"{node.node_id}.output.{tensor_name}",
            node_id=node.node_id,
            tensor_name=tensor_name,
            tensor_role="metadata",
            lifetime_bucket="store",
            backing_store="vmem-local",
            memory_class=cast(TensorMemoryClass, memory_class),
            address_space="VMEM",
            region_name="misc",
            offset_bytes=0,
            size_bytes=256,
            alignment_bytes=64,
        )
    ]


def _planning_tile_shape(
    node: NIGNode,
    scenario: ScenarioProfile,
    *,
    region_capacities: dict[str, int],
    input_region: str,
    output_region: str,
) -> tuple[int, int, int]:
    if node.binding is None:
        raise ValueError(f"bound node {node.node_id} is missing binding payload")
    default_m_tile = 1 if scenario.mode == "decode" else 64
    resolved_shape = node.binding.resolved_shape or node.shape
    logical_m = _logical_m_dimension(resolved_shape)
    logical_n = max(1, resolved_shape[-1]) if resolved_shape else 1

    if node.macro_op in _GEMM_LIKE_MACROS:
        n_tile = min(128, logical_n)
        k_tile = 128
        m_tile = min(
            default_m_tile,
            logical_m,
            _max_fit_rows(region_capacities.get("accum", 0), n_tile * 4),
            _max_fit_rows(
                region_capacities.get(input_region, 0),
                k_tile * _dtype_bytes(node.quant.activation_dtype),
            ),
            _max_fit_rows(
                region_capacities.get(output_region, 0),
                n_tile * _dtype_bytes(node.quant.activation_dtype),
            ),
        )
        return (max(1, m_tile), n_tile, k_tile)

    if node.macro_op == "EMBEDDING_LOOKUP":
        embedding_dim = logical_n
        row_bytes = embedding_dim * _dtype_bytes(_effective_weight_dtype(node))
        output_row_bytes = embedding_dim * _dtype_bytes(node.quant.activation_dtype)
        rows = min(
            logical_m,
            _max_fit_rows(region_capacities.get("weight", 0), row_bytes),
            _max_fit_rows(region_capacities.get(output_region, 0), output_row_bytes),
        )
        return (max(1, rows), embedding_dim, embedding_dim)

    if node.macro_op in {"KVLOAD", "KVSTORE"} and node.binding.attention is not None:
        attention = node.binding.attention
        query_rows = attention.query_len if scenario.mode == "decode" else min(attention.query_len, 16)
        head_tile = min(attention.head_dim, 128)
        return (max(1, query_rows), max(1, head_tile), max(1, head_tile))

    if node.macro_op in _STREAMING_VECTOR_MACROS:
        stream_rows = min(logical_m, 1 if scenario.mode == "decode" else 16)
        vector_width = min(logical_n, 128)
        return (max(1, stream_rows), max(1, vector_width), max(1, vector_width))

    if node.macro_op == "LAYOUT_FALLBACK":
        vector_width = min(logical_n, 128)
        stream_rows = min(logical_m, 1 if scenario.mode == "decode" else 16)
        return (max(1, stream_rows), max(1, vector_width), max(1, vector_width))

    return (max(1, logical_m), logical_n, 128)


def _logical_m_dimension(shape: list[int]) -> int:
    if not shape:
        return 1
    if len(shape) == 1:
        return max(1, shape[0])
    logical_m = 1
    for dim in shape[:-1]:
        logical_m *= max(1, dim)
    return max(1, logical_m)


def _empty_lifetime_bucket_map() -> dict[LifetimeBucket, int]:
    return {bucket: 0 for bucket in _LIFETIME_BUCKETS}


def _empty_memory_class_map() -> dict[TensorMemoryClass, int]:
    return {memory_class: 0 for memory_class in _MEMORY_CLASSES}


def _empty_backing_store_map() -> dict[BackingStoreKind, int]:
    return {backing_store: 0 for backing_store in _BACKING_STORES}


def _build_non_kv_address_diagnostics(
    allocations: list[PlannedAllocation],
) -> list[AddressBindingDiagnostic]:
    diagnostics: list[AddressBindingDiagnostic] = []
    for allocation in allocations:
        if allocation.backing_store == "vmem-local":
            continue
        if allocation.tensor_role == "weight":
            diagnostics.append(
                _build_symbolic_address_diagnostic(
                    allocation,
                    address_kind="weight",
                    message="weight staging is bound to a symbolic DDR tensor base",
                )
            )
        elif allocation.tensor_role == "quant_param":
            diagnostics.append(
                _build_symbolic_address_diagnostic(
                    allocation,
                    address_kind="quant",
                    message="quant-param staging is bound to a symbolic DDR tensor base",
                )
            )
    return diagnostics


def _build_symbolic_address_diagnostic(
    allocation: PlannedAllocation,
    *,
    address_kind: Literal["weight", "quant"],
    message: str,
) -> AddressBindingDiagnostic:
    bound = allocation.backing_symbol is not None
    return AddressBindingDiagnostic(
        diagnostic_id=f"addr.{address_kind}.{allocation.allocation_id}",
        node_id=allocation.node_id,
        address_kind=address_kind,
        status="bound" if bound else "unresolved",
        storage_binding_id=allocation.storage_binding_id,
        symbol=allocation.backing_symbol or f"UNRESOLVED::{allocation.tensor_name}",
        message=message if bound else f"{message}; symbolic DDR binding is unresolved",
    )


def _register_storage_bindings(
    bindings_by_id: dict[str, StorageBindingDescriptor],
    node: NIGNode,
    allocations: list[PlannedAllocation],
) -> None:
    for allocation in allocations:
        binding = _build_storage_binding_descriptor(node, allocation)
        if binding is None:
            continue
        bindings_by_id.setdefault(binding.binding_id, binding)


def _build_storage_binding_descriptor(
    node: NIGNode,
    allocation: PlannedAllocation,
) -> StorageBindingDescriptor | None:
    if allocation.storage_binding_id is None or allocation.backing_symbol is None:
        return None
    if allocation.tensor_role == "weight":
        return StorageBindingDescriptor(
            binding_id=allocation.storage_binding_id,
            node_id=node.node_id,
            tensor_name=allocation.tensor_name,
            memory_class="WEIGHT",
            backing_store=allocation.backing_store,
            source_kind="weight_tensor",
            symbol=allocation.backing_symbol,
            binding_scope="per-tensor-base",
            dtype=_effective_weight_dtype(node),
        )
    if allocation.tensor_role == "quant_param":
        return StorageBindingDescriptor(
            binding_id=allocation.storage_binding_id,
            node_id=node.node_id,
            tensor_name=allocation.tensor_name,
            memory_class="QUANT_PARAM",
            backing_store=allocation.backing_store,
            source_kind="quant_tensor",
            symbol=allocation.backing_symbol,
            binding_scope="per-tensor-base",
        )
    if allocation.tensor_role == "kv_cache":
        return StorageBindingDescriptor(
            binding_id=allocation.storage_binding_id,
            node_id=node.node_id,
            tensor_name=allocation.tensor_name,
            memory_class="KV_CACHE",
            backing_store=allocation.backing_store,
            source_kind="kv_cache_slice",
            symbol=allocation.backing_symbol,
            binding_scope="per-layer-slice",
            layout="LBHSD",
            dtype=node.quant.activation_dtype,
            layer_id=_infer_layer_id(node),
            tensor_kind=_kv_tensor_kind(node, tensor_name=allocation.tensor_name),
        )
    return None


def _sanitize_symbol_component(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", value).strip("_") or "unnamed"


def _weight_storage_binding_id(node: NIGNode, *, tensor_name: str) -> str:
    return f"storage.weight.{node.node_id}.{_sanitize_symbol_component(tensor_name)}"


def _quant_storage_binding_id(node: NIGNode, *, tensor_name: str) -> str:
    return f"storage.quant.{node.node_id}.{_sanitize_symbol_component(tensor_name)}"


def _kv_storage_binding_id(node: NIGNode, *, tensor_kind: Literal['key', 'value']) -> str:
    return f"storage.kv.{node.node_id}.{tensor_kind}"


def _weight_backing_symbol(tensor_name: str) -> str:
    return f"WEIGHT_BASE::{_sanitize_symbol_component(tensor_name)}"


def _quant_backing_symbol(tensor_name: str) -> str:
    return f"QUANT_BASE::{_sanitize_symbol_component(tensor_name)}"


def _kv_tensor_kind(node: NIGNode, *, tensor_name: str) -> Literal["key", "value"]:
    normalized_tensor_name = tensor_name.lower()
    if "value" in normalized_tensor_name:
        return "value"
    if "key" in normalized_tensor_name:
        return "key"
    attrs_tensor_kind = str(node.attrs.get("tensor_kind", "")).lower()
    if attrs_tensor_kind == "value":
        return "value"
    return "key"


def _primary_kv_tensor_name(node: NIGNode) -> str:
    if node.binding is None:
        return ""
    for tensor_name in [*node.inputs, *node.outputs]:
        if node.binding.input_memory_classes.get(tensor_name) == "KV_CACHE":
            return tensor_name
        if node.binding.output_memory_classes.get(tensor_name) == "KV_CACHE":
            return tensor_name
    return node.inputs[0] if node.inputs else ""


def _activation_input_bytes(
    node: NIGNode,
    m_tile: int,
    n_tile: int,
    k_tile: int,
    *,
    scenario: ScenarioProfile,
) -> int:
    if node.macro_op in _GEMM_LIKE_MACROS:
        return max(1, m_tile * k_tile * _dtype_bytes(node.quant.activation_dtype))
    if node.macro_op in {"EMBEDDING_LOOKUP", "LAYOUT_FALLBACK", "KVSTORE"} | _STREAMING_VECTOR_MACROS:
        return max(1, m_tile * n_tile * _dtype_bytes(node.quant.activation_dtype))
    if node.binding is None:
        return max(1, _shape_bytes(node.shape, node.quant.activation_dtype))
    return max(1, _shape_bytes(node.binding.resolved_shape, node.quant.activation_dtype))


def _output_bytes(
    node: NIGNode,
    m_tile: int,
    n_tile: int,
    k_tile: int,
    *,
    scenario: ScenarioProfile,
) -> int:
    if node.macro_op in _GEMM_LIKE_MACROS:
        return max(1, m_tile * n_tile * _dtype_bytes(node.quant.activation_dtype))
    if node.macro_op in {"EMBEDDING_LOOKUP", "LAYOUT_FALLBACK"} | _STREAMING_VECTOR_MACROS:
        return max(1, m_tile * n_tile * _dtype_bytes(node.quant.activation_dtype))
    if node.binding is None:
        return max(1, _shape_bytes(node.shape, node.quant.activation_dtype))
    if node.macro_op in {"KVLOAD", "KVSTORE"}:
        return max(1, min(_shape_bytes(node.binding.resolved_shape, node.quant.activation_dtype), m_tile * k_tile * 2))
    return max(1, _shape_bytes(node.binding.resolved_shape, node.quant.activation_dtype))


def _weight_input_bytes(
    node: NIGNode,
    *,
    tensor_name: str,
    m_tile: int,
    n_tile: int,
    k_tile: int,
) -> int:
    if node.macro_op == "EMBEDDING_LOOKUP":
        if tensor_name == node.inputs[0]:
            return max(1, m_tile * n_tile * _dtype_bytes(_effective_weight_dtype(node)))
        return max(1, math.ceil(_dtype_bytes(node.quant.activation_dtype)))
    if node.macro_op == "ROPE_TABLE":
        head_dim = int(node.attrs.get("head_dim", node.shape[-1] if node.shape else 0))
        return max(1, (max(head_dim, 1) // 2) * _dtype_bytes(_effective_weight_dtype(node)))
    if node.macro_op == "RMSNORM_GEMM" and len(node.inputs) >= 2 and tensor_name == node.inputs[1]:
        return max(1, k_tile * _dtype_bytes(_effective_weight_dtype(node)))
    return max(1, k_tile * n_tile * _dtype_bytes(_effective_weight_dtype(node)))


def _effective_weight_dtype(node: NIGNode) -> str:
    if node.quant.weight_dtype.lower() in {"none", "unknown"}:
        return node.quant.activation_dtype
    return node.quant.weight_dtype


def _max_fit_rows(capacity_bytes: int, row_bytes: float) -> int:
    if capacity_bytes <= 0:
        return 1
    if row_bytes <= 0:
        return 1
    return max(1, int(capacity_bytes // row_bytes))


def _weight_region_name(node: NIGNode, tensor_name: str) -> str:
    if node.macro_op == "RMSNORM_GEMM" and len(node.inputs) >= 2 and tensor_name == node.inputs[1]:
        return "misc"
    return "weight"


def _misc_temp_bytes(node: NIGNode, *, m_tile: int, n_tile: int) -> int:
    if node.macro_op == "ROPE":
        working_set_bytes = m_tile * n_tile * _dtype_bytes(node.quant.activation_dtype)
        return max(256, min(int(working_set_bytes), 2048))
    return max(256, min(_shape_bytes(node.binding.resolved_shape, node.quant.activation_dtype), 4096))


def _quant_param_bytes(node: NIGNode, *, tensor_name: str, k_tile: int) -> int:
    groups_per_tile = max(1, math.ceil(k_tile / node.quant.group_size))
    if "zp" in tensor_name.lower():
        return groups_per_tile * 2
    return groups_per_tile * 2


def _kv_tensor_bytes(node: NIGNode) -> int:
    attention = node.binding.attention if node.binding is not None else None
    if attention is None:
        return 1
    return max(1, attention.kv_len * attention.num_key_value_heads * attention.head_dim * 2)


def _build_kv_formula(node: NIGNode) -> KVAddressFormula | None:
    if node.binding is None or node.binding.attention is None:
        return None
    if node.macro_op not in {"KVSTORE", "KVLOAD"}:
        return None

    attention = node.binding.attention
    token_stride = attention.num_key_value_heads * attention.head_dim * 2
    kv_kind_stride = attention.kv_len * token_stride
    layer_stride = 2 * kv_kind_stride
    head_stride = attention.head_dim * 2
    tensor_kind = _kv_tensor_kind(node, tensor_name=_primary_kv_tensor_name(node))

    return KVAddressFormula(
        node_id=node.node_id,
        tensor_kind=tensor_kind,
        layer_id=_infer_layer_id(node),
        layout="LBHSD",
        base_symbol="KV_BASE",
        layer_stride_bytes=layer_stride,
        kv_kind_stride_bytes=kv_kind_stride,
        token_stride_bytes=token_stride,
        head_stride_bytes=head_stride,
        dim_stride_bytes=2,
        formula=(
            "KV_BASE + layer_id * KV_LAYER_STRIDE + kv_kind * KV_KIND_STRIDE "
            "+ token * KV_TOKEN_STRIDE"
        ),
    )


def _infer_layer_id(node: NIGNode) -> int | None:
    source_ids = list(node.audit_ref.source_ids) + list(node.source_ref)
    for source_id in source_ids:
        for pattern in _LAYER_PATTERNS:
            match = pattern.search(source_id)
            if match is not None:
                return int(match.group(1))
    return None


def _build_kv_address_diagnostic(
    kv_formula: KVAddressFormula,
    *,
    storage_binding_id: str,
) -> AddressBindingDiagnostic:
    if kv_formula.layer_id is None:
        return AddressBindingDiagnostic(
            diagnostic_id=f"addr.kv.{kv_formula.node_id}",
            node_id=kv_formula.node_id,
            address_kind="kv",
            status="unresolved",
            storage_binding_id=storage_binding_id,
            symbol="KV_LAYER_STRIDE",
            message="kv address formula is present but layer_id could not be inferred from traceability",
        )
    return AddressBindingDiagnostic(
        diagnostic_id=f"addr.kv.{kv_formula.node_id}",
        node_id=kv_formula.node_id,
        address_kind="kv",
        status="bound",
        storage_binding_id=storage_binding_id,
        symbol="KV_LAYER_STRIDE",
        message="kv address formula resolved with concrete layer_id",
    )


def _shape_bytes(shape: list[int], dtype: str) -> int:
    num_elements = 1
    for dim in shape:
        num_elements *= max(1, dim)
    return max(1, math.ceil(num_elements * _dtype_bytes(dtype)))


def _dtype_bytes(dtype: str) -> float:
    normalized = dtype.lower()
    if normalized in {"bf16", "float16", "fp16"}:
        return 2
    if normalized in {"float32", "fp32", "int32", "uint32"}:
        return 4
    if normalized in {"int64", "uint64"}:
        return 8
    if normalized in {"int8", "uint8", "bool"}:
        return 1
    if normalized in {"int4", "uint4", "nf4"}:
        return 0.5
    if normalized in {"none", "unknown"}:
        return 1
    return 2


def _diagnostic_message(region_name: str, required_bytes: int, capacity_bytes: int, fits: bool) -> str:
    if fits:
        return f"region '{region_name}' fits: required {required_bytes} bytes within {capacity_bytes} bytes"
    return f"region '{region_name}' overflows: required {required_bytes} bytes exceeds {capacity_bytes} bytes"
