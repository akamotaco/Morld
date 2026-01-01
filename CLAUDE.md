# Morld - ECS 기반 캐릭터 시뮬레이션 시스템

## 프로젝트 개요

Morld는 ECS(Entity Component System) 아키텍처를 기반으로 한 게임 월드 시뮬레이션 시스템입니다.
캐릭터의 일정(Schedule)에 따라 자동으로 경로를 계획하고 이동하는 시스템을 제공합니다.

**핵심 기술:**
- Godot 4 엔진
- C# .NET
- ECS 아키텍처
- JSON 기반 데이터 관리
- Dijkstra Pathfinding

---

## 아키텍처 원칙

### ECS 시스템의 두 가지 역할

#### 1. Data Management Systems (데이터 관리 시스템)
게임 상태(persistent state)를 저장하고 관리하는 시스템

**특징:**
- ✅ JSON Import/Export (`UpdateFromFile()`, `SaveToFile()`)
- ❌ Proc 함수 없음 (순수 데이터 저장소)
- 세이브/로드 대상
- 게임 데이터의 원천(Source of Truth)

**구현 시스템:**
- `WorldSystem` - 지형(Terrain) 데이터 및 GameTime 보관
- `CharacterSystem` - 캐릭터 데이터 (위치, 스케줄, CurrentEdge, Inventory)
- `ItemSystem` - 아이템 정의 데이터 (PassiveTags, EquipTags)

#### 2. Logic/Behavior Systems (로직 시스템)
매 Step마다 게임 로직을 실행하는 시스템

**특징:**
- ❌ JSON Import/Export 없음
- ✅ Proc 함수 구현 (`Proc(int step, Span<Component[]> allComponents)`)
- Data Systems의 데이터를 읽고 수정
- 런타임 데이터만 보관 (ActionQueue 등)

**구현 시스템:**
- `MovementSystem` - ActionQueue 소비 및 캐릭터 이동 처리, GameTime 업데이트
- `PlanningSystem` - 캐릭터 스케줄 기반 ActionQueue 생성, 자정까지 계획
- `PlayerSystem` - 플레이어 입력 기반 시간 진행 제어, Look 기능
- `DescribeSystem` - 묘사 텍스트 생성 (시간 기반 키 선택)

### 시스템 실행 순서

```
MovementSystem → PlanningSystem → PlayerSystem → DescribeSystem
```

### 데이터 흐름

```
┌─────────────────────┐
│   GameEngine        │
│  _Ready()           │
└──────────┬──────────┘
           │
           ├─> WorldSystem.UpdateFromFile("location_data.json")
           ├─> WorldSystem.GetTime().UpdateFromFile("time_data.json")
           ├─> CharacterSystem.UpdateFromFile("character_data.json")
           ├─> ItemSystem.UpdateFromFile("item_data.json")
           ├─> PlayerSystem.UpdateFromFile("player_data.json")
           │
           ├─> MovementSystem 등록
           ├─> PlanningSystem 등록
           ├─> PlayerSystem 등록
           └─> DescribeSystem 등록
```

---

## 시스템 상세

### WorldSystem (Data System)
**역할:** 게임의 지형(Terrain) 데이터 및 시간 보관

**주요 기능:**
- Region 및 Location 그래프 관리
- Edge를 통한 이동 시간 정보
- RegionEdge를 통한 Region 간 연결
- GameTime 보관 (시간 업데이트는 MovementSystem에서 수행)
- JSON 기반 Import/Export

**데이터 구조:**
```csharp
Terrain
├─ Region[] (여러 지역)
│  └─ Location[] (각 지역의 장소들)
│     ├─ Edge[] (장소 간 연결 및 이동 시간)
│     └─ Description (Dictionary<string, string> - 상황별 묘사)
└─ RegionEdge[] (지역 간 연결)

GameTime (시간 관리)
├─ _year, _month, _day (날짜)
├─ _minuteOfDay (0~1439, hour/minute 통합)
├─ Calendar (달력 설정)
├─ Holidays (휴일 정보)
└─ GetCurrentTags() (시간대/계절/기념일 태그 반환)
```

**파일 위치:**
- `scripts/system/world_system.cs`
- `scripts/morld/terrain/` (Terrain, Region, Location, Edge, RegionEdge)
- `scripts/morld/schedule/GameTime.cs`

