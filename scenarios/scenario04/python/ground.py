# ground.py — engine.ground shim (S02 패턴과 동일)
#
# 외부 코드 `import ground`가 scenarios/common/python/engine/ground.py를 쓰도록 연결.
# drop 시 바닥 자동 생성 등에서 사용.

import sys
from engine import ground as _engine_module
sys.modules[__name__] = _engine_module
