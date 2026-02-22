# spawner.py — 생물(Creature) 스폰/디스폰 관리
#
# 스폰 소스 등록 → 1시간마다 스폰 체크 + 시체 정리 + 수명 소멸
# 명세: docs/combat-implementation.md Section 12

import morld
from events import subscribe_time_elapsed

MILLIS_PER_HOUR = 3_600_000
CORPSE_DESPAWN_HOURS = 4          # 시체 정리 시각 (사망 후 4시간)
CORPSE_DESPAWN_MS = CORPSE_DESPAWN_HOURS * MILLIS_PER_HOUR
DEFAULT_LIFESPAN_HOURS = 72       # 기본 수명 (3일)

# {source_id: {"class": MonsterClass, "max": int, "interval_h": int,
#              "region_id": int, "location_id": int, "lifespan_h": int,
#              "spawned": [unit_id, ...], "last_spawn_hour": 0}}
_spawn_sources = {}
_corpses = []     # 사망 유닛 추적 (시체 정리 대기)
_initialized = False


def register_spawn_source(source_id, monster_class, max_count,
                          interval_hours, region_id, location_id,
                          lifespan_hours=DEFAULT_LIFESPAN_HOURS):
    """스폰 소스 등록

    Args:
        source_id: 고유 식별자 (str)
        monster_class: 몬스터 Asset 클래스 (예: Wolf)
        max_count: 최대 동시 존재 수
        interval_hours: 스폰 간격 (시간)
        region_id: 스폰 Region
        location_id: 스폰 Location
        lifespan_hours: 수명 (시간, 기본 72h=3일)
    """
    _spawn_sources[source_id] = {
        "class": monster_class,
        "max": max_count,
        "interval_h": interval_hours,
        "region_id": region_id,
        "location_id": location_id,
        "lifespan_h": lifespan_hours,
        "spawned": [],
        "last_spawn_hour": 0,
    }
    _ensure_initialized()


def _ensure_initialized():
    """시간 구독 초기화 (lazy)"""
    global _initialized
    if _initialized:
        return
    _initialized = True
    subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)


def _on_time_elapsed(millis):
    """매 1시간: 스폰 체크 + 수명 소멸 + 시체 정리"""
    current_time = morld.get_current_time()
    current_hour = current_time // MILLIS_PER_HOUR

    for source_id, source in _spawn_sources.items():
        _update_spawned_list(source, current_time)
        _try_spawn(source_id, source, current_hour, current_time)

    _cleanup_corpses(current_time)


def _update_spawned_list(source, current_time):
    """사망/디스폰/수명 만료 유닛 제거"""
    import think

    lifespan_ms = source["lifespan_h"] * MILLIS_PER_HOUR
    spawn_region = source["region_id"]
    spawn_loc = source["location_id"]

    alive = []
    for unit_id in source["spawned"]:
        info = morld.get_unit_info(unit_id)
        if info is None:
            continue
        # 사망이면 spawned 목록에서 제거 → _corpses로 이관
        if morld.get_unit_prop(unit_id, "상태:사망"):
            if unit_id not in _corpses:
                _corpses.append(unit_id)
            continue
        # 맵 밖(-1,-1)이면 제거
        loc = morld.get_unit_location(unit_id)
        if loc is None or loc[0] < 0:
            continue
        # 수명 체크: 수명 초과 + spawn location에 위치 → 자연 소멸
        birth = morld.get_unit_prop(unit_id, "생물:탄생시각")
        if birth is not None and (current_time - birth) > lifespan_ms:
            if loc[0] == spawn_region and loc[1] == spawn_loc:
                morld.set_unit_location(unit_id, -1, -1)
                think.unregister_agent(unit_id)
                print(f"[spawner] Natural despawn (id={unit_id}, age={int((current_time - birth) / MILLIS_PER_HOUR)}h)")
                continue
        alive.append(unit_id)
    source["spawned"] = alive


def _try_spawn(source_id, source, current_hour, current_time):
    """스폰 조건 체크 + 생물 생성"""
    # 최대 수 도달
    if len(source["spawned"]) >= source["max"]:
        return
    # 스폰 간격
    if current_hour - source["last_spawn_hour"] < source["interval_h"]:
        return

    monster_class = source["class"]
    region_id = source["region_id"]
    location_id = source["location_id"]

    # 생물 생성
    monster_id = morld.create_id("unit")
    monster = monster_class()
    monster.instantiate(monster_id, region_id, location_id)

    # 드롭 테이블 기반 인벤토리 생성
    if hasattr(monster, '_populate_inventory'):
        monster._populate_inventory()

    # 생물 prop 설정
    morld.set_unit_prop(monster_id, "전투:홈리전", region_id)
    morld.set_unit_prop(monster_id, "생물:스폰위치", location_id)
    morld.set_unit_prop(monster_id, "생물:탄생시각", current_time)

    # CreatureAgent 등록
    import think
    from think.creature_agent import CreatureAgent
    schedule = getattr(monster_class, 'SCHEDULE', None)
    agent = CreatureAgent(monster_id, schedule=schedule)
    think.register_agent(monster_id, agent)

    source["spawned"].append(monster_id)
    source["last_spawn_hour"] = current_hour
    print(f"[spawner] Spawned {monster_class.unique_id} (id={monster_id}) at R{region_id}:L{location_id}")


def _cleanup_corpses(current_time):
    """시체 정리 — 사망 후 4시간 + 플레이어 부재 시 디스폰"""
    import think

    player_id = morld.get_player_id()
    player_loc = morld.get_unit_location(player_id) if player_id else None

    for unit_id in list(_corpses):
        death_time = morld.get_unit_prop(unit_id, "상태:사망시각")
        if death_time is None:
            continue
        if current_time - death_time < CORPSE_DESPAWN_MS:
            continue
        # 플레이어가 같은 Location에 있으면 정리 보류
        corpse_loc = morld.get_unit_location(unit_id)
        if player_loc and corpse_loc and player_loc == corpse_loc:
            continue
        # 디스폰 (맵 밖으로 이동 + Agent 해제)
        morld.set_unit_location(unit_id, -1, -1)
        think.unregister_agent(unit_id)
        _corpses.remove(unit_id)
        print(f"[spawner] Despawned corpse (id={unit_id})")


def reset():
    """챕터 전환 시 초기화"""
    global _spawn_sources, _corpses, _initialized
    _spawn_sources = {}
    _corpses = []
    _initialized = False
