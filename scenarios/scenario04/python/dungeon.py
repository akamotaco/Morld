# dungeon.py - S04 인스턴트 던전 관리
#
# S02/common의 BSP + Bridge 알고리즘 재활용.
# 점진적 돌파 + 플레이어 실신 시 재편성.
# 20층, 5층마다 구간 전환.

import morld
import random

# === 상수 ===
TOTAL_FLOORS = 20
DUNGEON_ENTRANCE_REGION = 0
DUNGEON_ENTRANCE_LOCATION = 7  # 마을 "던전 입구"
DUNGEON_REGION_BASE = 100      # 던전 Region ID 시작 (100 + floor)

# 층별 기본 오염도
FLOOR_POLLUTION = {
    # 상층 1~5F
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6,
    # 중층 6~10F
    6: 8, 7: 10, 8: 12, 9: 14, 10: 16,
    # 하층 11~15F
    11: 20, 12: 24, 13: 28, 14: 32, 15: 36,
    # 심층 16~20F
    16: 42, 17: 48, 18: 55, 19: 62, 20: 70,
}

# 숏컷 해금 층
SHORTCUT_FLOORS = {5, 10, 15}

# 보스 층
BOSS_FLOORS = {5, 10, 15, 20}

# 꺾기 이벤트 층
TWIST_FLOOR = 10

# === 상태 ===
_current_dungeon = None   # 현재 던전 데이터
_highest_floor = 0        # 도달 최고 층 (실적)
_shortcuts_unlocked = set()  # 해금된 숏컷 층
_twist_triggered = False  # 꺾기 이벤트 발생 여부


def reset():
    """챕터 전환 시 리셋"""
    global _current_dungeon, _highest_floor, _twist_triggered
    _current_dungeon = None
    _highest_floor = 0
    _shortcuts_unlocked.clear()
    _twist_triggered = False


def get_highest_floor() -> int:
    return _highest_floor


def is_shortcut_unlocked(floor: int) -> bool:
    return floor in _shortcuts_unlocked


def is_twist_triggered() -> bool:
    return _twist_triggered


# === 던전 생성/재편성 ===

def generate_dungeon():
    """
    던전 전체 구조 생성 (BSP 사용).
    현재는 심플한 구조. 향후 common/dungeon/generator.py 연동.
    """
    global _current_dungeon

    _current_dungeon = {
        "floors": {},
        "seed": random.randint(0, 999999),
    }

    for floor in range(1, TOTAL_FLOORS + 1):
        _current_dungeon["floors"][floor] = _generate_floor(floor)

    # 숏컷 리셋
    _shortcuts_unlocked.clear()

    print(f"[dungeon] Generated dungeon (seed={_current_dungeon['seed']}, "
          f"{TOTAL_FLOORS} floors)")


def _generate_floor(floor: int) -> dict:
    """
    층 생성 (심플 버전).
    향후 BSP + Bridge로 교체.
    """
    # 방 개수: 상층 3~5, 중층 5~7, 하층 6~8, 심층 7~10
    if floor <= 5:
        room_count = random.randint(3, 5)
    elif floor <= 10:
        room_count = random.randint(5, 7)
    elif floor <= 15:
        room_count = random.randint(6, 8)
    else:
        room_count = random.randint(7, 10)

    rooms = []
    for i in range(room_count):
        # 방 크기 (length): 좁은/중간/넓은
        size = random.choices(
            ["narrow", "medium", "wide"],
            weights=[40, 40, 20],
            k=1
        )[0]
        length = {"narrow": 100, "medium": 250, "wide": 500}[size]

        rooms.append({
            "id": i,
            "name": f"{floor}F-{i}",
            "length": length,
            "size": size,
            "pollution": FLOOR_POLLUTION.get(floor, 10),
            "has_boss": (i == room_count - 1 and floor in BOSS_FLOORS),
            "has_monster": random.random() < 0.4,
        })

    return {
        "floor": floor,
        "rooms": rooms,
        "region_id": DUNGEON_REGION_BASE + floor,
    }


# === 던전 진입 ===

