import json
import shutil
from pathlib import Path

import pytest

from llm_sched.config.loader import load_scenario_profile, load_target_profile
from llm_sched.contracts.manifest import RunManifest
from llm_sched.contracts.run_summary import RunSummary
from tests_diagnosis_baseline import (
    get_diagnosis_baseline_case,
    get_diagnosis_baseline_root,
    load_diagnosis_baseline_index_from_root,
)
from llm_sched.pipeline import (
    run_descriptor_generation,
    run_dual_core_scheduling,
    run_frontend_analysis,
    run_memory_planning,
    run_performance_estimation,
    run_single_core_scheduling,
    run_tile_planning,
)


PIPELINE_STAGES = ("frontend", "memory", "tile", "schedule", "descriptor", "performance")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def diagnosis_baseline_root(repo_root: Path) -> Path:
    return get_diagnosis_baseline_root(repo_root)


@pytest.fixture(scope="session")
def diagnosis_baseline_index(diagnosis_baseline_root: Path) -> dict[str, object]:
    return load_diagnosis_baseline_index_from_root(diagnosis_baseline_root)


@pytest.fixture(scope="session")
def diagnosis_baseline_case_loader(
    diagnosis_baseline_root: Path,
    diagnosis_baseline_index: dict[str, object],
):
    def load_case(case_id: str) -> tuple[Path, dict[str, object]]:
        case_entry = get_diagnosis_baseline_case(diagnosis_baseline_index, case_id)
        return diagnosis_baseline_root / case_id, case_entry

    return load_case


@pytest.fixture(scope="session")
def prepared_run_root_factory(tmp_path_factory: pytest.TempPathFactory, repo_root: Path):
    cache_root = tmp_path_factory.mktemp("prepared-run-roots", numbered=False)

    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
        final_stage: str,
    ) -> Path:
        cache_key = (
            Path(target_relative_path).stem,
            Path(scenario_relative_path).stem,
            final_stage,
        )
        prepared_root = cache_root / "__".join(cache_key)
        ready_flag = prepared_root / ".prepared"
        if not ready_flag.is_file():
            if prepared_root.exists():
                shutil.rmtree(prepared_root)
            _write_initialized_run(
                prepared_root,
                repo_root,
                target_relative_path=target_relative_path,
                scenario_relative_path=scenario_relative_path,
            )
            _prepare_run_root_to_stage(
                prepared_root,
                repo_root,
                target_relative_path=target_relative_path,
                final_stage=final_stage,
            )
            ready_flag.write_text("prepared", encoding="utf-8")

        _clone_prepared_run_root(prepared_root, target_run_root)
        _rewrite_run_identity(target_run_root, target_run_root.name)
        return target_run_root

    return factory


@pytest.fixture
def minimal_descriptor_run_root_factory(repo_root: Path):
    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
    ) -> Path:
        _write_initialized_run(
            target_run_root,
            repo_root,
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
        )
        _write_minimal_descriptor_stage_run(
            target_run_root,
            repo_root,
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
        )
        return target_run_root

    return factory


@pytest.fixture
def minimal_performance_run_root_factory(minimal_descriptor_run_root_factory):
    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
    ) -> Path:
        run_root = minimal_descriptor_run_root_factory(
            target_run_root=target_run_root,
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
        )
        assert run_performance_estimation(run_root).status == "completed"
        return run_root

    return factory


@pytest.fixture
def minimal_tile_run_root_factory(repo_root: Path):
    def factory(
        *,
        target_run_root: Path,
        target_relative_path: str,
        scenario_relative_path: str,
    ) -> Path:
        _write_initialized_run(
            target_run_root,
            repo_root,
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
        )
        _write_minimal_tile_stage_run(
            target_run_root,
            repo_root,
            target_relative_path=target_relative_path,
            scenario_relative_path=scenario_relative_path,
        )
        return target_run_root

    return factory


def _prepare_run_root_to_stage(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    final_stage: str,
) -> None:
    if final_stage not in PIPELINE_STAGES:
        raise ValueError(f"unsupported final_stage: {final_stage}")

    target_profile = load_target_profile(repo_root / target_relative_path)
    for stage in PIPELINE_STAGES:
        if stage == "frontend":
            assert run_frontend_analysis(run_root).status == "completed"
        elif stage == "memory":
            assert run_memory_planning(run_root).status == "completed"
        elif stage == "tile":
            assert run_tile_planning(run_root).status == "completed"
        elif stage == "schedule":
            if target_profile.core_mode == "single-core":
                assert run_single_core_scheduling(run_root).status == "completed"
            else:
                assert run_dual_core_scheduling(run_root).status == "completed"
        elif stage == "descriptor":
            assert run_descriptor_generation(run_root).status == "completed"
        elif stage == "performance":
            assert run_performance_estimation(run_root).status == "completed"
        if stage == final_stage:
            return


