# Morld - ECS 기반 유닛 시뮬레이션 시스템

## 프로젝트 개요

Morld는 ECS(Entity Component System) 아키텍처를 기반으로 한 게임 월드 시뮬레이션 시스템입니다.
유닛(캐릭터/오브젝트)의 스케줄 스택에 따라 자동으로 경로를 계획하고 이동하는 시스템을 제공합니다.

**핵심 기술:**
- Godot 4 엔진
- C# .NET
- ECS 아키텍처
- JSON 기반 데이터 관리
- Dijkstra Pathfinding
- 스택 기반 스케줄 시스템
- 통합 Unit 시스템 (캐릭터/오브젝트)

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
- `UnitSystem` - 유닛 데이터 (캐릭터/오브젝트 통합, 위치, 스케줄 스택, CurrentEdge, Inventory)
- `ItemSystem` - 아이템 정의 데이터 (PassiveTags, EquipTags, Actions)

#### 2. Logic/Behavior Systems (로직 시스템)
매 Step마다 게임 로직을 실행하는 시스템

**특징:**
- ❌ JSON Import/Export 없음
- ✅ Proc 함수 구현 (`Proc(int step, Span<Component[]> allComponents)`)
- Data Systems의 데이터를 읽고 수정
- Stateless - 자체 상태를 저장하지 않음

**구현 시스템:**
- `MovementSystem` - 스케줄 스택 기반 경로 계산, 유닛 이동 처리, GameTime 업데이트
- `BehaviorSystem` - 스케줄 종료 조건 체크 및 스택 pop
- `PlayerSystem` - 플레이어 입력 기반 시간 진행 제어, 스케줄 push, Look 기능
- `DescribeSystem` - 묘사 텍스트 생성 (시간 기반 키 선택)
- `ActionSystem` - 유닛 행동 실행 (talk, trade, use 등)
- `TextUISystem` - RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링

### 시스템 실행 순서

```
MovementSystem → BehaviorSystem → PlayerSystem → DescribeSystem
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
           ├─> UnitSystem.UpdateFromFile("unit_data.json")
           ├─> ItemSystem.UpdateFromFile("item_data.json")
           ├─> ActionSystem 등록
           │
           ├─> MovementSystem 등록
           ├─> BehaviorSystem 등록
           ├─> PlayerSystem 등록
           ├─> DescribeSystem 등록
           └─> TextUISystem 등록 (text_ui_data.json 로드)
```

---

## 스택 기반 스케줄 시스템

### 핵심 개념

플레이어와 NPC가 **동일한 메커니즘**을 사용합니다:
- 플레이어 명령 = 임시 스케줄 push
- 명령 완료 = pop → 자동으로 이전 상태로 복귀

```
스케줄 스택 예시 (NPC 여행):
┌─────────────────────────────┐
│ 여행 출발 (→ 목적지 도달)    │ ← 현재 활성 (pop 시 아래로)
├─────────────────────────────┤
│ 여행 복귀 (→ 집 도달)        │
├─────────────────────────────┤
│ 일상 스케줄 (종료 조건 없음)  │ ← 기본 베이스
└─────────────────────────────┘

플레이어 스케줄 스택:
┌─────────────────────────────┐
│ 이동 (→ 목적지 도달 시 pop)  │ ← 플레이어 명령 push
├─────────────────────────────┤
│ 빈 스케줄 (종료 조건 없음)    │ ← 기본 (대기 상태)
└─────────────────────────────┘

오브젝트 (스케줄 없음):
- IsObject = true
- 스케줄 스택 비어있음
- 이동하지 않음
- 인벤토리 보유 가능
```

### ScheduleLayer 구조

```csharp
ScheduleLayer
├─ Name (string - "일상", "이동", "여행" 등)
├─ Schedule (DailySchedule? - 시간 기반 스케줄, null = 단일 목표)
├─ EndConditionType (string? - "이동", "따라가기", "순찰" 등)
├─ EndConditionParam (string? - "0:1", "3", "0:1,0:2,0:3")
└─ IsComplete(unit, unitSystem) (종료 조건 체크)
```

**종료 조건 타입:**
| EndConditionType | EndConditionParam | 설명 |
|------------------|-------------------|------|
| `"이동"` | `"0:1"` | 위치 0:1 도달 시 pop |
| `"따라가기"` | `"3"` | 유닛 3과 같은 위치 시 pop |
| `"순찰"` | `"0:1,0:2,0:3"` | 순환 순찰 (영구) |
| `null` | `null` | 종료 없음 (일상 스케줄) |