def enter_dungeon(floor: int = 1) -> bool:
    """
    던전 진입.

    Args:
        floor: 진입 층 (1 또는 해금된 숏컷 층)

    Returns:
        True: 진입 성공
    """
    if _current_dungeon is None:
        generate_dungeon()

    # 숏컷 체크
    if floor > 1 and floor not in _shortcuts_unlocked:
        print(f"[dungeon] Floor {floor} shortcut not unlocked")
        return False

    if floor not in _current_dungeon["floors"]:
        print(f"[dungeon] Invalid floor: {floor}")
        return False

    floor_data = _current_dungeon["floors"][floor]

    # Region/Location 생성 (C# 측)
    region_id = floor_data["region_id"]
    morld.add_region(region_id, f"던전 {floor}층")

    import pollution

    for room in floor_data["rooms"]:
        morld.add_location(region_id, room["id"], room["name"],
                          length=room["length"])
        # 오염도 등록
        pollution.register_location(region_id, room["id"], room["pollution"])

    # Gate 생성 (선형 연결: 0→1→2→...→N)
    for i in range(len(floor_data["rooms"]) - 1):
        r1 = floor_data["rooms"][i]
        r2 = floor_data["rooms"][i + 1]
        morld.add_gate(region_id, r1["id"], 0, r1["length"] - 10,
                      region_id, r2["id"], 10)
        morld.add_gate(region_id, r2["id"], 1, 10,
                      region_id, r1["id"], r1["length"] - 10)

    # 입구와 마을 연결
    if floor == 1:
        first_room = floor_data["rooms"][0]
        morld.add_gate(region_id, first_room["id"], 2, 0,
                      DUNGEON_ENTRANCE_REGION, DUNGEON_ENTRANCE_LOCATION, 50)

    # 플레이어 이동
    player_id = morld.get_player_id()
    if player_id:
        first_room = floor_data["rooms"][0]
        morld.set_unit_location(player_id, region_id, first_room["id"], x=10)

    # 생물 풀 초기화 (방별 몬스터 상태 등록)
    import creature_pool
    for room in floor_data["rooms"]:
        creature_pool.init_room(
            floor, room["id"],
            has_monster=room.get("has_monster", False),
            is_boss_room=room.get("has_boss", False),
        )

    # 침식 시스템에 등록
    import erosion
    import party
    for mid in party.get_members():
        erosion.register(mid)

    print(f"[dungeon] Entered floor {floor} ({len(floor_data['rooms'])} rooms)")
    return True


# === 층 클리어 ===

def clear_floor(floor: int):
    """층 클리어 처리"""
    global _highest_floor, _twist_triggered

    if floor > _highest_floor:
        _highest_floor = floor

    # 숏컷 해금
    if floor in SHORTCUT_FLOORS:
        _shortcuts_unlocked.add(floor)
        print(f"[dungeon] Shortcut unlocked: floor {floor}")

    # 꺾기 이벤트
    if floor == TWIST_FLOOR and not _twist_triggered:
        _twist_triggered = True
        print(f"[dungeon] TWIST EVENT triggered at floor {floor}!")
        import morale
        morale.on_twist_revealed()

    print(f"[dungeon] Floor {floor} cleared! (highest: {_highest_floor})")


# === 방 진입 조우 ===

def on_room_enter(region_id, location_id):
    """방 진입 시 조우 판정 (on_reach 이벤트에서 호출)

    Returns:
        dict: encounter 결과 또는 None (조우 없음)
    """
    # 던전 region인지 확인
    floor = region_id - DUNGEON_REGION_BASE
    if floor < 1 or floor > 20:
        return None

    import creature_pool
    import morld

    # 리스폰 체크
    time_info = morld.get_time_info()
    current_ms = time_info.get("total_millis", 0) if time_info else 0
    creature_pool.check_respawn(floor, location_id, current_ms)

    # 조우 판정
    enemies = creature_pool.get_encounter(floor, location_id)
    if not enemies:
        return None

    # 은신 판정
    import stealth as stealth_mod
    if stealth_mod.is_party_stealthed():
        rate = stealth_mod.calculate_party_detection_rate()
        import random
        if random.random() > rate:
            # 미감지 → 선제 공격 or 우회 선택 (UI에서 처리)
            print(f"[dungeon] Stealth success — enemies not alerted")
            return {"type": "stealth_success", "enemies": enemies}

    # 전투 개시
    import encounter_handler
    result = encounter_handler.start_encounter(enemies)

    # 전투 승리 → 방 클리어 기록
    if result and result.get("result") == "victory":
        creature_pool.mark_cleared(floor, location_id, enemies)

        # 보스 방이면 층 클리어
        floor_data = _current_dungeon["floors"].get(floor) if _current_dungeon else None
        if floor_data:
            for room in floor_data["rooms"]:
                if room["id"] == location_id and room.get("has_boss"):
                    clear_floor(floor)
                    break

    return result


# === 재편성 ===

def reorganize():
    """
    던전 재편성 (플레이어 실신 시 호출).
    구조 재생성, 숏컷 리셋, 잔류 NPC 처리.
    """
    global _current_dungeon

    print("[dungeon] === REORGANIZATION ===")

    # 잔�� NPC → 잔류자 처리 (TODO: 잔류자 시스템 연동)

    # 생물 풀 초기화
    import creature_pool
    creature_pool.reset()

    # 새 던전 생성
    generate_dungeon()

    print("[dungeon] Dungeon reorganized. Shortcuts reset.")
