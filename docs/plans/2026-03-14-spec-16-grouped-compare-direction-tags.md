# SPEC-16 Grouped Compare Direction Tags Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add lightweight direction tags to grouped compare sections so users can scan whether a group implies faster/slower behavior or higher/lower pressure before reading individual rows.

**Architecture:** Keep the logic entirely inside the static catalog/workbench JS renderers. Derive one small direction tag from the already-ranked lead scalar in each group, using narrow group-aware heuristics and no new bundle/catalog contract fields.

**Tech Stack:** Python, static HTML/CSS/JavaScript generation, pytest

## Execution Policy

The user already approved continuing in the current session, so this plan is being implemented directly here.

---

### Task 1: Lock direction-tag behavior with failing tests

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`

**Step 1: Write the failing tests**

Add assertions that require:
- one helper for grouped compare direction tags in each JS bundle
- direction-tag phrases for at least:
  - `candidate faster`
  - `candidate slower`
  - `pressure up`
  - `pressure down`
- grouped section rendering to include the tag helper in the section heading path

**Step 2: Run tests to verify RED**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q -k "grouped or sweep"
```

Expected: FAIL because grouped compare sections currently render title-only headings.

### Task 2: Implement minimal direction-tag rendering

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add one tag helper per JS bundle**

Use the sorted lead scalar from each group and narrow heuristics:
- `headline`: faster/slower from cycle-oriented or throughput-oriented lead metrics
- `throughput_latency`: faster/slower or throughput up/down from the lead metric family
- `memory_pressure`: pressure up/down
- `phase_shape` / `schedule_shape`: shifted up/down or neutral group-shape wording

**Step 2: Render the tag inline**

Render the direction tag next to the group title with a compact badge-like style.

### Task 3: Verify and commit

**Files:**
- Modify: `D:\workspace\llmSched\docs\development\evaluation-compiler-roadmap.md`
- Add/Update: `D:\workspace\llmSched\docs\plans\2026-03-14-spec-16-grouped-compare-direction-tags.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_packaging_workflow.py -q
git diff --check
```

Expected: PASS with no diff errors.

**Step 2: Commit**

Run:

```powershell
git add docs/plans/2026-03-14-spec-16-grouped-compare-direction-tags.md docs/development/evaluation-compiler-roadmap.md src/llm_sched/visualization/catalog_builder.py src/llm_sched/visualization/workbench_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py
git commit -m "feat: add grouped compare direction tags"
```
