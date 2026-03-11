import importlib
import importlib.util


def test_frontend_package_exports_entrypoints() -> None:
    spec = importlib.util.find_spec("llm_sched.frontend")
    assert spec is not None

    frontend = importlib.import_module("llm_sched.frontend")

    assert callable(frontend.import_onnx_to_graph_ir)
    assert callable(frontend.canonicalize_graph_ir)
