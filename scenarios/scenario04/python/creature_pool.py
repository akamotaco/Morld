# creature_pool.py — 층별 생물 풀 + 적 데이터 생성
#
# dungeon.py에서 방 진입 시 호출하여 적 그룹을 생성.
# encounter_handler.start_encounter()에 전달할 enemy_data를 생산.
#
# 참조: docs/creature-system.md

import random
from assets.characters.creatures import (
    BlindRat, Fangdog, Petraspider, Slimeworm,
    GreaterPetraspider, Plaguedog,
)

# ========================================
# 층별 생물 풀
# ========================================
# weight: 출현 가중치 (높을수록 자주)
# elite: True면 리스폰 없음, 방당 1회만
# boss: True면 보스 방 전용

FLOOR_POOLS = {
    1: [
        {"class": BlindRat,      "weight": 40},
        {"class": Fangdog,       "weight": 30},
        {"class": Slimeworm,     "weight": 20},
        {"class": Petraspider,   "weight": 10},
    ],
    2: [
        {"class": BlindRat,      "weight": 30},
        {"class": Fangdog,       "weight": 35},
        {"class": Slimeworm,     "weight": 15},
        {"class": Petraspider,   "weight": 15},
        {"class": GreaterPetraspider, "weight": 5},
    ],
    3: [
        {"class": BlindRat,      "weight": 25},
        {"class": Fangdog,       "weight": 35},
        {"class": Petraspider,   "weight": 20},
        {"class": Slimeworm,     "weight": 10},
        {"class": GreaterPetraspider, "weight": 10},
    ],
    4: [
        {"class": Fangdog,       "weight": 35},
        {"class": Petraspider,   "weight": 25},
        {"class": BlindRat,      "weight": 15},
        {"class": Slimeworm,     "weight": 10},
        {"class": GreaterPetraspider, "weight": 15},
    ],
    5: [
        {"class": Fangdog,       "weight": 30},
        {"class": Petraspider,   "weight": 30},
        {"class": BlindRat,      "weight": 15},
        {"class": GreaterPetraspider, "weight": 20},
        {"class": Slimeworm,     "weight": 5},
    ],
}

# 보스 매핑
FLOOR_BOSSES = {
    5: Plaguedog,
}


# ========================================
# 적 데이터 생성
# ========================================

def generate_encounter(floor, is_boss_room=False):
    """방의 적 그룹 생성 → encounter_handler용 enemy_data 리스트

    Args:
        floor: 던전 층
        is_boss_room: 보스 방 여부

    Returns:
        list[dict] — [{"name", "stats", "skills", "exp", "drop_table", ...}, ...]
        또는 None (생물 없음)
    """
    # 보스 방
    if is_boss_room:
        boss_cls = FLOOR_BOSSES.get(floor)
        if boss_cls:
            return [_make_enemy_data(boss_cls, floor)]
        # 보스 미정의 → 일반 전투
        return _generate_normal_encounter(floor)

    return _generate_normal_encounter(floor)


def _generate_normal_encounter(floor):
    """일반 방 전투 생성"""
    pool = FLOOR_POOLS.get(floor)
    if not pool:
        # 풀 미정의 → 가장 가까운 하위 층 풀 사용
        for f in range(floor - 1, 0, -1):
            if f in FLOOR_POOLS:
                pool = FLOOR_POOLS[f]
                break
    if not pool:
        return None

    # 가중치 랜덤 선택
    entry = _weighted_random(pool)
    cls = entry["class"]

    # 출현 수
    if cls.behavior == "swarm":
        count = random.randint(*cls.spawn_count)
    else:
        count = 1

    # 층 보정 (깊을수록 강함)
    floor_modifier = 1.0 + (floor - 1) * 0.05

    enemies = []
    for _ in range(count):
        enemies.append(_make_enemy_data(cls, floor, floor_modifier))

    return enemies


