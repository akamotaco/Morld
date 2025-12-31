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
- `CharacterSystem` - 캐릭터 데이터 (위치, 스케줄, CurrentEdge)

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
- `PlayerSystem` - 플레이어 입력 기반 시간 진행 제어

### 시스템 실행 순서

```
MovementSystem → PlanningSystem → PlayerSystem
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
           │
           ├─> MovementSystem 등록
           ├─> PlanningSystem 등록
           └─> PlayerSystem 등록

┌─────────────────────┐
│   GameEngine        │
│  _Input()           │
└──────────┬──────────┘
           │
           └─> PlayerSystem.RequestTimeAdvance(minutes, actionName)
                 └─> _remainingDuration += minutes

┌─────────────────────┐
│   GameEngine        │
│  _Process(delta)    │
└──────────┬──────────┘
           │
           ├─> PlayerSystem.HasPendingTime 확인
           │     └─> false면 Step 스킵 (시간 정지)
           │
           └─> ECS.World.Step(deltaTime)
                 │
                 ├─> MovementSystem.Proc()
                 │     ├─> PlanningSystem.NextStepDuration 읽기
                 │     ├─> ActionQueue 소비 → Character 위치 업데이트
                 │     └─> GameTime 업데이트
                 │
                 ├─> PlanningSystem.Proc()
                 │     ├─> MinutesToMidnight 계산 (자정 제한)
                 │     ├─> 스케줄 분석 → 자정까지 ActionQueue 생성
                 │     └─> NextStepDuration = MinutesToMidnight (기본값)
                 │
                 └─> PlayerSystem.Proc()
                       ├─> _lastSetDuration 차감 (이전 Step 소비분)
                       └─> NextStepDuration = _remainingDuration 설정
```

**시간 처리 순서 (1-Step Delay):**
1. Step N: PlayerSystem이 `NextStepDuration = X` 설정
2. Step N+1: MovementSystem이 X분 진행, PlayerSystem이 X분 차감
3. 이를 위해 `_lastSetDuration`으로 이전 Step 설정값 추적

**자정 제한:**
- PlanningSystem이 `MinutesToMidnight` 계산
- `SetNextStepDuration()`이 자동으로 자정까지로 제한
- 남은 시간은 다음 Step에서 계속 진행

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
│     └─ Edge[] (장소 간 연결 및 이동 시간)
└─ RegionEdge[] (지역 간 연결)

