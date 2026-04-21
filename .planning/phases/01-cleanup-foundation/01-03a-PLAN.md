---
phase: 01-cleanup-foundation
plan: 03a
type: execute
wave: 3
depends_on:
  - 01-02a
  - 01-02b
files_modified:
  - src/llm_sched/cli.py
  - src/llm_sched/config.py
  - src/llm_sched/arch.py
  - src/llm_sched/models.py
  - src/llm_sched/ir/
  - src/llm_sched/cli/
  - src/llm_sched/config/
  - src/llm_sched/arch/
  - src/llm_sched/contracts/
autonomous: true
requirements:
  - CLEAN-01
  - CLEAN-04
must_haves:
  truths:
    - "Package root has cli.py, config.py, arch.py, models.py"
    - "ir/ is retained with graph.py, nig.py, schedule.py, common.py, validators.py, io.py"
    - "Old subpackages cli/, config/, arch/, contracts/ are removed"
  artifacts:
    - path: "src/llm_sched/cli.py"
      provides: "CLI entrypoint (stub for Plan 04)"
    - path: "src/llm_sched/config.py"
      provides: "Config module with TargetProfile and ScenarioProfile"
    - path: "src/llm_sched/arch.py"
      provides: "Simplified hardware model"
    - path: "src/llm_sched/models.py"
      provides: "Flattened Pydantic schemas"
  key_links:
    - from: "config.py"
      to: "arch.py"
      via: "arch.py imports from llm_sched.config"
    - from: "models.py"
      to: "config.py"
      via: "models.py imports from llm_sched.config"
---

<objective>
Create flat domain files at package root and rename IR modules. Remove old subpackages cli/, config/, arch/, contracts/.

Purpose: Establish the v2 package layout foundation that downstream phases will build against.
Output: Flat root files (cli.py, config.py, arch.py, models.py) and renamed IR files (graph.py, schedule.py).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-cleanup-foundation/01-CONTEXT.md

## Decisions Implemented
- D-19: Restructure into flat domain packages:
  - `cli.py` (entrypoint, replaces `cli/main.py`)
  - `config.py` (minimal config, Phase 2 expands)
  - `arch.py` (simplified hardware model)
  - `models.py` (flattened Pydantic schemas)
  - `ir/` (`graph.py`, `nig.py`, `schedule.py`, `common.py`, `validators.py`, `io.py`)

## Target Structure (partial — scheduler/ and descriptor/ created in Plan 03b)
```
src/llm_sched/
  __init__.py
  cli.py
  config.py
  arch.py
  models.py
  ir/
    __init__.py
    graph.py
    nig.py
    schedule.py
    common.py
    validators.py
    io.py
```

