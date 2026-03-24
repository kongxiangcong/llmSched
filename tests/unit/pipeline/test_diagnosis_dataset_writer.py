from pathlib import Path


def test_write_diagnosis_dataset_writes_core_csvs(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context, write_diagnosis_dataset
    from llm_sched.analysis.architecture_assessment_report_builder import build_architecture_assessment_report
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report
    from llm_sched.analysis.operator_representation_report_builder import build_operator_representation_report
    from llm_sched.analysis.performance_diagnostics_report_builder import build_performance_diagnostics_report
    from llm_sched.analysis.resource_demand_report_builder import build_resource_demand_report
    from llm_sched.analysis.roofline_report_builder import build_roofline_report
    from llm_sched.analysis.schedule_diagnostics_report_builder import build_schedule_diagnostics_report
    from llm_sched.analysis.support_matrix_report_builder import build_support_matrix_report
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-dataset-writer",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    ctx = build_diagnosis_context(run_root)
    model_report = build_model_structure_report(ctx=ctx)
    operator_report = build_operator_representation_report(ctx=ctx)
    demand_report = build_resource_demand_report(ctx=ctx, model_structure_report=model_report, operator_representation_report=operator_report)
    support_report = build_support_matrix_report(ctx=ctx, model_structure_report=model_report, operator_representation_report=operator_report)
    schedule_report = build_schedule_diagnostics_report(ctx=ctx)
    performance_report = build_performance_diagnostics_report(
        ctx=ctx,
        model_structure_report=model_report,
        operator_representation_report=operator_report,
        schedule_diagnostics_report=schedule_report,
        support_matrix_report=support_report,
    )
    roofline_report = build_roofline_report(ctx=ctx, resource_demand_report=demand_report, performance_diagnostics_report=performance_report)
    assessment_report = build_architecture_assessment_report(
        ctx=ctx,
        resource_demand_report=demand_report,
        support_matrix_report=support_report,
        schedule_diagnostics_report=schedule_report,
        performance_diagnostics_report=performance_report,
        roofline_report=roofline_report,
    )

    dataset_dir = tmp_path / "dataset"
    write_diagnosis_dataset(
        dataset_dir,
        ctx=ctx,
        model_structure_report=model_report,
        operator_representation_report=operator_report,
        resource_demand_report=demand_report,
        support_matrix_report=support_report,
        schedule_diagnostics_report=schedule_report,
        performance_diagnostics_report=performance_report,
        roofline_report=roofline_report,
        architecture_assessment_report=assessment_report,
    )

    assert (dataset_dir / "structure_inventory.csv").is_file()
    assert (dataset_dir / "operator_mapping.csv").is_file()
    assert (dataset_dir / "schedule_blocks.csv").is_file()
    assert (dataset_dir / "perf_by_structure.csv").is_file()
    assert (dataset_dir / "subject_structure_map.csv").is_file()
    assert (dataset_dir / "subject_block_map.csv").is_file()
    assert (dataset_dir / "block_descriptor_map.csv").is_file()
    assert (dataset_dir / "realization_gap.csv").is_file()
    assert (dataset_dir / "timeline_loss_detail.csv").is_file()
    assert (dataset_dir / "timeline_loss_summary.csv").is_file()
    header = (dataset_dir / "schedule_blocks.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == "block_id,normalized_node_id,macro_op,schedule_stage,core_id,start_slot,end_slot,duration_slots,stall_reason"



def test_diagnosis_dataset_writer_outputs_joinable_relations(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    import csv
    from llm_sched.pipeline import run_prefill_evaluation, run_diagnosis_analysis

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-joinable-dataset",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    assert run_diagnosis_analysis(run_root).status == "completed"

    dataset_dir = run_root / "reports" / "diagnosis" / "dataset"
    def read_csv(name: str):
        with (dataset_dir / name).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    operator_mapping = read_csv("operator_mapping.csv")
    subject_structure = read_csv("subject_structure_map.csv")
    subject_block = read_csv("subject_block_map.csv")
    schedule_blocks = read_csv("schedule_blocks.csv")
    block_descriptor = read_csv("block_descriptor_map.csv")
    realization_gap = read_csv("realization_gap.csv")
    timeline_summary = read_csv("timeline_loss_summary.csv")

    structure_by_subject = {row["normalized_node_id"]: row["structure_id"] for row in subject_structure}
    block_ids = {row["block_id"] for row in schedule_blocks}
    descriptor_block_ids = {row["block_id"] for row in block_descriptor}

    assert operator_mapping
    assert subject_structure
    assert schedule_blocks
    assert block_descriptor
    assert realization_gap
    assert timeline_summary
    assert all(row["normalized_node_id"] in structure_by_subject for row in operator_mapping)
    assert all(row["block_id"] in block_ids for row in subject_block)
    assert descriptor_block_ids.issubset(block_ids)
    assert all(row["gap_confidence"] in {"low", "medium", "high"} for row in realization_gap)
    assert all(float(row["recoverable_slots_total"]) >= 0.0 for row in timeline_summary)
