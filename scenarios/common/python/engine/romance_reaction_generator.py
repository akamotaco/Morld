"""묘사 생성기 — 성격 아키타입 + 3D 좌표(감정×욕구×절정) 기반 (:during 3인칭)

10종 아키타입 × 5 카테고리 × 좌표 포인트 = 풍부한 자동 반응.
네임드 NPC는 캐릭터 오버레이로 일부 좌표 대체 + 나머지 아키타입 텍스트.
모브 NPC는 REACTION_PROFILE만으로 전체 반응 자동 생성.

대사(:start 1인칭)는 romance_line_generator.py 참조.

좌표 공간:
  X축 (sentiment): 호감 - 반발*0.8          (-100 ~ +100)
  Y축 (desire):    (성욕*0.5 + 욕망*0.5) - 순수도*0.5  (-100 ~ +100)
  Z축 (climax):    gauge*0.6 + min(total,4)*10          (0 ~ 100)
"""
import random

from engine.tone_templates import (
    CATEGORY_TEMPLATES, ARCHETYPE_TEMPLATES,
    calc_coordinates, select_by_coord,
)
from engine.tone_templates.coords import ACTION_TO_CATEGORY


# ─────────────────────────────────────────────
# 유틸 — 특수 템플릿/override 호환용
# ─────────────────────────────────────────────

def resolve_arousal_tier(arousal):
    """성욕 → 흥분 단계"""
    if arousal >= 90:
        return "extreme"
    if arousal >= 70:
        return "high"
    if arousal >= 40:
        return "medium"
    return "low"


def resolve_tone(state):
    """좌표 → 4-tone 매핑 (특수 템플릿/override 호환용).

    사분면 기반: X >= 0 + Y >= 0 → romance 등.
    """
    sx, sy, _sz = calc_coordinates(state)
    if sx >= 0:
        return "romance" if sy >= 0 else "platonic"
    return "lust" if sy >= 0 else "rejection"


# ─────────────────────────────────────────────
# ReactionGenerator 클래스
# ─────────────────────────────────────────────

class ReactionGenerator:
    """성격 아키타입 + 3D 좌표 기반 반응 생성기.

    네임드 NPC: char_reactions로 일부 좌표 대체 + 아키타입 텍스트 fallback.
    모브 NPC: REACTION_PROFILE만으로 전체 반응 자동 생성.
    """

    def __init__(self, profile):
        self.profile = profile
        self.name = profile["name"]
        self.archetype = profile.get("archetype", "stoic")
        self._overrides = profile.get("overrides", {})
        self._char_reactions = profile.get("char_reactions", {})

    def generate(self, action_id, timing, state):
        """반응 텍스트 생성 — 3단계 fallback chain.

        1) 캐릭터 override (tone 기반 — 기존 호환)
        2) 행위별 아키타입 템플릿 (좌표 기반 + 캐릭터 오버레이)
        3) 카테고리 fallback (좌표 기반 + 캐릭터 오버레이)
        """
        sx, sy, sz = calc_coordinates(state)
        fmt = self._fmt_vars()

        # 1) 캐릭터 override (tone 기반)
        text = self._try_override(action_id, timing, state, fmt)
        if text:
            return text

        # 2) 행위별 아키타입 템플릿 (좌표 기반)
        key = f"{action_id}:{timing}"
        pool = ARCHETYPE_TEMPLATES.get(key, {}).get(self.archetype, {})
        pool = self._merge_char_pool(pool, action_id)
        text = select_by_coord(pool, sx, sy, sz)
        if text:
            return text.format(**fmt)

        # 3) 카테고리 fallback (좌표 기반)
        category = ACTION_TO_CATEGORY.get(action_id)
        if category:
            pool = CATEGORY_TEMPLATES.get(f"{category}:{timing}", {}).get(
                self.archetype, {})
            pool = self._merge_char_pool(pool, category)
            text = select_by_coord(pool, sx, sy, sz)
            if text:
                return text.format(**fmt)

        return None

    def _merge_char_pool(self, base_pool, key):
        """캐릭터 오버레이 머지 — 같은 좌표는 대체, 나머지는 유지."""
        char_pool = self._char_reactions.get(key, {})
        if not char_pool:
            return base_pool
        merged = dict(base_pool)
        merged.update(char_pool)
        return merged

    def _try_override(self, action_id, timing, state, fmt):
        """캐릭터 override (tone 기반 — REACTION_PROFILE 호환)."""
        key = f"{action_id}:{timing}"
        override = self._overrides.get(key)
        if not override:
            return None

        tone = resolve_tone(state)
        texts = override.get(self.archetype, {}).get(tone)
        if texts:
            return random.choice(texts).format(**fmt)
        return None

    def _fmt_vars(self):
        """포맷 변수 딕트."""
        return {"name": self.name, **self.profile.get("vars", {})}
