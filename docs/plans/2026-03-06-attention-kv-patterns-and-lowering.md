# Attention KV Patterns and Lowering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the Gemma3 frontend to canonicalize `ROPE`, `KVStore`, `KVLoad`, and `SDPA` attention subgraphs and lower them into attention/KV NIG macro-ops.

**Architecture:** Keep the work split into two layers. The canonicalizer will rewrite Gemma3-style attention subgraphs into stable Graph IR nodes (`ROPE`, `KVStore`, `KVLoad`, `SDPA`) without making scheduling decisions; the NIG lowerer will then map those canonical nodes into `ROPE`, `KVSTORE`, `KVLOAD`, `SDPA`, and `SDPA_DECODE`, using `ScenarioProfile` when needed to distinguish prefill from decode.

**Tech Stack:** Python 3.14, `onnx`, `pydantic`, `pytest`.

---

### Task 1: Add ROPE and KV canonical patterns

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`
- Modify: `tests/unit/frontend/test_canonicalize.py`

**Step 1: Write the failing test**

Add Graph IR fixtures that assert:

- standard RoPE branch `Mul(x, cos) + Mul(rotate_half(x), sin)` becomes `ROPE`,
- `Concat(Slice(past), current)` to `present.key/value` becomes `KVStore`,
- `Unsqueeze -> Expand -> Reshape -> [Transpose]` from `present.key/value` becomes `KVLoad`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: FAIL because these patterns are not yet canonicalized.

**Step 3: Write minimal implementation**

Extend canonicalization with:

- one `ROPE` node per rotated tensor,
- one `KVStore` node per `present.*` append path,
- one `KVLoad` node per attention-ready K/V expansion path,
- traceability preservation across all fused nodes.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/canonicalize.py tests/unit/frontend/test_canonicalize.py
git commit -m "feat: add attention rope and kv canonical patterns"
```

### Task 2: Add SDPA composite canonicalization

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`
- Modify: `tests/unit/frontend/test_canonicalize.py`

**Step 1: Write the failing test**

Add a canonicalization fixture that asserts:

- `MatMul(q, k_t) -> Add(mask) -> Softmax -> MatMul(v) -> Transpose -> Reshape`
  becomes one `SDPA` node,
- the `SDPA` node consumes canonical `ROPE` and `KVLoad` outputs,
- query/kv token hints are preserved in attrs when available.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: FAIL because the SDPA composite is not yet recognized.

**Step 3: Write minimal implementation**

Add one `SDPA` canonical rewrite pass that:

- requires the exact `MatMul -> Add -> Softmax -> MatMul -> Transpose -> Reshape` chain,
- preserves traceability across the full fused path,
- stores `query_len` and `kv_len` hints in attrs when source shapes are concrete.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/canonicalize.py tests/unit/frontend/test_canonicalize.py
git commit -m "feat: add sdpa canonical graph pattern"
```

### Task 3: Extend NIG lowering for attention and KV

**Files:**
- Modify: `src/llm_sched/frontend/nig_lowering.py`
- Modify: `src/llm_sched/frontend/__init__.py`
- Modify: `tests/unit/frontend/test_nig_lowering.py`

**Step 1: Write the failing test**

Add NIG lowering fixtures that assert:

- `ROPE` lowers to `ROPE`,
- `KVStore` lowers to `KVSTORE`,
- `KVLoad` lowers to `KVLOAD`,
- `SDPA` lowers to `SDPA` for prefill scenario,
- `SDPA` lowers to `SDPA_DECODE` for decode scenario.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_nig_lowering.py -v`
Expected: FAIL because the lowerer does not yet support these nodes or scenario-aware SDPA mode selection.

**Step 3: Write minimal implementation**

Extend `lower_graph_ir_to_nig()` to accept optional `ScenarioProfile` and add lowering rules for:

- `ROPE`,
- `KVStore`,
- `KVLoad`,
- `SDPA` / `SDPA_DECODE`.

Use `scenario.mode` when provided to select `SDPA_DECODE`; otherwise fall back to shape hints.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_nig_lowering.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/nig_lowering.py src/llm_sched/frontend/__init__.py tests/unit/frontend/test_nig_lowering.py
git commit -m "feat: add attention and kv nig lowering"
```

### Task 4: Publish the attention/KV frontend contract

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Write the failing checklist**

Confirm docs do not fully describe:

- `ROPE` / `KVStore` / `KVLoad` / `SDPA` canonical coverage,
- scenario-aware `SDPA` vs `SDPA_DECODE` lowering,
- remaining non-goals such as full attention legality and residual unsupported nodes.

**Step 2: Verify the checklist fails**

Re-open docs and confirm one or more items are missing.

**Step 3: Write minimal implementation**

Document:

- the new canonical nodes,
- scenario-aware SDPA lowering,
- remaining gaps (`mask/rope legality`, unsupported fallbacks, scheduler not started).

**Step 4: Verify the checklist passes**

Re-open docs and confirm all checklist items are present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md
git commit -m "docs: describe attention and kv frontend coverage"
```
