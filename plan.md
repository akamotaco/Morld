# Character/Object → Unit 통합 리팩토링 계획

## 현재 구조 분석

### Character와 Object의 공통점
| 항목 | Character | Object |
|------|-----------|--------|
| 클래스 | Character.cs | Character.cs (동일) |
| ID 체계 | 통합 ID | 통합 ID |
| 위치 | CurrentLocation | CurrentLocation |
| 인벤토리 | Dictionary<int, int> | Dictionary<int, int> |
| JSON 로드 | CharacterSystem | CharacterSystem |

### 차이점 (isObject 플래그로 구분)
| 항목 | Character (isObject=false) | Object (isObject=true) |
|------|---------------------------|------------------------|
| 이동 | 스케줄 기반 자동 이동 | 이동 없음 |
| 상호작용 | Interactions (talk, trade 등) | Actions (use, open 등) |
| 스케줄 | ScheduleStack 사용 | 빈 상태 유지 |

---

## 제안: Unit 통합 구조

### 1. 네이밍 변경
```
Character.cs → Unit.cs
CharacterSystem.cs → UnitSystem.cs
character_data.json → unit_data.json
CharacterJsonFormat.cs → UnitJsonFormat.cs
```

### 2. isObject 플래그 처리 방안

**방안 A: 플래그 유지**
```csharp
public class Unit
{
    public bool IsObject { get; set; } = false;
    // isObject=true면 이동/스케줄 비활성화
}
```
- 장점: 최소 변경, 기존 로직 유지
- 단점: "Object"라는 용어가 여전히 남음

**방안 B: UnitType enum 도입**
```csharp
public enum UnitType
{
    Character,  // 이동 가능, 대화 가능
    Object,     // 고정, 상호작용 가능
    // 향후 확장: NPC, Monster, Vehicle 등
}

public class Unit
{
    public UnitType Type { get; set; } = UnitType.Character;
}
```
- 장점: 확장성, 명확한 타입 구분
- 단점: 변경량 증가

**방안 C: 플래그 제거, 행동으로 구분**
```csharp
public class Unit
{
    public bool CanMove => ScheduleStack.Count > 0;
    public bool CanTalk => Interactions.Contains("talk");
}
```
- 장점: 유연함, 플래그 불필요
- 단점: 암묵적 규칙, 디버깅 어려움

---

## 3. 상호작용 통합 시스템

### 현재 상태 (분리됨)

| 대상 | 필드명 | 예시 |
|------|--------|------|
| Character | `interactions` | talk, trade |
| Object | `actions` | use, open |
| Item (바닥) | 하드코딩 | 줍기 |
| Item (인벤토리) | 하드코딩 | 사용, 조합, 버리기 |

### 통합 방안: 모든 객체에 `actions` 리스트

**핵심 아이디어:**
- Unit과 Item 모두 `actions: [...]` 필드를 가짐
- 각 액션은 **컨텍스트에 따라 활성화/비활성화**됨
- 실제 UI에서는 현재 가능한 액션만 표시

### 예시: 돌멩이 (Item)

```json
{
  "id": 4,
  "name": "돌멩이",
  "actions": ["pickup", "drop", "use", "combine", "throw"]
}
```

**컨텍스트별 활성화:**
| 컨텍스트 | 활성 액션 | 비활성 |
|----------|-----------|--------|
| 바닥에 있을 때 | pickup | drop, use, combine, throw |
| 인벤토리에 있을 때 | drop, use, combine, throw | pickup |
| 오브젝트 안에 있을 때 | take(pickup) | 나머지 |

### 예시: 나무 상자 (Unit/Object)

```json
{
  "id": 10,
  "name": "나무 상자",
  "actions": ["look", "open", "close", "examine"]
}
```

### 예시: 철수 (Unit/NPC)

```json
{
  "id": 1,
  "name": "철수",
  "actions": ["look", "talk", "trade", "give", "attack"]
}
```

