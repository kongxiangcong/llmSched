import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from llm_sched.contracts.frontend_binding_report import FrontendBindingReport
from llm_sched.ir.io import load_ir_document
from llm_sched.ir.nig import NIGIR


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(cwd / "src")
        if not existing_pythonpath
        else os.pathsep.join([str(cwd / "src"), existing_pythonpath])
    )
    return subprocess.run(
        [sys.executable, "-m", "llm_sched.cli.main", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("target_profile", "scenario_profile", "minimum_binding_coverage"),
    [
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            0.78,
            id="single-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_single_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            0.77,
            id="single-core-decode",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/prefill_seq128.json",
            0.78,
            id="dual-core-prefill",
        ),
        pytest.param(
            "profiles/targets/riscv_npu_dual_core_v1.json",
            "profiles/scenarios/decode_token1_kv2048.json",
            0.77,
            id="dual-core-decode",
        ),
    ],
)
def test_phase_b_closure_matrix(
    tmp_path: Path,
    target_profile: str,
    scenario_profile: str,
    minimum_binding_coverage: float,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    run_root = tmp_path / f"{Path(target_profile).stem}-{Path(scenario_profile).stem}"

    init_result = run_cli(
        "init-run",
        "--run-root",
        str(run_root),
        "--model-path",
        "models/gemma3_1b/model_q4f16.onnx",
        "--target-profile",
        target_profile,
        "--scenario-profile",
        scenario_profile,
        cwd=repo_root,
    )
    assert init_result.returncode == 0

    run_result = run_cli(
        "run-frontend-analysis",
        "--run-root",
        str(run_root),
        cwd=repo_root,
    )
    assert run_result.returncode == 0

    import_report = json.loads((run_root / "reports" / "frontend_import_report.json").read_text(encoding="utf-8"))
    decomposition_report = json.loads(
        (run_root / "reports" / "workload_decomposition_report.json").read_text(encoding="utf-8")
    )
    legality_report = json.loads((run_root / "reports" / "frontend_legality.json").read_text(encoding="utf-8"))
    pseudo_report = json.loads((run_root / "reports" / "pseudo_fallback_summary.json").read_text(encoding="utf-8"))
    binding_report = FrontendBindingReport.model_validate(
        json.loads((run_root / "reports" / "frontend_binding_report.json").read_text(encoding="utf-8"))
    )
    bound_nig_ir = load_ir_document(run_root / "dumps" / "bound_nig_ir.json", NIGIR)

    assert import_report["raw_node_total"] > 0
    assert import_report["canonical_node_total"] > 0
    assert decomposition_report["unmapped_node_ids"] == []
    assert decomposition_report["macro_op_counts"]["WDQ_GEMM"] > 0
    assert bound_nig_ir.binding_state == "bound"
    assert legality_report["issue_counts"].get("dynamic_shape_unresolved", 0) == 0
    assert legality_report["issue_counts"]["no_hardware_mapping"] > 0
    assert legality_report["issue_counts"]["kv_cache_dtype_mismatch"] > 0
    assert legality_report["issue_counts"]["target_quant_activation_dtype_gap"] > 0
    assert legality_report["issue_counts"]["target_quant_group_size_gap"] > 0
    assert pseudo_report["record_counts"]["ATTENTION_MASK_PREP"] > 0
    assert pseudo_report["record_counts"]["SHAPE_HELPER"] > 0
    assert pseudo_report["record_counts"]["LAYOUT_FALLBACK"] > 0
    assert all(not key.startswith("target_") for key in pseudo_report["record_counts"])
    assert "SHAPE_HELPER" not in legality_report["issue_counts"]
    assert binding_report.binding_coverage_ratio >= minimum_binding_coverage
