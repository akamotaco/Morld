# Morld 확장 기능 계획

---

## 완료된 작업

### Phase 7: 스케줄 수명 시스템 (완료)

1. **ScheduleLayer.RemainingLifetime**
   - [x] 스케줄 레이어의 남은 수명 (분) 필드 추가
   - [x] 0 이하면 무제한, 양수면 시간 경과에 따라 감소

2. **MovementSystem에서 Lifetime 감소**
   - [x] 시간 진행 시 각 유닛의 스케줄 RemainingLifetime 감소

3. **BehaviorSystem에서 Lifetime 만료 체크**
   - [x] EndConditionType == "대기" && RemainingLifetime == 0 시 자동 pop

4. **freeze_others 개선**
   - [x] "대기" 스케줄을 RemainingLifetime = time_consumed로 push
   - [x] time_consumed 분 경과 후 자동 pop → 원래 스케줄 복귀

5. **Python 이벤트 필터링 예시**
   - [x] 수면 중 meet 이벤트 무시 패턴 추가 (scenario04)

---

## 남은 작업

### Phase 5: 확장 기능 (기본)

1. **플래그 영속성 (세이브/로드)**
   - [ ] `events.py`: `export_flags()`, `import_flags()` 함수
   - [ ] `ScriptSystem`: 세이브/로드 연동
   - [ ] `flags_data.json` 파일 생성/로드

2. **캐릭터 데이터 수정 API** (일부 구현됨)
   - [x] morld 모듈: `set_unit_tags` (구현 완료)
   - [ ] morld 모듈: `set_unit_tag`, `add_unit_tag` (단일 태그 조작)
   - [ ] morld 모듈: `add_mood`, `remove_mood`

3. **데이터 초기화 API** (구현 완료)
   - [x] morld 모듈: `clear_units()`, `clear_items()`, `clear_inventory()`, `clear_world()`, `clear_all()`
   - [x] morld 모듈: `set_unit_location()`, `advance_time()`
   - [x] morld 모듈: `push_schedule()`

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

### morld 모듈 확장 (미구현)

```csharp
// 유닛 태그(스탯) 수정 - 단일 태그
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

### 구현 순서

1. [ ] morld API 확장 (`add_unit_action`, `remove_unit_action`, `pop_schedule`, `get_units_at_location`)
2. [ ] 동적 액션 관리 Python 함수 (`add_dynamic_action`, `remove_dynamic_action`, `get_dynamic_actions`)
3. [ ] "interrupt" 종료 조건 타입 구현
4. [ ] `handle_npc_meet` 남녀 조합 체크 로직
5. [ ] `romance_action` 애정행각 액션 구현
6. [ ] `handle_romance_interrupt` 인터럽트 처리
7. [ ] 우선순위 스케줄 체크 로직
8. [ ] 테스트 시나리오 작성
