# SPEC-12 Descriptor And ISA Mapping Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable `ScheduleIR -> DescriptorIR` foundation plus ISA coverage reporting for single-core and dual-core schedule artifacts.

**Architecture:** Reuse the current `ScheduleIR` as the only scheduling input surface. First freeze a descriptor-facing contract that can represent control fields, shape packing, address bindings, transfer descriptors, and audit traceability. Then add a deterministic descriptor builder and a lightweight ISA coverage report that classifies mapped and unmapped schedule blocks without pretending to be a full hardware packer.

**Tech Stack:** Python 3.14, Pydantic models, existing run-root pipeline/CLI pattern, pytest smoke/unit tests.

---

### Task 1: Extend Descriptor Contracts For Schedule-Derived Encoding

**Files:**
- Modify: `src/llm_sched/ir/descriptor_ir.py`
- Modify: `tests/unit/ir/test_descriptor_ir_invariants.py`
- Modify: `tests/unit/ir/test_ir_roundtrip.py`

**Step 1: Write the failing tests**

Add tests for:
- transfer descriptors carrying `kind`, `src_core_id`, `dst_core_id`, `transfer_bytes`
- descriptor records carrying `schedule_block_id`
- descriptor records carrying packed width metadata such as `encoding_bits=512`
- descriptor IR rejecting duplicate `schedule_block_id` reuse when descriptor ids differ but block mapping is ambiguous

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -q`
Expected: FAIL because the current schema does not accept the new fields/invariants.

**Step 3: Write minimal implementation**

Implement:
- `DescriptorRecord.schedule_block_id`
- `DescriptorRecord.encoding_bits`
- `DescriptorRecord.transfer_fields`
- validator checks for unique descriptor ids and unique `schedule_block_id`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/ir/test_ir_roundtrip.py -q`
Expected: PASS

### Task 2: Add ISA Coverage Report Contract

**Files:**
- Create: `src/llm_sched/contracts/isa_coverage_report.py`
- Create: `tests/unit/contracts/test_isa_coverage_report.py`

**Step 1: Write the failing test**

Add a contract test for:
- `mapped_descriptor_count`
- `unmapped_block_count`
- `opcode_counts`
- `gap_counts`
- per-block gaps keyed by `schedule_block_id`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_isa_coverage_report.py -q`
Expected: FAIL because the contract file does not exist.

**Step 3: Write minimal implementation**

Create a small Pydantic contract with:
- `ISACoverageIssue`
- `ISACoverageSummary`
- `ISACoverageReport`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_isa_coverage_report.py -q`
Expected: PASS

### Task 3: Add Deterministic Descriptor Builder

**Files:**
- Create: `src/llm_sched/planning/descriptor_builder.py`
- Modify: `src/llm_sched/planning/__init__.py`
- Create: `tests/unit/planning/test_descriptor_builder.py`

**Step 1: Write the failing tests**

Add builder tests for:
- single-core compute blocks mapping to descriptors with opcode, packed shape, address fields, and `schedule_block_id`
- dual-core transfer blocks mapping to transfer descriptors with `Core Link` vs `DMA`
- unsupported schedule blocks producing ISA coverage gaps rather than silent drops

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_descriptor_builder.py -q`
Expected: FAIL because the builder does not exist.

**Step 3: Write minimal implementation**

Implement:
- `build_descriptor_artifacts(schedule_ir, bound_nig_ir, memory_plan, hardware, scenario)`
- deterministic descriptor id generation
- opcode mapping directly from `ScheduleBlock.macro_op` / `stage`
- shape packing from `tiling_candidate_id` and block metadata when available
- address field binding from `buffer_binding`
- coverage gaps for unmapped blocks

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_descriptor_builder.py -q`
Expected: PASS

### Task 4: Add Run-Root Workflow

**Files:**
- Create: `src/llm_sched/pipeline/descriptor_generation.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Create: `tests/unit/pipeline/test_descriptor_generation_workflow.py`

**Step 1: Write the failing test**

Add a workflow test verifying:
- input artifacts are `bound_nig_ir`, `memory_plan`, and either `schedule_ir` or `dual_core_schedule_ir`
- outputs are `artifacts/descriptor_ir.json` and `reports/isa_coverage_report.json`
- manifest/run-summary updates are stable

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py -q`
Expected: FAIL because the workflow does not exist.

**Step 3: Write minimal implementation**

Implement a run-root workflow mirroring the current Phase C pattern:
- detect single-core vs dual-core schedule artifact
- load artifacts
- emit descriptor and coverage outputs
- update `manifest.artifact_index`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_descriptor_generation_workflow.py -q`
Expected: PASS

### Task 5: Add CLI And Smoke Gates

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Create: `tests/smoke/test_cli_run_descriptor_generation.py`
- Create: `tests/smoke/test_phase_c_descriptor_matrix.py`

**Step 1: Write the failing tests**

Add smoke tests for:
- `llm-sched run-descriptor-generation --run-root ...`
- single-core and dual-core Gemma3 matrix runs
- descriptor artifact and ISA coverage report existence
- failure path without traceback when schedule artifacts are missing

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_descriptor_generation.py tests/smoke/test_phase_c_descriptor_matrix.py -q`
Expected: FAIL because the CLI command does not exist.

**Step 3: Write minimal implementation**

Add CLI wiring and user-facing messages only. Do not add extra command-line switches in this batch.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_descriptor_generation.py tests/smoke/test_phase_c_descriptor_matrix.py -q`
Expected: PASS

### Task 6: Docs, Handoff, Verification, Commit

**Files:**
- Create: `docs/development/phase-c-descriptor-handoff.md`
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`

**Step 1: Update docs**

Document:
- stable `DescriptorIR` assumptions
- ISA coverage report shape
- CLI/workflow entrypoint
- what `SPEC-13` may now assume

**Step 2: Run focused verification**

Run:
- `python -m pytest tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/contracts/test_isa_coverage_report.py tests/unit/planning/test_descriptor_builder.py tests/unit/pipeline/test_descriptor_generation_workflow.py tests/smoke/test_cli_run_descriptor_generation.py tests/smoke/test_phase_c_descriptor_matrix.py -q`

Expected: PASS

**Step 3: Run full verification**

Run:
- `python -m pytest -q`
- `git diff --check`

Expected: PASS with no diff errors.

**Step 4: Commit**

```bash
git add src/llm_sched/ir/descriptor_ir.py src/llm_sched/contracts/isa_coverage_report.py src/llm_sched/planning/descriptor_builder.py src/llm_sched/pipeline/descriptor_generation.py src/llm_sched/cli/main.py docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-descriptor-handoff.md tests/unit/ir/test_descriptor_ir_invariants.py tests/unit/contracts/test_isa_coverage_report.py tests/unit/planning/test_descriptor_builder.py tests/unit/pipeline/test_descriptor_generation_workflow.py tests/smoke/test_cli_run_descriptor_generation.py tests/smoke/test_phase_c_descriptor_matrix.py
git commit -m "feat: add spec 12 descriptor mapping foundation"
```
