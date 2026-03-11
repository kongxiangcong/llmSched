# SPEC-09 Tile Candidate Planner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first stable `SPEC-09` tile candidate planner that consumes bound-NIG plus `MemoryPlanArtifact` and emits evaluable `TilingPlan` candidates for GEMM and attention workloads.

**Architecture:** Add a new tiling contract layer that records candidate tiles, VMEM usage, DMA bytes, and quant-alignment explanations. Implement a minimal tile planner that focuses on `M_tile` search under the existing `N_tile=128` / `K_tile=128` architecture constraints and reuses `SPEC-08` memory-plan diagnostics instead of recomputing VMEM regions from scratch. Wire the planner into a dedicated run-root workflow so Phase C can treat tile planning as a standalone artifact producer.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, Typer CLI, existing run-root artifact contracts.

---

### Task 1: Add `TilingPlan` Contract

**Files:**
- Create: `src/llm_sched/contracts/tiling_plan.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Test: `tests/unit/contracts/test_tiling_plan_contract.py`

**Step 1: Write the failing test**

```python
from llm_sched.contracts.tiling_plan import TileCandidate, TilingPlanArtifact


def test_tiling_plan_contract_round_trips_candidate_metadata() -> None:
    artifact = TilingPlanArtifact(
        graph_id="graph.demo",
        scenario_name="prefill_seq128",
        core_mode="single-core",
        candidates=[
            TileCandidate(
                candidate_id="node.linear.m64",
                node_id="nig.node.linear",
                macro_op="GEMM",
                strategy="prefill-balanced",
                m_tile=64,
                n_tile=128,
                k_tile=128,
                read_bytes=4096,
                write_bytes=2048,
                total_vmem_bytes=8192,
                quant_alignment_ok=True,
                quant_alignment_message="group_size=128 aligns with k_tile=128",
                source_memory_plan_region_pressure={"ping": 4096, "pong": 2048},
            )
        ],
    )

    assert artifact.candidates[0].m_tile == 64
    assert artifact.candidates[0].quant_alignment_ok is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/contracts/test_tiling_plan_contract.py -v`
Expected: FAIL with import or model-not-found error for `tiling_plan`.

**Step 3: Write minimal implementation**

Add Pydantic models for:
- `TileCandidate`
- `TileCandidateIssue`
- `TileCandidateResourceSummary`
- `TilingPlanArtifact`

Keep fields minimal but sufficient for `SPEC-09` acceptance:
- tile shape
- strategy
- VMEM bytes
- DMA bytes
- quant alignment explanation
- memory-plan pressure snapshot

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/contracts/test_tiling_plan_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/contracts/tiling_plan.py src/llm_sched/contracts/__init__.py tests/unit/contracts/test_tiling_plan_contract.py
git commit -m "feat: add tiling plan contract"
```

### Task 2: Add Minimal Tile Planner Foundation

**Files:**
- Create: `src/llm_sched/planning/tile_planner.py`
- Modify: `src/llm_sched/planning/__init__.py`
- Test: `tests/unit/planning/test_tile_planner.py`

**Step 1: Write the failing test**

```python
def test_plan_tiling_prefill_emits_multiple_m_tile_candidates_for_gemm() -> None:
    artifact = plan_tiling_artifact(bound_nig_ir, memory_plan, target_profile, scenario_prefill)

    candidates = [candidate for candidate in artifact.candidates if candidate.node_id == "nig.node.linear"]

    assert [candidate.m_tile for candidate in candidates] == [64, 32, 16]
```

Add a second test for decode:

```python
def test_plan_tiling_decode_defaults_to_m_tile_1_for_sdpa_decode() -> None:
    artifact = plan_tiling_artifact(bound_nig_ir, memory_plan, target_profile, scenario_decode)

    candidate = next(candidate for candidate in artifact.candidates if candidate.node_id == "nig.node.attn")

    assert candidate.m_tile == 1
    assert candidate.strategy == "decode-latency-first"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/planning/test_tile_planner.py -v`
Expected: FAIL because `plan_tiling_artifact` does not exist.

**Step 3: Write minimal implementation**

Implement:
- `plan_tiling_artifact(bound_nig_ir, memory_plan, hardware, scenario)`
- support first-pass macros:
  - `GEMM`
  - `WDQ_GEMM`
  - `RMSNORM_GEMM`
  - `SDPA`
  - `SDPA_DECODE`
- candidate policy:
  - prefill GEMM-like nodes: emit descending `M_tile` set capped by memory-plan fit and scenario sequence length
  - decode attention path: emit `M_tile=1`
  - respect `K_tile=128`
  - explain quant alignment against bound group size

