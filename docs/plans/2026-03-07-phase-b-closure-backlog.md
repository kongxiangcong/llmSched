# Phase B Closure Backlog

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this backlog task-by-task.

**Goal:** Close `SPEC-03` / `SPEC-04` / `SPEC-07` so Phase B can be declared complete and the project can enter Phase C on top of a stable semantic layer.

**Architecture:** Keep the existing frontend pipeline as the only model-to-workload semantic entrypoint. Do not start VMEM/KV planning, tiling, scheduler, or descriptor logic before quant/shape/layout binding is explicit in NIG and traceable in run artifacts.

**Tech Stack:** Python 3.14, Pydantic, ONNX, Typer, pytest, JSON IR artifacts, checked-in Gemma3 fixtures.

---

## Scope

Phase B 收口只处理三类事情：

- `SPEC-03`
  - 把模型导入与规范化图的 diagnostics / report / artifact 补齐。
- `SPEC-04`
  - 把工作负载拆解的 coverage / unmapped-path / pseudo-fallback 分类补齐。
- `SPEC-07`
  - 把 quant / shape / layout / memory-class 绑定做成稳定 contract，并接入 legality 与 run-root workflow。

明确不做：

- `SPEC-08` VMEM/KV 地址规划
- `SPEC-09` tiling
- `SPEC-10/11` scheduler
- `SPEC-12` descriptor / ISA mapping
- 完整 `SPEC-13` perf pipeline

## Phase B Exit Criteria

Phase B 只有在以下条件全部满足时才算完成：

- `SPEC-03 = done`
  - 导入 / canonicalization 有稳定 artifact 和诊断报告。
- `SPEC-04 = done`
  - decomposition 有稳定 coverage report，pseudo/fallback surface 和 unmapped-path 可分离统计。
- `SPEC-07 = done`
  - NIG 上的 quant / shape / layout / memory-class 绑定是显式且可校验的。
- 真实 Gemma3 在以下 4 个象限上都能稳定跑完 frontend 主线：
  - `prefill + single-core`
  - `prefill + dual-core`
  - `decode + single-core`
  - `decode + dual-core`
- `dynamic_shape_unresolved` 不再阻塞 Gemma3 主路径。
- `unsupported_quant_activation_dtype` / `unsupported_quant_group_size` 要么被消除，要么被重分类成显式 target gap，而不是前端绑定缺失。
- `no_hardware_mapping` 仅允许出现在显式 pseudo/fallback surface 上，且必须单独出现在报告中。

## Backlog Overview

| Story ID | Spec | Title | Priority | Depends On |
| --- | --- | --- | --- | --- |
| PHB-01 | SPEC-03 | Freeze frontend import/canonicalization report contract | P0 | None |
| PHB-02 | SPEC-04 | Freeze workload decomposition coverage contract | P0 | PHB-01 |
| PHB-03 | SPEC-07 | Define bound-NIG quant/shape/layout contract | P0 | PHB-02 |
| PHB-04 | SPEC-07 | Bind linear quant metadata and group semantics | P0 | PHB-03 |
| PHB-05 | SPEC-07 | Bind attention/KV shape and layout semantics | P0 | PHB-03 |
| PHB-06 | SPEC-07 | Bind memory class and target-facing layout legality | P0 | PHB-04, PHB-05 |
| PHB-07 | SPEC-07 | Emit binding diagnostics and bound-NIG reports | P1 | PHB-06 |
| PHB-08 | SPEC-03, SPEC-04, SPEC-07 | Integrate Phase B artifacts into run-root workflow | P1 | PHB-07 |
| PHB-09 | SPEC-03, SPEC-04, SPEC-07 | Add Gemma3 Phase B closure smoke matrix | P0 | PHB-08 |
| PHB-10 | SPEC-03, SPEC-04, SPEC-07 | Publish Phase B handoff and flip roadmap status | P1 | PHB-09 |

## Detailed Stories

### Story PHB-01: Freeze frontend import/canonicalization report contract

**Spec:** `SPEC-03`

**Goal:** Make model import and canonicalization emit stable diagnostics, counts, and unsupported-path summaries that can be archived in run artifacts.

**Files:**
- Modify: `src/llm_sched/frontend/onnx_importer.py`
- Modify: `src/llm_sched/frontend/canonicalize.py`
- Create: `src/llm_sched/contracts/frontend_import_report.py`
- Create: `tests/unit/contracts/test_frontend_import_report.py`
- Modify: `tests/unit/frontend/test_onnx_importer.py`
- Modify: `tests/unit/frontend/test_canonicalize.py`

**Deliverables:**
- `frontend_import_report` contract.
- Import stats for raw ONNX nodes, inferred shapes, unresolved dims, canonical node counts.
- Stable unsupported/import-warning surface.

**Acceptance:**
- `python -m pytest tests/unit/contracts/test_frontend_import_report.py tests/unit/frontend/test_onnx_importer.py tests/unit/frontend/test_canonicalize.py -v`
- Real Gemma3 import can emit one deterministic report object per run.

### Story PHB-02: Freeze workload decomposition coverage contract

