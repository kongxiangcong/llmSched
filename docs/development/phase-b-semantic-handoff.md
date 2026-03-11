# Phase B Semantic Handoff

## 1. What Is Stable Now

Phase B 已经把 frontend 语义层从“能跑通”收口到“可作为 Phase C 规划层输入契约”：

- `ONNX -> GraphIR -> canonical GraphIR -> NIG -> bound-NIG -> pseudo/fallback AnalysisIR`
- Gemma3 `prefill` / `decode` 场景化 shape binding
- single-core / dual-core target-aware legality
- import / decomposition / binding / legality / pseudo-fallback summary 独立报告
- run-root artifact 闭环

当前重点不是再扩 frontend coverage，而是把已经稳定的 bound-NIG 和 artifact contract 交给后续的 memory planner、tiling planner 和 scheduler 使用。

## 2. Stable Bound-NIG Contract

`bound_nig_ir.json` 是 Phase C 可以正式依赖的输入之一。当前稳定约束如下：

- `NIGIR.binding_state = "bound"`
- compute 节点具备 `binding` payload
- `binding.resolved_shape`
  - 经过 scenario-aware shape binding 后的稳定 shape
- `binding.canonical_layout`
  - 当前宏算子的 canonical tensor layout
- `binding.memory_class`
  - 节点主 memory class
- `binding.input_memory_classes` / `binding.output_memory_classes`
  - tensor 级 memory class 标注
- `binding.quant`
  - `quant_mode`
  - `scale_present`
  - `zero_point_present`
  - `k_tile_size`
  - `k_tile_aligned`
- `binding.attention`
  - `mode`
  - `query_len`
  - `kv_len`
  - `head_dim`
  - `num_heads`
  - `num_key_value_heads`
  - `tensor_layout`
  - `kv_layout_rule`

Phase C 不应再回退到 frontend 内部 pattern 节点去重新推导这些信息。

## 3. Stable Run Artifacts

执行 `llm-sched run-frontend-analysis --run-root <path>` 后，当前稳定输出是：

### Dumps

- `dumps/graph_ir.json`
- `dumps/canonical_graph_ir.json`
- `dumps/nig_ir.json`
- `dumps/bound_nig_ir.json`
- `dumps/analysis_ir.json`

### Reports

- `reports/frontend_import_report.json`
- `reports/workload_decomposition_report.json`
- `reports/frontend_binding_report.json`
- `reports/frontend_legality.json`
- `reports/pseudo_fallback_summary.json`

### Run State

- `manifest.json`
  - `status`
  - `artifact_index`
- `run-summary.json`
  - `status`
  - `exit_code`
  - `diagnostics`

这些 artifact 已经被 CLI smoke 和 workflow unit test 覆盖，Phase C 应直接复用，不要另起平行输出格式。

## 4. Phase B Closure Gate

Gemma3 Phase B smoke matrix 当前已经稳定覆盖：

- `single-core + prefill`
- `single-core + decode`
- `dual-core + prefill`
- `dual-core + decode`

四个组合都满足：

- import succeeds
- decomposition succeeds
- bound-NIG exists
- `dynamic_shape_unresolved = 0`
- pseudo/fallback 与 target gap 分离统计

当前稳定基线：

- legality issue counts
  - `kv_cache_dtype_mismatch = 69`
  - `no_hardware_mapping = 1220`
  - `target_quant_activation_dtype_gap = 182`
  - `target_quant_group_size_gap = 182`
- pseudo/fallback record counts
  - `ATTENTION_MASK_PREP = 16`
  - `EMBEDDING_LOOKUP = 1`
  - `LAYOUT_FALLBACK = 412`
  - `ROPE_TABLE = 2`
  - `SHAPE_HELPER = 789`
- binding coverage
  - prefill: `0.7864`
  - decode: `0.7797`

这组数字应该被当成 Phase B 关闭时的已知基线，而不是缺陷列表。

## 5. What Phase C Can Assume

Phase C 可以直接假设以下前提成立：

- canonical Graph IR 和 NIG lowering 对当前 Gemma3 主路径已经闭合
- bound-NIG 已包含 quant / shape / layout / memory-class / attention binding
- run-root artifact 已能稳定落盘并被 manifest 索引
- legality 中不再存在 blocking `dynamic_shape_unresolved`
- pseudo/fallback surface 已从 target gap 中分离

Phase C 不需要再处理“前端是否能识别这条 Gemma3 主路径”这类问题。

## 6. What Is Still Not Solved

Phase B 完成不意味着这些能力已经存在：

- VMEM / KV address planning
- tile candidate generation
- single-core scheduling
- dual-core partition / barrier / transfer scheduling
- descriptor generation
- ISA coverage mapping
- full compute perf estimator
- prefill / decode full evaluation pipeline
- visualization data service / UI

这些是 Phase C / D / E 的工作，不应回灌成 frontend 需求。

## 7. Recommended Next Step

下一阶段应该正式进入 Phase C，顺序保持为：

1. `SPEC-08` VMEM / KV / address planner
2. `SPEC-09` tile planner
3. `SPEC-10` / `SPEC-11` single-core / dual-core scheduler
4. `SPEC-12` descriptor / ISA coverage mapping

建议第一步先冻结 `bound-NIG -> memory planner` 的输入 contract，再开实现。
