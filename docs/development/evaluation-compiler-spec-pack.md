# RISC-V + NPU 评估编译器工程规格拆解

## 1. 项目定位

### 1.1 系统使命

本项目要构建的不是“面向既有 RTL 芯片的生产编译器”，而是一套在架构设计初期服务于架构团队的评估型编译器系统。它的核心责任是：

1. 把 Gemma3 这类模型拆成硬件可理解的工作负载单元。
2. 建立从模型语义到硬件语义的可追溯映射。
3. 显式建模 tile、buffer、KV、调度、双核分工与同步。
4. 输出性能估算、带宽压力、瓶颈定位、ISA 覆盖分析。
5. 支持快速改变硬件假设并重跑分析，为架构设计反馈提供工具闭环。

### 1.2 成功标准

系统应至少满足以下结果：

- 能导入 `models/gemma3_1b/model_q4f16.onnx` 并识别 Gemma3 的主路径结构。
- 能分别对 `prefill` 和 `decode` 场景输出单层与整模型级评估结果。
- 能支持 `single-core` 与 `dual-core` 两种目标模式。
- 能输出分层 IR、描述符视图、性能报告、带宽报告、瓶颈分析和 ISA 覆盖报告。
- 能在修改硬件 profile 后无需改代码即可重跑，并给出差异化结果。
- 能通过可视化界面查看模型分解、调度、内存、KV、双核分工和性能热点。

### 1.3 非目标

- 不追求 RTL/cycle-accurate 精度等价。
- 不在第一阶段追求通用多模型、多框架、多芯片集群能力。
- 不把真实驱动/固件/ELF 链接链路作为主要交付。
- 不把训练编译、动态图控制流、自动并行搜索作为第一阶段目标。

## 2. 拆解原则

### 2.1 面向架构评估的四条原则

1. 语义抽象必须对齐架构问题。
   - 以 `macro-op + resource + memory + sync` 为核心语义，而不是把大量框架细节带入后端。
2. 建模必须足够轻。
   - 以分析模型和离线估算为主，避免在 MVP 阶段引入 RTL 级仿真复杂度。
3. 每层 IR 必须服务一个明确评估任务。
   - Graph IR 服务导入与回溯；NIG 服务工作负载抽象；Schedule IR 服务资源映射；Descriptor IR 服务 ISA/编码检查；Analysis IR 服务报告与可视化。
4. 硬件假设必须参数化。
   - 双核模式、DMA 带宽、VMEM 预算、可用 opcode、KV 布局、WDQ 参数都应通过 profile 驱动，而不是散落在代码中。

### 2.2 Spec 切分规则

每个 spec 必须满足：

- 有单一主目标。
- 有明确输入和输出工件。
- 功能边界清楚，知道“不做什么”。
- 可以独立验收，不依赖整系统全部完成。
- 与其它 spec 的依赖关系可枚举。

## 3. Spec 总表

