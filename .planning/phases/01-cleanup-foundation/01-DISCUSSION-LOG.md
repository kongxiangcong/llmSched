# Phase 1: Cleanup & Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 01-cleanup-foundation
**Areas discussed:** Deletion granularity and staging, CLI shape after cleanup, Contracts and IR retention, Test handling during cleanup, Package structure reorganization, Dependency pruning, README content

---

## Deletion granularity and staging

| Option | Description | Selected |
|--------|-------------|----------|
| Whole directories where possible | `analysis/` and old docs get wholesale `git rm`. Selective pruning only for `contracts/`, `pipeline/`, `ir/`, `frontend/`. | ✓ |
| File-by-file audit everywhere | Review every file individually before deletion. More thorough but significantly slower for ~60+ files. | |

**User's choice:** Whole directories where possible
**Notes:** Faster, less error-prone. Analysis/ is a clean wholesale delete.

---

## Commit strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One big cleanup commit | Single `git rm` commit for everything. Fast. | ✓ |
| Staged by subsystem | Separate commits: analysis/, contracts/, pipeline/, CLI/, docs/. Cleaner history. | |

**User's choice:** One big cleanup commit
**Notes:** Single commit message: `cleanup: remove v0.9-era analysis, diagnosis, visualization, evaluation`

---

## Old descriptor generation module

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Phase 4 creates a new descriptor_generation.py from scratch. | ✓ |
| Keep a minimal skeleton | Preserve the module file with only imports and a stub function signature. | |

**User's choice:** Delete entirely

---

## Old docs directories

| Option | Description | Selected |
|--------|-------------|----------|
| Delete them | `git rm` the directories. Git history preserves them if ever needed. | ✓ |
| Archive to a separate branch | Create a `legacy/v0.9-archive` branch, then delete from main. | |

**User's choice:** Delete them
**Notes:** docs/development/ and docs/architecture-diagnosis/ both deleted.

---

## Single-core scheduling module

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | Dual-core only. Single-core scheduling is out of scope. | ✓ |
| Keep it | Might serve as reference for dual-core scheduler rewrite in Phase 3. | |

**User's choice:** Delete it

---

## Performance estimation module

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Phase 6 creates structural metrics, not cycle-level estimation. | ✓ |
| Keep a skeleton | Preserve the module file as a placeholder for Phase 6. | |

**User's choice:** Delete entirely

---

## Old execution plans

| Option | Description | Selected |
|--------|-------------|----------|
| Delete them | Historical execution slices from v0.9 work. Not relevant to v2. | ✓ |
| Keep them | May contain spec definitions useful for reference during v2. | |

**User's choice:** Delete them
**Notes:** docs/plans/ directory deleted.

---

## End-to-end script

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Phase 6 or later creates a new script when v2 pipeline is complete. | ✓ |
| Rewrite into minimal v2 script | Strip to ONNX → descriptor set only. | |

**User's choice:** Delete entirely

---

## CLI shape after cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| Single compile command | `llmsched compile model.onnx --config config.yaml --output ./out/` | ✓ |
| Hybrid: compile + debug steps | Single compile plus individual frontend/schedule/pack commands. | |
| Keep step-by-step model | Retain existing `init-run` + `run-*` commands. | |

**User's choice:** Single compile command

---

## Run-root infrastructure

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with direct output | `--output ./out/` writes descriptors + metrics directly. | ✓ |
| Keep run-root model | `init-run` creates structured workspace, compile populates it. | |

**User's choice:** Replace with direct output

---

## validate-profile command

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it | `compile` validates inline. | ✓ |
| Keep standalone | Useful for CI pipelines and pre-flight checks. | |

**User's choice:** Drop it

---

## Profile files

| Option | Description | Selected |
|--------|-------------|----------|
| Merge into single config | One YAML file with hardware + model config sections. | ✓ |
| Keep two profiles | Separation of hardware vs model concerns. | |

**User's choice:** Merge into single config

---

## Contracts and IR retention

### Manifest/artifact_layout/run_summary

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | v2 uses direct output. | |
| Keep them internally | Still needed for internal artifact tracking during compilation. | ✓ |
| Keep and simplify | Strip to minimal fields for compile command's internal state. | |

