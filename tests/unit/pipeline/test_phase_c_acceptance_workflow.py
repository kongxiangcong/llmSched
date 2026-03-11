import json
from pathlib import Path


def test_run_phase_c_acceptance_writes_report_for_canonical_workspace_matrix(
    tmp_path: Path,
    minimal_performance_run_root_factory,
) -> None:
    from llm_sched.contracts.phase_c_acceptance_report import PhaseCAcceptanceReport
    from llm_sched.pipeline import run_phase_c_acceptance, run_visualization_packaging

    workspace_root = tmp_path / "phase-c-workspace"
    report_root = workspace_root
    runs_root = workspace_root / "runs"
    run_roots = [
        _prepare_phase_c_run(
            minimal_performance_run_root_factory,
            target_run_root=runs_root / "single-prefill",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            visualization_runner=run_visualization_packaging,
        ),
        _prepare_phase_c_run(
            minimal_performance_run_root_factory,
            target_run_root=runs_root / "single-decode",
            target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            visualization_runner=run_visualization_packaging,
        ),
        _prepare_phase_c_run(
            minimal_performance_run_root_factory,
            target_run_root=runs_root / "dual-prefill",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/prefill_seq128.json",
            visualization_runner=run_visualization_packaging,
        ),
        _prepare_phase_c_run(
            minimal_performance_run_root_factory,
            target_run_root=runs_root / "dual-decode",
            target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
            scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
            visualization_runner=run_visualization_packaging,
        ),
    ]

    result = run_phase_c_acceptance(report_root, workspace_root=workspace_root)

    assert result.status == "completed"
    assert result.report_path == report_root / "reports" / "phase_c_acceptance_report.json"

    report = PhaseCAcceptanceReport.model_validate_json(result.report_path.read_text(encoding="utf-8"))

    assert len(run_roots) == 4
    assert report.status == "ready_for_acceptance"
    assert report.matrix_coverage.present_case_ids == [
        "single-core:prefill",
        "single-core:decode",
        "dual-core:prefill",
        "dual-core:decode",
    ]
    assert report.matrix_coverage.planner_blocked_case_count == 0
    assert report.matrix_coverage.downstream_blocked_case_count == 0
    assert report.remaining_gaps == []
    assert all(case.closure_status == "ready_for_acceptance" for case in report.case_records)
    assert all(case.planner_closure_status == "ready_for_acceptance" for case in report.case_records)
    assert all(case.planner_remaining_gaps == [] for case in report.case_records)
    assert all(case.downstream_closure_status == "ready_for_acceptance" for case in report.case_records)
    assert all(case.downstream_remaining_gaps == [] for case in report.case_records)


def test_run_phase_c_acceptance_rejects_empty_workspace(tmp_path: Path) -> None:
    from llm_sched.pipeline import run_phase_c_acceptance

    workspace_root = tmp_path / "empty-workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    result = run_phase_c_acceptance(workspace_root, workspace_root=workspace_root)

    assert result.status == "failed"
    assert result.report_path is None
    assert "no run roots" in result.diagnostics[0].message.lower()


def _prepare_phase_c_run(
    factory,
    *,
    target_run_root: Path,
    target_relative_path: str,
    scenario_relative_path: str,
    visualization_runner,
) -> Path:
    run_root = factory(
        target_run_root=target_run_root,
        target_relative_path=target_relative_path,
        scenario_relative_path=scenario_relative_path,
    )
    _seed_phase_c_ready_artifacts(run_root)
    assert visualization_runner(run_root).status == "completed"
    return run_root


