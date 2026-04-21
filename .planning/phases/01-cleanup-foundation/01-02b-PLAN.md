---
phase: 01-cleanup-foundation
plan: 02b
type: execute
wave: 2
depends_on:
  - 01-02a
files_modified:
  - src/llm_sched/ir/
  - src/llm_sched/contracts/
  - src/llm_sched/config/loader.py
autonomous: true
requirements:
  - CLEAN-01
  - CLEAN-04
must_haves:
  truths:
    - "ir/ no longer has descriptor_ir.py or analysis_ir.py"
    - "contracts/ is flattened to models.py with only retained schemas"
    - "config/loader.py is deleted"
    - "No retained module imports from deleted paths"
  artifacts:
    - path: "src/llm_sched/ir/__init__.py"
      provides: "Clean IR exports"
      absent_exports:
        - "DescriptorIR"
        - "AnalysisIR"
    - path: "src/llm_sched/ir/validators.py"
      provides: "Validators without deleted IR types"
      absent: "validate_descriptor_ir, validate_analysis_ir"
    - path: "src/llm_sched/contracts/models.py"
      provides: "Flattened contracts"
      contains: "class MemoryPlanArtifact"
    - path: "src/llm_sched/config/"
      provides: "Config without loader"
      absent: "loader.py"
  key_links:
    - from: "contracts/models.py"
      to: "planning/memory_planner.py"
      via: "import llm_sched.contracts.models"
      note: "Will be updated in Plan 03 restructure"
---

<objective>
Delete IR modules, flatten contracts to models.py, and remove config loader. Verify no retained modules reference deleted paths.

Purpose: Complete selective cleanup of ir/, contracts/, and config/ after pipeline/planning deletions are committed.
Output: Clean ir/, flattened contracts/, and config/ without loader.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-cleanup-foundation/01-CONTEXT.md
@.planning/PROJECT.md

## Decisions Implemented
- D-14: ir/descriptor_ir.py deleted
- D-15: config/loader.py deleted
- D-17: ir/analysis_ir.py deleted
- D-18: Remaining contracts flattened into models.py

## Modules to DELETE in ir/
- descriptor_ir.py (D-14)
- analysis_ir.py (D-17)

## Modules to KEEP in ir/
- graph_ir.py
- nig.py
- schedule_ir.py
- common.py
- validators.py (rewritten)
- io.py
- __init__.py (rewritten)

## Contracts flattening (D-18)
KEEP and move into models.py:
- manifest.py (RunManifest)
- artifact_layout.py (ArtifactLayout, build_run_layout)
- run_summary.py (RunSummary)
- memory_plan.py (MemoryPlanArtifact, PlannedAllocation, etc.)
- tiling_plan.py (TilingPlanArtifact, TileCandidate, etc.)

