# 도착 이벤트 시스템 설계

## 1. 개요

플레이어가 특정 위치에 도착했을 때 이벤트(모놀로그 등)를 트리거하는 시스템.
Python 측에서 이벤트 정의 및 플래그 관리를 담당하고, C#에서는 도착 시점에 Python 함수를 호출하는 역할만 수행.

## 2. 핵심 요구사항

1. **위치 도착 시 이벤트 트리거**: 특정 location에 도착하면 모놀로그 표시
2. **일회성 이벤트 지원**: 한 번 발생한 이벤트는 다시 발생하지 않음
3. **Python 측 이벤트 관리**: 이벤트 정의, 플래그 관리 모두 Python에서 처리
4. **플래그 영속성**: 세이브/로드 시 플래그 상태 유지 (JSON export/import)
5. **캐릭터 데이터 수정**: 이벤트에서 HP 회복 등 유닛 데이터 변경 가능
6. **플레이어 영향 이벤트**: 모놀로그 스타일의 플레이어 대상 이벤트

## 3. C# 측 구현

### 3.1. 호출 시점

**위치**: `GameEngine._Process()` 또는 `MovementSystem`에서 이동 완료 감지 후

**호출 순서**:
```
이동 완료 감지 → ScriptSystem.CallOnArrive() → (결과가 있으면) ShowMonologue → ShowSituation
```

**중요**: `ShowSituation()` 호출 **전에** `on_arrive` 실행해야 함
- 도착 이벤트 모놀로그가 먼저 표시됨
- 사용자가 확인 후 상황 화면으로 전환

### 3.2. ScriptSystem 확장

```csharp
/// <summary>
/// 위치 도착 시 Python on_arrive 함수 호출
/// </summary>
/// <returns>모놀로그 결과 또는 null</returns>
public ScriptResult? CallOnArrive(int regionId, int locationId)
{
    try
    {
        var result = CallFunction("events", "on_arrive", regionId, locationId);
        return result;
    }
    catch
    {
        return null;  // 이벤트 없음 또는 에러
    }
}
```

### 3.3. GameEngine 또는 PlayerSystem에서 호출

```csharp
// 이동 완료 후 (ShowSituation 전에)
private void OnMoveComplete(int regionId, int locationId)
{
    var arriveResult = _scriptSystem?.CallOnArrive(regionId, locationId);

    if (arriveResult is MonologueScriptResult monoResult)
    {
        // 도착 이벤트 모놀로그 표시
        _textUISystem?.ShowMonologue(monoResult.Pages, monoResult.TimeConsumed,
            monoResult.ButtonType, monoResult.DoneCallback, monoResult.CancelCallback);
    }
    else
    {
        // 이벤트 없으면 바로 상황 화면
        UpdateSituationText();
    }
}
```

## 4. Python 측 구현

### 4.1. 파일 구조

```
scenarios/scenario02/python/
├── monologues.py      # 기존 모놀로그/스크립트 함수
├── events.py          # 도착 이벤트 핸들러 (신규)
└── flags.py           # 플래그 관리 (신규, 또는 events.py에 통합)
```

### 4.2. events.py 설계