def _make_enemy_data(cls, floor, floor_modifier=1.0):
    """Creature 클래스 → encounter_handler용 dict 변환"""
    props = cls.props if hasattr(cls, 'props') and cls.props else {}

    base_hp = props.get("생존:체력", 30)
    max_hp = props.get("생존:최대체력", base_hp)
    attack = props.get("전투:공격력", 8)
    defense = props.get("전투:방어력", 4)

    # 층 보정 적용
    scaled_hp = int(max_hp * floor_modifier)
    scaled_attack = int(attack * floor_modifier)
    scaled_defense = int(defense * floor_modifier)

    stats = {
        "hp": scaled_hp,
        "max_hp": scaled_hp,
        "str": cls.base_str,
        "agi": cls.base_agi,
        "vit": cls.base_vit,
        "mnd": cls.base_mnd,
        "ap_max": 2,
        "attack": scaled_attack,
        "defense": scaled_defense,
    }

    return {
        "name": cls.name,
        "stats": stats,
        "skills": [],
        "exp": cls.exp,
        "drop_table": cls.drop_table,
        "combat_lines": cls.combat_lines,
        "behavior": cls.behavior,
        "erosion_on_hit": cls.erosion_on_hit,
        "respawnable": cls.respawnable,
        "is_elite": cls.is_elite,
    }


def _weighted_random(pool):
    """가중치 랜덤 선택"""
    total = sum(e["weight"] for e in pool)
    r = random.random() * total
    cumulative = 0
    for entry in pool:
        cumulative += entry["weight"]
        if r <= cumulative:
            return entry
    return pool[-1]


# ========================================
# 리스폰 관리
# ========================================

# {(floor, room_id): {"slots": [...], "elite_cleared": bool}}
_room_state = {}

RESPAWN_INTERVAL_MS = 10_800_000  # 3시간


def reset():
    """던전 리셋 시 전체 초기화"""
    _room_state.clear()


def init_room(floor, room_id, has_monster, is_boss_room=False):
    """방 초기 몬스터 상태 등록"""
    key = (floor, room_id)
    if has_monster or is_boss_room:
        _room_state[key] = {
            "has_encounter": True,
            "is_boss_room": is_boss_room,
            "alive": True,
            "killed_at": None,
            "elite_cleared": False,
        }
    else:
        _room_state[key] = {
            "has_encounter": False,
        }


def get_encounter(floor, room_id):
    """방 진입 시 조우 판정 → enemy_data 또는 None

    Returns:
        list[dict] 또는 None
    """
    key = (floor, room_id)
    state = _room_state.get(key)
    if not state or not state.get("has_encounter"):
        return None

    if not state["alive"]:
        # 리스폰 체크
        return None  # 리스폰은 check_respawn에서 처리

    # 생성
    enemies = generate_encounter(floor, is_boss_room=state.get("is_boss_room", False))
    return enemies


def mark_cleared(floor, room_id, enemies):
    """전투 승리 후 방 클리어 기록"""
    import morld
    key = (floor, room_id)
    state = _room_state.get(key)
    if not state:
        return

    # 엘리트/보스면 리스폰 불가
    has_non_respawnable = any(not e.get("respawnable", True) for e in enemies)

    if has_non_respawnable:
        state["alive"] = False
        state["killed_at"] = None  # 리스폰 안 함
        state["elite_cleared"] = True
    else:
        time_info = morld.get_time_info()
        current_ms = time_info.get("total_millis", 0) if time_info else 0
        state["alive"] = False
        state["killed_at"] = current_ms


def check_respawn(floor, room_id, current_time_ms):
    """리스폰 체크 — 시간 경과 후 일반 몬스터 부활"""
    key = (floor, room_id)
    state = _room_state.get(key)
    if not state or not state.get("has_encounter"):
        return

    if state["alive"]:
        return  # 이미 살아있음

    if state.get("elite_cleared"):
        return  # 엘리트/보스 — 리스폰 없음

    killed_at = state.get("killed_at")
    if killed_at is None:
        return

    if current_time_ms - killed_at >= RESPAWN_INTERVAL_MS:
        state["alive"] = True
        state["killed_at"] = None
        print(f"[creature_pool] Respawned: floor={floor}, room={room_id}")
