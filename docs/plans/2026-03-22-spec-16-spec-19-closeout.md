# SPEC-16 / SPEC-19 Closeout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reconfirm that `SPEC-16` is already at a practical stop-line and that `SPEC-19` remains downstream polish, then publish that closeout state in the project entry docs.

**Architecture:** This is a documentation-first closeout slice. It re-reads the current closure docs, re-runs the focused visualization verification commands, and only updates project-status docs if the runtime evidence still matches the earlier closure audit. No new UI contract or recommendation-detail interaction should be introduced in this slice.

**Tech Stack:** Markdown planning docs, static visualization builders, focused `pytest` verification commands

---

### Task 1: Reconfirm the closure boundary

**Files:**
- Read: `D:/workspace/llmSched/README.md`
- Read: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
- Read: `D:/workspace/llmSched/docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`
- Read: `D:/workspace/llmSched/docs/plans/2026-03-21-spec-16-recommendation-detail-close-enough-checklist.md`

**Step 1: Re-read the stop-line**

Confirm the current branch boundary is still:

- queue-aware catalog/workbench continuity
- side-by-side top recommendation inspection
- recommendation detail UI continuity
- recommendation detail export/snapshot continuity
- shared recommendation-detail semantics across catalog/workbench

**Step 2: Note what stays frozen**

Record that the following are not default expansion targets in this slice:

- more recommendation-detail interactions
- unrelated `SPEC-19` screenshot polish
- reopened upstream compare contracts

### Task 2: Re-run the focused proof

**Files:**
- Test: `D:/workspace/llmSched/tests/unit/visualization/test_catalog_builder.py`
- Test: `D:/workspace/llmSched/tests/unit/visualization/test_workbench_builder.py`
- Test: `D:/workspace/llmSched/tests/unit/pipeline/test_visualization_catalog_workflow.py`
- Test: `D:/workspace/llmSched/tests/unit/pipeline/test_visualization_workbench_workflow.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_visualization_catalog.py`
- Test: `D:/workspace/llmSched/tests/smoke/test_cli_run_visualization_workbench.py`

**Step 1: Run focused unit/pipeline verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: pass

**Step 2: Run focused visualization smoke verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected: pass

### Task 3: Publish the closeout decision

**Files:**
- Modify: `D:/workspace/llmSched/README.md`
- Modify: `D:/workspace/llmSched/docs/development/evaluation-compiler-roadmap.md`
- Modify: `D:/workspace/llmSched/docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`

**Step 1: Update status wording**

If Task 2 stays green, make the entry docs say:

- `SPEC-16` recommendation-detail remains frozen at the practical stop-line
- the remaining `SPEC-16` work, if any, must be justified by a concrete blocker instead of default interaction expansion
- `SPEC-19` remains downstream polish and is not a project-close blocker

**Step 2: Keep the next-step language narrow**

Point the project back toward blocker review or final project closeout, not a new default `SPEC-19` feature queue.

### Task 4: Final verification and commit

**Files:**
- Modify if needed: `D:/workspace/llmSched/docs/plans/2026-03-22-spec-16-spec-19-closeout.md`

**Step 1: Re-read diffs**

Confirm the slice stayed docs-only.

**Step 2: Commit**

If the docs and focused verification agree, commit with a closeout-oriented message.