```python
# events.py

import json

# ============================================================
# 플래그 관리
# ============================================================

_flags = {}                    # 범용 플래그 (key → value)
_triggered_events = set()      # 발생한 이벤트 ID 집합

def set_flag(key, value=True):
    """플래그 설정"""
    _flags[key] = value

def get_flag(key, default=None):
    """플래그 조회"""
    return _flags.get(key, default)

def has_flag(key):
    """플래그 존재 여부"""
    return key in _flags

def clear_flag(key):
    """플래그 삭제"""
    _flags.pop(key, None)

# ============================================================
# 세이브/로드
# ============================================================

def export_flags():
    """세이브용 JSON 문자열 반환"""
    return json.dumps({
        "flags": _flags,
        "triggered_events": list(_triggered_events)
    }, ensure_ascii=False)

def import_flags(json_str):
    """로드용 JSON 파싱"""
    global _flags, _triggered_events
    if not json_str:
        _flags = {}
        _triggered_events = set()
        return

    data = json.loads(json_str)
    _flags = data.get("flags", {})
    _triggered_events = set(data.get("triggered_events", []))

# ============================================================
# 도착 이벤트 정의
# ============================================================

# 위치별 이벤트 핸들러 매핑
# key: (region_id, location_id)
# value: 함수명 (문자열) 또는 함수 객체
ARRIVE_EVENTS = {
    (0, 2): "on_arrive_bedroom",     # 침실
    (0, 5): "on_arrive_basement",    # 지하실
}

# ============================================================
# 메인 진입점
# ============================================================

def on_arrive(region_id, location_id):
    """
    C#에서 호출하는 메인 함수

    Returns:
        dict: 모놀로그 결과 (있으면)
        None: 이벤트 없음
    """
    key = (region_id, location_id)

    # 이벤트 핸들러 찾기
    handler = ARRIVE_EVENTS.get(key)
    if handler is None:
        return None

    # 문자열이면 함수로 변환
    if isinstance(handler, str):
        handler = globals().get(handler)
        if handler is None:
            return None

    # 이미 발생한 이벤트인지 확인 (일회성)
    event_id = f"arrive:{region_id}:{location_id}"
    if event_id in _triggered_events:
        return None

    # 핸들러 실행
    result = handler()

    # 결과가 있으면 이벤트 발생으로 기록
    if result is not None:
        _triggered_events.add(event_id)

    return result

# ============================================================
# 이벤트 핸들러 구현
# ============================================================

def on_arrive_bedroom():
    """침실 첫 방문 이벤트"""
    return {
        "type": "monologue",
        "pages": [
            "...이상한 기분이 든다.",
            "누군가 이 방에서 나를 지켜보고 있는 것 같다."
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }

def on_arrive_basement():
    """지하실 첫 방문 이벤트"""
    return {
        "type": "monologue",
        "pages": [
            "차가운 공기가 피부를 스친다.",
            "어둠 속에서 무언가가 움직이는 소리가 들린다..."
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }
```

### 4.3. 반복 이벤트 지원 (선택적)

일회성이 아닌 반복 이벤트가 필요한 경우:

```python
# 반복 이벤트는 ARRIVE_EVENTS 대신 REPEATABLE_ARRIVE_EVENTS에 등록
REPEATABLE_ARRIVE_EVENTS = {
    (0, 3): "on_arrive_hallway",  # 복도 - 매번 발생
}

def on_arrive(region_id, location_id):
    key = (region_id, location_id)

    # 일회성 이벤트 먼저 체크
    handler = ARRIVE_EVENTS.get(key)
    if handler:
        event_id = f"arrive:{region_id}:{location_id}"
        if event_id not in _triggered_events:
            result = _call_handler(handler)
            if result:
                _triggered_events.add(event_id)
            return result

    # 반복 이벤트 체크
    handler = REPEATABLE_ARRIVE_EVENTS.get(key)
    if handler:
        return _call_handler(handler)

    return None
```

## 5. 캐릭터 데이터 수정 API

### 5.1. morld 모듈 확장 (ScriptSystem)

```csharp
// 유닛 태그(스탯) 수정
morldModule.ModuleDict["set_unit_tag"] = new PyBuiltinFunction("set_unit_tag", args =>
{
    int unitId = args[0].ToInt();
    string tagName = args[1].AsString();
    int value = args[2].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        unit.Tags[tagName] = value;
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 태그 증가/감소
morldModule.ModuleDict["add_unit_tag"] = new PyBuiltinFunction("add_unit_tag", args =>
{
    int unitId = args[0].ToInt();
    string tagName = args[1].AsString();
    int delta = args[2].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        if (!unit.Tags.ContainsKey(tagName))
            unit.Tags[tagName] = 0;
        unit.Tags[tagName] += delta;
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 무드 추가
morldModule.ModuleDict["add_mood"] = new PyBuiltinFunction("add_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        unit.Mood.Add(mood);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 무드 제거
morldModule.ModuleDict["remove_mood"] = new PyBuiltinFunction("remove_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        return PyBool.FromBool(unit.Mood.Remove(mood));
    }
    return PyBool.False;
});
```

### 5.2. Python 사용 예시

```python
import morld

def on_arrive_healing_spring():
    """치유의 샘 도착 이벤트"""
    player_id = morld.get_player_id()

    # HP 회복
    morld.add_unit_tag(player_id, "hp", 30)

    # 상태이상 제거
    morld.remove_mood(player_id, "독")
    morld.remove_mood(player_id, "피로")

    return {
        "type": "monologue",
        "pages": [
            "맑은 샘물이 흐르고 있다.",
            "물을 마시자 몸에 활력이 돌아온다.",
            "[HP가 30 회복되었다]"
        ],
        "time_consumed": 5,
        "button_type": "ok"
    }
```

