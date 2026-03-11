from pydantic import ValidationError


def test_memory_plan_artifact_accepts_valid_payload() -> None:
    from llm_sched.contracts.memory_plan import (
        AddressBindingDiagnostic,
        KVAddressFormula,
        MemoryPlanArtifact,
        PlannedAllocation,
        RegionSummary,
        StorageBindingDescriptor,
        VMEMFitDiagnostic,
    )

    artifact = MemoryPlanArtifact(
        graph_id="gemma3-layer0",
        scenario_name="decode_token1_kv2048",
        core_mode="single-core",
        allocations=[
            PlannedAllocation(
                allocation_id="alloc.act.0",
                node_id="nig.node.0",
                tensor_name="act",
                tensor_role="input",
                lifetime_bucket="preload",
                backing_store="vmem-local",
                backing_symbol=None,
                memory_class="ACTIVATION",
                address_space="VMEM",
                region_name="ping",
                offset_bytes=0,
                size_bytes=256,
                alignment_bytes=64,
            ),
            PlannedAllocation(
                allocation_id="alloc.weight.0",
                node_id="nig.node.0",
                tensor_name="proj.weight",
                tensor_role="weight",
                lifetime_bucket="preload",
                backing_store="ddr-backed-staged",
                backing_symbol="WEIGHT_BASE::proj_weight",
                storage_binding_id="storage.weight.nig.node.0.proj_weight",
                memory_class="WEIGHT",
                address_space="VMEM",
                region_name="weight",
                offset_bytes=0,
                size_bytes=1024,
                alignment_bytes=64,
            ),
        ],
        storage_bindings=[
            StorageBindingDescriptor(
                binding_id="storage.weight.nig.node.0.proj_weight",
                node_id="nig.node.0",
                tensor_name="proj.weight",
                memory_class="WEIGHT",
                backing_store="ddr-backed-staged",
                source_kind="weight_tensor",
                symbol="WEIGHT_BASE::proj_weight",
                binding_scope="per-tensor-base",
                dtype="int4",
            ),
            StorageBindingDescriptor(
                binding_id="storage.kv.nig.kvload.0.key",
                node_id="nig.kvload.0",
                tensor_name="past_key",
                memory_class="KV_CACHE",
                backing_store="ddr-persistent",
                source_kind="kv_cache_slice",
                symbol="KV_BASE",
                binding_scope="per-layer-slice",
                layout="LBHSD",
                dtype="bf16",
                layer_id=0,
                tensor_kind="key",
            ),
        ],
        region_summaries={
            "ping": RegionSummary(
                region_name="ping",
                capacity_bytes=30 * 1024,
                peak_bytes=256,
                peak_lifetime_bucket="preload",
                peak_bytes_by_lifetime_bucket={"preload": 256, "compute": 0, "store": 0, "persist": 0},
                peak_bytes_by_memory_class={
                    "ACTIVATION": 256,
                    "WEIGHT": 0,
                    "KV_CACHE": 0,
                    "QUANT_PARAM": 0,
                    "METADATA": 0,
                },
                peak_bytes_by_backing_store={
                    "vmem-local": 256,
                    "ddr-backed-staged": 0,
                    "ddr-persistent": 0,
                },
                fits=True,
                allocation_ids=["alloc.act.0"],
            )
        },
        kv_formulas=[
            KVAddressFormula(
                node_id="nig.kvload.0",
                tensor_kind="key",
                layer_id=0,
                layout="LBHSD",
                base_symbol="KV_BASE",
                layer_stride_bytes=2_097_152,
                kv_kind_stride_bytes=1_048_576,
                token_stride_bytes=512,
                head_stride_bytes=512,
                dim_stride_bytes=2,
                formula="KV_BASE + layer_id * KV_LAYER_STRIDE + token * KV_TOKEN_STRIDE",
            )
        ],
        diagnostics=[
            VMEMFitDiagnostic(
                diagnostic_id="diag.quant.0",
                region_name="quant",
                status="fit",
                required_bytes=512,
                required_bytes_by_memory_class={
                    "ACTIVATION": 0,
                    "WEIGHT": 0,
                    "KV_CACHE": 0,
                    "QUANT_PARAM": 512,
                    "METADATA": 0,
                },
                required_bytes_by_backing_store={
                    "vmem-local": 0,
                    "ddr-backed-staged": 512,
                    "ddr-persistent": 0,
                },
                capacity_bytes=4096,
                offending_node_ids=[],
                message="quant region fits current staging requirement",
            )
        ],
        address_diagnostics=[
            AddressBindingDiagnostic(
                diagnostic_id="addr.kv.0",
                node_id="nig.kvload.0",
                address_kind="kv",
                status="bound",
                storage_binding_id="storage.kv.nig.kvload.0.key",
                symbol="KV_LAYER_STRIDE",
                message="kv address formula resolved with concrete layer_id",
            )
        ],
    )

    assert artifact.allocations[0].region_name == "ping"
    assert artifact.allocations[0].lifetime_bucket == "preload"
    assert artifact.allocations[0].backing_store == "vmem-local"
    assert artifact.kv_formulas[0].token_stride_bytes == 512
    assert artifact.region_summaries["ping"].peak_bytes == 256
    assert artifact.region_summaries["ping"].peak_lifetime_bucket == "preload"
    assert artifact.region_summaries["ping"].peak_bytes_by_memory_class["ACTIVATION"] == 256
    assert artifact.region_summaries["ping"].peak_bytes_by_backing_store["vmem-local"] == 256
    assert artifact.diagnostics[0].required_bytes_by_memory_class["QUANT_PARAM"] == 512
    assert artifact.allocations[1].storage_binding_id == "storage.weight.nig.node.0.proj_weight"
    assert artifact.storage_bindings[0].source_kind == "weight_tensor"
    assert artifact.address_diagnostics[0].status == "bound"
    assert artifact.address_diagnostics[0].storage_binding_id == "storage.kv.nig.kvload.0.key"


