import pytest
from pydantic import ValidationError


def test_performance_diagnostics_report_captures_hotspots_fit_gap_bottlenecks_and_pressure() -> None:
    from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport

    report = PerformanceDiagnosticsReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "dual-core",
            "report_kind": "prefill",
            "phase_breakdown": [
                {
                    "phase": "projection",
                    "estimated_cycles": 768.0,
                    "fitted_work_cycles": 880.0,
                    "critical_path_share": 0.75,
                    "total_bytes": 32768.0,
                },
                {
                    "phase": "sync",
                    "estimated_cycles": 256.0,
                    "fitted_work_cycles": 256.0,
                    "critical_path_share": 0.25,
                    "total_bytes": 32768.0,
                },
            ],
            "layer_hotspots": [
                {
                    "layer_id": 0,
                    "estimated_cycles": 880.0,
                    "fitted_work_cycles": 924.0,
                    "cycle_share": 0.86,
                    "fitted_cycle_share": 0.78,
                    "total_bytes": 32768.0,
                    "dominant_phase": "projection",
                    "dominant_bound": "compute_bound",
                    "support_gap_count": 1,
                }
            ],
            "node_hotspots": [
                {
                    "node_id": "nig.node.linear.0",
                    "graph_node_id": "graph.node.linear.0",
                    "layer_id": 0,
                    "structure_id": "structure.layer0.attention_block",
                    "structure_kind": "attention_block",
                    "phase": "projection",
                    "macro_op": "WDQ_GEMM",
                    "support_status": "native",
                    "bound_kind": "compute_bound",
                    "estimated_cycles": 768.0,
                    "fitted_work_cycles": 880.0,
                    "cycle_share": 0.75,
                    "fitted_cycle_share": 0.74,
                    "total_bytes": 32768.0,
                }
            ],
            "critical_path_summary": {
                "critical_path_cycles": 128.0,
                "estimated_cycles": 1024.0,
                "fitted_work_cycles": 1180.0,
                "critical_path_minus_estimated_cycles": -896.0,
                "critical_path_minus_fitted_cycles": -1052.0,
                "critical_path_blocks": [
                    "sched.block.q_proj.dma_in",
                    "sched.block.q_proj.compute",
                ],
                "dominant_phase": "projection",
                "dominant_macro": "WDQ_GEMM",
            },
            "bottleneck_classification": {
                "dominant_bottleneck": "compute-bound",
                "bottleneck_counts": {
                    "compute-bound": 3,
                    "sync-bound": 1,
                },
                "issue_count": 1,
                "issues": [
                    {
                        "subject_id": "sched.block.unmapped",
                        "bottleneck": "isa-gap-bound",
                        "message": "ATTENTION_MASK_PREP did not map to a supported opcode",
                    }
                ],
            },
            "bandwidth_diagnostics": {
                "peak_bandwidth_pressure": 512.0,
                "peak_pressure_subject_id": "sched.block.0",
                "dominant_read_address_space": "DDR",
                "dominant_write_address_space": "VMEM",
                "dominant_read_backing_store": "ddr-backed-staged",
                "dominant_write_backing_store": "vmem-local",
                "dominant_read_memory_class": "WEIGHT",
                "dominant_write_memory_class": "ACTIVATION",
                "read_bytes_by_address_space": {"DDR": 32768.0},
                "write_bytes_by_address_space": {"VMEM": 24576.0},
            },
            "vmem_diagnostics": {
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 24576,
                "hottest_region_capacity_bytes": 30720,
                "hottest_region_utilization": 0.8,
                "hottest_region_dominant_memory_class": "ACTIVATION",
                "hottest_region_dominant_backing_store": "vmem-local",
                "hottest_region_peak_bytes_by_backing_store": {"vmem-local": 16384},
                "hottest_region_peak_bytes_by_memory_class": {"ACTIVATION": 24576},
            },
            "support_gap_diagnostics": {
                "isa_gap_counts": {"opcode_not_supported": 2},
                "issue_subject_ids": ["sched.block.unmapped"],
                "messages": ["ATTENTION_MASK_PREP did not map to a supported opcode"],
            },
        }
    )

    assert report.report_kind == "prefill"
    assert report.phase_breakdown[0].critical_path_share == 0.75
    assert report.layer_hotspots[0].layer_id == 0
    assert report.layer_hotspots[0].dominant_phase == "projection"
    assert report.layer_hotspots[0].dominant_bound == "compute_bound"
    assert report.layer_hotspots[0].support_gap_count == 1
    assert report.node_hotspots[0].node_id == "nig.node.linear.0"
    assert report.node_hotspots[0].graph_node_id == "graph.node.linear.0"
    assert report.node_hotspots[0].structure_id == "structure.layer0.attention_block"
    assert report.node_hotspots[0].structure_kind == "attention_block"
    assert report.node_hotspots[0].phase == "projection"
    assert report.node_hotspots[0].macro_op == "WDQ_GEMM"
    assert report.node_hotspots[0].support_status == "native"
    assert report.node_hotspots[0].bound_kind == "compute_bound"
    assert report.critical_path_summary.critical_path_blocks[1] == "sched.block.q_proj.compute"
    assert report.bottleneck_classification.dominant_bottleneck == "compute-bound"
    assert report.bandwidth_diagnostics.read_bytes_by_address_space["DDR"] == 32768.0
    assert report.vmem_diagnostics.hottest_region_peak_bytes_by_memory_class["ACTIVATION"] == 24576
    assert report.support_gap_diagnostics.isa_gap_counts["opcode_not_supported"] == 2


