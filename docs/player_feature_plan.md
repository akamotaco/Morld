# 플레이어 기능 추가 계획

## 개요

플레이어가 직접 조작할 수 있는 캐릭터 시스템을 추가합니다.
NPC와 달리 스케줄이 없으며, 플레이어 입력에 따라 행동합니다.

---

## 검토 결과 및 설계 결정

### 코드베이스 확인 사항

1. **Location 클래스 구조**
   - `Location`에는 `Edges` 필드 없음 (Region이 Edge 관리)
   - `region.GetEdges(location)` 사용

2. **TerrainJsonFormat 확장 필요**
   - `LocationJsonData`, `RegionJsonData`에 description 필드 추가 필요

### 주요 설계 결정

1. **태그 필드명**: `tags` 유지 (JSON), `GetActualTags()` 메서드로 장비 효과 합산
2. **ExitInfo → RouteInfo**: 이동 경로 정보 클래스 이름 변경
3. **조건 체크**: GetActualTags()로 통합 (아이템 PassiveTags + EquipTags 포함)
4. **Look 이동 중 처리**: Edge에서도 Look 구현 (런타임에서는 호출 안됨)
5. **Description 키 선택**: GameTime의 시간 태그 시스템 활용

---

## 1. 플레이어 캐릭터 추가

### 1.1 character_data.json 수정

```json
{
  "id": 0,
  "name": "플레이어",
  "comment": "player",
  "regionId": 0,
  "locationId": 0,
  "schedule": []
}
```

**참고:**
- `id`는 int 타입 (Location, Region과 동일한 방식)
- `comment`는 가독성을 위한 선택 필드
- `tags` 필드는 선택사항 (null 허용됨)

### 1.2 Character 클래스 확장 검토

현재 `Character` 클래스는 스케줄이 비어있어도 동작합니다.
- `Schedule.GetEntryAt()` → null 반환
- `PlanningSystem`에서 스케줄 없으면 Idle 상태 유지

**설계 원칙:**
- `IsPlayer` 속성 불필요 → PlayerSystem에서 ID로 구분
- **Inventory, EquippedItems는 Character 클래스에 추가** (NPC/플레이어 공통)
- PlayerSystem은 특정 캐릭터를 조작하기 위한 시스템
- PlayerId 변경으로 다른 캐릭터도 동일한 방식으로 조작 가능

---

## 2. PlayerSystem 확장

### 2.1 플레이어 캐릭터 추적

```csharp
public class PlayerSystem : ECS.System
{
    // 기존 시간 진행 관련 필드
    private int _remainingDuration = 0;
    private int _lastSetDuration = 0;
    private string _currentAction = "";

    // 새로 추가: 플레이어 캐릭터 ID
    public int PlayerId { get; private set; } = 0;

    // 플레이어 캐릭터 접근 헬퍼
    public Character? GetPlayerCharacter()
    {
        var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
        return characterSystem?.GetCharacter(PlayerId);
    }
}
```

### 2.2 Look 함수 구현

```csharp
/// <summary>
/// 현재 플레이어 위치의 정보 조회
/// </summary>
public class LookResult
{
    public LocationInfo Location { get; set; }           // 현재 위치 정보
    public List<int> CharacterIds { get; set; } = new(); // 같은 위치/엣지의 캐릭터 ID들
    public List<RouteInfo> Routes { get; set; } = new(); // 이동 가능한 경로들
    // public List<int> ItemIds { get; set; }            // 같은 위치의 아이템들 (향후)
}

public class LocationInfo
{
    public string RegionName { get; set; } = "";
    public string LocationName { get; set; } = "";
    public string DescriptionText { get; set; } = "";  // DescribeSystem에서 선택된 묘사 텍스트
    public LocationRef LocationRef { get; set; }
}

public class RouteInfo
{
    public string LocationName { get; set; } = "";
    public string RegionName { get; set; } = "";      // 다른 Region일 경우 표시
    public LocationRef Destination { get; set; }
    public int TravelTime { get; set; }               // 이동 소요 시간 (분)
    public bool IsRegionEdge { get; set; }            // Region 간 이동인지
    public bool IsBlocked { get; set; }               // Edge.IsBlocked 또는 조건 미충족
    public string? BlockedReason { get; set; }        // 불가 사유 (아이템 미보유 시)
}
```

**Description Dictionary 키 예시:**
- `"default"`: 기본 묘사
- `"아침"`: 아침 시간대 묘사
- `"밤"`: 밤 시간대 묘사
- `"겨울,밤"`: 복합 조건 묘사

