# EventSystem 확장 기능 (미구현)

## 남은 작업

### Phase 5: 확장 기능 (기본)

1. **플래그 영속성 (세이브/로드)**
   - [ ] `events.py`: `export_flags()`, `import_flags()` 함수
   - [ ] `ScriptSystem`: 세이브/로드 연동
   - [ ] `flags_data.json` 파일 생성/로드

2. **캐릭터 데이터 수정 API**
   - [ ] morld 모듈: `set_unit_tag`, `add_unit_tag`
   - [ ] morld 모듈: `add_mood`, `remove_mood`

---

## 참고: 플래그 세이브/로드 설계

### Python 측

```python
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
```

### C# 측

```csharp
// 세이브 시
public void SaveGame(string path)
{
    var flagsJson = _scriptSystem?.CallFunctionString("events", "export_flags");
    // flagsJson을 세이브 파일에 포함
}

// 로드 시
public void LoadGame(string path)
{
    var flagsJson = // 세이브 파일에서 읽기
    _scriptSystem?.CallFunction("events", "import_flags", flagsJson);
}
```

---

## 참고: 캐릭터 데이터 수정 API 설계

### morld 모듈 확장

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
        unit.TraversalContext.SetTag(tagName, value);
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
        var current = unit.TraversalContext.GetTagValue(tagName);
        unit.TraversalContext.SetTag(tagName, current + delta);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 무드 추가/제거
morldModule.ModuleDict["add_mood"] = new PyBuiltinFunction("add_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    unit?.Mood.Add(mood);
    return PyBool.FromBool(unit != null);
});

morldModule.ModuleDict["remove_mood"] = new PyBuiltinFunction("remove_mood", args =>
{
    int unitId = args[0].ToInt();
    string mood = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    return PyBool.FromBool(unit?.Mood.Remove(mood) ?? false);
});
```

### Python 사용 예시

```python
import morld

def on_reach_healing_spring():
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

---

## Phase 6: 고급 이벤트 시스템 (애정행각 시나리오)

### 개요

NPC 간 만남(on_meet) 시 동적으로 행동이 추가되고, 해당 행동 수행 중 시간이 흐르며, 제3자 도착 시 중단되는 복합 이벤트 시스템.

### 요구사항

1. **동적 액션 추가**: 남녀 NPC가 만나면 "애정행각" 액션이 동적으로 추가됨
2. **스케줄 중단**: 행동 수행 중 기존 스케줄 일시 중단
3. **시간 경과**: 행동 수행 중에도 게임 시간이 흐름
4. **제3자 인터럽트**: 같은 장소에 다른 유닛 도착 시 행동 중단
5. **우선순위 스케줄**: 수면 시간 등 중요 스케줄이 오면 행동 강제 종료

### 설계

#### 1. 동적 액션 시스템

```python
# events.py

# 현재 활성 동적 액션 (유닛 ID → 액션 리스트)
_dynamic_actions = {}

def add_dynamic_action(unit_id, action):
    """유닛에 동적 액션 추가"""
    if unit_id not in _dynamic_actions:
        _dynamic_actions[unit_id] = []
    if action not in _dynamic_actions[unit_id]:
        _dynamic_actions[unit_id].append(action)

def remove_dynamic_action(unit_id, action):
    """유닛에서 동적 액션 제거"""
    if unit_id in _dynamic_actions:
        _dynamic_actions[unit_id] = [a for a in _dynamic_actions[unit_id] if a != action]

def get_dynamic_actions(unit_id):
    """유닛의 동적 액션 조회"""
    return _dynamic_actions.get(unit_id, [])
```

#### 2. morld API 확장

```csharp
// ScriptSystem.cs - morld 모듈 확장

// 유닛 액션 동적 추가
morldModule.ModuleDict["add_unit_action"] = new PyBuiltinFunction("add_unit_action", args =>
{
    int unitId = args[0].ToInt();
    string action = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null && !unit.Actions.Contains(action))
    {
        unit.Actions.Add(action);
        return PyBool.True;
    }
    return PyBool.False;
});

// 유닛 액션 동적 제거
morldModule.ModuleDict["remove_unit_action"] = new PyBuiltinFunction("remove_unit_action", args =>
{
    int unitId = args[0].ToInt();
    string action = args[1].AsString();

    var unit = _unitSystem?.GetUnit(unitId);
    return PyBool.FromBool(unit?.Actions.Remove(action) ?? false);
});

// 스케줄 레이어 Push (Python에서 호출)
morldModule.ModuleDict["push_schedule"] = new PyBuiltinFunction("push_schedule", args =>
{
    int unitId = args[0].ToInt();
    string name = args[1].AsString();
    string? endType = args.Count > 2 ? args[2].AsString() : null;
    string? endParam = args.Count > 3 ? args[3].AsString() : null;

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null)
    {
        unit.PushSchedule(new ScheduleLayer
        {
            Name = name,
            Schedule = null,
            EndConditionType = endType,
            EndConditionParam = endParam
        });
        return PyBool.True;
    }
    return PyBool.False;
});

// 스케줄 레이어 Pop
morldModule.ModuleDict["pop_schedule"] = new PyBuiltinFunction("pop_schedule", args =>
{
    int unitId = args[0].ToInt();

    var unit = _unitSystem?.GetUnit(unitId);
    if (unit != null && unit.ScheduleStack.Count > 1)
    {
        unit.PopSchedule();
        return PyBool.True;
    }
    return PyBool.False;
});

// 같은 위치의 유닛 목록 조회
morldModule.ModuleDict["get_units_at_location"] = new PyBuiltinFunction("get_units_at_location", args =>
{
    int regionId = args[0].ToInt();
    int locationId = args[1].ToInt();

    var units = _unitSystem?.GetUnitsAtLocation(regionId, locationId);
    var pyList = new PyList();
    if (units != null)
    {
        foreach (var unit in units)
        {
            pyList.Append(PyInt.Create(unit.Id));
        }
    }
    return pyList;
});
```

