# NPC 시스템 리팩토링 계획

## 목표

C# 스케줄 기반 시스템 → Python Agent 기반 시스템으로 전환

**핵심 원칙:**
- **Python**: 모든 NPC 행동 결정 (Decision/AI)
- **C#**: 순수 시뮬레이터 (Execution/Body)

---

## 현재 구조 (C# 중심)

```
[C# MovementSystem]
    ↓ ScheduleStack에서 목표 추출
    ↓ FindPath() 경로 계산
    ↓ 이동 실행
    ↓ BehaviorSystem이 종료 조건 체크 → pop
```

**문제점:**
- 스케줄이 고정적 (시간+위치 기반)
- 동적 행동 어려움 (문 잠그기, 전등 끄기 등)
- freeze나 특수 상황 처리가 복잡

---

## 목표 구조 (Python Agent)

```
[Python Agent]                     [C# Simulator]
    │                                    │
    ├─ think() 호출 ←────────────────────│ on_step 이벤트
    │                                    │
    ├─ "뭘 할지" 결정                     │
    │   └─ 이동? 대기? 상호작용?          │
    │                                    │
    ├─ morld.move_to(target) ───────────→│ 이동 명령
    ├─ morld.wait(duration) ────────────→│ 대기 명령
    ├─ morld.interact(object) ──────────→│ 상호작용
    │                                    │
    │                                    ↓ 시뮬레이션 실행
    │                                    │
    └─ on_reach/on_idle 이벤트 ←─────────│ 완료 알림
```

---

## 파일 구조 (최종 확정)

```
scenarios/scenario02/
├─ entities/                  # 모든 엔티티 정의
│  ├─ __init__.py             # 통합 로더 + 진행률 콜백
│  ├─ base.py                 # BaseEntity
│  │
│  ├─ characters/             # 캐릭터 (플레이어 + NPC)
│  │  ├─ __init__.py          # 자동 로딩 + think_all()
│  │  ├─ base.py              # BaseCharacter
│  │  ├─ player.py            # 플레이어
│  │  ├─ lina.py              # 리나
│  │  ├─ sera.py              # 세라
│  │  ├─ mila.py              # 밀라
│  │  ├─ yuki.py              # 유키
│  │  └─ ella.py              # 엘라
│  │
│  ├─ objects/                # 오브젝트
│  │  ├─ __init__.py
│  │  ├─ base.py              # BaseObject
│  │  ├─ fireplace.py
│  │  └─ ...
│  │
│  ├─ items/                  # 아이템
│  │  ├─ __init__.py
│  │  ├─ base.py              # BaseItem
│  │  └─ ...
│  │
│  └─ world/                  # 지형 (Region, Location)
│     ├─ __init__.py          # RegionEdge 정의
│     ├─ base.py              # BaseRegion, Location, Edge
│     ├─ mansion.py           # Region 0
│     └─ forest.py            # Region 1
│
├─ events.py                  # 글로벌 이벤트 핸들러
└─ runtime/
   └─ state.json              # 동적 상태 (save/load 대상)
```

**기존 구조 대비 변경점:**
- `characters/` → `entities/characters/` (통합)
- `agents/` → 삭제 (BaseCharacter가 Agent 역할 통합)
- `behaviors/` → 삭제 (캐릭터별 메서드로 통합)
- `python/` 폴더 제거 → 시나리오 루트에 직접 배치

---

## 결정 사항

### 0. 시스템 개편

**결정: Python이 시스템의 근간**

- **ScriptSystem 제거**: Python이 보조가 아닌 핵심이므로 별도 시스템 불필요
- **ThinkSystem 신설**: 기존 PlanningSystem 위치에 배치, Python think() 호출 담당
- **Python 직접 통합**: GameEngine에서 Python 인터프리터 직접 관리
- **JSON 로딩 폐기**: 모든 데이터는 Python 파일에서 정의

**ThinkSystem 설계:**

```
[시스템 실행 순서]
MovementSystem → EventSystem → WeatherSystem → ThinkSystem → BehaviorSystem → (플레이어 조작)
      │              │              │               │              │
   이동 처리     이벤트 감지     날씨 변경      다음 목표 설정    스케줄 pop
   (duration분)  (on_reach,     (다음 턴용)    (다음 턴용)      (종료조건 체크)
                 on_meet)
```

**ThinkSystem과 BehaviorSystem의 관계:**
- 둘 다 "다음 턴 준비" 역할 (같은 층위)
- ThinkSystem: 스케줄 **push** (새 목표 설정)
- BehaviorSystem: 스케줄 **pop** (완료된 스케줄 제거)

