import pytest

from llm_sched.config.scenario_profile import LayerScope, ReportingConfig, ScenarioProfile
from llm_sched.contracts.isa_coverage_report import ISACoverageReport
from llm_sched.contracts.memory_plan import (
    AddressBindingDiagnostic,
    MemoryPlanArtifact,
    RegionSummary,
    VMEMFitDiagnostic,
)
from llm_sched.contracts.perf_report import PerfSummaryReport


def test_build_prefill_evaluation_report_aggregates_prefill_metrics() -> None:
    from llm_sched.analysis import build_prefill_evaluation_report

    report = build_prefill_evaluation_report(
        "run-prefill-001",
        _prefill_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.schedule_kind == "single-core"
    assert report.mxu_dominant is True
    assert report.throughput.total_tokens == 128
    assert report.throughput.tokens_per_cycle == pytest.approx(128 / 4096.0)
    assert report.memory_summary.max_region_utilization == pytest.approx(0.75)
    assert report.memory_summary.overflow_region_count == 0
    assert report.memory_summary.unresolved_address_count == 1
    assert report.memory_hotspot.dominant_address_space == "DDR"
    assert report.memory_hotspot.read_bytes_by_address_space == {"DDR": 131072.0, "VMEM": 65536.0}
    assert report.memory_hotspot.write_bytes_by_address_space == {"VMEM": 32768.0}
    assert report.memory_hotspot.hottest_region == "ping"
    assert report.memory_hotspot.hottest_region_peak_bytes == 49152
    assert report.memory_hotspot.hottest_region_capacity_bytes == 65536
    assert report.memory_hotspot.hottest_region_utilization == pytest.approx(0.75)
    assert report.isa_summary.unmapped_block_count == 1
    assert [hotspot.macro_op for hotspot in report.macro_hotspots] == ["WDQ_GEMM", "SDPA", "DMA_LOAD"]


def test_build_prefill_evaluation_report_rejects_decode_scenarios() -> None:
    from llm_sched.analysis import build_prefill_evaluation_report

    with pytest.raises(ValueError, match="prefill"):
        build_prefill_evaluation_report(
            "run-decode-001",
            _decode_scenario(),
            _perf_summary_report(),
            _coverage_report(),
            _memory_plan(),
        )


def test_build_prefill_evaluation_report_propagates_hottest_region_backing_store_breakdown() -> None:
    from llm_sched.analysis import build_prefill_evaluation_report

    report = build_prefill_evaluation_report(
        "run-prefill-001",
        _prefill_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.memory_hotspot.hottest_region_peak_bytes_by_backing_store == {
        "ddr-backed-staged": 8192,
        "ddr-persistent": 0,
        "vmem-local": 40960,
    }


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


def _perf_summary_report() -> PerfSummaryReport:
    return PerfSummaryReport.model_validate(
        {
            "run_id": "run-prefill-001",
            "graph_id": "gemma3-prefill",
            "schedule_kind": "single-core",
            "totals": {
                "estimated_cycles": 4096.0,
                "total_bytes": 262144.0,
                "read_bytes": 196608.0,
                "write_bytes": 65536.0,
                "sync_cycles": 0.0,
            },
            "per_macro_cycles": {
                "WDQ_GEMM": 3072.0,
                "SDPA": 768.0,
                "DMA_LOAD": 256.0,
            },
            "per_macro_bytes": {
                "WDQ_GEMM": 131072.0,
                "SDPA": 98304.0,
                "DMA_LOAD": 32768.0,
            },
            "bottleneck_counts": {"compute-bound": 16, "memory-bound": 4},
            "isa_gap_counts": {"opcode_not_supported": 1},
            "data_movement_read_bytes_by_address_space": {"DDR": 131072.0, "VMEM": 65536.0},
            "data_movement_write_bytes_by_address_space": {"VMEM": 32768.0},
            "vmem_region_peak_bytes": {"ping": 49152, "weight": 32768},
            "vmem_region_capacity_bytes": {"ping": 65536, "weight": 65536},
            "vmem_region_peak_utilization": {"ping": 0.75, "weight": 0.5},
            "issues": [],
        }
    )


def _coverage_report() -> ISACoverageReport:
    return ISACoverageReport.model_validate(
        {
            "graph_id": "gemma3-prefill",
            "schedule_kind": "single-core",
            "mapped_descriptor_count": 32,
            "unmapped_block_count": 1,
            "opcode_counts": {"WDQ_GEMM": 16, "SDPA": 8, "DMA_LOAD": 8},
            "gap_counts": {"opcode_not_supported": 1},
            "issues": [],
        }
    )


def _memory_plan() -> MemoryPlanArtifact:
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": "gemma3-prefill",
            "scenario_name": "prefill_seq128",
            "core_mode": "single-core",
            "allocations": [],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 49152,
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 40960,
                        "ddr-backed-staged": 8192,
                        "ddr-persistent": 0,
                    },
                    "fits": True,
                    "allocation_ids": [],
                },
                "weight": {
                    "region_name": "weight",
                    "capacity_bytes": 65536,
                    "peak_bytes": 32768,
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 0,
                        "ddr-backed-staged": 32768,
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
                    "base_symbol": "KV_BASE",
                    "layer_stride_bytes": 1024,
                    "kv_kind_stride_bytes": 512,
                    "token_stride_bytes": 256,
                    "head_stride_bytes": 64,
                    "dim_stride_bytes": 2,
                    "formula": "KV_BASE + layer * 1024",
                }
            ],
            "diagnostics": [
                {
                    "diagnostic_id": "vmem-fit.0",
                    "region_name": "ping",
                    "status": "fit",
                    "required_bytes": 49152,
                    "capacity_bytes": 65536,
                    "offending_node_ids": [],
                    "message": "fits in region",
                }
            ],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.weight.0",
                    "address_kind": "weight",
                    "status": "bound",
                    "symbol": "WEIGHT_BASE",
                    "message": "weight address resolved",
                },
                {
                    "diagnostic_id": "addr.1",
                    "node_id": "nig.quant.0",
                    "address_kind": "quant",
                    "status": "unresolved",
                    "symbol": "QUANT_BASE",
                    "message": "quant address unresolved",
                },
            ],
        }
    )