#### 3. 이벤트 처리 흐름

```python
# events.py

def handle_npc_meet(unit_ids):
    """NPC끼리 만남 - 조건 체크 후 동적 액션 추가"""
    # 남녀 조합 체크
    male_ids = []
    female_ids = []

    for unit_id in unit_ids:
        unit_info = morld.get_unit_info(unit_id)
        if unit_info:
            unit_type = unit_info.get("type", "")
            if unit_type == "male":
                male_ids.append(unit_id)
            elif unit_type == "female":
                female_ids.append(unit_id)

    # 남녀가 모두 있으면 동적 액션 추가
    if male_ids and female_ids:
        for unit_id in male_ids + female_ids:
            add_dynamic_action(unit_id, "script:romance_action:애정행각")
            morld.add_unit_action(unit_id, "script:romance_action:애정행각")


def romance_action(context_unit_id):
    """애정행각 액션 시작"""
    unit_info = morld.get_unit_info(context_unit_id)
    if not unit_info:
        return None

    region_id = unit_info.get("region_id")
    location_id = unit_info.get("location_id")

    # 같은 위치의 이성 찾기
    partner_id = find_opposite_gender_at_location(context_unit_id, region_id, location_id)
    if partner_id is None:
        return {
            "type": "monologue",
            "pages": ["상대방이 없다."],
            "time_consumed": 0,
            "button_type": "ok"
        }

    # 두 유닛 모두 "애정행각" 스케줄 Push
    morld.push_schedule(context_unit_id, "애정행각", "interrupt", f"{region_id}:{location_id}")
    morld.push_schedule(partner_id, "애정행각", "interrupt", f"{region_id}:{location_id}")

    # 플래그 설정
    set_flag(f"romance:{context_unit_id}:{partner_id}", True)

    return {
        "type": "monologue",
        "pages": [
            "둘은 서로를 바라본다...",
            "(시간이 흐른다...)"
        ],
        "time_consumed": 60,  # 1시간 소요
        "button_type": "ok"
    }


def handle_romance_interrupt(unit_id, intruder_id):
    """제3자 도착으로 애정행각 중단"""
    # 스케줄 Pop
    morld.pop_schedule(unit_id)

    # 파트너도 Pop
    partner_id = get_romance_partner(unit_id)
    if partner_id:
        morld.pop_schedule(partner_id)

    # 플래그 정리
    clear_romance_flags(unit_id)

    # 동적 액션 제거
    remove_dynamic_action(unit_id, "script:romance_action:애정행각")
    morld.remove_unit_action(unit_id, "script:romance_action:애정행각")

    if partner_id:
        remove_dynamic_action(partner_id, "script:romance_action:애정행각")
        morld.remove_unit_action(partner_id, "script:romance_action:애정행각")
```

#### 4. 인터럽트 종료 조건 타입

```csharp
// ScheduleLayer.cs - 새로운 종료 조건 타입 추가

// EndConditionType: "interrupt"
// EndConditionParam: "region_id:location_id"
// 의미: 해당 위치에 제3자가 도착하면 종료

public bool IsComplete(Unit unit, UnitSystem unitSystem)
{
    if (EndConditionType == "interrupt")
    {
        // 현재 위치에 다른 유닛이 도착했는지 체크
        var parts = EndConditionParam?.Split(':');
        if (parts?.Length == 2)
        {
            int regionId = int.Parse(parts[0]);
            int locationId = int.Parse(parts[1]);

            // 같은 위치의 유닛 수 체크 (2명 초과면 제3자 도착)
            var unitsAtLocation = unitSystem.GetUnitsAtLocation(regionId, locationId);
            if (unitsAtLocation.Count > 2)
            {
                return true;  // 인터럽트 발생
            }
        }
    }
    // ... 기존 조건들
}
```

#### 5. 우선순위 스케줄 처리

```python
# events.py

# 우선순위 스케줄 정의 (이 스케줄이 되면 현재 행동 강제 종료)
PRIORITY_SCHEDULES = ["수면", "식사"]

def check_priority_schedule(unit_id):
    """우선순위 스케줄 체크 - 해당 시간이 되면 현재 행동 중단"""
    unit_info = morld.get_unit_info(unit_id)
    if not unit_info:
        return False

    # 현재 스케줄 레이어가 우선순위 스케줄인지 체크
    # (BehaviorSystem에서 매 Step마다 호출)
    schedule_name = unit_info.get("schedule_name", "")

    # 하위 스케줄 레이어에 우선순위 스케줄이 있으면 현재 레이어 Pop
    # (구현: C# 측에서 스택 순회)

    return False
```

### 구현 순서

1. [ ] morld API 확장 (`add_unit_action`, `remove_unit_action`, `push_schedule`, `pop_schedule`, `get_units_at_location`)
2. [ ] 동적 액션 관리 Python 함수 (`add_dynamic_action`, `remove_dynamic_action`, `get_dynamic_actions`)
3. [ ] "interrupt" 종료 조건 타입 구현
4. [ ] `handle_npc_meet` 남녀 조합 체크 로직
5. [ ] `romance_action` 애정행각 액션 구현
6. [ ] `handle_romance_interrupt` 인터럽트 처리
7. [ ] 우선순위 스케줄 체크 로직
8. [ ] 테스트 시나리오 작성
