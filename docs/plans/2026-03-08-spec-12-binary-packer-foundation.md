# SPEC-12 Binary Packer Foundation Implementation Plan

> **For Codex:** Use the existing `SPEC-12` descriptor artifact as the stable symbolic contract, then add a separate packed-descriptor artifact that freezes deterministic 512-bit payload placement without pretending the RTL/driver ABI is final.

**Goal:** Add a first-pass binary-packer foundation for `SPEC-12` so `run-descriptor-generation` emits a deterministic packed descriptor artifact alongside `descriptor_ir.json` and `isa_coverage_report.json`.

**Architecture:** Keep `DescriptorIR` symbolic and traceable. Introduce a standalone packed artifact with `8 x 64-bit words`, `packed_hex`, and field-placement metadata. Reuse the existing `DescriptorPackingProfile` plus target descriptor-encoding config to derive field placement. Do not introduce a final driver binary stream or hardware-specific byte order policy beyond a deterministic internal convention.

**Tech Stack:** Pydantic models, existing descriptor-generation workflow, pytest.

---

### Task 1: Freeze the packed-descriptor artifact contract

**Files:**
- Add: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\packed_descriptor_bundle.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\contracts\__init__.py`
- Test: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\contracts\test_packed_descriptor_bundle.py`

**Intent:**
- add a validation-backed contract for packed descriptors
- require deterministic `word_hex`, `packed_hex`, and non-overlapping field placements
- keep the artifact JSON-friendly so it can be consumed by later tooling and visualization

### Task 2: Add failing tests for packer output and descriptor field-width detail

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_builder.py`
- Add: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\planning\test_descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\unit\pipeline\test_descriptor_generation_workflow.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_cli_run_descriptor_generation.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\tests\smoke\test_phase_c_descriptor_matrix.py`

**Intent:**
- require more granular shape and transfer packing widths
- require a packed bundle with `8` words for every mapped descriptor
- require the run-root workflow and CLI to emit `packed_descriptor_bundle.json`

### Task 3: Implement packer logic and integrate the workflow

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\ir\descriptor_ir.py`
- Add: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_packer.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\descriptor_builder.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\planning\__init__.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\pipeline\descriptor_generation.py`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\src\llm_sched\cli\main.py`

**Intent:**
- refine `DescriptorPackingProfile.field_widths` so the packer has field-level widths, not only coarse group widths
- add a deterministic bit-placement policy over 512 bits
- serialize packed payloads as a separate artifact without changing downstream `DescriptorIR` consumers

### Task 4: Update handoff/status docs and verify closure

**Files:**
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\phase-c-descriptor-handoff.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\evaluation-compiler-roadmap.md`
- Modify: `D:\workspace\llmSched\.worktrees\phb-01-import-report\docs\development\README.md`

**Intent:**
- document that `SPEC-12` now has a deterministic packed payload artifact
- keep the remaining gap framed as “final byte-order / driver ABI hardening” rather than “descriptor payload still missing”
- run focused descriptor tests and full `pytest` before commit
