# RISC-V + NPU 评估编译器实施依赖、分期与状态

## 1. 状态说明

本路线图从 2026-03-07 开始采用显式状态标记：

- `done`
  - 当前仓库已经存在稳定契约、实现和验证，可作为下游阶段依赖。
- `in_progress`
  - 已有可运行骨架或部分实现，但还没有满足该 SPEC 的完整验收。
- `not_started`
  - 还没有稳定主线，或只有上游准备工作，没有形成可依赖交付物。

## 2. 当前阶段状态总览

| 阶段 | 包含 Spec | 状态 | 当前判断 |
| --- | --- | --- | --- |
| Phase A | SPEC-01, SPEC-02, SPEC-05, SPEC-06 | `done` | 契约、工件、架构模型、IR 栈都已经稳定落地。 |
| Phase B | SPEC-03, SPEC-04, SPEC-07 | `done` | import/decomposition/bound-NIG/report/smoke gate 已收口。 |
| Phase C | SPEC-08, SPEC-09, SPEC-10, SPEC-11, SPEC-12 | `in_progress` | `SPEC-08` 已进入 planner-closure 阶段，`SPEC-09` 当前 scope 已接受，`SPEC-10/11` helper-store 审计已收敛到 acceptance list，`SPEC-12` 的 `M2` stop-line 已冻结。 |
| Phase D | SPEC-13, SPEC-14, SPEC-15, SPEC-16 | `in_progress` | `SPEC-13` 已有 descriptor-driven estimator/workflow/CLI/smoke foundation，`SPEC-14` 已有 prefill top-level foundation，`SPEC-15` 已有 decode top-level foundation，`SPEC-16` 已有 sweep/delta workflow、CLI 和 smoke foundation。 |
| Phase E | SPEC-17, SPEC-18, SPEC-19 | `in_progress` | `SPEC-17` 已有大量 regression tests，`SPEC-18` 已有 visualization bundle workflow、CLI 和 smoke foundation，`SPEC-19` 已有 static workbench、cross-run catalog workflow、CLI、smoke foundation，以及 sweep/workspace discovery、catalog grouping、panel deep-link、workbench cross-links、saved-view/export controls、SVG snapshot export、catalog compare tray、baseline-pinned compare workspace、baseline/candidate role swap、compare scope toggle 和 shared summary-metric compare。 |

结论：

- Phase A 已完成。
- Phase B 已完成。
- 当前关键路径仍是 Phase C 收口，但 Phase D 已正式启动。

## 3. Spec 状态矩阵

| Spec | 名称 | Phase | 状态 | 当前证据 | 收口门槛 |
| --- | --- | --- | --- | --- | --- |
| SPEC-01 | 目标配置与场景配置系统 | A | `done` | 已有 `target/scenario profile` schema、loader、fixtures、diagnostics。 | 保持兼容；后续只允许增量扩展。 |
| SPEC-02 | 驱动入口与工件契约 | A | `done` | 已有 `validate-profile`、`init-run`、`run-frontend-analysis`、manifest/run-summary/run-root artifact。 | 保持 artifact contract 稳定。 |
| SPEC-03 | 模型导入与规范化图 | B | `done` | 已支持 `ONNX -> GraphIR -> canonical GraphIR`、`source_ref/audit_ref`、Gemma3 shape binding。 | 继续 harden，但不阻塞 Phase C。 |
| SPEC-04 | 工作负载拆解与宏算子识别 | B | `done` | 真实 Gemma3 主路径已能 lower 到 NIG，unsupported lowering nodes = `0`。 | 继续补 report/diagnostics，但不阻塞 Phase C。 |
| SPEC-05 | 架构语义模型 | A | `done` | 已有 capability model、constraint checker、query API、单核/双核 baseline target。 | 保持 target contract 稳定。 |
| SPEC-06 | IR 栈与 Lowering 契约 | A | `done` | 五层 IR schema、validator、traceability、JSON roundtrip 已完成。 | 保持 version/invariant 稳定。 |
| SPEC-07 | 量化/形状/布局绑定 | B | `done` | 已有 bound-NIG contract、quant/layout/memory-class/attention binding、binding report、四象限 smoke matrix。 | 保持 contract 稳定；后续只允许增量扩展。 |
| SPEC-08 | VMEM/KV/地址规划器 | C | `in_progress` | 已有 `MemoryPlanArtifact`、lifetime reuse、DDR/storage binding surface、fit-aware diagnostics、`SPEC-09` tile-planner 消费，以及 `SPEC-12` 对 `storage_binding_id/backing_store`、`SPEC-13` 对 `peak_bytes_by_backing_store`、`SPEC-14/15` 对 hottest-region `peak_bytes_by_backing_store`、`SPEC-18` 对 per-region `peak_bytes_by_backing_store` 的直接消费。 | 剩余是 planner closure、必要的剩余 capacity reasoning，以及只在有具体 consumer 证据时继续扩大 downstream reuse；不再缺 foundation。 |
| SPEC-09 | Tile 候选规划器 | C | `in_progress` | 已有 `TilingPlanArtifact`、storage-aware ranking、`run-tile-planning` workflow/CLI，以及被 `SPEC-10/11` 直接消费的稳定候选面。 | `M2` 现接受当前 GEMM-like / attention candidate surface + untiled-helper scheduling；只有出现具体 downstream failure 时才重新打开更广 coverage。 |
| SPEC-10 | 单核映射与调度器 | C | `in_progress` | 已有扩展后的 `ScheduleIR`、interval reservations、duration policy、phased reservations，以及 `RMSNORM/GEGLU/ELEM_ADD` helper-store 审计结果。 | 剩余是冻结 acceptance list 并持续供 `SPEC-12/13` 消费；不再默认继续扩宽搜索或无证据 specialization。 |
| SPEC-11 | 双核映射与调度器 | C | `in_progress` | 已有 dual-core `ScheduleIR` foundation、transfer/sync overlap、shared-resource contention，以及 `RMSNORM/GEGLU/ELEM_ADD` helper-store 审计结果。 | 剩余是冻结 acceptance list 并持续供 `SPEC-12/13` 消费；不再默认继续扩宽 repartition/search。 |
| SPEC-12 | 描述符生成与 ISA 覆盖映射 | C | `in_progress` | 已有稳定 `DescriptorIR` / packed stream artifact、summary-grade packed consumer proof、workbench packed-summary visibility，以及 structured `address_fields` 对 `storage_binding_id/backing_store` 的直接复用。 | `M2` stop-line 已冻结为 packed summary consumer proof + workbench summary visibility；per-record drilldown 和更重 ABI hardening 只在具体 consumer 出现时再开。 |
| SPEC-13 | 性能估算与瓶颈分析器 | D | `in_progress` | 已有 pseudo/fallback `AnalysisIR` estimator，以及 descriptor-driven `AnalysisIR` / `PerfSummaryReport`、run-root workflow、CLI 和四象限 smoke foundation。 | 仍缺更深 cycle model、bandwidth/VMEM breakdown，以及进入 `SPEC-14/15` 的 top-level eval report 收口。 |
| SPEC-14 | Prefill 评估流水线 | D | `in_progress` | 已有 `PrefillEvaluationReport` contract、prefill report builder、run-root workflow、CLI 和 `single-core/dual-core x prefill` smoke foundation，且 `memory_hotspot` 已直接带 hottest-region backing-store attribution。 | 仍缺 layer-level prefill 视图、单/双核对比输出和与 `SPEC-15/16` 的统一 top-level eval 收口。 |
| SPEC-15 | Decode 评估流水线 | D | `in_progress` | 已有 `DecodeEvaluationReport` contract、decode report builder、run-root workflow、CLI 和 `single-core/dual-core x decode` smoke foundation，且 `memory_hotspot` 已直接带 hottest-region backing-store attribution。 | 仍缺更细 token latency 拆解、`kv_len` sweep aggregation 和与 `SPEC-16/18` 的统一 top-level eval 收口。 |
| SPEC-16 | 假设扫描与差异对比引擎 | D | `in_progress` | 已有 `SweepSpec` / `SweepDeltaReport` contract、serial rerun workflow、CLI 和 Gemma3 sweep smoke foundation。 | 仍缺 layer-level diff、并行执行、缓存复用和更丰富的比较模式。 |
| SPEC-17 | 验证与回归框架 | E | `in_progress` | 当前已覆盖 profile、IR、frontend、pipeline 的大量 regression tests。 | 需扩展到 planner/descriptor/perf/report schema。 |
| SPEC-18 | 可视化数据服务 | E | `in_progress` | 已有 `VisualizationBundle` contract、run-root packaging workflow、CLI 和 Gemma3 visualization smoke foundation，且 `vmem_view.regions` 已直接带 per-region backing-store attribution。 | 仍缺 live query service、多运行 catalog、深层 drill-down 数据和更正式的 API/service 层。 |
| SPEC-19 | 可视化分析工作台 | E | `in_progress` | 已有 `VisualizationWorkbenchArtifact`、static workbench builder、`run-visualization-workbench` workflow/CLI、支持显式 `run_root` 与 `sweep_root/workspace_root` 发现的 cross-run catalog foundation，以及 graph/timeline 搜索过滤、timeline block drill-down、catalog search、scenario grouping/navigation、panel deep-link routing、workbench 内部的 descriptor/block/tensor cross-links、memory panel 的 per-region backing-store visibility，以及 saved-view link copy / active-panel JSON export / active-panel SVG export / catalog compare tray / baseline-pinned compare workspace / baseline-candidate role swap / same-scenario versus all-visible compare scope / shared summary-metric compare。 | 仍缺 richer screenshot workflow、更丰富的 workspace 导航，以及超出当前 shared summary-metric delta 的更深 compare modes。 |

## 4. 当前主路径

当前真实阶段不是“Phase B 收口前”，而是：

1. `Phase A = done`
2. `Phase B = done`
3. `Phase C = in_progress`
   - 当前真正的主门槛是 `M2`
   - 也就是把 `SPEC-08/09/10/11/12` 从 foundation 推到可稳定交付的闭环
4. `Phase D = in_progress`
   - `SPEC-13/14/15/16` 都已有 stable foundation
   - 但 foundation 不等于 Phase D 已收口
5. `Phase E = in_progress`
   - `SPEC-18/19` 已有 bundle/workbench/catalog/compare foundation
   - 但团队日常使用闭环还没有完成

### 当前优先顺序

1. 先继续收口 `M2`
   - `SPEC-08 -> SPEC-09 -> SPEC-10/11 -> SPEC-12`
2. 在不打断 `M2` 的前提下继续 harden `SPEC-13/14/15/16`
3. `SPEC-18/19` 继续做产品化 hardening，但不再开新的底层 contract
4. 避免误把 “foundation 已有” 当成 “phase 已完成”

### 正式进入下一阶段的门槛

