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
# 층별 파티 프리셋
# ========================================
# 각 프리셋은 {"leader": Class, "minions": [(Class, count), ...]} 형태.
# 랜덤 선택으로 파티 구성 결정.
# MAX_PARTY_SIZE(4) 이내로만 정의.

FLOOR_PARTY_PRESETS = {
    1: [
        {"leader": BlindRat,    "minions": [(BlindRat, 2)]},        # 쥐 3마리
        {"leader": Fangdog,     "minions": []},                     # 개 단독
        {"leader": Slimeworm,   "minions": [(BlindRat, 1)]},        # 슬라임+쥐
    ],
    2: [
        {"leader": Fangdog,     "minions": [(BlindRat, 2)]},        # 개+쥐2
        {"leader": BlindRat,    "minions": [(BlindRat, 3)]},        # 쥐 4마리 (풀)
        {"leader": Petraspider, "minions": []},
        {"leader": Slimeworm,   "minions": [(BlindRat, 2)]},
    ],
    3: [
        {"leader": Fangdog,     "minions": [(Fangdog, 1), (BlindRat, 1)]},
        {"leader": Petraspider, "minions": [(Petraspider, 1)]},
        {"leader": GreaterPetraspider, "minions": [(Petraspider, 2)]},  # 엘리트+부하
    ],
    4: [
        {"leader": Fangdog,     "minions": [(Fangdog, 2), (BlindRat, 1)]},
        {"leader": Petraspider, "minions": [(Petraspider, 2)]},
        {"leader": GreaterPetraspider, "minions": [(Fangdog, 2)]},
        {"leader": Slimeworm,   "minions": [(Petraspider, 2)]},
    ],
    5: [
        {"leader": GreaterPetraspider, "minions": [(Petraspider, 3)]},
        {"leader": Fangdog,     "minions": [(Fangdog, 2), (Petraspider, 1)]},
    ],
}

# 보스 파티 (보스 방 전용)
FLOOR_BOSS_PARTIES = {
    5: {"leader": Plaguedog, "minions": [(Fangdog, 2)]},  # 보스+부하2
}


# ========================================
# 적 데이터 생성
# ========================================

def generate_encounter(floor, is_boss_room=False):
    """방의 적 파티 생성 → encounter_handler용 enemy_data 리스트

    Args:
        floor: 던전 층
        is_boss_room: 보스 방 여부

    Returns:
        list[dict] — [{"name", "stats", ..., "is_leader": bool}, ...]
        첫 번째 요소가 파티 리더. 없으면 None.
    """
    if is_boss_room:
        preset = FLOOR_BOSS_PARTIES.get(floor)
        if preset:
            return _build_party_from_preset(preset, floor)
        # 보스 미정의 → 일반 전투
        return _generate_normal_encounter(floor)

    return _generate_normal_encounter(floor)


def _generate_normal_encounter(floor):
    """일반 방 전투 생성 — 파티 프리셋에서 랜덤 선택"""
    presets = FLOOR_PARTY_PRESETS.get(floor)
    if not presets:
        # 프리셋 미정의 → 가장 가까운 하위 층 프리셋 사용
        for f in range(floor - 1, 0, -1):
            if f in FLOOR_PARTY_PRESETS:
                presets = FLOOR_PARTY_PRESETS[f]
                break
    if not presets:
        return None

    preset = random.choice(presets)
    return _build_party_from_preset(preset, floor)


def _build_party_from_preset(preset, floor):
    """프리셋 → enemy_data 리스트. 리더는 첫 요소."""
    floor_modifier = 1.0 + (floor - 1) * 0.05

    leader_cls = preset["leader"]
    members = [_make_enemy_data(leader_cls, floor, floor_modifier, is_leader=True)]

    for minion_cls, count in preset.get("minions", []):
        for _ in range(count):
            members.append(_make_enemy_data(minion_cls, floor, floor_modifier))

    return members


def _make_enemy_data(cls, floor, floor_modifier=1.0, is_leader=False):
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
        "is_leader": is_leader,
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
# 리스폰 관리 (카운트다운 방식)
# ========================================
# on_time_elapsed에서 시간 차감. 0 이하 → 리스폰.

_room_state = {}

RESPAWN_INTERVAL_MS = 10_800_000  # 3시간

def reset():
    """던전 리셋 시 전체 초기화 + 이벤트 재구독"""
    _room_state.clear()
    from events import subscribe_time_elapsed
    subscribe_time_elapsed(_on_time_elapsed, min_interval=60_000)


def init_room(floor, room_id, has_monster, is_boss_room=False):
    """방 초기 몬스터 상태 등록"""
    key = (floor, room_id)
    if has_monster or is_boss_room:
        _room_state[key] = {
            "has_encounter": True,
            "is_boss_room": is_boss_room,
            "alive": True,
            "respawn_remaining": 0,
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
    """전투 승리 후 방 클리어 → 리스폰 카운트다운 시작"""
    key = (floor, room_id)
    state = _room_state.get(key)
    if not state:
        return

    has_non_respawnable = any(not e.get("respawnable", True) for e in enemies)

    if has_non_respawnable:
        state["alive"] = False
        state["respawn_remaining"] = -1  # 리스폰 안 함
        state["elite_cleared"] = True
        print(f"[creature_pool] Elite/Boss cleared: floor={floor}, room={room_id} (no respawn)")
    else:
        state["alive"] = False
        state["respawn_remaining"] = RESPAWN_INTERVAL_MS
        print(f"[creature_pool] Cleared: floor={floor}, room={room_id} (respawn in {RESPAWN_INTERVAL_MS // 60000}min)")


def _on_time_elapsed(millis):
    """시간 경과 → 모든 죽은 방의 리스폰 카운트다운 차감"""
    for key, state in _room_state.items():
        if not state.get("has_encounter"):
            continue
        if state["alive"]:
            continue
        if state.get("elite_cleared"):
            continue

        remaining = state.get("respawn_remaining", 0)
        if remaining <= 0:
            continue

        remaining -= millis
        if remaining <= 0:
            state["alive"] = True
            state["respawn_remaining"] = 0
            print(f"[creature_pool] Respawned: floor={key[0]}, room={key[1]}")
        else:
            state["respawn_remaining"] = remaining
