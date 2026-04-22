"""Transform NIGIR into TaskDAG."""

from __future__ import annotations

import re

from llm_sched.ir.common import AuditRef
from llm_sched.ir.nig import NIGIR, NIGNode
from llm_sched.ir.task_dag import TaskDAG, TaskInput, TaskNode, TaskOutput


_ELIDED_MACRO_OPS = frozenset({"LAYOUT_FALLBACK", "SHAPE_HELPER", "ATTENTION_MASK_PREP"})


class TaskDAGBuildError(Exception):
    def __init__(self, message: str, diagnostics: list[str] | None = None) -> None:
        self.message = message
        self.diagnostics = diagnostics or []
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


def build_task_dag(nig_ir: NIGIR, graph_input_names: set[str] | None = None) -> TaskDAG:
    graph_input_names = graph_input_names or set()

    # Step A: Build producer map from NIGIR nodes
    nig_producer_by_tensor: dict[str, NIGNode] = {}
    for node in nig_ir.nodes:
        for output_name in node.outputs:
            nig_producer_by_tensor[output_name] = node

    # Step B: Identify elided nodes and build tensor rewriting map
    elided_node_ids: set[str] = {
        node.node_id for node in nig_ir.nodes if node.macro_op in _ELIDED_MACRO_OPS
    }

    tensor_rewrite: dict[str, str] = {}
    for node in nig_ir.nodes:
        if node.macro_op not in _ELIDED_MACRO_OPS:
            continue
        for output_name in node.outputs:
            if len(node.inputs) == 1:
                resolved_input = _resolve_tensor_name(node.inputs[0], tensor_rewrite)
                tensor_rewrite[output_name] = resolved_input
            elif len(node.inputs) == 0:
                pass
            else:
                for input_name in node.inputs:
                    if input_name:
                        resolved_input = _resolve_tensor_name(input_name, tensor_rewrite)
                        tensor_rewrite[output_name] = resolved_input
                        break

    # Step C: Create task nodes for non-elided NIG nodes (inputs unwired for now)
    task_nodes: list[TaskNode] = []
    for node in nig_ir.nodes:
        if node.macro_op in _ELIDED_MACRO_OPS:
            continue

        task_id = node.node_id.replace("nig.", "task.", 1)
        outputs = [
            TaskOutput(tensor_name=output_name, shape=node.shape)
            for output_name in node.outputs
        ]
        task_nodes.append(
            TaskNode(
                task_id=task_id,
                macro_op=node.macro_op,
                inputs=[],  # wired later
                outputs=outputs,
                attrs=dict(node.attrs),
                audit_ref=node.audit_ref,
            )
        )

    # Helper: find first non-elided consumer for shape inference
    def _first_non_elided_consumer(tensor_name: str) -> NIGNode | None:
        for node in nig_ir.nodes:
            if node.macro_op in _ELIDED_MACRO_OPS:
                continue
            for inp in node.inputs:
                if _resolve_tensor_name(inp, tensor_rewrite) == tensor_name:
                    return node
        return None

    # Step D: Determine graph inputs and constants
    consumed_tensors: set[str] = set()
    for node in nig_ir.nodes:
        if node.macro_op in _ELIDED_MACRO_OPS:
            continue
        for input_name in node.inputs:
            consumed_tensors.add(_resolve_tensor_name(input_name, tensor_rewrite))

    produced_tensors: set[str] = set()
    for node in nig_ir.nodes:
        for output_name in node.outputs:
            produced_tensors.add(output_name)

    graph_input_tensors = (consumed_tensors - produced_tensors) & graph_input_names
    constant_tensors = (consumed_tensors - produced_tensors) - graph_input_names

    # Create Input tasks
    input_tasks: list[TaskNode] = []
    input_task_id_by_tensor: dict[str, str] = {}
    for tensor_name in sorted(graph_input_tensors):
        consumer_node = _first_non_elided_consumer(tensor_name)
        shape = consumer_node.shape if consumer_node is not None else []
        task_id = f"task.input.{_sanitize_tensor_name(tensor_name)}"
        input_task_id_by_tensor[tensor_name] = task_id
        input_tasks.append(
            TaskNode(
                task_id=task_id,
                macro_op="Input",
                inputs=[],
                outputs=[TaskOutput(tensor_name=tensor_name, shape=shape)],
                attrs={},
                audit_ref=AuditRef(),
            )
        )

    # Create Constant tasks
    constant_tasks: list[TaskNode] = []
    constant_task_id_by_tensor: dict[str, str] = {}
    for tensor_name in sorted(constant_tensors):
        consumer_node = _first_non_elided_consumer(tensor_name)
        shape = consumer_node.shape if consumer_node is not None else []
        task_id = f"task.const.{_sanitize_tensor_name(tensor_name)}"
        constant_task_id_by_tensor[tensor_name] = task_id
        constant_tasks.append(
            TaskNode(
                task_id=task_id,
                macro_op="Constant",
                inputs=[],
                outputs=[TaskOutput(tensor_name=tensor_name, shape=shape)],
                attrs={},
                audit_ref=AuditRef(),
            )
        )

    # Step E: Wire inputs for compute tasks
    nig_node_by_id = {node.node_id: node for node in nig_ir.nodes}
    for task in task_nodes:
        nig_node = nig_node_by_id.get(task.task_id.replace("task.", "nig.", 1))
        if nig_node is None:
            continue
        new_inputs: list[TaskInput] = []
        for input_name in nig_node.inputs:
            resolved_tensor = _resolve_tensor_name(input_name, tensor_rewrite)
            producer = _find_non_elided_producer(
                resolved_tensor, nig_producer_by_tensor, elided_node_ids
            )
            if producer is not None:
                producer_task_id = producer.node_id.replace("nig.", "task.", 1)
                new_inputs.append(
                    TaskInput(source_task_id=producer_task_id, tensor_name=resolved_tensor)
                )
            elif resolved_tensor in input_task_id_by_tensor:
                new_inputs.append(
                    TaskInput(
                        source_task_id=input_task_id_by_tensor[resolved_tensor],
                        tensor_name=resolved_tensor,
                    )
                )
            elif resolved_tensor in constant_task_id_by_tensor:
                new_inputs.append(
                    TaskInput(
                        source_task_id=constant_task_id_by_tensor[resolved_tensor],
                        tensor_name=resolved_tensor,
                    )
                )
            # If no producer and not graph input or constant, leave unwired
        task.inputs = new_inputs

    # Order: Input tasks first, then Constant tasks, then compute tasks
    all_task_nodes = input_tasks + constant_tasks + task_nodes

    # Step F: Build output_tasks
    all_task_output_tensors = {
        output.tensor_name for task in all_task_nodes for output in task.outputs
    }
    all_task_input_tensors = {
        input.tensor_name for task in all_task_nodes for input in task.inputs
    }
    graph_output_tensors = all_task_output_tensors - all_task_input_tensors

    output_tasks: list[str] = []
    for tensor_name in graph_output_tensors:
        for task in all_task_nodes:
            if any(output.tensor_name == tensor_name for output in task.outputs):
                output_tasks.append(task.task_id)
                break

    # Step G: Assemble TaskDAG
    task_dag = TaskDAG(
        ir_version=nig_ir.ir_version,
        graph_id=nig_ir.graph_id,
        nodes=all_task_nodes,
        output_tasks=sorted(set(output_tasks)),
    )
    validate_task_dag(task_dag)
    return task_dag


