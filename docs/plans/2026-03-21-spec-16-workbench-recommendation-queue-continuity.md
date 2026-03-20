# SPEC-16 Workbench Recommendation Queue Continuity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Preserve analysis-flow recommendation queue context when analysts jump from catalog workspace compare into workbench sweep exploration.

**Architecture:** Keep compare payloads and visualization bundle contracts unchanged. Reuse catalog recommendation ordering, pass queue context through workbench URL state, render a queue-aware sweep summary in the static workbench, and preserve the same queue continuity in sweep export metadata.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing workbench tests for recommendation queue continuity

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_workbench_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_workbench_workflow.py`

**Step 1: Write the failing test**

Add assertions proving generated workbench assets:

- hydrate queue-related URL state such as `recommendation_queue_position`, `recommendation_prev_candidate`, `recommendation_next_candidate`, and `recommendation_top_candidates`
- expose helpers such as `currentRecommendationQueueState`, `buildRecommendationQueuePanelLink`, and `buildSweepRecommendationQueueSummary`
- preserve `focused_recommendation_queue` in sweep export payloads and render analyst-facing actions such as `Open Top Recommendation`, `Previous Recommended Candidate`, and `Next Recommended Candidate`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: FAIL on the new queue-continuity assertions.

### Task 2: Implement queue-aware workbench sweep continuity

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\workbench_builder.py`

**Step 1: Extend catalog workbench links**

Thread recommendation queue context into existing workbench deep links without reopening compare contracts.

**Step 2: Hydrate queue state in workbench**

Add workbench UI-state support for queue position, neighboring candidates, and top recommendations.

**Step 3: Render sweep queue continuity**

Add a `Recommendation Queue` section in sweep that:

- shows queue position and top recommended candidates
- lets analysts jump to previous/next/top recommendation
- keeps queue state stable across workbench navigation and exports

**Step 4: Run the focused test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-21
- Implemented:
  - catalog-to-workbench recommendation queue URL-state continuity
  - workbench sweep `Recommendation Queue` summary with top/previous/next actions
  - sweep export continuity for focused queue state
- Verification:
  - `python -m pytest tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `9 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- Next:
  - keep pushing richer compare interaction above the current catalog-to-workbench recommendation queue surface
  - prefer the next slice to deepen workbench-side multi-candidate inspection or bring the same queue continuity into the dedicated sweep deep links
