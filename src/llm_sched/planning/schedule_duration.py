"""Shared schedule duration policy for SPEC-10/11."""

from __future__ import annotations

from math import ceil

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.contracts.memory_plan import PlannedAllocation
from llm_sched.contracts.tiling_plan import TileCandidate
from llm_sched.ir.nig import NIGNode


_GEMM_LIKE_MACROS = frozenset({"GEMM", "WDQ_GEMM", "RMSNORM_GEMM", "SDPA"})
_VECTOR_STAGE_MACROS = frozenset(
    {
        "RMSNORM",
        "ELEM_ADD",
        "GEGLU",
        "ROPE",
        "ATTENTION_MASK_PREP",
        "EMBEDDING_LOOKUP",
        "SHAPE_HELPER",
        "LAYOUT_FALLBACK",
    }
)
_VECTOR_STAGE_FACTORS: dict[tuple[str, str], int] = {
    ("RMSNORM", "compute"): 2,
    ("GEGLU", "prepare"): 2,
    ("GEGLU", "compute"): 3,
    ("ROPE", "prepare"): 2,
    ("ROPE", "compute"): 2,
    ("ATTENTION_MASK_PREP", "prepare"): 2,
    ("ATTENTION_MASK_PREP", "compute"): 2,
    ("LAYOUT_FALLBACK", "prepare"): 2,
    ("LAYOUT_FALLBACK", "compute"): 2,
}
_ATTENTION_MASK_PREP_COMPLEXITY = {
    "Add": 1,
    "Sub": 1,
    "Mul": 1,
    "Max": 1,
    "Greater": 1,
    "Neg": 1,
    "Trilu": 2,
    "ScatterND": 4,
}


def estimate_stage_duration_slots(
    *,
    node: NIGNode,
    stage: str,
    candidate: TileCandidate | None,
    allocations: list[PlannedAllocation],
    capabilities: ArchitectureCapabilities,
    transfer_bytes: int = 0,
    transfer_kind: str | None = None,
) -> int:
    if stage == "transfer":
        transport_slots, sync_slots = estimate_transfer_timing_slots(
            transfer_bytes=transfer_bytes,
            transfer_kind=transfer_kind,
            capabilities=capabilities,
        )
        return max(1, transport_slots + sync_slots)
    if stage in {"dma_in", "store"}:
        transport_slots, prefix_slots, tail_slots = _dma_stage_slot_breakdown(
            node=node,
            stage=stage,
            candidate=candidate,
            allocations=allocations,
            capabilities=capabilities,
        )
        return max(1, prefix_slots + transport_slots + tail_slots)
    if stage == "prepare":
        base_duration = max(1, ceil(_vector_element_count(node, candidate) / max(capabilities.vpu.lanes, 1)))
        return max(1, base_duration * _vector_stage_factor_for_node(node=node, stage=stage))
    if stage == "compute":
        if node.macro_op == "SDPA_DECODE":
            vpu_slots, dma_slots = _sdpa_decode_compute_slot_breakdown(
                node=node,
                candidate=candidate,
                allocations=allocations,
                capabilities=capabilities,
            )
            return max(vpu_slots, dma_slots)
        if node.macro_op in _GEMM_LIKE_MACROS:
            _body_duration, overhead_slots = _mixed_engine_slot_breakdown(
                node=node,
                candidate=candidate,
                capabilities=capabilities,
            )
            return max(
                1,
                _body_duration + overhead_slots,
            )
        if node.macro_op in _VECTOR_STAGE_MACROS:
            base_duration = max(1, ceil(_vector_element_count(node, candidate) / max(capabilities.vpu.lanes, 1)))
            return max(1, base_duration * _vector_stage_factor_for_node(node=node, stage=stage))
    return 1


def _dma_stage_bytes(
    stage: str,
    allocations: list[PlannedAllocation],
    candidate: TileCandidate | None,
) -> int:
    if candidate is not None and candidate.resource_summary is not None:
        if stage == "dma_in":
            return max(1, candidate.resource_summary.read_bytes)
        return max(1, candidate.resource_summary.write_bytes)
    if stage == "dma_in":
        roles = {"input", "weight", "quant_param", "kv_cache", "metadata", "temp"}
    else:
        roles = {"output", "temp"}
    byte_count = sum(allocation.size_bytes for allocation in allocations if allocation.tensor_role in roles)
    return max(1, byte_count)


