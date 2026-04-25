# npc_dialogue.py — S04 생성형 NPC(Tier-3) 상황별 대사 풀
#
# 아키타입 × 상황 → 라인 목록. get_line()으로 랜덤 1개 선택.
# 고정 NPC는 자체 Character 서브클래스에서 override 가능.
#
# Phase 1 범위 (2026-04-14):
#   - greeting, invite_accept/decline/full, dismiss_leave, dungeon_ambient
#   - vote_advance / vote_return (다수결 선호 표현)
#
# Phase 2 (성인 모드 시): romance_line_generator.py의 S02 tone_templates로 확장.

import random

import morld
from engine import persona as _persona
from engine.dialogue_hybrid import stateless as _hybrid


# ========================================
# Hybrid 라우팅 — situation → (context, intent)
# ========================================
# Phase B-2/B-3 (2026-04-26): _LINES 단순 random.choice 대신 묶음 단위 hybrid 호출.
# - 호출 archetype에 해당 묶음 yaml이 없으면 hybrid가 빈 문자열 반환 → _LINES fallback
# - daily: greet 등 인삿말
# - party: 모집/이탈/투표 (invite_*/dismiss_leave/vote_*)
# - dungeon: 던전 환경 발화 (dungeon_ambient)
_SITUATION_TO_HYBRID = {
    "greeting": ("daily", "greet"),
    "first_meet": ("daily", "first_meet"),
    "invite_accept": ("party", "invite_accept"),
    "invite_decline": ("party", "invite_decline"),
    "invite_switch": ("party", "invite_switch"),
    "invite_loyalty_decline": ("party", "invite_loyalty_decline"),
    "invite_full": ("party", "invite_full"),
    "dismiss_leave": ("party", "dismiss_leave"),
    "vote_advance": ("party", "vote_advance"),
    "vote_return": ("party", "vote_return"),
    "dungeon_ambient": ("dungeon", "dungeon_ambient"),
    "corrosion_rise": ("dungeon", "corrosion_rise"),
    "corrosion_critical": ("dungeon", "corrosion_critical"),
    "floor_descent": ("dungeon", "floor_descent"),
    "combat_discover": ("combat", "combat_discover"),
    "combat_engage": ("combat", "combat_engage"),
    "combat_hit": ("combat", "combat_hit"),
    "combat_critical": ("combat", "combat_critical"),
    "combat_victory": ("combat", "combat_victory"),
    "combat_defeat": ("combat", "combat_defeat"),
    "combat_taunt": ("combat", "combat_taunt"),
    "combat_ally_down": ("combat", "combat_ally_down"),
    "room_pref_battle": ("party", "room_pref_battle"),
    "room_pref_rest": ("party", "room_pref_rest"),
    "room_pref_exit": ("party", "room_pref_exit"),
}


# ========================================
# 대사 풀 (아키타입 → 상황 → 라인 리스트)
# ========================================
# 라인은 "{name}" 등 format 키 지원 — get_line(context=…)로 주입.

_LINES = {
    # Phase B-2/B-3 마이그레이트 (2026-04-26): 모든 archetype daily/party/dungeon/combat 묶음 hybrid 이관.
    # 후속(2026-04-26): fierce/innocent/devoted/seductive/gentle daily.yaml 추가 — _LINES 비움.
    # 신규 archetype 도입 시 hybrid yaml 우선, 부득이한 경우만 여기 추가.
}


# 폴백 (아키타입 풀이 없거나 상황 키 없을 때)
_FALLBACK = {
    "greeting":                ["...",],
    "invite_accept":           ["...알겠어. 함께 가지.",],
    "invite_decline":          ["...미안, 같이 가고 싶지 않아.",],
    "invite_switch":           ["...알겠어. 옮기지.",],
    "invite_loyalty_decline":  ["...지금 파티를 떠날 수 없어.",],
    "invite_full":             ["미안해. 내가 들어갈 자리는 없는 것 같네.",],
    "dismiss_leave":           ["...알겠어. 각자의 길을 가자.",],
    "dungeon_ambient":         ["...",],
    "vote_advance":            ["계속 가자.",],
    "vote_return":             ["돌아가자.",],
    "room_pref_battle":        ["싸우자.", "한판 해보자.", "여긴 전투가 낫겠어."],
    "room_pref_rest":          ["잠시 쉬자.", "피곤해... 쉬어가자.", "회복부터 하자."],
    "room_pref_exit":          ["이제 돌아가자.", "충분하다. 마을로.", "오늘은 여기까지."],
}


# ========================================
# API
# ========================================

def get_line(unit_id, situation, **context) -> str:
    """유닛의 아키타입으로 상황 대사 1개 선택.

    Phase B-2 (2026-04-26): situation이 _SITUATION_TO_HYBRID에 매핑돼 있으면
    hybrid 풀(archetype_dialogues/{arch}/{ctx}.yaml) 우선 시도. 빈 결과면 _LINES fallback.

    Args:
        unit_id: 대상 NPC
        situation: 상황 키 (greeting / invite_accept / ...)
        context: format 플레이스홀더 주입 (예: name="세라")

    Returns:
        포맷 적용된 한 줄. 실패 시 "..."
    """
    archetype = _persona.get_archetype(unit_id)

    line = ""
    hybrid_route = _SITUATION_TO_HYBRID.get(situation)
    if hybrid_route:
        ctx_name, intent = hybrid_route
        char_name = morld.get_unit_name(unit_id) or "anon"
        # context 중 name 외 placeholder는 dungeon ally_corrosion_concern 등에서 사용
        extra = {k: v for k, v in context.items() if k != "name"}
        if ctx_name == "daily":
            line = _hybrid.generate_daily_line(archetype, char_name, intent, state=None)
        elif ctx_name == "party":
            line = _hybrid.generate_party_line(archetype, char_name, intent, state=None)
        elif ctx_name == "dungeon":
            line = _hybrid.generate_dungeon_line(archetype, char_name, intent, state=None,
                                                  extra_context=extra or None)
        elif ctx_name == "combat":
            line = _hybrid.generate_combat_line(archetype, char_name, intent, state=None)

    if not line:
        pool = _LINES.get(archetype, {})
        lines = pool.get(situation)
        if not lines:
            lines = _FALLBACK.get(situation, ["..."])
        line = random.choice(lines)

    if context:
        try:
            line = line.format(**context)
        except (KeyError, IndexError):
            pass
    return line


def get_preference(unit_id, context=None) -> str:
    """다수결 선호 1차 결정 — 'advance' 또는 'return'.

    Phase 1: 아키타입별 성향 기반 가중 랜덤.
      - cheerful/fierce/cold/devoted: advance 쪽으로 기움
      - timid/innocent: return 쪽으로 기움
      - stoic: 중립
    Phase 2(인텐션 시스템 이후): 현재 상태(HP/침식/관계)로 정교화 예정.
    """
    archetype = _persona.get_archetype(unit_id)
    advance_weight = {
        "fierce":    0.80,
        "cheerful":  0.65,
        "cold":      0.60,
        "devoted":   0.55,
        "stoic":     0.50,
        "innocent":  0.40,
        "timid":     0.25,
        "gentle":    0.45,
        "seductive": 0.50,
        "proud":     0.60,
    }.get(archetype, 0.50)

    return "advance" if random.random() < advance_weight else "return"
