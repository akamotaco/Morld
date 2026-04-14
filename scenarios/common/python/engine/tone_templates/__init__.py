"""tone_templates — 아키타입별 좌표 기반 텍스트풀 집계

각 아키타입 모듈은 4개 dict를 export:
  REACTIONS       — 카테고리별 :during (3인칭 묘사)
  ACTION_REACTIONS — 행위별 :during 오버라이드
  LINES           — 카테고리별 :start (1인칭 대사)
  ACTION_LINES    — 행위별 :start 오버라이드

이 모듈이 집계하여 generator가 사용하는 4개 dict 빌드:
  CATEGORY_TEMPLATES   "light:during" → {"stoic": {(x,y):[texts]}, ...}
  ARCHETYPE_TEMPLATES  "hug:during"   → {"stoic": {(x,y):[texts]}, ...}
  LINE_TEMPLATES       "light:start"  → {"stoic": {(x,y):[texts]}, ...}
  ACTION_LINE_TEMPLATES "hug:start"   → {"stoic": {(x,y):[texts]}, ...}
"""

from .coords import COORD_TONES, calc_coordinates, select_by_coord, ACTION_TO_CATEGORY
from . import stoic, gentle, cheerful, timid, cold
from . import seductive, fierce, proud, innocent, devoted

_ALL = {
    "stoic": stoic, "gentle": gentle, "cheerful": cheerful,
    "timid": timid, "cold": cold, "seductive": seductive,
    "fierce": fierce, "proud": proud, "innocent": innocent,
    "devoted": devoted,
}

CATEGORY_TEMPLATES = {}      # "light:during" → {"stoic": {(x,y):[texts]}, ...}
ARCHETYPE_TEMPLATES = {}     # "hug:during"   → {"stoic": {(x,y):[texts]}, ...}
LINE_TEMPLATES = {}          # "light:start"  → {"stoic": {(x,y):[texts]}, ...}
ACTION_LINE_TEMPLATES = {}   # "hug:start"    → {"stoic": {(x,y):[texts]}, ...}

for _name, _mod in _ALL.items():
    for _cat, _pool in _mod.REACTIONS.items():
        CATEGORY_TEMPLATES.setdefault(f"{_cat}:during", {})[_name] = _pool
    for _act, _pool in _mod.ACTION_REACTIONS.items():
        ARCHETYPE_TEMPLATES.setdefault(f"{_act}:during", {})[_name] = _pool
    for _cat, _pool in _mod.LINES.items():
        LINE_TEMPLATES.setdefault(f"{_cat}:start", {})[_name] = _pool
    for _act, _pool in _mod.ACTION_LINES.items():
        ACTION_LINE_TEMPLATES.setdefault(f"{_act}:start", {})[_name] = _pool
