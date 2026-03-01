# combat.py — 전투 코어 모듈
#
# 전투 스탯, 데미지 공식, 적대도, 디버프, 시간 처리
# 명세: docs/combat-implementation.md Section 2-3

import random
import morld
from events import subscribe_time_elapsed

# ── 전투 스탯 기본값 ──
DEFAULT_STATS = {
    "전투:공격력": 1,          # 맨손
    "전투:방어력": 0,
    "전투:명중": 80,           # %
    "전투:회피": 5,            # %
    "전투:치명타": 5,          # %
    "전투:사거리": 50,         # px (맨손)
    "전투:공격속도": 1.0,      # 배율
}

# ── 데미지 공식 ──
CRIT_MULTIPLIER = 1.5
DAMAGE_VARIANCE = 0.10        # ±10%
MIN_DAMAGE = 1

# ── 명중률 범위 ──
HIT_CHANCE_MIN = 5
HIT_CHANCE_MAX = 95

# ── 공격 시간 (ms) ──
MELEE_ATTACK_DURATION = 6_000
RANGED_ATTACK_DURATION = 10_000

# ── 적대도 ──
HOSTILITY_NEUTRAL = 29
HOSTILITY_ALERT = 49
HOSTILITY_HOSTILE = 50
HOSTILITY_ATTACK_ON_SIGHT = 80
HOSTILITY_DECAY_PER_HOUR = 2

HOSTILITY_ON_ATTACK = 30
HOSTILITY_ON_FAINT = 50
HOSTILITY_ON_STEAL_SUCCESS = 20
HOSTILITY_ON_STEAL_FAIL = 40
HOSTILITY_ON_NURSING = -20

AFFECTION_ON_ATTACK = -10
AFFECTION_ON_FAINT = -25
AFFECTION_ON_STEAL_FAIL = -20
AFFECTION_ON_NURSING = 10

# ── 세력(Faction) 시스템 ──
# 관계값: -1=적대, 0=중립, 1=우호
# 같은 세력 → 우호(1). 세력 미설정(None) → 중립(0).
#
# 해석 순서 (get_unit_relation):
#   ① 두 유닛의 세력 prop("세력") 조회
#   ② Region 테이블 → Global 테이블 → 기본값(중립) 순으로 세력 관계 조회
#   ③ 개인 세력 override: 관계:{target_faction}:세력도
#   ④ 개인 유닛 override: 관계:{target_unique_id}:세력도 (최우선)

GLOBAL_FACTION_RELATIONS = {}   # {(faction_a, faction_b): relation}
REGION_FACTION_RELATIONS = {}   # {region_id: {(faction_a, faction_b): relation}}


def register_faction_relation(faction_a, faction_b, relation, region_id=None):
    """세력 관계 등록 (시나리오 초기화 시 호출)

    Args:
        faction_a, faction_b: 세력 이름
        relation: -1=적대, 0=중립, 1=우호
        region_id: 지정 시 해당 Region에만 적용, None이면 전역(global)
    """
    if region_id is not None:
        REGION_FACTION_RELATIONS.setdefault(region_id, {})[(faction_a, faction_b)] = relation
    else:
        GLOBAL_FACTION_RELATIONS[(faction_a, faction_b)] = relation


def get_faction_relation(faction_a, faction_b, region_id=None) -> int:
    """세력 관계 조회: 1=우호, 0=중립, -1=적대.

    해석 순서: Region 테이블 → Global 테이블 → 기본값(중립)
    같은 세력끼리는 우호(1). 세력 미설정(None)이면 중립(0).
    """
    if faction_a and faction_b and faction_a == faction_b:
        return 1  # 같은 세력 = 우호
    # Region 우선
    if region_id is not None:
        region_table = REGION_FACTION_RELATIONS.get(region_id, {})
        if faction_a and faction_b:
            rel = region_table.get((faction_a, faction_b))
            if rel is None:
                rel = region_table.get((faction_b, faction_a))
            if rel is not None:
                return rel
    # Global fallback
    if faction_a and faction_b:
        rel = GLOBAL_FACTION_RELATIONS.get((faction_a, faction_b))
        if rel is None:
            rel = GLOBAL_FACTION_RELATIONS.get((faction_b, faction_a))
        if rel is not None:
            return rel
    return 0  # 세력 정보 없으면 중립


def get_unit_relation(unit_id, target_id, region_id=None) -> int:
    """두 유닛 간 최종 관계도 (-1/0/1).

    해석 순서:
      1. 두 유닛의 세력(세력 prop) 조회
      2. Region → Global 세력 관계 조회 (없으면 중립)
      3. unit의 개인 세력 override: 관계:{target_faction}:세력도
      4. unit의 개인 유닛 override: 관계:{target_unique_id}:세력도 (최우선)
    """
    my_faction = morld.get_unit_prop(unit_id, "세력")
    target_faction = morld.get_unit_prop(target_id, "세력")

    # 기본 세력 관계
    result = get_faction_relation(my_faction, target_faction, region_id)

    # 개인 세력 override
    if target_faction:
        override = morld.get_unit_prop(unit_id, f"관계:{target_faction}:세력도")
        if override is not None:
            result = int(override)

    # 개인 유닛 override (최우선)
    target_info = morld.get_unit_info(target_id)
    if target_info:
        target_unique = target_info.get("unique_id") or ""
        if target_unique:
            override = morld.get_unit_prop(unit_id, f"관계:{target_unique}:세력도")
            if override is not None:
                return int(override)

    return result