DELETE all other contracts/*.py files.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Delete ir/descriptor_ir.py and ir/analysis_ir.py, rewrite ir/__init__.py and ir/validators.py</name>
  <files>
    src/llm_sched/ir/descriptor_ir.py
    src/llm_sched/ir/analysis_ir.py
    src/llm_sched/ir/__init__.py
    src/llm_sched/ir/validators.py
  </files>
  <read_first>
    - src/llm_sched/ir/__init__.py (current content, empty)
    - src/llm_sched/ir/validators.py (current content, imports analysis_ir and descriptor_ir)
    - src/llm_sched/ir/graph_ir.py (confirm it stays)
    - src/llm_sched/ir/nig.py (confirm it stays)
    - src/llm_sched/ir/schedule_ir.py (confirm it stays)
    - src/llm_sched/ir/common.py (confirm it stays)
    - src/llm_sched/ir/io.py (confirm it stays)
  </read_first>
  <action>
    1. Delete the two IR modules:
       - `git rm src/llm_sched/ir/descriptor_ir.py`
       - `git rm src/llm_sched/ir/analysis_ir.py`

    2. Rewrite `src/llm_sched/ir/validators.py` to remove descriptor_ir and analysis_ir validators:

    ```python
    """IR validation entrypoints."""

    from llm_sched.ir.graph_ir import GraphIR
    from llm_sched.ir.nig import NIGIR
    from llm_sched.ir.schedule_ir import ScheduleIR


    def validate_graph_ir(payload: dict) -> GraphIR:
        return GraphIR.model_validate(payload)


    def validate_nig_ir(payload: dict) -> NIGIR:
        return NIGIR.model_validate(payload)


    def validate_schedule_ir(payload: dict) -> ScheduleIR:
        return ScheduleIR.model_validate(payload)
    ```

    3. Rewrite `src/llm_sched/ir/__init__.py` to export retained IR types:

    ```python
    """IR contracts for llm_sched."""

    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.graph_ir import GraphIR, GraphNode
    from llm_sched.ir.io import dump_ir_document, load_ir_document
    from llm_sched.ir.nig import NIGBinding, NIGIR, NIGNode, QuantBinding
    from llm_sched.ir.schedule_ir import ScheduleBlock, ScheduleIR
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
      test -f src/llm_sched/ir/descriptor_ir.py && echo "FAIL" && exit 1 || echo "OK descriptor_ir deleted"
      test -f src/llm_sched/ir/analysis_ir.py && echo "FAIL" && exit 1 || echo "OK analysis_ir deleted"
      grep -q "validate_descriptor_ir" src/llm_sched/ir/validators.py && echo "FAIL" && exit 1 || echo "OK validators clean"
      grep -q "validate_analysis_ir" src/llm_sched/ir/validators.py && echo "FAIL" && exit 1 || echo "OK validators clean"
      grep -q "DescriptorIR" src/llm_sched/ir/__init__.py && echo "FAIL" && exit 1 || echo "OK init clean"
      grep -q "AnalysisIR" src/llm_sched/ir/__init__.py && echo "FAIL" && exit 1 || echo "OK init clean"
      grep -q "GraphIR" src/llm_sched/ir/__init__.py && echo "OK init has GraphIR" || (echo "FAIL" && exit 1)
    </automated>
  </verify>
  <acceptance_criteria>
    - descriptor_ir.py and analysis_ir.py do not exist
    - validators.py has no references to DescriptorIR, AnalysisIR, validate_descriptor_ir, validate_analysis_ir
    - ir/__init__.py exports GraphIR, GraphNode, NIGIR, NIGNode, NIGBinding, QuantBinding, ScheduleIR, ScheduleBlock, AuditRef, dump_ir_document, load_ir_document, validate_graph_ir, validate_nig_ir, validate_schedule_ir
  </acceptance_criteria>
  <done>IR directory contains only retained schemas with clean validators and exports.</done>
</task>

<task type="auto">
  <name>Task 2: Flatten contracts to models.py and delete old contract files</name>
  <files>
    src/llm_sched/contracts/manifest.py
    src/llm_sched/contracts/artifact_layout.py
    src/llm_sched/contracts/run_summary.py
    src/llm_sched/contracts/memory_plan.py
    src/llm_sched/contracts/tiling_plan.py
    src/llm_sched/contracts/models.py
    src/llm_sched/contracts/__init__.py
  </files>
  <read_first>
    - src/llm_sched/contracts/manifest.py (RunManifest — keep)
    - src/llm_sched/contracts/artifact_layout.py (ArtifactLayout, build_run_layout — keep)
    - src/llm_sched/contracts/run_summary.py (RunSummary — keep)
    - src/llm_sched/contracts/memory_plan.py (MemoryPlanArtifact, PlannedAllocation, etc. — keep)
    - src/llm_sched/contracts/tiling_plan.py (TilingPlanArtifact, TileCandidate, etc. — keep)
    - src/llm_sched/planning/memory_planner.py (to see which memory_plan symbols are imported)
    - src/llm_sched/planning/tile_planner.py (to see which tiling_plan symbols are imported)
    - src/llm_sched/planning/dual_core_scheduler.py (to see which contract symbols are imported)
    - src/llm_sched/planning/schedule_duration.py (to see which contract symbols are imported)
  </read_first>
  <action>
    1. Read the five keep contracts files and concatenate their contents into a single new file `src/llm_sched/contracts/models.py`. Preserve all class definitions, function definitions, and imports. Adjust internal imports within the file so that references to `llm_sched.contracts.X` become relative or self-contained where possible. The file should be a straightforward concatenation of the five source files with a single module docstring at the top:

    ```python
    """Flattened Pydantic models for internal state tracking.

    Merged from: manifest, artifact_layout, run_summary, memory_plan, tiling_plan.
    """
    ```

    2. After creating models.py, delete all old contracts/*.py files EXCEPT the newly created models.py:
       - `git rm src/llm_sched/contracts/manifest.py`
       - `git rm src/llm_sched/contracts/artifact_layout.py`
       - `git rm src/llm_sched/contracts/run_summary.py`
       - `git rm src/llm_sched/contracts/memory_plan.py`
       - `git rm src/llm_sched/contracts/tiling_plan.py`
       - Also delete all other contracts files that are not in the keep list:
         `for f in src/llm_sched/contracts/*.py; do basename=$(basename "$f"); if [ "$basename" != "models.py" ] && [ "$basename" != "__init__.py" ]; then git rm "$f"; fi; done`

    3. Rewrite `src/llm_sched/contracts/__init__.py` to export from models.py:

    ```python
    """Contracts for run artifacts and manifests."""

    from llm_sched.contracts.models import (
        ArtifactLayout,
        MemoryPlanArtifact,
        PlannedAllocation,
        RegionSummary,
        RunManifest,
        RunSummary,
        TileCandidate,
        TileCandidateIssue,
        TileCandidateResourceSummary,
        TilingPlanArtifact,
        VMEMFitDiagnostic,
        build_run_layout,
    )

    __all__ = [
        "ArtifactLayout",
        "MemoryPlanArtifact",
        "PlannedAllocation",
        "RegionSummary",
        "RunManifest",
        "RunSummary",
        "TileCandidate",
        "TileCandidateIssue",
        "TileCandidateResourceSummary",
        "TilingPlanArtifact",
        "VMEMFitDiagnostic",
        "build_run_layout",
    ]
    ```

    Note: The exact export list may need adjustment based on what symbols the retained planning modules actually import. The executor should verify by reading planning/*.py import statements and ensuring all imported symbols from contracts are present in __init__.py.
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/contracts/models.py && echo "OK models.py exists" || (echo "FAIL" && exit 1)
      test -f src/llm_sched/contracts/manifest.py && echo "FAIL manifest still exists" && exit 1 || echo "OK manifest deleted"
      test -f src/llm_sched/contracts/artifact_layout.py && echo "FAIL artifact_layout still exists" && exit 1 || echo "OK artifact_layout deleted"
      test -f src/llm_sched/contracts/run_summary.py && echo "FAIL run_summary still exists" && exit 1 || echo "OK run_summary deleted"
      test -f src/llm_sched/contracts/memory_plan.py && echo "FAIL memory_plan still exists" && exit 1 || echo "OK memory_plan deleted"
      test -f src/llm_sched/contracts/tiling_plan.py && echo "FAIL tiling_plan still exists" && exit 1 || echo "OK tiling_plan deleted"
      python3 -c "from llm_sched.contracts import MemoryPlanArtifact, TilingPlanArtifact, RunManifest, ArtifactLayout, RunSummary; print('OK imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - models.py exists and contains classes from all five kept contract files
    - No old contract files remain (manifest.py, artifact_layout.py, run_summary.py, memory_plan.py, tiling_plan.py, and all others except models.py and __init__.py)
    - contracts/__init__.py exports all symbols that planning/ modules import
    - `python3 -c "from llm_sched.contracts import MemoryPlanArtifact, TilingPlanArtifact, RunManifest, ArtifactLayout, RunSummary"` succeeds
  </acceptance_criteria>
  <done>Contracts flattened to models.py with clean exports; all old contract files deleted.</done>
</task>

<task type="auto">
  <name>Task 3: Delete config/loader.py</name>
  <files>
    src/llm_sched/config/loader.py
    src/llm_sched/config/__init__.py
  </files>
  <read_first>
    - src/llm_sched/config/loader.py (confirm it exists, to be deleted per D-15)
    - src/llm_sched/config/__init__.py (current content)
    - src/llm_sched/config/scenario_profile.py (confirm it stays)
    - src/llm_sched/config/target_profile.py (confirm it stays)
  </read_first>
  <action>
    1. Delete config/loader.py: `git rm src/llm_sched/config/loader.py`

    2. Rewrite `src/llm_sched/config/__init__.py` to export only the profile schemas:

    ```python
    """Configuration schemas for target and scenario profiles."""

    from llm_sched.config.scenario_profile import ScenarioProfile
    from llm_sched.config.target_profile import TargetProfile

    __all__ = [
        "ScenarioProfile",
        "TargetProfile",
    ]
    ```
  </action>
  <verify>
    <automated>
      test -f src/llm_sched/config/loader.py && echo "FAIL loader still exists" && exit 1 || echo "OK loader deleted"
      grep -q "load_target_profile" src/llm_sched/config/__init__.py && echo "FAIL init has loader refs" && exit 1 || echo "OK init clean"
      python3 -c "from llm_sched.config import TargetProfile, ScenarioProfile; print('OK imports')"
    </automated>
  </verify>
  <acceptance_criteria>
    - config/loader.py does not exist
    - config/__init__.py exports only TargetProfile and ScenarioProfile
    - `python3 -c "from llm_sched.config import TargetProfile, ScenarioProfile"` succeeds
  </acceptance_criteria>
  <done>Config loader deleted; config package exports only profile schemas.</done>
</task>

<task type="auto">
  <name>Task 4: Verify no retained modules import deleted paths, then commit</name>
  <files>
    src/llm_sched/
    .git/
  </files>
  <read_first>
    - src/llm_sched/ir/__init__.py
    - src/llm_sched/contracts/__init__.py
    - src/llm_sched/config/__init__.py
    - src/llm_sched/pipeline/__init__.py
    - src/llm_sched/planning/__init__.py
  </read_first>
  <action>
    Run grep across all retained Python files to confirm no references to deleted modules remain:

    1. `grep -r "from llm_sched.ir.descriptor_ir" src/llm_sched/ || echo "OK no descriptor_ir imports"`
    2. `grep -r "from llm_sched.ir.analysis_ir" src/llm_sched/ || echo "OK no analysis_ir imports"`
    3. `grep -r "from llm_sched.config.loader" src/llm_sched/ || echo "OK no loader imports"`
    4. `grep -r "llm_sched.contracts.manifest" src/llm_sched/ || echo "OK no manifest imports"`
    5. `grep -r "llm_sched.contracts.artifact_layout" src/llm_sched/ || echo "OK no artifact_layout imports"`
    6. `grep -r "llm_sched.contracts.run_summary" src/llm_sched/ || echo "OK no run_summary imports"`
    7. `grep -r "llm_sched.contracts.memory_plan" src/llm_sched/ || echo "OK no memory_plan imports"`
    8. `grep -r "llm_sched.contracts.tiling_plan" src/llm_sched/ || echo "OK no tiling_plan imports"`

    Any match indicates a retained module still imports a deleted path and must be fixed before commit.

    After verification passes, stage all changes and commit:

    `git add -A && git commit -m "cleanup: remove v0.9-era ir, contracts, config modules; flatten contracts to models.py"`

    If pre-commit hooks fail, investigate and fix.
  </action>
  <verify>
    <automated>
      grep -r "from llm_sched.ir.descriptor_ir" src/llm_sched/ && echo "FAIL descriptor_ir import found" && exit 1 || echo "OK no descriptor_ir imports"
      grep -r "from llm_sched.ir.analysis_ir" src/llm_sched/ && echo "FAIL analysis_ir import found" && exit 1 || echo "OK no analysis_ir imports"
      grep -r "from llm_sched.config.loader" src/llm_sched/ && echo "FAIL loader import found" && exit 1 || echo "OK no loader imports"
      grep -r "llm_sched.contracts.manifest" src/llm_sched/ && echo "FAIL manifest import found" && exit 1 || echo "OK no manifest imports"
      grep -r "llm_sched.contracts.artifact_layout" src/llm_sched/ && echo "FAIL artifact_layout import found" && exit 1 || echo "OK no artifact_layout imports"
      grep -r "llm_sched.contracts.run_summary" src/llm_sched/ && echo "FAIL run_summary import found" && exit 1 || echo "OK no run_summary imports"
      grep -r "llm_sched.contracts.memory_plan" src/llm_sched/ && echo "FAIL memory_plan import found" && exit 1 || echo "OK no memory_plan imports"
      grep -r "llm_sched.contracts.tiling_plan" src/llm_sched/ && echo "FAIL tiling_plan import found" && exit 1 || echo "OK no tiling_plan imports"
      git log -1 --oneline | grep -q "cleanup: remove v0.9-era ir, contracts, config modules; flatten contracts to models.py"
    </automated>
  </verify>
  <acceptance_criteria>
    - No retained Python file in src/llm_sched/ imports from descriptor_ir, analysis_ir, config.loader, or any old contracts submodules (manifest, artifact_layout, run_summary, memory_plan, tiling_plan)
    - `git log -1 --oneline` contains "cleanup: remove v0.9-era ir, contracts, config modules; flatten contracts to models.py"
    - `git status` is clean
  </acceptance_criteria>
  <done>No retained modules reference deleted paths; IR, contracts, and config cleanup committed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Working tree -> git index | Changes staged before commit; reversible until commit |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-01-02b | Denial of Service | Working tree | accept | Same as T-01-01; git history preserves old files. |
| T-01-02b-02 | Information Disclosure | models.py flattening | mitigate | Ensure no secrets in flattened models.py by reading source files before concatenation. |
</threat_model>

<verification>
1. ir/ has exactly 7 .py files: __init__.py, graph_ir.py, nig.py, schedule_ir.py, common.py, validators.py, io.py
2. contracts/ has exactly 2 .py files: __init__.py, models.py
3. config/ has exactly 3 .py files: __init__.py, scenario_profile.py, target_profile.py
4. All deleted files are absent and committed
5. No retained module imports from deleted paths (verified by grep in Task 4)
</verification>

<success_criteria>
- ir/ no longer has descriptor_ir.py or analysis_ir.py
- contracts/ is flattened to models.py
- config/ no longer has loader.py
- All changes committed
- No retained modules reference deleted paths
</success_criteria>

<output>
After completion, create `.planning/phases/01-cleanup-foundation/01-02b-SUMMARY.md`
</output>
