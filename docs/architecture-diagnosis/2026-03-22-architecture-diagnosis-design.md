# Architecture Diagnosis Design

## Intent

当前分支已经达到 `close-enough / practical stop-line`，应被视为一个冻结的评估编译器基线节点，而不是继续在现有 `SPEC-13/14/15/16/19` 上无边界追加交互或局部指标。后续开发不再把“补更多 summary 可视化”作为默认方向，而是切换到一个新的、显式设计过的架构诊断轨道。

本设计文档定义一个新的诊断体系。目标不是替换现有编译流水线，而是在现有 artifact、IR 和评估结果之上增加一层更高阶、更成体系的分析输出，使系统能够回答下面这些问题：

- 模型结构是什么，关键子结构在哪里
- 编译器实际如何理解这些结构
- 每个结构需要多少计算、带宽、存储和时序资源
- 当前架构能否原生支持，若不能，卡在什么约束
- 调度如何落地，哪里出现空闲、串行化、屏障等待和资源争用
- 性能瓶颈究竟来自算力、带宽、容量、同步，还是支持性缺口
- 哪些层、节点、结构对当前架构最不友好
- 应该优先改模型、改调度，还是改架构

## Baseline Freeze

本设计采用如下冻结语义：

- 当前分支为 `2026-03-22` 基线节点
- 现有 `Phase A/B/C` 与当前 `Phase D/E` closeout judgment 继续成立
- 现有 `SPEC-13/14/15/16/19` 不因本设计自动 reopening
- 新轨道是加法式扩展，不是对当前主线 closeout 结论的回滚
- 除非出现新的 concrete failing evidence，否则不重写现有 foundation contract

换句话说，新的开发起点不是“当前项目还没做完”，而是“当前项目作为 baseline engine 已冻结，下一阶段开始建设 diagnosis layer”。

## Problem Statement

当前仓库已经具备大量可复用能力：

- `GraphIR / NIG / ScheduleIR / DescriptorIR / PerfSummaryReport`
- prefill/decode top-level report
- sweep compare 与 standalone compare report
- visualization bundle 与 static workbench/catalog

但这些能力目前仍然是“可分析数据 + 分散面板”的形态，还不是完整诊断链：

- 模型结构视图和架构支持视图没有系统聚合
- legality issue 存在，但没有提升为结构化 support matrix
- perf 有 phase/node/layer 数据，但没有显式 demand model 和 bottleneck taxonomy
- schedule 有 `issue_slot` 与 `duration_slots`，但当前 timeline 仍是 block table，不是真正的 timeline
- roofline 完全缺位
- 当前系统缺少一个最终的 architecture assessment synthesis artifact

因此，新的开发重点不是“再补一些 summary 字段”，而是补齐完整诊断链上的缺失层，并把当前已有的离散证据组织为体系产物。

## Goals

- 定义一条完整、可落地、可验证的架构诊断链
- 在现有编译与评估 artifact 之上增加 diagnosis-specific report layer
- 保持 traceability: `graph node -> normalized op -> macro/phase -> schedule block -> descriptor -> perf -> diagnosis`
- 让输出从“局部指标”升级为“结构化 diagnosis reports + diagnosis workbench”
- 让未来开发能够按明确 spec 和 task roadmap 推进，而不是继续 ad hoc 扩展现有 visualization

## Non-Goals

- 不在本设计阶段修改任何代码
- 不在本设计阶段重新设计底层 IR 栈
- 不在本设计阶段引入 live service 或数据库
- 不默认扩大当前编译器支持的模型族或硬件族
- 不把 deeper estimator research 当作本轨道的前置阻塞条件

## Approach Options

### Option A: 继续在当前 workbench 上补 summary/panel

优点：

- 短期改动小
- 可以快速让现有前端看起来更“丰富”

缺点：

- 依然没有统一 diagnosis contract
- 很容易把结构支持、需求建模、roofline、timeline、assessment 混进一个不断膨胀的 static UI
- 难以验证，也难以复用到 compare/export/report

### Option B: 在现有编译流水线之上增加 diagnosis artifact layer

优点：

- 与当前仓库结构最兼容
- 可以复用现有 artifact 和 tests
- 可以先把 diagnosis reports 建稳，再做 UI
- 最利于 traceability、回归测试与 compare reuse

缺点：

- 新 contract 数量会增加
- 前期需要接受“先补报告层，再补界面层”的节奏

### Option C: 为诊断重新设计一套独立 IR / pipeline

优点：

- 理论上最干净
- 适合未来演化成完全独立的诊断产品

缺点：

- 对当前仓库破坏性太强
- 成本最高
- 容易把“诊断层建设”误做成“重写编译器”

## Recommended Approach

选择 Option B。