```csharp
public LookResult Look()
{
    var player = GetPlayerCharacter();
    if (player == null)
        return new LookResult();

    // 이동 중인 경우도 처리 (런타임에서는 호출되지 않음)
    if (player.IsMoving && player.CurrentEdge != null)
    {
        return LookFromEdge(player);
    }

    return LookFromLocation(player);
}

private LookResult LookFromLocation(Character player)
{
    var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
    var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
    var describeSystem = _hub.FindSystem("describeSystem") as DescribeSystem;
    var itemSystem = _hub.FindSystem("itemSystem") as ItemSystem;
    var terrain = worldSystem?.GetTerrain();
    var gameTime = worldSystem?.GetTime();

    // 1. 현재 위치 정보
    var location = terrain?.GetLocation(player.CurrentLocation);
    var region = location != null ? terrain?.GetRegion(location.RegionId) : null;

    var locationInfo = new LocationInfo
    {
        RegionName = region?.Name ?? "",
        LocationName = location?.Name ?? "",
        DescriptionText = describeSystem?.GetLocationDescription(location, gameTime) ?? "",
        LocationRef = player.CurrentLocation
    };

    // 2. 같은 위치에 있는 캐릭터들 (플레이어 제외)
    var characterIds = new List<int>();
    foreach (var c in characterSystem?.Characters.Values ?? Enumerable.Empty<Character>())
    {
        if (c.Id == PlayerId) continue;

        // 같은 위치에 있는 캐릭터 (이동 중이 아닌)
        if (c.CurrentLocation == player.CurrentLocation && c.CurrentEdge == null)
        {
            characterIds.Add(c.Id);
        }
    }

    // 3. 이동 가능한 경로들 (조건 필터링 적용)
    var routes = BuildRoutes(player, terrain, region, location, itemSystem);

    return new LookResult
    {
        Location = locationInfo,
        CharacterIds = characterIds,
        Routes = routes
    };
}

private LookResult LookFromEdge(Character player)
{
    var worldSystem = _hub.FindSystem("worldSystem") as WorldSystem;
    var characterSystem = _hub.FindSystem("characterSystem") as CharacterSystem;
    var terrain = worldSystem?.GetTerrain();

    // Edge 정보
    var fromLocation = terrain?.GetLocation(player.CurrentEdge!.From);
    var toLocation = terrain?.GetLocation(player.CurrentEdge!.To);

    var locationInfo = new LocationInfo
    {
        RegionName = "",  // Edge에서는 Region 정보 생략
        LocationName = $"{fromLocation?.Name} → {toLocation?.Name}",
        DescriptionText = "이동 중입니다.",
        LocationRef = player.CurrentLocation
    };

    // 같은 Edge에 있는 캐릭터들
    var characterIds = new List<int>();
    foreach (var c in characterSystem?.Characters.Values ?? Enumerable.Empty<Character>())
    {
        if (c.Id == PlayerId) continue;

        if (c.CurrentEdge != null)
        {
            // 같은 Edge = From-To 쌍이 같거나 반대
            bool sameEdge = (c.CurrentEdge.From == player.CurrentEdge!.From &&
                            c.CurrentEdge.To == player.CurrentEdge!.To) ||
                           (c.CurrentEdge.From == player.CurrentEdge!.To &&
                            c.CurrentEdge.To == player.CurrentEdge!.From);
            if (sameEdge)
            {
                characterIds.Add(c.Id);
            }
        }
    }

    return new LookResult
    {
        Location = locationInfo,
        CharacterIds = characterIds,
        Routes = new List<RouteInfo>()  // Edge에서는 경로 없음
    };
}
```

**참고:** 이동 중(Edge에 있을 때)의 Look은 구현되어 있지만, 런타임에서는 플레이어가
이동 중일 때 Look을 호출하지 않으므로 실제로 사용되지 않습니다.

---

## 3. 플레이어 데이터 저장/로드

### 3.1 player_data.json 구조

```json
{
  "playerId": 0
}
```

**참고:** 플레이어 스탯, 인벤토리 등은 character_data.json에 저장됩니다.
player_data.json은 조작할 캐릭터 ID(int)만 저장합니다.

### 3.2 PlayerSystem에 Import/Export 추가

```csharp
public PlayerSystem UpdateFromFile(string filePath)
{
    // JSON 로드 → PlayerId 복원
    return this;
}

public void SaveToFile(string filePath)
{
    // PlayerId → JSON 저장
}
```

---

## 4. Location 묘사 데이터 추가

### 4.1 location_data.json 확장

**현재 JSON 구조 확인 결과:**
- `locations`는 Region 내부에 배열로 존재
- `edges`는 Region 레벨에 별도 배열로 존재 (locations 안이 아님)

```json
{
  "regions": [
    {
      "id": 0,
      "name": "마을",
      "description": {
        "default": "평화로운 작은 마을입니다.",
        "night": "어둠이 내린 조용한 마을입니다."
      },
      "locations": [
        {
          "id": 0,
          "name": "광장",
          "description": {
            "default": "마을의 중심부에 있는 넓은 광장입니다.",
            "morning": "아침 햇살이 비추는 광장입니다. 상인들이 가판대를 펼치고 있습니다.",
            "night": "텅 빈 광장에 달빛만이 비추고 있습니다."
          }
        },
        {
          "id": 1,
          "name": "상점",
          "description": {
            "default": "다양한 물건을 파는 작은 상점입니다."
          }
        }
      ],
      "edges": [...]
    }
  ]
}
```

