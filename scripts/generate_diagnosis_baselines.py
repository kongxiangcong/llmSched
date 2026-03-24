from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate frozen diagnosis baseline fixtures under tests/fixtures/diagnosis_baseline/."
    )
    parser.add_argument(
        "--output-root",
        default="tests/fixtures/diagnosis_baseline",
        help="Directory used to store the generated baseline fixtures.",
    )
    parser.add_argument(
        "--run-root-base",
        default=".runs/diagnosis_baseline_generation",
        help="Temporary run-root directory used while generating the baselines.",
    )
    return parser


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from llm_sched.config.loader import load_target_profile
    from llm_sched.contracts.manifest import RunManifest
    from llm_sched.contracts.run_summary import RunSummary
    from llm_sched.pipeline import (
        run_decode_evaluation,
        run_descriptor_generation,
        run_diagnosis_analysis,
        run_diagnosis_packaging,
        run_diagnosis_workbench,
        run_dual_core_scheduling,
        run_frontend_analysis,
        run_memory_planning,
        run_performance_estimation,
        run_prefill_evaluation,
        run_single_core_scheduling,
        run_tile_planning,
    )
    from tests_diagnosis_baseline import (
        DEFAULT_DIAGNOSIS_BASELINE_CASE_IDS,
        normalize_diagnosis_baseline_document,
        summarize_baseline_file,
        summarize_json_payload,
    )

    parser = _build_parser()
    arguments = parser.parse_args()
    output_root = (repo_root / arguments.output_root).resolve()
    run_root_base = (repo_root / arguments.run_root_base).resolve()

    cases = (
        {
            "case_id": "single_core_prefill",
            "target_relative_path": "profiles/targets/riscv_npu_single_core_v1.json",
            "scenario_relative_path": "profiles/scenarios/prefill_seq128.json",
            "evaluation_mode": "prefill",
        },
        {
            "case_id": "single_core_decode",
            "target_relative_path": "profiles/targets/riscv_npu_single_core_v1.json",
            "scenario_relative_path": "profiles/scenarios/decode_token1_kv2048.json",
            "evaluation_mode": "decode",
        },
        {
            "case_id": "dual_core_prefill",
            "target_relative_path": "profiles/targets/riscv_npu_dual_core_v1.json",
            "scenario_relative_path": "profiles/scenarios/prefill_seq128.json",
            "evaluation_mode": "prefill",
        },
        {
            "case_id": "dual_core_decode",
            "target_relative_path": "profiles/targets/riscv_npu_dual_core_v1.json",
            "scenario_relative_path": "profiles/scenarios/decode_token1_kv2048.json",
            "evaluation_mode": "decode",
        },
    )
    if tuple(case["case_id"] for case in cases) != DEFAULT_DIAGNOSIS_BASELINE_CASE_IDS:
        raise ValueError("baseline case ids drifted from the shared default ordering")

    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    if run_root_base.exists():
        shutil.rmtree(run_root_base)
    run_root_base.mkdir(parents=True, exist_ok=True)

    baseline_index: dict[str, object] = {
        "format_version": 1,
        "generated_by": "scripts/generate_diagnosis_baselines.py",
        "comparison_policies": {
            "strict_json_files": [
                "reports/diagnosis_bundle.json",
                "diagnosis_workbench/workbench_manifest.json",
                "reports/diagnosis/model_structure_report.json",
                "reports/diagnosis/operator_representation_report.json",
                "reports/diagnosis/resource_demand_report.json",
                "reports/diagnosis/support_matrix_report.json",
                "reports/diagnosis/schedule_diagnostics_report.json",
                "reports/diagnosis/performance_diagnostics_report.json",
                "reports/diagnosis/roofline_report.json",
                "reports/diagnosis/architecture_assessment_report.json",
            ],
            "planned_relaxed_files_after_report_shrink": [
                "reports/diagnosis/model_structure_report.json",
                "reports/diagnosis/operator_representation_report.json",
                "reports/diagnosis/resource_demand_report.json",
                "reports/diagnosis/support_matrix_report.json",
                "reports/diagnosis/schedule_diagnostics_report.json",
                "reports/diagnosis/performance_diagnostics_report.json",
                "reports/diagnosis/roofline_report.json",
                "reports/diagnosis/architecture_assessment_report.json",
            ],
        },
        "normalization_placeholders": {
            "run_id": "__BASELINE_RUN_ID__",
            "run_root": "__BASELINE_RUN_ROOT__",
            "diagnosis_reports_dir": "__BASELINE_DIAGNOSIS_REPORTS_DIR__",
        },
        "cases": [],
    }

    for case_definition in cases:
        case_id = case_definition["case_id"]
        run_root = run_root_base / case_id
        if run_root.exists():
            shutil.rmtree(run_root)
        _initialize_run_root(
            run_root,
            repo_root,
            target_relative_path=case_definition["target_relative_path"],
            scenario_relative_path=case_definition["scenario_relative_path"],
            run_manifest_type=RunManifest,
            run_summary_type=RunSummary,
        )

        target_profile = load_target_profile(repo_root / case_definition["target_relative_path"])

        _run_stage(run_frontend_analysis, run_root, "frontend")
        _run_stage(run_memory_planning, run_root, "memory")
        _run_stage(run_tile_planning, run_root, "tile")
        if target_profile.core_mode == "single-core":
            _run_stage(run_single_core_scheduling, run_root, "single-core scheduling")
        else:
            _run_stage(run_dual_core_scheduling, run_root, "dual-core scheduling")
        _run_stage(run_descriptor_generation, run_root, "descriptor")
        _run_stage(run_performance_estimation, run_root, "performance")
        if case_definition["evaluation_mode"] == "prefill":
            _run_stage(run_prefill_evaluation, run_root, "prefill evaluation")
        else:
            _run_stage(run_decode_evaluation, run_root, "decode evaluation")
        _run_stage(run_diagnosis_analysis, run_root, "diagnosis analysis")
        _run_stage(run_diagnosis_packaging, run_root, "diagnosis packaging")
        _run_stage(run_diagnosis_workbench, run_root, "diagnosis workbench")

        manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
        diagnosis_report_paths = sorted((run_root / "reports" / "diagnosis").glob("*.json"))
        selected_paths = [
            *diagnosis_report_paths,
            *(run_root / "reports" / "diagnosis" / "trace").glob("*.json"),
            run_root / "reports" / "diagnosis" / "diagnosis_chain_summary.json",
            run_root / "reports" / "diagnosis" / "dataset" / "structure_inventory.csv",
            run_root / "reports" / "diagnosis" / "dataset" / "operator_mapping.csv",
            run_root / "reports" / "diagnosis" / "dataset" / "schedule_blocks.csv",
            run_root / "reports" / "diagnosis" / "dataset" / "realization_gap.csv",
            run_root / "reports" / "diagnosis" / "dataset" / "timeline_loss_summary.csv",
            run_root / "reports" / "diagnosis_bundle.json",
            run_root / "diagnosis_workbench" / "workbench_manifest.json",
        ]
        case_root = output_root / case_id
        case_root.mkdir(parents=True, exist_ok=True)

        relative_files: list[str] = []
        file_summaries: dict[str, object] = {}
        for source_path in selected_paths:
            relative_path = source_path.relative_to(run_root)
            relative_path_text = str(relative_path).replace("\\", "/")
            if source_path.suffix == ".json":
                payload = json.loads(source_path.read_text(encoding="utf-8"))
                normalized_payload = normalize_diagnosis_baseline_document(payload, run_root)
                serialized_text = json.dumps(normalized_payload, indent=2)
            else:
                normalized_payload = None
                serialized_text = source_path.read_text(encoding="utf-8")
            target_path = case_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(serialized_text, encoding="utf-8")
            relative_files.append(relative_path_text)
            file_summaries[relative_path_text] = summarize_baseline_file(target_path)

        baseline_index["cases"].append(
            {
                **case_definition,
                "schedule_kind": target_profile.core_mode,
                "relative_files": relative_files,
                "diagnosis_report_count": len(diagnosis_report_paths),
                "artifact_index_snapshot": {
                    key: manifest.artifact_index[key]
                    for key in sorted(manifest.artifact_index)
                    if key.startswith("diagnosis") or key.endswith("_report")
                },
                "file_summaries": file_summaries,
            }
        )

    (output_root / "index.json").write_text(
        json.dumps(baseline_index, indent=2),
        encoding="utf-8",
    )
    return 0


def _initialize_run_root(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
    run_manifest_type,
    run_summary_type,
) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative_path in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative_path).mkdir(parents=True, exist_ok=True)

    manifest = run_manifest_type(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
        target_profile_path=str((repo_root / target_relative_path).resolve()),
        scenario_profile_path=str((repo_root / scenario_relative_path).resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            run_summary_type(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_stage(stage_function, run_root: Path, label: str) -> None:
    result = stage_function(run_root)
    if result.status != "completed":
        raise RuntimeError(f"{label} failed for {run_root}: {result}")


if __name__ == "__main__":
    raise SystemExit(main())
