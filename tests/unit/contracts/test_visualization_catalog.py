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


def test_visualization_catalog_contract_accepts_sweep_compare_summaries() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact

    artifact = VisualizationCatalogArtifact.model_validate(
        {
            "catalog_id": "catalog.phase-e",
            "title": "Phase E Catalog",
            "metadata": {
                "generated_by": "run-visualization-catalog",
                "entry_count": 1,
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
                    "sweep_baseline_target_profile_name": "riscv_npu_single_core_v1",
                    "sweep_comparisons": [
                        {
                            "candidate_target_profile_name": "riscv_npu_dual_core_v1",
                            "scenario_name": "prefill_seq128",
                            "mode": "prefill",
                            "metric_deltas": {"estimated_cycles": -1024.0},
                            "compare_summary": {
                                "baseline_schedule_kind": "single-core",
                                "candidate_schedule_kind": "dual-core",
                                "profile_diff_fields": ["core_mode", "num_cores"],
                                "highlighted_scalar_deltas": [
                                    {
                                        "metric_name": "estimated_cycles",
                                        "baseline_value": 4096.0,
                                        "candidate_value": 3072.0,
                                        "delta_value": -1024.0,
                                        "delta_ratio": -0.25,
                                    },
                                    {
                                        "metric_name": "tokens_per_cycle",
                                        "baseline_value": 0.03125,
                                        "candidate_value": 0.0416666667,
                                        "delta_value": 0.0104166667,
                                        "delta_ratio": 0.3333333344,
                                    },
                                ],
                                "scalar_deltas": [
                                    {
                                        "metric_name": "estimated_cycles",
                                        "baseline_value": 4096.0,
                                        "candidate_value": 3072.0,
                                        "delta_value": -1024.0,
                                        "delta_ratio": -0.25,
                                    },
                                    {
                                        "metric_name": "tokens_per_cycle",
                                        "baseline_value": 0.03125,
                                        "candidate_value": 0.0416666667,
                                        "delta_value": 0.0104166667,
                                        "delta_ratio": 0.3333333344,
                                    },
                                ],
                                "scalar_delta_groups": [
                                    {
                                        "group_id": "headline",
                                        "title": "Headline",
                                        "scalar_deltas": [
                                            {
                                                "metric_name": "estimated_cycles",
                                                "baseline_value": 4096.0,
                                                "candidate_value": 3072.0,
                                                "delta_value": -1024.0,
                                                "delta_ratio": -0.25,
                                            }
                                        ],
                                    },
                                    {
                                        "group_id": "throughput_latency",
                                        "title": "Throughput / Latency",
                                        "scalar_deltas": [
                                            {
                                                "metric_name": "tokens_per_cycle",
                                                "baseline_value": 0.03125,
                                                "candidate_value": 0.0416666667,
                                                "delta_value": 0.0104166667,
                                                "delta_ratio": 0.3333333344,
                                            }
                                        ],
                                    },
                                ],
                            },
                            "layer_deltas": [
                                {
                                    "layer_id": 0,
                                    "baseline_cycles": 2048.0,
                                    "candidate_cycles": 1536.0,
                                    "delta_cycles": -512.0,
                                    "baseline_cycle_share": 0.5,
                                    "candidate_cycle_share": 0.4444444444,
                                    "delta_cycle_share": -0.0555555556,
                                    "delta_cycles_ratio": -0.25,
                                    "baseline_bytes": 65536.0,
                                    "candidate_bytes": 49152.0,
                                    "delta_bytes": -16384.0,
                                    "delta_bytes_ratio": -0.25,
                                    "change_direction": "down",
                                }
                            ],
                            "fitted_layer_deltas": [
                                {
                                    "layer_id": 0,
                                    "baseline_fitted_work_cycles": 1792.0,
                                    "candidate_fitted_work_cycles": 1280.0,
                                    "delta_fitted_work_cycles": -512.0,
                                    "baseline_fitted_cycle_share": 0.7,
                                    "candidate_fitted_cycle_share": 0.625,
                                    "delta_fitted_cycle_share": -0.075,
                                    "delta_fitted_work_cycles_ratio": -0.2857142857,
                                    "baseline_bytes": 65536.0,
                                    "candidate_bytes": 49152.0,
                                    "delta_bytes": -16384.0,
                                    "delta_bytes_ratio": -0.25,
                                    "change_direction": "down",
                                }
                            ],
                        }
                    ],
                    "workbench_entry_path": "../run-prefill-single/workbench/index.html",
                }
            ],
        }
    )

    assert artifact.entries[0].sweep_baseline_target_profile_name == "riscv_npu_single_core_v1"
    assert artifact.entries[0].sweep_comparisons[0].metric_deltas["estimated_cycles"] == -1024.0
    assert artifact.entries[0].sweep_comparisons[0].compare_summary is not None
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.candidate_schedule_kind == (
        "dual-core"
    )
    assert [
        delta.metric_name
        for delta in artifact.entries[0].sweep_comparisons[0].compare_summary.highlighted_scalar_deltas
    ] == [
        "estimated_cycles",
        "tokens_per_cycle",
    ]
    assert artifact.entries[0].sweep_comparisons[0].compare_summary.scalar_deltas[0].delta_value == (
        -1024.0
    )
    assert [
        group.group_id
        for group in artifact.entries[0].sweep_comparisons[0].compare_summary.scalar_delta_groups
    ] == ["headline", "throughput_latency"]
    assert (
        artifact.entries[0]
        .sweep_comparisons[0]
        .compare_summary.scalar_delta_groups[1]
        .scalar_deltas[0]
        .metric_name
        == "tokens_per_cycle"
    )
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].baseline_cycle_share == 0.5
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].delta_cycles_ratio == -0.25
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].change_direction == "down"
    assert artifact.entries[0].sweep_comparisons[0].layer_deltas[0].delta_cycles == -512.0
    assert (
        artifact.entries[0].sweep_comparisons[0].fitted_layer_deltas[0].baseline_fitted_cycle_share
        == 0.7
    )
    assert (
        artifact.entries[0].sweep_comparisons[0].fitted_layer_deltas[0].delta_fitted_work_cycles_ratio
        == pytest.approx(-0.2857142857)
    )


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


