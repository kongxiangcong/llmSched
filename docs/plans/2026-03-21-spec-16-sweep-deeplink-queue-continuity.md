# SPEC-16 Sweep Deep-Link Queue Continuity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make all catalog sweep deep links preserve the same recommendation queue continuity already available in focused panel navigation.

**Architecture:** Keep compare payloads unchanged and avoid new contracts. Extract one shared catalog helper for recommendation-aware workbench params, reuse it across `Open Selected Panel`, `Open Sweep Panel`, and `Open Layer In Sweep`, and verify the same queue continuity survives through catalog, workbench, and smoke coverage.

**Tech Stack:** Python, static visualization builders, generated JavaScript, pytest

---

### Task 1: Add failing catalog tests for sweep deep-link queue continuity

**Files:**
- Modify: `D:\workspace\llmSched\tests\unit\visualization\test_catalog_builder.py`
- Modify: `D:\workspace\llmSched\tests\unit\pipeline\test_visualization_catalog_workflow.py`
- Modify: `D:\workspace\llmSched\tests\smoke\test_cli_run_visualization_catalog.py`

**Step 1: Write the failing test**

Add assertions proving generated catalog assets:

- expose a shared helper such as `buildWorkspaceRecommendationParams`
- preserve `recommendation_queue_position`, `recommendation_prev_candidate`, `recommendation_next_candidate`, `recommendation_top_candidates`, and `recommendation_queue_candidates` in all sweep deep links
- route both `Open Sweep Panel` and `Open Layer In Sweep` through the shared queue-aware helper instead of older hand-built param maps

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: FAIL on the new sweep deep-link assertions.

### Task 2: Implement shared queue-aware sweep deep-link params

**Files:**
- Modify: `D:\workspace\llmSched\src\llm_sched\visualization\catalog_builder.py`

**Step 1: Extract shared recommendation param builder**

Create one helper for queue-aware workbench deep-link params based on the current workspace state and candidate.

**Step 2: Reuse it across all workbench deep links**

Apply the same helper to:

- `Open Selected Panel`
- `Open Sweep Panel`
- `Open Layer In Sweep`

**Step 3: Run the focused tests**

Run:

```powershell
python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q
```

Expected: PASS.

## Completion

- Status: completed on 2026-03-21
- Implemented:
  - shared `buildWorkspaceRecommendationParams` helper for queue-aware workbench deep links
  - sweep deep-link continuity for both `Open Sweep Panel` and `Open Layer In Sweep`
  - aligned unit, pipeline, and smoke coverage for the shared helper path
- Verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q` -> `11 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- Next:
  - keep pushing richer compare interaction above the current fully queue-aware sweep deep-link surface
  - prefer the next slice to add workbench-side multi-candidate inspection or queue-aware side-by-side compare
