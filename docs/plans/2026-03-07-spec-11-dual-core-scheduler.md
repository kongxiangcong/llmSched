# SPEC-11 Dual-Core Scheduler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable `SPEC-11` dual-core scheduler that consumes bound-NIG, `MemoryPlanArtifact`, and `TilingPlanArtifact`, and emits explicit dual-core `ScheduleIR` blocks with core assignment, transfer, and barrier semantics.

**Architecture:** Extend the existing `ScheduleIR` contract just enough to represent dual-core transfer stages, peer-core identity, and sync/transfer cost hints. Implement a deterministic dual-core scheduler that partitions supported macro-ops across core `0` and core `1`, inserts explicit transfer blocks and barrier names for cross-core dependencies, and chooses `Core Link` or `DMA` transfer resources based on target capability. Keep the scope narrow: no global search, no automatic single-vs-dual mode switching, and no descriptor encoding.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, Typer CLI, existing Phase C artifact contracts.

---

### Task 1: Extend `ScheduleIR` for Dual-Core Transfer Metadata

**Files:**
- Modify: `src/llm_sched/ir/schedule_ir.py`
- Modify: `tests/unit/ir/test_schedule_ir_invariants.py`
- Modify: `tests/unit/ir/test_ir_roundtrip.py`

**Step 1: Write the failing test**

```python
def test_schedule_ir_accepts_dual_core_transfer_block_metadata() -> None:
    schedule = validate_schedule_ir(
        {
            "ir_version": "phase-a.v1",
            "graph_id": "sched-dual-001",
            "core_mode": "dual-core",
            "blocks": [
                {
                    "block_id": "sched.block.transfer.0",
                    "core_id": "both",
                    "node_id": "nig.node.linear",
                    "macro_op": "WDQ_GEMM",
                    "stage": "transfer",
                    "tiling_candidate_id": "nig.node.linear.m48.n128.k128",
                    "resource_set": ["Core Link"],
                    "buffer_binding": {"input": "pong", "output": "pong"},
                    "barrier_in": ["sync.linear.0"],
                    "barrier_out": ["sync.linear.1"],
                    "order_key": 3,
                    "peer_core_id": 1,
                    "transfer_kind": "core_link",
                    "transfer_bytes": 24576,
                    "sync_cost_cycles": 32,
                }
            ],
        }
    )

    assert schedule.blocks[0].stage == "transfer"
```

Add a second invariant test:

```python
def test_dual_core_schedule_rejects_invalid_peer_core_id() -> None:
    with pytest.raises(ValidationError):
        validate_schedule_ir({... "core_id": 0, "peer_core_id": 0 ...})
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -v`
Expected: FAIL because `ScheduleBlock` does not yet accept dual-core transfer metadata.

**Step 3: Write minimal implementation**

Extend `ScheduleBlock` with optional dual-core fields:
- `peer_core_id`
- `transfer_kind`
- `transfer_bytes`
- `sync_cost_cycles`

Extend `stage` to include `transfer`.

Add dual-core invariants:
- `peer_core_id` must differ from `core_id`
- `transfer` blocks must declare non-empty barriers
- `Core Link` may only appear in `dual-core`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/ir/schedule_ir.py tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py
git commit -m "feat: extend schedule ir for dual-core scheduling"
```

### Task 2: Add Deterministic Dual-Core Scheduler

**Files:**
- Create: `src/llm_sched/planning/dual_core_scheduler.py`
- Modify: `src/llm_sched/planning/__init__.py`
- Test: `tests/unit/planning/test_dual_core_scheduler.py`

**Step 1: Write the failing test**

```python
def test_plan_dual_core_schedule_inserts_transfer_between_split_nodes() -> None:
    schedule = plan_dual_core_schedule(bound_nig_ir, memory_plan, tiling_plan, target_profile, scenario)

    transfer_blocks = [block for block in schedule.blocks if block.stage == "transfer"]
    assert transfer_blocks
    assert transfer_blocks[0].transfer_kind in {"core_link", "dma"}
