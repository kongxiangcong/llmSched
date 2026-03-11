# SPEC-08 Storage Binding Surface

## Goal

Close the next `SPEC-08` planner-closure gap by replacing opaque DDR binding strings with a small structured storage/source binding surface that downstream `SPEC-09/12/13` can consume without re-parsing `backing_symbol`.

## Scope

In scope:
- add a formal storage binding contract to `MemoryPlanArtifact`
- make non-local allocations reference a `storage_binding_id`
- emit structured binding records for:
  - staged `WEIGHT`
  - staged `QUANT_PARAM`
  - persistent `KV_CACHE`
- link `address_diagnostics` to the formal binding records
- keep the current symbolic `backing_symbol` for backward-compatible readability

Out of scope:
- target-specific address packing
- binary descriptor encoding
- schedule-aware lifetime analysis
- DDR traffic or cycle modeling

## Contract Shape

Add a new `StorageBindingDescriptor` surface with the minimum fields needed by downstream layers:
- `binding_id`
- `node_id`
- `tensor_name`
- `memory_class`
- `backing_store`
- `source_kind`
- `symbol`
- `binding_scope`
- optional `layout`
- optional `dtype`
- optional `layer_id`
- optional `tensor_kind`

`PlannedAllocation` will gain:
- `storage_binding_id`

`MemoryPlanArtifact` will gain:
- `storage_bindings`

`AddressBindingDiagnostic` will gain:
- `storage_binding_id`

## Implementation Steps

1. Extend the memory-plan contract with `StorageBindingDescriptor` and reference fields.
2. Add focused contract tests for valid payloads and invalid `storage_binding_id` usage.
3. Update the planner to emit structured bindings for weight / quant / KV surfaces.
4. Deduplicate bindings deterministically inside one `MemoryPlanArtifact`.
5. Update workflow and smoke tests to assert the new artifact surface is present.
6. Update handoff and roadmap docs after the tests are green.

## Validation

- `python -m pytest tests/unit/contracts/test_memory_plan_contract.py tests/unit/planning/test_memory_planner.py tests/unit/pipeline/test_memory_planning_workflow.py tests/smoke/test_phase_c_memory_planner_matrix.py -q`
- `python -m pytest -q`
- `git diff --check`

## Expected Outcome

After this batch, `SPEC-08` should expose a formal address-mapping artifact for staged weights, staged quant parameters, and persistent KV storage. Later tiling, descriptor, and performance layers should be able to consume storage/source intent from structured records instead of parsing symbolic strings.
