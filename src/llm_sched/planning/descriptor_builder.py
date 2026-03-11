"""SPEC-12 deterministic schedule-to-descriptor builder foundation."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.isa_coverage_report import ISACoverageIssue, ISACoverageReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact, PlannedAllocation
from llm_sched.ir.common import AuditRef
from llm_sched.ir.descriptor_ir import (
    AddressField,
    DescriptorIR,
    DescriptorPackingProfile,
    DescriptorRecord,
    TransferFields,
)
from llm_sched.ir.nig import NIGIR, NIGNode
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR


_TILE_ID_PATTERN = re.compile(r"\.m(?P<m>\d+)\.n(?P<n>\d+)\.k(?P<k>\d+)$")
_ADDRESS_PATTERN = re.compile(
    r"^(?P<address_space>[A-Z]+)(?::(?P<region_name>[^@]+))?(?:@(?P<offset_bytes>\d+))?$"
)
_STAGE_ROLE_ORDER = {
    "transfer": ("src", "dst"),
    "dma_in": ("input", "activation", "weight", "scale", "zp", "quant", "kv"),
    "store": ("output", "dst", "kv"),
    "prepare": ("input", "activation", "weight", "scale", "zp", "quant", "output", "dst", "src", "kv"),
    "compute": ("input", "activation", "weight", "scale", "zp", "quant", "output", "dst", "src", "kv"),
}


@dataclass(slots=True)
class _DescriptorEncodingError(Exception):
    code: str
    message: str


def build_descriptor_artifacts(
    schedule_ir: ScheduleIR,
    bound_nig_ir: NIGIR,
    memory_plan: MemoryPlanArtifact,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> tuple[DescriptorIR, ISACoverageReport]:
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("descriptor builder requires bound NIGIR input")
    if schedule_ir.graph_id != bound_nig_ir.graph_id:
        raise ValueError("schedule_ir graph_id must match bound_nig_ir graph_id")
    if memory_plan.graph_id != bound_nig_ir.graph_id:
        raise ValueError("memory_plan graph_id must match bound_nig_ir graph_id")
    if memory_plan.scenario_name != scenario.scenario_name:
        raise ValueError("memory_plan scenario_name must match scenario profile")

    capabilities = (
        hardware
        if isinstance(hardware, ArchitectureCapabilities)
        else ArchitectureCapabilities.from_target_profile(hardware)
    )
    nodes_by_id = {node.node_id: node for node in bound_nig_ir.nodes}
    allocations_by_node = _group_allocations_by_node(memory_plan.allocations)

    descriptors: list[DescriptorRecord] = []
    opcode_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    issues: list[ISACoverageIssue] = []

    for block in schedule_ir.blocks:
        opcode = _descriptor_opcode(block)
        supported, gap_code, gap_message = _descriptor_support(block, opcode, capabilities)
        if not supported:
            gap_counts[gap_code] += 1
            issues.append(
                ISACoverageIssue(
                    issue_id=f"isa-gap.{len(issues)}",
                    schedule_block_id=block.block_id,
                    core_id=block.core_id,
                    stage=block.stage or "unknown",
                    macro_op=block.macro_op,
                    requested_opcode=opcode,
                    code=gap_code,
                    message=gap_message,
                )
            )
            continue

        node = nodes_by_id.get(block.node_id or "")
        node_allocations = allocations_by_node.get(block.node_id or "", [])
        try:
            addr_fields = _addr_fields(block, node_allocations)
            address_fields = _address_fields(block, addr_fields, node_allocations, capabilities)
            dma_fields = _dma_fields(block, node_allocations)
            packing_profile = _packing_profile(block, opcode, address_fields, dma_fields, capabilities)
        except _DescriptorEncodingError as error:
            gap_counts[error.code] += 1
            issues.append(
                ISACoverageIssue(
                    issue_id=f"isa-gap.{len(issues)}",
                    schedule_block_id=block.block_id,
                    core_id=block.core_id,
                    stage=block.stage or "unknown",
                    macro_op=block.macro_op,
                    requested_opcode=opcode,
                    code=error.code,
                    message=error.message,
                )
            )
            continue
        descriptor = DescriptorRecord(
            descriptor_id=f"desc.{block.block_id}",
            schedule_block_id=block.block_id,
            opcode=opcode,
            core_id=int(block.core_id) if block.core_id != "both" else 0,
            encoding_bits=capabilities.descriptor_encoding.total_bits,
            ctrl_fields=_ctrl_fields(block, scenario, node),
            packing_profile=packing_profile,
            shape_pack=_shape_pack(block, node),
            addr_fields=addr_fields,
            address_fields=address_fields,
            dma_fields=dma_fields,
            transfer_fields=_transfer_fields(block),
            source_ref=list(node.source_ref if node is not None else []),
            audit_ref=_descriptor_audit_ref(block, node),
        )
        descriptors.append(descriptor)
        opcode_counts[opcode] += 1

    descriptor_ir = DescriptorIR(
        ir_version=schedule_ir.ir_version,
        graph_id=schedule_ir.graph_id,
        descriptors=descriptors,
    )
    coverage_report = ISACoverageReport(
        graph_id=schedule_ir.graph_id,
        schedule_kind=schedule_ir.core_mode,
        mapped_descriptor_count=len(descriptors),
        unmapped_block_count=len(issues),
        opcode_counts=dict(opcode_counts),
        gap_counts=dict(gap_counts),
        issues=issues,
    )
    return descriptor_ir, coverage_report


def _group_allocations_by_node(
    allocations: list[PlannedAllocation],
) -> dict[str, list[PlannedAllocation]]:
    grouped: dict[str, list[PlannedAllocation]] = {}
    for allocation in allocations:
        grouped.setdefault(allocation.node_id, []).append(allocation)
    return grouped


def _descriptor_opcode(block: ScheduleBlock) -> str:
    if block.stage == "dma_in":
        return "DMA_LOAD"
    if block.stage == "store":
        return "DMA_STORE"
    if block.stage == "prepare":
        return "VPU_PREPARE"
    if block.stage == "transfer":
        return "CORE_LINK_COPY" if block.transfer_kind == "core_link" else "DMA_TRANSFER"
    return block.macro_op or "UNKNOWN"


def _descriptor_support(
    block: ScheduleBlock,
    opcode: str,
    capabilities: ArchitectureCapabilities,
) -> tuple[bool, str, str]:
    if block.stage == "compute":
        if opcode in capabilities.opcodes:
            return True, "", ""
        return False, "compute_opcode_not_supported", f"target profile does not advertise compute opcode {opcode}"
    if block.stage in {"dma_in", "store"}:
        if capabilities.shared_dma.channels > 0:
            return True, "", ""
        return False, "dma_stage_not_available", f"shared DMA channels are not available for stage {block.stage}"
    if block.stage == "prepare":
        if capabilities.vpu.lanes > 0:
            return True, "", ""
        return False, "prepare_vpu_not_available", "VPU lanes are not available for prepare stage"
    if block.stage == "transfer":
        if block.transfer_kind == "core_link":
            if capabilities.core_link.enabled:
                return True, "", ""
            return False, "transfer_core_link_not_available", "core_link transfer requested on target without core_link"
        if capabilities.shared_dma.channels > 0:
            return True, "", ""
        return False, "transfer_dma_not_available", "DMA transfer requested on target without DMA channels"
    return False, "descriptor_stage_not_supported", f"unsupported schedule stage {block.stage}"


def _ctrl_fields(
    block: ScheduleBlock,
    scenario: ScenarioProfile,
    node: NIGNode | None,
) -> dict[str, object]:
    fields: dict[str, object] = {
        "stage": block.stage,
        "order_key": block.order_key,
        "issue_slot": block.issue_slot,
        "duration_slots": block.duration_slots,
        "scenario_mode": scenario.mode,
    }
    if block.macro_op is not None:
        fields["macro_op"] = block.macro_op
    if block.peer_core_id is not None:
        fields["peer_core_id"] = block.peer_core_id
    if (
        node is not None
        and node.binding is not None
        and node.binding.quant is not None
        and block.macro_op in {"WDQ_GEMM", "RMSNORM_GEMM"}
    ):
        fields["group_size"] = node.binding.quant.group_size
    return fields


def _shape_pack(block: ScheduleBlock, node: NIGNode | None) -> dict[str, int]:
    if block.tiling_candidate_id:
        match = _TILE_ID_PATTERN.search(block.tiling_candidate_id)
        if match is not None:
            return {axis: int(value) for axis, value in match.groupdict().items()}
    if node is None or node.binding is None:
        return {}
    resolved_shape = list(node.binding.resolved_shape)
    if not resolved_shape:
        return {
            "m": 1,
            "n": 1,
            "k": max(1, node.quant.k_tile_size),
        }
    return {
        "m": max(1, resolved_shape[0]),
        "n": max(1, resolved_shape[-1]),
        "k": max(1, node.quant.k_tile_size),
    }


def _packing_profile(
    block: ScheduleBlock,
    opcode: str,
    address_fields: list[AddressField],
    dma_fields: dict[str, int],
    capabilities: ArchitectureCapabilities,
) -> DescriptorPackingProfile:
    encoding = capabilities.descriptor_encoding
    stage = block.stage or "compute"
    required_ctrl_fields = ["stage", "order_key", "scenario_mode"]
    if block.macro_op is not None:
        required_ctrl_fields.append("macro_op")
    if block.peer_core_id is not None:
        required_ctrl_fields.append("peer_core_id")

    required_shape_axes = ["m", "n", "k"]
    required_addr_roles = [field.role for field in address_fields]
    required_dma_fields = [
        field_name for field_name in ["length", "channel", "priority"] if field_name in dma_fields
    ]
    field_widths = {
        "opcode": encoding.opcode_bits,
        "control": encoding.control_bits,
        "order_key": encoding.control_bits,
        "shape_m": encoding.shape_bits,
        "shape_n": encoding.shape_bits,
        "shape_k": encoding.shape_bits,
    }
    if opcode in {"WDQ_GEMM", "RMSNORM_GEMM"}:
        field_widths["group_size"] = encoding.group_size_bits
        required_ctrl_fields.append("group_size")
    for field in address_fields:
        field_widths[_field_width_key(field)] = field.encoded_width_bits
        if field.uses_addr_ext:
            field_widths[_field_width_hi_key(field)] = max(
                1,
                encoding.full_address_bits - field.encoded_width_bits,
            )
    if "length" in dma_fields:
        field_widths["dma_length"] = encoding.dma_length_bits
    if "channel" in dma_fields:
        field_widths["dma_channel"] = encoding.dma_channel_bits
    if "priority" in dma_fields:
        field_widths["dma_priority"] = encoding.dma_priority_bits
    if stage == "transfer":
        field_widths["transfer_kind"] = max(8, encoding.dma_channel_bits)
        field_widths["transfer_src_core_id"] = max(8, encoding.dma_channel_bits)
        field_widths["transfer_dst_core_id"] = max(8, encoding.dma_channel_bits)
        field_widths["transfer_bytes"] = encoding.dma_length_bits

    if stage == "prepare":
        return DescriptorPackingProfile(
            stage_family="prepare",
            opcode_family="vpu_prepare",
            layout_template="vpu_prepare_v1",
            field_groups=["ctrl", "shape", "addr"] if address_fields else ["ctrl", "shape"],
            field_layout=_field_layout(
                stage=stage,
                opcode=opcode,
                address_fields=address_fields,
                dma_fields=dma_fields,
            ),
            required_ctrl_fields=required_ctrl_fields,
            required_shape_axes=required_shape_axes,
            required_addr_roles=required_addr_roles,
            required_dma_fields=[],
            field_widths=field_widths,
        )
    if stage in {"dma_in", "store"}:
        opcode_family = "dma_load" if stage == "dma_in" else "dma_store"
        layout_template = "dma_load_v1" if stage == "dma_in" else "dma_store_v1"
        return DescriptorPackingProfile(
            stage_family="dma",
            opcode_family=opcode_family,
            layout_template=layout_template,
            field_groups=["ctrl", "shape", "addr", "dma"],
            field_layout=_field_layout(
                stage=stage,
                opcode=opcode,
                address_fields=address_fields,
                dma_fields=dma_fields,
            ),
            required_ctrl_fields=required_ctrl_fields,
            required_shape_axes=required_shape_axes,
            required_addr_roles=required_addr_roles,
            required_dma_fields=required_dma_fields,
            field_widths=field_widths,
        )
    if stage == "transfer":
        opcode_family = "core_link_transfer" if block.transfer_kind == "core_link" else "dma_transfer"
        layout_template = (
            "core_link_transfer_v1"
            if block.transfer_kind == "core_link"
            else "dma_transfer_v1"
        )
        return DescriptorPackingProfile(
            stage_family="transfer",
            opcode_family=opcode_family,
            layout_template=layout_template,
            field_groups=["ctrl", "shape", "addr", "dma", "transfer"],
            field_layout=_field_layout(
                stage=stage,
                opcode=opcode,
                address_fields=address_fields,
                dma_fields=dma_fields,
            ),
            required_ctrl_fields=required_ctrl_fields,
            required_shape_axes=required_shape_axes,
            required_addr_roles=required_addr_roles,
            required_dma_fields=required_dma_fields,
            field_widths=field_widths,
        )
    layout_template = "wdq_compute_v1" if opcode == "WDQ_GEMM" else "tensor_compute_v1"
    if opcode == "RMSNORM_GEMM":
        layout_template = "rmsnorm_gemm_compute_v1"
    return DescriptorPackingProfile(
        stage_family="compute",
        opcode_family=f"{opcode.lower()}_compute",
        layout_template=layout_template,
        field_groups=["ctrl", "shape", "addr"] if address_fields else ["ctrl", "shape"],
        field_layout=_field_layout(
            stage=stage,
            opcode=opcode,
            address_fields=address_fields,
            dma_fields=dma_fields,
        ),
        required_ctrl_fields=required_ctrl_fields,
        required_shape_axes=required_shape_axes,
        required_addr_roles=required_addr_roles,
        required_dma_fields=[],
        field_widths=field_widths,
    )


def _field_layout(
    *,
    stage: str,
    opcode: str,
    address_fields: list[AddressField],
    dma_fields: dict[str, int],
) -> list[str]:
    layout = ["opcode", "control", "order_key"]
    if opcode in {"WDQ_GEMM", "RMSNORM_GEMM"}:
        layout.append("group_size")
    layout.extend(["shape_m", "shape_n", "shape_k"])
    for field in address_fields:
        layout.append(_field_width_key(field))
        if field.uses_addr_ext:
            layout.append(_field_width_hi_key(field))
    if stage in {"dma_in", "store", "transfer"}:
        for field_name in ("dma_length", "dma_channel", "dma_priority"):
            if field_name.removeprefix("dma_") in dma_fields:
                layout.append(field_name)
    if stage == "transfer":
        layout.extend(
            [
                "transfer_kind",
                "transfer_src_core_id",
                "transfer_dst_core_id",
                "transfer_bytes",
            ]
        )
    return layout


def _addr_fields(block: ScheduleBlock, allocations: list[PlannedAllocation]) -> dict[str, str]:
    addr_fields: dict[str, str] = {}
    allowed_roles = _stage_allowed_roles(block.stage or "compute")
    for allocation in allocations:
        role = _allocation_role_key(allocation)
        if role is None:
            continue
        if role not in allowed_roles:
            continue
        addr_fields.setdefault(role, _allocation_address(allocation))
    for key, value in block.buffer_binding.items():
        if key in {"accum", "wdq_reserved"}:
            continue
        if key == "quant" and ("scale" in addr_fields or "zp" in addr_fields):
            continue
        if key not in allowed_roles:
            continue
        addr_fields.setdefault(key, _normalize_address_space(value))
    return addr_fields


def _address_fields(
    block: ScheduleBlock,
    addr_fields: dict[str, str],
    allocations: list[PlannedAllocation],
    capabilities: ArchitectureCapabilities,
) -> list[AddressField]:
    allocation_lookup = {
        role: allocation
        for allocation in allocations
        for role in [_allocation_role_key(allocation)]
        if role is not None
    }
    address_fields: list[AddressField] = []
    for role in _ordered_stage_roles(block.stage or "compute", addr_fields):
        symbol = addr_fields[role]
        parsed = _parse_address_symbol(symbol)
        descriptor_field, encoded_width_bits, uses_addr_ext = _address_encoding(
            role=role,
            stage=block.stage or "compute",
            address_space=parsed["address_space"],
            capabilities=capabilities,
        )
        region_name = parsed["region_name"]
        offset_bytes = int(parsed["offset_bytes"])
        allocation = allocation_lookup.get(role)
        if allocation is not None:
            region_name = allocation.region_name or region_name
            offset_bytes = allocation.offset_bytes
        field = AddressField(
            role=role,
            address_space=parsed["address_space"],
            region_name=region_name,
            offset_bytes=offset_bytes,
            storage_binding_id=allocation.storage_binding_id if allocation is not None else None,
            backing_store=allocation.backing_store if allocation is not None else None,
            symbol=symbol,
            descriptor_field=descriptor_field,
            encoded_width_bits=encoded_width_bits,
            uses_addr_ext=uses_addr_ext,
        )
        _validate_address_field_fit(field, capabilities)
        address_fields.append(field)
    return address_fields


def _ordered_stage_roles(stage: str, addr_fields: dict[str, str]) -> list[str]:
    order = _STAGE_ROLE_ORDER.get(stage, _STAGE_ROLE_ORDER["compute"])
    priority = {role: index for index, role in enumerate(order)}
    return sorted(addr_fields, key=lambda role: (priority.get(role, len(priority)), role))


def _dma_fields(block: ScheduleBlock, allocations: list[PlannedAllocation]) -> dict[str, int]:
    if block.stage not in {"dma_in", "store", "transfer"}:
        return {}
    length = (
        block.transfer_bytes
        if block.stage == "transfer"
        else _stage_dma_length(block.stage, allocations)
    )
    return {
        "channel": 0,
        "priority": 1,
        "length": length,
    }


def _transfer_fields(block: ScheduleBlock) -> TransferFields | None:
    if block.stage != "transfer" or block.peer_core_id is None or block.transfer_kind is None:
        return None
    return TransferFields(
        kind=block.transfer_kind,
        src_core_id=int(block.core_id) if block.core_id != "both" else 0,
        dst_core_id=block.peer_core_id,
        transfer_bytes=block.transfer_bytes,
    )


def _descriptor_audit_ref(block: ScheduleBlock, node: NIGNode | None) -> AuditRef:
    return AuditRef(
        graph_node_ids=list(block.audit_ref.graph_node_ids),
        nig_node_ids=list(block.audit_ref.nig_node_ids),
        schedule_block_ids=[block.block_id],
        source_ids=list(node.source_ref if node is not None else block.audit_ref.source_ids),
    )


def _normalize_address_space(binding: str) -> str:
    if ":" in binding:
        return binding
    return f"VMEM:{binding}"


def _allocation_address(allocation: PlannedAllocation) -> str:
    if allocation.region_name:
        return f"{allocation.address_space}:{allocation.region_name}@{allocation.offset_bytes}"
    return f"{allocation.address_space}@{allocation.offset_bytes}"


def _allocation_role_key(allocation: PlannedAllocation) -> str | None:
    if allocation.tensor_role == "quant_param":
        tensor_name = allocation.tensor_name.lower()
        if "scale" in tensor_name:
            return "scale"
        if "zp" in tensor_name or "zero" in tensor_name:
            return "zp"
        return "quant"
    if allocation.tensor_role == "kv_cache":
        return "kv"
    if allocation.tensor_role == "temp":
        return None
    return allocation.tensor_role


def _parse_address_symbol(symbol: str) -> dict[str, object]:
    match = _ADDRESS_PATTERN.match(symbol)
    if match is None:
        raise ValueError(f"unsupported descriptor address symbol: {symbol}")
    groups = match.groupdict()
    address_space = groups["address_space"]
    if address_space not in {"VMEM", "DDR"}:
        raise ValueError(f"unsupported descriptor address space: {address_space}")
    offset_bytes = int(groups["offset_bytes"] or 0)
    return {
        "address_space": address_space,
        "region_name": groups["region_name"],
        "offset_bytes": offset_bytes,
    }


def _address_encoding(
    *,
    role: str,
    stage: str,
    address_space: str,
    capabilities: ArchitectureCapabilities,
) -> tuple[str, int, bool]:
    encoding = capabilities.descriptor_encoding
    uses_addr_ext = False
    if stage == "transfer":
        descriptor_field = "SRC_ADDR" if role == "src" else "DST_ADDR"
        return descriptor_field, encoding.full_address_bits, False
    if role == "weight":
        return "WEIGHT_ADDR", encoding.full_address_bits, False
    if role in {"input", "activation"}:
        return "ACT_ADDR", encoding.full_address_bits, False
    if role == "scale":
        return "SCALE_ADDR", encoding.full_address_bits, False
    if role == "zp":
        uses_addr_ext = address_space == "DDR"
        return "ZP_ADDR", encoding.split_address_bits, uses_addr_ext
    if role in {"output", "dst"}:
        uses_addr_ext = address_space == "DDR"
        return "DST_ADDR", encoding.split_address_bits, uses_addr_ext
    if role == "src":
        return "SRC_ADDR", encoding.full_address_bits, False
    descriptor_field = f"{role.upper()}_ADDR"
    return descriptor_field, encoding.full_address_bits, False


def _validate_address_field_fit(
    field: AddressField,
    capabilities: ArchitectureCapabilities,
) -> None:
    encoding = capabilities.descriptor_encoding
    if field.encoded_width_bits > encoding.full_address_bits:
        raise _DescriptorEncodingError(
            code="descriptor_field_width_not_supported",
            message=f"descriptor field {field.descriptor_field} exceeds target full_address_bits",
        )
    if field.address_space == "DDR" and field.encoded_width_bits < encoding.full_address_bits and not field.uses_addr_ext:
        raise _DescriptorEncodingError(
            code="descriptor_addr_ext_required",
            message=f"descriptor field {field.descriptor_field} requires ADDR_EXT_HI for DDR addresses",
        )
    if field.address_space == "VMEM":
        absolute_offset = _vmem_region_base_bytes(field.region_name, capabilities) + field.offset_bytes
        if absolute_offset >= (1 << field.encoded_width_bits):
            raise _DescriptorEncodingError(
                code="descriptor_address_width_overflow",
                message=(
                    f"VMEM address {field.symbol} requires {absolute_offset.bit_length()} bits "
                    f"but field {field.descriptor_field} only provides {field.encoded_width_bits}"
                ),
            )


def _vmem_region_base_bytes(region_name: str | None, capabilities: ArchitectureCapabilities) -> int:
    if region_name is None:
        return 0
    offset_bytes = 0
    for name, size_kb in capabilities.vmem.regions.items():
        if name == region_name:
            return offset_bytes
        offset_bytes += int(size_kb) * 1024
    raise _DescriptorEncodingError(
        code="descriptor_unknown_vmem_region",
        message=f"unknown VMEM region {region_name} in descriptor address encoding",
    )


def _field_width_key(field: AddressField) -> str:
    key = field.descriptor_field.lower()
    if field.encoded_width_bits < 64:
        return f"{key}_low"
    return key


def _field_width_hi_key(field: AddressField) -> str:
    key = field.descriptor_field.lower()
    if key.endswith("_low"):
        key = key[: -len("_low")]
    return f"{key}_hi"


def _stage_allowed_roles(stage: str) -> set[str]:
    if stage == "transfer":
        return {"src", "dst"}
    if stage == "dma_in":
        return {"input", "activation", "weight", "scale", "zp", "quant", "kv"}
    if stage == "store":
        return {"output", "dst", "kv"}
    return {"input", "activation", "weight", "scale", "zp", "quant", "output", "dst", "src", "kv"}


def _stage_dma_length(stage: str | None, allocations: list[PlannedAllocation]) -> int:
    if stage == "dma_in":
        roles = {"input", "weight", "quant_param", "metadata", "kv_cache"}
    elif stage == "store":
        roles = {"output", "kv_cache", "metadata"}
    else:
        return 0
    length = sum(allocation.size_bytes for allocation in allocations if allocation.tensor_role in roles)
    if length > 0:
        return length
    return sum(allocation.size_bytes for allocation in allocations if allocation.tensor_role != "temp")
