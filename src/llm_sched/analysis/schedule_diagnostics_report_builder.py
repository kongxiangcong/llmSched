"""Builder for the DIAG-05 schedule diagnostics report."""

from __future__ import annotations

from collections import defaultdict

from llm_sched.contracts.schedule_diagnostics_report import (
    CoreLaneOccupancy,
    IdleSpanEntry,
    ResourceContentionSummary,
    ScheduleDiagnosticBlock,
    ScheduleDiagnosticsReport,
    StallEventEntry,
)
from llm_sched.ir.descriptor_ir import DescriptorIR
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR


_GLOBAL_CONTENTION_RESOURCES = {"DMA", "Core Link"}


def build_schedule_diagnostics_report(
    *,
    run_id: str,
    scenario_name: str,
    schedule_ir: ScheduleIR,
    descriptor_ir: DescriptorIR,
) -> ScheduleDiagnosticsReport:
    descriptor_by_block_id = {
        descriptor.schedule_block_id: descriptor for descriptor in descriptor_ir.descriptors
    }
    core_ids = _schedule_core_ids(schedule_ir)
    block_end_by_id = {
        block.block_id: max(0, block.issue_slot) + max(0, block.duration_slots)
        for block in schedule_ir.blocks
    }

    blocks = [
        _build_block_entry(
            block,
            descriptor_by_block_id.get(block.block_id),
            block_end_by_id=block_end_by_id,
            core_ids=core_ids,
        )
        for block in sorted(schedule_ir.blocks, key=lambda item: item.order_key)
    ]
    makespan_slots = max((block.end_slot for block in blocks), default=0)
    core_lanes = _build_core_lanes(blocks, core_ids=core_ids, makespan_slots=makespan_slots)
    idle_spans, stall_events = _build_idle_and_stall_entries(
        schedule_ir.blocks,
        block_end_by_id=block_end_by_id,
        core_ids=core_ids,
    )
    critical_path_blocks = _build_critical_path_blocks(schedule_ir.blocks)
    resource_contention_summary = _build_resource_contention_summary(
        schedule_ir.blocks,
        core_ids=core_ids,
        makespan_slots=makespan_slots,
    )

    return ScheduleDiagnosticsReport(
        run_id=run_id,
        graph_id=schedule_ir.graph_id,
        scenario_name=scenario_name,
        blocks=blocks,
        core_lanes=core_lanes,
        idle_spans=idle_spans,
        stall_events=stall_events,
        critical_path_blocks=critical_path_blocks,
        resource_contention_summary=resource_contention_summary,
    )


def _build_block_entry(
    block: ScheduleBlock,
    descriptor,
    *,
    block_end_by_id: dict[str, int],
    core_ids: list[int],
) -> ScheduleDiagnosticBlock:
    start_slot = max(0, block.issue_slot)
    duration_slots = max(1, block.duration_slots)
    return ScheduleDiagnosticBlock(
        block_id=block.block_id,
        node_id=block.node_id,
        macro_op=block.macro_op or getattr(descriptor, "opcode", None),
        stage=block.stage or getattr(descriptor, "ctrl_fields", {}).get("stage"),
        core_ids=_block_core_ids(block, core_ids),
        issue_slot=start_slot,
        duration_slots=duration_slots,
        start_slot=start_slot,
        end_slot=start_slot + duration_slots,
        span_slots=duration_slots,
        depends_on=list(block.depends_on),
        stall_reason=_infer_block_stall_reason(block, block_end_by_id=block_end_by_id),
        wait_for_block_ids=_waiting_dependency_ids(block, block_end_by_id=block_end_by_id),
    )


