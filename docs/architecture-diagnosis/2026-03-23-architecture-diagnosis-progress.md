# Architecture Diagnosis Refactor Progress

- 当前版本：P5-T3 completed
- 当前阶段：Phase 5 / validation
- 总体状态：green
- 日期：2026-03-23
- 负责人：Codex

## 已完成任务

- [x] P0-T1
- [x] P0-T2
- [x] P0-T3（第一轮 spike 证据收集与结论记录）
- [x] P1-T1
- [x] P1-T2（共享索引 / accessor 首版）
- [x] P1-T3
- [x] P1-T4（workflow 回归）
- [x] P2-T1
- [x] P2-T2（首版 ctx 迁移 + Stage 3/4/5 extract helpers）
- [x] P2-T3（首版 ctx 迁移 + Stage 6/7/9 extract helpers）
- [x] P3-T1
- [x] P3-T2
- [x] P3-T3
- [x] P3-T4（focused writer/schema/workflow regression）
- [x] P4-T1（以已记录 spike notes + 降级策略落地首版）
- [x] P4-T2（first-pass `realization_gap.csv`）
- [x] P4-T3（first-pass timeline loss detail/summary）
- [x] P4-T4（first-pass relation tables）
- [x] P4-T5（root report shrink + DIAG-08 扩充）
- [x] P5-T1（baseline 重生 + shrink 合理性回归）
- [x] P5-T2（dataset / join / gap / timeline tests）
- [x] P5-T3（smoke matrix 更新）

## 进行中任务

- [ ] 任务编号：无
  说明：当前执行计划内主线任务已跑通。
  当前结果：baseline、unit、pipeline、smoke 均已覆盖新的 root / trace / dataset / layer2 输出体系。

## 阻塞项

| 阻塞编号 | 对应任务 | 阻塞描述 | 是否影响主线 | 需要谁确认 | 预计解除时间 |
|---|---|---|---|---|---|
| B-01 | 后续优化 | `critical_gaps.csv` 严格主体键、`timeline_loss_summary.csv.representative_entities` 的最终语义仍可继续设计收口 | 否 | 实现者 / 设计评审 | 后续迭代 |

## 风险变化

| 风险编号 | 新状态 | 变化说明 | 是否新增缓解动作 |
|---|---|---|---|
| R-14 | mitigated | baseline、shrink、trace/dataset/layer2 regression 已全部自动化 | 是 |
| R-01 | mitigated | schema registry、DiagnosisContext、dataset writer、derived builders、smoke 断言均已落地 | 是 |

## 回归结果

- focused unit：`pytest tests/unit/analysis/test_realization_gap_builder.py tests/unit/pipeline/test_diagnosis_dataset_writer.py -q` → 9 passed
- workflow：`diagnosis_analysis` 已输出 root / trace / dataset / layer2，并验证 root shrink 与 trace 全量共存
- smoke：`pytest tests/smoke/test_cli_run_diagnosis_analysis.py tests/smoke/test_phase_f_architecture_diagnosis_matrix.py -q` → 6 passed
- baseline compare：新的三层 baseline fixture 已重生并通过解析/摘要校验
- join validation：核心 relation / dataset join correctness 已有自动测试

## 新发现问题

- 问题：`critical_gaps.csv` 仍采用 `subject_id -> normalized_node_id` 的兼容映射，严格主体语义尚未最终收口
  影响：不会阻塞当前导出和 join，但会影响后续严格 schema 语义说明
  临时处理：继续保留 `subject_kind` 区分，并在 spike notes 中记录

- 问题：`timeline_loss_summary.csv.representative_entities` 仍采用扁平字符串首版
  影响：可消费但不如 relation 方案规范
  临时处理：在 schema 中保留 provisional note，后续再决定是否拆 relation

## 下一步计划

- [ ] 下一任务 1：如需进一步收口，优先统一 `critical_gaps.csv` 的主体键设计
- [ ] 下一任务 2：评估是否将 `representative_entities` 升级为 relation 表
- [ ] 下一任务 3：整理最终验收记录 / 评审材料

## 是否偏离边界

- 否

## 是否影响既有契约

- 影响 diagnosis root report 的主视图体量，但 trace 保留全量，bundle/workbench 兼容性已验证
- 影响文件：diagnosis report root JSON、derived CSV、Layer 2 summary、相关测试/文档
- 影响范围：diagnosis 主视图 / trace / dataset / chain summary 四层输出
- 是否已同步测试：是

## 需要同步给评审者的事项

- [x] schema 冻结变更
- [x] 新 blocker
- [x] risk 状态变化
- [ ] regression 失败
- [ ] 边界偏离
