"""Descriptor IR schema."""

from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from llm_sched.ir.common import AuditRef


AddressSpace = Literal["VMEM", "DDR"]
DescriptorFieldGroup = Literal["ctrl", "shape", "addr", "dma", "transfer"]


class TransferFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["dma", "core_link"]
    src_core_id: int = Field(ge=0)
    dst_core_id: int = Field(ge=0)
    transfer_bytes: int = Field(gt=0)


class AddressField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1)
    address_space: AddressSpace
    region_name: str | None = None
    offset_bytes: int = Field(default=0, ge=0)
    symbol: str = Field(min_length=1)
    descriptor_field: str = Field(min_length=1)
    encoded_width_bits: int = Field(gt=0)
    uses_addr_ext: bool = False


class DescriptorPackingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_family: Literal["compute", "prepare", "dma", "transfer"]
    opcode_family: str = Field(min_length=1)
    layout_template: str = Field(min_length=1)
    field_groups: list[DescriptorFieldGroup] = Field(default_factory=list)
    field_layout: list[str] = Field(default_factory=list)
    required_ctrl_fields: list[str] = Field(default_factory=list)
    required_shape_axes: list[str] = Field(default_factory=list)
    required_addr_roles: list[str] = Field(default_factory=list)
    required_dma_fields: list[str] = Field(default_factory=list)
    field_widths: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_field_layout(self) -> "DescriptorPackingProfile":
        if not self.field_layout:
            _validate_opcode_family_layout_template(self)
            return self
        if len(self.field_layout) != len(set(self.field_layout)):
            raise ValueError("descriptor packing_profile.field_layout must not contain duplicates")
        layout_fields = set(self.field_layout)
        width_fields = set(self.field_widths)
        if not layout_fields.issubset(width_fields):
            raise ValueError("descriptor packing_profile.field_layout must only reference field_widths")
        _validate_layout_template_semantics(self)
        _validate_opcode_family_layout_template(self)
        if layout_fields != width_fields:
            raise ValueError("descriptor packing_profile.field_layout must cover all field_widths")
        return self


class DescriptorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptor_id: str
    schedule_block_id: str
    opcode: str
    core_id: int
    encoding_bits: int = Field(default=512, gt=0)
    ctrl_fields: dict[str, Any] = Field(default_factory=dict)
    packing_profile: DescriptorPackingProfile
    shape_pack: dict[str, int] = Field(default_factory=dict)
    addr_fields: dict[str, str] = Field(default_factory=dict)
    address_fields: list[AddressField] = Field(default_factory=list)
    dma_fields: dict[str, int] = Field(default_factory=dict)
    transfer_fields: TransferFields | None = None
    source_ref: list[str] = Field(default_factory=list)
    audit_ref: AuditRef = Field(default_factory=AuditRef)

    @model_validator(mode="after")
    def validate_stage_specific_fields(self) -> "DescriptorRecord":
        stage = self.ctrl_fields.get("stage")
        if not isinstance(stage, str) or not stage:
            raise ValueError("descriptor ctrl_fields must include stage")
        expected_stage_family = _stage_family(stage)
        if self.packing_profile.stage_family != expected_stage_family:
            raise ValueError("descriptor packing_profile.stage_family must match ctrl_fields.stage")
        if "ctrl" not in set(self.packing_profile.field_groups):
            raise ValueError("descriptor packing_profile.field_groups must include ctrl")
        if not self.packing_profile.field_widths:
            raise ValueError("descriptor packing_profile.field_widths must not be empty")
        if sum(self.packing_profile.field_widths.values()) > self.encoding_bits:
            raise ValueError("descriptor packing_profile.field_widths exceed descriptor encoding_bits")
        for field_name in self.packing_profile.required_ctrl_fields:
            if field_name not in self.ctrl_fields:
                raise ValueError(f"descriptor ctrl_fields must include {field_name}")
        if stage in {"compute", "prepare"} and not self.shape_pack:
            raise ValueError(f"{stage} descriptors must include non-empty shape_pack")
        for axis in self.packing_profile.required_shape_axes:
            if axis not in self.shape_pack:
                raise ValueError(f"descriptor shape_pack must include required axis {axis}")
        if self.packing_profile.required_shape_axes and "shape" not in set(self.packing_profile.field_groups):
            raise ValueError("descriptor packing_profile.field_groups must include shape")
        if self.addr_fields:
            if not self.address_fields:
                raise ValueError("descriptor address_fields must cover symbolic addr_fields")
            if "addr" not in set(self.packing_profile.field_groups):
                raise ValueError("descriptor packing_profile.field_groups must include addr")
            symbolic_roles = set(self.addr_fields)
            structured_roles = {field.role for field in self.address_fields}
            if symbolic_roles != structured_roles:
                raise ValueError("descriptor address_fields roles must match addr_fields roles")
            for field in self.address_fields:
                if self.addr_fields.get(field.role) != field.symbol:
                    raise ValueError("descriptor address_fields symbol must match addr_fields entry")
                if field.encoded_width_bits > max(self.encoding_bits, 1):
                    raise ValueError("descriptor address field width must fit descriptor encoding_bits")
        if stage in {"dma_in", "store", "transfer"}:
            if not self.addr_fields:
                raise ValueError("DMA descriptors must include non-empty addr_fields")
            if int(self.dma_fields.get("length", 0)) <= 0:
                raise ValueError("DMA descriptors must include positive dma_fields.length")
            if "channel" not in self.dma_fields or "priority" not in self.dma_fields:
                raise ValueError("DMA descriptors must include channel and priority")
            if "dma" not in set(self.packing_profile.field_groups):
                raise ValueError("descriptor packing_profile.field_groups must include dma")
        for role in self.packing_profile.required_addr_roles:
            if role not in self.addr_fields:
                raise ValueError(f"descriptor addr_fields must include required role {role}")
        for field_name in self.packing_profile.required_dma_fields:
            if field_name not in self.dma_fields:
                raise ValueError(f"descriptor dma_fields must include required field {field_name}")
        if stage == "transfer" and self.transfer_fields is None:
            raise ValueError("transfer descriptors must include transfer_fields")
        if stage == "transfer" and "transfer" not in set(self.packing_profile.field_groups):
            raise ValueError("descriptor packing_profile.field_groups must include transfer")
        if stage != "transfer" and self.transfer_fields is not None:
            raise ValueError("non-transfer descriptors must not include transfer_fields")
        return self


class DescriptorIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ir_version: str
    graph_id: str
    descriptors: list[DescriptorRecord]

    @model_validator(mode="after")
    def validate_unique_descriptor_ids(self) -> "DescriptorIR":
        descriptor_ids = [descriptor.descriptor_id for descriptor in self.descriptors]
        if len(descriptor_ids) != len(set(descriptor_ids)):
            raise ValueError("descriptor ids must be unique")
        schedule_block_ids = [descriptor.schedule_block_id for descriptor in self.descriptors]
        if len(schedule_block_ids) != len(set(schedule_block_ids)):
            raise ValueError("schedule block ids must be unique across descriptors")
        return self


def _stage_family(stage: str) -> Literal["compute", "prepare", "dma", "transfer"]:
    if stage in {"dma_in", "store"}:
        return "dma"
    if stage == "transfer":
        return "transfer"
    if stage == "prepare":
        return "prepare"
    return "compute"


def _validate_layout_template_semantics(profile: DescriptorPackingProfile) -> None:
    layout = profile.field_layout
    if layout[:3] != ["opcode", "control", "order_key"]:
        raise ValueError(
            f"{profile.layout_template} must start with opcode/control/order_key in field_layout"
        )

    expected_index = 3
    if profile.layout_template in {"wdq_compute_v1", "rmsnorm_gemm_compute_v1"}:
        if len(layout) <= expected_index or layout[expected_index] != "group_size":
            raise ValueError(
                f"{profile.layout_template} must place group_size immediately after order_key"
            )
        expected_index += 1

    if "shape" in profile.field_groups:
        expected_shape = ["shape_m", "shape_n", "shape_k"]
        if layout[expected_index : expected_index + 3] != expected_shape:
            raise ValueError(
                f"{profile.layout_template} must place shape_m/shape_n/shape_k before address fields"
            )

    if profile.layout_template in {"dma_load_v1", "dma_store_v1"}:
        if layout[-3:] != ["dma_length", "dma_channel", "dma_priority"]:
            raise ValueError(
                f"{profile.layout_template} must end with dma_length/dma_channel/dma_priority"
            )

    if profile.layout_template in {"core_link_transfer_v1", "dma_transfer_v1"}:
        if layout[-7:-4] != ["dma_length", "dma_channel", "dma_priority"]:
            raise ValueError(
                f"{profile.layout_template} must place DMA fields immediately before transfer fields"
            )
        if layout[-4:] != [
            "transfer_kind",
            "transfer_src_core_id",
            "transfer_dst_core_id",
            "transfer_bytes",
        ]:
            raise ValueError(
                f"{profile.layout_template} must end with transfer_kind/transfer_src_core_id/transfer_dst_core_id/transfer_bytes"
            )

    if profile.layout_template == "vpu_prepare_v1":
        illegal = [field for field in layout if field.startswith("dma_") or field.startswith("transfer_")]
        if illegal:
            raise ValueError("vpu_prepare_v1 must not carry dma_ or transfer_ fields")


def _validate_opcode_family_layout_template(profile: DescriptorPackingProfile) -> None:
    expected_layout_template = {
        "dma_load": "dma_load_v1",
        "dma_store": "dma_store_v1",
        "dma_transfer": "dma_transfer_v1",
        "core_link_transfer": "core_link_transfer_v1",
        "vpu_prepare": "vpu_prepare_v1",
        "wdq_gemm_compute": "wdq_compute_v1",
        "rmsnorm_gemm_compute": "rmsnorm_gemm_compute_v1",
    }.get(profile.opcode_family)
    if expected_layout_template is None:
        return
    if profile.layout_template != expected_layout_template:
        raise ValueError("layout_template must match opcode_family")
