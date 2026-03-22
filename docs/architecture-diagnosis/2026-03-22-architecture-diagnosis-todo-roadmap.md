# Architecture Diagnosis To-Do Roadmap

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this roadmap task-by-task.

**Goal:** Build an additive architecture-diagnosis layer on top of the frozen `2026-03-22` evaluation-compiler baseline, producing structured diagnosis reports, a diagnosis bundle, and a diagnosis workbench without reopening the current closeout judgment.

**Architecture:** Keep existing Phase A-E artifacts as canonical upstream inputs. Add a new diagnosis track under `reports/diagnosis/`, then implement the new layer in dependency order: structure -> representation -> demand/support -> schedule/perf -> roofline/assessment -> bundle/workbench.

**Tech Stack:** Python, Pydantic contracts, Typer CLI, static HTML/JS workbench builders, `pytest` unit/pipeline/smoke tests

---

## Usage Rules

- 每个 checkbox 都应该可以独立标记。
- 默认按里程碑顺序推进，不要跳过上游 diagnosis reports 直接做 UI。
- 每完成一项，都要补对应测试与文档同步。
- 没有验证证据前，不要勾选完成。
- 当前 roadmap 只覆盖 diagnosis track，不重开现有 baseline closeout judgment。

## Milestones

- `D0`: Baseline Freeze And Diagnosis Skeleton
- `D1`: Structural Diagnosis Foundation
- `D2`: Execution Diagnosis Foundation
- `D3`: Synthesis, Packaging, And Product Surface

## D0: Baseline Freeze And Diagnosis Skeleton

- [x] Confirm the frozen baseline interpretation stays unchanged
  - Scope:
    - Preserve `2026-03-22` branch state as the baseline node.
    - Treat new diagnosis work as additive, not as reopening `SPEC-13/14/15/16/19`.
  - Files:
    - Read/keep aligned: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
    - Read/keep aligned: `D:/workspace/llmSched/docs/architecture-diagnosis/2026-03-22-architecture-diagnosis-design.md`
  - Done when:
    - baseline preservation rules remain explicit in canonical docs.

- [x] Create the diagnosis workflow skeleton
  - Scope:
    - Add the first diagnosis-oriented pipeline entrypoint.
    - Reserve `reports/diagnosis/` as the canonical diagnosis output directory.
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/diagnosis_common.py`
    - Create: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/__init__.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/cli/main.py`
    - Test: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_analysis_workflow.py`
    - Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_diagnosis_analysis.py`
  - Verification:
    - `python -m pytest tests/unit/pipeline/test_diagnosis_analysis_workflow.py -q`

## D1: Structural Diagnosis Foundation

### DIAG-01 Model Structure Report

- [x] Define `DIAG-01` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/model_structure_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_model_structure_report.py`
  - Contract must cover:
    - `run_id`
    - `graph_id`
    - `scenario_name`
    - `model_summary`
    - `structures[]`
    - `layers[]`
    - `node_index[]`

- [x] Implement `DIAG-01` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/model_structure_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_model_structure_report_builder.py`
  - Builder must answer:
    - layer/block/subgraph hierarchy
    - structure classification
    - structure-to-node traceability

- [x] Verify `DIAG-01`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_model_structure_report.py tests/unit/analysis/test_model_structure_report_builder.py -q`

### DIAG-02 Operator Representation Report

- [x] Define `DIAG-02` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/operator_representation_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_operator_representation_report.py`
  - Contract must cover:
    - `node_mappings[]`
    - `macro_groups[]`
    - `phase_groups[]`
    - `fallback_entries[]`
    - `traceability_index`

- [x] Implement `DIAG-02` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/operator_representation_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_operator_representation_report_builder.py`
  - Builder must answer:
    - graph node -> canonical op -> macro-op -> phase
    - helper/fallback surfaces
    - traceability anchors into downstream schedule/descriptor stages

- [x] Verify `DIAG-02`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_operator_representation_report.py tests/unit/analysis/test_operator_representation_report_builder.py -q`

### DIAG-03 Resource Demand Report

- [x] Define `DIAG-03` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/resource_demand_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_resource_demand_report.py`
  - Contract must cover:
    - `node_demands[]`
    - `layer_demands[]`
    - `structure_demands[]`
    - `totals`
    - `assumptions`

- [x] Implement `DIAG-03` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/resource_demand_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_resource_demand_report_builder.py`
  - Builder must answer:
    - compute demand
    - IO demand
    - storage demand
    - dependency depth
    - layer/structure aggregation

