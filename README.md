# llm-sched

RISC-V + NPU architecture-evaluation compiler for Gemma3-like workloads.

当前主线阶段：
- `M1` 已完成
- `M2` 已完成
- 当前重点仍然是 `Phase D / M3`，也就是继续收口 `SPEC-13/14/15/16`
- `SPEC-19` 继续做产品化 hardening，但应建立在当前稳定的 `SPEC-16` compare/workspace/workbench surface 之上
- `Phase C` 当前维持 keep-green，不再作为默认主线 blocker

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

当前全量基线（2026-03-19）：
- `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
- `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
- `python -m pytest -q --durations=30` -> `436 passed`

最新 compare/visualization 代表性 focused 验证（2026-03-21）：
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/contracts/test_visualization_bundle.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `39 passed`

full regression 仍然不适合作为默认开发循环；日常迭代优先跑 focused unit / pipeline / smoke 组合。

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
- `SPEC-16` 当前又新增了：
  - shared `compare focus modes`
  - shared `layer diff modes`
  - broader grouped compare focus
  - focused workspace candidate/detail/preset/analysis-flow state
  - analysis-flow bridge into workbench sweep/export
  - flow-ranked candidate inspection 与 recommendation metadata
- `SPEC-16` 最新又新增了：
  - focused workspace `Recommendation Queue`
  - top/previous/next recommended candidate navigation
  - queue-aware workspace JSON/SVG export metadata
- `SPEC-16` 现在也已把 recommendation queue 贯通到 workbench：
  - catalog -> workbench queue continuity
  - workbench sweep `Recommendation Queue` summary/actions
  - queue-aware sweep export metadata
- `SPEC-16` 现在也已补齐 dedicated sweep deep links：
  - `Open Sweep Panel` queue continuity
  - `Open Layer In Sweep` queue continuity
  - shared queue-aware workbench deep-link params
- `SPEC-16` workbench sweep 现在也已有：
  - `Top Recommendation Compare Strip`
  - top candidates 的 compact side-by-side inspection
- `SPEC-16` workbench sweep 现在也已补上更深一层的并排细节：
  - `Recommendation Detail Blocks`
  - top recommendations 的 explicit side-by-side candidate detail
  - estimated/fitted layer summaries embedded into the compare workflow
- `SPEC-16` workbench sweep 现在也已把这组并排细节接进导出链路：
  - `focused_recommendation_details` export payload
  - snapshot header `Top Recommendation Detail Candidates`
  - side-by-side detail summaries preserved in sweep snapshot text
- `SPEC-16` catalog workspace 现在也已和 workbench 对齐这组 richer compare state：
  - focused workspace `Recommendation Detail Blocks`
  - `focused_workspace_recommendation_details` export payload
  - catalog workspace snapshot continuity for top-candidate detail summaries
- `SPEC-16` 这组 recommendation detail continuity 现在也已有 shared builder 收敛：
  - shared detail layer summary helper
  - shared snapshot-line helper
  - catalog/workbench recommendation detail flows now reuse the same static JS builder pattern
- `SPEC-16` recommendation detail 的渲染结构现在也进一步收敛：
  - shared detail-entry markup helper
  - catalog/workbench detail blocks no longer maintain fully separate entry markup
- `SPEC-16 / SPEC-19` 的最新 closure audit 判断是：
  - 当前 recommendation-detail 这条 `SPEC-16` 子主线已经通过 closure pass，可按 practical stop-line 冻结
  - 下一步不该再默认继续发散更多同类交互，而应把 blocker review 拉回更上层的剩余 `SPEC-16` / `SPEC-13/14/15`
  - `SPEC-19` 继续作为 downstream polish，不应因为 convenience interaction 继续阻塞项目收尾
- `SPEC-16 / SPEC-19` 这条 closeout 判断已在 `2026-03-22` 用 fresh visualization proof 重新确认：
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `20 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- 项目级 closeout 判断也已在 `2026-03-22` 用 broader keep-green 重新确认：
  - `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `32 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed`
- 当前对 `SPEC-16 / SPEC-19` 更合理的解释已经进一步收敛：
  - `SPEC-16` recommendation-detail 分支继续保持冻结，除非后续 blocker audit 重新发现真实缺口
  - `SPEC-19` 当前 static catalog/workbench surface 已足够支撑项目 closeout，剩余 richer screenshot / convenience polish 不再作为默认收尾门槛
- 当前对整个项目更合理的解释也已经收敛：
  - 当前仓库主线已达到 `close-enough / practical stop-line`
  - 剩余工作默认归入 downstream polish、targeted follow-up 或 future research，而不是继续把项目保持在默认未收尾状态
  - 只有出现新的 concrete failing evidence 时，才应重新打开已冻结的 `SPEC-13/14/15/16/19` closeout judgment
- 当前推荐的执行方式已经进一步具体化：
  - `docs/plans/2026-03-21-spec-16-recommendation-detail-close-enough-checklist.md` 已完成本轮 closure 判定
  - recommendation-detail 这条子主线现在应保持冻结，除非后续 blocker review 重新发现真实缺口
