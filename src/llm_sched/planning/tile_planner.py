"""SPEC-09 tile candidate planner foundation."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.memory_plan import MemoryPlanArtifact, PlannedAllocation, StorageBindingDescriptor
from llm_sched.contracts.tiling_plan import (
    TileCandidate,
    TileCandidateResourceSummary,
    TilingPlanArtifact,
)
from llm_sched.ir.nig import NIGIR, NIGNode


_GEMM_LIKE_MACROS = frozenset({"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"})
_ATTENTION_MACROS = frozenset({"SDPA", "SDPA_DECODE"})
_PREFILL_TEMPLATE = (64, 48, 32, 24, 16, 12, 8, 4, 2, 1)


def plan_tiling_artifact(
    bound_nig_ir: NIGIR,
    memory_plan: MemoryPlanArtifact,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> TilingPlanArtifact:
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("tile planner requires bound NIGIR input")
    if memory_plan.graph_id != bound_nig_ir.graph_id:
        raise ValueError("memory_plan graph_id must match bound_nig_ir graph_id")
    if memory_plan.scenario_name != scenario.scenario_name:
        raise ValueError("memory_plan scenario_name must match scenario profile")

    capabilities = (
        hardware
        if isinstance(hardware, ArchitectureCapabilities)
        else ArchitectureCapabilities.from_target_profile(hardware)
    )
    allocations_by_node = _group_allocations_by_node(memory_plan.allocations)
    storage_bindings_by_id = {binding.binding_id: binding for binding in memory_plan.storage_bindings}

    candidates: list[TileCandidate] = []
    for node in bound_nig_ir.nodes:
        if node.binding is None:
            continue
        if node.macro_op in _GEMM_LIKE_MACROS:
            candidates.extend(
                _build_gemm_candidates(
                    node,
                    allocations_by_node.get(node.node_id, []),
                    storage_bindings_by_id,
                    scenario=scenario,
                    capabilities=capabilities,
                )
            )
        elif node.macro_op in _ATTENTION_MACROS:
            candidates.extend(
                _build_attention_candidates(
                    node,
                    allocations_by_node.get(node.node_id, []),
                    storage_bindings_by_id,
                    scenario=scenario,
                    capabilities=capabilities,
                )
            )

    return TilingPlanArtifact(
        graph_id=bound_nig_ir.graph_id,
        scenario_name=scenario.scenario_name,
        core_mode=capabilities.core_mode,
        candidates=candidates,
    )


def _build_gemm_candidates(
    node: NIGNode,
    allocations: list[PlannedAllocation],
    storage_bindings_by_id: dict[str, StorageBindingDescriptor],
    *,
    scenario: ScenarioProfile,
    capabilities: ArchitectureCapabilities,
) -> list[TileCandidate]:
    logical_n = _logical_n_dimension(node)
    n_tile = min(capabilities.mxu.cols, logical_n)
    k_tile = min(capabilities.mxu.rows, max(1, node.quant.k_tile_size))
    base_m_tile = _infer_gemm_base_m_tile(allocations, n_tile) or _fallback_logical_m_dimension(node)

    if scenario.mode == "decode":
        candidate_rows = [1]
        strategy = "decode-latency-first"
    else:
        candidate_rows = _prefill_m_tile_candidates(base_m_tile)
        strategy = "prefill-balanced"

    candidates = [
        _build_candidate(
            node,
            allocations,
            storage_bindings_by_id,
            strategy=strategy,
            candidate_m_tile=m_tile,
            base_m_tile=base_m_tile,
            n_tile=n_tile,
            k_tile=k_tile,
        )
        for m_tile in candidate_rows
    ]
    return _rank_candidates(candidates, scenario=scenario)


def _build_attention_candidates(
    node: NIGNode,
    allocations: list[PlannedAllocation],
    storage_bindings_by_id: dict[str, StorageBindingDescriptor],
    *,
    scenario: ScenarioProfile,
    capabilities: ArchitectureCapabilities,
) -> list[TileCandidate]:
    if node.binding is None or node.binding.attention is None:
        return []

    attention = node.binding.attention
    logical_n = _logical_n_dimension(node)
    n_tile = min(capabilities.mxu.cols, logical_n)
    k_tile = min(capabilities.mxu.rows, max(1, attention.head_dim))

    if scenario.mode == "decode" or node.macro_op == "SDPA_DECODE" or attention.mode == "decode":
        candidate_rows = [1]
        strategy = "decode-latency-first"
        base_m_tile = 1
    else:
        base_m_tile = max(1, min(attention.query_len, 16))
        candidate_rows = [m_tile for m_tile in (base_m_tile, 8, 4) if m_tile <= base_m_tile]
        strategy = "prefill-attention-streaming"

    candidates = [
        _build_candidate(
            node,
            allocations,
            storage_bindings_by_id,
            strategy=strategy,
            candidate_m_tile=m_tile,
            base_m_tile=base_m_tile,
            n_tile=n_tile,
            k_tile=k_tile,
        )
        for m_tile in candidate_rows
    ]
    return _rank_candidates(candidates, scenario=scenario)


def _build_candidate(
    node: NIGNode,
    allocations: list[PlannedAllocation],
    storage_bindings_by_id: dict[str, StorageBindingDescriptor],
    *,
    strategy: str,
    candidate_m_tile: int,
    base_m_tile: int,
    n_tile: int,
    k_tile: int,
) -> TileCandidate:
    scale = candidate_m_tile / max(base_m_tile, 1)
    scaled_pressure = _scaled_region_pressure_snapshot(allocations, scale)
    read_bytes = _scaled_input_bytes(allocations, scale)
    write_bytes = _scaled_output_bytes(allocations, scale)
    total_vmem_bytes = _scaled_total_vmem_bytes(allocations, scale)
    quant_alignment_ok, quant_alignment_message = _quant_alignment(node, k_tile)
    storage_binding_ids = _storage_binding_ids(allocations)
    storage_read_bytes_by_source_kind = _storage_read_bytes_by_source_kind(
        allocations,
        storage_bindings_by_id=storage_bindings_by_id,
        scale=scale,
    )
    storage_read_bytes_by_backing_store = _storage_read_bytes_by_backing_store(
        allocations,
        storage_bindings_by_id=storage_bindings_by_id,
        scale=scale,
    )

    resource_summary = TileCandidateResourceSummary(
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        total_vmem_bytes=total_vmem_bytes,
        dma_bytes=read_bytes + write_bytes,
        region_pressure_bytes=scaled_pressure,
        storage_binding_ids=storage_binding_ids,
        storage_read_bytes_by_source_kind=storage_read_bytes_by_source_kind,
        storage_read_bytes_by_backing_store=storage_read_bytes_by_backing_store,
    )

    return TileCandidate(
        candidate_id=f"{node.node_id}.m{candidate_m_tile}.n{n_tile}.k{k_tile}",
        node_id=node.node_id,
        macro_op=node.macro_op,
        strategy=strategy,
        m_tile=candidate_m_tile,
        n_tile=n_tile,
        k_tile=k_tile,
        read_bytes=read_bytes,
        write_bytes=write_bytes,
        total_vmem_bytes=total_vmem_bytes,
        rank=1,
        ranking_reason="unranked",
        quant_alignment_ok=quant_alignment_ok,
        quant_alignment_message=quant_alignment_message,
        source_memory_plan_region_pressure=scaled_pressure,
        resource_summary=resource_summary,
        issues=[],
    )


def _group_allocations_by_node(
    allocations: list[PlannedAllocation],
) -> dict[str, list[PlannedAllocation]]:
    allocations_by_node: dict[str, list[PlannedAllocation]] = defaultdict(list)
    for allocation in allocations:
        allocations_by_node[allocation.node_id].append(allocation)
    return dict(allocations_by_node)


def _infer_gemm_base_m_tile(allocations: list[PlannedAllocation], n_tile: int) -> int:
    accum_bytes = sum(
        allocation.size_bytes
        for allocation in allocations
        if allocation.region_name == "accum" and allocation.tensor_name == "accum"
    )
    if accum_bytes <= 0 or n_tile <= 0:
        return 0
    return max(1, accum_bytes // max(1, n_tile * 4))


def _prefill_m_tile_candidates(base_m_tile: int) -> list[int]:
    candidates = [m_tile for m_tile in _PREFILL_TEMPLATE if m_tile <= max(base_m_tile, 1)]
    if not candidates or candidates[0] != base_m_tile:
        candidates.insert(0, max(1, base_m_tile))

    deduped: list[int] = []
    for m_tile in candidates:
        if m_tile not in deduped:
            deduped.append(m_tile)
        if len(deduped) == 4:
            break
    return deduped


def _scaled_region_pressure_snapshot(
    allocations: list[PlannedAllocation],
    scale: float,
) -> dict[str, int]:
    pressure: dict[str, int] = defaultdict(int)
    for allocation in allocations:
        if allocation.address_space != "VMEM" or allocation.region_name is None:
            continue
        pressure[allocation.region_name] += _scaled_allocation_bytes(allocation, scale)
    return dict(pressure)


def _scaled_input_bytes(allocations: list[PlannedAllocation], scale: float) -> int:
    total = sum(
        _scaled_allocation_bytes(allocation, scale)
        for allocation in allocations
        if allocation.tensor_role in {"input", "weight", "quant_param", "kv_cache"}
    )
    return max(0, total)


def _scaled_output_bytes(allocations: list[PlannedAllocation], scale: float) -> int:
    total = sum(
        _scaled_allocation_bytes(allocation, scale)
        for allocation in allocations
        if allocation.tensor_role == "output"
    )
    return max(0, total)


def _scaled_total_vmem_bytes(allocations: list[PlannedAllocation], scale: float) -> int:
    total = sum(
        _scaled_allocation_bytes(allocation, scale)
        for allocation in allocations
        if allocation.address_space == "VMEM"
    )
    return max(0, total)


def _scaled_bytes(value: int, scale: float) -> int:
    return max(1 if value > 0 else 0, int(round(value * scale)))


def _scaled_allocation_bytes(allocation: PlannedAllocation, scale: float) -> int:
    if allocation.tensor_role in {"weight", "quant_param"}:
        return allocation.size_bytes
    return _scaled_bytes(allocation.size_bytes, scale)


def _storage_binding_ids(allocations: list[PlannedAllocation]) -> list[str]:
    return sorted(
        {
            allocation.storage_binding_id
            for allocation in allocations
            if allocation.storage_binding_id is not None
        }
    )


def _storage_read_bytes_by_source_kind(
    allocations: list[PlannedAllocation],
    *,
    storage_bindings_by_id: dict[str, StorageBindingDescriptor],
    scale: float,
) -> dict[str, int]:
    by_kind: dict[str, int] = defaultdict(int)
    for allocation in allocations:
        if allocation.tensor_role not in {"weight", "quant_param", "kv_cache"}:
            continue
        if allocation.storage_binding_id is None:
            continue
        binding = storage_bindings_by_id.get(allocation.storage_binding_id)
        if binding is None:
            continue
        by_kind[binding.source_kind] += _scaled_allocation_bytes(allocation, scale)
    return dict(by_kind)


def _storage_read_bytes_by_backing_store(
    allocations: list[PlannedAllocation],
    *,
    storage_bindings_by_id: dict[str, StorageBindingDescriptor],
    scale: float,
) -> dict[str, int]:
    by_backing_store: dict[str, int] = defaultdict(int)
    for allocation in allocations:
        if allocation.tensor_role not in {"weight", "quant_param", "kv_cache"}:
            continue
        if allocation.storage_binding_id is None:
            continue
        binding = storage_bindings_by_id.get(allocation.storage_binding_id)
        if binding is None:
            continue
        by_backing_store[binding.backing_store] += _scaled_allocation_bytes(allocation, scale)
    return dict(by_backing_store)


def _rank_candidates(
    candidates: list[TileCandidate],
    *,
    scenario: ScenarioProfile,
) -> list[TileCandidate]:
    if not candidates:
        return []
    ranking_reason = (
        "decode-latency-first: smaller working-set wins; ties break on read_bytes then candidate_id"
        if scenario.mode == "decode"
        else "prefill-throughput-first: larger m_tile wins; ties break on total_vmem_bytes then staged_storage_bytes"
    )
    ranked = sorted(candidates, key=lambda candidate: _candidate_rank_key(candidate, scenario=scenario))
    return [
        candidate.model_copy(update={"rank": index + 1, "ranking_reason": ranking_reason})
        for index, candidate in enumerate(ranked)
    ]


def _candidate_rank_key(
    candidate: TileCandidate,
    *,
    scenario: ScenarioProfile,
) -> tuple[int, int, int, str]:
    staged_storage_bytes = sum(
        candidate.resource_summary.storage_read_bytes_by_backing_store.values()
        if candidate.resource_summary is not None
        else []
    )
    if scenario.mode == "decode":
        return (candidate.total_vmem_bytes, candidate.read_bytes, candidate.m_tile, candidate.candidate_id)
    return (-candidate.m_tile, candidate.total_vmem_bytes, staged_storage_bytes, candidate.candidate_id)


def _quant_alignment(node: NIGNode, k_tile: int) -> tuple[bool, str]:
    if node.quant.quant_mode == "none":
        return (True, f"quantization disabled; using k_tile={k_tile}")
    group_size = node.quant.group_size
    is_aligned = (k_tile % group_size == 0) or (group_size % k_tile == 0)
    if is_aligned:
        return (True, f"group_size={group_size} aligns with k_tile={k_tile}")
    return (False, f"group_size={group_size} does not align with k_tile={k_tile}")


def _fallback_logical_m_dimension(node: NIGNode) -> int:
    resolved_shape = node.binding.resolved_shape if node.binding is not None else node.shape
    if not resolved_shape:
        return 1
    logical_m = 1
    for dim in resolved_shape[:-1]:
        logical_m *= max(1, dim)
    return max(1, logical_m)


def _logical_n_dimension(node: NIGNode) -> int:
    resolved_shape = node.binding.resolved_shape if node.binding is not None else node.shape
    if not resolved_shape:
        return 1
    return max(1, resolved_shape[-1])
