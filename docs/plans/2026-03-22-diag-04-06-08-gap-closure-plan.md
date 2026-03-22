# DIAG-04 DIAG-06 DIAG-08 Gap Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the current quality gaps in `DIAG-04` support traceability, `DIAG-06` performance traceability/taxonomy, and `DIAG-08` assessment consistency so the diagnosis layer can express the intended layer/block/subgraph diagnosis chain with materially higher fidelity.

**Architecture:** Keep the frozen `2026-03-22` baseline pipeline and treat this work as additive diagnosis-layer hardening. Build the missing quality in dependency order: first restore true structure/layer provenance in `DIAG-04`, then join that provenance into `DIAG-06` node/layer/phase diagnostics, then rebuild `DIAG-08` verdict and recommendation synthesis on top of the stronger evidence chain. Do not bypass reports by jumping straight to workbench polish.

**Tech Stack:** Python, Pydantic contracts, diagnosis analysis builders, Typer CLI workflows, `pytest` unit/pipeline/smoke tests

---

## Scope Rules

- This plan is a follow-on hardening pass above the completed diagnosis skeleton.
- Keep the existing diagnosis report filenames and top-level workflow commands stable.
- Prefer additive contract growth over breaking renames unless a field is actively misleading.
- Do not re-open the frozen Phase A-E baseline semantics unless new failing evidence requires it.
- Every behavior change must start with a failing test and end with fresh verification evidence.

## Delivery Checklist

- [ ] `DIAG-04` stops inferring `layer0`/`auxiliary_block` for most nodes and instead derives structure provenance from diagnosis inputs.
- [ ] `support_matrix_report.json` can aggregate support at node/layer/structure with real per-structure identities.
- [ ] `DIAG-06` `node_hotspots[]` can be traced back to layer/structure/phase/macro-op.
- [ ] `DIAG-06` bottleneck classification is explicit enough to distinguish compute / bandwidth / VMEM / sync / fallback style limits.
- [ ] `DIAG-08` never emits a verdict/summary pair with contradictory semantics.
- [ ] `DIAG-08` recommendations are evidence-backed and categorized by model / schedule / hardware / compiler intent.
- [ ] A real diagnosis run can be reviewed from structure -> support -> performance -> assessment without falling back to raw guesswork.

## Evidence Checklist

- [ ] Unit contract tests cover all new fields and invariants.
- [ ] Builder unit tests cover the new traceability joins and aggregation rules.
- [ ] Diagnosis pipeline tests prove the new fields survive the real run-root workflows.
- [ ] At least one smoke or prepared-run proof shows `layer_support_summary` and `structure_support_summary` are not collapsed to a trivial subset.
- [ ] At least one proof checks `DIAG-08` verdict text against a support-gap scenario.