- 当前更合理的下一步，不是回去重开 compare contract，也不是继续默认扩 recommendation-detail surface，而是把注意力转回剩余真实 blocker
- `SPEC-19` 仍然继续 hardening，但要严格以下游消费这套稳定 compare/export payload 为前提
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

- roadmap 的 `Current Next Slice`
- `docs/plans/2026-03-21-m3-close-out-blocker-audit.md`
- `docs/plans/2026-03-21-spec-14-15-eval-compare-closure.md`
- `docs/plans/2026-03-21-spec-14-15-residual-blocker-audit.md`
- `docs/plans/2026-03-21-spec-13-fit-gap-summary.md`
- `docs/plans/2026-03-21-spec-13-critical-path-fit-gap-decomposition.md`
- `docs/plans/2026-03-21-spec-13-fit-floor-source-summary.md`
- `docs/plans/2026-03-21-spec-13-compare-grade-estimator-summary.md`
- 最新已落盘的 `SPEC-16` execution slices 位于：
  - `docs/plans/2026-03-20-spec-16-*.md`
  - `docs/plans/2026-03-21-spec-16-analysis-flow-candidate-inspection.md`
  - `docs/plans/2026-03-21-spec-16-recommendation-queue.md`
  - `docs/plans/2026-03-21-spec-16-workbench-recommendation-queue-continuity.md`
  - `docs/plans/2026-03-21-spec-16-sweep-deeplink-queue-continuity.md`
  - `docs/plans/2026-03-21-spec-16-workbench-top-recommendation-compare-strip.md`
  - `docs/plans/2026-03-21-spec-16-workbench-recommendation-detail-blocks.md`
  - `docs/plans/2026-03-21-spec-16-workbench-detail-export-continuity.md`
  - `docs/plans/2026-03-21-spec-16-catalog-recommendation-detail-continuity.md`
  - `docs/plans/2026-03-21-spec-16-recommendation-detail-shared-builders.md`
- `docs/plans/2026-03-21-spec-16-recommendation-detail-shared-renderers.md`
- `docs/plans/2026-03-21-spec-16-spec-19-closure-audit.md`
- `docs/plans/2026-03-21-spec-16-recommendation-detail-close-enough-checklist.md`
- `docs/plans/2026-03-22-spec-16-spec-19-closeout.md`
- `docs/plans/2026-03-22-project-closeout-audit.md`

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

## 2026-03-21 Audited Status

Fresh verification evidence currently reflected in project status:

- `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
- `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
- `python -m pytest -q --durations=30` -> `436 passed` on the last full-project audited checkpoint (`2026-03-19`)
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/contracts/test_visualization_bundle.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `39 passed` (`2026-03-21`)
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/smoke/test_cli_run_visualization_catalog.py -q` -> `17 passed` (`2026-03-21`)
- `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `28 passed` (`2026-03-21`)

Current working interpretation:

- `Phase A/B/C` 主线已稳定，`run-phase-c-gate` 对应的 canonical matrix 继续维持 keep-green
- `SPEC-13/14/15` 已具备稳定的评估与 compare foundation，当前真正的主 blocker 是继续把 `SPEC-16` compare/workspace/workbench workflow 做完整
- `SPEC-16` 当前已经从基础 compare surface 推进到：
  - compare focus modes
  - layer diff modes
  - broader compare grouping
  - focused workspace candidate/detail/preset/analysis-flow
  - analysis-flow workbench bridge
  - analysis-flow-ranked candidate inspection
  - recommendation-queue navigation and export continuity
  - catalog-to-workbench recommendation queue continuity
  - fully queue-aware sweep deep-link continuity
  - top-recommendation side-by-side inspection in workbench sweep
  - explicit recommendation detail blocks in workbench sweep
  - multi-candidate detail export/snapshot continuity in workbench sweep
  - aligned recommendation detail continuity in catalog workspace/export
  - shared recommendation detail builder pattern across catalog/workbench
  - shared recommendation detail renderer pattern across catalog/workbench
- 当前更合理的下一步不再是默认继续扩 recommendation-detail surface，而是接受这条 recommendation-detail 子主线已经达到 stop-line，并把注意力转回剩余真实 blocker
- 当前更具体的下一步是先执行 `docs/plans/2026-03-21-m3-close-out-blocker-audit.md`，把 `SPEC-13/14/15/16` 的剩余真实 blocker 重新分层，再决定最后一条主执行线
- 这轮更高层 blocker audit 的第一版结论是：
  - 当前最值得优先推进的主执行线不是再做 recommendation-detail，也不是先做 `SPEC-19` polish
  - 推荐把下一条主执行线收敛到 `SPEC-14/15` eval-compare closure，并让后续 `SPEC-16` 只做最小必要消费面
- 这条主执行线现在已经落成 focused plan：
  - `docs/plans/2026-03-21-spec-14-15-eval-compare-closure.md`
  - 当前建议继续沿 compare artifact 收口，先补强 `PhaseDCompareReport`，而不是先扩 UI
