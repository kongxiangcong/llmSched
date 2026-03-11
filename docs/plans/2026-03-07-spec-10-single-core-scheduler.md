# SPEC-10 Single-Core Scheduler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable `SPEC-10` single-core scheduler that consumes bound-NIG, `MemoryPlanArtifact`, and `TilingPlanArtifact`, and emits deterministic `ScheduleIR` blocks for single-core execution.

**Architecture:** Extend the existing `ScheduleIR` contract just enough to represent scheduler-relevant block identity, source macro-op, stage, and chosen tile candidate. Implement a deterministic single-core scheduler that lowers each supported macro-op into an ordered block sequence over `DMA`, `VPU`, `WDQ`, `MXU`, and writeback resources without overlap search. Wire it into a dedicated run-root workflow so Phase C can treat scheduling as a standalone artifact producer before descriptor generation.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, Typer CLI, existing run-root artifact contracts and Phase C planning modules.

---

### Task 1: Extend `ScheduleIR` for Scheduler Blocks

**Files:**
- Modify: `src/llm_sched/ir/schedule_ir.py`
- Modify: `tests/unit/ir/test_schedule_ir_invariants.py`
- Modify: `tests/unit/ir/test_ir_roundtrip.py`

**Step 1: Write the failing test**

```python
def test_schedule_ir_accepts_single_core_scheduler_block_metadata() -> None:
    schedule = validate_schedule_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "sched-001",
            "core_mode": "single-core",
            "blocks": [
                {
                    "block_id": "sched.block.linear.compute",
                    "core_id": 0,
                    "node_id": "nig.node.linear",
                    "macro_op": "WDQ_GEMM",
                    "stage": "compute",
                    "tiling_candidate_id": "nig.node.linear.m48.n128.k128",
                    "resource_set": ["WDQ", "MXU"],
                    "buffer_binding": {"input": "ping", "output": "pong"},
                    "barrier_in": [],
                    "barrier_out": [],
                    "order_key": 2,
                }
            ],
        }
    )

    assert schedule.blocks[0].stage == "compute"
```

Add a second invariant test:

```python
def test_single_core_schedule_rejects_core_link_resource() -> None:
    with pytest.raises(ValidationError):
        validate_schedule_ir({... "resource_set": ["Core Link"] ...})
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -v`
Expected: FAIL because `ScheduleBlock` does not yet accept scheduler metadata or resource restrictions.

**Step 3: Write minimal implementation**

Extend `ScheduleBlock` with optional scheduler fields:
- `node_id`
- `macro_op`
- `stage`
- `tiling_candidate_id`

Add single-core invariants:
- all blocks target exactly one core
- no `Core Link`
- no cross-core barrier use in `single-core`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/ir/schedule_ir.py tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py
git commit -m "feat: extend schedule ir for single-core scheduling"
```

### Task 2: Add Deterministic Single-Core Scheduler

**Files:**
- Create: `src/llm_sched/planning/single_core_scheduler.py`
- Modify: `src/llm_sched/planning/__init__.py`
- Test: `tests/unit/planning/test_single_core_scheduler.py`

**Step 1: Write the failing test**

```python
def test_plan_single_core_schedule_emits_ordered_blocks_for_quant_gemm() -> None:
    schedule = plan_single_core_schedule(bound_nig_ir, memory_plan, tiling_plan, target_profile, scenario)

    stages = [block.stage for block in schedule.blocks if block.node_id == "nig.node.linear"]
    assert stages == ["dma_in", "compute", "store"]
```

Add a second test for decode attention:

```python
def test_plan_single_core_schedule_uses_latency_first_decode_candidate() -> None:
    schedule = plan_single_core_schedule(bound_nig_ir, memory_plan, tiling_plan, target_profile, scenario_decode)

    block = next(block for block in schedule.blocks if block.node_id == "nig.node.attn.decode" and block.stage == "compute")
    assert block.tiling_candidate_id.endswith(".m1.n128.k128")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py -v`
Expected: FAIL because the scheduler module does not exist.

**Step 3: Write minimal implementation**

Implement:
- `plan_single_core_schedule(bound_nig_ir, memory_plan, tiling_plan, hardware, scenario)`
- support first-pass macro coverage:
  - `GEMM`
  - `WDQ_GEMM`
  - `RMSNORM_GEMM`
  - `SDPA`
  - `SDPA_DECODE`
- deterministic block lowering:
  - `dma_in`
  - optional `prepare`
  - `compute`
  - `store`

Do not implement overlap search, dual-core, or descriptor-facing encoding decisions.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/planning/single_core_scheduler.py src/llm_sched/planning/__init__.py tests/unit/planning/test_single_core_scheduler.py
git commit -m "feat: add single-core scheduler foundation"
```