## Old Structure to Remove
- cli/ (main.py, __init__.py)
- config/ (loader.py already deleted, scenario_profile.py, target_profile.py, __init__.py)
- arch/ (capabilities.py, constraints.py, query_api.py, __init__.py)
- contracts/ (models.py, __init__.py)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create flat domain files at package root</name>
  <files>
    src/llm_sched/cli.py
    src/llm_sched/config.py
    src/llm_sched/arch.py
    src/llm_sched/models.py
  </files>
  <read_first>
    - src/llm_sched/cli/main.py (to extract minimal CLI skeleton)
    - src/llm_sched/config/scenario_profile.py
    - src/llm_sched/config/target_profile.py
    - src/llm_sched/arch/capabilities.py
    - src/llm_sched/arch/constraints.py
    - src/llm_sched/arch/query_api.py
    - src/llm_sched/contracts/models.py (created in Plan 02b)
  </read_first>
  <action>
    Create four new flat files at the package root by moving content from old subpackages. Use `git mv` where possible to preserve history.

    1. **src/llm_sched/config.py** — Move content from config/scenario_profile.py and config/target_profile.py:
       - `git mv src/llm_sched/config/scenario_profile.py src/llm_sched/config.py` is NOT correct because we need both files merged.
       - Instead: read both files, write their combined content to `src/llm_sched/config.py`, then delete the old files.
       - The file should contain all classes from target_profile.py (SharedDMAConfig, VMEMConfig, QuantizationConfig, SyncConfig, VPUConfig, MXUConfig, WDQConfig, KVCacheConfig, CoreLinkConfig, DescriptorEncodingConfig, TargetProfile) and scenario_profile.py (LayerScope, ReportingConfig, ScenarioProfile).
       - Add a module docstring: `"""Configuration schemas for target and scenario profiles."""`

    2. **src/llm_sched/arch.py** — Move content from arch/capabilities.py, arch/constraints.py, arch/query_api.py:
       - Concatenate the three files into one, preserving all class and function definitions.
       - Update internal imports: `from llm_sched.config.target_profile import ...` becomes `from llm_sched.config import ...`.
       - Add module docstring: `"""Simplified hardware capability and constraint model."""`

    3. **src/llm_sched/models.py** — Move content from contracts/models.py:
       - `git mv src/llm_sched/contracts/models.py src/llm_sched/models.py`
       - Update internal imports: `from llm_sched.config.target_profile import ...` becomes `from llm_sched.config import ...`.
       - Add module docstring: `"""Flattened Pydantic schemas for internal state tracking."""`

    4. **src/llm_sched/cli.py** — Create a minimal stub (full implementation in Plan 04):
       ```python
       """CLI entrypoint for llm_sched."""

       import typer

       app = typer.Typer(add_completion=False, help="llmSched v2 — v0.10 descriptor compiler.")

       def run() -> None:
           """Run the CLI application."""
           app()
       ```

    After creating the four files, delete the old subpackage directories:
    - `git rm -r src/llm_sched/config/`
    - `git rm -r src/llm_sched/arch/`
    - `git rm -r src/llm_sched/contracts/`
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/config.py && echo "OK config.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/arch.py && echo "OK arch.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/models.py && echo "OK models.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/cli.py && echo "OK cli.py exists" || (echo "FAIL" && exit 1)
      test -d src/llm_sched/config && echo "FAIL config dir still exists" && exit 1 || echo "OK config dir removed"
      test -d src/llm_sched/arch && echo "FAIL arch dir still exists" && exit 1 || echo "OK arch dir removed"
      test -d src/llm_sched/contracts && echo "FAIL contracts dir still exists" && exit 1 || echo "OK contracts dir removed"
      python3 -c "from llm_sched.config import TargetProfile, ScenarioProfile; print('OK config imports')"
      python3 -c "from llm_sched.arch import ArchitectureCapabilities, ArchitectureQueryAPI; print('OK arch imports')"
      python3 -c "from llm_sched.models import MemoryPlanArtifact, TilingPlanArtifact; print('OK models imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - config.py, arch.py, models.py, cli.py exist at src/llm_sched/
    - config/, arch/, contracts/ directories do not exist
    - `python3 -c "from llm_sched.config import TargetProfile, ScenarioProfile"` succeeds
    - `python3 -c "from llm_sched.arch import ArchitectureCapabilities, ArchitectureQueryAPI"` succeeds
    - `python3 -c "from llm_sched.models import MemoryPlanArtifact, TilingPlanArtifact"` succeeds
  </acceptance_criteria>
  <done>Flat domain files created at package root; old subpackages config/, arch/, contracts/ removed.</done>
</task>