```

Add a second test:

```python
def test_plan_dual_core_schedule_assigns_blocks_to_both_cores() -> None:
    schedule = plan_dual_core_schedule(...)
    assert {block.core_id for block in schedule.blocks if block.core_id != "both"} == {0, 1}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -v`
Expected: FAIL because the scheduler module does not exist.

**Step 3: Write minimal implementation**

Implement:
- `plan_dual_core_schedule(bound_nig_ir, memory_plan, tiling_plan, hardware, scenario)`
- deterministic partition policy:
  - alternate supported nodes across core `0` and `1`
  - insert `transfer` blocks when producer and consumer land on different cores
  - choose `Core Link` if enabled, otherwise `DMA`
  - use `sync.barrier.*` names to connect producer -> transfer -> consumer

Support first-pass macro coverage:
- `GEMM`
- `WDQ_GEMM`
- `RMSNORM_GEMM`
- `SDPA`
- `SDPA_DECODE`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_dual_core_scheduler.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/planning/dual_core_scheduler.py src/llm_sched/planning/__init__.py tests/unit/planning/test_dual_core_scheduler.py
git commit -m "feat: add dual-core scheduler foundation"
```

### Task 3: Add Dual-Core Scheduling Workflow

**Files:**
- Create: `src/llm_sched/pipeline/dual_core_scheduling.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Test: `tests/unit/pipeline/test_dual_core_scheduling_workflow.py`

**Step 1: Write the failing test**

```python
def test_run_dual_core_scheduling_writes_schedule_ir(tmp_path: Path) -> None:
    result = run_dual_core_scheduling(run_root)

    assert result.status == "completed"
    assert (run_root / "artifacts" / "dual_core_schedule_ir.json").is_file()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_dual_core_scheduling_workflow.py -v`
Expected: FAIL because the workflow module does not exist.

**Step 3: Write minimal implementation**

Workflow responsibilities:
- load `manifest.json`
- load `bound_nig_ir.json`
- load `memory_plan.json`
- load `tiling_plan.json`
- load target/scenario profiles
- call `plan_dual_core_schedule(...)`
- write `artifacts/dual_core_schedule_ir.json`
- update `manifest.artifact_index["dual_core_schedule_ir"]`
- update `run-summary.json`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_dual_core_scheduling_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/pipeline/dual_core_scheduling.py src/llm_sched/pipeline/__init__.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py
git commit -m "feat: add dual-core scheduling workflow"
```

### Task 4: Add CLI Entry and Smoke Gate

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Test: `tests/smoke/test_cli_run_dual_core_scheduling.py`
- Test: `tests/smoke/test_phase_c_dual_core_schedule_matrix.py`

**Step 1: Write the failing test**

```python
def test_run_dual_core_scheduling_writes_schedule_artifact(tmp_path: Path) -> None:
    result = run_cli("run-dual-core-scheduling", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0
```

Add matrix expectations:
- only `dual-core` targets are valid
- emitted schedules use both cores
- transfer blocks are explicit

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_dual_core_scheduling.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -v`
Expected: FAIL because the CLI command is missing.

**Step 3: Write minimal implementation**

Add `run-dual-core-scheduling` to the CLI and route to the new workflow.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_dual_core_scheduling.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/cli/main.py tests/smoke/test_cli_run_dual_core_scheduling.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py
git commit -m "feat: add dual-core scheduling cli and smoke gate"
```

### Task 5: Update Phase C Docs and Handoff

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Create: `docs/development/phase-c-dual-core-scheduler-handoff.md`

**Step 1: Write the failing test**

Use a documentation checklist:
- `SPEC-11` status must move from `not_started` to `in_progress`
- README must mention `run-dual-core-scheduling`
- handoff must describe explicit transfer/barrier semantics

**Step 2: Run the checklist**

Run:
- `Get-ChildItem docs/development -Filter *.md | Select-String -Pattern "run-dual-core-scheduling|SPEC-11|dual_core_schedule_ir"`

Expected: Missing or stale references before the edits.

**Step 3: Write minimal implementation**

Document:
- what is stable now
- what SPEC-12 and SPEC-13 can assume
- what remains outside scope

**Step 4: Run verification**

Run:
- `Get-ChildItem docs/development -Filter *.md | Select-String -Pattern "run-dual-core-scheduling|SPEC-11|dual_core_schedule_ir"`

Expected: Updated references present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-single-core-scheduler-handoff.md docs/development/phase-c-dual-core-scheduler-handoff.md
git commit -m "docs: update phase c dual-core scheduling status"
```

### Task 6: Final Verification Batch

**Files:**
- Verify all files changed in Tasks 1-5.

**Step 1: Run focused verification**

Run:
- `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_dual_core_scheduler.py tests/unit/pipeline/test_dual_core_scheduling_workflow.py tests/smoke/test_cli_run_dual_core_scheduling.py tests/smoke/test_phase_c_dual_core_schedule_matrix.py -v`

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
git commit -m "feat: add spec 11 dual-core scheduler foundation"
```

**Step 5: Prepare handoff**

Report:
- implemented tasks
- fresh verification output
- remaining SPEC-11 gaps before SPEC-12/13