## 6. 플래그 세이브/로드 연동

### 6.1. 세이브 시

```csharp
// SaveManager 또는 GameEngine에서
public void SaveGame(string path)
{
    // 기존 시스템 저장...

    // Python 플래그 저장
    var flagsJson = _scriptSystem?.CallFunctionString("events", "export_flags");
    // flagsJson을 세이브 파일에 포함
}
```

### 6.2. 로드 시

```csharp
public void LoadGame(string path)
{
    // 기존 시스템 로드...

    // Python 플래그 로드
    var flagsJson = // 세이브 파일에서 읽기
    _scriptSystem?.CallFunction("events", "import_flags", flagsJson);
}
```

## 7. 코드 분석 결과

### 7.1. 이동 완료 감지 위치

**현재 흐름:**
```
1. MetaActionHandler.HandleMoveAction()
   → PlayerSystem.RequestCommand("이동:regionId:localId")

2. PlayerSystem.ExecuteMove()
   → 스케줄 Push + RequestTimeAdvance()

3. GameEngine._Process()
   → while (HasPendingTime): world.Step()
   → MovementSystem.Proc(): 유닛 이동 처리

4. 이동 완료 감지: GameEngine._Process()
   → if (!_playerSystem.HasPendingTime): UpdateSituationText()
```

**결론:**
- 이동 완료는 `GameEngine._Process()`에서 `!HasPendingTime` 조건으로 감지
- `UpdateSituationText()` → `ShowSituation()` 호출 **전에** `on_arrive` 실행 필요

### 7.2. 플레이어 위치 정보

이동 완료 시점에 플레이어 위치를 가져오는 방법:
```csharp
var player = _playerSystem.GetPlayerUnit();
var regionId = player.CurrentLocation.RegionId;
var localId = player.CurrentLocation.LocalId;
```

## 8. 검토 사항

### 8.1. 해결된 사항

1. **✅ on_arrive 호출 위치**
   - `GameEngine._Process()`에서 `!HasPendingTime` 조건 만족 시
   - `UpdateSituationText()` 호출 전에 `CallOnArrive()` 실행

2. **✅ context_unit_id 전달**
   - `on_arrive`는 `context_unit_id` 없이 `(region_id, location_id)`만 전달
   - 도착 이벤트는 위치 기반이므로 유닛 컨텍스트가 불필요
   - 기존 `script:` 함수와 다른 시그니처 사용 (합리적)

3. **✅ 모놀로그 완료 후 상황 갱신**
   - 기존 `HandleMonologueDoneAction`에서 `DoneCallback` 없으면 `RequestUpdateSituation()` 호출
   - 도착 이벤트 모놀로그도 동일하게 처리됨 (추가 작업 불필요)

### 8.2. 설계 결정 필요

1. **events.py 위치**
   - 시나리오별 (`scenarios/scenario02/python/events.py`) ✓
   - 이벤트는 시나리오마다 다르므로 시나리오별이 적합

2. **플래그 저장 위치**
   - 옵션 A: 별도 JSON 파일 (`flags_data.json`)
   - 옵션 B: 기존 세이브 파일에 포함
   - **제안**: 별도 파일이 관리하기 쉬움

3. **반복 이벤트 지원 여부**
   - Phase 1에서는 일회성만 지원
   - 필요시 `REPEATABLE_ARRIVE_EVENTS` 추가

### 8.3. 잠재적 문제점

1. **휴식 후 on_arrive 호출 문제**
   - 현재 `!HasPendingTime` 조건은 이동 완료뿐 아니라 휴식 완료 시에도 만족
   - 휴식 시에는 위치가 변하지 않으므로 `on_arrive` 호출 불필요
   - **해결**: 위치 변경 여부를 추적하거나, `on_arrive`에서 중복 호출 방지

2. **이전 위치 추적 필요**
   ```csharp
   // GameEngine에 추가
   private LocationRef? _lastPlayerLocation = null;

   // _Process에서
   if (!_playerSystem.HasPendingTime)
   {
       var currentLocation = player.CurrentLocation;
       if (_lastPlayerLocation != currentLocation)
       {
           // 위치가 변경된 경우에만 on_arrive 호출
           CallOnArrive(currentLocation);
           _lastPlayerLocation = currentLocation;
       }
       UpdateSituationText();
   }
   ```

