"""SPEC-10 deterministic single-core scheduler foundation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from heapq import heappop, heappush

from llm_sched.arch.capabilities import ArchitectureCapabilities
from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile
from llm_sched.contracts.memory_plan import MemoryPlanArtifact, PlannedAllocation
from llm_sched.contracts.tiling_plan import TileCandidate, TilingPlanArtifact
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


_GEMM_COMPUTE_RESOURCES = {
    "GEMM": ["MXU"],
    "WDQ_GEMM": ["WDQ", "MXU"],
    "RMSNORM_GEMM": ["VPU", "MXU"],
}
_TILED_MACROS = frozenset({*(_GEMM_COMPUTE_RESOURCES.keys()), "SDPA", "SDPA_DECODE"})
_STAGE_POLICIES: dict[str, list[tuple[str, list[str]]]] = {
    "RMSNORM": [("dma_in", ["DMA"]), ("compute", ["VPU"]), ("store", ["DMA"])],
    "ELEM_ADD": [("dma_in", ["DMA"]), ("compute", ["VPU"]), ("store", ["DMA"])],
    "GEGLU": [
        ("dma_in", ["DMA"]),
        ("prepare", ["VPU"]),
        ("compute", ["MXU", "VPU"]),
        ("store", ["DMA"]),
    ],
    "ROPE": [
        ("dma_in", ["DMA"]),
        ("prepare", ["VPU"]),
        ("compute", ["VPU"]),
        ("store", ["DMA"]),
    ],
    "ATTENTION_MASK_PREP": [
        ("dma_in", ["DMA"]),
        ("prepare", ["VPU"]),
        ("compute", ["VPU"]),
        ("store", ["DMA"]),
    ],
    "EMBEDDING_LOOKUP": [("dma_in", ["DMA"]), ("compute", ["VPU"]), ("store", ["DMA"])],
    "SHAPE_HELPER": [("prepare", ["VPU"]), ("compute", ["VPU"])],
    "LAYOUT_FALLBACK": [
        ("dma_in", ["DMA"]),
        ("prepare", ["VPU"]),
        ("compute", ["VPU"]),
        ("store", ["DMA"]),
    ],
    "ROPE_TABLE": [("dma_in", ["DMA"])],
    "KVLOAD": [("dma_in", ["DMA"])],
    "KVSTORE": [("store", ["DMA"])],
}


@dataclass(frozen=True, slots=True)
class _PendingBlock:
    block_id: str
    node_id: str
    macro_op: str
    stage: str
    tiling_candidate_id: str | None
    resource_set: list[str]
    buffer_binding: dict[str, str]
    depends_on: list[str]
    duration_slots: int
    resource_reservations: list[tuple[str, int, int]]
    priority: tuple[int, int]
    audit_ref: AuditRef


def plan_single_core_schedule(
    bound_nig_ir: NIGIR,
    memory_plan: MemoryPlanArtifact,
    tiling_plan: TilingPlanArtifact,
    hardware: TargetProfile | ArchitectureCapabilities,
    scenario: ScenarioProfile,
) -> ScheduleIR:
    if bound_nig_ir.binding_state != "bound":
        raise ValueError("single-core scheduler requires bound NIGIR input")
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
    if capabilities.core_mode != "single-core":
        raise ValueError("single-core scheduler requires a single-core target profile")

    allocations_by_node = _group_allocations_by_node(memory_plan.allocations)
    candidates_by_node = _group_candidates_by_node(tiling_plan.candidates)
    node_lookup = {node.node_id: node for node in bound_nig_ir.nodes}
    producer_by_tensor = _group_producer_by_tensor(bound_nig_ir.nodes)
    pending_blocks = _build_pending_blocks(
        bound_nig_ir.nodes,
        candidates_by_node=candidates_by_node,
        allocations_by_node=allocations_by_node,
        producer_by_tensor=producer_by_tensor,
        capabilities=capabilities,
        scenario=scenario,
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
            depends_on=pending.depends_on,
            resource_reservations=pending.resource_reservations,
            reservations_by_resource=reservations_by_resource,
            block_end_slots=block_end_slots,
        )
        if issue_slot != scheduled_issue_slot:
            heappush(ready_heap, (issue_slot, pending.priority, next_block_id))
            continue
        node = node_lookup[pending.node_id]
        block = ScheduleBlock(
            block_id=pending.block_id,
            core_id=0,
            node_id=pending.node_id,
            macro_op=pending.macro_op,
            stage=pending.stage,
            tiling_candidate_id=pending.tiling_candidate_id,
            resource_set=pending.resource_set,
            buffer_binding=pending.buffer_binding,
            barrier_in=[],
            barrier_out=[],
            depends_on=pending.depends_on,
            issue_slot=issue_slot,
            duration_slots=pending.duration_slots,
            order_key=order_key,
            audit_ref=AuditRef(
                graph_node_ids=list(node.audit_ref.graph_node_ids),
                nig_node_ids=[pending.node_id],
                source_ids=list(node.audit_ref.source_ids),
            ),
        )
        blocks.append(block)
        _reserve_resources(
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
        core_mode="single-core",
        blocks=blocks,
    )


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