GameTime (시간 관리)
├─ _year, _month, _day (날짜)
├─ _minuteOfDay (0~1439, hour/minute 통합)
├─ Calendar (달력 설정)
└─ Holidays (휴일 정보)
```

**파일 위치:**
- `scripts/system/world_system.cs`
- `scripts/morld/terrain/` (Terrain, Region, Location, Edge, RegionEdge)
- `scripts/morld/schedule/GameTime.cs`

### CharacterSystem (Data System)
**역할:** 게임 내 모든 캐릭터의 데이터 관리

**주요 기능:**
- 캐릭터 생성/삭제/조회
- Dictionary<string, Character> 기반 O(1) 조회
- 캐릭터 위치, 스케줄, CurrentEdge 관리
- JSON 기반 Import/Export (CurrentEdge 포함)

**데이터 구조:**
```csharp
Character
├─ Id (고유 식별자)
├─ Name (이름)
├─ CurrentLocation (현재 위치 - LocationRef)
├─ CurrentEdge (이동 중 Edge 진행 상태 - EdgeProgress?)
├─ CurrentSchedule (현재 수행 중인 스케줄)
├─ Schedule (일일 스케줄 - DailySchedule)
│  └─ ScheduleEntry[] (시간대별 일정)
├─ TraversalContext (이동 조건, 태그)
├─ IsMoving (CurrentEdge != null)
└─ IsIdle (CurrentEdge == null)
```

**EdgeProgress (이동 중 상태):**
```csharp
EdgeProgress
├─ From (출발 Location)
├─ To (도착 Location)
├─ TotalTime (총 이동 시간)
├─ ElapsedTime (경과 시간)
├─ RemainingTime (남은 시간)
└─ Progress (진행률 0.0~1.0)
```

**파일 위치:**
- `scripts/system/character_system.cs`
- `scripts/morld/character/Character.cs`
- `scripts/morld/character/ActionLog.cs` (ActionLog, EdgeProgress)
- `scripts/morld/schedule/` (DailySchedule, ScheduleEntry)

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

**핵심 메서드:**
- `ProcessCharacter()` - 개별 캐릭터 ActionQueue 소비
- `ProcessMovingAction()` - 이동 Action 처리
- `ProcessIdleAction()` - 활동/대기 Action 처리

**파일 위치:**
- `scripts/system/movement_system.cs`

### PlanningSystem (Logic System)
**역할:** 캐릭터의 스케줄을 분석하여 ActionQueue 생성, 자정 제한 관리

**주요 필드:**
```csharp
public int NextStepDuration { get; private set; } = 0;  // 다음 Step 진행 시간 (분)
public int MinutesToMidnight { get; private set; }       // 자정까지 남은 시간
private Dictionary<string, List<ActionLog>> _actionQueues;  // 캐릭터별 ActionQueue
private Dictionary<string, int> _currentActionIndices;  // 현재 Action 인덱스
```

**실행 로직:**
1. MinutesToMidnight 계산 (1440 - minuteOfDay)
2. 매 Step마다 Queue 초기화 (새로 생성)
3. 각 캐릭터에 대해:
   - CurrentEdge 확인 → 남은 이동을 첫 Action으로 추가
   - 스케줄 기반으로 **자정까지** ActionQueue 생성 (Edge 단위로 분리)
4. NextStepDuration = MinutesToMidnight 설정 (기본값, PlayerSystem이 덮어씀)

**ActionLog 구조:**
```csharp
ActionLog
├─ StartTime (상대 분 - Step 시작 기준)
├─ EndTime (상대 분)
├─ IsMoving (이동 중 여부)
├─ Location (현재/출발 위치)
├─ Destination (도착 위치 - IsMoving=true일 때)
├─ Activity (활동명 - 스케줄에서 복사)
└─ Duration (소요 시간)
```

**핵심 메서드:**
- `BuildActionQueue()` - 캐릭터별 ActionQueue 생성
- `GetActionQueue()` - Queue 조회
- `GetCurrentActionIndex()` / `SetCurrentActionIndex()` - 인덱스 관리
- `SetNextStepDuration()` - 시간 설정 (자정 제한 자동 적용)
- `GetTravelTime()` - Edge 이동 시간 계산

**PathFinding:**
- Dijkstra 알고리즘 기반
- Region 내부 이동 및 Region 간 이동 지원
- TraversalContext를 통한 조건부 이동 (예: 열쇠 필요)

**파일 위치:**
- `scripts/system/planning_system.cs`
- `scripts/morld/pathfinding/PathFinder.cs` (경로 탐색 알고리즘)

### PlayerSystem (Logic System)
**역할:** 플레이어 입력 기반 시간 진행 제어

**주요 필드:**
```csharp
private int _remainingDuration = 0;    // 남은 처리 시간 (분)
private int _lastSetDuration = 0;      // 이전 Step에서 설정한 시간 (1-Step Delay용)
private string _currentAction = "";    // 현재 액션 이름 (디버그용)
```

**핵심 속성:**
- `HasPendingTime` - `_remainingDuration > 0` 여부 (GameEngine에서 Step 실행 여부 결정)

**실행 로직:**
1. `_lastSetDuration` 차감 (이전 Step에서 MovementSystem이 실제 소비한 시간)
2. `_remainingDuration <= 0`이면 `NextStepDuration = 0` 설정 후 리턴
3. `SetNextStepDuration(_remainingDuration)` 호출 (자정 제한 자동 적용)
4. `_lastSetDuration = NextStepDuration` 저장 (다음 Step에서 차감용)

**외부 API:**
```csharp
// 시간 진행 요청 (GameEngine._Input()에서 호출)
public void RequestTimeAdvance(int minutes, string actionName = "")
{
    _remainingDuration += minutes;  // 누적 (여러 요청 지원)
    _currentAction = actionName;
}
```

**시간 처리 흐름 (1-Step Delay):**
```
Step N:
  PlayerSystem.Proc() → NextStepDuration = 240 설정, _lastSetDuration = 240 저장

Step N+1:
  MovementSystem.Proc() → 240분 진행
  PlayerSystem.Proc() → _remainingDuration -= 240 (실제 소비분 차감)
