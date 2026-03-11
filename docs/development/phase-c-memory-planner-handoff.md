# Phase C Memory Planner Handoff

## 2026-03-12 Planner Closure Gate Checkpoint

- New plan: `../plans/2026-03-12-spec-08-planner-closure-gate.md`
- `memory_planner_closure_report.json` now carries a dedicated `planner_closure` section above downstream consumer evidence.
- planner closure is now machine-readable instead of implicit:
  - overflow regions must stay at `0`
  - unresolved address diagnostics must stay at `0`
  - every active region must preserve both memory-class and backing-store attribution
- `ready_for_acceptance` now requires both planner-side closure and required downstream consumer verification, so `SPEC-08` no longer reads green only because later layers consume part of the artifact.

## 2026-03-12 Phase C Acceptance Matrix Report Checkpoint

- New plan: `../plans/2026-03-12-phase-c-acceptance-matrix-report.md`
- `run-phase-c-acceptance` now emits `reports/phase_c_acceptance_report.json`.
- the new report regenerates `memory_planner_closure_report.json` across the canonical `single-core/dual-core x prefill/decode` matrix and summarizes missing, duplicate, or blocked cases in one machine-readable artifact.
- each case record now also distinguishes planner-side closure from downstream-consumer closure, so blocked matrix cells no longer require reopening per-run closure JSON just to see which side failed first.
- the matrix coverage summary now also exposes planner-blocked and downstream-blocked case counts as a top-level scan surface; the two counts may overlap when one case is blocked on both sides.
- `run-phase-c-acceptance` CLI output now prints the same matrix summary line, so the gate is visible directly from terminal runs instead of only inside `phase_c_acceptance_report.json`.
- `run-phase-c-gate` now promotes that same summary to the formal `M2 / SPEC-08` terminal gate: it regenerates the matrix report and exits nonzero unless the canonical matrix is `ready_for_acceptance`.
- `SPEC-08` acceptance evidence now exists at both per-run and cross-run levels, so the remaining `M2` question is planner-side closure rather than downstream evidence bookkeeping.

## 2026-03-12 Memory Planner Closure Report Checkpoint

- New plan: `../plans/2026-03-12-memory-planner-closure-report.md`
- `run-memory-planner-closure` now emits `reports/memory_planner_closure_report.json`.
- the closure report now enumerates required downstream consumers across tile planning, descriptor generation, perf estimation, mode-specific top-level eval, and visualization packaging.
- the closure report also tracks optional visible evidence from the static workbench memory panel, so `SPEC-08` acceptance proof no longer lives only in prose checkpoints.

## 2026-03-12 Visualization Memory-Class Visibility Checkpoint

- New plan: `../plans/2026-03-12-spec-08-visualization-memory-class-visibility.md`
- `VisualizationBundle.vmem_view.regions[*]` now carry `peak_bytes_by_memory_class`.
- the static workbench memory panel now renders per-region `peak_bytes_by_memory_class` and exposes top-region memory-class attribution in SVG snapshot lines.
- `SPEC-18/19` now make one more `SPEC-08` planner attribution visible to human-facing consumers without reopening planner contracts or visualization service scope.

## 2026-03-12 Prefill/Decode Hotspot Memory-Class Reuse Checkpoint

- New plan: `../plans/2026-03-12-spec-08-prefill-decode-memory-class-hotspot-reuse.md`
- `PrefillEvaluationReport.memory_hotspot` and `DecodeEvaluationReport.memory_hotspot` now carry `hottest_region_peak_bytes_by_memory_class`.
- `SPEC-14/15` now reuse `memory_plan.region_summaries[hottest_region].peak_bytes_by_memory_class` directly instead of leaving the hottest-region source-class mix trapped inside planner-only JSON.
- This closes one more concrete downstream-reuse gap without reopening planner contracts or introducing layer-level hotspot replay.

## 2026-03-11 Perf Summary Memory-Class Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-perf-memory-class-reuse.md`
- `PerfSummaryReport` now carries `vmem_region_peak_bytes_by_memory_class`.
- `SPEC-13` now reuses `memory_plan.region_summaries[*].peak_bytes_by_memory_class` directly instead of leaving region pressure by memory class trapped inside planner-only JSON.
- This closes one more concrete downstream-reuse gap without reopening planner contracts or introducing block-level lifetime replay.