def _clone_prepared_run_root(prepared_root: Path, target_run_root: Path) -> None:
    if target_run_root.exists():
        shutil.rmtree(target_run_root)
    shutil.copytree(prepared_root, target_run_root)
    prepared_flag = target_run_root / ".prepared"
    if prepared_flag.exists():
        prepared_flag.unlink()


def _rewrite_run_identity(run_root: Path, run_id: str) -> None:
    manifest_path = run_root / "manifest.json"
    run_summary_path = run_root / "run-summary.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    run_summary = RunSummary.model_validate_json(run_summary_path.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps(manifest.model_copy(update={"run_id": run_id}).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    run_summary_path.write_text(
        json.dumps(run_summary.model_copy(update={"run_id": run_id}).model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )


def _write_initialized_run(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
) -> None:
    run_root.mkdir(parents=True, exist_ok=True)
    for relative in ("artifacts", "reports", "logs", "dumps"):
        (run_root / relative).mkdir(parents=True, exist_ok=True)

    manifest = RunManifest(
        run_id=run_root.name,
        contract_version="phase-a.v1",
        status="initialized",
        model_path=str((repo_root / "models" / "gemma3_1b" / "model_q4f16.onnx").resolve()),
        target_profile_path=str((repo_root / target_relative_path).resolve()),
        scenario_profile_path=str((repo_root / scenario_relative_path).resolve()),
        artifact_index={
            "manifest": "manifest.json",
            "artifacts_dir": "artifacts",
            "reports_dir": "reports",
            "logs_dir": "logs",
            "dumps_dir": "dumps",
        },
    )
    (run_root / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    (run_root / "run-summary.json").write_text(
        json.dumps(
            RunSummary(
                run_id=run_root.name,
                status="initialized",
                exit_code=0,
                manifest_path="manifest.json",
                diagnostics=[],
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_minimal_descriptor_stage_run(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
) -> None:
    from llm_sched.ir.io import dump_ir_document

    target_profile = load_target_profile(repo_root / target_relative_path)
    scenario_profile = load_scenario_profile(repo_root / scenario_relative_path)
    graph_id = f"workflow-minimal::{Path(target_relative_path).stem}::{scenario_profile.scenario_name}"

    if target_profile.core_mode == "single-core":
        descriptor_ir = _minimal_single_core_descriptor_ir(graph_id)
        coverage_report = _minimal_single_core_coverage_report(graph_id)
        schedule_ir = _minimal_single_core_schedule_ir(graph_id)
        schedule_artifact_name = "schedule_ir"
    else:
        descriptor_ir = _minimal_dual_core_descriptor_ir(graph_id)
        coverage_report = _minimal_dual_core_coverage_report(graph_id)
        schedule_ir = _minimal_dual_core_schedule_ir(graph_id)
        schedule_artifact_name = "dual_core_schedule_ir"

    memory_plan = _minimal_memory_plan(
        graph_id=graph_id,
        scenario_name=scenario_profile.scenario_name,
        core_mode=target_profile.core_mode,
        scenario_mode=scenario_profile.mode,
    )

    descriptor_path = run_root / "artifacts" / "descriptor_ir.json"
    coverage_path = run_root / "reports" / "isa_coverage_report.json"
    memory_plan_path = run_root / "artifacts" / "memory_plan.json"
    schedule_path = run_root / "artifacts" / f"{schedule_artifact_name}.json"

    dump_ir_document(descriptor_ir, descriptor_path)
    _write_json_model(coverage_path, coverage_report)
    _write_json_model(memory_plan_path, memory_plan)
    dump_ir_document(schedule_ir, schedule_path)
    _update_manifest_artifact_index(
        run_root,
        {
            "descriptor_ir": "artifacts/descriptor_ir.json",
            "isa_coverage_report": "reports/isa_coverage_report.json",
            "memory_plan": "artifacts/memory_plan.json",
            schedule_artifact_name: f"artifacts/{schedule_artifact_name}.json",
        },
    )


def _write_minimal_tile_stage_run(
    run_root: Path,
    repo_root: Path,
    *,
    target_relative_path: str,
    scenario_relative_path: str,
) -> None:
    from llm_sched.ir.io import dump_ir_document
    from llm_sched.planning.memory_planner import plan_memory_artifact
    from llm_sched.planning.tile_planner import plan_tiling_artifact

    target_profile = load_target_profile(repo_root / target_relative_path)
    scenario_profile = load_scenario_profile(repo_root / scenario_relative_path)
    graph_id = f"workflow-tile-minimal::{Path(target_relative_path).stem}::{scenario_profile.scenario_name}"

    if target_profile.core_mode == "single-core":
        bound_nig = _minimal_single_core_bound_nig(graph_id)
    else:
        bound_nig = _minimal_dual_core_bound_nig(graph_id)

    memory_plan = plan_memory_artifact(bound_nig, target_profile, scenario_profile)
    tiling_plan = plan_tiling_artifact(bound_nig, memory_plan, target_profile, scenario_profile)

    bound_nig_path = run_root / "dumps" / "bound_nig_ir.json"
    memory_plan_path = run_root / "artifacts" / "memory_plan.json"
    tiling_plan_path = run_root / "artifacts" / "tiling_plan.json"

    dump_ir_document(bound_nig, bound_nig_path)
    _write_json_model(memory_plan_path, memory_plan)
    _write_json_model(tiling_plan_path, tiling_plan)
    _update_manifest_artifact_index(
        run_root,
        {
            "bound_nig_ir": "dumps/bound_nig_ir.json",
            "memory_plan": "artifacts/memory_plan.json",
            "tiling_plan": "artifacts/tiling_plan.json",
        },
    )


def _update_manifest_artifact_index(run_root: Path, updates: dict[str, str]) -> None:
    manifest_path = run_root / "manifest.json"
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps(
            manifest.model_copy(
                update={"artifact_index": {**manifest.artifact_index, **updates}},
                deep=True,
            ).model_dump(mode="json"),
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_json_model(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=2), encoding="utf-8")


def _minimal_single_core_descriptor_ir(graph_id: str):
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import DescriptorIR, DescriptorPackingProfile, DescriptorRecord

    return DescriptorIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute",
                opcode="WDQ_GEMM",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"macro_op": "WDQ_GEMM", "stage": "compute", "duration_slots": 32},
                packing_profile=DescriptorPackingProfile(
                    stage_family="compute",
                    opcode_family="tensor_compute",
                    layout_template="wdq_compute_v1",
                    field_groups=["ctrl", "shape"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    field_widths={
                        "opcode": 16,
                        "control": 16,
                        "shape_m": 16,
                        "shape_n": 16,
                        "shape_k": 16,
                    },
                ),
                shape_pack={"m": 48, "n": 128, "k": 128},
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute"],
                    source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
                ),
            )
        ],
    )