def test_performance_diagnostics_report_requires_support_gap_diagnostics() -> None:
    from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport

    with pytest.raises(ValidationError):
        PerformanceDiagnosticsReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "phase_breakdown": [],
                "layer_hotspots": [],
                "node_hotspots": [],
                "critical_path_summary": {
                    "critical_path_cycles": 0.0,
                    "estimated_cycles": 0.0,
                    "fitted_work_cycles": 0.0,
                    "critical_path_minus_estimated_cycles": 0.0,
                    "critical_path_minus_fitted_cycles": 0.0,
                    "critical_path_blocks": [],
                    "dominant_phase": "",
                    "dominant_macro": "",
                },
                "bottleneck_classification": {
                    "dominant_bottleneck": "",
                    "bottleneck_counts": {},
                    "issue_count": 0,
                    "issues": [],
                },
                "bandwidth_diagnostics": {
                    "peak_bandwidth_pressure": 0.0,
                    "peak_pressure_subject_id": None,
                    "dominant_read_address_space": None,
                    "dominant_write_address_space": None,
                    "dominant_read_backing_store": None,
                    "dominant_write_backing_store": None,
                    "dominant_read_memory_class": None,
                    "dominant_write_memory_class": None,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                },
                "vmem_diagnostics": {
                    "hottest_region": None,
                    "hottest_region_peak_bytes": 0,
                    "hottest_region_capacity_bytes": 0,
                    "hottest_region_utilization": 0.0,
                    "hottest_region_dominant_memory_class": None,
                    "hottest_region_dominant_backing_store": None,
                    "hottest_region_peak_bytes_by_backing_store": {},
                    "hottest_region_peak_bytes_by_memory_class": {},
                },
            }
        )


