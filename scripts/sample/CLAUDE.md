# PathFinding Library

.NET 8.0 기반의 계층적 월드 구조와 NPC 시뮬레이션을 위한 경로 탐색 라이브러리.

## 프로젝트 구조

```
PathFinding/
├── Models/           # 핵심 데이터 모델
│   ├── World.cs      # 최상위 월드 컨테이너
│   ├── Region.cs     # 지역 (Location 그룹)
│   ├── Location.cs   # 개별 위치
│   ├── Edge.cs       # Region 내부 연결
│   ├── RegionEdge.cs # Region 간 연결
│   ├── RegionBuilder.cs
│   └── ValidationResult.cs
├── Core/
│   └── PathFinder.cs # Dijkstra 경로 탐색
├── Game/             # 게임 시뮬레이션
│   ├── GameWorld.cs  # 시뮬레이션 컨트롤러
│   ├── GameTime.cs   # 게임 내 시간
│   ├── NPC.cs        # NPC 엔티티
│   └── Schedule.cs   # 일일 스케줄
├── Serialization/
│   ├── WorldSerializer.cs  # JSON 직렬화
│   └── DebugPrinter.cs     # 디버그 출력
├── Data/
│   ├── world_data.json     # 월드 데이터
│   └── npc_data.json       # NPC 데이터
└── Program.cs        # 시뮬레이션 데모
```

## 핵심 개념

### 계층 구조

```
World
├── Region (id: int)
│   ├── Location (localId: int)
│   └── Edge (Location ↔ Location)
└── RegionEdge (Region ↔ Region)
```

- **World**: 전체 게임 월드. 여러 Region과 RegionEdge를 포함
- **Region**: 논리적 지역 단위. 내부에 Location과 Edge를 포함
- **Location**: 실제 위치. `(RegionId, LocalId)` 쌍으로 고유 식별
- **Edge**: 같은 Region 내 Location 간 연결
- **RegionEdge**: 서로 다른 Region의 Location을 연결

### ID 체계

| 타입 | ID 타입 | 범위 |
|------|---------|------|
| Region | `int` | World 내 고유 |
| Location | `int` (LocalId) | Region 내 고유 |
| RegionEdge | `int` | World 내 고유 |

위치 참조는 `LocationRef` 구조체 사용:
```csharp
var locRef = new LocationRef(regionId: 0, localId: 1);
```

### 양방향 Edge

모든 Edge는 양방향이며 방향별로 다른 속성 가능:
```csharp
edge.TravelTimeAtoB = 10f;  // A→B 이동 시간
edge.TravelTimeBtoA = 15f;  // B→A 이동 시간
edge.AddConditionAtoB("열쇠", 1);  // A→B 조건
```

## 주요 API

### World 생성

```csharp
var world = new World("마을");

// Region 추가
var region = new Region(0, "주거지역");
region.AddLocation(0, "집");
region.AddLocation(1, "광장");
region.AddEdge(0, 1, travelTime: 10f);
world.AddRegion(region);

// 또는 직접 추가
world.AddRegion(1, "상업지역");
var region2 = world.GetRegion(1);

// RegionEdge 추가 (Region 간 연결)
world.AddRegionEdge(
    edgeId: 0,
    regionIdA: 0, localIdA: 1,  // 주거지역 광장
    regionIdB: 1, localIdB: 0,  // 상업지역 입구
    travelTimeAtoB: 8f
);
```

### 경로 탐색

```csharp
var pathFinder = new PathFinder(world);

// Region 내부 경로
var result = pathFinder.FindPath(
    startRegionId: 0, startLocalId: 0,
    goalRegionId: 0, goalLocalId: 4
);

// Region 간 경로
var crossResult = pathFinder.FindPath(
    startRegionId: 0, startLocalId: 0,
    goalRegionId: 1, goalLocalId: 2
);

if (result.Success)
{
    Console.WriteLine($"경로: {string.Join(" → ", result.Path)}");
    Console.WriteLine($"총 시간: {result.TotalTime}");
}
```

### NPC 시뮬레이션

```csharp
var gameWorld = new GameWorld(world, stepMinutes: 15);

// NPC 추가
var npc = gameWorld.AddNPC("npc_001", "철수", regionId: 0, localId: 0);

// 스케줄 추가 (시간은 분 단위, 0-1439)
npc.Schedule.AddEntry("아침식사", regionId: 1, localId: 0, start: 420, end: 480);
npc.Schedule.AddEntry("근무", regionId: 1, localId: 1, start: 540, end: 1080);

// 시뮬레이션 실행
gameWorld.SetTime(month: 1, day: 1, hour: 6, minute: 0);
var result = gameWorld.Step();  // 15분 진행
```

### 이벤트 처리

