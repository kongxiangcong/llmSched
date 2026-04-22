"""Frontend entrypoints for model import and graph canonicalization."""

from llm_sched.frontend.binding import bind_nig_ir
from llm_sched.frontend.canonicalize import canonicalize_graph_ir
from llm_sched.frontend.legality import (
    FrontendLegalityError,
    FrontendLegalityIssue,
    collect_frontend_legality_issues,
    validate_frontend_legality,
)
from llm_sched.frontend.model_metadata import GemmaModelMetadata, load_gemma_model_metadata
from llm_sched.frontend.nig_lowering import GraphToNIGLoweringError, lower_graph_ir_to_nig
from llm_sched.frontend.onnx_importer import import_onnx_to_graph_ir
from llm_sched.frontend.task_dag_builder import TaskDAGBuildError, build_task_dag
from llm_sched.frontend.shape_binding import FrontendShapeBinding, build_gemma3_shape_bindings

__all__ = [
    "FrontendLegalityError",
    "FrontendLegalityIssue",
    "FrontendShapeBinding",
    "GemmaModelMetadata",
    "GraphToNIGLoweringError",
    "TaskDAGBuildError",
    "bind_nig_ir",
    "build_gemma3_shape_bindings",
    "build_task_dag",
    "canonicalize_graph_ir",
    "collect_frontend_legality_issues",
    "import_onnx_to_graph_ir",
    "load_gemma_model_metadata",
    "lower_graph_ir_to_nig",
    "validate_frontend_legality",
]
