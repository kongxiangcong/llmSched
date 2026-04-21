# llmSched v2 — Project Guide

## Project

llmSched v2 is a compiler that transforms ONNX LLM models into verified v0.10 descriptor sets for the `tars-npu-ctrl` NPU controller.

## Core Value

Given an ONNX model, produce a correct, verifiable v0.10 descriptor set that the NPU controller can parse and execute. Round-trip verification must pass for every descriptor.

## Current Focus

Phase 1 of 6: Cleanup & Foundation — removing old v0.9-era code and docs.

## Tech Stack

- Python 3.12+
- Pydantic v2 (schema validation)
- Typer (CLI)
- ONNX (model import)
- Standard library only for bitfield/CRC work

## Key Constraints

- v0.10 descriptor format only (version 0x6). No v0.9 backward compatibility.
- ONNX remains the sole input format.
- No modeling of reshape, transpose, squeeze, unsqueeze, gather ops.
- Execution semantics only — no diagnosis, visualization, evaluation reports.
- Dual-core NPU only. Each core has independent VMEM. No single-core scenarios.

## Architecture (Target)

ONNX Frontend → Task DAG Builder → Task Scheduler → v0.10 Descriptor Engine → Structural Metrics

## Workflow

This project uses GSD (Get Shit Done) workflow:
- `.planning/PROJECT.md` — living project context
- `.planning/REQUIREMENTS.md` — scoped requirements with REQ-IDs
- `.planning/ROADMAP.md` — 6-phase execution roadmap
- `.planning/STATE.md` — current position and progress

## Next Step

Run `/gsd-discuss-phase 1` to gather context and clarify approach for Phase 1.