def _tile_shape(node: NIGNode, candidate: TileCandidate | None) -> tuple[int, int, int]:
    if candidate is not None:
        return candidate.m_tile, candidate.n_tile, candidate.k_tile
    resolved_shape = list(node.binding.resolved_shape if node.binding is not None else node.shape)
    m = max(1, resolved_shape[0]) if resolved_shape else 1
    n = max(1, resolved_shape[-1]) if resolved_shape else 1
    k = max(1, node.quant.k_tile_size)
    return m, n, k


def _vector_element_count(node: NIGNode, candidate: TileCandidate | None) -> int:
    if candidate is not None and node.macro_op in _GEMM_LIKE_MACROS:
        return max(1, candidate.m_tile * candidate.n_tile)
    resolved_shape = list(node.binding.resolved_shape if node.binding is not None else node.shape)
    element_count = 1
    for dim in resolved_shape:
        element_count *= max(1, dim)
    return max(1, element_count)


def _vector_stage_factor(macro_op: str, stage: str) -> int:
    return _VECTOR_STAGE_FACTORS.get((macro_op, stage), 1)


def _vector_stage_factor_for_node(*, node: NIGNode, stage: str) -> int:
    base_factor = _vector_stage_factor(node.macro_op, stage)
    if node.macro_op == "ATTENTION_MASK_PREP" and stage == "compute":
        return max(1, base_factor * _attention_mask_prep_complexity(node))
    return base_factor


def _attention_mask_prep_complexity(node: NIGNode) -> int:
    return _ATTENTION_MASK_PREP_COMPLEXITY.get(str(node.attrs.get("original_op_kind", "")), 1)


