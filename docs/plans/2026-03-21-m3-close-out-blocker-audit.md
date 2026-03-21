# M3 Close-Out Blocker Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run one explicit Phase D / `M3` blocker audit after freezing the `SPEC-16` recommendation-detail branch, then decide the smallest remaining execution lane needed before `M3` can be considered closeable.

**Architecture:** This plan is a documentation-first closure pass. It treats the recommendation-detail branch as frozen, re-reads the project-status source of truth, and separates remaining work into true blockers versus downstream polish. If the audit finds one clearly dominant blocker lane, the follow-on work should stay narrowly attached to that lane instead of reopening multiple compare/UI branches at once.

**Tech Stack:** Markdown planning docs, roadmap status tables, existing CLI / pytest verification commands, static visualization and Phase D workflow artifacts

---

### Task 1: Reconfirm the frozen branch boundary

**Files:**
- Read: `README.md`
- Read: `docs/development/evaluation-compiler-roadmap.md`
- Read: `docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`

**Step 1: Re-read the practical stop-line**

Confirm the current recommendation-detail branch is already frozen as:

- queue-aware catalog/workbench continuity
- side-by-side top recommendation inspection
- recommendation detail UI continuity
- recommendation detail export/snapshot continuity
- shared recommendation-detail semantics across catalog/workbench

**Step 2: Write the branch boundary down**

Record one short note that these items are no longer default expansion targets unless a later blocker audit proves a concrete missing capability.

### Task 2: Audit the remaining true `M3` blockers

**Files:**
- Read: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/plans/2026-03-21-m3-close-out-blocker-audit.md`

**Step 1: Extract the current gap statements**

List the still-open gap language for:

- `SPEC-13`
- `SPEC-14`
- `SPEC-15`
- `SPEC-16`

**Step 2: Reclassify each gap**

For every open gap, mark it as one of:

- `true blocker`
- `supports blocker`
- `downstream polish`

**Step 3: Name the dominant blocker lane**

Choose the single most likely next execution lane, such as:

- deeper `SPEC-13` compare-grade estimator aggregation
- `SPEC-14/15` eval-compare closure
- broader non-recommendation `SPEC-16` compare/workspace drill-down

### Task 3: Define the stop-line question for that lane

**Files:**
- Modify: `docs/plans/2026-03-21-m3-close-out-blocker-audit.md`

**Step 1: State the closure question**

Write one explicit question the next lane must answer before `M3` can move materially closer to `done`.

Examples:

- can analysts compare fitted estimator behavior across scenarios with enough depth to trust the recommendation?
- can prefill/decode evaluation outputs now support the top-level compare loop without dropping to raw artifacts?
- can the sweep/workspace workflow expose the remaining non-recommendation compare drill-down needed for daily use?

**Step 2: State what does not belong**

Write a short exclusion list of work that should remain frozen during this lane, especially:

- more recommendation-detail embellishment
- unrelated `SPEC-19` polish
- reopened Phase C contract expansion

### Task 4: Lock verification expectations

**Files:**
- Modify: `docs/plans/2026-03-21-m3-close-out-blocker-audit.md`

**Step 1: Define proof commands**

Name the exact verification commands the next lane must keep green:

```powershell
python -m pytest tests/smoke -m local_smoke -q
python -m pytest tests/smoke -m milestone_matrix -q
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

**Step 2: Define any focused add-on proof**

Leave a placeholder for one focused verification command tied to the chosen dominant blocker lane.

### Task 5: Publish the new execution handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update project-status entry points**

Point the active execution handoff at this new `M3` blocker audit plan.

**Step 2: Update current-next-slice wording**

Change the roadmap and README wording so the current next slice is:

- run the broader `M3` blocker audit
- identify the dominant remaining blocker lane
- only then open the next focused execution slice

---

## Initial Audit Notes

### Frozen Branch Boundary

- the current `SPEC-16` recommendation-detail branch remains frozen at the already-audited practical stop-line
- queue continuity, side-by-side recommendation inspection, recommendation-detail UI/export continuity, and shared catalog/workbench semantics are no longer default expansion targets
- any future reopening of that branch now requires a concrete blocker, not “one more compare interaction” by default

### Remaining Gap Reclassification

- `SPEC-13`
  - deeper cycle fitting: `supports blocker`
  - compare-grade aggregation above current critical-path / token-phase / node-layer summaries: `supports blocker`
  - clearer bandwidth / VMEM breakdown wording: `downstream polish`
- `SPEC-14`
  - finer layer-level prefill view: `supports blocker`
  - stronger top-level eval compare closure: `true blocker`
- `SPEC-15`
  - finer token latency decomposition: `supports blocker`
  - `kv_len` sweep aggregation: `supports blocker`
  - stronger top-level eval compare closure: `true blocker`
- `SPEC-16`
  - deeper non-recommendation compare/workspace drill-down: `supports blocker`
  - parallel execution and cache reuse: `supports blocker`
  - broader compare modes beyond the current grouped scalar-plus-layer-plus-pressure surface: `supports blocker`
- `SPEC-19`
  - richer screenshot workflow and deeper workspace polish: `downstream polish`

### Dominant Remaining Blocker Lane

- recommended dominant lane: `SPEC-14/15` eval-compare closure, with `SPEC-16` limited to the minimum consumer-facing compare surface needed to expose it cleanly
- why this lane wins:
  - current recommendation-detail work already made the compare UI materially more usable
  - the bigger remaining uncertainty is whether prefill/decode evaluation outputs themselves now form a convincing compare loop
  - any further `SPEC-16` interaction work is lower confidence until the still-open eval-compare gap is narrowed first

### Closure Question For The Next Lane

- can prefill/decode evaluation outputs now support the top-level compare loop across scenarios strongly enough that analysts do not need to reopen raw evaluation artifacts for the main decision path?

### Exclusions While Executing That Lane

- do not reopen the frozen recommendation-detail branch unless this audit’s closure question proves a concrete UI gap
- do not spend the next slice on unrelated `SPEC-19` screenshot or workspace polish
- do not reopen Phase C contracts or accepted `SPEC-08/09/10/11/12` scope unless keep-green verification regresses

### Verification Expectations

- baseline proof to keep green:
  - `python -m pytest tests/smoke -m local_smoke -q`
  - `python -m pytest tests/smoke -m milestone_matrix -q`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q`
- focused add-on proof to define in the next slice:
  - one targeted `SPEC-14/15` compare/evaluation command or pytest selection tied directly to the chosen eval-compare closure task

## Follow-Up Audit Update (2026-03-21, after `SPEC-14/15` cross-mode closure)

### Result

- the focused `SPEC-14/15` eval-compare closure lane now passes its practical stop-line
- row verdicts, decode `kv_len` aggregation, decode token-latency decomposition, prefill layer decomposition, and cross-mode compare closure now collectively answer the main analyst decision path from standalone compare artifacts

### Reclassified Dominant Remaining Lane

- updated dominant lane: `SPEC-13` deeper cycle fitting plus compare-grade estimator aggregation
- why it moves:
  - the previous `SPEC-14/15` closure question is now answered with `yes`
  - the next real uncertainty is no longer “can compare artifacts summarize eval outputs”, but “is the estimator surface itself deep and trustworthy enough for the remaining compare/recommendation loop”

### What Stays Frozen

- do not reopen the current `SPEC-14/15` compare-closure lane by default
- do not reopen the frozen `SPEC-16` recommendation-detail branch
- keep `SPEC-19` classified as downstream polish only