```

**자정 제한 처리:**
- 22:00에 4시간(240분) 요청 시:
  - Step 1: NextStepDuration = 120 (자정까지), _remainingDuration = 120 남음
  - Step 2: NextStepDuration = 120 (자정~02:00), _remainingDuration = 0

**파일 위치:**
- `scripts/system/player_system.cs`

---

## JSON 데이터 포맷

### location_data.json (WorldSystem)
```json
{
  "regions": [
    {
      "id": 0,
      "name": "마을",
      "locations": [
        {
          "id": 0,
          "name": "광장",
          "edges": [
            {
              "to": 1,
              "travelTime": 5,
              "conditions": []
            }
          ]
        }
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

### time_data.json (WorldSystem - GameTime)
```json
{
  "calendar": {
    "daysPerMonth": [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
    "weekdayNames": ["월", "화", "수", "목", "금", "토", "일"]
  },
  "currentTime": {
    "year": 1,
    "month": 1,
    "day": 1,
    "hour": 6,
    "minute": 0
  },
  "holidays": [
    {
      "name": "신년",
      "month": 1,
      "startDay": 1,
      "endDay": 1
    }
  ]
}
```

### character_data.json (CharacterSystem)
```json
[
  {
    "id": "guard_001",
    "name": "마을 경비병",
    "regionId": 0,
    "locationId": 0,
    "tags": {
      "열쇠": 1
    },
    "currentEdge": {
      "fromRegionId": 0,
      "fromLocalId": 0,
      "toRegionId": 0,
      "toLocalId": 1,
      "totalTime": 10,
      "elapsedTime": 5
    },
    "schedule": [
      {
        "name": "순찰",
        "regionId": 0,
        "locationId": 1,
        "start": 360,
        "end": 720,
        "activity": "순찰"
      }
    ]
  }
]
```

**시간 표현:**
- `start`, `end`: 하루의 분 단위 (0 = 00:00, 1439 = 23:59)
- 예: 360 = 06:00, 720 = 12:00

**currentEdge:**
- 이동 중이 아닌 캐릭터는 필드 생략 (null)
- 게임 로드 시 이동 중 상태 복원에 사용

---

## 게임 엔진 초기화

```csharp
// GameEngine.cs
private SE.World _world;
private PlayerSystem _playerSystem;

public override void _Ready()
{
    this._world = new SE.World(this);

    // 1. Data Systems 초기화 및 데이터 로드
    (this._world.AddSystem(new WorldSystem("worldName"), "worldSystem") as WorldSystem)
        .GetTerrain().UpdateFromFile("res://scripts/morld/json_data/location_data.json");

    (this._world.FindSystem("worldSystem") as WorldSystem)
        .GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

    (this._world.AddSystem(new CharacterSystem(), "characterSystem") as CharacterSystem)
        .UpdateFromFile("res://scripts/morld/json_data/character_data.json");

    // 2. Logic Systems 등록 (실행 순서: MovementSystem → PlanningSystem → PlayerSystem)
    this._world.AddSystem(new MovementSystem(), "movementSystem");
    this._world.AddSystem(new PlanningSystem(), "planningSystem");
    _playerSystem = this._world.AddSystem(new PlayerSystem(), "playerSystem") as PlayerSystem;
}

public override void _Input(InputEvent @event)
{
    if (@event is InputEventMouseButton mouseEvent && mouseEvent.Pressed)
    {
        if (mouseEvent.ButtonIndex == MouseButton.Left)
            _playerSystem?.RequestTimeAdvance(240, "수면 (4시간)");
        else if (mouseEvent.ButtonIndex == MouseButton.Right)
            _playerSystem?.RequestTimeAdvance(15, "휴식 (15분)");
    }
}

public override void _Process(double delta)
{
    // 대기 중인 시간이 있을 때만 Step 실행 (시간 정지 상태에서는 스킵)
    if (_playerSystem == null || !_playerSystem.HasPendingTime)
        return;

    int delta_int = (int)(delta * 1000);
    this._world.Step(delta_int);
}
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
- **런타임:** MovementSystem에서 시간 진행 및 캐릭터 상태 출력 (시간 흐를 때만)
- **런타임:** PlayerSystem에서 시간 요청/완료 로그

### 실행
Godot 에디터에서 프로젝트 실행

---

## 확장 가능성

### 새로운 Logic System 추가
1. `ECS.System`을 상속
2. `Proc(int step, Span<Component[]> allComponents)` 구현
3. `_hub.FindSystem()`으로 필요한 System 접근
4. `GameEngine._Ready()`에서 등록 (순서 중요)

**예시: EventSystem (캐릭터 조우 감지)**
```csharp
public class EventSystem : ECS.System
{
    protected override void Proc(int step, Span<Component[]> allComponents)
    {
        var planningSystem = _hub.FindSystem("planningSystem") as PlanningSystem;
        var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;

        // ActionQueue를 분석하여 같은 위치에 도착하는 캐릭터 쌍 감지
        // 조우 시점에 이벤트 트리거
    }
}
```

### 새로운 Data System 추가
1. `ECS.System`을 상속
2. 데이터 저장용 필드 추가 (Dictionary, List 등)
3. `UpdateFromFile()`, `SaveToFile()` 구현
4. Proc() 구현하지 않음
5. `GameEngine._Ready()`에서 데이터 로드

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ system/ (ECS Systems)
│  ├─ world_system.cs (WorldSystem - Data)
│  ├─ character_system.cs (CharacterSystem - Data)
│  ├─ movement_system.cs (MovementSystem - Logic)
│  ├─ planning_system.cs (PlanningSystem - Logic)
│  └─ player_system.cs (PlayerSystem - Logic)
├─ morld/ (Core Data Structures)
│  ├─ terrain/
│  │  ├─ Terrain.cs
│  │  ├─ Region.cs
│  │  ├─ Location.cs
│  │  ├─ Edge.cs
│  │  └─ RegionEdge.cs
│  ├─ character/
│  │  ├─ Character.cs
│  │  ├─ ActionLog.cs (ActionLog, EdgeProgress)
│  │  └─ CharacterJsonFormat.cs
│  ├─ pathfinding/
│  │  └─ PathFinder.cs
│  └─ schedule/
│     ├─ GameTime.cs
│     ├─ DailySchedule.cs
│     ├─ ScheduleEntry.cs
│     └─ TimeRange.cs
├─ simple_engine/
│  ├─ ecs.cs (ECS 기반 클래스)
│  └─ world.cs (SE.World, ECS 허브)
└─ json_data/ (게임 데이터)
   ├─ location_data.json
   ├─ time_data.json
   └─ character_data.json
```

---

## 핵심 개념 정리

### ECS (Entity Component System)
- **Entity:** 게임 오브젝트 (현재 미사용)
- **Component:** 데이터 (Character, Location 등)
- **System:** 로직 (MovementSystem, PlanningSystem)

### Queue 기반 시간 점프
- **ActionQueue:** 캐릭터별 자정까지 행동 계획 (Edge 단위)
- **NextStepDuration:** 다음 Step에서 진행할 시간 (분)
- **자정 제한:** ActionQueue는 자정까지만 생성, 요청 시간도 자정까지 자동 제한
- **시간 점프:** 플레이어 입력에 따라 유연한 시간 점프 (15분, 4시간 등)
- **이벤트 드리븐:** 향후 캐릭터 조우 등 이벤트 발생 시 시간 단축 가능

### 상태 판단
- **IsMoving:** `CurrentEdge != null`
- **IsIdle:** `CurrentEdge == null`
- **Activity:** 스케줄에서 복사된 활동명 (이동 중에도 유지)

### 시간 처리
- **Game Time:** GameTime (년/월/일/시/분)
- **Step Duration:** 플레이어 입력에 따라 유동적 (15분, 240분 등)
- **자정 제한:** 하루 경계를 넘지 않도록 자동 분할
- **Travel Time:** Edge 및 RegionEdge의 이동 시간 (분)
- **GameTime 구조:**
  - `_year`, `_month`, `_day`: 명시적 필드
  - `_minuteOfDay`: 0~1439, Hour/Minute 통합 (O(1) 계산)
- **1-Step Delay:** PlayerSystem이 설정한 시간은 다음 Step에서 MovementSystem이 소비

### Pathfinding
- **Dijkstra 알고리즘:** 최단 경로 탐색
- **Region 내부:** Edge 기반 탐색
- **Region 간:** RegionEdge 기반 탐색
- **조건부 이동:** TraversalContext의 Tag 시스템

---

## 작성자 노트

이 시스템은 **입력 기반 시간 진행**과 **자정 제한**을 통해 다음을 달성합니다:

1. **플레이어 주도:** 입력이 없으면 시간 정지, Step 자체가 스킵되어 연산 비용 절감
2. **유연한 시간 점프:** 15분 휴식, 4시간 수면 등 다양한 시간 진행 지원
3. **자정 제한:** 하루 경계를 안전하게 처리, 남은 시간은 자동으로 다음 날 이월
4. **이벤트 지원:** ActionQueue 분석으로 캐릭터 조우 등 이벤트 탐지 가능 (향후)
5. **1-Step Delay 패턴:** 시스템 실행 순서 문제를 우아하게 해결

세이브 파일 저장 시:
- WorldSystem → location_data.json, time_data.json
- CharacterSystem → character_data.json (CurrentLocation, CurrentEdge 포함)
- MovementSystem, PlanningSystem → 저장 불필요 (재실행 시 자동 재생성)

게임 로드 시:
- JSON 파일 로드 → Character 위치 및 CurrentEdge 복원
- PlanningSystem 실행 → CurrentEdge 기반으로 남은 이동을 첫 Action으로 추가
- 이동 중이던 캐릭터도 자연스럽게 이동 재개