| ID | 名称 | 核心价值 | 主要依赖 |
| --- | --- | --- | --- |
| SPEC-01 | 目标配置与场景配置系统 | 让硬件假设和评测场景可配置、可切换 | 无 |
| SPEC-02 | 驱动入口与工件契约 | 让整条流程有稳定入口和稳定输出 | SPEC-01 |
| SPEC-03 | 模型导入与规范化图 | 把 ONNX 模型转成稳定的 Graph IR | SPEC-01, SPEC-02 |
| SPEC-04 | 工作负载拆解与宏算子识别 | 把模型语义压缩成硬件关注的 workload 单元 | SPEC-03 |
| SPEC-05 | 架构语义模型 | 把 NPU/DMA/VMEM/KV/双核约束转成程序可消费语义 | SPEC-01 |
| SPEC-06 | IR 栈与 Lowering 契约 | 固化 Graph/NIG/Schedule/Descriptor/Analysis IR 的职责与不变量 | SPEC-03, SPEC-04, SPEC-05 |
| SPEC-07 | 量化/形状/布局绑定 | 把 A16W4、shape、layout 约束绑定到 NIG | SPEC-04, SPEC-05, SPEC-06 |
| SPEC-08 | VMEM/KV/地址规划器 | 显式规划 buffer、KV、量化参数和地址绑定 | SPEC-05, SPEC-06, SPEC-07 |
| SPEC-09 | Tile 候选规划器 | 为 GEMM/Attention 建立可评估 tiling 候选 | SPEC-05, SPEC-07, SPEC-08 |
| SPEC-10 | 单核映射与调度器 | 输出合法的单核调度计划 | SPEC-08, SPEC-09 |
| SPEC-11 | 双核映射与调度器 | 输出合法的双核分工、同步和传输计划 | SPEC-08, SPEC-09 |
| SPEC-12 | 描述符生成与 ISA 覆盖映射 | 输出 Descriptor IR，并检查 ISA 覆盖度 | SPEC-06, SPEC-10, SPEC-11 |
| SPEC-13 | 性能估算与瓶颈分析器 | 输出 cycles、带宽、利用率、瓶颈类型 | SPEC-08, SPEC-09, SPEC-10, SPEC-11, SPEC-12 |
| SPEC-14 | Prefill 评估流水线 | 面向长序列 prefill 的端到端评估 | SPEC-02, SPEC-12, SPEC-13 |
| SPEC-15 | Decode 评估流水线 | 面向单 token decode 的端到端评估 | SPEC-02, SPEC-12, SPEC-13 |
| SPEC-16 | 假设扫描与差异对比引擎 | 支持快速修改硬件假设并重跑分析 | SPEC-01, SPEC-13, SPEC-14, SPEC-15 |
| SPEC-17 | 验证与回归框架 | 让每层 IR/规划/报告都有可重复验证 | SPEC-06, SPEC-12, SPEC-13 |
| SPEC-18 | 可视化数据服务 | 把编译和分析工件整理成 UI 可消费数据 | SPEC-02, SPEC-13, SPEC-14, SPEC-15, SPEC-16 |
| SPEC-19 | 可视化分析工作台 | 图形化查看 workload、映射、性能、瓶颈与对比 | SPEC-18 |

## 4. 详细 Spec 条目

### SPEC-01 目标配置与场景配置系统

| 字段 | 内容 |
| --- | --- |
| 目标 | 用统一、可版本化的配置描述硬件假设和评估场景，使“改硬件假设并重跑”成为数据变更而不是代码变更。 |
| 输入 | 架构规格文档中的核心约束；Gemma3 模型配置；评测场景参数，如 `prefill/decode`、`batch`、`seq_len`、`kv_len`、`single-core/dual-core`。 |
| 输出 | `target_profile`、`scenario_profile`、profile 校验规则。 |
| 范围 | Core 数、DMA 带宽、VMEM 布局、KV 约束、可用 opcode、量化能力、同步成本、调度模式约束。 |
| 非范围 | RTL 细节、真实寄存器写序列、驱动实现。 |
| 依赖 | 无。 |
| 验收 | 1. 一个 profile 能完整表达单核和双核模式。<br>2. 修改 `BW_dma_eff`、`core_mode`、`vmem_size` 后，下游任务可直接重跑。<br>3. 非法 profile 会给出明确的约束错误，而不是隐式回退。 |

### SPEC-02 驱动入口与工件契约

| 字段 | 内容 |
| --- | --- |
| 目标 | 定义整套工具链的统一入口和统一输出目录结构，保证不同 spec 产出的工件可互相消费。 |
| 输入 | `target_profile`、`scenario_profile`、模型路径、评估模式、输出目录。 |
| 输出 | 运行目录结构、工件命名规范、JSON/Markdown 报告契约、CLI/服务入口约定。 |
| 范围 | `compile`、`evaluate-prefill`、`evaluate-decode`、`sweep`、`visualize` 等入口；每次运行的 artifact manifest。 |
| 非范围 | 具体前端解析、调度算法、UI 展示。 |
| 依赖 | SPEC-01。 |
| 验收 | 1. 任一一次运行都能产出可枚举的 manifest。<br>2. 所有核心工件都包含版本号、profile 引用、scenario 引用。<br>3. 下游模块只靠 artifact contract 就能读取前序输出。 |

### SPEC-03 模型导入与规范化图

| 字段 | 内容 |
| --- | --- |
| 目标 | 以 ONNX 主路径把 Gemma3 模型转成稳定的 Graph IR，并保留源节点可追溯关系。 |
| 输入 | `models/gemma3_1b/model_q4f16.onnx`、`models/gemma3_1b/config.json`。 |
| 输出 | Graph IR、source map、导入诊断报告。 |
| 范围 | ONNX 导入、常量节点显式化、广播规则显式化、规范化 MatMul/Norm/Attention 子图表达。 |
| 非范围 | 通用动态图控制流、训练图、非 Gemma3 优先路径的广泛框架兼容。 |
| 依赖 | SPEC-01、SPEC-02。 |
| 验收 | 1. Gemma3 ONNX 能稳定导入并输出 DAG 化 Graph IR。<br>2. 关键张量 shape、dtype、source map 可查询。<br>3. 不支持的节点和属性会以显式诊断暴露。 |