---

## 시스템 상세

### WorldSystem (Data System)
**역할:** 게임의 지형(Terrain) 데이터 및 시간 보관

**주요 기능:**
- Region 및 Location 그래프 관리
- Edge를 통한 이동 시간 정보
- RegionEdge를 통한 Region 간 연결
- GameTime 보관 (시간 업데이트는 MovementSystem에서 수행)
- `Terrain.FindPath()` 메서드로 경로 탐색 제공
- JSON 기반 Import/Export

**데이터 구조:**
```csharp
Terrain
├─ Region[] (여러 지역)
│  └─ Location[] (각 지역의 장소들)
│     ├─ Edge[] (장소 간 연결 및 이동 시간)
│     └─ Appearance (Dictionary<string, string> - 시간 태그 기반 외관 묘사)
├─ RegionEdge[] (지역 간 연결)
└─ FindPath(from, to, character?, itemSystem?) (경로 탐색)

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

### UnitSystem (Data System)
**역할:** 게임 내 모든 유닛(캐릭터/오브젝트)의 데이터 관리

**주요 기능:**
- 유닛 생성/삭제/조회
- Dictionary<int, Unit> 기반 O(1) 조회
- 유닛 위치, 스케줄 스택, CurrentEdge, Inventory, Appearance 관리
- JSON 기반 Import/Export (ScheduleStack, CurrentEdge, Inventory, Appearance, Mood 포함)

**데이터 구조:**
```csharp
Unit
├─ Id (int - 고유 식별자)
├─ Name (이름)
├─ IsObject (bool - true: 오브젝트, false: 캐릭터)
├─ CurrentLocation (현재 위치 - LocationRef)
├─ CurrentEdge (이동 중 Edge 진행 상태 - EdgeProgress?)
├─ CurrentSchedule (현재 수행 중인 스케줄 엔트리)
├─ ScheduleStack (Stack<ScheduleLayer> - 스케줄 스택)
│  └─ CurrentScheduleLayer (스택 최상위 레이어)
├─ PushSchedule(layer) / PopSchedule() (스케줄 스택 조작)
├─ TraversalContext (기본 태그/스탯)
├─ Inventory (Dictionary<int, int> - 아이템ID → 개수)
├─ EquippedItems (List<int> - 장착된 아이템 ID)
├─ Actions (List<string> - 가능한 행동: "talk", "trade", "use" 등)
├─ Appearance (Dictionary<string, string> - 상황별 외관 묘사)
├─ Mood (HashSet<string> - 현재 감정 상태: "기쁨", "슬픔" 등)
├─ GetActualTags(ItemSystem) (아이템 효과 반영된 최종 태그)
├─ CanPass(conditions, ItemSystem) (조건 충족 여부)
├─ IsMoving (CurrentEdge != null)
└─ IsIdle (CurrentEdge == null)
```

**캐릭터 vs 오브젝트:**
| 구분 | 캐릭터 (IsObject=false) | 오브젝트 (IsObject=true) |
|------|-------------------------|--------------------------|
| 이동 | 스케줄에 따라 이동 | 이동 없음 |
| 스케줄 | 스케줄 스택 보유 | 스택 비어있음 |
| 인벤토리 | 가능 | 가능 |
| 행동 | talk, trade 등 | use, open 등 |
| 외관 묘사 | Mood + Activity 기반 | 고정 또는 없음 |

**파일 위치:**
- `scripts/system/unit_system.cs`
- `scripts/morld/unit/Unit.cs`
- `scripts/morld/unit/UnitJsonFormat.cs`
- `scripts/morld/schedule/` (DailySchedule, ScheduleEntry, ScheduleLayer)

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
├─ EquipTags (Dictionary<string, int> - 장착 시 효과)
├─ Value (int - 거래 가치)
└─ Actions (List<string> - 가능한 액션: "use", "combine" 등)
```

**파일 위치:**
- `scripts/system/item_system.cs`
- `scripts/morld/item/Item.cs`
- `scripts/morld/item/ItemJsonFormat.cs`

### MovementSystem (Logic System)
**역할:** 스케줄 스택 기반 경로 계산 및 유닛 이동 처리

