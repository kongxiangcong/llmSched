# SPEC-10 Single-Core Overlap Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the first scheduler-facing overlap/occupancy semantics to single-core `ScheduleIR` so downstream stages can distinguish deterministic block order from actual staged issue timing.

**Architecture:** Extend `ScheduleBlock` with lightweight occupancy metadata rather than introducing a new timing IR. Single-core scheduling will continue to emit deterministic block sequences, but each block will now also carry explicit dependency edges plus `issue_slot` / `duration_slots`. The scheduler will use a conservative earliest-issue policy: stage order remains deterministic, inter-node dependencies follow producer-to-consumer edges, and only resource-disjoint stages may overlap.

**Tech Stack:** Pydantic models, scheduler planners, pytest unit/smoke tests, run-root JSON artifacts.

---

### Task 1: Extend `ScheduleIR` with occupancy metadata

**Files:**
- Modify: `src/llm_sched/ir/schedule_ir.py`
- Modify: `tests/unit/ir/test_schedule_ir_invariants.py`
- Modify: `tests/unit/ir/test_ir_roundtrip.py`

**Step 1: Write the failing test**

Add invariant coverage for:
- `depends_on`
- `issue_slot`
- `duration_slots`
- rejection of unknown dependency ids

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -q`

**Step 3: Write minimal implementation**

Add optional occupancy fields to `ScheduleBlock` and only the invariants needed for stable JSON roundtrip and dependency reference validation.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -q`

**Step 5: Commit**

```bash
git add src/llm_sched/ir/schedule_ir.py tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py
git commit -m "feat: add schedule occupancy metadata"
```

### Task 2: Add single-core overlap red tests

**Files:**
- Modify: `tests/unit/planning/test_single_core_scheduler.py`
- Modify: `tests/unit/pipeline/test_single_core_scheduling_workflow.py`
- Modify: `tests/smoke/test_phase_c_single_core_schedule_matrix.py`

**Step 1: Write the failing test**

Cover:
- producer/consumer chain keeps deterministic order but allows `node1.compute` and `node2.dma_in` to share an `issue_slot`
- blocks carry `depends_on`
- blocks carry positive `duration_slots`
- real Gemma3 single-core smoke emits non-zero `issue_slot` span

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -q`

**Step 3: Write minimal implementation**

Add conservative single-core earliest-issue scheduling:
- intra-node stage dependencies
- inter-node producer-consumer dependency edges
- resource conflict check using `resource_set`
- occupancy fields on each emitted block

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_single_core_scheduler.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -q`

**Step 5: Commit**

```bash
git add src/llm_sched/planning/single_core_scheduler.py tests/unit/planning/test_single_core_scheduler.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/smoke/test_phase_c_single_core_schedule_matrix.py
git commit -m "feat: add single-core overlap scheduling"
```

### Task 3: Keep descriptor compatibility stable

**Files:**
- Modify: `tests/unit/planning/test_descriptor_builder.py`
- Modify: `src/llm_sched/planning/descriptor_builder.py` only if required

**Step 1: Write the failing test**

If occupancy metadata changes descriptor consumption assumptions, add the minimal regression test proving `ScheduleIR -> DescriptorIR` still succeeds with overlap metadata present.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_descriptor_builder.py -q`

**Step 3: Write minimal implementation**

Keep descriptor generation oblivious to occupancy except for tolerating the new schedule fields.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_descriptor_builder.py -q`

**Step 5: Commit**

```bash
git add src/llm_sched/planning/descriptor_builder.py tests/unit/planning/test_descriptor_builder.py
git commit -m "test: preserve descriptor compatibility with overlap metadata"
```

### Task 4: Update handoff and roadmap

**Files:**
- Modify: `docs/development/phase-c-single-core-scheduler-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Step 1: Write the doc update**

Document:
- what occupancy metadata means
- what is still intentionally missing
- why dual-core overlap is still deferred

**Step 2: Verify the docs mention the new checkpoint**

Run: `git grep -n "occupancy\\|issue_slot\\|duration_slots" -- docs/development docs/plans`

**Step 3: Commit**

```bash
git add docs/development/phase-c-single-core-scheduler-handoff.md docs/development/evaluation-compiler-roadmap.md docs/development/README.md docs/plans/2026-03-09-spec-10-single-core-overlap-foundation.md
git commit -m "docs: add single-core overlap checkpoint"
```

### Task 5: Full verification batch

**Files:**
- No new files

**Step 1: Run focused verification**

Run: `python -m pytest tests/unit/ir/test_schedule_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py tests/unit/planning/test_single_core_scheduler.py tests/unit/pipeline/test_single_core_scheduling_workflow.py tests/unit/planning/test_descriptor_builder.py tests/smoke/test_phase_c_single_core_schedule_matrix.py -q`

**Step 2: Run full verification**

Run: `python -m pytest -q`

**Step 3: Run diff hygiene**

Run: `git diff --check`

**Step 4: Commit final batch**

```bash
git add -A
git commit -m "feat: add spec 10 single-core overlap foundation"
```
