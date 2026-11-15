"""Compatibility entrypoint for the tools bundled in the Explain skill."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/explain/scripts'))
import explain_doctor as _implementation
from explain_doctor import *

if __name__ == '__main__':
    sys.exit(main())
else:
    sys.modules[__name__] = _implementation