| 进入阶段 | 必须满足 |
| --- | --- |
| 进入 Phase C | `SPEC-03 = done`、`SPEC-04 = done`、`SPEC-07 = done`，且 `Milestone M1 = done` |
| 进入 Phase D | `SPEC-08` 到 `SPEC-12` 全部 `done`，且单核/双核计划和 descriptor/ISA coverage 可稳定输出 |
| 进入 Phase E | `SPEC-13` 到 `SPEC-16` 全部 `done`，且 prefill/decode 全流程评估结果稳定 |

当前已经有 Phase D 与 Phase E 的 foundation，但项目主门槛仍然是 `Phase C / M2` 收口。

## 5. 依赖图

```mermaid
graph TD
    S01["SPEC-01 Profile / Scenario"]
    S02["SPEC-02 Driver / Artifact"]
    S03["SPEC-03 Model Import"]
    S04["SPEC-04 Workload Decomposer"]
    S05["SPEC-05 Architecture Model"]
    S06["SPEC-06 IR Contract"]
    S07["SPEC-07 Quant/Shape/Layout"]
    S08["SPEC-08 Memory / KV Planner"]
    S09["SPEC-09 Tile Planner"]
    S10["SPEC-10 Single-Core Scheduler"]
    S11["SPEC-11 Dual-Core Scheduler"]
    S12["SPEC-12 Descriptor / ISA Mapping"]
    S13["SPEC-13 Estimator / Bottleneck"]
    S14["SPEC-14 Prefill Pipeline"]
    S15["SPEC-15 Decode Pipeline"]
    S16["SPEC-16 Sweep / Delta"]
    S17["SPEC-17 Validation / Regression"]
    S18["SPEC-18 Visualization Data"]
    S19["SPEC-19 Visualization Workbench"]

    S01 --> S02
    S01 --> S05
    S02 --> S03
    S03 --> S04
    S03 --> S06
    S04 --> S06
    S05 --> S06
    S04 --> S07
    S05 --> S07
    S06 --> S07
    S05 --> S08
    S06 --> S08
    S07 --> S08
    S05 --> S09
    S07 --> S09
    S08 --> S09
    S08 --> S10
    S09 --> S10
    S08 --> S11
    S09 --> S11
    S06 --> S12
    S10 --> S12
    S11 --> S12
    S08 --> S13
    S09 --> S13
    S10 --> S13
    S11 --> S13
    S12 --> S13
    S02 --> S14
    S12 --> S14
    S13 --> S14
    S02 --> S15
    S12 --> S15
    S13 --> S15
    S01 --> S16
    S13 --> S16
    S14 --> S16
    S15 --> S16
    S06 --> S17
    S12 --> S17
    S13 --> S17
    S02 --> S18
    S13 --> S18
    S14 --> S18
    S15 --> S18
    S16 --> S18
    S18 --> S19
```

## 6. 里程碑状态

| 里程碑 | 对应完成条件 | 状态 | 当前判断 |
| --- | --- | --- | --- |
| M1 能看懂模型 | SPEC-01,02,03,04,05,06,07 | `done` | Phase B 已完成，语义层契约可稳定供 Phase C 复用。 |
| M2 能映射到硬件 | SPEC-08,09,10,11,12 | `in_progress` | `SPEC-09` scope 与 `SPEC-12` stop-line 已明确，`SPEC-10/11` helper-store 审计已完成，`SPEC-08` 也已有 tile/descriptor/perf 三条真实 downstream reuse；剩余主问题已收敛到 planner closure 与最终 acceptance evidence。 |
| M3 能做架构评估 | SPEC-13,14,15,16 | `in_progress` | `SPEC-13` 已有正式 perf foundation，`SPEC-14` 和 `SPEC-15` 已有 top-level foundation，`SPEC-16` 已有 sweep/delta foundation；同时 `SPEC-18/19` 已能消费这些结果，但 Phase D 仍缺更深的 estimator、layer-level compare 和更完整的 top-level report 闭环。 |
| M4 能被团队日常使用 | SPEC-17,18,19 | `in_progress` | `SPEC-18` 已有 visualization bundle foundation，`SPEC-19` 也已有带搜索/过滤/drill-down、cross-links、saved-view/export、SVG snapshot 的 static workbench，以及带 grouping/navigation、panel deep-link、compare tray、baseline-pinned compare workspace、baseline/candidate role swap、compare scope toggle 和 shared summary-metric compare 的发现式 catalog，但团队日常使用闭环仍缺更强的 workspace 导航、超出当前 shared summary-metric compare 的更深 compare 能力和 richer screenshot 能力。 |

## 7. 当前 To Do List

### P0：收口 `M2`

- `SPEC-08`
  - 把当前 memory planner foundation 收口成稳定 planner contract
  - descriptor / perf / top-level eval / visualization bundle 已开始直接消费 `storage_binding_id/backing_store`、`peak_bytes_by_backing_store` 与 backing-store attribution；继续只审计仍在重构 planner 已有信息的窄缺口
  - 仅在有具体证据时继续补窄范围 capacity reasoning
- `SPEC-09`
  - `M2` 现接受当前 GEMM-like / attention candidate surface
  - untiled-helper scheduling 现作为当前编译器范围内的 accepted closure policy
  - 只有在出现具体 scheduler / descriptor / perf 消费失败证据时，才重新打开更广的 macro coverage
- `SPEC-10/11`
  - 继续保持 evidence-driven closure pass，而不是回到宽泛探索
  - `RMSNORM.store` / `GEGLU.store` / `ELEM_ADD.store` 的 generic-store audit 已完成
  - 余下工作应聚焦最终 acceptance list，而不是继续无证据增加 specialization
- `SPEC-12`
  - `M2` stop-line 现冻结为 packed summary consumer proof + workbench summary visibility
  - 没有具体 consumer 要求前，不再默认追加 per-record drilldown
  - 后续仅保留窄范围 hardening，而不再作为唯一主线

### P1：继续收口 `M3`

- `SPEC-13`
  - deeper cycle model
  - 更清晰的 bandwidth / VMEM breakdown
- `SPEC-14/15`
  - layer-level breakdown
  - single-core / dual-core compare view
- `SPEC-16`
  - richer diff mode
  - multi-metric compare，而不只是 baseline summary

### P2：继续 harden `SPEC-19`

- richer compare drill-down beyond current shared summary-metric deltas
- richer workspace navigation
- richer screenshot/export workflow

## 8. 风险前置结论

### 8.1 当前最容易失控的点

- 把 Phase B done 误读成“完整编译器已经完成”。
- 把 `run-frontend-analysis` 误读成完整 prefill/decode 评估流水线。
- 因为有了 descriptor-driven perf foundation，就误判完整 prefill/decode eval pipeline 已经建立。

### 8.2 当前最值得优先固化的点

- `bound NIG -> memory planner` 的输入 contract
- `bound NIG -> tile planner` 的输入 contract
- Phase C 的 first-pass VMEM/KV planning 数据结构
- Gemma3 memory planner 四象限 smoke matrix
- Phase B handoff 和 roadmap 状态同步机制

## 9. 下一步方向建议

最合理的下一步不是再开新的 foundation，而是回到当前主门槛：

1. 优先继续 `Phase C / M2`
   - 首选方向：`SPEC-08` planner closure + downstream reuse
   - 原因：`SPEC-09` 的 scope 和 `SPEC-12` 的 stop-line 已明确，`SPEC-10/11` 也已从 broad exploration 收敛到 acceptance list，当前最真实的剩余收口面在 memory artifact 的最终消费闭环
2. 如果继续做 UI，只做 `SPEC-19` 的增量 hardening
   - 首选方向：workspace navigation + richer compare drill-down
   - 不建议再开新的 service/contract
3. 不建议现在把主要精力放回 frontend
   - `SPEC-03/04/07` 已是 `done`
   - 当前瓶颈不在模型导入，而在 mapping / descriptor / estimator 收口

对应 backlog 入口：

- `../plans/2026-03-07-phase-b-closure-backlog.md`
- `phase-b-semantic-handoff.md`
- `phase-c-memory-planner-handoff.md`
- `phase-c-tile-planner-handoff.md`
- `phase-c-single-core-scheduler-handoff.md`
- `phase-c-dual-core-scheduler-handoff.md`
- `phase-c-descriptor-handoff.md`
- `phase-d-performance-foundation-handoff.md`
- `phase-d-prefill-foundation-handoff.md`
- `phase-d-decode-foundation-handoff.md`
- `phase-e-visualization-workbench-handoff.md`
## 2026-03-07 SPEC-08 Checkpoint

