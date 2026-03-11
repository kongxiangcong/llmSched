# Phase A Foundation Handoff

## 1. Current Stable Surface

Phase A 当前稳定下来的，不是完整编译器，而是一层后续 Phase B / Phase C 可以直接依赖的“契约 + frontend 骨架”：

- profile schema 和 loader
- `llm-sched` CLI 的 `validate-profile` / `init-run` / `run-frontend-analysis`
- run manifest / artifact layout / run summary
- `TargetProfile -> ArchitectureCapabilities`
- constraint checker 和 query API
- 五层 IR schema / validator / traceability / JSON roundtrip
- Graph frontend 主链路：
  - `ONNX -> GraphIR -> canonical GraphIR -> initial NIG -> pseudo/fallback AnalysisIR`
- run-root driven workflow：
  - `manifest.json` 作为输入契约
  - `dumps/`、`reports/`、`run-summary.json` 作为稳定输出契约

后续模块应该直接复用这些契约，不要绕开它们自建一套输入输出对象。

## 2. Frontend Contract

### Import

- `llm_sched.frontend.import_onnx_to_graph_ir(model_path_or_proto, shape_bindings=None)`
- 显式导入 `Input` / `Constant` / 原始 ONNX 节点
- 保留 `source_ref` / `audit_ref`
- 支持在 shape inference 之前绑定 Gemma3 相关输入维

### Scenario Binding

- `llm_sched.frontend.load_gemma_model_metadata(path)`
- `llm_sched.frontend.build_gemma3_shape_bindings(metadata, scenario)`

当前 shape binding 解决的是输入符号维绑定，不等于整图所有动态维都已经完全收敛。

### Legality

- `llm_sched.frontend.validate_frontend_legality(graph_ir, hardware=None)`
- `hardware` 可传 `TargetProfile` 或 `ArchitectureCapabilities`

legality 当前分两层：

- 结构准入
  - 拒绝 `If` / `Loop` / `Scan`
  - 拒绝未收敛的动态 shape
  - 拒绝白名单外 layout
  - 要求量化 `Linear` 显式声明合法 `group_size`
- target-aware 准入
  - 检查 canonical 节点所需 opcode 是否在 target 中启用
  - 检查量化 `weight_dtype` / `activation_dtype` / `group_size`
  - 检查 `KVStore` / `KVLoad` 的 dtype / layout 是否匹配 `kv_cache`
  - 对以下显式 fallback surface 报 `no_hardware_mapping`
    - `EmbeddingLookup`
    - `ROPETable`
    - `AttentionMaskPrep`
    - `ShapeHelper`
    - `LayoutFallback`

重要边界：

- legality 回答的是“这张图在当前前端契约和硬件假设下是否允许进入后续阶段”。
- legality 不回答“这张图是否已经完全映射到原生硬件”。

### Canonical Graph IR

- `llm_sched.frontend.canonicalize_graph_ir(graph_ir)`

当前已覆盖：

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

- `SDPA` 会吸收 q/k score scaling 的 `Mul(tensor, constant)`，在 attrs 中记录 `query_scale_tensor` / `key_scale_tensor`
- `AttentionMaskPrep` 用来显式承接 attention mask 路径上的 arithmetic / mask-construction 节点，不吞并 shape-only / layout-only helper

### NIG Lowering

- `llm_sched.frontend.lower_graph_ir_to_nig(graph_ir, scenario=None)`

当前已覆盖：

- `Linear -> GEMM / WDQ_GEMM`
- `RMSNorm -> RMSNORM`
- `RMSNorm -> Linear -> RMSNORM_GEMM`
- `GeGLU -> GEGLU`
- `ROPE -> ROPE`
- `KVStore -> KVSTORE`
- `KVLoad -> KVLOAD`
- `ResidualAdd -> ELEM_ADD`
- `SDPA -> SDPA / SDPA_DECODE`
- `EmbeddingLookup -> EMBEDDING_LOOKUP`
- `ROPETable -> ROPE_TABLE`
- `AttentionMaskPrep -> ATTENTION_MASK_PREP`
- `ShapeHelper -> SHAPE_HELPER`
- `LayoutFallback -> LAYOUT_FALLBACK`

`SDPA_DECODE` 的选择优先看 `scenario.mode`，没有 scenario 时回退到 `query_len == 1`。
未覆盖的 compute 节点仍会显式抛出 `GraphToNIGLoweringError`，不会静默丢失。

### NIG Metadata Contract

`NIGNode` 现在还保留：

- `shape`
  - 当前 workload 输出 shape
- `attrs`
  - 从 canonical Graph IR 保留下来的语义提示

这使 NIG 可以直接作为 analysis / schedule 的输入，不必再回头重新解析 Graph IR。

### Analysis Estimator

- `llm_sched.analysis.estimate_nig_analysis(nig_ir, hardware)`

当前 scope 只覆盖 pseudo/fallback workload：