### 4.2 Location 클래스 확장

```csharp
public class Location
{
    public int LocalId { get; }
    public int RegionId { get; }        // 참고: 현재 get-only
    public string Name { get; set; }
    public Dictionary<string, string> Description { get; set; } = new();  // 새로 추가
    // ...
}
```

### 4.3 Region 클래스 확장

```csharp
public class Region
{
    public int Id { get; }
    public string Name { get; set; }
    public Dictionary<string, string> Description { get; set; } = new();  // 새로 추가
    // ...
}
```

### 4.4 TerrainJsonFormat 수정

```csharp
public class LocationJsonData
{
    [JsonPropertyName("id")]
    public int Id { get; set; }

    [JsonPropertyName("name")]
    public string Name { get; set; } = "unknown";

    [JsonPropertyName("description")]
    public Dictionary<string, string> Description { get; set; } = new();  // 새로 추가
}

public class RegionJsonData
{
    // ... 기존 필드들 ...

    [JsonPropertyName("description")]
    public Dictionary<string, string> Description { get; set; } = new();  // 새로 추가
}
```

### 4.5 Terrain.UpdateFromJson() 수정 필요

Location 및 Region 생성 시 Description 필드 복사 로직 추가

---

## 5. 설계 결정 사항

### Q1: 플레이어 상태를 어디에 저장?
**A:** PlayerSystem 내부 + player_data.json
- Character 클래스는 NPC와 공유하므로 플레이어 전용 데이터는 분리
- PlayerSystem이 하이브리드 역할 (Logic + 일부 Data)

### Q2: Look 결과 형식?
**A:** 구조화된 클래스 반환
- UI 레이어에서 자유롭게 포맷팅 가능
- 테스트 용이성
- 향후 확장 용이 (아이템, 이벤트 등)

### Q3: 플레이어 이동 처리?
**A:** 플레이어 ActionQueue 직접 조작
- 플레이어 입력 대기 시 SE.World는 Step 실행 안함 (시간 정지)
- Godot UI에서 입력 → PlayerSystem으로 명령 전달
- PlayerSystem이 연결된 캐릭터의 ActionQueue를 직접 조작
- **유저 조작 우선**: 기존 ActionQueue(스케줄 기반)가 있어도 모두 삭제하고 새 ActionQueue 입력
- NPC: PlanningSystem이 스케줄 기반으로 ActionQueue 자동 생성
- 조작 대상 캐릭터: PlayerId 변경으로 다른 캐릭터도 동일하게 조작 가능

### Q4: 이동 조건(열쇠 등)은 어디서 처리?
**A:** GetActualTags()로 통합 처리
- 모든 조건은 `GetActualTags(itemSystem).GetTagValue(tag) >= requiredValue`로 확인
- 아이템 소유 효과(PassiveTags)가 자동으로 GetActualTags()에 포함됨
- 조건 미충족 시 Look 목록에 `IsBlocked=true`로 표시 (BlockedReason 포함)

### Q5: Description을 Dictionary로 사용하는 이유?
**A:** 다양한 상황별 출력 대응
- 시간대(아침/낮/밤), 날씨(비/눈), 방문 횟수 등에 따라 다른 묘사
- UI에서 적절한 키를 선택하여 출력
- 키가 없으면 "default" 사용
- 확장성: 새로운 상황 추가 시 JSON만 수정

### Q6: 조건 값의 의미?
**A:** 모든 조건은 GetActualTags()로 통합 확인
- 아이템 소유 효과(PassiveTags)와 장착 효과(EquipTags)가 GetActualTags()에 합산됨
- 조건 체크: `GetActualTags().GetTagValue(tag) >= requiredValue`
- 아이템/스탯 구분 없이 단일 로직으로 처리

### Q7: 아이템 소모는 어떻게?
**A:** 별도 이벤트로 처리
- 이동 시 아이템 소모하면 길찾기가 복잡해짐
- 필요 시: 아이템 삭제 + Edge 조건 삭제로 처리
- 예: "열쇠로 문 열기" → Inventory에서 열쇠 삭제, Edge 조건 삭제

### Q8: GetActualTags()를 왜 메서드로?
**A:** 코드 명확성 + 성능 부담 없음
- 턴제 게임이므로 매번 계산해도 괜찮음
- 프로퍼티보다 메서드가 "계산된다"는 의미 전달에 적합
- JSON 저장 대상이 아님을 명확히 표현

### Q9: Description 키 선택은?
**A:** GameTime의 시간 태그 시스템 활용
- `GetCurrentTags()`로 시간대/계절/기념일 태그 반환
- Description 키는 쉼표로 구분된 태그 조합 (예: "크리스마스,겨울,저녁")
- 가장 많은 태그가 매칭되는 키 선택, 없으면 "default"

