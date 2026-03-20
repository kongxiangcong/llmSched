# Real Model Frontend Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore `run-frontend-analysis` for the current real `models/gemma3_1b/model_q4f16.onnx` export.

**Architecture:** Extend frontend import/canonicalize/lowering only where the current real ONNX export diverges from the older Gemma3 pattern assumptions. Prefer normalizing new ONNX spellings back into the existing canonical graph and `NIG` macro-op surface instead of inventing new downstream contracts unless decomposition proves impossible.

**Tech Stack:** Python, ONNX, pytest, CLI smoke tests

---

### Task 1: Capture the current real-model operator surface

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_onnx_importer.py`
- Test: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_onnx_importer.py`

**Step 1: Write the failing test**

Add a focused test that imports the real `models/gemma3_1b/model_q4f16.onnx` with current shape bindings and asserts the imported graph contains the newly observed ONNX operator families (`GroupQueryAttention`, `SimplifiedLayerNormalization`, `FastGelu`, `Gather_Quant`) so we lock the real export shape before changing canonicalization.

**Step 2: Run test to verify it fails or exposes the wrong surface**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -q`

Expected: the new test fails until the importer-side real-model fixture is wired correctly.

**Step 3: Write minimal implementation**

Add only the minimal fixture/helper code needed for the test to import the real model and assert the operator counts deterministically.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -q`

Expected: PASS.

### Task 2: Normalize current real-model ONNX spellings into canonical graph nodes

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\frontend\canonicalize.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_decomposition_extensions.py`
- Test: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_decomposition_extensions.py`

**Step 1: Write the failing test**

Add the smallest synthetic Graph IR cases that model the newly observed spellings:
- `SimplifiedLayerNormalization` / `LayerNorm` variants that should become `RMSNorm`
- `FastGelu` + downstream multiply that should become `GeGLU`
- `Gather_Quant` / post-scale embedding spellings that should become `EmbeddingLookup`
- mask reformat arithmetic that should become `AttentionMaskPrep`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_decomposition_extensions.py -q`

Expected: FAIL on unsupported or residual raw op kinds.

**Step 3: Write minimal implementation**

Teach canonicalization to absorb the new ONNX spellings into the existing canonical node set, preserving source refs and audit refs.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_decomposition_extensions.py -q`

Expected: PASS.

### Task 3: Reconcile `GroupQueryAttention` with the existing lowering path

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\frontend\canonicalize.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\frontend\nig_lowering.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_decomposition_extensions.py`
- Test: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\frontend\test_decomposition_extensions.py`

**Step 1: Write the failing test**

Add a synthetic `GroupQueryAttention` case showing the canonical/lowering behavior we want. Prefer decomposing it back into the existing `SDPA` contract if the real export provides enough metadata; only add a new canonical pattern if decomposition cannot preserve the existing downstream shape.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_decomposition_extensions.py -q`

Expected: FAIL because the new attention spelling is currently unsupported.

**Step 3: Write minimal implementation**

Implement the smallest canonicalization/lowering change that lets `GroupQueryAttention` rejoin the current `SDPA`/attention path without reopening unrelated downstream contracts.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_decomposition_extensions.py -q`

Expected: PASS.

### Task 4: Restore frontend workflow on the real model

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\pipeline\test_frontend_analysis_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\smoke\test_cli_run_frontend_analysis.py`
- Modify if needed: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\src\llm_sched\pipeline\frontend_analysis.py`
- Test: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\unit\pipeline\test_frontend_analysis_workflow.py`
- Test: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\tests\smoke\test_cli_run_frontend_analysis.py`

**Step 1: Write the failing test**

Update or add assertions that the workflow now completes on the real model and emits a decomposition report without the current unsupported-node failure.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/smoke/test_cli_run_frontend_analysis.py -q`

Expected: FAIL with the current real-model lowering error.

**Step 3: Write minimal implementation**

Adjust workflow code only if canonicalization/lowering changes require corresponding report or diagnostic updates.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_frontend_analysis_workflow.py tests/smoke/test_cli_run_frontend_analysis.py -q`

Expected: PASS.

### Task 5: Revalidate the frontend-owned regression ladder

**Files:**
- Modify if needed: `D:\workspace\llmSched\.worktrees\frontend-real-model-alignment\docs\development\evaluation-compiler-roadmap.md`

**Step 1: Run focused verification**

Run:

```powershell
python -m pytest tests/unit/frontend/test_onnx_importer.py tests/unit/frontend/test_decomposition_extensions.py tests/unit/pipeline/test_frontend_analysis_workflow.py tests/smoke/test_cli_run_frontend_analysis.py -q
```

Expected: PASS.

**Step 2: Run smoke checkpoint**

Run:

```powershell
python -m pytest tests/smoke -m local_smoke -q
```

Expected: improved result versus the current frontend-blocked baseline; document the actual outcome.

**Step 3: Record new checkpoint reality**

If the focused batch or `local_smoke` outcome changes the blocker story, update roadmap/README before moving on to downstream stages.

## Execution Outcome

- real-model frontend alignment is complete for the current `models/gemma3_1b/model_q4f16.onnx` export
- restored canonical surface:
  - `GatherBlockQuantized + Mul -> EmbeddingLookup`
  - `SimplifiedLayerNormalization -> RMSNorm`
  - `Gelu/FastGelu + Mul -> GeGLU`
  - `GroupQueryAttention -> SDPA`
- follow-up closure done in the same slice:
  - shape binding now resolves `total_sequence_length`
  - SDPA auxiliary input binding no longer misclassifies rope-cache tensors into staged `weight`
  - real-model `dynamic_shape_unresolved` is now `0`
- refreshed verification on 2026-03-19:
  - `python -m pytest tests/unit/frontend/test_binding_contract.py -q` -> `7 passed`
  - `python -m pytest tests/smoke/test_phase_c_memory_planner_matrix.py -q` -> `4 passed`
  - `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
  - `python -m pytest -q --durations=30` -> `436 passed`
- resulting checkpoint:
  - `SPEC-08/09/10/11/12` return to keep-green
  - mainline priority returns to `SPEC-13 -> SPEC-14/15 -> SPEC-16`, then `SPEC-19` hardening
