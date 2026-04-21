# NPU Controller 如何解析和使用 v0.10 Descriptor

**目标读者**: `tars-npu-ctrl` controller / parser / dispatcher 实现方  
**交付版本**: v0.10  
**日期**: 2026-04-21  
**当前有效 descriptor_version**: `0x6`

---

## 1. controller 需要关心的核心结论

controller 只需要按当前 v0.10 contract 做两件事：

1. **解析** descriptor word stream，恢复结构化字段
2. **物化**成 controller 可执行的 `exec_plan_ctx`

v0.10 的 descriptor 是一个 **固定顺序、长度可推导** 的 flat word stream：

```text
[primary_header]
[FAMILY]
[BUFFER x buffer_count]
[LOOP]
[TEMPLATE if template_slot_count > 0]
```

controller 只要读出 `primary_header`，后续所有 record 边界都可以机械推导出来。

---

## 2. 建议先读哪几份文档

建议按这个顺序：

1. `docs/deliveries/npu-controller-v0.10/a3-encoding-layout.md`
2. `docs/deliveries/npu-controller-v0.10/family-schema-lut-summary.md`
3. 本文档

分工建议：

- parser 实现人重点看 encoding layout
- family decode / verifier 实现人重点看 family schema LUT
- dispatcher / execution owner 重点看本文档第 5 到第 9 节

---

## 3. controller 视角下的解析流程

## 3.1 Step 0: 读取 primary_header

descriptor 第 0 个 64-bit word 就是 `primary_header`。  
controller 首先提取以下字段：

| 字段 | 位段 | 用途 |
|---|---|---|
| `descriptor_version` | `[63:60]` | 必须为 `0x6` |
| `task_type_id` | `[59:54]` | 决定 family 语义与 FAMILY 长度 |
| `dep_mask` | `[53:46]` | 多核依赖控制 |
| `signal_mask` | `[45:38]` | 多核完成信号 |
| `crc16` | `[37:22]` | 完整 descriptor CRC |
| `buffer_count` | `[21:19]` | BUFFER record 数量 |
| `loop_rank` | `[18:17]` | LOOP 长度推导 |
| `template_slot_count` | `[16:14]` | TEMPLATE 长度推导 |

如果 `descriptor_version != 0x6`，直接 reject。

## 3.2 Step 1: 推导各 record 长度

controller 不需要 descriptor 里额外给长度表。  
长度由 `primary_header` 中的字段直接推导：

```text
family_words   = family_word_count(task_type_id)
buffer_words   = 4 * buffer_count
loop_words     = ceil(loop_rank * 32 / 64)
template_words = ceil(template_slot_count * 32 / 64)
```

其中：

- `FAMILY = 2 words` for `RMSNORM / ELEM_ADD / GEGLU`
- `FAMILY = 3 words` for all other families
- `LOOP = 1 word` for `loop_rank = 1 or 2`
- `LOOP = 2 words` for `loop_rank = 3`
- `TEMPLATE` absent when `template_slot_count = 0`

完整 descriptor 长度：

```text
total_words = 1
            + family_words
            + 4 * buffer_count
            + loop_words
            + template_words
```

## 3.3 Step 2: 拉取完整 descriptor 并做 CRC

建议 controller 先基于 `total_words` 把完整 descriptor 拉回本地，再做 CRC：

- 算法: `CRC-16/CCITT-FALSE`
- 覆盖范围: descriptor 全部 words
- 计算时 `crc16` 字段清零
- 序列化: word 内 MSB-first

CRC 不通过则 reject，不进入 dispatcher。

## 3.4 Step 3: 顺序解码

word stream 的解码顺序固定：

1. `primary_header`
2. `FAMILY`
3. `BUFFER[0..buffer_count-1]`
4. `LOOP`
5. `TEMPLATE`（若存在）

controller 不应通过“猜测字段内容”寻找 record 边界，只能按长度推导前进。

---

## 4. controller 端建议拆成两个阶段

建议实现成两个明确阶段：

### 4.1 parse 阶段

输入：descriptor words  
输出：`parsed_descriptor_raw`

职责：

- 从 bitfield 中恢复各 record 的原始字段
- 做结构合法性检查
- 做 CRC / reserved bits / length consistency 检查

### 4.2 materialize 阶段

输入：`parsed_descriptor_raw`  
输出：`exec_plan_ctx_v010`

职责：

- 根据 `task_type_id` 解释 FAMILY 字段语义
- 生成 buffer 绑定 / loop 计划 / slot 计划
- 形成 dispatcher / DMA / TC.VPU 可直接消费的上下文

