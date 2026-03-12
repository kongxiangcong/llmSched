"""Descriptor-driven performance estimator foundation for SPEC-13."""

from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil
import re

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfBottleneckIssue, PerfPhaseSummary, PerfSummaryReport
from llm_sched.ir.analysis_ir import AnalysisIR, AnalysisRecord
from llm_sched.ir.common import AuditRef
from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorRecord
from llm_sched.ir.schedule_ir import ScheduleIR

_LAYER_PATTERNS = (
    re.compile(r"layers\.(\d+)"),
    re.compile(r"layers_(\d+)"),
)
_PERF_PHASE_ORDER = ("projection", "kv_io", "attention", "sync", "other")
_PROJECTION_MACROS = frozenset({"GEMM", "WDQ_GEMM", "RMSNORM_GEMM"})
_KV_IO_MACROS = frozenset({"KVLOAD", "KVSTORE"})
_ATTENTION_MACROS = frozenset({"SDPA_DECODE", "SDPA", "ROPE", "ATTENTION_MASK_PREP"})


def estimate_descriptor_analysis(
    descriptor_ir: DescriptorIR,
    coverage_report: ISACoverageReport,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> AnalysisIR:
    capabilities = _resolve_capabilities(hardware)
    records: list[AnalysisRecord] = []

    for descriptor in descriptor_ir.descriptors:
        metrics, tags = _estimate_descriptor_record(descriptor, capabilities, scenario)
        records.append(
            AnalysisRecord(
                record_id=_analysis_record_id(descriptor.schedule_block_id),
                subject_id=descriptor.schedule_block_id,
                metrics=metrics,
                tags=tags,
                audit_ref=descriptor.audit_ref.model_copy(
                    update={
                        "descriptor_ids": descriptor.audit_ref.descriptor_ids or [descriptor.descriptor_id],
                        "schedule_block_ids": descriptor.audit_ref.schedule_block_ids
                        or [descriptor.schedule_block_id],
                    },
                    deep=True,
                ),
            )
        )

    for issue in coverage_report.issues:
        records.append(
            AnalysisRecord(
                record_id=_analysis_record_id(issue.schedule_block_id),
                subject_id=issue.schedule_block_id,
                metrics=_zero_metrics(),
                tags=["descriptor-analysis", "isa-gap-bound"],
                audit_ref=AuditRef(schedule_block_ids=[issue.schedule_block_id]),
            )
        )

    return AnalysisIR(
        ir_version=descriptor_ir.ir_version,
        graph_id=descriptor_ir.graph_id,
        records=records,
    )


def build_perf_summary_report(
    run_id: str,
    descriptor_ir: DescriptorIR,
    analysis_ir: AnalysisIR,
    coverage_report: ISACoverageReport,
    scenario: ScenarioProfile | None = None,
    schedule_ir: ScheduleIR | None = None,
    memory_plan: MemoryPlanArtifact | None = None,
) -> PerfSummaryReport:
    descriptor_by_subject = {descriptor.schedule_block_id: descriptor for descriptor in descriptor_ir.descriptors}
    node_by_subject = (
        {block.block_id: block.node_id for block in schedule_ir.blocks}
        if schedule_ir is not None
        else {}
    )
    layer_by_subject = (
        {
            block.block_id: layer_key
            for block in schedule_ir.blocks
            if (layer_key := _infer_layer_key(block.audit_ref)) is not None
        }
        if schedule_ir is not None
        else {}
    )
    per_macro_cycles: Counter[str] = Counter()
    per_macro_bytes: Counter[str] = Counter()
    phase_cycles: Counter[str] = Counter()
    phase_bytes: Counter[str] = Counter()
    per_node_cycles: Counter[str] = Counter()
    per_node_bytes: Counter[str] = Counter()
    per_layer_cycles: Counter[str] = Counter()
    per_layer_bytes: Counter[str] = Counter()
    bottleneck_counts: Counter[str] = Counter()
    issues: list[PerfBottleneckIssue] = []
    data_movement_read_bytes_by_address_space: defaultdict[str, float] = defaultdict(float)
    data_movement_write_bytes_by_address_space: defaultdict[str, float] = defaultdict(float)
    totals = {
        "estimated_cycles": 0.0,
        "total_bytes": 0.0,
        "read_bytes": 0.0,
        "write_bytes": 0.0,
        "sync_cycles": 0.0,
    }
    schedule_makespan_slots = 0
    per_core_makespan_slots: dict[str, int] = {}
    per_core_busy_slots: dict[str, int] = {}
    per_core_idle_slots: dict[str, int] = {}
    schedule_transfer_slots = 0
    schedule_stage_slot_totals: dict[str, int] = {}

    for record in analysis_ir.records:
        for bottleneck in ("compute-bound", "memory-bound", "sync-bound", "isa-gap-bound"):
            if bottleneck in record.tags:
                bottleneck_counts[bottleneck] += 1
                if bottleneck == "isa-gap-bound":
                    issues.append(
                        PerfBottleneckIssue(
                            subject_id=record.subject_id,
                            bottleneck=bottleneck,
                            message="descriptor mapping reported an ISA coverage gap",
                        )
                    )
        totals["estimated_cycles"] += record.metrics.get("estimated_cycles", 0.0)
        totals["total_bytes"] += record.metrics.get("total_bytes", 0.0)
        totals["read_bytes"] += record.metrics.get("read_bytes", 0.0)
        totals["write_bytes"] += record.metrics.get("write_bytes", 0.0)
        totals["sync_cycles"] += record.metrics.get("sync_cycles", 0.0)
        node_id = node_by_subject.get(record.subject_id)
        if node_id is not None:
            per_node_cycles[node_id] += record.metrics.get("estimated_cycles", 0.0)
            per_node_bytes[node_id] += record.metrics.get("total_bytes", 0.0)

        descriptor = descriptor_by_subject.get(record.subject_id)
        attributed_cycles, attributed_bytes = _phase_contribution_for_record(descriptor, record.metrics)
        for phase_name, estimated_cycles in attributed_cycles.items():
            phase_cycles[phase_name] += estimated_cycles
        for phase_name, total_bytes in attributed_bytes.items():
            phase_bytes[phase_name] += total_bytes

        layer_key = layer_by_subject.get(record.subject_id)
        if layer_key is None and descriptor is not None:
            layer_key = _infer_layer_key(descriptor.audit_ref)
            if layer_key is not None:
                layer_by_subject[record.subject_id] = layer_key
        if layer_key is not None:
            per_layer_cycles[layer_key] += record.metrics.get("estimated_cycles", 0.0)
            per_layer_bytes[layer_key] += record.metrics.get("total_bytes", 0.0)

        if descriptor is None:
            continue
        macro = str(descriptor.ctrl_fields.get("macro_op", descriptor.opcode))
        per_macro_cycles[macro] += record.metrics.get("estimated_cycles", 0.0)
        per_macro_bytes[macro] += record.metrics.get("total_bytes", 0.0)
        _accumulate_data_movement_breakdown(
            descriptor,
            record.metrics,
            data_movement_read_bytes_by_address_space,
            data_movement_write_bytes_by_address_space,
        )

    if schedule_ir is not None:
        (
            schedule_makespan_slots,
            per_core_makespan_slots,
            per_core_busy_slots,
            per_core_idle_slots,
            schedule_transfer_slots,
            schedule_stage_slot_totals,
        ) = _summarize_schedule_timing(schedule_ir)

    (
        vmem_region_peak_bytes,
        vmem_region_peak_bytes_by_memory_class,
        vmem_region_peak_bytes_by_backing_store,
        vmem_region_capacity_bytes,
        vmem_region_peak_utilization,
    ) = _summarize_vmem_regions(memory_plan)
    totals["critical_path_cycles"] = _critical_path_cycles(
        schedule_makespan_slots=schedule_makespan_slots,
        estimated_cycles=float(totals["estimated_cycles"]),
    )
    total_tokens = _total_tokens_for_scenario(scenario)

    return PerfSummaryReport(
        run_id=run_id,
        graph_id=analysis_ir.graph_id,
        schedule_kind=coverage_report.schedule_kind,
        schedule_makespan_slots=schedule_makespan_slots,
        per_core_makespan_slots=per_core_makespan_slots,
        per_core_busy_slots=per_core_busy_slots,
        per_core_idle_slots=per_core_idle_slots,
        schedule_transfer_slots=schedule_transfer_slots,
        schedule_stage_slot_totals=schedule_stage_slot_totals,
        data_movement_read_bytes_by_address_space=dict(sorted(data_movement_read_bytes_by_address_space.items())),
        data_movement_write_bytes_by_address_space=dict(
            sorted(data_movement_write_bytes_by_address_space.items())
        ),
        vmem_region_peak_bytes=vmem_region_peak_bytes,
        vmem_region_peak_bytes_by_memory_class=vmem_region_peak_bytes_by_memory_class,
        vmem_region_peak_bytes_by_backing_store=vmem_region_peak_bytes_by_backing_store,
        vmem_region_capacity_bytes=vmem_region_capacity_bytes,
        vmem_region_peak_utilization=vmem_region_peak_utilization,
        totals=totals,
        phase_attribution=_build_phase_attribution(
            phase_cycles,
            phase_bytes,
            total_tokens=total_tokens,
        ),
        per_macro_cycles=dict(per_macro_cycles),
        per_macro_bytes=dict(per_macro_bytes),
        per_node_cycles=dict(sorted(per_node_cycles.items())),
        per_node_bytes=dict(sorted(per_node_bytes.items())),
        per_layer_cycles=_sorted_layer_totals(per_layer_cycles),
        per_layer_bytes=_sorted_layer_totals(per_layer_bytes),
        bottleneck_counts=dict(bottleneck_counts),
        isa_gap_counts=dict(coverage_report.gap_counts),
        issues=issues,
    )


def _critical_path_cycles(*, schedule_makespan_slots: int, estimated_cycles: float) -> float:
    if schedule_makespan_slots > 0:
        return float(schedule_makespan_slots)
    return float(estimated_cycles)


def _accumulate_data_movement_breakdown(
    descriptor: DescriptorRecord,
    metrics: dict[str, float],
    read_totals: defaultdict[str, float],
    write_totals: defaultdict[str, float],
) -> None:
    stage = str(descriptor.ctrl_fields.get("stage", "compute"))
    read_bytes = float(metrics.get("read_bytes", 0.0))
    write_bytes = float(metrics.get("write_bytes", 0.0))
    read_spaces = _address_spaces_for_roles(descriptor, _read_roles_for_stage(stage))
    write_spaces = _address_spaces_for_roles(descriptor, _write_roles_for_stage(stage))

    _distribute_bytes(read_totals, read_spaces, read_bytes)
    _distribute_bytes(write_totals, write_spaces, write_bytes)

    if stage == "compute":
        inferred_ddr_weight_bytes = _infer_external_weight_bytes(descriptor)
        if inferred_ddr_weight_bytes > 0.0:
            read_totals["DDR"] += inferred_ddr_weight_bytes


def _summarize_vmem_regions(
    memory_plan: MemoryPlanArtifact | None,
) -> tuple[
    dict[str, int],
    dict[str, dict[str, int]],
    dict[str, dict[str, int]],
    dict[str, int],
    dict[str, float],
]:
    if memory_plan is None:
        return {}, {}, {}, {}, {}
    peak_bytes: dict[str, int] = {}
    peak_bytes_by_memory_class: dict[str, dict[str, int]] = {}
    peak_bytes_by_backing_store: dict[str, dict[str, int]] = {}
    capacity_bytes: dict[str, int] = {}
    peak_utilization: dict[str, float] = {}
    for region_name in sorted(memory_plan.region_summaries):
        summary = memory_plan.region_summaries[region_name]
        peak_bytes[region_name] = summary.peak_bytes
        peak_bytes_by_memory_class[region_name] = dict(sorted(summary.peak_bytes_by_memory_class.items()))
        peak_bytes_by_backing_store[region_name] = dict(sorted(summary.peak_bytes_by_backing_store.items()))
        capacity_bytes[region_name] = summary.capacity_bytes
        utilization = summary.peak_bytes / max(summary.capacity_bytes, 1)
        peak_utilization[region_name] = round(utilization, 4)
    return (
        peak_bytes,
        peak_bytes_by_memory_class,
        peak_bytes_by_backing_store,
        capacity_bytes,
        peak_utilization,
    )


def _phase_contribution_for_record(
    descriptor: DescriptorRecord | None,
    metrics: dict[str, float],
) -> tuple[dict[str, float], dict[str, float]]:
    estimated_cycles = float(metrics.get("estimated_cycles", 0.0))
    sync_cycles = min(float(metrics.get("sync_cycles", 0.0)), estimated_cycles)
    non_sync_cycles = max(0.0, estimated_cycles - sync_cycles)
    total_bytes = float(metrics.get("total_bytes", 0.0))

    cycles = {phase_name: 0.0 for phase_name in _PERF_PHASE_ORDER}
    bytes_by_phase = {phase_name: 0.0 for phase_name in _PERF_PHASE_ORDER}
    phase_name = _classify_record_phase(descriptor)
    cycles[phase_name] = non_sync_cycles
    bytes_by_phase[phase_name] = total_bytes
    cycles["sync"] = sync_cycles
    return cycles, bytes_by_phase


def _classify_record_phase(descriptor: DescriptorRecord | None) -> str:
    if descriptor is None:
        return "other"
    stage = str(descriptor.ctrl_fields.get("stage", "compute"))
    macro = str(descriptor.ctrl_fields.get("macro_op", descriptor.opcode))
    if stage == "transfer":
        return "other"
    if macro in _KV_IO_MACROS:
        return "kv_io"
    if macro in _ATTENTION_MACROS:
        return "attention"
    if macro in _PROJECTION_MACROS:
        return "projection"
    return "other"


def _build_phase_attribution(
    phase_cycles: Counter[str],
    phase_bytes: Counter[str],
    *,
    total_tokens: int,
) -> dict[str, PerfPhaseSummary]:
    return {
        phase_name: PerfPhaseSummary(
            estimated_cycles=float(phase_cycles.get(phase_name, 0.0)),
            total_bytes=float(phase_bytes.get(phase_name, 0.0)),
            cycles_per_token=(
                float(phase_cycles.get(phase_name, 0.0)) / float(total_tokens)
            ) if total_tokens > 0 else 0.0,
            bytes_per_token=(
                float(phase_bytes.get(phase_name, 0.0)) / float(total_tokens)
            ) if total_tokens > 0 else 0.0,
        )
        for phase_name in _PERF_PHASE_ORDER
    }


def _total_tokens_for_scenario(scenario: ScenarioProfile | None) -> int:
    if scenario is None:
        return 0
    return int(max(0, scenario.batch * scenario.seq_len))


def _address_spaces_for_roles(descriptor: DescriptorRecord, roles: set[str]) -> list[str]:
    spaces = [
        field.address_space
        for field in descriptor.address_fields
        if field.role in roles and field.address_space
    ]
    return sorted(set(spaces))


def _read_roles_for_stage(stage: str) -> set[str]:
    if stage == "transfer":
        return {"src"}
    if stage == "dma_in":
        return {"input", "activation", "weight", "scale", "zp", "quant", "kv", "src"}
    if stage == "store":
        return set()
    return set()


def _write_roles_for_stage(stage: str) -> set[str]:
    if stage == "transfer":
        return {"dst"}
    if stage == "store":
        return {"output", "dst", "kv"}
    return set()


def _distribute_bytes(
    totals: defaultdict[str, float],
    address_spaces: list[str],
    byte_count: float,
) -> None:
    if byte_count <= 0.0 or not address_spaces:
        return
    share = float(byte_count) / len(address_spaces)
    for address_space in address_spaces:
        totals[address_space] += share


def _infer_external_weight_bytes(descriptor: DescriptorRecord) -> float:
    macro = str(descriptor.ctrl_fields.get("macro_op", descriptor.opcode))
    k = max(1, descriptor.shape_pack.get("k", 1))
    n = max(1, descriptor.shape_pack.get("n", 1))
    if macro == "WDQ_GEMM":
        return float(k * n * 0.5)
    if macro in {"GEMM", "RMSNORM_GEMM"}:
        return float(k * n * 2.0)
    return 0.0


def _summarize_schedule_timing(
    schedule_ir: ScheduleIR,
) -> tuple[int, dict[str, int], dict[str, int], dict[str, int], int, dict[str, int]]:
    per_core_makespan: dict[str, int] = {}
    per_core_intervals: dict[str, list[tuple[int, int]]] = {}
    stage_slot_totals: Counter[str] = Counter()
    transfer_slots = 0

    for block in schedule_ir.blocks:
        block_start = max(0, block.issue_slot)
        block_end = block_start + max(0, block.duration_slots)
        core_key = str(block.core_id)
        per_core_makespan[core_key] = max(per_core_makespan.get(core_key, 0), block_end)
        per_core_intervals.setdefault(core_key, []).append((block_start, block_end))
        stage_slot_totals[block.stage] += max(0, block.duration_slots)
        if block.stage == "transfer":
            transfer_slots += max(0, block.duration_slots)

    makespan = max(per_core_makespan.values(), default=0)
    per_core_busy = {
        core_key: _merged_interval_length(intervals)
        for core_key, intervals in per_core_intervals.items()
    }
    per_core_idle = {
        core_key: max(0, makespan - per_core_busy.get(core_key, 0))
        for core_key in per_core_makespan
    }
    return (
        makespan,
        dict(sorted(per_core_makespan.items())),
        dict(sorted(per_core_busy.items())),
        dict(sorted(per_core_idle.items())),
        transfer_slots,
        dict(sorted(stage_slot_totals.items())),
    )


def _merged_interval_length(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    ordered = sorted(intervals)
    merged_start, merged_end = ordered[0]
    total = 0
    for start, end in ordered[1:]:
        if start <= merged_end:
            merged_end = max(merged_end, end)
            continue
        total += max(0, merged_end - merged_start)
        merged_start, merged_end = start, end
    total += max(0, merged_end - merged_start)
    return total


def _estimate_descriptor_record(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> tuple[dict[str, float], list[str]]:
    schedule_duration_floor = float(max(0, int(descriptor.ctrl_fields.get("duration_slots", 0))))
    stage = str(descriptor.ctrl_fields.get("stage", "compute"))
    if stage == "compute":
        return _estimate_compute_descriptor(descriptor, capabilities, schedule_duration_floor)
    if stage in {"dma_in", "store"}:
        return _estimate_dma_descriptor(descriptor, capabilities, stage, schedule_duration_floor)
    if stage == "transfer":
        return _estimate_transfer_descriptor(descriptor, capabilities, schedule_duration_floor)
    if stage == "prepare":
        return _estimate_prepare_descriptor(descriptor, capabilities, schedule_duration_floor)
    return _zero_metrics(), ["descriptor-analysis", "memory-bound"]


def _estimate_compute_descriptor(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    schedule_duration_floor: float,
) -> tuple[dict[str, float], list[str]]:
    m = max(1, descriptor.shape_pack.get("m", 1))
    n = max(1, descriptor.shape_pack.get("n", 1))
    k = max(1, descriptor.shape_pack.get("k", 1))
    activation_bytes = _dtype_size(capabilities.quantization.activation_dtype)
    weight_bytes = _dtype_size(capabilities.quantization.weight_dtype)

    read_bytes = float((m * k * activation_bytes) + (k * n * weight_bytes))
    write_bytes = float(m * n * activation_bytes)
    estimated_cycles = float(
        max(
            schedule_duration_floor,
            max(1, ceil((m * n * k) / max(capabilities.mxu.rows * capabilities.mxu.cols, 1))),
        )
    )
    return _metrics(read_bytes, write_bytes, estimated_cycles, sync_cycles=0.0), [
        "descriptor-analysis",
        "compute-bound",
    ]


def _estimate_dma_descriptor(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    stage: str,
    schedule_duration_floor: float,
) -> tuple[dict[str, float], list[str]]:
    byte_count = float(descriptor.dma_fields.get("length", _fallback_byte_count(descriptor, capabilities)))
    estimated_cycles = float(
        max(schedule_duration_floor, _bandwidth_cycles(byte_count, capabilities.shared_dma.effective_bandwidth_gbps))
    )
    if stage == "dma_in":
        read_bytes = byte_count
        write_bytes = 0.0
    else:
        read_bytes = 0.0
        write_bytes = byte_count
    return _metrics(read_bytes, write_bytes, estimated_cycles, sync_cycles=0.0), [
        "descriptor-analysis",
        "memory-bound",
    ]


def _estimate_transfer_descriptor(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    schedule_duration_floor: float,
) -> tuple[dict[str, float], list[str]]:
    transfer_bytes = float(
        descriptor.transfer_fields.transfer_bytes if descriptor.transfer_fields is not None else 0
    )
    bandwidth_gbps = (
        capabilities.core_link.bandwidth_gbps
        if descriptor.transfer_fields is not None and descriptor.transfer_fields.kind == "core_link"
        else capabilities.shared_dma.effective_bandwidth_gbps
    )
    sync_cycles = float(capabilities.sync.cross_core_transfer_cost_cycles)
    estimated_cycles = float(
        max(schedule_duration_floor, _bandwidth_cycles(transfer_bytes, bandwidth_gbps) + sync_cycles)
    )
    return _metrics(transfer_bytes, transfer_bytes, estimated_cycles, sync_cycles=sync_cycles), [
        "descriptor-analysis",
        "sync-bound",
    ]


def _estimate_prepare_descriptor(
    descriptor: DescriptorRecord,
    capabilities: ArchitectureCapabilities,
    schedule_duration_floor: float,
) -> tuple[dict[str, float], list[str]]:
    m = max(1, descriptor.shape_pack.get("m", 1))
    n = max(1, descriptor.shape_pack.get("n", 1))
    k = max(1, descriptor.shape_pack.get("k", 1))
    elements = m * n * k
    byte_count = float(elements * _dtype_size(capabilities.quantization.activation_dtype))
    estimated_cycles = float(max(schedule_duration_floor, max(1, ceil(elements / max(capabilities.vpu.lanes, 1)))))
    return _metrics(byte_count, byte_count, estimated_cycles, sync_cycles=0.0), [
        "descriptor-analysis",
        "compute-bound",
    ]


def _metrics(
    read_bytes: float,
    write_bytes: float,
    estimated_cycles: float,
    *,
    sync_cycles: float,
) -> dict[str, float]:
    total_bytes = float(read_bytes + write_bytes)
    return {
        "read_bytes": float(read_bytes),
        "write_bytes": float(write_bytes),
        "total_bytes": total_bytes,
        "estimated_cycles": float(estimated_cycles),
        "sync_cycles": float(sync_cycles),
        "bandwidth_pressure": total_bytes / max(float(estimated_cycles), 1.0),
    }


def _zero_metrics() -> dict[str, float]:
    return {
        "read_bytes": 0.0,
        "write_bytes": 0.0,
        "total_bytes": 0.0,
        "estimated_cycles": 0.0,
        "sync_cycles": 0.0,
        "bandwidth_pressure": 0.0,
    }


def _analysis_record_id(subject_id: str) -> str:
    return f"analysis.record.{subject_id.replace('.', '_')}"


def _bandwidth_cycles(byte_count: float, bandwidth_gbps: float) -> int:
    divisor = max(1.0, bandwidth_gbps * 64.0)
    return max(1, ceil(byte_count / divisor))


def _fallback_byte_count(descriptor: DescriptorRecord, capabilities: ArchitectureCapabilities) -> int:
    m = max(1, descriptor.shape_pack.get("m", 1))
    n = max(1, descriptor.shape_pack.get("n", 1))
    return int(m * n * _dtype_size(capabilities.quantization.activation_dtype))


def _resolve_capabilities(
    hardware: TargetProfile | ArchitectureCapabilities,
) -> ArchitectureCapabilities:
    if isinstance(hardware, ArchitectureCapabilities):
        return hardware
    return ArchitectureCapabilities.from_target_profile(hardware)


def _dtype_size(dtype: str) -> float:
    if dtype in {"bf16", "float16"}:
        return 2.0
    if dtype in {"float32", "int32"}:
        return 4.0
    if dtype == "int64":
        return 8.0
    if dtype == "int4":
        return 0.5
    return 1.0


def _infer_layer_key(audit_ref: AuditRef) -> str | None:
    for source_id in audit_ref.source_ids:
        for pattern in _LAYER_PATTERNS:
            match = pattern.search(source_id)
            if match is not None:
                return str(int(match.group(1)))
    return None


def _sorted_layer_totals(counter: Counter[str]) -> dict[str, float]:
    return dict(sorted(counter.items(), key=lambda item: (int(item[0]), item[0])))