**컨텍스트별 활성화:**
| 컨텍스트 | 활성 액션 |
|----------|-----------|
| 같은 위치 | look, talk, trade, give, attack |
| 다른 위치 | (없음 - 보이지 않음) |
| 적대 상태 | attack만 강조 |

---

### 액션 활성화 로직 설계

```csharp
public interface IActionContext
{
    string ContextType { get; }  // "ground", "inventory", "container", "nearby"
    int? ContainerId { get; }    // 오브젝트 ID (container 컨텍스트용)
}

public static class ActionFilter
{
    public static List<string> GetAvailableActions(
        List<string> allActions,
        IActionContext context)
    {
        return allActions.Where(action => IsActionAvailable(action, context)).ToList();
    }

    private static bool IsActionAvailable(string action, IActionContext context)
    {
        return (action, context.ContextType) switch
        {
            ("pickup", "ground") => true,
            ("pickup", "container") => true,  // take로 표시
            ("pickup", _) => false,

            ("drop", "inventory") => true,
            ("drop", _) => false,

            ("use", "inventory") => true,
            ("combine", "inventory") => true,

            ("talk", "nearby") => true,
            ("trade", "nearby") => true,

            // 기본: 활성화
            _ => true
        };
    }
}
```

---

### 액션 정의 테이블

| 액션 ID | 표시명 | 대상 | 가능 컨텍스트 |
|---------|--------|------|---------------|
| pickup | 줍기 | Item | ground, container |
| drop | 버리기 | Item | inventory |
| use | 사용 | Item | inventory |
| combine | 조합 | Item | inventory |
| throw | 던지기 | Item | inventory |
| give | 주기 | Item | inventory + nearby unit |
| look | 살펴보기 | Unit | nearby |
| talk | 대화하기 | Unit | nearby |
| trade | 거래하기 | Unit | nearby |
| attack | 공격하기 | Unit | nearby |
| open | 열기 | Unit(Object) | nearby |
| close | 닫기 | Unit(Object) | nearby |
| examine | 자세히 보기 | Unit(Object) | nearby |

---

### JSON 스키마 변경

**Item (item_data.json):**
```json
{
  "id": 4,
  "name": "돌멩이",
  "actions": ["pickup", "drop", "use", "combine", "throw"],
  "passiveTags": {},
  "equipTags": {},
  "value": 1
}
```

**Unit (unit_data.json):**
```json
{
  "id": 1,
  "name": "철수",
  "actions": ["look", "talk"],
  "scheduleStack": [...]
}
```

---

### 기존 방안 (참고용)

**방안 A: Actions로 통합** ← 채택
```json
{
    "actions": ["talk", "trade", "use", "open"]
}
```
- 모든 상호작용을 actions 하나로 관리
- 표시명은 코드에서 매핑 (talk→대화하기, use→사용하기)

**방안 B: 카테고리 분리 유지** (불채택)
```json
{
    "interactions": ["talk", "trade"],
    "actions": ["use", "open"]
}
```
- UI에서 구분 표시 가능
- 기존 구조 유지

---

## 4. 액션 실행 통합 시스템

### 핵심 메서드

```csharp
public class ActionSystem : ECS.System
{
    /// <summary>
    /// 통합 액션 실행
    /// </summary>
    /// <param name="user">액션 수행자 (플레이어 또는 NPC)</param>
    /// <param name="action">액션 ID (예: "talk", "use", "share_meal")</param>
    /// <param name="targets">대상 유닛들 (복수 가능)</param>
    /// <returns>액션 결과</returns>
    public ActionResult ApplyAction(Unit user, string action, List<Unit> targets)
    {
        return action switch
        {
            // 단일 대상 액션
            "talk" => ExecuteTalk(user, targets.FirstOrDefault()),
            "trade" => ExecuteTrade(user, targets.FirstOrDefault()),
            "attack" => ExecuteAttack(user, targets.FirstOrDefault()),
            "give" => ExecuteGive(user, targets.FirstOrDefault()),

            // 복수 대상 액션
            "share_meal" => ExecuteShareMeal(user, targets),
            "group_heal" => ExecuteGroupHeal(user, targets),

            // 대상 없는 액션 (self)
            "rest" => ExecuteRest(user),
            "meditate" => ExecuteMeditate(user),

            _ => new ActionResult { Success = false, Message = $"Unknown action: {action}" }
        };
    }
}
```