def test_region_summary_rejects_negative_peak_bytes() -> None:
    from llm_sched.contracts.memory_plan import RegionSummary

    try:
        RegionSummary(
            region_name="ping",
            capacity_bytes=30 * 1024,
            peak_bytes=-1,
            fits=False,
        )
    except ValidationError:
        return

    raise AssertionError("expected RegionSummary to reject negative peak_bytes")


def test_kv_formula_requires_positive_strides() -> None:
    from llm_sched.contracts.memory_plan import KVAddressFormula

    try:
        KVAddressFormula(
            node_id="nig.kvload.0",
            tensor_kind="value",
            layer_id=3,
            layout="LBHSD",
            base_symbol="KV_BASE",
            layer_stride_bytes=0,
            kv_kind_stride_bytes=1,
            token_stride_bytes=1,
            head_stride_bytes=1,
            dim_stride_bytes=2,
            formula="bad",
        )
    except ValidationError:
        return

    raise AssertionError("expected KVAddressFormula to reject non-positive layer_stride_bytes")


def test_planned_allocation_rejects_storage_binding_for_vmem_local() -> None:
    from llm_sched.contracts.memory_plan import PlannedAllocation

    try:
        PlannedAllocation(
            allocation_id="alloc.local.0",
            node_id="nig.node.0",
            tensor_name="act",
            tensor_role="input",
            lifetime_bucket="preload",
            backing_store="vmem-local",
            backing_symbol=None,
            storage_binding_id="storage.local.0",
            memory_class="ACTIVATION",
            address_space="VMEM",
            region_name="ping",
            offset_bytes=0,
            size_bytes=256,
            alignment_bytes=64,
        )
    except ValidationError:
        return

    raise AssertionError("expected PlannedAllocation to reject storage_binding_id for vmem-local allocation")


def test_memory_plan_artifact_rejects_unknown_storage_binding_reference() -> None:
    from llm_sched.contracts.memory_plan import MemoryPlanArtifact, PlannedAllocation

    try:
        MemoryPlanArtifact(
            graph_id="graph",
            scenario_name="decode",
            core_mode="single-core",
            allocations=[
                PlannedAllocation(
                    allocation_id="alloc.weight.0",
                    node_id="nig.node.0",
                    tensor_name="proj.weight",
                    tensor_role="weight",
                    lifetime_bucket="preload",
                    backing_store="ddr-backed-staged",
                    backing_symbol="WEIGHT_BASE::proj_weight",
                    storage_binding_id="storage.weight.missing",
                    memory_class="WEIGHT",
                    address_space="VMEM",
                    region_name="weight",
                    offset_bytes=0,
                    size_bytes=1024,
                    alignment_bytes=64,
                )
            ],
        )
    except ValidationError:
        return

    raise AssertionError("expected MemoryPlanArtifact to reject missing storage binding references")