### Q10: Look은 이동 중에도 가능?
**A:** 코드는 구현, 런타임에서는 미사용
- `LookFromEdge()` 메서드로 Edge에서의 Look 구현
- 런타임에서는 플레이어가 이동 중일 때 Look 호출 안함
- 향후 확장 또는 테스트용으로 유지

### Q11: 묘사 텍스트 생성은 어디서?
**A:** DescribeSystem으로 분리
- 묘사 생성 로직을 별도 시스템으로 분리
- PlayerSystem은 DescribeSystem을 통해 문자열을 받음
- 향후 LLM 연동 등 확장 가능

### Q12: RequestMove(destination)는 언제 구현?
**A:** 향후 구현 (UI 연동 후)
- Look 기능 완성 후 UI 설계와 함께 구현
- 이동 명령은 PlayerSystem이 ActionQueue를 직접 조작하는 방식
- PathFinder로 경로 탐색 → ActionQueue에 이동 Action 추가 → 시간 진행

---

## 6. DescribeSystem (묘사 시스템)

### 6.1 역할

묘사 텍스트 생성을 담당하는 Logic System입니다.
향후 LLM 연동, 캐싱, 다국어 지원 등을 고려하여 별도 시스템으로 분리합니다.

**시스템 등록 순서:**
```
[Data Systems - 초기화 시 데이터 로드]
WorldSystem → CharacterSystem → ItemSystem

[Logic Systems - Step에서 실행]
MovementSystem → PlanningSystem → PlayerSystem → DescribeSystem
```

**참고:** ItemSystem은 CharacterSystem처럼 데이터 시스템으로, `UpdateFromFile()`로 item_data.json을 로드합니다.

### 6.2 IDescribable 인터페이스

```csharp
/// <summary>
/// 묘사 가능한 객체를 위한 인터페이스
/// </summary>
public interface IDescribable
{
    Dictionary<string, string> Description { get; set; }
}
```

**구현 클래스:**
- `Location` - 장소 묘사
- `Region` - 지역 묘사

### 6.3 DescribeSystem 구조

```csharp
public class DescribeSystem : ECS.System
{
    /// <summary>
    /// Location 묘사 반환
    /// </summary>
    public string GetLocationDescription(Location location, GameTime time)
    {
        if (location == null) return "";
        return SelectDescription(location.Description, time);
    }

    /// <summary>
    /// Region 묘사 반환
    /// </summary>
    public string GetRegionDescription(Region region, GameTime time)
    {
        if (region == null) return "";
        return SelectDescription(region.Description, time);
    }

    /// <summary>
    /// Character 묘사 반환 (향후 확장)
    /// </summary>
    public string GetCharacterDescription(Character character, GameTime time)
    {
        // 기본: 이름 + 활동
        // 향후: LLM으로 풍성한 묘사 생성
        return character?.Name ?? "";
    }

    /// <summary>
    /// Description Dictionary에서 적절한 키 선택
    /// </summary>
    private string SelectDescription(Dictionary<string, string> descriptions, GameTime time)
    {
        if (descriptions == null || descriptions.Count == 0)
            return "";

        var currentTags = time.GetCurrentTags();

        string bestKey = "default";
        int bestMatchCount = 0;

        foreach (var (key, _) in descriptions)
        {
            if (key == "default") continue;

            var keyTags = key.Split(',').Select(t => t.Trim()).ToHashSet();
            var matchCount = keyTags.Intersect(currentTags).Count();

            // 모든 키 태그가 현재 태그에 포함되어야 함
            if (matchCount == keyTags.Count && matchCount > bestMatchCount)
            {
                bestMatchCount = matchCount;
                bestKey = key;
            }
        }

        return descriptions.TryGetValue(bestKey, out var desc) ? desc : "";
    }

    /// <summary>
    /// Proc은 비어있음 (호출 기반 시스템)
    /// </summary>
    protected override void Proc(int step, Span<ECS.Component[]> allComponents)
    {
        // 호출 기반이므로 Proc에서 할 일 없음
    }
}
```

### 6.4 PlayerSystem에서 사용

섹션 2.2의 `LookFromLocation()` 참조:
- `describeSystem = _hub.FindSystem("describeSystem") as DescribeSystem`
- `DescriptionText = describeSystem?.GetLocationDescription(location, gameTime) ?? ""`

### 6.5 향후 확장

```csharp
// LLM 연동 예시 (향후)
public class DescribeSystem : ECS.System
{
    private IDescriptionGenerator _generator;

    public DescribeSystem(IDescriptionGenerator generator = null)
    {
        _generator = generator ?? new DefaultDescriptionGenerator();
    }

    public string GetLocationDescription(Location location, GameTime time)
    {
        return _generator.Generate(location, time);
    }
}

public interface IDescriptionGenerator
{
    string Generate(IDescribable target, GameTime time);
}

public class DefaultDescriptionGenerator : IDescriptionGenerator { ... }
public class LLMDescriptionGenerator : IDescriptionGenerator { ... }
```

