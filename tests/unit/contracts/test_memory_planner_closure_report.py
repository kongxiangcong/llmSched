def test_memory_planner_closure_report_tracks_required_and_optional_evidence() -> None:
    from llm_sched.contracts.memory_planner_closure_report import MemoryPlannerClosureReport

    report = MemoryPlannerClosureReport.model_validate(
        {
            "run_id": "run-closure-001",
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "mode": "decode",
            "schedule_kind": "dual-core",
            "memory_plan_path": "artifacts/memory_plan.json",
            "planner_surface": {
                "storage_binding_count": 2,
                "region_count": 3,
                "regions_with_memory_class_attribution": 3,
                "regions_with_backing_store_attribution": 3,
                "bound_address_diagnostic_count": 2,
                "unresolved_address_diagnostic_count": 0,
            },
            "planner_closure": {
                "status": "ready_for_acceptance",
                "active_region_count": 3,
                "attributed_memory_class_region_count": 3,
                "attributed_backing_store_region_count": 3,
                "overflow_region_count": 0,
                "unresolved_address_diagnostic_count": 0,
                "remaining_gaps": [],
            },
            "downstream_consumers": [
                {
                    "consumer_id": "tile_planning",
                    "required_for_acceptance": True,
                    "status": "verified",
                    "artifact_key": "tiling_plan",
                    "artifact_path": "artifacts/tiling_plan.json",
                    "consumed_fields": ["storage_bindings"],
                    "message": "tile candidates record storage binding usage",
                },
                {
                    "consumer_id": "visualization_workbench",
                    "required_for_acceptance": False,
                    "status": "verified",
                    "artifact_key": "visualization_workbench_entry",
                    "artifact_path": "workbench/index.html",
                    "consumed_fields": [
                        "peak_bytes_by_backing_store",
                        "peak_bytes_by_memory_class",
                    ],
                    "message": "memory panel surfaces planner attribution",
                },
            ],
            "acceptance": {
                "status": "ready_for_acceptance",
                "verified_required_consumer_count": 5,
                "required_consumer_count": 5,
                "verified_optional_consumer_count": 1,
                "optional_consumer_count": 1,
                "remaining_gaps": [],
            },
        }
    )

    assert report.planner_surface.storage_binding_count == 2
    assert report.planner_closure.status == "ready_for_acceptance"
    assert report.planner_closure.active_region_count == 3
    assert report.downstream_consumers[0].consumer_id == "tile_planning"
    assert report.downstream_consumers[0].required_for_acceptance is True
    assert report.downstream_consumers[1].required_for_acceptance is False
    assert report.acceptance.status == "ready_for_acceptance"
