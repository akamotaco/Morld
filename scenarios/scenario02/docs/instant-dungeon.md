# 인스턴트 던전 시스템 설계

> 전투/탐험을 위해 동적으로 생성·삭제되는 지역.
> 로그라이크 방식의 2D 공간 분할(BSP) + PCG.

---

## 1. 개요

### 용어
- **인스턴트 던전**: 동적 생성/삭제되는 임시 Region. 입장 시 생성, 퇴장·클리어 시 삭제.
- **BSP (Binary Space Partition)**: 2D 공간을 재귀적으로 분할하여 방/복도를 생성하는 알고리즘.
- **Fog of War**: 방문한 Location만 지도에 표시. 내부 데이터는 완전 정보.

### 기존 시스템과의 관계
```
기존 고정 지형 (mansion, forest, city)
  └── Region + Location + Gate (수동 정의)

인스턴트 던전
  └── Region + Location + Gate (PCG 자동 생성)
  └── 동일한 API 사용 (add_region, add_location, add_gate)
  └── 기존 combat, creature, spawner, carry 시스템 그대로 활용
```

---

## 2. 아키텍처

```
instant_dungeon/
├── generator.py      # BSP 기반 2D 맵 생성 → Room 리스트
├── builder.py        # Room 리스트 → Region/Location/Gate 등록 (morld API)
├── populator.py      # 적/아이템/오브젝트 배치
├── fog.py            # 안개 관리 (방문 Location 추적)
├── manager.py        # 던전 라이프사이클 (생성/삭제/상태 관리)
└── templates.py      # 던전 템플릿 (난이도/테마/규모 정의)
```

---

## 3. 생성 파이프라인

```
1. 템플릿 선택
   → 난이도, 테마, 규모, 적 풀

2. BSP 2D 공간 분할 (generator.py)
   → 사각형 영역을 재귀 분할 → 방(Room) 목록 + 연결(복도) 목록
   → 각 Room에 (x, y, w, h) 좌표 → 나중에 지도 표시에 사용

3. Location/Gate 변환 (builder.py)
   → Room → Location (length = w, 방 이름)
   → 복도 연결 → Gate (x 좌표 기반 양방향)
   → morld.add_region(), add_location(), add_gate()

4. 적/아이템 배치 (populator.py)
   → 방별 난이도 기반 적 스폰 (spawner.py 활용)
   → 아이템 오브젝트 배치 (보물상자 등)

5. 입구 Gate 연결
   → 외부 고정 지형의 던전 입구 ↔ 던전 Region 입구 연결
```

---

## 4. BSP 2D 맵 생성 (generator.py)

### 알고리즘

```python
def generate_bsp(width, height, min_room_size, max_depth):
    """
    BSP 기반 던전 생성

    1. 전체 영역 (0, 0, width, height) 시작
    2. 재귀 분할:
       - 가로/세로 랜덤 선택
       - 분할선 위치 랜덤 (min_room_size 보장)
       - max_depth 도달 또는 min_room_size 미만 → 리프(방)
    3. 리프 노드에 방(Room) 생성 (패딩 적용)
    4. 형제 노드 간 복도(Corridor) 연결

    Returns:
        rooms: [(id, x, y, w, h, room_type)]
        corridors: [(room_id_a, room_id_b)]
    """
```

### Room → Location 매핑

| BSP 데이터 | morld 데이터 | 비고 |
|-----------|-------------|------|
| Room (x, y, w, h) | Location (length=w) | y 좌표는 지도 표시용으로 보존 |
| Corridor (a, b) | Gate (양방향) | x 좌표는 방의 가장자리 |
| Room type | Location props | "시작방", "보스방", "보물방" 등 |

### 2D 좌표 보존 (지도 표시용)

```python
# 각 Location에 prop으로 2D 좌표 저장
morld.set_location_prop(region_id, location_id, "던전:x", room.x)
morld.set_location_prop(region_id, location_id, "던전:y", room.y)
morld.set_location_prop(region_id, location_id, "던전:w", room.w)
morld.set_location_prop(region_id, location_id, "던전:h", room.h)
```

