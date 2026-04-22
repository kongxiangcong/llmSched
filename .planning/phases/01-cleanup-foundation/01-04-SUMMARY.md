---
phase: 01-cleanup-foundation
plan: 04
subsystem: cli

tags: [typer, cli, pydantic, entrypoint]

# Dependency graph
requires:
  - phase: 01-03b
    provides: "Cleaned src/ structure with cli.py stub"
provides:
  - Single-command Typer CLI with compile command
  - Updated pyproject.toml entrypoint (llm_sched.cli:run)
  - Clean pytest configuration (no old markers)
affects:
  - 01-05
  - 01-06
  - 02-frontend

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-command CLI pattern: one Typer app with one command"
    - "Path validation at CLI boundary: Typer validates existence, code validates extension"
    - "Exit code constants: EXIT_OK, EXIT_VALIDATION_ERROR"

key-files:
  created: []
  modified:
    - src/llm_sched/cli.py
    - pyproject.toml

key-decisions:
  - "D-09: Single compile command with model/config/output args"
  - "D-10: Direct output to directory, no run-root infrastructure"
  - "D-11: Config validation inlined into compile, no separate validate-profile command"
  - "D-12: Single --config file (two-profile model merged)"

patterns-established:
  - "CLI boundary validation: Typer checks file existence, code checks .onnx extension"
  - "Stub commands echo status and indicate future phase wiring"
  - "Exit codes as module constants for testability"

requirements-completed: [CLEAN-01, CLEAN-04]

# Metrics
duration: 10min
completed: 2026-04-22
---

# Phase 1 Plan 04: CLI Cleanup Summary

**Single-command Typer CLI with compile command, updated pyproject.toml entrypoint, and clean pytest config**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-22T08:12:00Z
- **Completed:** 2026-04-22T08:22:02Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Replaced stub cli.py with full single-command `compile` implementation
- `compile` validates model path ends in .onnx, config exists, creates output directory
- Updated pyproject.toml entrypoint from `llm_sched.cli.main:run` to `llm_sched.cli:run`
- Updated project description to "v0.10 descriptor compiler for ONNX LLM models"
- Removed old pytest markers (local_smoke, milestone_matrix)
- Verified `llm-sched --help` shows only the compile command

## Task Commits

All tasks committed in a single commit (plan tasks were sequential file edits):

1. **Task 1-3: Implement single-command CLI and update pyproject.toml** - `0277d0f` (cli)

## Files Created/Modified
- `src/llm_sched/cli.py` - Single `compile` command with model/config/output validation
- `pyproject.toml` - Updated entrypoint, description, and pytest config

## Decisions Made
- Followed plan exactly: D-09 (single compile command), D-10 (direct output), D-11 (inline validation), D-12 (single config file)
- No deviations from specified implementation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Package not installed in development mode initially; `pip install -e .` resolved import checks
- Old `llm-sched` console script cached old entrypoint; reinstall after pyproject.toml change resolved it

## Known Stubs

| File | Line | Description | Resolution |
|------|------|-------------|------------|
| `src/llm_sched/cli.py` | 108-109 | Compile command body only validates inputs and echoes stub message | Phase 2 will wire actual frontend logic |

## Threat Flags

None - no new security-relevant surface beyond the planned CLI path validation.

## Next Phase Readiness
- CLI surface is stable and ready for Phase 2 frontend wiring
- `compile` command signature will not change; Phase 2 injects logic between validation and stub echo
- No blockers

---
*Phase: 01-cleanup-foundation*
*Completed: 2026-04-22*
