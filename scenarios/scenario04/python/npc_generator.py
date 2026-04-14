# npc_generator.py - S04 랜덤 NPC 생성 시스템
#
# 마을 여관에 동적으로 NPC 생성/소멸.
# 생활형 NPC: 외형/성격만, 가만히 있다가 소멸
# 파티 후보 NPC: 전투 스타일/스킬/기벽 포함, 파티 합류 가능
#
# 1시간마다 체류 시간 감소. 만료 시 소멸.
# 하루(게임 내) 1~2명 출현. 최대 동시 체류 5명.

import morld
import random
from events import subscribe_time_elapsed
import character_randomizer as randomizer

# === 상수 ===

MAX_VILLAGE_NPC = 5           # 최대 동시 체류
SPAWN_CHECK_INTERVAL = 3600000  # 1시간마다 스폰 체크
SPAWN_CHANCE_PER_HOUR = 0.80  # 시간당 스폰 확률 (테스트용 — 원래 0.08)
DEFAULT_STAY_HOURS = 48       # 기본 체류 시간 (48시간)

# 여관 위치 (Region 0, Location 1)
INN_REGION = 0
INN_LOCATION = 1

# 마을 체류 NPC가 돌아다닐 수 있는 장소 (region, location)
# 여관 / 광장 / 술집 / 잡화점
ROAM_LOCATIONS = [
    (0, 1),  # 여관
    (0, 0),  # 광장
    (0, 4),  # 술집
    (0, 3),  # 잡화점
]
ROAM_CHANCE_PER_HOUR = 0.30  # 시간당 이동 확률

# === 상태 ===

_village_npcs = {}  # unit_id -> {name, type, stay_remaining, ...}
_accumulated_millis = 0
_next_id_counter = 1000  # NPC unique_id 카운터


def reset():
    """챕터 전환 시 리셋 + 이벤트 재구독"""
    global _accumulated_millis, _next_id_counter
    _village_npcs.clear()
    _accumulated_millis = 0
    _next_id_counter = 1000
    # event_core.reset() 이후 재구독 필요
    subscribe_time_elapsed(_on_time_elapsed, min_interval=SPAWN_CHECK_INTERVAL)


def _on_time_elapsed(millis: int):
    """시간 경과: 체류 시간 감소 + 스폰 체크"""
    global _accumulated_millis
    _accumulated_millis += millis

    hours = _accumulated_millis // 3600000
    if hours < 1:
        return
    _accumulated_millis %= 3600000

    for _ in range(hours):
        _update_stay_times()
        _update_roam()
        _check_spawn()


def _update_roam():
    """파티 미소속 체류 NPC의 간이 랜덤 이동.

    파티 합류 시 remove_from_village로 _village_npcs에서 빠지므로
    여기 남아있는 유닛은 모두 idle 상태로 간주.
    """
    for unit_id in _village_npcs:
        if random.random() >= ROAM_CHANCE_PER_HOUR:
            continue
        region, location = random.choice(ROAM_LOCATIONS)
        x = random.randint(20, 150)
        morld.set_unit_location(unit_id, region, location, x=x)


def _update_stay_times():
    """체류 시간 1시간 감소, 만료 시 소멸"""
    expired = []
    for unit_id, info in _village_npcs.items():
        info["stay_remaining"] -= 1
        if info["stay_remaining"] <= 0:
            expired.append(unit_id)

    for unit_id in expired:
        info = _village_npcs.pop(unit_id)
        morld.remove_unit(unit_id)
        print(f"[npc_gen] NPC departed: {info['name']} (id={unit_id})")


def _check_spawn():
    """스폰 확률 체크"""
    if len(_village_npcs) >= MAX_VILLAGE_NPC:
        return

    if random.random() < SPAWN_CHANCE_PER_HOUR:
        _spawn_random_npc()


def _spawn_random_npc():
    """랜덤 NPC 1명 생성"""
    global _next_id_counter

    # 타입 결정 (60% 파티 후보, 40% 생활형)
    is_party_candidate = random.random() < 0.6

    existing_names = {info["name"] for info in _village_npcs.values()}

    # unique_id 생성
    unique_id = f"npc_{_next_id_counter}"
    _next_id_counter += 1

    # 랜더마이저로 이름만 먼저 뽑아서 add_character에 사용
    is_male = randomizer.roll_gender()
    name = randomizer.roll_name(is_male, avoid=existing_names)

    # C# 측 유닛 생성
    unit_id = morld.create_id("character")
    morld.add_character(unit_id, name, INN_REGION, INN_LOCATION, x=random.randint(10, 180))

    # 공용 Character 인스턴스 등록 (focus 액션 제공용)
    from assets.base import Character
    from assets.characters import register_instance
    instance = Character()
    instance.instance_id = unit_id
    instance.name = name
    register_instance(unit_id, instance)

    # 랜덤 속성 적용 (성별은 위에서 결정한 값 고정)
    applied = randomizer.apply_random_character(
        unit_id,
        is_male=is_male,
        assign_class=is_party_candidate,
        assign_quirks=True,
    )

    # 파티 후보 플래그
    if is_party_candidate:
        morld.set_unit_prop(unit_id, "파티후보", 1)

    # 체류 시간
    stay_hours = DEFAULT_STAY_HOURS + random.randint(-12, 24)

    # 소지금 (랜덤)
    import economy
    economy.init_money(unit_id, random.randint(5000, 30000))

    # 시스템 초기화
    import survival, morale, trust
    survival.register_character(unit_id)
    morale.set_morale(unit_id, morale.MORALE_DEFAULT)
    trust.set_trust(unit_id, trust.TRUST_DEFAULT)

    # 등록
    _village_npcs[unit_id] = {
        "name": name,
        "unique_id": unique_id,
        "type": "party_candidate" if is_party_candidate else "civilian",
        "stay_remaining": stay_hours,
        "class": applied["class"],
    }

    npc_type = "파티 후보" if is_party_candidate else "생활형"
    class_str = f", 클래스={applied['class']}" if applied["class"] else ""
    print(f"[npc_gen] NPC spawned: {name} ({npc_type}{class_str}, "
          f"체류 {stay_hours}h, id={unit_id})")


# === 조회 API ===

def get_village_npcs() -> dict:
    """현재 마을 체류 NPC 목록"""
    return _village_npcs.copy()


def get_party_candidates() -> list:
    """파티 후보 NPC 목록"""
    return [
        {"unit_id": uid, **info}
        for uid, info in _village_npcs.items()
        if info["type"] == "party_candidate"
    ]


def remove_from_village(unit_id: int):
    """마을에서 NPC 제거 (파티 합류 시 등)"""
    if unit_id in _village_npcs:
        del _village_npcs[unit_id]


# 이벤트 구독
subscribe_time_elapsed(_on_time_elapsed, min_interval=SPAWN_CHECK_INTERVAL)
