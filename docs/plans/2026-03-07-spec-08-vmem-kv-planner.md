# SPEC-08 VMEM / KV Planner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first deterministic VMEM/KV/address planner that consumes bound-NIG and emits `MemAllocTable`, KV address formulas, and VMEM fit diagnostics.

**Architecture:** This phase starts with a static planning foundation rather than a full lifetime-optimized allocator. The planner will consume bound-NIG plus target/scenario profiles, derive deterministic working-set allocations for VMEM regions, emit KV DDR address formulas, and surface fit failures with region-specific diagnostics. The output contract must already be stable enough for later tiling and scheduling stages to consume directly.

**Tech Stack:** Python 3.14, Pydantic models, existing `TargetProfile` / `ScenarioProfile` / bound-NIG contracts, pytest.

---

### Task 1: Add Memory Planning Contracts

**Files:**
- Create: `src/llm_sched/contracts/memory_plan.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Test: `tests/unit/contracts/test_memory_plan_contract.py`

**Step 1: Write the failing test**

Add contract tests that validate:

- `MemoryPlanArtifact` accepts:
  - `graph_id`
  - `scenario_name`
  - `core_mode`
  - `allocations`
  - `region_summaries`
  - `kv_formulas`
  - `diagnostics`
- region summaries reject negative `used_bytes`
- KV formulas require positive strides

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_memory_plan_contract.py -v`

Expected: FAIL because `memory_plan.py` does not exist yet.

**Step 3: Write minimal implementation**

Create models for:

- `PlannedAllocation`
- `RegionSummary`
- `KVAddressFormula`
- `VMEMFitDiagnostic`
- `MemoryPlanArtifact`

Keep fields minimal and deterministic. Do not add scheduling concerns or descriptor fields yet.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_memory_plan_contract.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/memory_plan.py src/llm_sched/contracts/__init__.py tests/unit/contracts/test_memory_plan_contract.py
git commit -m "feat: add memory planning contracts"
```

### Task 2: Implement Static VMEM / KV Planner Foundation

**Files:**
- Create: `src/llm_sched/planning/__init__.py`
- Create: `src/llm_sched/planning/memory_planner.py`
- Test: `tests/unit/planning/test_memory_planner.py`

**Step 1: Write the failing test**

Add planner tests for:

```python
def test_plan_memory_for_quantized_gemm_uses_weight_quant_and_accum_regions():
    ...

def test_plan_memory_for_decode_kv_ops_emits_formula_with_layer_stride():
    ...

def test_plan_memory_reports_region_overflow_with_offending_nodes():
    ...
```

Assertions should cover:

- `WDQ_GEMM` allocates `weight`, `quant`, `wdq_reserved`, `accum`, and activation staging regions
- decode KV path emits deterministic `KV_LAYER_STRIDE` and `KV_TOKEN_STRIDE`
- overflow diagnostics identify the overflowing region and offending node

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_memory_planner.py -v`

Expected: FAIL because `memory_planner.py` does not exist yet.

**Step 3: Write minimal implementation**

Implement:

- `plan_memory_artifact(bound_nig_ir, hardware, scenario)`
- dtype/element byte helpers
- deterministic default tile assumptions:
  - `decode -> M_tile=1`
  - `prefill -> M_tile=64`
  - `K_tile=N_tile=128`
- region planning heuristics:
  - activation staging -> `ping` / `pong`
  - weight staging -> `weight`
  - accumulators -> `accum`
  - op-local vector scratch -> `misc`
  - WDQ scratch -> `wdq_reserved`
  - scale / zp staging -> `quant`
- KV formula generation using `LBHSD` and layer/token/head/dim stride
- layer id inference from `audit_ref.source_ids`

Keep this planner static and deterministic. Do not implement lifetime reuse optimization or cross-core transfer routing yet.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_memory_planner.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/planning/__init__.py src/llm_sched/planning/memory_planner.py tests/unit/planning/test_memory_planner.py
git commit -m "feat: add static vmem and kv planner foundation"
```

### Task 3: Add Planner Pipeline Entry and Artifact Dump

**Files:**
- Create: `src/llm_sched/pipeline/memory_planning.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Test: `tests/unit/pipeline/test_memory_planning_workflow.py`

**Step 1: Write the failing test**

Add a workflow test that:

- loads bound-NIG from an initialized frontend run
- executes memory planning
- writes `artifacts/memory_plan.json`
- validates the artifact schema

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_memory_planning_workflow.py -v`

Expected: FAIL because the pipeline entry does not exist yet.

**Step 3: Write minimal implementation**

Implement a dedicated pipeline function rather than overloading `run_frontend_analysis`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_memory_planning_workflow.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/pipeline/memory_planning.py src/llm_sched/pipeline/__init__.py tests/unit/pipeline/test_memory_planning_workflow.py
git commit -m "feat: add memory planning workflow"
```

### Task 4: Add CLI / Smoke Coverage for SPEC-08

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Modify: `tests/smoke/test_cli_run_frontend_analysis.py`
- Create: `tests/smoke/test_cli_run_memory_planning.py`
- Modify: `docs/development/README.md`

**Step 1: Write the failing test**

Add smoke coverage for:

- `llm-sched run-memory-planning --run-root ...`
- artifact existence and manifest indexing

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_memory_planning.py -v`

Expected: FAIL because the CLI command does not exist yet.

**Step 3: Write minimal implementation**

Add a dedicated CLI entrypoint and document the new artifact.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_memory_planning.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/cli/main.py tests/smoke/test_cli_run_memory_planning.py tests/smoke/test_cli_run_frontend_analysis.py docs/development/README.md
git commit -m "feat: expose memory planning run workflow"
```

### Task 5: Publish SPEC-08 Foundation Handoff

**Files:**
- Create: `docs/development/phase-c-memory-planner-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Write the handoff doc**

Document:

- stable memory plan contract
- default tile assumptions used by planner
- known limitations
- next dependency to `SPEC-09`

**Step 2: Verify docs**

Run:

- `python -m pytest tests/unit/contracts/test_memory_plan_contract.py tests/unit/planning/test_memory_planner.py -v`
- `git diff --check`

Expected: PASS / no diff errors

**Step 3: Commit**

```bash
git add docs/development/phase-c-memory-planner-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md
git commit -m "docs: publish spec 08 memory planner handoff"
```
