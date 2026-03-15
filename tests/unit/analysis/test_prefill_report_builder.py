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
    assert report.mxu_dominant is False
    assert report.throughput.total_tokens == 128
    assert report.throughput.tokens_per_cycle == pytest.approx(128 / 4096.0)
    assert report.throughput.fitted_work_cycles == pytest.approx(4608.0)
    assert report.throughput.tokens_per_fitted_work_cycle == pytest.approx(128 / 4608.0)
    assert report.throughput.fitted_cycles_per_token == pytest.approx(4608.0 / 128.0)
    assert report.throughput.critical_path_cycles == pytest.approx(3072.0)
    assert report.throughput.tokens_per_critical_path_cycle == pytest.approx(128 / 3072.0)
    assert report.throughput.projection_cycles == pytest.approx(1536.0)
    assert report.throughput.projection_fitted_work_cycles == pytest.approx(2048.0)
    assert report.throughput.kv_io_cycles == pytest.approx(0.0)
    assert report.throughput.kv_io_fitted_work_cycles == pytest.approx(0.0)
    assert report.throughput.attention_cycles == pytest.approx(2048.0)
    assert report.throughput.attention_fitted_work_cycles == pytest.approx(2048.0)
    assert report.throughput.sync_cycles == pytest.approx(0.0)
    assert report.throughput.sync_fitted_work_cycles == pytest.approx(0.0)
    assert report.throughput.other_cycles == pytest.approx(512.0)
    assert report.throughput.other_fitted_work_cycles == pytest.approx(512.0)
    assert report.throughput.projection_bytes == pytest.approx(65536.0)
    assert report.throughput.kv_io_bytes == pytest.approx(0.0)
    assert report.throughput.attention_bytes == pytest.approx(163840.0)
    assert report.throughput.sync_bytes == pytest.approx(0.0)
    assert report.throughput.other_bytes == pytest.approx(32768.0)
    assert report.throughput.phase_attribution["projection"].compute_cycles == pytest.approx(1536.0)
    assert report.throughput.phase_attribution["attention"].memory_cycles == pytest.approx(512.0)
    assert report.throughput.phase_attribution["other"].sync_cycles == pytest.approx(0.0)
    assert report.throughput.phase_attribution["projection"].schedule_compression_cycles == pytest.approx(512.0)
    assert report.throughput.phase_attribution["attention"].schedule_compression_ratio == pytest.approx(0.25)
    assert report.throughput.phase_attribution["other"].schedule_overhang_cycles == pytest.approx(0.0)
    assert report.throughput.phase_attribution["projection"].cycles_per_token == pytest.approx(12.0)
    assert report.throughput.phase_attribution["attention"].bytes_per_token == pytest.approx(1280.0)
    assert report.throughput.phase_attribution["projection"].occupied_slots == pytest.approx(1024.0)
    assert report.throughput.phase_attribution["other"].occupied_slots_per_token == pytest.approx(4.0)
    assert report.throughput.phase_attribution["projection"].per_core_occupied_slots == {"0": 1024.0}
    assert report.throughput.phase_attribution["projection"].per_core_span_slots == {"0": 1024.0}
    assert report.throughput.phase_attribution["projection"].occupied_slot_imbalance_slots == pytest.approx(0.0)
    assert report.throughput.phase_attribution["projection"].occupied_slot_balance_ratio == pytest.approx(1.0)
    assert report.throughput.phase_attribution["projection"].span_imbalance_slots == pytest.approx(0.0)
    assert report.throughput.phase_attribution["projection"].span_balance_ratio == pytest.approx(1.0)
    assert report.throughput.phase_attribution["projection"].read_bytes_by_address_space == {"DDR": 49152.0}
    assert report.throughput.phase_attribution["projection"].write_bytes_by_address_space == {"VMEM": 16384.0}
    assert report.throughput.phase_attribution["attention"].read_bytes_by_address_space == {
        "DDR": 81920.0,
        "VMEM": 32768.0,
    }
    assert report.throughput.phase_attribution["projection"].read_bytes_by_backing_store == {
        "ddr-backed-staged": 49152.0
    }
    assert report.throughput.phase_attribution["projection"].write_bytes_by_backing_store == {
        "vmem-local": 16384.0
    }
    assert report.throughput.phase_attribution["attention"].read_bytes_by_backing_store == {
        "ddr-persistent": 81920.0,
        "vmem-local": 32768.0,
    }
    assert report.throughput.phase_attribution["projection"].read_bytes_by_memory_class == {
        "WEIGHT": 49152.0
    }
    assert report.throughput.phase_attribution["projection"].write_bytes_by_memory_class == {
        "ACTIVATION": 16384.0
    }
    assert report.throughput.phase_attribution["attention"].read_bytes_by_memory_class == {
        "ACTIVATION": 32768.0,
        "KV_CACHE": 81920.0,
    }
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
    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class == {
        "ACTIVATION": 40960,
        "QUANT_PARAM": 8192,
    }
    assert report.isa_summary.unmapped_block_count == 1
    assert [hotspot.macro_op for hotspot in report.macro_hotspots] == ["WDQ_GEMM", "SDPA", "DMA_LOAD"]
    assert [hotspot.node_id for hotspot in report.node_hotspots] == [
        "nig.node.linear.0",
        "nig.node.sdpa.0",
        "nig.node.dma_load.0",
    ]
    assert [row.layer_id for row in report.layer_breakdown] == [0, 1]


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


