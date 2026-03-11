# Pseudo Fallback Estimator Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first analysis-layer estimator for pseudo/fallback workloads by preserving estimable workload metadata in NIG and lowering it into Analysis IR.

**Architecture:** Extend `NIGNode` so lowering preserves output shape and canonical attrs from Graph IR. Build a narrow `NIG -> AnalysisIR` estimator that focuses on pseudo/fallback workloads (`ATTENTION_MASK_PREP`, `SHAPE_HELPER`, `LAYOUT_FALLBACK`, `EMBEDDING_LOOKUP`, `ROPE_TABLE`) and emits deterministic per-node metrics for bytes, cycles, and bottleneck tags without pretending to be cycle-accurate.

**Tech Stack:** Python 3.14, Pydantic IR models, `pytest`.

---

### Task 1: Preserve estimable workload metadata in NIG

**Files:**
- Modify: `src/llm_sched/ir/nig.py`
- Modify: `src/llm_sched/frontend/nig_lowering.py`
- Modify: `tests/unit/frontend/test_nig_lowering.py`

**Step 1: Write the failing tests**

Add assertions that lowered NIG nodes preserve:
- output `shape`
- canonical `attrs`

Cover at least:
- `Linear`
- `SDPA`
- `AttentionMaskPrep` or another pseudo/fallback node

**Step 2: Run the focused test**

Run:

```powershell
python -m pytest tests/unit/frontend/test_nig_lowering.py -v
```

Expected: new assertions fail because `NIGNode` does not carry shape/attrs yet.

**Step 3: Implement the minimal contract extension**

- Add `shape: list[int] = Field(default_factory=list)` to `NIGNode`
- Add `attrs: dict[str, Any] = Field(default_factory=dict)` to `NIGNode`
- Thread `shape` / `attrs` through all lowering paths

**Step 4: Run the focused test again**

Run:

```powershell
python -m pytest tests/unit/frontend/test_nig_lowering.py -v
```

Expected: focused lowering tests pass.

### Task 2: Add failing estimator tests

**Files:**
- Create: `tests/unit/analysis/test_nig_estimator.py`

**Step 1: Write the failing tests**

Add tests for a new estimator entrypoint that:
- accepts `NIGIR` and target hardware
- emits `AnalysisIR`
- creates records for pseudo/fallback nodes
- reports deterministic metrics:
  - `read_bytes`
  - `write_bytes`
  - `total_bytes`
  - `estimated_cycles`
  - `bandwidth_pressure`
- adds bottleneck tags such as `memory-bound` or `metadata-bound`

Use a tiny mixed NIG fixture with:
- `ATTENTION_MASK_PREP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`

**Step 2: Run the focused test**

Run:

```powershell
python -m pytest tests/unit/analysis/test_nig_estimator.py -v
```

Expected: FAIL because estimator module does not exist.

### Task 3: Implement the pseudo/fallback estimator

**Files:**
- Create: `src/llm_sched/analysis/__init__.py`
- Create: `src/llm_sched/analysis/nig_estimator.py`

**Step 1: Implement the minimal estimator**

Add an entrypoint such as:

```python
def estimate_nig_analysis(nig_ir: NIGIR, hardware: TargetProfile | ArchitectureCapabilities) -> AnalysisIR:
    ...
```

Implement deterministic formulas for:
- `ATTENTION_MASK_PREP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`
- `EMBEDDING_LOOKUP`
- `ROPE_TABLE`

Rules:
- bytes come from preserved `shape`, dtype, and macro-op-specific assumptions
- cycles are lightweight abstract estimates, not cycle-accurate
- bottleneck tags are explicit heuristics, not inferred from nonexistent scheduler data

**Step 2: Run the focused test again**

Run:

```powershell
python -m pytest tests/unit/analysis/test_nig_estimator.py -v
```

Expected: estimator tests pass.

### Task 4: Regressions and integration coverage

**Files:**
- Modify: `tests/unit/ir/test_ir_roundtrip.py`
- Modify: `tests/unit/ir/test_ir_traceability.py`
- Modify: `tests/unit/ir/test_nig_invariants.py`

**Step 1: Add or adjust regression coverage**

Ensure:
- new `NIGNode.shape` / `NIGNode.attrs` round-trip through JSON
- invariant tests still pass
- traceability behavior stays intact

**Step 2: Run targeted regression suites**

Run:

```powershell
python -m pytest tests/unit/ir -v
python -m pytest tests/unit/frontend/test_nig_lowering.py -v
python -m pytest tests/unit/analysis/test_nig_estimator.py -v
```

Expected: all targeted suites pass.

### Task 5: Docs and smoke

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Update docs**

Document:
- `NIGNode` now preserves estimable workload metadata
- the new estimator entrypoint
- the scope limit: pseudo/fallback workloads only

**Step 2: Run full verification**

Run:

```powershell
python -m pytest -v
git diff --check
```

Expected: full suite passes; no diff errors.

### Task 6: Real-model smoke and commit

**Files:**
- No source changes required unless smoke reveals regressions

**Step 1: Run a real Gemma3 smoke**

Use the existing Gemma3 decode smoke and confirm:
- `lower_graph_ir_to_nig` outputs shape/attrs for pseudo/fallback nodes
- `estimate_nig_analysis(...)` emits records for `ATTENTION_MASK_PREP`, `SHAPE_HELPER`, and `LAYOUT_FALLBACK`

**Step 2: Commit**

```powershell
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md docs/plans/2026-03-07-pseudo-fallback-estimator-foundation.md src/llm_sched/analysis/__init__.py src/llm_sched/analysis/nig_estimator.py src/llm_sched/frontend/nig_lowering.py src/llm_sched/ir/nig.py tests/unit/analysis/test_nig_estimator.py tests/unit/frontend/test_nig_lowering.py tests/unit/ir/test_ir_roundtrip.py tests/unit/ir/test_ir_traceability.py tests/unit/ir/test_nig_invariants.py
git commit -m "feat: add pseudo fallback nig estimator"
```
