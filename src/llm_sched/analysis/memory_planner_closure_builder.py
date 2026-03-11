"""Builder for SPEC-08 memory-planner closure evidence."""

from __future__ import annotations

from llm_sched.contracts.decode_report import DecodeEvaluationReport
from llm_sched.contracts.memory_plan import MemoryPlanArtifact
from llm_sched.contracts.memory_planner_closure_report import (
    MemoryPlannerAcceptanceSummary,
    MemoryPlannerClosureSummary,
    MemoryPlannerClosureReport,
    MemoryPlannerConsumerEvidence,
    MemoryPlannerSurfaceSummary,
)
from llm_sched.contracts.perf_report import PerfSummaryReport
from llm_sched.contracts.prefill_report import PrefillEvaluationReport
from llm_sched.contracts.tiling_plan import TilingPlanArtifact
from llm_sched.contracts.visualization_bundle import VisualizationBundle
from llm_sched.ir.descriptor_ir import DescriptorIR


def build_memory_planner_closure_report(
    *,
    run_id: str,
    scenario_name: str,
    mode: str,
    schedule_kind: str,
    memory_plan_path: str,
    artifact_paths: dict[str, str],
    memory_plan: MemoryPlanArtifact,
    tiling_plan: TilingPlanArtifact | None,
    descriptor_ir: DescriptorIR | None,
    perf_summary_report: PerfSummaryReport | None,
    prefill_report: PrefillEvaluationReport | None,
    decode_report: DecodeEvaluationReport | None,
    visualization_bundle: VisualizationBundle | None,
    workbench_app_js: str | None,
) -> MemoryPlannerClosureReport:
    if mode not in {"prefill", "decode"}:
        raise ValueError(f"unsupported mode for memory-planner closure report: {mode}")
    if schedule_kind not in {"single-core", "dual-core"}:
        raise ValueError(f"unsupported schedule kind for memory-planner closure report: {schedule_kind}")
    if prefill_report is not None and decode_report is not None:
        raise ValueError("memory-planner closure report accepts either prefill_report or decode_report")

    consumers = [
        _build_tile_evidence(tiling_plan, artifact_paths),
        _build_descriptor_evidence(descriptor_ir, artifact_paths),
        _build_perf_evidence(perf_summary_report, artifact_paths),
        _build_top_level_evidence(mode, prefill_report, decode_report, artifact_paths),
        _build_visualization_evidence(visualization_bundle, artifact_paths),
        _build_workbench_evidence(workbench_app_js, artifact_paths),
    ]
    planner_closure = _build_planner_closure(memory_plan)

    required_consumers = [consumer for consumer in consumers if consumer.required_for_acceptance]
    optional_consumers = [consumer for consumer in consumers if not consumer.required_for_acceptance]
    downstream_remaining_gaps = [
        f"{consumer.consumer_id}: {consumer.message}"
        for consumer in required_consumers
        if consumer.status != "verified"
    ]
    remaining_gaps = [
        *[f"planner_closure: {gap}" for gap in planner_closure.remaining_gaps],
        *downstream_remaining_gaps,
    ]

    return MemoryPlannerClosureReport(
        run_id=run_id,
        graph_id=memory_plan.graph_id,
        scenario_name=scenario_name,
        mode=mode,
        schedule_kind=schedule_kind,
        memory_plan_path=memory_plan_path,
        planner_surface=MemoryPlannerSurfaceSummary(
            storage_binding_count=len(memory_plan.storage_bindings),
            region_count=len(memory_plan.region_summaries),
            regions_with_memory_class_attribution=sum(
                1 for region in memory_plan.region_summaries.values() if region.peak_bytes_by_memory_class
            ),
            regions_with_backing_store_attribution=sum(
                1 for region in memory_plan.region_summaries.values() if region.peak_bytes_by_backing_store
            ),
            bound_address_diagnostic_count=sum(
                1 for diagnostic in memory_plan.address_diagnostics if diagnostic.status == "bound"
            ),
            unresolved_address_diagnostic_count=sum(
                1 for diagnostic in memory_plan.address_diagnostics if diagnostic.status == "unresolved"
            ),
        ),
        planner_closure=planner_closure,
        downstream_consumers=consumers,
        acceptance=MemoryPlannerAcceptanceSummary(
            status="ready_for_acceptance" if not remaining_gaps else "in_progress",
            verified_required_consumer_count=sum(
                1 for consumer in required_consumers if consumer.status == "verified"
            ),
            required_consumer_count=len(required_consumers),
            verified_optional_consumer_count=sum(
                1 for consumer in optional_consumers if consumer.status == "verified"
            ),
            optional_consumer_count=len(optional_consumers),
            remaining_gaps=remaining_gaps,
        ),
    )


