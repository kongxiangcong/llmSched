from pathlib import Path


def test_build_end_to_end_plan_for_both_modes_and_both_core_modes() -> None:
    from llm_sched.tools.end_to_end_runner import build_end_to_end_plan

    repo_root = Path("D:/workspace/llmSched")
    session_root = repo_root / ".runs" / "demo"

    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx",
        core_mode="both",
        eval_mode="both",
    )

    assert [case.run_id for case in plan.run_cases] == [
        "prefill-single-core",
        "prefill-dual-core",
        "decode-single-core",
        "decode-dual-core",
    ]
    assert [case.schedule_kind for case in plan.run_cases] == [
        "single-core",
        "dual-core",
        "single-core",
        "dual-core",
    ]
    assert [spec.sweep_name for spec in plan.sweep_specs] == [
        "prefill-single-vs-dual",
        "decode-single-vs-dual",
    ]
    assert plan.catalog_root == session_root / "catalog-root"


def test_build_end_to_end_plan_for_single_prefill_does_not_create_sweep() -> None:
    from llm_sched.tools.end_to_end_runner import build_end_to_end_plan

    repo_root = Path("D:/workspace/llmSched")
    session_root = repo_root / ".runs" / "demo"

    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx",
        core_mode="single-core",
        eval_mode="prefill",
    )

    assert [case.run_id for case in plan.run_cases] == ["prefill-single-core"]
    assert plan.sweep_specs == []


def test_resolve_selected_modes_accepts_short_aliases() -> None:
    from llm_sched.tools.end_to_end_runner import resolve_selected_core_modes, resolve_selected_eval_modes

    assert resolve_selected_core_modes("single") == ("single-core",)
    assert resolve_selected_core_modes("dual") == ("dual-core",)
    assert resolve_selected_core_modes("both") == ("single-core", "dual-core")

    assert resolve_selected_eval_modes("prefill") == ("prefill",)
    assert resolve_selected_eval_modes("decode") == ("decode",)
    assert resolve_selected_eval_modes("both") == ("prefill", "decode")


def test_build_session_root_uses_runs_directory() -> None:
    from llm_sched.tools.end_to_end_runner import build_session_root

    repo_root = Path("D:/workspace/llmSched")

    session_root = build_session_root(
        repo_root=repo_root,
        output_root=repo_root / ".runs",
        run_name="manual-demo",
    )

    assert session_root == repo_root / ".runs" / "manual-demo"


def test_build_default_run_name_uses_eval_core_model_and_timestamp() -> None:
    from datetime import datetime

    from llm_sched.tools.end_to_end_runner import build_default_run_name

    repo_root = Path("D:/workspace/llmSched")
    model_path = repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx"

    run_name = build_default_run_name(
        repo_root=repo_root,
        model_path=model_path,
        core_mode="single",
        eval_mode="prefill",
        timestamp=datetime(2026, 3, 22, 13, 21, 56),
    )

    assert run_name == "prefill_single_gemma3_1b_20260322_132156"


def test_build_session_root_uses_generated_default_name_when_run_name_is_missing() -> None:
    from datetime import datetime

    from llm_sched.tools.end_to_end_runner import build_session_root

    repo_root = Path("D:/workspace/llmSched")
    model_path = repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx"

    session_root = build_session_root(
        repo_root=repo_root,
        output_root=repo_root / ".runs",
        run_name=None,
        model_path=model_path,
        core_mode="single-core",
        eval_mode="decode",
        timestamp=datetime(2026, 3, 22, 13, 21, 56),
    )

    assert session_root == repo_root / ".runs" / "decode_single_gemma3_1b_20260322_132156"


def test_find_missing_python_modules_reports_unavailable_runtime_dependencies() -> None:
    from llm_sched.tools.end_to_end_runner import find_missing_python_modules

    missing = find_missing_python_modules(
        required_modules=("json", "definitely_missing_codex_module"),
    )

    assert missing == ("definitely_missing_codex_module",)
