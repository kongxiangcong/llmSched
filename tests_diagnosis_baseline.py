from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


BASELINE_ROOT_RELATIVE = Path("tests/fixtures/diagnosis_baseline")
DEFAULT_DIAGNOSIS_BASELINE_CASE_IDS = (
    "single_core_prefill",
    "single_core_decode",
    "dual_core_prefill",
    "dual_core_decode",
)
RUN_ID_PLACEHOLDER = "__BASELINE_RUN_ID__"
RUN_ROOT_PLACEHOLDER = "__BASELINE_RUN_ROOT__"
DIAGNOSIS_REPORTS_DIR_PLACEHOLDER = "__BASELINE_DIAGNOSIS_REPORTS_DIR__"


def get_diagnosis_baseline_root(repo_root: Path) -> Path:
    return repo_root / BASELINE_ROOT_RELATIVE


def load_diagnosis_baseline_index(repo_root: Path) -> dict[str, Any]:
    return load_diagnosis_baseline_index_from_root(get_diagnosis_baseline_root(repo_root))


def load_diagnosis_baseline_index_from_root(baseline_root: Path) -> dict[str, Any]:
    return json.loads((baseline_root / "index.json").read_text(encoding="utf-8"))


def get_diagnosis_baseline_case(
    diagnosis_baseline_index: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    for case_entry in diagnosis_baseline_index["cases"]:
        if case_entry["case_id"] == case_id:
            return case_entry
    raise KeyError(f"unknown diagnosis baseline case_id: {case_id}")


def summarize_json_payload(payload: Any) -> dict[str, Any]:
    array_lengths: dict[str, int] = {}
    _collect_array_lengths(payload, "$", array_lengths)
    top_level_keys = sorted(payload.keys()) if isinstance(payload, dict) else []
    return {
        "top_level_keys": top_level_keys,
        "array_lengths": array_lengths,
    }


def normalize_diagnosis_baseline_document(payload: Any, run_root: Path) -> Any:
    run_id = run_root.name
    run_root_variants = {
        str(run_root),
        str(run_root.resolve()),
        run_root.as_posix(),
        run_root.resolve().as_posix(),
    }
    diagnosis_reports_dir = run_root / "reports" / "diagnosis"
    diagnosis_reports_dir_variants = {
        str(diagnosis_reports_dir),
        str(diagnosis_reports_dir.resolve()),
        diagnosis_reports_dir.as_posix(),
        diagnosis_reports_dir.resolve().as_posix(),
    }
    return _normalize_value(
        payload,
        run_id=run_id,
        run_root_variants=run_root_variants,
        diagnosis_reports_dir_variants=diagnosis_reports_dir_variants,
    )


def _collect_array_lengths(payload: Any, path: str, array_lengths: dict[str, int]) -> None:
    if isinstance(payload, list):
        array_lengths[path] = len(payload)
        for index, item in enumerate(payload):
            _collect_array_lengths(item, f"{path}[{index}]", array_lengths)
        return
    if isinstance(payload, dict):
        for key, value in payload.items():
            _collect_array_lengths(value, f"{path}.{key}", array_lengths)


def _normalize_value(
    payload: Any,
    *,
    run_id: str,
    run_root_variants: set[str],
    diagnosis_reports_dir_variants: set[str],
) -> Any:
    if isinstance(payload, dict):
        return {
            key: _normalize_value(
                value,
                run_id=run_id,
                run_root_variants=run_root_variants,
                diagnosis_reports_dir_variants=diagnosis_reports_dir_variants,
            )
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [
            _normalize_value(
                item,
                run_id=run_id,
                run_root_variants=run_root_variants,
                diagnosis_reports_dir_variants=diagnosis_reports_dir_variants,
            )
            for item in payload
        ]
    if isinstance(payload, str):
        if payload == run_id:
            return RUN_ID_PLACEHOLDER
        if payload in run_root_variants:
            return RUN_ROOT_PLACEHOLDER
        if payload in diagnosis_reports_dir_variants:
            return DIAGNOSIS_REPORTS_DIR_PLACEHOLDER
        return payload.replace(run_id, RUN_ID_PLACEHOLDER)
    return payload


def summarize_baseline_file(path: Path) -> dict[str, Any]:
    if path.suffix == ".json":
        return summarize_json_payload(json.loads(path.read_text(encoding="utf-8")))
    if path.suffix == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
            header = list(rows[0].keys()) if rows else next(csv.reader([path.read_text(encoding="utf-8").splitlines()[0]]), []) if path.read_text(encoding="utf-8").splitlines() else []
        return {"header": header, "row_count": len(rows)}
    raise ValueError(f"unsupported baseline file type: {path}")