**Spec:** `SPEC-04`

**Goal:** Separate “成功识别的宏算子”、“显式 pseudo/fallback workload”、“真正未映射路径” 三类结果，避免 decomposition 结果只靠 ad-hoc print 或 smoke script 判断。

**Files:**
- Modify: `src/llm_sched/frontend/nig_lowering.py`
- Create: `src/llm_sched/contracts/workload_decomposition_report.py`
- Create: `tests/unit/contracts/test_workload_decomposition_report.py`
- Modify: `tests/unit/frontend/test_nig_lowering.py`

**Deliverables:**
- `workload_decomposition_report` contract.
- 宏算子计数、pseudo/fallback 计数、unmapped-path 计数。
- traceability summary，能把宏算子映射回 canonical Graph IR 节点集合。

**Acceptance:**
- `python -m pytest tests/unit/contracts/test_workload_decomposition_report.py tests/unit/frontend/test_nig_lowering.py -v`
- 真实 Gemma3 report 中 unmapped-path 必须为 `0`，pseudo/fallback 单独统计。

### Story PHB-03: Define bound-NIG quant/shape/layout contract

**Spec:** `SPEC-07`

**Goal:** Freeze NIG 上的绑定层语义，避免后续 memory planner / tiling planner 直接依赖 frontend 临时 attrs。

**Files:**
- Modify: `src/llm_sched/ir/nig.py`
- Create: `src/llm_sched/frontend/binding.py`
- Create: `tests/unit/frontend/test_binding_contract.py`
- Modify: `tests/unit/ir/test_nig_invariants.py`

**Deliverables:**
- 显式的 bound-NIG field 或 binding payload。
- 至少覆盖：
  - quant metadata
  - resolved shape
  - canonical layout
  - memory class
- validator 规则，禁止缺失关键 binding 的 compute macro-op 混入后续阶段。

**Acceptance:**
- `python -m pytest tests/unit/frontend/test_binding_contract.py tests/unit/ir/test_nig_invariants.py -v`
- bound-NIG dump/reload 不丢字段、不丢 ids。

### Story PHB-04: Bind linear quant metadata and group semantics

**Spec:** `SPEC-07`

**Goal:** 把 `Linear / WDQ_GEMM / RMSNORM_GEMM / GEGLU` 路径上的 quant 语义从“诊断性 attrs”升级成“正式 binding”。

**Files:**
- Modify: `src/llm_sched/frontend/binding.py`
- Modify: `src/llm_sched/frontend/legality.py`
- Modify: `tests/unit/frontend/test_binding_contract.py`
- Modify: `tests/unit/frontend/test_legality.py`

**Deliverables:**
- `weight_dtype` / `activation_dtype` / `quant_mode` / `group_size` / `scale/zp presence` 的正式绑定。
- `group_size` 与后续 `K_tile` 对齐前置检查。
- 把不合法量化配置分类成 binding 缺失、target gap、或真实 unsupported case。

**Acceptance:**
- `python -m pytest tests/unit/frontend/test_binding_contract.py tests/unit/frontend/test_legality.py -v`
- 真实 Gemma3 上 `unsupported_quant_activation_dtype` / `unsupported_quant_group_size` 不再以“前端未绑定”形式出现。

### Story PHB-05: Bind attention/KV shape and layout semantics

**Spec:** `SPEC-07`

**Goal:** 把 `ROPE / SDPA / SDPA_DECODE / KVSTORE / KVLOAD` 的形状和布局从 partial attrs 收口成正式绑定。

**Files:**
- Modify: `src/llm_sched/frontend/binding.py`
- Modify: `src/llm_sched/frontend/shape_binding.py`
- Modify: `src/llm_sched/frontend/legality.py`
- Modify: `tests/unit/frontend/test_binding_contract.py`
- Modify: `tests/unit/frontend/test_shape_binding.py`

**Deliverables:**
- `query_len` / `kv_len` / `head_dim` / `num_heads` / `layout` / `kv layout rule` 的正式绑定。
- prefill 与 decode 两种场景的不同 binding rule。
- 主路径上未收敛动态维的显式收口策略。

**Acceptance:**
- `python -m pytest tests/unit/frontend/test_binding_contract.py tests/unit/frontend/test_shape_binding.py tests/unit/frontend/test_legality.py -v`
- Gemma3 prefill/decode 主路径不再由 `dynamic_shape_unresolved` 阻塞。

### Story PHB-06: Bind memory class and target-facing layout legality

**Spec:** `SPEC-07`

**Goal:** 为后续 `SPEC-08` 预埋明确的 tensor class，而不是把地址规划责任提前压到 planner。

**Files:**
- Modify: `src/llm_sched/frontend/binding.py`
- Modify: `src/llm_sched/frontend/legality.py`
- Create: `tests/unit/frontend/test_memory_class_binding.py`

**Deliverables:**
- `ACTIVATION` / `WEIGHT` / `KV_CACHE` / `QUANT_PARAM` / `METADATA` 等 memory class 绑定。
- target-aware layout legality 改为消费绑定结果，而不是读临时 attrs。
- pseudo/fallback surface 的 memory class 也要显式化。

