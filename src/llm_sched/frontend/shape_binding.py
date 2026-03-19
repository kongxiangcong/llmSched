"""Scenario-aware frontend shape binding helpers."""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.frontend.model_metadata import GemmaModelMetadata

_ATTENTION_KINDS = frozenset({"ROPE", "KVStore", "KVLoad", "KVSTORE", "KVLOAD", "SDPA", "SDPA_DECODE"})
_MAIN_PATH_KINDS = frozenset(
    {
        "Linear",
        "GEMM",
        "WDQ_GEMM",
        "RMSNorm",
        "RMSNORM",
        "RMSNORM_GEMM",
        "GeGLU",
        "GEGLU",
        "ResidualAdd",
        "ELEM_ADD",
    }
)


class FrontendShapeBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol_values: dict[str, int]
    kv_tensor_shape: list[int]
    mode: Literal["prefill", "decode"]
    batch_size: int = Field(gt=0)
    query_len: int = Field(gt=0)
    past_kv_len: int = Field(ge=0)
    present_kv_len: int = Field(gt=0)
    hidden_size: int = Field(gt=0)
    head_dim: int = Field(gt=0)
    num_attention_heads: int = Field(gt=0)
    num_key_value_heads: int = Field(gt=0)
    activation_layout: Literal["HSD"] = "HSD"
    attention_layout: Literal["BHSD"] = "BHSD"
    kv_cache_layout: Literal["LBHSD"] = "LBHSD"
    kv_layout_rule: str = "per-layer-slice-of-LBHSD"
    num_hidden_layers: int


def build_gemma3_shape_bindings(
    metadata: GemmaModelMetadata,
    scenario: ScenarioProfile,
) -> FrontendShapeBinding:
    present_kv_len = scenario.kv_len + scenario.seq_len
    return FrontendShapeBinding(
        symbol_values={
            "batch_size": scenario.batch,
            "sequence_length": scenario.seq_len,
            "past_sequence_length": scenario.kv_len,
            "total_sequence_length": present_kv_len,
        },
        kv_tensor_shape=[
            scenario.batch,
            metadata.num_key_value_heads,
            scenario.kv_len,
            metadata.head_dim,
        ],
        mode=scenario.mode,
        batch_size=scenario.batch,
        query_len=scenario.seq_len,
        past_kv_len=scenario.kv_len,
        present_kv_len=present_kv_len,
        hidden_size=metadata.hidden_size,
        head_dim=metadata.head_dim,
        num_attention_heads=metadata.num_attention_heads,
        num_key_value_heads=metadata.num_key_value_heads,
        num_hidden_layers=metadata.num_hidden_layers,
    )


def resolve_bound_shape(
    shape_bindings: FrontendShapeBinding | None,
    kind: str,
    raw_shape: list[int],
    attrs: Mapping[str, object] | None = None,
) -> list[int]:
    resolved_shape = list(raw_shape)
    if shape_bindings is None or not any(dim < 0 for dim in resolved_shape):
        return resolved_shape

    attrs = attrs or {}
    if kind in _ATTENTION_KINDS:
        return _resolve_attention_shape(shape_bindings, kind, resolved_shape, attrs)
    if kind in _MAIN_PATH_KINDS:
        return _resolve_main_path_shape(shape_bindings, resolved_shape, attrs)
    return resolved_shape


def resolve_canonical_layout(
    shape_bindings: FrontendShapeBinding | None,
    kind: str,
    default_layout: str,
) -> str:
    if shape_bindings is None:
        return default_layout
    if kind in {"ROPE", "KVStore", "KVLoad", "KVSTORE", "KVLOAD"}:
        return shape_bindings.attention_layout
    if kind in {"SDPA", "SDPA_DECODE"}:
        return shape_bindings.activation_layout
    return default_layout