**실행 로직:**
1. PlayerSystem에서 `NextStepDuration` 읽기
2. 시간 진행이 없으면 스킵
3. 각 유닛에 대해 (IsObject=true는 스킵):
   - 스케줄 스택 최상위에서 목표 위치 추출
   - 목표가 있으면 경로 계산 (`terrain.FindPath()`)
   - 경로를 따라 이동 처리
   - 도착 시 CurrentLocation 업데이트
   - 이동 중단 시 CurrentEdge에 진행 상태 저장
4. GameTime을 NextStepDuration만큼 증가
5. (디버그) 충돌 감지 - 경로가 겹치는 유닛 출력

**목표 위치 추출 (`GetGoalLocation`):**
- 시간 기반 스케줄 → 현재 시간의 ScheduleEntry.Location
- 단일 목표 이동 → EndConditionParam 파싱
- 따라가기 → 대상 유닛의 CurrentLocation

**파일 위치:**
- `scripts/system/movement_system.cs`
- `scripts/morld/character/MovementPlan.cs` (충돌 감지용)

### BehaviorSystem (Logic System)
**역할:** 스케줄 종료 조건 체크 및 스택 pop

**실행 로직:**
1. 모든 유닛 순회 (IsObject=true는 스킵)
2. 현재 스케줄 레이어의 `IsComplete()` 체크
3. 완료 시 `unit.PopSchedule()`
4. 다음 Step에서 MovementSystem이 새 스케줄로 동작

**파일 위치:**
- `scripts/system/behavior_system.cs`

### ActionSystem (Logic System)
**역할:** 유닛 행동 실행 (대화, 거래, 사용 등)

**주요 메서드:**
```csharp
ApplyAction(Unit user, string action, List<Unit> targets)
// 유닛 대상 행동 실행 (talk, trade 등)

ApplyItemAction(Unit user, string action, Item item, List<Unit>? targets)
// 아이템 사용 행동 실행 (use, combine 등)
```

**행동 결과:**
```csharp
ActionResult
├─ Success (bool - 성공 여부)
├─ Message (string - 결과 메시지)
└─ TimeConsumed (int - 소요 시간, 분)
```

**파일 위치:**
- `scripts/system/action_system.cs`
- `scripts/morld/action/ActionResult.cs`

### PlayerSystem (Logic System)
**역할:** 플레이어 입력 기반 시간 진행 제어, 스케줄 push, Look 기능

**주요 필드:**
```csharp
public int PlayerId { get; set; } = 0;     // 조작할 캐릭터 ID
public int NextStepDuration { get; }        // 다음 Step 진행 시간 (분)
public bool HasPendingTime { get; }         // 처리 대기 중인 시간 여부
private int _remainingDuration = 0;         // 남은 처리 시간 (분)
```

**명령 처리:**
```csharp
RequestCommand(string cmd)  // Deferred 명령 등록
// "이동:0:1" → ExecuteMove() → 스케줄 push + 이동 시간 요청
// "휴식:30" → ExecuteIdle() → 시간 진행만 (스택 변화 없음)

RequestTimeAdvance(int minutes, string reason)  // 시간 진행 요청
```

**Look 기능:**
```csharp
public LookResult Look()
// 반환:
// - Location: 현재 위치 정보 (AppearanceText 포함)
// - UnitIds: 같은 위치의 유닛 ID 목록 (캐릭터+오브젝트 통합)
// - Routes: 이동 가능한 경로 목록 (조건 필터링 적용)
// - GroundItems: 바닥에 떨어진 아이템 (아이템ID → 개수)

public UnitLookResult LookUnit(int unitId)
// 반환:
// - UnitId, Name, IsObject
// - Inventory: 유닛의 인벤토리
// - Actions: 가능한 행동 목록
// - AppearanceText: 현재 상태 기반 외관 묘사 (Mood + Activity)
```

**파일 위치:**
- `scripts/system/player_system.cs`
- `scripts/morld/player/LookResult.cs`

### DescribeSystem (Logic System)
**역할:** 묘사 텍스트 생성 (시간/상태 기반 키 선택)

**주요 기능:**
- `GetLocationAppearance(location, time)` - Location 외관 묘사 반환 (시간 태그 기반)
- `GetRegionAppearance(region, time)` - Region 외관 묘사 반환 (시간 태그 기반)
- `GetUnitAppearance(unit)` - Unit 외관 묘사 반환 (Mood + Activity 기반)
- `GetSituationText(lookResult, time)` - BBCode 포함 상황 텍스트 생성
- `GetUnitLookText(unitLook, unit)` - 유닛 살펴보기 텍스트 생성