def _seed_phase_c_ready_artifacts(run_root: Path) -> None:
    from llm_sched.config.loader import load_scenario_profile, load_target_profile
    from llm_sched.contracts.manifest import RunManifest
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact
    from llm_sched.contracts.packed_descriptor_bundle import (
        PackedDescriptorBundle,
        PackedDescriptorFieldPlacement,
        PackedDescriptorRecord,
        assemble_bundle_stream_hex,
        serialize_stream_hex,
    )
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.graph_ir import GraphIR, GraphNode

    manifest = RunManifest.model_validate_json((run_root / "manifest.json").read_text(encoding="utf-8"))
    scenario_profile = load_scenario_profile(manifest.scenario_profile_path)
    target_profile = load_target_profile(manifest.target_profile_path)

    baseline_memory_plan = MemoryPlanArtifact.model_validate_json(
        (run_root / "artifacts" / "memory_plan.json").read_text(encoding="utf-8")
    )
    graph_id = baseline_memory_plan.graph_id
    ready_memory_plan = _memory_plan(
        graph_id=graph_id,
        scenario_name=scenario_profile.scenario_name,
        core_mode=target_profile.core_mode,
    )
    _write_model(run_root / "artifacts" / "memory_plan.json", ready_memory_plan)
    _write_model(
        run_root / "artifacts" / "tiling_plan.json",
        _tiling_plan(
            graph_id=graph_id,
            scenario_name=scenario_profile.scenario_name,
            core_mode=target_profile.core_mode,
        ),
    )
    _write_model(run_root / "artifacts" / "descriptor_ir.json", _descriptor_ir(graph_id))
    _write_model(
        run_root / "reports" / "perf_summary_report.json",
        _perf_summary_report(
            run_id=manifest.run_id,
            graph_id=graph_id,
            schedule_kind=target_profile.core_mode,
        ),
    )
    if scenario_profile.mode == "prefill":
        _write_model(
            run_root / "reports" / "prefill_evaluation_report.json",
            _prefill_report(
                run_id=manifest.run_id,
                graph_id=graph_id,
                scenario_name=scenario_profile.scenario_name,
                schedule_kind=target_profile.core_mode,
            ),
        )
    else:
        _write_model(
            run_root / "reports" / "decode_evaluation_report.json",
            _decode_report(
                run_id=manifest.run_id,
                graph_id=graph_id,
                scenario_name=scenario_profile.scenario_name,
                schedule_kind=target_profile.core_mode,
            ),
        )

    canonical_graph = GraphIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        nodes=[
            GraphNode(
                node_id="graph.input.0",
                op_kind="Input",
                inputs=[],
                outputs=["hidden_states"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={},
                source_ref=[],
                audit_ref=AuditRef(),
            ),
            GraphNode(
                node_id="graph.compute.0",
                op_kind="Linear",
                inputs=["hidden_states"],
                outputs=["out0"],
                shape=[1, 128, 1024],
                dtype="bf16",
                attrs={},
                source_ref=[],
                audit_ref=AuditRef(),
            ),
        ],
    )
    (run_root / "dumps" / "canonical_graph_ir.json").write_text(
        json.dumps(canonical_graph.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )

    word_hex = [f"0x{i:016x}" for i in range(8)]
    record = PackedDescriptorRecord(
        descriptor_id="desc.compute.0",
        schedule_block_id="sched.0",
        opcode="WDQ_GEMM",
        core_id=0,
        stage="compute",
        layout_template="wdq_compute_v1",
        record_index=0,
        stream_offset_bytes=0,
        stream_size_bytes=64,
        word_order="lsw-first",
        byte_order="little-endian",
        word_hex=word_hex,
        packed_hex="0x" + "".join(word[2:] for word in reversed(word_hex)),
        stream_hex=serialize_stream_hex(
            word_hex,
            word_order="lsw-first",
            byte_order="little-endian",
        ),
        field_placements=[
            PackedDescriptorFieldPlacement(
                field_name="opcode",
                field_group="ctrl",
                word_index=0,
                bit_offset=0,
                bit_width=16,
                value_hex="0x0011",
            )
        ],
    )
    packed_bundle = PackedDescriptorBundle(
        graph_id=graph_id,
        encoding_bits=512,
        container_format="aligned-flat-v1",
        record_alignment_bytes=64,
        stream_total_bytes=64,
        stream_hex=assemble_bundle_stream_hex([record], 64),
        descriptors=[record],
    )
    (run_root / "artifacts" / "packed_descriptor_bundle.json").write_text(
        json.dumps(packed_bundle.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def _write_model(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=2), encoding="utf-8")


def _memory_plan(*, graph_id: str, scenario_name: str, core_mode: str):
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact

    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": graph_id,
            "scenario_name": scenario_name,
            "core_mode": core_mode,
            "allocations": [],
            "storage_bindings": [
                {
                    "binding_id": "sb.weight.0",
                    "node_id": "nig.weight.0",
                    "tensor_name": "weight0",
                    "memory_class": "WEIGHT",
                    "source_kind": "weight_tensor",
                    "backing_store": "ddr-backed-staged",
                    "symbol": "WEIGHT_BASE",
                    "binding_scope": "per-tensor-base",
                    "layout": "HSD",
                    "dtype": "int4",
                }
            ],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 49152,
                    "peak_bytes_by_memory_class": {"ACTIVATION": 40960, "WEIGHT": 8192},
                    "peak_bytes_by_backing_store": {
                        "vmem-local": 40960,
                        "ddr-backed-staged": 8192,
                    },
                    "fits": True,
                    "allocation_ids": [],
                }
            },
            "kv_formulas": [],
            "diagnostics": [],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.weight.0",
                    "address_kind": "weight",
                    "status": "bound",
                    "storage_binding_id": "sb.weight.0",
                    "symbol": "WEIGHT_BASE",
                    "message": "weight address resolved",
                }
            ],
        }
    )