→ 지도 UI에서 이 좌표를 읽어 2D 맵 표시.
→ 캐릭터 위치가 Location 기반이므로 일관성 보장.

---

## 5. Fog of War (fog.py)

### 방문 추적

```python
# 플레이어 prop으로 방문 기록
# "던전:{dungeon_id}:방문:{location_id}" = 1
def mark_visited(player_id, dungeon_id, location_id):
    morld.set_unit_prop(player_id, f"던전:{dungeon_id}:방문:{location_id}", 1)

def is_visited(player_id, dungeon_id, location_id):
    return (morld.get_unit_prop(player_id, f"던전:{dungeon_id}:방문:{location_id}") or 0) >= 1
```

### 지도 표시

```
미방문: ■■■ (어둠 마스킹 — 기존 LinkMaskedColor 활용 가능)
방문:   방 이름 + 연결 표시
현재:   ★ 표시
```

### on_reach 연동

```python
# events/reach/ 에 등록:
# 플레이어가 던전 Location에 도착 → 자동으로 방문 기록
def on_reach_dungeon_location(player_id, region_id, location_id):
    dungeon_id = get_dungeon_id_for_region(region_id)
    if dungeon_id:
        mark_visited(player_id, dungeon_id, location_id)
```

---

## 6. 적/아이템 배치 (populator.py)

### 적 배치

```python
# 기존 spawner.py + creature 시스템 활용
# 방 타입에 따라 적 풀 선택

ROOM_ENEMY_TABLE = {
    "normal": {"pool": ["wolf", "bat"], "count": (1, 3)},
    "elite":  {"pool": ["spider", "arachne"], "count": (1, 2)},
    "boss":   {"pool": ["succubus"], "count": (1, 1)},
    "start":  {"pool": [], "count": (0, 0)},  # 시작방은 적 없음
    "treasure": {"pool": ["bat"], "count": (0, 1)},  # 보물방은 약한 적
}
```

### 아이템 배치

```python
# 보물상자 오브젝트 배치 → 기존 Object 시스템 활용
# 보상 아이템은 난이도 기반 랜덤

ROOM_LOOT_TABLE = {
    "treasure": {"pool": ["herb", "branch", "fish", "wolf_pelt"], "count": (1, 3)},
    "boss":     {"pool": ["sera_pendant", "wolf_pelt"], "count": (1, 2)},
    "normal":   {"pool": ["herb", "branch"], "count": (0, 1)},
}
```

---

## 7. 던전 라이프사이클 (manager.py)

### 생성

```python
def create_dungeon(template_id, entrance_region, entrance_location, entrance_x):
    """
    인스턴트 던전 생성

    1. 템플릿에서 설정 로드
    2. BSP 생성 → rooms, corridors
    3. Region/Location/Gate 등록
    4. 적/아이템 배치
    5. 입구 Gate 연결 (외부 ↔ 던전)
    6. 던전 ID 반환

    Returns:
        dungeon_id: str (고유 식별자)
    """
```

### 삭제

```python
def destroy_dungeon(dungeon_id):
    """
    인스턴트 던전 삭제

    1. 내부 유닛 전부 제거 (적/오브젝트)
    2. 플레이어가 내부에 있으면 입구로 텔레포트
    3. Gate 제거 (외부 연결 포함)
    4. Location 제거
    5. Region 제거
    6. 방문 prop 정리
    """
```

### Region ID 관리

```python
# 동적 Region은 100번대 이상 사용 (고정 지형과 충돌 방지)
# 고정: 0(저택), 2(도시), 3(숲), 4(광산), 5(유적), 10(상인대기), 99(Limbo)
# 동적: 100, 101, 102, ... (생성 시 auto-increment)

INSTANT_DUNGEON_REGION_START = 100
_next_region_id = INSTANT_DUNGEON_REGION_START
```

---

## 8. 던전 템플릿 (templates.py)

