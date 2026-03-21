# 인스턴트 던전 시스템 설계 v2

> BSP 기반 동적 생성 + 층별 Lazy Generation + Bridge 그래프 확장

---

## 1. 핵심 개념

### 용어
- **인스턴트 던전**: 동적 생성/삭제되는 임시 Region. 스케줄러가 입구만 생성, 진입 시 내부 확장.
- **BSP (Binary Space Partition)**: 2D 공간 재귀 분할 → 방/복도 생성.
- **Spec**: 던전의 청사진. seed와 함께 항상 동일한 던전을 재현.
- **Lazy Generation**: 층별로 플레이어 진입 시점에 생성. 미방문 층은 존재하지 않음.
- **Bridge**: BSP tree 위에 추가되는 비트리 간선. 탐색 루프를 생성.

### 기존 시스템과의 관계
```
고정 던전 (dungeon.md)
  └── 수동 정의 Region/Location/Gate

인스턴트 던전
  └── Spec + seed → BSP 자동 생성
  └── 동일한 morld API (add_region, add_location, add_gate)
  └── 기존 combat, creature, spawner 시스템 그대로 활용
```

---

## 2. 던전 Spec

Spec은 던전의 완전한 청사진. **같은 seed + 같은 Spec = 항상 동일한 던전**.

```python
FOREST_CAVE_SPEC = {
    "name": "숲속 동굴",
    "max_floors": 3,           # None = 무한

    # BSP 기본값 (층별 오버라이드 가능)
    "base": {
        "width": 400,
        "height": 400,
        "min_size": 60,
        "max_depth": 4,
    },

    # 층별 오버라이드 (없으면 base 사용)
    "floor_overrides": {
        2: {"width": 500, "height": 500, "max_depth": 5},
    },

    # 층별 자동 스케일링 (base 위에 가산)
    "floor_scaling": {
        "width_per_floor": 30,       # 층마다 +30
        "max_depth_per_floor": 0.5,  # 2층마다 +1
    },

    # 층간 연결 구조
    "connections": {
        "type": "linear",            # linear / branching / loop
        "stairs_per_floor": 1,       # 층당 계단 수
        "bridges_per_floor": 2,      # 층당 추가 bridge 수
        "bridge_max_distance": 200,  # bridge 후보 최대 거리
    },

    # 등장 생물 풀 (층별)
    "creatures": {
        0: [
            {"type": "wolf", "count": (1, 3), "weight": 70},
            {"type": "bat", "count": (2, 4), "weight": 30},
        ],
        1: [
            {"type": "wolf", "count": (2, 4), "weight": 50},
            {"type": "spider", "count": (1, 3), "weight": 50},
        ],
        2: [  # 보스층
            {"type": "dire_wolf", "count": (1, 1), "weight": 100},
        ],
    },

    # 보물/아이템 풀 (층별)
    "loot": {
        0: [
            {"item": "food_herb", "count": (1, 2), "chance": 0.5},
        ],
        2: [  # 보스방 보상
            {"item": "rare_pelt", "count": (1, 1), "chance": 1.0},
        ],
    },

    # 환경
    "environment": {
        "brightness": 0.2,
        "temperature_mod": -3,
    },
}
```

### 결정론 보장 (seed 파생)

| 용도 | seed 계산 | 비고 |
|------|----------|------|
| 층 BSP | `base_seed + floor * 100` | 층별 독립 |
| 분기 BSP | `base_seed + floor * 100 + branch` | branching 시 |
| 방별 몬스터 | `base_seed + floor * 100 + room_id * 10` | 방 단위 |
| 방별 아이템 | `base_seed + floor * 100 + room_id * 10 + 1` | 방 단위 |
| bridge 선택 | `base_seed + floor * 100 + 99` | 층 단위 |

---

## 3. 층간 연결 패턴

### connection type

| type | 구조 | 특징 |
|------|------|------|
| `linear` | `1F → 2F → 3F` | 일직선. stairs_per_floor로 계단 수 조절 |
| `branching` | `1F → 2Fa, 1F → 2Fb` | 분기. 각 분기는 별도 region+BSP |
| `loop` | `1F ↔ 2F` (양쪽 계단) | 순환 가능 |

```
linear (1):          linear (2):          branching (2):
  1F                   1F                   1F
  │                   ╱  ╲                 ╱  ╲
  2F                 2F   2F              2Fa  2Fb
  │                   ╲  ╱                 │    │
  3F                   3F                  3F   3Fb
```

### stairs_per_floor