**외관 묘사 선택 알고리즘:**
- Appearance 딕셔너리에서 키를 쉼표로 분리하여 태그 집합으로 처리
- 현재 태그와 가장 많이 일치하는 키 선택 (best-match)
- 일치하는 키가 없으면 "default" 사용

**파일 위치:**
- `scripts/system/describe_system.cs`

### TextUISystem (Logic System)
**역할:** RichTextLabel.Text 관리의 단일 수정 지점, Focus 스택 기반 화면 전환

**핵심 설계:**
- **Focus 기반 스택**: 스택에는 텍스트가 아닌 Focus 정보(타입, ID)만 저장
- **On-demand 렌더링**: 표시 시 항상 최신 게임 데이터에서 텍스트 생성
- **Stale Data 방지**: Pop 시 자동으로 상위 화면이 최신 데이터로 렌더링

**주요 기능:**
- `ShowSituation()` - 상황 화면 표시 (Clear → Push Situation Focus)
- `ShowUnitLook(unitId)` - 유닛 상세 화면 표시 (Push Unit Focus)
- `ShowInventory()` - 인벤토리 화면 표시 (Push Inventory Focus)
- `ShowItemMenu(itemId, context, unitId?)` - 아이템 메뉴 표시 (Push Item Focus)
- `ShowResult(message)` - 결과 메시지 표시 (Push Result Focus)
- `Pop()` - 최상위 포커스 제거 후 자동 갱신
- `PopIfInvalid()` - 아이템 개수가 0이면 Pop, 아니면 UpdateDisplay
- `UpdateDisplay()` - 현재 Focus 기반으로 텍스트 재생성
- `ToggleExpand(toggleId)` - 토글 펼침/접힘 전환
- `SetHoveredMeta(meta)` - hover 중인 링크 설정 (색상 변경)

**Focus 타입:**
```csharp
public enum FocusType
{
    Situation,   // 상황 화면 (location)
    Unit,        // 유닛/오브젝트 화면
    Inventory,   // 플레이어 인벤토리
    Item,        // 아이템 메뉴
    Result       // 결과 메시지
}
```

**Focus 클래스:**
```csharp
public class Focus
{
    public FocusType Type { get; set; }
    public int? UnitId { get; set; }      // Unit, Item 타입에서 사용
    public int? ItemId { get; set; }      // Item 타입에서 사용
    public string? Context { get; set; }   // "ground", "inventory", "container"
    public string? Message { get; set; }   // Result 타입에서 사용
    public HashSet<string> ExpandedToggles { get; set; }

    // 팩토리 메서드
    public static Focus Situation();
    public static Focus Unit(int unitId);
    public static Focus Inventory();
    public static Focus Item(int itemId, string context, int? unitId = null);
    public static Focus Result(string message);
}
```

**토글 마크업:**
```bbcode
[url=toggle:idle]▶ 멍때리기[/url][hidden=idle]
  [url=idle:15]15분[/url]
  [url=idle:30]30분[/url]
[/hidden=idle]
```

**스택 동작 규칙:**
| 이벤트 | 동작 |
|--------|------|
| 위치 이동 완료 | `ShowSituation()` (Clear → Push) |
| 유닛/인벤토리/아이템 클릭 | Push (해당 Focus) |
| back/confirm/done 클릭 | `Pop()` |
| 데이터 변경 (아이템 남음) | `UpdateDisplay()` |
| 데이터 변경 (아이템 0개) | `PopIfInvalid()` → Pop |
| toggle 클릭 | ExpandedToggles 토글 |

**파일 위치:**
- `scripts/system/text_ui_system.cs`
- `scripts/morld/ui/Focus.cs` (Focus, FocusType)
- `scripts/morld/ui/FocusStack.cs`
- `scripts/morld/ui/ToggleRenderer.cs`
- `scripts/morld/ui/UIStateJsonFormat.cs`

---

## JSON 데이터 포맷

