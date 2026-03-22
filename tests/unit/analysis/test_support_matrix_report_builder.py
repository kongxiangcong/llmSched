from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.frontend_analysis_report import FrontendLegalityReport
from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.contracts.operator_representation_report import OperatorRepresentationReport
from llm_sched.contracts.support_matrix_report import SupportMatrixReport
from llm_sched.frontend.legality import FrontendLegalityIssue


def test_build_support_matrix_report_joins_real_structure_and_layer_provenance() -> None:
    from llm_sched.analysis.support_matrix_report_builder import build_support_matrix_report

    report = build_support_matrix_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        legality_report=_legality_report(),
        binding_report=_binding_report(),
        model_structure_report=_model_structure_report(),
        operator_representation_report=_operator_representation_report(),
    )

    assert report.graph_id == "graph::gemma3-prefill"
    assert [entry.support_status for entry in report.node_support_entries] == [
        "native",
        "fallback",
        "constrained",
    ]
    assert [entry.layer_id for entry in report.node_support_entries] == [3, 3, 7]
    assert [entry.structure_id for entry in report.node_support_entries] == [
        "structure.layer3.attention_block",
        "structure.layer3.rope_block",
        "structure.layer7.kv_cache_block",
    ]
    assert [entry.structure_kind for entry in report.node_support_entries] == [
        "attention_block",
        "rope_block",
        "kv_cache_block",
    ]
    assert [entry.phase for entry in report.node_support_entries] == ["projection", "attention", "kv_io"]
    assert [entry.canonical_op for entry in report.node_support_entries] == ["MatMul", "RoPE", "KVLoad"]
    assert [entry.fallback_kind for entry in report.node_support_entries] == ["none", "helper", "none"]
    assert report.node_support_entries[1].binding_issue_ids == []
    assert report.node_support_entries[1].legality_rule_ids == ["no_hardware_mapping"]
    assert report.node_support_entries[2].binding_issue_ids == ["attention_binding_missing"]
    assert report.node_support_entries[2].legality_rule_ids == []
    assert [(summary.layer_id, summary.node_count) for summary in report.layer_support_summary] == [
        (3, 2),
        (7, 1),
    ]
    assert report.layer_support_summary[0].support_status == "fallback"
    assert report.layer_support_summary[0].fallback_count == 1
    assert [(summary.structure_id, summary.node_count) for summary in report.structure_support_summary] == [
        ("structure.layer3.attention_block", 1),
        ("structure.layer3.rope_block", 1),
        ("structure.layer7.kv_cache_block", 1),
    ]
    assert report.structure_support_summary[1].support_status == "fallback"
    assert report.reason_counts == {
        "helper_only_lowering": 1,
        "binding_issue:attention_binding_missing": 1,
        "no_hardware_mapping": 1,
    }
    assert report.critical_gaps[0].reason_code == "helper_only_lowering"
    assert report.critical_gaps[1].reason_code == "no_hardware_mapping"
    assert report.critical_gaps[2].support_status == "constrained"


def test_build_support_matrix_report_tolerates_cached_frontend_report_run_ids() -> None:
    from llm_sched.analysis.support_matrix_report_builder import build_support_matrix_report

    legality_report = _legality_report().model_copy(update={"run_id": "run-other"}, deep=True)
    binding_report = _binding_report().model_copy(update={"run_id": "run-other"}, deep=True)

    report = build_support_matrix_report(
        run_id="run-diagnosis-001",
        scenario_name="prefill_seq128",
        legality_report=legality_report,
        binding_report=binding_report,
        model_structure_report=_model_structure_report(),
        operator_representation_report=_operator_representation_report(),
    )

    assert report.run_id == "run-diagnosis-001"


def _legality_report() -> FrontendLegalityReport:
    return FrontendLegalityReport(
        run_id="run-diagnosis-001",
        issue_counts={"no_hardware_mapping": 1},
        issues=[
            FrontendLegalityIssue(
                rule_id="no_hardware_mapping",
                message="node 'ROPETable' is modeled explicitly but still requires a non-native fallback surface",
                node_id="graph.node.rope",
            )
        ],
    )


