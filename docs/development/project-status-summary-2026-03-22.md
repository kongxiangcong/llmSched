# 项目状态摘要（2026-03-22）

## 结论

当前项目已经达到可收口状态，更适合定义为 `close-enough / practical stop-line`，而不是继续作为“默认仍在开发中的主线功能项目”。

- `Phase B = done`
- `Phase C = done`
- `Phase D/E = in_progress`

这里的 `in_progress` 更准确地表示“仍有可继续优化项”，而不是“核心链路未完成”。结合最新路线图结论，`SPEC-13`、`SPEC-14/15`、`SPEC-16` 当前 recommendation-detail 分支、以及 `SPEC-19` 当前静态 catalog/workbench 能力，已经可以视为主决策路径上的实践收口线。

## 当前已落地的主线能力

项目已经形成从 frontend 到评估与可视化的完整主线：

1. Frontend / Phase A-B
   - 支持 `ONNX -> GraphIR -> canonical GraphIR -> NIG -> bound-NIG`
   - 已完成 target/scenario profile、合法性检查、Gemma3 lowering、pseudo/fallback analysis

2. Planning / Phase C
   - 已完成 memory planning、tile planning、single-core / dual-core scheduling、descriptor generation
   - 对应 contract、workflow、CLI 与 smoke matrix 已成体系

3. Evaluation / Phase D
   - 已完成 `run-performance-estimation`
   - 已完成 `run-prefill-evaluation`
   - 已完成 `run-decode-evaluation`
   - 已完成 `run-sweep-analysis`
   - 已完成 `run-phase-d-compare`

4. Visualization / Phase E
   - 已完成 `run-visualization-packaging`
   - 已完成 `run-visualization-workbench`
   - 已完成 `run-visualization-catalog`
   - 当前 catalog/workbench 已具备 compare、workspace drill-down、JSON/SVG export 等闭环能力

## 里程碑收口判断

### `SPEC-13`

`SPEC-13` 当前应视为“已足够收口”。

- 路线图已经把它明确标成 `close-enough / practical stop-line`
- 当前 remaining gap 主要是更深的 estimator fidelity 与更细粒度 overlap/slack 策略
- 这些内容更适合未来研究或定向问题修复，不再适合作为默认 blocker

### `SPEC-14/15`

Prefill / Decode 顶层评估链路已经闭环。

- 有独立 contract
- 有 pipeline/workflow
- 有 CLI
- 有 Phase D smoke foundation matrix
- 已接入 pressure summary、hotspot、layer / node 级汇总等主要消费面

### `SPEC-16`

`SPEC-16` 当前 recommendation-detail 分支建议冻结在现有边界。

- 当前 compare surface、fitted compare、workspace continuity、detail export continuity 已达到实用收口线
- 如果后续继续扩展，应只在出现明确 consumer blocker 时再开
- 不建议把“更多交互、更复杂 detail 展示”继续作为默认主线目标

### `SPEC-19`

`SPEC-19` 当前静态 catalog/workbench 表面已经足够支撑项目 closeout。

- workspace drill-down 已存在
- workspace-local link / JSON / SVG export 已存在
- 更丰富的截图 polish、便捷交互、UI 细化可以继续做，但应归类为 downstream polish

## 仓库现状核对

当前仓库中，Phase D/E 相关 CLI 入口已经全部落地在 `src/llm_sched/cli/main.py`：

- `run-performance-estimation`
- `run-prefill-evaluation`
- `run-decode-evaluation`
- `run-sweep-analysis`
- `run-phase-d-compare`
- `run-visualization-packaging`
- `run-visualization-workbench`
- `run-visualization-catalog`

对应的 unit / pipeline / smoke tests 也都在 `tests/` 下有明确覆盖，说明路线图中的状态不只是文档结论，而是和当前代码结构一致。

另外，当前工作树状态为干净：

- branch: `main`
- `git status --short --branch` 无未提交修改

## 验证现状

路线图和开发文档中记录的最新 keep-green 结论是：

- `python -m pytest tests/smoke -m local_smoke -q`
- `python -m pytest tests/smoke -m milestone_matrix -q`
- Phase D focused regression
- visualization focused regression

这些在 2026-03-22 的 closeout audit 中都被记录为绿色。

但需要说明一个现实差异：当前终端环境里没有安装 `pytest`，因此本次梳理无法在本地直接复跑 smoke 来重新确认。`pyproject.toml` 中已经声明了：

- Python >= 3.11
- `pytest>=9,<10` 位于 `project.optional-dependencies.dev`

因此，当前更像是“仓库依赖声明齐全，但本地验证环境尚未激活”。

## 建议的下一步

### 推荐优先级 1：正式收口与交接

建议把当前项目定义为“主线已收口，可进入维护/按需跟进阶段”，并以这份摘要连同以下文档作为 handoff 入口：

- `docs/development/evaluation-compiler-roadmap.md`
- `docs/plans/2026-03-22-project-closeout-audit.md`
- `docs/plans/2026-03-22-spec-16-spec-19-closeout.md`

### 推荐优先级 2：补齐可复现验证环境

如果还要继续维护这个项目，最值得先做的不是继续加功能，而是把本地验证路径固定下来，例如：

- 创建或补充开发环境 bootstrap 说明
- 固定 dev 依赖安装方式
- 固定 `local_smoke` / `milestone_matrix` / focused regression 的运行命令

这样后续任何 reopen 判断都能基于当前仓库直接复现，而不是只依赖文档中的历史绿灯。

### 推荐优先级 3：只接受“证据驱动”的后续开发

后续若要继续推进，建议只接受以下类型的工作：

- 新的 failing test
- 新的 smoke regression
- 明确的 consumer-blocking 缺口
- 对外演示或交付必须补齐的最小 polish

不建议默认继续投入：

- 更深 estimator fidelity 实验
- 更复杂 recommendation-detail 交互扩张
- 更丰富但非阻塞的可视化 convenience 功能

## 一句话判断

这条主线已经从“继续建设功能”转向“完成收口、稳定维护、按证据 reopening”更合适。
