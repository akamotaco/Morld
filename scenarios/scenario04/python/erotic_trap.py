# erotic_trap.py - S04 에로 함정 시스템
#
# 던전 특정 Location에 설치된 성적 함정.
# S02 arousal/stimulation 메카닉 재활용 (향후).
# 현재: 확률 판정 + 침식/사기 영향만.

import morld
import random
import erosion
import morale
import party

# === 함정 유형 ===

TRAP_TYPES = {
    "최음가스": {
        "desc": "달콤한 향기가 퍼진다... 몸이 뜨거워진다.",
        "erosion": 8,      # 침식 증가
        "morale": -3,       # 사기 감소
        "arousal": 30,      # 흥분도 (향후 arousal 시스템 연동)
        "target": "party",  # 파티 전원
    },
    "속박함정": {
        "desc": "바닥에서 사슬이 튀어나와 한 명을 붙잡았다!",
        "erosion": 5,
        "morale": -5,
        "arousal": 10,
        "target": "single",  # 랜덤 1명
    },
    "환각포자": {
        "desc": "이상한 포자가 퍼진다... 환각이 보인다...",
        "erosion": 15,       # 침식 급증
        "morale": -8,
        "arousal": 50,
        "target": "party",
        "quirk_chance": 0.2,  # 20% 확률로 성적 기벽 유발
    },
}


def check_trap(region_id: int, location_id: int) -> dict:
    """
    Location 진입 시 에로 함정 체크.

    Returns:
        {"triggered": bool, "trap_type": str, "events": [str]}
        or {"triggered": False}
    """
    # 마을에서는 함정 없음
    if region_id == 0:
        return {"triggered": False}

    # 함정 확률 (오염도 기반)
    import pollution
    poll = pollution.get_pollution(region_id, location_id)
    trap_chance = min(0.15, poll * 0.002)  # 최대 15%

    if random.random() > trap_chance:
        return {"triggered": False}

    # 함정 유형 선택
    trap_name = random.choice(list(TRAP_TYPES.keys()))
    trap = TRAP_TYPES[trap_name]
    events = [f"[함정] {trap['desc']}"]

    # 대상 결정
    members = party.get_members()
    if trap["target"] == "party":
        targets = members
    else:
        targets = [random.choice(members)] if members else []

    # 효과 적용
    for mid in targets:
        erosion.add_erosion(mid, trap["erosion"])
        morale.modify_morale(mid, trap["morale"])

        # 흥분도 (향후 arousal prop으로)
        current_arousal = morld.get_unit_prop(mid, "성욕:흥분") or 0
        morld.set_unit_prop(mid, "성욕:흥분", min(100, current_arousal + trap["arousal"]))

        name = ""
        info = morld.get_unit_info(mid)
        if info:
            name = info.get("name", "???")
        events.append(f"  {name}: 침식+{trap['erosion']}, 흥분+{trap['arousal']}")

    # 성적 기벽 유발 (환각포자)
    if trap.get("quirk_chance"):
        import quirk
        for mid in targets:
            if random.random() < trap["quirk_chance"]:
                sexual_quirks = ["몽정", "노출증", "성적집착"]
                q = random.choice(sexual_quirks)
                quirk.add_quirk(mid, q)
                name = ""
                info = morld.get_unit_info(mid)
                if info:
                    name = info.get("name", "???")
                events.append(f"  {name}에게 기벽 '{q}' 발현!")

    # 흥분 상태 파생 이벤트 체크 (향후 확장)
    _check_arousal_events(targets, events)

    return {"triggered": True, "trap_type": trap_name, "events": events}


def _check_arousal_events(targets: list, events: list):
    """흥분 상태에서의 파생 이벤트 (임시)"""
    if len(targets) < 2:
        return

    # 2인 이상 + 높은 흥분 → 이벤트 암시
    high_arousal = [mid for mid in targets
                    if (morld.get_unit_prop(mid, "성욕:흥분") or 0) >= 60]

    if len(high_arousal) >= 2:
        events.append("  ... 위험한 분위기가 감돈다.")
        # 향후: 성행위 이벤트 선택지, NTR/BBS 판정 등