## 2026-03-11 Workbench VMEM Backing-Store Visibility Checkpoint

- New plan: `../plans/2026-03-11-spec-19-workbench-vmem-backing-store-visibility.md`
- the static workbench memory panel now renders per-region `peak_bytes_by_backing_store` from the existing visualization bundle.
- `SPEC-19` now makes `SPEC-08` per-region backing-store attribution visible to a human-facing consumer instead of leaving it latent in packaged JSON.
- This closes one more concrete downstream-reuse visibility gap without reopening planner contracts or visualization bundle schema.

## 2026-03-11 Visualization VMEM Backing-Store Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-visualization-vmem-backing-store-reuse.md`
- `VisualizationBundle.vmem_view.regions[*]` now carry `peak_bytes_by_backing_store`.
- `SPEC-18` now reuses `memory_plan.region_summaries[*].peak_bytes_by_backing_store` directly instead of collapsing each VMEM region to one scalar peak plus utilization.
- This closes one more concrete downstream-reuse gap without reopening planner contracts or forcing the UI to read raw memory-plan artifacts.

## 2026-03-11 Prefill/Decode Hotspot Backing-Store Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-prefill-decode-backing-store-hotspot-reuse.md`
- `PrefillEvaluationReport.memory_hotspot` and `DecodeEvaluationReport.memory_hotspot` now carry `hottest_region_peak_bytes_by_backing_store`.
- `SPEC-14/15` now reuse `memory_plan.region_summaries[hottest_region].peak_bytes_by_backing_store` directly instead of collapsing the hottest region to one scalar peak.
- This closes one more concrete downstream-reuse gap without reopening planner contracts or inventing a new memory summary layer.

## 2026-03-11 Descriptor Address Storage Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-descriptor-address-storage-reuse.md`
- `DescriptorIR.address_fields[*]` now carry `storage_binding_id` and `backing_store` when the field is backed by a `PlannedAllocation`.
- `SPEC-12` now reuses `memory_plan.allocations[*]` storage provenance directly instead of forcing later layers to reopen raw allocation tables.
- This closes one more concrete downstream-reuse gap without reopening planner contracts or introducing target-specific packing.

## 2026-03-11 Perf Summary Backing-Store Reuse Checkpoint

- New plan: `../plans/2026-03-11-spec-08-perf-backing-store-reuse.md`
- `PerfSummaryReport` now carries `vmem_region_peak_bytes_by_backing_store`.
- `SPEC-13` now reuses `memory_plan.region_summaries[*].peak_bytes_by_backing_store` directly instead of flattening all region pressure to one total.
- This closes one concrete downstream-reuse gap without reopening planner contracts or introducing schedule-aware allocation.

## 2026-03-09 Storage Binding Surface Checkpoint

- New plan: `../plans/2026-03-09-spec-08-storage-binding-surface.md`
- `MemoryPlanArtifact` now carries a formal `storage_bindings` surface.
- `PlannedAllocation` now carries `storage_binding_id` for non-local backing stores.
- `AddressBindingDiagnostic` now carries `storage_binding_id`, so diagnostics point at the same formal binding records as the allocations.
- `StorageBindingDescriptor` now covers:
  - staged `WEIGHT`
  - staged `QUANT_PARAM`
  - persistent `KV_CACHE`
- The planner now uses one structured source/storage surface instead of requiring downstream layers to parse `backing_symbol`.
- This closes the next `SPEC-08` planner-closure gap without introducing target-specific encoding or schedule-aware reuse.

## 2026-03-09 Fit Reasoning Checkpoint

- New plan: `../plans/2026-03-09-spec-08-fit-reasoning.md`
- `RegionSummary` now carries:
  - `peak_bytes_by_memory_class`
  - `peak_bytes_by_backing_store`
- `VMEMFitDiagnostic` now carries:
  - `required_bytes_by_memory_class`
  - `required_bytes_by_backing_store`
- `SPEC-08` can now explain region pressure by source class and backing-store type instead of only total bytes.
- This closes the next planner-closure gap without introducing traffic/cycle modeling.

## 2026-03-09 DDR Binding Checkpoint