def _build_core_lanes(
    blocks: list[ScheduleDiagnosticBlock],
    *,
    core_ids: list[int],
    makespan_slots: int,
) -> list[CoreLaneOccupancy]:
    lanes: list[CoreLaneOccupancy] = []
    for core_id in core_ids:
        core_blocks = [block for block in blocks if core_id in block.core_ids]
        occupied_slots = _merged_interval_length(
            [(block.start_slot, block.end_slot) for block in core_blocks]
        )
        utilization_ratio = (occupied_slots / makespan_slots) if makespan_slots > 0 else 0.0
        lanes.append(
            CoreLaneOccupancy(
                core_id=core_id,
                occupied_slots=occupied_slots,
                makespan_slots=makespan_slots,
                utilization_ratio=utilization_ratio,
                block_ids=[block.block_id for block in core_blocks],
            )
        )
    return lanes


def _build_idle_and_stall_entries(
    schedule_blocks: list[ScheduleBlock],
    *,
    block_end_by_id: dict[str, int],
    core_ids: list[int],
) -> tuple[list[IdleSpanEntry], list[StallEventEntry]]:
    idle_spans: list[IdleSpanEntry] = []
    stall_events: list[StallEventEntry] = []
    for core_id in core_ids:
        core_blocks = sorted(
            (block for block in schedule_blocks if core_id in _block_core_ids(block, core_ids)),
            key=lambda item: (item.issue_slot, item.order_key),
        )
        previous_end = 0
        previous_block_id: str | None = None
        for block in core_blocks:
            block_start = max(0, block.issue_slot)
            if block_start > previous_end:
                reason = _infer_gap_reason(block, previous_end=previous_end, block_end_by_id=block_end_by_id)
                if reason is not None:
                    idle_spans.append(
                        IdleSpanEntry(
                            core_id=core_id,
                            start_slot=previous_end,
                            end_slot=block_start,
                            span_slots=block_start - previous_end,
                            reason=reason,
                            preceding_block_id=previous_block_id,
                            following_block_id=block.block_id,
                        )
                    )
                    if reason != "idle":
                        stall_events.append(
                            StallEventEntry(
                                block_id=block.block_id,
                                core_id=core_id,
                                start_slot=previous_end,
                                end_slot=block_start,
                                span_slots=block_start - previous_end,
                                reason=reason,
                                wait_for_block_ids=_waiting_dependency_ids(
                                    block,
                                    block_end_by_id=block_end_by_id,
                                    previous_end=previous_end,
                                ),
                            )
                        )
            previous_end = max(previous_end, block_start + max(1, block.duration_slots))
            previous_block_id = block.block_id
    return idle_spans, stall_events


def _build_critical_path_blocks(schedule_blocks: list[ScheduleBlock]) -> list[str]:
    blocks_by_id = {block.block_id: block for block in schedule_blocks}
    best_duration_by_id: dict[str, int] = {}
    parent_by_id: dict[str, str | None] = {}

    for block in sorted(schedule_blocks, key=lambda item: item.order_key):
        duration = max(1, block.duration_slots)
        best_parent: str | None = None
        best_parent_duration = 0
        for dependency_id in block.depends_on:
            dependency_duration = best_duration_by_id.get(dependency_id, 0)
            if dependency_duration > best_parent_duration:
                best_parent_duration = dependency_duration
                best_parent = dependency_id
        best_duration_by_id[block.block_id] = best_parent_duration + duration
        parent_by_id[block.block_id] = best_parent

    if not best_duration_by_id:
        return []

    tail_block_id = max(
        best_duration_by_id,
        key=lambda block_id: (best_duration_by_id[block_id], blocks_by_id[block_id].order_key),
    )
    path: list[str] = []
    current_block_id: str | None = tail_block_id
    while current_block_id is not None:
        path.append(current_block_id)
        current_block_id = parent_by_id.get(current_block_id)
    path.reverse()
    return path


