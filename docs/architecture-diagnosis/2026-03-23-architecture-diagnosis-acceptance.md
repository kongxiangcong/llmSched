# Architecture Diagnosis Dataset Refactor Acceptance

- 日期：2026-03-23
- 状态：accepted-for-review
- 范围：`docs/architecture-diagnosis/2026-03-23-architecture-diagnosis-execution-plan.md`
- 执行人：Codex

## 1. 结果摘要

本轮已完成 diagnosis 重构主线：

- 引入共享 `DiagnosisContext`，统一 diagnosis 输入加载与 provenance/accessor。
- 将 diagnosis pipeline 扩展为四层持久化输出：
  - root reports：`reports/diagnosis/*.json`
  - trace：`reports/diagnosis/trace/*.json`
  - dataset：`reports/diagnosis/dataset/*.csv`
  - layer 2 summary：`reports/diagnosis/diagnosis_chain_summary.json`
- 冻结并落地 diagnosis dataset schema registry。
- 为 8 个 diagnosis builders 增加 context 入口与 dataset-ready extract helpers。
- 落地 relation / realization gap / timeline loss 首版导出。
- 收缩 DIAG-01~07 root 主视图，保留 trace 全量证据。
- 扩充 DIAG-08，增加 `key_metrics` 与 `top_realization_gaps`。
- 更新 baseline / unit / pipeline / smoke 验证链路。

## 2. 已交付文件

### 核心实现

- `src/llm_sched/analysis/diagnosis_context.py`
- `src/llm_sched/analysis/diagnosis_dataset_writer.py`
- `src/llm_sched/analysis/realization_gap_builder.py`
- `src/llm_sched/analysis/timeline_loss_builder.py`
- `src/llm_sched/contracts/diagnosis_dataset_schema.py`
- `src/llm_sched/contracts/diagnosis_chain_summary.py`
- `src/llm_sched/pipeline/diagnosis_analysis.py`

### 契约 / 布局更新

- `src/llm_sched/contracts/diagnosis_common.py`
- `src/llm_sched/contracts/architecture_assessment_report.py`
- `src/llm_sched/contracts/__init__.py`

### 测试与基线

- `tests/unit/contracts/test_diagnosis_dataset_schema.py`
- `tests/unit/contracts/test_diagnosis_chain_summary.py`
- `tests/unit/analysis/test_realization_gap_builder.py`
- `tests/unit/pipeline/test_diagnosis_context.py`
- `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
- `tests/unit/pipeline/test_diagnosis_baseline_fixtures.py`
- `tests/smoke/test_cli_run_diagnosis_analysis.py`
- `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
- `tests/fixtures/diagnosis_baseline/`
- `scripts/generate_diagnosis_baselines.py`
- `tests_diagnosis_baseline.py`

## 3. 当前输出结构

一次完整 diagnosis 运行现在会写出：

- root：`reports/diagnosis/*.json`
- trace：`reports/diagnosis/trace/*.json`
- dataset：`reports/diagnosis/dataset/*.csv`
- layer 2：`reports/diagnosis/diagnosis_chain_summary.json`
- 兼容：`reports/diagnosis_bundle.json`、`diagnosis_workbench/`

## 4. 已验证能力

### Context / Builder

- diagnosis pipeline 只构建一次共享 context
- 8 个 diagnosis builders 支持 `ctx` 直入
- Stage 1~9 都有首版 extract helper 可供 writer 复用

### Dataset

已导出并验证的关键表包括：