def resolve_attention_binding_payload(
    shape_bindings: FrontendShapeBinding | None,
    kind: str,
    attrs: Mapping[str, object] | None = None,
) -> dict[str, object] | None:
    if shape_bindings is None or kind not in _ATTENTION_KINDS:
        return None

    attrs = attrs or {}
    return {
        "mode": shape_bindings.mode,
        "query_len": shape_bindings.query_len,
        "kv_len": shape_bindings.present_kv_len,
        "head_dim": _coerce_positive_int(attrs.get("head_dim")) or shape_bindings.head_dim,
        "num_heads": _coerce_positive_int(attrs.get("num_heads")) or shape_bindings.num_attention_heads,
        "num_key_value_heads": shape_bindings.num_key_value_heads,
        "tensor_layout": shape_bindings.attention_layout,
        "kv_layout_rule": shape_bindings.kv_layout_rule,
    }


def can_resolve_dynamic_shape(
    shape_bindings: FrontendShapeBinding | None,
    kind: str,
    raw_shape: list[int],
    attrs: Mapping[str, object] | None = None,
) -> bool:
    return all(dim >= 0 for dim in resolve_bound_shape(shape_bindings, kind, raw_shape, attrs))


def _resolve_attention_shape(
    shape_bindings: FrontendShapeBinding,
    kind: str,
    raw_shape: list[int],
    attrs: Mapping[str, object],
) -> list[int]:
    resolved = list(raw_shape)
    if resolved:
        resolved[0] = _coalesce_positive(resolved[0], shape_bindings.batch_size)

    if kind in {"SDPA", "SDPA_DECODE"}:
        if len(resolved) > 1:
            resolved[1] = _coalesce_positive(resolved[1], shape_bindings.query_len)
        if len(resolved) > 2:
            resolved[2] = _coalesce_positive(
                resolved[2],
                (_coerce_positive_int(attrs.get("num_heads")) or shape_bindings.num_attention_heads)
                * (_coerce_positive_int(attrs.get("head_dim")) or shape_bindings.head_dim),
            )
        return resolved

    if len(resolved) > 1:
        resolved[1] = _coalesce_positive(
            resolved[1],
            _resolve_head_axis(shape_bindings, kind, attrs),
        )
    if len(resolved) > 2:
        resolved[2] = _coalesce_positive(
            resolved[2],
            shape_bindings.query_len if kind == "ROPE" else shape_bindings.present_kv_len,
        )
    if len(resolved) > 3:
        resolved[3] = _coalesce_positive(
            resolved[3],
            _coerce_positive_int(attrs.get("head_dim")) or shape_bindings.head_dim,
        )
    return resolved


def _resolve_main_path_shape(
    shape_bindings: FrontendShapeBinding,
    raw_shape: list[int],
    attrs: Mapping[str, object],
) -> list[int]:
    resolved = list(raw_shape)
    if resolved:
        resolved[0] = _coalesce_positive(resolved[0], shape_bindings.batch_size)
    if len(resolved) == 3:
        resolved[1] = _coalesce_positive(resolved[1], shape_bindings.query_len)
        return resolved
    if len(resolved) == 4:
        resolved[1] = _coalesce_positive(
            resolved[1],
            _resolve_head_axis(shape_bindings, "ROPE", attrs),
        )
        resolved[2] = _coalesce_positive(resolved[2], shape_bindings.query_len)
        resolved[3] = _coalesce_positive(
            resolved[3],
            _coerce_positive_int(attrs.get("head_dim")) or shape_bindings.head_dim,
        )
    return resolved


def _resolve_head_axis(
    shape_bindings: FrontendShapeBinding,
    kind: str,
    attrs: Mapping[str, object],
) -> int:
    if kind == "KVStore":
        return shape_bindings.num_key_value_heads
    if kind == "KVSTORE":
        return shape_bindings.num_key_value_heads
    if kind in {"KVLoad", "KVLOAD"} and str(attrs.get("tensor_kind", "")) == "cache":
        return shape_bindings.num_key_value_heads
    return _coerce_positive_int(attrs.get("num_heads")) or shape_bindings.num_attention_heads


def _coerce_positive_int(value: object) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _coalesce_positive(current: int, fallback: int) -> int:
    return current if current >= 0 else fallback