def is_faction_hostile(faction_a, faction_b) -> bool:
    """두 세력이 적대 관계인지"""
    return get_faction_relation(faction_a, faction_b) < 0


def is_faction_friendly(faction_a, faction_b) -> bool:
    """두 세력이 우호 관계인지"""
    return get_faction_relation(faction_a, faction_b) > 0


def is_creature_unit(unit_id):
    """생물(Creature) 유닛인지 — morld API의 UnitType 기반"""
    info = morld.get_unit_info(unit_id)
    if not info:
        return False
    return bool(info.get("is_creature", False))


def has_enemies_at_location(unit_id, region_id, location_id):
    """해당 location에 unit_id의 적이 존재하는지"""
    import survival as _surv
    units = morld.get_units_at_location(region_id, location_id)
    for uid in units:
        if uid == unit_id:
            continue
        if morld.get_unit_prop(uid, "상태:사망"):
            continue
        if _surv.is_npc_fainted(uid):
            continue
        if get_unit_relation(unit_id, uid, region_id) < 0:
            return True
        if is_hostile_to(unit_id, uid):
            return True
    return False


def hears_combat_sound(unit_id):
    """전투 소리를 듣고 있는지"""
    import sound
    return len(sound.get_heard_by_category(unit_id, "전투")) > 0


def get_combat_sound_locations(unit_id):
    """전투 소리가 들리는 source location 집합 반환"""
    import sound
    events = sound.get_heard_by_category(unit_id, "전투")
    return {e.source_location for e in events if e.source_location}


DEFAULT_AGGRO_RANGE = 100
DEFAULT_TERRITORY_RANGE = 50

# ── 디버프 ──
BLEEDING_DAMAGE_PER_HOUR = 3
BLEEDING_CHANCE_ON_CRIT = 50
BLEEDING_DURATION_HOURS = 3
SLOW_DURATION_HOURS = 2
SLOW_SPEED_PERCENT = 50

# ── 독 ──
POISON_DAMAGE_PER_HOUR = 2
POISON_DURATION_HOURS = 4

# ── 부위 부상 ──
BODY_PARTS = ("머리", "팔", "다리", "몸통")
INJURY_DURATION_HOURS = 4
INJURY_CHANCE_ON_CRIT = 30        # %
LEG_INJURY_SPEED = 60             # 이동속도 60%
ARM_INJURY_ATK_PENALTY = 0.30     # 공격력 30% 감소
HEAD_INJURY_ACC_PENALTY = 15      # 명중 -15

# ── 조준 공격 ──
AIMED_ATTACK_ACC_PENALTY = 20     # 명중률 -20
AIMED_ATTACK_SPEED_MULT = 1.2     # 공격속도 ×1.2 (20% 느림)

# ── 마비 ──
PARALYSIS_DURATION_HOURS = 2

# ── 거미줄 ──
WEB_BIND_DURATION_HOURS = 2
WEB_BIND_ESCAPE_DIFFICULTY = 20   # 결박:강도 상당 (로프=30보다 약함)

# ── 엄폐 ──
COVER_DISTANCE = 15               # 엄폐 유효 거리 (px)
COVER_PARTIAL = 1                 # 부분 엄폐 (나무, 벤치 등)
COVER_HALF = 2                    # 절반 엄폐 (식탁, 바리케이드 등)
COVER_FULL = 3                    # 완전 엄폐 (벽, 대형 구조물 등)
COVER_BONUS = {
    COVER_PARTIAL: {"evasion": 10, "damage_reduction": 0.20},
    COVER_HALF:    {"evasion": 20, "damage_reduction": 0.40},
    COVER_FULL:    {"evasion": 40, "damage_reduction": 0.70},
}

# ── 탄약 ──
RELOAD_DURATION = 5_000
JAM_BASE_CHANCE = 3

# ── 은신 기습 ──
STEALTH_CRIT_BONUS = 30


# ========================================
# 모듈 상태
# ========================================

_hostile_mode = False

# ── 특수 공격 테이블 (범용 — 새 능력은 여기에 1줄 추가) ──
# key = attacker prop, value = 적용 함수 (target_id)
# 확률은 attacker의 해당 prop 값 (%)
_SPECIAL_ATTACKS = None   # lazy 초기화


def _get_special_attacks():
    """특수 공격 테이블 lazy 초기화 (순환참조 회피)"""
    global _SPECIAL_ATTACKS
    if _SPECIAL_ATTACKS is None:
        _SPECIAL_ATTACKS = {
            "전투:독공격":     lambda tid: apply_poison(tid),
            "전투:거미줄공격": lambda tid: apply_web_bind(tid) if not is_web_bound(tid) else None,
            "전투:마비공격":   lambda tid: apply_paralysis(tid),
        }
    return _SPECIAL_ATTACKS


def get_equipped_weapon(unit_id: int):
    """장착된 무기 item_id 반환 (없으면 None)"""
    import equipment
    items = equipment.get_equipped_items(unit_id)
    for item_id in (items or []):
        info = morld.get_item_info(item_id)
        if not info:
            continue
        equip_props = info.get("equip_props") or {}
        if "전투:공격력" in equip_props:
            return item_id
    return None


