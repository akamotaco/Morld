# tone_templates — S02 → engine 리다이렉트 래퍼
#
# 실제 구현은 engine/tone_templates. S02와 S04가 공유.
# `from tone_templates import X` 경로로 import 시 engine 모듈을 반환.

import sys
from engine import tone_templates as _engine_module

sys.modules[__name__] = _engine_module