## Task 1: DIAG-04 Contract Hardening

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/contracts/support_matrix_report.py`
- Modify: `D:/workspace/llmSched/tests/unit/contracts/test_support_matrix_report.py`

**Intent:**
- Expand `NodeSupportEntry` so support records can carry enough identity to join back to structure, phase, and fallback surfaces.
- Keep existing top-level report shape, but make the per-entry schema sufficient for later `DIAG-06` and `DIAG-08` reuse.

**Step 1: Write the failing contract test**

- Add assertions for new `NodeSupportEntry` fields:
  - `structure_kind`
  - `phase`
  - `canonical_op`
  - `fallback_kind`
  - `binding_issue_ids`
  - `legality_rule_ids`
- Add a validation test that the legacy minimal payload now fails unless the new required/derived fields are present where intended.

**Step 2: Run the contract test to verify it fails**

Run:
```bash
python -m pytest tests/unit/contracts/test_support_matrix_report.py -q
```

Expected:
- FAIL because the new fields are not yet defined on `NodeSupportEntry` or related summaries.

**Step 3: Implement the minimal contract change**

- Extend `NodeSupportEntry`.
- Only add new fields that are required by later builder joins; do not add speculative UI-only fields.
- Keep `SupportMatrixReport` top-level keys stable.

**Step 4: Re-run the contract test**

Run:
```bash
python -m pytest tests/unit/contracts/test_support_matrix_report.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/support_matrix_report.py tests/unit/contracts/test_support_matrix_report.py
git commit -m "feat: harden DIAG-04 support matrix contract"
```

## Task 2: DIAG-04 Real Structure Traceability

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/analysis/support_matrix_report_builder.py`
- Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
- Modify: `D:/workspace/llmSched/tests/unit/analysis/test_support_matrix_report_builder.py`
- Modify: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_analysis_support_matrix.py`

**Intent:**
- Replace the current guessed `layer_id` and hardcoded `structure.layer0.*` classification with provenance derived from upstream diagnosis artifacts.

**Step 1: Write the failing builder test**

- Add a test fixture where multiple structures and layers exist.
- Assert that support entries preserve the actual `layer_id`, `structure_id`, and `structure_kind` instead of collapsing to layer 0 / auxiliary.
- Assert that `layer_support_summary` and `structure_support_summary` counts reflect the fixture’s true structure graph.

**Step 2: Run the builder test to verify it fails**

Run:
```bash
python -m pytest tests/unit/analysis/test_support_matrix_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_support_matrix.py -q
```

Expected:
- FAIL because the current builder still uses `_infer_layer_id()` and `_infer_structure_id()`.

**Step 3: Implement the minimal builder change**

- Add `ModelStructureReport` as a builder input path through `diagnosis_analysis.py`.
- Build lookup indices from `model_structure_report.node_index[]`.
- Replace `_infer_layer_id()` and `_infer_structure_id()` with direct lookup joins.
- Remove or sharply limit any fallback heuristics. If heuristics remain, they must be explicit and diagnostics-visible.

**Step 4: Add richer aggregation**

- Aggregate by:
  - layer
  - structure
  - reason code
- If justified by the input data, add:
  - `phase_support_summary`
  - `macro_op_support_summary`
- Keep the change additive unless top-level schema churn becomes unavoidable.

**Step 5: Re-run targeted tests**

Run:
```bash
python -m pytest tests/unit/analysis/test_support_matrix_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_support_matrix.py -q
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add src/llm_sched/analysis/support_matrix_report_builder.py src/llm_sched/pipeline/diagnosis_analysis.py tests/unit/analysis/test_support_matrix_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_support_matrix.py
git commit -m "feat: join DIAG-04 support entries to real model structure provenance"
```

## Task 3: DIAG-06 Contract Expansion

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/contracts/performance_diagnostics_report.py`
- Modify: `D:/workspace/llmSched/tests/unit/contracts/test_performance_diagnostics_report.py`

**Intent:**
- Make node and layer hotspot entries structurally traceable enough to support the diagnosis chain and downstream assessment logic.

**Step 1: Write the failing contract test**

- Add assertions that `NodeHotspotEntry` includes:
  - `graph_node_id`
  - `layer_id`
  - `structure_id`
  - `structure_kind`
  - `phase`
  - `macro_op`
  - `support_status`
  - `bound_kind`
- Add assertions that `LayerHotspotEntry` includes at least:
  - `dominant_phase`
  - `dominant_bound`
  - `support_gap_count`

**Step 2: Run the contract test to verify it fails**

Run:
```bash
python -m pytest tests/unit/contracts/test_performance_diagnostics_report.py -q
```

Expected:
- FAIL because the current contract only carries shallow hotspot fields.

**Step 3: Implement the minimal contract change**

- Extend the hotspot entry models.
- Keep names aligned with the diagnosis design vocabulary.

**Step 4: Re-run the contract test**

Run:
```bash
python -m pytest tests/unit/contracts/test_performance_diagnostics_report.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/performance_diagnostics_report.py tests/unit/contracts/test_performance_diagnostics_report.py
git commit -m "feat: expand DIAG-06 hotspot contracts for structure traceability"
```

