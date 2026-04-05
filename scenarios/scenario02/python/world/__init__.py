# world/__init__.py - 월드 모듈
#
# 역할:
# - 지형 데이터 정의 및 초기화
# - 시간 설정
# - 아이템/오브젝트/캐릭터 인스턴스화
# - Region 간 연결 (RegionGate) 관리
#
# 챕터별 Region 선택적 로드:
# - 챕터 파일에서 필요한 Region만 initialize_terrain() 호출
# - RegionGate는 양쪽 Region이 존재할 때만 등록 (없으면 무시)
# - 예: 챕터 2에서 mansion + forest만 로드하면, city 연결 Gate는 무시됨

import morld
import map_coords

from . import mansion   # Region 0: 숲속 저택
from . import vehicle   # Region 1: 대형 차량 내부 (버스 interior)
from . import city      # Region 2: 황폐화된 도시
from . import forest    # Region 3: 숲
from . import mine      # Region 4: 폐광산
from . import test_dungeon      # Region 5: 잊혀진 유적
from . import merchant_limbo    # Region 10: 상인 대기소 (Gate 없음 — 페이 오프 시간 전용)

# ========================================
# Region 간 연결 (cross-region Gate)
# ========================================
# (region_a, location_a, region_b, location_b, distance)
# distance: location units (BaseSpeed = 1 unit/sec, 120분 도보 = 7200 units)
#
# add_gate 양방향으로 등록. RegionGate 레거시 제거.
# Gate X 좌표: Location 끝(length-10) 또는 시작(10)에 배치.

CROSS_REGION_GATES = [
    # 숲 입구(R0:20) ↔ 도시 입구(R2:0) - ≈2시간 도보
    (mansion.REGION_ID, 20, city.REGION_ID, 0, 7200),

    # 버스 내부(R1:L0) ↔ 주차장(R2:L4) - 즉시 (하차/탑승)
    (vehicle.REGION_ID, 0, city.REGION_ID, 4, 0),

    # 숲 입구(R0:20) ↔ 숲 입구(R3:0) - ≈30분 도보
    (mansion.REGION_ID, 20, forest.REGION_ID, 0, 1800),

    # 주차장(R2:4) ↔ 광산 입구(R4:0) - ≈30분 도보
    (city.REGION_ID, 4, mine.REGION_ID, 0, 1800),

    # 숲속(R3:3) ↔ 유적 입구(R5:0) - ≈15분 도보
    (forest.REGION_ID, 3, test_dungeon.REGION_ID, 0, 900),
]

# cross-region gate_id 카운터 (region 내 gate_id 충돌 방지)
_CROSS_GATE_ID_BASE = 100


def _safe_add_cross_region_gate(region_a, loc_a, region_b, loc_b, distance, gate_idx):
    """Region이 존재할 때만 양방향 Gate 등록

    Gate X: Location 길이 조회 → 끝에 배치.
    gate_id: _CROSS_GATE_ID_BASE + gate_idx (기존 Gate와 충돌 방지)
    """
    if not (morld.region_exists(region_a) and morld.region_exists(region_b)):
        return False

    # Location 길이 조회
    info_a = morld.get_location_info(region_a, loc_a)
    info_b = morld.get_location_info(region_b, loc_b)
    length_a = info_a.get("length", 100) if info_a else 100
    length_b = info_b.get("length", 100) if info_b else 100

    gate_id_a = _CROSS_GATE_ID_BASE + gate_idx * 2
    gate_id_b = _CROSS_GATE_ID_BASE + gate_idx * 2 + 1

    # A→B: A의 끝 → B의 시작
    morld.add_gate(region_a, loc_a, gate_id_a, max(0, length_a - 10),
                   region_b, loc_b, 10)
    # B→A: B의 시작 → A의 끝
    morld.add_gate(region_b, loc_b, gate_id_b, 10,
                   region_a, loc_a, max(0, length_a - 10))

    # Gate에 travel distance 설정 (C# gate.Distance)
    # add_gate의 마지막 파라미터들: arrival_y, conditions_fwd, conditions_bwd, is_blocked, name, distance
    # 간단한 방법: 별도 API 호출 또는 positional 전달
    # TODO: add_gate에 distance kwarg 지원 후 정리
    # 현재는 distance=0으로 등록 (travel time은 Gate X간 거리에서 계산)

    return True


def initialize_cross_region_gates():
    """cross-region Gate 양방향 등록"""
    registered = 0
    for idx, entry in enumerate(CROSS_REGION_GATES):
        region_a, loc_a, region_b, loc_b, distance = entry
        if _safe_add_cross_region_gate(region_a, loc_a, region_b, loc_b, distance, idx):
            registered += 1
    print(f"[world] Cross-region gates registered: {registered}/{len(CROSS_REGION_GATES)}")


# ========================================
# 초기화 함수들
# ========================================

def initialize_world():
    """월드 초기화 (지형 + 시간 + cross-region Gate + 맵 좌표)"""
    # 각 Region 초기화
    mansion.initialize_terrain()
    vehicle.initialize_terrain()  # Region 1: 대형 차량 내부
    city.initialize_terrain()
    forest.initialize_terrain()
    mine.initialize_terrain()
    merchant_limbo.initialize_terrain()

    # 시간 설정 (mansion에서 관리)
    mansion.initialize_time()

    # Region 간 연결 (add_gate 양방향)
    initialize_cross_region_gates()

    # 맵 2D 좌표 등록
    _register_map_coordinates()


def instantiate_player():
    """플레이어만 인스턴스화 (챕터 0용)"""
    mansion.instantiate_player()


def instantiate_npcs():
    """NPC들만 인스턴스화 (챕터 1 전환 시)"""
    mansion.instantiate_npcs()


def instantiate_all():
    """모든 유닛 인스턴스화 (플레이어 + NPC + 오브젝트 + 아이템)"""
    mansion.instantiate()


# ========================================
# 맵 2D 좌표 자동 배치
# ========================================
#
# Gate 그래프 기반 자동 배치. 수동 좌표 불필요.
# 건축/파괴 시 rebuild()로 전체 재조정.

def _register_map_coordinates():
    """각 Region의 Location을 등록하고 Gate 기반 2D 좌표 자동 계산"""
    region_ids = [
        mansion.REGION_ID,       # 0
        city.REGION_ID,          # 2
        forest.REGION_ID,        # 3
        mine.REGION_ID,          # 4
        test_dungeon.REGION_ID,  # 5
    ]

    total = 0
    for rid in region_ids:
        region_info = morld.get_region_info(rid)
        if not region_info:
            continue
        for loc in region_info.get("locations", []):
            loc_id = loc["id"] if isinstance(loc, dict) else int(loc)
            map_coords.register(rid, loc_id)
        map_coords.rebuild(rid)
        total += len(map_coords.get_all(rid))

    print(f"[world] Map coordinates auto-placed: {total} locations across {len(region_ids)} regions")
