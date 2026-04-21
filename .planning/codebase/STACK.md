# Technology Stack

**Analysis Date:** 2026-04-21

## Languages

**Primary:**
- Python 3.12+ - All source code, tests, and tooling

**Secondary:**
- JavaScript (inline in Python strings) - Generated visualization workbench assets
- HTML/CSS (inline in Python strings) - Generated static workbench and catalog pages
- JSON - Configuration profiles, artifacts, reports, and IR serialization
- CSV - Diagnosis dataset layer output

## Runtime

**Environment:**
- CPython >=3.11 (tested on 3.12.3)

**Package Manager:**
- uv (lockfile: `uv.lock` present)
- setuptools build backend (`pyproject.toml`)

## Frameworks

**Core:**
- Pydantic v2 (>=2.12,<3) - Schema validation for all contracts, IR, and config models
- Typer (>=0.24,<0.25) - CLI framework with typed arguments
- ONNX (>=1.20,<2) - Model import and shape inference

**Testing:**
- pytest (>=9,<10) - Test runner with custom markers

**Build/Dev:**
- setuptools (>=68) - Build backend
- wheel - Build artifact

## Key Dependencies

**Critical:**
- `pydantic` - 2,400+ usages of BaseModel, ConfigDict, Field, model_validator across the codebase. Drives all data contracts.
- `typer` - CLI entrypoint in `src/llm_sched/cli/main.py`. All commands use `typer.Option`, `typer.Exit`, `typer.echo`.
- `onnx` - Frontend model import. Used in `src/llm_sched/frontend/onnx_importer.py` for `onnx.load`, `onnx.shape_inference.infer_shapes`, and protobuf node traversal.

**Infrastructure:**
- Standard library only beyond the three packages above
- `pathlib.Path` (129 occurrences) for all file I/O
- `json` (62 dumps/loads occurrences) for artifact serialization
- `csv` (one module: `diagnosis_dataset_writer.py`) for diagnosis dataset export

## Configuration

**Environment:**
- No `.env` file or environment-variable-driven configuration detected
- Configuration is file-based via JSON profiles

**Build:**
- `pyproject.toml` - Project metadata, dependencies, build system, pytest config
- `uv.lock` - Locked dependency resolution

**Project Scripts:**
- `llm-sched = "llm_sched.cli.main:run"` - CLI entrypoint

## Platform Requirements

**Development:**
- Python 3.11+
- uv (recommended) or pip for package management

**Production:**
- Local CLI tool; no server or network requirements
- Generates static HTML/JSON artifacts to local filesystem

---

*Stack analysis: 2026-04-21*
