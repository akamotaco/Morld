# Morld - World & Character System (Godot C# Integration)

.NET 8.0 기반의 계층적 월드 구조와 캐릭터 시뮬레이션을 위한 시스템.
**Godot 4 C# 환경으로 포팅 및 확장 완료.**

## 프로젝트 구조

```
morld/
├── scripts/
│   ├── morld/
│   │   ├── terrain/              # 월드 지형 시스템
│   │   │   ├── World.cs          # 최상위 월드 컨테이너
│   │   │   ├── WorldJsonFormat.cs
│   │   │   ├── Region.cs         # 지역 (Location 그룹)
│   │   │   ├── Location.cs       # 개별 위치
│   │   │   ├── Edge.cs           # Region 내부 연결
│   │   │   ├── RegionEdge.cs     # Region 간 연결
│   │   │   └── RegionBuilder.cs
│   │   ├── schedule/             # 시간 및 스케줄 시스템
│   │   │   ├── GameTime.cs       # 게임 내 시간 (년/월/일/시/분)
│   │   │   ├── GameTimeJsonFormat.cs
│   │   │   ├── TimeRange.cs      # 시간 범위 (스케줄용)
│   │   │   ├── DailySchedule.cs  # 하루 스케줄 관리
│   │   │   └── ScheduleEntry.cs  # 개별 스케줄 항목
│   │   ├── character/            # 캐릭터 시스템
│   │   │   ├── Character.cs      # 캐릭터 엔티티
│   │   │   └── CharacterJsonFormat.cs
│   │   └── json_data/            # JSON 데이터 파일
│   │       ├── location_data.json
│   │       ├── time_data.json
│   │       └── character_data.json
│   ├── system/                   # ECS 시스템
│   │   ├── world_system.cs       # World + GameTime 관리
│   │   └── character_system.cs   # Character 관리
│   ├── sample/                   # 참고용 샘플 코드
│   │   ├── Core/PathFinder.cs
│   │   ├── Game/
│   │   │   ├── GameWorld.cs (주석 처리)
│   │   │   ├── NPC.cs
│   │   │   └── Schedule.cs
│   │   └── Serialization/
│   └── GameEngine.cs             # 메인 게임 엔진
```

## 핵심 시스템

### 1. World System (월드 구조)

#### 계층 구조

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
- **Edge**: 같은 Region 내 Location 간 연결 (양방향, 이동시간 분 단위)
- **RegionEdge**: 서로 다른 Region의 Location을 연결

#### ID 체계

| 타입 | ID 타입 | 범위 |
|------|---------|------|
| Region | `int` | World 내 고유 |
| Location | `int` (LocalId) | Region 내 고유 |
| RegionEdge | `int` | World 내 고유 |

위치 참조는 `LocationRef` 구조체 사용:
```csharp
var locRef = new LocationRef(regionId: 0, localId: 1);
```

#### 양방향 Edge

모든 Edge는 양방향이며 방향별로 다른 속성 가능:
```csharp
edge.SetTravelTime(10, 15);  // A→B: 10분, B→A: 15분
edge.AddConditionAtoB("열쇠", 1);  // A→B 조건
edge.IsBlocked = true;  // 완전 차단
```

**중요**: 이동 시간 단위가 **분(minute)**으로 변경되었습니다. (기존: float)

### 2. GameTime System (시간 시스템)

#### 구성 요소

```csharp
// 시간 정보
year: int    // 년도
month: int   // 월 (1~12 또는 사용자 정의)
day: int     // 일 (1~해당 월의 일수)
hour: int    // 시 (0~23)
minute: int  // 분 (0~59)
```

#### 달력 설정 (정적 - 모든 GameTime 인스턴스 공유)

```csharp
// 월별 일수 (기본: 지구 달력)
daysPerMonth: [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

// 요일 이름
weekdayNames: ["일", "월", "화", "수", "목", "금", "토"]
```

#### 기념일 시스템

날짜 범위로 기념일 정의 가능:
```csharp
{
  "name": "신년",
  "month": 1,
  "startDay": 1,
  "endDay": 3
}
```

#### 시간 조작

```csharp
var time = new GameTime();
time.SetTime(year: 1, month: 1, day: 1, hour: 6, minute: 0);

// 시간 추가
time.AddMinutes(30);
time.AddHours(2);
time.AddDays(5);
time.AddMonths(2);
time.AddYears(1);

// 정보 조회
int weekdayIndex = time.WeekdayIndex;  // 0~6
string weekday = time.WeekdayName;     // "일", "월", ...
int minuteOfDay = time.MinuteOfDay;    // 0~1439
List<Holiday> holidays = time.GetHolidays();
bool isHoliday = time.IsHoliday();
```

