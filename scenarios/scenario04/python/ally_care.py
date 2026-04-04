# ally_care.py - S04 동료 케어 시스템
#
# 플레이어 사기 20~39에서 랜덤 행동 발생 시,
# 동료가 케어하면 취소 + 사기 회복.
#
# 연인/D/신뢰 높은 NPC에 따라 효과 다름.

import morld
import party
import morale
import trust


def attempt_care(player_id: int) -> dict:
    """
    동료 케어 시도.
    플레이어 사기가 낮을 때 호출.

    Returns:
        {"cared": bool, "carer_id": int, "carer_name": str,
         "morale_gain": int, "message": str}
    """
    members = party.get_non_leader_members()
    if not members:
        return {"cared": False, "message": "혼자서는 버텨야 한다..."}

    # 케어 가능 NPC 찾기 (신뢰 높은 순)
    best_carer = None
    best_gain = 0
    best_message = ""

    for mid in members:
        t = trust.get_trust(mid)
        m = morale.get_morale(mid)

        # 본인도 사기 낮으면 케어 불가
        if m < morale.MORALE_SHAKEN:
            continue

        info = morld.get_unit_info(mid)
        name = info.get("name", "???") if info else "???"

        # D (특수 존재): 동질감
        if morld.get_unit_prop(mid, "정규NPC") == "D":
            gain = 10
            msg = f'{name}: "나도 알아, 그 느낌... 괜찮아."'
        # 연인 관계
        elif morld.get_unit_prop(mid, f"관계:{name}:연인"):
            gain = 15
            msg = f'{name}이(가) 조용히 손을 잡아준다.'
        # 신뢰 높음
        elif t >= trust.TRUST_LOYALTY_THRESHOLD:
            gain = 8
            msg = f'{name}: "정신 차려! 여기서 무너지면 안 돼!"'
        # 보통
        elif t >= trust.TRUST_DISCONTENT_THRESHOLD:
            gain = 3
            msg = f'{name}이(가) 걱정스럽게 바라본다.'
        else:
            continue  # 신뢰 낮으면 케어 안 함

        if gain > best_gain:
            best_carer = mid
            best_gain = gain
            best_message = msg

    if best_carer is None:
        return {"cared": False, "message": "아무도 신경 쓰지 않는다..."}

    # 사기 회복
    morale.modify_morale(player_id, best_gain)

    return {
        "cared": True,
        "carer_id": best_carer,
        "carer_name": best_message.split(":")[0] if ":" in best_message else "동료",
        "morale_gain": best_gain,
        "message": best_message,
    }


def check_player_morale_event(player_id: int) -> dict:
    """
    플레이어 사기 체크 → 랜덤 행동 or 동료 케어.
    게임 루프에서 주기적으로 호출.

    Returns:
        {"event": str, "details": dict}
        event: "normal" / "care" / "random_action" / "collapse"
    """
    m = morale.get_morale(player_id)

    if m >= morale.MORALE_SHAKEN:
        return {"event": "normal", "details": {}}

    if m <= 0:
        # 붕괴
        return {"event": "collapse", "details": {
            "message": "더 이상 버틸 수 없다... 마을로 돌아가야 한다."
        }}

    if m < morale.MORALE_DANGER:
        # 위험 구간: 랜덤 행동 → 동료 케어 시도
        import random
        if random.random() < 0.3:  # 30% 확률로 랜덤 행동 발생
            care_result = attempt_care(player_id)
            if care_result["cared"]:
                return {"event": "care", "details": care_result}
            else:
                # 케어 실패 → 랜덤 행동 실행
                action = random.choice([
                    "도망치고 싶다...",
                    "아이템을 떨어뜨렸다!",
                    "동료가 의심스럽다...",
                ])
                return {"event": "random_action", "details": {"message": action}}

    return {"event": "normal", "details": {}}
