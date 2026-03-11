"""NIG schema."""

from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef

TensorMemoryClass = Literal["ACTIVATION", "WEIGHT", "KV_CACHE", "QUANT_PARAM", "METADATA"]


class QuantBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight_dtype: str
    activation_dtype: str
    group_size: int = Field(gt=0)
    quant_mode: Literal["none", "per-tensor", "per-channel", "per-group"] = "none"
    scale_present: bool = False
    zero_point_present: bool = False
    k_tile_size: int = Field(default=128, gt=0)
    k_tile_aligned: bool = True


class AttentionBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["prefill", "decode"]
    query_len: int = Field(gt=0)
    kv_len: int = Field(gt=0)
    head_dim: int = Field(gt=0)
    num_heads: int = Field(gt=0)
    num_key_value_heads: int = Field(gt=0)
    tensor_layout: str
    kv_layout_rule: str


class NIGBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resolved_shape: list[int] = Field(default_factory=list)
    canonical_layout: str
    memory_class: TensorMemoryClass
    input_memory_classes: dict[str, TensorMemoryClass] = Field(default_factory=dict)
    output_memory_classes: dict[str, TensorMemoryClass] = Field(default_factory=dict)
    quant: QuantBinding
    attention: AttentionBinding | None = None


class NIGNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    macro_op: str
    inputs: list[str]
    outputs: list[str]
    shape: list[int] = Field(default_factory=list)
    layout: str
    memory_class: str
    legal_opcodes: list[str]
    quant: QuantBinding
    binding: NIGBinding | None = None
    attrs: dict[str, Any] = Field(default_factory=dict)
    source_ref: list[str] = Field(default_factory=list)
    audit_ref: AuditRef = Field(default_factory=AuditRef)


class NIGIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    binding_state: Literal["raw", "bound"] = "raw"
    nodes: list[NIGNode]

    @model_validator(mode="after")
    def validate_nodes(self) -> "NIGIR":
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("nig node ids must be unique")
        if any(not node.legal_opcodes for node in self.nodes):
            raise ValueError("nig nodes must declare at least one legal opcode")
        if self.binding_state == "bound" and any(
            node.binding is None for node in self.nodes if _requires_bound_binding(node.macro_op)
        ):
            raise ValueError("bound nig compute nodes must declare binding payloads")
        return self


def _requires_bound_binding(macro_op: str) -> bool:
    return macro_op not in {
        "ATTENTION_MASK_PREP",
        "EMBEDDING_LOOKUP",
        "LAYOUT_FALLBACK",
        "ROPE_TABLE",
        "SHAPE_HELPER",
    }
