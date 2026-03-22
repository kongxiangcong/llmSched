# RISC-V + NPU 评估编译器开发文档

这里收敛的是“面向架构评估”的编译器工程规格和开发检查点，不是面向冻结 RTL 芯片的生产编译器。目标是把 Gemma3 这类模型拆成可映射到 RISC-V + NPU 架构问题上的工作负载单元，并支撑单核 / 双核、prefill / decode 的建模、仿真、性能估算、带宽压力和瓶颈分析。

## 文档索引

- `evaluation-compiler-spec-pack.md`
  - 顶层 spec 包，定义系统目标、分层原则和完整 SPEC 清单。
- `evaluation-compiler-roadmap.md`
  - 当前 roadmap 与收口判断的主参考，包括 2026-03-22 project closeout audit 和 `close-enough / practical stop-line` 结论。
- `project-status-summary-2026-03-22.md`
  - 当前项目状态、Phase A-E 落地能力、收口判断和下一步建议的简明 handoff 摘要。
- `test-strategy-and-run-modes.md`
  - 当前测试分层、默认回归模式、`local_smoke / milestone_matrix` 的使用方式，以及慢测试优化检查点。
- `mainline-test-recommendations.md`
  - 面向 `master` 合入和后续主线运行的测试建议，包括 merge gate、`local_smoke`、`milestone_matrix` 和全量回归的使用边界。
- `phase-a-foundation-handoff.md`
  - 当前 Phase A / frontend 主线的稳定契约、CLI 流程和真实模型状态。
- `phase-b-semantic-handoff.md`
  - Phase B 关闭后的 bound-NIG 契约、artifact 清单和进入 Phase C 的前提。
- `phase-c-memory-planner-handoff.md`
  - `SPEC-08` foundation 的 memory plan 契约、四象限基线和进入 `SPEC-09` 的前提。
- `phase-c-tile-planner-handoff.md`
  - `SPEC-09` foundation 的 tiling contract、CLI/workflow 入口和进入 `SPEC-10/11` 的当前前提。
- `phase-c-single-core-scheduler-handoff.md`
  - `SPEC-10` foundation 的 `ScheduleIR` contract、single-core CLI/workflow 入口和进入 `SPEC-12` 的当前前提。
- `phase-c-dual-core-scheduler-handoff.md`
  - `SPEC-11` foundation 的 dual-core `ScheduleIR` contract、dual-core CLI/workflow 入口和进入 `SPEC-12` 的当前前提。
- `phase-c-descriptor-handoff.md`
  - `SPEC-12` foundation 的 `DescriptorIR` / `ISACoverageReport` contract、descriptor-generation CLI/workflow 入口和进入 `SPEC-13` 的当前前提。
- `phase-d-performance-foundation-handoff.md`
  - `SPEC-13` foundation 的 `perf_analysis_ir` / `PerfSummaryReport` contract、performance-estimation CLI/workflow 入口和进入 `SPEC-14/15` 的当前前提。
- `phase-d-prefill-foundation-handoff.md`
  - `SPEC-14` foundation 的 `PrefillEvaluationReport` contract、prefill-evaluation CLI/workflow 入口和进入 `SPEC-15/16` 的当前前提。
- `phase-d-decode-foundation-handoff.md`
  - `SPEC-15` foundation 的 `DecodeEvaluationReport` contract、decode-evaluation CLI/workflow 入口和进入 `SPEC-16/18` 的当前前提。
- `../plans/2026-03-06-phase-a-foundation-story-backlog.md`
  - Phase A 基础 backlog。
- `../plans/2026-03-06-graph-ir-import-canonicalization.md`
  - Graph frontend 第一批导入与 canonicalization。
- `../plans/2026-03-06-gemma3-patterns-legality-nig-lowering.md`
  - Gemma3 pattern、legality、NIG lowering 第一批。
- `../plans/2026-03-06-frontend-shape-binding.md`
  - scenario-aware shape binding。
- `../plans/2026-03-06-profile-aware-legality-and-residual-decomposition.md`
  - target-aware legality 和 `ResidualAdd`。
- `../plans/2026-03-07-embedding-rope-table-and-fallback-decomposition.md`
  - `EmbeddingLookup`、`ROPETable`、`ShapeHelper`、`LayoutFallback`。
- `../plans/2026-03-07-attention-mask-prep-decomposition.md`
  - `AttentionMaskPrep` 和 `SDPA` score scaling 吸收。
- `../plans/2026-03-07-pseudo-fallback-estimator-foundation.md`
  - pseudo/fallback workload 的第一版 AnalysisIR estimator。
- `../plans/2026-03-07-frontend-analysis-cli-integration.md`
  - `run-frontend-analysis` CLI、run artifact 和 report integration。
- `../plans/2026-03-07-phase-b-closure-backlog.md`
  - Phase B 正式收口 backlog，覆盖 `SPEC-03/04/07`。
- `../plans/2026-03-07-spec-08-vmem-kv-planner.md`
  - Phase C 第一批：`SPEC-08` 的 VMEM / KV / address planner foundation。
- `../plans/2026-03-09-spec-08-lifetime-reuse.md`
  - Phase C hardening：`SPEC-08` 的 phase-bucket lifetime reuse。
- `../plans/2026-03-09-spec-08-ddr-binding-realism.md`
  - Phase C hardening：`SPEC-08` 的 DDR-backed binding realism。
- `../plans/2026-03-09-spec-08-fit-reasoning.md`
  - Phase C hardening：`SPEC-08` 的 source-class-aware fit reasoning。
- `../plans/2026-03-09-spec-10-11-phased-engine-reservations.md`
  - Phase C hardening：`SPEC-10/11` 的 phased engine reservation fidelity。
- `../plans/2026-03-09-spec-10-11-geglu-resource-specialization.md`
  - Phase C hardening：`SPEC-10/11` 的 `GEGLU` mixed-engine scheduler specialization。
- `../plans/2026-03-09-spec-10-11-vector-duration-specialization.md`
  - Phase C hardening：`SPEC-10/11` 的 vector-family duration specialization。
- `../plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md`
  - Phase C hardening：`SPEC-10/11` 的 mixed-engine compute duration specialization。
- `../plans/2026-03-07-spec-09-tile-candidate-planner.md`
  - Phase C 第二批：`SPEC-09` 的 tile candidate planner foundation。
- `../plans/2026-03-07-spec-10-single-core-scheduler.md`
  - Phase C 第三批：`SPEC-10` 的 deterministic single-core scheduler foundation。
- `../plans/2026-03-07-spec-11-dual-core-scheduler.md`
  - Phase C 第四批：`SPEC-11` 的 deterministic dual-core scheduler foundation。
- `../plans/2026-03-07-spec-12-descriptor-isa-mapping.md`
  - Phase C 第五批：`SPEC-12` 的 deterministic descriptor generation 和 ISA coverage foundation。
- `../plans/2026-03-07-spec-13-performance-estimator-foundation.md`
  - Phase D 第一批：`SPEC-13` 的 descriptor-driven performance estimation foundation。
- `../plans/2026-03-07-spec-14-prefill-eval-pipeline.md`
  - Phase D 第二批：`SPEC-14` 的 prefill-only top-level evaluation foundation。
- `../plans/2026-03-07-spec-15-decode-eval-pipeline.md`
  - Phase D 第三批：`SPEC-15` 的 decode-only top-level evaluation foundation。