### location_data.json (WorldSystem)
```json
{
  "regions": [
    {
      "id": 0,
      "name": "마을",
      "appearance": {
        "default": "평화로운 마을입니다."
      },
      "locations": [
        {
          "id": 0,
          "name": "광장",
          "appearance": {
            "default": "마을 중심의 광장입니다.",
            "아침": "상인들이 가판대를 펼치고 있습니다.",
            "저녁": "노을빛에 물든 광장이 아름답다."
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

**Location/Region appearance 키 규칙:**
- `"default"`: 기본 묘사
- `"아침"`, `"저녁"` 등: 시간대 태그 (GameTime.GetCurrentTags())

### unit_data.json (UnitSystem)
```json
[
  {
    "id": 0,
    "name": "플레이어",
    "comment": "player",
    "type": "male",
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
    "actions": ["rest", "sleep", "wait"],
    "scheduleStack": [
      {
        "name": "대기",
        "schedule": [],
        "endConditionType": null,
        "endConditionParam": null
      }
    ]
  },
  {
    "id": 1,
    "name": "철수",
    "comment": "npc_001",
    "type": "male",
    "regionId": 0,
    "locationId": 0,
    "actions": ["talk"],
    "appearance": {
      "default": "평범한 청년이다. 차분한 표정을 짓고 있다.",
      "기쁨": "환하게 웃고 있다. 기분이 좋아 보인다.",
      "슬픔": "어깨가 축 처져 있고 눈가가 촉촉하다.",
      "기쁨,긴장": "들뜬 표정이지만 어딘가 불안해 보인다.",
      "식사": "맛있게 음식을 먹고 있다.",
      "수면": "편안하게 잠들어 있다."
    },
    "mood": ["기쁨"],
    "scheduleStack": [
      {
        "name": "일상",
        "schedule": [
          { "name": "아침식사", "regionId": 1, "locationId": 0, "start": 420, "end": 480, "activity": "식사" }
        ],
        "endConditionType": null,
        "endConditionParam": null
      }
    ]
  },
  {
    "id": 10,
    "name": "나무 상자",
    "comment": "object_wooden_box",
    "type": "object",
    "regionId": 0,
    "locationId": 1,
    "inventory": { "1": 5 },
    "actions": ["open"],
    "scheduleStack": []
  }
]
```

**Unit appearance 키 규칙:**
- `"default"`: 기본 묘사 (일치하는 태그가 없을 때)
- `"기쁨"`, `"슬픔"` 등: 단일 Mood 태그
- `"식사"`, `"수면"` 등: Activity 태그 (CurrentSchedule.Activity)
- `"기쁨,긴장"`: 복합 태그 (쉼표로 구분, 순서 무관)

**참고:** 스택은 배열의 마지막 요소가 최상위 (Peek)

### item_data.json (ItemSystem)
```json
[
  {
    "id": 0,
    "name": "녹슨 열쇠",
    "comment": "rusty_key",
    "passiveTags": { "열쇠": 1 },
    "equipTags": {},
    "value": 10,
    "actions": ["use"]
  },
  {
    "id": 2,
    "name": "망원경",
    "comment": "telescope",
    "passiveTags": {},
    "equipTags": { "관찰": 2 },
    "value": 100,
    "actions": ["use", "equip"]
  }
]
```

---

## 프로젝트 구조

```
scripts/
├─ GameEngine.cs (진입점)
├─ MetaActionHandler.cs (BBCode URL 클릭 핸들러)
├─ system/ (ECS Systems)
│  ├─ world_system.cs (WorldSystem - Data)
│  ├─ unit_system.cs (UnitSystem - Data)
│  ├─ item_system.cs (ItemSystem - Data)
│  ├─ action_system.cs (ActionSystem - Logic)
│  ├─ movement_system.cs (MovementSystem - Logic)
│  ├─ behavior_system.cs (BehaviorSystem - Logic)
│  ├─ player_system.cs (PlayerSystem - Logic)
│  ├─ describe_system.cs (DescribeSystem - Logic)
│  └─ text_ui_system.cs (TextUISystem - Logic)
├─ morld/ (Core Data Structures)
│  ├─ IDescribable.cs (묘사 인터페이스)
│  ├─ terrain/
│  │  ├─ Terrain.cs (FindPath 포함)
│  │  ├─ Region.cs (IDescribable)
│  │  ├─ Location.cs (IDescribable)
│  │  ├─ Edge.cs
│  │  └─ RegionEdge.cs
│  ├─ unit/
│  │  ├─ Unit.cs (ScheduleStack, Inventory, Actions, GetActualTags)
│  │  └─ UnitJsonFormat.cs
│  ├─ item/
│  │  ├─ Item.cs (PassiveTags, EquipTags, Actions)
│  │  └─ ItemJsonFormat.cs
│  ├─ action/
│  │  └─ ActionResult.cs (행동 결과)
│  ├─ player/
│  │  ├─ LookResult.cs (LookResult, UnitLookResult, LocationInfo, RouteInfo)
│  │  └─ PlayerJsonFormat.cs
│  ├─ pathfinding/
│  │  └─ PathFinder.cs (Unit + ItemSystem 기반)
│  ├─ schedule/
│  │  ├─ GameTime.cs (GetCurrentTags)
│  │  ├─ DailySchedule.cs
│  │  ├─ ScheduleEntry.cs
│  │  ├─ ScheduleLayer.cs (스케줄 스택 레이어)
│  │  └─ TimeRange.cs
│  └─ ui/
│     ├─ ScreenLayer.cs (화면 레이어)
│     ├─ ScreenStack.cs (화면 스택)
│     ├─ ToggleRenderer.cs (토글 마크업 렌더러)
│     └─ UIStateJsonFormat.cs (JSON 직렬화)
├─ simple_engine/
│  ├─ ecs.cs (ECS 기반 클래스)
│  └─ world.cs (SE.World, ECS 허브)
└─ json_data/ (게임 데이터)
   ├─ location_data.json
   ├─ time_data.json
   ├─ unit_data.json
   ├─ item_data.json
   ├─ player_data.json
   └─ text_ui_data.json
