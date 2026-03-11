"""Planner-facing architecture query helpers."""

from llm_sched.arch.capabilities import ArchitectureCapabilities


class ArchitectureQueryAPI:
    def __init__(self, capabilities: ArchitectureCapabilities) -> None:
        self._capabilities = capabilities

    def supports_mode(self, mode: str) -> bool:
        return self._capabilities.core_mode == mode

    def vmem_region(self, name: str) -> int:
        return self._capabilities.vmem.regions[name]

    def opcode_enabled(self, opcode: str) -> bool:
        return opcode in self._capabilities.opcodes

    def shared_dma_bandwidth(self) -> float:
        return self._capabilities.shared_dma.effective_bandwidth_gbps

    def kv_layout_rule(self) -> str:
        return self._capabilities.kv_cache.layout

    def link_available(self) -> bool:
        return self._capabilities.core_link.enabled
