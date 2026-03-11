"""Lightweight Analysis IR estimator for pseudo/fallback NIG workloads."""

from math import ceil, prod

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.target_profile import TargetProfile
from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
from llm_sched.ir.nig import NIGIR, NIGNode


def estimate_nig_analysis(
    nig_ir: NIGIR,
    hardware: TargetProfile | ArchitectureCapabilities,
) -> AnalysisIR:
    capabilities = _resolve_capabilities(hardware)
    records: list[AnalysisRecord] = []

    for node in nig_ir.nodes:
        estimator = _ESTIMATOR_BY_MACRO_OP.get(node.macro_op)
        if estimator is None:
            continue

        metrics, tags = estimator(node, capabilities)
        records.append(
            AnalysisRecord(
                record_id=_analysis_record_id(node.node_id),
                subject_id=node.node_id,
                metrics=metrics,
                tags=tags,
                audit_ref=node.audit_ref.model_copy(
                    update={"nig_node_ids": node.audit_ref.nig_node_ids or [node.node_id]},
                    deep=True,
                ),
            )
        )

    return AnalysisIR(
        ir_version=nig_ir.ir_version,
        graph_id=nig_ir.graph_id,
        records=records,
    )


def _resolve_capabilities(
    hardware: TargetProfile | ArchitectureCapabilities,
) -> ArchitectureCapabilities:
    if isinstance(hardware, ArchitectureCapabilities):
        return hardware
    return ArchitectureCapabilities.from_target_profile(hardware)


def _analysis_record_id(node_id: str) -> str:
    return f"analysis.record.{node_id.replace('.', '_')}"


def _estimate_attention_mask_prep(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> tuple[dict[str, float], list[str]]:
    elements = _tensor_elements(node.shape)
    dtype_bytes = _dtype_size(node.quant.activation_dtype)
    write_bytes = float(elements * dtype_bytes)
    read_bytes = float(write_bytes * max(len(node.inputs), 1))
    complexity = _MASK_PREP_COMPLEXITY.get(str(node.attrs.get("original_op_kind", "")), 1)
    estimated_cycles = float(max(1, ceil((elements * complexity) / capabilities.vpu.lanes)))
    return (
        _metrics(read_bytes, write_bytes, estimated_cycles),
        _with_dynamic_shape_tag(node, ["pseudo-fallback", "attention-mask-prep", "memory-bound"]),
    )


def _estimate_shape_helper(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> tuple[dict[str, float], list[str]]:
    elements = _tensor_elements(node.shape)
    dtype_bytes = _dtype_size(node.quant.activation_dtype)
    write_bytes = float(elements * dtype_bytes)
    read_bytes = float(max(write_bytes, len(node.inputs) * dtype_bytes))
    estimated_cycles = float(max(1, ceil(max(elements, len(node.inputs)) / capabilities.vpu.sublanes)))
    return (
        _metrics(read_bytes, write_bytes, estimated_cycles),
        _with_dynamic_shape_tag(node, ["pseudo-fallback", "shape-helper", "metadata-bound"]),
    )


def _estimate_layout_fallback(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> tuple[dict[str, float], list[str]]:
    elements = _tensor_elements(node.shape)
    dtype_bytes = _dtype_size(node.quant.activation_dtype)
    read_bytes = float(elements * dtype_bytes)
    write_bytes = float(elements * dtype_bytes)
    estimated_cycles = float(max(1, ceil(elements / capabilities.vpu.sublanes)))
    return (
        _metrics(read_bytes, write_bytes, estimated_cycles),
        _with_dynamic_shape_tag(node, ["pseudo-fallback", "layout-fallback", "memory-bound"]),
    )


def _estimate_embedding_lookup(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> tuple[dict[str, float], list[str]]:
    elements = _tensor_elements(node.shape)
    dtype_bytes = _dtype_size(node.quant.activation_dtype)
    write_bytes = float(elements * dtype_bytes)
    scale_bytes = float(dtype_bytes if bool(node.attrs.get("scaled_output")) else 0)
    read_bytes = float(write_bytes + scale_bytes)
    estimated_cycles = float(max(1, ceil(elements / capabilities.vpu.lanes)))
    return (
        _metrics(read_bytes, write_bytes, estimated_cycles),
        _with_dynamic_shape_tag(node, ["pseudo-fallback", "embedding-lookup", "memory-bound"]),
    )


def _estimate_rope_table(
    node: NIGNode,
    capabilities: ArchitectureCapabilities,
) -> tuple[dict[str, float], list[str]]:
    dtype_bytes = _dtype_size(node.quant.activation_dtype)
    output_elements = _tensor_elements(node.shape) * max(len(node.outputs), 1)
    head_dim = int(node.attrs.get("head_dim", node.shape[-1] if node.shape else 0))
    batch = _normalize_dim(node.shape[0]) if len(node.shape) >= 1 else 1
    seq_len = _normalize_dim(node.shape[1]) if len(node.shape) >= 2 else 1

    position_bytes = batch * seq_len * _dtype_size("int64")
    inv_freq_bytes = max(head_dim // 2, 1) * dtype_bytes
    read_bytes = float(position_bytes + inv_freq_bytes)
    write_bytes = float(output_elements * dtype_bytes)
    estimated_cycles = float(max(1, ceil((output_elements * 2) / capabilities.vpu.lanes)))
    return (
        _metrics(read_bytes, write_bytes, estimated_cycles),
        _with_dynamic_shape_tag(node, ["pseudo-fallback", "rope-table", "compute-bound"]),
    )


def _metrics(read_bytes: float, write_bytes: float, estimated_cycles: float) -> dict[str, float]:
    total_bytes = float(read_bytes + write_bytes)
    return {
        "read_bytes": float(read_bytes),
        "write_bytes": float(write_bytes),
        "total_bytes": total_bytes,
        "estimated_cycles": float(estimated_cycles),
        "bandwidth_pressure": total_bytes / max(estimated_cycles, 1.0),
    }


def _tensor_elements(shape: list[int]) -> int:
    if not shape:
        return 1
    return int(prod(_normalize_dim(dim) for dim in shape))


def _normalize_dim(dim: int) -> int:
    return dim if dim > 0 else 1


def _with_dynamic_shape_tag(node: NIGNode, tags: list[str]) -> list[str]:
    if any(dim <= 0 for dim in node.shape):
        return [*tags, "dynamic-shape-approx"]
    return tags


def _dtype_size(dtype: str) -> int:
    if dtype in {"bf16", "float16"}:
        return 2
    if dtype in {"float32", "int32"}:
        return 4
    if dtype == "int64":
        return 8
    if dtype == "bool":
        return 1
    return 1


_MASK_PREP_COMPLEXITY = {
    "Add": 1,
    "Sub": 1,
    "Mul": 1,
    "Max": 1,
    "Greater": 1,
    "Neg": 1,
    "Trilu": 2,
    "ScatterND": 4,
}

_ESTIMATOR_BY_MACRO_OP = {
    "ATTENTION_MASK_PREP": _estimate_attention_mask_prep,
    "SHAPE_HELPER": _estimate_shape_helper,
    "LAYOUT_FALLBACK": _estimate_layout_fallback,
    "EMBEDDING_LOOKUP": _estimate_embedding_lookup,
    "ROPE_TABLE": _estimate_rope_table,
}