这样做的好处是：

- parser 易于验证
- materialization 逻辑清晰
- bring-up 时更容易定位问题是“读错 bit”还是“解释错语义”

---

## 5. FAMILY 的解析与使用

## 5.1 controller 对 FAMILY 的基本理解

FAMILY record 承载的是 family-specific 的执行语义。  
controller 读 FAMILY 时必须先看 `task_type_id`，再决定：

- FAMILY 是 2 words 还是 3 words
- 哪些字段有效
- 哪些字段必须为 0
- 各字段如何映射成 controller 的执行语义

这一步不要写死成统一结构直接消费，应该通过 LUT 做物化。

**关键约束**：materializer 必须先按 `task_type_id` dispatch，再解释 `family_mode` [47:44] 和 shared surface slots（`primary_surface_slot` [43:41]、`secondary_surface_slot` [40:38]）。非 owning family 必须将这些共享 slot 视为 `must_be_zero`，禁止在 dispatch 前按默认语义消费。

## 5.2 FAMILY 通用字段布局

### Word 0-1：始终存在

| 字段 | 位段 | 说明 |
|---|---|---|
| `dim0_full_extent` | `[127:112]` | 第 1 个 full shape 维度 |
| `dim1_full_extent` | `[111:96]` | 第 2 个 full shape 维度 |
| `dim2_full_extent` | `[95:80]` | 第 3 个 full shape 维度 |
| `dim0_tile_extent` | `[79:72]` | 第 1 个 tile 维度 |
| `dim1_tile_extent` | `[71:64]` | 第 2 个 tile 维度 |
| `dim2_tile_extent` | `[63:56]` | 第 3 个 tile 维度 |
| `extra_dim0` | `[55:40]` | 扩展维度 0 |
| `extra_tile0` | `[39:32]` | 扩展 tile 维度 |
| `extra_dim1` | `[31:16]` | 扩展维度 1 |
| `scalar0` | `[15:0]` | family-specific scalar |

### Word 2：按 family 决定是否存在

| 字段 | 位段 | 说明 |
|---|---|---|
| `engine_profile` | `[63:60]` | 执行 profile |
| `mask_cfg` | `[59:56]` | attention mask 配置 |
| `cache_layout_class` | `[55:52]` | KV 布局类；GEMM 中复用为 `act_dtype` |
| `cache_axis_order` | `[51:48]` | KV 轴顺序；GEMM 中复用为 `weight_dtype` |
| `family_mode` | `[47:44]` | **neutral dispatch-first slot**；语义别名由 `task_type_id` 决定 |
| `primary_surface_slot` | `[43:41]` | 主 surface slot；KVSTORE 中复用为 `primary_input_surface` |
| `secondary_surface_slot` | `[40:38]` | 次 surface slot；KVSTORE 中复用为 `secondary_input_surface` |

## 5.3 controller 实际消费 FAMILY 的方式

不建议下游模块直接消费 raw FAMILY bitfield。  
建议先物化成 family-specific semantic view。

### GEMM

controller 应恢复：

- `m`, `n`, `k`
- `tile_m`, `tile_n`, `tile_k`
- `act_dtype`
- `weight_dtype`
- `accum_dtype`
- `engine_profile`
- `primary_output_surface`

### SDPA

controller 应恢复：

- `num_heads`
- `query_len`
- `kv_len`
- `tile_query`
- `tile_kv`
- `head_dim`
- `tile_head_dim`
- `num_kv_heads`
- `softmax_scale`
- `mask_cfg`
- `engine_profile`
- `primary_output_surface`

### SDPA_DECODE

在 SDPA 基础上额外恢复：

- `kv_operand_binding_mode`

它的编码位置在 `family_mode` [47:44]。

### KVLOAD

controller 应恢复：

- `kv_len`
- `num_kv_heads`
- `head_dim`
- `tile_kv`
- `cache_layout_class`
- `cache_axis_order`
- `source_binding_mode`（编码位置 `family_mode` [47:44]）
- `primary_output_surface`（编码位置 `primary_surface_slot` [43:41]）
- `secondary_output_surface`（编码位置 `secondary_surface_slot` [40:38]）

### KVSTORE

controller 应恢复：

- `kv_len_before`
- `kv_len_after`
- `num_kv_heads`
- `head_dim`
- `tile_kv`
- `cache_layout_class`
- `cache_axis_order`
- `append_mode`
- `primary_input_surface`
- `secondary_input_surface`

其中：