```

---

## 핵심 개념 정리

### GetActualTags() - 아이템 효과 통합
```csharp
// Unit.GetActualTags(itemSystem)
// 1. 기본 Tags 복사
// 2. + Inventory 아이템의 PassiveTags (소유 효과)
// 3. + EquippedItems의 EquipTags (장착 효과)

var actualTags = unit.GetActualTags(itemSystem);
// 열쇠(PassiveTags: 열쇠:1) 소유 → actualTags["열쇠"] = 1
// 망원경(EquipTags: 관찰:2) 장착 + 기본 관찰:3 → actualTags["관찰"] = 5
```

### 스케줄 스택 조작
```csharp
// 플레이어 이동 명령
player.PushSchedule(new ScheduleLayer
{
    Name = "이동",
    Schedule = null,
    EndConditionType = "이동",
    EndConditionParam = "0:1"  // 목적지
});

// 도착 시 BehaviorSystem이 자동 pop
// → 이전 스케줄로 복귀
```

### Look 기능
```csharp
var result = playerSystem.Look();
// result.Location.AppearanceText: 시간 기반 위치 외관 묘사
// result.UnitIds: 같은 위치의 유닛 ID 목록 (캐릭터+오브젝트)
// result.Routes: 이동 가능한 경로 (IsBlocked, BlockedReason 포함)
// result.GroundItems: 바닥 아이템 (아이템ID → 개수)

var unitResult = playerSystem.LookUnit(unitId);
// unitResult.AppearanceText: Mood + Activity 기반 유닛 외관 묘사
// unitResult.Actions: 가능한 행동 목록
// unitResult.Inventory: 유닛의 인벤토리 (오브젝트만)
```

### 행동 실행
```csharp
// ActionSystem을 통한 행동 실행
var result = actionSystem.ApplyAction(player, "talk", [targetUnit]);
// result.Success: 성공 여부
// result.Message: "대화를 시작합니다."
// result.TimeConsumed: 소요 시간 (분)
```

---

## 빌드 및 실행

### 빌드
```bash
dotnet build
```

### 디버그 로그
`#define DEBUG_LOG` 활성화 시:
- **초기화:** World 구조, GameTime 정보, Unit 목록 및 스케줄 스택, System 개수 출력
- **런타임:** MovementSystem에서 시간 진행, 유닛 상태, 충돌 감지 출력
- **런타임:** BehaviorSystem에서 스케줄 레이어 완료/pop 출력
- **런타임:** PlayerSystem에서 시간 요청/완료 로그

### 실행
Godot 에디터에서 프로젝트 실행

---

## 세이브/로드

저장 대상:
- `WorldSystem` → location_data.json, time_data.json
- `UnitSystem` → unit_data.json (CurrentLocation, CurrentEdge, ScheduleStack, Inventory, Actions 포함)
- `ItemSystem` → item_data.json
- `PlayerSystem` → player_data.json
- `TextUISystem` → text_ui_data.json (ScreenStack, ExpandedToggles 포함)

저장 불필요:
- `MovementSystem`, `BehaviorSystem` → Stateless
- `ActionSystem`, `DescribeSystem` → Stateless