```csharp
gameWorld.OnNPCMovementStart += (gw, e) =>
{
    Console.WriteLine($"{e.Movement.NPC.Name} 이동 시작");
};

gameWorld.OnNPCArrival += (gw, e) =>
{
    Console.WriteLine($"{e.Arrival.NPC.Name} 도착: {e.Arrival.Destination}");
};
```

### JSON 직렬화

```csharp
// 분리 로드
var gameWorld = WorldSerializer.LoadWorldFromFile("world_data.json");
var validation = WorldSerializer.ValidateNPCFile(gameWorld.World, "npc_data.json");
if (validation.IsValid)
{
    WorldSerializer.LoadNPCsFromFile(gameWorld, "npc_data.json");
}

// 분리 저장
WorldSerializer.SaveWorldToFile(gameWorld, "world_save.json");
WorldSerializer.SaveNPCsToFile(gameWorld, "npc_save.json");

// 통합 저장/로드
WorldSerializer.SaveToFile(gameWorld, "game_save.json");
var loaded = WorldSerializer.LoadFromFile("game_save.json");
```

### 디버그 출력

```csharp
// 콘솔 출력
DebugPrinter.DumpWorld(world);
DebugPrinter.DumpNPCs(gameWorld);
DebugPrinter.DumpGameWorld(gameWorld, detailed: true);

// 문자열로 받기
string summary = DebugPrinter.PrintWorld(world);
string graph = DebugPrinter.PrintWorldGraph(world);
```

## JSON 스키마

### world_data.json

```json
{
  "world": {
    "name": "마을",
    "regions": [
      {
        "id": 0,
        "name": "주거지역",
        "locations": [
          { "id": 0, "name": "집" }
        ],
        "edges": [
          { "a": 0, "b": 1, "timeAtoB": 10, "timeBtoA": 10 }
        ]
      }
    ],
    "regionEdges": [
      {
        "id": 0,
        "regionA": 0, "localA": 1,
        "regionB": 1, "localB": 0,
        "timeAtoB": 8, "timeBtoA": 8
      }
    ]
  },
  "gameTime": { "month": 1, "day": 1, "hour": 6, "minute": 0 },
  "settings": { "stepMinutes": 15 }
}
```

### npc_data.json

```json
{
  "npcs": [
    {
      "id": "npc_001",
      "name": "철수",
      "regionId": 0,
      "locationId": 0,
      "tags": { "열쇠": 1 },
      "schedule": [
        {
          "name": "아침식사",
          "regionId": 1,
          "locationId": 0,
          "start": 420,
          "end": 480
        }
      ]
    }
  ]
}
```

## 시간 표현

- 게임 내 시간은 **분 단위 정수** (0-1439)
- `420` = 07:00, `1080` = 18:00
- 자정을 넘는 스케줄: `start: 1320, end: 360` (22:00 ~ 06:00)

```csharp
// GameTime 유틸리티
var time = new GameTime(month: 1, day: 1, hour: 7, minute: 30);
int minutes = time.TotalMinutesOfDay;  // 450
string str = time.ToTimeString();       // "07:30"
```

## NPC 상태

| 상태 | 설명 |
|------|------|
| `Idle` | 대기 중 (목적지 도착 또는 스케줄 없음) |
| `Moving` | 이동 중 |

```csharp
if (npc.IsMoving)
{
    var movement = npc.Movement;
    Console.WriteLine($"진행률: {movement.ProgressPercent}%");
    Console.WriteLine($"남은 시간: {movement.RemainingTime}분");
}
```

## 검증

NPC 데이터 검증:
```csharp
var result = WorldSerializer.ValidateNPCData(world, npcData);

if (!result.IsValid)
{
    foreach (var error in result.Errors)
        Console.WriteLine($"오류: {error}");
}

foreach (var warning in result.Warnings)
    Console.WriteLine($"경고: {warning}");
```

검증 항목:
- NPC 시작 위치 존재 여부 (Error)
- 스케줄 목적지 존재 여부 (Error)
- 시간 범위 유효성 0-1439 (Error)
- 스케줄 시간 겹침 (Warning)

## 확장 포인트

### TraversalContext

NPC별 이동 조건 태그:
```csharp
npc.TraversalContext.SetTag("열쇠", 1);
npc.TraversalContext.SetTag("수영가능", 1);

// Edge 조건과 매칭되어 경로 탐색에 영향
edge.AddConditionAtoB("열쇠", 1);  // 열쇠가 있어야 통과
```

### Change Tracking

World 변경 추적:
```csharp
world.ClearChanges();
// ... 수정 작업
var changedRegions = world.GetChangedRegions();
var changedEdges = world.GetChangedRegionEdges();
```

## 빌드 및 실행

```bash
dotnet build
dotnet run
```

실행 중 단축키:
- `W`: World 정보 출력
- `N`: NPC 정보 출력
- `D`: 전체 상세 정보
- `G`: World 그래프
- `S`: 분리 저장
- `A`: 통합 저장
- `Ctrl+C`: 종료
