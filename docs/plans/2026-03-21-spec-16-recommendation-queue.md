# SPEC-16 Recommendation Queue Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn analysis-flow candidate ranking into a navigable workspace recommendation queue so analysts can move through the strongest candidates without rebuilding context manually.

**Architecture:** Keep existing compare math and contracts unchanged. Reuse the current analysis-flow recommendation scores, derive a queue from the ordered workspace candidates, render queue-aware navigation inside the focused workspace drill-down, and preserve queue context in workspace JSON/SVG exports.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog and workflow assertions for recommendation queue behavior

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_catalog_workflow.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose helpers such as `resolveWorkspaceRecommendationQueue` and `renderWorkspaceRecommendationQueue`
- render analyst-facing queue labels such as `Recommendation Queue`, `Top Recommended Candidates`, `Previous Recommended Candidate`, `Next Recommended Candidate`, and `Open Top Recommendation`
- preserve structured queue metadata in workspace export payloads, including `focused_workspace_recommendation_queue`, `queue_position`, `previous_candidate_entry_id`, `next_candidate_entry_id`, and `top_recommendation_entry_ids`

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL on the new recommendation-queue assertions.

### Task 2: Implement queue-aware focused workspace navigation

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Add recommendation queue helpers**

Derive a queue from the existing ordered workspace candidates and active analysis-flow recommendation state.

**Step 2: Render queue-aware focused drill-down controls**

Add:

- a `Recommendation Queue` summary block
- top-recommendation visibility
- previous/next/top recommendation actions that keep workspace context stable

**Step 3: Preserve queue metadata in exports**

Extend workspace JSON/SVG export payloads and snapshot header rows with queue-aware metadata.

**Step 4: Run the focused test**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-21
- Implemented:
  - queue-aware recommendation helpers above the existing analysis-flow scoring layer
  - focused workspace recommendation queue rendering with top/previous/next recommendation actions
  - workspace export continuity for queue position, neighboring candidates, and top recommendation ids
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q` -> `11 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed`
- Next:
  - keep pushing richer compare interaction above the current recommendation-queue workspace surface
  - prefer the next slice to deepen queue-to-workbench continuity or multi-candidate side-by-side inspection without reopening compare contracts