- 这条 focused slice 的当前执行结果是：
  - `PhaseDCompareReport` 已补上 row-level `verdict_summary` 和 top-level `prefill_summary` / `decode_summary`
  - `SweepRunRecord` / `SweepComparison` / `PhaseDDecodeCompareRow` 已补上 structured `kv_len`
  - `PhaseDCompareReport` 已补上 `decode_kv_len_summaries`
  - `PhaseDCompareReport` 已补上 `decode_latency_decomposition_summary`
  - `PhaseDCompareReport` 已补上 `prefill_layer_decomposition_summary`
  - `PhaseDCompareReport` 已补上 `cross_mode_summaries`
  - focused compare regression 已 fresh 通过：`14 passed`
  - visualization keep-green 已 fresh 通过：`28 passed`
  - `local_smoke` 已 fresh 通过：`11 passed, 70 deselected`
  - `milestone_matrix` 已 fresh 通过：`11 passed, 70 deselected`
  - decode `kv_len` aggregation regression 已 fresh 通过：`26 passed`
  - decode token-latency decomposition regression 已 fresh 通过：`26 passed`
  - prefill layer decomposition regression 已 fresh 通过：`27 passed`
  - cross-mode compare closure regression 已 fresh 通过：`28 passed`
  - `SPEC-14/15` residual blocker audit 已落盘：`docs/plans/2026-03-21-spec-14-15-residual-blocker-audit.md`
  - 这说明 `SPEC-14/15` 当前已具备 decode 侧的 `kv_len` / token-latency 收口、prefill 侧的 layer decomposition，以及 standalone compare artifact 内的 cross-mode closure；这条 compare-closure 子主线现在可以按 practical stop-line 冻结
- 当前执行顺序应保持：

1. 先沿 `docs/plans/2026-03-21-m3-close-out-blocker-audit.md` 和 `docs/plans/2026-03-21-spec-14-15-residual-blocker-audit.md` 收口当前 `M3` blocker 重排。
2. 继续用 `run-phase-c-gate`、`local_smoke`、`milestone_matrix` 保持 `SPEC-08/09/10/11/12` 绿色。
3. 下一刀优先转回 `SPEC-13` deeper cycle fitting / compare-grade estimator aggregation，而不是回头扩 recommendation-detail、重开当前 `SPEC-14/15` compare closure，或提前做 `SPEC-19` polish。

- `SPEC-13` focused close-out slice 已启动：
  - `docs/plans/2026-03-21-spec-13-fit-gap-summary.md`
  - `docs/plans/2026-03-21-spec-13-critical-path-fit-gap-decomposition.md`
  - `docs/plans/2026-03-21-spec-13-fit-floor-source-summary.md`
  - `docs/plans/2026-03-21-spec-13-compare-grade-estimator-summary.md`
  - `docs/plans/2026-03-21-spec-13-residual-external-stall-fitting.md`
  - `docs/plans/2026-03-21-spec-13-shared-dma-bidirectional-stall.md`
  - `docs/plans/2026-03-21-spec-13-fit-floor-direction-summary.md`
  - `docs/plans/2026-03-21-spec-13-external-write-drain-overlap.md`
  - `docs/plans/2026-03-21-spec-13-schedule-slack-write-absorption.md`
  - `docs/plans/2026-03-21-spec-13-close-enough-checklist.md`
  - `PerfSummaryReport` 已补上 `fit_gap_summary`、`critical_path_fit_gap_summary` 和 `fit_floor_source_summary`
  - compute fitted-cycle math 现已从 `max(schedule_floor, external_read_floor)` 推进到 residual external stall model：保留 `schedule_floor`，只叠加未被 `estimated_cycles` 吸收的 external-read stall
  - compute fitted-cycle math 现又进一步覆盖 shared-DMA bidirectional stall：external writes 与 read/write contention 也会抬升 `external_bandwidth_floor_cycles` 与 `fitted_work_cycles`
  - canonical perf artifact 现也补上 `fit_floor_direction_summary`，可以直接区分 external read / write floor 谁在主导当前 external-bandwidth uplift
  - overlap budgeting 现已进一步收紧成 direction-aware math：external reads 继续共享 compute overlap budget，而 external writes 现在按 write-drain 处理，不再默认被 `estimated_cycles` 吸收
  - overlap budgeting 现又进一步引入 schedule-slack write absorption：`schedule_floor - estimated_cycles` 这部分 slack 会先吸收一部分 external write drain，避免在有排程余量时继续过度悲观
  - `PhaseDCompareReport` 已补上 `prefill_estimator_summary` 和 `decode_estimator_summary`
  - focused `SPEC-13` deeper-cycle regression 已 fresh 通过：`python -m pytest tests/unit/analysis/test_descriptor_estimator.py tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_phase_d_perf_foundation_matrix.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `32 passed`
  - downstream `SPEC-14/15` unit/workflow/smoke regression 已 fresh 通过：`python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
  - `SPEC-13` 当前 closure pass 的判断是：已经达到 practical stop-line，可以按 `close-enough` 冻结
  - 剩余内容更像 fidelity polish 或后续 estimator research，不再是应该默认继续阻塞项目收尾的 blocker
