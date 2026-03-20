"""Bind raw NIG nodes into a stable bound-NIG contract."""

from collections.abc import Mapping

from llm_sched.frontend.shape_binding import (
    FrontendShapeBinding,
    resolve_attention_binding_payload,
    resolve_bound_shape,
    resolve_canonical_layout,
)
from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGIR, NIGNode, TensorMemoryClass


_QUANTIZED_WEIGHT_DTYPES = {"int4", "uint4", "nf4"}
_DEFAULT_K_TILE_SIZE = 128


def bind_nig_ir(
    nig_ir: NIGIR,
    shape_bindings: FrontendShapeBinding | None = None,
) -> NIGIR:
    bound_nodes = []

    for node in nig_ir.nodes:
        attention_payload = resolve_attention_binding_payload(shape_bindings, node.macro_op, node.attrs)
        bound_nodes.append(
            node.model_copy(
                update={
                    "binding": NIGBinding(
                        resolved_shape=resolve_bound_shape(shape_bindings, node.macro_op, node.shape, node.attrs),
                        canonical_layout=resolve_canonical_layout(shape_bindings, node.macro_op, node.layout),
                        memory_class=resolve_primary_memory_class(
                            node.macro_op,
                            node.inputs,
                            node.outputs,
                            attrs=node.attrs,
                            fallback_memory_class=node.memory_class,
                        ),
                        input_memory_classes=resolve_input_memory_classes(
                            node.macro_op,
                            node.inputs,
                            attrs=node.attrs,
                            fallback_memory_class=node.memory_class,
                        ),
                        output_memory_classes=resolve_output_memory_classes(
                            node.macro_op,
                            node.outputs,
                            attrs=node.attrs,
                            fallback_memory_class=node.memory_class,
                        ),
                        quant=_bind_quant_contract(node),
                        attention=(
                            AttentionBinding.model_validate(attention_payload)
                            if attention_payload is not None
                            else None
                        ),
                    )
                },
                deep=True,
            )
        )

    return nig_ir.model_copy(
        update={
            "binding_state": "bound",
            "nodes": bound_nodes,
        },
        deep=True,
    )


def _bind_quant_contract(node: NIGNode):
    quant_mode = _resolve_quant_mode(node)
    k_tile_size = _resolve_k_tile_size(node)
    scale_present, zero_point_present = _resolve_quant_param_presence(node, quant_mode)
    return node.quant.model_copy(
        update={
            "quant_mode": quant_mode,
            "scale_present": scale_present,
            "zero_point_present": zero_point_present,
            "k_tile_size": k_tile_size,
            "k_tile_aligned": _is_group_size_k_tile_aligned(node.quant.group_size, k_tile_size),
        },
        deep=True,
    )


def _resolve_quant_mode(node: NIGNode) -> str:
    explicit_mode = str(node.attrs.get("quant_mode", "")).strip()
    if explicit_mode:
        return explicit_mode
    if node.quant.weight_dtype in _QUANTIZED_WEIGHT_DTYPES or node.macro_op == "WDQ_GEMM":
        return "per-group"
    return "none"


def _resolve_quant_param_presence(node: NIGNode, quant_mode: str) -> tuple[bool, bool]:
    if quant_mode == "none":
        return (False, False)

    quant_param_inputs = max(len(node.inputs) - 2, 0)
    scale_present = bool(node.attrs.get("scale_present", quant_param_inputs >= 1))
    zero_point_present = bool(node.attrs.get("zero_point_present", quant_param_inputs >= 2))
    return (scale_present, zero_point_present)


def _resolve_k_tile_size(node: NIGNode) -> int:
    return int(node.attrs.get("k_tile_size", _DEFAULT_K_TILE_SIZE))


def _is_group_size_k_tile_aligned(group_size: int, k_tile_size: int) -> bool:
    if group_size <= 0:
        return False
    if group_size % 16 != 0:
        return False
    if group_size > k_tile_size:
        return False
    return k_tile_size % group_size == 0


