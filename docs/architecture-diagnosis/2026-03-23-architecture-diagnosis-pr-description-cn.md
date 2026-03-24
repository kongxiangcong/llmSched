# Architecture Diagnosis Refactor PR Description (CN)

## 背景

当前 diagnosis 流程存在几个结构性问题：

- diagnosis builders 各自重复读取 run-root artifact
- provenance / structure / layer / node / block / descriptor 关系分散在多个 builder 内重复构建
- diagnosis 缺少稳定的 dataset 层，无法可靠支撑 join、gap、timeline 和 layer-2 汇总
- root diagnosis report 同时承载“结论层”和“证据层”，导致一部分 report 过重，另一部分 report 又缺乏量化支撑

本 PR 的目标是把 diagnosis 从“8 个独立 report 的集合”重构为“共享 context + trace / dataset / layer2 四层输出”的体系，同时保持 diagnosis bundle / workbench 的消费边界可用。

## 主要改动

### 1. 引入共享 DiagnosisContext

新增：

- `src/llm_sched/analysis/diagnosis_context.py`

实现内容：

- 统一加载 diagnosis 所需 artifact / report / profile
- 统一解析 `report_kind` / `schedule_kind`
- 提供 graph node / normalized node / block / descriptor / allocation / provenance accessor
- 让 diagnosis pipeline 只在入口构建一次 context

### 2. 冻结 diagnosis dataset schema

新增：

- `src/llm_sched/contracts/diagnosis_dataset_schema.py`

实现内容：

- 固定 28 张 diagnosis dataset 表的 schema registry
- 区分 core / view / relation 表
- 提供按表查询 row model / schema / validation 入口

### 3. 迁移 diagnosis builders 到共享 context

已让以下 builders 支持 `ctx` 直入：

- DIAG-01 model structure
- DIAG-02 operator representation
- DIAG-03 resource demand
- DIAG-04 support matrix
- DIAG-05 schedule diagnostics
- DIAG-06 performance diagnostics
- DIAG-07 roofline
- DIAG-08 architecture assessment

同时为 Stage 1~9 补了首版 extract helpers，供 dataset writer 复用。

### 4. 建立 trace / dataset / layer2 输出体系

输出层次现在为：

- root：`reports/diagnosis/*.json`
- trace：`reports/diagnosis/trace/*.json`
- dataset：`reports/diagnosis/dataset/*.csv`
- layer2：`reports/diagnosis/diagnosis_chain_summary.json`

新增：

- `src/llm_sched/analysis/diagnosis_dataset_writer.py`
- `src/llm_sched/contracts/diagnosis_chain_summary.py`

### 5. 导出 relation / gap / timeline 视图

新增：

- `src/llm_sched/analysis/realization_gap_builder.py`
- `src/llm_sched/analysis/timeline_loss_builder.py`

当前已导出：

- relation：
  - `subject_structure_map.csv`
  - `subject_block_map.csv`
  - `block_descriptor_map.csv`
- gap：
  - `realization_gap.csv`
- timeline：
  - `timeline_loss_detail.csv`
  - `timeline_loss_summary.csv`

### 6. 收缩 root report，保留 trace 全量证据

root diagnosis report 现已做结论层收缩，例如：

- DIAG-01 root 不再携带完整 `node_index[]`
- DIAG-02 root 不再携带完整 `traceability_index[]`
- DIAG-03 root 不再携带完整 `node_demands[]`
- DIAG-04 root 不再携带完整 `node_support_entries[]`
- DIAG-05 root 不再携带完整 `blocks[] / idle_spans[] / stall_events[]`
- DIAG-07 root 不再携带完整 `node_points[]`

完整明细仍保留在 `trace/` 中。

### 7. 扩充 DIAG-08

`architecture_assessment_report.json` 现已包含：

- `top_realization_gaps`
- `key_metrics`
- 原有 `overall_assessment`
- `top_bottlenecks`
- `top_support_gaps`
- `top_timeline_losses`
- `recommendations`
- `confidence_summary`

## 验证

执行了以下完整回归：

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

结果：

- `40 passed`

## 对兼容性的影响

### 保持兼容

- diagnosis 根目录报表路径仍保留
- diagnosis bundle / workbench 路径兼容已验证
- 非 diagnosis 主线未改语义

### 有意变化

- root diagnosis report 已从“全量证据层”转为“较轻的结论层”
- 全量明细转移到 `trace/`
- 新增 `dataset/` 和 `diagnosis_chain_summary.json`
- DIAG-08 增加了新的字段和结论支撑信息

## 已知保留项

当前仍有 3 个后续可继续收口的点：

1. `critical_gaps.csv` 的主体键仍是兼容态设计
2. `schedule_blocks.csv` dual-core / shared block 仍使用首版扁平多行表达
3. `timeline_loss_summary.csv.representative_entities` 仍使用扁平字符串，不是 relation 表

这些问题当前不阻塞主线导出、join、smoke 与 bundle/workbench 消费。

## 建议 reviewer 重点看

1. `src/llm_sched/analysis/diagnosis_context.py`
2. `src/llm_sched/pipeline/diagnosis_analysis.py`
3. `src/llm_sched/contracts/diagnosis_dataset_schema.py`
4. `src/llm_sched/analysis/diagnosis_dataset_writer.py`
5. `src/llm_sched/analysis/architecture_assessment_report_builder.py`
6. `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
7. `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
