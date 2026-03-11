# Frontend Shape Binding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bind Gemma3 ONNX symbolic input dimensions from scenario and model metadata so importer shape inference becomes scenario-aware and frontend legality can operate on more concrete shapes.

**Architecture:** Add a small frontend binding layer that converts `config.json` and `ScenarioProfile` into ONNX symbolic dimension bindings, then thread those bindings into the ONNX importer before shape inference. Keep the binding logic separate from canonicalization and lowering so later attention/KV pattern work can reuse it without rewriting the frontend pipeline.

**Tech Stack:** Python 3.14, `onnx`, `pydantic`, `pytest`.

---

### Task 1: Add Gemma model metadata and binding contract

**Files:**
- Create: `src/llm_sched/frontend/model_metadata.py`
- Create: `src/llm_sched/frontend/shape_binding.py`
- Modify: `src/llm_sched/frontend/__init__.py`
- Create: `tests/unit/frontend/test_shape_binding.py`

**Step 1: Write the failing test**

Add tests that assert:

- `GemmaModelMetadata` loads `hidden_size`, `head_dim`, `num_hidden_layers`, and `num_key_value_heads` from `config.json`,
- `build_gemma3_shape_bindings()` maps:
  - `batch_size` -> `scenario.batch`
  - `sequence_length` -> `scenario.seq_len`
  - `past_sequence_length` -> `scenario.kv_len`
- binding metadata exposes expected KV tensor shape for decode.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_shape_binding.py -v`
Expected: FAIL because binding helpers do not exist.

**Step 3: Write minimal implementation**

Implement:

- `GemmaModelMetadata`
- `load_gemma_model_metadata(path)`
- `FrontendShapeBinding`
- `build_gemma3_shape_bindings(metadata, scenario)`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_shape_binding.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/model_metadata.py src/llm_sched/frontend/shape_binding.py src/llm_sched/frontend/__init__.py tests/unit/frontend/test_shape_binding.py
git commit -m "feat: add frontend shape binding contract"
```

### Task 2: Thread shape bindings into ONNX importer

**Files:**
- Modify: `src/llm_sched/frontend/onnx_importer.py`
- Modify: `tests/unit/frontend/test_onnx_importer.py`

**Step 1: Write the failing test**

Add a symbolic-shape ONNX fixture and assert:

- without bindings, importer keeps unresolved dims as `-1`,
- with bindings, importer materializes concrete input and output shapes.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -v`
Expected: FAIL because importer ignores shape bindings.

**Step 3: Write minimal implementation**

Extend `import_onnx_to_graph_ir()` with optional `shape_bindings` and apply them to ONNX graph inputs before shape inference.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/onnx_importer.py tests/unit/frontend/test_onnx_importer.py
git commit -m "feat: add importer shape binding support"
```

### Task 3: Document scenario-aware import entrypoint

**Files:**
- Modify: `docs/development/README.md`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Step 1: Write the failing checklist**

Confirm docs do not fully describe:

- `build_gemma3_shape_bindings`,
- importer `shape_bindings` usage,
- current limitation that decode still leaves many unsupported attention/KV nodes unresolved for lowering.

**Step 2: Verify the checklist fails**

Re-open docs and confirm one or more checklist items are absent.

**Step 3: Write minimal implementation**

Document the new binding entrypoint and the current boundary between shape binding and future attention/KV pattern work.

**Step 4: Verify the checklist passes**

Re-open docs and confirm all checklist items are present.

**Step 5: Commit**

```bash
git add docs/development/README.md docs/development/phase-a-foundation-handoff.md
git commit -m "docs: describe scenario-aware frontend import"
```