def test_visualization_catalog_contract_accepts_optional_phase_c_gate_summary() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact

    artifact = VisualizationCatalogArtifact.model_validate(
        {
            "catalog_id": "catalog.phase-c",
            "title": "Phase C Catalog",
            "metadata": {
                "generated_by": "run-visualization-catalog",
                "entry_count": 1,
                "default_sort_key": "primary_metric",
                "phase_c_gate_summary": {
                    "status": "ready_for_acceptance",
                    "ready_case_count": 4,
                    "blocked_case_count": 0,
                    "planner_blocked_case_count": 0,
                    "downstream_blocked_case_count": 0,
                    "missing_case_count": 0,
                    "duplicate_case_count": 0,
                },
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
                    "workbench_entry_path": "../run-prefill-single/workbench/index.html",
                }
            ],
        }
    )

    assert artifact.metadata.phase_c_gate_summary is not None
    assert artifact.metadata.phase_c_gate_summary.status == "ready_for_acceptance"
    assert artifact.metadata.phase_c_gate_summary.ready_case_count == 4


def test_visualization_catalog_contract_accepts_optional_phase_c_blocked_cases() -> None:
    from llm_sched.contracts.visualization_catalog import VisualizationCatalogArtifact

    artifact = VisualizationCatalogArtifact.model_validate(
        {
            "catalog_id": "catalog.phase-c",
            "title": "Phase C Catalog",
            "metadata": {
                "generated_by": "run-visualization-catalog",
                "entry_count": 1,
                "default_sort_key": "primary_metric",
                "phase_c_blocked_cases": [
                    {
                        "case_id": "single-core:prefill",
                        "run_id": "run-single-prefill",
                        "workbench_entry_path": "../run-single-prefill/workbench/index.html",
                        "blocker_kind": "planner",
                        "planner_closure_status": "in_progress",
                        "downstream_closure_status": "ready_for_acceptance",
                        "downstream_missing_consumers": [],
                        "remaining_gaps": ["planner_closure: overflow region: ping"],
                    },
                    {
                        "case_id": "single-core:decode",
                        "run_id": "run-single-decode",
                        "workbench_entry_path": "../run-single-decode/workbench/index.html",
                        "blocker_kind": "downstream",
                        "planner_closure_status": "ready_for_acceptance",
                        "downstream_closure_status": "in_progress",
                        "downstream_missing_consumers": ["performance_estimation"],
                        "remaining_gaps": ["required downstream evidence missing"],
                    },
                    {
                        "case_id": "dual-core:prefill",
                        "run_id": None,
                        "blocker_kind": "missing_case",
                        "planner_closure_status": None,
                        "downstream_closure_status": None,
                        "downstream_missing_consumers": [],
                        "remaining_gaps": ["missing canonical case: dual-core:prefill"],
                    },
                ],
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
                    "workbench_entry_path": "../run-prefill-single/workbench/index.html",
                }
            ],
        }
    )

    assert len(artifact.metadata.phase_c_blocked_cases) == 3
    assert artifact.metadata.phase_c_blocked_cases[0].blocker_kind == "planner"
    assert artifact.metadata.phase_c_blocked_cases[1].downstream_missing_consumers == [
        "performance_estimation"
    ]
    assert (
        artifact.metadata.phase_c_blocked_cases[0].workbench_entry_path
        == "../run-single-prefill/workbench/index.html"
    )
    assert artifact.metadata.phase_c_blocked_cases[2].blocker_kind == "missing_case"
