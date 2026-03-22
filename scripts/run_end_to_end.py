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
    )
    plan = build_end_to_end_plan(
        repo_root=repo_root,
        session_root=session_root,
        model_path=model_path,
        core_mode=args.core_mode,
        eval_mode=args.eval_mode,
    )
    result = run_end_to_end_session(plan)

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
