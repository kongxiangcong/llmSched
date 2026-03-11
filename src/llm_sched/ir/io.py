"""IR serialization helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


def dump_ir_document(document: BaseModel, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def load_ir_document(path: str | Path, model_type: type[T]) -> T:
    input_path = Path(path)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    return model_type.model_validate(payload)
