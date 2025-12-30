# Morld - ECS 기반 캐릭터 시뮬레이션 시스템

## 프로젝트 개요

Morld는 ECS(Entity Component System) 아키텍처를 기반으로 한 게임 월드 시뮬레이션 시스템입니다.
캐릭터의 일정(Schedule)에 따라 자동으로 경로를 계획하고 이동하는 시스템을 제공합니다.

**핵심 기술:**
- Godot 4 엔진
- C# .NET
- ECS 아키텍처
- JSON 기반 데이터 관리
- A* Pathfinding

---

## 아키텍처 원칙

### ECS 시스템의 두 가지 역할

#### 1. Data Management Systems (데이터 관리 시스템)
게임 상태(persistent state)를 저장하고 관리하는 시스템

**특징:**
- ✅ JSON Import/Export (`UpdateFromFile()`, `SaveToFile()`)
- ❌ Step 함수 없음
- 세이브/로드 대상
- 게임 데이터의 원천(Source of Truth)

**구현 시스템:**
- `WorldSystem` - 월드 지형 데이터 (Region, Location, Edge)
- `CharacterSystem` - 캐릭터 데이터 (위치, 스케줄, 상태)

#### 2. Logic/Behavior Systems (로직 시스템)
매 프레임 게임 로직을 실행하는 시스템

**특징:**
- ❌ JSON Import/Export 없음
- ✅ Step 함수 구현 (`Proc(int step, Span<Component[]> allComponents)`)
- Data Systems의 데이터를 읽고 수정
- Stateless - 자체 상태를 저장하지 않음

**구현 시스템:**
- `PlanningSystem` - 캐릭터 스케줄 기반 경로 계획
- `MovementSystem` - 캐릭터 실시간 이동 처리

### 데이터 흐름

```
┌─────────────────────┐
│   GameEngine        │
│  _Ready()           │
└──────────┬──────────┘
           │
           ├─> WorldSystem.UpdateFromFile("location_data.json")
           ├─> CharacterSystem.UpdateFromFile("character_data.json")
           │
           ├─> PlanningSystem 등록
           └─> MovementSystem 등록

┌─────────────────────┐
│   GameEngine        │
│  _Process(delta)    │
└──────────┬──────────┘
           │
           └─> World.Step(deltaTime)
                 │
                 ├─> PlanningSystem.Proc()
                 │     └─> 스케줄 확인 → 경로 계획 → Character 상태 업데이트
                 │
                 └─> MovementSystem.Proc()
                       └─> 이동 진행 → Character 위치 업데이트
```

---

## 시스템 상세

### WorldSystem
**역할:** 게임 월드의 지형 데이터 관리

**주요 기능:**
- Region 및 Location 그래프 관리
- Edge를 통한 이동 시간 정보
- RegionEdge를 통한 Region 간 연결
- JSON 기반 Import/Export

**데이터 구조:**
```csharp
World
├─ Region[] (여러 지역)
│  └─ Location[] (각 지역의 장소들)
│     └─ Edge[] (장소 간 연결 및 이동 시간)
└─ RegionEdge[] (지역 간 연결)

GameTime (시간 관리)
├─ Calendar (달력 설정)
├─ CurrentTime (현재 시각)
└─ Holidays (휴일 정보)
```

**파일 위치:**
- `scripts/system/world_system.cs`
- `scripts/morld/terrain/` (World, Region, Location, Edge, RegionEdge)
- `scripts/morld/schedule/GameTime.cs`

### CharacterSystem
**역할:** 게임 내 모든 캐릭터의 데이터 관리

**주요 기능:**
- 캐릭터 생성/삭제/조회
- Dictionary<string, Character> 기반 O(1) 조회
- 캐릭터 위치, 상태, 스케줄 관리
- JSON 기반 Import/Export

**데이터 구조:**
```csharp
Character
├─ Id (고유 식별자)
├─ Name (이름)
├─ CurrentLocation (현재 위치)
├─ State (Idle / Moving)
├─ Movement (이동 정보)
│  ├─ FullPath (전체 경로)
│  ├─ CurrentPathIndex (현재 위치)
│  ├─ ElapsedTime / TotalTravelTime (진행 시간)
│  └─ FinalDestination (최종 목적지)
├─ Schedule (일일 스케줄)
│  └─ ScheduleEntry[] (시간대별 일정)
└─ TraversalContext (이동 조건, 태그)
```

