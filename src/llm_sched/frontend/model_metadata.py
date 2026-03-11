"""Model metadata helpers for frontend binding."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class GemmaModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hidden_size: int
    head_dim: int
    num_attention_heads: int
    num_hidden_layers: int
    num_key_value_heads: int


def load_gemma_model_metadata(path: str | Path) -> GemmaModelMetadata:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return GemmaModelMetadata.model_validate(
        {
            "hidden_size": payload["hidden_size"],
            "head_dim": payload["head_dim"],
            "num_attention_heads": payload["num_attention_heads"],
            "num_hidden_layers": payload["num_hidden_layers"],
            "num_key_value_heads": payload["num_key_value_heads"],
        }
    )