def _minimal_single_core_bound_nig(graph_id: str):
    return _make_bound_nig_ir(
        graph_id,
        [
            _make_wdq_gemm_node(
                node_id="nig.node.linear.0",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act0",
                output_name="out0",
            )
        ],
    )


def _minimal_dual_core_bound_nig(graph_id: str):
    return _make_bound_nig_ir(
        graph_id,
        [
            _make_wdq_gemm_node(
                node_id="nig.node.linear.0",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="act0",
                output_name="mid0",
            ),
            _make_wdq_gemm_node(
                node_id="nig.node.linear.1",
                output_shape=[1, 128, 1024],
                group_size=128,
                input_name="mid0",
                output_name="out1",
            ),
        ],
    )


def _make_bound_nig_ir(graph_id: str, nodes: list[object]):
    from llm_sched.ir.nig import NIGIR

    return NIGIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        binding_state="bound",
        nodes=nodes,
    )


def _make_wdq_gemm_node(
    *,
    node_id: str,
    output_shape: list[int],
    group_size: int,
    input_name: str,
    output_name: str,
):
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="int4",
        activation_dtype="bf16",
        group_size=group_size,
        quant_mode="per-group",
        scale_present=True,
        zero_point_present=True,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="WDQ_GEMM",
        inputs=[input_name, "weight", "scale", "zp"],
        outputs=[output_name],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["WDQ_GEMM"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                input_name: "ACTIVATION",
                "weight": "WEIGHT",
                "scale": "QUANT_PARAM",
                "zp": "QUANT_PARAM",
            },
            output_memory_classes={output_name: "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
        ),
    )