原因很简单：当前仓库已经拥有稳定的上游 artifact、评估产物和 static packaging 能力，新的开发最应该做的是显式增加一层 diagnosis reports，把分散的数据组织成可验证、可打包、可导出的体系输出。这样既能冻结当前分支，又不会把新需求变成“重开整个项目主线”。

## Canonical Diagnosis Chain

下面这条链是新的 canonical diagnosis flow：

1. 模型结构抽取
2. 算子表示与归一化
3. 资源需求建模
4. 架构支持性匹配
5. 映射与调度诊断
6. 性能归因与瓶颈分类
7. roofline 与上界解释
8. timeline / idle / stall 诊断
9. 架构评估综合结论

### Stage 1: 模型结构抽取

回答的问题：

- 模型由哪些 layer/block/subgraph 组成
- attention、MLP、KV、embedding、辅助路径分别在哪里
- 每个结构的输入输出 shape、dtype、序列依赖是什么

主要输入：

- `canonical_graph_ir.json`
- `frontend_import_report.json`
- `frontend_binding_report.json`

主要输出：

- `model_structure_report.json`

### Stage 2: 算子表示与归一化

回答的问题：

- 编译器最终把模型理解成了哪些 canonical op / macro-op / phase
- 原模型节点如何映射到 normalized node、macro-op、schedule block
- 哪些节点落入 helper/fallback surface

主要输入：

- `canonical_graph_ir.json`
- `bound_nig_ir.json`
- `workload_decomposition_report.json`

主要输出：

- `operator_representation_report.json`

### Stage 3: 资源需求建模

回答的问题：

- 每个结构理论上需要多少 compute、memory、bandwidth 和时序资源
- 哪些结构天然 compute-heavy，哪些结构天然 memory-heavy
- 哪些结构的 working set 或 IO 模式天生不适合当前架构

主要输入：

- `model_structure_report.json`
- `operator_representation_report.json`
- `memory_plan.json`

主要输出：

- `resource_demand_report.json`

### Stage 4: 架构支持性匹配

回答的问题：

- 当前架构对每个结构/节点是 native、constrained、fallback 还是 unsupported
- 约束来自 opcode、dtype、layout、group size、KV layout、memory class、core topology 还是其它 contract

主要输入：

- `target_profile`
- `frontend_legality.json`
- `frontend_binding_report.json`
- `operator_representation_report.json`

主要输出：

- `support_matrix_report.json`

### Stage 5: 映射与调度诊断

回答的问题：

- 当前结构如何被 tile、映射到 core、插入 DMA/transfer/barrier
- 真正的开始/结束时刻是什么
- 哪些资源争用导致串行化

主要输入：

- `tiling_plan.json`
- `schedule_ir.json` 或 `dual_core_schedule_ir.json`
- `descriptor_ir.json`

主要输出：

- `schedule_diagnostics_report.json`

### Stage 6: 性能归因与瓶颈分类

回答的问题：

- 当前性能主要卡在哪些 phase、layer、node
- critical path 是什么
- 瓶颈更接近 compute、bandwidth、VMEM、sync，还是 fallback/unsupported

主要输入：

- `perf_summary_report.json`
- `prefill_evaluation_report.json`
- `decode_evaluation_report.json`
- `schedule_diagnostics_report.json`

主要输出：

- `performance_diagnostics_report.json`

### Stage 7: Roofline 与上界解释

回答的问题：

- 当前结构是在 compute ceiling 还是 bandwidth ceiling 下工作
- arithmetic intensity 和实际 achieved 点位于哪里
- 理论上还能向哪个上界靠近

主要输入：

- `resource_demand_report.json`
- `performance_diagnostics_report.json`
- `target_profile`

主要输出：

- `roofline_report.json`

### Stage 8: Timeline / Idle / Stall 诊断

回答的问题：

- 调度空闲和 bubble 在哪里
- idle 是依赖等待、DMA 等待、VMEM 容量、barrier，同步还是 fallback 膨胀造成的
- 哪些空闲可通过 overlap、tiling、resource rebalance 吸收

主要输入：

- `schedule_diagnostics_report.json`
- `performance_diagnostics_report.json`

主要输出：

- timeline sections in `schedule_diagnostics_report.json`
- diagnosis visualization timeline views

### Stage 9: 架构评估综合结论

回答的问题：

- 当前架构对该模型的总体适配度如何
- 最主要瓶颈是什么
- 不支持结构和高风险结构有哪些
- 优先建议改模型、改调度，还是改架构

主要输入：

- 前述全部 diagnosis reports
- 可选 `phase_d_compare_report.json` / `sweep_delta_report.json`

主要输出：

- `architecture_assessment_report.json`

## New Diagnosis Specs

为避免与现有 `SPEC-01` 到 `SPEC-19` 混用，本设计定义一个新的 follow-on spec family：