# ========================================
# 스탯 조회
# ========================================

def get_combat_stat(unit_id: int, stat_name: str):
    """전투 스탯 조회 (base prop + equip_props 합산 + 부상 페널티)"""
    all_props = morld.get_actual_props(unit_id)
    if all_props and stat_name in all_props:
        value = all_props[stat_name]
    else:
        value = DEFAULT_STATS.get(stat_name, 0)

    # 팔 부상 → 공격력 감소
    if stat_name == "전투:공격력":
        if morld.get_unit_prop(unit_id, "부상:팔"):
            value = max(1, int(value * (1 - ARM_INJURY_ATK_PENALTY)))
    # 머리 부상 → 명중 감소
    elif stat_name == "전투:명중":
        if morld.get_unit_prop(unit_id, "부상:머리"):
            value = value - HEAD_INJURY_ACC_PENALTY

    return value


def get_weapon_equip_props(unit_id: int) -> dict:
    """장착 무기의 equip_props만 추출

    morld.get_actual_props()에서 전투: prefix 키만 필터링.
    """
    all_props = morld.get_actual_props(unit_id)
    if not all_props:
        return {}
    return {k: v for k, v in all_props.items() if k.startswith("전투:")}


# ========================================
# 거리 계산
# ========================================

def get_distance(unit_a: int, unit_b: int) -> float:
    """두 유닛 간 거리 (px). 다른 Location → float('inf')."""
    info_a = morld.get_unit_info(unit_a)
    info_b = morld.get_unit_info(unit_b)
    if not info_a or not info_b:
        return float('inf')

    if (info_a.get("region_id") != info_b.get("region_id") or
            info_a.get("location_id") != info_b.get("location_id")):
        return float('inf')

    return abs(info_a.get("x", 0) - info_b.get("x", 0))


def is_in_range(attacker_id: int, target_id: int) -> bool:
    """공격 사거리 내 여부"""
    weapon_range = get_combat_stat(attacker_id, "전투:사거리")
    dist = get_distance(attacker_id, target_id)
    return dist <= weapon_range


# ========================================
# 명중 / 데미지
# ========================================

def calculate_hit_chance(attacker_id, target_id) -> int:
    """명중률 = attacker_명중 - target_회피 - 엄폐보너스, clamp(5, 95)"""
    accuracy = get_combat_stat(attacker_id, "전투:명중")
    evasion = get_combat_stat(target_id, "전투:회피")

    # 엄폐 회피 보너스
    cover = get_cover_bonus(target_id)
    if cover:
        evasion += cover["evasion"]

    return max(HIT_CHANCE_MIN, min(HIT_CHANCE_MAX, accuracy - evasion))


def roll_hit(attacker_id, target_id) -> tuple:
    """Returns: (hit: bool, crit: bool)"""
    hit_chance = calculate_hit_chance(attacker_id, target_id)
    roll = random.randint(1, 100)
    if roll > hit_chance:
        return (False, False)

    crit_chance = get_combat_stat(attacker_id, "전투:치명타")
    crit_roll = random.randint(1, 100)
    return (True, crit_roll <= crit_chance)