def test_build_prefill_evaluation_report_propagates_hottest_region_memory_class_breakdown() -> None:
    from llm_sched.analysis import build_prefill_evaluation_report

    report = build_prefill_evaluation_report(
        "run-prefill-001",
        _prefill_scenario(),
        _perf_summary_report(),
        _coverage_report(),
        _memory_plan(),
    )

    assert report.memory_hotspot.hottest_region_peak_bytes_by_memory_class == {
        "ACTIVATION": 40960,
        "QUANT_PARAM": 8192,
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
                "fitted_work_cycles": 4608.0,
                "critical_path_cycles": 3072.0,
                "total_bytes": 262144.0,
                "read_bytes": 196608.0,
                "write_bytes": 65536.0,
                "sync_cycles": 0.0,
            },
            "phase_attribution": {
                "projection": {
                    "estimated_cycles": 1536.0,
                    "fitted_work_cycles": 2048.0,
                    "compute_cycles": 1536.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 512.0,
                    "schedule_compression_ratio": 512.0 / 1536.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 65536.0,
                    "cycles_per_token": 12.0,
                    "bytes_per_token": 512.0,
                    "occupied_slots": 1024.0,
                    "occupied_slots_per_token": 8.0,
                    "per_core_occupied_slots": {"0": 1024.0},
                    "per_core_span_slots": {"0": 1024.0},
                    "occupied_slot_imbalance_slots": 0.0,
                    "occupied_slot_balance_ratio": 1.0,
                    "span_imbalance_slots": 0.0,
                    "span_balance_ratio": 1.0,
                    "read_bytes_by_address_space": {"DDR": 49152.0},
                    "write_bytes_by_address_space": {"VMEM": 16384.0},
                    "read_bytes_by_backing_store": {"ddr-backed-staged": 49152.0},
                    "write_bytes_by_backing_store": {"vmem-local": 16384.0},
                    "read_bytes_by_memory_class": {"WEIGHT": 49152.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 16384.0},
                },
                "kv_io": {
                    "estimated_cycles": 0.0,
                    "fitted_work_cycles": 0.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 0.0,
                    "schedule_compression_ratio": 0.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 0.0,
                    "cycles_per_token": 0.0,
                    "bytes_per_token": 0.0,
                    "occupied_slots": 0.0,
                    "occupied_slots_per_token": 0.0,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                    "read_bytes_by_backing_store": {},
                    "write_bytes_by_backing_store": {},
                    "read_bytes_by_memory_class": {},
                    "write_bytes_by_memory_class": {},
                },
                "attention": {
                    "estimated_cycles": 2048.0,
                    "fitted_work_cycles": 2048.0,
                    "compute_cycles": 1536.0,
                    "memory_cycles": 512.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 512.0,
                    "schedule_compression_ratio": 0.25,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 163840.0,
                    "cycles_per_token": 16.0,
                    "bytes_per_token": 1280.0,
                    "occupied_slots": 1536.0,
                    "occupied_slots_per_token": 12.0,
                    "read_bytes_by_address_space": {"DDR": 81920.0, "VMEM": 32768.0},
                    "write_bytes_by_address_space": {"VMEM": 49152.0},
                    "read_bytes_by_backing_store": {"ddr-persistent": 81920.0, "vmem-local": 32768.0},
                    "write_bytes_by_backing_store": {"vmem-local": 49152.0},
                    "read_bytes_by_memory_class": {"KV_CACHE": 81920.0, "ACTIVATION": 32768.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 49152.0},
                },
                "sync": {
                    "estimated_cycles": 0.0,
                    "fitted_work_cycles": 0.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 0.0,
                    "schedule_compression_ratio": 0.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 0.0,
                    "cycles_per_token": 0.0,
                    "bytes_per_token": 0.0,
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
                    "estimated_cycles": 512.0,
                    "fitted_work_cycles": 512.0,
                    "compute_cycles": 256.0,
                    "memory_cycles": 256.0,
                    "sync_cycles": 0.0,
                    "schedule_compression_cycles": 0.0,
                    "schedule_compression_ratio": 0.0,
                    "schedule_overhang_cycles": 0.0,
                    "total_bytes": 32768.0,
                    "cycles_per_token": 4.0,
                    "bytes_per_token": 256.0,
                    "occupied_slots": 512.0,
                    "occupied_slots_per_token": 4.0,
                    "read_bytes_by_address_space": {"VMEM": 16384.0},
                    "write_bytes_by_address_space": {"VMEM": 16384.0},
                    "read_bytes_by_backing_store": {"vmem-local": 16384.0},
                    "write_bytes_by_backing_store": {"vmem-local": 16384.0},
                    "read_bytes_by_memory_class": {"ACTIVATION": 16384.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 16384.0},
                },
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
            "per_node_cycles": {
                "nig.node.linear.0": 3072.0,
                "nig.node.sdpa.0": 768.0,
                "nig.node.dma_load.0": 256.0,
            },
            "per_node_bytes": {
                "nig.node.linear.0": 131072.0,
                "nig.node.sdpa.0": 98304.0,
                "nig.node.dma_load.0": 32768.0,
            },
            "per_layer_cycles": {
                "0": 3072.0,
                "1": 1024.0,
            },
            "per_layer_bytes": {
                "0": 131072.0,
                "1": 131072.0,
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
                    "peak_bytes_by_memory_class": {
                        "ACTIVATION": 40960,
                        "QUANT_PARAM": 8192,
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
                    "peak_bytes_by_memory_class": {
                        "WEIGHT": 32768,
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