### 3. Character System (캐릭터 시스템)

#### Character 클래스

```csharp
public class Character
{
    string Id              // 고유 ID
    string Name            // 이름
    LocationRef CurrentLocation    // 현재 위치
    CharacterState State   // Idle / Moving
    MovementInfo? Movement // 이동 중일 때만 유효
    DailySchedule Schedule // 하루 스케줄
    TraversalContext TraversalContext  // 이동 조건 태그
    ScheduleEntry? CurrentSchedule     // 현재 스케줄
}
```

#### 캐릭터 상태

- **Idle**: 대기/활동 중 (Location에 머물러 있음)
- **Moving**: 이동 중 (경로를 따라 이동)

#### 이동 정보 (MovementInfo)

```csharp
LocationRef From              // 출발지
LocationRef FinalDestination  // 최종 목적지
LocationRef NextLocation      // 현재 이동 중인 다음 Location
List<Location> FullPath       // 전체 경로
int CurrentPathIndex          // 현재 경로 인덱스
int TotalTravelTime           // 현재 구간 총 이동 시간 (분)
int ElapsedTime               // 현재 구간 경과 시간 (분)
int RemainingTime             // 남은 시간 (분)
float ProgressPercent         // 진행도 (0~100%)
bool IsSegmentComplete        // 구간 완료 여부
bool IsPathComplete           // 전체 경로 완료 여부
```

#### 스케줄 시스템

**DailySchedule**: 하루 스케줄 관리
```csharp
var schedule = new DailySchedule();
schedule.AddEntry("아침식사", regionId: 1, locationId: 0, start: 420, end: 480);
schedule.AddEntry("근무", regionId: 1, locationId: 1, start: 540, end: 1080);

// 조회
ScheduleEntry? current = schedule.GetCurrentEntry(time);
ScheduleEntry? starting = schedule.GetStartingEntry(time);
```

**ScheduleEntry**: 개별 스케줄 항목
```csharp
public class ScheduleEntry
{
    string Name            // 스케줄 이름
    LocationRef Location   // 목적지
    TimeRange TimeRange    // 시간 범위
}
```

**TimeRange**: 시간 범위 (분 단위, 0~1439)
```csharp
var range = TimeRange.FromHourMinute(7, 0, 8, 0);  // 07:00 ~ 08:00
var range2 = TimeRange.FromHours(9, 18);           // 09:00 ~ 18:00
var range3 = new TimeRange(420, 480);              // 420분 ~ 480분

bool contains = range.Contains(time);
bool started = range.HasStarted(time);
bool ended = range.HasEnded(time);
```

### 4. CharacterSystem (ECS System)

캐릭터를 Dictionary로 관리하는 시스템:

```csharp
var charSystem = new CharacterSystem();

// 캐릭터 추가/제거
charSystem.AddCharacter(character);
charSystem.RemoveCharacter("npc_001");
charSystem.ClearCharacters();

// 조회
Character? character = charSystem.GetCharacter("npc_001");
IReadOnlyDictionary<string, Character> all = charSystem.Characters;

// JSON 로드/저장
charSystem.UpdateFromFile("res://scripts/morld/json_data/character_data.json");
charSystem.SaveToFile("res://output/character_save.json");

// 디버그
charSystem.DebugPrint();
```

## 주요 API

### World 생성 및 조작

```csharp
var world = new World("마을");

// Region 추가
var region = new Region(0, "주거지역");
region.AddLocation(0, "집");
region.AddLocation(1, "광장");
region.AddEdge(0, 1, travelTime: 10);  // 10분
world.AddRegion(region);

// RegionEdge 추가 (Region 간 연결)
world.AddRegionEdge(
    edgeId: 0,
    regionIdA: 0, localIdA: 1,  // 주거지역 광장
    regionIdB: 1, localIdB: 0,  // 상업지역 입구
    travelTimeAtoB: 8,          // 8분
    travelTimeBtoA: 8           // 8분
);
```

### GameTime 사용

```csharp
var time = new GameTime();

// JSON에서 로드 (달력 설정 + 현재 시간 + 기념일)
time.UpdateFromFile("res://scripts/morld/json_data/time_data.json");

// 시간 조작
time.AddMinutes(15);
time.AddHours(1);
time.AddDays(1);

// 정보 조회
string dateStr = time.ToDateString();        // "1년 1월 1일 (일)"
string timeStr = time.ToTimeString();        // "06:00"
string fullStr = time.ToFullString();        // "1년 1월 1일 (일) 06:00"

// 디버그 출력
time.DebugPrint();
```