def calculate_damage(attacker_id, target_id, is_crit=False) -> int:
    """공식: max(1, atk - def//2) × variance × crit_mult × 엄폐감소"""
    atk = get_combat_stat(attacker_id, "전투:공격력")
    defense = get_combat_stat(target_id, "전투:방어력")

    base = max(MIN_DAMAGE, atk - defense // 2)

    # ±10% variance
    variance = 1.0 + random.uniform(-DAMAGE_VARIANCE, DAMAGE_VARIANCE)
    damage = base * variance

    if is_crit:
        damage *= CRIT_MULTIPLIER

    # 엄폐 피해 감소
    cover = get_cover_bonus(target_id)
    if cover:
        damage = damage * (1 - cover["damage_reduction"])

    return max(MIN_DAMAGE, int(damage))


# ========================================
# 데미지 적용
# ========================================

def apply_damage(target_id: int, damage: int, attacker_id: int = None):
    """HP 감소 + 기절/탈진 판정

    survival.add_health()는 기절을 자동 트리거하지 않으므로
    HP가 0이 되면 명시적으로 기절 함수를 호출한다.
    HP가 EXHAUSTION_HP_THRESHOLD 이하이면 탈진 상태로 진입한다.
    """
    import survival

    survival.add_health(target_id, -damage)

    current_hp = morld.get_unit_prop(target_id, "생존:체력") or 0
    fainted = False

    if current_hp <= 0:
        player_id = morld.get_player_id()
        if target_id == player_id:
            survival._enter_player_faint()
        else:
            survival._enter_faint(target_id)
        fainted = True
    elif current_hp <= survival.EXHAUSTION_HP_THRESHOLD:
        # 탈진 자동 진입 (전투 피해)
        if target_id != morld.get_player_id():
            survival._enter_exhaustion(target_id)

    return fainted


# ========================================
# 전투 대사
# ========================================

def _emit_combat_line(unit_id, line_type):
    """전투 대사 출력 (COMBAT_LINES 보유 캐릭터만)"""
    from assets.characters import get_instance
    char = get_instance(unit_id)
    if not char:
        return
    combat_lines = getattr(char, 'COMBAT_LINES', None)
    if not combat_lines:
        return
    lines = combat_lines.get(line_type, [])
    if lines:
        import random as _rnd
        morld.add_action_log(_rnd.choice(lines))


# ========================================
# 공격 실행
# ========================================

def execute_attack(attacker_id: int, target_id: int) -> dict:
    """단일 공격 실행

    Returns: {"hit", "crit", "damage", "target_hp", "target_fainted", "message"}
    """
    import sound

    result = {
        "hit": False,
        "crit": False,
        "damage": 0,
        "target_hp": 0,
        "target_fainted": False,
        "message": "",
    }

    # 사거리 체크
    if not is_in_range(attacker_id, target_id):
        result["message"] = "사거리 밖이다."
        return result

    # 원거리 무기 체크
    weapon_range = get_combat_stat(attacker_id, "전투:사거리")
    is_ranged = weapon_range > 100

    if is_ranged:
        current_ammo = morld.get_unit_prop(attacker_id, "전투:현재탄약") or 0
        if current_ammo <= 0:
            result["message"] = "탄약이 없다!"
            return result

        # 화기 잼 판정
        ammo_type = get_combat_stat(attacker_id, "전투:탄약")
        if ammo_type and ammo_type != "arrow":
            weapon_id = get_equipped_weapon(attacker_id)
            durability = morld.get_unit_prop(weapon_id, "내구도") if weapon_id else 100
            if durability is None:
                durability = 100
            jam_chance = JAM_BASE_CHANCE + max(0, (50 - durability) // 10)
            if random.randint(1, 100) <= jam_chance:
                morld.set_unit_prop(attacker_id, "상태:잼", 1)
                morld.modify_prop(attacker_id, "전투:현재탄약", -1)
                result["message"] = "잼이 발생했다! 재장전이 필요하다."
                return result

    # 공격 판정
    attacker_info = morld.get_unit_info(attacker_id)
    target_info = morld.get_unit_info(target_id)
    attacker_name = attacker_info.get("name", "?") if attacker_info else "?"
    target_name = target_info.get("name", "?") if target_info else "?"

    hit, crit = roll_hit(attacker_id, target_id)

    if not hit:
        result["message"] = f"{attacker_name}의 공격이 빗나갔다."
        # 원거리 탄약 소모
        if is_ranged:
            morld.modify_prop(attacker_id, "전투:현재탄약", -1)
        # 소리
        if is_ranged:
            ammo_type = get_combat_stat(attacker_id, "전투:탄약")
            if ammo_type and ammo_type != "arrow":
                sound.emit_sound(attacker_id, "gunshot")
            else:
                sound.emit_sound(attacker_id, "combat")
        else:
            sound.emit_sound(attacker_id, "combat")
        return result

    # 데미지 계산
    damage = calculate_damage(attacker_id, target_id, crit)
    fainted = apply_damage(target_id, damage, attacker_id)
    target_hp = morld.get_unit_prop(target_id, "생존:체력") or 0

    result["hit"] = True
    result["crit"] = crit
    result["damage"] = damage
    result["target_hp"] = target_hp
    result["target_fainted"] = fainted

    # 전투 대사 — 공격/피격/low_hp/사망
    _emit_combat_line(attacker_id, "attack")
    _emit_combat_line(target_id, "hit")
    target_max_hp = morld.get_unit_prop(target_id, "생존:최대체력") or 1
    if target_hp > 0 and target_hp / target_max_hp <= 0.3:
        _emit_combat_line(target_id, "low_hp")
    if fainted:
        _emit_combat_line(target_id, "death")

    # 메시지
    if crit:
        result["message"] = f"{attacker_name}의 치명타! {target_name}에게 {damage}의 피해를 입혔다."
    else:
        result["message"] = f"{attacker_name}이(가) {target_name}에게 {damage}의 피해를 입혔다."

    if fainted:
        result["message"] += f" {target_name}이(가) 기절했다!"

    # 치명타 + 출혈
    if crit and random.randint(1, 100) <= BLEEDING_CHANCE_ON_CRIT:
        apply_bleeding(target_id)
        result["message"] += " 출혈이 발생했다!"

    # 치명타 + 부위 부상
    if crit and random.randint(1, 100) <= INJURY_CHANCE_ON_CRIT:
        part = random.choice(BODY_PARTS)
        if part != "몸통":
            apply_body_injury(target_id, part)
            result["message"] += f" {target_name}의 {part}에 부상!"

    # 특수 공격 처리 (범용 — 독, 거미줄, 마비 등 확장 가능)
    _SPECIAL_ATTACK_MESSAGES = {
        "전투:독공격":     "독이 퍼진다!",
        "전투:거미줄공격": "거미줄에 묶였다!",
        "전투:마비공격":   "몸이 마비됐다!",
    }
    for prop_key, apply_fn in _get_special_attacks().items():
        chance = morld.get_unit_prop(attacker_id, prop_key) or 0
        if chance > 0 and hit and random.randint(1, 100) <= chance:
            apply_fn(target_id)
            msg = _SPECIAL_ATTACK_MESSAGES.get(prop_key, "")
            if msg:
                result["message"] += f" {msg}"

    # 무기 내구도 감소
    weapon_id = get_equipped_weapon(attacker_id)
    if weapon_id is not None:
        degrade_durability(weapon_id, amount=1, owner_id=attacker_id)

    # 소리
    if is_ranged:
        ammo_type = get_combat_stat(attacker_id, "전투:탄약")
        if ammo_type and ammo_type != "arrow":
            sound.emit_sound(attacker_id, "gunshot")
        else:
            sound.emit_sound(attacker_id, "combat")
    else:
        sound.emit_sound(attacker_id, "combat")

    # 원거리 탄약 소모
    if is_ranged:
        morld.modify_prop(attacker_id, "전투:현재탄약", -1)

    return result


def execute_aimed_attack(attacker_id: int, target_id: int, body_part: str) -> dict:
    """조준 공격 — 명중률↓ + 명중 시 해당 부위 부상 확정

    Returns: {"hit", "crit", "damage", "target_hp", "target_fainted", "message"}
    """
    import sound

    result = {
        "hit": False, "crit": False, "damage": 0,
        "target_hp": 0, "target_fainted": False, "message": "",
    }

    if not is_in_range(attacker_id, target_id):
        result["message"] = "사거리 밖이다."
        return result

    weapon_range = get_combat_stat(attacker_id, "전투:사거리")
    is_ranged = weapon_range > 100

    if is_ranged:
        current_ammo = morld.get_unit_prop(attacker_id, "전투:현재탄약") or 0
        if current_ammo <= 0:
            result["message"] = "탄약이 없다!"
            return result
        ammo_type = get_combat_stat(attacker_id, "전투:탄약")
        if ammo_type and ammo_type != "arrow":
            durability = morld.get_unit_prop(attacker_id, "내구도") or 100
            jam_chance = JAM_BASE_CHANCE + max(0, (50 - durability) // 10)
            if random.randint(1, 100) <= jam_chance:
                morld.set_unit_prop(attacker_id, "상태:잼", 1)
                morld.modify_prop(attacker_id, "전투:현재탄약", -1)
                result["message"] = "잼이 발생했다! 재장전이 필요하다."
                return result

    attacker_info = morld.get_unit_info(attacker_id)
    target_info = morld.get_unit_info(target_id)
    attacker_name = attacker_info.get("name", "?") if attacker_info else "?"
    target_name = target_info.get("name", "?") if target_info else "?"

    # 조준 공격 명중률 페널티 적용
    accuracy = get_combat_stat(attacker_id, "전투:명중") - AIMED_ATTACK_ACC_PENALTY
    evasion = get_combat_stat(target_id, "전투:회피")
    cover = get_cover_bonus(target_id)
    if cover:
        evasion += cover["evasion"]
    hit_chance = max(HIT_CHANCE_MIN, min(HIT_CHANCE_MAX, accuracy - evasion))

    roll = random.randint(1, 100)
    if roll > hit_chance:
        result["message"] = f"{attacker_name}의 조준 공격이 빗나갔다."
        if is_ranged:
            morld.modify_prop(attacker_id, "전투:현재탄약", -1)
        sound.emit_sound(attacker_id, "combat")
        return result

    crit_chance = get_combat_stat(attacker_id, "전투:치명타")
    crit = random.randint(1, 100) <= crit_chance

    damage = calculate_damage(attacker_id, target_id, is_crit=crit)
    fainted = apply_damage(target_id, damage, attacker_id)
    target_hp = morld.get_unit_prop(target_id, "생존:체력") or 0

    result["hit"] = True
    result["crit"] = crit
    result["damage"] = damage
    result["target_hp"] = target_hp
    result["target_fainted"] = fainted

    if crit:
        result["message"] = f"{attacker_name}의 {body_part} 조준 치명타! {target_name}에게 {damage}의 피해."
    else:
        result["message"] = f"{attacker_name}이(가) {target_name}의 {body_part}에 {damage}의 피해."

    if fainted:
        result["message"] += f" {target_name}이(가) 기절했다!"

    # 명중 → 해당 부위 부상 확정 (몸통 제외)
    if body_part != "몸통":
        apply_body_injury(target_id, body_part)
        result["message"] += f" {body_part} 부상!"

    # 치명타 + 출혈 (일반 공격과 동일)
    if crit and random.randint(1, 100) <= BLEEDING_CHANCE_ON_CRIT:
        apply_bleeding(target_id)
        result["message"] += " 출혈이 발생했다!"

    # 독 공격
    poison_chance = morld.get_unit_prop(attacker_id, "전투:독공격") or 0
    if poison_chance > 0 and random.randint(1, 100) <= poison_chance:
        apply_poison(target_id)
        result["message"] += " 독이 퍼진다!"

    # 무기 내구도 감소
    weapon_id = get_equipped_weapon(attacker_id)
    if weapon_id is not None:
        degrade_durability(weapon_id, amount=1, owner_id=attacker_id)

    if is_ranged:
        ammo_type = get_combat_stat(attacker_id, "전투:탄약")
        if ammo_type and ammo_type != "arrow":
            sound.emit_sound(attacker_id, "gunshot")
        else:
            sound.emit_sound(attacker_id, "combat")
    else:
        sound.emit_sound(attacker_id, "combat")

    if is_ranged:
        morld.modify_prop(attacker_id, "전투:현재탄약", -1)

    return result


def check_npc_combat_join(region_id: int, location_id: int) -> list:
    """같은 Location에서 전투에 합류할 NPC 리스트 반환

    BATTLE_BEHAVIOR.join_combat=True인 NPC 중,
    같은 location + 호감도 >= join_threshold(기본 0) → 합류 대상.
    """
    import think
    import survival

    joinable = []
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "") if player_info else ""

    for unit_id, agent in think.get_all_agents().items():
        # 같은 location인지 확인
        loc = morld.get_unit_location(unit_id)
        if not loc or loc[0] != region_id or loc[1] != location_id:
            continue

        # 행동불능 체크
        if survival.is_npc_fainted(unit_id) or survival.is_npc_exhausted(unit_id):
            continue

        # BATTLE_BEHAVIOR 확인
        behavior = getattr(agent, 'BATTLE_BEHAVIOR', None)
        if not behavior:
            continue
        if not behavior.get("join_combat", False):
            continue

        # 이미 전투 중이면 스킵 (FSM 스택 기반)
        if any(s.state_type == "combat" for s in agent._fsm_stack):
            continue

        # 호감도 체크
        threshold = behavior.get("join_threshold", 0)
        affection = morld.get_unit_prop(unit_id, f"관계:{player_name}:호감") or 0
        if affection >= threshold:
            joinable.append(unit_id)

    return joinable


def can_fight(unit_id: int) -> bool:
    """전투 가능 상태 확인 (HP > 0, 기절/탈진/마비/사망 아님)"""
    import survival

    hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
    if hp <= 0:
        return False

    if survival.is_npc_fainted(unit_id):
        return False

    if survival.is_npc_exhausted(unit_id):
        return False

    if morld.get_unit_prop(unit_id, "상태:사망"):
        return False

    if morld.get_unit_prop(unit_id, "상태:마비"):
        return False

    return True


# ========================================
# 적대도 API
# ========================================

def get_hostility(unit_id, target_name) -> int:
    """적대도 조회 (관계:{name}:적대 prop)"""
    return morld.get_unit_prop(unit_id, f"관계:{target_name}:적대") or 0


def set_hostility(unit_id, target_name, value):
    """적대도 설정 (0-100 clamp)"""
    clamped = max(0, min(100, value))
    morld.set_unit_prop(unit_id, f"관계:{target_name}:적대", clamped)


def modify_hostility(unit_id, target_name, delta):
    """적대도 증감"""
    current = get_hostility(unit_id, target_name)
    set_hostility(unit_id, target_name, current + delta)


def is_hostile_to(unit_id, target_id) -> bool:
    """target에 대한 적대 여부 (적대도 ≥ HOSTILITY_HOSTILE)"""
    target_info = morld.get_unit_info(target_id)
    if not target_info:
        return False
    target_name = target_info.get("name", "")
    return get_hostility(unit_id, target_name) >= HOSTILITY_HOSTILE


def clear_hostility(unit_id, target_name):
    """적대도 초기화"""
    morld.clear_prop(unit_id, f"관계:{target_name}:적대")


def get_hostility_level(unit_id, target_name) -> str:
    """적대도 레벨 문자열"""
    h = get_hostility(unit_id, target_name)
    if h >= HOSTILITY_ATTACK_ON_SIGHT:
        return "attack_on_sight"
    if h >= HOSTILITY_HOSTILE:
        return "hostile"
    if h >= HOSTILITY_ALERT:
        return "alert"
    return "neutral"


# ========================================
# 적대모드 (플레이어 전용)
# ========================================

def is_hostile_mode() -> bool:
    return _hostile_mode


def set_hostile_mode(enabled: bool):
    global _hostile_mode
    _hostile_mode = enabled
    player_id = morld.get_player_id()
    morld.set_unit_prop(player_id, "can:attack", 1 if enabled else 0)
    morld.set_unit_prop(player_id, "can:steal", 1 if enabled else 0)


# ========================================
# 디버프 API
# ========================================

def apply_bleeding(unit_id, duration_hours=None):
    """출혈 적용"""
    if duration_hours is None:
        duration_hours = BLEEDING_DURATION_HOURS
    morld.set_unit_prop(unit_id, "상태:출혈", duration_hours)


def cure_bleeding(unit_id):
    """출혈 치료"""
    morld.clear_prop(unit_id, "상태:출혈")


def apply_slow(unit_id, speed_percent=None, duration_hours=None):
    """둔화 적용 — 둔화:속도 + 이동:부상 재계산"""
    if speed_percent is None:
        speed_percent = SLOW_SPEED_PERCENT
    if duration_hours is None:
        duration_hours = SLOW_DURATION_HOURS
    morld.set_unit_prop(unit_id, "둔화:속도", speed_percent)
    morld.set_unit_prop(unit_id, "상태:둔화", duration_hours)
    _recompute_movement_injury(unit_id)


# ── 독 API ──

def apply_poison(unit_id, duration_hours=None):
    """독 적용"""
    if duration_hours is None:
        duration_hours = POISON_DURATION_HOURS
    morld.set_unit_prop(unit_id, "상태:독", duration_hours)


def cure_poison(unit_id):
    """독 치료"""
    morld.clear_prop(unit_id, "상태:독")


# ── 부위 부상 API ──

def apply_body_injury(unit_id, body_part, duration_hours=None):
    """부위 부상 적용 (몸통은 무효)"""
    if body_part == "몸통":
        return
    if duration_hours is None:
        duration_hours = INJURY_DURATION_HOURS
    prop = f"부상:{body_part}"
    existing = morld.get_unit_prop(unit_id, prop) or 0
    morld.set_unit_prop(unit_id, prop, max(existing, duration_hours))
    if body_part == "다리":
        _recompute_movement_injury(unit_id)


def cure_body_injury(unit_id, body_part=None):
    """부위 부상 치료 (body_part=None이면 전체)"""
    parts = [body_part] if body_part else ["머리", "팔", "다리"]
    for p in parts:
        morld.clear_prop(unit_id, f"부상:{p}")
    _recompute_movement_injury(unit_id)


# ── 마비 API ──

def apply_paralysis(unit_id, duration_hours=None):
    """마비 적용 — 이동 불가 + 전투 불가 (의식 유지)"""
    if duration_hours is None:
        duration_hours = PARALYSIS_DURATION_HOURS
    morld.set_unit_prop(unit_id, "상태:마비", duration_hours)


def cure_paralysis(unit_id):
    """마비 치료"""
    morld.clear_prop(unit_id, "상태:마비")


def is_paralyzed(unit_id):
    """마비 상태 여부"""
    return bool(morld.get_unit_prop(unit_id, "상태:마비"))


# ── 거미줄 API ──

def apply_web_bind(unit_id, duration_hours=None):
    """거미줄 결박 — 이동 불가 (하체 결박과 별개 트래킹)"""
    if duration_hours is None:
        duration_hours = WEB_BIND_DURATION_HOURS
    morld.set_unit_prop(unit_id, "상태:거미줄", duration_hours)


def cure_web_bind(unit_id):
    """거미줄 결박 해제"""
    morld.clear_prop(unit_id, "상태:거미줄")


def is_web_bound(unit_id):
    """거미줄 결박 여부"""
    return bool(morld.get_unit_prop(unit_id, "상태:거미줄"))


def attempt_web_escape(unit_id):
    """거미줄 자력 탈출 — 결박 탈출 공식 재사용"""
    props = morld.get_unit_props(unit_id) or {}
    strength = props.get("근력", 5)
    body_type = props.get("체격", 5)
    hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
    max_hp = morld.get_unit_prop(unit_id, "생존:최대체력") or 100
    hp_ratio = hp / max(1, max_hp)

    power = strength * 2 + body_type * 3 + hp_ratio * 50
    difficulty = WEB_BIND_ESCAPE_DIFFICULTY
    chance = min(0.70, max(0.05, power / (difficulty + power)))

    if random.random() < chance:
        cure_web_bind(unit_id)
        return True
    return False


def _recompute_movement_injury(unit_id):
    """둔화 + 다리 부상 중 최소 속도를 이동:부상에 반영"""
    slow_speed = morld.get_unit_prop(unit_id, "둔화:속도")
    leg_hours = morld.get_unit_prop(unit_id, "부상:다리") or 0
    sources = []
    if slow_speed is not None:
        sources.append(slow_speed)
    if leg_hours > 0:
        sources.append(LEG_INJURY_SPEED)
    if sources:
        morld.set_unit_prop(unit_id, "이동:부상", min(sources))
    else:
        morld.clear_prop(unit_id, "이동:부상")


# ── 엄폐 API ──

def get_cover_bonus(unit_id):
    """웅크리기 + 근처 오브젝트 → 엄폐 보너스 반환

    Returns: {"evasion": int, "damage_reduction": float} or None
    """
    if not morld.get_unit_prop(unit_id, "posture:crouch"):
        return None

    loc = morld.get_unit_location(unit_id)
    if not loc or loc[0] < 0:
        return None

    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return None
    unit_x = unit_info.get("x", 0)

    objects = morld.get_units_at_location(loc[0], loc[1], "object")
    best_cover = None
    best_dist = float('inf')

    for obj_id in (objects or []):
        cover_level = morld.get_unit_prop(obj_id, "cover:level")
        if not cover_level:
            continue
        obj_info = morld.get_unit_info(obj_id)
        if not obj_info:
            continue
        obj_x = obj_info.get("x", 0)
        dist = abs(unit_x - obj_x)
        if dist <= COVER_DISTANCE and dist < best_dist:
            best_dist = dist
            best_cover = cover_level

    if best_cover and best_cover in COVER_BONUS:
        return COVER_BONUS[best_cover]
    return None


# ========================================
# 내구도
# ========================================

def degrade_durability(item_id, amount=1, owner_id=None):
    """내구도 감소. 0이면 장착 해제 + 파손 표시 (인벤토리 유지, 향후 복구 가능)."""
    current = morld.get_unit_prop(item_id, "내구도")
    if current is None:
        return  # 내구도 없는 아이템 (시나리오03 호환)
    new_val = max(0, current - amount)
    morld.set_unit_prop(item_id, "내구도", new_val)
    if new_val == 0:
        morld.set_unit_prop(item_id, "상태:파손", 1)
        item_info = morld.get_item_info(item_id)
        item_name = item_info.get("name", "아이템") if item_info else "아이템"
        if owner_id is not None:
            import equipment
            if equipment.is_equipped(owner_id, item_id):
                equipment.unequip_item(owner_id, item_id)
        morld.add_action_log(f"{item_name}이(가) 파손되었다.")


# ========================================
# 재장전
# ========================================

def reload_weapon(player_id) -> bool:
    """재장전: equip_props에서 탄약타입/장탄수 조회 → 인벤토리 소모 → 현재탄약 설정"""
    from assets.registry import get_or_create_item_id

    all_props = morld.get_actual_props(player_id)
    if not all_props:
        return False

    ammo_type = all_props.get("전투:탄약")
    max_ammo = all_props.get("전투:장탄수", 0)
    if not ammo_type or max_ammo <= 0:
        morld.add_action_log("장전할 무기가 없다.")
        return False

    # 잼 해제
    morld.clear_prop(player_id, "상태:잼")

    # 탄약 보유량 확인
    ammo_item_id = get_or_create_item_id(ammo_type)
    if not ammo_item_id:
        morld.add_action_log("탄약이 없다.")
        return False

    inventory = morld.get_inventory(player_id)
    owned = inventory.get(ammo_item_id, 0)
    if owned <= 0:
        morld.add_action_log("탄약이 없다.")
        return False

    # 현재 탄약 → 장전
    current = morld.get_unit_prop(player_id, "전투:현재탄약") or 0
    need = max_ammo - current
    if need <= 0:
        morld.add_action_log("이미 장전되어 있다.")
        return False

    load = min(need, owned)
    morld.remove_item(player_id, ammo_item_id, load)
    morld.set_unit_prop(player_id, "전투:현재탄약", current + load)

    morld.add_action_log(f"장전 완료 ({current + load}/{max_ammo}).")
    return True


# ========================================
# 시간 구독 + 리셋
# ========================================

def _tick_debuffs(unit_id, is_player=False):
    """한 유닛의 디버프 1시간 틱 (출혈/독/둔화/부위부상/마비/거미줄)"""
    import survival

    # 출혈 데미지
    bleeding = morld.get_unit_prop(unit_id, "상태:출혈") or 0
    if bleeding > 0:
        survival.add_health(unit_id, -BLEEDING_DAMAGE_PER_HOUR)
        if bleeding - 1 <= 0:
            cure_bleeding(unit_id)
        else:
            morld.set_unit_prop(unit_id, "상태:출혈", bleeding - 1)

        hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
        if hp <= 0:
            if is_player:
                survival._enter_player_faint()
            else:
                survival._enter_faint(unit_id)

    # 독 데미지
    poison = morld.get_unit_prop(unit_id, "상태:독") or 0
    if poison > 0:
        survival.add_health(unit_id, -POISON_DAMAGE_PER_HOUR)
        if poison - 1 <= 0:
            cure_poison(unit_id)
        else:
            morld.set_unit_prop(unit_id, "상태:독", poison - 1)

        hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
        if hp <= 0:
            if is_player:
                survival._enter_player_faint()
            else:
                survival._enter_faint(unit_id)

    # 둔화 회복
    slow_remaining = morld.get_unit_prop(unit_id, "상태:둔화") or 0
    if slow_remaining > 0:
        if slow_remaining - 1 <= 0:
            morld.clear_prop(unit_id, "상태:둔화")
            morld.clear_prop(unit_id, "둔화:속도")
            _recompute_movement_injury(unit_id)
        else:
            morld.set_unit_prop(unit_id, "상태:둔화", slow_remaining - 1)

    # 부위 부상 자연 회복
    for part in ("머리", "팔", "다리"):
        remaining = morld.get_unit_prop(unit_id, f"부상:{part}") or 0
        if remaining > 0:
            if remaining - 1 <= 0:
                morld.clear_prop(unit_id, f"부상:{part}")
                if part == "다리":
                    _recompute_movement_injury(unit_id)
            else:
                morld.set_unit_prop(unit_id, f"부상:{part}", remaining - 1)

    # 마비 회복
    paralysis = morld.get_unit_prop(unit_id, "상태:마비") or 0
    if paralysis > 0:
        if paralysis - 1 <= 0:
            cure_paralysis(unit_id)
        else:
            morld.set_unit_prop(unit_id, "상태:마비", paralysis - 1)

    # 거미줄 결박 자연 해제
    web = morld.get_unit_prop(unit_id, "상태:거미줄") or 0
    if web > 0:
        if web - 1 <= 0:
            cure_web_bind(unit_id)
        else:
            morld.set_unit_prop(unit_id, "상태:거미줄", web - 1)


def _on_time_elapsed(millis):
    """매 1시간: 적대도 감소 + 디버프 틱 (출혈/독/둔화/부위부상)"""
    hours = millis / 3_600_000
    if hours < 1:
        return

    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "") if player_info else ""

    try:
        import think
        agents = think.get_all_agents()
    except (ImportError, AttributeError):
        agents = {}

    for unit_id in agents:
        # 적대도 감소 (매 시간)
        if player_name:
            hostility = get_hostility(unit_id, player_name)
            if hostility > 0:
                modify_hostility(unit_id, player_name, -HOSTILITY_DECAY_PER_HOUR)

        _tick_debuffs(unit_id, is_player=False)

    # 플레이어 디버프
    _tick_debuffs(player_id, is_player=True)


def reset():
    """챕터 전환: 모듈 상태 초기화"""
    global _hostile_mode
    _hostile_mode = False
    GLOBAL_FACTION_RELATIONS.clear()
    REGION_FACTION_RELATIONS.clear()


# 모듈 로드 시 이벤트 구독 (1시간 간격)
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)
