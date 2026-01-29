# 지도 시스템 (계획)

플레이어가 지도를 통해 목적지를 선택하고 루트를 따라 이동하는 시스템입니다.

---

## 현재 상태

### 이동 방식
- 플레이어가 한 노드씩 직접 이동
- Gate 클릭 → 인접 Location으로 이동
- 경로 계획 없이 즉시 이동

### Location 구조
```python
class Location:
    id: int
    name: str
    region_id: int      # 소속 Region
    gates: list[Gate]   # 연결된 Gate 목록
```

---

## 목표 시스템

### 1. Map 기반 계층 구조

```
World
├── Region 0 (저택)
│   ├── Map 0 (저택 내부)
│   │   ├── Location 0 (현관)
│   │   ├── Location 1 (거실)
│   │   └── ...
│   └── Map 1 (저택 외부/숲)
│       ├── Location 12 (앞마당)
│       ├── Location 20 (숲 입구)
│       └── ...
└── Region 1 (도시)
    └── Map 2 (도시)
        ├── Location 0 (도시 입구)
        └── ...
```

### 2. Location에 Map 참조 추가

```python
class Location:
    id: int
    name: str
    region_id: int
    map_id: int         # 소속 Map (NEW)
    gates: list[Gate]
```

### 3. 지도 UI 흐름

```
[지도 버튼 클릭]
    ↓
[현재 Map 표시]
    ↓
[목적지 Location 클릭]
    ↓
[경로 계산 (Dijkstra)]
    ↓
[루트 따라 자동 이동]
```

---

## 그래프 자동 배치 알고리즘

### 문제 정의
- 입력: Graph (Nodes + Gates), 해상도 (예: 900x1080)
- 출력: 각 Node의 2D 좌표 (x, y)
- 제약: 연결된 노드는 가깝게, Gate 교차 최소화

### 알고리즘 후보

#### 1. Force-Directed Layout (힘 기반 배치)
**원리:**
- 노드 간 척력 (모든 노드가 서로 밀어냄)
- Gate 연결 노드 간 인력 (스프링처럼 당김)
- 반복 시뮬레이션으로 평형점 수렴

**장점:**
- 구현 간단
- 연결 구조 자연스럽게 반영
- 동적 업데이트 가능

**단점:**
- 수렴 시간 필요
- 로컬 최적에 빠질 수 있음

**의사 코드:**
```python
def force_directed_layout(nodes, edges, width, height, iterations=100):
    # 초기 위치: 랜덤 또는 원형 배치
    for node in nodes:
        node.x = random(0, width)
        node.y = random(0, height)

    for _ in range(iterations):
        # 척력: 모든 노드 쌍
        for n1 in nodes:
            for n2 in nodes:
                if n1 != n2:
                    dx, dy = n1.x - n2.x, n1.y - n2.y
                    dist = sqrt(dx*dx + dy*dy)
                    force = REPULSION / (dist * dist)
                    n1.vx += force * dx / dist
                    n1.vy += force * dy / dist

        # 인력: Gate로 연결된 노드
        for edge in edges:
            n1, n2 = edge.from_node, edge.to_node
            dx, dy = n2.x - n1.x, n2.y - n1.y
            dist = sqrt(dx*dx + dy*dy)
            force = ATTRACTION * dist
            n1.vx += force * dx / dist
            n2.vx -= force * dx / dist
            # ... y도 동일

        # 위치 업데이트 + 경계 제한
        for node in nodes:
            node.x = clamp(node.x + node.vx * dt, 0, width)
            node.y = clamp(node.y + node.vy * dt, 0, height)
            node.vx *= DAMPING
            node.vy *= DAMPING

    return [(n.x, n.y) for n in nodes]
```

#### 2. Kamada-Kawai Algorithm
**원리:**
- 그래프 거리(최단 경로 길이)를 2D 거리로 매핑
- 에너지 함수 최소화

**장점:**
- Force-Directed보다 안정적
- 전역 구조 잘 보존

**단점:**
- 계산량 많음 (O(n³))
- 노드 수 많으면 느림

#### 3. Fruchterman-Reingold Algorithm
**원리:**
- Force-Directed의 개선판
- 온도 개념 도입 (점진적 수렴)

**장점:**
- Force-Directed보다 균일한 배치
- 수렴 보장

