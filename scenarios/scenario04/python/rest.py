# rest.py - S04 휴식 시스템
#
# 짧은 휴식: 중간 크기 Location, HP 일부 + 침식 소폭 감소
# 긴 휴식: 넓은 Location만, HP 전부 + 침식 대폭 감소 + 자동 세이브
# 공간 제약: location length 기반
#
# 휴식 중 이벤트: 기벽 발현, 수거반 습격, 파티원 대화, 도주 등

import morld
import random

# === 상수 ===

# Location length 기준
LENGTH_SHORT_REST = 200   # 짧은 휴식 최소 length
LENGTH_LONG_REST = 400    # 긴 휴식 최소 length

# 회복량
SHORT_REST_HP_RATIO = 0.3       # 최대 HP의 30%
SHORT_REST_EROSION_REDUCE = 5   # 침식 -5
SHORT_REST_HOURS = 2            # 2시간 소비

LONG_REST_HP_RATIO = 1.0        # HP 전량 회복
LONG_REST_EROSION_REDUCE = 30   # 침식 -30
LONG_REST_HOURS = 8             # 8시간 소비


def can_short_rest(region_id: int, location_id: int) -> bool:
    """짧은 휴식 가능?"""
    loc_info = morld.get_location_info(region_id, location_id)
    if not loc_info:
        return False
    return loc_info.get("length", 0) >= LENGTH_SHORT_REST


def can_long_rest(region_id: int, location_id: int) -> bool:
    """긴 휴식 가능?"""
    loc_info = morld.get_location_info(region_id, location_id)
    if not loc_info:
        return False
    return loc_info.get("length", 0) >= LENGTH_LONG_REST


def short_rest() -> dict:
    """
    짧은 휴식 실행.

    Returns:
        {"success": bool, "events": [str], "message": str}
    """
    player_id = morld.get_player_id()
    if not player_id:
        return {"success": False, "events": [], "message": "플레이어 없음"}

    loc = morld.get_unit_location(player_id)
    if not loc:
        return {"success": False, "events": [], "message": "위치 불명"}

    region_id, loc_id = loc
    if not can_short_rest(region_id, loc_id):
        return {"success": False, "events": [], "message": "이 장소는 너무 좁아 쉴 수 없다."}

    events = []

    # HP 회복 + 침식 감소 (파티 전원)
    import party, survival, erosion

    for mid in party.get_members():
        max_hp = morld.get_unit_prop(mid, "생존:최대체력") or 100
        heal = int(max_hp * SHORT_REST_HP_RATIO)
        current_hp = survival.get_health(mid)
        survival.set_health(mid, min(max_hp, current_hp + heal))
        erosion.reduce_erosion(mid, SHORT_REST_EROSION_REDUCE)

    events.append(f"파티가 {SHORT_REST_HOURS}시간 동안 짧은 휴식을 취했다.")

    # 시간 경과
    morld.advance_time_des(SHORT_REST_HOURS * 3600000)

    return {"success": True, "events": events, "message": "짧은 휴식 완료."}


def long_rest() -> dict:
    """
    긴 휴식 실행. 자동 세이브 포함.

    Returns:
        {"success": bool, "events": [str], "message": str}
    """
    player_id = morld.get_player_id()
    if not player_id:
        return {"success": False, "events": [], "message": "플레이어 없음"}

    loc = morld.get_unit_location(player_id)
    if not loc:
        return {"success": False, "events": [], "message": "위치 불명"}

    region_id, loc_id = loc
    if not can_long_rest(region_id, loc_id):
        return {"success": False, "events": [],
                "message": "이 장소는 긴 휴식을 취하기엔 너무 좁다."}

    events = []

    # HP 전량 회복 + 침식 대폭 감소 (파티 전원)
    import party, survival, erosion, morale

    for mid in party.get_members():
        max_hp = morld.get_unit_prop(mid, "생존:최대체력") or 100
        survival.set_health(mid, max_hp)
        survival.set_satiety(mid, 80)  # 배고픔 해소
        erosion.reduce_erosion(mid, LONG_REST_EROSION_REDUCE)

    events.append(f"파티가 {LONG_REST_HOURS}시간 동안 긴 휴식을 취했다.")

    # 사기 회복
    morale.modify_party_morale(5)

    # 휴식 중 이벤트 발생
    rest_events = _roll_rest_events()
    events.extend(rest_events)

    # 시간 경과
    morld.advance_time_des(LONG_REST_HOURS * 3600000)

    # 자동 세이브
    import save_system
    if save_system.can_save_auto():
        save_system.save_auto()
        events.append("[자동 저장 완료]")

    return {"success": True, "events": events, "message": "긴 휴식 완료."}


def _roll_rest_events() -> list:
    """휴식 중 랜덤 이벤트"""
    events = []
    import party, quirk, trust, morale

    members = party.get_non_leader_members()
    if not members:
        return events

    for mid in members:
        visible_quirks = quirk.get_visible_quirks(mid)
        name = morld.get_unit_info(mid).get("name", "???") if morld.get_unit_info(mid) else "???"

        for q in visible_quirks:
            qname = q["name"]

            if qname == "도벽" and random.random() < 0.3:
                events.append(f"{name}이(가) 동료의 물건을 슬쩍했다!")
                trust.modify_trust(mid, -3)

            elif qname == "잠꼬대" and random.random() < 0.5:
                events.append(f"{name}이(가) 잠꼬대를 했다...")

            elif qname == "코골이" and random.random() < 0.5:
                events.append(f"{name}의 코골이가 심하다. 수면 방해.")

            elif qname == "몽정" and random.random() < 0.2:
                events.append(f"{name}이(가) 꿈에서... 이상한 반응을 보였다.")

        # 도주 체크 (신뢰 낮은 NPC)
        t = trust.get_trust(mid)
        m = morale.get_morale(mid)
        if t < trust.TRUST_DISCONTENT_THRESHOLD and m < morale.MORALE_SHAKEN:
            if random.random() < 0.15:
                events.append(f"{name}이(가) 밤중에 도주했다!")
                party.remove_member(mid, reason="도주")

    # 선천 기벽 발각 (랜덤)
    for mid in party.get_non_leader_members():
        all_quirks = quirk.get_quirks(mid)
        undiscovered = [q for q in all_quirks if not q["discovered"] and q["origin"] == "선천"]
        if undiscovered and random.random() < 0.2:
            q = random.choice(undiscovered)
            quirk.discover_quirk(mid, q["index"])
            name = morld.get_unit_info(mid).get("name", "???") if morld.get_unit_info(mid) else "???"
            events.append(f"{name}의 기벽 발견: {q['name']}")

    return events