3. **게임 시작 시 초기 위치**
   - `_Ready()`에서 `_lastPlayerLocation` 초기화 필요
   - 또는 첫 번째 이동 전에는 `on_arrive` 호출 안 함

### 8.4. 구현 순서

1. **Phase 1**: 기본 도착 이벤트
   - [x] 설계 문서 작성
   - [ ] `GameEngine`: 위치 변경 추적 + `CallOnArrive()` 호출
   - [ ] `ScriptSystem`: `CallOnArrive()` 메서드 추가
   - [ ] `events.py`: 기본 구조 + 테스트 이벤트

2. **Phase 2**: 캐릭터 데이터 수정 API
   - [ ] morld 모듈: `set_unit_tag`, `add_unit_tag`
   - [ ] morld 모듈: `add_mood`, `remove_mood`

3. **Phase 3**: 플래그 영속성
   - [ ] `events.py`: `export_flags`, `import_flags`
   - [ ] `ScriptSystem`: 세이브/로드 연동
   - [ ] `flags_data.json` 파일 생성/로드

## 9. 개선된 설계 (v2)

### 9.1. 핵심 변경점

1. **EventSystem 분리**: InventorySystem처럼 독립 시스템으로 분리
2. **이벤트 배치 처리**: 이벤트를 수집해서 한 번에 Python으로 전달
3. **Python 측 일괄 처리**: `on_event_list(ev_list)` 함수에서 모든 이벤트 처리

### 9.2. 이벤트 타입 정의

```csharp
// EventType 열거형
public enum EventType
{
    GameStart,      // 게임 시작
    OnReach,        // 위치 도착 (플레이어)
    OnMeet,         // 유닛들이 같은 위치에 있음
    OnTimePass,     // 시간 경과 (특정 시간대 진입)
    OnItemGet,      // 아이템 획득
    OnItemLost,     // 아이템 소실
    // ... 확장 가능
}

// 이벤트 데이터
public class GameEvent
{
    public EventType Type { get; set; }
    public List<object> Args { get; set; } = new();

    // 팩토리 메서드
    public static GameEvent GameStart()
        => new() { Type = EventType.GameStart };

    public static GameEvent OnReach(int unitId, int regionId, int locationId)
        => new() { Type = EventType.OnReach, Args = { unitId, regionId, locationId } };

    public static GameEvent OnMeet(params int[] unitIds)
        => new() { Type = EventType.OnMeet, Args = unitIds.Cast<object>().ToList() };
}
```

### 9.3. EventSystem 설계

```csharp
public class EventSystem : ECS.System
{
    // 이번 Step에서 발생한 이벤트 큐
    private readonly List<GameEvent> _pendingEvents = new();

    // 시스템 참조
    private ScriptSystem _scriptSystem;
    private TextUISystem _textUISystem;

    // 이전 상태 추적 (이벤트 감지용)
    private Dictionary<int, LocationRef> _lastLocations = new();

    /// <summary>
    /// 이벤트 등록 (외부에서 호출)
    /// </summary>
    public void Enqueue(GameEvent evt)
    {
        _pendingEvents.Add(evt);
    }

    /// <summary>
    /// 이벤트 큐 플러시 및 Python 호출
    /// </summary>
    public void FlushEvents()
    {
        if (_pendingEvents.Count == 0) return;

        // Python에 이벤트 리스트 전달
        var result = _scriptSystem?.CallEventHandler(_pendingEvents);
        _pendingEvents.Clear();

        // 결과 처리 (모놀로그 등)
        ProcessEventResult(result);
    }

    /// <summary>
    /// 위치 변경 감지 및 OnReach 이벤트 생성
    /// </summary>
    public void DetectLocationChanges(UnitSystem unitSystem)
    {
        foreach (var unit in unitSystem.Units.Values)
        {
            var currentLoc = unit.CurrentLocation;

            if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
            {
                if (currentLoc != lastLoc)
                {
                    Enqueue(GameEvent.OnReach(unit.Id, currentLoc.RegionId, currentLoc.LocalId));
                }
            }

            _lastLocations[unit.Id] = currentLoc;
        }
    }

    /// <summary>
    /// 같은 위치에 있는 유닛들의 OnMeet 이벤트 생성
    /// </summary>
    public void DetectMeetings(UnitSystem unitSystem, int playerId)
    {
        var player = unitSystem.GetUnit(playerId);
        if (player == null) return;

        var unitsAtSameLocation = unitSystem.Units.Values
            .Where(u => u.Id != playerId && u.CurrentLocation == player.CurrentLocation && !u.IsObject)
            .Select(u => u.Id)
            .ToList();

        if (unitsAtSameLocation.Count > 0)
        {
            var allIds = new List<int> { playerId };
            allIds.AddRange(unitsAtSameLocation);
            Enqueue(GameEvent.OnMeet(allIds.ToArray()));
        }
    }
}
```

