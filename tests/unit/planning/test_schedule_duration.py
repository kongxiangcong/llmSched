from pathlib import Path
from math import ceil


def test_estimate_stage_duration_slots_specializes_vector_compute_macros() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)

    rmsnorm_node = _make_vector_node("nig.node.norm", "RMSNORM", [1, 128, 1024])
    geglu_node = _make_vector_node("nig.node.geglu", "GEGLU", [1, 128, 1024])
    rope_node = _make_vector_node("nig.node.rope", "ROPE", [1, 128, 1024])
    helper_node = _make_vector_node("nig.node.helper", "SHAPE_HELPER", [1, 128, 1024])
    mask_node = _make_vector_node("nig.node.mask", "ATTENTION_MASK_PREP", [1, 128, 1024])

    rmsnorm_duration = estimate_stage_duration_slots(
        node=rmsnorm_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    geglu_duration = estimate_stage_duration_slots(
        node=geglu_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    rope_duration = estimate_stage_duration_slots(
        node=rope_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    helper_duration = estimate_stage_duration_slots(
        node=helper_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    mask_duration = estimate_stage_duration_slots(
        node=mask_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )

    assert geglu_duration > rmsnorm_duration
    assert rope_duration > helper_duration
    assert mask_duration > helper_duration


def test_estimate_stage_duration_slots_specializes_geglu_prepare() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)

    geglu_node = _make_vector_node("nig.node.geglu", "GEGLU", [1, 128, 1024])
    helper_node = _make_vector_node("nig.node.helper", "SHAPE_HELPER", [1, 128, 1024])

    geglu_prepare = estimate_stage_duration_slots(
        node=geglu_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    helper_prepare = estimate_stage_duration_slots(
        node=helper_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )

    assert geglu_prepare > helper_prepare


def test_estimate_stage_duration_slots_specializes_attention_mask_prep_by_original_op_kind() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)

    add_node = _make_attention_mask_prep_node("nig.node.mask.add", [1, 1, 128, 128], "Add")
    trilu_node = _make_attention_mask_prep_node("nig.node.mask.trilu", [1, 1, 128, 128], "Trilu")

    add_prepare = estimate_stage_duration_slots(
        node=add_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    trilu_prepare = estimate_stage_duration_slots(
        node=trilu_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    add_compute = estimate_stage_duration_slots(
        node=add_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    trilu_compute = estimate_stage_duration_slots(
        node=trilu_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )

    assert add_prepare == trilu_prepare
    assert trilu_compute > add_compute


def test_estimate_stage_duration_slots_characterizes_layout_fallback_as_dma_then_vpu_then_dma() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)

    layout_node = _make_layout_fallback_node("nig.node.layout", [1, 1152, 1])
    helper_node = _make_vector_node("nig.node.helper", "SHAPE_HELPER", [1, 1152, 1])

    layout_dma = estimate_stage_duration_slots(
        node=layout_node,
        stage="dma_in",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    layout_prepare = estimate_stage_duration_slots(
        node=layout_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    layout_compute = estimate_stage_duration_slots(
        node=layout_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    layout_store = estimate_stage_duration_slots(
        node=layout_node,
        stage="store",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    helper_prepare = estimate_stage_duration_slots(
        node=helper_node,
        stage="prepare",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )
    helper_compute = estimate_stage_duration_slots(
        node=helper_node,
        stage="compute",
        candidate=None,
        allocations=[],
        capabilities=capabilities,
    )

    assert layout_prepare > helper_prepare
    assert layout_compute > helper_compute
    assert estimate_stage_resource_reservations(
        macro_op="LAYOUT_FALLBACK",
        stage="dma_in",
        resource_set=["DMA"],
        duration_slots=layout_dma,
        node=layout_node,
        candidate=None,
        capabilities=capabilities,
    ) == [("DMA", 0, layout_dma)]
    layout_store_reservations = estimate_stage_resource_reservations(
        macro_op="LAYOUT_FALLBACK",
        stage="store",
        resource_set=["DMA"],
        duration_slots=layout_store,
        node=layout_node,
        candidate=None,
        capabilities=capabilities,
    )
    assert any(resource_name == "DMA" for resource_name, _start, _duration in layout_store_reservations)
    assert layout_store_reservations[-1][1] + layout_store_reservations[-1][2] == layout_store


def test_estimate_stage_resource_reservations_specializes_layout_fallback_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    layout_node = _make_layout_fallback_node("nig.node.layout.store", [1, 1152, 1])
    allocations = [_make_allocation("alloc.output", "output", 32768)]

    duration_slots = estimate_stage_duration_slots(
        node=layout_node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="LAYOUT_FALLBACK",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=layout_node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_attention_mask_prep_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    allocations = [_make_allocation("alloc.output", "output", 32768)]
    add_node = _make_attention_mask_prep_node("nig.node.mask.add.store", [1, 1, 128, 128], "Add")
    trilu_node = _make_attention_mask_prep_node("nig.node.mask.trilu.store", [1, 1, 128, 128], "Trilu")

    add_duration_slots = estimate_stage_duration_slots(
        node=add_node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    trilu_duration_slots = estimate_stage_duration_slots(
        node=trilu_node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    add_reservations = estimate_stage_resource_reservations(
        macro_op="ATTENTION_MASK_PREP",
        stage="store",
        resource_set=["DMA"],
        duration_slots=add_duration_slots,
        node=add_node,
        candidate=None,
        capabilities=capabilities,
    )
    trilu_reservations = estimate_stage_resource_reservations(
        macro_op="ATTENTION_MASK_PREP",
        stage="store",
        resource_set=["DMA"],
        duration_slots=trilu_duration_slots,
        node=trilu_node,
        candidate=None,
        capabilities=capabilities,
    )

    add_vpu_reservation = next(item for item in add_reservations if item[0] == "VPU")
    add_dma_reservation = next(item for item in add_reservations if item[0] == "DMA")
    trilu_vpu_reservation = next(item for item in trilu_reservations if item[0] == "VPU")
    trilu_dma_reservation = next(item for item in trilu_reservations if item[0] == "DMA")

    assert add_vpu_reservation[1] == 0
    assert trilu_vpu_reservation[1] == 0
    assert trilu_vpu_reservation[2] > add_vpu_reservation[2] > 0
    assert add_dma_reservation[1] == add_vpu_reservation[2]
    assert trilu_dma_reservation[1] == trilu_vpu_reservation[2]
    assert add_dma_reservation[1] + add_dma_reservation[2] == add_duration_slots
    assert trilu_dma_reservation[1] + trilu_dma_reservation[2] == trilu_duration_slots


def test_estimate_stage_resource_reservations_specializes_rope_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    rope_node = _make_vector_node("nig.node.rope.store", "ROPE", [1, 128, 1024])
    allocations = [_make_allocation("alloc.output", "output", 32768)]

    duration_slots = estimate_stage_duration_slots(
        node=rope_node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="ROPE",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=rope_node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_embedding_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_embedding_lookup_node("nig.node.embedding.store", [1, 16, 1024])
    allocations = [_make_allocation("alloc.output", "output", 32768)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="EMBEDDING_LOOKUP",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_duration_slots_specializes_mixed_engine_compute_macros() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import estimate_stage_duration_slots

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.m48.n128.k128", "fixture", "GEMM")

    gemm_duration = estimate_stage_duration_slots(
        node=_make_gemm_like_node("nig.node.gemm", "GEMM", [1, 128, 1024]),
        stage="compute",
        candidate=candidate,
        allocations=[],
        capabilities=capabilities,
    )
    wdq_duration = estimate_stage_duration_slots(
        node=_make_gemm_like_node("nig.node.wdq", "WDQ_GEMM", [1, 128, 1024]),
        stage="compute",
        candidate=candidate.model_copy(update={"macro_op": "WDQ_GEMM", "candidate_id": "fixture.wdq"}),
        allocations=[],
        capabilities=capabilities,
    )
    rmsnorm_gemm_duration = estimate_stage_duration_slots(
        node=_make_gemm_like_node("nig.node.rg", "RMSNORM_GEMM", [1, 128, 1024]),
        stage="compute",
        candidate=candidate.model_copy(update={"macro_op": "RMSNORM_GEMM", "candidate_id": "fixture.rg"}),
        allocations=[],
        capabilities=capabilities,
    )
    sdpa_duration = estimate_stage_duration_slots(
        node=_make_sdpa_like_node("nig.node.sdpa", "SDPA", [1, 128, 1024], query_len=48, kv_len=128),
        stage="compute",
        candidate=candidate.model_copy(update={"macro_op": "SDPA", "candidate_id": "fixture.sdpa"}),
        allocations=[],
        capabilities=capabilities,
    )
    sdpa_decode_duration = estimate_stage_duration_slots(
        node=_make_sdpa_like_node("nig.node.sdpa.decode", "SDPA_DECODE", [1, 1, 1024], query_len=1, kv_len=2049),
        stage="compute",
        candidate=candidate.model_copy(update={"macro_op": "SDPA_DECODE", "candidate_id": "fixture.sdpa.decode"}),
        allocations=[],
        capabilities=capabilities,
    )

    assert wdq_duration > gemm_duration
    assert rmsnorm_gemm_duration > gemm_duration
    assert sdpa_duration > gemm_duration
    assert sdpa_decode_duration > gemm_duration


def test_estimate_stage_resource_reservations_specializes_wdq_prefix() -> None:
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    reservations = estimate_stage_resource_reservations(
        macro_op="WDQ_GEMM",
        stage="compute",
        resource_set=["WDQ", "MXU"],
        duration_slots=64,
    )

    wdq_reservation = next(item for item in reservations if item[0] == "WDQ")
    mxu_reservation = next(item for item in reservations if item[0] == "MXU")

    assert wdq_reservation == ("WDQ", 0, 8)
    assert mxu_reservation[1] > 0
    assert mxu_reservation[1] + mxu_reservation[2] == 64


def test_estimate_stage_resource_reservations_aligns_rmsnorm_gemm_prefix_with_overhead() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.rg", "fixture", "RMSNORM_GEMM")
    node = _make_gemm_like_node("nig.node.rg", "RMSNORM_GEMM", [1, 128, 1024])

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="compute",
        candidate=candidate,
        allocations=[],
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="RMSNORM_GEMM",
        stage="compute",
        resource_set=["VPU", "MXU"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    expected_overhead_slots = ceil((candidate.m_tile * candidate.n_tile) / capabilities.vpu.lanes)
    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    mxu_reservation = next(item for item in reservations if item[0] == "MXU")

    assert vpu_reservation == ("VPU", 0, expected_overhead_slots)
    assert mxu_reservation == ("MXU", expected_overhead_slots, duration_slots - expected_overhead_slots)


def test_estimate_stage_resource_reservations_aligns_geglu_with_vpu_prefix_and_tail() -> None:
    from llm_sched.planning.schedule_duration import estimate_stage_resource_reservations

    reservations = estimate_stage_resource_reservations(
        macro_op="GEGLU",
        stage="compute",
        resource_set=["MXU", "VPU"],
        duration_slots=64,
    )

    vpu_reservations = [item for item in reservations if item[0] == "VPU"]
    mxu_reservation = next(item for item in reservations if item[0] == "MXU")

    assert vpu_reservations == [("VPU", 0, 8), ("VPU", 48, 16)]
    assert mxu_reservation == ("MXU", 8, 40)


def test_estimate_stage_resource_reservations_aligns_sdpa_prefix_and_tail_with_overhead() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.sdpa", "fixture", "SDPA")
    node = _make_sdpa_like_node("nig.node.sdpa", "SDPA", [1, 128, 1024], query_len=48, kv_len=128)

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="compute",
        candidate=candidate,
        allocations=[],
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA",
        stage="compute",
        resource_set=["MXU", "VPU"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    expected_overhead_slots = ceil((48 * 128 * 4) / capabilities.vpu.lanes)
    expected_prefix_slots = max(1, ceil(expected_overhead_slots / 2))
    expected_tail_slots = max(0, expected_overhead_slots - expected_prefix_slots)
    base_gemm_slots = duration_slots - expected_overhead_slots
    mxu_reservation = next(item for item in reservations if item[0] == "MXU")
    vpu_reservations = [item for item in reservations if item[0] == "VPU"]

    assert mxu_reservation == ("MXU", expected_prefix_slots, base_gemm_slots)
    assert vpu_reservations == [
        ("VPU", 0, expected_prefix_slots),
        ("VPU", expected_prefix_slots + base_gemm_slots, expected_tail_slots),
    ]


def test_estimate_stage_resource_reservations_keeps_sdpa_decode_on_dma_and_vpu() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.sdpa.decode", "fixture", "SDPA_DECODE")
    node = _make_sdpa_like_node(
        "nig.node.sdpa.decode",
        "SDPA_DECODE",
        [1, 1, 1024],
        query_len=1,
        kv_len=2049,
    )
    allocations = [
        _make_allocation("alloc.kv", "kv_cache", 131072),
        _make_allocation("alloc.output", "output", 2048),
    ]
    expected_vpu_slots = ceil((1 * 2049 * 4) / capabilities.vpu.lanes)
    expected_dma_bytes = 131072
    expected_dma_slots = ceil(expected_dma_bytes / (capabilities.shared_dma.effective_bandwidth_gbps * 64.0))

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="compute",
        candidate=candidate,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA_DECODE",
        stage="compute",
        resource_set=["DMA", "VPU"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    assert expected_vpu_slots < expected_dma_slots
    assert duration_slots == max(expected_vpu_slots, expected_dma_slots)
    assert ("DMA", 0, expected_dma_slots) in reservations
    assert ("VPU", 0, expected_vpu_slots) in reservations
    assert ("VPU", 0, duration_slots) not in reservations
    assert all(resource_name != "MXU" for resource_name, _start, _duration in reservations)


def test_estimate_stage_resource_reservations_specializes_wdq_dma_in_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_gemm_like_node("nig.node.wdq.dma", "WDQ_GEMM", [1, 128, 1024])
    candidate = _make_tile_candidate("fixture.wdq.dma", "fixture", "WDQ_GEMM")
    allocations = [
        _make_allocation("alloc.input", "input", 8192),
        _make_allocation("alloc.weight", "weight", 16384),
        _make_allocation("alloc.quant", "quant_param", 2048),
    ]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="dma_in",
        candidate=candidate,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="WDQ_GEMM",
        stage="dma_in",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    dma_reservation = next(item for item in reservations if item[0] == "DMA")
    wdq_reservation = next(item for item in reservations if item[0] == "WDQ")

    assert dma_reservation[1] == 0
    assert dma_reservation[2] < duration_slots
    assert wdq_reservation[1] == dma_reservation[2]
    assert wdq_reservation[1] + wdq_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_kvstore_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_vector_node("nig.node.kvstore", "KVSTORE", [1, 128, 1024])
    allocations = [_make_allocation("alloc.output", "output", 32768)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="KVSTORE",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_sdpa_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.sdpa.store", "fixture", "SDPA")
    node = _make_sdpa_like_node("nig.node.sdpa.store", "SDPA", [1, 128, 1024], query_len=128, kv_len=128)
    allocations = [_make_allocation("alloc.output", "output", 65536)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=candidate,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_sdpa_decode_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    candidate = _make_tile_candidate("fixture.sdpa.decode.store", "fixture", "SDPA_DECODE")
    node = _make_sdpa_like_node(
        "nig.node.sdpa.decode.store",
        "SDPA_DECODE",
        [1, 1, 1024],
        query_len=1,
        kv_len=2049,
    )
    allocations = [_make_allocation("alloc.output", "output", 32768)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=candidate,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="SDPA_DECODE",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=candidate,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_rmsnorm_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_vector_node("nig.node.rmsnorm.store", "RMSNORM", [1, 128, 1024])
    allocations = [_make_allocation("alloc.output", "output", 65536)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="RMSNORM",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_geglu_store_prefix() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_vector_node("nig.node.geglu.store", "GEGLU", [1, 128, 1024])
    allocations = [_make_allocation("alloc.output", "output", 65536)]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="store",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="GEGLU",
        stage="store",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    vpu_reservation = next(item for item in reservations if item[0] == "VPU")
    dma_reservation = next(item for item in reservations if item[0] == "DMA")

    assert vpu_reservation[1] == 0
    assert dma_reservation[1] > 0
    assert dma_reservation[1] == vpu_reservation[2]
    assert dma_reservation[1] + dma_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_kvload_dma_in_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_vector_node("nig.node.kvload", "KVLOAD", [1, 128, 1024])
    allocations = [
        _make_allocation("alloc.kv", "kv_cache", 32768),
        _make_allocation("alloc.output", "output", 32768),
    ]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="dma_in",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="KVLOAD",
        stage="dma_in",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    dma_reservation = next(item for item in reservations if item[0] == "DMA")
    vpu_reservation = next(item for item in reservations if item[0] == "VPU")

    assert dma_reservation[1] == 0
    assert dma_reservation[2] < duration_slots
    assert vpu_reservation[1] == dma_reservation[2]
    assert vpu_reservation[1] + vpu_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_embedding_lookup_dma_in_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_embedding_lookup_node("nig.node.embedding", [1, 16, 1024])
    allocations = [
        _make_allocation("alloc.weight", "weight", 32768),
        _make_allocation("alloc.meta", "metadata", 512),
    ]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="dma_in",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="EMBEDDING_LOOKUP",
        stage="dma_in",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    dma_reservation = next(item for item in reservations if item[0] == "DMA")
    vpu_reservation = next(item for item in reservations if item[0] == "VPU")

    assert dma_reservation[1] == 0
    assert dma_reservation[2] < duration_slots
    assert vpu_reservation[1] == dma_reservation[2]
    assert vpu_reservation[1] + vpu_reservation[2] == duration_slots


def test_estimate_stage_resource_reservations_specializes_rope_table_dma_in_tail() -> None:
    from llm_sched.arch.capabilities import ArchitectureCapabilities
    from llm_sched.config.loader import load_target_profile
    from llm_sched.planning.schedule_duration import (
        estimate_stage_duration_slots,
        estimate_stage_resource_reservations,
    )

    repo_root = Path(__file__).resolve().parents[3]
    target = load_target_profile(repo_root / "profiles" / "targets" / "riscv_npu_single_core_v1.json")
    capabilities = ArchitectureCapabilities.from_target_profile(target)
    node = _make_rope_table_node("nig.node.rope.table", [1, 1, 256])
    allocations = [
        _make_allocation("alloc.position_ids", "metadata", 32),
        _make_allocation("alloc.inv_freq", "weight", 512),
    ]

    duration_slots = estimate_stage_duration_slots(
        node=node,
        stage="dma_in",
        candidate=None,
        allocations=allocations,
        capabilities=capabilities,
    )
    reservations = estimate_stage_resource_reservations(
        macro_op="ROPE_TABLE",
        stage="dma_in",
        resource_set=["DMA"],
        duration_slots=duration_slots,
        node=node,
        candidate=None,
        capabilities=capabilities,
    )

    dma_reservation = next(item for item in reservations if item[0] == "DMA")
    vpu_reservation = next(item for item in reservations if item[0] == "VPU")

    assert dma_reservation[1] == 0
    assert dma_reservation[2] < duration_slots
    assert vpu_reservation[1] == dma_reservation[2]
    assert vpu_reservation[1] + vpu_reservation[2] == duration_slots


def _make_vector_node(node_id: str, macro_op: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="bf16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op=macro_op,
        inputs=["in0"],
        outputs=["out0"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=[macro_op],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"in0": "ACTIVATION"},
            output_memory_classes={"out0": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=[f"onnx::{macro_op}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{macro_op}"],
        ),
    )


def _make_attention_mask_prep_node(node_id: str, shape: list[int], original_op_kind: str) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="bf16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ATTENTION_MASK_PREP",
        inputs=["attn.mask.raw"],
        outputs=["attn.mask.ready"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ATTENTION_MASK_PREP"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"attn.mask.raw": "ACTIVATION"},
            output_memory_classes={"attn.mask.ready": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "AttentionMaskPrep",
            "original_op_kind": original_op_kind,
        },
        source_ref=[f"onnx::{original_op_kind}_mask_ready"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{original_op_kind}_mask_ready"],
        ),
    )


def _make_layout_fallback_node(node_id: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="LAYOUT_FALLBACK",
        inputs=["tokens.embed"],
        outputs=["tokens.transposed"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["LAYOUT_FALLBACK"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"tokens.embed": "ACTIVATION"},
            output_memory_classes={"tokens.transposed": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "LayoutFallback",
            "original_op_kind": "Transpose",
        },
        source_ref=["onnx::Transpose_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Transpose_0"],
        ),
    )


def _make_rope_table_node(node_id: str, output_shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="ROPE_TABLE",
        inputs=["position_ids", "rope.inv_freq"],
        outputs=["rope.cos", "rope.sin"],
        shape=output_shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=["ROPE_TABLE"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "position_ids": "METADATA",
                "rope.inv_freq": "WEIGHT",
            },
            output_memory_classes={
                "rope.cos": "ACTIVATION",
                "rope.sin": "ACTIVATION",
            },
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "ROPETable",
            "head_dim": output_shape[-1],
        },
        source_ref=["onnx::Cos_0", "onnx::Sin_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Cos_0", "onnx::Sin_0"],
        ),
    )


def _make_embedding_lookup_node(node_id: str, output_shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op="EMBEDDING_LOOKUP",
        inputs=["model.embed_tokens.weight", "input_ids"],
        outputs=["tokens.embed"],
        shape=output_shape,
        layout="SD",
        memory_class="weight",
        legal_opcodes=["EMBEDDING_LOOKUP"],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=output_shape,
            canonical_layout="SD",
            memory_class="ACTIVATION",
            input_memory_classes={
                "model.embed_tokens.weight": "WEIGHT",
                "input_ids": "METADATA",
            },
            output_memory_classes={"tokens.embed": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={
            "canonical_pattern": "EmbeddingLookup",
            "embedding_dim": output_shape[-1],
            "vocab_size": 262144,
        },
        source_ref=["onnx::Gather_0"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=["onnx::Gather_0"],
        ),
    )


def _make_gemm_like_node(node_id: str, macro_op: str, shape: list[int]) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="int4" if macro_op == "WDQ_GEMM" else "bf16",
        activation_dtype="bf16",
        group_size=128,
        quant_mode="per-group" if macro_op == "WDQ_GEMM" else "none",
        scale_present=macro_op == "WDQ_GEMM",
        zero_point_present=macro_op == "WDQ_GEMM",
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op=macro_op,
        inputs=["in0", "weight"],
        outputs=["out0"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=[macro_op],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"in0": "ACTIVATION", "weight": "WEIGHT"},
            output_memory_classes={"out0": "ACTIVATION"},
            quant=quant,
            attention=None,
        ),
        attrs={},
        source_ref=[f"onnx::{macro_op}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{macro_op}"],
        ),
    )


def _make_sdpa_like_node(
    node_id: str,
    macro_op: str,
    shape: list[int],
    *,
    query_len: int,
    kv_len: int,
) -> object:
    from llm_sched.ir.common import AuditRef
    from llm_sched.ir.nig import AttentionBinding, NIGBinding, NIGNode, QuantBinding

    quant = QuantBinding(
        weight_dtype="none",
        activation_dtype="float16",
        group_size=1,
        quant_mode="none",
        scale_present=False,
        zero_point_present=False,
        k_tile_size=128,
        k_tile_aligned=True,
    )
    return NIGNode(
        node_id=node_id,
        macro_op=macro_op,
        inputs=["q", "k", "v", "mask"],
        outputs=["out0"],
        shape=shape,
        layout="HSD",
        memory_class="activation",
        legal_opcodes=[macro_op],
        quant=quant,
        binding=NIGBinding(
            resolved_shape=shape,
            canonical_layout="HSD",
            memory_class="ACTIVATION",
            input_memory_classes={"q": "ACTIVATION", "k": "ACTIVATION", "v": "ACTIVATION", "mask": "ACTIVATION"},
            output_memory_classes={"out0": "ACTIVATION"},
            quant=quant,
            attention=AttentionBinding(
                mode="decode" if macro_op == "SDPA_DECODE" else "prefill",
                query_len=query_len,
                kv_len=kv_len,
                head_dim=256,
                num_heads=4,
                num_key_value_heads=1,
                tensor_layout="BHSD",
                kv_layout_rule="per-layer-slice-of-LBHSD",
            ),
        ),
        attrs={"query_len": query_len, "kv_len": kv_len, "num_heads": 4, "head_dim": 256},
        source_ref=[f"onnx::{macro_op}"],
        audit_ref=AuditRef(
            graph_node_ids=[node_id.replace("nig.", "graph.", 1)],
            source_ids=[f"onnx::{macro_op}"],
        ),
    )


def _make_tile_candidate(candidate_id: str, node_id: str, macro_op: str) -> object:
    from llm_sched.contracts.tiling_plan import TileCandidate

    return TileCandidate(
        candidate_id=candidate_id,
        node_id=node_id,
        macro_op=macro_op,
        strategy="fixture",
        m_tile=48,
        n_tile=128,
        k_tile=128,
        read_bytes=0,
        write_bytes=0,
        total_vmem_bytes=0,
        rank=1,
        ranking_reason="fixture",
        quant_alignment_ok=True,
        quant_alignment_message="fixture",
        source_memory_plan_region_pressure={},
        resource_summary=None,
        issues=[],
    )


def _make_allocation(allocation_id: str, tensor_role: str, size_bytes: int) -> object:
    from llm_sched.contracts.memory_plan import PlannedAllocation

    return PlannedAllocation(
        allocation_id=allocation_id,
        node_id="fixture",
        tensor_name=allocation_id,
        tensor_role=tensor_role,
        lifetime_bucket="compute",
        backing_store="vmem-local",
        memory_class="ACTIVATION",
        address_space="VMEM",
        region_name="ping",
        size_bytes=size_bytes,
    )
