"""Analysis-layer entrypoints."""

from llm_sched.analysis.architecture_assessment_report_builder import (
    build_architecture_assessment_report,
)
from llm_sched.analysis.diagnosis_bundle_builder import build_diagnosis_bundle
from llm_sched.analysis.diagnosis_context import (
    DiagnosisContext,
    build_diagnosis_context,
)
from llm_sched.analysis.diagnosis_dataset_writer import write_diagnosis_dataset
from llm_sched.analysis.memory_planner_closure_builder import build_memory_planner_closure_report
from llm_sched.analysis.model_structure_report_builder import build_model_structure_report
from llm_sched.analysis.operator_representation_report_builder import (
    build_operator_representation_report,
)
from llm_sched.analysis.performance_diagnostics_report_builder import (
    build_performance_diagnostics_report,
)
from llm_sched.analysis.phase_c_acceptance_report_builder import build_phase_c_acceptance_report
from llm_sched.analysis.phase_d_compare_report_builder import build_phase_d_compare_report
from llm_sched.analysis.resource_demand_report_builder import build_resource_demand_report
from llm_sched.analysis.roofline_report_builder import build_roofline_report
from llm_sched.analysis.schedule_diagnostics_report_builder import (
    build_schedule_diagnostics_report,
)
from llm_sched.analysis.support_matrix_report_builder import build_support_matrix_report
from llm_sched.analysis.decode_report_builder import build_decode_evaluation_report
from llm_sched.analysis.descriptor_estimator import (
    build_perf_summary_report,
    estimate_descriptor_analysis,
)
from llm_sched.analysis.nig_estimator import estimate_nig_analysis
from llm_sched.analysis.prefill_report_builder import build_prefill_evaluation_report
from llm_sched.analysis.sweep_report_builder import build_sweep_delta_report
from llm_sched.analysis.visualization_bundle_builder import build_visualization_bundle

__all__ = [
    "write_diagnosis_dataset",
    "build_diagnosis_context",
    "DiagnosisContext",
    "build_architecture_assessment_report",
    "build_diagnosis_bundle",
    "build_memory_planner_closure_report",
    "build_model_structure_report",
    "build_operator_representation_report",
    "build_performance_diagnostics_report",
    "build_phase_c_acceptance_report",
    "build_phase_d_compare_report",
    "build_resource_demand_report",
    "build_roofline_report",
    "build_schedule_diagnostics_report",
    "build_support_matrix_report",
    "build_decode_evaluation_report",
    "build_prefill_evaluation_report",
    "build_perf_summary_report",
    "build_sweep_delta_report",
    "build_visualization_bundle",
    "estimate_descriptor_analysis",
    "estimate_nig_analysis",
]