Do not add scheduling or cross-core decisions.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/planning/test_tile_planner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/planning/tile_planner.py src/llm_sched/planning/__init__.py tests/unit/planning/test_tile_planner.py
git commit -m "feat: add tile planner foundation"
```

### Task 3: Add Tile Planning Run-Root Workflow

**Files:**
- Create: `src/llm_sched/pipeline/tile_planning.py`
- Modify: `src/llm_sched/pipeline/__init__.py`
- Test: `tests/unit/pipeline/test_tile_planning_workflow.py`

**Step 1: Write the failing test**

```python
def test_run_tile_planning_writes_tiling_plan_artifact(run_root: Path) -> None:
    result = run_tile_planning(run_root)

    assert result.status == "completed"
    assert (run_root / "artifacts" / "tiling_plan.json").is_file()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/pipeline/test_tile_planning_workflow.py -v`
Expected: FAIL because the workflow module does not exist.

**Step 3: Write minimal implementation**

Workflow responsibilities:
- load `manifest.json`
- load `bound_nig_ir.json`
- load `memory_plan.json`
- load target/scenario profiles
- call `plan_tiling_artifact(...)`
- write `artifacts/tiling_plan.json`
- update `manifest.artifact_index["tiling_plan"]`
- update `run-summary.json`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/pipeline/test_tile_planning_workflow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/pipeline/tile_planning.py src/llm_sched/pipeline/__init__.py tests/unit/pipeline/test_tile_planning_workflow.py
git commit -m "feat: add tile planning workflow"
```

### Task 4: Add CLI Entry and Smoke Gate

**Files:**
- Modify: `src/llm_sched/cli/main.py`
- Test: `tests/smoke/test_cli_run_tile_planning.py`
- Test: `tests/smoke/test_phase_c_tile_planner_matrix.py`

**Step 1: Write the failing test**

```python
def test_cli_run_tile_planning_updates_artifacts(tmp_path: Path) -> None:
    result = run_cli("run-tile-planning", "--run-root", str(run_root), cwd=repo_root)
    assert result.returncode == 0
```

Add matrix expectation:
- prefill quadrants emit non-empty GEMM candidates
- decode quadrants emit `SDPA_DECODE` candidates with `m_tile=1`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_run_tile_planning.py tests/smoke/test_phase_c_tile_planner_matrix.py -v`
Expected: FAIL because CLI command is missing.

**Step 3: Write minimal implementation**

Add `run-tile-planning` to the CLI and route to the new pipeline workflow.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_run_tile_planning.py tests/smoke/test_phase_c_tile_planner_matrix.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/cli/main.py tests/smoke/test_cli_run_tile_planning.py tests/smoke/test_phase_c_tile_planner_matrix.py
git commit -m "feat: add tile planning cli and smoke gate"
```

### Task 5: Update Phase C Docs and Handoff

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/phase-c-memory-planner-handoff.md`
- Create: `docs/development/phase-c-tile-planner-handoff.md`

**Step 1: Write the failing test**

Use a documentation checklist instead of code:
- `SPEC-09` status must move from `not_started` to `in_progress`
- README must mention `run-tile-planning`
- handoff must describe stable `TilingPlanArtifact` input/output

**Step 2: Run the checklist**

Run:
- `rg "run-tile-planning|SPEC-09|TilingPlanArtifact" docs/development`

Expected: Missing or stale references before the edits.

**Step 3: Write minimal implementation**

Document:
- what is stable now
- what SPEC-10/11 can assume
- current non-goals and remaining gaps

**Step 4: Run verification**

Run:
- `rg "run-tile-planning|SPEC-09|TilingPlanArtifact" docs/development`

Expected: Updated references present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/evaluation-compiler-roadmap.md docs/development/phase-c-memory-planner-handoff.md docs/development/phase-c-tile-planner-handoff.md
git commit -m "docs: update phase c tile planner status"
```

### Task 6: Final Verification Batch

**Files:**
- Verify the files changed in Tasks 1-5.

**Step 1: Run focused verification**

Run:
- `python -m pytest tests/unit/contracts/test_tiling_plan_contract.py tests/unit/planning/test_tile_planner.py tests/unit/pipeline/test_tile_planning_workflow.py tests/smoke/test_cli_run_tile_planning.py tests/smoke/test_phase_c_tile_planner_matrix.py -v`

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
git commit -m "feat: add spec 09 tile candidate planner foundation"
```

**Step 5: Prepare handoff**

Report:
- implemented tasks
- fresh verification output
- remaining SPEC-09 gaps before SPEC-10/11