## Task 4: DIAG-06 Traceability Join And Bottleneck Taxonomy

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/analysis/performance_diagnostics_report_builder.py`
- Modify: `D:/workspace/llmSched/src/llm_sched/pipeline/diagnosis_analysis.py`
- Modify: `D:/workspace/llmSched/tests/unit/analysis/test_performance_diagnostics_report_builder.py`
- Modify: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_analysis_performance_diagnostics.py`

**Intent:**
- Join performance hotspots back to structure/support lineage and make bottleneck classification explicitly diagnosis-grade.

**Step 1: Write the failing builder test**

- Add a test case where two node hotspots belong to different structures/layers.
- Assert that the builder emits the correct `layer_id`, `structure_id`, `phase`, and `macro_op`.
- Add a bottleneck test that differentiates at least:
  - `compute_bound`
  - `bandwidth_bound`
  - `vmem_bound`
  - `sync_bound`
  - `fallback_bound`

**Step 2: Run the builder test to verify it fails**

Run:
```bash
python -m pytest tests/unit/analysis/test_performance_diagnostics_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_performance_diagnostics.py -q
```

Expected:
- FAIL because the current builder only forwards top-level hotspot rows and raw bottleneck counts.

**Step 3: Implement the join**

- Thread `ModelStructureReport`, `OperatorRepresentationReport`, and `SupportMatrixReport` into the builder path.
- Build node lookup maps once.
- For each hotspot row, attach:
  - graph identity
  - structure identity
  - canonical/macro identity
  - support identity

**Step 4: Implement the taxonomy**

- Map existing bottleneck evidence into an explicit diagnosis taxonomy.
- Preserve raw upstream counts if useful, but emit a diagnosis-level dominant classification that can be consumed by `DIAG-08`.

**Step 5: Re-run targeted tests**

Run:
```bash
python -m pytest tests/unit/analysis/test_performance_diagnostics_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_performance_diagnostics.py -q
```

Expected:
- PASS

**Step 6: Commit**

```bash
git add src/llm_sched/analysis/performance_diagnostics_report_builder.py src/llm_sched/pipeline/diagnosis_analysis.py tests/unit/analysis/test_performance_diagnostics_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_performance_diagnostics.py
git commit -m "feat: join DIAG-06 performance hotspots to structure and support lineage"
```