- `1`: BSP에서 stairs_down 방 1개 생성
- `2`: stairs_down 방 2개 생성
- branching + 2: 각 계단이 다른 region으로 연결 (분기)
- linear + 2: 같은 다음 층으로 연결 (두 경로)

### max_floors 동작

| max_floors | 동작 |
|-----------|------|
| `3` | 0층~2층. 마지막 층 BSP에서 stairs_down 제거 |
| `None` | 무한. 항상 stairs_down 포함 |

---

## 4. Bridge 시스템

BSP는 tree 구조(각 방이 하나의 부모와 연결). Bridge는 이 tree 위에 **추가 간선**을 넣어 사이클(루프)을 생성.

### 효과
```
Tree (before):          + Bridge (after):
  A───B                    A───B
  │   │                    │ ╲ │
  C───D───E                C───D───E
      │                        │ ╱
      F                        F
```
- 탐색 루프 → 우회 경로, 전략적 이동
- 막다른 길 감소 → 도주 가능
- 공간 밀도 증가

### 알고리즘

```
1. BSP 완료 후 모든 방의 중심점 좌표 계산
2. 비연결 방 쌍의 유클리디안 거리 계산
3. 거리순 정렬 (가까운 쌍 우선)
4. 각 후보에 대해:
   a. 거리 > bridge_max_distance → skip
   b. bridge 수 >= bridges_per_floor → stop
   c. 두 방 중심을 잇는 선분이 기존 corridor/bridge와 교차 → skip
   d. 통과 → bridge 추가 (Gate 등록)
5. 교차 검사: 2D 선분 교차 판정 (유클리디안)
```

### 선분 교차 판정

```python
def segments_intersect(p1, p2, p3, p4):
    """두 선분 (p1-p2)와 (p3-p4)의 교차 여부"""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = cross(p3, p4, p1)
    d2 = cross(p3, p4, p2)
    d3 = cross(p1, p2, p3)
    d4 = cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False
```

### Spec 설정

```python
"connections": {
    "bridges_per_floor": 2,       # 층당 최대 bridge 수
    "bridge_max_distance": 200,   # 후보 최대 거리
}
```

- `bridges_per_floor: 0` → tree 구조 유지 (bridge 없음)
- `bridges_per_floor: 3+` → 복잡한 미로

---

## 5. Lazy Generation (층별 동적 생성)

### 전체 흐름

```
[스케줄러 09:00]
  └─ create_dungeon_entrance(spec, seed)
     → Region 100 + "던전 입구" Location(0) + 뒷마당↔입구 RegionGate
     → dungeon_info.floors_generated = {} (비어있음)

[플레이어가 입구 Location 도착] ← on_reach
  └─ expand_floor(dungeon_id, floor=0)
     → BSP 생성 (1층, seed=base_seed + 0)
     → Location/Gate 추가 (입구 Location은 skip — 이미 존재)
     → Bridge 추가 (교차 검사)
     → Populator: 몬스터/아이템 배치
     → FoW 초기화
     → stairs_down 발견 시:
        └─ create_floor_stub(floor=1)
           → Region 101 + "상층 계단" Location 1개만
           → RegionGate: 1층 stairs_down ↔ 2층 stub

[플레이어가 2층 stub 도착] ← on_reach
  └─ expand_floor(dungeon_id, floor=1)
     → BSP 생성 (2층, seed=base_seed + 100)
     → stairs_up Location은 이미 stub에 존재 → skip
     → 나머지 방/복도/Bridge/Gate 추가
     → stairs_down 있으면 → create_floor_stub(floor=2)
     → FoW 초기화

[반복... max_floors까지 또는 무한]

[22:00 삭제]
  └─ destroy_dungeon()
     → 생성된 층만 정리 (floors_generated에 있는 것만)
```

### 데이터 구조

```python
dungeon_info = {
    "dungeon_id": "dungeon_1",
    "base_region_id": 100,
    "entrance_location": 0,
    "spec": FOREST_CAVE_SPEC,
    "base_seed": 2042,

    # 층별 생성 상태
    "floors_generated": {
        # floor_num: {
        #     "region_id": 100,
        #     "rooms": [...],
        #     "corridors": [...],
        #     "bridges": [...],
        #     "locations": {room_id: loc_id},
        #     "has_stairs_down": True,
        # }
    },

    # 다음 층 stub (미확장 상태)
    "floor_stubs": {
        # floor_num: {"region_id": 101, "stub_location": 0}
    },

    # 외부 연결
    "_entrance_ext_region": 0,
    "_entrance_ext_location": 13,
}
```

