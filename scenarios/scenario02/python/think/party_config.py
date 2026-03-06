# think/party_config.py — 파티 시스템 캐릭터 설정
#
# 아키타입(묘사 톤)과 별도인 전술/분대 설정을 중앙 관리.
# 캐릭터 파일 부담 최소화.

import random
import morld

# ========================================
# A1. Disposition — 지시 성향 (2D)
# ========================================

_COMMAND_DISPOSITION = {
    #              (공세,   집중)
    "sera":       (+0.7,  +0.3),   # 돌격형, 약간 목표 지향
    "mila":       (-0.6,  -0.3),   # 방어/회복, 약간 꼼꼼
    "lina":       (-0.7,  -0.8),   # 강한 지원형, 강한 수집형
    "yuki":       (+0.2,  +0.5),   # 약간 공세(정밀 타격), 목표형
    "ella":       (+0.4,  +0.7),   # 공세, 강한 목표 직행
    "faye":       (-0.3,  -0.6),   # 약간 방어, 수집형(상인 기질)
}


# ========================================
# F1. 모집 조건
# ========================================

_DEFAULT_RECRUIT_CONDITION = {
    "affection": 40,      # 호감 >= 40 (기본)
    "submission": 50,      # 또는 복종 >= 50 (대안 경로)
    "rebellion_max": 50,   # 반발 < 50 필수
}

_RECRUIT_OVERRIDE = {
    "sera":  {"affection": 50},
    "yuki":  {"affection": 30},
    "ella":  {"affection": 60, "submission": 40},
    "faye":  {"affection": 35},
}


# ========================================
# F2. 불복 위험도
# ========================================

_ORDER_RISK = {
    "이동": 0.0, "대기": 0.0,
    "수집": 0.05, "수색": 0.1, "경계": 0.1,
    "전투": 0.2, "후퇴": -0.1,
    "follow": 0.0,
}


# ========================================
# A6. 기본 분대 행동
# ========================================

_DEFAULT_PARTY_BEHAVIOR = {
    "recruitable": True,
    "follow_distance": 30,
    "combat_join_in_party": True,
    "leaves_if_hostile": True,
}


# ========================================
# 공개 API
# ========================================

def get_disposition(unique_id):
    """Disposition 2D 조회 — (aggression, focus), 기본값 (0.0, 0.0)"""
    return _COMMAND_DISPOSITION.get(unique_id, (0.0, 0.0))


def get_recruit_condition(unique_id):
    """모집 조건 조회 (기본 + 오버라이드 병합)"""
    base = dict(_DEFAULT_RECRUIT_CONDITION)
    override = _RECRUIT_OVERRIDE.get(unique_id, {})
    base.update(override)
    return base


def can_recruit(unit_id, recruiter_id):
    """모집 가능 여부 판정

    판정:
    - 반발 >= rebellion_max → 거절 (무조건)
    - 호감 >= affection OR 복종 >= submission → 수락
    """
    info = morld.get_unit_info(unit_id)
    if not info:
        return False

    unique_id = info.get("unique_id") or info.get("name", "")
    condition = get_recruit_condition(unique_id)

    # recruiter 이름으로 관계 prop 조회
    recruiter_info = morld.get_unit_info(recruiter_id)
    recruiter_name = recruiter_info.get("name", "") if recruiter_info else ""
    if not recruiter_name:
        return False

    props = morld.get_unit_props(unit_id) or {}
    affection = props.get(f"관계:{recruiter_name}:호감", 0)
    submission = props.get(f"관계:{recruiter_name}:복종", 0)
    rebellion = props.get(f"관계:{recruiter_name}:반발", 0)

    # 반발 초과 → 무조건 거절
    if rebellion >= condition["rebellion_max"]:
        return False

    # 호감 OR 복종 충족 → 수락
    return affection >= condition["affection"] or submission >= condition["submission"]


def check_disobedience(unit_id, leader_id, order):
    """불복 판정 — True면 지시 거부

    판정 요소:
    - 반발: 높을수록 거부 확률 증가
    - 복종: 높을수록 거부 확률 감소
    - order 위험도: 위험한 지시일수록 거부 확률 증가
    """
    props = morld.get_unit_props(unit_id) or {}
    leader_info = morld.get_unit_info(leader_id)
    leader_name = leader_info.get("name", "") if leader_info else ""
    if not leader_name:
        return False  # 리더 정보 없으면 복종

    rebellion = props.get(f"관계:{leader_name}:반발", 0)
    submission = props.get(f"관계:{leader_name}:복종", 0)

    # 절대 복종
    if submission >= 80:
        return False

    # follow/후퇴는 거부하지 않음
    main_type = order.order_type.split(":")[0] if hasattr(order, 'order_type') else ""
    if main_type in ("후퇴", "follow"):
        return False

    # 기본 거부 확률: (반발 - 복종) / 200
    base_chance = (rebellion - submission) / 200.0

    # order 위험도 보정
    risk = _ORDER_RISK.get(main_type, 0.0)
    chance = base_chance + risk

    # 0% ~ 80% 클램프
    chance = max(0.0, min(0.8, chance))

    return random.random() < chance


def build_leader_traits(unique_id):
    """리더 특성 생성 (assign_leader 시 호출)"""
    aggression, focus = get_disposition(unique_id)
    return {
        "aggression": aggression,
        "focus": focus,
        "unique_id": unique_id,
    }