- `ATTENTION_MASK_PREP`
- `SHAPE_HELPER`
- `LAYOUT_FALLBACK`
- `EMBEDDING_LOOKUP`
- `ROPE_TABLE`

输出 `AnalysisIR` per-node records，当前指标包括：

- `read_bytes`
- `write_bytes`
- `total_bytes`
- `estimated_cycles`
- `bandwidth_pressure`

以及显式 bottleneck tags：

- `memory-bound`
- `metadata-bound`
- `compute-bound`
- `dynamic-shape-approx`

重要边界：

- 这不是完整 perf estimator。
- 这是给 pseudo/fallback workload 先建立可解释、可比较、可组合的成本模型。
- 若 shape 中仍有 `dim <= 0`，estimator 会采用保守近似而不是输出负 metrics。

## 3. Run Workflow Contract

### CLI

当前推荐的稳定入口是：

```powershell
llm-sched init-run `
  --run-root <run-root> `
  --model-path models/gemma3_1b/model_q4f16.onnx `
  --target-profile profiles/targets/riscv_npu_single_core_v1.json `
  --scenario-profile profiles/scenarios/prefill_seq128.json

llm-sched run-frontend-analysis --run-root <run-root>
```

### Manifest Input

`init-run` 会生成：

- `manifest.json`
  - `model_path`
  - `target_profile_path`
  - `scenario_profile_path`
  - `artifact_index`
- `run-summary.json`
  - 初始状态 `initialized`

路径以绝对路径落盘，避免后续 workflow 受调用 cwd 影响。

### Workflow Output

`run-frontend-analysis` 会写出：

- `dumps/graph_ir.json`
- `dumps/canonical_graph_ir.json`
- `dumps/nig_ir.json`
- `dumps/analysis_ir.json`
- `reports/frontend_legality.json`
- `reports/pseudo_fallback_summary.json`

同时更新：

- `manifest.json`
  - `status = completed | failed`
  - `artifact_index` 追加上述 dumps / reports
- `run-summary.json`
  - 写入 `status`、`exit_code`、diagnostics

### Report Contract

`frontend_legality.json`：

- `run_id`
- `issue_counts`
- `issues`

`pseudo_fallback_summary.json`：

- `run_id`
- `record_counts`
- `tag_counts`
- `totals`
- `total_bytes_by_macro`
- `estimated_cycles_by_macro`

## 4. Baseline Targets

当前 baseline target profile 与已经实现的 lowering 面对齐，声明了这些 opcode：

- `GEMM`
- `WDQ_GEMM`
- `RMSNORM`
- `RMSNORM_GEMM`
- `ROPE`
- `GEGLU`
- `KVSTORE`
- `KVLOAD`
- `ELEM_ADD`
- `SDPA`
- `SDPA_DECODE`

对应文件：

- `profiles/targets/riscv_npu_single_core_v1.json`
- `profiles/targets/riscv_npu_dual_core_v1.json`

## 5. Example Flow

### Python API

```python
from llm_sched.analysis import estimate_nig_analysis
from llm_sched.config.loader import load_scenario_profile, load_target_profile
from llm_sched.frontend import (
    build_gemma3_shape_bindings,
    canonicalize_graph_ir,
    collect_frontend_legality_issues,
    import_onnx_to_graph_ir,
    load_gemma_model_metadata,
    lower_graph_ir_to_nig,
)

metadata = load_gemma_model_metadata("models/gemma3_1b/config.json")
scenario = load_scenario_profile("profiles/scenarios/decode_token1_kv2048.json")
target = load_target_profile("profiles/targets/riscv_npu_single_core_v1.json")
bindings = build_gemma3_shape_bindings(metadata, scenario)

graph_ir = import_onnx_to_graph_ir(
    "models/gemma3_1b/model_q4f16.onnx",
    shape_bindings=bindings,
)
canonical_graph_ir = canonicalize_graph_ir(graph_ir)
legality_issues = collect_frontend_legality_issues(canonical_graph_ir, hardware=target)
nig_ir = lower_graph_ir_to_nig(canonical_graph_ir, scenario=scenario)
analysis_ir = estimate_nig_analysis(nig_ir, target)
```

### Run-root Workflow

```python
from llm_sched.pipeline import run_frontend_analysis

result = run_frontend_analysis("runs/gemma3-prefill-001")
assert result.status == "completed"
```

## 6. Real Gemma3 Smoke Status

对象：

- model: `models/gemma3_1b/model_q4f16.onnx`
- target: `profiles/targets/riscv_npu_single_core_v1.json`
- scenarios:
  - `profiles/scenarios/decode_token1_kv2048.json`
  - `profiles/scenarios/prefill_seq128.json`

### Decode

- canonical counts
  - `SDPA=26`
  - `AttentionMaskPrep=16`
  - `ResidualAdd=52`
  - `Linear=183`
  - `EmbeddingLookup=1`
  - `ROPETable=2`
  - `ShapeHelper=789`
  - `LayoutFallback=412`
