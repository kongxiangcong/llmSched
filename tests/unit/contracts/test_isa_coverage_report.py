from llm_sched.contracts.isa_coverage_report import ISACoverageReport


def test_isa_coverage_report_tracks_mapped_and_gap_counts() -> None:
    report = ISACoverageReport.model_validate(
        {
            "graph_id": "spec-12-graph",
            "schedule_kind": "single-core",
            "mapped_descriptor_count": 12,
            "unmapped_block_count": 2,
            "opcode_counts": {"WDQ_GEMM": 4, "DMA_LOAD": 4, "DMA_STORE": 4},
            "gap_counts": {"opcode_not_supported": 2},
            "issues": [
                {
                    "issue_id": "gap.0",
                    "schedule_block_id": "sched.block.unmapped",
                    "core_id": 0,
                    "stage": "compute",
                    "macro_op": "ATTENTION_MASK_PREP",
                    "requested_opcode": "ATTENTION_MASK_PREP",
                    "code": "opcode_not_supported",
                    "message": "target profile does not advertise ATTENTION_MASK_PREP",
                }
            ],
        }
    )

    assert report.schedule_kind == "single-core"
    assert report.mapped_descriptor_count == 12
    assert report.gap_counts["opcode_not_supported"] == 2
    assert report.issues[0].schedule_block_id == "sched.block.unmapped"
