import sys
from engine import region_registry as _engine_module
sys.modules[__name__] = _engine_module
