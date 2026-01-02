# 액션 셋 시스템 구현 계획

## 목표

현재 하드코딩된 행동들을 데이터 기반으로 전환하여:
1. 유닛별로 다른 행동 옵션 제공
2. 반복 타이핑 최소화 (`@` 접두어로 액션 셋 참조)
3. Unit과 Item 각각 독립적인 액션 셋 관리

---

## 현재 하드코딩된 행동 (DescribeSystem)

```csharp
// GetSituationText() 내 하드코딩
lines.Add("[color=yellow]행동:[/color]");
lines.Add("  [url=inventory]소지품 확인[/url]");
lines.Add("  [url=toggle:idle]▶ 멍때리기[/url][hidden=idle]");
lines.Add("    [url=idle:15]15분[/url]");
lines.Add("    [url=idle:30]30분[/url]");
lines.Add("    [url=idle:60]1시간[/url]");
lines.Add("    [url=idle:240]4시간[/url]");
lines.Add("  [/hidden=idle]");
```

---

## 설계

### 1. 액션 셋 정의 위치

**Unit 액션 셋:** `unit_data.json` 내부에 `actionSets` 섹션 추가
```json
{
  "actionSets": {
    "common": ["inventory"],
    "idle": {
      "type": "toggle",
      "name": "멍때리기",
      "options": [
        {"label": "15분", "action": "idle:15"},
        {"label": "30분", "action": "idle:30"},
        {"label": "1시간", "action": "idle:60"},
        {"label": "4시간", "action": "idle:240"}
      ]
    }
  },
  "units": [...]
}
```

**Item 액션 셋:** `item_data.json` 내부에 `actionSets` 섹션 추가
```json
{
  "actionSets": {
    "consumable": ["use", "drop"],
    "equipment": ["equip", "drop"]
  },
  "items": [...]
}
```

### 2. 액션 셋 참조 방식

`@` 접두어로 액션 셋 참조:
```json
{
  "id": 0,
  "name": "플레이어",
  "actions": ["@common", "@idle", "rest", "sleep"]
}
```

확장 결과:
- `@common` → `["inventory"]`
- `@idle` → 토글 형식의 멍때리기 메뉴
- `rest`, `sleep` → 개별 액션

### 3. 액션 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `simple` | 단일 액션 (기본값) | `"inventory"`, `"rest"` |
| `toggle` | 토글 메뉴 | `멍때리기` (시간 선택) |
| `list` | 단순 액션 목록 | `["use", "drop"]` |

---

## 구현 단계

### Phase 1: 데이터 구조 정의

1. **UnitActionSet 클래스 생성**
   - 파일: `scripts/morld/action/UnitActionSet.cs`
   - 액션 셋 정의 및 확장 로직

2. **ItemActionSet 클래스 생성**
   - 파일: `scripts/morld/action/ItemActionSet.cs`
   - 아이템용 액션 셋 정의

3. **JSON 포맷 정의**
   - `UnitActionSetJsonFormat.cs`
   - `ItemActionSetJsonFormat.cs`

### Phase 2: 시스템 수정

4. **UnitSystem 수정**
   - `actionSets` 섹션 파싱
   - `GetExpandedActions(unit)` 메서드 추가
   - `@` 접두어 액션을 실제 액션 목록으로 확장

5. **ItemSystem 수정**
   - `actionSets` 섹션 파싱
   - `GetExpandedActions(item)` 메서드 추가

### Phase 3: UI 연동

6. **DescribeSystem 수정**
   - `GetSituationText()` 에서 하드코딩 제거
   - `UnitSystem.GetExpandedActions()` 사용
   - 토글 타입 액션 자동 렌더링

7. **MetaActionHandler 수정**
   - 새로운 액션 타입 처리 (필요 시)

### Phase 4: 데이터 마이그레이션

8. **unit_data.json 수정**
   ```json
   {
     "actionSets": {
       "common": ["inventory"],
       "idle": {
         "type": "toggle",
         "name": "멍때리기",
         "options": [
           {"label": "15분", "action": "idle:15"},
           {"label": "30분", "action": "idle:30"},
           {"label": "1시간", "action": "idle:60"},
           {"label": "4시간", "action": "idle:240"}
         ]
       }
     },
     "units": [
       {
         "id": 0,
         "name": "플레이어",
         "actions": ["@common", "@idle"]
       }
     ]
   }
   ```

9. **item_data.json 수정** (필요 시)

---

## 파일 변경 목록

### 새로 생성
- `scripts/morld/action/UnitActionSet.cs`
- `scripts/morld/action/UnitActionSetJsonFormat.cs`
- `scripts/morld/action/ItemActionSet.cs` (Phase 2)
- `scripts/morld/action/ItemActionSetJsonFormat.cs` (Phase 2)

### 수정
- `scripts/system/unit_system.cs` - 액션 셋 파싱 및 확장
- `scripts/system/item_system.cs` - 액션 셋 파싱 및 확장 (Phase 2)
- `scripts/system/describe_system.cs` - 하드코딩 제거, 데이터 기반 렌더링
- `scripts/morld/json_data/unit_data.json` - actionSets 추가
- `scripts/morld/json_data/item_data.json` - actionSets 추가 (Phase 2)

---

## 예상 결과

**Before (하드코딩):**
```csharp
lines.Add("  [url=inventory]소지품 확인[/url]");
lines.Add("  [url=toggle:idle]▶ 멍때리기[/url][hidden=idle]");
// ...
```

**After (데이터 기반):**
```csharp
var actions = unitSystem.GetExpandedActions(player);
foreach (var action in actions)
{
    lines.Add(action.ToBBCode());
}
```

---

## 질문 사항

1. **토글 옵션의 동적 생성**: 멍때리기 시간 옵션을 고정할지, 상황에 따라 변경 가능하게 할지?

2. **액션 조건**: 특정 조건에서만 표시되는 액션 지원 필요? (예: 밤에만 "잠자기")

3. **액션 순서**: 표시 순서를 데이터에서 지정할지, 타입별 자동 정렬할지?