## 当前 frontend / analysis 入口

- `llm_sched.frontend.import_onnx_to_graph_ir(model_path_or_proto, shape_bindings=None)`
  - 导入 `ONNX -> GraphIR`，显式生成 `Input` / `Constant` / 原始 ONNX 节点，保留 `source_ref` / `audit_ref`。
- `llm_sched.frontend.load_gemma_model_metadata(path)`
- `llm_sched.frontend.build_gemma3_shape_bindings(metadata, scenario)`
  - 用 `ScenarioProfile` 绑定 `batch_size` / `sequence_length` / `past_sequence_length` 和 KV cache 输入维度。
- `llm_sched.frontend.validate_frontend_legality(graph_ir, hardware=None)`
  - 做结构准入和 target-aware legality 检查。
- `llm_sched.frontend.canonicalize_graph_ir(graph_ir)`
  - 做语义归一化和显式 fallback 建模。
- `llm_sched.frontend.lower_graph_ir_to_nig(graph_ir, scenario=None)`
  - 把 canonical Graph IR lower 到第一版 NIG workload 图。
- `llm_sched.analysis.estimate_nig_analysis(nig_ir, hardware)`
  - 对 pseudo/fallback workload 输出第一版 `AnalysisIR`，当前覆盖 bytes / abstract cycles / bottleneck tags。
- `llm_sched.analysis.estimate_descriptor_analysis(descriptor_ir, coverage_report, hardware, scenario)`
  - 对 `DescriptorIR` 输出 descriptor-driven `AnalysisIR`，当前覆盖 compute / DMA / transfer / ISA gap 的抽象性能估算。
- `llm_sched.analysis.build_perf_summary_report(run_id, descriptor_ir, analysis_ir, coverage_report, schedule_ir=None)`
  - 基于 `DescriptorIR + AnalysisIR + ISACoverageReport` 输出第一版 `PerfSummaryReport`。
- `llm_sched.analysis.build_prefill_evaluation_report(run_id, scenario, perf_summary, coverage_report, memory_plan)`
  - 基于 `PerfSummaryReport + ISACoverageReport + MemoryPlanArtifact` 输出第一版 `PrefillEvaluationReport`。
- `llm_sched.analysis.build_decode_evaluation_report(run_id, scenario, perf_summary, coverage_report, memory_plan)`
  - 基于 `PerfSummaryReport + ISACoverageReport + MemoryPlanArtifact` 输出第一版 `DecodeEvaluationReport`。
- `llm_sched.planning.plan_memory_artifact(bound_nig_ir, hardware, scenario)`
  - 基于 bound-NIG 输出第一版 `MemoryPlanArtifact`，当前覆盖静态 VMEM region 规划、KV 地址公式和 VMEM fit 诊断。
- `llm_sched.planning.plan_tiling_artifact(bound_nig_ir, memory_plan, hardware, scenario)`
  - 基于 bound-NIG + `MemoryPlanArtifact` 输出第一版 `TilingPlanArtifact`，当前覆盖 GEMM-like 和 attention 的 tile candidate foundation。
- `llm_sched.planning.plan_single_core_schedule(bound_nig_ir, memory_plan, tiling_plan, hardware, scenario)`
  - 基于 bound-NIG + memory plan + tiling plan 输出第一版 `ScheduleIR`，当前覆盖 deterministic single-core block scheduling foundation。
- `llm_sched.planning.plan_dual_core_schedule(bound_nig_ir, memory_plan, tiling_plan, hardware, scenario)`
  - 基于 bound-NIG + memory plan + tiling plan 输出第一版 dual-core `ScheduleIR`，当前覆盖 deterministic core assignment / transfer / barrier foundation。
- `llm_sched.planning.build_descriptor_artifacts(schedule_ir, bound_nig_ir, memory_plan, hardware, scenario)`
  - 基于 `ScheduleIR`、bound-NIG 和 memory plan 输出第一版 `DescriptorIR` 与 `ISACoverageReport`，当前覆盖 deterministic descriptor mapping 和 unsupported gap reporting foundation。
- `llm_sched.pipeline.run_frontend_analysis(run_root)`
  - 读取 `manifest.json`，执行 `ONNX -> GraphIR -> canonical GraphIR -> NIG -> bound-NIG -> AnalysisIR`，并写回 run-root artifacts 和 reports。
- `llm_sched.pipeline.run_memory_planning(run_root)`
  - 消费 `bound_nig_ir` 并写出 `artifacts/memory_plan.json`。
- `llm_sched.pipeline.run_tile_planning(run_root)`
  - 消费 `bound_nig_ir` 和 `artifacts/memory_plan.json`，写出 `artifacts/tiling_plan.json`。
- `llm_sched.pipeline.run_single_core_scheduling(run_root)`
  - 消费 `bound_nig_ir`、`memory_plan.json` 和 `tiling_plan.json`，写出 `artifacts/schedule_ir.json`。
- `llm_sched.pipeline.run_dual_core_scheduling(run_root)`
  - 消费 `bound_nig_ir`、`memory_plan.json` 和 `tiling_plan.json`，写出 `artifacts/dual_core_schedule_ir.json`。
- `llm_sched.pipeline.run_descriptor_generation(run_root)`
  - 消费 `bound_nig_ir`、`memory_plan.json` 与 schedule artifact，写出 `artifacts/descriptor_ir.json` 和 `reports/isa_coverage_report.json`。
- `llm_sched.pipeline.run_performance_estimation(run_root)`
  - 消费 `descriptor_ir.json`、`isa_coverage_report.json`、`memory_plan.json` 与 schedule artifact，写出 `artifacts/perf_analysis_ir.json` 和 `reports/perf_summary_report.json`。
- `llm_sched.pipeline.run_prefill_evaluation(run_root)`
  - 消费 `perf_summary_report.json`、`isa_coverage_report.json` 和 `memory_plan.json`，写出 `reports/prefill_evaluation_report.json`。
- `llm_sched.pipeline.run_decode_evaluation(run_root)`
  - 消费 `perf_summary_report.json`、`isa_coverage_report.json` 和 `memory_plan.json`，写出 `reports/decode_evaluation_report.json`。

## 当前 CLI 入口

- `llm-sched validate-profile --target-profile ... --scenario-profile ...`
  - 校验 target / scenario profile。
- `llm-sched init-run --run-root ... --model-path ... --target-profile ... --scenario-profile ...`
  - 初始化 run 目录、`manifest.json`、`run-summary.json`。
- `llm-sched run-frontend-analysis --run-root ...`
  - 基于已初始化 run 执行 frontend import / canonicalize / legality / lowering / pseudo-fallback analysis。
- `llm-sched run-memory-planning --run-root ...`
  - 基于已有 `bound_nig_ir` 执行 `SPEC-08` 静态内存规划。
- `llm-sched run-tile-planning --run-root ...`
  - 基于已有 `bound_nig_ir` 和 `memory_plan.json` 执行 `SPEC-09` tile candidate planning。
- `llm-sched run-single-core-scheduling --run-root ...`
  - 基于已有 `bound_nig_ir`、`memory_plan.json` 和 `tiling_plan.json` 执行 `SPEC-10` deterministic single-core scheduling。