### 9.4. Python 측 이벤트 핸들러

```python
# events.py

import morld

# ============================================================
# 플래그 관리
# ============================================================

_flags = {}
_triggered_events = set()

# ============================================================
# 이벤트 핸들러 등록
# ============================================================

# 이벤트 타입별 핸들러
EVENT_HANDLERS = {
    "game_start": "handle_game_start",
    "on_reach": "handle_on_reach",
    "on_meet": "handle_on_meet",
}

# 위치별 도착 이벤트
REACH_EVENTS = {
    (0, 2): "on_reach_bedroom",
    (0, 5): "on_reach_basement",
}

# ============================================================
# 메인 진입점 (C#에서 호출)
# ============================================================

def on_event_list(ev_list):
    """
    이벤트 리스트를 받아서 순차 처리

    Args:
        ev_list: [("game_start",), ("on_reach", 0, 0, 2), ("on_meet", 0, 1, 2), ...]

    Returns:
        첫 번째 모놀로그 결과 또는 None
    """
    for event in ev_list:
        event_type = event[0]
        args = event[1:] if len(event) > 1 else ()

        handler_name = EVENT_HANDLERS.get(event_type)
        if handler_name:
            handler = globals().get(handler_name)
            if handler:
                result = handler(*args)
                if result is not None:
                    # 첫 번째 결과만 반환 (나머지는 다음 Step에서 처리)
                    return result

    return None

# ============================================================
# 이벤트 핸들러 구현
# ============================================================

def handle_game_start():
    """게임 시작 이벤트"""
    event_id = "game_start"
    if event_id in _triggered_events:
        return None

    _triggered_events.add(event_id)

    return {
        "type": "monologue",
        "pages": [
            "어둠 속에서 눈을 떴다.",
            "여기는... 어디지?"
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }

def handle_on_reach(unit_id, region_id, location_id):
    """위치 도착 이벤트"""
    # 플레이어만 처리 (NPC 도착은 무시)
    player_id = morld.get_player_id()
    if unit_id != player_id:
        return None

    # 위치별 핸들러 찾기
    key = (region_id, location_id)
    handler_name = REACH_EVENTS.get(key)
    if handler_name is None:
        return None

    # 일회성 체크
    event_id = f"reach:{region_id}:{location_id}"
    if event_id in _triggered_events:
        return None

    handler = globals().get(handler_name)
    if handler:
        result = handler()
        if result:
            _triggered_events.add(event_id)
        return result

    return None

def handle_on_meet(unit_id, *other_unit_ids):
    """유닛 만남 이벤트"""
    # 특정 NPC와의 만남 처리 등
    return None

# ============================================================
# 위치별 핸들러
# ============================================================

def on_reach_bedroom():
    """침실 도착 이벤트"""
    return {
        "type": "monologue",
        "pages": [
            "...이상한 기분이 든다.",
            "누군가 이 방에서 나를 지켜보고 있는 것 같다."
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }

def on_reach_basement():
    """지하실 도착 이벤트"""
    return {
        "type": "monologue",
        "pages": [
            "차가운 공기가 피부를 스친다.",
            "어둠 속에서 무언가가 움직이는 소리가 들린다..."
        ],
        "time_consumed": 0,
        "button_type": "ok"
    }
```

### 9.5. 호출 흐름

```
GameEngine._Ready()
├─ EventSystem 초기화
├─ _lastLocations 초기화 (현재 위치로)
└─ eventSystem.Enqueue(GameEvent.GameStart())

GameEngine._Process()
├─ while (HasPendingTime): world.Step()
└─ if (!HasPendingTime):
    ├─ eventSystem.DetectLocationChanges(unitSystem)
    ├─ eventSystem.DetectMeetings(unitSystem, playerId)
    ├─ eventSystem.FlushEvents()  // Python 호출
    │   └─ 결과가 모놀로그면 ShowMonologue()
    └─ if (모놀로그 없으면) UpdateSituationText()
```