---

## 7. Tag 시스템 확장

### 7.1 아이템-태그 통합 설계

모든 조건 체크는 `GetActualTags()`로 통합됩니다:

```
Character
├─ Tags (기본 스탯)
├─ Inventory: Dictionary<int, int> (아이템ID → 개수)
├─ EquippedItems: List<int> (장착된 아이템 ID)
└─ GetActualTags()
     ├─ 기본 Tags 복사
     ├─ + Inventory에 있는 아이템의 PassiveTags (소유 효과)
     └─ + EquippedItems에 있는 아이템의 EquipTags (장착 효과)
```

**설계 이점:**
- 조건 체크 로직이 단순해짐 (GetActualTags()만 확인)
- 아이템/스탯 구분 없이 동일한 방식으로 처리
- PathFinder에서도 동일한 로직 사용 가능

### 7.2 Item 클래스

```csharp
public class Item
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string? Comment { get; set; }  // 가독성을 위한 선택 필드

    /// <summary>
    /// 소유만으로 효과가 있는 태그 (예: 열쇠)
    /// </summary>
    public Dictionary<string, int> PassiveTags { get; set; } = new();

    /// <summary>
    /// 장착해야 효과가 있는 태그 (예: 망원경 +관찰)
    /// </summary>
    public Dictionary<string, int> EquipTags { get; set; } = new();
}
```

**아이템 유형 예시:**
| 아이템 | PassiveTags | EquipTags | 설명 |
|--------|-------------|-----------|------|
| 열쇠 | `{"열쇠": 1}` | - | 소유만으로 문 통과 |
| 망원경 | - | `{"관찰": 2}` | 장착해야 관찰력 증가 |
| 마법 반지 | `{"마법저항": 1}` | `{"마력": 3}` | 소유+장착 효과 분리 |

### 7.3 조건 체크 로직

```csharp
public class Character
{
    /// <summary>
    /// 주어진 조건들을 모두 충족하는지 확인
    /// </summary>
    public bool CanPass(Dictionary<string, int> conditions, ItemSystem itemSystem)
    {
        if (conditions == null || conditions.Count == 0)
            return true;

        var actualTags = GetActualTags(itemSystem);

        foreach (var (tag, requiredValue) in conditions)
        {
            if (actualTags.GetTagValue(tag) < requiredValue)
                return false;
        }

        return true;
    }
}
```

**사용 예시:**
```csharp
var conditions = edge.GetConditions(location);
if (character.CanPass(conditions, itemSystem))
{
    // 통과 가능
}
```

### 7.4 JSON 예시

```json
{
  "edges": [
    {
      "a": 0, "b": 1,
      "conditionsAtoB": {
        "열쇠": 1,      // 열쇠 아이템의 PassiveTags로 충족
        "관찰": 4       // 기본 스탯 + 장비 EquipTags로 충족
      }
    }
  ]
}
```

### 7.5 GetActualTags() (아이템 효과 반영)

```csharp
public class Character
{
    // JSON 저장 대상
    public TraversalContext Tags { get; } = new();                    // 기본 스탯
    public Dictionary<int, int> Inventory { get; set; } = new();      // 아이템ID → 개수
    public List<int> EquippedItems { get; set; } = new();             // 장착 아이템 ID

    /// <summary>
    /// 아이템 효과가 반영된 최종 태그 계산 (매 호출 시 계산)
    /// </summary>
    public TraversalContext GetActualTags(ItemSystem itemSystem)
    {
        var result = new TraversalContext();

        // 1. 기본 태그 복사
        foreach (var (tag, value) in Tags.Tags)
        {
            result.SetTag(tag, value);
        }

        // 2. 인벤토리 아이템의 PassiveTags 합산 (소유 효과)
        foreach (var (itemId, count) in Inventory)
        {
            if (count <= 0) continue;
            var item = itemSystem?.GetItem(itemId);
            if (item == null) continue;

            foreach (var (tag, bonus) in item.PassiveTags)
            {
                var current = result.GetTagValue(tag);
                result.SetTag(tag, current + bonus);
            }
        }

        // 3. 장착 아이템의 EquipTags 합산 (장착 효과)
        foreach (var itemId in EquippedItems)
        {
            var item = itemSystem?.GetItem(itemId);
            if (item == null) continue;

            foreach (var (tag, bonus) in item.EquipTags)
            {
                var current = result.GetTagValue(tag);
                result.SetTag(tag, current + bonus);
            }
        }

        return result;
    }
}
```

**핵심 포인트:**
- `Tags`는 JSON 저장, `GetActualTags()`는 호출 시 계산
- PassiveTags: 인벤토리에 있으면 자동 적용
- EquipTags: 장착해야 적용
- 턴제 게임이므로 매번 계산해도 성능 부담 없음
- **NPC도 동일한 방식 적용** - 모든 캐릭터가 Inventory/EquippedItems를 가질 수 있음

