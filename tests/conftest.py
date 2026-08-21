"""Load bump-version/bump.py by path.

The repo is a collection of actions rather than an installable package, so the
script is imported directly from its action directory.
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

BUMP_SCRIPT = Path(__file__).parents[1] / "bump-version" / "bump.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bump", BUMP_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bump = _load()