def resolve_primary_memory_class(
    kind: str,
    inputs: list[str],
    outputs: list[str],
    attrs: Mapping[str, object] | None = None,
    fallback_memory_class: str | None = None,
) -> TensorMemoryClass:
    input_classes = resolve_input_memory_classes(
        kind,
        inputs,
        attrs=attrs,
        fallback_memory_class=fallback_memory_class,
    )
    output_classes = resolve_output_memory_classes(
        kind,
        outputs,
        attrs=attrs,
        fallback_memory_class=fallback_memory_class,
    )
    if output_classes:
        return next(iter(output_classes.values()))
    if input_classes:
        return next(iter(input_classes.values()))
    return _normalize_memory_class(fallback_memory_class or "activation")


def resolve_input_memory_classes(
    kind: str,
    inputs: list[str],
    attrs: Mapping[str, object] | None = None,
    fallback_memory_class: str | None = None,
) -> dict[str, TensorMemoryClass]:
    attrs = attrs or {}
    if kind in {"Linear", "GEMM", "WDQ_GEMM"}:
        return _classify_linear_inputs(kind, inputs)
    if kind == "RMSNorm":
        return _classify_rmsnorm_inputs(inputs)
    if kind == "RMSNORM_GEMM":
        return _classify_rmsnorm_gemm_inputs(inputs)
    if kind in {"SDPA", "SDPA_DECODE"}:
        return _classify_sdpa_inputs(inputs)
    if kind in {"GeGLU", "GEGLU", "ResidualAdd", "ELEM_ADD", "AttentionMaskPrep", "LAYOUT_FALLBACK"}:
        return {tensor_name: "ACTIVATION" for tensor_name in inputs}
    if kind in {"ROPE", "ROPE_TABLE", "ROPETable"}:
        return _classify_rope_inputs(kind, inputs)
    if kind in {"KVStore", "KVSTORE"}:
        return _classify_kvstore_inputs(inputs)
    if kind in {"KVLoad", "KVLOAD"}:
        return _classify_kvload_inputs(inputs)
    if kind in {"EmbeddingLookup", "EMBEDDING_LOOKUP"}:
        return _classify_embedding_inputs(inputs)
    if kind in {"ShapeHelper", "SHAPE_HELPER"}:
        return {tensor_name: "ACTIVATION" for tensor_name in inputs}
    return {tensor_name: _normalize_memory_class(fallback_memory_class or "activation") for tensor_name in inputs}


def resolve_output_memory_classes(
    kind: str,
    outputs: list[str],
    attrs: Mapping[str, object] | None = None,
    fallback_memory_class: str | None = None,
) -> dict[str, TensorMemoryClass]:
    if kind in {"KVStore", "KVSTORE"}:
        return {tensor_name: "KV_CACHE" for tensor_name in outputs}
    if kind in {"KVLoad", "KVLOAD"}:
        return {tensor_name: "ACTIVATION" for tensor_name in outputs}
    if kind in {"SDPA", "SDPA_DECODE"}:
        return _classify_sdpa_outputs(outputs)
    if kind in {"ROPE_TABLE", "ROPETable", "ShapeHelper", "SHAPE_HELPER"}:
        return {tensor_name: "METADATA" for tensor_name in outputs}
    if kind in {"EmbeddingLookup", "EMBEDDING_LOOKUP"}:
        return {tensor_name: "ACTIVATION" for tensor_name in outputs}
    return {tensor_name: resolve_primary_memory_class_from_kind(kind, fallback_memory_class) for tensor_name in outputs}


def resolve_primary_memory_class_from_kind(
    kind: str,
    fallback_memory_class: str | None = None,
) -> TensorMemoryClass:
    if kind in {"KVStore", "KVSTORE"}:
        return "KV_CACHE"
    if kind in {"KVLoad", "KVLOAD"}:
        return "ACTIVATION"
    if kind in {"ROPE_TABLE", "ROPETable", "ShapeHelper", "SHAPE_HELPER"}:
        return "METADATA"
    return _normalize_memory_class(fallback_memory_class or "activation")