- `SPEC-08` 褰撳墠浠嶆槸 `in_progress`锛屼絾宸茬粡涓嶅啀闃诲 `SPEC-09` 鍚姩銆?
- `MemoryPlanArtifact`銆並V address diagnostics 鍜?CLI / workflow contract 宸茬ǔ瀹氥€?
- Gemma3 鍥涜薄闄?memory-planning smoke 褰撳墠鍩虹嚎鏄?`overflow_regions = {}`锛屼笖 `unresolved_addresses = 0`銆?
- 鏈壒鏂板鐨?working-set heuristics 宸茬粡瑕嗙洊 `SDPA`銆乣RMSNORM_GEMM`銆乣RMSNORM`銆乣ELEM_ADD`銆乣KVLOAD`銆乣KVSTORE` 鍦ㄥ唴鐨勫叧閿儹鐐硅矾寰勩€?
- `SPEC-08` 鍓╀綑灏鹃」涓昏鏄?DDR binding銆佸弻鏍告暟鎹氦鎹㈣矾寰勮涔夊拰鏇寸郴缁熺殑 candidate search锛岃€屼笉鏄?Gemma3 baseline fit 闂銆?
## 2026-03-08 SPEC-12 Hardening Checkpoint

- `SPEC-12` remains `in_progress`, but the descriptor contract is now materially stronger.
- `DescriptorIR` now carries:
  - `packing_profile`
  - structured `address_fields`
  - the existing symbolic `addr_fields` for downstream compatibility
- Current new closure evidence:
  - descriptor validators now enforce stage-family/profile consistency
  - descriptor validators now enforce role-aligned symbolic versus structured address fields
  - builder now emits deterministic opcode-family packing profiles for compute / prepare / DMA / transfer stages
  - builder now emits deterministic structured address fields for compute, DMA, and transfer descriptors
  - descriptor-generation workflow and Phase C descriptor smoke remain green
- Remaining `SPEC-12` closure gap:
  - target-facing field packing specialization
  - final address-width / field-width encoding validation
  - final binary descriptor packer

## 2026-03-09 SPEC-10/11 Scheduler Fidelity Checkpoint

- `SPEC-09` storage-aware ranking is now consumed by both schedulers through `TileCandidate.rank`; schedulers no longer re-derive preference from `m_tile`.
- `SPEC-10` and `SPEC-11` now keep stable untiled helper macros in `ScheduleIR` instead of silently dropping them when no tile candidate exists.
- Current newly covered untiled scheduler surfaces include:
  - `RMSNORM`
  - `ELEM_ADD`
  - `GEGLU`
  - `ROPE`
  - `ATTENTION_MASK_PREP`
  - `EMBEDDING_LOOKUP`
  - `SHAPE_HELPER`
  - `LAYOUT_FALLBACK`
  - `ROPE_TABLE`
  - `KVLOAD`
  - `KVSTORE`
- Gemma3 single-core and dual-core prefill smoke now gate on the presence of untiled compute blocks such as `RMSNORM` or `ELEM_ADD`.
- This moves the remaining `M2` pressure away from "candidate fidelity" and toward:
  - richer scheduler overlap/resource modeling
  - broader macro scheduling coverage
  - final descriptor-facing closure across `SPEC-10/11/12`

## 2026-03-09 SPEC-10 Single-Core Overlap Checkpoint

- `SPEC-10` now has the first explicit occupancy metadata in `ScheduleIR`:
  - `depends_on`
  - `issue_slot`
  - `duration_slots`
- single-core scheduling now uses conservative earliest-issue placement instead of equating `order_key` with execution timing.
- the current overlap model is intentionally limited:
  - producer-consumer dependencies are explicit
  - resource-disjoint stages may overlap
  - there is still no global search, no alternative schedule exploration, and no dual-core overlap model yet
- this moves the next `M2` closure step toward:
  - dual-core overlap / transfer occupancy
  - broader resource-fidelity modeling
  - eventual descriptor/perf consumption of occupancy metadata
## 2026-03-08 SPEC-12 Target Packing Validation Checkpoint

- `SPEC-12` remains `in_progress`, but the descriptor contract is now close enough to a true target-facing ABI surface that the remaining gap is clearly “binary packer”, not “schema ambiguity”.
- New closure evidence:
  - `TargetProfile` now exposes `descriptor_encoding`
  - `packing_profile` now carries `layout_template` and deterministic `field_widths`
  - `address_fields` now carry `descriptor_field`, `encoded_width_bits`, and `uses_addr_ext`
  - builder now emits explicit coverage gaps when target address encoding cannot fit the descriptor view
- Remaining `SPEC-12` closure gap:
  - final 512-bit payload packer
  - stronger opcode-family specialization
  - target-specific low-level field placement validation
## 2026-03-08 SPEC-12 Binary Packer Foundation Checkpoint

- `SPEC-12` remains `in_progress`, but the descriptor pipeline now emits a stable packed payload artifact in addition to `DescriptorIR`.
- New closure evidence:
  - `run-descriptor-generation` now emits `artifacts/packed_descriptor_bundle.json`
  - every mapped descriptor now has deterministic `8 x 64-bit` words plus one concatenated `packed_hex`
  - packed payloads preserve field-level traceability through explicit bit-placement metadata
  - Phase C descriptor workflow, CLI, and smoke gates remain green with packed payload emission enabled
- Remaining `SPEC-12` closure gap:
  - target-specific byte-order and driver-stream ABI hardening
  - richer opcode-family-specific low-level field placement
  - deciding whether later phases consume packed payloads directly or stay on `DescriptorIR`

## 2026-03-08 Current Progress Checkpoint

### Current Phase Status

- `Phase A = done`
- `Phase B = done`
- `Phase C = in_progress`
- `Phase D = in_progress`
- `Phase E = in_progress`

### Current Milestone Status

- `M1 = done`
- `M2 = in_progress`
- `M3 = in_progress`
- `M4 = in_progress`

### Current SPEC Status

- `done`
  - `SPEC-01`
  - `SPEC-02`
  - `SPEC-03`
  - `SPEC-04`
  - `SPEC-05`
  - `SPEC-06`
  - `SPEC-07`
- `in_progress`
  - `SPEC-08`
  - `SPEC-09`
  - `SPEC-10`
  - `SPEC-11`
  - `SPEC-12`
  - `SPEC-13`
  - `SPEC-14`
  - `SPEC-15`
  - `SPEC-16`
  - `SPEC-17`
  - `SPEC-18`
  - `SPEC-19`

### Current Prioritized To-Do List

- `P0: close M2`
  - `SPEC-08`: phase-bucket lifetime reuse, DDR-backed binding realism, source-class-aware fit reasoning, and the formal storage-binding surface are now done; next is tighter planner closure and stronger downstream use of the memory artifact.
  - `SPEC-09`: storage-aware search/ranking is now done; next is broader macro coverage and stronger scheduler-facing tiling fidelity.
  - `SPEC-10/11`: broader macro coverage plus stronger resource-overlap and schedule-fidelity modeling; `GEGLU` mixed-engine specialization, vector-family duration specialization, and mixed-engine compute duration specialization are now done, and the next closure step is extending the same policy to more macro-stage families.
  - `SPEC-12`: richer opcode-family-specific specialization and stronger proof that packed descriptors can be treated as a stable downstream contract.
- `P1: keep closing M3`
  - `SPEC-13`: deeper cycle model and stronger bandwidth / VMEM breakdowns.
  - `SPEC-14/15`: layer-level breakdowns and stronger single-core versus dual-core comparison surfaces.
  - `SPEC-16`: richer diff modes and multi-metric compare instead of summary-only deltas.
- `P2: harden M4 surfaces`
  - `SPEC-17`: broaden regression gates around Phase C/Phase D closure.
  - `SPEC-18/19`: multi-metric compare, richer workspace navigation, and stronger export/screenshot workflows.

### Recommended Next Direction

- Primary recommendation: start an `M2` closure pass across `SPEC-08/09/10/11`, with `SPEC-12` moving to targeted hardening instead of remaining the sole focus.
  - Reason: after the stream/container ABI batch, `SPEC-12` no longer holds the sharpest unresolved contract gap in Phase C.
  - The highest-value next batch is:
    - `SPEC-08`: tighter planner closure and richer DDR/VMEM realism on top of the new phase-bucket lifetime reuse, DDR-backed binding semantics, and fit-attribution surface
    - `SPEC-09`: richer tile candidate search/ranking
    - `SPEC-10/11`: broader macro coverage and stronger resource-overlap modeling, now centered on extending macro-stage-specific specialization beyond the current mixed-engine compute and vector-duration set
- Secondary recommendation: keep `SPEC-12` for narrow follow-up work only.
  - Focus:
    - finer opcode-family placement specialization
    - stronger downstream-consumption proof for the packed stream

## 2026-03-09 SPEC-08 Lifetime Reuse Checkpoint

- New plan: `../plans/2026-03-09-spec-08-lifetime-reuse.md`
- `SPEC-08` remains `in_progress`, but the static memory planner has now crossed the first lifetime-reuse threshold.
- New closure evidence:
  - `MemoryPlanArtifact.allocations[*]` now carries `lifetime_bucket`
  - `region_summaries[*]` now carries `peak_lifetime_bucket`
  - `region_summaries[*]` now carries `peak_bytes_by_lifetime_bucket`
  - region peak accounting now uses static phase-bucket reuse instead of same-node raw-sum accounting
- This batch deliberately does not introduce:
  - schedule-aware liveness
  - a runtime allocator / free list
  - tile/schedule-coupled reuse
- The remaining `SPEC-08` closure gaps are now narrower:
  - stronger DDR / VMEM binding realism
  - planner closure
  - broader capacity reasoning on top of the new reuse model

## 2026-03-09 SPEC-08 DDR Binding Checkpoint

- New plan: `../plans/2026-03-09-spec-08-ddr-binding-realism.md`
- `SPEC-08` remains `in_progress`, but the memory planner no longer treats KV as the only explicit external-memory binding surface.
- New closure evidence:
  - `MemoryPlanArtifact.allocations[*]` now carries `backing_store`
  - `MemoryPlanArtifact.allocations[*]` now carries `backing_symbol`
  - staged `weight` and `quant` allocations now emit explicit `ddr-backed-staged` semantics
  - persistent `kv_cache` allocations now emit explicit `ddr-persistent` semantics
  - `address_diagnostics` now covers `weight` and `quant` in addition to `kv`
- This batch still deliberately does not introduce:
  - final target-specific address packing
  - schedule-coupled buffer binding
  - runtime allocation
- The remaining `SPEC-08` closure gaps are now:
  - tighter planner closure
  - richer DDR / VMEM realism
  - broader capacity reasoning above the current static staging model

## 2026-03-09 SPEC-08 Fit Reasoning Checkpoint

- New plan: `../plans/2026-03-09-spec-08-fit-reasoning.md`
- `SPEC-08` remains `in_progress`, but the planner can now explain pressure in terms of data classes instead of only total bytes.
- New closure evidence:
  - `RegionSummary` now carries `peak_bytes_by_memory_class`
  - `RegionSummary` now carries `peak_bytes_by_backing_store`
  - `VMEMFitDiagnostic` now carries `required_bytes_by_memory_class`
  - `VMEMFitDiagnostic` now carries `required_bytes_by_backing_store`
  - Phase C memory-planning workflow and smoke gates remain green with the stronger artifact
- This batch still deliberately does not introduce:
  - traffic/cycle estimation
  - schedule-coupled fit analysis
  - runtime allocation
- The remaining `SPEC-08` closure gaps are now narrower:
  - tighter planner closure
  - richer DDR / VMEM realism
  - broader capacity reasoning above the current static staging model

## 2026-03-09 SPEC-08 Storage Binding Checkpoint

- New plan: `../plans/2026-03-09-spec-08-storage-binding-surface.md`
- `SPEC-08` remains `in_progress`, but the memory artifact now exposes a formal source/storage binding surface instead of only opaque DDR symbol strings.
- New closure evidence:
  - `MemoryPlanArtifact` now carries `storage_bindings`
  - non-local `PlannedAllocation` records now carry `storage_binding_id`
  - `AddressBindingDiagnostic` now carries `storage_binding_id`
  - structured binding records now cover staged `weight`, staged `quant`, and persistent `kv`
  - Phase C memory-planning unit/workflow/smoke gates stay green with the stronger artifact
- This batch still deliberately does not introduce:
  - target-specific address encoding
  - binary transport/container layout
  - schedule-aware buffer reuse
- The remaining `SPEC-08` closure gaps are now:
  - tighter planner closure above the new storage-binding contract
  - stronger downstream consumption by `SPEC-09/12/13`
  - richer DDR / VMEM realism beyond the current symbolic storage view

## 2026-03-09 SPEC-09 Storage-Aware Search and Ranking Checkpoint

- New plan: `../plans/2026-03-09-spec-09-storage-aware-search-ranking.md`
- `SPEC-09` remains `in_progress`, but the tile planner has now crossed the first storage-aware ranking threshold.
- New closure evidence:
  - `TileCandidateResourceSummary` now carries:
    - `storage_binding_ids`
    - `storage_read_bytes_by_source_kind`
    - `storage_read_bytes_by_backing_store`
  - `TileCandidate` now carries:
    - `rank`
    - `ranking_reason`
  - staged `weight` / `quant` reads are no longer incorrectly scaled with `M_tile`
  - prefill GEMM-like nodes now emit a richer descending `M_tile` search set
  - Phase C tile-planning unit/workflow/smoke gates stay green with the stronger artifact
- This batch still deliberately does not introduce:
  - final scheduler policy
  - dual-core-aware tiling heuristics
  - traffic/cycle-accurate ranking
- The remaining `SPEC-09` closure gaps are now:
  - broader macro coverage outside GEMM-like and attention main paths
  - stronger dual-core-aware tiling tradeoffs
  - tighter coupling to `SPEC-10/11` schedule-fidelity work

## 2026-03-09 SPEC-11 Dual-Core Overlap Checkpoint

- New plan: `../plans/2026-03-09-spec-11-dual-core-overlap-foundation.md`
- `SPEC-11` remains `in_progress`, but the dual-core scheduler has now crossed the first explicit overlap/occupancy threshold.
- New closure evidence:
  - dual-core schedules now emit explicit `depends_on` instead of relying on append order alone
  - transfer blocks now depend on producer terminal blocks and gate consumer `prepare/compute` on cross-core paths
  - dual-core blocks now carry meaningful `issue_slot` timing beyond raw `order_key`
  - shared `DMA` and shared `Core Link` contention is now represented in scheduling decisions
  - Phase C dual-core unit/workflow/smoke gates remain green with the stronger schedule artifact
- This batch still deliberately does not introduce:
  - repartition search
  - cycle-calibrated duration modeling
  - cost-based `DMA` versus `Core Link` policy
- The remaining `SPEC-11` closure gaps are now:
  - broader macro coverage and more faithful stage lowering
  - stronger overlap/resource-fidelity above the current 1-slot occupancy model
  - tighter integration with `SPEC-10` and downstream descriptor/perf consumers

## 2026-03-09 SPEC-10/11 Duration Policy Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-duration-policy.md`
- `SPEC-10` / `SPEC-11` remain `in_progress`, but scheduling has now crossed the first non-unit-occupancy threshold.
- New closure evidence:
  - single-core and dual-core blocks now use a shared stage-duration policy
  - compute duration is now tile-shape-aware
  - `dma_in` / `store` duration is now byte-count / bandwidth-aware
  - transfer duration is now transport-bandwidth / sync-aware
  - descriptor `ctrl_fields` now propagate `issue_slot` and `duration_slots`
  - descriptor analysis now treats schedule duration as a lower bound on `estimated_cycles`
