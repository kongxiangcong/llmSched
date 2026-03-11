import pytest


def test_visualization_catalog_contract_accepts_minimal_static_index() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact

    artifact = VisualizationCatalogArtifact.model_validate(
        {
            "catalog_id": "catalog.phase-e",
            "title": "Phase E Catalog",
            "metadata": {
                "generated_by": "run-visualization-catalog",
                "entry_count": 2,
                "default_sort_key": "primary_metric",
            },
            "entries": [
                {
                    "entry_id": "run.prefill.single",
                    "run_id": "run-prefill-single",
                    "scenario_name": "prefill_seq128",
                    "mode": "prefill",
                    "schedule_kind": "single-core",
                    "target_profile_name": "riscv_npu_single_core_v1",
                    "primary_metric_name": "estimated_cycles",
                    "primary_metric_value": 4096.0,
                    "metric_values": {
                        "estimated_cycles": 4096.0,
                        "tokens_per_cycle": 0.03125,
                    },
                    "workbench_entry_path": "../run-prefill-single/workbench/index.html",
                },
                {
                    "entry_id": "run.decode.dual",
                    "run_id": "run-decode-dual",
                    "scenario_name": "decode_token1_kv2048",
                    "mode": "decode",
                    "schedule_kind": "dual-core",
                    "target_profile_name": "riscv_npu_dual_core_v1",
                    "primary_metric_name": "token_latency_cycles",
                    "primary_metric_value": 512.0,
                    "metric_values": {
                        "token_latency_cycles": 512.0,
                        "tokens_per_second": 1953.125,
                    },
                    "workbench_entry_path": "../run-decode-dual/workbench/index.html",
                },
            ],
        }
    )

    assert artifact.metadata.default_sort_key == "primary_metric"
    assert artifact.entries[0].workbench_entry_path.endswith("workbench/index.html")
    assert artifact.entries[0].metric_values["tokens_per_cycle"] == 0.03125


def test_visualization_catalog_contract_rejects_duplicate_entry_ids() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact

    with pytest.raises(ValueError, match="duplicate"):
        VisualizationCatalogArtifact.model_validate(
            {
                "catalog_id": "catalog.phase-e",
                "title": "Phase E Catalog",
                "metadata": {
                    "generated_by": "run-visualization-catalog",
                    "entry_count": 2,
                    "default_sort_key": "primary_metric",
                },
                "entries": [
                    {
                        "entry_id": "run.same",
                        "run_id": "run-a",
                        "scenario_name": "prefill_seq128",
                        "mode": "prefill",
                        "schedule_kind": "single-core",
                        "target_profile_name": "riscv_npu_single_core_v1",
                        "primary_metric_name": "estimated_cycles",
                        "primary_metric_value": 4096.0,
                        "workbench_entry_path": "../run-a/workbench/index.html",
                    },
                    {
                        "entry_id": "run.same",
                        "run_id": "run-b",
                        "scenario_name": "decode_token1_kv2048",
                        "mode": "decode",
                        "schedule_kind": "dual-core",
                        "target_profile_name": "riscv_npu_dual_core_v1",
                        "primary_metric_name": "token_latency_cycles",
                        "primary_metric_value": 512.0,
                        "workbench_entry_path": "../run-b/workbench/index.html",
                    },
                ],
            }
        )