def _mixed_engine_slot_breakdown(
    *,
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> tuple[int, int]:
    m, n, k = _tile_shape(node, candidate)
    base_duration = max(1, ceil((m * n * k) / max(capabilities.mxu.rows * capabilities.mxu.cols, 1)))
    overhead_slots = _mixed_engine_compute_overhead_slots(node, candidate, capabilities)
    return base_duration, overhead_slots


def _mixed_engine_compute_overhead_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    if node.macro_op == "WDQ_GEMM":
        m_tile, _n_tile, k_tile = _tile_shape(node, candidate)
        return max(1, ceil((m_tile * k_tile) / max(capabilities.vpu.lanes, 1)))
    if node.macro_op == "RMSNORM_GEMM":
        return max(1, ceil(_vector_element_count(node, candidate) / max(capabilities.vpu.lanes, 1)))
    if node.macro_op == "SDPA":
        return max(1, ceil(_attention_score_element_count(node) / max(capabilities.vpu.lanes, 1)))
    return 0


def _attention_score_element_count(node: NIGNode) -> int:
    if node.binding is not None and node.binding.attention is not None:
        attention = node.binding.attention
        return max(1, attention.query_len * attention.kv_len * attention.num_heads)
    query_len = max(1, int(node.attrs.get("query_len", 1)))
    kv_len = max(1, int(node.attrs.get("kv_len", 1)))
    num_heads = max(1, int(node.attrs.get("num_heads", 1)))
    return max(1, query_len * kv_len * num_heads)


def _bandwidth_cycles(byte_count: int, bandwidth_gbps: float) -> int:
    divisor = max(1.0, bandwidth_gbps * 64.0)
    return max(1, ceil(byte_count / divisor))


def estimate_transfer_timing_slots(
    *,
    transfer_bytes: int,
    transfer_kind: str | None,
    capabilities: ArchitectureCapabilities,
) -> tuple[int, int]:
    bandwidth_gbps = (
        capabilities.core_link.bandwidth_gbps
        if transfer_kind == "core_link"
        else capabilities.shared_dma.effective_bandwidth_gbps
    )
    transport_slots = max(1, _bandwidth_cycles(transfer_bytes, bandwidth_gbps))
    sync_slots = max(0, capabilities.sync.cross_core_transfer_cost_cycles)
    return transport_slots, sync_slots


def estimate_stage_resource_reservations(
    *,
    macro_op: str,
    stage: str,
    resource_set: list[str],
    duration_slots: int,
    sync_cost_cycles: int = 0,
    node: NIGNode | None = None,
    candidate: TileCandidate | None = None,
    capabilities: ArchitectureCapabilities | None = None,
) -> list[tuple[str, int, int]]:
    if not resource_set:
        return []
    if stage in {"dma_in", "store"} and node is not None and capabilities is not None:
        prefix_slots = 0
        tail_slots = 0
        if stage == "dma_in" and macro_op == "WDQ_GEMM":
            tail_slots = _wdq_dma_tail_slots(node, candidate, capabilities)
        elif stage == "dma_in" and macro_op == "ROPE_TABLE":
            tail_slots = _rope_table_dma_tail_slots(node, candidate, capabilities)
        elif stage == "dma_in" and macro_op == "EMBEDDING_LOOKUP":
            tail_slots = _embedding_lookup_dma_tail_slots(node, candidate, capabilities)
        elif stage == "dma_in" and macro_op == "KVLOAD":
            tail_slots = _kvload_dma_tail_slots(node, candidate, capabilities)
        elif stage == "store" and macro_op == "KVSTORE":
            prefix_slots = _kvstore_store_prefix_slots(node, candidate, capabilities)
        elif stage == "store" and macro_op == "ATTENTION_MASK_PREP":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _attention_mask_prep_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "ELEM_ADD":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _elem_add_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "LAYOUT_FALLBACK":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _layout_fallback_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "RMSNORM":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _rmsnorm_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "EMBEDDING_LOOKUP":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _embedding_lookup_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "GEGLU":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _geglu_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op == "ROPE":
            prefix_slots = min(
                max(0, duration_slots - 1),
                _rope_store_prefix_slots(node, candidate, capabilities),
            )
        elif stage == "store" and macro_op in {"SDPA", "SDPA_DECODE"}:
            prefix_slots = min(
                max(0, duration_slots - 1),
                _sdpa_store_prefix_slots(node, candidate, capabilities),
            )
        transport_slots = max(1, duration_slots - prefix_slots - tail_slots)
        if stage == "dma_in" and macro_op == "WDQ_GEMM" and "DMA" in resource_set:
            reservations: list[tuple[str, int, int]] = []
            if transport_slots > 0:
                reservations.append(("DMA", 0, transport_slots))
            if tail_slots > 0:
                reservations.append(("WDQ", transport_slots, tail_slots))
            return reservations
        if stage == "dma_in" and macro_op == "ROPE_TABLE" and "DMA" in resource_set:
            reservations = []
            if transport_slots > 0:
                reservations.append(("DMA", 0, transport_slots))
            if tail_slots > 0:
                reservations.append(("VPU", transport_slots, tail_slots))
            return reservations
        if stage == "dma_in" and macro_op == "EMBEDDING_LOOKUP" and "DMA" in resource_set:
            reservations = []
            if transport_slots > 0:
                reservations.append(("DMA", 0, transport_slots))
            if tail_slots > 0:
                reservations.append(("VPU", transport_slots, tail_slots))
            return reservations
        if stage == "dma_in" and macro_op == "KVLOAD" and "DMA" in resource_set:
            reservations = []
            if transport_slots > 0:
                reservations.append(("DMA", 0, transport_slots))
            if tail_slots > 0:
                reservations.append(("VPU", transport_slots, tail_slots))
            return reservations
        if stage == "store" and macro_op == "KVSTORE" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "ATTENTION_MASK_PREP" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "ELEM_ADD" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "LAYOUT_FALLBACK" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "RMSNORM" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "EMBEDDING_LOOKUP" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "GEGLU" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op == "ROPE" and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
        if stage == "store" and macro_op in {"SDPA", "SDPA_DECODE"} and "DMA" in resource_set:
            reservations = []
            if prefix_slots > 0:
                reservations.append(("VPU", 0, prefix_slots))
            if transport_slots > 0:
                reservations.append(("DMA", prefix_slots, transport_slots))
            return reservations
    duration_slots = max(1, duration_slots)
    if stage == "transfer":
        transport_slots = max(1, duration_slots - max(0, sync_cost_cycles))
        sync_slots = max(0, duration_slots - transport_slots)
        reservations = [(resource_name, 0, transport_slots) for resource_name in resource_set]
        if sync_slots > 0:
            reservations.append(("SYNC", transport_slots, sync_slots))
        return reservations
    if stage == "compute" and duration_slots > 1:
        if (
            macro_op == "SDPA_DECODE"
            and node is not None
            and capabilities is not None
            and {"DMA", "VPU"}.issubset(resource_set)
        ):
            vpu_slots, dma_slots = _sdpa_decode_compute_slot_breakdown(
                node=node,
                candidate=candidate,
                allocations=[],
                capabilities=capabilities,
            )
            if candidate is not None and candidate.resource_summary is not None:
                dma_slots = max(
                    1,
                    _bandwidth_cycles(
                        _sdpa_decode_stream_bytes(candidate, []),
                        capabilities.shared_dma.effective_bandwidth_gbps,
                    ),
                )
            elif duration_slots > dma_slots:
                dma_slots = duration_slots
            return [
                ("DMA", 0, min(duration_slots, dma_slots)),
                ("VPU", 0, min(duration_slots, vpu_slots)),
            ]
        if (
            node is not None
            and capabilities is not None
            and macro_op == node.macro_op
            and {"MXU", "VPU"}.issubset(resource_set)
        ):
            base_duration, overhead_slots = _mixed_engine_slot_breakdown(
                node=node,
                candidate=candidate,
                capabilities=capabilities,
            )
            overhead_slots = min(max(1, overhead_slots), max(1, duration_slots - 1))
            if macro_op == "RMSNORM_GEMM":
                body_slots = max(1, duration_slots - overhead_slots)
                return [
                    ("VPU", 0, overhead_slots),
                    ("MXU", overhead_slots, body_slots),
                ]
            if macro_op == "SDPA":
                vpu_prefix_slots, mxu_slots, vpu_tail_slots = _sdpa_compute_phase_slots(
                    duration_slots=duration_slots,
                    overhead_slots=overhead_slots,
                )
                reservations: list[tuple[str, int, int]] = []
                if vpu_prefix_slots > 0:
                    reservations.append(("VPU", 0, vpu_prefix_slots))
                reservations.append(("MXU", vpu_prefix_slots, mxu_slots))
                if vpu_tail_slots > 0:
                    reservations.append(("VPU", vpu_prefix_slots + mxu_slots, vpu_tail_slots))
                return reservations
        if macro_op == "SDPA" and {"MXU", "VPU"}.issubset(resource_set):
            vpu_overhead_slots = max(1, ceil(duration_slots / 4))
            vpu_prefix_slots, mxu_slots, vpu_tail_slots = _sdpa_compute_phase_slots(
                duration_slots=duration_slots,
                overhead_slots=vpu_overhead_slots,
            )
            reservations: list[tuple[str, int, int]] = []
            if vpu_prefix_slots > 0:
                reservations.append(("VPU", 0, vpu_prefix_slots))
            reservations.append(("MXU", vpu_prefix_slots, mxu_slots))
            if vpu_tail_slots > 0:
                reservations.append(("VPU", vpu_prefix_slots + mxu_slots, vpu_tail_slots))
            return reservations
        if macro_op == "GEGLU" and {"MXU", "VPU"}.issubset(resource_set):
            vpu_prefix_slots, mxu_slots, vpu_tail_slots = _geglu_compute_phase_slots(duration_slots)
            reservations: list[tuple[str, int, int]] = []
            if vpu_prefix_slots > 0:
                reservations.append(("VPU", 0, vpu_prefix_slots))
            reservations.append(("MXU", vpu_prefix_slots, mxu_slots))
            if vpu_tail_slots > 0:
                reservations.append(("VPU", vpu_prefix_slots + mxu_slots, vpu_tail_slots))
            return reservations
        if macro_op == "RMSNORM_GEMM" and {"MXU", "VPU"}.issubset(resource_set):
            vpu_prefix_slots = max(1, ceil(duration_slots / 4))
            mxu_slots = max(1, duration_slots - vpu_prefix_slots)
            return [
                ("VPU", 0, vpu_prefix_slots),
                ("MXU", vpu_prefix_slots, duration_slots - vpu_prefix_slots),
            ]
        if macro_op == "WDQ_GEMM" and {"WDQ", "MXU"}.issubset(resource_set):
            wdq_prefix_slots = max(1, ceil(duration_slots / 8))
            return [
                ("WDQ", 0, wdq_prefix_slots),
                ("MXU", wdq_prefix_slots, max(1, duration_slots - wdq_prefix_slots)),
            ]
    return [(resource_name, 0, duration_slots) for resource_name in resource_set]


def _dma_stage_slot_breakdown(
    *,
    node: NIGNode,
    stage: str,
    candidate: TileCandidate | None,
    allocations: list[PlannedAllocation],
    capabilities: ArchitectureCapabilities,
) -> tuple[int, int, int]:
    byte_count = _dma_stage_bytes(stage, allocations, candidate)
    transport_slots = max(1, _bandwidth_cycles(byte_count, capabilities.shared_dma.effective_bandwidth_gbps))
    prefix_slots = 0
    tail_slots = 0
    if stage == "dma_in" and node.macro_op == "WDQ_GEMM":
        tail_slots = _wdq_dma_tail_slots(node, candidate, capabilities)
    elif stage == "dma_in" and node.macro_op == "ROPE_TABLE":
        tail_slots = _rope_table_dma_tail_slots(node, candidate, capabilities)
    elif stage == "dma_in" and node.macro_op == "EMBEDDING_LOOKUP":
        tail_slots = _embedding_lookup_dma_tail_slots(node, candidate, capabilities)
    elif stage == "dma_in" and node.macro_op == "KVLOAD":
        tail_slots = _kvload_dma_tail_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "KVSTORE":
        prefix_slots = _kvstore_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "ATTENTION_MASK_PREP":
        prefix_slots = _attention_mask_prep_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "ELEM_ADD":
        prefix_slots = _elem_add_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "RMSNORM":
        prefix_slots = _rmsnorm_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "EMBEDDING_LOOKUP":
        prefix_slots = _embedding_lookup_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "GEGLU":
        prefix_slots = _geglu_store_prefix_slots(node, candidate, capabilities)
    elif stage == "store" and node.macro_op == "ROPE":
        prefix_slots = _rope_store_prefix_slots(node, candidate, capabilities)
    return transport_slots, prefix_slots, tail_slots


def _sdpa_decode_stream_bytes(
    candidate: TileCandidate | None,
    allocations: list[PlannedAllocation],
) -> int:
    if candidate is not None and candidate.resource_summary is not None:
        return max(1, candidate.resource_summary.read_bytes)
    byte_count = sum(
        allocation.size_bytes
        for allocation in allocations
        if allocation.tensor_role in {"input", "kv_cache", "metadata", "temp"}
    )
    return max(1, byte_count)


def _sdpa_decode_compute_slot_breakdown(
    *,
    node: NIGNode,
    candidate: TileCandidate | None,
    allocations: list[PlannedAllocation],
    capabilities: ArchitectureCapabilities,
) -> tuple[int, int]:
    vpu_slots = max(1, ceil(_attention_score_element_count(node) / max(capabilities.vpu.lanes, 1)))
    dma_slots = max(
        1,
        _bandwidth_cycles(
            _sdpa_decode_stream_bytes(candidate, allocations),
            capabilities.shared_dma.effective_bandwidth_gbps,
        ),
    )
    return vpu_slots, dma_slots


def _wdq_dma_tail_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    m_tile, _n_tile, k_tile = _tile_shape(node, candidate)
    group_size = max(1, node.quant.group_size)
    group_count = max(1, ceil(k_tile / group_size))
    return max(1, ceil((m_tile * group_count) / max(capabilities.vpu.sublanes, 1)))


def _rope_table_dma_tail_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    output_count = max(len(node.outputs), 1)
    return max(
        1,
        ceil((_vector_element_count(node, candidate) * output_count * 2) / max(capabilities.vpu.lanes, 1)),
    )


def _embedding_lookup_dma_tail_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    return max(1, ceil(_vector_element_count(node, candidate) / max(capabilities.vpu.lanes, 1)))


def _embedding_lookup_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate fused gather-scale output normalization before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    divisor_scale = 128 if bool(node.attrs.get("scaled_output")) else 256
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * divisor_scale, 1)))


