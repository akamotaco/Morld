# 동적 맵 생성 시스템 (Dynamic Map Generation)

## 개요

탐사 지역은 매 회차/탐사마다 **동적으로 생성**된다. 로그라이크 형식을 응용하되, 기존 시나리오02의 Region/Location/Gate 시스템 위에서 동작한다.

**핵심 원칙: 시각은 2D, 데이터는 1D**

```
┌─────┐    ┌─────┐    ┌─────┐
│Room1│────│통로 │────│Room2│   ← 2D 시각 (미니맵/탐사 UI)
└─────┘    └─────┘    └─────┘

Location0 ──Gate── Location1 ──Gate── Location2   ← 1D 데이터 (게임 로직)
(length=200)        (length=80)        (length=300)
```

- **2D 좌표**: 미니맵 렌더링, 시각적 배치에 사용
- **1D Location/Gate**: 실제 게임 로직 (이동, 전투, 이벤트) 에 사용
- **기존 시스템 완전 재활용**: DES, FSM, 이동, 전투, 환경 시스템 모두 그대로

C# 변경 없음 — 순수 Python 맵 생성기.

---

## 기존 시스템 활용

| 기존 시스템 | 동적 맵에서의 역할 |
|-----------|------------------|
| `Region` | 탐사 지역 1개 = Region 1개 (동적 생성/삭제) |
| `Location` | 방(Room) 1개 = Location 1개 (geometry="line", length=가변) |
| `Gate` | 방 간 연결 = Gate (travel_time으로 통로 길이 표현) |
| `add_location()` | 방 생성 API |
| `add_gate()` | 연결 생성 API (조건부 잠금 가능) |
| `_move_to()` | NPC 이동 (DES 기반, 변경 없음) |
| `CombatState` / `MicroTurnCombatState` | 전투 (FSM 기반, 변경 없음) |
| `spawner.py` | 적 배치 (prop 기반) |
| `facility_resolver.py` | 자원/시설 탐색 (prop 기반) |
| `temperature/humidity/pollution.py` | 환경 시뮬레이션 (Location 등록만 하면 자동 작동) |

---

## 생성 파이프라인

### 1단계: 2D 레이아웃 생성

BSP(Binary Space Partition) 또는 Force-Directed 알고리즘으로 2D 방 배치를 생성한다.

**입력:**
- 난이도 → 방 개수, 크기 범위, 분기 밀도
- 심(深) 레벨 → 환경 위험도, 적 밀도
- 시드(seed) → 재현 가능한 생성

**출력:**
```python
rooms = [
    {"id": 0, "x": 0, "y": 0, "width": 200, "height": 150, "type": "entrance"},
    {"id": 1, "x": 300, "y": 0, "width": 180, "height": 120, "type": "corridor"},
    {"id": 2, "x": 600, "y": -100, "width": 250, "height": 200, "type": "room"},
    {"id": 3, "x": 600, "y": 200, "width": 200, "height": 180, "type": "room"},
    ...
]

connections = [
    {"from": 0, "to": 1, "corridor_length": 80},
    {"from": 1, "to": 2, "corridor_length": 60},
    {"from": 1, "to": 3, "corridor_length": 100},
    ...
]
```

### 2단계: Location 변환

각 방(Room)을 Location으로 변환한다.

```python
def create_locations_from_rooms(region_id, rooms):
    """2D Room 목록 → Location 생성"""
    for room in rooms:
        location_id = room["id"]
        # Room의 width를 Location의 length로 사용
        morld.add_location(
            region_id, location_id,
            name=f"구역-{location_id}",
            stay_duration=0,
            is_indoor=True,
            geometry="line",
            length=room["width"],
        )
        # 2D 좌표를 Location prop에 저장 (미니맵용)
        morld.set_location_prop(region_id, location_id, "map:x", room["x"])
        morld.set_location_prop(region_id, location_id, "map:y", room["y"])
        morld.set_location_prop(region_id, location_id, "map:type", room["type"])
```

### 3단계: Gate 생성

방 간 연결(Connection)을 Gate로 변환한다.

```python
def create_gates_from_connections(region_id, rooms, connections):
    """Connection 목록 → Gate 생성"""
    gate_id = 0
    for conn in connections:
        room_a = rooms[conn["from"]]
        room_b = rooms[conn["to"]]

        # Gate 위치: 각 방의 끝점
        gate_x_a = room_a["width"]   # 방 A의 오른쪽 끝
        arrival_x_b = 0              # 방 B의 왼쪽 끝

        # 양방향 Gate 생성
        morld.add_gate(
            region_id, conn["from"], gate_id, gate_x_a,
            region_id, conn["to"], arrival_x_b,
            travel_time=conn["corridor_length"],  # 통로 이동 시간
        )
        gate_id += 1

        # 역방향
        morld.add_gate(
            region_id, conn["to"], gate_id, 0,
            region_id, conn["from"], room_a["width"],
            travel_time=conn["corridor_length"],
        )
        gate_id += 1
```

### 4단계: 콘텐츠 배치

생성된 Location에 적, 자원, 환경 위협을 배치한다.

