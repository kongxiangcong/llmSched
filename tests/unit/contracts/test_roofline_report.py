import pytest
from pydantic import ValidationError


def test_roofline_report_captures_ceilings_points_dominant_bound_and_headroom() -> None:
    from llm_sched.contracts.roofline_report import RooflineReport

    report = RooflineReport.model_validate(
        {
            "run_id": "run-diagnosis-001",
            "graph_id": "graph::gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "schedule_kind": "dual-core",
            "report_kind": "prefill",
            "compute_ceiling": {
                "ceiling_id": "compute.tensor-core",
                "label": "Tensor core peak",
                "peak_ops_per_cycle": 2048.0,
            },
            "bandwidth_ceilings": [
                {
                    "ceiling_id": "bw.ddr",
                    "label": "DDR bandwidth",
                    "bandwidth_bytes_per_cycle": 512.0,
                },
                {
                    "ceiling_id": "bw.vmem",
                    "label": "VMEM bandwidth",
                    "bandwidth_bytes_per_cycle": 1024.0,
                },
            ],
            "node_points": [
                {
                    "node_id": "nig.node.q_proj.0",
                    "layer_id": 0,
                    "macro_op": "WDQ_GEMM",
                    "phase": "projection",
                    "arithmetic_intensity": 128.0,
                    "achieved_ops_per_cycle": 768.0,
                    "compute_ops": 67108864.0,
                    "total_bytes": 524288.0,
                    "dominant_bound": "compute",
                    "active_bandwidth_ceiling_id": "bw.vmem",
                    "headroom_ratio": 0.625,
                }
            ],
            "layer_points": [
                {
                    "layer_id": 0,
                    "structure_ids": ["structure.layer0.attention_block"],
                    "node_count": 4,
                    "arithmetic_intensity": 96.0,
                    "achieved_ops_per_cycle": 640.0,
                    "compute_ops": 134217728.0,
                    "total_bytes": 1398101.3333333333,
                    "dominant_bound": "bandwidth",
                    "active_bandwidth_ceiling_id": "bw.ddr",
                    "headroom_ratio": 0.25,
                }
            ],
            "dominant_bound_summary": {
                "dominant_bound": "compute",
                "node_counts": {"compute": 1, "bandwidth": 0},
                "layer_counts": {"compute": 0, "bandwidth": 1},
                "top_node_ids": ["nig.node.q_proj.0"],
                "top_layer_ids": [0],
            },
            "headroom_summary": {
                "max_headroom_ratio": 0.625,
                "mean_headroom_ratio": 0.4375,
                "most_limited_node_id": "nig.node.q_proj.0",
                "most_limited_layer_id": 0,
                "top_headroom_node_ids": ["nig.node.q_proj.0"],
                "top_headroom_layer_ids": [0],
            },
        }
    )

    assert report.compute_ceiling.peak_ops_per_cycle == 2048.0
    assert report.bandwidth_ceilings[0].ceiling_id == "bw.ddr"
    assert report.node_points[0].dominant_bound == "compute"
    assert report.layer_points[0].active_bandwidth_ceiling_id == "bw.ddr"
    assert report.dominant_bound_summary.node_counts["compute"] == 1
    assert report.headroom_summary.max_headroom_ratio == pytest.approx(0.625)


def test_roofline_report_requires_headroom_summary() -> None:
    from llm_sched.contracts.roofline_report import RooflineReport

    with pytest.raises(ValidationError):
        RooflineReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "compute_ceiling": {
                    "ceiling_id": "compute.tensor-core",
                    "label": "Tensor core peak",
                    "peak_ops_per_cycle": 2048.0,
                },
                "bandwidth_ceilings": [],
                "node_points": [],
                "layer_points": [],
                "dominant_bound_summary": {
                    "dominant_bound": "compute",
                    "node_counts": {},
                    "layer_counts": {},
                    "top_node_ids": [],
                    "top_layer_ids": [],
                },
            }
        )


def test_roofline_report_rejects_negative_arithmetic_intensity() -> None:
    from llm_sched.contracts.roofline_report import RooflineReport

    with pytest.raises(ValidationError):
        RooflineReport.model_validate(
            {
                "run_id": "run-diagnosis-001",
                "graph_id": "graph::gemma3-prefill",
                "scenario_name": "prefill_seq128",
                "schedule_kind": "dual-core",
                "report_kind": "prefill",
                "compute_ceiling": {
                    "ceiling_id": "compute.tensor-core",
                    "label": "Tensor core peak",
                    "peak_ops_per_cycle": 2048.0,
                },
                "bandwidth_ceilings": [
                    {
                        "ceiling_id": "bw.ddr",
                        "label": "DDR bandwidth",
                        "bandwidth_bytes_per_cycle": 512.0,
                    }
                ],
                "node_points": [
                    {
                        "node_id": "nig.node.bad.0",
                        "layer_id": 0,
                        "macro_op": "BAD",
                        "phase": "other",
                        "arithmetic_intensity": -1.0,
                        "achieved_ops_per_cycle": 0.0,
                        "compute_ops": 0.0,
                        "total_bytes": 0.0,
                        "dominant_bound": "bandwidth",
                        "active_bandwidth_ceiling_id": "bw.ddr",
                        "headroom_ratio": 0.0,
                    }
                ],
                "layer_points": [],
                "dominant_bound_summary": {
                    "dominant_bound": "bandwidth",
                    "node_counts": {"bandwidth": 1},
                    "layer_counts": {},
                    "top_node_ids": ["nig.node.bad.0"],
                    "top_layer_ids": [],
                },
                "headroom_summary": {
                    "max_headroom_ratio": 0.0,
                    "mean_headroom_ratio": 0.0,
                    "most_limited_node_id": "nig.node.bad.0",
                    "most_limited_layer_id": None,
                    "top_headroom_node_ids": [],
                    "top_headroom_layer_ids": [],
                },
            }
        )
