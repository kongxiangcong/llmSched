# Profile-Aware Legality and Residual Decomposition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bind frontend legality to `TargetProfile` / `ArchitectureCapabilities`, then extend the frontend with residual-add decomposition so more of Gemma3 can lower into hardware-facing workload units.

**Architecture:** Keep legality and decomposition separate. Legality remains an admission check on `GraphIR`, but it becomes target-aware by consulting hardware capabilities for opcode availability, quantization settings, and KV cache contracts. Canonicalization and lowering then grow one bounded new workload unit, `ResidualAdd -> ELEM_ADD`, without conflating shape-helper preprocessing or scheduler behavior.

**Tech Stack:** Python 3.14, `pydantic`, `pytest`.

---

### Task 1: Add profile-aware frontend legality

**Files:**
- Modify: `src/llm_sched/frontend/legality.py`
- Modify: `src/llm_sched/frontend/__init__.py`
- Test: `tests/unit/frontend/test_legality.py`

**Step 1: Write the failing test**

Add tests asserting that legality can accept either `TargetProfile` or `ArchitectureCapabilities`, and that it rejects:

- canonical ops whose required opcode is not enabled in the active target,
- quantized `Linear` nodes whose `group_size` is not in the target profile whitelist,
- KV nodes whose dtype disagrees with `kv_cache.dtype`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_legality.py -v`
Expected: FAIL because legality is not yet target-aware.

**Step 3: Write minimal implementation**

Extend legality with:

- optional `hardware` input accepting `TargetProfile | ArchitectureCapabilities`,
- target-capability resolution helper,
- opcode requirement mapping from canonical `GraphIR` nodes,
- quantization and KV cache contract checks.

Keep existing structural legality rules unchanged.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_legality.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/legality.py src/llm_sched/frontend/__init__.py tests/unit/frontend/test_legality.py
git commit -m "feat: add profile-aware frontend legality"
```

### Task 2: Add residual-add decomposition

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`
- Modify: `src/llm_sched/frontend/nig_lowering.py`
- Test: `tests/unit/frontend/test_canonicalize.py`
- Test: `tests/unit/frontend/test_nig_lowering.py`

**Step 1: Write the failing test**

Add tests asserting that:

- residual-style `Add(x, projected)` canonicalizes to `ResidualAdd`,
- scalar/shape-helper `Add` nodes do not canonicalize to `ResidualAdd`,
- canonical `ResidualAdd` lowers to `ELEM_ADD`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py tests/unit/frontend/test_nig_lowering.py -v`
Expected: FAIL because residual-add decomposition does not exist yet.

**Step 3: Write minimal implementation**

Extend the canonicalizer with one bounded rule:

- only fuse `Add` when both inputs are non-constant activation-like tensors,
- require tensor rank >= 2 and matching output shape,
- preserve traceability.

Extend lowering with:

- `ResidualAdd -> ELEM_ADD`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py tests/unit/frontend/test_nig_lowering.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/canonicalize.py src/llm_sched/frontend/nig_lowering.py tests/unit/frontend/test_canonicalize.py tests/unit/frontend/test_nig_lowering.py
git commit -m "feat: add residual add decomposition"
```

### Task 3: Align baseline target profiles with implemented macro-ops

**Files:**
- Modify: `profiles/targets/riscv_npu_single_core_v1.json`
- Modify: `profiles/targets/riscv_npu_dual_core_v1.json`
- Test: `tests/unit/config/test_profile_fixtures.py`
- Test: `tests/unit/frontend/test_legality.py`

**Step 1: Write the failing test**

Add or extend tests to assert the checked-in baseline targets expose the macro-ops already implemented by the frontend:

- `RMSNORM`
- `RMSNORM_GEMM`
- `WDQ_GEMM`
- `GEGLU`
- `ROPE`
- `KVSTORE`
- `KVLOAD`
- `SDPA`
- `SDPA_DECODE`
- `ELEM_ADD`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/config/test_profile_fixtures.py tests/unit/frontend/test_legality.py -v`
Expected: FAIL because the baseline profiles currently under-declare supported opcodes.

**Step 3: Write minimal implementation**

Update both baseline target profiles so their opcode lists match the already documented architecture contract and implemented lowering surface.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/config/test_profile_fixtures.py tests/unit/frontend/test_legality.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add profiles/targets/riscv_npu_single_core_v1.json profiles/targets/riscv_npu_dual_core_v1.json tests/unit/config/test_profile_fixtures.py tests/unit/frontend/test_legality.py
git commit -m "chore: align baseline opcodes with frontend lowering"
```

### Task 4: Publish the new frontend contract

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Write the failing checklist**

Confirm docs do not yet clearly state:

- what `frontend legality` means after target binding,
- why legal graphs can still contain unsupported nodes,
- that `ResidualAdd -> ELEM_ADD` is now implemented,
- that `embedding` and rope-table preprocessing remain out of scope for this batch.

**Step 2: Verify the checklist fails**

Re-open docs and confirm one or more items are missing.

**Step 3: Write minimal implementation**

Document:

- legality as structural + target-aware admission,
- unsupported nodes as a decomposition coverage gap, not a legality contradiction,
- new residual-add coverage,
- remaining gaps (`embedding`, rope-table preprocessing, fallback decomposition).

**Step 4: Verify the checklist passes**

Re-open docs and confirm all checklist items are present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md
git commit -m "docs: explain profile-aware legality and residual decomposition"
```
