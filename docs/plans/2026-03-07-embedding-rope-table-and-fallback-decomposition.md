# 2026-03-07 Embedding / RoPE Table / Fallback Decomposition

## Goal

补齐 Graph frontend 在 Gemma3 attention 周边剩余的第一批 decomposition，使前端不再只覆盖 attention 主路径，而是把以下三类路径显式建模出来：

- `EmbeddingLookup`
- `ROPETable` preprocessing
- `ShapeHelper` / `LayoutFallback` fallback surface

这批工作的目标不是把这些路径伪装成“已经有硬件原生映射”，而是把它们从大量零散 ONNX helper 节点收敛成边界清晰、可分析、可统计、可继续推进的工作负载节点。

## Scope

### Canonical Graph IR

- `MatMul(const-weight) -> Linear`
- `Gather(weight, input_ids)` 以及 `Gather + Mul(scale)` -> `EmbeddingLookup`
- RoPE cos/sin table preprocessing 链 -> `ROPETable`
- `ROPE` 允许吸收共享的 cos/sin `Unsqueeze`
- 残余 int/bool shape 子图 -> `ShapeHelper`
- 残余 float layout/helper 子图 -> `LayoutFallback`

### Legality

- 当传入 `TargetProfile` / `ArchitectureCapabilities` 时：
  - `EmbeddingLookup`
  - `ROPETable`
  - `ShapeHelper`
  - `LayoutFallback`

  统一显式报出 `no_hardware_mapping`，而不是静默留给后续阶段。

### NIG Lowering

- `EmbeddingLookup -> EMBEDDING_LOOKUP`
- `ROPETable -> ROPE_TABLE`
- `ShapeHelper -> SHAPE_HELPER`
- `LayoutFallback -> LAYOUT_FALLBACK`

这些 macro-op 当前属于显式 fallback / pseudo workload surface，不代表已经存在硬件 ISA 映射。

## Tests

新增测试文件：

- `tests/unit/frontend/test_decomposition_extensions.py`

覆盖点：

- embedding canonicalization
- rope-table canonicalization
- shared unsqueezed rope-table reuse
- shape/layout fallback classification
- pseudo/fallback lowering
- target-aware legality for unmapped frontend surfaces

## Real Gemma3 Decode Smoke

场景：

- model: `models/gemma3_1b/model_q4f16.onnx`
- scenario: `decode_token1_kv2048`
- target: `riscv_npu_single_core_v1`

最新结果：

- canonical counts
  - `EmbeddingLookup=1`
  - `ROPETable=2`
  - `ROPE=52`
  - `KVStore=43`
  - `KVLoad=26`
  - `SDPA=26`
  - `ResidualAdd=52`
  - `ShapeHelper=789`
  - `LayoutFallback=412`
  - `Linear=183`
- legality issues
  - `no_hardware_mapping=1204`
  - `dynamic_shape_unresolved=1009`
  - `unsupported_quant_activation_dtype=182`
  - `unsupported_quant_group_size=182`
  - `kv_cache_dtype_mismatch=69`
- lowering remaining unsupported nodes: `68`
  - `Mul=53`
  - `Add=6`
  - `Sub=2`
  - `Max=2`
  - `Trilu=2`
  - `Neg=1`
  - `Greater=1`
  - `ScatterND=1`

相对上一批，attention 周边 helper 路径已经从大量 `Gather/Shape/Unsqueeze/Transpose/Where/Concat` 噪声收敛到少数显式 frontend surface，真正剩下的缺口开始集中到 mask/arithmetic fallback。

## Remaining Gaps

- attention mask 路径的 `Mul/Add/Sub/Max/Trilu` decomposition
- 更细粒度的 fallback 成本模型
- 把 pseudo/fallback workload 接进后续 perf / bandwidth / ISA coverage analysis
- prefill/decode 双场景统一 smoke 报表