**권장:** 노드 수가 적으면 (< 50개) Force-Directed로 충분

---

## Godot 구현 계획

### 1. 컴포넌트 구조

```
MapView (Control)
├── MapBackground (TextureRect) - 배경 이미지 (선택)
├── GateContainer (Node2D)
│   └── GateLine (Line2D) × N
└── NodeContainer (Node2D)
    └── LocationNode (Button) × N
```

### 2. LocationNode 컴포넌트

```gdscript
# LocationNode.gd
extends Button

var location_id: int
var location_name: String

func _ready():
    text = location_name
    connect("pressed", self, "_on_pressed")

func _on_pressed():
    emit_signal("location_selected", location_id)
```

### 3. MapView 컴포넌트

```gdscript
# MapView.gd
extends Control

signal destination_selected(location_id)

var current_map_id: int
var node_positions: Dictionary  # location_id -> Vector2

func show_map(map_id: int):
    current_map_id = map_id
    var locations = get_locations_for_map(map_id)
    var gates = get_gates_for_map(map_id)

    # 자동 배치 계산
    node_positions = calculate_layout(locations, gates, size)

    # 노드/게이트 생성
    _create_gate_lines(gates)
    _create_location_nodes(locations)

func calculate_layout(locations, gates, viewport_size) -> Dictionary:
    # Force-Directed 알고리즘 호출
    return ForceDirectedLayout.calculate(
        locations, gates,
        viewport_size.x, viewport_size.y
    )
```

### 4. C# 연동

```csharp
// MapSystem.cs
public class MapSystem : ISystem
{
    public List<Vector2> CalculateLayout(int mapId, int width, int height)
    {
        var locations = GetLocationsForMap(mapId);
        var gates = GetGatesForMap(mapId);

        // Force-Directed 실행
        var layout = new ForceDirectedLayout(width, height);
        return layout.Calculate(locations, gates);
    }
}
```

---

## 동적 업데이트 지원

### 인게임 지도 변경 시나리오
1. 새 Location 발견 → 노드 추가
2. 길 개통/봉쇄 → Gate 추가/제거
3. 맵 확장 → 해상도 재계산

### 점진적 레이아웃 업데이트

```python
def update_layout_incremental(existing_positions, new_node, new_gates):
    """
    기존 노드 위치 유지하면서 새 노드만 배치
    """
    # 새 노드 초기 위치: 연결된 노드들의 평균
    connected = [existing_positions[e.other] for e in new_gates]
    new_node.x = avg([p.x for p in connected])
    new_node.y = avg([p.y for p in connected])

    # 짧은 Force-Directed 반복 (새 노드만 이동)
    for _ in range(20):
        apply_forces(new_node, all_nodes, new_gates)
        # 기존 노드는 고정, 새 노드만 이동

    return new_node.x, new_node.y
```

---

## 구현 우선순위

| 단계 | 내용 | 의존성 |
|------|------|--------|
| 1 | Location.map_id 필드 추가 | - |
| 2 | Force-Directed 알고리즘 구현 (C#) | - |
| 3 | MapView Godot 컴포넌트 | 1, 2 |
| 4 | 지도 버튼 → 목적지 선택 UI | 3 |
| 5 | 경로 계산 + 자동 이동 | 4 |
| 6 | 점진적 레이아웃 업데이트 | 2 |

---

## 참고: 라이브러리/알고리즘

### Force-Directed 참고 자료
- [D3.js Force Layout](https://d3js.org/d3-force)
- [Graphviz neato](https://graphviz.org/docs/layouts/neato/)
- Fruchterman-Reingold 논문 (1991)

### Godot 관련
- GraphEdit (노드 기반 에디터용, 참고용)
- Line2D (Gate 렌더링)
- Control (레이아웃 컨테이너)

---

## 파일 위치 (예상)

### C#
- `scripts/system/map_system.cs` - 레이아웃 계산
- `scripts/morld/terrain/Map.cs` - Map 데이터 구조
- `scripts/morld/layout/ForceDirectedLayout.cs` - 배치 알고리즘

### Godot
- `scenes/ui/MapView.tscn` - 지도 UI 씬
- `scripts/ui/MapView.cs` - 지도 컨트롤러
- `scripts/ui/LocationNode.cs` - 위치 노드 버튼

### Python
- `world/*.py` - Location에 map_id 추가
