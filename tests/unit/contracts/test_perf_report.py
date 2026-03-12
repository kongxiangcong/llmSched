from llm_sched.contracts.perf_report import PerfSummaryReport


def test_perf_summary_report_tracks_totals_and_gaps() -> None:
    report = PerfSummaryReport.model_validate(
        {
            "run_id": "run-spec13-001",
            "graph_id": "spec13-graph",
            "schedule_kind": "dual-core",
            "schedule_makespan_slots": 128,
            "per_core_makespan_slots": {"0": 96, "1": 128},
            "per_core_busy_slots": {"0": 88, "1": 120},
            "per_core_idle_slots": {"0": 40, "1": 8},
            "schedule_transfer_slots": 24,
            "schedule_stage_slot_totals": {"compute": 96, "transfer": 24, "dma_in": 16},
            "data_movement_read_bytes_by_address_space": {"DDR": 32768.0, "VMEM": 16384.0},
            "data_movement_write_bytes_by_address_space": {"DDR": 8192.0, "VMEM": 24576.0},
            "vmem_region_peak_bytes": {"ping": 24576, "pong": 12288},
            "vmem_region_peak_bytes_by_memory_class": {
                "ping": {"ACTIVATION": 24576},
                "pong": {"ACTIVATION": 8192, "METADATA": 4096},
            },
            "vmem_region_capacity_bytes": {"ping": 30720, "pong": 30720},
            "vmem_region_peak_utilization": {"ping": 0.8, "pong": 0.4},
            "totals": {
                "estimated_cycles": 1024.0,
                "critical_path_cycles": 128.0,
                "total_bytes": 65536.0,
            },
            "phase_attribution": {
                "projection": {
                    "estimated_cycles": 768.0,
                    "compute_cycles": 768.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "total_bytes": 32768.0,
                    "cycles_per_token": 6.0,
                    "bytes_per_token": 256.0,
                    "occupied_slots": 96.0,
                    "occupied_slots_per_token": 0.75,
                    "read_bytes_by_address_space": {"DDR": 24576.0},
                    "write_bytes_by_address_space": {"VMEM": 8192.0},
                    "read_bytes_by_backing_store": {"ddr-backed-staged": 24576.0},
                    "write_bytes_by_backing_store": {"vmem-local": 8192.0},
                    "read_bytes_by_memory_class": {"WEIGHT": 24576.0},
                    "write_bytes_by_memory_class": {"ACTIVATION": 8192.0},
                },
                "sync": {
                    "estimated_cycles": 256.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 256.0,
                    "total_bytes": 32768.0,
                    "cycles_per_token": 2.0,
                    "bytes_per_token": 256.0,
                    "occupied_slots": 24.0,
                    "occupied_slots_per_token": 0.1875,
                    "read_bytes_by_address_space": {"DDR": 8192.0},
                    "write_bytes_by_address_space": {},
                    "read_bytes_by_backing_store": {"ddr-persistent": 8192.0},
                    "write_bytes_by_backing_store": {},
                    "read_bytes_by_memory_class": {"KV_CACHE": 8192.0},
                    "write_bytes_by_memory_class": {},
                },
                "kv_io": {
                    "estimated_cycles": 0.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
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
                    "estimated_cycles": 0.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
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
                    "estimated_cycles": 0.0,
                    "compute_cycles": 0.0,
                    "memory_cycles": 0.0,
                    "sync_cycles": 0.0,
                    "total_bytes": 0.0,
                    "cycles_per_token": 0.0,
                    "bytes_per_token": 0.0,
                    "occupied_slots": 8.0,
                    "occupied_slots_per_token": 0.0625,
                    "read_bytes_by_address_space": {},
                    "write_bytes_by_address_space": {},
                    "read_bytes_by_backing_store": {},
                    "write_bytes_by_backing_store": {},
                    "read_bytes_by_memory_class": {},
                    "write_bytes_by_memory_class": {},
                },
            },
            "per_macro_cycles": {"WDQ_GEMM": 768.0, "DMA_TRANSFER": 256.0},
            "per_macro_bytes": {"WDQ_GEMM": 32768.0, "DMA_TRANSFER": 32768.0},
            "per_node_cycles": {"nig.node.linear.0": 768.0, "nig.node.transfer.0": 256.0},
            "per_node_bytes": {"nig.node.linear.0": 32768.0, "nig.node.transfer.0": 32768.0},
            "per_layer_cycles": {"0": 768.0, "1": 256.0},
            "per_layer_bytes": {"0": 32768.0, "1": 32768.0},
            "bottleneck_counts": {"compute-bound": 3, "sync-bound": 1},
            "isa_gap_counts": {"opcode_not_supported": 2},
            "issues": [
                {
                    "subject_id": "sched.block.unmapped",
                    "bottleneck": "isa-gap-bound",
                    "message": "ATTENTION_MASK_PREP did not map to a supported opcode",
                }
            ],
        }
    )

    assert report.schedule_kind == "dual-core"
    assert report.schedule_makespan_slots == 128
    assert report.per_core_makespan_slots["1"] == 128
    assert report.per_core_busy_slots["0"] == 88
    assert report.per_core_idle_slots["1"] == 8
    assert report.schedule_transfer_slots == 24
    assert report.schedule_stage_slot_totals["compute"] == 96
    assert report.data_movement_read_bytes_by_address_space["DDR"] == 32768.0
    assert report.data_movement_write_bytes_by_address_space["VMEM"] == 24576.0
    assert report.vmem_region_peak_bytes["ping"] == 24576
    assert report.vmem_region_peak_bytes_by_memory_class["pong"]["METADATA"] == 4096
    assert report.vmem_region_capacity_bytes["pong"] == 30720
    assert report.vmem_region_peak_utilization["ping"] == 0.8
    assert report.totals["estimated_cycles"] == 1024.0
    assert report.totals["critical_path_cycles"] == 128.0
    assert report.phase_attribution["projection"].estimated_cycles == 768.0
    assert report.phase_attribution["projection"].compute_cycles == 768.0
    assert report.phase_attribution["projection"].memory_cycles == 0.0
    assert report.phase_attribution["projection"].sync_cycles == 0.0
    assert report.phase_attribution["sync"].total_bytes == 32768.0
    assert report.phase_attribution["sync"].sync_cycles == 256.0
    assert report.phase_attribution["projection"].cycles_per_token == 6.0
    assert report.phase_attribution["sync"].bytes_per_token == 256.0
    assert report.phase_attribution["projection"].occupied_slots == 96.0
    assert report.phase_attribution["other"].occupied_slots_per_token == 0.0625
    assert report.phase_attribution["projection"].read_bytes_by_address_space["DDR"] == 24576.0
    assert report.phase_attribution["projection"].write_bytes_by_address_space["VMEM"] == 8192.0
    assert report.phase_attribution["sync"].write_bytes_by_address_space == {}
    assert report.phase_attribution["projection"].read_bytes_by_backing_store["ddr-backed-staged"] == 24576.0
    assert report.phase_attribution["projection"].write_bytes_by_backing_store["vmem-local"] == 8192.0
    assert report.phase_attribution["sync"].write_bytes_by_backing_store == {}
    assert report.phase_attribution["projection"].read_bytes_by_memory_class["WEIGHT"] == 24576.0
    assert report.phase_attribution["projection"].write_bytes_by_memory_class["ACTIVATION"] == 8192.0
    assert report.phase_attribution["sync"].write_bytes_by_memory_class == {}
    assert report.per_macro_cycles["WDQ_GEMM"] == 768.0
    assert report.per_node_cycles["nig.node.linear.0"] == 768.0
    assert report.per_node_bytes["nig.node.transfer.0"] == 32768.0
    assert report.per_layer_cycles["0"] == 768.0
    assert report.per_layer_bytes["1"] == 32768.0
    assert report.isa_gap_counts["opcode_not_supported"] == 2
    assert report.issues[0].bottleneck == "isa-gap-bound"
