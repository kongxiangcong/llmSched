# External Integrations

**Analysis Date:** 2026-04-21

## APIs & External Services

**None.** This is a fully offline, local CLI tool. No network calls, no external APIs, no cloud services.

## Data Storage

**Databases:**
- None. No SQL or NoSQL databases are used.

**File Storage:**
- Local filesystem only. All artifacts are JSON, HTML, CSS, JS, or CSV files written to run directories.

**Caching:**
- None. No Redis, memcached, or disk-cache libraries detected.

## Authentication & Identity

**Auth Provider:**
- None. No authentication, authorization, or identity management.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Rollbar, or similar services.

**Logs:**
- No logging framework detected (no `logging` module usage).
- CLI uses `typer.echo` for user-facing output.
- No log files are produced; diagnostics are embedded in JSON run summaries.

## CI/CD & Deployment

**Hosting:**
- Not applicable. This is a local CLI tool, not a deployed service.

**CI Pipeline:**
- None detected. No GitHub Actions, GitLab CI, or similar configuration files present.

## Environment Configuration

**Required env vars:**
- None. The tool does not rely on environment variables for configuration.

**Secrets location:**
- None. No secrets, API keys, or credentials are used.

## Webhooks & Callbacks

**Incoming:**
- None. No HTTP server or webhook endpoints.

**Outgoing:**
- None. No outbound webhooks or callbacks.

## Notable External Inputs

**ONNX Models:**
- The tool consumes ONNX model files (e.g., `inputs/gemma3_1b/model_q4f16.onnx`) as its primary input.
- These are local files, not fetched from a remote service.

**JSON Profiles:**
- `profiles/targets/*.json` - Hardware target configuration (e.g., `riscv_npu_single_core_v1.json`)
- `profiles/scenarios/*.json` - Workload scenario configuration (e.g., `prefill_seq128.json`)

## Subprocess Usage

**Source code:**
- One occurrence: `src/llm_sched/tools/end_to_end_runner.py` uses `subprocess.run` to orchestrate the full CLI pipeline end-to-end.

**Tests:**
- 36 occurrences across smoke tests in `tests/smoke/`, which invoke the CLI via `subprocess.run` for integration testing.

---

*Integration audit: 2026-04-21*