def _build_planner_closure(memory_plan: MemoryPlanArtifact) -> MemoryPlannerClosureSummary:
    active_regions = [
        region for region in memory_plan.region_summaries.values() if region.peak_bytes > 0
    ]
    attributed_memory_class_region_count = sum(
        1 for region in active_regions if region.peak_bytes_by_memory_class
    )
    attributed_backing_store_region_count = sum(
        1 for region in active_regions if region.peak_bytes_by_backing_store
    )
    overflow_region_names = sorted(
        diagnostic.region_name
        for diagnostic in memory_plan.diagnostics
        if diagnostic.status == "overflow"
    )
    unresolved_address_diagnostic_count = sum(
        1 for diagnostic in memory_plan.address_diagnostics if diagnostic.status == "unresolved"
    )

    remaining_gaps: list[str] = []
    if overflow_region_names:
        remaining_gaps.append(
            "overflow regions remain: " + ", ".join(overflow_region_names)
        )
    if unresolved_address_diagnostic_count:
        remaining_gaps.append("unresolved address diagnostics remain")
    if attributed_memory_class_region_count != len(active_regions):
        remaining_gaps.append("active region memory-class attribution is incomplete")
    if attributed_backing_store_region_count != len(active_regions):
        remaining_gaps.append("active region backing-store attribution is incomplete")

    return MemoryPlannerClosureSummary(
        status="ready_for_acceptance" if not remaining_gaps else "in_progress",
        active_region_count=len(active_regions),
        attributed_memory_class_region_count=attributed_memory_class_region_count,
        attributed_backing_store_region_count=attributed_backing_store_region_count,
        overflow_region_count=len(overflow_region_names),
        unresolved_address_diagnostic_count=unresolved_address_diagnostic_count,
        remaining_gaps=remaining_gaps,
    )


