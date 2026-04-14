# romance_reaction_generator — S02 → engine 리다이렉트 래퍼
#
# 실제 구현은 engine/romance_reaction_generator. S02와 S04가 공유.

import sys
from engine import romance_reaction_generator as _engine_module

sys.modules[__name__] = _engine_module