def _rmsnorm_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate final normalization-vector packing before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 256, 1)))


def _elem_add_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate final residual-write packing before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 512, 1)))


def _geglu_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate final gated-activation output packing before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 128, 1)))


def _attention_mask_prep_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate final mask materialization before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    complexity = _attention_mask_prep_complexity(node)
    return max(1, ceil((output_elements * complexity) / max(capabilities.vpu.lanes * 128, 1)))


def _geglu_compute_phase_slots(duration_slots: int) -> tuple[int, int, int]:
    if duration_slots <= 2:
        return 0, max(1, duration_slots - 1), 1
    vpu_prefix_slots = max(1, ceil(duration_slots / 8))
    vpu_tail_slots = max(1, ceil(duration_slots / 4))
    max_prefix_slots = max(1, duration_slots - vpu_tail_slots - 1)
    vpu_prefix_slots = min(vpu_prefix_slots, max_prefix_slots)
    mxu_slots = max(1, duration_slots - vpu_prefix_slots - vpu_tail_slots)
    vpu_tail_slots = max(1, duration_slots - vpu_prefix_slots - mxu_slots)
    return vpu_prefix_slots, mxu_slots, vpu_tail_slots


def _sdpa_compute_phase_slots(*, duration_slots: int, overhead_slots: int) -> tuple[int, int, int]:
    if duration_slots <= 1:
        return 0, 1, 0
    clamped_overhead_slots = min(max(1, overhead_slots), max(1, duration_slots - 1))
    vpu_prefix_slots = max(1, ceil(clamped_overhead_slots / 2))
    vpu_tail_slots = max(0, clamped_overhead_slots - vpu_prefix_slots)
    max_prefix_slots = max(1, duration_slots - vpu_tail_slots - 1)
    vpu_prefix_slots = min(vpu_prefix_slots, max_prefix_slots)
    mxu_slots = max(1, duration_slots - vpu_prefix_slots - vpu_tail_slots)
    vpu_tail_slots = max(0, duration_slots - vpu_prefix_slots - mxu_slots)
    return vpu_prefix_slots, mxu_slots, vpu_tail_slots


def _kvload_dma_tail_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    del candidate
    return _kv_layout_vector_slots(node, capabilities)


def _kvstore_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    del candidate
    return _kv_layout_vector_slots(node, capabilities)


def _kv_layout_vector_slots(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> int:
    if node.binding is not None and node.binding.attention is not None:
        attention = node.binding.attention
        element_count = max(1, attention.query_len * attention.head_dim * attention.num_key_value_heads)
    else:
        resolved_shape = list(node.binding.resolved_shape if node.binding is not None else node.shape)
        element_count = max(1, resolved_shape[-1] if resolved_shape else 1)
    return max(1, ceil(element_count / max(capabilities.vpu.lanes, 1)))


def _sdpa_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate the fused post-attention transpose/reshape packing before output writeback.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 64, 1)))


def _layout_fallback_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate transpose-like packing before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 64, 1)))


def _rope_store_prefix_slots(
    node: NIGNode,
    candidate: TileCandidate | None,
    capabilities: ArchitectureCapabilities,
) -> int:
    # Approximate the rotate-half slice/concat packing before the later DMA writeback window.
    output_elements = _vector_element_count(node, candidate)
    return max(1, ceil(output_elements / max(capabilities.vpu.lanes * 32, 1)))
