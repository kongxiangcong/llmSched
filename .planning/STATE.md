# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** Given an ONNX model, produce a correct, verifiable v0.10 descriptor set that the NPU controller can parse and execute
**Current focus:** Phase 1 — Cleanup & Foundation

## Current Position

Phase: 1 of 6 (Cleanup & Foundation)
Plan: 0 of TBD
Status: Ready to plan
Last activity: 2026-04-21 — Dual-core constraint added

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Cleanup: Old code deleted from `src/`, not just disabled. Git history may be rewritten.
- Descriptor: v0.10 only (0x6). No backward compatibility with v0.9.
- Scope: No layout-op task modeling (reshape/transpose/etc. are transparent).
- Hardware: Dual-core NPU only. Each core has independent VMEM. Single-core scenarios are not supported.

### Pending Todos

None yet.

### Blockers/Concerns

None yet.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-21
Stopped at: Roadmap created; awaiting Phase 1 planning
Resume file: None