### SPEC-04 工作负载拆解与宏算子识别

| 字段 | 内容 |
| --- | --- |
| 目标 | 把 Graph IR 中的框架语义压缩成架构关心的宏算子工作负载单元。 |
| 输入 | Graph IR、Gemma3 pattern 规则。 |
| 输出 | NIG 初稿、pattern 匹配报告、未识别子图列表。 |
| 范围 | `RMSNORM_GEMM`、`ROPE`、`SDPA`、`SDPA_DECODE`、`GEGLU`、`KVSTORE/KVLOAD`、`WDQ_GEMM` 等宏算子识别。 |
| 非范围 | 资源调度、地址规划、最终 opcode 编码。 |
| 依赖 | SPEC-03。 |
| 验收 | 1. Gemma3 单层可拆成与架构规格一致的宏算子序列。<br>2. 每个宏算子都能关联原始框架节点集合。<br>3. 未命中 pattern 的路径不会静默丢失，而会进入保守路径或报错。 |

### SPEC-05 架构语义模型

| 字段 | 内容 |
| --- | --- |
| 目标 | 用一套轻量但严格的语义模型表示 NPU Core、DMA、VPU、MXU、WDQ、VMEM、KV 和双核同步约束。 |
| 输入 | `target_profile`、架构规格文档约束。 |
| 输出 | 资源模型、约束检查器、能力查询接口。 |
| 范围 | `VPU` 是 `MXU` 唯一主控；NoC 不参与单加速器内部路由；DMA 是唯一外存访问者；单核/双核模式语义；VMEM 分区；KV 地址规则。 |
| 非范围 | 真实 RTL 状态机、时钟域实现细节、NoC 多芯片扩展细节。 |
| 依赖 | SPEC-01。 |
| 验收 | 1. 同一架构模型能实例化单核或双核目标。<br>2. 违反刚性约束的方案在规划阶段就会被拒绝。<br>3. 架构能力查询可被 tiling、调度、描述符、分析模块复用。 |

### SPEC-06 IR 栈与 Lowering 契约

| 字段 | 内容 |
| --- | --- |
| 目标 | 固化 Graph IR、NIG、Schedule IR、Descriptor IR、Analysis IR 的职责、字段与不变量。 |
| 输入 | Graph IR、NIG、架构语义模型。 |
| 输出 | IR schema、validator、层间映射规则、dump 契约。 |
| 范围 | 每层 IR 的字段定义、层间 traceability、层间合法性检查。 |
| 非范围 | 各具体启发式算法本身。 |
| 依赖 | SPEC-03、SPEC-04、SPEC-05。 |
| 验收 | 1. 每层 IR 都可独立 dump 和校验。<br>2. 任一 Descriptor 字段都能回溯到上层语义来源。<br>3. 不满足 `single-core`/`dual-core` 不变量的 Schedule IR 会被 validator 拒绝。 |

### SPEC-07 量化/形状/布局绑定

| 字段 | 内容 |
| --- | --- |
| 目标 | 在 NIG 上绑定 A16W4、静态 shape、layout 与 memory class，使工作负载变成可规划对象。 |
| 输入 | NIG、模型量化信息、架构 profile。 |
| 输出 | 完整 shape/layout/quant 标注后的 NIG。 |
| 范围 | `W_DTYPE/A_DTYPE/QUANT_MODE/GROUP_SIZE`、`SD/HSD/BHSD/LBHSD` 布局、memory class 标记、shape 收敛。 |
| 非范围 | 权重真正打包落盘、描述符编码、调度顺序。 |
| 依赖 | SPEC-04、SPEC-05、SPEC-06。 |
| 验收 | 1. 每个量化线性层都携带合法 `scale/zp/group_size` 信息。<br>2. `GROUP_SIZE` 与 `K_tile` 对齐约束可被提前发现。<br>3. 所有关键张量都能收敛到架构允许的布局之一。 |

### SPEC-08 VMEM/KV/地址规划器