**freeze 처리:**
- freeze는 Step 외부(FlushEvents)에서 "대기" 스케줄 push
- ThinkSystem에서 "대기" 스케줄이 있으면 think() 호출 스킵 (C#에서 필터링)

```csharp
// ThinkSystem.cs (Logic System)
public class ThinkSystem : ECS.System
{
    private PyInterpreter _python;
    private PlayerSystem _playerSystem;

    public void Proc(int step)
    {
        // 1. Python think_all() 호출 - 모든 캐릭터 결정
        var commands = _python.Call("entities.characters", "think_all", gameTime);
        // 반환: { unitId: { "action": "move", "target": (0, 1) }, ... }

        // 2. PlayerSystem override 체크
        int playerId = _playerSystem.PlayerId;
        if (_playerSystem.HasPendingCommand())
        {
            // 사용자 입력이 있으면 Python 결과 무시
            commands[playerId] = _playerSystem.GetPendingCommand();
        }

        // 3. 각 캐릭터에 명령 적용
        foreach (var (unitId, command) in commands)
        {
            ApplyCommand(unitId, command);
        }
    }

    private void ApplyCommand(int unitId, Command cmd)
    {
        switch (cmd.Action)
        {
            case "move":
                // 이동 스케줄 push
                PushMoveSchedule(unitId, cmd.Target);
                break;
            case "wait":
                // 대기 스케줄 push
                PushWaitSchedule(unitId, cmd.Duration);
                break;
            case "activity":
                // 활동 설정
                SetActivity(unitId, cmd.Activity);
                break;
        }
    }
}
```

**Python 측 인터페이스:**

```python
# entities/characters/__init__.py
def think_all(game_time: int) -> dict:
    """
    모든 캐릭터의 think() 호출하고 명령 수집

    Returns:
        { unit_id: { "action": "move", "target": (0, 1) }, ... }
    """
    commands = {}

    for char in _characters.values():
        result = char.think(game_time)
        if result:
            commands[char.ID] = result

    return commands
```

**실행 흐름:**

```
사용자 클릭/명령
    ↓
[MovementSystem]
    └─ 이전 턴 스케줄 기반 이동 실행 (duration분)
    ↓
[EventSystem]
    └─ on_reach, on_meet 감지 → Python 핸들러 호출 → 다이얼로그/pending
    ↓
[WeatherSystem]
    └─ 날씨 업데이트 (다음 턴 think에 반영)
    ↓
[ThinkSystem]
    ├─ Python think_all(game_time) 호출
    │   └─ 각 캐릭터 think() → 명령 반환
    │       ├─ NPC: 스케줄 기반 이동/활동
    │       └─ 플레이어: 자동 행동 (수면 등)
    │
    └─ PlayerSystem override 체크
        ├─ 입력 있음 → 플레이어 명령 덮어쓰기
        └─ 입력 없음 → Python 결과 유지
    ↓
[BehaviorSystem]
    └─ 종료 조건 체크, 스케줄 pop
    ↓
(플레이어 조작 대기)
```

**Python ECS 패턴:**

각 C# 시스템이 담당하는 Python Base 클래스의 인스턴스만 찾아서 처리:

```
[ThinkSystem]   → BaseCharacter 서브클래스 → think()
[WeatherSystem] → BaseRegion 서브클래스   → update_weather()
[ObjectSystem]  → BaseObject 서브클래스   → update() (향후)
```

```python
# entities/__init__.py
from typing import Type

# 등록된 엔티티 인스턴스 (Base 클래스별로 분류)
_instances: dict[Type, dict[int, object]] = {}

def register_instance(instance):
    """엔티티 인스턴스 등록 (Base 클래스별 분류)"""
    for base in type(instance).__mro__:
        if base.__name__.startswith("Base") and base.__name__ != "BaseEntity":
            if base not in _instances:
                _instances[base] = {}
            _instances[base][instance.ID] = instance
            break

def get_all_by_base(base_class_name: str) -> list:
    """특정 Base 클래스의 모든 인스턴스 반환"""
    for base, instances in _instances.items():
        if base.__name__ == base_class_name:
            return list(instances.values())
    return []

def get_by_id(base_class_name: str, entity_id: int):
    """특정 Base 클래스에서 ID로 인스턴스 조회"""
    for base, instances in _instances.items():
        if base.__name__ == base_class_name:
            return instances.get(entity_id)
    return None
```

```csharp
// C# 시스템에서 Python 엔티티 조회
public class ThinkSystem : ECS.System
{
    public void Proc(int step)
    {
        // BaseCharacter의 모든 인스턴스에 대해 think() 호출
        var results = _python.Call("entities", "proc_all", "BaseCharacter", "think", gameTime);
        // ...
    }
}

public class WeatherSystem : ECS.System
{
    public void Proc(int step)
    {
        // BaseRegion의 모든 인스턴스에 대해 update_weather() 호출
        _python.Call("entities", "proc_all", "BaseRegion", "update_weather", gameTime);
    }
}
```

```python
# entities/__init__.py
def proc_all(base_class_name: str, method_name: str, *args) -> dict:
    """
    특정 Base 클래스의 모든 인스턴스에 대해 메서드 호출

    Returns:
        { entity_id: result, ... }
    """
    results = {}
    instances = get_all_by_base(base_class_name)

    for instance in instances:
        method = getattr(instance, method_name, None)
        if method and callable(method):
            result = method(*args)
            if result is not None:
                results[instance.ID] = result

    return results
```

**시스템별 담당 엔티티:**

| C# System | Python Base Class | 호출 메서드 | 설명 |
|-----------|-------------------|-------------|------|
| ThinkSystem | BaseCharacter | think() | 캐릭터 행동 결정 |
| WeatherSystem | BaseRegion | update_weather() | 날씨 변경 |
| ObjectSystem | BaseObject | update() | 오브젝트 상태 (향후) |

**WeatherSystem 설계:**

```csharp
// WeatherSystem.cs (Logic System)
public class WeatherSystem : ECS.System
{
    public void Proc(int step)
    {
        int gameTime = _worldSystem.GameTime.MinuteOfDay;

        // 모든 Region의 날씨 업데이트
        _python.Call("entities", "proc_all", "BaseRegion", "update_weather", gameTime);
    }
}
```

```python
# entities/world/base.py
class BaseRegion(BaseEntity):
    ID: int = 0
    NAME: str = ""
    WEATHER_PATTERNS: list = []  # 시간대별 날씨 패턴

    def __init__(self):
        self._current_weather = "맑음"

    def update_weather(self, game_time: int):
        """시간에 따른 날씨 업데이트"""
        hour = game_time // 60

        # 날씨 패턴에 따라 변경
        for start, end, weather, probability in self.WEATHER_PATTERNS:
            if start <= hour < end:
                if random.random() < probability:
                    self._current_weather = weather
                    morld.set_region_weather(self.ID, weather)
                break

    def get_weather(self) -> str:
        return self._current_weather

# entities/world/forest.py
class Forest(BaseRegion):
    ID = 1
    NAME = "숲"

    WEATHER_PATTERNS = [
        # (시작시, 종료시, 날씨, 확률)
        (6, 12, "맑음", 0.8),
        (12, 18, "흐림", 0.3),
        (18, 22, "비", 0.2),
        (22, 6, "맑음", 0.9),
    ]
```

### 1. 플레이어 처리 방식

**결정: 모든 캐릭터 동일 처리 + PlayerSystem이 override**

```python
# entities/characters/base.py
class BaseCharacter(BaseEntity):
    # IS_PLAYER 플래그 없음 - 모든 캐릭터 동일
    ...

# entities/characters/player.py
class Player(BaseCharacter):
    ID = 0
    NAME = "플레이어"

    def think(self, game_time):
        # 빈 함수여도 호출됨
        # 실제 행동은 PlayerSystem이 override
        pass

    def decide(self, game_time):
        # NPC처럼 스케줄 기반 행동 가능 (자동 행동)
        # 하지만 PlayerSystem이 사용자 입력으로 override
        return None
```

**동작:**
- `think_all()` 에서 **모든 캐릭터** think() 호출 (플레이어 포함)
- 플레이어도 Python에서 자동 행동 정의 가능 (예: 자동 수면)
- **PlayerSystem이 사용자 입력으로 행동 override**
  - 사용자 명령 있으면 → Python think() 결과 무시
  - 사용자 명령 없으면 → Python think() 결과 적용 (자동 행동)

**override 메커니즘:**
```
[Python] player.think() → "자동_수면" (새벽이면 자동으로 잠)
    ↓
[PlayerSystem] 사용자 입력 체크
    ├─ 입력 있음 → Python 결과 무시, 사용자 명령 실행
    └─ 입력 없음 → Python 결과("자동_수면") 적용
```

**장점:**
- 플레이어도 NPC처럼 자동 행동 가능 (밤에 자동 수면 등)
- 특수 상황에서 플레이어 행동 제한 가능 (감옥, 수면 중 등)
- IS_PLAYER 분기 없이 코드 단순화

### 2. 기존 스케줄 시스템 처리

**결정: ScheduleLayer만 유지, DailySchedule/ScheduleEntry 삭제**

| 구분 | 유지 | 삭제 |
|------|------|------|
| ScheduleLayer | ✅ | - |
| EndConditionType/Param | ✅ | - |
| RemainingLifetime | ✅ | - |
| DailySchedule | - | ✅ |
| ScheduleEntry | - | ✅ |
| MovementSystem.GetGoalFromSchedule() | - | ✅ (시간 기반 부분) |

**이유:**
- `move_unit()` → "이동" 스케줄 push/pop 구조 재활용
- `wait_unit()` → "대기" 스케줄 + RemainingLifetime 재활용
- 시간 기반 스케줄은 Python SCHEDULE로 대체

### 3. think() 호출 타이밍

**결정: 플레이어 행동 직후, 이동 처리 전 (매 Step 시작)**

```
플레이어 클릭/명령
    ↓
[EventSystem] on_step 이벤트 생성 (game_time 포함)
    ↓
[Python] on_event_list() → think_all() 호출
    ↓ (NPC들이 move_to() 등 명령 내림)
    ↓
[MovementSystem] 이동 처리 (플레이어 + NPC)
    ↓
[EventSystem] on_reach, on_meet 감지
    ↓
[Python] on_reach/on_meet 핸들러 호출
```

**on_step 호출 조건:**
- `NextStepDuration > 0` 일 때만 (시간 진행이 있을 때)
- 모놀로그/대화 중에는 호출 안 함

### 4. freeze 구현 방식

**결정: 기존 "대기" 스케줄 재활용**

```python
# BaseCharacter.freeze()
def freeze(self, duration: int):
    """일정 시간 행동 중지 (기존 대기 스케줄 사용)"""
    morld.wait_unit(self.ID, duration)
    self._state = "frozen"

# C# morld.wait_unit() 구현
public void WaitUnit(int unitId, int duration)
{
    var unit = _unitSystem.GetUnit(unitId);
    unit.PushSchedule(new ScheduleLayer {
        Name = "대기",
        EndConditionType = "대기",
        RemainingLifetime = duration
    });
}
```

**이점:**
- 새로운 시스템 불필요
- BehaviorSystem이 자동으로 RemainingLifetime 감소 및 pop
- freeze_others도 동일 메커니즘 사용

### 5. 이동 중 중복 move_to() 방지

**문제:** NPC가 이미 이동 중인데 매 think()마다 move_to() 호출

**해결: 상태 기반 체크**

```python
# BaseCharacter
def move_to(self, region_id: int, location_id: int):
    """이동 명령 - 이미 이동 중이면 무시"""
    current = self.get_location()
    target = (region_id, location_id)

    # 이미 목적지에 있음
    if current == target:
        return False

    # 이미 같은 목적지로 이동 중
    if self._state == "moving" and self._target == target:
        return False

    # 이동 명령 실행
    morld.move_unit(self.ID, region_id, location_id)
    self._state = "moving"
    self._target = target
    return True

def on_reach(self, location: tuple[int, int]):
    """도착 시 상태 초기화"""
    self._state = "idle"
    self._target = None
```

**C# 보완 (선택적):**
```csharp
// morld.move_unit() 에서 중복 체크
public bool MoveUnit(int unitId, int regionId, int locationId)
{
    var unit = _unitSystem.GetUnit(unitId);

    // 이미 "이동" 스케줄이 같은 목적지면 무시
    if (unit.CurrentScheduleLayer?.EndConditionType == "이동" &&
        unit.CurrentScheduleLayer?.EndConditionParam == $"{regionId}:{locationId}")
    {
        return false;
    }

    // 이동 스케줄 push
    unit.PushSchedule(...);
    return true;
}
```

### 6. activity 설정 타이밍

**문제:** activity를 언제 설정하는가?

**해결: 목적지 도착 시 설정**

```python
# 리나 예시
SCHEDULE = [
    # (시작시, 종료시, 활동, 위치)
    (7, 8, "식사", DINING),
    (9, 12, "채집", GATHERING),
    ...
]

def decide(self, game_time: int) -> str | None:
    hour = game_time // 60
    current_loc = self.get_location()

    for start, end, activity, location in self.SCHEDULE:
        if self._in_time_range(hour, start, end):
            if current_loc != location:
                # 아직 도착 안 함 → 이동 (activity는 아직 설정 X)
                self.move_to(*location)
                return f"moving_to_{activity}"
            else:
                # 도착함 → activity 설정
                self.set_activity(activity)
                return activity

    # 스케줄 외 시간
    self.set_activity(None)
    return None

def on_reach(self, location: tuple[int, int]):
    """도착 시 activity 자동 설정"""
    super().on_reach(location)

    # 현재 시간에 맞는 스케줄 찾아서 activity 설정
    game_time = morld.get_game_time()
    hour = game_time // 60

    for start, end, activity, loc in self.SCHEDULE:
        if self._in_time_range(hour, start, end) and location == loc:
            self.set_activity(activity)
            return
```

**원칙:**
1. 이동 중에는 activity = None (또는 "이동")
2. 도착 시 스케줄에 맞는 activity 설정
3. appearance는 activity 태그로 자동 매칭

### 7. 바닥 오브젝트 자동 생성

**문제:** 기존 시스템에서 각 Location마다 바닥 오브젝트(ID: 100+)가 있었음

**해결: World 로딩 시 자동 생성**

```python
# entities/world/__init__.py
def initialize_world():
    """World 로딩 후 바닥 오브젝트 자동 생성"""
    from entities.world import mansion, forest  # 모든 Region

    regions = [mansion.Mansion, forest.Forest]

    for region_cls in regions:
        region_cls().register()

    # 바닥 오브젝트 생성
    _create_ground_objects()

def _create_ground_objects():
    """각 Location에 바닥 오브젝트 생성"""
    terrain = morld.get_terrain_info()

    for region in terrain["regions"]:
        region_id = region["id"]
        for location in region["locations"]:
            location_id = location["id"]
            ground_id = 100 + region_id * 100 + location_id  # 예: 0:5 → 105

            morld.add_unit(
                ground_id,
                f"바닥",  # 이름
                region_id,
                location_id,
                "object",  # type
                ["putinobject"],  # actions
                {},  # appearance
                []   # mood
            )
            morld.set_unit_visible(ground_id, True)  # 바닥은 항상 visible

# 또는 C# 에서 처리 (더 간단)
# entities/world/ 로딩 후 자동으로 바닥 생성
```

**C# 처리 대안:**
```csharp
// GameEngine.cs - Python 로딩 완료 후
private void CreateGroundObjects()
{
    foreach (var region in _worldSystem.Terrain.Regions)
    {
        foreach (var location in region.Locations)
        {
            int groundId = 100 + region.Id * 100 + location.Id;
            _unitSystem.AddUnit(new Unit {
                Id = groundId,
                Name = "바닥",
                IsObject = true,
                CurrentLocation = new LocationRef(region.Id, location.Id),
                Actions = new List<string> { "putinobject" }
            });
            _inventorySystem.SetUnitInventoryVisible(groundId, true);
        }
    }
}
```

**결정:** C# 에서 자동 생성 (Python 파일로 정의할 필요 없음)

### 8. RegionEdge 등록

**문제:** Region 간 연결을 어디서 정의하는가?

**해결: entities/world/__init__.py에서 정의**

```python
# entities/world/__init__.py
from entities.world.base import RegionEdge

REGION_EDGES = [
    RegionEdge(
        location_a=(0, 12),  # 저택 앞마당
        location_b=(1, 0),   # 숲 입구
        travel_time_a_to_b=3,
        travel_time_b_to_a=3
    ),
]

def register_region_edges():
    """RegionEdge 등록"""
    for edge in REGION_EDGES:
        morld.add_region_edge(
            edge.location_a,
            edge.location_b,
            edge.travel_time_a_to_b,
            edge.travel_time_b_to_a
        )
```

---

## 캐릭터 모듈화 설계

### 목표

- **하나의 파일 = 하나의 캐릭터**
- 파일 추가만으로 새 캐릭터 등장
- 데이터와 행동 로직을 한 곳에서 관리

### 현재 구조 (분산)

```
characters/lina/
├─ __init__.py     # 빈 파일
├─ data.py         # CHARACTER_DATA, PRESENCE_TEXT
├─ events.py       # on_meet_player 등
└─ dialogues.py    # 대화 데이터
```

**문제점:**
- 파일이 분산되어 관리 어려움
- 새 캐릭터 추가 시 4개 파일 + `__init__.py` 수정 필요
- scheduleStack이 data.py에 있어서 행동과 데이터가 혼재

### 목표 구조 (통합)

```
characters/
├─ __init__.py     # 자동 로딩 + BaseCharacter
├─ base.py         # BaseCharacter 클래스
├─ lina.py         # 리나 (데이터 + 행동)
├─ sera.py         # 세라
├─ mila.py         # 밀라
├─ yuki.py         # 유키
└─ ella.py         # 엘라
```

### BaseCharacter 클래스

```python
# characters/base.py
import morld

class BaseCharacter:
    """모든 캐릭터의 기본 클래스"""

    # === 서브클래스에서 정의 (데이터) ===
    ID: int = 0
    NAME: str = ""
    TYPE: str = "female"
    START_LOCATION: tuple[int, int] = (0, 0)  # (region_id, location_id)

    # 스탯 (태그)
    TAGS: dict = {}

    # 외관 묘사 (appearance)
    APPEARANCE: dict = {
        "default": ""
    }

    # 행동 가능 목록
    ACTIONS: list = []

    # 상황별 presence text
    PRESENCE_TEXT: dict = {
        "default": "{name}가 있다."
    }

    # 대화 데이터
    DIALOGUES: dict = {
        "default": {"pages": ["..."]}
    }

    # === 인스턴스 상태 ===
    def __init__(self):
        self._frozen = False
        self._frozen_until = 0
        self._state = "idle"
        self._first_met = False

    # === 시스템 통신 (morld API 래핑) ===
    def get_location(self) -> tuple[int, int]:
        """현재 위치 반환"""
        info = morld.get_unit_info(self.ID)
        return (info["region_id"], info["location_id"])

    def get_activity(self) -> str | None:
        """현재 활동 반환"""
        info = morld.get_unit_info(self.ID)
        return info.get("activity")

    def get_tag(self, tag_name: str) -> int:
        """스탯 값 조회"""
        info = morld.get_unit_info(self.ID)
        return info.get("tags", {}).get(tag_name, 0)

    def set_tag(self, tag_name: str, value: int):
        """스탯 값 설정"""
        morld.set_unit_tag(self.ID, tag_name, value)

    def get_mood(self) -> list[str]:
        """현재 감정 상태"""
        info = morld.get_unit_info(self.ID)
        return info.get("mood", [])

    def set_mood(self, moods: list[str]):
        """감정 상태 설정"""
        morld.set_unit_mood(self.ID, moods)

    def move_to(self, region_id: int, location_id: int):
        """이동 명령"""
        morld.move_unit(self.ID, region_id, location_id)
        self._state = "moving"

    def set_activity(self, activity: str):
        """활동 설정 (appearance 매칭용)"""
        morld.set_unit_activity(self.ID, activity)

    def wait(self, duration: int):
        """대기"""
        morld.wait_unit(self.ID, duration)
        self._state = "waiting"

    # === 행동 결정 (서브클래스에서 오버라이드) ===
    def think(self, game_time: int) -> str | None:
        """매 Step마다 호출 - 다음 행동 결정"""
        if self._frozen:
            if game_time >= self._frozen_until:
                self._frozen = False
            else:
                return None
        return self.decide(game_time)

    def decide(self, game_time: int) -> str | None:
        """실제 결정 로직 - 서브클래스에서 구현"""
        return None

    # === 이벤트 핸들러 (서브클래스에서 오버라이드) ===
    def on_reach(self, location: tuple[int, int]):
        """목적지 도착 시"""
        self._state = "idle"

    def on_meet_player(self) -> dict | None:
        """플레이어와 만났을 때"""
        return None

    def on_talk(self) -> dict | None:
        """대화 시작 시"""
        activity = self.get_activity()

        # activity 기반 대화
        if activity and activity in self.DIALOGUES:
            return self.DIALOGUES[activity]

        return self.DIALOGUES.get("default")

    # === 유틸리티 ===
    def freeze(self, duration: int):
        """일정 시간 행동 중지"""
        self._frozen = True
        self._frozen_until = morld.get_game_time() + duration

    def unfreeze(self):
        """행동 재개"""
        self._frozen = False

    def get_presence_text(self, region_id: int, location_id: int) -> str | None:
        """현재 상태에 맞는 presence text 반환"""
        activity = self.get_activity()
        moods = self.get_mood()

        # 우선순위 1: activity
        if activity:
            key = f"activity:{activity}"
            if key in self.PRESENCE_TEXT:
                return self.PRESENCE_TEXT[key].format(name=self.NAME)

        # 우선순위 2: 장소
        loc_key = f"{region_id}:{location_id}"
        if loc_key in self.PRESENCE_TEXT:
            return self.PRESENCE_TEXT[loc_key].format(name=self.NAME)

        # 우선순위 3: mood
        for mood in moods:
            key = f"mood:{mood}"
            if key in self.PRESENCE_TEXT:
                return self.PRESENCE_TEXT[key].format(name=self.NAME)

        # 우선순위 4: 기본값
        return self.PRESENCE_TEXT.get("default", "").format(name=self.NAME)

    # === 시스템 등록 ===
    def register(self):
        """morld에 캐릭터 등록"""
        region_id, location_id = self.START_LOCATION
        morld.add_unit(
            self.ID, self.NAME, region_id, location_id,
            self.TYPE, self.ACTIONS, self.APPEARANCE, []
        )
        if self.TAGS:
            morld.set_unit_tags(self.ID, self.TAGS)
```

### 캐릭터 구현 예시 (리나)

```python
# characters/lina.py
from characters.base import BaseCharacter

class Lina(BaseCharacter):
    # === 데이터 정의 ===
    ID = 1
    NAME = "리나"
    TYPE = "female"
    START_LOCATION = (0, 7)  # 리나의 방

    TAGS = {
        "외모:금발": 1, "외모:단발": 1, "외모:녹색눈": 1,
        "성격:명랑함": 1, "성격:활발함": 1,
        "애정": 0, "성욕": 0, "질투": 0,
        "피로": 0, "기분": 7,
    }

    APPEARANCE = {
        "default": "밝은 금발 단발머리의 활기찬 소녀. 녹색 눈이 반짝인다.",
        "기쁨": "환하게 웃고 있다. 에너지가 넘쳐 보인다.",
        "슬픔": "평소와 달리 기운이 없어 보인다.",
        "식사": "맛있게 음식을 먹고 있다.",
        "수면": "새근새근 잠들어 있다.",
        "채집": "바구니를 들고 열심히 열매를 따고 있다."
    }

    ACTIONS = ["script:npc_talk:대화"]

    PRESENCE_TEXT = {
        "activity:채집": "{name}가 채집 준비를 하고 있다.",
        "activity:식사": "{name}가 맛있게 밥을 먹고 있다.",
        "activity:수면": "{name}가 새근새근 잠들어 있다.",
        "0:23": "{name}가 열매를 따고 있다.",
        "0:1": "{name}가 소파에 앉아 발을 흔들고 있다.",
        "default": "{name}가 밝은 표정으로 주변을 둘러본다."
    }

    DIALOGUES = {
        "default": {"pages": ["안녕! 나는 리나야.", "오늘 날씨가 좋네~"]},
        "식사": {"pages": ["(음식을 먹고 있다)", "...냠냠, 맛있어!"]},
        "수면": {"pages": ["(자고 있다)", "...zzZ"]},
        "채집": {"pages": ["어? 왔어?", "나 지금 열매 따는 중이야!"]},
    }

    # === 개인 데이터 ===
    MY_ROOM = (0, 7)
    DINING = (0, 3)
    GATHERING = (1, 3)
    LIVING = (0, 1)

    # 시간대별 스케줄 (기존 scheduleStack 대체)
    SCHEDULE = [
        # (시작시, 종료시, 활동, 위치)
        (6, 7, "준비", MY_ROOM),
        (7, 8, "식사", DINING),
        (9, 12, "채집", GATHERING),
        (12, 13, "식사", DINING),
        (14, 17, "채집", GATHERING),
        (18, 19, "휴식", LIVING),
        (19, 20, "식사", DINING),
        (20, 22, "휴식", LIVING),
        (22, 6, "수면", MY_ROOM),  # 다음날 6시까지
    ]

    # === 행동 결정 ===
    def decide(self, game_time: int) -> str | None:
        hour = game_time // 60
        current_loc = self.get_location()

        # 시간대별 스케줄 확인
        for start, end, activity, location in self.SCHEDULE:
            if self._in_time_range(hour, start, end):
                # 활동 설정
                self.set_activity(activity)

                # 위치가 다르면 이동
                if current_loc != location:
                    self.move_to(*location)
                    return f"moving_to_{activity}"

                return activity

        return None

    def _in_time_range(self, hour: int, start: int, end: int) -> bool:
        """시간 범위 체크 (자정 넘김 처리)"""
        if start <= end:
            return start <= hour < end
        else:  # 22시 ~ 6시 같은 경우
            return hour >= start or hour < end

    # === 이벤트 핸들러 ===
    def on_meet_player(self) -> dict | None:
        if not self._first_met:
            self._first_met = True
            return {
                "type": "monologue",
                "pages": [
                    "어? 너 누구야?",
                    "...아, 쓰러져 있던 사람?",
                    "나는 리나! 반가워~"
                ],
                "time_consumed": 5,
                "button_type": "ok"
            }
        return None
```

### 자동 로딩 시스템

```python
# characters/__init__.py
import os
import importlib
from characters.base import BaseCharacter

# 등록된 캐릭터 인스턴스
_characters: dict[int, BaseCharacter] = {}

def _auto_discover():
    """characters/ 폴더의 모든 캐릭터 모듈 자동 로드"""
    current_dir = os.path.dirname(__file__)

    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and filename not in ('__init__.py', 'base.py'):
            module_name = filename[:-3]  # .py 제거
            module = importlib.import_module(f"characters.{module_name}")

            # BaseCharacter 서브클래스 찾기
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, BaseCharacter) and
                    attr is not BaseCharacter):
                    # 인스턴스 생성 및 등록
                    instance = attr()
                    _characters[instance.ID] = instance

def initialize_characters():
    """모든 캐릭터를 morld에 등록"""
    _auto_discover()
    for char in _characters.values():
        char.register()
    print(f"[characters] {len(_characters)} characters initialized")

def get_character(unit_id: int) -> BaseCharacter | None:
    """캐릭터 인스턴스 반환"""
    return _characters.get(unit_id)

def get_all_characters() -> list[BaseCharacter]:
    """모든 캐릭터 반환"""
    return list(_characters.values())

def think_all(game_time: int):
    """모든 캐릭터의 think() 호출"""
    for char in _characters.values():
        char.think(game_time)

def get_presence_text(unit_id: int, region_id: int, location_id: int) -> str | None:
    """특정 캐릭터의 presence text 반환"""
    char = _characters.get(unit_id)
    if char:
        return char.get_presence_text(region_id, location_id)
    return None
```

### morld API 통신 정리

| 기능 | BaseCharacter 메서드 | morld API |
|------|---------------------|-----------|
| 위치 조회 | `get_location()` | `morld.get_unit_info()` |
| 활동 조회 | `get_activity()` | `morld.get_unit_info()` |
| 스탯 조회 | `get_tag(name)` | `morld.get_unit_info()` |
| 스탯 설정 | `set_tag(name, value)` | `morld.set_unit_tag()` (신규) |
| 감정 조회 | `get_mood()` | `morld.get_unit_info()` |
| 감정 설정 | `set_mood(moods)` | `morld.set_unit_mood()` (신규) |
| 이동 명령 | `move_to(r, l)` | `morld.move_unit()` (신규) |
| 활동 설정 | `set_activity(act)` | `morld.set_unit_activity()` (신규) |
| 대기 명령 | `wait(duration)` | `morld.wait_unit()` (신규) |
| 시간 조회 | - | `morld.get_game_time()` (신규) |
| 등록 | `register()` | `morld.add_unit()` (기존) |

### 필요한 신규 morld API

```python
# 기존 API
morld.get_unit_info(unit_id)      # 유닛 정보 조회
morld.add_unit(...)               # 유닛 등록
morld.set_unit_tags(id, tags)     # 태그 일괄 설정

# 신규 API (추가 필요)
morld.set_unit_tag(id, name, value)   # 단일 태그 설정
morld.set_unit_mood(id, moods)        # 감정 설정
morld.set_unit_activity(id, activity) # 활동 설정
morld.move_unit(id, region, location) # 이동 명령
morld.wait_unit(id, duration)         # 대기 명령
morld.get_game_time()                 # 현재 시간 조회
```

---

## 통합 Python 엔티티 시스템

> **Note:** 이 섹션은 "파일 구조 (최종 확정)"과 동일한 내용입니다. 상단 섹션을 참조하세요.

### Base 클래스 계층

```python
# entities/base.py
class BaseEntity:
    """모든 엔티티의 기본"""
    ID: int = 0
    NAME: str = ""

    def register(self):
        raise NotImplementedError

# entities/characters/base.py
class BaseCharacter(BaseEntity):
    TYPE = "female"
    START_LOCATION = (0, 0)
    TAGS = {}
    APPEARANCE = {}
    ACTIONS = []
    PRESENCE_TEXT = {}
    DIALOGUES = {}
    SCHEDULE = []                    # [(시작시, 종료시, 활동, 위치), ...]

    def think(self, game_time): ...
    def decide(self, game_time): ...

# entities/objects/base.py
class BaseObject(BaseEntity):
    LOCATION = (0, 0)
    ACTIONS = []
    APPEARANCE = {}
    IS_VISIBLE = False

# entities/items/base.py
class BaseItem(BaseEntity):
    PASSIVE_TAGS = {}
    EQUIP_TAGS = {}
    ACTIONS = []
    VALUE = 0

# entities/world/base.py
class Location:
    def __init__(self, id, name, is_indoor=True, stay_duration=0, appearance=None): ...

class Edge:
    def __init__(self, a, b, travel_time, conditions=None): ...

class BaseRegion(BaseEntity):
    CURRENT_WEATHER = "맑음"
    LOCATIONS = []
    EDGES = []
```

### 분할 예시 (대사가 많은 캐릭터)

```python
# entities/characters/lina.py
from entities.characters.base import BaseCharacter
from entities.characters.lina_dialogues import DIALOGUES

class Lina(BaseCharacter):
    ID = 1
    NAME = "리나"
    DIALOGUES = DIALOGUES  # 분할된 파일에서 import
    ...

# entities/characters/lina_dialogues.py
DIALOGUES = {
    "default": {"pages": ["안녕!", "나는 리나야~"]},
    "식사": {"pages": ["냠냠", "맛있어!"]},
    # ... 많은 대사
}
```

### Region/Location 예시

```python
# entities/world/mansion.py
from entities.world.base import BaseRegion, Location, Edge

class Mansion(BaseRegion):
    ID = 0
    NAME = "저택"
    CURRENT_WEATHER = "맑음"

    LOCATIONS = [
        Location(0, "현관", is_indoor=True, appearance={
            "default": "저택의 입구다."
        }),
        Location(1, "거실", is_indoor=True, appearance={
            "default": "넓은 거실이다.",
            "밤": "어두운 거실. 벽난로만 희미하게 빛난다."
        }),
        Location(3, "식당", is_indoor=True),
        Location(14, "2층 복도", is_indoor=True),
        # ...
    ]

    EDGES = [
        Edge(0, 1, travel_time=1),           # 현관 ↔ 거실
        Edge(1, 3, travel_time=1),           # 거실 ↔ 식당
        Edge(1, 14, travel_time=2),          # 거실 ↔ 2층복도 (계단)
        # ...
    ]

# entities/world/__init__.py
from entities.world.base import RegionEdge

REGION_EDGES = [
    RegionEdge(
        location_a=(0, 12),  # 저택 앞마당
        location_b=(1, 0),   # 숲 입구
        travel_time=3
    ),
]
```

### Save/Load 분리

**정적 데이터 (Python 파일):**
- ID, NAME, 초기 위치, 초기 태그
- APPEARANCE, PRESENCE_TEXT, DIALOGUES
- SCHEDULE, ACTIONS

**동적 상태 (runtime/state.json):**
```json
{
    "game_time": {"year": 1, "month": 3, "day": 15, "minute": 480},
    "units": {
        "1": {
            "location": [0, 3],
            "tags": {"애정": 5, "피로": 2},
            "mood": ["기쁨"],
            "activity": "식사"
        }
    },
    "flags": {
        "chapter": 1,
        "first_met_lina": true
    },
    "inventories": {...},
    "object_states": {
        "50": {"켜짐": true}
    }
}
```

**로드 시:**
1. Python 엔티티 로드 → 초기 상태로 morld에 등록
2. state.json 로드 → 변경된 상태 덮어쓰기

**저장 시:**
1. 초기값과 달라진 부분만 state.json에 저장

---

## 로딩 UI 시스템

### 목표

- 엔티티 파일을 하나씩 로드하면서 진행률 표시
- Godot RichTextLabel에 "Loading... 45%" 형태로 표시

### Python 로더 설계

```python
# entities/__init__.py
import os
import importlib

def discover_all_entities():
    """모든 엔티티 파일 목록 반환 (로드 전)"""
    entities = []

    # characters/*.py
    char_dir = os.path.join(os.path.dirname(__file__), "characters")
    for f in os.listdir(char_dir):
        if f.endswith('.py') and f not in ('__init__.py', 'base.py'):
            entities.append(("character", f"characters.{f[:-3]}"))

    # objects/*.py
    obj_dir = os.path.join(os.path.dirname(__file__), "objects")
    for f in os.listdir(obj_dir):
        if f.endswith('.py') and f not in ('__init__.py', 'base.py'):
            entities.append(("object", f"objects.{f[:-3]}"))

    # items/*.py
    # world/*.py
    # ...

    return entities

def load_entity(module_path, on_progress=None):
    """단일 엔티티 로드 및 등록"""
    module = importlib.import_module(f"entities.{module_path}")
    # BaseEntity 서브클래스 찾아서 register()
    ...

def load_all_entities(on_progress=None):
    """
    모든 엔티티 로드
    on_progress: callback(current, total, name)
    """
    entities = discover_all_entities()
    total = len(entities)

    for i, (entity_type, module_path) in enumerate(entities):
        name = module_path.split('.')[-1]

        if on_progress:
            on_progress(i, total, name)

        load_entity(module_path)

    if on_progress:
        on_progress(total, total, "완료")
```

### C# 연동 (GameEngine)

```csharp
// GameEngine.cs
public void LoadEntitiesWithProgress(Action<int, int, string> onProgress)
{
    // Python 함수 호출
    var loadFunc = _python.GetVariable("entities", "load_all_entities");

    // 콜백 래핑
    PyObject callback = PyObject.FromManagedObject((int cur, int total, string name) => {
        onProgress?.Invoke(cur, total, name);
    });

    loadFunc.Call(callback);
}
```

### Godot UI 표시

```csharp
// GameEngine.cs
private RichTextLabel _loadingLabel;

public override void _Ready()
{
    _loadingLabel = GetNode<RichTextLabel>("LoadingLabel");

    LoadEntitiesWithProgress((current, total, name) => {
        int percent = total > 0 ? (current * 100 / total) : 0;
        _loadingLabel.Text = $"Loading... {percent}%\n{name}";

        // UI 갱신을 위해 프레임 대기 (필요시)
        // await ToSignal(GetTree(), "process_frame");
    });

    _loadingLabel.Visible = false;
    // 게임 시작
}
```

### 로딩 순서 (의존성 기반)

**필수 순서:**
1. **World/Region** 먼저 (위치 정보 필요)
2. **Items** (인벤토리 등록 시 아이템 정의 필요)
3. **Characters/Objects** (위치, 아이템 참조)

```
Phase 1: World 로딩
├─ Loading... 0%   (world/mansion)
├─ Loading... 5%   (world/forest)
├─ Loading... 10%  (region_edges 등록)
└─ Loading... 12%  (바닥 오브젝트 생성)

Phase 2: Items 로딩
├─ Loading... 15%  (items/rusty_key)
├─ Loading... 20%  (items/bread)
└─ Loading... 30%  (...)

Phase 3: Characters 로딩
├─ Loading... 35%  (characters/player)
├─ Loading... 45%  (characters/lina)
├─ Loading... 55%  (characters/sera)
├─ Loading... 65%  (characters/mila)
├─ Loading... 75%  (characters/yuki)
└─ Loading... 85%  (characters/ella)

Phase 4: Objects 로딩
├─ Loading... 90%  (objects/fireplace)
└─ Loading... 95%  (objects/bed)

Loading... 100% (완료)
```

**구현:**
```python
# entities/__init__.py
def load_all_entities(on_progress=None):
    """순서 보장 로딩"""
    phases = [
        ("world", discover_world_entities),      # Region, Location
        ("items", discover_item_entities),       # Item 정의
        ("characters", discover_character_entities),  # Player + NPC
        ("objects", discover_object_entities),   # 오브젝트
    ]

    # 전체 엔티티 수 계산
    all_entities = []
    for phase_name, discover_func in phases:
        all_entities.extend([(phase_name, e) for e in discover_func()])

    total = len(all_entities)

    for i, (phase, entity_info) in enumerate(all_entities):
        name = entity_info["name"]

        if on_progress:
            on_progress(i, total, f"{phase}/{name}")

        load_entity(entity_info)

        # World 로딩 완료 후 특수 처리
        if phase == "world" and is_last_in_phase(i, all_entities, "world"):
            register_region_edges()
            create_ground_objects()

    if on_progress:
        on_progress(total, total, "완료")
```

### 테스트 계획

1. **기본 로딩 테스트**
   - [ ] 엔티티 파일 3~5개로 테스트
   - [ ] 진행률 표시 확인
   - [ ] 로딩 완료 후 게임 시작 확인

2. **콜백 동작 테스트**
   - [ ] Python → C# 콜백 호출 확인
   - [ ] UI 갱신 타이밍 확인

3. **에러 처리**
   - [ ] 잘못된 파일 스킵
   - [ ] 에러 로그 출력

---

## 구현 우선순위 (수정)

### Phase 0: 로딩 시스템 테스트
- [ ] 간단한 엔티티 3개 (캐릭터 1, 오브젝트 1, 아이템 1)
- [ ] 로딩 진행률 UI 표시 테스트
- [ ] Python → C# 콜백 동작 확인

### Phase 1: 기반 구축
- [ ] BaseEntity, BaseCharacter, BaseObject, BaseItem, BaseRegion 클래스
- [ ] 자동 로딩 시스템
- [ ] morld API 확장

### Phase 2: 캐릭터 마이그레이션
- [ ] 리나 → lina.py 전환 (테스트)
- [ ] 나머지 캐릭터 전환
- [ ] 기존 JSON/폴더 구조 제거

### Phase 3: 전체 엔티티 마이그레이션
- [ ] 오브젝트 전환
- [ ] 아이템 전환
- [ ] World/Region 전환

### Phase 4: Save/Load
- [ ] 동적 상태 추출 로직
- [ ] state.json 저장/로드
- [ ] 초기값 비교 로직

---

## 시스템 구성요소 변화

### 삭제되는 시스템/클래스

| 대상 | 이유 |
|------|------|
| ScriptSystem | Python이 보조가 아닌 핵심이므로 별도 시스템 불필요. GameEngine에서 Python 직접 관리 |
| DailySchedule | Python SCHEDULE 리스트로 대체 |
| ScheduleEntry | Python SCHEDULE 리스트로 대체 |
| JSON 로더 | Python 파일에서 직접 정의로 대체 |

### 신설되는 시스템/클래스

| 대상 | 역할 |
|------|------|
| ThinkSystem | 모든 캐릭터의 Python think() 호출. PlayerSystem과 연동하여 플레이어 명령 override |
| WeatherSystem | 모든 Region의 Python update_weather() 호출 |
| Python BaseEntity | 모든 엔티티의 공통 기반 클래스 |
| Python BaseCharacter | 캐릭터 기반 클래스 (think, decide, on_reach 등) |
| Python BaseRegion | Region 기반 클래스 (update_weather 등) |
| Python BaseObject | 오브젝트 기반 클래스 |
| Python BaseItem | 아이템 기반 클래스 |

### 유지되는 시스템 (기능 변경 없음)

| 시스템 | 비고 |
|--------|------|
| MovementSystem | 스케줄 스택 기반 이동 처리 (기존과 동일) |
| BehaviorSystem | 종료 조건 체크 및 pop (기존과 동일) |
| EventSystem | on_reach, on_meet 감지 (기존과 동일) |
| TextUISystem | UI 렌더링 (기존과 동일) |
| WorldSystem | Terrain 데이터 관리 (Python에서 등록) |
| UnitSystem | Unit 데이터 관리 (Python에서 등록) |
| ItemSystem | Item 데이터 관리 (Python에서 등록) |
| InventorySystem | 인벤토리 관리 (기존과 동일) |

### 수정되는 시스템

| 시스템 | 변경 내용 |
|--------|----------|
| PlayerSystem | think() 결과 override 로직 추가. HasPendingCommand(), GetPendingCommand() 메서드 추가 |
| GameEngine | Python 인터프리터 직접 관리. 시스템 실행 순서에 ThinkSystem, WeatherSystem 추가 |

---

## 결정된 사항

### 1. DescribeSystem 처리

**결정: A) 현행 유지**
- C#에서 Appearance best-match 선택 로직 처리
- Python 캐릭터는 APPEARANCE 딕셔너리만 제공
- 이유: 선택 로직이 범용적이고 캐릭터마다 다를 필요 없음

