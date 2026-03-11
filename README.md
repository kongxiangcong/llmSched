# llm-sched

RISC-V + NPU architecture-evaluation compiler for Gemma3-like workloads.

当前主线阶段：
- `M1` 已完成
- `M2` 进行中
- 当前重点是 `SPEC-10/11` 的 schedule-fidelity hardening，而不是回到 frontend 继续开新 foundation

核心 CLI 流水线：

```powershell
python -m llm_sched.cli.main validate-profile --target-profile ... --scenario-profile ...
python -m llm_sched.cli.main init-run --run-root ... --model-path ... --target-profile ... --scenario-profile ...
python -m llm_sched.cli.main run-frontend-analysis --run-root ...
python -m llm_sched.cli.main run-memory-planning --run-root ...
python -m llm_sched.cli.main run-tile-planning --run-root ...
python -m llm_sched.cli.main run-single-core-scheduling --run-root ...
python -m llm_sched.cli.main run-dual-core-scheduling --run-root ...
python -m llm_sched.cli.main run-descriptor-generation --run-root ...
python -m llm_sched.cli.main run-performance-estimation --run-root ...
python -m llm_sched.cli.main run-prefill-evaluation --run-root ...
python -m llm_sched.cli.main run-decode-evaluation --run-root ...
```

## Development Verification

不要把下面这个命令当成默认开发循环：

```powershell
python -m pytest -q
```

它是全量回归面，适合主线稳定化或夜跑，不适合日常迭代。

当前基线（2026-03-11）：
- `python -m pytest tests/smoke -q --durations=30` -> `71 passed in 37m52s`
- `python -m pytest -q --durations=30` -> `363 passed in 50m39s`
- full gate 现在已经可以跑完，但仍然不适合默认开发循环

### 1. Fast Local Default

改 contract、frontend、IR、planner 内部逻辑时，默认先跑：

```powershell
python -m pytest `
  tests/unit/contracts `
  tests/unit/config `
  tests/unit/arch `
  tests/unit/ir `
  tests/unit/frontend `
  tests/unit/planning -q
```

这是当前最稳定、最快的本地安全网。

### 2. Workflow-Focused Regression

改 pipeline、run-root artifact、schedule/perf/report 聚合时，只补跑受影响的 workflow 文件，不要整目录全扫。

常用示例：

```powershell
python -m pytest `
  tests/unit/pipeline/test_frontend_analysis_workflow.py `
  tests/unit/pipeline/test_memory_planning_workflow.py `
  tests/unit/pipeline/test_tile_planning_workflow.py -q
```

如果改的是单核/双核调度、descriptor 或 perf，按影响面补跑对应文件，例如：

```powershell
python -m pytest `
  tests/unit/planning/test_schedule_duration.py `
  tests/unit/planning/test_single_core_scheduler.py `
  tests/unit/planning/test_dual_core_scheduler.py `
  tests/unit/pipeline/test_dual_core_scheduling_workflow.py -q
```

说明：
- `tests/unit/pipeline` 比普通 unit 明显更重
- `test_dual_core_scheduling_workflow.py` 当前单文件就可能需要数分钟

### 3. Smoke Escalation

只有在 CLI 或阶段闭环行为变更时，再升级到 smoke。

本地代表性 smoke：

```powershell
python -m pytest tests/smoke -m local_smoke -q
```

里程碑或跨场景/跨 target 关闭时再跑：

```powershell
python -m pytest tests/smoke -m milestone_matrix -q
```

说明：
- `local_smoke` 也不轻，当前会真实经过 cached run-root + CLI stage 链路
- 当前 smoke gate 已改成 cache-backed CLI setup；重场景会复用 prepared run-root / prepared sweep-root，而不是每个测试都重跑全链路
- 不要把 `tests/smoke` 当成每次提交前的默认循环

### 4. 推荐升级顺序

日常开发建议按这个顺序升级验证：

1. `tests/unit/contracts|config|arch|ir|frontend|planning`
2. 受影响的 `tests/unit/pipeline/test_*workflow.py`
3. `tests/smoke -m local_smoke`
4. `tests/smoke -m milestone_matrix`
5. `python -m pytest -q`

## Current Direction

当前最有价值的下一批工作：
- 继续收口 `M2`
- 优先做 `SPEC-08` 的 planner closure + downstream reuse
- `SPEC-08 -> SPEC-13` 现已有一条真实 downstream reuse：`PerfSummaryReport` 直接带 `peak_bytes_by_backing_store`
- `SPEC-08 -> SPEC-12` 现也已有一条真实 downstream reuse：`DescriptorIR.address_fields` 直接带 `storage_binding_id/backing_store`
- `SPEC-08 -> SPEC-14/15` 现也已有一条真实 downstream reuse：prefill/decode `memory_hotspot` 直接带 hottest-region 的 `peak_bytes_by_backing_store`
- `SPEC-08 -> SPEC-18` 现也已有一条真实 downstream reuse：`VisualizationBundle.vmem_view.regions` 直接带 `peak_bytes_by_backing_store`
- `SPEC-18 -> SPEC-19` 现也已有一条真实 visible consumer：workbench memory panel 直接显示 per-region `peak_bytes_by_backing_store`
- `SPEC-19` catalog compare 现也已有 shared summary-metric compare：静态 catalog 直接携带 `metric_values`，不再只看单一 primary metric
- `SPEC-19` catalog compare 现也已有 selected-panel deep-link navigation：compare tray / workspace 可直接跳到 `summary/timeline/memory/coverage`
- `SPEC-10/11` 的 helper-store audit batch 已完成；后续以 acceptance list 维持稳定，不再默认继续宽泛铺开
- `SPEC-09` 现接受当前 GEMM-like / attention tiling + untiled-helper scheduling 作为 `M2` 收口范围
- 把更强的调度时序信号继续喂给 `SPEC-13`
- `SPEC-12` 的 `M2` stop-line 现冻结为 packed summary consumer + workbench summary visibility
- `SPEC-12` 只做窄范围 hardening，不再作为唯一主线
- 现实里的验证瓶颈已经从 “full pytest 跑不完” 收敛到 “sweep / visualization packaging 仍然偏重”

参考文档：
- `docs/development/evaluation-compiler-roadmap.md`
- `docs/development/test-strategy-and-run-modes.md`
- `docs/development/mainline-test-recommendations.md`