<task type="auto">
  <name>Task 2: Rename and restructure ir/ modules</name>
  <files>
    src/llm_sched/ir/graph.py
    src/llm_sched/ir/nig.py
    src/llm_sched/ir/schedule.py
    src/llm_sched/ir/common.py
    src/llm_sched/ir/validators.py
    src/llm_sched/ir/io.py
    src/llm_sched/ir/__init__.py
    src/llm_sched/ir/graph_ir.py
    src/llm_sched/ir/schedule_ir.py
  </files>
  <read_first>
    - src/llm_sched/ir/graph_ir.py
    - src/llm_sched/ir/schedule_ir.py
    - src/llm_sched/ir/nig.py
    - src/llm_sched/ir/common.py
    - src/llm_sched/ir/validators.py
    - src/llm_sched/ir/io.py
    - src/llm_sched/ir/__init__.py
  </read_first>
  <action>
    Rename ir/ files to match D-19 naming. Use `git mv` to preserve history.

    1. `git mv src/llm_sched/ir/graph_ir.py src/llm_sched/ir/graph.py`
    2. `git mv src/llm_sched/ir/schedule_ir.py src/llm_sched/ir/schedule.py`
    3. nig.py, common.py, validators.py, io.py keep their names.

    Update `src/llm_sched/ir/validators.py` to import from new paths:
    - `from llm_sched.ir.graph import GraphIR`
    - `from llm_sched.ir.nig import NIGIR`
    - `from llm_sched.ir.schedule import ScheduleIR`

    Update `src/llm_sched/ir/__init__.py` to export from new paths:
    ```python
    """IR contracts for llm_sched."""

    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.graph import GraphIR, GraphNode
    from llm_sched.ir.io import dump_ir_document, load_ir_document
    from llm_sched.ir.nig import NIGBinding, NIGIR, NIGNode, QuantBinding
    from llm_sched.ir.schedule import ScheduleBlock, ScheduleIR
    from llm_sched.ir.validators import (
        validate_graph_ir,
        validate_nig_ir,
        validate_schedule_ir,
    )

    __all__ = [
        "AuditRef",
        "GraphIR",
        "GraphNode",
        "NIGBinding",
        "NIGIR",
        "NIGNode",
        "QuantBinding",
        "ScheduleBlock",
        "ScheduleIR",
        "dump_ir_document",
        "load_ir_document",
        "validate_graph_ir",
        "validate_nig_ir",
        "validate_schedule_ir",
    ]
    ```
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/ir/graph.py && echo "OK graph.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/ir/schedule.py && echo "OK schedule.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/ir/graph_ir.py && echo "FAIL graph_ir.py still exists" && exit 1 || echo "OK graph_ir.py removed"
      test -f src/llm_sched/ir/schedule_ir.py && echo "FAIL schedule_ir.py still exists" && exit 1 || echo "OK schedule_ir.py removed"
      python3 -c "from llm_sched.ir import GraphIR, NIGIR, ScheduleIR; print('OK ir imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - ir/graph.py exists and ir/graph_ir.py does not
    - ir/schedule.py exists and ir/schedule_ir.py does not
    - ir/__init__.py exports GraphIR, GraphNode, NIGIR, NIGNode, NIGBinding, QuantBinding, ScheduleIR, ScheduleBlock, AuditRef, dump_ir_document, load_ir_document, validate_graph_ir, validate_nig_ir, validate_schedule_ir
    - `python3 -c "from llm_sched.ir import GraphIR, NIGIR, ScheduleIR"` succeeds
  </acceptance_criteria>
  <done>IR files renamed to graph.py and schedule.py; imports updated.</done>
</task>

<task type="auto">
  <name>Task 3: Commit root files and IR renames</name>
  <files>.git/</files>
  <read_first>
    - git status output from Tasks 1-2
  </read_first>
  <action>
    Stage all changes and commit:

    `git add -A && git commit -m "restructure: create flat root files and rename ir modules per D-19"`

    If pre-commit hooks fail, investigate and fix.
  </action>
  <verify>
    <automated>
      git log -1 --oneline | grep -q "restructure: create flat root files and rename ir modules per D-19"
    </automated>
  </verify>
  <acceptance_criteria>
    - `git log -1 --oneline` contains "restructure: create flat root files and rename ir modules per D-19"
    - `git status` is clean
  </acceptance_criteria>
  <done>Root flat files and IR renames committed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Working tree -> git index | Moves and edits staged before commit |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03a-01 | Denial of Service | Import breakage | mitigate | Verify all imports with python3 -c "from X import Y" after each move. |
| T-03a-02 | Tampering | File content during move | accept | git mv preserves content; only imports are edited. |
</threat_model>

<verification>
1. Package root has: cli.py, config.py, arch.py, models.py
2. ir/ has: graph.py, nig.py, schedule.py, common.py, validators.py, io.py
3. Old directories (cli/, config/, arch/, contracts/) are absent
4. All python import smoke tests pass
</verification>

<success_criteria>
- src/llm_sched/cli.py exists
- src/llm_sched/config.py exists and exports TargetProfile, ScenarioProfile
- src/llm_sched/arch.py exists and exports ArchitectureCapabilities
- src/llm_sched/models.py exists and exports MemoryPlanArtifact, TilingPlanArtifact
- src/llm_sched/ir/ contains graph.py, nig.py, schedule.py, common.py, validators.py, io.py
- Old subpackages cli/, config/, arch/, contracts/ are removed
- All import smoke tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-cleanup-foundation/01-03a-SUMMARY.md`
</output>