- `append_mode` 使用 `family_mode` [47:44] 的位点
- `primary_input_surface` 使用 `primary_surface_slot` [43:41] 的位点
- `secondary_input_surface` 使用 `secondary_surface_slot` [40:38] 的位点

KVSTORE 的输入/输出方向性由 BUFFER 的 `role` 和 `access_mode` 决定，而不是由 FAMILY 中 surface slot 的历史名称决定。

### RMSNORM / ELEM_ADD / GEGLU

这三个 family 只有 2 words。  
controller 在推进 word offset 时必须特别注意，不要多吃 1 个 word。

---

## 6. BUFFER 的解析与使用

每个 BUFFER 固定 4 words。  
controller 建议先恢复一个标准化 `buffer_ctx`：

```c
struct buffer_ctx {
    uint8_t  role;
    uint8_t  address_space;
    uint8_t  access_mode;
    uint8_t  layout_class;
    uint8_t  dim_count;
    uint16_t span;
    uint64_t base_address;
    uint16_t dim_extent[3];
    uint32_t dim_stride_bytes[3];
};
```

## 6.1 BUFFER 关键字段

| 字段 | 位段 | 说明 |
|---|---|---|
| `role` | `[255:252]` | operand 角色 |
| `address_space` | `[251:248]` | DDR / VMEM 等 |
| `access_mode` | `[247:245]` | read / write / read_write |
| `layout_class` | `[244:241]` | dense / tiled / strided |
| `dim_count` | `[240:238]` | 有效 stride 维数 |
| `span` | `[237:222]` | byte span |
| `base_binding_lo` | `[221:190]` | base addr low |
| `base_binding_hi` | `[189:158]` | base addr high |
| `dim_0_extent` | `[157:142]` | dim0 extent |
| `dim_0_stride_lo` | `[141:126]` | dim0 stride low |
| `dim_0_stride_hi` | `[125:118]` | dim0 stride high |
| `dim_1_extent` | `[117:102]` | dim1 extent |
| `dim_1_stride_lo` | `[101:86]` | dim1 stride low |
| `dim_1_stride_hi` | `[85:78]` | dim1 stride high |
| `dim_2_extent` | `[77:62]` | dim2 extent |
| `dim_2_stride_lo` | `[61:46]` | dim2 stride low |
| `dim_2_stride_hi` | `[45:38]` | dim2 stride high |

## 6.2 controller 怎么用 BUFFER

controller 下游真正要用的是：

- buffer 角色和访问模式
- `base_address`
- 各维 extent
- 各维 stride

典型 materialization：

```text
base_address = (base_binding_hi << 32) | base_binding_lo
dim_stride_bytes[i] = (stride_hi << 16) | stride_lo
```

然后结合 loop 坐标得到 tile 级地址解析。

---

## 7. LOOP 的解析与使用

LOOP record 是 controller 生成 tile iteration 的直接输入。

## 7.1 LOOP slot 格式

每个 loop slot 固定 32 bits：

| 字段 | 位段 | 说明 |
|---|---|---|
| `dim_extent` | `[31:12]` | 20-bit loop extent |
| `tile_extent` | `[11:4]` | tile 大小 |
| `axis_encoding` | `[3:0]` | 逻辑轴编码 |

## 7.2 LOOP 长度

- `loop_rank = 1` -> `1 word`
- `loop_rank = 2` -> `1 word`
- `loop_rank = 3` -> `2 words`

controller 应把 LOOP materialize 成统一的结构，例如：

```c
struct loop_slot {
    uint32_t dim_extent;
    uint8_t  tile_extent;
    uint8_t  axis_encoding;
};
```

## 7.3 controller 怎么用 LOOP

LOOP 是 controller 生成 tile 坐标和 iteration 次序的输入。  
至少应支持：

- 恢复有效 loop 维数
- 恢复每个 loop 维的 extent
- 恢复每个 loop 维的 tile size
- 恢复 axis 语义

后续 dispatcher / address resolver 用它生成：

- 当前 tile 坐标
- 当前 tile 的 buffer 地址
- 当前 tile 应执行哪些 template slot

---

## 8. TEMPLATE 的解析与使用

TEMPLATE record 描述单次 iteration 内的 action plan。  
controller 可以把它直接视作 slot 序列。

## 8.1 TEMPLATE slot 格式

每个 slot 固定 32 bits：

| 字段 | 位段 | 说明 |
|---|---|---|
| `kind` | `[31:30]` | nop / load / compute / store |
| `engine` | `[29:26]` | DMA / MXU / VPU / scalar |
| `src_surface` | `[25:23]` | 源 surface |
| `dst_surface` | `[22:20]` | 目的 surface |
| `apply_scope` | `[19:17]` | 作用范围 |
| `dma_channel_hint` | `[16:14]` | DMA channel hint |
| `dma_burst_type` | `[13:12]` | DMA burst 类型 |
| `fence_after` | `[11]` | 当前 slot 后是否插 fence |