def _build_resource_contention_summary(
    schedule_blocks: list[ScheduleBlock],
    *,
    core_ids: list[int],
    makespan_slots: int,
) -> ResourceContentionSummary:
    intervals_by_resource: dict[str, list[tuple[int, int]]] = defaultdict(list)
    overlap_by_block_id: dict[str, int] = defaultdict(int)

    ordered_blocks = sorted(schedule_blocks, key=lambda item: item.order_key)
    for index, left in enumerate(ordered_blocks):
        left_cores = set(_block_core_ids(left, core_ids))
        left_interval = (max(0, left.issue_slot), max(0, left.issue_slot) + max(1, left.duration_slots))
        for right in ordered_blocks[index + 1 :]:
            right_cores = set(_block_core_ids(right, core_ids))
            if left_cores & right_cores:
                continue
            overlap_start = max(left_interval[0], max(0, right.issue_slot))
            overlap_end = min(left_interval[1], max(0, right.issue_slot) + max(1, right.duration_slots))
            if overlap_end <= overlap_start:
                continue
            shared_resources = sorted(
                (set(left.resource_set) & set(right.resource_set)) & _GLOBAL_CONTENTION_RESOURCES
            )
            if not shared_resources:
                continue
            overlap_slots = overlap_end - overlap_start
            overlap_by_block_id[left.block_id] += overlap_slots
            overlap_by_block_id[right.block_id] += overlap_slots
            for resource_name in shared_resources:
                intervals_by_resource[resource_name].append((overlap_start, overlap_end))

    contention_slots = _merged_interval_length(
        [interval for intervals in intervals_by_resource.values() for interval in intervals]
    )
    contended_resources = {
        resource_name: _merged_interval_length(intervals)
        for resource_name, intervals in sorted(intervals_by_resource.items())
    }
    top_contention_block_ids = [
        block_id
        for block_id, _slots in sorted(
            overlap_by_block_id.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    return ResourceContentionSummary(
        makespan_slots=makespan_slots,
        contention_slots=contention_slots,
        contention_ratio=(contention_slots / makespan_slots) if makespan_slots > 0 else 0.0,
        contended_resources=contended_resources,
        top_contention_block_ids=top_contention_block_ids,
    )


def _schedule_core_ids(schedule_ir: ScheduleIR) -> list[int]:
    seen_core_ids = {
        block.core_id
        for block in schedule_ir.blocks
        if isinstance(block.core_id, int)
    }
    seen_core_ids.update(
        block.peer_core_id
        for block in schedule_ir.blocks
        if block.peer_core_id is not None
    )
    if schedule_ir.core_mode == "dual-core":
        seen_core_ids.update({0, 1})
    if not seen_core_ids:
        seen_core_ids.add(0)
    return sorted(seen_core_ids)


def _block_core_ids(block: ScheduleBlock, core_ids: list[int]) -> list[int]:
    if block.core_id == "both":
        return list(core_ids)
    block_core_ids = [int(block.core_id)]
    if block.peer_core_id is not None and block.peer_core_id not in block_core_ids:
        block_core_ids.append(block.peer_core_id)
    return sorted(block_core_ids)


def _infer_gap_reason(
    block: ScheduleBlock,
    *,
    previous_end: int,
    block_end_by_id: dict[str, int],
) -> str | None:
    waiting_dependency_ids = _waiting_dependency_ids(
        block,
        block_end_by_id=block_end_by_id,
        previous_end=previous_end,
    )
    if waiting_dependency_ids:
        return "dependency_wait"
    if block.barrier_in:
        return "barrier_wait"
    return "idle"


def _infer_block_stall_reason(
    block: ScheduleBlock,
    *,
    block_end_by_id: dict[str, int],
) -> str | None:
    if _waiting_dependency_ids(block, block_end_by_id=block_end_by_id):
        return "dependency_wait"
    if block.barrier_in:
        return "barrier_wait"
    return None


def _waiting_dependency_ids(
    block: ScheduleBlock,
    *,
    block_end_by_id: dict[str, int],
    previous_end: int | None = None,
) -> list[str]:
    wait_threshold = 0 if previous_end is None else previous_end
    return [
        dependency_id
        for dependency_id in block.depends_on
        if block_end_by_id.get(dependency_id, 0) > wait_threshold
    ]


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
