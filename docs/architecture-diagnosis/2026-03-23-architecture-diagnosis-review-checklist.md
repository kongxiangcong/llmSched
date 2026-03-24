# Architecture Diagnosis Review Checklist

- 日期：2026-03-23
- 用途：给 reviewer 快速过一遍 diagnosis 重构关键风险点

## 1. 先看产物边界

- [ ] `reports/diagnosis/*.json` 仍可被 packaging/workbench 消费
- [ ] `reports/diagnosis/trace/*.json` 保留全量明细
- [ ] `reports/diagnosis/dataset/*.csv` 字段顺序与 schema 一致
- [ ] `reports/diagnosis/diagnosis_chain_summary.json` 已生成且 stage 链完整

## 2. 核心代码入口

- [ ] `src/llm_sched/pipeline/diagnosis_analysis.py`
  - [ ] diagnosis pipeline 是否只构建一次 `DiagnosisContext`
  - [ ] root / trace / dataset / layer2 是否都由同一轮 workflow 写出
  - [ ] root shrink 是否只影响 root，不影响 trace
- [ ] `src/llm_sched/analysis/diagnosis_context.py`
  - [ ] artifact 解析是否覆盖 prefill/decode + single/dual-core
  - [ ] accessor 是否统一 provenance / relation 查询
- [ ] `src/llm_sched/analysis/diagnosis_dataset_writer.py`
  - [ ] writer 是否按 schema field 顺序输出 header
  - [ ] 所有 CSV 是否都在写出前经过 schema validation

## 3. 高风险派生检查

- [ ] `src/llm_sched/analysis/realization_gap_builder.py`
  - [ ] `gap_kind` 分类是否符合当前降级策略
  - [ ] `gap_confidence` 是否不会伪装为高置信
- [ ] `src/llm_sched/analysis/timeline_loss_builder.py`
  - [ ] `loss_kind` 六分类是否能覆盖 stall/idle 场景
  - [ ] `recoverable_slots_estimated` 系数是否与设计文档一致

## 4. DIAG-08 检查

- [ ] `src/llm_sched/contracts/architecture_assessment_report.py`
  - [ ] `top_realization_gaps` contract 是否稳定
  - [ ] `key_metrics` contract 是否足够支撑 layer-2 summary / smoke
- [ ] `src/llm_sched/analysis/architecture_assessment_report_builder.py`
  - [ ] `key_metrics` 是否来自当前 dataset / report 闭环
  - [ ] `top_realization_gaps` 是否在无 context 时也有安全降级

## 5. 仍待后续设计收口的点

- [ ] `critical_gaps.csv` 的主体键是否继续保留 mixed-granularity
- [ ] `schedule_blocks.csv` dual-core/shared block 是否保持当前扁平多行表达
- [ ] `timeline_loss_summary.csv.representative_entities` 是否升级为 relation 表

## 6. 自动化验证

- [ ] 查看 `docs/architecture-diagnosis/2026-03-23-architecture-diagnosis-acceptance.md`
- [ ] 查看 `docs/architecture-diagnosis/2026-03-23-architecture-diagnosis-pr-summary.md`
- [ ] 关键测试是否覆盖：
  - [ ] `tests/unit/pipeline/test_diagnosis_context.py`
  - [ ] `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
  - [ ] `tests/unit/analysis/test_realization_gap_builder.py`
  - [ ] `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`

## 7. 推荐评审顺序

1. `src/llm_sched/analysis/diagnosis_context.py`
2. `src/llm_sched/contracts/diagnosis_dataset_schema.py`
3. `src/llm_sched/analysis/diagnosis_dataset_writer.py`
4. `src/llm_sched/pipeline/diagnosis_analysis.py`
5. `src/llm_sched/analysis/architecture_assessment_report_builder.py`
6. `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
7. `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
