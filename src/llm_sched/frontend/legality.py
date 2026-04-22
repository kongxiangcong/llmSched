"""Frontend legality diagnostics for Graph IR."""

from llm_sched.arch import ArchitectureCapabilities
from llm_sched.config import TargetProfile
from pydantic import BaseModel, ConfigDict

from llm_sched.frontend.binding import (
    resolve_input_memory_classes,
)
from llm_sched.frontend.shape_binding import (
    FrontendShapeBinding,
    can_resolve_dynamic_shape,
    resolve_attention_binding_payload,
    resolve_canonical_layout,
)
from llm_sched.ir.graph import GraphIR


_CONTROL_FLOW_OPS = {"If", "Loop", "Scan"}
_SUPPORTED_LAYOUTS = {"SD", "HSD", "BHSD", "LBHSD", "METADATA"}
_QUANTIZED_WEIGHT_DTYPES = {"int4", "uint4", "nf4"}
_DEFAULT_K_TILE_SIZE = 128
_CANONICAL_OPCODE_BY_OP_KIND = {
    "GeGLU": "GEGLU",
    "KVLoad": "KVLOAD",
    "KVStore": "KVSTORE",
    "RMSNorm": "RMSNORM",
    "ROPE": "ROPE",
    "ResidualAdd": "ELEM_ADD",
}
_FALLBACK_SURFACE_BY_OP_KIND = {
    "AttentionMaskPrep": "ATTENTION_MASK_PREP",
    "EmbeddingLookup": "EMBEDDING_LOOKUP",
    "ROPETable": "ROPE_TABLE",
    "ShapeHelper": "SHAPE_HELPER",
    "LayoutFallback": "LAYOUT_FALLBACK",
}


class FrontendLegalityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str
    message: str
    node_id: str


class FrontendLegalityError(Exception):
    def __init__(self, issues: list[FrontendLegalityIssue]) -> None:
        self.issues = issues
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        rendered = ", ".join(f"{issue.rule_id}@{issue.node_id}" for issue in self.issues)
        return f"frontend legality failed: {rendered}"


def collect_frontend_legality_issues(
    graph_ir: GraphIR,
    hardware: TargetProfile | ArchitectureCapabilities | None = None,
    shape_bindings: FrontendShapeBinding | None = None,
) -> list[FrontendLegalityIssue]:
    capabilities = _resolve_capabilities(hardware)
    issues: list[FrontendLegalityIssue] = []

    for node in graph_ir.nodes:
        if node.op_kind in _CONTROL_FLOW_OPS:
            issues.append(
                FrontendLegalityIssue(
                    rule_id="unsupported_control_flow",
                    message=f"control-flow op '{node.op_kind}' is not supported",
                    node_id=node.node_id,
                )
            )

        if any(dim < 0 for dim in node.shape) and not _dynamic_shape_is_closeable(node, shape_bindings):
            issues.append(
                FrontendLegalityIssue(
                    rule_id="dynamic_shape_unresolved",
                    message="dynamic or unresolved shape dimensions are not allowed",
                    node_id=node.node_id,
                )
            )

        layout = node.attrs.get("layout")
        if layout is not None and layout not in _SUPPORTED_LAYOUTS:
            issues.append(
                FrontendLegalityIssue(
                    rule_id="unsupported_layout",
                    message=f"layout '{layout}' is not supported by the frontend contract",
                    node_id=node.node_id,
                )
            )

        if node.op_kind == "Linear" and node.attrs.get("weight_dtype") in _QUANTIZED_WEIGHT_DTYPES:
            issues.extend(_collect_graph_quant_binding_issues(node))

        if capabilities is not None:
            fallback_surface = _FALLBACK_SURFACE_BY_OP_KIND.get(node.op_kind)
            if fallback_surface is not None:
                issues.append(
                    FrontendLegalityIssue(
                        rule_id="no_hardware_mapping",
                        message=(
                            f"node '{node.op_kind}' is modeled explicitly but still requires "
                            f"a non-native fallback surface '{fallback_surface}'"
                        ),
                        node_id=node.node_id,
                    )
                )
                continue

            required_opcode = _required_opcode_for_node(node, shape_bindings=shape_bindings)
            if required_opcode is not None and required_opcode not in capabilities.opcodes:
                issues.append(
                    FrontendLegalityIssue(
                        rule_id="opcode_not_enabled",
                        message=f"required opcode '{required_opcode}' is not enabled by the active target",
                        node_id=node.node_id,
                    )
                )

            issues.extend(_collect_target_bound_issues(node, capabilities, shape_bindings=shape_bindings))

    return issues