- This batch still deliberately does not introduce:
  - cycle-calibrated duration fitting
  - global critical-path accounting in perf totals
  - scheduler feedback into tile ranking
- The remaining `SPEC-10/11` closure gaps are now:
  - richer stage fidelity and macro-specific duration specialization
  - broader overlap/resource modeling beyond local stage occupancy
  - stronger integration with later Phase D comparison/report layers

## 2026-03-09 SPEC-11 Shared Sync Overlap Checkpoint

- New plan: `../plans/2026-03-09-spec-11-shared-sync-overlap.md`
- `SPEC-11` remains `in_progress`, but dual-core transfer timing has now crossed the first phased-reservation threshold.
- New closure evidence:
  - transfer blocks still remain single stable `ScheduleIR` blocks
  - internal scheduling now models transport occupancy separately from sync-tail occupancy
  - shared `Core Link` or shared `DMA` resources may be released before the transfer block fully ends when only sync tail remains
  - shared sync timing is now represented explicitly instead of being hidden inside transport contention only
  - Phase C dual-core unit/workflow/smoke gates remain green with the stronger timing model
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cost-based transport choice
  - repartition search
- The remaining `SPEC-11` closure gaps are now:
  - broader macro coverage and more faithful stage lowering
  - richer shared-resource modeling beyond transfer/sync decomposition
  - tighter integration with later descriptor/perf consumers

## 2026-03-09 SPEC-10/11 Phased Engine Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-phased-engine-reservations.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but mixed-engine compute occupancy has now crossed the first per-engine reservation threshold.
- New closure evidence:
  - scheduler internals now reserve resources by `(resource, start_offset, duration)` windows instead of only whole-block resource sets
  - `SDPA` / `SDPA_DECODE` compute now releases `MXU` before the trailing `VPU` tail completes
  - later `WDQ_GEMM` work may now reuse `MXU` during the `SDPA` VPU tail when dependencies allow it
  - the public `ScheduleIR` contract remains stable; the upgrade is internal timing fidelity only
  - Phase C single-core and dual-core scheduler unit/workflow/smoke gates remain green with the stronger occupancy model
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cycle-calibrated micro-engine timing
  - cost-based overlap search
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific resource specialization beyond the current mixed-engine compute set
  - richer shared-resource modeling across compute, DMA, transfer, and sync
  - tighter feedback of schedule fidelity into later descriptor/perf summaries

## 2026-03-09 SPEC-10/11 GEGLU Resource Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-geglu-resource-specialization.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but `GEGLU` has now crossed the first macro-specific mixed-engine scheduler threshold.
- New closure evidence:
  - single-core and dual-core schedulers now expose `GEGLU` compute as `["MXU", "VPU"]`
  - `GEGLU` compute now reuses the phased reservation helper instead of being modeled as a pure `VPU` compute block
  - Phase C single-core and dual-core unit/workflow/smoke gates remain green with the stronger `GEGLU` scheduler surface
- This batch still deliberately does not introduce:
  - new public `GEGLU` sub-stages
  - cycle-calibrated `GEGLU` duration fitting
  - a generic specialization policy for every untiled helper macro
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific specialization beyond `GEGLU` and the current mixed-engine compute set
  - richer shared-resource modeling across compute, DMA, transfer, and sync
  - tighter feedback of schedule fidelity into later descriptor/perf summaries

## 2026-03-09 SPEC-10/11 Vector Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-vector-duration-specialization.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but vector-family stage timing has now crossed the first macro-specific duration threshold.
- New closure evidence:
  - `RMSNORM`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, and `LAYOUT_FALLBACK` no longer all share one generic vector-stage duration formula
  - `GEGLU` prepare/compute now has a distinct cost surface from generic helper stages of the same shape
  - focused scheduler and perf-facing integration tests remain green with the stronger duration policy
- This batch still deliberately does not introduce:
  - cycle-calibrated duration fitting
  - layer-level timing attribution
  - new public schedule stages
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific specialization beyond the current mixed-engine and vector-duration set
  - richer shared-resource modeling across compute, DMA, transfer, and sync
  - tighter feedback of schedule fidelity into later descriptor/perf summaries

## 2026-03-09 SPEC-10/11 Mixed-Engine Duration Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but mixed-engine compute timing has now crossed the first macro-specific duration threshold.
- New closure evidence:
  - `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE` no longer share one plain GEMM compute duration formula
  - compute duration now reflects explicit non-MXU overhead on top of base GEMM cycles
  - focused scheduler and perf-facing integration tests remain green with the stronger mixed-engine compute policy
- This batch still deliberately does not introduce:
  - cycle-calibrated compute fitting
  - layer-level timing attribution
  - new public schedule stages
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific specialization beyond the current mixed-engine compute and vector-duration set
  - richer shared-resource modeling across compute, DMA, transfer, and sync
  - tighter feedback of schedule fidelity into later descriptor/perf summaries

## 2026-03-09 SPEC-10/11 Interval Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-interval-resource-reservations.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but scheduler overlap fidelity has now crossed the first true interval-reservation threshold.
- New closure evidence:
  - scheduler internals now resolve resource conflicts against sorted `(start, end)` windows instead of scalar `available_at` timestamps
  - a later `VPU` helper block may now issue before a delayed `SDPA` `VPU` tail starts when dependencies allow it
  - single-core and dual-core ready queues now use lazy earliest-issue heaps instead of rescanning the full ready set each scheduling step
  - public `ScheduleIR` blocks remain unchanged; this is internal timing/runtime hardening only
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific resource specialization beyond the current mixed-engine and vector families
  - richer shared-resource fidelity across compute, DMA, transfer, and sync
  - tighter feedback of schedule makespan into later Phase D comparison and report layers

## 2026-03-09 SPEC-10/11 WDQ Prefix Specialization Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-wdq-prefix-specialization.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but `WDQ_GEMM` compute timing has now crossed the first macro-specific prefix/body reservation threshold.
- New closure evidence:
  - `WDQ_GEMM` compute no longer reserves `MXU` from `issue_slot = 0`
  - `WDQ_GEMM` now exposes an explicit WDQ-only prefix before matrix compute occupies `MXU`
  - single-core and dual-core schedulers can now exploit that prefix via the interval reservation engine
  - public `ScheduleIR` artifacts stay unchanged; this is internal timing-fidelity hardening only
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific specialization beyond `WDQ_GEMM`, `GEGLU`, and the current mixed-engine/vector families
  - richer shared-resource fidelity across compute, DMA, transfer, and sync
  - tighter feedback of schedule makespan into later Phase D comparison and report layers

## 2026-03-09 SPEC-10/11 Overhead-Aligned Reservation Checkpoint

- New plan: `../plans/2026-03-09-spec-10-11-overhead-aligned-reservations.md`
- `SPEC-10` and `SPEC-11` remain `in_progress`, but mixed-engine reservation windows have now crossed the first duration-aligned specialization threshold.
- New closure evidence:
  - `RMSNORM_GEMM` compute now reserves `VPU` for the true norm-prefix window and delays `MXU` occupancy until that prefix completes
  - `SDPA` / `SDPA_DECODE` compute now reserve `MXU` for the true GEMM body and reserve `VPU` only for the true attention-tail window
  - single-core and dual-core schedulers now precompute reservation windows per block instead of recomputing coarse resource splits during issue-time conflict checks
  - focused scheduler unit tests, single/dual scheduling workflows, Phase C single/dual smoke, and `test_performance_estimation_workflow.py` all remain green with the stronger timing model
- This batch still deliberately does not introduce:
  - new public schedule stages
  - cycle-calibrated micro-engine timing
  - cost-based overlap search
- The remaining `SPEC-10/11` closure gaps are now:
  - broader macro-stage-specific specialization beyond the current mixed-engine/vector set
  - richer shared-resource fidelity across compute, DMA, transfer, and sync
  - tighter feedback of schedule fidelity into later Phase D comparison and report layers

## 2026-03-09 SPEC-13 Schedule Makespan Summary Checkpoint

- New plan: `../plans/2026-03-09-spec-13-schedule-makespan-summary.md`
- `SPEC-13` remains `in_progress`, but `PerfSummaryReport` now crosses the first schedule-aware summary threshold.
- New closure evidence:
  - `PerfSummaryReport` now carries `schedule_makespan_slots`
  - `PerfSummaryReport` now carries `per_core_makespan_slots`
  - `PerfSummaryReport` now carries `schedule_transfer_slots`
  - `run-performance-estimation` now consumes the resolved schedule artifact when building the summary report
  - Phase D perf workflow and Gemma3 perf smoke gates remain green with the stronger summary contract
