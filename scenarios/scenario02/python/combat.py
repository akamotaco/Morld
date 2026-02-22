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
# 각 세력이 적대하는 세력 목록 (양방향 체크)
FACTION_HOSTILITY = {
    "주민":   set(),               # NPC/플레이어 — BATTLE_BEHAVIOR로 판단
    "늑대":   {"주민", "거미"},     # 사람+거미 공격
    "거미":   {"주민", "늑대"},     # 사람+늑대 공격
    "박쥐":   {"주민"},             # 사람만 공격
}
DEFAULT_FACTION = "주민"           # 세력 미설정 시 기본값


def is_faction_hostile(faction_a, faction_b):
    """두 세력이 적대 관계인지 (양방향 체크)"""
    a = faction_a or DEFAULT_FACTION
    b = faction_b or DEFAULT_FACTION
    if a == b:
        return False
    return (b in FACTION_HOSTILITY.get(a, set())
            or a in FACTION_HOSTILITY.get(b, set()))


def is_creature_unit(unit_id):
    """생물(Creature) 유닛인지 — 세력이 주민이 아닌 경우"""
    faction = morld.get_unit_prop(unit_id, "전투:세력")
    return faction is not None and faction != DEFAULT_FACTION


DEFAULT_AGGRO_RANGE = 100
DEFAULT_TERRITORY_RANGE = 50

# ── 디버프 ──
BLEEDING_DAMAGE_PER_HOUR = 3
BLEEDING_CHANCE_ON_CRIT = 50
BLEEDING_DURATION_HOURS = 3
SLOW_DURATION_HOURS = 2
SLOW_SPEED_PERCENT = 50

# ── 탄약 ──
RELOAD_DURATION = 5_000
JAM_BASE_CHANCE = 3

# ── 은신 기습 ──
STEALTH_CRIT_BONUS = 30


# ========================================
# 모듈 상태
# ========================================

_hostile_mode = False


# ========================================
# 스탯 조회
# ========================================