- New plan: `../plans/2026-03-09-spec-08-ddr-binding-realism.md`
- `MemoryPlanArtifact.allocations[*]` now carries `backing_store` and `backing_symbol`.
- staged `WEIGHT` / `QUANT_PARAM` allocations now explicitly model `ddr-backed-staged`.
- `KV_CACHE` allocations now explicitly model `ddr-persistent` with `KV_BASE`.
- `address_diagnostics` now covers:
  - `kv`
  - `weight`
  - `quant`
- This closes the second `SPEC-08` realism gap without pulling final target-specific address packing into the memory planner.

## 2026-03-09 Lifetime Reuse Checkpoint

- New plan: `../plans/2026-03-09-spec-08-lifetime-reuse.md`
- `MemoryPlanArtifact.allocations[*]` now carries a static `lifetime_bucket`.
- `region_summaries[*]` now carries `peak_lifetime_bucket` and `peak_bytes_by_lifetime_bucket`.
- Region peaks now use static phase-bucket reuse instead of the old same-node raw-sum model.
- This closes the first `SPEC-08` lifetime-reuse gap without introducing schedule-aware liveness or a runtime allocator.
- The remaining `SPEC-08` closure work is now:
  - stronger DDR / VMEM binding realism
  - planner closure
  - broader capacity reasoning beyond the current static phase buckets

## 2026-03-07 Checkpoint