- This batch still deliberately does not introduce:
  - overlap-aware global critical-path accounting in `totals`
  - schedule-derived bandwidth accounting
  - layer- or phase-level timing aggregation
- The remaining `SPEC-13` closure gaps are now:
  - deeper cycle and bandwidth modeling above the current descriptor estimator
  - stronger VMEM / region breakdowns
  - richer aggregation inputs for `SPEC-14/15/16`

## 2026-03-08 SPEC-12 Byte Order and Driver ABI Checkpoint

- `SPEC-12` remains `in_progress`, but the descriptor pipeline has now crossed the byte-order / stream-ABI threshold that was still open after `674b939`.
- New closure evidence:
  - target profiles now carry descriptor `word_order` and `byte_order` defaults
  - builder-emitted packing profiles now carry explicit `field_layout`
  - packed descriptor records now expose both descriptor-view payloads and target-stream payloads:
    - `word_hex`
    - `packed_hex`
    - `stream_hex`
    - `word_order`
    - `byte_order`
  - descriptor-generation workflow, CLI, and Phase C descriptor smoke stay green with the stronger packed artifact
- Remaining `SPEC-12` closure gap:
  - richer opcode-family-specific field placement validation
  - final transport/container ABI above the current packed stream
  - proof that later Phase C / Phase D consumers can treat packed descriptors as a stable contract instead of reconstructing layout assumptions

## 2026-03-08 SPEC-12 Container ABI Checkpoint

- `SPEC-12` remains `in_progress`, but the packed descriptor artifact has now crossed from per-record payload emission to a stable aligned-stream contract.
- New closure evidence:
  - target profiles now carry `stream_container` and `record_alignment_bytes`
  - packed bundles now carry:
    - `container_format`
    - `record_alignment_bytes`
    - `stream_total_bytes`
    - `stream_hex`
  - packed records now carry:
    - `record_index`
    - `stream_offset_bytes`
    - `stream_size_bytes`
  - `DescriptorPackingProfile` now enforces layout-template-specific placement rules for compute, DMA, transfer, and prepare families
- Remaining `SPEC-12` closure gap:
  - richer opcode-family specialization beyond the current layout-template rules
  - stronger proof that downstream phases can consume the packed stream directly as a stable ABI surface

## 2026-03-09 Current Progress Checkpoint

### Current phase and milestone status

- `Phase A = done`
- `Phase B = done`
- `Phase C = in_progress`
- `Phase D = in_progress`
- `Phase E = in_progress`
- `M1 = done`
- `M2 = in_progress`
- `M3 = in_progress`
- `M4 = in_progress`

### Current SPEC status

- `done`
  - `SPEC-01`
  - `SPEC-02`
  - `SPEC-03`
  - `SPEC-04`
  - `SPEC-05`
  - `SPEC-06`
  - `SPEC-07`
- `in_progress`
  - `SPEC-08`
  - `SPEC-09`
  - `SPEC-10`
  - `SPEC-11`
  - `SPEC-12`
  - `SPEC-13`
  - `SPEC-14`
  - `SPEC-15`
  - `SPEC-16`
  - `SPEC-17`
  - `SPEC-18`
  - `SPEC-19`

### Updated P0 / P1 / P2 todo list

- `P0: close M2`
  - `SPEC-08`
    - planner closure on top of `storage_bindings`
    - more realistic DDR / VMEM / reuse reasoning for downstream consumers
  - `SPEC-09`
    - richer tile candidate search and ranking beyond the current GEMM-like focus
    - stronger consumption of storage-aware pressure and downstream schedule needs
  - `SPEC-10/11`
    - macro-stage-specific shared-resource specialization beyond the current mixed-engine compute set
    - stronger prepare / store / DMA overlap fidelity
    - more stable schedule closure for downstream descriptor and perf consumers
  - `SPEC-12`
    - narrower hardening only
    - richer opcode-family field placement validation
    - stronger downstream proof for packed stream / transport ABI stability
- `P1: close M3`
  - `SPEC-13`
    - deeper cycle model and richer bandwidth / VMEM breakdown
  - `SPEC-14/15`
    - layer-level breakdown and stronger single-core versus dual-core compare surfaces
  - `SPEC-16`
    - richer diff modes and multi-metric compare
- `P2: harden M4`
  - `SPEC-17`
    - broader regression gates around Phase C / Phase D closure
  - `SPEC-18/19`
    - multi-metric compare
    - richer workspace navigation
    - stronger export / screenshot workflow

### Updated next-direction recommendation

- Primary recommendation: keep closing `M2`, but move the center of gravity to `SPEC-10/11` schedule-fidelity hardening instead of reopening frontend or over-focusing `SPEC-12`.
- Recommended next batch:
  - extend macro-stage-specific shared-resource specialization to the prepare / store / DMA neighborhood
  - keep feeding the resulting stronger makespan signal into `SPEC-13`
- Rationale:
  - `SPEC-08` already has lifetime reuse, DDR-backed binding realism, fit reasoning, and structured storage bindings
  - `SPEC-09` already exposes storage-aware ranking and is good enough as scheduler input
  - `SPEC-10/11` now have interval reservations, duration policy, phased reservations, prefix/tail specialization, and overhead-aligned windows
  - the sharpest remaining `M2` gap is therefore schedule fidelity, not another new foundation layer

## 2026-03-09 SPEC-10/11 DMA Window Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-dma-window-specialization.md`
- `SPEC-10/11` now extend phased reservation modeling into the DMA neighborhood instead of only mixed-engine compute.
- new closure evidence:
  - `WDQ_GEMM.dma_in` now separates `DMA` transport from a short `WDQ` staging tail
  - `KVSTORE.store` now separates a `VPU` pack/layout prefix from the later shared-`DMA` writeback window
  - single-core and dual-core interval schedulers can now place later independent DMA work into those non-DMA windows when dependencies allow it
- what this closes:
  - stronger `prepare / store / DMA` overlap fidelity inside `SPEC-10/11`
  - a more credible path for feeding schedule makespan into `SPEC-13`
- what still remains for `M2`:
  - broader macro-stage-specific specialization beyond the current targeted cases
  - richer tile search/ranking in `SPEC-09`
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 KVLOAD DMA Tail Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-kvload-dma-tail-specialization.md`
- `SPEC-10/11` now extend phased DMA-neighborhood modeling into `KVLOAD` instead of treating untiled KV reads as a single shared-`DMA` slab.
- new closure evidence:
  - `KVLOAD.dma_in` now separates shared-`DMA` transport from a later core-local `VPU` unpack/layout tail
  - single-core interval scheduling may now place later pure-`DMA` work into that non-`DMA` tail window
  - dual-core interval scheduling preserves the same overlap under shared-`DMA` contention across cores
- what this closes:
  - broader macro-stage-specific specialization inside the `prepare / store / DMA` neighborhood
  - a stronger `SPEC-10/11` makespan signal for later `SPEC-13` consumers on decode-heavy paths
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused `compute` / `DMA` cases
  - more stable workflow-scale closure for downstream descriptor and perf consumers
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 SDPA Decode Phased Release Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-sdpa-decode-phased-release.md`
- `SPEC-10/11` now refine `SDPA_DECODE.compute` beyond the first `DMA + VPU` resource-set correction by releasing each engine on its true modeled sub-window.
- new closure evidence:
  - decode compute still reports one stable `ScheduleIR` block, but internal reservations no longer pin `VPU` and `DMA` to the same full-block duration
  - single-core scheduling may now place later same-core `VPU` helper work into the decode `DMA` tail once the shorter `VPU` sub-window ends
  - dual-core scheduling preserves that same core-local `VPU` reuse while respecting cross-core dependency and transfer timing
- what this closes:
  - stronger decode-heavy overlap fidelity inside the `SPEC-10/11` compute / DMA boundary
  - a more credible schedule signal for later `SPEC-13` occupancy and makespan consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine cases
  - more stable workflow-scale closure for downstream descriptor and perf consumers
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 Workflow Minimal Run-Root Fixture Checkpoint

- plan doc: `../plans/2026-03-10-workflow-minimal-run-root-fixtures.md`
- workflow-shell validation for `performance`, `prefill`, and `decode` no longer rebuilds the full upstream pipeline for every case.
- new closure evidence:
  - unit workflow tests now use minimal legal descriptor-stage and performance-stage run roots written directly in `tests/unit/pipeline/conftest.py`
  - `test_performance_estimation_workflow.py`, `test_prefill_evaluation_workflow.py`, and `test_decode_evaluation_workflow.py` dropped from the previous multi-minute setup path to `6 passed in 0.43s`
  - the broader workflow regression slice now completes in `11 passed in 265.17s`, with runtime dominated by the actual scheduling workflow tests instead of downstream shell setup
- what this closes:
  - a meaningful part of the workflow-scale validation bottleneck that was slowing `M2` iteration on `SPEC-10/11`
  - faster local evidence for downstream perf/prefill/decode consumers without weakening product-path coverage inside those workflow entrypoints
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine cases
  - additional workflow-cost reduction for the still-heavy scheduling regression path
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 Scheduling Workflow Minimal Tile Fixture Checkpoint

- plan doc: `../plans/2026-03-10-scheduling-workflow-minimal-tile-fixtures.md`
- scheduling workflow validation for `single-core` and `dual-core` no longer rebuilds frontend plus planner state up to tile-stage for each case.
- new closure evidence:
  - unit workflow tests now use a new minimal tile-stage run-root fixture that writes a tiny bound-NIG plus real `memory_plan` and `tiling_plan` artifacts in `tests/unit/pipeline/conftest.py`
  - `test_single_core_scheduling_workflow.py` and `test_dual_core_scheduling_workflow.py` dropped from `2 passed in 231.24s` to `2 passed in 0.37s`
  - the broader workflow regression slice now completes in `11 passed in 16.90s`; remaining slowest calls are the real `frontend`, `memory`, and `tile` entrypoints at roughly five to six seconds each