---

### 아이템 액션 처리

```csharp
/// <summary>
/// 아이템 관련 액션 실행
/// </summary>
/// <param name="user">액션 수행자</param>
/// <param name="action">액션 ID</param>
/// <param name="item">대상 아이템</param>
/// <param name="targets">추가 대상 유닛들 (give, share 등)</param>
public ActionResult ApplyItemAction(Unit user, string action, Item item, List<Unit>? targets = null)
{
    return action switch
    {
        // 기본 아이템 액션
        "pickup" => ExecutePickup(user, item),
        "drop" => ExecuteDrop(user, item),
        "use" => ExecuteUse(user, item),
        "combine" => ExecuteCombine(user, item),  // 추가 UI 필요
        "throw" => ExecuteThrow(user, item, targets?.FirstOrDefault()),

        // 대상 필요 액션
        "give" => ExecuteGiveItem(user, item, targets?.FirstOrDefault()),
        "share" => ExecuteShareItem(user, item, targets ?? new List<Unit>()),

        _ => new ActionResult { Success = false, Message = $"Unknown item action: {action}" }
    };
}
```

---

### 복수 대상 예시: 솥밥 나눠먹기

```csharp
/// <summary>
/// 솥밥 나눠먹기 - 함께 먹은 모든 유닛에게 배부름 효과
/// </summary>
private ActionResult ExecuteShareMeal(Unit user, List<Unit> targets)
{
    // 모든 참여자 (user 포함)
    var participants = new List<Unit> { user };
    participants.AddRange(targets);

    foreach (var unit in participants)
    {
        // 배부름 상태 부여
        unit.AddStatus("배부름", duration: 480);  // 8시간

        // 관계도 상승 (user와 targets 간)
        if (unit != user)
        {
            RelationSystem.ModifyRelation(user, unit, +5);
        }
    }

    return new ActionResult
    {
        Success = true,
        Message = $"{participants.Count}명이 함께 식사했다.",
        TimeConsumed = 30  // 30분 소요
    };
}
```

---

### ActionResult 구조

```csharp
public class ActionResult
{
    /// <summary>
    /// 성공 여부
    /// </summary>
    public bool Success { get; set; }

    /// <summary>
    /// 결과 메시지 (UI 표시용)
    /// </summary>
    public string Message { get; set; } = "";

    /// <summary>
    /// 소요 시간 (분, 0이면 즉시)
    /// </summary>
    public int TimeConsumed { get; set; } = 0;

    /// <summary>
    /// 추가 데이터 (액션별 커스텀)
    /// </summary>
    public Dictionary<string, object>? Data { get; set; }

    /// <summary>
    /// 후속 액션 (연쇄 이벤트)
    /// </summary>
    public string? FollowUpAction { get; set; }
}
```

---

### 액션 카테고리

| 카테고리 | 대상 | 예시 |
|----------|------|------|
| **Self** | user만 (targets 빈 리스트) | rest, meditate, sleep |
| **Single Target** | user + target 1명 | talk, trade, attack, give |
| **Multi Target** | user + targets 여러 명 | share_meal, group_heal, announce |
| **Item Single** | user + item | pickup, drop, use, examine |
| **Item + Target** | user + item + target | give_item, throw, share_item |

---

### Self 액션은 Unit의 actions에 포함

