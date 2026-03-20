# Recommendation Detail Close-Enough Checklist

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Run one explicit closure pass on the current `SPEC-16` recommendation-detail branch and decide whether it can be frozen as “closed enough”.

**Architecture:** This is a decision checklist, not a feature plan. It assumes the current catalog/workbench recommendation-detail surfaces already exist and asks whether they satisfy the branch stop-line without reopening contracts or inventing more interaction by default. If any check fails, allow at most one final focused slice tied directly to that failed item.

**Tech Stack:** Markdown planning docs, static catalog/workbench builders, existing focused pytest/smoke verification commands

---

### Task 1: Reconfirm the stop-line surface

**Files:**
- Read: `README.md`
- Read: `docs/development/evaluation-compiler-roadmap.md`
- Read: `docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`

**Step 1: Verify the intended stop-line is unchanged**

Confirm the branch is expected to provide all of the following:

- queue-aware catalog/workbench continuity
- side-by-side top recommendation inspection
- richer recommendation detail in page UI
- recommendation detail export/snapshot continuity
- shared recommendation-detail semantics across catalog/workbench

**Step 2: Record outcome**

Write `pass` / `fail` beside each stop-line item in a short audit note before changing roadmap priority again.

### Task 2: Check the analyst question directly

**Files:**
- Read: `docs/plans/2026-03-21-spec-16-workbench-recommendation-detail-blocks.md`
- Read: `docs/plans/2026-03-21-spec-16-workbench-detail-export-continuity.md`
- Read: `docs/plans/2026-03-21-spec-16-catalog-recommendation-detail-continuity.md`

**Step 1: Ask the closure question against the current UX**

Use the current surfaces to answer:

- can an analyst tell which candidate to inspect next?
- can they see why that candidate is recommended?
- can they inspect deeper detail without reopening raw bundle JSON?
- can they preserve that context through JSON/SVG export?

**Step 2: Mark result**

- if every answer is yes, mark the branch `close-enough`
- if any answer is no, write the exact missing capability in one sentence

### Task 3: Enforce the one-slice rule if needed

**Files:**
- Modify only if needed: `docs/plans/YYYY-MM-DD-<next-slice>.md`

**Step 1: Gate further work**

If Task 2 is `close-enough`, do not create another recommendation-detail feature plan.

If Task 2 is not `close-enough`, create exactly one final focused slice with:

- one missing capability
- one verification path
- no reopened contracts
- no unrelated polish

### Task 4: Reconfirm verification evidence

**Files:**
- Read: `README.md`
- Read: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Re-run the focused proof commands before declaring the branch frozen**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q
```

Expected:

- first command stays green
- second command stays green

### Task 5: Freeze or escalate

**Files:**
- Modify: `README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: If close-enough**

Update both docs to say:

- the recommendation-detail branch is frozen as a practical stop-line
- the next blocker review moves back to remaining `SPEC-16` / `SPEC-13/14/15` gaps
- `SPEC-19` remains downstream polish

**Step 2: If not close-enough**

Update both docs to say:

- one final focused slice remains
- name that slice explicitly
- keep all other recommendation-detail expansion frozen until that slice is done

### Task 6: Close the loop

**Files:**
- Modify: `docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`

**Step 1: Add the final decision**

Append one short section:

- `Decision: close-enough` or `Decision: one final slice required`
- the reason in 2-4 bullets
- the exact next action