def _tiling_plan(*, graph_id: str, scenario_name: str, core_mode: str):
    from llm_sched.contracts.tiling_plan import TilingPlanArtifact

    return TilingPlanArtifact.model_validate(
        {
            "graph_id": graph_id,
            "scenario_name": scenario_name,
            "core_mode": core_mode,
            "candidates": [
                {
                    "candidate_id": "cand.compute.0",
                    "node_id": "nig.compute.0",
                    "macro_op": "WDQ_GEMM",
                    "strategy": "vmem-fit",
                    "m_tile": 1,
                    "n_tile": 128,
                    "k_tile": 128,
                    "read_bytes": 32768,
                    "write_bytes": 16384,
                    "total_vmem_bytes": 49152,
                    "rank": 1,
                    "ranking_reason": "best fit",
                    "quant_alignment_ok": True,
                    "quant_alignment_message": "ok",
                    "source_memory_plan_region_pressure": {"ping": 49152},
                    "resource_summary": {
                        "read_bytes": 32768,
                        "write_bytes": 16384,
                        "total_vmem_bytes": 49152,
                        "dma_bytes": 8192,
                        "region_pressure_bytes": {"ping": 49152},
                        "storage_binding_ids": ["sb.weight.0"],
                        "storage_read_bytes_by_source_kind": {"weight_tensor": 8192},
                        "storage_read_bytes_by_backing_store": {"ddr-backed-staged": 8192},
                    },
                    "issues": [],
                }
            ],
        }
    )


def _descriptor_ir(graph_id: str):
    from llm_sched.ir.descriptor_ir import DescriptorIR

    return DescriptorIR.model_validate(
        {
            "ir_version": "phase-a.v1",
            "graph_id": graph_id,
            "descriptors": [
                {
                    "descriptor_id": "desc.dma.0",
                    "schedule_block_id": "sched.0",
                    "opcode": "DMA_LOAD",
                    "core_id": 0,
                    "encoding_bits": 512,
                    "ctrl_fields": {"macro_op": "WDQ_GEMM", "stage": "dma_in"},
                    "packing_profile": {
                        "stage_family": "dma",
                        "opcode_family": "dma_load",
                        "layout_template": "dma_load_v1",
                        "field_groups": ["ctrl", "shape", "addr", "dma"],
                        "required_ctrl_fields": ["stage", "macro_op"],
                        "required_shape_axes": ["m", "n", "k"],
                        "required_addr_roles": ["src", "dst"],
                        "required_dma_fields": ["length", "channel", "priority"],
                        "field_widths": {
                            "opcode": 16,
                            "control": 16,
                            "shape_m": 16,
                            "shape_n": 16,
                            "shape_k": 16,
                            "src_addr": 64,
                            "dst_addr": 64,
                            "dma_length": 32,
                            "dma_channel": 8,
                            "dma_priority": 4,
                        },
                    },
                    "shape_pack": {"m": 1, "n": 128, "k": 128},
                    "addr_fields": {"src": "WEIGHT_BASE", "dst": "VMEM:ping"},
                    "address_fields": [
                        {
                            "role": "src",
                            "address_space": "DDR",
                            "offset_bytes": 0,
                            "storage_binding_id": "sb.weight.0",
                            "backing_store": "ddr-backed-staged",
                            "symbol": "WEIGHT_BASE",
                            "descriptor_field": "SRC_ADDR",
                            "encoded_width_bits": 64,
                        },
                        {
                            "role": "dst",
                            "address_space": "VMEM",
                            "region_name": "ping",
                            "offset_bytes": 0,
                            "symbol": "VMEM:ping",
                            "descriptor_field": "DST_ADDR",
                            "encoded_width_bits": 64,
                        },
                    ],
                    "dma_fields": {"length": 8192, "channel": 0, "priority": 1},
                    "audit_ref": {"schedule_block_ids": ["sched.0"]},
                }
            ],
        }
    )