**핵심 아이디어:**
- Self 액션(rest, sleep 등)도 Unit.actions에 정의
- 플레이어가 다른 캐릭터로 전환해도 동일하게 동작
- NPC도 자체적으로 Self 액션 실행 가능 (AI 행동)

**예시: 플레이어 캐릭터 (aka)**
```json
{
  "id": 0,
  "name": "aka",
  "actions": ["rest", "sleep", "meditate", "look_around"],
  "scheduleStack": [...]
}
```

**예시: NPC (철수) - 모든 캐릭터에 공통 액션 추가**
```json
{
  "id": 1,
  "name": "철수",
  "actions": ["rest", "sleep", "talk", "trade"],
  "scheduleStack": [...]
}
```

**호출 시:**
```csharp
// Self 액션: targets가 빈 리스트
ApplyAction(user: aka, action: "rest", targets: [])

// 내부에서는 user 자신에게 효과 적용
private ActionResult ExecuteRest(Unit user, List<Unit> targets)
{
    // targets는 무시하고 user에게 효과 적용
    user.AddStatus("휴식중", duration: 60);
    return new ActionResult
    {
        Success = true,
        Message = "휴식을 취한다.",
        TimeConsumed = 60
    };
}
```

**URL 형식:**
```
action:rest       → 휴식 (target 없음)
action:sleep      → 수면 (target 없음)
action:meditate   → 명상 (target 없음)
```

---

### Self 액션 목록

| 액션 ID | 표시명 | 소요 시간 | 효과 |
|---------|--------|-----------|------|
| rest | 휴식 | 60분 | 피로 회복 |
| sleep | 수면 | 480분 | 피로 완전 회복, 체력 회복 |
| meditate | 명상 | 30분 | 정신력 회복 |
| look_around | 주변 살피기 | 5분 | 숨겨진 것 발견 가능 |
| wait | 대기 | 15분 | 시간만 경과 |
| idle | 멍때리기 | 15분 | 아무것도 안함 |

---

### NPC AI에서 Self 액션 사용

```csharp
// BehaviorSystem에서 NPC가 자체적으로 Self 액션 실행
public void ProcessNpcBehavior(Unit npc)
{
    if (npc.HasStatus("피곤함") && npc.Actions.Contains("rest"))
    {
        // NPC가 자신에게 rest 액션 실행
        _actionSystem.ApplyAction(npc, "rest", new List<Unit>());
    }
}
```

---

### GameEngine에서 호출

```csharp
// 기존: 개별 핸들러
private void HandleInteractAction(string[] parts) { ... }
private void HandleObjectAction(string[] parts) { ... }

// 통합: 단일 핸들러
private void HandleAction(string[] parts)
{
    // action:actionId:targetId1:targetId2:...
    var actionId = parts[1];
    var targetIds = parts.Skip(2).Select(int.Parse).ToList();

    var user = _playerSystem.GetPlayerCharacter();
    var targets = targetIds.Select(id => _unitSystem.GetUnit(id)).ToList();

    var result = _actionSystem.ApplyAction(user, actionId, targets);

    if (result.TimeConsumed > 0)
    {
        _worldSystem.AdvanceTime(result.TimeConsumed);
    }

    ShowActionResult(result);
}
```

---

### URL 메타 형식 변경

**기존:**
```
interact:characterId:interactionType  → interact:1:talk
action:objectId:actionType            → action:10:open
```

**통합:**
```
action:actionId:targetId1:targetId2:...

예시:
action:talk:1           → 철수에게 대화
action:open:10          → 나무 상자 열기
action:share_meal:1:2:3 → 철수, 영희, 민수와 함께 식사
action:give:2           → 영희에게 주기 (아이템은 별도 context)
```

---

### 아이템 액션 URL 형식

```
item_action:actionId:itemId:targetId1:targetId2:...

예시:
item_action:pickup:4           → 돌멩이 줍기
item_action:drop:4             → 돌멩이 버리기
item_action:use:1              → 체력 포션 사용
item_action:give:4:2           → 돌멩이를 영희에게 주기
item_action:share:5:1:2:3      → 솥밥을 철수, 영희, 민수와 나눠먹기
```

