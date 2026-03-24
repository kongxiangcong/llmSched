from pathlib import Path

import pytest


def test_build_diagnosis_context_resolves_prefill_single_core(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-context-prefill-single",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"

    ctx = build_diagnosis_context(run_root)

    assert ctx.report_kind == "prefill"
    assert ctx.schedule_kind == "single-core"
    assert ctx.scenario_name == "prefill_seq128"
    assert ctx.top_level_report.run_id == run_root.name
    assert ctx.graph_id == ctx.canonical_graph_ir.graph_id
    assert ctx.descriptor_by_block_id
    normalized_node_id = next(iter(ctx.normalized_node_by_id))
    provenance = ctx.resolve_normalized_node_provenance(normalized_node_id)
    assert provenance.structure_id



def test_build_diagnosis_context_resolves_decode_dual_core(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.pipeline import run_decode_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-context-decode-dual",
        target_relative_path="profiles/targets/riscv_npu_dual_core_v1.json",
        scenario_relative_path="profiles/scenarios/decode_token1_kv2048.json",
        final_stage="performance",
    )
    assert run_decode_evaluation(run_root).status == "completed"

    ctx = build_diagnosis_context(run_root)

    assert ctx.report_kind == "decode"
    assert ctx.schedule_kind == "dual-core"
    assert ctx.scenario_name == "decode_token1_kv2048"
    descriptor = next(iter(ctx.descriptor_ir.descriptors))
    resolved = ctx.resolve_descriptor_for_block(descriptor.schedule_block_id)
    assert resolved is not None
    assert resolved.descriptor_id == descriptor.descriptor_id



def test_build_diagnosis_context_rejects_missing_top_level_report(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-context-missing-report",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )

    with pytest.raises(ValueError, match="top-level evaluation report"):
        build_diagnosis_context(run_root, require_top_level_report=True)



def test_run_diagnosis_analysis_still_succeeds_with_shared_context(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.pipeline import run_diagnosis_analysis, run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-context-workflow",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"

    result = run_diagnosis_analysis(run_root)

    assert result.status == "completed"
    assert (run_root / "reports" / "diagnosis" / "model_structure_report.json").is_file()
    assert (run_root / "reports" / "diagnosis" / "diagnosis_chain_summary.json").is_file()



def test_diag01_and_diag02_builders_accept_context(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report
    from llm_sched.analysis.operator_representation_report_builder import build_operator_representation_report
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-builder-context",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    ctx = build_diagnosis_context(run_root)

    model_report = build_model_structure_report(ctx=ctx)
    operator_report = build_operator_representation_report(ctx=ctx)

    assert model_report.graph_id == ctx.graph_id
    assert operator_report.graph_id == ctx.graph_id
    assert operator_report.node_mappings



def test_stage1_and_stage2_extract_helpers_emit_dataset_ready_rows(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.analysis.model_structure_report_builder import (
        _extract_model_summary_rows,
        _extract_structure_inventory_rows,
        build_model_structure_report,
    )
    from llm_sched.analysis.operator_representation_report_builder import (
        _extract_macro_op_summary_rows,
        _extract_operator_mapping_rows,
        build_operator_representation_report,
    )
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-extract-helpers",
        target_relative_path="profiles/targets/riscv_npu_single_core_v1.json",
        scenario_relative_path="profiles/scenarios/prefill_seq128.json",
        final_stage="performance",
    )
    assert run_prefill_evaluation(run_root).status == "completed"
    ctx = build_diagnosis_context(run_root)
    model_report = build_model_structure_report(ctx=ctx)
    operator_report = build_operator_representation_report(ctx=ctx)

    structure_rows = _extract_structure_inventory_rows(model_report)
    model_rows = _extract_model_summary_rows(model_report)
    mapping_rows = _extract_operator_mapping_rows(operator_report, ctx=ctx)
    macro_rows = _extract_macro_op_summary_rows(operator_report)

    assert structure_rows and set(structure_rows[0]) == {
        "structure_id", "structure_kind", "layer_id", "node_count", "input_shape", "output_shape", "dtype", "parameter_count", "parameter_bytes"
    }
    assert any(row["metric"] == "total_layers" for row in model_rows)
    assert mapping_rows and set(mapping_rows[0]) == {
        "normalized_node_id", "graph_node_id", "canonical_op", "macro_op", "phase", "fallback_kind", "structure_id", "layer_id"
    }
    assert macro_rows and set(macro_rows[0]) == {
        "macro_op", "phase", "node_count", "fallback_count", "helper_count", "native_count"
    }



def test_diag03_diag04_diag05_builders_accept_context_and_emit_extract_rows(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report
    from llm_sched.analysis.operator_representation_report_builder import build_operator_representation_report
    from llm_sched.analysis.resource_demand_report_builder import (
        _extract_layer_demand_rows,
        _extract_structure_demand_rows,
        _extract_subject_demand_rows,
        build_resource_demand_report,
    )
    from llm_sched.analysis.schedule_diagnostics_report_builder import (
        _extract_core_utilization_rows,
        _extract_schedule_block_rows,
        build_schedule_diagnostics_report,
    )
    from llm_sched.analysis.support_matrix_report_builder import (
        _extract_structure_support_rows,
        build_support_matrix_report,
    )
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-stage345-context",
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

    assert _extract_structure_demand_rows(demand_report)
    assert _extract_layer_demand_rows(demand_report)
    assert _extract_subject_demand_rows(demand_report)
    assert _extract_structure_support_rows(support_report)
    assert _extract_schedule_block_rows(schedule_report)
    assert _extract_core_utilization_rows(schedule_report)



def test_diag06_diag07_diag08_builders_accept_context_and_emit_extract_rows(
    tmp_path: Path,
    prepared_run_root_factory,
) -> None:
    from llm_sched.analysis import build_diagnosis_context
    from llm_sched.analysis.architecture_assessment_report_builder import (
        _extract_assessment_summary_rows,
        _extract_recommendation_rows,
        build_architecture_assessment_report,
    )
    from llm_sched.analysis.model_structure_report_builder import build_model_structure_report
    from llm_sched.analysis.operator_representation_report_builder import build_operator_representation_report
    from llm_sched.analysis.performance_diagnostics_report_builder import (
        _extract_bottleneck_summary_rows,
        _extract_node_hotspot_rows,
        _extract_perf_by_structure_rows,
        _extract_phase_breakdown_rows,
        _extract_pressure_summary_rows,
        _extract_structure_bottleneck_rows,
        build_performance_diagnostics_report,
    )
    from llm_sched.analysis.resource_demand_report_builder import build_resource_demand_report
    from llm_sched.analysis.roofline_report_builder import (
        _extract_roofline_points_by_layer_rows,
        build_roofline_report,
    )
    from llm_sched.analysis.schedule_diagnostics_report_builder import build_schedule_diagnostics_report
    from llm_sched.analysis.support_matrix_report_builder import build_support_matrix_report
    from llm_sched.pipeline import run_prefill_evaluation

    run_root = prepared_run_root_factory(
        target_run_root=tmp_path / "run-diagnosis-stage678-context",
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

    assert _extract_perf_by_structure_rows(performance_report)
    assert _extract_phase_breakdown_rows(performance_report)
    assert _extract_node_hotspot_rows(performance_report)
    assert _extract_bottleneck_summary_rows(performance_report)
    assert _extract_structure_bottleneck_rows(performance_report)
    assert _extract_pressure_summary_rows(performance_report)
    assert _extract_roofline_points_by_layer_rows(roofline_report)
    assert _extract_assessment_summary_rows(assessment_report)
    assert _extract_recommendation_rows(assessment_report)
