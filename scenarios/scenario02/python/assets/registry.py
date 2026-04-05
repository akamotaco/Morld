import sys
from engine import asset_registry as _engine_module
sys.modules[__name__] = _engine_module