---

## 5. 수정 대상 파일 목록

### Core 파일 (이름 변경 + 폴더 이동)
- [ ] `scripts/morld/character/` → `scripts/morld/unit/` (폴더명 변경)
- [ ] `Character.cs` → `Unit.cs`
- [ ] `CharacterJsonFormat.cs` → `UnitJsonFormat.cs`
- [ ] `scripts/system/character_system.cs` → `unit_system.cs`

### JSON 데이터
- [ ] `character_data.json` → `unit_data.json`
- [ ] `interactions` → `actions` 필드 변환

### 참조 수정
- [ ] `scripts/GameEngine.cs` - 시스템 이름, URL 핸들러 통합
- [ ] `scripts/system/player_system.cs` - 타입명 변경
- [ ] `scripts/system/describe_system.cs` - 시스템 참조, UnitIds 통합
- [ ] `scripts/system/planning_system.cs` - 타입명 변경
- [ ] `scripts/system/movement_system.cs` - 타입명 변경
- [ ] `scripts/morld/player/LookResult.cs` - CharacterIds/ObjectIds → UnitIds 통합

### 문서
- [ ] `CLAUDE.md` - 용어 업데이트

---

## 6. 추가 논의 사항 (해결됨)

### Q1: CharacterIds, ObjectIds 필드명은? → **UnitIds 통합**
```csharp
// 변경 전
public List<int> CharacterIds { get; set; }
public List<int> ObjectIds { get; set; }

// 변경 후
public List<int> UnitIds { get; set; }  // IsObject로 구분
```

### Q2: 폴더 구조는? → **unit/ 폴더로 변경**
```
scripts/morld/character/ → scripts/morld/unit/
```

### Q3: Player도 Unit인가? → **Yes**
- Player는 Unit의 특수 케이스
- PlayerSystem은 별도 유지 (플레이어 전용 로직)
- Player Unit은 `id: 0`으로 고정 (또는 별도 식별자)

---

## 6-1. 구현 순서 (제안)

1. **Unit 클래스 생성** - Character.cs 복사 후 이름 변경
2. **UnitSystem 생성** - CharacterSystem 복사 후 이름 변경
3. **unit_data.json 생성** - character_data.json 복사
4. **GameEngine 수정** - 새 시스템 등록
5. **다른 시스템들 수정** - 참조 변경
6. **기존 파일 삭제** - Character 관련 파일
7. **테스트 및 검증**
8. **CLAUDE.md 업데이트**

---

## 7. 결정사항 (확정)

| 항목 | 결정 |
|------|------|
| **isObject 처리** | 방안 A - IsObject 플래그 유지 |
| **ID 체계** | UnitIds 통합 (Character/Object 구분 없이 단일 리스트) |
| **URL 메타 형식** | 바로 새 형식으로 변경 (하위 호환 X) |
| **폴더명** | `character/` → `unit/` 변경 |
| **Interactions/Actions** | actions로 통합 (interactions 필드 제거) |

---

## 8. 검토 결과 및 보완 사항

### 누락된 파일 목록 추가

**신규 생성:**
- [ ] `scripts/system/action_system.cs` - ActionSystem 클래스
- [ ] `scripts/morld/action/ActionResult.cs` - 액션 결과 클래스

**수정 필요:**
- [ ] `scripts/morld/item/Item.cs` - actions 필드 추가
- [ ] `scripts/morld/item/ItemJsonFormat.cs` - actions JSON 매핑
- [ ] `scripts/system/item_system.cs` - actions 로드/저장

### 마이그레이션 계획

**JSON 데이터 변환:**
```
기존 character_data.json:
  "interactions": ["talk", "trade"]

변환 후 unit_data.json:
  "actions": ["talk", "trade"]
```