- [x] Verify `DIAG-03`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_resource_demand_report.py tests/unit/analysis/test_resource_demand_report_builder.py -q`

### DIAG-04 Support Matrix Report

- [x] Define `DIAG-04` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/support_matrix_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_support_matrix_report.py`
  - Contract must cover:
    - `node_support_entries[]`
    - `layer_support_summary[]`
    - `structure_support_summary[]`
    - `reason_counts`
    - `critical_gaps[]`

- [x] Implement `DIAG-04` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/support_matrix_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_support_matrix_report_builder.py`
  - Builder must answer:
    - native / constrained / fallback / unsupported classification
    - layer/structure support aggregation
    - gap reasons and critical unsupported structures

- [x] Verify `DIAG-04`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_support_matrix_report.py tests/unit/analysis/test_support_matrix_report_builder.py -q`

## D2: Execution Diagnosis Foundation

### DIAG-05 Schedule Diagnostics Report

- [x] Define `DIAG-05` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/schedule_diagnostics_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_schedule_diagnostics_report.py`
  - Contract must cover:
    - `blocks[]`
    - `core_lanes[]`
    - `idle_spans[]`
    - `stall_events[]`
    - `critical_path_blocks[]`
    - `resource_contention_summary`

- [x] Implement `DIAG-05` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/schedule_diagnostics_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_schedule_diagnostics_report_builder.py`
  - Builder must answer:
    - block start/end/span from `issue_slot` + `duration_slots`
    - per-core occupancy
    - idle spans
    - wait/stall reasons
    - critical path and contention

- [x] Verify `DIAG-05`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_schedule_diagnostics_report.py tests/unit/analysis/test_schedule_diagnostics_report_builder.py -q`

### DIAG-06 Performance Diagnostics Report

- [x] Define `DIAG-06` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/performance_diagnostics_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_performance_diagnostics_report.py`
  - Contract must cover:
    - `phase_breakdown`
    - `layer_hotspots`
    - `node_hotspots`
    - `critical_path_summary`
    - `bottleneck_classification`
    - `bandwidth_diagnostics`
    - `vmem_diagnostics`
    - `support_gap_diagnostics`

- [x] Implement `DIAG-06` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/performance_diagnostics_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_performance_diagnostics_report_builder.py`
  - Builder must answer:
    - phase/layer/node hotspots
    - fitted vs estimated divergence
    - critical path
    - bottleneck taxonomy
    - bandwidth / VMEM / support gap drilldown

- [x] Verify `DIAG-06`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_performance_diagnostics_report.py tests/unit/analysis/test_performance_diagnostics_report_builder.py -q`

## D3: Synthesis, Packaging, And Product Surface

### DIAG-07 Roofline Report

- [x] Define `DIAG-07` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/roofline_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_roofline_report.py`
  - Contract must cover:
    - `compute_ceiling`
    - `bandwidth_ceilings[]`
    - `node_points[]`
    - `layer_points[]`
    - `dominant_bound_summary`
    - `headroom_summary`

- [x] Implement `DIAG-07` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/roofline_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_roofline_report_builder.py`
  - Builder must answer:
    - compute ceiling
    - bandwidth ceilings
    - arithmetic intensity points
    - dominant bound
    - headroom summary

- [x] Verify `DIAG-07`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_roofline_report.py tests/unit/analysis/test_roofline_report_builder.py -q`

### DIAG-08 Architecture Assessment Report

- [x] Define `DIAG-08` contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/architecture_assessment_report.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_architecture_assessment_report.py`
  - Contract must cover:
    - `overall_assessment`
    - `top_bottlenecks[]`
    - `top_support_gaps[]`
    - `top_timeline_losses[]`
    - `recommendations[]`
    - `confidence_summary`

