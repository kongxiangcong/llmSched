# llmSched v2

> **Warning**: This project is undergoing complete refactoring. Current outputs are not correct. Do not use for production.

A compiler that transforms ONNX LLM models into verified v0.10 descriptor sets for the `tars-npu-ctrl` NPU controller.

## What This Is

Given an ONNX model, llmSched v2 produces a correct, verifiable v0.10 descriptor set that the NPU controller can parse and execute. Round-trip verification must pass for every descriptor.

The pipeline:

```
ONNX model → Task DAG → Scheduling → v0.10 Descriptor Packing → Structural Metrics
```

## Roadmap

The project is organized into 6 phases:

1. **Cleanup & Foundation** — Remove old v0.9-era code and docs, restructure packages (in progress)
2. **Task DAG Frontend** — Extract task-unit dependency DAG from ONNX models
3. **Task-Centric Scheduling** — Schedule task DAGs with memory planning and execution ordering for dual-core NPU
4. **Descriptor Packing** — Pack and parse v0.10 descriptors for all 11 families
5. **Descriptor Verification** — Harden correctness with round-trip and 4-layer verification gate
6. **Performance Metrics** — Emit structural metrics and per-layer timelines

## Tech Stack

- Python 3.11+
- Pydantic v2 (schema validation)
- Typer (CLI)
- ONNX (model import)
- NumPy (tensor manipulation)

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Compile (stub — full pipeline wires in Phase 2)
llm-sched compile model.onnx --config config.yaml --output ./out/
```

## Input Constraints

- **Input format**: ONNX only
- **Target hardware**: Dual-core NPU with independent per-core VMEM
- **Ignored ops**: reshape, transpose, squeeze, unsqueeze, gather (transparent to NPU)
- **Descriptor version**: v0.10 (0x6) only — no backward compatibility

## Development Workflow

This project uses the GSD (Get Shit Done) workflow:

- `.planning/PROJECT.md` — Living project context
- `.planning/REQUIREMENTS.md` — Scoped requirements with REQ-IDs
- `.planning/ROADMAP.md` — 6-phase execution roadmap
- `.planning/STATE.md` — Current position and progress

## License

TBD