**User's choice:** Keep them internally

### Descriptor IR

| Option | Description | Selected |
|--------|-------------|----------|
| Delete entirely | Phase 4 creates v0.10 from scratch. | ✓ |
| Keep and mutate | File stays, contents rewritten in Phase 4. | |

**User's choice:** Delete entirely

### Config loader

| Option | Description | Selected |
|--------|-------------|----------|
| Delete | Phase 2 creates new single-config loader. | ✓ |
| Keep and adapt | Update loader to handle merged config. | |

**User's choice:** Delete

### Arch module

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as-is | Hardware modeling still needed. | |
| Keep and simplify | Strip single-core paths, reshape for dual-core-only. | ✓ |
| Delete | Phase 3 creates new hardware model. | |

**User's choice:** Keep and simplify

---

## Package structure reorganization

| Option | Description | Selected |
|--------|-------------|----------|
| Flat domain packages | `cli.py`, `config.py`, `arch.py`, `models.py`, `ir/`, `frontend/`, `scheduler/`, `descriptor/` | ✓ |
| Layered architecture | `models/`, `compiler/` layers. | |
| Minimal restructure | Merge pipeline/ into planning/, delete analysis/. | |

**User's choice:** Flat domain packages

---

## analysis_ir.py

| Option | Description | Selected |
|--------|-------------|----------|
| Delete it | Part of old report/diagnosis layer. | ✓ |
| Keep it | Might contain useful IR patterns. | |

**User's choice:** Delete it

---

## Contracts flattening

| Option | Description | Selected |
|--------|-------------|----------|
| Flatten to models.py | Single module with all Pydantic schemas. | ✓ |
| Keep individual files | Each model in its own file. | |

**User's choice:** Flatten to models.py

---

## Test handling

### Old tests

| Option | Description | Selected |
|--------|-------------|----------|
| Delete all old tests now | Clean slate. New tests written per phase. | ✓ |
| Selectively prune | Delete test files as their source modules are removed. | |
| Mark as skipped | Use `@pytest.mark.skip` to preserve file structure. | |

**User's choice:** Delete all old tests now

### Test infrastructure

| Option | Description | Selected |
|--------|-------------|----------|
| Keep infrastructure | `conftest.py` and `fixtures/` stay. | ✓ |
| Delete and recreate | Start fresh. | |

**User's choice:** Keep infrastructure

### Cleanup verification test

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add test | Minimal test asserting old modules are removed. | ✓ |
| No — git history enough | No test needed. | |

**User's choice:** Yes — add test

### Tests for staying modules

| Option | Description | Selected |
|--------|-------------|----------|
| Delete them too | All old tests go. | ✓ |
| Keep until rewritten | Tests stay until their module is replaced. | |
| Delete and add placeholders | Minimal `test_module_exists()` placeholders. | |

**User's choice:** Delete them too

---

## Dependency pruning

### pyproject.toml changes

| Option | Description | Selected |
|--------|-------------|----------|
| Bump Python and keep deps | Match PROJECT.md 3.12+ constraint. | |
| Add numpy | Add numpy for tensor handling. | ✓ |
| Keep as-is | No changes needed. | |

**User's choice:** Add numpy

### Python version

| Option | Description | Selected |
|--------|-------------|----------|
| Bump to >=3.12 | Match PROJECT.md constraint. | |
| Keep >=3.11 | Wider compatibility. | ✓ |

**User's choice:** Keep >=3.11

---

## README content

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal placeholder | Short paragraph + refactoring notice. | |
| Keep structure, update | Replace v0.9 content but keep existing sections. | |
| Full rewrite with v2 scope | Complete rewrite describing v2 pipeline and roadmap. | ✓ |

**User's choice:** Full rewrite with v2 scope

---

## Claude's Discretion

- Exact module names within the new domain packages
- Exact fields preserved in the flattened `models.py`
- Specific content of the cleanup verification test
- Exact simplification applied to `arch.py`

---

## Deferred Ideas

- End-to-end script — Phase 6 or later
- Single-config loader — Phase 2
- v0.10 DescriptorIR — Phase 4
- Structural metrics module — Phase 6
- New smoke tests — written per-phase as modules land