- [x] Implement `DIAG-08` builder
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/architecture_assessment_report_builder.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_architecture_assessment_report_builder.py`
  - Builder must answer:
    - overall suitability
    - top bottlenecks
    - top unsupported/constrained structures
    - top timeline losses
    - ranked recommendations

- [x] Verify `DIAG-08`
  - Verification:
    - `python -m pytest tests/unit/contracts/test_architecture_assessment_report.py tests/unit/analysis/test_architecture_assessment_report_builder.py -q`

### DIAG-09 Diagnosis Bundle And Packaging

- [x] Define diagnosis bundle contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/diagnosis_bundle.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_diagnosis_bundle.py`
  - Contract must cover:
    - diagnosis metadata
    - report references
    - available panels
    - optional compare payloads

- [x] Implement diagnosis bundle builder and packaging workflow
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/analysis/diagnosis_bundle_builder.py`
    - Create: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_packaging.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/__init__.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/cli/main.py`
    - Test: `D:/workspace/llmSched/tests/unit/analysis/test_diagnosis_bundle_builder.py`
    - Test: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_packaging_workflow.py`

- [x] Verify diagnosis packaging
  - Verification:
    - `python -m pytest tests/unit/contracts/test_diagnosis_bundle.py tests/unit/analysis/test_diagnosis_bundle_builder.py tests/unit/pipeline/test_diagnosis_packaging_workflow.py -q`

### Diagnosis Workbench

- [x] Define diagnosis workbench contract
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/contracts/diagnosis_workbench.py`
    - Test: `D:/workspace/llmSched/tests/unit/contracts/test_diagnosis_workbench.py`
  - Workbench must expose:
    - `summary`
    - `model-structure`
    - `operator-representation`
    - `support-matrix`
    - `resource-demand`
    - `schedule`
    - `timeline`
    - `performance`
    - `roofline`
    - `assessment`
    - optional `compare`

- [x] Implement diagnosis workbench builder and workflow
  - Files:
    - Create: `D:/workspace/llmSched/src/llm_sched/visualization/diagnosis_workbench_builder.py`
    - Create: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_workbench.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/__init__.py`
    - Modify: `D:/workspace/llmSched/src/llm_sched/cli/main.py`
    - Test: `D:/workspace/llmSched/tests/unit/visualization/test_diagnosis_workbench_builder.py`
    - Test: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_workbench_workflow.py`
    - Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_diagnosis_workbench.py`

- [x] Verify diagnosis workbench
  - Verification:
    - `python -m pytest tests/unit/contracts/test_diagnosis_workbench.py tests/unit/visualization/test_diagnosis_workbench_builder.py tests/unit/pipeline/test_diagnosis_workbench_workflow.py -q`

## Final Integration And Proof

- [x] Add focused end-to-end smoke proof for the diagnosis track
  - Files:
    - Create: `D:/workspace/llmSched/tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
    - Modify: `D:/workspace/llmSched/tests/smoke`
  - Smoke must prove:
    - diagnosis analysis
    - diagnosis packaging
    - diagnosis workbench
    - presence of all required diagnosis artifacts

- [x] Update canonical docs after the diagnosis track has passing proof
  - Files:
    - Modify: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
    - Modify: `D:/workspace/llmSched/README.md`
  - Rule:
    - do not advertise diagnosis completion before smoke proof is green

- [x] Run the representative diagnosis proof set
  - Verification:
    - `python -m pytest tests/unit/contracts/test_model_structure_report.py tests/unit/contracts/test_operator_representation_report.py tests/unit/contracts/test_resource_demand_report.py tests/unit/contracts/test_support_matrix_report.py tests/unit/contracts/test_schedule_diagnostics_report.py tests/unit/contracts/test_performance_diagnostics_report.py tests/unit/contracts/test_roofline_report.py tests/unit/contracts/test_architecture_assessment_report.py tests/unit/contracts/test_diagnosis_bundle.py tests/unit/contracts/test_diagnosis_workbench.py tests/unit/pipeline/test_diagnosis_analysis_workflow.py tests/unit/pipeline/test_diagnosis_packaging_workflow.py tests/unit/pipeline/test_diagnosis_workbench_workflow.py tests/unit/visualization/test_diagnosis_workbench_builder.py tests/smoke/test_cli_run_diagnosis_analysis.py tests/smoke/test_cli_run_diagnosis_workbench.py tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q`

## Completion Criteria

- [x] `D0` is complete
- [x] `D1` is complete
- [x] `D2` is complete
- [x] `D3` is complete
- [x] diagnosis reports are contract-stable
- [x] diagnosis workbench is smoke-proven
- [x] roadmap/README are updated with verified reality