def _binding_report() -> FrontendBindingReport:
    return FrontendBindingReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "node_count": 3,
            "fully_bound_node_count": 2,
            "binding_coverage_ratio": 2 / 3,
            "issue_counts": {"attention_binding_missing": 1},
            "missing_field_counts": {"attention": 1},
            "macro_summaries": {},
            "issues": [
                {
                    "issue_id": "attention_binding_missing",
                    "message": "attention-path node is missing bound attention payload",
                    "node_id": "nig.node.kvload.0",
                    "macro_op": "KVLOAD",
                    "severity": "error",
                }
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
                    "schedule_block_ids": [],
                    "descriptor_ids": [],
                    "fallback_kind": "helper",
                    "helper_surface": True,
                },
                {
                    "graph_node_id": "graph.node.kvload",
                    "canonical_op": "KVLoad",
                    "macro_op": "KVLOAD",
                    "phase": "kv_io",
                    "normalized_node_id": "nig.node.kvload.0",
                    "schedule_block_ids": ["sched.block.nig.node.kvload.0"],
                    "descriptor_ids": ["desc.nig.node.kvload.0"],
                    "fallback_kind": None,
                    "helper_surface": False,
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


def _model_structure_report() -> ModelStructureReport:
    return ModelStructureReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "model_summary": {
                "model_name": "gemma3_1b",
                "total_layers": 2,
                "total_structures": 3,
                "total_nodes": 3,
                "structure_type_counts": {
                    "attention_block": 1,
                    "rope_block": 1,
                    "kv_cache_block": 1,
                },
            },
            "structures": [
                {
                    "structure_id": "structure.layer3.attention_block",
                    "structure_name": "layer3_attention_block",
                    "structure_kind": "attention_block",
                    "hierarchy_path": ["model", "layer.3", "attention_block"],
                    "layer_id": 3,
                    "node_ids": ["graph.node.q_proj"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
                {
                    "structure_id": "structure.layer3.rope_block",
                    "structure_name": "layer3_rope_block",
                    "structure_kind": "rope_block",
                    "hierarchy_path": ["model", "layer.3", "rope_block"],
                    "layer_id": 3,
                    "node_ids": ["graph.node.rope"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
                {
                    "structure_id": "structure.layer7.kv_cache_block",
                    "structure_name": "layer7_kv_cache_block",
                    "structure_kind": "kv_cache_block",
                    "hierarchy_path": ["model", "layer.7", "kv_cache_block"],
                    "layer_id": 7,
                    "node_ids": ["graph.node.kvload"],
                    "input_ports": [],
                    "output_ports": [],
                    "attributes": {},
                },
            ],
            "layers": [
                {
                    "layer_id": 3,
                    "layer_name": "layer.3",
                    "structure_ids": [
                        "structure.layer3.attention_block",
                        "structure.layer3.rope_block",
                    ],
                    "node_ids": ["graph.node.q_proj", "graph.node.rope"],
                    "structure_kinds": ["attention_block", "rope_block"],
                },
                {
                    "layer_id": 7,
                    "layer_name": "layer.7",
                    "structure_ids": ["structure.layer7.kv_cache_block"],
                    "node_ids": ["graph.node.kvload"],
                    "structure_kinds": ["kv_cache_block"],
                },
            ],
            "node_index": [
                {
                    "node_id": "graph.node.q_proj",
                    "layer_id": 3,
                    "structure_ids": ["structure.layer3.attention_block"],
                    "node_name": "q_proj",
                },
                {
                    "node_id": "graph.node.rope",
                    "layer_id": 3,
                    "structure_ids": ["structure.layer3.rope_block"],
                    "node_name": "rope",
                },
                {
                    "node_id": "graph.node.kvload",
                    "layer_id": 7,
                    "structure_ids": ["structure.layer7.kv_cache_block"],
                    "node_name": "kvload",
                },
            ],
        }
    )
