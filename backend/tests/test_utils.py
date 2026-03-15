import importlib.util
from pathlib import Path


def load_module(module_name: str, relative_path: str):
    """Load a module directly from a repository-relative path for isolated tests."""
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module
