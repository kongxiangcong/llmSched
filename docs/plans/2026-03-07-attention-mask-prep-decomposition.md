# Attention Mask Prep Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an explicit `AttentionMaskPrep` frontend surface for Gemma3 mask/arithmetic paths, while absorbing q/k score scaling into `SDPA`.

**Architecture:** Keep q/k score scaling inside `SDPA` because those `Mul` nodes are pure attention-score arithmetic and only feed `SDPA`. Model the remaining mask arithmetic path explicitly as `AttentionMaskPrep`, but keep shape/layout-only helpers on the existing `ShapeHelper` / `LayoutFallback` surfaces. Extend legality and NIG lowering so the new surface is explicit and analyzable.

**Tech Stack:** Python 3.14, Pydantic IR models, `pytest`, ONNX-derived Graph IR.

---

### Task 1: Add failing decomposition tests

**Files:**
- Modify: `tests/unit/frontend/test_decomposition_extensions.py`

**Step 1: Write the failing tests**

Add tests for:
- `SDPA` absorbing q/k scale `Mul` nodes into attrs and rewiring inputs
- mask arithmetic nodes on an `SDPA` mask path being reclassified to `AttentionMaskPrep`
- `AttentionMaskPrep -> ATTENTION_MASK_PREP` lowering
- target-aware legality reporting `no_hardware_mapping` for `AttentionMaskPrep`

**Step 2: Run tests to verify they fail**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/frontend/test_decomposition_extensions.py -v
```

Expected: new tests fail because `AttentionMaskPrep` and SDPA scale absorption do not exist yet.

**Step 3: Commit**

Do not commit yet. Continue to implementation once failures are confirmed.

### Task 2: Absorb q/k score scaling into SDPA

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`

**Step 1: Implement minimal canonicalization**

Add a pass after `SDPA` fusion that:
- detects `Mul(tensor, constant)` on `SDPA.inputs[0]` and `SDPA.inputs[1]`
- requires single-consumer outputs
- rewrites `SDPA` to consume the unscaled tensors
- records scale metadata in `SDPA.attrs`
- appends traceability from the absorbed `Mul` nodes

**Step 2: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/frontend/test_decomposition_extensions.py -k scale -v
```

Expected: the SDPA scale test passes, mask-related tests still fail.

### Task 3: Add `AttentionMaskPrep` canonical surface

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`

**Step 1: Implement minimal mask-path classification**

Add a pass after SDPA rewriting that:
- starts from each `SDPA` mask input tensor
- walks upstream through `ShapeHelper` / `LayoutFallback` connector nodes
- reclassifies arithmetic mask ops (`Add`, `Sub`, `Mul`, `Max`, `Trilu`, `Greater`, `Neg`, `ScatterND`) on that path to `AttentionMaskPrep`
- preserves existing tensor names, `source_ref`, and `audit_ref`

**Step 2: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/frontend/test_decomposition_extensions.py -k mask -v
```

Expected: canonicalization tests for `AttentionMaskPrep` pass.

### Task 4: Extend legality and NIG lowering

**Files:**
- Modify: `src/llm_sched/frontend/legality.py`
- Modify: `src/llm_sched/frontend/nig_lowering.py`

**Step 1: Extend legality**

Add `AttentionMaskPrep` to the explicit fallback surface map so target-aware legality reports `no_hardware_mapping`.

**Step 2: Extend lowering**

Lower `AttentionMaskPrep` to `ATTENTION_MASK_PREP` with an activation or metadata memory class chosen by the node layout.

**Step 3: Run focused tests**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/frontend/test_decomposition_extensions.py -v
```

Expected: all extension tests pass.

### Task 5: Regressions and docs

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`
- Create: `docs/plans/2026-03-07-attention-mask-prep-decomposition.md`

**Step 1: Update docs**

Document:
- `AttentionMaskPrep`
- SDPA score-scale absorption
- updated Gemma3 decode smoke status

**Step 2: Run frontend and full test suites**

Run:

```powershell
$env:PYTHONPATH='src'; python -m pytest tests/unit/frontend -v
$env:PYTHONPATH='src'; python -m pytest -v
git diff --check
```

Expected: all tests pass; `git diff --check` reports no diff errors.

### Task 6: Real-model smoke and commit

**Files:**
- No source changes required unless smoke reveals regressions

**Step 1: Run Gemma3 decode smoke**

Run the same local Python smoke used in earlier batches and confirm:
- `Mul` nodes feeding `SDPA` are absorbed
- unsupported node count drops again
- remaining unsupported nodes are more tightly concentrated

**Step 2: Commit**

```powershell
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md docs/plans/2026-03-07-attention-mask-prep-decomposition.md src/llm_sched/frontend/canonicalize.py src/llm_sched/frontend/legality.py src/llm_sched/frontend/nig_lowering.py tests/unit/frontend/test_decomposition_extensions.py
git commit -m "feat: add attention mask prep decomposition"
```