**URL 메타 변환:**
```
기존: interact:1:talk, action:10:open
변환: action:talk:1, action:open:10
```

### 방안 C 수정 (문서 정합성)

방안 C에서 `Interactions.Contains("talk")` 사용 부분 → actions 통합 후에는:
```csharp
public bool CanTalk => Actions.Contains("talk");
```
(단, 방안 A 채택으로 실제 구현에는 영향 없음)

### give 액션 구분

| 액션 ID | 대상 | 설명 |
|---------|------|------|
| give | Unit → Unit | 아이템 없이 무언가 주기 (향후 확장) |
| give_item | Item + Unit | 아이템을 대상에게 주기 |

→ 현재는 `give_item`만 구현, `give`는 향후 확장

---

## 9. 추가 결정사항

### Q1: Unit ID와 Item ID 통합? → **Yes, 전역 ID 사용**

**결정:** 모든 엔티티(Unit, Item)가 전역 고유 ID 사용

**ID 타입 선택:**
| 옵션 | 장점 | 단점 |
|------|------|------|
| `int` (현재) | 단순, 기존 코드 호환 | 21억 제한, 음수 가능 |
| `uint` | 42억, 음수 없음 | JSON 호환성 주의 |
| `long` | 사실상 무제한 | 오버킬, 메모리 증가 |

**권장:** `int` 유지 (현재 규모에서 충분, JSON 호환성 좋음)

**ID 할당 전략:**
```
Unit: 0 ~ 9,999 (플레이어 0번 고정)
Item: 10,000 ~ 19,999
Location: 20,000 ~ (향후 확장 시)
```

또는 런타임에서 ID 생성기로 관리:
```csharp
public class IdGenerator
{
    private int _nextId = 0;
    public int Next() => _nextId++;
}
```

### Q2: Player 식별 방식? → **PlayerSystem에서 지정**

**결정:** 현재 구조 유지
- PlayerSystem이 조작할 캐릭터 ID를 보유
- `isPlayer` 플래그 불필요
- 플레이어 전환 시 PlayerSystem의 대상 ID만 변경

```csharp
public class PlayerSystem : ECS.System
{
    private int _playerUnitId = 0;  // 현재 조작 중인 Unit ID

    public void SetPlayerUnit(int unitId)
    {
        _playerUnitId = unitId;
    }

    public Unit? GetPlayerUnit()
    {
        var unitSystem = _hub.FindSystem("unitSystem") as UnitSystem;
        return unitSystem?.GetUnit(_playerUnitId);
    }
}
```

---

## 10. 추가 결정사항 (2차)

### Q1: Status 시스템 → **향후 구현으로 미룬다 (C)**
- `AddStatus()` 관련 코드는 TODO 처리
- ActionResult에서 Status 효과는 주석으로 표시만

### Q2: RelationSystem → **향후 구현으로 미룬다 (C)**
- `RelationSystem.ModifyRelation()` 코드는 TODO 처리
- 관계도 시스템은 별도 계획으로 분리

### Q3: 액션 표시명 → **string 그대로 사용**
- 별도 매핑 테이블 없음
- `action: "talk"` → UI에 "talk" 표시
- 필요시 한글 액션 ID 사용 (예: `"대화하기"`, `"거래하기"`)

---

## 11. 누락 사항 보완

### ActionFilter 클래스 위치
- `scripts/morld/action/ActionFilter.cs` 신규 생성

### item_action URL 핸들러
- GameEngine.cs에 `item_action` case 추가 필요

---

## 메모

- 전역 ID 사용 시 기존 JSON 데이터 마이그레이션 필요
- Unit/Item ID 충돌 방지를 위해 ID 범위 분리 또는 생성기 사용
- 구현 우선순위: 먼저 Character→Unit 리팩토링, 이후 전역 ID 통합
- Status/Relation 시스템은 향후 별도 계획으로 진행

