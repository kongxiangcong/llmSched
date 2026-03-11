import pytest
from pydantic import ValidationError

from llm_sched.ir.validators import validate_analysis_ir


def test_analysis_ir_rejects_duplicate_record_ids() -> None:
    with pytest.raises(ValidationError) as exc_info:
        validate_analysis_ir(
            {
                "ir_version": "phase-a.v1",
                "graph_id": "analysis-001",
                "records": [
                    {
                        "record_id": "analysis.record.0",
                        "subject_id": "desc.0",
                        "metrics": {"cycles": 1.0},
                        "tags": [],
                    },
                    {
                        "record_id": "analysis.record.0",
                        "subject_id": "desc.1",
                        "metrics": {"cycles": 2.0},
                        "tags": [],
                    },
                ],
            }
        )

    assert "analysis record ids must be unique" in str(exc_info.value)