def _build_tile_evidence(
    tiling_plan: TilingPlanArtifact | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if tiling_plan is None:
        return _consumer(
            "tile_planning",
            required=True,
            status="missing_artifact",
            artifact_key="tiling_plan",
            artifact_path=artifact_paths.get("tiling_plan"),
            consumed_fields=["storage_bindings"],
            message="tiling_plan artifact is missing.",
        )

    consumers = [
        candidate
        for candidate in tiling_plan.candidates
        if candidate.resource_summary is not None
        and (
            candidate.resource_summary.storage_binding_ids
            or candidate.resource_summary.storage_read_bytes_by_backing_store
        )
    ]
    if consumers:
        return _consumer(
            "tile_planning",
            required=True,
            status="verified",
            artifact_key="tiling_plan",
            artifact_path=artifact_paths.get("tiling_plan"),
            consumed_fields=["storage_bindings"],
            message=f"{len(consumers)} tile candidates record storage binding usage.",
        )

    return _consumer(
        "tile_planning",
        required=True,
        status="missing_evidence",
        artifact_key="tiling_plan",
        artifact_path=artifact_paths.get("tiling_plan"),
        consumed_fields=["storage_bindings"],
        message="tiling_plan exists but does not expose storage binding usage.",
    )


def _build_descriptor_evidence(
    descriptor_ir: DescriptorIR | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if descriptor_ir is None:
        return _consumer(
            "descriptor_generation",
            required=True,
            status="missing_artifact",
            artifact_key="descriptor_ir",
            artifact_path=artifact_paths.get("descriptor_ir"),
            consumed_fields=["storage_binding_id", "backing_store"],
            message="descriptor_ir artifact is missing.",
        )

    address_fields = [
        field
        for descriptor in descriptor_ir.descriptors
        for field in descriptor.address_fields
    ]
    has_storage_binding = any(field.storage_binding_id for field in address_fields)
    has_backing_store = any(field.backing_store for field in address_fields)
    if has_storage_binding and has_backing_store:
        return _consumer(
            "descriptor_generation",
            required=True,
            status="verified",
            artifact_key="descriptor_ir",
            artifact_path=artifact_paths.get("descriptor_ir"),
            consumed_fields=["storage_binding_id", "backing_store"],
            message="descriptor address fields preserve storage provenance.",
        )

    return _consumer(
        "descriptor_generation",
        required=True,
        status="missing_evidence",
        artifact_key="descriptor_ir",
        artifact_path=artifact_paths.get("descriptor_ir"),
        consumed_fields=["storage_binding_id", "backing_store"],
        message="descriptor_ir exists but structured address fields lack storage provenance.",
    )


def _build_perf_evidence(
    perf_summary_report: PerfSummaryReport | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if perf_summary_report is None:
        return _consumer(
            "performance_estimation",
            required=True,
            status="missing_artifact",
            artifact_key="perf_summary_report",
            artifact_path=artifact_paths.get("perf_summary_report"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="perf_summary_report artifact is missing.",
        )

    if _has_nested_values(perf_summary_report.vmem_region_peak_bytes_by_backing_store) and _has_nested_values(
        perf_summary_report.vmem_region_peak_bytes_by_memory_class
    ):
        return _consumer(
            "performance_estimation",
            required=True,
            status="verified",
            artifact_key="perf_summary_report",
            artifact_path=artifact_paths.get("perf_summary_report"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="perf summary carries per-region backing-store and memory-class attribution.",
        )

    return _consumer(
        "performance_estimation",
        required=True,
        status="missing_evidence",
        artifact_key="perf_summary_report",
        artifact_path=artifact_paths.get("perf_summary_report"),
        consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
        message="perf_summary_report exists but lacks attributed VMEM region evidence.",
    )


def _build_top_level_evidence(
    mode: str,
    prefill_report: PrefillEvaluationReport | None,
    decode_report: DecodeEvaluationReport | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if mode == "prefill":
        if prefill_report is None:
            return _consumer(
                "prefill_evaluation",
                required=True,
                status="missing_artifact",
                artifact_key="prefill_evaluation_report",
                artifact_path=artifact_paths.get("prefill_evaluation_report"),
                consumed_fields=[
                    "hottest_region_peak_bytes_by_backing_store",
                    "hottest_region_peak_bytes_by_memory_class",
                ],
                message="prefill_evaluation_report artifact is missing.",
            )

        if (
            prefill_report.memory_hotspot.hottest_region_peak_bytes_by_backing_store
            and prefill_report.memory_hotspot.hottest_region_peak_bytes_by_memory_class
        ):
            return _consumer(
                "prefill_evaluation",
                required=True,
                status="verified",
                artifact_key="prefill_evaluation_report",
                artifact_path=artifact_paths.get("prefill_evaluation_report"),
                consumed_fields=[
                    "hottest_region_peak_bytes_by_backing_store",
                    "hottest_region_peak_bytes_by_memory_class",
                ],
                message="prefill memory hotspot carries attributed hottest-region evidence.",
            )

        return _consumer(
            "prefill_evaluation",
            required=True,
            status="missing_evidence",
            artifact_key="prefill_evaluation_report",
            artifact_path=artifact_paths.get("prefill_evaluation_report"),
            consumed_fields=[
                "hottest_region_peak_bytes_by_backing_store",
                "hottest_region_peak_bytes_by_memory_class",
            ],
            message="prefill_evaluation_report exists but lacks attributed hottest-region evidence.",
        )

    if decode_report is None:
        return _consumer(
            "decode_evaluation",
            required=True,
            status="missing_artifact",
            artifact_key="decode_evaluation_report",
            artifact_path=artifact_paths.get("decode_evaluation_report"),
            consumed_fields=[
                "hottest_region_peak_bytes_by_backing_store",
                "hottest_region_peak_bytes_by_memory_class",
            ],
            message="decode_evaluation_report artifact is missing.",
        )

    if (
        decode_report.memory_hotspot.hottest_region_peak_bytes_by_backing_store
        and decode_report.memory_hotspot.hottest_region_peak_bytes_by_memory_class
    ):
        return _consumer(
            "decode_evaluation",
            required=True,
            status="verified",
            artifact_key="decode_evaluation_report",
            artifact_path=artifact_paths.get("decode_evaluation_report"),
            consumed_fields=[
                "hottest_region_peak_bytes_by_backing_store",
                "hottest_region_peak_bytes_by_memory_class",
            ],
            message="decode memory hotspot carries attributed hottest-region evidence.",
        )

    return _consumer(
        "decode_evaluation",
        required=True,
        status="missing_evidence",
        artifact_key="decode_evaluation_report",
        artifact_path=artifact_paths.get("decode_evaluation_report"),
        consumed_fields=[
            "hottest_region_peak_bytes_by_backing_store",
            "hottest_region_peak_bytes_by_memory_class",
        ],
        message="decode_evaluation_report exists but lacks attributed hottest-region evidence.",
    )


def _build_visualization_evidence(
    visualization_bundle: VisualizationBundle | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if visualization_bundle is None:
        return _consumer(
            "visualization_packaging",
            required=True,
            status="missing_artifact",
            artifact_key="visualization_bundle",
            artifact_path=artifact_paths.get("visualization_bundle"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="visualization_bundle artifact is missing.",
        )

    regions = [
        region
        for region in visualization_bundle.vmem_view.regions
        if region.peak_bytes_by_backing_store and region.peak_bytes_by_memory_class
    ]
    if regions:
        return _consumer(
            "visualization_packaging",
            required=True,
            status="verified",
            artifact_key="visualization_bundle",
            artifact_path=artifact_paths.get("visualization_bundle"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="visualization bundle preserves attributed VMEM region summaries.",
        )

    return _consumer(
        "visualization_packaging",
        required=True,
        status="missing_evidence",
        artifact_key="visualization_bundle",
        artifact_path=artifact_paths.get("visualization_bundle"),
        consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
        message="visualization_bundle exists but lacks attributed VMEM region summaries.",
    )


def _build_workbench_evidence(
    workbench_app_js: str | None,
    artifact_paths: dict[str, str],
) -> MemoryPlannerConsumerEvidence:
    if workbench_app_js is None:
        return _consumer(
            "visualization_workbench",
            required=False,
            status="missing_artifact",
            artifact_key="visualization_workbench_entry",
            artifact_path=artifact_paths.get("visualization_workbench_entry"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="visualization workbench assets are missing.",
        )

    required_tokens = (
        "Region Backing Store Mix",
        "peak_bytes_by_backing_store",
        "Region Memory Class Mix",
        "peak_bytes_by_memory_class",
    )
    if all(token in workbench_app_js for token in required_tokens):
        return _consumer(
            "visualization_workbench",
            required=False,
            status="verified",
            artifact_key="visualization_workbench_entry",
            artifact_path=artifact_paths.get("visualization_workbench_entry"),
            consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
            message="workbench memory panel visibly surfaces planner attribution.",
        )

    return _consumer(
        "visualization_workbench",
        required=False,
        status="missing_evidence",
        artifact_key="visualization_workbench_entry",
        artifact_path=artifact_paths.get("visualization_workbench_entry"),
        consumed_fields=["peak_bytes_by_backing_store", "peak_bytes_by_memory_class"],
        message="workbench assets exist but memory-panel visibility is incomplete.",
    )


def _consumer(
    consumer_id: str,
    *,
    required: bool,
    status: str,
    artifact_key: str,
    artifact_path: str | None,
    consumed_fields: list[str],
    message: str,
) -> MemoryPlannerConsumerEvidence:
    return MemoryPlannerConsumerEvidence(
        consumer_id=consumer_id,
        required_for_acceptance=required,
        status=status,
        artifact_key=artifact_key,
        artifact_path=artifact_path,
        consumed_fields=consumed_fields,
        message=message,
    )


def _has_nested_values(values: dict[str, dict[str, int]]) -> bool:
    return any(inner for inner in values.values())
