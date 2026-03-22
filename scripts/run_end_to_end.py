from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full llm_sched CLI pipeline end-to-end and save outputs under .runs/."
    )
    parser.add_argument("--model-path", required=True, help="Path to the ONNX model file.")
    parser.add_argument(
        "--core-mode",
        default="both",
        choices=["single", "single-core", "dual", "dual-core", "both"],
        help="Select single-core, dual-core, or both.",
    )
    parser.add_argument(
        "--eval-mode",
        default="both",
        choices=["prefill", "decode", "both"],
        help="Select prefill, decode, or both.",
    )
    parser.add_argument(
        "--output-root",
        default=".runs",
        help="Directory used to store end-to-end session outputs.",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Optional fixed session directory name under the output root.",
    )
    return parser


def _format_progress_event(event: dict[str, object]) -> str | None:
    event_name = str(event.get("event", ""))
    if event_name == "session_started":
        return (
            f"[progress] session started: total stages={event['total_stage_count']}, "
            f"{event['run_case_count']} run(s), {event['sweep_count']} sweep(s), "
            f"output={event['session_root']}"
        )
    if event_name == "run_started":
        return (
            f"[progress] run {event['index']}/{event['total']} queued at stage "
            f"{event['stage_index']}/{event['total_stage_count']}: "
            f"{event['run_id']} ({event['eval_mode']}, {event['schedule_kind']})"
        )
    if event_name == "run_completed":
        suffix = ""
        if event.get("failed_command_label"):
            suffix = f", failed_command={event['failed_command_label']}"
        return (
            f"[progress] run {event['index']}/{event['total']} completed by stage "
            f"{event['stage_index']}/{event['total_stage_count']}: "
            f"{event['run_id']} status={event['status']}{suffix}"
        )
    if event_name == "run_stage_started":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(run step {event['stage_index']}/{event['stage_count']}) started: "
            f"{event['run_id']} -> {event['stage_label']}"
        )
    if event_name == "run_stage_completed":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(run step {event['stage_index']}/{event['stage_count']}) completed: {event['run_id']} -> "
            f"{event['stage_label']} returncode={event['returncode']}"
        )
    if event_name == "sweep_started":
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(sweep {event['index']}/{event['total']}) started: {event['sweep_name']}"
        )
    if event_name == "sweep_completed":
        suffix = ""
        if event.get("reason"):
            suffix = f", reason={event['reason']}"
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(sweep {event['index']}/{event['total']}) completed: "
            f"{event['sweep_name']} status={event['status']}{suffix}"
        )
    if event_name == "sweep_stage_started":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(sweep step {event['stage_index']}/{event['stage_count']}) started: "
            f"{event['sweep_name']} -> {event['stage_label']}"
        )
    if event_name == "sweep_stage_completed":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(sweep step {event['stage_index']}/{event['stage_count']}) completed: {event['sweep_name']} -> "
            f"{event['stage_label']} returncode={event['returncode']}"
        )
    if event_name == "visualization_started":
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(visualization {event['index']}/{event['total']}) started: {event['run_id']}"
        )
    if event_name == "visualization_completed":
        suffix = ""
        if event.get("failed_command_label"):
            suffix = f", failed_command={event['failed_command_label']}"
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(visualization {event['index']}/{event['total']}) completed: "
            f"{event['run_id']} status={event['status']}{suffix}"
        )
    if event_name == "visualization_stage_started":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(visualization step {event['stage_index']}/{event['stage_count']}) started: "
            f"{event['run_id']} -> {event['stage_label']}"
        )
    if event_name == "visualization_stage_completed":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(visualization step {event['stage_index']}/{event['stage_count']}) completed: {event['run_id']} -> "
            f"{event['stage_label']} returncode={event['returncode']}"
        )
    if event_name == "catalog_started":
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(catalog) started: {event['run_root_count']} run root(s), "
            f"output={event['catalog_root']}"
        )
    if event_name == "catalog_completed":
        suffix = ""
        if event.get("reason"):
            suffix = f", reason={event['reason']}"
        return (
            f"[progress] stage {event['stage_index']}/{event['total_stage_count']} "
            f"(catalog) completed: status={event['status']}{suffix}"
        )
    if event_name == "catalog_stage_started":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(catalog step {event['stage_index']}/{event['stage_count']}) started: {event['stage_label']}"
        )
    if event_name == "catalog_stage_completed":
        return (
            f"[progress] stage {event['overall_stage_index']}/{event['total_stage_count']} "
            f"(catalog step {event['stage_index']}/{event['stage_count']}) completed: "
            f"{event['stage_label']} returncode={event['returncode']}"
        )
    if event_name == "session_completed":
        return (
            f"[progress] session completed: successful_runs={event['successful_run_count']}, "
            f"failed_runs={event['failed_run_count']}, completed_sweeps={event['completed_sweep_count']}, "
            f"catalog={event['catalog_status']}, summary={event['summary_path']}"
        )
    return None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from llm_sched.tools.end_to_end_runner import build_end_to_end_plan
    from llm_sched.tools.end_to_end_runner import build_session_root
    from llm_sched.tools.end_to_end_runner import find_missing_python_modules
    from llm_sched.tools.end_to_end_runner import run_end_to_end_session

    args = _build_parser().parse_args()
    output_root = Path(args.output_root)
    model_path = Path(args.model_path)
    if not model_path.is_absolute():
        model_path = repo_root / model_path
    model_path = model_path.resolve()
    missing_modules = find_missing_python_modules(
        required_modules=("typer", "pydantic", "onnx"),
    )
    if missing_modules:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": "missing_python_dependencies",
                    "missing_modules": list(missing_modules),
                    "hint": "Install project runtime dependencies before running the end-to-end script.",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    if not model_path.is_file():
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": "model_not_found",
                    "model_path": str(model_path),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2
    session_root = build_session_root(
        repo_root=repo_root,
        output_root=output_root,
        run_name=args.run_name,
        model_path=model_path,
        core_mode=args.core_mode,
        eval_mode=args.eval_mode,
    )
    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=model_path,
        core_mode=args.core_mode,
        eval_mode=args.eval_mode,
    )
    result = run_end_to_end_session(
        plan,
        progress_callback=lambda event: (
            print(message) if (message := _format_progress_event(event)) is not None else None
        ),
    )

    summary = {
        "session_root": str(result.plan.session_root),
        "summary_path": str(result.summary_path),
        "successful_runs": [result.run_case.run_id for result in result.run_results if result.status == "completed"],
        "failed_runs": [result.run_case.run_id for result in result.run_results if result.status != "completed"],
        "completed_sweeps": [result.sweep_spec.sweep_name for result in result.sweep_results if result.status == "completed"],
        "catalog_status": result.catalog_result.status,
    }
    print(json.dumps(summary, indent=2))
    has_failures = any(result.status != "completed" for result in result.run_results)
    if result.catalog_result.status == "failed":
        has_failures = True
    return 1 if has_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