### 7.6 character_data.json 확장

```json
{
  "id": 0,
  "name": "플레이어",
  "comment": "player",
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
  "schedule": []
}
```

### 7.7 item_data.json

```json
[
  {
    "id": 0,
    "name": "녹슨 열쇠",
    "comment": "rusty_key",
    "passiveTags": {
      "열쇠": 1
    },
    "equipTags": {}
  },
  {
    "id": 1,
    "name": "체력 포션",
    "comment": "health_potion",
    "passiveTags": {},
    "equipTags": {}
  },
  {
    "id": 2,
    "name": "망원경",
    "comment": "telescope",
    "passiveTags": {},
    "equipTags": {
      "관찰": 2
    }
  },
  {
    "id": 3,
    "name": "가죽 장갑",
    "comment": "leather_gloves",
    "passiveTags": {},
    "equipTags": {
      "방어": 1
    }
  }
]
```

**참고:**
- `id`는 int 타입 (Location, Region, Character와 동일한 방식)
- `comment`는 가독성을 위한 선택 필드
- Inventory 키: JSON에서는 문자열(`"0"`)이지만, System.Text.Json이 `Dictionary<int, int>`로 자동 변환

**결과:**
- 열쇠(id:0) 소유 → GetActualTags()에 `열쇠: 1` 포함 → Edge 조건 `열쇠: 1` 통과
- 기본 관찰 3 + 망원경(id:2) 장착(+2) = GetActualTags()의 관찰 5

---

## 8. Look 기능 상세

### 8.1 Look의 목적

RichTextLabel을 사용하여 다음 정보를 텍스트로 출력:

1. **환경 묘사** - 현재 위치의 상황별 설명
2. **상호작용 가능한 캐릭터** - 행동 선택으로 연결 (보기/말하기/거래 등)
3. **상호작용 가능한 아이템** - 행동 선택으로 연결 (보기/집기 등) [향후]
4. **이동 가능한 경로** - 조건에 따라 필터링

### 8.2 Description 키 선택 (GameTime 시간 태그)

GameTime에서 현재 시간에 해당하는 태그들을 반환합니다:

```csharp
public class GameTime
{
    /// <summary>
    /// 현재 시간에 해당하는 모든 태그 반환
    /// </summary>
    public HashSet<string> GetCurrentTags()
    {
        var tags = new HashSet<string>();

        // 시간대
        if (Hour >= 6 && Hour < 12) tags.Add("아침");
        else if (Hour >= 12 && Hour < 18) tags.Add("낮");
        else if (Hour >= 18 && Hour < 21) tags.Add("저녁");
        else tags.Add("밤");

        // 계절 (월 기반)
        if (Month >= 3 && Month <= 5) tags.Add("봄");
        else if (Month >= 6 && Month <= 8) tags.Add("여름");
        else if (Month >= 9 && Month <= 11) tags.Add("가을");
        else tags.Add("겨울");

        // 현재 활성화된 기념일들
        foreach (var holiday in GetActiveHolidays())
        {
            tags.Add(holiday.Name);  // "크리스마스", "신년" 등
        }

        return tags;
    }
}
```

Description 키 형식은 쉼표로 구분된 태그 조합입니다:

```json
{
  "description": {
    "default": "마을 광장입니다.",
    "아침": "아침 햇살이 비추는 광장입니다.",
    "크리스마스,겨울,저녁": "크리스마스 트리 위로 소복히 쌓인 눈이 보인다. 불이 반짝반짝 빛을 발하고 있다.",
    "겨울,밤": "차가운 겨울 밤, 광장이 고요합니다."
  }
}
```

**키 선택 로직:** `DescribeSystem.SelectDescription()` 참조 (섹션 6.3)

### 8.3 경로 필터링 로직

