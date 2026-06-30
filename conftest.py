import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent
for p in (_ROOT, _ROOT / "backend"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