def validate_frontend_legality(
    graph_ir: GraphIR,
    hardware: TargetProfile | ArchitectureCapabilities | None = None,
    shape_bindings: FrontendShapeBinding | None = None,
) -> None:
    issues = collect_frontend_legality_issues(graph_ir, hardware=hardware, shape_bindings=shape_bindings)
    if issues:
        raise FrontendLegalityError(issues)


def _resolve_capabilities(
    hardware: TargetProfile | ArchitectureCapabilities | None,
) -> ArchitectureCapabilities | None:
    if hardware is None:
        return None
    if isinstance(hardware, ArchitectureCapabilities):
        return hardware
    return ArchitectureCapabilities.from_target_profile(hardware)


def _required_opcode_for_node(
    node: object,
    shape_bindings: FrontendShapeBinding | None = None,
) -> str | None:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return None
    if node.op_kind == "Linear":
        weight_dtype = str(node.attrs.get("weight_dtype", node.dtype))
        return "WDQ_GEMM" if weight_dtype in _QUANTIZED_WEIGHT_DTYPES else "GEMM"
    if node.op_kind == "SDPA":
        if shape_bindings is not None:
            return "SDPA_DECODE" if shape_bindings.mode == "decode" else "SDPA"
        query_len = int(node.attrs.get("query_len", 0))
        return "SDPA_DECODE" if query_len == 1 else "SDPA"
    return _CANONICAL_OPCODE_BY_OP_KIND.get(node.op_kind)


def _dynamic_shape_is_closeable(
    node: object,
    shape_bindings: FrontendShapeBinding | None,
) -> bool:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return False
    if node.op_kind in _FALLBACK_SURFACE_BY_OP_KIND:
        return True
    return can_resolve_dynamic_shape(shape_bindings, node.op_kind, node.shape, node.attrs)


def _collect_target_bound_issues(
    node: object,
    capabilities: ArchitectureCapabilities,
    shape_bindings: FrontendShapeBinding | None = None,
) -> list[FrontendLegalityIssue]:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return []

    issues: list[FrontendLegalityIssue] = []

    if node.op_kind == "Linear" and node.attrs.get("weight_dtype") in _QUANTIZED_WEIGHT_DTYPES:
        issues.extend(_collect_quantization_issues(node, capabilities))

    if node.op_kind in {"KVStore", "KVLoad"}:
        issues.extend(_collect_kv_contract_issues(node, capabilities, shape_bindings=shape_bindings))

    return issues


def _collect_quantization_issues(
    node: object,
    capabilities: ArchitectureCapabilities,
) -> list[FrontendLegalityIssue]:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return []

    issues: list[FrontendLegalityIssue] = []
    weight_dtype = str(node.attrs.get("weight_dtype", ""))
    group_size = int(node.attrs.get("group_size", 0))

    if not capabilities.wdq.enabled:
        issues.append(
            FrontendLegalityIssue(
                rule_id="wdq_disabled",
                message="quantized Linear requires WDQ support in the active target",
                node_id=node.node_id,
            )
        )

    if weight_dtype != capabilities.quantization.weight_dtype:
        issues.append(
            FrontendLegalityIssue(
                rule_id="target_quant_weight_dtype_gap",
                message=(
                    f"quantized Linear weight_dtype '{weight_dtype}' does not match "
                    f"target weight_dtype '{capabilities.quantization.weight_dtype}'"
                ),
                node_id=node.node_id,
            )
        )

    if node.dtype != capabilities.quantization.activation_dtype:
        issues.append(
            FrontendLegalityIssue(
                rule_id="target_quant_activation_dtype_gap",
                message=(
                    f"quantized Linear activation dtype '{node.dtype}' does not match "
                    f"target activation dtype '{capabilities.quantization.activation_dtype}'"
                ),
                node_id=node.node_id,
            )
        )

    if _is_group_size_k_tile_aligned(group_size, _DEFAULT_K_TILE_SIZE) and (
        group_size not in capabilities.quantization.group_sizes
        or group_size not in capabilities.wdq.supported_group_sizes
    ):
        issues.append(
            FrontendLegalityIssue(
                rule_id="target_quant_group_size_gap",
                message=f"group_size '{group_size}' is not supported by the active target",
                node_id=node.node_id,
            )
        )

    return issues