```csharp
private List<RouteInfo> BuildRoutes(Character player, Terrain terrain, Region region, Location location, ItemSystem itemSystem)
{
    var routes = new List<RouteInfo>();
    if (region == null || location == null) return routes;

    var actualTags = player.GetActualTags(itemSystem);

    // Region 내부 Edge
    var edges = region.GetEdges(location);
    foreach (var edge in edges)
    {
        // Edge.IsBlocked 체크 - 완전 차단된 경로는 제외
        if (edge.IsBlocked) continue;

        var conditions = edge.GetConditions(location);
        bool canPass = true;
        string? blockedReason = null;

        foreach (var (tag, requiredValue) in conditions)
        {
            if (actualTags.GetTagValue(tag) < requiredValue)
            {
                canPass = false;
                blockedReason = $"{tag}이(가) 필요합니다";
                break;
            }
        }

        var neighbor = edge.GetOtherLocation(location);
        routes.Add(new RouteInfo
        {
            LocationName = neighbor.Name,
            RegionName = region.Name,
            Destination = new LocationRef(neighbor.RegionId, neighbor.LocalId),
            TravelTime = edge.GetTravelTime(location),
            IsRegionEdge = false,
            IsBlocked = !canPass,
            BlockedReason = blockedReason
        });
    }

    // Region 간 Edge (RegionEdge)
    foreach (var regionEdge in terrain.GetRegionEdgesFrom(player.CurrentLocation))
    {
        if (regionEdge.IsBlocked) continue;

        var conditions = regionEdge.GetConditions(player.CurrentLocation);
        bool canPass = true;
        string? blockedReason = null;

        foreach (var (tag, requiredValue) in conditions)
        {
            if (actualTags.GetTagValue(tag) < requiredValue)
            {
                canPass = false;
                blockedReason = $"{tag}이(가) 필요합니다";
                break;
            }
        }

        var destination = regionEdge.GetOtherLocation(player.CurrentLocation);
        var destLocation = terrain.GetLocation(destination);
        var destRegion = terrain.GetRegion(destination.RegionId);

        routes.Add(new RouteInfo
        {
            LocationName = destLocation?.Name ?? "",
            RegionName = destRegion?.Name ?? "",
            Destination = destination,
            TravelTime = regionEdge.GetTravelTime(player.CurrentLocation),
            IsRegionEdge = true,
            IsBlocked = !canPass,
            BlockedReason = blockedReason
        });
    }

    return routes;
}
```

### 8.4 조건 처리 요약

| 조건 | Look에서 | 이동 명령에서 |
|-----|---------|-------------|
| **Edge.IsBlocked** | 목록에서 제외 | - |
| **조건 미충족** | 목록 표시 + `IsBlocked=true` | BlockedReason 메시지 출력 |
| **조건 충족** | 목록 표시 + `IsBlocked=false` | 정상 이동 |

**참고:** GetActualTags()에 아이템 PassiveTags가 포함되므로, 열쇠를 소유하면 자동으로 조건을 충족합니다.

---

## 9. 테스트 시나리오

### 9.1 기본 Look 테스트
- 게임 시작 → Look() 호출
- 현재 위치 묘사 확인
- 주변 캐릭터 목록 확인

### 9.2 시간 경과 후 Look
- 4시간 진행 → Look() 호출
- NPC 위치 변화 확인 (스케줄에 따라 이동)

### 9.3 조건부 출구 테스트
- 조건 미충족 출구가 `IsBlocked=true`로 표시되는지 확인
- 아이템 소유(PassiveTags) 후 `IsBlocked=false`로 변경되는지 확인
- 장비 착용(EquipTags) 후 `IsBlocked=false`로 변경되는지 확인

### 9.4 장비 효과 테스트
- 기본 관찰 3 상태에서 관찰 4 필요한 출구 → `IsBlocked=true`
- 망원경(+2) 착용 → GetActualTags() 관찰 5 → `IsBlocked=false`
- 망원경 해제 → 다시 `IsBlocked=true`

### 9.5 저장/로드 테스트
- 게임 진행 → SaveToFile()
- 게임 재시작 → UpdateFromFile()
- Tags, EquippedItems 복원 확인
- GetActualTags() 재계산 확인

---

## 10. 구현 순서

### Phase 0: ID 타입 통일 (선행 필수)
1. [ ] CharacterJsonFormat.cs의 Id를 string → int로 변경, Comment 필드 추가
2. [ ] Character.cs의 _id 필드를 string → int로 변경
3. [ ] CharacterSystem의 Dictionary 키를 string → int로 변경
4. [ ] character_data.json의 id를 int로 변경 (선택: comment 필드 추가)

### Phase 1: 아이템 시스템 (선행 필수)
1. [ ] Item 클래스 생성 (Id: int, Name, Comment, PassiveTags, EquipTags)
2. [ ] ItemJsonFormat 클래스 생성
3. [ ] ItemSystem 생성 (아이템 조회, JSON Import/Export)
4. [ ] item_data.json 생성 및 테스트 데이터 추가

### Phase 2: 기본 구조
5. [ ] IDescribable 인터페이스 생성
6. [ ] Location 클래스에 Description 필드 추가 (IDescribable 구현)
7. [ ] Region 클래스에 Description 필드 추가 (IDescribable 구현)
8. [ ] TerrainJsonFormat에 description 필드 추가
9. [ ] Terrain.UpdateFromJson()에서 Description 파싱 로직 추가
10. [ ] Terrain.GetRegionEdgesFrom(LocationRef) 메서드 추가
11. [ ] RegionEdge에 GetConditions(), GetOtherLocation(), GetTravelTime() 메서드 추가
12. [ ] GameTime에 GetCurrentTags() 메서드 추가
13. [ ] DescribeSystem 생성
14. [ ] location_data.json에 묘사 데이터 추가

