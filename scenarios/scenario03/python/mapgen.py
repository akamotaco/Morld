# mapgen.py — 동적 맵 생성 (시나리오03)
#
# common dungeon.generator를 활용한 탐사 지역 생성기.
# BSP 생성은 공통 모듈, 타입 할당 + 콘텐츠 배치는 시나리오 전용.

import random
import morld
from dungeon.generator import generate_dungeon, generate_bridges, Room, Corridor


# ========================================
# 난이도 설정
# ========================================

class DifficultyConfig:
    __slots__ = ("room_count_min", "room_count_max",
                 "enemy_chance", "loot_chance",
                 "min_room_size", "map_width", "map_height",
                 "max_depth", "max_bridges")

    def __init__(self, room_count_min=5, room_count_max=8,
                 enemy_chance=0.3, loot_chance=0.4,
                 min_room_size=100, map_width=800, map_height=600,
                 max_depth=4, max_bridges=1):
        self.room_count_min = room_count_min
        self.room_count_max = room_count_max
        self.enemy_chance = enemy_chance
        self.loot_chance = loot_chance
        self.min_room_size = min_room_size
        self.map_width = map_width
        self.map_height = map_height
        self.max_depth = max_depth
        self.max_bridges = max_bridges


DIFFICULTY_PRESETS = {
    "easy":   DifficultyConfig(5, 8, 0.2, 0.5, 120, 800, 600, 3, 1),
    "normal": DifficultyConfig(8, 12, 0.4, 0.4, 100, 1000, 800, 4, 2),
    "hard":   DifficultyConfig(12, 18, 0.6, 0.3, 80, 1200, 1000, 5, 3),
}


# ========================================
# 탐사 데이터
# ========================================

_expeditions = {}  # {region_id: {"rooms", "corridors", "bridges"}}


def reset():
    """모듈 상태 초기화 (챕터 전환/테스트 간 격리 — pi-world reset 계약)"""
    _expeditions.clear()

THREAT_CODES = ["P", "R", "B", "W"]
ROOM_NAMES = {
    "entrance": "입구",
    "normal": "구역",
    "objective": "목표 지점",
}


# ========================================
# 맵 생성 API
# ========================================

def generate_expedition(region_id, difficulty="easy", seed=None):
    """탐사 지역 동적 생성

    Args:
        region_id: 할당할 Region ID (예: 100)
        difficulty: "easy" / "normal" / "hard"
        seed: 랜덤 시드 (None = 랜덤)

    Returns:
        (rooms, corridors, bridges)
    """
    cfg = DIFFICULTY_PRESETS.get(difficulty, DIFFICULTY_PRESETS["easy"])

    # 1. BSP 생성 (공통 모듈)
    rooms, corridors = generate_dungeon(
        width=cfg.map_width,
        height=cfg.map_height,
        min_size=cfg.min_room_size,
        max_depth=cfg.max_depth,
        seed=seed,
    )

    # 2. 타입 할당 (시나리오 03 전용)
    if rooms:
        rooms[0].room_type = "entrance"
        rooms[-1].room_type = "objective"

    # 3. Bridge 생성 (공통 모듈)
    bridges = generate_bridges(
        rooms, corridors,
        max_bridges=cfg.max_bridges,
        max_distance=300,
        seed=(seed + 99) if seed else None,
    )

    # 4. morld에 Region/Location/Gate 생성
    morld.add_region(region_id, f"탐사구역-{region_id}")

    for room in rooms:
        name = ROOM_NAMES.get(room.room_type, f"구역-{room.id}")
        morld.add_location(
            region_id, room.id, name,
            0, True, None, None, None,
            "line", room.w,
        )

    gate_id = 0
    for conn in corridors:
        room_a = next(r for r in rooms if r.id == conn.room_a)
        room_b = next(r for r in rooms if r.id == conn.room_b)

        morld.add_gate(
            region_id, conn.room_a, gate_id,
            room_a.w, region_id, conn.room_b, 0,
        )
        gate_id += 1
        morld.add_gate(
            region_id, conn.room_b, gate_id,
            0, region_id, conn.room_a, room_b.w,
        )
        gate_id += 1

    # Bridge도 Gate로 등록
    for bridge in bridges:
        room_a = next(r for r in rooms if r.id == bridge.room_a)
        room_b = next(r for r in rooms if r.id == bridge.room_b)

        morld.add_gate(
            region_id, bridge.room_a, gate_id,
            room_a.w // 2, region_id, bridge.room_b, room_b.w // 2,
        )
        gate_id += 1
        morld.add_gate(
            region_id, bridge.room_b, gate_id,
            room_b.w // 2, region_id, bridge.room_a, room_a.w // 2,
        )
        gate_id += 1

    # 5. 콘텐츠 배치
    _populate_rooms(rooms, cfg)

    # 저장
    _expeditions[region_id] = {
        "rooms": rooms,
        "corridors": corridors,
        "bridges": bridges,
    }

    print(f"[mapgen] Generated expedition R{region_id}: "
          f"{len(rooms)} rooms, {len(corridors)} corridors, "
          f"{len(bridges)} bridges (difficulty={difficulty})")

    return rooms, corridors, bridges


def _populate_rooms(rooms, cfg):
    """방에 위협/전리품 배치"""
    for room in rooms:
        if room.room_type == "entrance":
            continue

        if random.random() < cfg.enemy_chance:
            room.room_type = room.room_type  # 유지
            # TODO: 실제 몬스터 스폰

        if random.random() < cfg.loot_chance:
            pass  # TODO: 실제 아이템 배치


def cleanup_expedition(region_id):
    """탐사 완료 후 Region 정리"""
    data = _expeditions.pop(region_id, None)
    if not data:
        return

    rooms = data["rooms"]
    for room in rooms:
        units = morld.get_units_at_location(region_id, room.id)
        for uid in units:
            morld.remove_unit(uid)
        morld.remove_location(region_id, room.id)

    print(f"[mapgen] Cleaned up expedition R{region_id}")


def get_expedition_data(region_id):
    """탐사 데이터 조회"""
    return _expeditions.get(region_id)