### 2. ActionSystem 처리

**결정: A) 현행 유지**
- C#에서 talk, trade, use 등 액션 실행
- Python 캐릭터는 on_talk() 등 이벤트 핸들러만 제공
- 이유: 액션 틀(시간 소모, 결과 반환)은 C#, 콘텐츠(대화 내용)는 Python으로 역할 분리

### 3. 시스템 실행 순서

**결정:**

```
MovementSystem → EventSystem → WeatherSystem → ThinkSystem → BehaviorSystem → (플레이어 조작)
```

- MovementSystem: 이전 턴에 설정된 스케줄로 이동 처리
- EventSystem: 이동 결과로 이벤트 발생 (on_reach, on_meet → 다이얼로그 등)
- WeatherSystem: 날씨 업데이트 (다음 턴 think에 반영)
- ThinkSystem: 현재 시간 기준으로 다음 목표 설정 (스케줄 push)
- BehaviorSystem: 완료된 스케줄 pop (종료조건 체크)
- (플레이어 조작): pending 상태 또는 다음 명령 대기

---

## 메모

- 이 문서는 scenario02 (구 scenario04)의 Python 중심 시스템 설계
- JSON 파일 로딩 방식 폐기 → Python 파일에서 직접 정의
- 점진적 전환: 엔티티 타입별로 테스트하며 적용
- 로딩 UI는 Phase 0에서 먼저 검증
