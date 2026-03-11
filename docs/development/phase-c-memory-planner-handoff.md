# Phase C Memory Planner Handoff

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

当前还没有：

- lifetime reuse / free-list 复用
- broader capacity reasoning for remaining activation-heavy surfaces
- dual-core 数据交换路径选择
- quant / weight / output 的真实 DDR 地址绑定
- `Schedule IR` 级 buffer binding

这些都是 `SPEC-08` 后续收口项或 `SPEC-09/10/11/12` 的工作，不应回灌成 frontend 需求。

## 7. Recommended Next Step

`SPEC-08` 当前已经不再阻塞 `SPEC-09`。下一步应该把 Phase C 主线切到 tile planner：

1. 冻结 `TilingPlanArtifact` 和 `run-tile-planning` 的 artifact contract
2. 让 prefill / decode 四象限稳定产出可比较的 GEMM / attention tile candidates
3. 在 `bound-NIG + MemoryPlanArtifact + TilingPlanArtifact` 之上启动 `SPEC-10` single-core scheduling
