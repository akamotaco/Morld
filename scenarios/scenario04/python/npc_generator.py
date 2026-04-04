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
from assets.base import Character
from assets.registry import register_character

# === 상수 ===

MAX_VILLAGE_NPC = 5           # 최대 동시 체류
SPAWN_CHECK_INTERVAL = 3600000  # 1시간마다 스폰 체크
SPAWN_CHANCE_PER_HOUR = 0.08  # 시간당 스폰 확률 (~2명/일)
DEFAULT_STAY_HOURS = 48       # 기본 체류 시간 (48시간)

# 여관 위치 (Region 0, Location 1)
INN_REGION = 0
INN_LOCATION = 1

# === 이름풀 (임시, 세계관 확정 후 교체) ===

_NAME_POOL_MALE = [
    "카이", "렌", "아키", "진", "하루", "소라", "유진", "태호",
    "마루", "건우", "세진", "도윤", "현", "리오", "준",
]

_NAME_POOL_FEMALE = [
    "미카", "사나", "유나", "하나", "리나", "세이", "아야", "나츠",
    "수아", "지안", "서연", "다은", "채원", "하윤", "예린",
]

# 성격 풀
_PERSONALITY_POOL = [
    "호쾌", "과묵", "조심성", "낙천적", "신경질", "차분", "수다쟁이",
    "의심많은", "충직", "탐욕", "겁쟁이", "용감", "영악", "순진",
]

# 클래스 목록
_CLASS_POOL = ["척후", "타격수", "사수", "방패잡이", "약사", "기술자", "거간꾼"]
_CLASS_RARE = ["오염술사"]  # 희귀 (낮은 확률)

# 선천 기벽 풀 (숨겨진 상태로 부여)
_QUIRK_POOL_MINOR = ["잠꼬대", "코골이", "편식", "수집벽", "혼잣말"]
_QUIRK_POOL_MODERATE = ["도벽", "대식", "겁쟁이", "의심병"]
_QUIRK_POOL_POSITIVE = ["충직", "자기희생"]

# === 상태 ===

_village_npcs = {}  # unit_id -> {name, type, stay_remaining, ...}
_accumulated_millis = 0
_next_id_counter = 1000  # NPC unique_id 카운터


def reset():
    """챕터 전환 시 리셋"""
    global _accumulated_millis, _next_id_counter
    _village_npcs.clear()
    _accumulated_millis = 0
    _next_id_counter = 1000


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
        _check_spawn()


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

    # 성별
    is_male = random.random() < 0.5
    name_pool = _NAME_POOL_MALE if is_male else _NAME_POOL_FEMALE
    name = random.choice(name_pool)

    # 중복 이름 방지
    existing_names = {info["name"] for info in _village_npcs.values()}
    attempts = 0
    while name in existing_names and attempts < 10:
        name = random.choice(name_pool)
        attempts += 1

    # 성격
    personality = random.choice(_PERSONALITY_POOL)

    # 스탯 (랜덤 범위)
    stats = _generate_stats()

    # 클래스 (파티 후보만)
    npc_class = None
    if is_party_candidate:
        if random.random() < 0.05:  # 5% 확률로 희귀 클래스
            npc_class = random.choice(_CLASS_RARE)
        else:
            npc_class = random.choice(_CLASS_POOL)

    # 선천 기벽 (0~2개, 숨겨진 상태)
    quirks = _generate_quirks()

    # 체류 시간
    stay_hours = DEFAULT_STAY_HOURS + random.randint(-12, 24)

    # unique_id 생성
    unique_id = f"npc_{_next_id_counter}"
    _next_id_counter += 1

    # C# 측 유닛 생성
    unit_id = morld.create_id("character")
    morld.add_character(unit_id, name, INN_REGION, INN_LOCATION, x=random.randint(10, 180))

    # props 설정
    morld.set_unit_prop(unit_id, "성격", personality)
    morld.set_unit_prop(unit_id, "성별", "남" if is_male else "여")
    morld.set_unit_prop(unit_id, "스탯:근력", stats["str"])
    morld.set_unit_prop(unit_id, "스탯:민첩", stats["agi"])
    morld.set_unit_prop(unit_id, "스탯:체력", stats["vit"])
    morld.set_unit_prop(unit_id, "스탯:정신", stats["mnd"])

    if npc_class:
        morld.set_unit_prop(unit_id, "클래스", npc_class)

    if is_party_candidate:
        morld.set_unit_prop(unit_id, "파티후보", 1)

    # 기벽 (숨겨진 prop)
    for i, quirk in enumerate(quirks):
        morld.set_unit_prop(unit_id, f"기벽:선천:{i}", quirk)
        morld.set_unit_prop(unit_id, f"기벽:발각:{i}", 0)  # 0=미발각

    # 소지금 (랜덤)
    import economy
    economy.init_money(unit_id, random.randint(5000, 30000))

    # 등록
    _village_npcs[unit_id] = {
        "name": name,
        "unique_id": unique_id,
        "type": "party_candidate" if is_party_candidate else "civilian",
        "stay_remaining": stay_hours,
        "class": npc_class,
    }

    npc_type = "파티 후보" if is_party_candidate else "생활형"
    class_str = f", 클래스={npc_class}" if npc_class else ""
    print(f"[npc_gen] NPC spawned: {name} ({npc_type}{class_str}, "
          f"체류 {stay_hours}h, id={unit_id})")


def _generate_stats() -> dict:
    """랜덤 스탯 생성 (8~15 범위)"""
    return {
        "str": random.randint(8, 15),
        "agi": random.randint(8, 15),
        "vit": random.randint(8, 15),
        "mnd": random.randint(8, 15),
    }


def _generate_quirks() -> list:
    """선천 기벽 0~2개 생성"""
    quirks = []
    count = random.choices([0, 1, 2], weights=[50, 35, 15])[0]

    pool = _QUIRK_POOL_MINOR + _QUIRK_POOL_MODERATE + _QUIRK_POOL_POSITIVE
    for _ in range(count):
        q = random.choice(pool)
        if q not in quirks:
            quirks.append(q)
    return quirks


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