**Acceptance:**
- `python -m pytest tests/unit/frontend/test_memory_class_binding.py tests/unit/frontend/test_legality.py -v`
- 任意关键张量都能归入一个明确 memory class。

### Story PHB-07: Emit binding diagnostics and bound-NIG reports

**Spec:** `SPEC-07`

**Goal:** 让 Phase B 收口结果能通过 artifact 复盘，而不是只能读 NIG dump 和 legality issue。

**Files:**
- Create: `src/llm_sched/contracts/frontend_binding_report.py`
- Modify: `src/llm_sched/pipeline/frontend_analysis.py`
- Create: `tests/unit/contracts/test_frontend_binding_report.py`
- Modify: `tests/unit/pipeline/test_frontend_analysis_workflow.py`

**Deliverables:**
- `frontend_binding_report` contract。
- 绑定覆盖率、未绑定字段计数、per-macro binding completeness、issue 分类。
- 与 legality report 并存，但语义分离。

**Acceptance:**
- `python -m pytest tests/unit/contracts/test_frontend_binding_report.py tests/unit/pipeline/test_frontend_analysis_workflow.py -v`
- run artifact 中可以同时看到 import、decomposition、binding、legality 四类报告。

### Story PHB-08: Integrate Phase B artifacts into run-root workflow

**Spec:** `SPEC-03`, `SPEC-04`, `SPEC-07`

**Goal:** 把 Phase B 的新报告和 bound-NIG dump 接进现有 `run-frontend-analysis` 主线。

**Files:**
- Modify: `src/llm_sched/pipeline/frontend_analysis.py`
- Modify: `src/llm_sched/cli/main.py`
- Modify: `src/llm_sched/contracts/__init__.py`
- Modify: `tests/smoke/test_cli_run_frontend_analysis.py`

**Deliverables:**
- `dumps/bound_nig_ir.json`
- `reports/frontend_import_report.json`
- `reports/workload_decomposition_report.json`
- `reports/frontend_binding_report.json`
- manifest artifact index 扩展

**Acceptance:**
- `python -m pytest tests/smoke/test_cli_run_frontend_analysis.py tests/unit/pipeline/test_frontend_analysis_workflow.py -v`
- `run-frontend-analysis` 的 artifact manifest 能完整枚举 Phase B 所需工件。

### Story PHB-09: Add Gemma3 Phase B closure smoke matrix

**Spec:** `SPEC-03`, `SPEC-04`, `SPEC-07`

**Goal:** 用真实 Gemma3 和 baseline target/scenario 建一个 Phase B 的正式回归门禁。

**Files:**
- Create: `tests/smoke/test_phase_b_closure_matrix.py`
- Modify: `tests/smoke/test_cli_run_frontend_analysis.py`
- Modify: `docs/development/phase-a-foundation-handoff.md`

**Deliverables:**
- 四象限 smoke matrix：
  - `prefill + single-core`
  - `prefill + dual-core`
  - `decode + single-core`
  - `decode + dual-core`
- 断言项至少包括：
  - import succeeds
  - decomposition succeeds
  - bound-NIG exists
  - blocking `dynamic_shape_unresolved` 已清空
  - pseudo/fallback 和 target gap 分离统计

**Acceptance:**
- `python -m pytest tests/smoke/test_phase_b_closure_matrix.py -v`
- 该 smoke matrix 成为进入 Phase C 的强门禁。

### Story PHB-10: Publish Phase B handoff and flip roadmap status

**Spec:** `SPEC-03`, `SPEC-04`, `SPEC-07`

**Goal:** 当 Phase B 收口完成后，给下一阶段留下一份明确 handoff，而不是口头宣告。

**Files:**
- Create: `docs/development/phase-b-semantic-handoff.md`
- Modify: `docs/development/evaluation-compiler-roadmap.md`
- Modify: `docs/development/README.md`

**Deliverables:**
- Phase B handoff 文档。
- roadmap 中把 `SPEC-07` 和 `Phase B` 翻成 `done`。
- 明确列出 Phase C 可以假设稳定存在的输入契约。

**Acceptance:**
- handoff 文档包含：
  - bound-NIG contract
  - import/decomposition/binding/legality artifact list
  - 四象限 smoke matrix 结果
  - Phase C 非目标和输入边界

## Execution Order

按这个顺序推进：

1. `PHB-01`
2. `PHB-02`
3. `PHB-03`
4. `PHB-04`, `PHB-05`
5. `PHB-06`
6. `PHB-07`
7. `PHB-08`
8. `PHB-09`
9. `PHB-10`

## Definition of Done for Phase B

Phase B 只有在以下条件都满足时才算 done：

- `SPEC-03 = done`
- `SPEC-04 = done`
- `SPEC-07 = done`
- `Milestone M1 = done`
- run-root artifact 已包含 import / decomposition / binding / legality / NIG / bound-NIG / analysis 工件
- Gemma3 四象限 smoke matrix 稳定通过
- roadmap 已把 `Phase B` 标为 `done`