def _minimal_dual_core_descriptor_ir(graph_id: str):
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.descriptor_ir import (
        AddressField,
        DescriptorIR,
        DescriptorPackingProfile,
        DescriptorRecord,
        TransferFields,
    )

    return DescriptorIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        descriptors=[
            DescriptorRecord(
                descriptor_id="desc.compute.0",
                schedule_block_id="sched.block.compute",
                opcode="SDPA_DECODE",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"macro_op": "SDPA_DECODE", "stage": "compute", "duration_slots": 40},
                packing_profile=DescriptorPackingProfile(
                    stage_family="compute",
                    opcode_family="tensor_compute",
                    layout_template="sdpa_decode_compute_v1",
                    field_groups=["ctrl", "shape"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    field_widths={
                        "opcode": 16,
                        "control": 16,
                        "shape_m": 16,
                        "shape_n": 16,
                        "shape_k": 16,
                    },
                ),
                shape_pack={"m": 1, "n": 128, "k": 128},
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute"]),
            ),
            DescriptorRecord(
                descriptor_id="desc.transfer.0",
                schedule_block_id="sched.transfer.0",
                opcode="CORE_LINK_COPY",
                core_id=0,
                encoding_bits=512,
                ctrl_fields={"macro_op": "KVLOAD", "stage": "transfer", "duration_slots": 12},
                packing_profile=DescriptorPackingProfile(
                    stage_family="transfer",
                    opcode_family="core_link_transfer",
                    layout_template="core_link_transfer_v1",
                    field_groups=["ctrl", "shape", "addr", "dma", "transfer"],
                    required_ctrl_fields=["stage", "macro_op"],
                    required_shape_axes=["m", "n", "k"],
                    required_addr_roles=["src", "dst"],
                    required_dma_fields=["length", "channel", "priority"],
                    field_widths={
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
                        "transfer_kind": 8,
                        "transfer_src_core_id": 8,
                        "transfer_dst_core_id": 8,
                        "transfer_bytes": 32,
                    },
                ),
                shape_pack={"m": 1, "n": 128, "k": 128},
                addr_fields={"src": "VMEM:ping", "dst": "VMEM:pong"},
                address_fields=[
                    AddressField(
                        role="src",
                        address_space="VMEM",
                        region_name="ping",
                        offset_bytes=0,
                        symbol="VMEM:ping",
                        descriptor_field="SRC_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                    AddressField(
                        role="dst",
                        address_space="VMEM",
                        region_name="pong",
                        offset_bytes=0,
                        symbol="VMEM:pong",
                        descriptor_field="DST_ADDR",
                        encoded_width_bits=64,
                        uses_addr_ext=False,
                    ),
                ],
                dma_fields={"length": 16384, "channel": 0, "priority": 1},
                transfer_fields=TransferFields(
                    kind="core_link",
                    src_core_id=0,
                    dst_core_id=1,
                    transfer_bytes=16384,
                ),
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.transfer.0"],
                    source_ids=["onnx::/model/layers.0/self_attn/kv_cache_transfer"],
                ),
            ),
        ],
    )


def _minimal_single_core_coverage_report(graph_id: str):
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport

    return ISACoverageReport(
        graph_id=graph_id,
        schedule_kind="single-core",
        mapped_descriptor_count=1,
        unmapped_block_count=0,
        opcode_counts={"WDQ_GEMM": 1},
        gap_counts={},
        issues=[],
    )


def _minimal_dual_core_coverage_report(graph_id: str):
    from llm_sched.contracts.isa_coverage_report import ISACoverageReport

    return ISACoverageReport(
        graph_id=graph_id,
        schedule_kind="dual-core",
        mapped_descriptor_count=2,
        unmapped_block_count=0,
        opcode_counts={"SDPA_DECODE": 1, "CORE_LINK_COPY": 1},
        gap_counts={},
        issues=[],
    )


