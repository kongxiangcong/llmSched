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


def test_run_end_to_end_session_emits_progress_events(monkeypatch, tmp_path) -> None:
    from llm_sched.tools.end_to_end_runner import CatalogExecutionResult
    from llm_sched.tools.end_to_end_runner import CommandResult
    from llm_sched.tools.end_to_end_runner import RunExecutionResult
    from llm_sched.tools.end_to_end_runner import SweepExecutionResult
    from llm_sched.tools.end_to_end_runner import SweepSpecConfig
    from llm_sched.tools.end_to_end_runner import build_end_to_end_plan
    from llm_sched.tools.end_to_end_runner import run_end_to_end_session

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    model_path = repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("fake", encoding="utf-8")
    for rel_path in (
        "profiles/targets/riscv_npu_single_core_v1.json",
        "profiles/targets/riscv_npu_dual_core_v1.json",
        "profiles/scenarios/prefill_seq128.json",
        "profiles/scenarios/decode_token1_kv2048.json",
    ):
        path = repo_root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=repo_root / ".runs" / "demo",
        model_path=model_path,
        core_mode="both",
        eval_mode="prefill",
    )

    def _command_result(label: str) -> CommandResult:
        return CommandResult(
            label=label,
            command=(label,),
            returncode=0,
            stdout_log_path=repo_root / f"{label}.stdout.log",
            stderr_log_path=repo_root / f"{label}.stderr.log",
        )

    def fake_execute_run_case(
        repo_root_arg,
        model_path_arg,
        run_case,
        *,
        progress_callback=None,
        stage_offset=0,
        total_stage_count=None,
    ):
        return RunExecutionResult(
            run_case=run_case,
            status="completed",
            command_results=[_command_result(f"run-{run_case.run_id}")],
        )

    def fake_execute_sweep(
        repo_root_arg,
        model_path_arg,
        sweep_spec: SweepSpecConfig,
        *,
        progress_callback=None,
        stage_offset=0,
        total_stage_count=None,
    ):
        return SweepExecutionResult(
            sweep_spec=sweep_spec,
            status="completed",
            command_results=[_command_result(f"sweep-{sweep_spec.sweep_name}")],
        )

    def fake_execute_visualization(
        repo_root_arg,
        run_root,
        *,
        sweep_root,
        progress_callback=None,
        run_id=None,
        stage_offset=0,
        total_stage_count=None,
    ):
        from llm_sched.tools.end_to_end_runner import _VisualizationResult

        return _VisualizationResult(
            status="completed",
            command_results=[_command_result(f"viz-{run_root.name}")],
        )

    def fake_execute_catalog(
        repo_root_arg,
        catalog_root,
        run_roots,
        *,
        progress_callback=None,
        stage_offset=0,
        total_stage_count=None,
    ):
        return CatalogExecutionResult(
            status="completed",
            command_results=[_command_result("catalog")],
            reason=None,
        )

    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._execute_run_case", fake_execute_run_case)
    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._execute_sweep", fake_execute_sweep)
    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._execute_visualization", fake_execute_visualization)
    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._execute_catalog", fake_execute_catalog)

    events: list[dict[str, object]] = []
    run_end_to_end_session(plan, progress_callback=events.append)

    event_names = [event["event"] for event in events]
    assert event_names == [
        "session_started",
        "run_started",
        "run_completed",
        "run_started",
        "run_completed",
        "sweep_started",
        "sweep_completed",
        "visualization_started",
        "visualization_completed",
        "visualization_started",
        "visualization_completed",
        "catalog_started",
        "catalog_completed",
        "session_completed",
    ]
    assert events[0]["run_case_count"] == 2
    assert events[0]["sweep_count"] == 1
    assert events[0]["total_stage_count"] == 27
    assert events[-1]["successful_run_count"] == 2
    assert events[-1]["completed_sweep_count"] == 1