- `llm-sched run-dual-core-scheduling --run-root ...`
  - 基于已有 `bound_nig_ir`、`memory_plan.json` 和 `tiling_plan.json` 执行 `SPEC-11` deterministic dual-core scheduling。
- `llm-sched run-descriptor-generation --run-root ...`
  - 基于已有 schedule artifact、`bound_nig_ir` 和 `memory_plan.json` 执行 `SPEC-12` deterministic descriptor generation 和 ISA coverage mapping。
- `llm-sched run-performance-estimation --run-root ...`
  - 基于已有 descriptor artifact、coverage report、`memory_plan.json` 和 schedule artifact 执行 `SPEC-13` descriptor-driven performance estimation。
- `llm-sched run-prefill-evaluation --run-root ...`
  - 基于已有 perf summary、coverage report 和 `memory_plan.json` 执行 `SPEC-14` prefill top-level evaluation。
- `llm-sched run-decode-evaluation --run-root ...`
  - 基于已有 perf summary、coverage report 和 `memory_plan.json` 执行 `SPEC-15` decode top-level evaluation。

当前 CLI 边界：

- `init-run` 只做 run 初始化，不执行编译分析。
- `run-frontend-analysis` 是当前 frontend 端到端主线入口。
- `run-memory-planning` 是稳定的 Phase C 独立入口，已包含 lifetime reuse、DDR-backed binding 和 fit reasoning hardening。
- `run-tile-planning`、`run-single-core-scheduling`、`run-dual-core-scheduling`、`run-descriptor-generation` 已构成完整的 Phase C 主线。
- `run-performance-estimation`、`run-prefill-evaluation`、`run-decode-evaluation` 已构成完整的 Phase D 评估主线。
- `run-sweep-analysis` 与 `run-phase-d-compare` 已提供 prefill / decode 的单核对双核 compare 路径。
- `run-visualization-packaging`、`run-visualization-workbench`、`run-visualization-catalog` 已构成稳定的静态可视化输出路径。

## End-to-End Runner

- script: `scripts/run_end_to_end.py`
- purpose: 用一条命令串起从 `init-run` 到 evaluation、visualization、optional sweep compare、final catalog 的完整仓库主线
- output root: `.runs/<run-name>/`

推荐命令：

```powershell
& "C:\Users\72449\AppData\Roaming\Python\Python314\Scripts\uv.exe" run --python .venv\Scripts\python.exe python scripts\run_end_to_end.py --model-path models\gemma3_1b\model_q4f16.onnx --core-mode both --eval-mode both --run-name full-e2e-demo
```

支持的输入：

- `--core-mode`: `single` / `single-core` / `dual` / `dual-core` / `both`
- `--eval-mode`: `prefill` / `decode` / `both`

常用示例：

```powershell
# single-core + decode
& "C:\Users\72449\AppData\Roaming\Python\Python314\Scripts\uv.exe" run --python .venv\Scripts\python.exe python scripts\run_end_to_end.py --model-path models\gemma3_1b\model_q4f16.onnx --core-mode single-core --eval-mode decode --run-name decode-single

# dual-core + prefill
& "C:\Users\72449\AppData\Roaming\Python\Python314\Scripts\uv.exe" run --python .venv\Scripts\python.exe python scripts\run_end_to_end.py --model-path models\gemma3_1b\model_q4f16.onnx --core-mode dual-core --eval-mode prefill --run-name prefill-dual
```

最新完整验证：

- session: `.runs/full-e2e-demo/`
- result: 4 runs completed, 2 sweeps completed, final catalog generated

## 2026-03-19 Real-Model Checkpoint

- real Gemma3 frontend import/canonicalize/lowering 已重新打通，`canonical Graph IR -> NIG` 的 unsupported lowering nodes 现在是 `0`
- `run-frontend-analysis` CLI smoke 已恢复通过
- 当前测试 checkpoint：
  - `python -m pytest tests/smoke -m local_smoke -q` -> `11 passed, 70 deselected`
  - `python -m pytest tests/smoke -m milestone_matrix -q` -> `11 passed, 70 deselected`
  - `python -m pytest -q --durations=30` -> `436 passed`
- 当前 remaining blockers 已不再停留在 real-model frontend / Phase B/C checkpoint：
  - `dynamic_shape_unresolved` 已清零
  - SDPA rope-cache auxiliary input 已不再错误计入 staged `weight`
  - `run-phase-c-gate` / acceptance matrix 已回到 green checkpoint
- 因此当前项目状态更准确地说是：
  - `Phase B = done`
  - `Phase C = done`
  - `Phase D/E = in_progress`
- 当前主线已重新回到 `M3` 收口与 `SPEC-19` hardening。

## 2026-03-22 Closeout Status Refresh

- 当前状态跟踪应以 `evaluation-compiler-roadmap.md` 和 `project-status-summary-2026-03-22.md` 为准。
- 当前仓库已经达到 `close-enough / practical stop-line`，默认不再把项目视为“仍缺少核心主线能力”。
- `Phase B`、`Phase C` 维持 `done`。
- `Phase D/E = in_progress` 现在更准确的含义是“仍有 polish 和按需 follow-up”，而不是“端到端主链路未闭环”。
- `SPEC-13`、当前 `SPEC-14/15` 评估链路、当前 `SPEC-16` recommendation-detail surface、当前 `SPEC-19` catalog/workbench surface 都应视为 practical closeout，除非出现新的 failing evidence。

## 2026-03-20 SPEC-13 Pressure Summary Checkpoint

- `PerfSummaryReport` 新增了 summary-grade `bandwidth_pressure_summary` 与 `vmem_pressure_summary`。
- 这两个字段直接复用现有 `AnalysisIR` bandwidth metrics、address-space/backing-store/memory-class breakdown 和 `MemoryPlanArtifact.region_summaries`，不重新定义 estimator 数学。
- 当前 focused verification：
  - `python -m pytest tests/unit/contracts/test_perf_report.py tests/unit/analysis/test_perf_summary_builder.py tests/unit/pipeline/test_performance_estimation_workflow.py tests/smoke/test_cli_run_performance_estimation.py -q` -> `12 passed`
- 这让后续 `SPEC-14/15/16/19` 可以直接消费一个更稳定、更可读的 pressure summary surface，而不必各自重组原始 breakdown maps。

## 2026-03-20 SPEC-14/15 Pressure Summary Adoption Checkpoint

- `PrefillEvaluationReport` 和 `DecodeEvaluationReport` 现在都直接暴露：
  - `bandwidth_pressure_summary`
  - `vmem_pressure_summary`
- 这一步没有重算 pressure，也没有发明 report-local 的新格式，而是直接复用 `SPEC-13` 的 summary-grade contract。
- 当前 focused verification：
  - `python -m pytest tests/unit/analysis/test_prefill_report_builder.py tests/unit/analysis/test_decode_report_builder.py tests/unit/pipeline/test_prefill_evaluation_workflow.py tests/unit/pipeline/test_decode_evaluation_workflow.py tests/smoke/test_phase_d_prefill_foundation_matrix.py tests/smoke/test_phase_d_decode_foundation_matrix.py -q` -> `16 passed`
- 这让下一步 `SPEC-16` 做 compare adoption 时可以直接消费 prefill/decode report 里的稳定 pressure summary，而不必回头再从 `PerfSummaryReport` 单独拼装。

## 2026-03-20 SPEC-16 Pressure Compare Adoption Checkpoint