- 鏈壒鏂板鐨?working-set heuristics 宸茬粡瑕嗙洊 `SDPA`銆乣RMSNORM_GEMM`銆乣RMSNORM`銆乣ELEM_ADD`銆乣KVLOAD`銆乣KVSTORE`銆?
- 鏂扮殑 Gemma3 鍥涜薄闄?smoke 鍩虹嚎鏄細`overflow_regions = {}`銆?`address_diagnostics.unresolved = 0`銆?`kv_formulas = 69`銆?
- 杩欒〃绀?`SPEC-08` 宸茬粡涓嶅啀鍥?Gemma3 baseline fit 闂闃诲 `SPEC-09`锛屽彲浠ヨ浆鍏?tile candidate planner 涓荤嚎銆?

## 2026-03-07 Tile Planner Transition

- `SPEC-08` remains `in_progress`, but it no longer blocks `SPEC-09`.
- The active Phase C mainline is now `bound-NIG -> MemoryPlanArtifact -> TilingPlanArtifact`.
- Scheduling work should consume the stable `SPEC-08` and `SPEC-09` artifacts rather than reopening frontend contracts.

## 1. What Is Stable Now

`SPEC-08` 当前已经有一版可运行、可验证、可落盘的 memory planner foundation。它的职责不是给出最终最优内存方案，而是把 bound-NIG 正式转换成可供后续 tiling / scheduling / descriptor 复用的显式地址与容量工件。

当前稳定输出包括：

- `MemoryPlanArtifact`
- `artifacts/memory_plan.json`
- KV 地址公式
- KV 地址绑定诊断
- region 级 VMEM fit 诊断

这意味着 Phase C 后续模块不需要再从 bound-NIG 里零散重推 VMEM/KV 假设。

## 2. Stable Contract

当前 `MemoryPlanArtifact` 稳定包含：

- `graph_id`
- `scenario_name`
- `core_mode`
- `allocations`
- `region_summaries`
- `kv_formulas`
- `diagnostics`
- `address_diagnostics`

其中关键语义是：

- `allocations`
  - tensor 级静态分配记录
  - 区分 `VMEM` / `DDR`
  - 记录 `memory_class`、`region_name`、`size_bytes`
- `region_summaries`
  - 按 `ping/pong/weight/accum/misc/wdq_reserved/quant` 汇总 peak usage
- `kv_formulas`
  - 当前使用 `LBHSD` 布局假设
  - 输出 `layer_stride/token_stride/head_stride/dim_stride`
- `diagnostics`
  - 当前只覆盖 `fit/overflow`
  - 以 region 为粒度暴露 VMEM 压力
- `address_diagnostics`
  - 当前只覆盖 KV 地址绑定
  - `bound/unresolved` 显式区分

## 3. Current Planning Assumptions

当前 planner 是静态 foundation，核心假设是：

- `decode -> M_tile = 1`
- `prefill -> default M_tile = 64`
- `N_tile = 128`
- `K_tile = 128`
- activation staging 使用 `ping/pong`
- weight staging 使用 `weight`
- GEMM accum 使用 `accum`
- VPU / helper scratch 使用 `misc`
- WDQ scratch 使用 `wdq_reserved`
- scale / zp staging 使用 `quant`
- GEMM-like nodes 现在会按 `accum/ping/pong` capacity 自动收缩 `M_tile`
- `EMBEDDING_LOOKUP` 使用 token-tiled working-set 估算
- `LAYOUT_FALLBACK` 使用 vector-tiled working-set 估算
- `GEGLU` 和 `ROPE` 使用 streaming activation tile 估算
- `ROPE_TABLE` 使用 head-dim-sliced weight working-set 估算

这些假设是为了让 Phase C 后续模块先有稳定输入面，不代表最终最优策略。

## 4. Gemma3 Smoke Baseline

当前 `run-memory-planning` 的 Gemma3 四象限 smoke matrix 已稳定通过：

- `single-core + prefill`
- `single-core + decode`
- `dual-core + prefill`
- `dual-core + decode`

四个组合当前都满足：

- frontend analysis succeeds
- memory planning succeeds
- `artifacts/memory_plan.json` exists
- `kv_formulas` 与 `address_diagnostics` 一一对应
- `address_diagnostics` 中 `unresolved = 0`

稳定基线：

- `kv_formulas = 69`
- `address_diagnostics = 69`
- prefill overflow regions
  - `ping`
  - `pong`
  - `weight`
- decode overflow regions
  - `ping`
  - `pong`
  - `weight`
- `quant` 和 `wdq_reserved` 当前在四象限下都保持 `fits = true`

这里的 overflow 不代表 planner 失败，而是当前静态假设下的显式容量诊断，正是这一步需要保留的工程信息。

## 5. What SPEC-09 Can Assume

`SPEC-09` 可以直接假设以下输入已经稳定存在：

- bound-NIG 已完成 quant / shape / layout / attention binding
- `MemoryPlanArtifact` 已能给出 region-level pressure
- KV stride 已公式化
- KV layer id 对 Gemma3 主路径可稳定解析
- `run-memory-planning` 已经是独立 CLI / pipeline 入口

tile planner 不需要再去处理“KV 地址是否能解析”或“region 名称是什么”这类问题。

## 6. What Is Still Missing

当前剩余 gap 已经收敛为：

- planner closure 本身的最终 status promotion
- stronger downstream consumption beyond tile planner，尤其是 descriptor / perf 层不再重构 memory artifact 已有信息
- 只在出现具体压力归因盲点时，再补窄范围 activation-heavy capacity reasoning

当前不再缺：

- lifetime reuse / phase-bucket reuse
- formal DDR / storage binding surface
- 启动 `SPEC-09` 所需的稳定输入面

这些是 `SPEC-08` 收口项或下游消费项，不应回灌成 frontend 需求，也不要求在 `SPEC-08` 内引入 runtime allocator 或 target-specific packing。当前 `SPEC-12` 已开始直接消费 `storage_binding_id/backing_store`，`SPEC-13` 已开始直接消费 `peak_bytes_by_backing_store` 和 `peak_bytes_by_memory_class`，`SPEC-14/15` 已开始直接消费 hottest-region backing-store attribution 和 hottest-region memory-class attribution，`SPEC-18` 已开始直接消费 per-region backing-store attribution，`SPEC-19` 也已把这张表提升到 memory panel 可见层，所以 downstream reuse 不再只停留在 tile planner。

## 7. Recommended Next Step

`SPEC-08` 当前下一步不是再开新语义，而是完成 planner closure：

1. 保持 `MemoryPlanArtifact` 稳定，作为 Phase C 后续模块的正式输入面。
2. 用 `run-phase-c-gate` 持续验证 canonical `single-core/dual-core x prefill/decode` matrix，而不是继续用口头 acceptance list或手工读取 JSON。
3. 只有在出现具体容量归因、overflow 或 unresolved-address 失败证据时，才补窄范围 planner hardening 或新增 downstream reuse。
