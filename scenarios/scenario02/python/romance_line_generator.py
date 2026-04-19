# romance_line_generator — S02 → Hybrid 어댑터 리다이렉트
#
# Layer 2 fallback 경로. ROMANCE_REACTIONS dict (Layer 1) 이 미스했을 때만 호출됨.
# 실제 구현은 engine/dialogue_hybrid/s02_adapter.LineGenerator (stateless).

import sys
from engine.dialogue_hybrid import s02_adapter as _engine_module

sys.modules[__name__] = _engine_module
