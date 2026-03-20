# SPEC-16 Workbench Top Recommendation Compare Strip Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let workbench sweep show the top recommended candidates side-by-side so analysts can compare the strongest queue entries without stepping through them one at a time.

**Architecture:** Keep sweep payload contracts unchanged. Reuse the existing recommendation queue and selected sweep comparisons, derive the top recommendation comparisons inside workbench rendering, and present them as a compact strip above the detailed sweep table.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing workbench tests for side-by-side recommendation inspection

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write the failing test**

Add assertions proving generated workbench assets:

- expose helpers such as `buildTopRecommendationComparisonCards` and `renderTopRecommendationComparisonCard`
- render analyst-facing labels such as `Top Recommendation Compare Strip` and `Top Recommended Candidate Comparisons`
- include recommendation strip styling hooks such as `recommendation-strip`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: FAIL on the new side-by-side strip assertions.

### Task 2: Implement compact top recommendation comparison cards

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Add top recommendation comparison helpers**

Map top recommendation queue entries back to sweep comparisons and build compact per-candidate cards.

**Step 2: Render the compare strip in sweep**

Insert the top recommendation strip above the detailed sweep table while keeping the focused candidate/table flow intact.

**Step 3: Add minimal styling**

Add a lightweight responsive grid for the new strip.

**Step 4: Run the focused test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-21
- Implemented:
  - top recommendation comparison cards derived from the current queue and sweep comparisons
  - a `Top Recommendation Compare Strip` above the sweep table
  - responsive strip styling without adding new queue state or changing contracts
- Verification:
  - `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `9 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- Next:
  - keep pushing richer compare interaction above the current top-recommendation strip surface
  - prefer the next slice to add explicit side-by-side detail blocks or promote multi-candidate compare snapshots/exports