def _minimal_single_core_schedule_ir(graph_id: str):
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    return ScheduleIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        core_mode="single-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.block.compute",
                core_id=0,
                node_id="nig.node.linear.0",
                macro_op="WDQ_GEMM",
                stage="compute",
                tiling_candidate_id="cand.compute.0",
                resource_set=["WDQ", "MXU"],
                buffer_binding={"activation": "ping", "output": "pong"},
                barrier_in=[],
                barrier_out=[],
                depends_on=[],
                issue_slot=0,
                duration_slots=32,
                order_key=0,
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.block.compute"],
                    source_ids=["onnx::/model/layers.0/self_attn/q_proj/MatMul_output_0"],
                ),
            )
        ],
    )


def _minimal_dual_core_schedule_ir(graph_id: str):
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR

    return ScheduleIR(
        ir_version="phase-a.v1",
        graph_id=graph_id,
        core_mode="dual-core",
        blocks=[
            ScheduleBlock(
                block_id="sched.block.compute",
                core_id=0,
                node_id="nig.node.attn.decode",
                macro_op="SDPA_DECODE",
                stage="compute",
                tiling_candidate_id="cand.decode.0",
                resource_set=["DMA", "VPU"],
                buffer_binding={"kv": "DDR", "output": "ping"},
                barrier_in=[],
                barrier_out=[],
                depends_on=[],
                issue_slot=0,
                duration_slots=40,
                order_key=0,
                audit_ref=AuditRef(schedule_block_ids=["sched.block.compute"]),
            ),
            ScheduleBlock(
                block_id="sched.transfer.0",
                core_id=0,
                peer_core_id=1,
                node_id="nig.node.kvload.0",
                macro_op="KVLOAD",
                stage="transfer",
                tiling_candidate_id=None,
                resource_set=["Core Link"],
                buffer_binding={"src": "ping", "dst": "pong"},
                barrier_in=["sync.transfer.0.in"],
                barrier_out=["sync.transfer.0.out"],
                depends_on=["sched.block.compute"],
                issue_slot=40,
                duration_slots=12,
                transfer_kind="core_link",
                transfer_bytes=16384,
                sync_cost_cycles=4,
                order_key=1,
                audit_ref=AuditRef(
                    schedule_block_ids=["sched.transfer.0"],
                    source_ids=["onnx::/model/layers.0/self_attn/kv_cache_transfer"],
                ),
            ),
        ],
    )


def _minimal_memory_plan(
    *,
    graph_id: str,
    scenario_name: str,
    core_mode: str,
    scenario_mode: str,
):
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact

    if scenario_mode == "decode":
        return MemoryPlanArtifact.model_validate(
            {
                "graph_id": graph_id,
                "scenario_name": scenario_name,
                "core_mode": core_mode,
                "allocations": [],
                "region_summaries": {
                    "ping": {
                        "region_name": "ping",
                        "capacity_bytes": 65536,
                        "peak_bytes": 40960,
                        "peak_bytes_by_memory_class": {"ACTIVATION": 32768, "KV_CACHE": 8192},
                        "fits": True,
                        "allocation_ids": [],
                    },
                    "pong": {
                        "region_name": "pong",
                        "capacity_bytes": 65536,
                        "peak_bytes": 32768,
                        "peak_bytes_by_memory_class": {"ACTIVATION": 32768},
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
                    }
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
                        "node_id": "nig.quant.0",
                        "address_kind": "quant",
                        "status": "unresolved",
                        "symbol": "QUANT_BASE",
                        "message": "quant address unresolved",
                    },
                ],
            }
        )
    return MemoryPlanArtifact.model_validate(
        {
            "graph_id": graph_id,
            "scenario_name": scenario_name,
            "core_mode": core_mode,
            "allocations": [],
            "region_summaries": {
                "ping": {
                    "region_name": "ping",
                    "capacity_bytes": 65536,
                    "peak_bytes": 49152,
                    "peak_bytes_by_memory_class": {"ACTIVATION": 49152},
                    "fits": True,
                    "allocation_ids": [],
                },
                "weight": {
                    "region_name": "weight",
                    "capacity_bytes": 65536,
                    "peak_bytes": 32768,
                    "peak_bytes_by_memory_class": {"WEIGHT": 32768},
                    "fits": True,
                    "allocation_ids": [],
                },
            },
            "kv_formulas": [],
            "diagnostics": [],
            "address_diagnostics": [
                {
                    "diagnostic_id": "addr.0",
                    "node_id": "nig.weight.0",
                    "address_kind": "weight",
                    "status": "bound",
                    "symbol": "WEIGHT_BASE",
                    "message": "weight address resolved",
                }
            ],
        }
    )
