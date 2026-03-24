# Architecture Diagnosis Commit Suggestions

以下是建议的分段提交方式，适合后续人工整理 commit history。

## Commit 1

`feat(diagnosis): add shared DiagnosisContext and pipeline context wiring`

包含：
- `src/llm_sched/analysis/diagnosis_context.py`
- `src/llm_sched/pipeline/diagnosis_analysis.py`
- `tests/unit/pipeline/test_diagnosis_context.py`

## Commit 2

`feat(diagnosis): freeze dataset schema registry and baseline fixtures`

包含：
- `src/llm_sched/contracts/diagnosis_dataset_schema.py`
- `tests/unit/contracts/test_diagnosis_dataset_schema.py`
- `tests_diagnosis_baseline.py`
- `scripts/generate_diagnosis_baselines.py`
- `tests/fixtures/diagnosis_baseline/`
- `tests/unit/pipeline/test_diagnosis_baseline_fixtures.py`

## Commit 3

`refactor(diagnosis): migrate report builders to shared context and extract helpers`

包含：
- 8 个 diagnosis builders 的 `ctx` 接入
- Stage 1~9 extract helpers
- 对应 builder tests

## Commit 4

`feat(diagnosis): add trace/dataset outputs and dataset writer`

包含：
- `src/llm_sched/contracts/diagnosis_common.py`
- `src/llm_sched/analysis/diagnosis_dataset_writer.py`
- `tests/unit/pipeline/test_diagnosis_dataset_writer.py`
- workflow tests 更新

## Commit 5

`feat(diagnosis): add realization gap, timeline loss, and relation dataset views`

包含：
- `src/llm_sched/analysis/realization_gap_builder.py`
- `src/llm_sched/analysis/timeline_loss_builder.py`
- relation / gap / timeline writer 接入
- `tests/unit/analysis/test_realization_gap_builder.py`

## Commit 6

`feat(diagnosis): add chain summary and expand architecture assessment`

包含：
- `src/llm_sched/contracts/diagnosis_chain_summary.py`
- `src/llm_sched/contracts/architecture_assessment_report.py`
- `src/llm_sched/analysis/architecture_assessment_report_builder.py`
- `diagnosis_chain_summary.json` pipeline 接入
- assessment tests / contract tests

## Commit 7

`test(diagnosis): refresh smoke matrix and baseline validation`

包含：
- `tests/smoke/test_cli_run_diagnosis_analysis.py`
- `tests/smoke/test_phase_f_architecture_diagnosis_matrix.py`
- baseline regeneration
- acceptance / progress / pr summary docs

## Squash 版本建议

如果不想保留细粒度历史，可直接 squash 成一条：

`feat(diagnosis): refactor diagnosis pipeline with context, dataset layers, and validation`