def _resolve_tensor_name(tensor_name: str, tensor_rewrite: dict[str, str]) -> str:
    current = tensor_name
    while current in tensor_rewrite:
        current = tensor_rewrite[current]
    return current


def _sanitize_tensor_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", name).strip("_")


def validate_task_dag(task_dag: TaskDAG) -> None:
    """Validate DAG properties. Raises TaskDAGBuildError on failure."""
    diagnostics: list[str] = []
    task_by_id = {node.task_id: node for node in task_dag.nodes}

    # Check 1: All TaskInput.source_task_id references exist
    missing_producers: list[str] = []
    for node in task_dag.nodes:
        for task_input in node.inputs:
            if task_input.source_task_id not in task_by_id:
                missing_producers.append(
                    f"task '{node.task_id}' input '{task_input.tensor_name}' "
                    f"references missing producer '{task_input.source_task_id}'"
                )
    if missing_producers:
        diagnostics.extend(missing_producers)

    # Check 2: Graph is acyclic (Kahn's algorithm)
    edges = task_dag.edges  # maps consumer -> list of producers it depends on
    # Build reverse_edges: producer -> list of consumers that depend on it
    reverse_edges: dict[str, list[str]] = {node.task_id: [] for node in task_dag.nodes}
    for node in task_dag.nodes:
        for dep_id in edges.get(node.task_id, []):
            reverse_edges.setdefault(dep_id, []).append(node.task_id)

    # in_degree[node] = number of producers it depends on
    in_degree = {node.task_id: len(edges.get(node.task_id, [])) for node in task_dag.nodes}

    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    topo_order: list[str] = []
    while queue:
        current = queue.pop(0)
        topo_order.append(current)
        for consumer in reverse_edges.get(current, []):
            in_degree[consumer] -= 1
            if in_degree[consumer] == 0:
                queue.append(consumer)

    if len(topo_order) != len(task_dag.nodes):
        # Find cycle nodes (those with remaining in-degree > 0)
        remaining = {task_id for task_id, degree in in_degree.items() if degree > 0}
        cycle_nodes = sorted(remaining) if remaining else ["unknown"]
        diagnostics.append(
            f"task DAG contains cycle involving tasks: {', '.join(cycle_nodes)}"
        )

    # Check 3: No orphaned tasks
    # A task is orphaned if it is not reachable from any Input/Constant task
    # AND it does not produce a graph output
    reachable: set[str] = set()
    # Start from Input and Constant tasks
    seeds = [node.task_id for node in task_dag.nodes if node.macro_op in {"Input", "Constant"}]
    queue = list(seeds)
    while queue:
        current = queue.pop(0)
        if current in reachable:
            continue
        reachable.add(current)
        for consumer in reverse_edges.get(current, []):
            if consumer not in reachable:
                queue.append(consumer)

    orphaned = []
    for node in task_dag.nodes:
        if node.task_id not in reachable and node.task_id not in task_dag.output_tasks:
            orphaned.append(node.task_id)
    if orphaned:
        diagnostics.append(
            f"orphaned tasks (not reachable from inputs and not graph outputs): {', '.join(sorted(orphaned))}"
        )

    if diagnostics:
        raise TaskDAGBuildError(
            f"TaskDAG validation failed with {len(diagnostics)} issue(s)",
            diagnostics=diagnostics,
        )


def _find_non_elided_producer(
    tensor_name: str,
    nig_producer_by_tensor: dict[str, NIGNode],
    elided_node_ids: set[str],
    visited: set[str] | None = None,
) -> NIGNode | None:
    if visited is None:
        visited = set()
    if tensor_name in visited:
        return None
    visited.add(tensor_name)
    producer = nig_producer_by_tensor.get(tensor_name)
    if producer is None:
        return None
    if producer.node_id not in elided_node_ids:
        return producer
    for input_name in producer.inputs:
        if not input_name:
            continue
        result = _find_non_elided_producer(
            input_name, nig_producer_by_tensor, elided_node_ids, visited
        )
        if result is not None:
            return result
    return None