- `DIAG-01` Model Structure Report
- `DIAG-02` Operator Representation Report
- `DIAG-03` Resource Demand Report
- `DIAG-04` Support Matrix Report
- `DIAG-05` Schedule Diagnostics Report
- `DIAG-06` Performance Diagnostics Report
- `DIAG-07` Roofline Report
- `DIAG-08` Architecture Assessment Report
- `DIAG-09` Diagnosis Bundle + Workbench Surface

### DIAG-01: Model Structure Report

必须回答：

- layer/block/subgraph hierarchy
- structure type taxonomy
- structure-level inputs/outputs
- structure-to-node traceability

最低 contract 要求：

- `run_id`
- `graph_id`
- `scenario_name`
- `model_summary`
- `structures[]`
- `layers[]`
- `node_index[]`

### DIAG-02: Operator Representation Report

必须回答：

- 原始 graph node -> canonical op -> macro-op -> phase 的映射
- helper/fallback surface 标记
- 与 schedule block / descriptor 的 traceability anchor

最低 contract 要求：

- `node_mappings[]`
- `macro_groups[]`
- `phase_groups[]`
- `fallback_entries[]`
- `traceability_index`

### DIAG-03: Resource Demand Report

必须回答：

- compute demand
- IO demand
- storage demand
- dependency depth
- per-layer/per-structure demand summary

最低 contract 要求：

- `node_demands[]`
- `layer_demands[]`
- `structure_demands[]`
- `totals`
- `assumptions`

备注：

- 第一版允许使用 approximate compute-demand model
- 第一版 roofline 所需 FLOPs/MACs 不要求完全物理精确，但必须 machine-readable、可解释、可比较

### DIAG-04: Support Matrix Report

必须回答：

- `native`
- `constrained`
- `fallback`
- `unsupported`

最低 contract 要求：

- `node_support_entries[]`
- `layer_support_summary[]`
- `structure_support_summary[]`
- `reason_counts`
- `critical_gaps[]`

### DIAG-05: Schedule Diagnostics Report

必须回答：

- block start/end/span
- per-core lane occupancy
- idle spans
- wait/stall reason
- overlap opportunities

最低 contract 要求：

- `blocks[]` with `issue_slot`, `duration_slots`, `start_slot`, `end_slot`
- `core_lanes[]`
- `idle_spans[]`
- `stall_events[]`
- `critical_path_blocks[]`
- `resource_contention_summary`

### DIAG-06: Performance Diagnostics Report

必须回答：

- phase/layer/node hotspot
- fitted vs estimated divergence
- bottleneck taxonomy
- pressure drilldown

最低 contract 要求：

- `phase_breakdown`
- `layer_hotspots`
- `node_hotspots`
- `critical_path_summary`
- `bottleneck_classification`
- `bandwidth_diagnostics`
- `vmem_diagnostics`
- `support_gap_diagnostics`

### DIAG-07: Roofline Report

必须回答：

- ceiling definitions
- per-node/per-layer point placement
- dominant bound
- theoretical headroom

最低 contract 要求：

- `compute_ceiling`
- `bandwidth_ceilings[]`
- `node_points[]`
- `layer_points[]`
- `dominant_bound_summary`
- `headroom_summary`

### DIAG-08: Architecture Assessment Report

必须回答：

- 架构适配度结论
- top bottlenecks
- top unsupported / constrained structures
- 优先改进建议
- 结论信心与假设边界

最低 contract 要求：

- `overall_assessment`
- `top_bottlenecks[]`
- `top_support_gaps[]`
- `top_timeline_losses[]`
- `recommendations[]`
- `confidence_summary`

### DIAG-09: Diagnosis Bundle + Workbench Surface

必须回答：

- 如何把上述 diagnosis reports 打包给 static UI
- 如何提供从 summary 一路 drill down 到 structure、support、demand、schedule、roofline、timeline、assessment

最低 contract 要求：

- `diagnosis_bundle.json`
- diagnosis workbench manifest
- stable deep-link model
- per-panel JSON/SVG export

## Report Packaging Strategy

推荐输出目录：

- `reports/diagnosis/model_structure_report.json`
- `reports/diagnosis/operator_representation_report.json`
- `reports/diagnosis/resource_demand_report.json`
- `reports/diagnosis/support_matrix_report.json`
- `reports/diagnosis/schedule_diagnostics_report.json`
- `reports/diagnosis/performance_diagnostics_report.json`
- `reports/diagnosis/roofline_report.json`
- `reports/diagnosis/architecture_assessment_report.json`
- `reports/diagnosis_bundle.json`

选择独立子目录的原因：

- 与当前 baseline `reports/*.json` 解耦
- 不污染现有 closeout artifact surface
- 允许 diagnosis layer 独立演进与回归

## Data Lineage

