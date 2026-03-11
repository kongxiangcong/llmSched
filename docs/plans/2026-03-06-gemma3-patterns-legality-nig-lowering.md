# Gemma3 Canonical Patterns, Legality, and NIG Lowering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the frontend so Gemma3-style ONNX graphs can be canonicalized into stable Graph IR patterns, checked for frontend legality, and lowered into an initial NIG workload graph.

**Architecture:** Keep the pipeline split into four explicit stages: import, legality, canonicalization, and GraphIR-to-NIG lowering. Canonicalization will normalize Gemma3 framework subgraphs into stable Graph IR nodes such as `Linear`, `RMSNorm`, and `GeGLU`; the lowerer will then map those canonical nodes into hardware-facing NIG macro-ops such as `WDQ_GEMM`, `RMSNORM_GEMM`, `RMSNORM`, and `GEGLU`.

**Tech Stack:** Python 3.14, `onnx`, `pydantic`, `pytest`.

---

### Task 1: Add frontend legality diagnostics

**Files:**
- Create: `src/llm_sched/frontend/legality.py`
- Modify: `src/llm_sched/frontend/__init__.py`
- Create: `tests/unit/frontend/test_legality.py`

**Step 1: Write the failing test**

Create Graph IR fixtures that assert:

- a graph with `If` is rejected as unsupported control-flow,
- a graph with `shape=[1, -1, 1152]` is rejected as unresolved dynamic shape,
- a graph with `attrs["layout"] = "NHWC"` is rejected as unsupported layout,
- a quantized `Linear` without `group_size` is rejected as missing quant metadata.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_legality.py -v`
Expected: FAIL because legality helpers do not exist.

**Step 3: Write minimal implementation**

Implement:

- `FrontendLegalityIssue`
- `FrontendLegalityError`
- `collect_frontend_legality_issues(graph_ir)`
- `validate_frontend_legality(graph_ir)`

Rules:

- reject control-flow ops: `If`, `Loop`, `Scan`;
- reject unresolved dynamic dims (`<= 0`);
- reject unsupported layouts outside `SD/HSD/BHSD/LBHSD`;
- require `group_size` and `weight_dtype` on quantized `Linear`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_legality.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/legality.py src/llm_sched/frontend/__init__.py tests/unit/frontend/test_legality.py
git commit -m "feat: add frontend legality diagnostics"
```

### Task 2: Expand Gemma3 canonical patterns

**Files:**
- Modify: `src/llm_sched/frontend/canonicalize.py`
- Modify: `tests/unit/frontend/test_canonicalize.py`

**Step 1: Write the failing test**

Add canonicalization fixtures that assert:

- `MatMulNBits` becomes quantized `Linear` with `weight_dtype=int4`,
- `Pow -> ReduceMean -> Add -> Sqrt -> Div -> Mul -> Mul` becomes `RMSNorm`,
- Gemma3 GELU-tanh branch multiplied by the sibling projection becomes `GeGLU`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: FAIL because canonicalizer does not yet rewrite these patterns.

**Step 3: Write minimal implementation**

Extend canonicalization with pure Graph IR passes:

- normalize `MatMulNBits` to `Linear`,
- match Gemma3 RMSNorm with epsilon add and scale multiply,
- match Gemma3 GeGLU via GELU-tanh branch multiplied by `up` projection,
- preserve `source_ref` / `audit_ref` across fused nodes.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/canonicalize.py tests/unit/frontend/test_canonicalize.py
git commit -m "feat: add gemma3 canonical graph patterns"
```

### Task 3: Lower canonical Graph IR to NIG

**Files:**
- Create: `src/llm_sched/frontend/nig_lowering.py`
- Modify: `src/llm_sched/frontend/__init__.py`
- Create: `tests/unit/frontend/test_nig_lowering.py`

**Step 1: Write the failing test**

Create canonical Graph IR fixtures that assert:

- `Linear(weight_dtype=int4)` lowers to `WDQ_GEMM`,
- `RMSNorm -> Linear(weight_dtype=int4)` lowers to one `RMSNORM_GEMM`,
- `RMSNorm` alone lowers to `RMSNORM`,
- `GeGLU` lowers to `GEGLU`,
- unsupported compute nodes raise an explicit lowering error instead of being dropped.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_nig_lowering.py -v`
Expected: FAIL because the lowerer does not exist.

**Step 3: Write minimal implementation**

Implement:

- `GraphToNIGLoweringError`
- `lower_graph_ir_to_nig(graph_ir)`

Rules:

- skip `Input` and `Constant` nodes,
- fuse `RMSNorm` followed by single-consumer `Linear` into `RMSNORM_GEMM`,
- lower quantized `Linear` to `WDQ_GEMM`,
- lower bf16/fp16 `Linear` to `GEMM`,
- lower `RMSNorm` to `RMSNORM`,
- lower `GeGLU` to `GEGLU`,
- preserve traceability into `NIGNode.source_ref` and `audit_ref`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_nig_lowering.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/nig_lowering.py src/llm_sched/frontend/__init__.py tests/unit/frontend/test_nig_lowering.py
git commit -m "feat: lower canonical graph ir to nig"
```

### Task 4: Publish the new frontend pipeline contract

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Write the failing checklist**

Check that the docs currently do not fully describe:

- legality entrypoints,
- Gemma3 canonical pattern coverage,
- NIG lowering entrypoint and current lowerable macro-ops.

**Step 2: Verify the checklist fails**

Re-open both docs and confirm one or more checklist items are missing.

**Step 3: Write minimal implementation**

Document:

- `validate_frontend_legality`,
- `lower_graph_ir_to_nig`,
- current pattern coverage (`Linear`, `RMSNorm`, `GeGLU`),
- explicit non-goals (`ROPE`, `SDPA`, `KV`, full legality coverage).

**Step 4: Verify the checklist passes**

Re-open both docs and confirm all checklist items are present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md
git commit -m "docs: describe gemma3 frontend and nig lowering"
```