### 9.6. InventorySystem 이벤트 연동

```csharp
// InventorySystem.OnInventoryChanged 콜백에서
_inventorySystem.OnInventoryChanged += (evt) =>
{
    // 기존 액션 로그 생성...

    // EventSystem에 이벤트 등록
    if (evt.Type == InventoryEventType.ItemAdded)
    {
        _eventSystem?.Enqueue(GameEvent.OnItemGet(evt.ToOwner, evt.ItemId, evt.Count));
    }
    else if (evt.Type == InventoryEventType.ItemLost)
    {
        _eventSystem?.Enqueue(GameEvent.OnItemLost(evt.FromOwner, evt.ItemId, evt.Count));
    }
};
```

### 9.7. 장점

1. **관심사 분리**: 이벤트 수집/감지 로직이 EventSystem에 집중
2. **배치 처리**: 여러 이벤트를 한 번의 Python 호출로 처리
3. **확장성**: 새 이벤트 타입 추가가 쉬움
4. **Python 제어**: 이벤트 처리 순서/우선순위를 Python에서 결정

## 10. 시나리오01 분석 결과

### 10.1. 현재 이벤트 시스템 (on_event)

**흐름:**
```
GameEngine._Ready()
  → TriggerEvent("ready")
    → ScriptSystem.TriggerEvent("ready")
      → Python: on_event("ready")
        → get_monologue("intro_001") + get_job_select_monologue()
        → 페이지 결합하여 반환
      → MonologueEventResult 반환
    → ShowMonologue()
```

**핵심 패턴:**
- `on_event("ready")`에서 여러 모놀로그를 **페이지 결합**하여 단일 모놀로그로 반환
- 직업 선택 페이지에서 `button_type: "none"` + BBCode 선택지 사용
- 선택 → `script:job_select:warrior` → YesNo 확인 → `yes_callback: "job_confirm:warrior"`

### 10.2. 다중 모놀로그 처리 방식

**현재 방식:** 페이지 결합 (`combined_pages = mono["pages"] + job_mono["pages"]`)

**대안:** DoneCallback 체이닝
```python
def on_event("ready"):
    return {
        "type": "monologue",
        "pages": ["인트로 페이지1", "인트로 페이지2"],
        "done_callback": "show_job_select"
    }

def show_job_select(context_unit_id):
    return {
        "type": "monologue",
        "pages": ["직업 선택...", "[url=script:...]"],
        "button_type": "none"
    }
```

→ **결론:** 현재 시스템에서 다중 모놀로그는 페이지 결합 또는 DoneCallback 체이닝으로 이미 가능

## 11. 설계 개선 (v3)

### 11.1. OnMeet 중복 방지 (C# 측)

```csharp
// EventSystem
private HashSet<string> _lastMeetings = new();

public void DetectMeetings(UnitSystem unitSystem, int playerId)
{
    var player = unitSystem.GetUnit(playerId);
    if (player == null) return;

    // 현재 위치의 유닛들 수집
    var unitsAtSameLocation = unitSystem.Units.Values
        .Where(u => u.Id != playerId && u.CurrentLocation == player.CurrentLocation && !u.IsObject)
        .Select(u => u.Id)
        .OrderBy(id => id)  // 순서 정규화
        .ToList();

    if (unitsAtSameLocation.Count == 0) return;

    // 만남 키 생성 (정렬된 ID 집합)
    var allIds = new List<int> { playerId };
    allIds.AddRange(unitsAtSameLocation);
    allIds.Sort();
    var meetingKey = string.Join(",", allIds);

    // 이미 발생한 만남인지 확인
    if (_lastMeetings.Contains(meetingKey)) return;

    _lastMeetings.Add(meetingKey);
    Enqueue(GameEvent.OnMeet(allIds.ToArray()));
}

// 위치 변경 시 만남 상태 리셋
public void DetectLocationChanges(UnitSystem unitSystem)
{
    foreach (var unit in unitSystem.Units.Values)
    {
        var currentLoc = unit.CurrentLocation;

        if (_lastLocations.TryGetValue(unit.Id, out var lastLoc))
        {
            if (currentLoc != lastLoc)
            {
                // 유닛이 이동했으면 관련 만남 키 제거
                ClearMeetingsForUnit(unit.Id);
                Enqueue(GameEvent.OnReach(unit.Id, currentLoc.RegionId, currentLoc.LocalId));
            }
        }

        _lastLocations[unit.Id] = currentLoc;
    }
}

// 역방향 인덱스: 유닛 ID → 해당 유닛이 포함된 만남 키 집합
private Dictionary<int, HashSet<string>> _unitToMeetings = new();

private void ClearMeetingsForUnit(int unitId)
{
    if (_unitToMeetings.TryGetValue(unitId, out var keys))
    {
        foreach (var key in keys)
            _lastMeetings.Remove(key);
        _unitToMeetings.Remove(unitId);
    }
}

// 만남 키 등록 시 역방향 인덱스도 갱신
private void AddMeetingKey(string meetingKey, int[] unitIds)
{
    _lastMeetings.Add(meetingKey);
    foreach (var id in unitIds)
    {
        if (!_unitToMeetings.ContainsKey(id))
            _unitToMeetings[id] = new HashSet<string>();
        _unitToMeetings[id].Add(meetingKey);
    }
}
```

