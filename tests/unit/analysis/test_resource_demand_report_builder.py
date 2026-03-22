from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport


def test_build_resource_demand_report_aggregates_node_layer_and_structure_demands() -> None:
    from llm_sched.analysis.resource_demand_report_builder import build_resource_demand_report

    report = build_resource_demand_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        model_structure_report=_model_structure_report(),
        operator_representation_report=_operator_representation_report(),
        memory_plan=_memory_plan(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert [demand.subject_id for demand in report.node_demands] == [
        "nig.node.q_proj.0",
        "nig.node.rope.0",
    ]
    assert report.node_demands[0].compute_ops == 1.0 * 128 * 2048
    assert report.node_demands[0].read_bytes == 131072.0
    assert report.node_demands[0].write_bytes == 32768.0
    assert report.node_demands[0].working_set_bytes == 65536.0
    assert report.node_demands[1].compute_ops == 0.0
    assert report.layer_demands[0].node_count == 2
    assert report.layer_demands[0].structure_ids == ["structure.layer0.attention_block"]
    assert report.structure_demands[0].structure_kind == "attention_block"
    assert report.totals.compute_ops == report.node_demands[0].compute_ops + report.node_demands[1].compute_ops
    assert report.totals.structure_count == 1
    assert report.assumptions[0].assumption_id == "approx.compute_ops.from_shape_volume"


def test_build_resource_demand_report_rejects_graph_id_mismatch() -> None:
    from llm_sched.analysis.resource_demand_report_builder import build_resource_demand_report

    memory_plan = _memory_plan().model_copy(update={"graph_id": "graph::other"}, deep=True)

    try:
        build_resource_demand_report(
            run_id="run-diagnosis-001",
            scenario_name="prefill_seq128",
            model_structure_report=_model_structure_report(),
            operator_representation_report=_operator_representation_report(),
            memory_plan=memory_plan,
        )
    except ValueError as exc:
        assert "graph_id" in str(exc)
    else:
        raise AssertionError("expected graph_id mismatch to fail")


def _model_structure_report() -> ModelStructureReport:
    return ModelStructureReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "model_summary": {
                "model_name": "gemma3_1b",
                "total_layers": 1,
                "total_structures": 1,
                "total_nodes": 2,
                "structure_type_counts": {"attention_block": 1},
            },
            "structures": [
                {
                    "structure_id": "structure.layer0.attention_block",
                    "structure_name": "layer0_attention_block",
                    "structure_kind": "attention_block",
                    "hierarchy_path": ["model", "layer.0", "attention_block"],
                    "layer_id": 0,
                    "node_ids": ["graph.node.q_proj", "graph.node.rope"],
                    "input_ports": [
                        {
                            "tensor_name": "hidden_states",
                            "shape": [1, 128, 2048],
                            "dtype": "bf16",
                        }
                    ],
                    "output_ports": [
                        {
                            "tensor_name": "attn_out",
                            "shape": [1, 128, 2048],
                            "dtype": "bf16",
                        }
                    ],
                    "attributes": {},
                }
            ],
            "layers": [
                {
                    "layer_id": 0,
                    "layer_name": "layer.0",
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_ids": ["graph.node.q_proj", "graph.node.rope"],
                    "structure_kinds": ["attention_block"],
                }
            ],
            "node_index": [
                {
                    "node_id": "graph.node.q_proj",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_name": "q_proj",
                },
                {
                    "node_id": "graph.node.rope",
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_name": "rope",
                },
            ],
        }
    )


def _operator_representation_report() -> OperatorRepresentationReport:
    return OperatorRepresentationReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "node_mappings": [
                {
                    "graph_node_id": "graph.node.q_proj",
                    "canonical_op": "MatMul",
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "normalized_node_id": "nig.node.q_proj.0",
                    "schedule_block_ids": ["sched.block.nig.node.q_proj.0"],
                    "descriptor_ids": ["desc.nig.node.q_proj.0"],
                    "fallback_kind": None,
                    "helper_surface": False,
                },
                {
                    "graph_node_id": "graph.node.rope",
                    "canonical_op": "RoPE",
                    "macro_op": "ROPE",
                    "phase": "attention",
                    "normalized_node_id": "nig.node.rope.0",
                    "schedule_block_ids": ["sched.block.nig.node.rope.0"],
                    "descriptor_ids": [],
                    "fallback_kind": "helper",
                    "helper_surface": True,
                },
            ],
            "macro_groups": [],
            "phase_groups": [],
            "fallback_entries": [
                {
                    "graph_node_id": "graph.node.rope",
                    "normalized_node_id": "nig.node.rope.0",
                    "macro_op": "ROPE",
                    "phase": "attention",
                    "fallback_kind": "helper",
                    "reason": "helper-only lowering",
                }
            ],
            "traceability_index": [],
        }
    )


def _memory_plan() -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "core_mode": "single-core",
            "allocations": [
                {
                    "allocation_id": "alloc.q_proj.out",
                    "node_id": "nig.node.q_proj.0",
                    "tensor_name": "q_out",
                    "tensor_role": "output",
                    "lifetime_bucket": "compute",
                    "backing_store": "vmem-local",
                    "memory_class": "ACTIVATION",
                    "address_space": "VMEM",
                    "region_name": "ping",
                    "offset_bytes": 0,
                    "size_bytes": 32768,
                    "alignment_bytes": 64,
                },
                {
                    "allocation_id": "alloc.q_proj.temp",
                    "node_id": "nig.node.q_proj.0",
                    "tensor_name": "q_tmp",
                    "tensor_role": "temp",
                    "lifetime_bucket": "compute",
                    "backing_store": "vmem-local",
                    "memory_class": "ACTIVATION",
                    "address_space": "VMEM",
                    "region_name": "ping",
                    "offset_bytes": 32768,
                    "size_bytes": 32768,
                    "alignment_bytes": 64,
                },
                {
                    "allocation_id": "alloc.rope.out",
                    "node_id": "nig.node.rope.0",
                    "tensor_name": "rope_out",
                    "tensor_role": "output",
                    "lifetime_bucket": "compute",
                    "backing_store": "vmem-local",
                    "memory_class": "ACTIVATION",
                    "address_space": "VMEM",
                    "region_name": "ping",
                    "offset_bytes": 65536,
                    "size_bytes": 16384,
                    "alignment_bytes": 64,
                },
            ],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 131072,
                    "peak_bytes": 65536,
                    "peak_lifetime_bucket": "compute",
                    "peak_bytes_by_lifetime_bucket": {"compute": 65536},
                    "peak_bytes_by_memory_class": {"ACTIVATION": 65536},
                    "peak_bytes_by_backing_store": {"vmem-local": 65536},
                    "fits": True,
                    "allocation_ids": ["alloc.q_proj.out", "alloc.q_proj.temp", "alloc.rope.out"],
                }
            },
            "kv_formulas": [],
            "diagnostics": [],
            "address_diagnostics": [],
        }
    )