def test_performance_diagnostics_report_rejects_unknown_report_kind() -> None:
    from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport

    with pytest.raises(ValidationError):
        PerformanceDiagnosticsReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "mystery",
                "phase_breakdown": [],
                "layer_hotspots": [],
                "node_hotspots": [],
                "critical_path_summary": {
                    "critical_path_cycles": 0.0,
                    "estimated_cycles": 0.0,
                    "fitted_work_cycles": 0.0,
                    "critical_path_minus_estimated_cycles": 0.0,
                    "critical_path_minus_fitted_cycles": 0.0,
                    "critical_path_blocks": [],
                    "dominant_phase": "",
                    "dominant_macro": "",
                },
                "bottleneck_classification": {
                    "dominant_bottleneck": "",
                    "bottleneck_counts": {},
                    "issue_count": 0,
                    "issues": [],
                },
                "bandwidth_diagnostics": {
                    "peak_bandwidth_pressure": 0.0,
                    "peak_pressure_subject_id": None,
                    "dominant_read_address_space": None,
                    "dominant_write_address_space": None,
                    "dominant_read_backing_store": None,
                    "dominant_write_backing_store": None,
                    "dominant_read_memory_class": None,
                    "dominant_write_memory_class": None,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                },
                "vmem_diagnostics": {
                    "hottest_region": None,
                    "hottest_region_peak_bytes": 0,
                    "hottest_region_capacity_bytes": 0,
                    "hottest_region_utilization": 0.0,
                    "hottest_region_dominant_memory_class": None,
                    "hottest_region_dominant_backing_store": None,
                    "hottest_region_peak_bytes_by_backing_store": {},
                    "hottest_region_peak_bytes_by_memory_class": {},
                },
                "support_gap_diagnostics": {
                    "isa_gap_counts": {},
                    "issue_subject_ids": [],
                    "messages": [],
                },
            }
        )


def test_performance_diagnostics_report_rejects_legacy_shallow_hotspot_payloads() -> None:
    from llm_sched.contracts.performance_diagnostics_report import PerformanceDiagnosticsReport

    with pytest.raises(ValidationError):
        PerformanceDiagnosticsReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "phase_breakdown": [],
                "layer_hotspots": [
                    {
                        "layer_id": 0,
                        "estimated_cycles": 880.0,
                        "fitted_work_cycles": 924.0,
                        "cycle_share": 0.86,
                        "fitted_cycle_share": 0.78,
                        "total_bytes": 32768.0,
                    }
                ],
                "node_hotspots": [
                    {
                        "node_id": "nig.node.linear.0",
                        "estimated_cycles": 768.0,
                        "fitted_work_cycles": 880.0,
                        "cycle_share": 0.75,
                        "fitted_cycle_share": 0.74,
                        "total_bytes": 32768.0,
                    }
                ],
                "critical_path_summary": {
                    "critical_path_cycles": 0.0,
                    "estimated_cycles": 0.0,
                    "fitted_work_cycles": 0.0,
                    "critical_path_minus_estimated_cycles": 0.0,
                    "critical_path_minus_fitted_cycles": 0.0,
                    "critical_path_blocks": [],
                    "dominant_phase": "",
                    "dominant_macro": "",
                },
                "bottleneck_classification": {
                    "dominant_bottleneck": "",
                    "bottleneck_counts": {},
                    "issue_count": 0,
                    "issues": [],
                },
                "bandwidth_diagnostics": {
                    "peak_bandwidth_pressure": 0.0,
                    "peak_pressure_subject_id": None,
                    "dominant_read_address_space": None,
                    "dominant_write_address_space": None,
                    "dominant_read_backing_store": None,
                    "dominant_write_backing_store": None,
                    "dominant_read_memory_class": None,
                    "dominant_write_memory_class": None,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                },
                "vmem_diagnostics": {
                    "hottest_region": None,
                    "hottest_region_peak_bytes": 0,
                    "hottest_region_capacity_bytes": 0,
                    "hottest_region_utilization": 0.0,
                    "hottest_region_dominant_memory_class": None,
                    "hottest_region_dominant_backing_store": None,
                    "hottest_region_peak_bytes_by_backing_store": {},
                    "hottest_region_peak_bytes_by_memory_class": {},
                },
                "support_gap_diagnostics": {
                    "isa_gap_counts": {},
                    "issue_subject_ids": [],
                    "messages": [],
                },
            }
        )