### CharacterSystem (Data System)
**역할:** 게임 내 모든 캐릭터의 데이터 관리

**주요 기능:**
- 캐릭터 생성/삭제/조회
- Dictionary<int, Character> 기반 O(1) 조회
- 캐릭터 위치, 스케줄, CurrentEdge, Inventory 관리
- JSON 기반 Import/Export (CurrentEdge, Inventory, EquippedItems 포함)

**데이터 구조:**
```csharp
Character
├─ Id (int - 고유 식별자)
├─ Name (이름)
├─ CurrentLocation (현재 위치 - LocationRef)
├─ CurrentEdge (이동 중 Edge 진행 상태 - EdgeProgress?)
├─ CurrentSchedule (현재 수행 중인 스케줄)
├─ Schedule (일일 스케줄 - DailySchedule)
│  └─ ScheduleEntry[] (시간대별 일정)
├─ TraversalContext (기본 태그/스탯)
├─ Inventory (Dictionary<int, int> - 아이템ID → 개수)
├─ EquippedItems (List<int> - 장착된 아이템 ID)
├─ GetActualTags(ItemSystem) (아이템 효과 반영된 최종 태그)
├─ CanPass(conditions, ItemSystem) (조건 충족 여부)
├─ IsMoving (CurrentEdge != null)
└─ IsIdle (CurrentEdge == null)
```

**파일 위치:**
- `scripts/system/character_system.cs`
- `scripts/morld/character/Character.cs`
- `scripts/morld/character/ActionLog.cs` (ActionLog, EdgeProgress)
- `scripts/morld/schedule/` (DailySchedule, ScheduleEntry)

### ItemSystem (Data System)
**역할:** 게임 내 아이템 정의 관리

**주요 기능:**
- 아이템 정의 조회 (ID 기반)
- PassiveTags (소유 효과) 및 EquipTags (장착 효과) 관리
- JSON 기반 Import/Export

**데이터 구조:**
```csharp
Item
├─ Id (int - 고유 식별자)
├─ Name (이름)
├─ PassiveTags (Dictionary<string, int> - 소유만으로 효과)
└─ EquipTags (Dictionary<string, int> - 장착 시 효과)
```

**아이템 효과 예시:**
| 아이템 | PassiveTags | EquipTags | 설명 |
|--------|-------------|-----------|------|
| 열쇠 | `{"열쇠": 1}` | - | 소유만으로 문 통과 |
| 망원경 | - | `{"관찰": 2}` | 장착해야 관찰력 증가 |

**파일 위치:**
- `scripts/system/item_system.cs`
- `scripts/morld/item/Item.cs`
- `scripts/morld/item/ItemJsonFormat.cs`

### MovementSystem (Logic System)
**역할:** PlanningSystem의 ActionQueue를 소비하여 캐릭터 이동 처리

**실행 로직:**
1. PlanningSystem에서 NextStepDuration 읽기
2. NextStepDuration = 0이면 스킵 (첫 Step)
3. 각 캐릭터에 대해:
   - ActionQueue 가져오기
   - 시간 범위 내 Action 순회 및 실행
   - 이동 완료 시 CurrentLocation 업데이트
   - 이동 중단 시 CurrentEdge에 진행 상태 저장
4. GameTime을 NextStepDuration만큼 증가

**파일 위치:**
- `scripts/system/movement_system.cs`

### PlanningSystem (Logic System)
**역할:** 캐릭터의 스케줄을 분석하여 ActionQueue 생성, 자정 제한 관리

**주요 필드:**
```csharp
public int NextStepDuration { get; private set; } = 0;  // 다음 Step 진행 시간 (분)
public int MinutesToMidnight { get; private set; }       // 자정까지 남은 시간
private Dictionary<int, List<ActionLog>> _actionQueues;  // 캐릭터별 ActionQueue
```

**PathFinding:**
- Dijkstra 알고리즘 기반
- `FindPath(start, goal, character, itemSystem)` - Character + ItemSystem 기반 조건 체크
- 내부에서 `character.GetActualTags(itemSystem)` 호출하여 아이템 효과 반영

**파일 위치:**
- `scripts/system/planning_system.cs`
- `scripts/morld/pathfinding/PathFinder.cs` (경로 탐색 알고리즘)

