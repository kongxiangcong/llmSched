"""SPEC-11 deterministic dual-core scheduler with overlap foundation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush

from llm_sched.arch import ArchitectureCapabilities
from llm_sched.config import ScenarioProfile
from llm_sched.config import TargetProfile
from llm_sched.contracts.models import MemoryPlanArtifact, PlannedAllocation
from llm_sched.contracts.models import TileCandidate, TilingPlanArtifact
from llm_sched.ir.common import AuditRef
from llm_sched.ir.nig import NIGIR, NIGNode
from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR
from llm_sched.planning.schedule_duration import (
    estimate_stage_duration_slots,
    estimate_stage_resource_reservations,
)
from llm_sched.planning.schedule_reservations import (
    build_reservation_timeline,
    find_earliest_issue_slot,
    reserve_resource_windows,
)


_TILED_MACROS = frozenset({"GEMM", "WDQ_GEMM", "RMSNORM_GEMM", "SDPA", "SDPA_DECODE"})


@dataclass(frozen=True, slots=True)
class _ScheduledNodePlan:
    node: NIGNode
    node_index: int
    core_id: int
    candidate: TileCandidate | None
    stages: list[tuple[str, list[str]]]
    buffer_binding: dict[str, str]


@dataclass(frozen=True, slots=True)
class _TransferPlan:
    block_id: str
    producer_node_id: str
    consumer_node_id: str
    producer_core_id: int
    consumer_core_id: int
    tiling_candidate_id: str | None
    resource_set: list[str]
    buffer_binding: dict[str, str]
    barrier_in: list[str]
    barrier_out: list[str]
    transfer_kind: str
    transfer_bytes: int
    sync_cost_cycles: int
    priority: tuple[int, int]
    audit_ref: AuditRef


@dataclass(frozen=True, slots=True)
class _PendingBlock:
    block_id: str
    core_id: int
    peer_core_id: int | None
    node_id: str
    macro_op: str
    stage: str
    tiling_candidate_id: str | None
    resource_set: list[str]
    buffer_binding: dict[str, str]
    barrier_in: list[str]
    barrier_out: list[str]
    depends_on: list[str]
    transfer_kind: str | None
    transfer_bytes: int
    sync_cost_cycles: int
    duration_slots: int
    resource_reservations: list[tuple[str, int, int]]
    priority: tuple[int, int]
    audit_ref: AuditRef


def plan_dual_core_schedule(
    bound_nig_ir: NIGIR,
    memory_plan: MemoryPlanArtifact,
    tiling_plan: TilingPlanArtifact,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> ScheduleIR:
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("dual-core scheduler requires bound NIGIR input")
    if memory_plan.graph_id != bound_nig_ir.graph_id:
        raise ValueError("memory_plan graph_id must match bound_nig_ir graph_id")
    if tiling_plan.graph_id != bound_nig_ir.graph_id:
        raise ValueError("tiling_plan graph_id must match bound_nig_ir graph_id")
    if tiling_plan.scenario_name != scenario.scenario_name:
        raise ValueError("tiling_plan scenario_name must match scenario profile")

    capabilities = (
        hardware
        if isinstance(hardware, ArchitectureCapabilities)
        else ArchitectureCapabilities.from_target_profile(hardware)
    )
    if capabilities.core_mode != "dual-core":
        raise ValueError("dual-core scheduler requires a dual-core target profile")

    allocations_by_node = _group_allocations_by_node(memory_plan.allocations)
    candidates_by_node = _group_candidates_by_node(tiling_plan.candidates)
    scheduled_nodes = _build_scheduled_node_plans(
        bound_nig_ir.nodes,
        candidates_by_node=candidates_by_node,
        allocations_by_node=allocations_by_node,
        scenario=scenario,
    )
    producer_by_tensor = _group_producer_by_tensor([plan.node for plan in scheduled_nodes])
    scheduled_node_by_id = {plan.node.node_id: plan for plan in scheduled_nodes}
    stage_names_by_node = {plan.node.node_id: [stage for stage, _ in plan.stages] for plan in scheduled_nodes}
    core_by_node = {plan.node.node_id: plan.core_id for plan in scheduled_nodes}
    transfer_plans = _build_transfer_plans(
        scheduled_nodes,
        producer_by_tensor=producer_by_tensor,
        core_by_node=core_by_node,
        allocations_by_node=allocations_by_node,
        capabilities=capabilities,
    )
    pending_blocks = _build_pending_blocks(
        scheduled_nodes,
        stage_names_by_node=stage_names_by_node,
        producer_by_tensor=producer_by_tensor,
        core_by_node=core_by_node,
        transfer_plans=transfer_plans,
        allocations_by_node=allocations_by_node,
        capabilities=capabilities,
    )

    pending_by_id = {block.block_id: block for block in pending_blocks}
    dependents_by_block_id: dict[str, list[str]] = defaultdict(list)
    remaining_dep_count: dict[str, int] = {}
    for block in pending_blocks:
        remaining_dep_count[block.block_id] = len(block.depends_on)
        for dependency_id in block.depends_on:
            dependents_by_block_id[dependency_id].append(block.block_id)

    ready_heap: list[tuple[int, tuple[int, int], str]] = []
    reservations_by_resource = build_reservation_timeline()
    block_end_slots: dict[str, int] = {}
    for block in pending_blocks:
        if remaining_dep_count[block.block_id] != 0:
            continue
        issue_slot = _earliest_issue_slot(
            core_id=block.core_id,
            depends_on=block.depends_on,
            resource_reservations=block.resource_reservations,
            reservations_by_resource=reservations_by_resource,
            block_end_slots=block_end_slots,
        )
        heappush(ready_heap, (issue_slot, block.priority, block.block_id))
    blocks: list[ScheduleBlock] = []
    order_key = 0
    while ready_heap:
        scheduled_issue_slot, _priority, next_block_id = heappop(ready_heap)
        pending = pending_by_id[next_block_id]
        issue_slot = _earliest_issue_slot(
            core_id=pending.core_id,
            depends_on=pending.depends_on,
            resource_reservations=pending.resource_reservations,
            reservations_by_resource=reservations_by_resource,
            block_end_slots=block_end_slots,
        )
        if issue_slot != scheduled_issue_slot:
            heappush(ready_heap, (issue_slot, pending.priority, next_block_id))
            continue
        block = ScheduleBlock(
            block_id=pending.block_id,
            core_id=pending.core_id,
            peer_core_id=pending.peer_core_id,
            node_id=pending.node_id,
            macro_op=pending.macro_op,
            stage=pending.stage,
            tiling_candidate_id=pending.tiling_candidate_id,
            resource_set=pending.resource_set,
            buffer_binding=pending.buffer_binding,
            barrier_in=pending.barrier_in,
            barrier_out=pending.barrier_out,
            depends_on=pending.depends_on,
            issue_slot=issue_slot,
            duration_slots=pending.duration_slots,
            transfer_kind=pending.transfer_kind,
            transfer_bytes=pending.transfer_bytes,
            sync_cost_cycles=pending.sync_cost_cycles,
            order_key=order_key,
            audit_ref=pending.audit_ref,
        )
        blocks.append(block)
        _reserve_resources(
            core_id=pending.core_id,
            issue_slot=issue_slot,
            resource_reservations=pending.resource_reservations,
            reservations_by_resource=reservations_by_resource,
        )
        block_end_slots[block.block_id] = issue_slot + pending.duration_slots
        for dependent_block_id in dependents_by_block_id.get(block.block_id, []):
            remaining_dep_count[dependent_block_id] -= 1
            if remaining_dep_count[dependent_block_id] == 0:
                dependent = pending_by_id[dependent_block_id]
                dependent_issue_slot = _earliest_issue_slot(
                    core_id=dependent.core_id,
                    depends_on=dependent.depends_on,
                    resource_reservations=dependent.resource_reservations,
                    reservations_by_resource=reservations_by_resource,
                    block_end_slots=block_end_slots,
                )
                heappush(
                    ready_heap,
                    (dependent_issue_slot, dependent.priority, dependent_block_id),
                )
        order_key += 1

    return ScheduleIR(
        ir_version=bound_nig_ir.ir_version,
        graph_id=bound_nig_ir.graph_id,
        core_mode="dual-core",
        blocks=blocks,
    )


def _build_scheduled_node_plans(
    nodes: list[NIGNode],
    *,
    candidates_by_node: dict[str, list[TileCandidate]],
    allocations_by_node: dict[str, list[PlannedAllocation]],
    scenario: ScenarioProfile,
) -> list[_ScheduledNodePlan]:
    scheduled_nodes: list[_ScheduledNodePlan] = []
    scheduled_index = 0
    for node_index, node in enumerate(nodes):
        if node.binding is None:
            continue
        candidate = _select_candidate(node, candidates_by_node.get(node.node_id, []), scenario)
        node_stages = _lower_node_stages(node)
        if candidate is None and node.macro_op in _TILED_MACROS:
            continue
        if not node_stages:
            continue
        core_id = scheduled_index % 2
        scheduled_nodes.append(
            _ScheduledNodePlan(
                node=node,
                node_index=node_index,
                core_id=core_id,
                candidate=candidate,
                stages=node_stages,
                buffer_binding=_buffer_binding(allocations_by_node.get(node.node_id, [])),
            )
        )
        scheduled_index += 1
    return scheduled_nodes


def _build_transfer_plans(
    scheduled_nodes: list[_ScheduledNodePlan],
    *,
    producer_by_tensor: dict[str, str],
    core_by_node: dict[str, int],
    allocations_by_node: dict[str, list[PlannedAllocation]],
    capabilities: ArchitectureCapabilities,
) -> dict[tuple[str, str], _TransferPlan]:
    scheduled_node_by_id = {plan.node.node_id: plan for plan in scheduled_nodes}
    transfer_plans: dict[tuple[str, str], _TransferPlan] = {}
    for consumer_plan in scheduled_nodes:
        for input_name in consumer_plan.node.inputs:
            producer_node_id = producer_by_tensor.get(input_name)
            if producer_node_id is None:
                continue
            producer_core_id = core_by_node.get(producer_node_id)
            if producer_core_id is None or producer_core_id == consumer_plan.core_id:
                continue
            key = (producer_node_id, consumer_plan.node.node_id)
            if key in transfer_plans:
                continue
            producer_plan = scheduled_node_by_id[producer_node_id]
            transfer_kind = "core_link" if capabilities.core_link.enabled else "dma"
            transfer_resource = "Core Link" if transfer_kind == "core_link" else "DMA"
            transfer_index = len(transfer_plans)
            transfer_plans[key] = _TransferPlan(
                block_id=f"sched.transfer.{producer_node_id}.to.{consumer_plan.node.node_id}",
                producer_node_id=producer_node_id,
                consumer_node_id=consumer_plan.node.node_id,
                producer_core_id=producer_core_id,
                consumer_core_id=consumer_plan.core_id,
                tiling_candidate_id=(
                    consumer_plan.candidate.candidate_id if consumer_plan.candidate is not None else None
                ),
                resource_set=[transfer_resource],
                buffer_binding={
                    "src": producer_plan.buffer_binding.get(
                        "output",
                        producer_plan.buffer_binding.get("activation", "DDR"),
                    ),
                    "dst": consumer_plan.buffer_binding.get(
                        "input",
                        consumer_plan.buffer_binding.get("activation", "VMEM"),
                    ),
                },
                barrier_in=[f"sync.transfer.{transfer_index}.in"],
                barrier_out=[f"sync.transfer.{transfer_index}.out"],
                transfer_kind=transfer_kind,
                transfer_bytes=_estimate_transfer_bytes(
                    producer_plan.node,
                    allocations_by_node.get(producer_node_id, []),
                ),
                sync_cost_cycles=capabilities.sync.cross_core_transfer_cost_cycles,
                priority=(consumer_plan.node_index, -1),
                audit_ref=AuditRef(
                    graph_node_ids=list(
                        dict.fromkeys(
                            [
                                *producer_plan.node.audit_ref.graph_node_ids,
                                *consumer_plan.node.audit_ref.graph_node_ids,
                            ]
                        )
                    ),
                    nig_node_ids=[producer_node_id, consumer_plan.node.node_id],
                    source_ids=list(
                        dict.fromkeys(
                            [
                                *producer_plan.node.audit_ref.source_ids,
                                *consumer_plan.node.audit_ref.source_ids,
                            ]
                        )
                    ),
                ),
            )
    return transfer_plans


def _build_pending_blocks(
    scheduled_nodes: list[_ScheduledNodePlan],
    *,
    stage_names_by_node: dict[str, list[str]],
    producer_by_tensor: dict[str, str],
    core_by_node: dict[str, int],
    transfer_plans: dict[tuple[str, str], _TransferPlan],
    allocations_by_node: dict[str, list[PlannedAllocation]],
    capabilities: ArchitectureCapabilities,
) -> list[_PendingBlock]:
    pending_blocks: list[_PendingBlock] = []

    for consumer_plan in scheduled_nodes:
        stage_names = stage_names_by_node[consumer_plan.node.node_id]
        input_dependency_block_ids = _input_dependency_block_ids(
            consumer_plan.node,
            consumer_core_id=consumer_plan.core_id,
            producer_by_tensor=producer_by_tensor,
            stage_names_by_node=stage_names_by_node,
            core_by_node=core_by_node,
            transfer_plans=transfer_plans,
        )
        previous_stage_block_id: str | None = None
        for stage_index, (stage, resource_set) in enumerate(consumer_plan.stages):
            block_id = f"sched.{consumer_plan.node.node_id}.{stage}.core{consumer_plan.core_id}"
            duration_slots = estimate_stage_duration_slots(
                node=consumer_plan.node,
                stage=stage,
                candidate=consumer_plan.candidate,
                allocations=allocations_by_node.get(consumer_plan.node.node_id, []),
                capabilities=capabilities,
            )
            pending_blocks.append(
                _PendingBlock(
                    block_id=block_id,
                    core_id=consumer_plan.core_id,
                    peer_core_id=None,
                    node_id=consumer_plan.node.node_id,
                    macro_op=consumer_plan.node.macro_op,
                    stage=stage,
                    tiling_candidate_id=(
                        consumer_plan.candidate.candidate_id if consumer_plan.candidate is not None else None
                    ),
                    resource_set=resource_set,
                    buffer_binding=consumer_plan.buffer_binding,
                    barrier_in=[],
                    barrier_out=[],
                    depends_on=_stage_dependencies(
                        stage,
                        previous_stage_block_id=previous_stage_block_id,
                        input_dependency_block_ids=input_dependency_block_ids,
                    ),
                    transfer_kind=None,
                    transfer_bytes=0,
                    sync_cost_cycles=0,
                    duration_slots=duration_slots,
                    resource_reservations=_resource_reservations(
                        core_id=consumer_plan.core_id,
                        macro_op=consumer_plan.node.macro_op,
                        stage=stage,
                        sync_cost_cycles=0,
                        duration_slots=duration_slots,
                        resource_set=resource_set,
                        node=consumer_plan.node,
                        candidate=consumer_plan.candidate,
                        capabilities=capabilities,
                    ),
                    priority=(consumer_plan.node_index, stage_index),
                    audit_ref=AuditRef(
                        graph_node_ids=list(consumer_plan.node.audit_ref.graph_node_ids),
                        nig_node_ids=[consumer_plan.node.node_id],
                        source_ids=list(consumer_plan.node.audit_ref.source_ids),
                    ),
                )
            )
            previous_stage_block_id = block_id

        for input_name in consumer_plan.node.inputs:
            producer_node_id = producer_by_tensor.get(input_name)
            if producer_node_id is None:
                continue
            key = (producer_node_id, consumer_plan.node.node_id)
            transfer_plan = transfer_plans.get(key)
            if transfer_plan is None:
                continue
            if any(block.block_id == transfer_plan.block_id for block in pending_blocks):
                continue
            duration_slots = estimate_stage_duration_slots(
                node=consumer_plan.node,
                stage="transfer",
                candidate=consumer_plan.candidate,
                allocations=allocations_by_node.get(producer_node_id, []),
                capabilities=capabilities,
                transfer_bytes=transfer_plan.transfer_bytes,
                transfer_kind=transfer_plan.transfer_kind,
            )
            pending_blocks.append(
                _PendingBlock(
                    block_id=transfer_plan.block_id,
                    core_id=transfer_plan.producer_core_id,
                    peer_core_id=transfer_plan.consumer_core_id,
                    node_id=transfer_plan.consumer_node_id,
                    macro_op=consumer_plan.node.macro_op,
                    stage="transfer",
                    tiling_candidate_id=transfer_plan.tiling_candidate_id,
                    resource_set=transfer_plan.resource_set,
                    buffer_binding=transfer_plan.buffer_binding,
                    barrier_in=transfer_plan.barrier_in,
                    barrier_out=transfer_plan.barrier_out,
                    depends_on=[
                        _terminal_block_id(
                            producer_node_id,
                            stage_names_by_node=stage_names_by_node,
                            core_by_node=core_by_node,
                        )
                    ],
                    transfer_kind=transfer_plan.transfer_kind,
                    transfer_bytes=transfer_plan.transfer_bytes,
                    sync_cost_cycles=transfer_plan.sync_cost_cycles,
                    duration_slots=duration_slots,
                    resource_reservations=_resource_reservations(
                        core_id=transfer_plan.producer_core_id,
                        macro_op=consumer_plan.node.macro_op,
                        stage="transfer",
                        sync_cost_cycles=transfer_plan.sync_cost_cycles,
                        duration_slots=duration_slots,
                        resource_set=transfer_plan.resource_set,
                    ),
                    priority=transfer_plan.priority,
                    audit_ref=transfer_plan.audit_ref,
                )
            )

    return pending_blocks


def _input_dependency_block_ids(
    node: NIGNode,
    *,
    consumer_core_id: int,
    producer_by_tensor: dict[str, str],
    stage_names_by_node: dict[str, list[str]],
    core_by_node: dict[str, int],
    transfer_plans: dict[tuple[str, str], _TransferPlan],
) -> list[str]:
    dependency_ids: list[str] = []
    for input_name in node.inputs:
        producer_node_id = producer_by_tensor.get(input_name)
        if producer_node_id is None:
            continue
        producer_core_id = core_by_node.get(producer_node_id)
        if producer_core_id is None:
            continue
        if producer_core_id == consumer_core_id:
            dependency_id = _terminal_block_id(
                producer_node_id,
                stage_names_by_node=stage_names_by_node,
                core_by_node=core_by_node,
            )
        else:
            transfer_plan = transfer_plans.get((producer_node_id, node.node_id))
            if transfer_plan is None:
                continue
            dependency_id = transfer_plan.block_id
        if dependency_id not in dependency_ids:
            dependency_ids.append(dependency_id)
    return dependency_ids


def _terminal_block_id(
    node_id: str,
    *,
    stage_names_by_node: dict[str, list[str]],
    core_by_node: dict[str, int],
) -> str:
    return f"sched.{node_id}.{stage_names_by_node[node_id][-1]}.core{core_by_node[node_id]}"


def _earliest_issue_slot(
    *,
    core_id: int,
    depends_on: list[str],
    resource_reservations: list[tuple[str, int, int]],
    reservations_by_resource: dict[str, list[tuple[int, int]]],
    block_end_slots: dict[str, int],
) -> int:
    dependency_ready_slot = max((block_end_slots[block_id] for block_id in depends_on), default=0)
    return find_earliest_issue_slot(
        ready_slot=dependency_ready_slot,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=resource_reservations,
    )


def _reserve_resources(
    *,
    core_id: int,
    issue_slot: int,
    resource_reservations: list[tuple[str, int, int]],
    reservations_by_resource: dict[str, list[tuple[int, int]]],
) -> None:
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=issue_slot,
        requested_reservations=resource_reservations,
    )


def _resource_keys(core_id: int, resource_set: list[str]) -> list[str]:
    keys: list[str] = []
    for resource in resource_set:
        if resource == "DMA":
            keys.append("shared:DMA")
        elif resource == "Core Link":
            keys.append("shared:Core Link")
        else:
            keys.append(f"core{core_id}:{resource}")
    return keys


def _resource_reservations(
    *,
    core_id: int,
    macro_op: str,
    stage: str,
    sync_cost_cycles: int,
    duration_slots: int,
    resource_set: list[str],
    node: NIGNode | None = None,
    candidate: TileCandidate | None = None,
    capabilities: ArchitectureCapabilities | None = None,
) -> list[tuple[str, int, int]]:
    return [
        (_map_resource_name(core_id, resource_name), start_offset, reservation_duration)
        for resource_name, start_offset, reservation_duration in estimate_stage_resource_reservations(
            macro_op=macro_op,
            stage=stage,
            resource_set=resource_set,
            duration_slots=duration_slots,
            sync_cost_cycles=sync_cost_cycles,
            node=node,
            candidate=candidate,
            capabilities=capabilities,
        )
    ]


def _map_resource_name(core_id: int, resource_name: str) -> str:
    if resource_name == "DMA":
        return "shared:DMA"
    if resource_name == "Core Link":
        return "shared:Core Link"
    if resource_name == "SYNC":
        return "shared:SYNC"
    return f"core{core_id}:{resource_name}"


def _estimate_transfer_bytes(node: NIGNode, allocations: list[PlannedAllocation]) -> int:
    output_bytes = sum(
        allocation.size_bytes for allocation in allocations if allocation.tensor_role == "output"
    )
    if output_bytes > 0:
        return output_bytes
    element_count = 1
    for dim in node.binding.resolved_shape if node.binding is not None else node.shape:
        element_count *= max(1, dim)
    return max(element_count * 2, 1)
def _group_allocations_by_node(
    allocations: list[PlannedAllocation],
) -> dict[str, list[PlannedAllocation]]:
    grouped: dict[str, list[PlannedAllocation]] = defaultdict(list)
    for allocation in allocations:
        grouped[allocation.node_id].append(allocation)
    return dict(grouped)


def _group_candidates_by_node(
    candidates: list[TileCandidate],
) -> dict[str, list[TileCandidate]]:
    grouped: dict[str, list[TileCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.node_id].append(candidate)
    return dict(grouped)


def _select_candidate(
    node: NIGNode,
    candidates: list[TileCandidate],
    scenario: ScenarioProfile,
) -> TileCandidate | None:
    if not candidates:
        return None
    return sorted(candidates, key=lambda candidate: (candidate.rank, candidate.candidate_id))[0]


def _buffer_binding(allocations: list[PlannedAllocation]) -> dict[str, str]:
    binding: dict[str, str] = {}
    for allocation in allocations:
        role = allocation.tensor_role
        if role == "quant_param":
            key = "quant"
        elif role == "kv_cache":
            key = "kv"
        elif role == "weight":
            key = "weight"
        elif role == "temp":
            key = allocation.tensor_name
        else:
            key = role
        binding.setdefault(key, allocation.region_name or allocation.address_space)
    return binding


def _lower_node_stages(node: NIGNode) -> list[tuple[str, list[str]]]:
    if node.macro_op in _GEMM_COMPUTE_RESOURCES:
        return [
            ("dma_in", ["DMA"]),
            ("compute", list(_GEMM_COMPUTE_RESOURCES[node.macro_op])),
            ("store", ["DMA"]),
        ]
    if node.macro_op == "SDPA":
        return [
            ("dma_in", ["DMA"]),
            ("prepare", ["VPU"]),
            ("compute", ["MXU", "VPU"]),
            ("store", ["DMA"]),
        ]
    if node.macro_op == "SDPA_DECODE":
        return [
            ("dma_in", ["DMA"]),
            ("prepare", ["VPU"]),
            ("compute", ["DMA", "VPU"]),
            ("store", ["DMA"]),
        ]
    return list(_STAGE_POLICIES.get(node.macro_op, []))


def _group_producer_by_tensor(nodes: list[NIGNode]) -> dict[str, str]:
    producer_by_tensor: dict[str, str] = {}
    for node in nodes:
        for output_name in node.outputs:
            producer_by_tensor[output_name] = node.node_id
    return producer_by_tensor


def _build_pending_blocks(
    nodes: list[NIGNode],
    *,
    candidates_by_node: dict[str, list[TileCandidate]],
    allocations_by_node: dict[str, list[PlannedAllocation]],
    producer_by_tensor: dict[str, str],
    capabilities: ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> list[_PendingBlock]:
    stage_names_by_node: dict[str, list[str]] = {}
    candidate_by_node: dict[str, TileCandidate | None] = {}
    for node in nodes:
        if node.binding is None:
            continue
        candidate = _select_candidate(node, candidates_by_node.get(node.node_id, []), scenario)
        node_stages = _lower_node_stages(node)
        if candidate is None and node.macro_op in _TILED_MACROS:
            continue
        if not node_stages:
            continue
        stage_names_by_node[node.node_id] = [stage for stage, _ in node_stages]
        candidate_by_node[node.node_id] = candidate

    pending_blocks: list[_PendingBlock] = []
    for node_index, node in enumerate(nodes):
        stage_names = stage_names_by_node.get(node.node_id)
        if stage_names is None:
            continue
        candidate = candidate_by_node[node.node_id]
        node_stages = _lower_node_stages(node)
        buffer_binding = _buffer_binding(allocations_by_node.get(node.node_id, []))
        input_dependency_block_ids = _input_dependency_block_ids(
            node,
            producer_by_tensor=producer_by_tensor,
            stage_names_by_node=stage_names_by_node,
        )
        previous_stage_block_id: str | None = None
        for stage_index, (stage, resource_set) in enumerate(node_stages):
            block_id = f"sched.{node.node_id}.{stage}"
            duration_slots = estimate_stage_duration_slots(
                node=node,
                stage=stage,
                candidate=candidate,
                allocations=allocations_by_node.get(node.node_id, []),
                capabilities=capabilities,
            )
            pending_blocks.append(
                _PendingBlock(
                    block_id=block_id,
                    node_id=node.node_id,
                    macro_op=node.macro_op,
                    stage=stage,
                    tiling_candidate_id=candidate.candidate_id if candidate is not None else None,
                    resource_set=resource_set,
                    buffer_binding=buffer_binding,
                    depends_on=_stage_dependencies(
                        stage,
                        previous_stage_block_id=previous_stage_block_id,
                        input_dependency_block_ids=input_dependency_block_ids,
                    ),
                    duration_slots=duration_slots,
                    resource_reservations=_resource_reservations(
                        macro_op=node.macro_op,
                        stage=stage,
                        resource_set=resource_set,
                        duration_slots=duration_slots,
                        node=node,
                        candidate=candidate,
                        capabilities=capabilities,
                    ),
                    priority=(node_index, stage_index),
                    audit_ref=AuditRef(
                        graph_node_ids=list(node.audit_ref.graph_node_ids),
                        nig_node_ids=[node.node_id],
                        source_ids=list(node.audit_ref.source_ids),
                    ),
                )
            )
            previous_stage_block_id = block_id
    return pending_blocks


def _input_dependency_block_ids(
    node: NIGNode,
    *,
    producer_by_tensor: dict[str, str],
    stage_names_by_node: dict[str, list[str]],
) -> list[str]:
    dependency_ids: list[str] = []
    for input_name in node.inputs:
        producer_node_id = producer_by_tensor.get(input_name)
        if producer_node_id is None:
            continue
        producer_stages = stage_names_by_node.get(producer_node_id)
        if not producer_stages:
            continue
        terminal_block_id = f"sched.{producer_node_id}.{producer_stages[-1]}"
        if terminal_block_id not in dependency_ids:
            dependency_ids.append(terminal_block_id)
    return dependency_ids


def _stage_dependencies(
    stage: str,
    *,
    previous_stage_block_id: str | None,
    input_dependency_block_ids: list[str],
) -> list[str]:
    depends_on: list[str] = []
    if previous_stage_block_id is not None:
        depends_on.append(previous_stage_block_id)
    if stage in {"prepare", "compute"} or (previous_stage_block_id is None and stage == "store"):
        for dependency_id in input_dependency_block_ids:
            if dependency_id not in depends_on:
                depends_on.append(dependency_id)
    return depends_on


def _earliest_issue_slot(
    *,
    depends_on: list[str],
    resource_reservations: list[tuple[str, int, int]],
    reservations_by_resource: dict[str, list[tuple[int, int]]],
    block_end_slots: dict[str, int],
) -> int:
    dependency_ready_slot = max((block_end_slots[block_id] for block_id in depends_on), default=0)
    return find_earliest_issue_slot(
        ready_slot=dependency_ready_slot,
        reservations_by_resource=reservations_by_resource,
        requested_reservations=resource_reservations,
    )


def _reserve_resources(
    *,
    issue_slot: int,
    resource_reservations: list[tuple[str, int, int]],
    reservations_by_resource: dict[str, list[tuple[int, int]]],
) -> None:
    reserve_resource_windows(
        reservations_by_resource=reservations_by_resource,
        issue_slot=issue_slot,
        requested_reservations=resource_reservations,
    )


def _resource_keys(resource_set: list[str]) -> list[str]:
    return [
        "shared:DMA" if resource == "DMA" else resource
        for resource in resource_set
    ]


def _resource_reservations(
    *,
    macro_op: str,
    stage: str,
    resource_set: list[str],
    duration_slots: int,
    node: NIGNode | None = None,
    candidate: TileCandidate | None = None,
    capabilities: ArchitectureCapabilities | None = None,
) -> list[tuple[str, int, int]]:
    return [
        (
            "shared:DMA" if resource_name == "DMA" else resource_name,
            start_offset,
            reservation_duration,
        )
        for resource_name, start_offset, reservation_duration in estimate_stage_resource_reservations(
            macro_op=macro_op,
            stage=stage,
            resource_set=resource_set,
            duration_slots=duration_slots,
            node=node,
            candidate=candidate,
            capabilities=capabilities,
        )
    ]
