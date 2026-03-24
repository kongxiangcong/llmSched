import pytest
from pydantic import ValidationError


def test_diagnosis_dataset_schema_registry_counts_match_design_spec() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import (
        DIAGNOSIS_DATASET_SCHEMA_REGISTRY,
        DiagnosisDatasetTableCategory,
    )

    assert len(DIAGNOSIS_DATASET_SCHEMA_REGISTRY) == 28
    assert sum(1 for schema in DIAGNOSIS_DATASET_SCHEMA_REGISTRY.values() if schema.category == DiagnosisDatasetTableCategory.CORE) == 12
    assert sum(1 for schema in DIAGNOSIS_DATASET_SCHEMA_REGISTRY.values() if schema.category == DiagnosisDatasetTableCategory.VIEW) == 13
    assert sum(1 for schema in DIAGNOSIS_DATASET_SCHEMA_REGISTRY.values() if schema.category == DiagnosisDatasetTableCategory.RELATION) == 3


def test_diagnosis_dataset_schema_registry_freezes_expected_headers() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import get_diagnosis_table_schema

    assert get_diagnosis_table_schema("structure_inventory.csv").csv_columns == (
        "structure_id", "structure_kind", "layer_id", "node_count", "input_shape", "output_shape", "dtype", "parameter_count", "parameter_bytes"
    )
    assert get_diagnosis_table_schema("operator_mapping.csv").csv_columns == (
        "normalized_node_id", "graph_node_id", "canonical_op", "macro_op", "phase", "fallback_kind", "structure_id", "layer_id"
    )
    assert get_diagnosis_table_schema("realization_gap.csv").csv_columns == (
        "structure_id", "structure_kind", "layer_id", "theoretical_compute_ops", "theoretical_bytes", "theoretical_ai", "scheduled_duration_slots",
        "estimated_cycles", "fitted_cycles", "worst_support_status", "support_penalty_score", "fallback_ratio", "sync_penalty_slots",
        "overlap_loss_slots", "effective_ai", "theoretical_ai_no_penalty", "gap_kind", "gap_score", "gap_confidence"
    )
    assert get_diagnosis_table_schema("timeline_loss_summary.csv").csv_columns == (
        "loss_kind", "total_slots", "event_count", "share_of_makespan", "recoverable_slots_total", "recoverable_share_of_makespan", "representative_entities"
    )
    assert get_diagnosis_table_schema("block_descriptor_map.csv").csv_columns == ("block_id", "descriptor_id")


def test_diagnosis_dataset_schema_fields_have_metadata_and_snake_case_names() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import DIAGNOSIS_DATASET_SCHEMA_REGISTRY

    for schema in DIAGNOSIS_DATASET_SCHEMA_REGISTRY.values():
        assert schema.primary_key
        for field in schema.fields:
            assert field.name == field.name.lower()
            assert "[" not in field.name and "]" not in field.name
            assert field.unit
            assert field.description
            assert field.heuristic_note
            assert field.source_layer is not None


def test_diagnosis_dataset_schema_exposes_validation_entrypoints() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import get_diagnosis_row_model, validate_diagnosis_dataset_row

    row_model = get_diagnosis_row_model("subject_block_map.csv")
    row = validate_diagnosis_dataset_row("subject_block_map.csv", {"normalized_node_id": "nig.node.q_proj.0", "block_id": "block.0001"})

    assert row_model.__name__ == "SubjectBlockMapRow"
    assert row.block_id == "block.0001"


def test_diagnosis_dataset_schema_rejects_missing_required_columns() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import validate_diagnosis_dataset_row

    with pytest.raises(ValidationError):
        validate_diagnosis_dataset_row(
            "schedule_blocks.csv",
            {
                "block_id": "block.0001",
                "normalized_node_id": "nig.node.q_proj.0",
                "macro_op": "WDQ_GEMM",
                "schedule_stage": "compute",
                "core_id": 0,
                "start_slot": 0,
                "end_slot": 12,
            },
        )


def test_diagnosis_dataset_schema_accepts_nullable_columns_and_notes() -> None:
    from llm_sched.contracts.diagnosis_dataset_schema import get_diagnosis_table_schema

    schema = get_diagnosis_table_schema("schedule_blocks.csv")
    row = schema.row_model.model_validate(
        {
            "block_id": "block.0001",
            "normalized_node_id": "nig.node.q_proj.0",
            "macro_op": "WDQ_GEMM",
            "schedule_stage": "compute",
            "core_id": 0,
            "start_slot": 0,
            "end_slot": 12,
            "duration_slots": 12,
            "stall_reason": None,
        }
    )

    assert row.stall_reason is None
    assert schema.notes