| 字段 | 内容 |
| --- | --- |
| 目标 | 显式规划 VMEM 区域、DDR 地址、KV 地址和量化参数地址，支撑 prefill/decode 两条路径。 |
| 输入 | 完整 NIG、架构语义模型、scenario profile。 |
| 输出 | `MemAllocTable`、KV 地址公式绑定、VMEM fit 诊断、地址映射工件。 |
| 范围 | Ping/Pong、Weight VMEM、Accum、Misc、Quant 区；KV layer/token stride；量化参数区；双核数据交换路径选择。 |
| 非范围 | 动态内存管理器、运行时抢占式地址重分配。 |
| 依赖 | SPEC-05、SPEC-06、SPEC-07。 |
| 验收 | 1. 给定 layer/scenario 可输出确定性的 VMEM 布局。<br>2. Decode 场景可输出可复核的 KV 地址公式和带宽用量。<br>3. VMEM fit 失败时能说明是激活、权重、累加还是量化区导致。 |

### SPEC-09 Tile 候选规划器

| 字段 | 内容 |
| --- | --- |
| 目标 | 在 `N_tile=128`、`K_tile=128` 的硬件边界内，为 GEMM/Attention 生成可评估的 tile 候选。 |
| 输入 | 量化/shape/layout 完整的 NIG、VMEM 规划结果、profile。 |
| 输出 | `TilingPlan` 候选集、每个候选的资源占用摘要。 |
| 范围 | `M_tile` 求解；prefill 与 decode 的不同默认策略；量化组与 tile 对齐；Weight/Activation/Output tile 大小估算。 |
| 非范围 | 最终资源排程、跨 core 同步决策。 |
| 依赖 | SPEC-05、SPEC-07、SPEC-08。 |
| 验收 | 1. Prefill 能输出一组可比较的 `M_tile` 候选。<br>2. Decode 默认可收敛到 `M_tile=1` 或说明为何不能。<br>3. 每个候选都带有 VMEM 占用、DMA 体量和 quant 对齐说明。 |

### SPEC-10 单核映射与调度器

| 字段 | 内容 |
| --- | --- |
| 目标 | 为 `single-core` 模式输出合法、稳定、可分析的资源调度计划。 |
| 输入 | `TilingPlan`、地址规划、架构语义模型。 |
| 输出 | 单核 Schedule IR、资源时间线、局部同步点。 |
| 范围 | DMA 预取、VPU 前处理、WDQ/MXU 计算、VPU 后处理、写回排序；资源冲突消解；调度稳定性。 |
| 非范围 | 双核 barrier、跨核传输、跨模式比较。 |
| 依赖 | SPEC-08、SPEC-09。 |
| 验收 | 1. 输出 Schedule IR 中所有 block 只绑定一个 core。<br>2. 不出现 `Core Link` 和跨 core barrier。<br>3. 同一输入在同一 profile 下生成稳定调度结果。 |

### SPEC-11 双核映射与调度器

| 字段 | 内容 |
| --- | --- |
| 目标 | 为 `dual-core` 模式生成数据并行、模型并行或流水线并行的合法候选并选择最佳方案。 |
| 输入 | `TilingPlan`、地址规划、双核 profile。 |
| 输出 | 双核 Schedule IR、core 分工摘要、barrier/transfer 计划。 |
| 范围 | 双核候选生成；共享 DMA 竞争；Core Link / DMA 传输选择；barrier 插入；负载均衡代价。 |
| 非范围 | 自动在单核与双核之间切换；多于 2 个 core 的扩展。 |
| 依赖 | SPEC-08、SPEC-09。 |
| 验收 | 1. 所有跨 core 依赖都显式化。<br>2. 每个候选都能输出同步成本和跨核传输成本。<br>3. 若双核不划算，系统也能说明瓶颈来自 DMA、同步还是不均衡。 |

### SPEC-12 描述符生成与 ISA 覆盖映射

| 字段 | 内容 |
| --- | --- |
| 目标 | 把 Schedule IR 转成 Descriptor IR，并输出 ISA 覆盖与缺口分析。 |
| 输入 | Schedule IR、量化/地址/形状信息、opcode 能力表。 |
| 输出 | Descriptor IR、descriptor 序列、ISA coverage report、unsupported gap report。 |
| 范围 | opcode 选择、字段打包、地址字段绑定、`GROUP_SIZE` 编码、调度到 descriptor 的审计映射。 |
| 非范围 | 真正执行硬件队列、驱动源码生成、真实 ELF 构建。 |
| 依赖 | SPEC-06、SPEC-10、SPEC-11。 |
| 验收 | 1. 每个 descriptor 都能无歧义编码到 512bit 视图。<br>2. 每个宏算子要么成功映射到 opcode，要么进入覆盖缺口报告。<br>3. coverage report 能按 layer/op/pattern 汇总缺失能力。 |

