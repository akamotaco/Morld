# combat.py — 자동 전투 해결 (시나리오03 데모)
#
# 데모용 자동 해결(auto-resolve). MicroTurn 전투는 미래 구현.
# squad.py의 공세 레벨 + 분대원 vita에 기반한 확률적 결과.

import random
import morld


# ========================================
# 위협 코드별 전투력
# ========================================

THREAT_POWER = {
    "P": 3,   # Pest (해충) — 약함
    "R": 5,   # Raider (약탈자) — 보통
    "B": 2,   # Beast (동물) — 약함
    "W": 7,   # Wraith (망령) — 강함
}

THREAT_NAMES = {
    "P": "해충 떼",
    "R": "약탈자",
    "B": "야수",
    "W": "망령",
}


# ========================================
# 전투 결과
# ========================================

class CombatResult:
    __slots__ = ("occurred", "victory", "threat_code", "threat_name",
                 "log", "damage_taken", "deaths", "growth")

    def __init__(self, occurred=False, victory=False, threat_code=None,
                 threat_name=None, log=None, damage_taken=None,
                 deaths=None, growth=None):
        self.occurred = occurred
        self.victory = victory
        self.threat_code = threat_code
        self.threat_name = threat_name or ""
        self.log = log or []
        self.damage_taken = damage_taken or {}  # {unit_id: damage}
        self.deaths = deaths or []              # [unit_id] — HP 0 도달 (결번 처리는 cycle 담당)
        self.growth = growth or {}              # {unit_id: vita 증가량}


# ========================================
# 전투 해결
# ========================================

def resolve_room_combat(squad_id, room):
    """방 진입 시 전투 자동 해결.

    Args:
        squad_id: 분대 ID
        room: mapgen room dict (threat 키 확인)

    Returns:
        CombatResult
    """
    threat_code = room.get("threat")
    if not threat_code:
        return CombatResult(occurred=False)

    import squad as squad_module

    threat_power = THREAT_POWER.get(threat_code, 3)
    threat_name = THREAT_NAMES.get(threat_code, "불명")

    # 분대 전투력 계산
    unit_ids = squad_module.get_all_unit_ids(squad_id)
    squad_power = 0
    unit_vitas = {}
    for uid in unit_ids:
        vita = morld.get_unit_prop(uid, "vita") or 5
        unit_vitas[uid] = vita
        squad_power += vita

    # 공세 레벨 보정
    aggression_val = squad_module.get_aggression_value(squad_id)
    # aggressive: +20% power, +30% damage taken
    # defensive: -20% power, -50% damage taken
    power_mod = 1.0 + aggression_val * 0.1
    damage_mod = 1.0 + aggression_val * 0.15

    effective_power = squad_power * power_mod

    # 승률 계산
    ratio = effective_power / max(threat_power, 1)
    win_chance = min(0.95, max(0.1, 0.5 + (ratio - 1.0) * 0.3))

    log = []
    log.append(f"{threat_name}과(와) 조우!")
    log.append(f"분대 전투력: {squad_power} vs 위협: {threat_power}")

    victory = random.random() < win_chance

    # 피해 배분 (전위가 더 많이 받음)
    damage_taken = {}
    deaths = []
    if victory:
        log.append("전투 승리!")
        base_damage = max(1, int(threat_power * 0.3 * damage_mod))
    else:
        log.append("전투 패배... 후퇴합니다.")
        base_damage = max(2, int(threat_power * 0.6 * damage_mod))

    for uid in unit_ids:
        rank = squad_module.get_member_rank(squad_id, uid)
        # 전위(1)는 더 많이, 후위(3)는 덜 받음
        rank_factor = max(0.3, 1.4 - (rank - 1) * 0.4)
        dmg = max(1, int(base_damage * rank_factor))
        damage_taken[uid] = dmg

        # HP 적용 — prop 부재 시 0 반환(계약)이므로 truthy 판정으로 초기화
        hp = morld.get_unit_prop(uid, "생존:체력")
        if not hp:
            from assets.characters.squad_member import base_hp_for_vita
            hp = base_hp_for_vita(unit_vitas[uid])
        new_hp = max(0, hp - dmg)
        morld.set_unit_prop(uid, "생존:체력", new_hp)
        if new_hp <= 0:
            deaths.append(uid)
            log.append(f"  {_get_name(uid)} 신호 두절 — 결번 처리 대상.")
        elif new_hp <= 5:
            log.append(f"  {_get_name(uid)} 중상!")

    # 성장/인간성 (생존자 대상)
    growth = {}
    survivors = [uid for uid in unit_ids if uid not in deaths]
    for uid in survivors:
        if victory:
            vita = unit_vitas[uid]
            if vita < 10:
                morld.set_unit_prop(uid, "vita", vita + 1)
                growth[uid] = 1
        # 인간성 마모: 전투 -2, 동료 결번 목격 -5 (하한 1 — 0은 미추적)
        humanity = morld.get_unit_prop(uid, "인간성")
        if humanity:
            wear = 2 + (5 * len(deaths))
            morld.set_unit_prop(uid, "인간성", max(1, humanity - wear))

    # 위협 제거 (승리 시)
    if victory:
        room.pop("threat", None)

    result = CombatResult(
        occurred=True,
        victory=victory,
        threat_code=threat_code,
        threat_name=threat_name,
        log=log,
        damage_taken=damage_taken,
        deaths=deaths,
        growth=growth,
    )
    return result


def _get_name(unit_id):
    """유닛 이름 조회"""
    info = morld.get_unit_info(unit_id)
    if info:
        return info.get("name", f"Unit-{unit_id}")
    return f"Unit-{unit_id}"
