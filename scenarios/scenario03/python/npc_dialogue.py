# npc_dialogue.py — Hybrid 대화 어댑터 (시나리오03)
#
# 규약 (docs/dialogue-hybrid.md):
#   - 핵심 대사(브리핑/계약/보고 등 서사 고정 지점)는 이벤트 코드의 고정 문자열 유지
#   - 주변 대사(전투 외침, 탐사 중얼거림, 인사)는 hybrid 엔진 동적 생성
#
# 분대원: 역할별 아키타입 공용 풀만 사용 (캐릭터 yaml 없음 → 순수 dynamic)
# 비서:   cold 아키타입 + characters/비서.yaml override (안드로이드/시스템 톤)
#
# state 매핑 (props → hybrid 상태축):
#   fatigue    = 1 - 체력/체력max      (부상이 클수록 지친 톤)
#   confidence = (vita - 5) / 5        (성장할수록 자신감)
#   affinity   = (인간성 - 50) / 50    (인간성이 마모되면 차가운 톤)

import morld

from engine.dialogue_hybrid import stateless as _st


# 역할 prop("역할") → 아키타입
ROLE_ARCHETYPES = {
    "돌격": "fierce",
    "화력 지원": "cheerful",
    "저격": "stoic",
    "의무병": "gentle",
}
DEFAULT_ARCHETYPE = "stoic"

SECRETARY_ARCHETYPE = "cold"
SECRETARY_CHARACTER = "비서"


def _clamp(v, lo=-1.0, hi=1.0):
    return max(lo, min(hi, v))


def member_archetype(unit_id):
    """분대원의 역할 prop 기반 아키타입"""
    role = morld.get_unit_prop(unit_id, "역할")
    return ROLE_ARCHETYPES.get(role, DEFAULT_ARCHETYPE)


def member_state(unit_id):
    """분대원 props → hybrid state dict"""
    hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
    hp_max = morld.get_unit_prop(unit_id, "생존:체력max") or 60
    vita = morld.get_unit_prop(unit_id, "vita") or 5
    humanity = morld.get_unit_prop(unit_id, "인간성")
    state = {
        "fatigue": _clamp(1.0 - hp / max(hp_max, 1), 0.0, 1.0),
        "confidence": _clamp((vita - 5) / 5.0),
    }
    if humanity:  # 0 = 미추적 (prop 계약)
        state["affinity"] = _clamp((humanity - 50) / 50.0)
    return state


def _member_name(unit_id):
    info = morld.get_unit_info(unit_id)
    if info:
        return info.get("name", f"Unit-{unit_id}")
    return f"Unit-{unit_id}"


# ==================== 분대원 대사 ====================

def member_combat_line(unit_id, intent, rng=None):
    """전투 발화. intent: combat_engage/hit/victory/defeat/taunt/ally_down 등.

    Returns: "「Echo-01」 대사" 형식 문자열, 생성 실패 시 "" (호출측에서 무시)
    """
    name = _member_name(unit_id)
    line = _st.generate_combat_line(
        member_archetype(unit_id), name, intent,
        state=member_state(unit_id), rng=rng)
    return f"{name}: 「{line}」" if line else ""


def member_dungeon_line(unit_id, intent, rng=None, extra_context=None):
    """탐사 발화. intent: dungeon_ambient/floor_descent/ally_corrosion_concern 등"""
    name = _member_name(unit_id)
    line = _st.generate_dungeon_line(
        member_archetype(unit_id), name, intent,
        state=member_state(unit_id), rng=rng, extra_context=extra_context)
    return f"{name}: 「{line}」" if line else ""


def member_party_line(unit_id, intent, rng=None):
    """파티/편성 발화. intent: invite_accept/vote_advance/vote_return 등"""
    name = _member_name(unit_id)
    line = _st.generate_party_line(
        member_archetype(unit_id), name, intent,
        state=member_state(unit_id), rng=rng)
    return f"{name}: 「{line}」" if line else ""


def member_daily_line(unit_id, intent, rng=None):
    """일상 발화. intent: greet/thank/complain 등 (보급 도착 인사 등)"""
    name = _member_name(unit_id)
    line = _st.generate_daily_line(
        member_archetype(unit_id), name, intent,
        state=member_state(unit_id), rng=rng)
    return f"{name}: 「{line}」" if line else ""


# ==================== 비서 대사 ====================

def secretary_line(intent, state=None, rng=None):
    """비서 주변 대사 (daily 풀 + 비서.yaml 시스템 톤 override).

    intent: greet/thank/complain
    state: 미지정 시 중립. 예: {"fatigue": 0.7} → 저전력/과부하 톤 유도
    """
    line = _st.generate_daily_line(
        SECRETARY_ARCHETYPE, SECRETARY_CHARACTER, intent,
        state=state, rng=rng)
    return line or ""


def clear_cache():
    """테스트/챕터 재로드용 — hybrid 데이터 캐시 비움"""
    _st.clear_cache()