### SPEC-13 性能估算与瓶颈分析器

| 字段 | 内容 |
| --- | --- |
| 目标 | 在不依赖 RTL 的前提下，对编译结果输出有工程价值的 cycles、带宽、利用率和瓶颈分析。 |
| 输入 | Schedule IR、Descriptor IR、tile 计划、profile、scenario。 |
| 输出 | `perf_report`、带宽压力报告、瓶颈归因报告、层级统计。 |
| 范围 | `T_compute`、`T_dma`、`T_kv`、同步成本、跨核传输成本、计算/内存/同步三类瓶颈归因。 |
| 非范围 | 门级精度、真实 DDR 控制器微结构、硅后时钟收敛。 |
| 依赖 | SPEC-08、SPEC-09、SPEC-10、SPEC-11、SPEC-12。 |
| 验收 | 1. 报告至少覆盖 per-op、per-layer、whole-run 三个粒度。<br>2. 能区分 compute-bound、memory-bound、sync-bound、ISA-gap-bound。<br>3. 估算过程依赖的参数都来自 profile/scenario，而不是硬编码。 |

### SPEC-14 Prefill 评估流水线

| 字段 | 内容 |
| --- | --- |
| 目标 | 建立面向 `prefill` 的端到端评估入口，产出适合长序列分析的编译和性能结果。 |
| 输入 | 模型、`prefill` scenario、target profile。 |
| 输出 | Prefill 的 IR dumps、调度结果、性能报告、带宽报告、瓶颈报告。 |
| 范围 | `seq_len > 1` 的 attention 计算路径、长序列 `M_tile` 评估、单核/双核比较内的同模式排序。 |
| 非范围 | 单 token decode 的 KV 增长行为。 |
| 依赖 | SPEC-02、SPEC-12、SPEC-13。 |
| 验收 | 1. 给定单层或整模型 prefill 请求能产出完整评估工件。<br>2. 报告能体现 MXU 主导计算路径和吞吐视角。<br>3. 能分别在单核和双核 profile 下复跑并生成可比较结果。 |

### SPEC-15 Decode 评估流水线

| 字段 | 内容 |
| --- | --- |
| 目标 | 建立面向 `decode` 的端到端评估入口，重点分析单 token 延迟和 KV 访问成本。 |
| 输入 | 模型、`decode` scenario、target profile、当前 KV 长度。 |
| 输出 | Decode 的 IR dumps、性能报告、KV 带宽报告、token 延迟拆解报告。 |
| 范围 | `S_q = 1` 路径、`SDPA_DECODE` 选择、KV stride/带宽建模、滑窗和 `S_cur` 变化影响。 |
| 非范围 | 长序列 prefill 吞吐建模。 |
| 依赖 | SPEC-02、SPEC-12、SPEC-13。 |
| 验收 | 1. 报告能展示 token 延迟由 `q_proj`、`kv load`、`dot`、`softmax`、`value` 等组成。<br>2. 能观察 `S_cur` 增长带来的带宽压力变化。<br>3. 单核/双核 profile 都能得到合法分析结果，即使最终结论是某模式不合适。 |

### SPEC-16 假设扫描与差异对比引擎

| 字段 | 内容 |
| --- | --- |
| 目标 | 支持批量修改硬件假设并自动重跑，生成多版本对比报告。 |
| 输入 | 基线 profile、变体矩阵、prefill/decode 评估任务。 |
| 输出 | 差异报告、排序结果、敏感参数分析、回归对比工件。 |
| 范围 | `DMA BW`、`VMEM size`、`core_mode`、`group_size`、`sync_cost`、`opcode availability` 等假设扫描。 |
| 非范围 | 自动搜索最优芯片设计；替代架构师做最终设计决策。 |
| 依赖 | SPEC-01、SPEC-13、SPEC-14、SPEC-15。 |
| 验收 | 1. 一组 profile 变体可在同一批任务下自动复跑。<br>2. 对比报告能按指标和 layer/op 两个维度展示差异。<br>3. 每个差异都能追溯到具体 profile 变化项。 |

### SPEC-17 验证与回归框架