```python
def populate_rooms(region_id, rooms, difficulty):
    """방에 콘텐츠 배치"""
    for room in rooms:
        loc_id = room["id"]

        if room["type"] == "entrance":
            # 입구: 안전 지대
            continue

        # 적 배치 (위협 코드에 따라)
        if random.random() < difficulty.enemy_chance:
            threat_code = random.choice(["P", "R", "B", "W"])
            morld.set_location_prop(region_id, loc_id, f"threat:{threat_code}", 1)
            # 스포너 오브젝트 배치 (CreatureAgent 재활용)
            place_spawner(region_id, loc_id, threat_code)

        # 환경 위협 (Code B 계열)
        if random.random() < difficulty.hazard_chance:
            hazard = random.choice(["spore_fog", "tick_swarm", "toxic_gas"])
            morld.set_location_prop(region_id, loc_id, f"hazard:{hazard}", 1)

        # 자원 배치
        if random.random() < difficulty.loot_chance:
            morld.set_location_prop(region_id, loc_id, "storage:loot", 1)
            place_loot_container(region_id, loc_id)

        # 환경 시스템 등록 (온도/오염/습도 자동 적용)
        temperature.register_location(region_id, loc_id)
        pollution.register_location(region_id, loc_id)
```

### 5단계: 시각화 데이터 출력

2D 좌표를 보존하여 미니맵/탐사 UI에 전달한다.

```python
def get_minimap_data(region_id, rooms, connections):
    """미니맵 렌더링용 데이터"""
    return {
        "rooms": [
            {
                "id": r["id"],
                "x": r["x"], "y": r["y"],
                "width": r["width"], "height": r["height"],
                "type": r["type"],
                "explored": is_explored(region_id, r["id"]),
            }
            for r in rooms
        ],
        "connections": connections,
    }
```

---

## BSP 알고리즘 개요

```
1. 전체 공간을 직사각형으로 정의
2. 재귀적으로 수직/수평 분할
   - 분할 위치: 30~70% 랜덤
   - 최소 크기 도달 시 분할 중단
3. 각 리프 노드에 방(Room) 배치
   - 방 크기: 리프 크기의 60~90%
   - 방 위치: 리프 내 랜덤 배치
4. 형제 노드 간 통로(Connection) 생성
   - 가장 가까운 점 연결
```

```python
class BSPNode:
    def __init__(self, x, y, width, height):
        self.x, self.y = x, y
        self.width, self.height = width, height
        self.left = None   # 분할 후 좌측/상단
        self.right = None  # 분할 후 우측/하단
        self.room = None   # 리프 노드의 방

    def split(self, min_size=100):
        if self.width < min_size * 2 and self.height < min_size * 2:
            return False  # 더 이상 분할 불가

        # 수직/수평 분할 결정
        if self.width > self.height * 1.25:
            split_vertical = True
        elif self.height > self.width * 1.25:
            split_vertical = False
        else:
            split_vertical = random.random() > 0.5

        # 분할 위치 (30~70%)
        ratio = random.uniform(0.3, 0.7)

        if split_vertical:
            split_pos = int(self.width * ratio)
            self.left = BSPNode(self.x, self.y, split_pos, self.height)
            self.right = BSPNode(self.x + split_pos, self.y,
                                self.width - split_pos, self.height)
        else:
            split_pos = int(self.height * ratio)
            self.left = BSPNode(self.x, self.y, self.width, split_pos)
            self.right = BSPNode(self.x, self.y + split_pos,
                                self.width, self.height - split_pos)
        return True
```

---

## 시나리오별 맵 특성

### 시나리오03 탐사 지역

| 심(深) | 맵 특성 | 방 개수 | 난이도 |
|--------|---------|---------|--------|
| 1심 (박층) | 넓은 통로, 분기 적음 | 5~8 | 낮음 |
| 2심 (본심) | 중간 밀도, 분기 있음 | 8~15 | 중간 |
| 3심 (심저) | 좁은 통로, 복잡한 분기 | 12~20 | 높음 |

### 시나리오02 던전 (호환)

기존 수동 정의 던전(Region 5 등)은 변경 없이 유지. 동적 생성은 새로운 Region에만 적용하여 기존 코드에 영향 없음.

---

## 전쟁의 안개 (Fog of War)

### 탐사 진행과 시야

- **미탐사 방**: 미니맵에 표시되지 않음
- **탐사 중인 방**: 분대원 위치 + 적 위치 표시
- **탐사 완료 방**: 구조만 표시, 실시간 정보 없음

구현: Location prop `explored` (0/1) + 분대원 현재 Location 기준 시야.

### CRT 연출과의 연동

미니맵은 CRT 모니터 스타일로 렌더링된다:
- 탐사 중인 방: 선명한 표시
- 인접 방: 노이즈 섞인 흐린 표시
- 먼 방: 표시 안 됨 (통신 범위 밖)

---

## 탐사 완료 후 정리

탐사가 끝나면 동적 생성된 Region을 정리한다.

```python
def cleanup_expedition(region_id):
    """탐사 완료 후 동적 Region 삭제"""
    # 환경 시스템 등록 해제
    temperature.unregister_region(region_id)
    pollution.unregister_region(region_id)

    # Region 삭제 (Location, Gate, Object 포함)
    morld.remove_region(region_id)
```

---

## 미정 사항

- [ ] BSP vs Force-Directed 알고리즘 최종 선택
- [ ] 방 타입별 템플릿 정의 (입구/통로/넓은 방/보스 방)
- [ ] Gate 조건 (잠긴 문, 해킹 필요 등) 생성 규칙
- [ ] 난이도 파라미터 밸런싱
- [ ] 미니맵 UI 설계 (C# TextUI 확장)
- [ ] `remove_region` C# API 존재 여부 확인 (없으면 추가 필요)
- [ ] 시드 기반 재현 가능성 테스트