```python
TEMPLATES = {
    "forest_cave": {
        "name": "숲속 동굴",
        "width": 500,        # BSP 전체 너비
        "height": 500,       # BSP 전체 높이
        "min_room_size": 80,
        "max_depth": 4,      # BSP 분할 깊이 → 방 개수 결정
        "enemy_level": 1,
        "enemy_pool": ["wolf", "bat"],
        "boss": "spider",
        "loot_quality": "low",
        "theme": "자연동굴",
    },
    "ancient_ruins": {
        "name": "고대 유적",
        "width": 800,
        "height": 600,
        "min_room_size": 100,
        "max_depth": 5,
        "enemy_level": 3,
        "enemy_pool": ["spider", "arachne"],
        "boss": "succubus",
        "loot_quality": "medium",
        "theme": "석조유적",
    },
}
```

---

## 9. 시나리오 2/3 공유

### 공유 범위

| 모듈 | 위치 | 시나리오 2 | 시나리오 3 |
|------|------|-----------|-----------|
| generator.py | 공용 or 시나리오별 복사 | BSP 동일 | BSP 동일 |
| builder.py | 공용 | morld API 동일 | morld API 동일 |
| populator.py | 시나리오별 | 적/아이템 풀 다름 | 적/아이템 풀 다름 |
| templates.py | 시나리오별 | 숲속 동굴/유적 | 도시 지하/건물 |
| fog.py | 공용 | 동일 로직 | 동일 로직 |
| manager.py | 공용 | 동일 라이프사이클 | 동일 라이프사이클 |

### 공유 방법
- `generator.py`, `builder.py`, `fog.py`, `manager.py` → 공용 모듈 (scenario 독립)
- `populator.py`, `templates.py` → 시나리오별 커스텀
- 시나리오 03 호환 원칙: 선택적 prop + 기본값 적용

---

## 10. 맵 표시 연동

### 기존 지형 vs 인스턴트 던전

| 항목 | 기존 지형 | 인스턴트 던전 |
|------|----------|-------------|
| 탐색 방식 | DFS (깊이우선) | BFS/자유 (방문 순) |
| 정보 표시 | 완전 정보 (전체 표시) | **Fog of War** (방문만 표시) |
| 내부 데이터 | 완전 정보 | 완전 정보 (표시만 제한) |
| 좌표 체계 | 1D (length 기반 X축) | **2D (BSP x,y 좌표)** |

### 지도 UI 렌더링

```
기존 지형:
  [거실] ─── [부엌] ─── [뒷마당]
    │
  [복도] ─── [세라방]

인스턴트 던전:
  ┌───────┐
  │ ■■■   │     ← 미방문 (안개)
  │       │
  ├───┐   │
  │ 방1│───│── 방2 (★ 현재 위치)
  │   │   │
  └───┴───┘
```

2D 좌표(던전:x, 던전:y, 던전:w, 던전:h)를 읽어서 위치 기반 렌더링.

---

## 11. 구현 순서

```
Phase 1: generator.py — BSP 맵 생성 (순수 Python, morld 의존 없음)
  → mock 테스트 가능

Phase 2: builder.py — Room → Region/Location/Gate 변환
  → mock morld 테스트

Phase 3: fog.py — 방문 추적 + on_reach 연동
  → prop 기반, 간단

Phase 4: populator.py — 적/아이템 배치
  → 기존 spawner/creature 시스템 활용

Phase 5: manager.py — 라이프사이클 (생성/삭제)
  → 통합 테스트

Phase 6: templates.py — 시나리오 02용 템플릿
  → 숲속 동굴, 고대 유적

Phase 7: 맵 UI 연동 (TextUI)
  → 2D 좌표 기반 지도 렌더링
```

---

## 12. 관련 문서

- [dungeon.md](dungeon.md) — 기존 던전 설계 (고정 던전)
- [battle.md](battle.md) — 전투 시스템
- [creature.md](creature.md) — 생물/세력 시스템
- [chapter1-routes.md](chapter1-routes.md) — 챕터 1 공략 루트
