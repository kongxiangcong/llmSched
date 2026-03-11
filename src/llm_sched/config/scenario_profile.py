"""Scenario profile schema for workload evaluation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LayerScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["all", "single", "range"]
    start_layer: int | None = Field(default=None, ge=0)
    end_layer: int | None = Field(default=None, ge=0)
    layer_id: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_scope_shape(self) -> "LayerScope":
        if self.kind == "all":
            return self
        if self.kind == "single" and self.layer_id is None:
            raise ValueError("single layer scopes must set layer_id")
        if self.kind == "range":
            if self.start_layer is None or self.end_layer is None:
                raise ValueError("range layer scopes must set start_layer and end_layer")
            if self.start_layer > self.end_layer:
                raise ValueError("range layer scopes must satisfy start_layer <= end_layer")
        return self


class ReportingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    include_layer_breakdown: bool = True
    include_bandwidth: bool = True


class ScenarioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    version: str
    mode: Literal["prefill", "decode"]
    batch: int = Field(gt=0)
    seq_len: int = Field(gt=0)
    kv_len: int = Field(ge=0)
    layer_scope: LayerScope
    reporting: ReportingConfig

    @model_validator(mode="after")
    def validate_mode_constraints(self) -> "ScenarioProfile":
        if self.mode == "decode" and self.seq_len != 1:
            raise ValueError("decode scenarios must use seq_len=1")
        if self.mode == "prefill" and self.kv_len != 0:
            raise ValueError("prefill scenarios must use kv_len=0")
        return self