- legality issues
  - `dynamic_shape_unresolved=957`
  - `no_hardware_mapping=1220`
  - `unsupported_quant_activation_dtype=182`
  - `unsupported_quant_group_size=182`
  - `kv_cache_dtype_mismatch=69`
- lowering unsupported nodes
  - `0`
- pseudo/fallback estimator records
  - `ATTENTION_MASK_PREP=16`
  - `SHAPE_HELPER=789`
  - `LAYOUT_FALLBACK=412`
  - `EMBEDDING_LOOKUP=1`
  - `ROPE_TABLE=2`

### Prefill

- canonical counts
  - `SDPA=26`
  - `AttentionMaskPrep=16`
  - `ResidualAdd=52`
  - `Linear=183`
  - `EmbeddingLookup=1`
  - `ROPETable=2`
  - `ShapeHelper=789`
  - `LayoutFallback=412`
- legality issues
  - `dynamic_shape_unresolved=1049`
  - `no_hardware_mapping=1220`
  - `unsupported_quant_activation_dtype=182`
  - `unsupported_quant_group_size=182`
  - `kv_cache_dtype_mismatch=69`
- lowering unsupported nodes
  - `0`
- pseudo/fallback estimator records
  - `ATTENTION_MASK_PREP=16`
  - `SHAPE_HELPER=789`
  - `LAYOUT_FALLBACK=412`
  - `EMBEDDING_LOOKUP=1`
  - `ROPE_TABLE=2`

这说明：

- frontend 现在已经能把真实 Gemma3 的主路径和显式 fallback 路径完整 lower 到第一版 NIG。
- NIG 已经保留足够的 workload metadata，可以直接支撑第一版 analysis。
- 通过 `run-frontend-analysis`，这些结果已经可以稳定写入 run-root artifact，而不是停留在 ad-hoc smoke script。
- 剩余问题已经从“lowering coverage 缺口”收敛为“front-end legality 与硬件假设不匹配”。

## 7. What Phase B Can Rely On

Phase B 可以直接依赖以下契约：

- profile 文件格式和 loader API
- `ArchitectureCapabilities` / `ArchitectureQueryAPI`
- IR schema 和 validator
- `source_ref` / `audit_ref`
- `import -> canonicalize -> legality -> lower -> estimate` 的 frontend / analysis 阶段边界
- baseline scenario / target fixture 路径
- run-root artifact 契约：
  - `manifest.json`
  - `run-summary.json`
  - `dumps/*.json`
  - `reports/*.json`
- 显式 pseudo/fallback workload 命名：
  - `EMBEDDING_LOOKUP`
  - `ROPE_TABLE`
  - `ATTENTION_MASK_PREP`
  - `SHAPE_HELPER`
  - `LAYOUT_FALLBACK`

## 8. Not Done Yet

以下能力仍未实现，不应被误判为已经存在：

- 非 pseudo/fallback compute macro-op 的完整成本模型
- 更完整的 perf / bandwidth / ISA coverage pipeline
- `AttentionMaskPrep` / `ShapeHelper` / `LayoutFallback` 之外的全量带宽归因
- 更完整的 attention legality 约束
- tiling planner
- VMEM / KV address planner
- single-core / dual-core scheduler
- descriptor builder
- visualization service / UI

## 9. Recommended Next Steps

建议按这个顺序继续：

1. 把 pseudo/fallback estimator 接进更完整的 perf / bandwidth / ISA coverage 管线。
2. 进入 `NIG -> Schedule IR` 的 tiling / memory / scheduler 主线。
3. 在 run-root artifact 基础上扩展 UI / visualization，而不是重建一套平行输出格式。

## 10. Phase B Closure Gate Baseline (2026-03-07)

当前 Phase B 的正式 smoke gate 已经扩成 Gemma3 四象限矩阵：

- `single-core + prefill`
- `single-core + decode`
- `dual-core + prefill`
- `dual-core + decode`

四个组合当前都满足以下门槛：

- import succeeds
- decomposition succeeds
- `dumps/bound_nig_ir.json` exists
- `frontend_legality.json` 中 `dynamic_shape_unresolved = 0`
- pseudo/fallback 统计和 target gap 统计已经分离

当前稳定基线如下：

- legality issue counts
  - `kv_cache_dtype_mismatch = 69`
  - `no_hardware_mapping = 1220`
  - `target_quant_activation_dtype_gap = 182`
  - `target_quant_group_size_gap = 182`
- pseudo/fallback record counts
  - `ATTENTION_MASK_PREP = 16`
  - `EMBEDDING_LOOKUP = 1`
  - `LAYOUT_FALLBACK = 412`
  - `ROPE_TABLE = 2`
  - `SHAPE_HELPER = 789`
- binding coverage
  - prefill scenarios: `0.7864`
  - decode scenarios: `0.7797`

这意味着 Phase B 当前的剩余问题已经明确收敛为 target gap / fallback surface，而不是前端 import、decomposition 或 shape binding 本身未闭合。