def _perf_summary_report(*, run_id: str, graph_id: str, schedule_kind: str):
    from llm_sched.contracts.perf_report import PerfSummaryReport

    return PerfSummaryReport.model_validate(
        {
            "run_id": run_id,
            "graph_id": graph_id,
            "schedule_kind": schedule_kind,
            "vmem_region_peak_bytes": {"ping": 49152},
            "vmem_region_peak_bytes_by_backing_store": {
                "ping": {"vmem-local": 40960, "ddr-backed-staged": 8192}
            },
            "vmem_region_peak_bytes_by_memory_class": {
                "ping": {"ACTIVATION": 40960, "WEIGHT": 8192}
            },
            "vmem_region_capacity_bytes": {"ping": 65536},
            "vmem_region_peak_utilization": {"ping": 0.75},
        }
    )


def _prefill_report(*, run_id: str, graph_id: str, scenario_name: str, schedule_kind: str):
    from llm_sched.contracts.prefill_report import PrefillEvaluationReport

    return PrefillEvaluationReport.model_validate(
        {
            "run_id": run_id,
            "graph_id": graph_id,
            "scenario_name": scenario_name,
            "schedule_kind": schedule_kind,
            "batch": 1,
            "seq_len": 128,
            "mxu_dominant": True,
            "throughput": {
                "total_tokens": 128,
                "estimated_cycles": 4096.0,
                "tokens_per_cycle": 0.03125,
                "cycles_per_token": 32.0,
                "bytes_per_cycle": 64.0,
            },
            "memory_summary": {
                "max_region_utilization": 0.75,
                "overflow_region_count": 0,
                "unresolved_address_count": 0,
                "kv_formula_count": 0,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 8192.0, "VMEM": 40960.0},
                "write_bytes_by_address_space": {"VMEM": 16384.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
                "hottest_region_peak_bytes_by_backing_store": {
                    "vmem-local": 40960,
                    "ddr-backed-staged": 8192,
                },
                "hottest_region_peak_bytes_by_memory_class": {
                    "ACTIVATION": 40960,
                    "WEIGHT": 8192,
                },
            },
            "isa_summary": {"unmapped_block_count": 0, "gap_counts": {}},
            "macro_hotspots": [],
        }
    )


def _decode_report(*, run_id: str, graph_id: str, scenario_name: str, schedule_kind: str):
    from llm_sched.contracts.decode_report import DecodeEvaluationReport

    return DecodeEvaluationReport.model_validate(
        {
            "run_id": run_id,
            "graph_id": graph_id,
            "scenario_name": scenario_name,
            "schedule_kind": schedule_kind,
            "batch": 1,
            "kv_len": 2048,
            "sdpa_decode_present": True,
            "token_latency": {
                "total_tokens": 1,
                "estimated_cycles": 512.0,
                "cycles_per_token": 512.0,
                "projection_cycles": 192.0,
                "kv_io_cycles": 128.0,
                "attention_cycles": 160.0,
                "sync_cycles": 32.0,
                "other_cycles": 0.0,
            },
            "kv_summary": {
                "kv_len": 2048,
                "kv_formula_count": 0,
                "unresolved_address_count": 0,
                "kv_related_cycle_share": 0.56,
                "kv_related_bytes": 8192.0,
            },
            "memory_hotspot": {
                "dominant_address_space": "DDR",
                "read_bytes_by_address_space": {"DDR": 8192.0, "VMEM": 40960.0},
                "write_bytes_by_address_space": {"VMEM": 16384.0},
                "hottest_region": "ping",
                "hottest_region_peak_bytes": 49152,
                "hottest_region_capacity_bytes": 65536,
                "hottest_region_utilization": 0.75,
                "hottest_region_peak_bytes_by_backing_store": {
                    "vmem-local": 40960,
                    "ddr-backed-staged": 8192,
                },
                "hottest_region_peak_bytes_by_memory_class": {
                    "ACTIVATION": 40960,
                    "WEIGHT": 8192,
                },
            },
            "isa_summary": {"unmapped_block_count": 0, "gap_counts": {}},
            "macro_hotspots": [],
        }
    )