**성능 분석 (100 유닛 기준):**
| 연산 | 복잡도 | 예상 시간 |
|------|--------|----------|
| 유닛 순회 | O(n) | ~0.01ms |
| 정렬 (만남 유닛 k개) | O(k log k) | ~0.001ms |
| 키 생성 | O(k) | ~0.001ms |
| HashSet 조회 | O(1) | ~0.0001ms |
| ClearMeetingsForUnit (역방향 인덱스) | O(m) | ~0.01ms |

**결론:** 100 유닛 기준 전체 연산 ~0.1-0.5ms, 프레임 영향 없음

### 11.2. 플레이어 vs NPC 구분 (Python 측)

```python
def on_event_list(ev_list):
    """
    이벤트 리스트 처리

    Args:
        ev_list: [
            ("game_start",),
            ("on_reach", unit_id, region_id, location_id),
            ("on_meet", unit_id1, unit_id2, ...),
        ]
    """
    player_id = morld.get_player_id()

    for event in ev_list:
        event_type = event[0]

        if event_type == "on_reach":
            unit_id, region_id, location_id = event[1], event[2], event[3]
            is_player = (unit_id == player_id)

            # 플레이어 도착 이벤트
            if is_player:
                result = handle_player_reach(region_id, location_id)
                if result:
                    return result

            # NPC 도착 이벤트 (모놀로그 없음, 상태 변경만)
            else:
                handle_npc_reach(unit_id, region_id, location_id)

        elif event_type == "on_meet":
            unit_ids = event[1:]
            is_player_involved = (player_id in unit_ids)

            if is_player_involved:
                # 플레이어와 NPC의 만남 → 다이얼로그 가능
                result = handle_player_meet(unit_ids)
                if result:
                    return result
            else:
                # NPC끼리 만남 → 상태 변경만
                handle_npc_meet(unit_ids)

    return None

def handle_player_reach(region_id, location_id):
    """플레이어 도착 이벤트 - 모놀로그 표시 가능"""
    key = (region_id, location_id)
    if key in REACH_EVENTS:
        event_id = f"reach:{region_id}:{location_id}"
        if event_id not in _triggered_events:
            handler = globals().get(REACH_EVENTS[key])
            if handler:
                result = handler()
                if result:
                    _triggered_events.add(event_id)
                return result
    return None

def handle_npc_reach(unit_id, region_id, location_id):
    """NPC 도착 이벤트 - 상태 변경만 (모놀로그 없음)"""
    # 예: NPC가 특정 위치에 도착하면 플래그 설정
    # set_flag(f"npc_{unit_id}_at_{region_id}_{location_id}", True)
    pass

def handle_player_meet(unit_ids):
    """플레이어-NPC 만남 - 모놀로그 표시 가능"""
    player_id = morld.get_player_id()
    npc_ids = [uid for uid in unit_ids if uid != player_id]

    # 특정 NPC와의 첫 만남 처리
    for npc_id in npc_ids:
        event_id = f"meet:{player_id}:{npc_id}"
        if event_id not in _triggered_events:
            handler_name = MEET_EVENTS.get(npc_id)
            if handler_name:
                handler = globals().get(handler_name)
                if handler:
                    result = handler(npc_id)
                    if result:
                        _triggered_events.add(event_id)
                    return result
    return None

def handle_npc_meet(unit_ids):
    """NPC끼리 만남 - 상태 변경만"""
    pass
```