---

## 6. 핵심 함수

| 함수 | 역할 | 호출 시점 |
|------|------|----------|
| `create_dungeon_entrance(spec, seed, gate)` | Region + 입구 1개 + 외부 Gate | 스케줄러 09:00 |
| `expand_floor(did, floor)` | BSP + Location/Gate/Bridge + FoW + Populator | on_reach (미확장 층) |
| `create_floor_stub(did, floor)` | 다음 층 Region + stub 1개 + 계단 Gate | expand_floor 내부 |
| `is_floor_expanded(did, floor)` | 해당 층 BSP 확장 여부 | on_reach 판별 |
| `get_floor_for_region(did, rid)` | region_id → floor 정보 | FoW/맵 렌더링 |
| `destroy_dungeon(did)` | 생성된 층만 정리 | 스케줄러 22:00 |

### on_reach 판별 로직

```python
dungeon_id, info = get_dungeon_for_region(region_id)
if info:
    floor_num = get_floor_num_for_region(dungeon_id, region_id)
    if floor_num is not None and not is_floor_expanded(dungeon_id, floor_num):
        expand_floor(dungeon_id, floor_num)
    # FoW 업데이트...
```

---

## 7. Spec 예시

### 단순 동굴

```python
SIMPLE_CAVE = {
    "name": "좁은 동굴",
    "max_floors": 2,
    "base": {"width": 300, "height": 300, "min_size": 60, "max_depth": 3},
    "connections": {
        "type": "linear", "stairs_per_floor": 1,
        "bridges_per_floor": 0,
    },
    "creatures": {
        0: [{"type": "bat", "count": (1, 3), "weight": 100}],
    },
}
```

### 대형 유적 (분기 + Bridge)

```python
GRAND_RUIN = {
    "name": "고대 유적",
    "max_floors": 5,
    "base": {"width": 500, "height": 500, "min_size": 50, "max_depth": 5},
    "connections": {
        "type": "branching", "stairs_per_floor": 2,
        "bridges_per_floor": 3, "bridge_max_distance": 250,
    },
    "floor_overrides": {
        4: {"width": 700, "height": 700, "max_depth": 6},
    },
    "creatures": {
        0: [{"type": "skeleton", "count": (2, 4), "weight": 100}],
        4: [{"type": "golem", "count": (1, 1), "weight": 100}],
    },
}
```

### 무한 광산

```python
ENDLESS_MINE = {
    "name": "끝없는 광산",
    "max_floors": None,
    "base": {"width": 350, "height": 350, "min_size": 50, "max_depth": 4},
    "connections": {
        "type": "linear", "stairs_per_floor": 1,
        "bridges_per_floor": 1, "bridge_max_distance": 150,
    },
    "floor_scaling": {
        "width_per_floor": 30,
        "max_depth_per_floor": 0.5,
    },
}
```

---

## 8. Fog of War

### 모드

| 모드 | 동작 | 적합한 상황 |
|------|------|-----------|
| `volatile` | 현재 위치 + 인접만 표시, 이동 시 이전 안개 | 인스턴트 던전 |
| `permanent` | 한 번 방문하면 영구 밝힘 | 신규 지역 탐험 |
| `none` | 완전 정보 | 기존 지도 |

### 맵 표시

```
HIDDEN:   · (윤곽만, 클릭 불가)
REVEALED: ○ (방문 적 있음, 회색)
VISIBLE:  ● (현재 위치 + 인접, 밝음, 클릭 이동 가능)
```

- 방 위치는 항상 고정 (FoW 상태와 무관)
- 캐릭터 코드네임: VISIBLE 방에만 표시 (A, B, C... / @ = 플레이어)

---

## 9. 아키텍처

```
instant_dungeon/
├── __init__.py       # 패키지 초기화
├── generator.py      # BSP 2D 맵 생성 + Bridge 알고리즘
├── builder.py        # Room → Region/Location/Gate 변환
├── populator.py      # 몬스터/아이템 배치 (미구현)
├── fog.py            # FoW 상태 관리
├── manager.py        # 라이프사이클 (entrance/expand/destroy)
├── scheduler.py      # 시간 기반 스케줄 (09:00 생성, 22:00 삭제)
└── specs.py          # 던전 Spec 정의 (미구현)
```

---

## 10. 관련 문서

- [dungeon.md](dungeon.md) — 고정 던전 설계
- [battle.md](battle.md) — 전투 시스템
- [creature.md](creature.md) — 생물/세력 시스템