## 8.2 TEMPLATE 长度

```text
template_words = ceil(template_slot_count * 32 / 64)
```

对应关系：

| `template_slot_count` | words |
|---|---|
| 0 | absent |
| 1, 2 | 1 |
| 3, 4 | 2 |
| 5, 6 | 3 |
| 7 | 4 |

## 8.3 controller 怎么用 TEMPLATE

controller 建议把 TEMPLATE materialize 成 `slots[]`：

```c
struct template_slot {
    uint8_t kind;
    uint8_t engine;
    uint8_t src_surface;
    uint8_t dst_surface;
    uint8_t apply_scope;
    uint8_t dma_channel_hint;
    uint8_t dma_burst_type;
    bool    fence_after;
};
```

dispatcher 按 slot 顺序执行即可，不建议引入额外的隐式 slot 语义。

---

## 9. controller 推荐输出的执行上下文

建议 controller parser 最终产出一个面向执行的 `exec_plan_ctx_v010`：

```c
struct exec_plan_ctx_v010 {
    // primary header
    uint8_t  descriptor_version;
    uint8_t  task_type_id;
    uint8_t  dep_mask;
    uint8_t  signal_mask;
    uint8_t  buffer_count;
    uint8_t  loop_rank;
    uint8_t  template_slot_count;

    // family semantic view
    uint8_t  family_words;
    uint8_t  engine_profile;
    uint8_t  primary_output_surface;
    uint8_t  secondary_output_surface;

    struct family_semantic_view family;
    struct buffer_ctx buffers[4];
    struct loop_slot loop[3];
    struct template_slot slots[7];
};
```

关键原则：

- ctx 里保留 controller 真要消费的语义
- raw bitfield 可作为 debug 辅助保存
- dispatcher / DMA / TC.VPU 尽量不要直接读 bitfield

---

## 10. controller 收到 descriptor 之后的推荐执行路径

建议按这个流水来接入：

1. 读取 `primary_header`
2. 推导 `total_words`
3. 拉取完整 descriptor
4. 做 CRC 校验
5. 顺序 parse `FAMILY / BUFFER / LOOP / TEMPLATE`
6. 通过 `task_type_id + FAMILY_SCHEMA_LUT` 做 materialization
7. 生成 `exec_plan_ctx_v010`
8. 交给 dispatcher / DMA / TC.VPU

对于下游模块，推荐分工是：

- parser 负责 bitfield decode
- materializer 负责 family-specific 语义恢复
- dispatcher 负责 slot 级执行调度
- address resolver 负责 `base + loop_coord * stride`

---

## 11. 最容易出错的 8 个点

1. 忘记先检查 `descriptor_version == 0x6`
2. 把 FAMILY 固定按 3 words 解析
3. 在 `RMSNORM / ELEM_ADD / GEGLU` 上多推进 1 个 word
4. 把 BUFFER 误当成 5 words
5. 把 `family_mode` 当成全 family 同义字段，不做 family-specific 解释
6. 没有识别 `KVSTORE` 中 surface slot 的 repurpose（`primary_surface_slot` -> `primary_input_surface`，`secondary_surface_slot` -> `secondary_input_surface`）
7. `loop_rank=1/2` 时仍按 2 words 读 LOOP
8. dispatcher 直接消费 raw fields，导致 family-specific 解释分散在各个下游模块

---

## 12. controller 最小验收标准

建议以这些点作为 parser/dispatcher 接入完成的验收标准：

- 能正确拒绝非 `0x6` descriptor
- 能仅依据 `primary_header` 推导总长度
- CRC 校验通过/失败路径都正确
- FAMILY 2-word / 3-word 两种分支都能通过
- BUFFER 4-word 解码正确
- LOOP 1-word / 2-word 解码正确
- TEMPLATE 变长解码正确
- 11 个 family 都能完成 semantic materialization
- 能输出稳定的 `exec_plan_ctx_v010`

---

## 13. 一句话总结

controller 拿到 v0.10 descriptor 后，正确做法就是：

> **先用 `primary_header` 推导结构，再按固定顺序 parse，再用 LUT 把 FAMILY 物化成执行语义，最后把结果交给 dispatcher。**

只要 parser 和 materialization 这两层边界清楚，后续 controller 的执行接线会比较稳定。
