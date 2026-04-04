# taming.py - S04 조교 시스템
#
# S02의 복종 시스템 재활용 + 조교소 확장.
# 납치 → 감금 → 결박/회유/강제 → 복종 축적 → 파티 편입.
#
# S02 기존 요소 (삭제하지 않고 유지):
# - `관계:{name}:복종` prop
# - 약점 이벤트 → 협박 → 복종↑
# - 강제 행위 → 복종 자연 증가
# - 결박 + 회유 → 장기간 복종 축적
# - 복종 임계치 (≥70) → 굴복 루트

import morld
from events import subscribe_time_elapsed

# === 상수 ===
SUBMISSION_THRESHOLD = 70      # 굴복 임계치
SUBMISSION_PER_VISIT = 3       # 매 방문 기본 복종↑
SUBMISSION_PASSIVE_PER_HOUR = 0.5  # 방치 시 시간당
SUBMISSION_FORCED_BONUS = 5    # 강제 행위 시 추가
SUBMISSION_INTIMIDATE_BONUS = 4  # 협박 시 추가

ESCAPE_BASE_CHANCE = 0.05     # 탈출 시도 기본 확률/시간
REBELLION_PER_ESCAPE = 5       # 탈출 실패 시 반발↑

# === 상태 ===

_captives = {}  # unit_id -> {"name", "submission", "rebellion", "restraint", "hours"}
_accumulated_millis = 0


def reset():
    global _accumulated_millis
    _captives.clear()
    _accumulated_millis = 0


# === 감금 ===

def imprison(unit_id: int, facility_loc_id: int = None):
    """NPC 감금"""
    name = ""
    info = morld.get_unit_info(unit_id)
    if info:
        name = info.get("name", "???")

    submission = morld.get_unit_prop(unit_id, "복종") or 0
    rebellion = morld.get_unit_prop(unit_id, "반발") or 0

    _captives[unit_id] = {
        "name": name,
        "submission": int(submission),
        "rebellion": int(rebellion),
        "restraint": 50,  # 결박 강도 (0~100)
        "hours": 0,
        "facility": facility_loc_id,
    }

    morld.set_unit_prop(unit_id, "상태:감금", 1)

    # 평판 영향
    import reputation
    reputation.modify_reputation("마을주민", -5, "NPC 감금")
    reputation.modify_reputation("모험가길드", -10, "NPC 감금")

    # 파티원 신뢰 영향 (목격자)
    import party, trust
    for mid in party.get_non_leader_members():
        trust.on_witnessed_cruelty(mid)

    print(f"[taming] Imprisoned: {name} (id={unit_id}, submission={submission})")


def release(unit_id: int):
    """감금 해제"""
    if unit_id in _captives:
        name = _captives[unit_id]["name"]
        del _captives[unit_id]
        morld.set_unit_prop(unit_id, "상태:감금", 0)
        print(f"[taming] Released: {name}")


def is_captive(unit_id: int) -> bool:
    return unit_id in _captives


# === 조교 행위 ===

def visit_captive(unit_id: int, action: str = "회유") -> dict:
    """
    감금 NPC 방문 (매일 가능).

    Args:
        action: "회유", "협박", "강제", "방치"

    Returns:
        {"submission": int, "rebellion": int, "message": str}
    """
    if unit_id not in _captives:
        return {"message": "감금 대상이 아닙니다."}

    captive = _captives[unit_id]

    if action == "회유":
        captive["submission"] += SUBMISSION_PER_VISIT
        msg = f"{captive['name']}에게 부드럽게 말을 걸었다."

    elif action == "협박":
        captive["submission"] += SUBMISSION_INTIMIDATE_BONUS
        captive["rebellion"] += 2
        msg = f"{captive['name']}을(를) 협박했다."

    elif action == "강제":
        captive["submission"] += SUBMISSION_FORCED_BONUS
        captive["rebellion"] += 3
        msg = f"{captive['name']}에게 강제 행위를 했다."

    elif action == "방치":
        msg = f"{captive['name']}을(를) 방치했다."

    else:
        msg = "알 수 없는 행동."

    # prop 동기화
    morld.set_unit_prop(unit_id, "복종", captive["submission"])
    morld.set_unit_prop(unit_id, "반발", captive["rebellion"])

    return {
        "submission": captive["submission"],
        "rebellion": captive["rebellion"],
        "can_recruit": captive["submission"] >= SUBMISSION_THRESHOLD,
        "message": msg,
    }


def can_recruit(unit_id: int) -> bool:
    """파티 편입 가능 여부"""
    if unit_id not in _captives:
        return False
    return _captives[unit_id]["submission"] >= SUBMISSION_THRESHOLD


def recruit_captive(unit_id: int) -> bool:
    """감금 NPC를 파티로 편입"""
    if not can_recruit(unit_id):
        return False

    import party

    release(unit_id)
    morld.set_unit_prop(unit_id, "조교완료", 1)

    if party.add_member(unit_id):
        print(f"[taming] Recruited captive {unit_id} to party")
        return True
    return False


# === 시간 경과: 방치 복종 + 탈출 시도 ===

def _on_time_elapsed(millis: int):
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    import random

    for unit_id in list(_captives):
        captive = _captives[unit_id]
        captive["hours"] += hours

        # 방치 복종 축적
        captive["submission"] += SUBMISSION_PASSIVE_PER_HOUR * hours
        morld.set_unit_prop(unit_id, "복종", int(captive["submission"]))

        # 탈출 시도
        for _ in range(hours):
            # 결박 vs 근력
            str_stat = morld.get_unit_prop(unit_id, "스탯:근력") or 10
            escape_chance = ESCAPE_BASE_CHANCE * (str_stat / 10) * (100 - captive["restraint"]) / 100

            if random.random() < escape_chance:
                _handle_escape(unit_id)
                break

            # 탈출 실패 → 반발↑
            if random.random() < 0.1:  # 10% 확률로 시도만
                captive["rebellion"] += 1


def _handle_escape(unit_id: int):
    """탈출 성공"""
    captive = _captives.pop(unit_id)
    morld.set_unit_prop(unit_id, "상태:감금", 0)
    print(f"[taming] ESCAPE! {captive['name']} broke free!")

    # 마을에 배치 (여관으로)
    morld.set_unit_location(unit_id, 0, 1, x=100)  # 여관

    # 혼란도 영향?
    import world_knowledge
    knowledge = world_knowledge.get_knowledge(unit_id)
    if knowledge > 20:
        world_knowledge.on_knower_departed(unit_id)


def get_captives() -> dict:
    return _captives.copy()


subscribe_time_elapsed(_on_time_elapsed, min_interval=3600000)