### Character 생성 및 관리

```csharp
var character = new Character("char_001", "철수", regionId: 0, localId: 0);

// 태그 설정 (이동 조건)
character.TraversalContext.SetTag("열쇠", 1);
character.TraversalContext.SetTag("수영가능", 1);

// 스케줄 추가
character.Schedule.AddEntry("기상/준비", 0, 0, 360, 420);   // 06:00~07:00
character.Schedule.AddEntry("아침식사", 1, 0, 420, 480);    // 07:00~08:00
character.Schedule.AddEntry("상점 방문", 1, 1, 540, 720);   // 09:00~12:00

// 상태 조회
if (character.IsMoving)
{
    var movement = character.Movement;
    GD.Print($"진행률: {movement.ProgressPercent}%");
    GD.Print($"남은 시간: {movement.RemainingTime}분");
}
```

### 경로 탐색 (PathFinder)

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
    goalRegionId: 1, goalLocalId: 2,
    context: character.TraversalContext  // 태그 조건 고려
);

if (result.Success)
{
    GD.Print($"경로: {string.Join(" → ", result.Path)}");
    GD.Print($"총 시간: {result.TotalTime}분");
}
```

## JSON 직렬화

### World

```csharp
// 파일에서 로드 (새 World 생성)
var world = World.LoadFromFile("res://scripts/morld/json_data/location_data.json");

// 기존 World 업데이트 (객체 유지)
world.UpdateFromFile("res://scripts/morld/json_data/location_data.json");
world.UpdateFromJson(jsonString);

// 파일로 저장
world.SaveToFile("res://output/location_save.json");

// JSON 문자열로 변환
string json = world.ToJson();
```

### GameTime

```csharp
// 파일에서 로드
time.UpdateFromFile("res://scripts/morld/json_data/time_data.json");
time.UpdateFromJson(jsonString);

// 파일로 저장
time.SaveToFile("res://output/time_save.json");

// JSON 문자열로 변환
string json = time.ToJson();
```

### CharacterSystem

```csharp
// 파일에서 로드
charSystem.UpdateFromFile("res://scripts/morld/json_data/character_data.json");
charSystem.UpdateFromJson(jsonString);

// 파일로 저장
charSystem.SaveToFile("res://output/character_save.json");