**파일 위치:**
- `scripts/system/character_system.cs`
- `scripts/morld/character/Character.cs`
- `scripts/morld/schedule/` (DailySchedule, ScheduleEntry)

### PlanningSystem
**역할:** 캐릭터의 스케줄을 분석하여 이동 경로 계획

**실행 로직:**
1. 매 Step마다 모든 캐릭터 검사
2. 이동 중인 캐릭터는 스킵
3. 현재 시간의 활성 스케줄 확인
4. 목적지와 현재 위치가 다르면 경로 탐색 (PathFinder)
5. 경로를 Character.Movement에 설정
6. Character.State를 Moving으로 변경

**핵심 메서드:**
- `ProcessCharacter()` - 개별 캐릭터 처리
- `TryPlanMovement()` - 경로 탐색 및 이동 시작
- `SetupNextSegment()` - 이동 구간별 시간 설정

**PathFinding:**
- Dijkstra 알고리즘 기반
- Region 내부 이동 및 Region 간 이동 지원
- TraversalContext를 통한 조건부 이동 (예: 열쇠 필요)

**파일 위치:**
- `scripts/system/planning_system.cs`
- `scripts/morld/pathfinding/PathFinder.cs` (경로 탐색 알고리즘)

### MovementSystem
**역할:** 시간 경과에 따라 캐릭터 실제 이동 처리

**실행 로직:**
1. 매 Step마다 Moving 상태인 캐릭터만 처리
2. deltaTime(밀리초)을 분 단위로 변환
3. Character.Movement의 ElapsedTime 증가
4. 현재 구간 완료 시:
   - 경로가 남아있으면 다음 구간으로 이동
   - 최종 목적지 도착 시 State를 Idle로 변경

**핵심 메서드:**
- `ProcessCharacter()` - 개별 캐릭터 이동 처리
- `SetupNextSegment()` - 다음 구간 이동 시간 계산

**시간 단위:**
- deltaTime: 밀리초 (게임 엔진 제공)
- TravelTime: 분 (게임 내 시간)
- 변환: `deltaMinutes = deltaTime / 1000 / 60`

**파일 위치:**
- `scripts/system/movement_system.cs`

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
    "schedule": [
      {
        "name": "순찰",
        "regionId": 0,
        "locationId": 1,
        "start": 360,
        "end": 720
      },
      {
        "name": "휴식",
        "regionId": 0,
        "locationId": 0,
        "start": 720,
        "end": 780
      }
    ]
  }
]
```

**시간 표현:**
- `start`, `end`: 하루의 분 단위 (0 = 00:00, 1439 = 23:59)
- 예: 360 = 06:00, 720 = 12:00

---

## 게임 엔진 초기화

```csharp
// GameEngine.cs
public override void _Ready()
{
    this._world = new SE.World(this);

    // 1. Data Systems 초기화 및 데이터 로드
    (this._world.AddSystem(new WorldSystem("worldName"), "worldSystem") as WorldSystem)
        .GetWorld().UpdateFromFile("res://scripts/morld/json_data/location_data.json");

    (this._world.FindSystem("worldSystem") as WorldSystem)
        .GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

    (this._world.AddSystem(new CharacterSystem(), "characterSystem") as CharacterSystem)
        .UpdateFromFile("res://scripts/morld/json_data/character_data.json");

    // 2. Logic Systems 등록
    this._world.AddSystem(new PlanningSystem(), "planningSystem");
    this._world.AddSystem(new MovementSystem(), "movementSystem");
}

