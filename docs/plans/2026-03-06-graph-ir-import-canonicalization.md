# Graph IR Import and Canonicalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first frontend slice that imports ONNX into Graph IR and runs canonicalization passes that normalize equivalent framework patterns into stable Graph IR nodes.

**Architecture:** Add a small `frontend` package with an ONNX importer and a canonicalization module. The importer will translate ONNX graph inputs, initializers, and nodes into the existing `GraphIR` schema; the canonicalizer will run purely on `GraphIR`, starting with identity elimination and `MatMul + Add -> Linear` normalization.

**Tech Stack:** Python 3.14, `onnx`, `pydantic`, `pytest`.

---

### Task 1: Frontend Package Skeleton

**Files:**
- Create: `src/llm_sched/frontend/__init__.py`
- Create: `tests/unit/frontend/test_frontend_package.py`

**Step 1: Write the failing test**

```python
from llm_sched.frontend import import_onnx_to_graph_ir, canonicalize_graph_ir
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_frontend_package.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing exports

**Step 3: Write minimal implementation**

Create the package and export placeholder callables.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_frontend_package.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/__init__.py tests/unit/frontend/test_frontend_package.py
git commit -m "feat: add frontend package skeleton"
```

### Task 2: ONNX Importer to Graph IR

**Files:**
- Create: `src/llm_sched/frontend/onnx_importer.py`
- Create: `tests/unit/frontend/test_onnx_importer.py`

**Step 1: Write the failing test**

Create a tiny ONNX graph with one input, one initializer, one `MatMul`, and assert:

- graph inputs become explicit `Input` nodes
- initializers become explicit `Constant` nodes
- ONNX nodes become Graph IR nodes with `op_kind`, `inputs`, `outputs`, `source_ref`

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -v`
Expected: FAIL because importer does not exist or does not emit expected Graph IR

**Step 3: Write minimal implementation**

Implement `import_onnx_to_graph_ir(model_path_or_proto)` using ONNX graph traversal and helper functions to extract dtype, shape, attributes, and source references.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_onnx_importer.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/onnx_importer.py tests/unit/frontend/test_onnx_importer.py
git commit -m "feat: add onnx importer for graph ir"
```

### Task 3: Graph IR Canonicalization

**Files:**
- Create: `src/llm_sched/frontend/canonicalize.py`
- Create: `tests/unit/frontend/test_canonicalize.py`

**Step 1: Write the failing test**

Create Graph IR fixtures for:

- `Identity -> MatMul` and assert `Identity` is removed
- `MatMul -> Add` with constant bias and assert it becomes one `Linear` node

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: FAIL because canonicalizer does not exist or does not rewrite nodes

**Step 3: Write minimal implementation**

Implement pure Graph IR canonicalization passes:

- remove no-op `Identity`
- fuse `MatMul + Add` into `Linear`
- preserve `source_ref`/`audit_ref`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/frontend/test_canonicalize.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/llm_sched/frontend/canonicalize.py tests/unit/frontend/test_canonicalize.py
git commit -m "feat: add graph ir canonicalization"
```

### Task 4: Frontend Handoff Notes

**Files:**
- Modify: `docs/development/phase-a-foundation-handoff.md`
- Modify: `docs/development/README.md`

**Step 1: Write the failing test**

No code test. Create a checklist:

- importer entrypoint documented
- canonicalization rules documented
- explicit non-goals documented

**Step 2: Verify the checklist fails**

Check the docs manually and confirm those items are absent or incomplete.

**Step 3: Write minimal implementation**

Update handoff docs with the new frontend entrypoints and current canonicalization scope.

**Step 4: Verify the checklist passes**

Re-open the docs and confirm all three items are present.

**Step 5: Commit**

```bash
git add docs/development/phase-a-foundation-handoff.md docs/development/README.md
git commit -m "docs: document graph ir frontend entrypoints"
```