def _classify_linear_inputs(kind: str, inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "ACTIVATION"
    if len(inputs) >= 2:
        classes[inputs[1]] = "WEIGHT"
    tail_class: TensorMemoryClass = "QUANT_PARAM" if kind in {"Linear", "WDQ_GEMM"} else "WEIGHT"
    for tensor_name in inputs[2:]:
        classes[tensor_name] = tail_class
    return classes


def _classify_rmsnorm_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "ACTIVATION"
    for tensor_name in inputs[1:]:
        classes[tensor_name] = "WEIGHT"
    return classes


def _classify_rmsnorm_gemm_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "ACTIVATION"
    if len(inputs) >= 2:
        classes[inputs[1]] = "WEIGHT"
    if len(inputs) >= 3:
        classes[inputs[2]] = "WEIGHT"
    for tensor_name in inputs[3:]:
        classes[tensor_name] = "QUANT_PARAM"
    return classes


def _classify_rope_inputs(kind: str, inputs: list[str]) -> dict[str, TensorMemoryClass]:
    if kind in {"ROPE_TABLE", "ROPETable"}:
        classes: dict[str, TensorMemoryClass] = {}
        if inputs:
            classes[inputs[0]] = "METADATA"
        for tensor_name in inputs[1:]:
            classes[tensor_name] = "WEIGHT"
        return classes

    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "ACTIVATION"
    for tensor_name in inputs[1:]:
        classes[tensor_name] = "METADATA"
    return classes


def _classify_kvstore_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "KV_CACHE"
    if len(inputs) >= 2:
        classes[inputs[1]] = "ACTIVATION"
    for tensor_name in inputs[2:]:
        classes[tensor_name] = "ACTIVATION"
    return classes


def _classify_kvload_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    return {tensor_name: "KV_CACHE" for tensor_name in inputs}


def _classify_embedding_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    if inputs:
        classes[inputs[0]] = "WEIGHT"
    if len(inputs) >= 2:
        classes[inputs[1]] = "METADATA"
    for tensor_name in inputs[2:]:
        classes[tensor_name] = "WEIGHT"
    return classes


def _classify_sdpa_inputs(inputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    for index, tensor_name in enumerate(inputs):
        lower_name = tensor_name.lower()
        if index < 4:
            classes[tensor_name] = "ACTIVATION"
            continue
        if "past_key_values" in lower_name or lower_name.startswith("past.") or lower_name.startswith("past_"):
            classes[tensor_name] = "KV_CACHE"
            continue
        if "cos_cache" in lower_name or "sin_cache" in lower_name:
            classes[tensor_name] = "METADATA"
            continue
        if "attn_mask" in lower_name or "mask.seq" in lower_name or lower_name.endswith(".seq"):
            classes[tensor_name] = "METADATA"
            continue
        classes[tensor_name] = "ACTIVATION"
    return classes


def _classify_sdpa_outputs(outputs: list[str]) -> dict[str, TensorMemoryClass]:
    classes: dict[str, TensorMemoryClass] = {}
    for tensor_name in outputs:
        lower_name = tensor_name.lower()
        if lower_name.startswith("present.") or "present." in lower_name:
            classes[tensor_name] = "KV_CACHE"
            continue
        classes[tensor_name] = "ACTIVATION"
    return classes


def _normalize_memory_class(value: str) -> TensorMemoryClass:
    normalized = value.strip().lower()
    mapping: dict[str, TensorMemoryClass] = {
        "activation": "ACTIVATION",
        "weight": "WEIGHT",
        "kv": "KV_CACHE",
        "kv_cache": "KV_CACHE",
        "metadata": "METADATA",
        "quant_param": "QUANT_PARAM",
        "quant": "QUANT_PARAM",
    }
    return mapping.get(normalized, "ACTIVATION")