新的 diagnosis layer 必须复用而不是绕过现有 artifact：

- `canonical_graph_ir.json` -> `model_structure_report`
- `bound_nig_ir.json` + `workload_decomposition_report.json` -> `operator_representation_report`
- `memory_plan.json` + normalized ops -> `resource_demand_report`
- `frontend_legality.json` + target profile -> `support_matrix_report`
- `schedule_ir.json` / `dual_core_schedule_ir.json` -> `schedule_diagnostics_report`
- `perf_summary_report.json` + prefill/decode report -> `performance_diagnostics_report`
- `resource_demand_report` + `performance_diagnostics_report` + target profile -> `roofline_report`
- 上述所有 report + compare report -> `architecture_assessment_report`

任何 diagnosis report 都不得破坏已有 artifact 的 canonical role。diagnosis layer 是下游消费者，不是上游替代物。

## New Workflow Surface

为了避免继续向 CLI 叠加大量零散命令，推荐新轨道使用三段式 workflow：

- `run-diagnosis-analysis --run-root ... [--sweep-root ...]`
  - 生成 diagnosis reports
- `run-diagnosis-packaging --run-root ... [--sweep-root ...]`
  - 生成 `diagnosis_bundle.json`
- `run-diagnosis-workbench --run-root ...`
  - 生成 static diagnosis workbench

内部 builder 可以按 report 分开，但面向用户的入口应该尽量少，避免复刻已有 Phase C/D/E 命令爆炸。

## Diagnosis Workbench Information Architecture

推荐的 diagnosis workbench 面板：

- `summary`
- `model-structure`
- `operator-representation`
- `support-matrix`
- `resource-demand`
- `schedule`
- `timeline`
- `performance`
- `roofline`
- `assessment`
- `compare`（当存在 `sweep_root`）

其中：

- `summary` 只做导航和全局结论，不再承载过多细节
- `support-matrix` 是“当前架构能不能接得住模型”的主入口
- `resource-demand + roofline` 负责解释理论上限
- `schedule + timeline` 负责解释空闲、串行化和 overlap
- `performance` 负责 phase/layer/node 级热点与瓶颈分类
- `assessment` 负责最终建议和行动排序

## Compatibility Rules

- 不修改现有 `PerfSummaryReport`、`PrefillEvaluationReport`、`DecodeEvaluationReport` 的既有语义
- diagnosis layer 允许复用现有字段，但不得把现有 report 变成 diagnosis report 的杂项容器
- diagnosis layer 可以新增 builder 和 bundle，但不应要求旧 workbench 退役
- 第一阶段 diagnosis workbench 可以与现有 workbench 并存

## Acceptance Criteria

本设计视为落地完成，至少需要满足下面这些验收条件：

- 对单个 run，可以从模型结构一路 drill down 到 assessment 结论
- 对至少一个真实模型 run，可以识别 unsupported/constrained/fallback/native 结构
- 对至少一个真实模型 run，可以展示真正的 timeline span 与 idle span
- 对至少一个真实模型 run，可以给出 roofline point 与 dominant bound
- 对至少一个真实 sweep，可以把 assessment 结论扩展到 baseline/candidate compare
- diagnosis layer 拥有独立 contract tests、builder tests、pipeline tests、smoke proof

## Milestone Roadmap

建议分四个里程碑推进：

- `D0` Baseline Freeze
  - 固化当前分支 closeout judgment
  - 合入本设计文档与实施计划
- `D1` Structural Diagnosis Foundation
  - `DIAG-01/02/03/04`
- `D2` Execution Diagnosis Foundation
  - `DIAG-05/06`
- `D3` Synthesis And Product Surface
  - `DIAG-07/08/09`

这四个里程碑的顺序不建议打乱。尤其不建议在 `D1/D2` 还未完成时，先做 diagnosis UI polish 或 roofline screenshot convenience。

## Risks

- 资源需求建模若过于理想化，会导致 roofline 成为装饰图而不是诊断图
- timeline 若只透传开始/结束、不显式建 stall taxonomy，依然无法解释空闲
- 如果 support matrix 只转述 legality issues，而不提升到 structure/layer 级别，就仍然无法回答“模型哪个结构当前架构不支持”
- 如果 assessment 直接从 existing summary 生成，缺少中间 diagnosis reports，将再次落回“结论先行、证据不足”的旧问题

## Final Design Decision

后续开发以“冻结当前基线 + 增加 diagnosis artifact layer + 增加 diagnosis workbench”为唯一主线解释。

新的开发默认顺序为：

1. 先建 diagnosis reports
2. 再建 diagnosis bundle
3. 最后建 diagnosis workbench

任何只补 summary 或只补 UI、却不补中间 diagnosis reports 的提案，都不应作为本轨道的默认实现方向。
