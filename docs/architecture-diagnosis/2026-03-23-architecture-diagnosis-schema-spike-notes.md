# Architecture Diagnosis Schema Spike Notes

- 日期：2026-03-23
- 阶段：P0-T3 in progress
- 目的：核对 4 个高风险 schema 点与当前 codebase 的真实约束是否一致。

## 1. `schedule_blocks.csv` 主键与 dual-core 表达

- 代码证据：`src/llm_sched/ir/schedule_ir.py`
  - `ScheduleBlock.block_id` 必须全局唯一。
  - `ScheduleBlock.core_id` 类型是 `int | "both"`。
  - transfer block 还带 `peer_core_id`。
- 代码证据：`src/llm_sched/contracts/schedule_diagnostics_report.py`
  - 诊断报告层 `ScheduleDiagnosticBlock.core_ids: list[int]`，不是单个 `core_id`。
- 当前结论：
  - `block_id` 作为主键是稳定的。
  - 仅用单列 `core_id:int` 无法完整表达 dual-core / shared block。
- 待决策：
  - 保持一行一个 block，则需要在 dataset schema 中引入 `peer_core_id` 或等价扁平字段。
  - 若坚持单列 `core_id`，将丢失 `"both"` / 双核占用信息。

## 2. `critical_gaps.csv` 主体主键语义

- 代码证据：`src/llm_sched/analysis/support_matrix_report_builder.py`
  - builder 直接为 node 级 gap 生成 `subject_kind="node"`。
  - 同时也聚合出 structure 级 gap，生成 `subject_kind="structure"`。
- 代码证据：`src/llm_sched/contracts/support_matrix_report.py`
  - `CriticalSupportGap` 合约字段是 `subject_id` + `subject_kind`。
- 当前结论：
  - 当前 codebase 的 `critical_gaps` 是混合粒度表，不是纯 node-only。
  - 设计稿中仅保留 `normalized_node_id` 列会丢失 structure 级记录。
- 待决策：
  - 方案 A：改成 `subject_id + subject_kind`。
  - 方案 B：拆成 node / structure 两张表。
  - 在结论确认前，不宜把 `normalized_node_id` 当成唯一主体键彻底冻结。

## 3. `block_descriptor_map.csv` 的 1:1 / 1:n 基数

- 代码证据：`src/llm_sched/ir/descriptor_ir.py`
  - `DescriptorIR` 校验 `schedule_block_id` 在 descriptors 中必须唯一。
- 当前结论：
  - 当前实现实际是 `schedule_block_id -> descriptor_id` 的 1:1。
  - 设计稿中的 relation 表保留 1:n 形状仍有前向兼容价值，但 writer 在当前 codebase 下最多输出一条映射。
- 建议：
  - schema 可以保留 relation 表形状不变。
  - spike 结论中应明确“当前实现 1:1，schema 允许未来扩展到 1:n”。

## 4. `timeline_loss_summary.csv` 禁数组列策略

- 设计证据：`docs/architecture-diagnosis/2026-03-23-architecture-diagnosis-design-spec.md`
  - 当前字段仍写作 `representative_entities`，说明为“最典型的 2-3 个 block_id”。
  - 附录 B 同时明确 CSV 禁数组列。
- 当前结论：
  - 设计稿内部仍有冲突，尚未落到代码实现。
- 待决策：
  - 方案 A：改为单个 `top_entity_id`。
  - 方案 B：保留汇总表纯聚合字段，另拆 relation 表。
  - 方案 C：写分隔字符串，但这会削弱 schema 稳定性与 join 友好性。

## 当前建议

- 先不要在 writer 层实现这 4 个点的最终严格语义。
- 其中第 3 点已经基本可判定；第 1 / 2 / 4 点需要先更新 schema 冻结备注，再继续 P1 / P3 之后的严格收口。
