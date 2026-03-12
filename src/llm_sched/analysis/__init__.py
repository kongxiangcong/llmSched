"""Analysis-layer entrypoints."""

from llm_sched.analysis.memory_planner_closure_builder import build_memory_planner_closure_report
from llm_sched.analysis.phase_c_acceptance_report_builder import build_phase_c_acceptance_report
from llm_sched.analysis.phase_d_compare_report_builder import build_phase_d_compare_report
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
    "build_memory_planner_closure_report",
    "build_phase_c_acceptance_report",
    "build_phase_d_compare_report",
    "build_decode_evaluation_report",
    "build_prefill_evaluation_report",
    "build_perf_summary_report",
    "build_sweep_delta_report",
    "build_visualization_bundle",
    "estimate_descriptor_analysis",
    "estimate_nig_analysis",
]