public override void _Process(double delta)
{
    int delta_int = (int)(delta * 1000); // 초 → 밀리초
    this._world.Step(delta_int);
}
```

---

## 주요 변경 이력

### NPC → Character 마이그레이션
- **이전:** sample 폴더의 NPC 클래스
- **이후:** morld/character/Character.cs
- **목적:** ECS 아키텍처에 맞춘 재설계

### float → int 시간 단위 변경
- **이전:** float (초 단위)
- **이후:** int (분 단위)
- **목적:** 게임 시간 정밀도 개선, 정수 연산

### 센티널 값 도입
- 이동 불가능: `travelTime = -1`
- 기본 문자열: `"unknown"`

### System 분리
- **데이터 관리:** WorldSystem, CharacterSystem
- **로직 실행:** PlanningSystem, MovementSystem
- **목적:** 관심사의 분리, 명확한 책임 분담

---

## 빌드 및 실행

### 빌드
```bash
dotnet build
```

### 디버그 로그
`GameEngine.cs`의 `#define DEBUG_LOG` 활성화 시:
- World 구조 출력
- GameTime 정보 출력
- Character 목록 및 스케줄 출력
- System 개수 출력

### 실행
Godot 에디터에서 프로젝트 실행

---

## 확장 가능성

### 새로운 Logic System 추가
1. `ECS.System`을 상속
2. `Proc(int step, Span<Component[]> allComponents)` 구현
3. `_hub.FindSystem()`으로 필요한 Data System 접근
4. `GameEngine._Ready()`에서 등록

**예시: CombatSystem**
```csharp
public class CombatSystem : ECS.System
{
    protected override void Proc(int step, Span<Component[]> allComponents)
    {
        var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
        var world = (_hub.FindSystem("worldSystem") as WorldSystem).GetWorld();

        // 전투 로직 구현
    }
}
```

### 새로운 Data System 추가
1. `ECS.System`을 상속
2. 데이터 저장용 필드 추가 (Dictionary, List 등)
3. `UpdateFromFile()`, `SaveToFile()` 구현
4. `GameEngine._Ready()`에서 데이터 로드

**예시: QuestSystem**
```csharp
public class QuestSystem : ECS.System
{
    private readonly Dictionary<string, Quest> _quests = new();

    public QuestSystem UpdateFromFile(string filePath)
    {
        // JSON 로드 및 파싱
        return this;
    }

    public void SaveToFile(string filePath)
    {
        // JSON 저장
    }
}
```

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ system/ (ECS Systems)
│  ├─ world_system.cs (WorldSystem)
│  ├─ character_system.cs (CharacterSystem)
│  ├─ planning_system.cs (PlanningSystem)
│  └─ movement_system.cs (MovementSystem)
├─ morld/ (Core Data Structures)
│  ├─ terrain/
│  │  ├─ World.cs
│  │  ├─ Region.cs
│  │  ├─ Location.cs
│  │  ├─ Edge.cs
│  │  └─ RegionEdge.cs
│  ├─ character/
│  │  ├─ Character.cs
│  │  └─ CharacterJsonFormat.cs
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
- **System:** 로직 (PlanningSystem, MovementSystem)

### Data-Oriented Design
- 데이터(Character)와 로직(Planning/Movement)의 분리
- 데이터는 CharacterSystem에, 로직은 별도 System에
- 로직 System은 Stateless - 자체 저장 데이터 없음

### 시간 처리
- **Real Time:** 엔진 deltaTime (밀리초)
- **Game Time:** GameTime (년/월/일/시/분)
- **Travel Time:** Edge 및 RegionEdge의 이동 시간 (분)

### Pathfinding
- **Dijkstra 알고리즘:** 최단 경로 탐색
- **Region 내부:** Edge 기반 탐색
- **Region 간:** RegionEdge 기반 탐색
- **조건부 이동:** TraversalContext의 Tag 시스템

---

## 작성자 노트

이 시스템은 **데이터와 로직의 명확한 분리**를 통해 다음을 달성합니다:

1. **확장성:** 새로운 System을 독립적으로 추가 가능
2. **유지보수성:** 각 System의 책임이 명확함
3. **저장/로드:** Data Systems만 저장하면 게임 상태 복원 가능
4. **성능:** Stateless Logic Systems은 오버헤드 최소화

세이브 파일 저장 시:
- WorldSystem → location_data.json
- CharacterSystem → character_data.json (현재 위치 포함)
- PlanningSystem, MovementSystem → 저장 불필요 (재실행 시 자동 동작)

게임 로드 시:
- JSON 파일 로드 → Character 위치 복원
- Logic Systems 재실행 → 자동으로 이동 재개