| 字段 | 内容 |
| --- | --- |
| 目标 | 为每层 IR、每类规划器和每类报告提供最小但稳定的验证与回归机制。 |
| 输入 | IR dumps、descriptor 工件、golden 子图、公式化期望结果。 |
| 输出 | invariant check、回归报告、失败样本包。 |
| 范围 | IR validator、pattern 回归、地址公式校验、descriptor 编码校验、性能报告字段校验、差异阈值回归。 |
| 非范围 | 与 RTL 的全量数值对拍；硅后板级验证。 |
| 依赖 | SPEC-06、SPEC-12、SPEC-13。 |
| 验收 | 1. 每个核心 IR 层都有 invariant test。<br>2. 每个核心宏算子路径都有最小回归样例。<br>3. 性能报告和 coverage 报告字段的 schema 有自动校验。 |

### SPEC-18 可视化数据服务

| 字段 | 内容 |
| --- | --- |
| 目标 | 把编译与评估工件转换成前端可查询的数据服务层，隔离 UI 与内部实现细节。 |
| 输入 | manifest、IR dumps、perf/bandwidth/bottleneck/coverage/sweep 报告。 |
| 输出 | UI 查询模型、聚合接口或静态数据包、视图索引。 |
| 范围 | layer/op/core/tensor/scenario/profile 维度的聚合查询；差异对比数据视图。 |
| 非范围 | 前端渲染逻辑、布局和交互设计。 |
| 依赖 | SPEC-02、SPEC-13、SPEC-14、SPEC-15、SPEC-16。 |
| 验收 | 1. UI 不需要理解底层 IR schema 差异也能取数。<br>2. 同一次运行的所有视图都能通过 run id / manifest 关联。<br>3. 能为 graph、timeline、KV、VMEM、coverage、sweep 六类视图提供直接数据。 |

### SPEC-19 可视化分析工作台

| 字段 | 内容 |
| --- | --- |
| 目标 | 提供工程师可直接使用的分析界面，查看 workload 分解、映射结果、性能热点和假设变更影响。 |
| 输入 | 可视化数据服务提供的数据。 |
| 输出 | 可交互的分析工作台。 |
| 范围 | Graph 视图、layer timeline、core occupancy、VMEM/quant/KV 视图、瓶颈归因、ISA coverage、假设对比面板。 |
| 非范围 | 在线编辑模型、自动修复编译结果、替代命令行驱动。 |
| 依赖 | SPEC-18。 |
| 验收 | 1. 能从模型层一路钻取到宏算子、schedule block、descriptor 和报告项。<br>2. 能切换 `prefill/decode` 和 `single-core/dual-core` 观察差异。<br>3. 能直接展示“为什么慢”以及“改了哪个硬件假设导致变化”。 |

## 5. 推荐的系统分层

为避免系统在实现早期就耦合成“大一统编译器”，建议按以下分层推进：

1. 约束与契约层
   - SPEC-01、SPEC-02、SPEC-05、SPEC-06
2. 语义建模层
   - SPEC-03、SPEC-04、SPEC-07
3. 映射与规划层
   - SPEC-08、SPEC-09、SPEC-10、SPEC-11、SPEC-12
4. 评估与分析层
   - SPEC-13、SPEC-14、SPEC-15、SPEC-16、SPEC-17
5. 产品化与可视化层
   - SPEC-18、SPEC-19

## 6. 关键边界结论

### 6.1 应该保留的复杂度

- 宏算子级工作负载建模。
- 单核/双核两套正式模式。
- Prefill/Decode 两条独立评估路径。
- VMEM/KV/量化参数的显式地址规划。
- Descriptor IR 与 ISA coverage 的硬件对齐检查。

### 6.2 应该主动避免的复杂度

- 在 MVP 阶段引入通用图优化器野心。
- 为了“真实”而过早转向 RTL/cycle-accurate 仿真。
- 让运行时或 UI 直接依赖内部 IR 细节。
- 把 profile、公式和硬件约束散落在多个模块里。

## 7. 交付建议

后续开发应以 `SPEC-01` 到 `SPEC-19` 作为一组正式的工程需求单元。每个 spec 在进入实现时，再切成 3 到 5 个 story，建议 story 结构固定为：

1. 契约与数据结构。
2. 核心算法或转换逻辑。
3. dump / report / diagnostics。
4. 最小验证与回归。

这样可以保持每个开发迭代既能前进，也能被验证。