- core：`structure_inventory.csv`、`operator_mapping.csv`、`structure_demand.csv`、`layer_demand.csv`、`structure_support_matrix.csv`、`schedule_blocks.csv`、`perf_by_structure.csv`、`realization_gap.csv`、`bottleneck_summary.csv`、`timeline_loss_detail.csv`、`timeline_loss_summary.csv`、`assessment_summary.csv`
- views：`model_summary.csv`、`macro_op_summary.csv`、`subject_demand.csv`、`phase_demand_summary.csv`、`demand_hotspot_top20.csv`、`critical_gaps.csv`、`core_utilization.csv`、`phase_breakdown.csv`、`node_hotspot_top30.csv`、`structure_bottleneck.csv`、`pressure_summary.csv`、`roofline_points_by_layer.csv`、`recommendations.csv`
- relations：`subject_structure_map.csv`、`subject_block_map.csv`、`block_descriptor_map.csv`

### Root / Trace

- root report 已做缩减，重点明细下沉到 trace
- trace 保留完整原始 diagnosis JSON，便于调试与回溯

### Assessment / Layer 2

- `architecture_assessment_report.json` 已包含：
  - `overall_assessment`
  - `top_bottlenecks`
  - `top_support_gaps`
  - `top_timeline_losses`
  - `top_realization_gaps`
  - `key_metrics`
  - `recommendations`
  - `confidence_summary`
- `diagnosis_chain_summary.json` 已包含 `realization_gap` / `timeline` 阶段

## 5. 测试结果

已通过的完整回归命令：

```powershell
pytest tests/unit/pipeline/test_diagnosis_baseline_fixtures.py \
       tests/unit/contracts/test_architecture_assessment_report.py \
       tests/unit/contracts/test_diagnosis_dataset_schema.py \
       tests/unit/contracts/test_diagnosis_chain_summary.py \
       tests/unit/analysis/test_architecture_assessment_report_builder.py \
       tests/unit/analysis/test_realization_gap_builder.py \
       tests/unit/pipeline/test_diagnosis_context.py \
       tests/unit/pipeline/test_diagnosis_dataset_writer.py \
       tests/unit/pipeline/test_diagnosis_analysis_architecture_assessment.py \
       tests/unit/pipeline/test_diagnosis_analysis_workflow.py \
       tests/unit/pipeline/test_diagnosis_packaging_workflow.py \
       tests/unit/pipeline/test_diagnosis_workbench_workflow.py \
       tests/smoke/test_cli_run_diagnosis_analysis.py \
       tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q
```

结果：`40 passed`

## 6. 已知保留项

以下问题当前不阻塞主线，但仍建议后续继续收口：

1. `critical_gaps.csv`
   - 当前仍为 mixed-granularity 设计
   - 通过 `subject_kind` 区分 node / structure
   - `normalized_node_id` 列实际承载了兼容态 `subject_id`

2. `schedule_blocks.csv`
   - dual-core / shared block 仍采用扁平多行表达 `core_ids`
   - 满足 CSV 导出与 join，但严格主键语义仍有设计优化空间

3. `timeline_loss_summary.csv`
   - `representative_entities` 仍采用扁平字符串首版
   - 若后续更强调 join 友好，可升级为 relation 表方案

## 7. 边界检查

本轮保持了以下边界：

- 未改 diagnosis bundle 结构定义
- 未改 diagnosis packaging / workbench 的职责边界
- 未动非 diagnosis 主线语义
- root diagnosis 报表路径仍兼容原消费方

## 8. 评审建议

建议评审优先检查：

- `src/llm_sched/analysis/diagnosis_context.py`
- `src/llm_sched/analysis/diagnosis_dataset_writer.py`
- `src/llm_sched/pipeline/diagnosis_analysis.py`
- `src/llm_sched/analysis/architecture_assessment_report_builder.py`
- `src/llm_sched/contracts/diagnosis_dataset_schema.py`
- `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
- `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`

## 9. 结论

按照执行计划主线目标，本轮 diagnosis 数据体系重构已达到可评审、可回归、可继续演进状态。

后续若继续迭代，建议优先处理：

- `critical_gaps.csv` 主体键最终设计
- `schedule_blocks.csv` dual-core 主键/表达优化
- `timeline_loss_summary.csv.representative_entities` relation 化
