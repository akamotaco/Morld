# engine/perception.py — 감각 시스템
#
# 기존 물리 시스템(sound/lighting/stealth/pollution) 출력을
# 캐릭터별 감도에 따라 다른 해상도의 정보로 가공.
#
# 4채널: 청각(sound), 시각(sight), 직감(intuition), 후각(smell)
# 감도: "감각:{���널}" prop (1~10+), 기본값 5
# 해상도:
#   1~3  존재만 ("무언가 소리가 들린다")
#   4~6  종류   ("전투 소리가 들린다")
#   7~9  상세   ("검이 부딪히는 소리가 동쪽에서 들린다")
#   10+  추적   ("2명이 전투 중 — 1홉 거리")
#
# Phase 1: 청각 (sound.get_heard 연동)
# Phase 2: 시각 (같은 Location 유닛 감지)
# Phase 3: 직감 (위험도/신뢰도 기반)
# Phase 4: 후각 (pollution 연동)

import morld


# ============================================
# 감도 기본값
# ============================================

DEFAULT_SENSITIVITY = 5

# 해상도 구간
RESOLUTION_EXISTENCE = 3   # 이하: 존재만
RESOLUTION_CATEGORY = 6    # 이하: 종류
RESOLUTION_DETAIL = 9      # 이하: 상세
# 10+: 추적


# ============================================
# 감도 조회
# ============================================

def get_sensitivity(unit_id, channel):
    """캐릭터의 감각 채널별 감도 조회.

    Args:
        unit_id: 캐릭터 unit_id
        channel: "청각" / "시각" / "직감" / "후각"

    Returns: int (1~10+, 기본값 5)
    """
    val = morld.get_unit_prop(unit_id, "감각:" + channel)
    if val is not None and val > 0:
        return int(val)
    return DEFAULT_SENSITIVITY


# ============================================
# Phase 1: 청각 (sound 연동)
# ============================================

def perceive_hearing(unit_id):
    """청각 감지 — sound.get_heard()를 감도별 해상도로 가공.

    Returns:
        list of dict:
        - resolution="existence": {"type": "hearing", "resolution": "existence", "text": "무언가 소리가 들린다"}
        - resolution="category":  {"type": "hearing", "resolution": "category", "category": "전투", "text": "전투 소리가 들린다"}
        - resolution="detail":    {"type": "hearing", "resolution": "detail", "category": ..., "sound_type": ..., "hops": ..., "text": ...}
        - resolution="tracking":  {"type": "hearing", "resolution": "tracking", "category": ..., "sound_type": ..., "hops": ..., "source_id": ..., "text": ...}
    """
    try:
        import sound
    except ImportError:
        return []

    events = sound.get_heard(unit_id)
    if not events:
        return []

    sensitivity = get_sensitivity(unit_id, "청각")
    results = []

    # 같은 location은 시각으로 확인 — 청각에서 제외
    filtered = [e for e in events if not (e.distance == 0 and e.hops == 0)]
    if not filtered:
        return []

    if sensitivity <= RESOLUTION_EXISTENCE:
        # 존재만: 소리가 있다/없다
        results.append({
            "type": "hearing",
            "resolution": "existence",
            "text": "어딘가에서 소리가 들린다.",
        })

    elif sensitivity <= RESOLUTION_CATEGORY:
        # 종류: 카테고리별 집계
        categories = set()
        for e in filtered:
            categories.add(e.category)
        for cat in categories:
            results.append({
                "type": "hearing",
                "resolution": "category",
                "category": cat,
                "text": cat + " 소리가 들린다.",
            })

    elif sensitivity <= RESOLUTION_DETAIL:
        # 상세: 타입 + 거리(홉)
        seen = set()
        for e in filtered:
            key = (e.sound_type, e.hops)
            if key in seen:
                continue
            seen.add(key)
            dist_text = str(e.hops) + "칸 거리" if e.hops > 0 else "가까이"
            results.append({
                "type": "hearing",
                "resolution": "detail",
                "category": e.category,
                "sound_type": e.sound_type,
                "hops": e.hops,
                "text": e.sound_type + " 소리 — " + dist_text,
            })

    else:
        # 추적: 소스 ID + 정확한 정보
        for e in filtered:
            dist_text = str(e.hops) + "칸 거리" if e.hops > 0 else "가까이"
            results.append({
                "type": "hearing",
                "resolution": "tracking",
                "category": e.category,
                "sound_type": e.sound_type,
                "hops": e.hops,
                "source_id": e.source_id,
                "intensity": e.intensity,
                "text": e.sound_type + " — " + dist_text + " (출처: " + str(e.source_id) + ")",
            })

    return results


# ============================================
# Phase 2: 시각 (같은 Location 유닛 감지)
# ============================================

def perceive_sight(unit_id):
    """시각 감지 — 같은 Location의 다른 유닛 목록.

    Returns:
        list of dict:
        - {"type": "sight", "unit_id": int, "name": str, "distance": float}
    """
    loc = morld.get_unit_location(unit_id)
    if not loc:
        return []

    try:
        units = morld.get_units_at_location(loc[0], loc[1])
    except (AttributeError, Exception):
        return []

    if not units:
        return []

    results = []
    for uid in units:
        if uid == unit_id:
            continue
        info = morld.get_unit_info(uid)
        if not info:
            continue
        # 오브젝트는 제외 (캐릭터만)
        if info.get("is_object"):
            continue
        name = info.get("name", str(uid))
        results.append({
            "type": "sight",
            "unit_id": uid,
            "name": name,
        })

    return results


# ============================================
# Phase 3: 직감 (위험도 기반)
# ============================================

def perceive_intuition(unit_id):
    """직감 감지 — 주변 위험도 평가.

    현재: 같은 Location에 적대 유닛(creature)이 있으면 ���험 감지.
    향후: 신뢰도/복종도 기반 배신 징후, 함정 감지 등.

    Returns:
        list of dict:
        - {"type": "intuition", "subtype": "danger"|"unease", "text": str}
    """
    sensitivity = get_sensitivity(unit_id, "직감")
    results = []

    # 같은 Location 위험 유닛 체크
    loc = morld.get_unit_location(unit_id)
    if not loc:
        return results

    try:
        units = morld.get_units_at_location(loc[0], loc[1])
    except (AttributeError, Exception):
        return results

    danger_count = 0
    for uid in units:
        if uid == unit_id:
            continue
        # creature prop 체크
        if morld.get_unit_prop(uid, "creature:hostile"):
            danger_count += 1

    if danger_count > 0 and sensitivity >= 3:
        if sensitivity <= RESOLUTION_EXISTENCE:
            results.append({
                "type": "intuition", "subtype": "danger",
                "text": "위험한 기운이 느껴진다.",
            })
        else:
            results.append({
                "type": "intuition", "subtype": "danger",
                "count": danger_count,
                "text": "적대적 존재 " + str(danger_count) + "체 감지.",
            })

    return results


# ============================================
# 통합 감지
# ============================================

def perceive_all(unit_id):
    """모든 채널의 감각 정보를 수집.

    Returns:
        {"hearing": [...], "sight": [...], "intuition": [...]}
    """
    return {
        "hearing": perceive_hearing(unit_id),
        "sight": perceive_sight(unit_id),
        "intuition": perceive_intuition(unit_id),
    }


def has_any_perception(unit_id):
    """감지된 것이 하나라도 있는지"""
    result = perceive_all(unit_id)
    for channel in result.values():
        if channel:
            return True
    return False