def test_execute_run_case_emits_stage_progress_events(monkeypatch, tmp_path) -> None:
    from llm_sched.tools.end_to_end_runner import RunCase
    from llm_sched.tools.end_to_end_runner import _execute_run_case

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    model_path = repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("fake", encoding="utf-8")

    run_case = RunCase(
        run_id="prefill-single-core",
        run_root=repo_root / ".runs" / "demo" / "runs" / "prefill-single-core",
        eval_mode="prefill",
        schedule_kind="single-core",
        target_profile_path=repo_root / "profiles/targets/riscv_npu_single_core_v1.json",
        scenario_profile_path=repo_root / "profiles/scenarios/prefill_seq128.json",
    )

    def fake_run_cli(repo_root_arg, command, *, log_root, label):
        from llm_sched.tools.end_to_end_runner import CommandResult

        return CommandResult(
            label=label,
            command=command,
            returncode=0,
            stdout_log_path=log_root / f"{label}.stdout.log",
            stderr_log_path=log_root / f"{label}.stderr.log",
        )

    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._run_cli", fake_run_cli)

    events: list[dict[str, object]] = []
    result = _execute_run_case(
        repo_root,
        model_path,
        run_case,
        progress_callback=events.append,
    )

    assert result.status == "completed"
    assert [event["event"] for event in events] == [
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
        "run_stage_started",
        "run_stage_completed",
    ]
    assert [event["stage_label"] for event in events[::2]] == [
        "validate-profile",
        "init-run",
        "frontend-analysis",
        "memory-planning",
        "memory-planner-closure",
        "tile-planning",
        "scheduling",
        "descriptor-generation",
        "performance-estimation",
        "evaluation",
    ]
    assert [event["stage_index"] for event in events[::2]] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert all(event["stage_count"] == 10 for event in events)
    assert all(event["run_id"] == "prefill-single-core" for event in events)


def test_execute_decode_run_case_uses_full_decode_chain(monkeypatch, tmp_path) -> None:
    from llm_sched.tools.end_to_end_runner import RunCase
    from llm_sched.tools.end_to_end_runner import _execute_run_case

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    model_path = repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx"
    model_path.parent.mkdir(parents=True)
    model_path.write_text("fake", encoding="utf-8")

    run_case = RunCase(
        run_id="decode-single-core",
        run_root=repo_root / ".runs" / "demo" / "runs" / "decode-single-core",
        eval_mode="decode",
        schedule_kind="single-core",
        target_profile_path=repo_root / "profiles/targets/riscv_npu_single_core_v1.json",
        scenario_profile_path=repo_root / "profiles/scenarios/decode_token1_kv2048.json",
    )

    seen_commands: list[tuple[str, tuple[str, ...]]] = []

    def fake_run_cli(repo_root_arg, command, *, log_root, label):
        from llm_sched.tools.end_to_end_runner import CommandResult

        seen_commands.append((label, command))
        return CommandResult(
            label=label,
            command=command,
            returncode=0,
            stdout_log_path=log_root / f"{label}.stdout.log",
            stderr_log_path=log_root / f"{label}.stderr.log",
        )

    monkeypatch.setattr("llm_sched.tools.end_to_end_runner._run_cli", fake_run_cli)

    result = _execute_run_case(
        repo_root,
        model_path,
        run_case,
    )

    assert result.status == "completed"
    assert [label for label, _ in seen_commands] == [
        "validate-profile",
        "init-run",
        "frontend-analysis",
        "memory-planning",
        "memory-planner-closure",
        "tile-planning",
        "scheduling",
        "descriptor-generation",
        "performance-estimation",
        "evaluation",
    ]
    assert seen_commands[-1][1][0] == "run-decode-evaluation"


def test_estimate_total_stage_count_for_single_decode_session_includes_full_chain() -> None:
    from llm_sched.tools.end_to_end_runner import _estimate_total_stage_count
    from llm_sched.tools.end_to_end_runner import build_end_to_end_plan

    repo_root = Path("D:/workspace/llmSched")
    session_root = repo_root / ".runs" / "demo"

    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx",
        core_mode="single-core",
        eval_mode="decode",
    )

    assert _estimate_total_stage_count(plan) == 13