## Task 5: DIAG-08 Contract And Verdict Semantics

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/contracts/architecture_assessment_report.py`
- Modify: `D:/workspace/llmSched/tests/unit/contracts/test_architecture_assessment_report.py`

**Intent:**
- Make the assessment contract capable of expressing blocked reasons, major support gaps, and confidence in a way that cannot contradict itself.

**Step 1: Write the failing contract test**

- Add assertions for fields such as:
  - `blocking_reasons`
  - `top_unsupported_structures`
  - `top_fallback_structures`
  - `assessment_basis`
- Add a validation case that disallows an `unsupported` verdict with a “viable” style summary.

**Step 2: Run the contract test to verify it fails**

Run:
```bash
python -m pytest tests/unit/contracts/test_architecture_assessment_report.py -q
```

Expected:
- FAIL because the current contract and validation rules do not express this distinction.

**Step 3: Implement the minimal contract change**

- Extend `OverallAssessment` and related finding models only where they improve diagnosis evidence.
- Add a validator if needed to prevent obviously contradictory verdict/summary pairs.

**Step 4: Re-run the contract test**

Run:
```bash
python -m pytest tests/unit/contracts/test_architecture_assessment_report.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/architecture_assessment_report.py tests/unit/contracts/test_architecture_assessment_report.py
git commit -m "feat: harden DIAG-08 assessment contract semantics"
```

## Task 6: DIAG-08 Evidence-Backed Synthesis

**Files:**
- Modify: `D:/workspace/llmSched/src/llm_sched/analysis/architecture_assessment_report_builder.py`
- Modify: `D:/workspace/llmSched/tests/unit/analysis/test_architecture_assessment_report_builder.py`
- Modify: `D:/workspace/llmSched/tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py`

**Intent:**
- Rebuild verdict and recommendations from support/performance/timeline evidence so the final report reflects the actual diagnosis chain.

**Step 1: Write the failing builder test**

- Add one scenario with an unsupported structure on the hottest path.
- Assert:
  - verdict is `unsupported`
  - summary language is blocking, not merely constrained
  - `top_support_gaps` surfaces the blocking structure
  - primary recommendation points to the right category

- Add one scenario with no unsupported structures but dominant bandwidth bound.
- Assert:
  - verdict is `constrained_fit`
  - summary language reflects a constrained but runnable fit

**Step 2: Run the builder test to verify it fails**

Run:
```bash
python -m pytest tests/unit/analysis/test_architecture_assessment_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py -q
```

Expected:
- FAIL because the current `_build_overall_assessment()` still allows summary/verdict drift.

**Step 3: Implement the synthesis change**

- Derive verdict from evidence in this order:
  - unsupported blocking gaps
  - severe fallback/constrained fit
  - dominant roofline and timeline losses
  - good fit
- Generate summary text from the chosen verdict, not from a separate free-floating rule.
- Categorize recommendations into model / schedule / hardware / compiler actions where justified.

**Step 4: Re-run targeted tests**

Run:
```bash
python -m pytest tests/unit/analysis/test_architecture_assessment_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py -q
```

Expected:
- PASS

**Step 5: Commit**

```bash
git add src/llm_sched/analysis/architecture_assessment_report_builder.py tests/unit/analysis/test_architecture_assessment_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py
git commit -m "feat: align DIAG-08 verdicts and recommendations with diagnosis evidence"
```

## Task 7: Cross-Report Proof On A Real Diagnosis Run

**Files:**
- Modify: `D:/workspace/llmSched/tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
- Optional Modify: `D:/workspace/llmSched/tests/smoke/test_cli_run_diagnosis_analysis.py`

**Intent:**
- Prove that the strengthened reports survive the real diagnosis pipeline and no longer collapse important layer/structure information.

**Step 1: Write the failing smoke assertion**

- Add assertions such as:
  - `len(layer_support_summary) > 1`
  - `len(structure_support_summary) > 2`
  - at least one `node_hotspots[]` row carries `layer_id` and `structure_id`
  - `unsupported` verdict cannot coexist with viability wording

**Step 2: Run smoke to verify it fails**

Run:
```bash
python -m pytest tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q
```

Expected:
- FAIL on the current weak aggregation / assessment semantics.

**Step 3: Re-run after implementation**

Run:
```bash
python -m pytest tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q
```

Expected:
- PASS

**Step 4: Commit**

```bash
git add tests/smoke/test_phase_f_architecture_diagnosis_matrix.py
git commit -m "test: prove DIAG-04 DIAG-06 DIAG-08 gap closure on real diagnosis smoke"
```

## Final Verification Checklist

- [ ] `python -m pytest tests/unit/contracts/test_support_matrix_report.py -q`
- [ ] `python -m pytest tests/unit/analysis/test_support_matrix_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_support_matrix.py -q`
- [ ] `python -m pytest tests/unit/contracts/test_performance_diagnostics_report.py -q`
- [ ] `python -m pytest tests/unit/analysis/test_performance_diagnostics_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_performance_diagnostics.py -q`
- [ ] `python -m pytest tests/unit/contracts/test_architecture_assessment_report.py -q`
- [ ] `python -m pytest tests/unit/analysis/test_architecture_assessment_report_builder.py tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py -q`
- [ ] `python -m pytest tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q`

## Exit Criteria

- [ ] Support matrix uses real structure provenance rather than layer-0 heuristics.
- [ ] Performance diagnostics expose diagnosis-grade node/layer/phase traceability.
- [ ] Assessment verdicts and summaries are semantically aligned.
- [ ] The diagnosis chain can be read linearly from support evidence into performance evidence into assessment conclusions.

Plan complete and saved to `docs/plans/2026-03-22-diag-04-06-08-gap-closure-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

Which approach?
