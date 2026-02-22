# spawner.py — 몬스터 스폰/디스폰 관리
#
# 스폰 소스 등록 → 1시간마다 스폰 체크 + 시체 정리
# 명세: docs/combat-implementation.md Section 12

import morld
from events import subscribe_time_elapsed

MILLIS_PER_HOUR = 3_600_000
CORPSE_DESPAWN_HOURS = 4          # 시체 정리 시각 (사망 후 4시간)
CORPSE_DESPAWN_MS = CORPSE_DESPAWN_HOURS * MILLIS_PER_HOUR

# {source_id: {"class": MonsterClass, "max": int, "interval_h": int,
#              "region_id": int, "location_id": int,
#              "spawned": [unit_id, ...], "last_spawn_hour": 0}}
_spawn_sources = {}
_initialized = False


def register_spawn_source(source_id, monster_class, max_count,
                          interval_hours, region_id, location_id):
    """스폰 소스 등록

    Args:
        source_id: 고유 식별자 (str)
        monster_class: 몬스터 Asset 클래스 (예: Wolf)
        max_count: 최대 동시 존재 수
        interval_hours: 스폰 간격 (시간)
        region_id: 스폰 Region
        location_id: 스폰 Location
    """
    _spawn_sources[source_id] = {
        "class": monster_class,
        "max": max_count,
        "interval_h": interval_hours,
        "region_id": region_id,
        "location_id": location_id,
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
    """매 1시간: 스폰 체크 + 시체 정리"""
    current_time = morld.get_current_time()
    current_hour = current_time // MILLIS_PER_HOUR

    for source_id, source in _spawn_sources.items():
        _update_spawned_list(source)
        _try_spawn(source_id, source, current_hour)

    _cleanup_corpses(current_time)


def _update_spawned_list(source):
    """사망/디스폰된 유닛 제거"""
    alive = []
    for unit_id in source["spawned"]:
        info = morld.get_unit_info(unit_id)
        if info is None:
            continue
        # 사망 또는 맵 밖(-1,-1)이면 제거
        death = morld.get_unit_prop(unit_id, "상태:사망")
        if death:
            continue
        loc = morld.get_unit_location(unit_id)
        if loc is None or loc[0] < 0:
            continue
        alive.append(unit_id)
    source["spawned"] = alive


def _try_spawn(source_id, source, current_hour):
    """스폰 조건 체크 + 몬스터 생성"""
    # 최대 수 도달
    if len(source["spawned"]) >= source["max"]:
        return
    # 스폰 간격
    if current_hour - source["last_spawn_hour"] < source["interval_h"]:
        return

    monster_class = source["class"]
    region_id = source["region_id"]
    location_id = source["location_id"]

    # 몬스터 생성
    monster_id = morld.create_id("unit")
    monster = monster_class()
    monster.instantiate(monster_id, region_id, location_id)

    # 드롭 테이블 기반 인벤토리 생성
    if hasattr(monster, '_populate_inventory'):
        monster._populate_inventory()

    # 전투:홈리전 prop 설정
    morld.set_unit_prop(monster_id, "전투:홈리전", region_id)

    # think agent 등록
    import think
    behavior = getattr(monster_class, 'BATTLE_BEHAVIOR', None)
    if behavior:
        # MonsterAgent 생성 (BaseAgent 사용, 몬스터 스케줄 적용)
        agent = think.BaseAgent(monster_id)
        # 몬스터 스케줄 설정
        schedule = getattr(monster_class, 'SCHEDULE', None)
        if schedule:
            agent._schedule = schedule
        think.register_agent(monster_id, agent)

    source["spawned"].append(monster_id)
    source["last_spawn_hour"] = current_hour
    print(f"[spawner] Spawned {monster_class.unique_id} (id={monster_id}) at R{region_id}:L{location_id}")


def _cleanup_corpses(current_time):
    """시체 정리 — 사망 후 4시간 + 플레이어 부재 시 디스폰"""
    player_id = morld.get_player_id()
    player_loc = morld.get_unit_location(player_id) if player_id else None

    for source in _spawn_sources.values():
        for unit_id in list(source["spawned"]):
            death = morld.get_unit_prop(unit_id, "상태:사망")
            if not death:
                continue
            death_time = morld.get_unit_prop(unit_id, "상태:사망시각")
            if death_time is None:
                continue
            if current_time - death_time < CORPSE_DESPAWN_MS:
                continue
            # 플레이어가 같은 Location에 있으면 정리 보류
            corpse_loc = morld.get_unit_location(unit_id)
            if player_loc and corpse_loc and player_loc == corpse_loc:
                continue
            # 디스폰 (맵 밖으로 이동)
            morld.set_unit_location(unit_id, -1, -1)
            print(f"[spawner] Despawned corpse (id={unit_id})")


def reset():
    """챕터 전환 시 초기화"""
    global _spawn_sources, _initialized
    _spawn_sources = {}
    _initialized = False
