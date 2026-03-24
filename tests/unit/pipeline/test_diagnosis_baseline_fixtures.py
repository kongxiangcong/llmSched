import json
from pathlib import Path

from tests_diagnosis_baseline import (
    DEFAULT_DIAGNOSIS_BASELINE_CASE_IDS,
    DIAGNOSIS_REPORTS_DIR_PLACEHOLDER,
    RUN_ID_PLACEHOLDER,
    RUN_ROOT_PLACEHOLDER,
    summarize_baseline_file,
    summarize_json_payload,
)


def test_diagnosis_baseline_index_covers_all_quadrants(
    diagnosis_baseline_root: Path,
    diagnosis_baseline_index: dict[str, object],
) -> None:
    assert diagnosis_baseline_root.is_dir()
    case_ids = {case_entry["case_id"] for case_entry in diagnosis_baseline_index["cases"]}
    assert case_ids == set(DEFAULT_DIAGNOSIS_BASELINE_CASE_IDS)


def test_diagnosis_baseline_cases_are_parseable_and_summarized(
    diagnosis_baseline_case_loader,
    diagnosis_baseline_index: dict[str, object],
) -> None:
    for case_entry in diagnosis_baseline_index["cases"]:
        case_root, metadata = diagnosis_baseline_case_loader(case_entry["case_id"])
        relative_files = metadata["relative_files"]
        diagnosis_reports = [
            relative_path
            for relative_path in relative_files
            if relative_path.startswith("reports/diagnosis/") and "/trace/" not in relative_path and relative_path.endswith(".json") and relative_path.count("/") == 2
        ]

        assert len(diagnosis_reports) >= 9
        assert "reports/diagnosis_bundle.json" in relative_files
        assert "diagnosis_workbench/workbench_manifest.json" in relative_files
        assert metadata["artifact_index_snapshot"]["diagnosis_reports_dir"] == "reports/diagnosis"
        assert metadata["artifact_index_snapshot"]["diagnosis_bundle"] == "reports/diagnosis_bundle.json"
        assert (
            metadata["artifact_index_snapshot"]["diagnosis_workbench_manifest"]
            == "diagnosis_workbench/workbench_manifest.json"
        )

        for relative_path in relative_files:
            assert summarize_baseline_file(case_root / relative_path) == metadata["file_summaries"][relative_path]

        bundle_payload = json.loads(
            (case_root / "reports" / "diagnosis_bundle.json").read_text(encoding="utf-8")
        )
        workbench_payload = json.loads(
            (case_root / "diagnosis_workbench" / "workbench_manifest.json").read_text(encoding="utf-8")
        )

        assert bundle_payload["metadata"]["run_id"] == RUN_ID_PLACEHOLDER
        assert bundle_payload["metadata"]["run_root"] == RUN_ROOT_PLACEHOLDER
        assert (
            bundle_payload["metadata"]["diagnosis_reports_dir"]
            == DIAGNOSIS_REPORTS_DIR_PLACEHOLDER
        )
        assert workbench_payload["metadata"]["run_id"] == RUN_ID_PLACEHOLDER