- what this closes:
  - the last major unit-workflow setup bottleneck blocking quick `M2` iteration on `SPEC-10/11`
  - a much cheaper local gate for schedule-fidelity hardening before escalating to smoke coverage
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine cases
  - broader Phase C closure on real schedule fidelity rather than more workflow-shell fixture work
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Embedding DMA Tail Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-embedding-dma-tail-specialization.md`
- `SPEC-10/11` now extend phased DMA-neighborhood modeling into `EMBEDDING_LOOKUP` instead of treating embedding staging as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `EMBEDDING_LOOKUP.dma_in` now separates shared-`DMA` transport from a later core-local `VPU` unpack/scale tail
  - single-core interval scheduling may now place later pure-`DMA` work into that non-`DMA` tail window
  - dual-core interval scheduling preserves the same overlap under shared-`DMA` contention across cores
- what this closes:
  - broader macro-stage-specific specialization inside the `prepare / store / DMA` neighborhood
  - a stronger `SPEC-10/11` schedule signal on embedding-heavy prefill paths
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine / embedding cases
  - broader Phase C closure on real schedule fidelity rather than more workflow-shell fixture work
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 RoPE Table DMA Tail Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-rope-table-dma-tail-specialization.md`
- `SPEC-10/11` now refine `ROPE_TABLE.dma_in` from a monolithic shared-`DMA` slab into one block with phased `DMA` transport followed by a core-local `VPU` table-generation tail.
- new closure evidence:
  - `ROPE_TABLE.dma_in` duration and reservations now expose `DMA -> VPU` sub-windows while keeping the public `ScheduleIR` block shape unchanged
  - single-core interval scheduling may now place later pure-`DMA` work into the non-`DMA` tail window once rope-table input transport completes
  - dual-core scheduling preserves that same shared-`DMA` reuse across cores without reopening stage lowering or descriptor contracts
- what this closes:
  - broader macro-stage-specific specialization across pseudo/fallback helper surfaces inside the `prepare / store / DMA` neighborhood
  - a stronger `SPEC-10/11` timing signal on metadata-heavy rope-table decode paths
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine / embedding / rope-table cases
  - broader Phase C closure on real schedule fidelity rather than more workflow-shell fixture work
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Attention Mask Prep Complexity Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-attention-mask-prep-complexity-specialization.md`
- `SPEC-10/11` now refine `ATTENTION_MASK_PREP` timing so scheduler duration no longer treats all mask-helper variants as one fixed-cost helper class.
- new closure evidence:
  - `ATTENTION_MASK_PREP.compute` now scales with frontend-preserved `original_op_kind` complexity instead of using one shared factor for `Add`, `Trilu`, and other mask-prep variants
  - single-core scheduling now delays later same-core `VPU` work more behind heavier mask-prep variants than behind lighter ones
  - dual-core scheduling preserves that same core-local `VPU` delay signal after core assignment, without changing stage lowering or public `ScheduleIR`
- what this closes:
  - broader macro-stage-specific specialization across pseudo/fallback helper surfaces beyond the current `DMA/store`-only hardening wave
  - a stronger `SPEC-10/11` timing signal on mask-heavy prefill paths where frontend already preserves helper semantics
- what still remains for `M2`:
  - more macro-specific specialization beyond the current focused decode / KV / mixed-engine / embedding / rope-table / mask-prep cases
  - broader Phase C closure on real schedule fidelity rather than more workflow-shell fixture work
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Layout Fallback Characterization Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-layout-fallback-characterization.md`
- `SPEC-10/11` now have direct planning regression evidence that `LAYOUT_FALLBACK` already exposes the expected `DMA -> VPU -> DMA` execution shape through existing stage boundaries.
- new closure evidence:
  - `LAYOUT_FALLBACK.dma_in` remains a narrow shared-`DMA` block instead of expanding into a whole-op reservation
  - `LAYOUT_FALLBACK.prepare` and `LAYOUT_FALLBACK.compute` remain `VPU`-only helper stages, preserving the middle compute window for overlap characterization
  - later independent `DMA` work can start as soon as `LAYOUT_FALLBACK.dma_in` completes, before `LAYOUT_FALLBACK.store`, under both single-core and dual-core scheduling
- what this closes:
  - a planning blind spot around transpose-like fallback helpers that previously had no direct regression coverage
  - ambiguity about whether `LAYOUT_FALLBACK` still needed a new phase-level specialization inside the current `M2` hardening wave
- what this means for `M2`:
  - this batch closed a coverage gap, not a new product-path fidelity gap
  - the next `SPEC-10/11` target should move to the next helper or store case with sharper evidence of missing schedule fidelity, rather than more generic characterization-only work

## 2026-03-10 SPEC-10/11 SDPA Store Prefix Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-sdpa-store-prefix-specialization.md`
- `SPEC-10/11` now refine `SDPA` and `SDPA_DECODE` output writeback so the fused attention macro no longer appears as one monolithic shared-`DMA` store window.
- new closure evidence:
  - `SDPA.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window, while keeping the public stage graph unchanged
  - `SDPA_DECODE.store` preserves the same phased writeback shape for decode output blocks
  - single-core and dual-core interval reservation logic may now co-issue later pure-`DMA` work at store-block issue time when the `DMA` sub-window has not started yet
- what this closes:
  - another output-side overlap-fidelity gap in the `prepare / store / DMA` neighborhood
  - a stronger makespan signal for downstream descriptor and perf consumers on attention-heavy paths
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Layout Fallback Store Prefix Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-layout-fallback-store-prefix-specialization.md`
- `SPEC-10/11` now refine `LAYOUT_FALLBACK.store` so transpose-like fallback output writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `LAYOUT_FALLBACK.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while keeping the public stage graph unchanged
  - single-core and dual-core interval reservation logic may now co-issue later pure-`DMA` work at layout-store issue time when the `DMA` sub-window has not started yet
  - the earlier `LAYOUT_FALLBACK` characterization coverage remains valid after updating store-side fidelity, so this batch upgrades a previously covered helper surface into a sharper behavior model
- what this closes:
  - another transpose-like helper writeback gap in the `prepare / store / DMA` neighborhood
  - a stronger overlap signal on fallback/helper-heavy paths for downstream descriptor and perf consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 ROPE Store Prefix Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-rope-store-prefix-specialization.md`
- `SPEC-10/11` now refine `ROPE.store` so fused rotary output writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `ROPE.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while keeping the public stage graph unchanged
  - single-core and dual-core interval reservation logic may now co-issue later pure-`DMA` work at rope-store issue time when the `DMA` sub-window has not started yet
  - this closes a real helper-path fidelity gap with explicit frontend evidence from the fused `Slice/Concat`-based rotary pattern, not only a coverage gap
- what this closes:
  - another helper writeback gap in the `prepare / store / DMA` neighborhood
  - a stronger overlap signal on rotary-heavy attention paths for downstream descriptor and perf consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store / rope-store cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Embedding Store Prefix Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-embedding-store-prefix-specialization.md`
- `SPEC-10/11` now refine `EMBEDDING_LOOKUP.store` so fused embedding output writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `EMBEDDING_LOOKUP.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while keeping the public stage graph unchanged
  - single-core and dual-core interval reservation logic may now co-issue later pure-`DMA` work at embedding-store issue time when the `DMA` sub-window has not started yet
  - this closes a helper-path fidelity gap on top of the earlier `EMBEDDING_LOOKUP.dma_in` tail specialization, extending the same surface from input-side fidelity to output-side fidelity
- what this closes:
  - another helper writeback gap in the `prepare / store / DMA` neighborhood
  - a stronger overlap signal on embedding-heavy prefill paths for downstream descriptor and perf consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store / rope-store / embedding-store cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 GEGLU Compute Phasing Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-geglu-compute-phasing.md`
- `SPEC-10/11` now refine `GEGLU.compute` so fused GeGLU execution no longer appears as only one long `MXU` slab followed by a terminal `VPU` tail.
- new closure evidence:
  - `GEGLU.compute` now exposes a short `VPU` prefix, a longer `MXU` body, and a later `VPU` tail while keeping the public stage graph unchanged
  - interval reservation logic may now start later pure-`VPU` work at the prefix release boundary instead of pessimistically waiting for the full GeGLU block to end
  - this batch started from a failed full-schedule test hypothesis, then corrected the proof surface to reservation-timeline level once the root cause showed the helper was simply being scheduled before the GeGLU block
- what this closes:
  - another mixed-engine overlap-fidelity gap in the `prepare / compute / store` neighborhood
  - a stronger same-core `VPU` reuse signal on feed-forward helper paths for downstream descriptor and perf consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store / rope-store / embedding-store / geglu-compute cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 SDPA Compute Phasing Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-sdpa-compute-phasing.md`
- `SPEC-10/11` now refine `SDPA.compute` so fused attention compute no longer appears as only one long `MXU` slab followed by a terminal `VPU` tail.
- new closure evidence:
  - `SDPA.compute` now exposes a front `VPU` prefix, a longer `MXU` body, and a later `VPU` tail while keeping duration stable and the public stage graph unchanged
  - interval reservation logic may now issue later pure-`VPU` work at the prefix release boundary instead of pessimistically waiting for the full SDPA block to end
  - the stronger phasing is grounded in existing frontend canonicalization evidence for pre-matmul and post-matmul vector-side work around fused attention, not only a synthetic timing split
- what this closes:
  - another mixed-engine overlap-fidelity gap on the main prefill attention path
  - a stronger same-core `VPU` reuse signal for downstream descriptor and perf consumers on attention-heavy schedules
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store / rope-store / embedding-store / geglu-compute / sdpa-compute cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-10/11 Attention Mask Store Prefix Checkpoint

- plan doc: `../plans/2026-03-10-spec-10-11-attention-mask-store-prefix-specialization.md`
- `SPEC-10/11` now refine `ATTENTION_MASK_PREP.store` so mask-prep writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `ATTENTION_MASK_PREP.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while keeping the public stage graph unchanged
  - heavier `original_op_kind` values such as `Trilu` now expose a larger writeback-side prefix than lighter cases such as `Add`
  - interval reservation logic may now co-issue later pure-`DMA` work at mask-store issue time once the `DMA` sub-window has not started yet
- what this closes:
  - another helper writeback gap in the `prepare / store / DMA` neighborhood
  - a stronger overlap signal on attention-mask-heavy prefill paths for downstream descriptor and perf consumers
- what still remains for `M2`:
  - more macro-specific specialization beyond the current decode / KV / embedding / rope-table / mask-prep / attention-store / layout-store / rope-store / embedding-store / geglu-compute / sdpa-compute / attention-mask-store cases
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-12 Address Field Order Stability Checkpoint

- plan doc: `../plans/2026-03-10-spec-12-address-field-order-stability.md`
- `SPEC-12` now canonicalizes descriptor address-field placement by stage-aware role order instead of allowing packed layout to drift with `memory_plan.allocations` insertion order.
- new closure evidence:
  - compute-stage descriptor address roles now serialize in a stable semantic order such as `input -> weight -> scale -> zp -> output` even when allocation lists are reversed
  - `DescriptorPackingProfile.field_layout`, compute payload field placements, and top-level packed `stream_hex` now remain identical under allocation-list permutation
  - descriptor-generation plus downstream performance / prefill / decode workflow gates remain green with the stronger deterministic builder contract
- what this closes:
  - a real packed-stream / transport ABI stability gap inside `SPEC-12`
  - a source of nondeterminism that could have made downstream consumers report descriptor diffs without any schedule or memory-semantic change
