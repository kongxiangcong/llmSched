from pathlib import Path

from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.model_structure_report import ModelStructureReport
from llm_sched.contracts.support_matrix_report import SupportMatrixReport


def test_run_diagnosis_analysis_writes_support_matrix_report_when_frontend_inputs_exist(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-support-matrix",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="frontend",
    )

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    report_path = run_root / "reports" / "diagnosis" / "support_matrix_report.json"
    assert report_path.is_file()

    report = SupportMatrixReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    model_structure_report = ModelStructureReport.model_validate_json(
        (run_root / "reports" / "diagnosis" / "model_structure_report.json").read_text(encoding="utf-8")
    )
    node_index = {entry.node_id: entry for entry in model_structure_report.node_index}
    structure_kind_by_id = {
        entry.structure_id: entry.structure_kind for entry in model_structure_report.structures
    }

    assert len(report.layer_support_summary) > 1
    assert len(report.structure_support_summary) > 1
    for entry in report.node_support_entries:
        index_entry = node_index[entry.graph_node_id]
        assert entry.layer_id == index_entry.layer_id
        assert entry.structure_id in index_entry.structure_ids
        assert entry.structure_kind == structure_kind_by_id[entry.structure_id]

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.artifact_index["support_matrix_report"] == "reports/diagnosis/support_matrix_report.json"
