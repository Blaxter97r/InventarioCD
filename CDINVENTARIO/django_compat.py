"""Compatibilidad para archivos de Django aislados por la protección corporativa."""

from importlib import import_module, util
from pathlib import Path
import sys


def ensure_django_cache_module():
    """Carga el bytecode oficial si django/utils/cache.py fue puesto en cuarentena."""
    module_name = "django.utils.cache"
    try:
        import_module(module_name)
        return
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        original_error = error

    cache_directory = (
        Path(sys.prefix)
        / "Lib"
        / "site-packages"
        / "django"
        / "utils"
        / "__pycache__"
    )
    candidates = sorted(cache_directory.glob("cache.cpython-*.pyc"), reverse=True)
    if not candidates:
        raise original_error

    spec = util.spec_from_file_location(module_name, candidates[0])
    if spec is None or spec.loader is None:
        raise original_error
    module = util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