- what still remains for `M2`:
  - more opcode-family and field-placement validation beyond the current deterministic ordering guarantee
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-10 SPEC-12 DMA / Transfer Layout Specialization Checkpoint

- plan doc: `../plans/2026-03-10-spec-12-dma-transfer-layout-specialization.md`
- `SPEC-12` now specializes DMA and transfer packing profiles by real opcode family and transport kind instead of collapsing them into generic `dma_stream` / `transfer_copy` naming.
- new closure evidence:
  - `dma_in` and `store` descriptors now emit `dma_load_v1` / `dma_store_v1` templates with matching `dma_load` / `dma_store` opcode families
  - transfer descriptors now emit `core_link_transfer_v1` or `dma_transfer_v1` according to `transfer_kind`
  - `DescriptorPackingProfile` validation now rejects mismatched specialized family/template pairs instead of letting transport ABI meaning drift silently
  - descriptor builder/packer, IR validator, analysis consumers, and descriptor/perf/prefill/decode workflows remain green with the stronger transport-aware contract
- what this closes:
  - a real opcode-family / layout-template ambiguity inside `SPEC-12`
  - one more downstream ABI inference gap for packed-stream consumers that previously had to treat generic DMA / transfer templates as overloaded shells
- what still remains for `M2`:
  - further field-placement proof above the current specialized template names, especially where later consumers may want to trust packed descriptors without symbolic reconstruction
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 SPEC-12 Visualization Packed Consumer Proof Checkpoint

- plan doc: `../plans/2026-03-11-spec-12-visualization-packed-consumer-proof.md`
- `SPEC-12` now has a real downstream packed consumer: visualization packaging reads `packed_descriptor_bundle.json` and emits packed-summary evidence into `VisualizationBundle.coverage_view`.
- new closure evidence:
  - visualization bundles now expose `packed_record_count` and `packed_stream_total_bytes`
  - visualization bundles now expose `packed_layout_template_counts`, so consumers can distinguish templates such as `wdq_compute_v1` and `core_link_transfer_v1` without re-inferring them from raw opcodes
  - visualization bundles now expose `packed_field_name_counts`, so consumers can trust emitted `field_placements` such as `transfer_kind` directly instead of reconstructing transport-specific expectations
  - visualization packaging, workbench, and catalog workflow gates remain green with the stronger packed-input requirement
- what this closes:
  - a missing downstream proof that packed descriptors can already serve as a stable consumer-facing contract
  - one more gap between `SPEC-12` specialized layout naming and later visualization/reporting layers
- what still remains for `M2`:
  - richer packed-descriptor consumption beyond summary-grade counts, if later phases need per-record or per-template drilldown without reopening `DescriptorIR`
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 SPEC-12 Workbench Packed Coverage Panel Checkpoint

- plan doc: `../plans/2026-03-11-spec-12-workbench-packed-coverage-panel.md`
- `SPEC-12` packed summary is now visible in the static workbench, not only in raw packaged JSON.
- new closure evidence:
  - the workbench coverage panel now renders `Packed Descriptor Summary`, `Packed Layout Templates`, and `Packed Field Placements`
  - coverage panel export JSON and SVG snapshot lines now carry packed summary fields alongside matched coverage issues
  - workbench builder and workbench workflow gates stay green after the stronger packed-summary display contract
- what this closes:
  - one more gap between packed-descriptor ABI proof and user-visible inspection tooling
  - the need to open raw `visualization_bundle.json` just to confirm specialized templates such as `core_link_transfer_v1` or field placements such as `transfer_kind`
- what still remains for `M2`:
  - decide whether `SPEC-12` needs richer per-record drilldown in workbench, or whether summary-grade visibility is enough for Phase C closure
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 Phase C / M2 Closure Audit Checkpoint

- plan doc: `../plans/2026-03-11-phase-c-m2-closure-audit.md`
- audit conclusion: `M2` is no longer blocked by missing foundation. The remaining Phase C risk is now a narrow closure list across planner closure, tiling scope, residual scheduler generic paths, and the final acceptance line for packed-descriptor fidelity.
- new audit evidence:
  - `SPEC-08` memory artifacts already expose `storage_bindings`, `storage_binding_id`, `backing_store`, and fit-attribution maps, but downstream consumption is still concentrated in the tile planner rather than fully reused by descriptor/perf layers
  - `SPEC-09` candidate generation is still centered on GEMM-like and attention macros, so Phase C still needs an explicit decision about whether broader macro tiling is required for closure
  - `SPEC-10/11` now have a strong phased-reservation base, but remaining generic reservation surfaces still exist and should be audited one by one instead of treated as a vague backlog
  - `SPEC-12` now has real packed consumers and workbench visibility, so its next step is freezing the Phase C stop-line rather than inventing more summary consumers by default
- what this closes:
  - the ambiguity around whether `M2` still needs broad foundation work
  - the tendency to treat all remaining Phase C work as one undifferentiated backlog
- what still remains for `M2`:
  - one evidence-driven `SPEC-10/11` audit batch on remaining generic `store/dma_in` surfaces such as `RMSNORM`, `ELEM_ADD`, and `GEGLU`
  - one explicit `SPEC-09` closure decision on broader tiling coverage versus accepted untiled-helper policy
  - one explicit `SPEC-12` stop-line decision on whether summary-grade packed consumer proof is enough for Phase C
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 SPEC-10/11 GEGLU Store Prefix Checkpoint

- plan doc: `../plans/2026-03-11-spec-10-11-geglu-store-audit.md`
- `SPEC-10/11` now refine `GEGLU.store` so fused feed-forward output writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `GEGLU.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while public stage lowering stays unchanged
  - focused reservation tests now prove a later pure-DMA follower can issue at the start of the `GEGLU` store block instead of waiting for the full block duration
  - planning mainline and single/dual scheduling workflow regressions remain green with the stronger reservation policy
- what this closes:
  - one more real generic-store fidelity gap inside `SPEC-10/11`
  - one more source of false shared-`DMA` pressure on feed-forward helper paths
- what still remains for `M2`:
  - the next evidence-driven scheduler audit should move to remaining generic store surfaces such as `RMSNORM.store` or `ELEM_ADD.store`
  - one explicit `SPEC-09` closure decision on broader tiling coverage versus accepted untiled-helper policy
  - one explicit `SPEC-12` stop-line decision on whether summary-grade packed consumer proof is enough for Phase C
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 SPEC-10/11 RMSNORM Store Prefix Checkpoint

- plan doc: `../plans/2026-03-11-spec-10-11-rmsnorm-store-audit.md`
- `SPEC-10/11` now refine `RMSNORM.store` so normalized activation writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - `RMSNORM.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while public stage lowering stays unchanged
  - focused reservation tests now prove a later pure-DMA follower can issue at the start of the `RMSNORM` store block instead of waiting for the full block duration
  - planning mainline and single/dual scheduling workflow regressions remain green with the stronger reservation policy
- what this closes:
  - one more real generic-store fidelity gap inside `SPEC-10/11`
  - one more source of false shared-`DMA` pressure on normalization-heavy helper paths
- what still remains for `M2`:
  - the next evidence-driven scheduler audit should move to remaining generic store surfaces such as `ELEM_ADD.store`
  - one explicit `SPEC-09` closure decision on broader tiling coverage versus accepted untiled-helper policy
  - one explicit `SPEC-12` stop-line decision on whether summary-grade packed consumer proof is enough for Phase C
  - final Phase C closure pass across `SPEC-08/09/10/11/12`

## 2026-03-11 Smoke Gate Cache-Backed CLI Setup Checkpoint

- plan doc: `../plans/2026-03-11-smoke-gate-cache-backed-cli-setup.md`
- the validation gate now reuses cached prepared smoke stages instead of rebuilding the full CLI chain for every heavy smoke case.
- new closure evidence:
  - `tests/smoke/conftest.py` now provides a hierarchical `prepared_smoke_run_root_factory`, so stage-complete roots reuse earlier cached stages instead of restarting from `init-run`
  - sweep-backed smoke now uses `prepared_smoke_sweep_root_factory`, including cloned report-path rewriting and shortened cache-root naming to stay clear of Windows path-length failures
  - heavy CLI smoke tests plus Phase B/C smoke matrices now clone the nearest valid cached stage and keep only the final CLI command under test real
  - `tests/smoke` now completes in `71 passed in 37m52s`, and full `python -m pytest -q --durations=30` now completes in `363 passed in 50m39s`
- what this closes:
  - the practical inability to finish the smoke/full regression gate locally
  - the ambiguity around whether current Phase C work still had a trustworthy end-to-end verification path
- what still remains:
  - sweep-heavy smoke and workflow paths remain the dominant wall-clock cost, especially `test_phase_d_sweep_foundation_matrix.py`, `test_cli_run_visualization_packaging.py`, `test_cli_run_sweep_analysis.py`, and `test_sweep_analysis_workflow.py`
  - Phase C / `M2` closure work should now return to explicit closure decisions on `SPEC-09`, the remaining evidence-driven `SPEC-10/11` audit surface such as `ELEM_ADD.store`, and the `SPEC-12` stop-line

## 2026-03-11 SPEC-10/11 ELEM_ADD Store Prefix and Phase C Closure Decisions Checkpoint

- plan doc: `../plans/2026-03-11-spec-10-11-elem-add-store-audit-and-phase-c-closure.md`
- `SPEC-10/11` now refine `ELEM_ADD.store` so residual-writeback no longer appears as one monolithic shared-`DMA` slab.
- new closure evidence:
  - focused single-core and dual-core red tests both failed first with `follower_issue == 4`, proving `ELEM_ADD.store` was still a real generic-store fidelity gap
  - `ELEM_ADD.store` now exposes a short `VPU` prefix before the later shared-`DMA` writeback window while public stage lowering stays unchanged
  - focused `store_issue_with_vpu_prefix` scheduler regression now passes at `16 passed`
  - full single-core plus dual-core scheduler unit slices now pass at `60 passed`
- explicit Phase C closure decisions:
  - `SPEC-09`: `M2` accepts the current GEMM-like plus attention tiling surface together with untiled-helper scheduling; broader macro tiling reopens only if a concrete downstream failure appears
  - `SPEC-12`: `M2` stops at packed summary consumer proof plus workbench summary visibility; no per-record workbench drilldown is required without a concrete consumer
- what this closes:
  - one more real generic-store fidelity gap inside `SPEC-10/11`
  - the ambiguity around whether `SPEC-09` still needed proactive macro-coverage expansion for `M2`
  - the ambiguity around whether `SPEC-12` still needed another default visibility / consumer batch for `M2`
- what still remains for `M2`:
  - planner-side closure and stronger downstream reuse on `SPEC-08`
  - final Phase C acceptance rewrite across `SPEC-08/09/10/11/12`

## 2026-03-11 Phase C Acceptance Rewrite Checkpoint