// JSON 문자열로 변환
string json = charSystem.ToJson();
```

## JSON 스키마

### location_data.json (World)

```json
{
  "name": "aka",
  "regions": [
    {
      "id": 0,
      "name": "주거지역",
      "locations": [
        { "id": 0, "name": "집" },
        { "id": 1, "name": "광장" }
      ],
      "edges": [
        {
          "a": 0,
          "b": 1,
          "timeAtoB": 10,
          "timeBtoA": 10,
          "conditionsAtoB": {},
          "conditionsBtoA": {},
          "isBlocked": false
        }
      ]
    }
  ],
  "regionEdges": [
    {
      "id": 0,
      "name": "주거-상업 연결",
      "regionA": 0,
      "localA": 1,
      "regionB": 1,
      "localB": 0,
      "timeAtoB": 8,
      "timeBtoA": 8,
      "isBlocked": false
    }
  ]
}
```

### time_data.json (GameTime)

```json
{
  "calendar": {
    "daysPerMonth": [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31],
    "weekdayNames": ["일", "월", "화", "수", "목", "금", "토"]
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
      "endDay": 3
    }
  ]
}
```

### character_data.json (Characters)

```json
[
  {
    "id": "npc_001",
    "name": "철수",
    "regionId": 0,
    "locationId": 0,
    "tags": {
      "열쇠": 1
    },
    "schedule": [
      {
        "name": "기상/준비",
        "regionId": 0,
        "locationId": 0,
        "start": 360,
        "end": 420
      },
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
```

## 시간 표현

### 분 단위 시스템

- 게임 내 시간은 **분 단위 정수** (0-1439)
- 하루 = 1440분 (24시간 × 60분)

### 시간 변환

| 시간 | 분 단위 |
|------|---------|
| 00:00 | 0 |
| 06:00 | 360 |
| 07:00 | 420 |
| 12:00 | 720 |
| 18:00 | 1080 |
| 22:00 | 1320 |
| 23:59 | 1439 |

### 자정 넘는 스케줄

```json
{
  "name": "수면",
  "start": 1320,
  "end": 360
}
```
→ 22:00부터 다음날 06:00까지

`TimeRange.SpansMidnight` 속성으로 확인 가능

## 디버그 출력

모든 주요 시스템에 `DebugPrint()` 메서드 제공:

```csharp
// GameEngine에서 자동 호출 (DEBUG_LOG 정의 시)
world.DebugPrint();        // World 구조 출력
time.DebugPrint();         // 현재 시간 및 기념일 출력
charSystem.DebugPrint();   // 캐릭터 목록 및 스케줄 출력
```

출력 예시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  현재 시간: 1년 1월 1일 (일) 06:00
  기념일: 신년
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  캐릭터 수: 3
  - Character[npc_001] 철수 @ 0:0 (Idle)
    스케줄: 8개 항목
  - Character[npc_002] 영희 @ 1:1 (Idle)
    스케줄: 8개 항목
  - Character[npc_003] 민수 @ 0:2 (Idle)
    스케줄: 7개 항목
    태그: 열쇠:1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 주요 변경사항

### Godot 포팅
- `System.IO` → `Godot.FileAccess`로 변경
- 모든 파일 경로는 `res://` 프리픽스 사용
- `InvalidDataException` → `InvalidOperationException`

### 이동 시간 단위 변경
- **float → int (분 단위)**
- `1.0f` → `1` (1분)
- 모든 Edge 및 이동 시간이 정수 분으로 표현

### NPC → Character 개념 변경
- NPC.cs는 sample 폴더에 참고용으로 보존
- Character.cs가 실제 게임에서 사용됨
- CharacterSystem이 Dictionary<string, Character>로 관리

### GameTime 대폭 확장
- 년도 지원 추가
- 달력 설정 가능 (월별 일수, 요일 이름)
- 기념일 시스템 (날짜 범위 지원)
- 시간 조작 메서드 (AddYears, AddMonths, AddDays 등)
- Export 기능 추가 (SaveToFile, ToJson)

### Export 기능 완성
- **World**: ✅ SaveToFile / ToJson (기존)
- **GameTime**: ✅ SaveToFile / ToJson (신규)
- **CharacterSystem**: ✅ SaveToFile / ToJson (신규)

## ECS 통합

### WorldSystem

```csharp
var worldSystem = new WorldSystem("aka");
var world = worldSystem.GetWorld();
var time = worldSystem.GetTime();

world.UpdateFromFile("res://scripts/morld/json_data/location_data.json");
time.UpdateFromFile("res://scripts/morld/json_data/time_data.json");
```

### CharacterSystem

```csharp
var charSystem = new CharacterSystem();
charSystem.UpdateFromFile("res://scripts/morld/json_data/character_data.json");

var character = charSystem.GetCharacter("npc_001");
```

### GameEngine 통합

```csharp
public override void _Ready()
{
    this._world = new SE.World(this);

    // 시스템 추가 및 데이터 로드
    (this._world.AddSystem(new WorldSystem("aka"), "worldSystem") as WorldSystem)
        .GetWorld().UpdateFromFile("res://scripts/morld/json_data/location_data.json");

    (this._world.FindSystem("worldSystem") as WorldSystem)
        .GetTime().UpdateFromFile("res://scripts/morld/json_data/time_data.json");

    (this._world.AddSystem(new CharacterSystem(), "characterSystem") as CharacterSystem)
        .UpdateFromFile("res://scripts/morld/json_data/character_data.json");

#if DEBUG_LOG
    // 디버그 출력
    (this._world.FindSystem("worldSystem") as WorldSystem).GetWorld().DebugPrint();
    (this._world.FindSystem("worldSystem") as WorldSystem).GetTime().DebugPrint();
    (this._world.FindSystem("characterSystem") as CharacterSystem).DebugPrint();
#endif
}
```

## 확장 포인트

### TraversalContext (이동 조건)

캐릭터별 이동 조건 태그:
```csharp
character.TraversalContext.SetTag("열쇠", 1);
character.TraversalContext.SetTag("수영가능", 1);

// Edge 조건과 매칭
edge.AddConditionAtoB("열쇠", 1);  // 열쇠가 있어야 A→B 통과 가능
```

### Change Tracking (변경 추적)

World 변경 추적:
```csharp
world.ClearChanges();
// ... 수정 작업
var changedRegions = world.GetChangedRegions();
var changedEdges = world.GetChangedRegionEdges();
```

### Custom Calendar (사용자 정의 달력)

```json
{
  "calendar": {
    "daysPerMonth": [30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
    "weekdayNames": ["첫날", "둘째날", "셋째날", "넷째날", "다섯째날"]
  }
}
```

→ 12개월, 각 30일, 5일 주기

## 빌드

```bash
dotnet build
```

경고 69개 (nullable 관련), 오류 0개 - 정상 빌드
