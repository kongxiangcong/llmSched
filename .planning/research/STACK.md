# Technology Stack

**Project:** llmSched v2 — v0.10 Descriptor Compiler
**Researched:** 2026-04-21
**Confidence:** HIGH

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Runtime | Project constraint; match-case syntax (3.10+) for family dispatch, `type` alias statement (3.12+) for clean type aliases, `graphlib` (3.9+) for topological sorting |
| Pydantic | 2.12+ (recommend 2.13) | Schema validation & semantic models | Hardware schemas need constrained integers (`Field(ge=, le=)`), discriminated unions for family dispatch (`Annotated[Union[...], Field(discriminator=...)]`), strict mode (`ConfigDict(strict=True)`) to reject accidental type coercion, `model_validator` for reserved-bit checks, `computed_field` for derived values |
| Typer | 0.24 | CLI interface | Already in project; zero-friction CLI with typed arguments, enum options for verify levels, integrates with Pydantic models |
| ONNX | 1.21 | Model import | Already in project; `onnx.load()`, `graph.node` iteration, `node.op_type` filtering, `graph.initializer` for weights, `value_info` for shapes |

### Bitfield & Binary Manipulation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `struct` (stdlib) | built-in | Word serialization | `struct.pack('>Q', word)` for big-endian 64-bit serialization; no dependency needed |
| `binascii` (stdlib) | built-in | CRC-16/CCITT-FALSE | `binascii.crc_hqx(data, 0xFFFF)` produces exactly CRC-16/CCITT-FALSE (polynomial 0x1021, init 0xFFFF, no reflection); verified against check value 0x29B1 |
| Python `int` (stdlib) | built-in | Bitfield packing | Arbitrary precision integers handle 64-bit, 128-bit, and 256-bit records natively; bit ops (`<<`, `>>`, `&`, `\|`) are the most readable and performant approach |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0+ | Schema file loading | Load `docs/descriptor/*.yaml` at import time; `yaml.safe_load()` is sufficient |
| `functools.lru_cache` (stdlib) | built-in | Schema caching | Cache loaded YAML schemas to avoid repeated file I/O |
| `graphlib.TopologicalSorter` (stdlib) | built-in | Task DAG scheduling | Native topological sort for task dependency resolution; no networkx dependency needed |
| `dataclasses` (stdlib) | built-in | Internal structs | Frozen dataclasses for bitfield definitions, buffer contexts, loop slots; lighter than Pydantic for internal non-validated structures |
| `enum.IntEnum` (stdlib) | built-in | Task type IDs | Type-safe task_type_id values with integer comparison support |
| pytest | 9.0+ | Testing | Already in project; parameterized tests for all 11 families, fixtures for schema loading |

## What NOT to Use and Why

| Technology | Why Avoid | What to Use Instead |
|------------|-----------|---------------------|
| `construct` / `bitstruct` / `bitarray` | New dependencies; project constraint says "no new major dependencies" | Plain Python `int` bit operations — more readable, zero dependency, verified sufficient for 64/128/256-bit records |
| `numpy` for bit manipulation | Overkill for descriptor packing; adds heavy dependency; endianness gotchas with `view()` | Python `int` + `to_bytes()`/`from_bytes()` |
| `marshmallow` / `cattrs` / `msgspec` | Redundant with Pydantic v2 already in project | Pydantic v2 `BaseModel` with `ConfigDict(strict=True, frozen=True)` |
| Custom CRC implementation | `binascii.crc_hqx` already produces the exact CRC-16/CCITT-FALSE spec | `binascii.crc_hqx(data, 0xFFFF)` — verified against 0x29B1 check value |
| `ctypes` bitfields | Unreliable packing order across platforms; poor DX | Explicit bit-shift packing with documented field positions |
| `hypothesis` (property-based testing) | Not installed; not needed for deterministic hardware schemas | pytest parameterized tests with exhaustive boundary values per field width |

## Architecture Patterns Verified

### Bitfield Packing

```python
def pack_word(fields: list[tuple[int, int, int]]) -> int:
    """Pack (value, high_bit, low_bit) into a 64-bit word."""
    word = 0
    for value, high, low in fields:
        width = high - low + 1
        mask = (1 << width) - 1
        word |= (value & mask) << low
    return word
```

Verified: produces correct big-endian word layout matching v0.10 spec.

### Multi-Word Record Packing (FAMILY 128/192 bits)

```python
@dataclass(frozen=True)
class FieldDef:
    name: str
    word_index: int   # which word in the record
    bit_high: int     # high bit within that word
    bit_low: int      # low bit within that word
    width: int
```

Verified: FAMILY word 0-1 packs `0x123456789ABC1122` correctly with fields at expected positions.

### CRC-16/CCITT-FALSE

```python
import binascii

def crc16_ccitt_false(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)
```

Verified: check value `0x29B1` for test string `b'123456789'`.

### Pydantic v2 Discriminated Union for Family Dispatch

```python
FamilyRecord = Annotated[
    Union[GemmFamily, RmsnormFamily, SdpaFamily, ...],
    Field(discriminator='family_type')
]
```

Verified: `family_type: Literal['gemm']` field correctly routes validation.

### Schema-Driven Code Generation

YAML schema files (`family_lut.yaml`, `field_tables.yaml`, `layout.yaml`) can drive:
1. Bitfield metadata generation at import time
2. Reserved-region validation tables
3. Family word-count lookup tables
4. Per-family semantic-to-wire mapping tables

## Installation

```bash
# Core (already in pyproject.toml)
pip install "pydantic>=2.12,<3" "typer>=0.24,<0.25" "onnx>=1.20,<2"

# Dev (already in pyproject.toml)
pip install "pytest>=9,<10"

# No additional dependencies needed for bitfield/CRC functionality
```

## Version Notes

| Package | Installed | Latest | Recommendation |
|---------|-----------|--------|----------------|
| Python | 3.12.3 | 3.12.x | Keep 3.12+; 3.13+ compatible but not required |
| Pydantic | 2.12.5 | 2.13.3 | Upgrade to 2.13 for latest bug fixes; no API changes affect this project |
| Typer | 0.24.1 | 0.24.1 | Current |
| ONNX | not installed | 1.21.0 | Install 1.20+ as specified in pyproject.toml |
| pytest | 9.0.3 | 9.0.3 | Current |

## Sources

- Pydantic v2 docs (verified via WebFetch): strict mode, discriminated unions, `ConfigDict`
- PyPI (verified via WebFetch): ONNX 1.21.0, Typer 0.24.1, pytest 9.0.3
- `binascii.crc_hqx` verified against CRC-16/CCITT-FALSE check value 0x29B1 via live test
- All packing patterns verified via live Python execution against v0.10 schema files
- Descriptor schema files: `docs/descriptor/layout.yaml`, `family_lut.yaml`, `field_tables.yaml`