def _collect_graph_quant_binding_issues(node: object) -> list[FrontendLegalityIssue]:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return []

    group_size = _coerce_positive_group_size(node.attrs.get("group_size"))
    if group_size is None:
        return [
            FrontendLegalityIssue(
                rule_id="quant_binding_missing",
                message="quantized Linear nodes must declare a positive group_size",
                node_id=node.node_id,
            )
        ]

    issues: list[FrontendLegalityIssue] = []
    if len(node.inputs) < 3:
        issues.append(
            FrontendLegalityIssue(
                rule_id="quant_binding_missing",
                message="quantized Linear nodes must declare a scale input",
                node_id=node.node_id,
            )
        )

    if not _is_group_size_k_tile_aligned(group_size, _DEFAULT_K_TILE_SIZE):
        issues.append(
            FrontendLegalityIssue(
                rule_id="unsupported_quant_group_size",
                message=(
                    f"group_size '{group_size}' must be a positive multiple of 16 and "
                    f"tile-align with K_tile={_DEFAULT_K_TILE_SIZE}"
                ),
                node_id=node.node_id,
            )
        )

    return issues


def _coerce_positive_group_size(value: object) -> int | None:
    try:
        group_size = int(value)
    except (TypeError, ValueError):
        return None
    return group_size if group_size > 0 else None


def _is_group_size_k_tile_aligned(group_size: int, k_tile_size: int) -> bool:
    if group_size <= 0:
        return False
    if group_size % 16 != 0:
        return False
    if group_size > k_tile_size:
        return False
    return k_tile_size % group_size == 0


def _collect_kv_contract_issues(
    node: object,
    capabilities: ArchitectureCapabilities,
    shape_bindings: FrontendShapeBinding | None = None,
) -> list[FrontendLegalityIssue]:
    from llm_sched.ir.graph import GraphNode

    if not isinstance(node, GraphNode):
        return []

    issues: list[FrontendLegalityIssue] = []

    if node.dtype != capabilities.kv_cache.dtype:
        issues.append(
            FrontendLegalityIssue(
                rule_id="kv_cache_dtype_mismatch",
                message=(
                    f"KV path dtype '{node.dtype}' does not match "
                    f"target kv_cache dtype '{capabilities.kv_cache.dtype}'"
                ),
                node_id=node.node_id,
            )
        )

    resolved_layout = (
        resolve_canonical_layout(
            shape_bindings,
            node.op_kind,
            _default_layout_for_op_kind(node.op_kind),
        )
        if shape_bindings is not None
        else str(node.attrs.get("layout", _default_layout_for_op_kind(node.op_kind)))
    )
    attention_payload = resolve_attention_binding_payload(shape_bindings, node.op_kind, node.attrs)
    kv_layout_rule = None if attention_payload is None else str(attention_payload.get("kv_layout_rule", ""))
    input_memory_classes = resolve_input_memory_classes(node.op_kind, node.inputs, attrs=node.attrs)

    should_check_layout = shape_bindings is not None or node.attrs.get("layout") is not None
    if should_check_layout and _uses_kv_cache(input_memory_classes) and not _kv_layout_is_compatible(
        resolved_layout,
        kv_layout_rule,
        capabilities.kv_cache.layout,
    ):
        issues.append(
            FrontendLegalityIssue(
                rule_id="kv_cache_layout_mismatch",
                message=(
                    f"KV path layout '{resolved_layout}' does not match "
                    f"target kv_cache layout '{capabilities.kv_cache.layout}'"
                ),
                node_id=node.node_id,
            )
        )

    return issues


def _uses_kv_cache(input_memory_classes: dict[str, str]) -> bool:
    return any(memory_class == "KV_CACHE" for memory_class in input_memory_classes.values())


def _kv_layout_is_compatible(
    resolved_layout: str,
    kv_layout_rule: str | None,
    target_layout: str,
) -> bool:
    if resolved_layout == target_layout:
        return True
    return (
        resolved_layout == "BHSD"
        and target_layout == "LBHSD"
        and kv_layout_rule == "per-layer-slice-of-LBHSD"
    )


def _default_layout_for_op_kind(op_kind: str) -> str:
    if op_kind in {"KVStore", "KVLoad", "ROPE"}:
        return "BHSD"
    if op_kind in {"ShapeHelper", "ROPETable"}:
        return "METADATA"
    return "HSD"