### Task 3: Add Single-Core Scheduling Workflow

**Files:**
- Create: `src/llm_sched/pipeline/single_core_scheduling.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Test: `tests/unit/pipeline/test_single_core_scheduling_workflow.py`

**Step 1: Write the failing test**

```python
def test_run_single_core_scheduling_writes_schedule_ir(tmp_path: Path) -> None:
    result = run_single_core_scheduling(run_root)

    assert result.status == "completed"
    assert (run_root / "artifacts" / "schedule_ir.json").is_file()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py -v`
Expected: FAIL because the workflow module does not exist.

**Step 3: Write minimal implementation**

Workflow responsibilities:
- load `manifest.json`
- load `bound_nig_ir.json`
- load `memory_plan.json`
- load `tiling_plan.json`
- load target/scenario profiles
- call `plan_single_core_schedule(...)`
- write `artifacts/schedule_ir.json`
- update `manifest.artifact_index["schedule_ir"]`
- update `run-summary.json`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_single_core_scheduling_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/pipeline/single_core_scheduling.py src/llm_sched/pipeline/__init__.py tests/unit/pipeline/test_single_core_scheduling_workflow.py
git commit -m "feat: add single-core scheduling workflow"
```

### Task 4: Add CLI Entry and Smoke Gate

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Test: `tests/smoke/test_cli_run_single_core_scheduling.py`
- Test: `tests/smoke/test_phase_c_single_core_schedule_matrix.py`

**Step 1: Write the failing test**

```python
def test_run_single_core_scheduling_writes_schedule_artifact(tmp_path: Path) -> None:
    result = run_cli("run-single-core-scheduling", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0
```

Add matrix expectations:
- only `single-core` targets are valid
- emitted blocks all bind to core `0`
- no `Core Link`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_single_core_scheduling.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -v`
Expected: FAIL because the CLI command is missing.

**Step 3: Write minimal implementation**

Add `run-single-core-scheduling` to the CLI and route to the new workflow.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_single_core_scheduling.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/cli/main.py tests/smoke/test_cli_run_single_core_scheduling.py tests/smoke/test_phase_c_single_core_schedule_matrix.py
git commit -m "feat: add single-core scheduling cli and smoke gate"
```

### Task 5: Update Phase C Docs and Handoff

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-c-tile-planner-handoff.md`
- Create: `docs/development/phase-c-single-core-scheduler-handoff.md`

**Step 1: Write the failing test**

Use a documentation checklist:
- `SPEC-10` status must move from `not_started` to `in_progress`
- README must mention `run-single-core-scheduling`
- handoff must describe stable `ScheduleIR` output and single-core assumptions

**Step 2: Run the checklist**

Run:
- `Get-ChildItem docs/development -Filter *.md | Select-String -Pattern "run-single-core-scheduling|SPEC-10|ScheduleIR"`

Expected: Missing or stale references before the edits.

**Step 3: Write minimal implementation**

Document:
- what is stable now
- what SPEC-12 can assume
- what remains outside scope

**Step 4: Run verification**

Run:
- `Get-ChildItem docs/development -Filter *.md | Select-String -Pattern "run-single-core-scheduling|SPEC-10|ScheduleIR"`

Expected: Updated references present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-tile-planner-handoff.md docs/development/phase-c-single-core-scheduler-handoff.md
git commit -m "docs: update phase c single-core scheduling status"
```

### Task 6: Final Verification Batch

**Files:**
- Verify all files changed in Tasks 1-5.

**Step 1: Run focused verification**

Run:
- `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_single_core_scheduler.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/smoke/test_cli_run_single_core_scheduling.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -v`

Expected: PASS

**Step 2: Run full regression**

Run:
- `python -m pytest -q`

Expected: PASS with zero failures.

**Step 3: Run diff hygiene check**

Run:
- `git diff --check`

Expected: No diff errors.

**Step 4: Commit final docs/checkpoint if needed**

```bash
git add -A
git commit -m "feat: add spec 10 single-core scheduler foundation"
```

**Step 5: Prepare handoff**

Report:
- implemented tasks
- fresh verification output
- remaining SPEC-10 gaps before SPEC-12
