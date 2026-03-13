import pytest

from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.perf_report import PerfSummaryReport


def test_build_decode_evaluation_report_aggregates_latency_and_kv_cost() -> None:
    from llm_sched.analysis import build_decode_evaluation_report

    report = build_decode_evaluation_report(
        "run-decode-001",
        _decode_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.schedule_kind == "dual-core"
    assert report.sdpa_decode_present is True
    assert report.token_latency.total_tokens == 1
    assert report.token_latency.cycles_per_token == pytest.approx(3120.0)
    assert report.token_latency.critical_path_cycles == pytest.approx(2048.0)
    assert report.token_latency.critical_path_cycles_per_token == pytest.approx(2048.0)
    assert report.token_latency.projection_cycles == pytest.approx(980.0)
    assert report.token_latency.kv_io_cycles == pytest.approx(960.0)
    assert report.token_latency.attention_cycles == pytest.approx(820.0)
    assert report.token_latency.sync_cycles == pytest.approx(120.0)
    assert report.token_latency.other_cycles == pytest.approx(240.0)
    assert report.token_latency.projection_bytes == pytest.approx(47000.0)
    assert report.token_latency.kv_io_bytes == pytest.approx(99000.0)
    assert report.token_latency.attention_bytes == pytest.approx(26000.0)
    assert report.token_latency.sync_bytes == pytest.approx(4000.0)
    assert report.token_latency.other_bytes == pytest.approx(4000.0)
    assert report.token_latency.phase_attribution["projection"].compute_cycles == pytest.approx(900.0)
    assert report.token_latency.phase_attribution["kv_io"].memory_cycles == pytest.approx(960.0)
    assert report.token_latency.phase_attribution["sync"].sync_cycles == pytest.approx(120.0)
    assert report.token_latency.phase_attribution["projection"].schedule_compression_cycles == pytest.approx(340.0)
    assert report.token_latency.phase_attribution["attention"].schedule_compression_ratio == pytest.approx(120.0 / 820.0)
    assert report.token_latency.phase_attribution["other"].schedule_overhang_cycles == pytest.approx(0.0)
    assert report.token_latency.phase_attribution["projection"].cycles_per_token == pytest.approx(980.0)
    assert report.token_latency.phase_attribution["kv_io"].bytes_per_token == pytest.approx(99000.0)
    assert report.token_latency.phase_attribution["kv_io"].occupied_slots == pytest.approx(960.0)
    assert report.token_latency.phase_attribution["other"].occupied_slots_per_token == pytest.approx(180.0)
    assert report.token_latency.phase_attribution["projection"].per_core_occupied_slots == {
        "0": 400.0,
        "1": 240.0,
    }
    assert report.token_latency.phase_attribution["projection"].per_core_span_slots == {
        "0": 460.0,
        "1": 280.0,
    }
    assert report.token_latency.phase_attribution["projection"].occupied_slot_imbalance_slots == pytest.approx(160.0)
    assert report.token_latency.phase_attribution["projection"].occupied_slot_balance_ratio == pytest.approx(
        240.0 / 400.0
    )
    assert report.token_latency.phase_attribution["projection"].span_imbalance_slots == pytest.approx(180.0)
    assert report.token_latency.phase_attribution["projection"].span_balance_ratio == pytest.approx(280.0 / 460.0)
    assert report.token_latency.phase_attribution["projection"].read_bytes_by_address_space == {
        "DDR": 32000.0,
        "VMEM": 8000.0,
    }
    assert report.token_latency.phase_attribution["kv_io"].write_bytes_by_address_space == {"DDR": 32000.0}
    assert report.token_latency.phase_attribution["other"].write_bytes_by_address_space == {
        "DDR": 16000.0,
        "VMEM": 4000.0,
    }
    assert report.token_latency.phase_attribution["projection"].read_bytes_by_backing_store == {
        "ddr-backed-staged": 32000.0,
        "vmem-local": 8000.0,
    }
    assert report.token_latency.phase_attribution["kv_io"].write_bytes_by_backing_store == {
        "ddr-persistent": 32000.0
    }
    assert report.token_latency.phase_attribution["other"].write_bytes_by_backing_store == {
        "ddr-persistent": 16000.0,
        "vmem-local": 4000.0,
    }
    assert report.token_latency.phase_attribution["projection"].read_bytes_by_memory_class == {
        "ACTIVATION": 8000.0,
        "WEIGHT": 32000.0,
    }
    assert report.token_latency.phase_attribution["kv_io"].write_bytes_by_memory_class == {
        "KV_CACHE": 32000.0
    }
    assert report.token_latency.phase_attribution["other"].write_bytes_by_memory_class == {
        "ACTIVATION": 4000.0,
        "KV_CACHE": 16000.0,
    }
    assert report.kv_summary.kv_len == 2048
    assert report.kv_summary.kv_formula_count == 2
    assert report.kv_summary.unresolved_address_count == 1
    assert report.kv_summary.kv_related_cycle_share == pytest.approx(960.0 / 3120.0)
    assert report.kv_summary.kv_related_bytes == pytest.approx(99000.0)
    assert report.memory_hotspot.dominant_address_space == "DDR"
    assert report.memory_hotspot.read_bytes_by_address_space == {"DDR": 128000.0, "VMEM": 32000.0}
    assert report.memory_hotspot.write_bytes_by_address_space == {"DDR": 48000.0, "VMEM": 16000.0}
    assert report.memory_hotspot.hottest_region == "ping"
    assert report.memory_hotspot.hottest_region_peak_bytes == 40960
    assert report.memory_hotspot.hottest_region_capacity_bytes == 65536
    assert report.memory_hotspot.hottest_region_utilization == pytest.approx(0.625)
    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class == {
        "ACTIVATION": 28672,
        "KV_CACHE": 12288,
    }
    assert report.isa_summary.unmapped_block_count == 1
    assert [hotspot.macro_op for hotspot in report.macro_hotspots][:3] == [
        "WDQ_GEMM",
        "KVLOAD",
        "SDPA_DECODE",
    ]
    assert [hotspot.node_id for hotspot in report.node_hotspots][:3] == [
        "nig.node.proj.0",
        "nig.node.kvload.0",
        "nig.node.sdpa_decode.0",
    ]
    assert [row.layer_id for row in report.layer_breakdown] == [0, 1]


def test_build_decode_evaluation_report_rejects_prefill_scenarios() -> None:
    from llm_sched.analysis import build_decode_evaluation_report

    with pytest.raises(ValueError, match="decode"):
        build_decode_evaluation_report(
            "run-prefill-001",
            _prefill_scenario(),
            _perf_summary_report(),
            _coverage_report(),
            _memory_plan(),
        )


def test_build_decode_evaluation_report_propagates_hottest_region_backing_store_breakdown() -> None:
    from llm_sched.analysis import build_decode_evaluation_report

    report = build_decode_evaluation_report(
        "run-decode-001",
        _decode_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.memory_hotspot.hottest_region_peak_bytes_by_backing_store == {
        "ddr-backed-staged": 0,
        "ddr-persistent": 12288,
        "vmem-local": 28672,
    }


def test_build_decode_evaluation_report_propagates_hottest_region_memory_class_breakdown() -> None:
    from llm_sched.analysis import build_decode_evaluation_report

    report = build_decode_evaluation_report(
        "run-decode-001",
        _decode_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class == {
        "ACTIVATION": 28672,
        "KV_CACHE": 12288,
    }


def _decode_scenario() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="decode_token1_kv2048",
        version="phase-a.v1",
        mode="decode",
        batch=1,
        seq_len=1,
        kv_len=2048,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )


def _prefill_scenario() -> ScenarioProfile:
    return ScenarioProfile(
        scenario_name="prefill_seq128",
        version="phase-a.v1",
        mode="prefill",
        batch=1,
        seq_len=128,
        kv_len=0,
        layer_scope=LayerScope(kind="all"),
        reporting=ReportingConfig(include_layer_breakdown=True, include_bandwidth=True),
    )


def _perf_summary_report() -> PerfSummaryReport:
    return PerfSummaryReport.model_validate(
        {
            "run_id": "run-decode-001",
            "graph_id": "gemma3-decode",
            "schedule_kind": "dual-core",
            "totals": {
                "estimated_cycles": 3120.0,
                "critical_path_cycles": 2048.0,
                "total_bytes": 180000.0,
                "read_bytes": 120000.0,
                "write_bytes": 60000.0,
                "sync_cycles": 120.0,
            },
            "phase_attribution": {
                "projection": {
                    "estimated_cycles": 980.0,
                    "compute_cycles": 900.0,
                    "memory_cycles": 80.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 340.0,
                    "schedule_compression_ratio": 340.0 / 980.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 47000.0,
                    "cycles_per_token": 980.0,
                    "bytes_per_token": 47000.0,
                    "occupied_slots": 640.0,
                    "occupied_slots_per_token": 640.0,
                    "per_core_occupied_slots": {"0": 400.0, "1": 240.0},
                    "per_core_span_slots": {"0": 460.0, "1": 280.0},
                    "occupied_slot_imbalance_slots": 160.0,
                    "occupied_slot_balance_ratio": 240.0 / 400.0,
                    "span_imbalance_slots": 180.0,
                    "span_balance_ratio": 280.0 / 460.0,
                    "read_bytes_by_address_space": {"DDR": 32000.0, "VMEM": 8000.0},
                    "write_bytes_by_address_space": {"VMEM": 10000.0},
                    "read_bytes_by_backing_store": {"ddr-backed-staged": 32000.0, "vmem-local": 8000.0},
                    "write_bytes_by_backing_store": {"vmem-local": 10000.0},
                    "read_bytes_by_memory_class": {"WEIGHT": 32000.0, "ACTIVATION": 8000.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 10000.0},
                },
                "kv_io": {
                    "estimated_cycles": 960.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 960.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 0.0,
                    "schedule_compression_ratio": 0.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 99000.0,
                    "cycles_per_token": 960.0,
                    "bytes_per_token": 99000.0,
                    "occupied_slots": 960.0,
                    "occupied_slots_per_token": 960.0,
                    "read_bytes_by_address_space": {"DDR": 64000.0},
                    "write_bytes_by_address_space": {"DDR": 32000.0},
                    "read_bytes_by_backing_store": {"ddr-persistent": 64000.0},
                    "write_bytes_by_backing_store": {"ddr-persistent": 32000.0},
                    "read_bytes_by_memory_class": {"KV_CACHE": 64000.0},
                    "write_bytes_by_memory_class": {"KV_CACHE": 32000.0},
                },
                "attention": {
                    "estimated_cycles": 820.0,
                    "compute_cycles": 700.0,
                    "memory_cycles": 120.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 120.0,
                    "schedule_compression_ratio": 120.0 / 820.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 26000.0,
                    "cycles_per_token": 820.0,
                    "bytes_per_token": 26000.0,
                    "occupied_slots": 700.0,
                    "occupied_slots_per_token": 700.0,
                    "read_bytes_by_address_space": {"DDR": 16000.0, "VMEM": 8000.0},
                    "write_bytes_by_address_space": {"VMEM": 2000.0},
                    "read_bytes_by_backing_store": {"ddr-persistent": 16000.0, "vmem-local": 8000.0},
                    "write_bytes_by_backing_store": {"vmem-local": 2000.0},
                    "read_bytes_by_memory_class": {"KV_CACHE": 16000.0, "ACTIVATION": 8000.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 2000.0},
                },
                "sync": {
                    "estimated_cycles": 120.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 120.0,
                    "schedule_compression_cycles": 0.0,
                    "schedule_compression_ratio": 0.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 4000.0,
                    "cycles_per_token": 120.0,
                    "bytes_per_token": 4000.0,
                    "occupied_slots": 0.0,
                    "occupied_slots_per_token": 0.0,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                    "read_bytes_by_backing_store": {},
                    "write_bytes_by_backing_store": {},
                    "read_bytes_by_memory_class": {},
                    "write_bytes_by_memory_class": {},
                },
                "other": {
                    "estimated_cycles": 240.0,
                    "compute_cycles": 120.0,
                    "memory_cycles": 120.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 60.0,
                    "schedule_compression_ratio": 0.25,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 4000.0,
                    "cycles_per_token": 240.0,
                    "bytes_per_token": 4000.0,
                    "occupied_slots": 180.0,
                    "occupied_slots_per_token": 180.0,
                    "read_bytes_by_address_space": {"VMEM": 4000.0},
                    "write_bytes_by_address_space": {"DDR": 16000.0, "VMEM": 4000.0},
                    "read_bytes_by_backing_store": {"vmem-local": 4000.0},
                    "write_bytes_by_backing_store": {"ddr-persistent": 16000.0, "vmem-local": 4000.0},
                    "read_bytes_by_memory_class": {"ACTIVATION": 4000.0},
                    "write_bytes_by_memory_class": {"KV_CACHE": 16000.0, "ACTIVATION": 4000.0},
                },
            },
            "per_macro_cycles": {
                "WDQ_GEMM": 1100.0,
                "KVLOAD": 900.0,
                "SDPA_DECODE": 700.0,
                "KVSTORE": 200.0,
                "ELEM_ADD": 100.0,
            },
            "per_macro_bytes": {
                "WDQ_GEMM": 50000.0,
                "KVLOAD": 64000.0,
                "SDPA_DECODE": 40000.0,
                "KVSTORE": 32000.0,
                "ELEM_ADD": 4000.0,
            },
            "per_node_cycles": {
                "nig.node.proj.0": 1100.0,
                "nig.node.kvload.0": 900.0,
                "nig.node.sdpa_decode.0": 700.0,
                "nig.node.kvstore.0": 200.0,
                "nig.node.elem_add.0": 100.0,
            },
            "per_node_bytes": {
                "nig.node.proj.0": 50000.0,
                "nig.node.kvload.0": 64000.0,
                "nig.node.sdpa_decode.0": 40000.0,
                "nig.node.kvstore.0": 32000.0,
                "nig.node.elem_add.0": 4000.0,
            },
            "per_layer_cycles": {
                "0": 2000.0,
                "1": 1120.0,
            },
            "per_layer_bytes": {
                "0": 114000.0,
                "1": 66000.0,
            },
            "bottleneck_counts": {"compute-bound": 8, "memory-bound": 6, "sync-bound": 2},
            "isa_gap_counts": {"opcode_not_supported": 1},
            "data_movement_read_bytes_by_address_space": {"DDR": 128000.0, "VMEM": 32000.0},
            "data_movement_write_bytes_by_address_space": {"DDR": 48000.0, "VMEM": 16000.0},
            "vmem_region_peak_bytes": {"ping": 40960, "pong": 32768},
            "vmem_region_capacity_bytes": {"ping": 65536, "pong": 65536},
            "vmem_region_peak_utilization": {"ping": 0.625, "pong": 0.5},
            "issues": [],
        }
    )


def _coverage_report() -> ISACoverageReport:
    return ISACoverageReport.model_validate(
        {
            "graph_id": "gemma3-decode",
            "schedule_kind": "dual-core",
            "mapped_descriptor_count": 40,
            "unmapped_block_count": 1,
            "opcode_counts": {"WDQ_GEMM": 16, "KVLOAD": 8, "SDPA_DECODE": 8},
            "gap_counts": {"opcode_not_supported": 1},
            "issues": [],
        }
    )


def _memory_plan() -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-decode",
            "scenario_name": "decode_token1_kv2048",
            "core_mode": "dual-core",
            "allocations": [],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 40960,
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 28672,
                        "ddr-backed-staged": 0,
                        "ddr-persistent": 12288,
                    },
                    "peak_bytes_by_memory_class": {
                        "ACTIVATION": 28672,
                        "KV_CACHE": 12288,
                    },
                    "fits": True,
                    "allocation_ids": [],
                },
                "pong": {
                    "region_name": "pong",
                    "capacity_bytes": 65536,
                    "peak_bytes": 32768,
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 32768,
                        "ddr-backed-staged": 0,
                        "ddr-persistent": 0,
                    },
                    "peak_bytes_by_memory_class": {
                        "ACTIVATION": 32768,
                    },
                    "fits": True,
                    "allocation_ids": [],
                },
            },
            "kv_formulas": [
                {
                    "node_id": "nig.kvload.0",
                    "tensor_kind": "key",
                    "layer_id": 0,
                    "layout": "LBHSD",
                    "base_symbol": "KV_BASE_K",
                    "layer_stride_bytes": 1024,
                    "kv_kind_stride_bytes": 512,
                    "token_stride_bytes": 256,
                    "head_stride_bytes": 64,
                    "dim_stride_bytes": 2,
                    "formula": "KV_BASE_K + layer * 1024",
                },
                {
                    "node_id": "nig.kvload.1",
                    "tensor_kind": "value",
                    "layer_id": 0,
                    "layout": "LBHSD",
                    "base_symbol": "KV_BASE_V",
                    "layer_stride_bytes": 1024,
                    "kv_kind_stride_bytes": 512,
                    "token_stride_bytes": 256,
                    "head_stride_bytes": 64,
                    "dim_stride_bytes": 2,
                    "formula": "KV_BASE_V + layer * 1024",
                },
            ],
            "diagnostics": [],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.kvload.0",
                    "address_kind": "kv",
                    "status": "bound",
                    "symbol": "KV_BASE_K",
                    "message": "key address resolved",
                },
                {
                    "diagnostic_id": "addr.1",
                    "node_id": "nig.kvload.1",
                    "address_kind": "kv",
                    "status": "bound",
                    "symbol": "KV_BASE_V",
                    "message": "value address resolved",
                },
                {
                    "diagnostic_id": "addr.2",
                    "node_id": "nig.quant.0",
                    "address_kind": "quant",
                    "status": "unresolved",
                    "symbol": "QUANT_BASE",
                    "message": "quant address unresolved",
                },
            ],
        }
    )