def get_combat_stat(unit_id: int, stat_name: str):
    """전투 스탯 조회 (base prop + equip_props 합산)"""
    all_props = morld.get_actual_props(unit_id)
    if all_props and stat_name in all_props:
        return all_props[stat_name]
    return DEFAULT_STATS.get(stat_name, 0)


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
    """명중률 = attacker_명중 - target_회피, clamp(5, 95)"""
    accuracy = get_combat_stat(attacker_id, "전투:명중")
    evasion = get_combat_stat(target_id, "전투:회피")
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
    """공식: max(1, atk - def//2) × variance × crit_mult"""
    atk = get_combat_stat(attacker_id, "전투:공격력")
    defense = get_combat_stat(target_id, "전투:방어력")

    base = max(MIN_DAMAGE, atk - defense // 2)

    # ±10% variance
    variance = 1.0 + random.uniform(-DAMAGE_VARIANCE, DAMAGE_VARIANCE)
    damage = base * variance

    if is_crit:
        damage *= CRIT_MULTIPLIER

    return max(MIN_DAMAGE, int(damage))


# ========================================
# 데미지 적용
# ========================================

def apply_damage(target_id: int, damage: int, attacker_id: int = None):
    """HP 감소 + 기절 판정

    survival.add_health()는 기절을 자동 트리거하지 않으므로
    HP가 0이 되면 명시적으로 기절 함수를 호출한다.
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

    return fainted


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
            durability = morld.get_unit_prop(attacker_id, "내구도") or 100
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
    damage = calculate_damage(attacker_id, target_id, is_crit)
    fainted = apply_damage(target_id, damage, attacker_id)
    target_hp = morld.get_unit_prop(target_id, "생존:체력") or 0

    result["hit"] = True
    result["crit"] = crit
    result["damage"] = damage
    result["target_hp"] = target_hp
    result["target_fainted"] = fainted

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

    # 내구도 감소
    degrade_durability(attacker_id)

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

        # 이미 전투 중이면 스킵
        if agent._memory.get("combat_phase") is not None:
            continue

        # 호감도 체크
        threshold = behavior.get("join_threshold", 0)
        affection = morld.get_unit_prop(unit_id, f"관계:{player_name}:호감") or 0
        if affection >= threshold:
            joinable.append(unit_id)

    return joinable


def can_fight(unit_id: int) -> bool:
    """전투 가능 상태 확인 (HP > 0, 기절 아님, 사망 아님)"""
    import survival

    hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
    if hp <= 0:
        return False

    if survival.is_npc_fainted(unit_id):
        return False

    if morld.get_unit_prop(unit_id, "상태:사망"):
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
    """둔화 적용 — 이동:부상 prop (Unit prop, actualProps에서 읽힘)"""
    if speed_percent is None:
        speed_percent = SLOW_SPEED_PERCENT
    if duration_hours is None:
        duration_hours = SLOW_DURATION_HOURS
    morld.set_unit_prop(unit_id, "이동:부상", speed_percent)
    morld.set_unit_prop(unit_id, "상태:둔화", duration_hours)


# ========================================
# 내구도
# ========================================

def degrade_durability(item_id, amount=1):
    """내구도 감소. 0이면 상태:파손 설정."""
    current = morld.get_unit_prop(item_id, "내구도")
    if current is None:
        return  # 내구도 없는 아이템 (시나리오03 호환)
    new_val = max(0, current - amount)
    morld.set_unit_prop(item_id, "내구도", new_val)
    if new_val == 0:
        morld.set_unit_prop(item_id, "상태:파손", 1)


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

def _on_time_elapsed(millis):
    """매 1시간: 적대도 감소 + 출혈 데미지 + 둔화 회복"""
    import survival

    hours = millis / 3_600_000
    if hours < 1:
        return

    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "") if player_info else ""

    # 모든 캐릭터에 대해 처리
    # get_units_at_location 대신 전역 처리가 필요하지만,
    # 현재 API 한계상 think 에이전트에 등록된 NPC들만 처리
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

        # 출혈 데미지
        bleeding = morld.get_unit_prop(unit_id, "상태:출혈") or 0
        if bleeding > 0:
            survival.add_health(unit_id, -BLEEDING_DAMAGE_PER_HOUR)
            new_bleeding = bleeding - 1
            if new_bleeding <= 0:
                cure_bleeding(unit_id)
            else:
                morld.set_unit_prop(unit_id, "상태:출혈", new_bleeding)

            # 출혈로 HP 0 → 기절
            hp = morld.get_unit_prop(unit_id, "생존:체력") or 0
            if hp <= 0:
                survival._enter_faint(unit_id)

        # 둔화 회복
        slow_remaining = morld.get_unit_prop(unit_id, "상태:둔화") or 0
        if slow_remaining > 0:
            new_slow = slow_remaining - 1
            if new_slow <= 0:
                morld.clear_prop(unit_id, "상태:둔화")
                morld.clear_prop(unit_id, "이동:부상")
            else:
                morld.set_unit_prop(unit_id, "상태:둔화", new_slow)

    # 플레이어 출혈/둔화도 처리
    bleeding = morld.get_unit_prop(player_id, "상태:출혈") or 0
    if bleeding > 0:
        survival.add_health(player_id, -BLEEDING_DAMAGE_PER_HOUR)
        new_bleeding = bleeding - 1
        if new_bleeding <= 0:
            cure_bleeding(player_id)
        else:
            morld.set_unit_prop(player_id, "상태:출혈", new_bleeding)

        hp = morld.get_unit_prop(player_id, "생존:체력") or 0
        if hp <= 0:
            survival._enter_player_faint()

    slow_remaining = morld.get_unit_prop(player_id, "상태:둔화") or 0
    if slow_remaining > 0:
        new_slow = slow_remaining - 1
        if new_slow <= 0:
            morld.clear_prop(player_id, "상태:둔화")
            morld.clear_prop(player_id, "이동:부상")
        else:
            morld.set_unit_prop(player_id, "상태:둔화", new_slow)


def reset():
    """챕터 전환: 모듈 상태 초기화"""
    global _hostile_mode
    _hostile_mode = False


# 모듈 로드 시 이벤트 구독 (1시간 간격)
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)
