"""Profile loading helpers and diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from llm_sched.config.scenario_profile import ScenarioProfile
from llm_sched.config.target_profile import TargetProfile


class Diagnostic(BaseModel):
    path: str
    field: str
    severity: Literal["error", "warning"]
    message: str


class ProfileLoadError(Exception):
    """Base exception for profile loading failures."""

    def __init__(self, message: str, diagnostics: list[Diagnostic]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class MalformedProfileError(ProfileLoadError):
    """Raised when JSON parsing fails."""


class ProfileValidationFailure(ProfileLoadError):
    """Raised when schema validation fails."""


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MalformedProfileError(
            message=f"Malformed JSON in profile: {path}",
            diagnostics=[
                Diagnostic(
                    path=str(path),
                    field="json",
                    severity="error",
                    message=str(exc),
                )
            ],
        ) from exc


def _validate_payload(path: Path, model_type: type[BaseModel]) -> BaseModel:
    payload = _read_json(path)
    try:
        return model_type.model_validate(payload)
    except ValidationError as exc:
        diagnostics = [
            Diagnostic(
                path=str(path),
                field=".".join(str(part) for part in error["loc"]) or "__root__",
                severity="error",
                message=error["msg"],
            )
            for error in exc.errors()
        ]
        raise ProfileValidationFailure(
            message=f"Profile validation failed: {path}",
            diagnostics=diagnostics,
        ) from exc


def load_target_profile(path: str | Path) -> TargetProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        raise FileNotFoundError(profile_path)
    return _validate_payload(profile_path, TargetProfile)


def load_scenario_profile(path: str | Path) -> ScenarioProfile:
    profile_path = Path(path)
    if not profile_path.exists():
        raise FileNotFoundError(profile_path)
    return _validate_payload(profile_path, ScenarioProfile)
