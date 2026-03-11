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
    assert report.token_latency.kv_io_cycles == pytest.approx(1100.0)
    assert report.kv_summary.kv_len == 2048
    assert report.kv_summary.kv_formula_count == 2
    assert report.kv_summary.unresolved_address_count == 1
    assert report.kv_summary.kv_related_cycle_share == pytest.approx(1100.0 / 3120.0)
    assert report.kv_summary.kv_related_bytes == pytest.approx(96000.0)
    assert report.memory_hotspot.dominant_address_space == "DDR"
    assert report.memory_hotspot.read_bytes_by_address_space == {"DDR": 128000.0, "VMEM": 32000.0}
    assert report.memory_hotspot.write_bytes_by_address_space == {"DDR": 48000.0, "VMEM": 16000.0}
    assert report.memory_hotspot.hottest_region == "ping"
    assert report.memory_hotspot.hottest_region_peak_bytes == 40960
    assert report.memory_hotspot.hottest_region_capacity_bytes == 65536
    assert report.memory_hotspot.hottest_region_utilization == pytest.approx(0.625)
    assert report.isa_summary.unmapped_block_count == 1
    assert [hotspot.macro_op for hotspot in report.macro_hotspots][:3] == [
        "WDQ_GEMM",
        "KVLOAD",
        "SDPA_DECODE",
    ]


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
                "total_bytes": 180000.0,
                "read_bytes": 120000.0,
                "write_bytes": 60000.0,
                "sync_cycles": 120.0,
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