### 11.3. 이벤트 타입별 Python 결과 처리

| 이벤트 | 플레이어 관련 | 결과 타입 |
|--------|---------------|-----------|
| game_start | Y | 모놀로그 |
| on_reach (player) | Y | 모놀로그 |
| on_reach (npc) | N | None (상태 변경) |
| on_meet (player + npc) | Y | 모놀로그 |
| on_meet (npc only) | N | None (상태 변경) |
| on_item_get | Y | 모놀로그 (선택적) |
| on_time_pass | Y | 모놀로그 (선택적) |

## 12. 최종 설계 결정

### 12.1. 확정 사항

1. **EventSystem 분리**: 독립 시스템으로 분리 ✓
2. **이벤트 배치 처리**: `on_event_list(ev_list)` 인터페이스 ✓
3. **OnMeet 중복 방지**: C# HashSet으로 관리, 위치 변경 시 리셋 ✓
4. **플레이어/NPC 구분**: Python에서 `morld.get_player_id()` 비교 ✓
5. **다중 모놀로그**: DoneCallback 체이닝 또는 페이지 결합 ✓

### 12.2. 이벤트 추적 대상 필터링

**문제**: 모든 Unit(캐릭터+오브젝트)을 추적하면 불필요한 이벤트가 생성됨

**해결**: `GeneratesEvents` 속성으로 필터링

```csharp
// Unit.cs에 추가
public bool EventTracking { get; set; } = false;  // 오브젝트용 수동 활성화
public bool GeneratesEvents => !IsObject || EventTracking;
```

**동작 규칙:**
| 유닛 타입 | IsObject | EventTracking | GeneratesEvents |
|-----------|----------|---------------|-----------------|
| 캐릭터 | false | (무시) | **true** (자동) |
| 일반 오브젝트 | true | false | false |
| 이벤트 오브젝트 | true | true | **true** (수동) |

**사용 예시:**
- 캐릭터(NPC): 자동으로 OnReach, OnMeet 이벤트 생성
- 일반 오브젝트(상자, 의자 등): 이벤트 없음
- 함정 문, 트리거 오브젝트: `EventTracking=true`로 활성화

**EventSystem에서 필터링:**
```csharp
public void DetectLocationChanges(UnitSystem unitSystem)
{
    foreach (var unit in unitSystem.Units.Values)
    {
        // 이벤트 비활성 유닛은 스킵
        if (!unit.GeneratesEvents) continue;

        var currentLoc = unit.CurrentLocation;
        // ... 기존 로직
    }
}

public void DetectMeetings(UnitSystem unitSystem, int playerId)
{
    var player = unitSystem.GetUnit(playerId);
    if (player == null) return;

    // 이벤트 활성 유닛만 대상
    var unitsAtSameLocation = unitSystem.Units.Values
        .Where(u => u.Id != playerId
                 && u.CurrentLocation == player.CurrentLocation
                 && u.GeneratesEvents)  // IsObject 대신 GeneratesEvents
        .Select(u => u.Id)
        .ToList();
    // ...
}
```

**unit_data.json 예시:**
```json
{
    "id": 50,
    "name": "함정 문",
    "type": "object",
    "eventTracking": true,
    "regionId": 0,
    "locationId": 5
}
```

### 12.3. 구현 순서 (최종)

1. **Phase 1**: EventSystem 기본 구조
   - [x] `EventSystem` 클래스 생성
   - [x] `GameEvent` 클래스 및 EventType enum
   - [x] GameEngine에서 EventSystem 초기화 및 호출

2. **Phase 2**: 이벤트 감지 로직
   - [x] DetectLocationChanges (OnReach)
   - [x] DetectMeetings (OnMeet, 중복 방지 포함)

3. **Phase 3**: Python 연동
   - [x] ScriptSystem.CallEventHandler() 구현
   - [x] events.py 기본 구조 + on_event_list()

4. **Phase 4**: 테스트 이벤트
   - [x] scenario02에 도착 이벤트 추가
   - [x] 동작 확인

5. **Phase 5**: 확장 기능
   - [ ] 플래그 export/import
   - [ ] 캐릭터 데이터 수정 API
