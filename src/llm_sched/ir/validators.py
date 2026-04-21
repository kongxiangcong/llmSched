"""IR validation entrypoints."""

from llm_sched.ir.graph_ir import GraphIR
from llm_sched.ir.nig import NIGIR
from llm_sched.ir.schedule_ir import ScheduleIR


def validate_graph_ir(payload: dict) -> GraphIR:
    return GraphIR.model_validate(payload)


def validate_nig_ir(payload: dict) -> NIGIR:
    return NIGIR.model_validate(payload)


def validate_schedule_ir(payload: dict) -> ScheduleIR:
    return ScheduleIR.model_validate(payload)