### PlayerSystem (Logic System)
**역할:** 플레이어 입력 기반 시간 진행 제어, Look 기능

**주요 필드:**
```csharp
public int PlayerId { get; set; } = 0;     // 조작할 캐릭터 ID
private int _remainingDuration = 0;         // 남은 처리 시간 (분)
private int _lastSetDuration = 0;           // 1-Step Delay용
```

**Look 기능:**
```csharp
public LookResult Look()
// 반환:
// - Location: 현재 위치 정보 (묘사 포함)
// - CharacterIds: 같은 위치의 캐릭터 ID 목록
// - Routes: 이동 가능한 경로 목록 (조건 필터링 적용)
```

**RouteInfo 구조:**
```csharp
RouteInfo
├─ LocationName (목적지 이름)
├─ RegionName (다른 Region일 경우)
├─ Destination (LocationRef)
├─ TravelTime (이동 시간, 분)
├─ IsRegionEdge (Region 간 이동 여부)
├─ IsBlocked (조건 미충족 시 true)
└─ BlockedReason (불가 사유)
```

**저장/로드:**
- `UpdateFromFile(filePath)` - player_data.json에서 PlayerId 로드
- `SaveToFile(filePath)` - PlayerId 저장

**파일 위치:**
- `scripts/system/player_system.cs`
- `scripts/morld/player/LookResult.cs`
- `scripts/morld/player/PlayerJsonFormat.cs`

### DescribeSystem (Logic System)
**역할:** 묘사 텍스트 생성 (시간 기반 키 선택)

**주요 기능:**
- `GetLocationDescription(location, time)` - Location 묘사 반환
- `GetRegionDescription(region, time)` - Region 묘사 반환
- GameTime.GetCurrentTags()로 시간대/계절/기념일 태그 확인
- Description Dictionary에서 가장 많은 태그가 매칭되는 키 선택

**Description 키 예시:**
```json
{
  "description": {
    "default": "마을 광장입니다.",
    "아침": "아침 햇살이 비추는 광장입니다.",
    "겨울,밤": "차가운 겨울 밤, 광장이 고요합니다."
  }
}
```

**파일 위치:**
- `scripts/system/describe_system.cs`
- `scripts/morld/IDescribable.cs` (인터페이스)

---

## JSON 데이터 포맷

### location_data.json (WorldSystem)
```json
{
  "regions": [
    {
      "id": 0,
      "name": "마을",
      "description": {
        "default": "평화로운 마을입니다."
      },
      "locations": [
        {
          "id": 0,
          "name": "광장",
          "description": {
            "default": "마을 중심의 광장입니다.",
            "아침": "상인들이 가판대를 펼치고 있습니다."
          }
        }
      ],
      "edges": [
        { "a": 0, "b": 1, "travelTime": 5 }
      ]
    }
  ],
  "regionEdges": [
    {
      "id": 0,
      "locationA": { "regionId": 0, "localId": 3 },
      "locationB": { "regionId": 1, "localId": 0 },
      "travelTimeAtoB": 30,
      "travelTimeBtoA": 30
    }
  ]
}
```

### character_data.json (CharacterSystem)
```json
[
  {
    "id": 0,
    "name": "플레이어",
    "comment": "player",
    "regionId": 0,
    "locationId": 0,
    "tags": {
      "관찰": 3,
      "힘": 5
    },
    "inventory": {
      "0": 1,
      "1": 3
    },
    "equippedItems": [2, 3],
    "schedule": []
  },
  {
    "id": 1,
    "name": "철수",
    "comment": "npc_001",
    "regionId": 0,
    "locationId": 0,
    "schedule": [
      { "name": "아침식사", "regionId": 1, "locationId": 0, "start": 420, "end": 480, "activity": "식사" }
    ]
  }
]
```

### item_data.json (ItemSystem)
```json
[
  {
    "id": 0,
    "name": "녹슨 열쇠",
    "comment": "rusty_key",
    "passiveTags": { "열쇠": 1 },
    "equipTags": {}
  },
  {
    "id": 2,
    "name": "망원경",
    "comment": "telescope",
    "passiveTags": {},
    "equipTags": { "관찰": 2 }
  }
]
```