- plan doc: `../plans/2026-03-11-phase-c-acceptance-rewrite.md`
- top-level roadmap, README, and Phase C handoff docs now describe `M2` as a narrow acceptance problem instead of a broad unfinished-foundation phase.
- rewritten acceptance boundaries:
  - `SPEC-08` is now framed as planner closure plus stronger downstream consumption
  - `SPEC-09` now carries an explicit accepted `M2` scope boundary instead of an open-ended macro-coverage backlog
  - `SPEC-10/11` now stay in acceptance-list mode after the completed helper-store audit batch
  - `SPEC-12` now carries a frozen `M2` stop-line at packed summary consumer proof plus workbench summary visibility
- what this closes:
  - the mismatch between the latest 2026-03-11 audit decisions and older top-level status language
  - the tendency to treat all remaining Phase C work as one undifferentiated backlog
- what still remains for `M2`:
  - `SPEC-08` planner closure and stronger downstream reuse
  - eventual status promotion from `in_progress` to `done` only after that remaining closure evidence exists

## 2026-03-11 SPEC-08 -> SPEC-13 Backing-Store Summary Reuse Checkpoint

- plan doc: `../plans/2026-03-11-spec-08-perf-backing-store-reuse.md`
- `SPEC-13` now consumes one more structured `SPEC-08` field directly instead of collapsing region pressure to a single total.
- new closure evidence:
  - `PerfSummaryReport` now carries `vmem_region_peak_bytes_by_backing_store`
  - performance-estimation now reuses `memory_plan.region_summaries[*].peak_bytes_by_backing_store` directly
  - focused perf-summary regression now proves backing-store-attributed VMEM pressure survives into the downstream summary layer
- what this closes:
  - one concrete downstream-reuse gap in the old `SPEC-08` planner-closure backlog
  - one place where later analysis previously had to reopen raw memory-plan detail to recover backing-store attribution
- what still remains for `M2`:
  - more `SPEC-08` downstream reuse beyond the current tile-planner and perf-summary consumers
  - planner-side closure and final acceptance evidence

## 2026-03-11 SPEC-08 -> SPEC-12 Descriptor Address Storage Reuse Checkpoint

- plan doc: `../plans/2026-03-11-spec-08-descriptor-address-storage-reuse.md`
- `SPEC-12` now consumes one more structured `SPEC-08` field directly through `DescriptorIR.address_fields` instead of forcing later layers to reopen raw allocation tables.
- new closure evidence:
  - `AddressField` now carries optional `storage_binding_id` and `backing_store`
  - descriptor generation now copies this storage provenance directly from `memory_plan.allocations[*]` when an address field is allocation-backed
  - focused descriptor-builder regression now proves compute descriptors preserve staged-weight versus VMEM-local output attribution
- what this closes:
  - one more concrete downstream-reuse gap in the old `SPEC-08` planner-closure backlog
  - one place where later descriptor or analysis consumers would otherwise need to reconstruct storage provenance from raw allocations
- what still remains for `M2`:
  - planner-side closure and final acceptance evidence on `SPEC-08`
  - only additional downstream reuse that is backed by a concrete consumer gap

## 2026-03-11 SPEC-08 -> SPEC-14/15 Hotspot Backing-Store Reuse Checkpoint

- plan doc: `../plans/2026-03-11-spec-08-prefill-decode-backing-store-hotspot-reuse.md`
- `SPEC-14/15` now consume one more structured `SPEC-08` field directly through top-level `memory_hotspot` summaries instead of collapsing the hottest VMEM region to one scalar peak.
- new closure evidence:
  - `PrefillMemoryHotspotSummary` and `DecodeMemoryHotspotSummary` now carry `hottest_region_peak_bytes_by_backing_store`
  - prefill/decode report builders now reuse `memory_plan.region_summaries[hottest_region].peak_bytes_by_backing_store` directly
  - focused contract, builder, and workflow regressions now prove hottest-region backing-store attribution survives into serialized top-level reports
- what this closes:
  - one more concrete downstream-reuse gap in the old `SPEC-08` planner-closure backlog
  - one place where top-level evaluation consumers previously knew which region was hottest but not which backing-store class dominated that peak
- what still remains for `M2`:
  - planner-side closure and final acceptance evidence on `SPEC-08`
  - only additional downstream reuse that is backed by a concrete consumer gap

## 2026-03-11 SPEC-08 -> SPEC-18 Visualization VMEM Backing-Store Reuse Checkpoint

- plan doc: `../plans/2026-03-11-spec-08-visualization-vmem-backing-store-reuse.md`
- `SPEC-18` now consumes one more structured `SPEC-08` field directly through `VisualizationBundle.vmem_view.regions` instead of collapsing each VMEM region to `peak_bytes` and utilization only.
- new closure evidence:
  - `VisualizationVMEMRegionView` now carries `peak_bytes_by_backing_store`
  - visualization bundle generation now reuses `memory_plan.region_summaries[*].peak_bytes_by_backing_store` directly
  - focused visualization contract, builder, and packaging-workflow regressions now prove per-region backing-store attribution survives into serialized bundles
- what this closes:
  - one more concrete downstream-reuse gap in the old `SPEC-08` planner-closure backlog
  - one place where visualization consumers previously knew which VMEM region was tight but not which backing-store class contributed to that peak
- what still remains for `M2`:
  - planner-side closure and final acceptance evidence on `SPEC-08`
  - only additional downstream reuse that is backed by a concrete consumer gap

## 2026-03-11 SPEC-19 Workbench VMEM Backing-Store Visibility Checkpoint

- plan doc: `../plans/2026-03-11-spec-19-workbench-vmem-backing-store-visibility.md`
- `SPEC-19` now makes the already-packaged per-region backing-store attribution visible in the workbench memory panel instead of leaving it latent in `visualization_bundle.json`.
- new closure evidence:
  - the workbench memory panel now renders `Region Backing Store Mix`
  - memory-panel SVG snapshot lines now include top-region backing-store attribution
  - focused workbench builder and workflow regressions now prove `peak_bytes_by_backing_store` is both consumed and visible in generated assets
- what this closes:
  - one concrete visibility gap between the landed `SPEC-18` bundle field and human-facing `SPEC-19` inspection
  - one case where workbench users previously needed to reopen raw bundle JSON to inspect VMEM backing-store attribution
- what still remains:
  - richer compare and workspace-navigation hardening on `SPEC-19`
  - no need to reopen `SPEC-18` contract unless a new missing query pattern appears

## 2026-03-11 SPEC-19 Catalog Multi-Metric Compare Checkpoint

- plan doc: `../plans/2026-03-11-spec-19-catalog-multi-metric-compare.md`
- `SPEC-19` catalog compare now carries structured `metric_values`, so compare tray and baseline-pinned workspace no longer collapse packaged reports to one primary metric.
- new closure evidence:
  - `VisualizationCatalogEntry` now carries a `metric_values` summary map
  - catalog packaging now copies `visualization_bundle.report_summary.primary_metrics` into the static catalog manifest
  - compare tray and workspace now render `Shared Metric Deltas` from the shared metric set instead of only one scalar delta
  - focused catalog contract, builder, and workflow regressions now prove the multi-metric compare surface is preserved end-to-end
- what this closes:
  - one concrete `SPEC-19` product gap where catalog compare previously degraded multi-metric reports to a single primary summary
  - one case where users had to reopen individual workbenches or raw bundle JSON just to inspect secondary summary metrics during compare
- what still remains:
  - richer workspace navigation and compare drill-down beyond the current summary-grade metric map
  - richer screenshot/export workflow

## 2026-03-09 SPEC-13 Schedule Occupancy Breakdown Checkpoint

- plan doc: `../plans/2026-03-09-spec-13-schedule-occupancy-breakdown.md`
- `SPEC-13` now consumes the stronger Phase C timing signal as occupancy summaries, not only top-line makespan.
- new closure evidence:
  - `PerfSummaryReport` now carries `per_core_busy_slots`
  - `PerfSummaryReport` now carries `per_core_idle_slots`
  - `PerfSummaryReport` now carries `schedule_stage_slot_totals`
  - busy-slot accounting now preserves overlap by merging scheduled intervals per core instead of summing raw block durations
- what this closes:
  - a first downstream consumer of the stronger `SPEC-10/11` schedule fidelity work
  - a clearer bridge from Phase C timing to later `SPEC-14/15/16` aggregation
- what still remains for `M3`:
  - deeper cycle and bandwidth models
  - layer-level breakdown
  - richer diff and compare surfaces

## 2026-03-09 SPEC-13 Bandwidth / VMEM Breakdown Checkpoint

- plan doc: `../plans/2026-03-09-spec-13-bandwidth-vmem-breakdown.md`
- `SPEC-13` now consumes `MemoryPlanArtifact` as a real summary input instead of only validating that it exists.
- new closure evidence:
  - `PerfSummaryReport` now carries `data_movement_read_bytes_by_address_space`
  - `PerfSummaryReport` now carries `data_movement_write_bytes_by_address_space`
  - `PerfSummaryReport` now carries `vmem_region_peak_bytes`
  - `PerfSummaryReport` now carries `vmem_region_capacity_bytes`
  - `PerfSummaryReport` now carries `vmem_region_peak_utilization`
  - Phase D perf workflow, prefill/decode workflow readers, and Gemma3 perf smoke remain green with the stronger summary contract
- what this closes:
  - first-order bandwidth attribution without reopening raw descriptors
  - first-order VMEM region pressure attribution without reopening raw memory-plan diagnostics
  - a stronger aggregation input for `SPEC-14/15/16`
- what still remains for `M3`:
  - deeper cycle fitting
  - layer-level or token-phase attribution
  - richer compare surfaces above the current summary-grade breakdown

## 2026-03-09 SPEC-14/15 Memory Hotspot Summary Checkpoint

- plan doc: `../plans/2026-03-09-spec-14-15-memory-hotspot-summary.md`
- `SPEC-14` and `SPEC-15` now consume the new `SPEC-13` address-space / VMEM summary instead of only exposing throughput-latency shells above perf totals.
- new closure evidence:
  - `PrefillEvaluationReport` now carries `memory_hotspot`
  - `DecodeEvaluationReport` now carries `memory_hotspot`
  - both top-level reports now expose `dominant_address_space`
  - both top-level reports now expose copied read/write movement maps plus hottest-region VMEM utilization
  - prefill/decode workflow gates and Phase D prefill/decode smoke remain green with the stronger report contracts
- what this closes:
  - top-level prefill/decode reports can now answer whether pressure is leaning toward `DDR` or `VMEM`
  - top-level prefill/decode reports can now answer which VMEM region is tightest without reopening raw memory-plan diagnostics
  - later compare/UI layers get a stronger stable surface without re-parsing `PerfSummaryReport`
- what still remains for `M3`:
  - layer-level breakdown and single-vs-dual compare surfaces
  - deeper cycle fitting above the current summary-grade contract
  - richer sweep and multi-metric compare modes