### Phase 3: 캐릭터 확장
15. [ ] Character 클래스에 Inventory (Dict<int,int>), EquippedItems (List<int>) 추가
16. [ ] GetActualTags(ItemSystem) 메서드 구현
17. [ ] Character.CanPass(conditions) 메서드 구현
18. [ ] CharacterJsonFormat에 inventory, equippedItems 필드 추가
19. [ ] character_data.json에 플레이어 캐릭터 및 인벤토리 추가

### Phase 4: PathFinder 수정
20. [ ] PathFinder.FindPath() 시그니처 변경
    - `TraversalContext` → `Character` + `ItemSystem` 전달
    - 내부에서 `character.CanPass(edge.GetConditions(location), itemSystem)` 호출
21. [ ] PlanningSystem에서 PathFinder 호출부 수정
22. [ ] MovementSystem에서 PathFinder 호출부 수정 (있다면)

### Phase 5: PlayerSystem 및 Look
23. [ ] PlayerSystem에 PlayerId 필드 및 GetPlayerCharacter() 추가
24. [ ] LookResult, RouteInfo, LocationInfo 클래스 정의
25. [ ] PlayerSystem.Look() 기본 구현 (Location/Edge 분리)
26. [ ] BuildRoutes()에서 GetActualTags() 기반 필터링 로직 구현

### Phase 6: 저장/로드
27. [ ] player_data.json 포맷 정의
28. [ ] PlayerSystem.UpdateFromFile() 구현
29. [ ] PlayerSystem.SaveToFile() 구현

### Phase 7: 확장 (향후)
30. [ ] 장비 슬롯 시스템 (신체 부위별 제한)
31. [ ] Look에 바닥 아이템 정보 추가
32. [ ] 아이템 획득/사용/버리기 로직

---

## 11. 파일 변경 목록

### Phase 0: ID 타입 통일
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/character/Character.cs` | _id 타입 string → int 변경 |
| `scripts/morld/character/CharacterJsonFormat.cs` | Id 타입 string → int 변경, Comment 필드 추가 |
| `scripts/system/character_system.cs` | Dictionary<string, Character> → Dictionary<int, Character> 변경 |
| `scripts/morld/json_data/character_data.json` | id를 int로 변경, comment 필드 추가 |

### Phase 1: 아이템 시스템
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/item/Item.cs` | 새 파일 - Item 클래스 (Id: int, Name, Comment, PassiveTags, EquipTags) |
| `scripts/morld/item/ItemJsonFormat.cs` | 새 파일 - JSON 직렬화용 클래스 |
| `scripts/system/item_system.cs` | 새 파일 - 아이템 관리 시스템 |
| `scripts/morld/json_data/item_data.json` | 새 파일 - 아이템 정의 데이터 |

### Phase 2: 기본 구조
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/IDescribable.cs` | 새 파일 - IDescribable 인터페이스 |
| `scripts/morld/terrain/Location.cs` | Description 필드 추가, IDescribable 구현 |
| `scripts/morld/terrain/Region.cs` | Description 필드 추가, IDescribable 구현 |
| `scripts/morld/terrain/TerrainJsonFormat.cs` | Description 추가 |
| `scripts/morld/terrain/Terrain.cs` | Description 파싱 로직, GetRegionEdgesFrom() 추가 |
| `scripts/morld/terrain/RegionEdge.cs` | GetConditions(), GetOtherLocation(), GetTravelTime() 추가 |
| `scripts/morld/schedule/GameTime.cs` | GetCurrentTags() 메서드 추가 |
| `scripts/system/describe_system.cs` | 새 파일 - 묘사 텍스트 생성 시스템 |
| `scripts/morld/json_data/location_data.json` | 묘사 데이터 추가 |

### Phase 3: 캐릭터 확장
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/character/Character.cs` | Inventory (Dict<int,int>), EquippedItems (List<int>), GetActualTags(ItemSystem), CanPass() 추가 |
| `scripts/morld/character/CharacterJsonFormat.cs` | inventory, equippedItems 필드 추가 |
| `scripts/morld/json_data/character_data.json` | 플레이어 캐릭터 추가, inventory 추가 |

### Phase 4: PathFinder 수정
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/pathfinding/PathFinder.cs` | FindPath() 시그니처 변경 (Character + ItemSystem) |
| `scripts/system/planning_system.cs` | PathFinder 호출부 수정 |

### Phase 5: PlayerSystem 및 Look
| 파일 | 변경 내용 |
|------|----------|
| `scripts/system/player_system.cs` | PlayerId, GetPlayerCharacter(), Look(), BuildRoutes() 추가 |
| `scripts/morld/player/LookResult.cs` | 새 파일 - LookResult, LocationInfo, RouteInfo 클래스 |

### Phase 6: 저장/로드
| 파일 | 변경 내용 |
|------|----------|
| `scripts/morld/player/PlayerData.cs` | 새 파일 - 저장 데이터 클래스 |
| `scripts/morld/json_data/player_data.json` | 새 파일 - 플레이어 저장 데이터 |