### player_data.json (PlayerSystem)
```json
{
  "playerId": 0
}
```

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ system/ (ECS Systems)
│  ├─ world_system.cs (WorldSystem - Data)
│  ├─ character_system.cs (CharacterSystem - Data)
│  ├─ item_system.cs (ItemSystem - Data)
│  ├─ movement_system.cs (MovementSystem - Logic)
│  ├─ planning_system.cs (PlanningSystem - Logic)
│  ├─ player_system.cs (PlayerSystem - Logic)
│  └─ describe_system.cs (DescribeSystem - Logic)
├─ morld/ (Core Data Structures)
│  ├─ IDescribable.cs (묘사 인터페이스)
│  ├─ terrain/
│  │  ├─ Terrain.cs
│  │  ├─ Region.cs (IDescribable)
│  │  ├─ Location.cs (IDescribable)
│  │  ├─ Edge.cs
│  │  └─ RegionEdge.cs
│  ├─ character/
│  │  ├─ Character.cs (Inventory, EquippedItems, GetActualTags)
│  │  ├─ ActionLog.cs (ActionLog, EdgeProgress)
│  │  └─ CharacterJsonFormat.cs
│  ├─ item/
│  │  ├─ Item.cs (PassiveTags, EquipTags)
│  │  └─ ItemJsonFormat.cs
│  ├─ player/
│  │  ├─ LookResult.cs (LookResult, LocationInfo, RouteInfo)
│  │  └─ PlayerJsonFormat.cs
│  ├─ pathfinding/
│  │  └─ PathFinder.cs (Character + ItemSystem 기반)
│  └─ schedule/
│     ├─ GameTime.cs (GetCurrentTags)
│     ├─ DailySchedule.cs
│     ├─ ScheduleEntry.cs
│     └─ TimeRange.cs
├─ simple_engine/
│  ├─ ecs.cs (ECS 기반 클래스)
│  └─ world.cs (SE.World, ECS 허브)
└─ json_data/ (게임 데이터)
   ├─ location_data.json
   ├─ time_data.json
   ├─ character_data.json
   ├─ item_data.json
   └─ player_data.json
```

---

## 핵심 개념 정리

### GetActualTags() - 아이템 효과 통합
```csharp
// Character.GetActualTags(itemSystem)
// 1. 기본 Tags 복사
// 2. + Inventory 아이템의 PassiveTags (소유 효과)
// 3. + EquippedItems의 EquipTags (장착 효과)

var actualTags = character.GetActualTags(itemSystem);
// 열쇠(PassiveTags: 열쇠:1) 소유 → actualTags["열쇠"] = 1
// 망원경(EquipTags: 관찰:2) 장착 + 기본 관찰:3 → actualTags["관찰"] = 5
```

### 조건 체크 흐름
```csharp
// Edge 조건: { "열쇠": 1, "관찰": 4 }
var conditions = edge.GetConditions(location);
var canPass = character.CanPass(conditions, itemSystem);
// → GetActualTags()로 아이템 효과 포함하여 체크
```

### Look 기능
```csharp
var result = playerSystem.Look();
// result.Location: 현재 위치 정보 (DescribeSystem으로 묘사 생성)
// result.CharacterIds: 같은 위치의 NPC ID 목록
// result.Routes: 이동 가능한 경로 (IsBlocked, BlockedReason 포함)
```

---

## 빌드 및 실행

### 빌드
```bash
dotnet build
```

### 디버그 로그
`#define DEBUG_LOG` 활성화 시:
- **초기화:** World 구조, GameTime 정보, Character 목록 및 스케줄, System 개수 출력
- **런타임:** MovementSystem에서 시간 진행 및 캐릭터 상태 출력
- **런타임:** PlayerSystem에서 시간 요청/완료 로그

### 실행
Godot 에디터에서 프로젝트 실행

---

## 세이브/로드

저장 대상:
- `WorldSystem` → location_data.json, time_data.json
- `CharacterSystem` → character_data.json (CurrentLocation, CurrentEdge, Inventory, EquippedItems 포함)
- `ItemSystem` → item_data.json
- `PlayerSystem` → player_data.json

저장 불필요:
- `MovementSystem`, `PlanningSystem` → 재실행 시 자동 재생성
- `DescribeSystem` → Stateless
