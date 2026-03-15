# llm-sched

RISC-V + NPU architecture-evaluation compiler for Gemma3-like workloads.

当前主线阶段：
- `M1` 已完成
- `M2` 已完成
- 当前重点转到 `SPEC-13/14/15/16` 的 `M3` 收口，以及 `SPEC-19` 的产品化 hardening，而不是继续把 `Phase C` 当成未收口 foundation

核心 CLI 流水线：

```powershell
python -m llm_sched.cli.main validate-profile --target-profile ... --scenario-profile ...
python -m llm_sched.cli.main init-run --run-root ... --model-path ... --target-profile ... --scenario-profile ...
python -m llm_sched.cli.main run-frontend-analysis --run-root ...
python -m llm_sched.cli.main run-memory-planning --run-root ...
python -m llm_sched.cli.main run-memory-planner-closure --run-root ...
python -m llm_sched.cli.main run-tile-planning --run-root ...
python -m llm_sched.cli.main run-single-core-scheduling --run-root ...
python -m llm_sched.cli.main run-dual-core-scheduling --run-root ...
python -m llm_sched.cli.main run-descriptor-generation --run-root ...
python -m llm_sched.cli.main run-performance-estimation --run-root ...
python -m llm_sched.cli.main run-prefill-evaluation --run-root ...
python -m llm_sched.cli.main run-decode-evaluation --run-root ...
python -m llm_sched.cli.main run-sweep-analysis --sweep-spec ... --sweep-root ...
python -m llm_sched.cli.main run-phase-d-compare --sweep-root ...
python -m llm_sched.cli.main run-visualization-packaging --run-root ... --sweep-root ...
python -m llm_sched.cli.main run-visualization-workbench --run-root ...
python -m llm_sched.cli.main run-visualization-catalog --catalog-root ... --run-root ... --sweep-root ... --workspace-root ...
python -m llm_sched.cli.main run-phase-c-acceptance --report-root ... --workspace-root ...
python -m llm_sched.cli.main run-phase-c-gate --report-root ... --workspace-root ...
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

当前里程碑验证（2026-03-12）：
- `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 68 deselected in 12m49s`
- `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 68 deselected in 15m00s`

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
- `M2` 当前正式 gate 已稳定为绿，不再作为默认主线 blocker
- 优先转向 `M3`：先做 `SPEC-13/14/15/16` 的评估闭环收口
- `SPEC-13` 现在已有 stable 的 per-node / per-layer perf summary；`SPEC-14/15` 也已正式暴露 `node_hotspots` 与 `layer_breakdown`
- `SPEC-16` 现在不只是 `metric/macro/layer deltas`，还已有结构化 `prefill_compare` / `decode_compare`，并新增 `run-phase-d-compare` 生成 standalone `phase_d_compare_report.json`
- `M3` 当前更合理的下一步，是让 `SPEC-18/19` 直接消费 `PhaseDCompareReport`，而不是继续从 raw `SweepComparison` 手拆 top-level compare
- 如果继续做 UI，优先 `SPEC-19` 的 deeper workspace drill-down / richer compare drill-down / richer screenshot/export workflow
- `SPEC-08 -> SPEC-13` 现已有一条真实 downstream reuse：`PerfSummaryReport` 直接带 `peak_bytes_by_backing_store`
- `SPEC-08 -> SPEC-13` 现也已有一条真实 downstream reuse：`PerfSummaryReport` 直接带 per-region `peak_bytes_by_memory_class`
- `SPEC-08 -> SPEC-12` 现也已有一条真实 downstream reuse：`DescriptorIR.address_fields` 直接带 `storage_binding_id/backing_store`
- `SPEC-08 -> SPEC-14/15` 现也已有一条真实 downstream reuse：prefill/decode `memory_hotspot` 直接带 hottest-region 的 `peak_bytes_by_backing_store`
- `SPEC-08 -> SPEC-14/15` 现也已有一条真实 downstream reuse：prefill/decode `memory_hotspot` 直接带 hottest-region 的 `peak_bytes_by_memory_class`
- `SPEC-08 -> SPEC-18` 现也已有一条真实 downstream reuse：`VisualizationBundle.vmem_view.regions` 直接带 `peak_bytes_by_backing_store`
- `SPEC-08 -> SPEC-18` 现也已有一条真实 downstream reuse：`VisualizationBundle.vmem_view.regions` 直接带 `peak_bytes_by_memory_class`
- `SPEC-18 -> SPEC-19` 现也已有一条真实 visible consumer：workbench memory panel 直接显示 per-region `peak_bytes_by_backing_store`
- `SPEC-18 -> SPEC-19` 现也已有一条真实 visible consumer：workbench memory panel 直接显示 per-region `peak_bytes_by_memory_class`
- `SPEC-19` catalog compare 现也已有 shared summary-metric compare：静态 catalog 直接携带 `metric_values`，不再只看单一 primary metric
- `SPEC-19` catalog compare 现也已有 selected-panel deep-link navigation：compare tray / workspace 可直接跳到 `summary/timeline/memory/coverage`
- `SPEC-19` 现也已有 catalog/workbench round-trip navigation：从 compare drill-down 到 workbench 后可直接回到同一 catalog compare/filter 上下文
- `SPEC-19` static catalog 现在也可在 `workspace_root` 模式下直接显示 `Phase C Gate` 摘要，不必再单独打开 `phase_c_acceptance_report.json`
- `SPEC-19` static catalog 现在也可直接列出被 planner / downstream / missing / duplicate 挡住的 `Phase C` canonical cases，便于在 workspace 级别快速定位卡点
- `SPEC-19` static catalog 现在也可从这些 blocked-case 行直接跳到对应 packaged workbench，而且会优先按 structured downstream consumer / planner blocker 默认落到 `summary`、`memory` 或 `coverage` 面板；其中 `descriptor_generation` blocker 会直接落到 coverage 的 packed-descriptor section；这些链接会保留当前 catalog 的 `catalog_return` 上下文，并且 planner blocked case 在能识别到 overflow region 时会直接带 `memory_query` 预过滤到对应 region；只有 missing / duplicate 这类无具体 run 的 case 保持纯摘要
- `SPEC-10/11` 的 helper-store audit batch 已完成；后续以 acceptance list 维持稳定，不再默认继续宽泛铺开
- `SPEC-09` 现接受当前 GEMM-like / attention tiling + untiled-helper scheduling 作为 `M2` 收口范围
- `SPEC-08` 现在也已有 machine-readable closure artifact：`memory_planner_closure_report.json` 会枚举 required/optional downstream consumers 和 remaining gaps
- `SPEC-08` 现在也已有 workspace-level canonical acceptance artifact：`run-phase-c-acceptance` 会生成 `phase_c_acceptance_report.json`，统一汇总 `single-core/dual-core x prefill/decode` 四象限 matrix
- `run-phase-c-gate` 现已成为 `M2 / SPEC-08` 的正式 gate：它会复用同一份 matrix report，但在 canonical matrix 不是 `ready_for_acceptance` 时返回非零
- 把更强的调度时序信号继续喂给 `SPEC-13`
- `SPEC-12` 的 `M2` stop-line 现冻结为 packed summary consumer + workbench summary visibility
- `SPEC-12` 只做窄范围 hardening，不再作为唯一主线
- 现实里的验证瓶颈已经从 “full pytest 跑不完” 收敛到 “sweep / visualization packaging 仍然偏重”

参考文档：
- `docs/development/evaluation-compiler-roadmap.md`
- `docs/development/test-strategy-and-run-modes.md`
- `docs/development/mainline-test-recommendations.md`

## Progress Records And Start-Here Rules

Read these in order before starting new development work:

1. `README.md`
2. `docs/development/evaluation-compiler-roadmap.md`
3. the active execution plan in `docs/plans/`

Current active execution plan:

- `docs/plans/2026-03-14-phase-d-m3-closure-followup.md`

Canonical documentation roles:

- `docs/development/evaluation-compiler-roadmap.md`
  - the only project-status source for phase/spec state, audit checkpoints, priority order, and current blockers
- `docs/plans/*.md`
  - execution queues for one concrete slice or closure track
- `docs/development/phase-*-handoff.md`
  - stable contract and handoff boundaries
- `docs/development/evaluation-compiler-spec-pack.md`
  - spec definition only, not a progress log

Update rules after each work slice:

- if a change only refactors implementation details or completes a local helper extraction, update the active plan doc if needed, but do not create a second project-status summary
- if a change alters current status, verification reality, blockers, or execution priority, update `docs/development/evaluation-compiler-roadmap.md`
- if a change alters a stable contract or handoff boundary, update the relevant `docs/development/phase-*-handoff.md`
- if a change starts a new multi-step execution slice, add a new dated plan doc under `docs/plans/`

## 2026-03-14 Audited Status

Fresh verification evidence on 2026-03-14:

- `python -m pytest -q` -> `408 passed, 11 failed`
- `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
- `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`

Current working interpretation:

- accepted smoke scope is stable enough to keep producing canonical-path artifacts
- full-repository regression is not closed yet
- main priority remains `P0: close M3`
- `SPEC-19` stays `P1` hardening unless it directly helps close `M3`

Current execution order:

1. Restore the 11 failing full-regression checks.
2. Continue `SPEC-13 -> SPEC-14/15 -> SPEC-16` in roadmap order.
3. Resume `SPEC-19` hardening only after the `M3` path is back under control.
