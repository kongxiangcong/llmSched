from llm_sched.config.loader import Diagnostic
from llm_sched.contracts.run_summary import RunSummary


def test_run_summary_round_trips() -> None:
    summary = RunSummary(
        run_id="run-001",
        status="initialized",
        exit_code=0,
        manifest_path="manifest.json",
        diagnostics=[
            Diagnostic(
                path="profiles/targets/riscv_npu_single_core_v1.json",
                field="core_mode",
                severity="warning",
                message="example warning",
            )
        ],
    )

    restored = RunSummary.model_validate(summary.model_dump(mode="json"))

    assert restored == summary
    assert restored.diagnostics[0].severity == "warning"