- `SweepRunRecord` 现在保留 summary-grade `bandwidth_pressure_summary` 与 `vmem_pressure_summary`，不再只保留数值 metrics。
- `SweepComparison` 新增：
  - `bandwidth_pressure_compare`
  - `vmem_pressure_compare`
- `PhaseDCompareReport` 的 prefill/decode compare rows 现在也透传这两个 compare summary，后续 `SPEC-19` 可以直接消费更语义化的 compare surface。
- 这一步仍然是窄切片：
  - 没有重开 estimator 数学
  - 没有改 visualization workbench
  - 只把现有 pressure summary 提升成 compare-grade contract
- 当前 focused verification：
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_phase_d_compare_report_builder.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q` -> `18 passed`
  - `python -m pytest tests/unit/pipeline/test_sweep_analysis_workflow.py tests/smoke/test_cli_run_phase_d_compare.py -q` -> `4 passed`

## 2026-03-20 SPEC-16 Visualization Pressure Compare Adoption Checkpoint

- `VisualizationBundle.compare_summary` 与 catalog manifest compare summary 现在都会直接透传：
  - `bandwidth_pressure_compare`
  - `vmem_pressure_compare`
- `SPEC-19` workbench 与 catalog compare surface 现在都会直接渲染：
  - `Peak Bandwidth Pressure`
  - `VMEM Pressure Shifts`
- 这一步保持窄切片：
  - 不重开 compare contract 设计
  - 不新增 service/API
  - 只把既有 `SPEC-16` pressure compare surface 接到 visualization payload 与 renderer
- 当前 focused verification：
  - `python -m pytest tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `22 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `8 passed`

## 2026-03-20 SPEC-16 Grouped Metric Delta Checkpoint

- `SweepComparison` 现在新增：
  - `metric_delta_groups`
  - `baseline_schedule_kind`
  - `candidate_schedule_kind`
- 这让 raw `SweepDeltaReport` 也能直接暴露 grouped multi-metric compare，而不再只剩一张平铺 `metric_deltas` 列表。
- `run-visualization-packaging` 现在即使没有 `PhaseDCompareReport`，也能从 raw sweep compare 合成稳定的 compare summary，继续复用 workbench/catalog 现有 grouped compare 渲染路径。
- 这一步依然保持窄切片：
  - 不重开 estimator 数学
  - 不新增新的 compare group taxonomy
  - 只把现有 metric delta surface 提升成 grouped compare-grade contract，并补上 raw packaging adoption
- 当前 focused verification：
  - `python -m pytest tests/unit/contracts/test_sweep_report.py tests/unit/analysis/test_sweep_report_builder.py tests/unit/analysis/test_visualization_bundle_builder.py -q` -> `15 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_phase_d_compare_workflow.py -q` -> `6 passed`
  - `python -m pytest tests/smoke/test_cli_run_phase_d_compare.py -q` -> `2 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py -q` -> `2 passed`

## 当前 canonical / lowering surface

### Canonical Graph IR

- `Identity` elimination
- `MatMul + Add -> Linear`
- `MatMul(const-weight) -> Linear`
- `MatMulNBits -> Linear`
- `EmbeddingLookup`
- `ROPETable`
- `RMSNorm`
- `GeGLU`
- `ROPE`
- `KVStore`
- `KVLoad`
- `SDPA`
- `ResidualAdd`
- `AttentionMaskPrep`
- `ShapeHelper`
- `LayoutFallback`

补充约定：

- `SDPA` 会吸收 q/k score scaling 的 `Mul(tensor, constant)`，并在 attrs 中记录 `query_scale_tensor` / `key_scale_tensor`。
- `AttentionMaskPrep` 只覆盖 attention mask 路径上的 arithmetic / mask-construction 节点，例如 `Add`、`Sub`、`Mul`、`Max`、`Trilu`、`Greater`、`Neg`、`ScatterND`。
- 纯 shape / layout helper 仍留在 `ShapeHelper` / `LayoutFallback`，不并入 `AttentionMaskPrep`。

### NIG macro-op

- `GEMM`
- `WDQ_GEMM`
- `RMSNORM`
- `RMSNORM_GEMM`
- `GEGLU`
- `ROPE`
- `KVSTORE`
- `KVLOAD`
- `ELEM_ADD`
- `SDPA`
- `SDPA_DECODE`
- `EMBEDDING_LOOKUP`
- `ROPE_TABLE`
- `ATTENTION_MASK_PREP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`

### NIG workload metadata

`NIGNode` 现在保留两类可估算元数据：

- `shape`
  - 当前 macro-op 的输出 shape，用于 bytes / abstract cycles 估算。
- `attrs`
  - frontend canonical 阶段已识别出的语义提示，例如 `query_len` / `kv_len` / `head_dim` / `original_op_kind` / `scaled_output` / `transpose_applied`。

这些字段不是为了重建 Graph IR，而是为了让 analysis / schedule 层不必再回头依赖 frontend 内部节点细节。

## 当前 run artifact

执行 `llm-sched run-frontend-analysis --run-root <path>` 后，会在 run 目录内写出：

### Dumps

- `dumps/graph_ir.json`
- `dumps/canonical_graph_ir.json`
- `dumps/nig_ir.json`
- `dumps/bound_nig_ir.json`
- `dumps/analysis_ir.json`

### Reports

- `reports/frontend_import_report.json`
- `reports/workload_decomposition_report.json`
- `reports/frontend_binding_report.json`
- `reports/frontend_legality.json`
  - `issue_counts`
  - `issues`
- `reports/pseudo_fallback_summary.json`
  - `record_counts`
  - `tag_counts`
  - `totals`
  - `total_bytes_by_macro`
  - `estimated_cycles_by_macro`

### Run state update

- `artifacts/memory_plan.json`
- `manifest.json`
  - `status` 更新为 `completed` 或 `failed`
  - `artifact_index` 追加 dumps / reports 路径
- `run-summary.json`
  - 记录本次 frontend analysis 的 `status`、`exit_code` 和 diagnostics

## Pseudo/fallback estimator scope

当前 `estimate_nig_analysis(...)` 只覆盖这些 pseudo/fallback surface：

- `ATTENTION_MASK_PREP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`
- `EMBEDDING_LOOKUP`
- `ROPE_TABLE`

输出是轻量、可解释、可稳定比较的抽象指标，不是 RTL/cycle-accurate 仿真：

- `read_bytes`
- `write_bytes`
- `total_bytes`
- `estimated_cycles`
- `bandwidth_pressure`
- bottleneck tags，例如 `memory-bound`、`metadata-bound`、`compute-bound`

如果节点仍带有未收敛动态维，estimator 会把 `dim <= 0` 近似为 `1` 并追加 `dynamic-shape-approx` tag，而不是产生负 bytes。

## 当前边界

- 这不是通用 ONNX 编译前端。控制流、子图、复杂广播重写和通用图优化仍不在范围内。
- legality 回答的是“前端契约和硬件假设下是否允许进入后续阶段”，不是“是否已经完全映射到原生硬件”。
- `EmbeddingLookup`、`ROPETable`、`AttentionMaskPrep`、`ShapeHelper`、`LayoutFallback` 目前是显式 pseudo/fallback workload，不代表已有原生 ISA 映射。
- 当前 estimator 已同时覆盖 pseudo/fallback foundation、descriptor-driven perf foundation、prefill top-level foundation 和 decode top-level foundation，但还不是完整 Phase D/Phase E pipeline。
- 当前 memory planner 还是静态 foundation，已支持 phase-bucket lifetime reuse、DDR-backed binding 和 source-class-aware fit reasoning，但还没有 schedule-aware reuse、tiling 联动和双核交换路径选择。
- 当前还没有进入 sweep/delta comparison 和 UI。

## 最新检查点

2026-03-07 当前主线已经具备两类稳定能力：

- 真实 Gemma3 前端 coverage 已打通到 `canonical Graph IR -> NIG`，lowering unsupported 节点数为 `0`。
- `run-frontend-analysis` 已把 import / decomposition / binding / legality / pseudo-fallback analysis 集成到 run-root driven CLI 流程中，可稳定生成 dumps / reports / manifest / run-summary。
- Gemma3 Phase B 四象限 smoke matrix 已通过，`dynamic_shape_unresolved` 已清空。
- `SPEC-08` 已有第一版静态 VMEM/KV planner，可输出 `MemoryPlanArtifact` 和 `artifacts/memory_plan.json`。
- `SPEC-08` 的 Gemma3 四象限 memory-planning smoke matrix 已通过，KV address diagnostics 当前对主路径 `unresolved = 0`。
- `SPEC-08` planner 已支持 fit-aware `M_tile` shrink；prefill GEMM 不再默认把 `accum` 视为固定 overflow。
- `EMBEDDING_LOOKUP` 和 `LAYOUT_FALLBACK` 已切到 token/vector working-set 估算；Gemma3 prefill overflow set 当前收敛为 `misc/ping/pong/weight`。
- `GEGLU`、`ROPE_TABLE` 和 `ROPE` 也已切到流式 working-set 估算；Gemma3 prefill overflow set 进一步收敛为 `ping/pong/weight`。
- 当前 prefill 最大剩余热点已经转移到 `SDPA` activation staging 和 `lm_head` weight staging。

真实 Gemma3 smoke 结果：

- `decode_token1_kv2048`
  - `SDPA=26`
  - `AttentionMaskPrep=16`
  - `ResidualAdd=52`
  - `Linear=183`
  - `EmbeddingLookup=1`
  - `ROPETable=2`
  - `ShapeHelper=789`
  - `LayoutFallback=412`
  - lowering unsupported 节点数 `0`
- `prefill_seq128`
  - `SDPA=26`
  - `AttentionMaskPrep=16`
  - `ResidualAdd=52`
  - `Linear=183`
  - `EmbeddingLookup=1`
  - `ROPETable=2`
  - `ShapeHelper=789`
  - `LayoutFallback=412`
  - lowering unsupported 节点数 `0`

目前剩余的 legality 问题是预期内的 contract / target 假设问题，而不是 lowering coverage 缺口，主要包括：

- `no_hardware_mapping`
- `target_quant_activation_dtype_gap`
- `target_quant_group_size_gap`
- `kv_cache_dtype_mismatch`

## 推荐阅读顺序

1. 先看 `evaluation-compiler-spec-pack.md`，确认系统目标和分层边界。
2. 再看 `evaluation-compiler-roadmap.md`，确认依赖关系和阶段推进顺序。
3. 进入 frontend 主线时，以 `phase-a-foundation-handoff.md` 为准，再结合对应批次计划文档推进。
## 2026-03-07 SPEC-18 Checkpoint

- New handoff: `phase-e-visualization-foundation-handoff.md`
- New plan: `../plans/2026-03-07-spec-18-visualization-data-foundation.md`
- Stable workflow entry: `llm_sched.pipeline.run_visualization_packaging(run_root, sweep_root=None)`
- Stable analysis/report entry: `llm_sched.analysis.build_visualization_bundle(...)`
- Stable CLI entry: `llm-sched run-visualization-packaging --run-root ... [--sweep-root ...]`
- Stable artifact: `reports/visualization_bundle.json`
- Current foundation guarantees:
  - package graph/timeline/KV/VMEM/coverage into one static bundle
  - optionally attach filtered sweep deltas for the current run context
  - isolate UI from raw IR and report schema differences
- Current foundation boundaries:
  - static bundle only
  - no live query service
  - no multi-run catalog
  - no workbench UI yet

## 2026-03-07 SPEC-19 Checkpoint

- New handoff: `phase-e-visualization-workbench-handoff.md`
- New plan: `../plans/2026-03-07-spec-19-visualization-workbench.md`
- Catalog plan: `../plans/2026-03-07-spec-19-visualization-catalog-foundation.md`
- Deep-link plan: `../plans/2026-03-07-spec-19-visualization-deep-links.md`
- Cross-link plan: `../plans/2026-03-07-spec-19-workbench-cross-links.md`
- Saved-view/export plan: `../plans/2026-03-07-spec-19-workbench-export-saved-view.md`
- SVG export plan: `../plans/2026-03-07-spec-19-workbench-svg-export.md`
- Compare tray plan: `../plans/2026-03-08-spec-19-catalog-compare-tray.md`
- Compare workspace plan: `../plans/2026-03-08-spec-19-compare-workspace.md`
- Compare modes plan: `../plans/2026-03-08-spec-19-compare-modes.md`
- Stable builder entry: `llm_sched.visualization.build_visualization_workbench(bundle, bundle_relative_path, workbench_root)`
- Stable workflow entry: `llm_sched.pipeline.run_visualization_workbench(run_root)`
- Stable CLI entry: `llm-sched run-visualization-workbench --run-root ...`
- Stable catalog builder entry: `llm_sched.visualization.build_visualization_catalog(catalog_id, title, entries, catalog_root)`
- Stable catalog workflow entry: `llm_sched.pipeline.run_visualization_catalog(catalog_root, run_roots=None, sweep_root=None, workspace_root=None)`
- Stable catalog CLI entry: `llm-sched run-visualization-catalog --catalog-root ... [--run-root ...] [--sweep-root ...] [--workspace-root ...]`
- Stable artifacts:
  - `workbench/index.html`
  - `workbench/assets/app.js`
  - `workbench/assets/styles.css`
  - `workbench/workbench_manifest.json`
  - `catalog/index.html`
  - `catalog/assets/app.js`
  - `catalog/assets/styles.css`
  - `catalog/catalog_manifest.json`
- Current foundation guarantees:
  - package one `visualization_bundle.json` into a browsable static workbench
  - package an explicit run-root list into a browsable static catalog
  - optionally discover packaged runs from `sweep_root` or a workspace directory
  - expose summary/graph/timeline/core-occupancy/memory/coverage panels
  - expose the sweep panel only when sweep context exists
  - support graph search, timeline search/filter, and timeline block drill-down without reopening raw artifacts
  - support catalog search, scenario-group navigation, and grouped run sections for multi-run browsing
  - support URL-state panel routing from catalog links into summary/timeline/memory/coverage workbench views
  - support workbench cross-links from graph nodes, timeline block detail, coverage issues, and KV formulas into focused panel filters
  - support copying the current saved-view link and exporting the active panel state as JSON
  - support exporting the active panel as an SVG snapshot without adding a live screenshot service
  - support selecting up to two runs in the catalog and viewing a static compare tray with metric delta and summary links
  - support a baseline-pinned scenario compare workspace for visible runs in the catalog
  - support swapping baseline/candidate roles and switching compare scope between same-scenario and all-visible runs
- Current foundation boundaries:
  - static workbench only
  - no app server
  - workspace discovery currently scans packaged child runs and `runs/*`
  - no deep multi-metric compare workflow beyond the current scalar-plus-layer-plus-pressure compare surface

## 2026-03-07 SPEC-16 Checkpoint

- New handoff: `phase-d-sweep-foundation-handoff.md`
- New plan: `../plans/2026-03-07-spec-16-sweep-delta-engine.md`
- Stable workflow entry: `llm_sched.pipeline.run_sweep_analysis(sweep_spec_path, sweep_root)`
- Stable analysis/report entry: `llm_sched.analysis.build_sweep_delta_report(sweep_name, baseline_target_profile_name, run_records, profile_diff_lookup)`
- Stable CLI entry: `llm-sched run-sweep-analysis --sweep-spec ... --sweep-root ...`
- Stable artifact: `reports/sweep_delta_report.json`
- Current foundation guarantees:
  - rerun a declared target-profile x scenario-profile matrix under one sweep workspace
  - emit summary-grade baseline-vs-candidate metric deltas and macro-hotspot deltas
  - surface failed reruns and missing baselines as explicit report issues
- Current foundation boundaries:
  - serial execution only
  - no block-level diffing
  - no cached reuse of prior run-roots
  - richer multi-metric compare modes remain later work beyond the current visualization-facing summary packaging

## 2026-03-07 SPEC-08 Checkpoint

- `SDPA`銆乣RMSNORM_GEMM`銆乣RMSNORM`銆乣ELEM_ADD`銆乣KVLOAD`銆乣KVSTORE` 宸茬粡鎺ュ叆鏇存帴杩戠湡瀹?staging 鐨?working-set 浼扮畻銆?
- Gemma3 鍥涜薄闄?memory-planning smoke 褰撳墠 `overflow_regions = {}`锛屽悓鏃朵繚鎸?`kv address unresolved = 0`銆?
- 杩欐剰鍛崇潃 `SPEC-08` 褰撳墠宸茬粡鍏峰浣滀负 `SPEC-09` 杈撳叆鐨勭ǔ瀹氬熀闈紝鍚庣画涓昏鍓╀綑 DDR binding 鍜屽弻鏍告暟鎹氦鎹㈣矾寰勫熬椤广€?
## 2026-03-08 SPEC-12 Hardening Checkpoint

- New plan: `../plans/2026-03-08-spec-12-packing-profile-and-address-encoding.md`
- `DescriptorIR` now carries `packing_profile` and structured `address_fields` in addition to symbolic `addr_fields`
- descriptor validation now checks:
  - `packing_profile.stage_family` matches descriptor stage
  - `packing_profile.required_*` fields are satisfied by the descriptor payload
  - symbolic and structured address fields agree on role coverage and symbols
- descriptor builder now emits:
  - stage-aware opcode-family packing profiles
  - structured address fields for compute, DMA, and transfer descriptors
- downstream compatibility is preserved:
  - `descriptor_estimator` still consumes `shape_pack`, `dma_fields`, `transfer_fields`, and symbolic `addr_fields`
  - descriptor-generation workflow and Phase C descriptor smoke remain stable
## 2026-03-08 SPEC-12 Target Packing Validation Checkpoint

- New plan: `../plans/2026-03-08-spec-12-target-packing-validation.md`
- target profiles now carry default `descriptor_encoding` assumptions
- `DescriptorIR.packing_profile` now carries:
  - `layout_template`
  - deterministic `field_widths`
- `DescriptorIR.address_fields` now carry:
  - `descriptor_field`
  - `encoded_width_bits`
  - `uses_addr_ext`
- descriptor builder now:
  - specializes opcode-family packing templates against target encoding defaults
  - validates VMEM local offsets against encoded field widths
  - emits explicit coverage gaps when descriptor address encoding does not fit the target

## 2026-03-09 SPEC-08 Lifetime Reuse Checkpoint

- New plan: `../plans/2026-03-09-spec-08-lifetime-reuse.md`
- `MemoryPlanArtifact.allocations[*]` 现在显式带 `lifetime_bucket`。
- `region_summaries[*]` 现在显式带 `peak_lifetime_bucket` 和 `peak_bytes_by_lifetime_bucket`。
- `SPEC-08` 的 region peak 语义已从“同节点 raw sum”收敛成“静态 phase-bucket 峰值”，因此 `misc` 等 scratch-heavy region 不再被 preload/store 临时量虚高。
- Focused memory batch 和 Phase C memory-planner smoke 当前保持绿色。
- `SPEC-08` 当前剩余主缺口已转向：
  - 更真实的 DDR / VMEM binding reasoning
  - planner closure
  - schedule-aware reuse 之外的更高保真容量建模

## 2026-03-09 SPEC-08 DDR Binding Checkpoint

- New plan: `../plans/2026-03-09-spec-08-ddr-binding-realism.md`
- `MemoryPlanArtifact.allocations[*]` 现在显式带 `backing_store` 和 `backing_symbol`。
- staged `WEIGHT` / `QUANT_PARAM` allocation 现在会显式标记为 `ddr-backed-staged`。
- `KV_CACHE` allocation 现在会显式标记为 `ddr-persistent`，并和 `KV_BASE` 对齐。
- `address_diagnostics` 现在不再只覆盖 KV，也会覆盖 `weight` 和 `quant`。
- `SPEC-08` 当前剩余主缺口已进一步收窄到：
  - richer DDR / VMEM realism
  - planner closure
  - schedule-aware reuse 之外的更高保真容量建模

## 2026-03-09 SPEC-08 Fit Reasoning Checkpoint

- New plan: `../plans/2026-03-09-spec-08-fit-reasoning.md`
- `RegionSummary` 现在显式带：
  - `peak_bytes_by_memory_class`
  - `peak_bytes_by_backing_store`
- `VMEMFitDiagnostic` 现在显式带：
  - `required_bytes_by_memory_class`
  - `required_bytes_by_backing_store`
- `SPEC-08` 现在不仅能告诉你哪个 region 爆了，还能告诉你峰值主要来自 activation / weight / quant / metadata 里的哪一类，以及是 `vmem-local` 还是 `ddr-backed-staged`。
- 当前剩余主缺口已继续收窄到：
  - richer DDR / VMEM realism
  - planner closure
  - broader capacity reasoning beyond the current static staging model
## 2026-03-08 SPEC-12 Binary Packer Foundation Checkpoint

- New plan: `../plans/2026-03-08-spec-12-binary-packer-foundation.md`
- `run-descriptor-generation` now emits:
  - `artifacts/descriptor_ir.json`
  - `artifacts/packed_descriptor_bundle.json`
  - `reports/isa_coverage_report.json`
- follow-on hardening plan: `../plans/2026-03-08-spec-12-byte-order-and-driver-abi-hardening.md`
- packed payloads now carry:
  - deterministic `8 x 64-bit` words
  - concatenated `packed_hex`
  - field-level bit placements for control / shape / address / DMA / transfer groups
- packed payloads now also carry:
  - `stream_hex`
  - `word_order`
  - `byte_order`
- builder-emitted packing profiles now also carry:
  - explicit `field_layout`
- updated remaining gap:
  - richer opcode-family field placement specialization
  - final transport/container ABI above the current packed stream

## 2026-03-08 SPEC-12 Container ABI Checkpoint

- New plan: `../plans/2026-03-08-spec-12-container-and-placement-hardening.md`
- target profiles now also carry:
  - `descriptor_encoding.stream_container`
  - `descriptor_encoding.record_alignment_bytes`
- `packed_descriptor_bundle.json` now also carries:
  - `container_format`
  - `record_alignment_bytes`
  - `stream_total_bytes`
  - `stream_hex`
- each packed descriptor record now also carries:
  - `record_index`
  - `stream_offset_bytes`
  - `stream_size_bytes`
- `DescriptorPackingProfile` now validates stronger layout-template rules for compute, DMA, transfer, and prepare families
- current remaining gap is no longer “missing payload artifact”; it is “target byte-order / final driver ABI hardening”
## 2026-03-09 SPEC-08 Storage Binding Checkpoint

- New plan: `../plans/2026-03-09-spec-08-storage-binding-surface.md`
- `MemoryPlanArtifact` now carries `storage_bindings`.
- non-local `allocations[*]` now carry `storage_binding_id`.
- `address_diagnostics[*]` now also carry `storage_binding_id`.
- structured storage bindings now cover:
  - staged `weight`
  - staged `quant`
  - persistent `kv`
- The stable intent of this batch is:
  - keep `backing_symbol` as a readable field
  - stop requiring downstream layers to parse it as the formal contract
  - give `SPEC-09/12/13` a structured source/storage surface to consume
## 2026-03-09 SPEC-09 Storage-Aware Search and Ranking Checkpoint

- New plan: `../plans/2026-03-09-spec-09-storage-aware-search-ranking.md`
- `TileCandidateResourceSummary` now carries:
  - `storage_binding_ids`
  - `storage_read_bytes_by_source_kind`
  - `storage_read_bytes_by_backing_store`
- `TileCandidate` now carries:
  - `rank`
  - `ranking_reason`
- The stable intent of this batch is:
  - let `SPEC-09` consume `SPEC-08.storage_bindings` directly
  - stop scaling staged `weight/quant` bytes as if they were activation traffic
  - give `SPEC-10/11` a stronger, deterministic tile preference surface
## 2026-03-09 SPEC-10 Single-Core Overlap Checkpoint

- `SPEC-10` now emits `depends_on`, `issue_slot`, and `duration_slots` on `ScheduleIR` blocks.
- scope is intentionally single-core only in this batch.
- plan doc: `../plans/2026-03-09-spec-10-single-core-overlap-foundation.md`

## 2026-03-09 SPEC-10/11 Scheduler Fidelity Checkpoint

- `SPEC-10` / `SPEC-11` now consume `TileCandidate.rank` directly.
- untiled stable helper macros now remain visible in `ScheduleIR` instead of being dropped when `tiling_candidate_id` is absent.
- plan doc: `../plans/2026-03-09-spec-10-11-scheduler-fidelity-and-coverage.md`

## 2026-03-09 SPEC-11 Shared Sync Overlap Checkpoint

- plan doc: `../plans/2026-03-09-spec-11-shared-sync-overlap.md`
- dual-core transfer scheduling now models transport occupancy separately from sync-tail occupancy while keeping one stable `transfer` block in `ScheduleIR`.
- this means `Core Link` or `DMA` transport may be released before the transfer block fully ends when only sync tail remains.
- workflow and Phase C dual-core smoke remain green with the stronger timing policy.

## 2026-03-09 SPEC-10/11 Phased Engine Reservation Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-phased-engine-reservations.md`
- scheduler internals now reserve selected mixed-engine compute resources by phased windows instead of whole-block occupancy only.
- `SDPA` / `SDPA_DECODE` now release `MXU` before the trailing `VPU` tail completes.
- later `WDQ_GEMM` work may now reuse `MXU` during that tail when dependencies allow it.
- `ScheduleIR` stays unchanged; this batch is a timing-fidelity hardening step, not a new public contract.

## 2026-03-09 SPEC-10/11 GEGLU Resource Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-geglu-resource-specialization.md`
- `GEGLU` compute now lowers as a mixed-engine scheduler block with `resource_set = ["MXU", "VPU"]`.
- single-core and dual-core schedulers now apply the phased reservation helper to `GEGLU` compute instead of treating it as a pure `VPU` block.
- current scope is intentionally narrow: public stage sequence remains unchanged and there is still no cycle-calibrated `GEGLU` duration model.

## 2026-03-09 SPEC-10/11 Vector Duration Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-vector-duration-specialization.md`
- `RMSNORM`, `GEGLU`, `ROPE`, `ATTENTION_MASK_PREP`, and `LAYOUT_FALLBACK` now carry macro-specific vector-stage duration weights instead of sharing one generic formula.
- `GEGLU` prepare/compute is now intentionally costlier than a generic helper stage of the same shape.
- current scope is still heuristic only: this is schedule-fidelity hardening, not a cycle-calibrated model.

## 2026-03-09 SPEC-10/11 Mixed-Engine Duration Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-mixed-engine-duration-specialization.md`
- `WDQ_GEMM`, `RMSNORM_GEMM`, `SDPA`, and `SDPA_DECODE` now carry macro-specific compute overhead on top of base GEMM cycles.
- this keeps compute duration more consistent with the existing mixed-engine reservation model.
- current scope is still heuristic only: this is schedule-fidelity hardening, not a cycle-calibrated model.

## 2026-03-09 SPEC-10/11 Interval Reservation Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-interval-resource-reservations.md`
- scheduler internals now keep sorted interval reservations instead of only scalar resource availability timestamps.
- the ready queue now uses lazy earliest-issue heap scheduling instead of rescanning the full ready set on each step.
- `SDPA` tail overlap is now real for later helper work when dependencies allow it, while `ScheduleIR` stays unchanged.

## 2026-03-09 SPEC-10/11 WDQ Prefix Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-wdq-prefix-specialization.md`
- `WDQ_GEMM` compute now reserves `WDQ` first and delays `MXU` occupancy until after the WDQ prefix completes.
- single-core and dual-core schedulers can now exploit that prefix through the interval reservation engine, so later independent `GEMM` work may fit before the `WDQ_GEMM` matrix body begins.
- this batch keeps the public `ScheduleIR` unchanged and only hardens internal timing fidelity.

## 2026-03-09 SPEC-10/11 Overhead-Aligned Reservation Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-overhead-aligned-reservations.md`
- `RMSNORM_GEMM` compute now uses the true norm-prefix reservation window instead of a coarse quarter-split fallback.
- `SDPA` / `SDPA_DECODE` compute now use the true body-plus-tail reservation split implied by the current duration-overhead model.
- single-core and dual-core schedulers now precompute reservation windows per block and feed them directly into the interval scheduler.
- focused scheduler unit tests, single/dual scheduling workflows, Phase C single/dual smoke, and the performance-estimation workflow remain green with the stronger timing model.

## 2026-03-09 SPEC-10/11 DMA Window Specialization Checkpoint

- plan doc: `../plans/2026-03-09-spec-10-11-dma-window-specialization.md`
- `WDQ_GEMM.dma_in` now separates `DMA` transport from a short `WDQ` staging tail.
- `KVSTORE.store` now separates a `VPU` pack/layout prefix from the later shared-`DMA` writeback window.
- single-core and dual-core interval schedulers can now place later independent DMA work inside those non-DMA windows when dependencies allow it.

## 2026-03-09 SPEC-13 Schedule Occupancy Breakdown Checkpoint

- plan doc: `../plans/2026-03-09-spec-13-schedule-occupancy-breakdown.md`
- `PerfSummaryReport` now carries `per_core_busy_slots`, `per_core_idle_slots`, and `schedule_stage_slot_totals`.
- these fields are derived from scheduled intervals, so overlap is preserved instead of being double-counted.
- this is intentionally a summary-grade downstream consumer of stronger schedule timing, not a deeper cycle model.

## 2026-03-09 SPEC-13 Bandwidth / VMEM Breakdown Checkpoint

- plan doc: `../plans/2026-03-09-spec-13-bandwidth-vmem-breakdown.md`
- `PerfSummaryReport` now also carries:
  - `data_movement_read_bytes_by_address_space`
  - `data_movement_write_bytes_by_address_space`
  - `vmem_region_peak_bytes`
  - `vmem_region_capacity_bytes`
  - `vmem_region_peak_utilization`
- `run-performance-estimation` now consumes `memory_plan.json` as a real summary input instead of only validating its presence.
- this batch stays summary-grade on purpose: it answers whether pressure is landing in `DDR` or `VMEM`, and which VMEM region is tight, without introducing a deeper timing model.

## 2026-03-09 SPEC-14/15 Memory Hotspot Summary Checkpoint

- plan doc: `../plans/2026-03-09-spec-14-15-memory-hotspot-summary.md`
- `PrefillEvaluationReport` and `DecodeEvaluationReport` now also carry `memory_hotspot`.
- `memory_hotspot` exposes:
  - `dominant_address_space`
  - `read_bytes_by_address_space`
  - `write_bytes_by_address_space`
  - `hottest_region`
  - `hottest_region_peak_bytes`
  - `hottest_region_capacity_bytes`
  - `hottest_region_utilization`
- this batch keeps `SPEC-14/15` top-level and summary-grade: it does not reopen raw descriptor semantics or create a deeper cycle model.

## 2026-03-20 SPEC-16 Fitted Layer Diff Visualization Checkpoint

- plan doc: `../plans/2026-03-20-spec-16-fitted-layer-diff-visualization.md`
- `VisualizationBundle.sweep_view.comparisons[*]` and `VisualizationCatalogEntry.sweep_comparisons[*]` now carry:
  - `layer_deltas`
  - `fitted_layer_deltas`
- `run-visualization-packaging` now threads existing `PhaseDCompareReport.fitted_layer_deltas` directly into visualization-facing payloads instead of dropping them at the bundle boundary.
- `run-visualization-catalog` now preserves fitted layer rows into catalog artifacts, so downstream compare/workspace surfaces can consume one stable fitted-layer contract.
- `SPEC-19` static JS now exposes richer layer diff modes for catalog compare:
  - `Top By Cycles`
  - `Candidate Regressions`
  - `Top By Bytes`
  - `Top By Fitted Work`
  - `Fitted Work Regressions`
- workbench sweep export/rendering now shows fitted layer deltas beside estimated layer deltas, and snapshot/export metadata now includes:
  - `Focused Fitted Layer Deltas`
  - `Focused Fitted Layer Summary`
- focused verification:
  - `python -m pytest tests/unit/contracts/test_visualization_bundle.py tests/unit/contracts/test_visualization_catalog.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/visualization/test_catalog_builder.py tests/unit/visualization/test_workbench_builder.py -q` -> `22 passed`
  - `python -m pytest tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py -q` -> `13 passed`
  - `python -m pytest tests/smoke/test_cli_run_visualization_packaging.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `10 passed`
- what this closes:
  - one visualization adoption gap where `SPEC-16` already emitted `fitted_layer_deltas` but `SPEC-18/19` still rendered only estimated `layer_deltas`
  - one compare-mode gap where catalog layer diff focus could not rank or filter by fitted work-cycle regressions
  - one export gap where workbench sweep snapshot metadata summarized only estimated layer deltas
- what still remains for `M3`:
  - richer compare modes beyond the current estimated-plus-fitted layer surface
  - deeper cycle fitting remains in `SPEC-13`, not in visualization packaging
  - `SPEC-19` deeper workspace drill-down and richer screenshot/export hardening remain later slices

## 2026-03-20 SPEC-19 Workspace Drilldown Checkpoint

- plan doc: `../plans/2026-03-20-spec-19-workspace-drilldown.md`
- catalog workspace compare now exposes one expandable `Workspace Compare Drilldown` block inside the `Sweep Layer Deltas` summary stack.
- the drilldown reuses existing compare helpers and now expands:
  - `Grouped Metric Deltas`
  - `Pressure Compare`
  - `Estimated Layer Deltas`
  - `Fitted Layer Deltas`
- this slice stays strictly inside the static catalog builder:
  - no new contracts
  - no workflow schema changes
  - no workbench-side interaction changes
- focused verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q` -> `11 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `30 passed`
- what this closes:
  - one workspace usability gap where compare rows only showed compressed summary stacks and forced the user to jump out to workbench for any richer matched compare context
  - one adoption gap where grouped scalar, pressure compare, estimated layer, and fitted layer detail all existed in the payload but were not co-located in the catalog workspace
- what still remains:
  - richer screenshot/export hardening for the new workspace drilldown state
  - deeper side-by-side compare interaction if we later want row selection or pinned detail panels

## 2026-03-20 SPEC-19 Workspace Export Hardening Checkpoint

- plan doc: `../plans/2026-03-20-spec-19-workspace-export-hardening.md`
- catalog workspace compare now exposes workspace-local actions for:
  - `Copy Workspace Link`
  - `Export Workspace JSON`
  - `Export Workspace SVG`
- this slice stays inside the static catalog builder and reuses existing catalog URL state instead of introducing a new service or contract.
- exported workspace metadata now carries the currently focused compare context:
  - `Focused Compare Scope`
  - `Focused Layer Delta Mode`
  - `Focused Baseline`
  - `Focused Candidate Count`
  - `Focused Sweep Candidate`
  - `Focused Sweep Layer`
- the new JSON/SVG path is intentionally summary-grade:
  - it snapshots the current workspace state and candidate set
  - it does not introduce row pinning, richer side-panel state, or a new interactive export format
- focused verification:
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py -q` -> `11 passed`
  - `python -m pytest tests/unit/visualization/test_catalog_builder.py tests/unit/pipeline/test_visualization_catalog_workflow.py tests/unit/analysis/test_visualization_bundle_builder.py tests/unit/pipeline/test_visualization_packaging_workflow.py tests/unit/pipeline/test_visualization_workbench_workflow.py tests/smoke/test_cli_run_visualization_catalog.py tests/smoke/test_cli_run_visualization_workbench.py -q` -> `30 passed`
- what this closes:
  - one workspace-export gap where the new drilldown state was visible but could not be copied or snapshotted from the catalog itself
  - one workflow gap where workspace context lived only in the browser URL and not in a human-readable JSON/SVG export
- what still remains:
  - richer compare modes beyond the current grouped scalar plus estimated/fitted layer plus pressure summary surface
  - deeper side-by-side workspace interaction if we later want pinned detail panels or row selection
