# UI 텍스트 시스템 설계

## 핵심 목표

1. **Stack 구조로 text 유지** - Push/Pop으로 이전 화면 상태 복원
2. **링크 reaction** - `[url=action:...]` 클릭 시 액션 처리
3. **토글 접기/펴기** - 2중 이상 중첩 토글 지원, 내부 링크 포함 가능
4. **JSON import/export** - ScreenStack을 JSON으로 저장/복원

---

## 아키텍처

### 시스템 분리 원칙

| 시스템 | 역할 | 특징 |
|--------|------|------|
| **DescribeSystem** | 콘텐츠 생성 | 순수 텍스트 생성, RichTextLabel 참조 없음 |
| **TextUISystem** | 화면 관리 | RichTextLabel 소유, 스택 관리, 이벤트 처리 |

```
┌─────────────────────────────────────────────────────────────────┐
│                      TextUISystem (ECS System)                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      ScreenStack                         │    │
│  │  ┌─────────────────────────────────────────────────┐    │    │
│  │  │                  ScreenLayer                     │    │    │
│  │  │  ├─ Text (원본 BBCode)                           │    │    │
│  │  │  └─ ExpandedToggles (HashSet<string>)           │    │    │
│  │  └─────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼ Render()                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    ToggleRenderer                        │    │
│  │  - [hidden=X]...[/hidden=X] 처리                        │    │
│  │  - ▶/▼ 아이콘 교체                                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                RichTextLabel.Text (유일한 수정 지점)              │
└─────────────────────────────────────────────────────────────────┘
                               ▲
                               │ GetSituationText(), GetUnitLookText() 등
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    DescribeSystem (기존)                         │
│  - 순수 텍스트 생성 (BBCode 포함)                                │
│  - RichTextLabel 참조 없음                                       │
│  - 토글 마크업 생성: [hidden=X]...[/hidden=X]                    │
└─────────────────────────────────────────────────────────────────┘
```

### 의존성 방향

```
GameEngine
    │
    ├──> TextUISystem (RichTextLabel 소유)
    │         │
    │         └──> DescribeSystem (텍스트 생성 요청)
    │
    └──> MetaActionHandler
              │
              └──> TextUISystem (Push/Pop/Toggle 요청)
```

---

## 토글 마크업 문법

### 결정: 닫는 태그 ID 방식

2중 이상 중첩과 내부 링크를 지원하기 위해 닫는 태그에도 ID를 포함.

**원본 (DescribeSystem이 생성):**
```bbcode
[url=toggle:action]▶ 행동[/url][hidden=action]
  [url=toggle:idle]▶ 멍때리기[/url][hidden=idle]
    [url=idle:15]15분[/url]
    [url=idle:30]30분[/url]
  [/hidden=idle]
  [url=toggle:rest]▶ 휴식[/url][hidden=rest]
    [url=rest:bed]침대에서[/url]
  [/hidden=rest]
[/hidden=action]
```

### 렌더링 예시

**ExpandedToggles = {}** (모두 접힘)
```
▶ 행동
```

**ExpandedToggles = {action}**
```
▼ 행동
  ▶ 멍때리기
  ▶ 휴식
```

**ExpandedToggles = {action, idle}**
```
▼ 행동
  ▼ 멍때리기
    15분
    30분
  ▶ 휴식
```

---

## 데이터 구조

```csharp
/// <summary>
/// 화면 레이어 (스택의 각 요소)
/// </summary>
public class ScreenLayer
{
    /// <summary>
    /// 원본 텍스트 (DescribeSystem이 생성한 BBCode)
    /// </summary>
    public string Text { get; set; } = "";

    /// <summary>
    /// 펼쳐진 토글 ID 목록
    /// </summary>
    public HashSet<string> ExpandedToggles { get; set; } = new();
}

/// <summary>
/// 화면 스택
/// </summary>
public class ScreenStack
{
    private readonly Stack<ScreenLayer> _layers = new();
    private int _maxDepth = 10;  // 조절 가능

    public int MaxDepth
    {
        get => _maxDepth;
        set => _maxDepth = value > 0 ? value : 10;
    }

    public ScreenLayer? Current => _layers.Count > 0 ? _layers.Peek() : null;
    public int Count => _layers.Count;

    public void Push(ScreenLayer layer)
    {
        if (_layers.Count >= _maxDepth)
        {
            throw new InvalidOperationException($"ScreenStack exceeded maximum depth ({_maxDepth})");
        }
        _layers.Push(layer);
    }

    public void Pop()
    {
        if (_layers.Count == 0)
        {
            return;  // 빈 스택에서 Pop은 무시
        }
        if (_layers.Count == 1)
        {
            // 콘텐츠 버그 또는 잘못된 호출 - 경고 출력
            GD.PrintErr("[ScreenStack] Warning: Pop called on stack with only 1 layer. This indicates a content or logic bug.");
        }
        _layers.Pop();
    }

    public void Clear() { _layers.Clear(); }

    // JSON 직렬화용
    public List<ScreenLayer> ToList() { ... }
    public void FromList(List<ScreenLayer> layers) { ... }
}
```

---

## TextUISystem (ECS System)

```csharp
/// <summary>
/// UI 텍스트 시스템 (RichTextLabel.Text 수정의 단일 지점)
/// ECS System으로 등록되어 GameEngine에서 관리
/// </summary>
public class TextUISystem : ECS.System
{
    private readonly RichTextLabel _textUi;
    private readonly ScreenStack _stack = new();
    private readonly DescribeSystem _describeSystem;

    public TextUISystem(RichTextLabel textUi, DescribeSystem describeSystem)
    {
        _textUi = textUi;
        _describeSystem = describeSystem;
    }

    /// <summary>
    /// 현재 화면을 렌더링하여 RichTextLabel에 반영
    /// </summary>
    public void UpdateDisplay()
    {
        if (_stack.Current == null)
        {
            // 스택이 비어있으면 빈 화면 표시
            _textUi.Text = "";
            return;
        }
        _textUi.Text = ToggleRenderer.Render(
            _stack.Current.Text,
            _stack.Current.ExpandedToggles
        );
    }

    // === 화면 전환 API ===

    /// <summary>
    /// 상황 화면 표시 (스택 초기화 후 Push)
    /// </summary>
    public void ShowSituation(LookResult lookResult, GameTime? time)
    {
        var text = _describeSystem.GetSituationText(lookResult, time);
        Clear();
        Push(text);
    }

    /// <summary>
    /// 유닛 상세 화면 표시 (Push)
    /// </summary>
    public void ShowUnitLook(UnitLookResult unitLook)
    {
        var text = _describeSystem.GetUnitLookText(unitLook);
        Push(text);
    }

    /// <summary>
    /// 인벤토리 화면 표시 (Push)
    /// </summary>
    public void ShowInventory()
    {
        var text = _describeSystem.GetInventoryText();
        Push(text);
    }

    /// <summary>
    /// 아이템 메뉴 표시 (Push)
    /// </summary>
    public void ShowItemMenu(int itemId, int count, string context)
    {
        var text = _describeSystem.GetItemMenuText(itemId, count, context);
        Push(text);
    }

    /// <summary>
    /// 결과 메시지 표시 (Push - 뒤로 가면 이전 화면 복귀)
    /// </summary>
    public void ShowResult(string message)
    {
        var text = $"[b]{message}[/b]\n\n[url=back]뒤로[/url]";
        Push(text);
    }

    // === 스택 조작 API ===

    public void Push(string text)
    {
        _stack.Push(new ScreenLayer { Text = text });
        UpdateDisplay();
    }

    public void Pop()
    {
        _stack.Pop();
        UpdateDisplay();
    }

    public void Clear()
    {
        _stack.Clear();
    }

    public void ToggleExpand(string toggleId)
    {
        if (_stack.Current == null) return;

        var toggles = _stack.Current.ExpandedToggles;
        if (toggles.Contains(toggleId))
            toggles.Remove(toggleId);
        else
            toggles.Add(toggleId);

        UpdateDisplay();
    }

    // === JSON 저장/복원 ===

    public UIStateJsonData ExportState() { ... }
    public void ImportState(UIStateJsonData data) { ... }
}
```

---

## 토글 렌더러 (스택 기반 파싱)

```csharp
public static class ToggleRenderer
{
    public static string Render(string text, HashSet<string> expanded)
    {
        var result = new StringBuilder();
        var hiddenStack = new Stack<string>();  // 현재 숨겨진 토글 ID
        int i = 0;

        while (i < text.Length)
        {
            // [hidden=X] 시작 태그 찾기
            if (TryParseOpenTag(text, i, out var openId, out var openEnd))
            {
                if (!expanded.Contains(openId))
                {
                    hiddenStack.Push(openId);  // 숨김 시작
                }
                i = openEnd;
                continue;
            }

            // [/hidden=X] 닫는 태그 찾기
            if (TryParseCloseTag(text, i, out var closeId, out var closeEnd))
            {
                if (hiddenStack.Count > 0 && hiddenStack.Peek() == closeId)
                {
                    hiddenStack.Pop();  // 숨김 종료
                }
                i = closeEnd;
                continue;
            }

            // 현재 숨김 상태가 아니면 출력
            if (hiddenStack.Count == 0)
            {
                result.Append(text[i]);
            }
            i++;
        }

        // ▶/▼ 아이콘 교체
        return ReplaceToggleIcons(result.ToString(), expanded);
    }

    private static bool TryParseOpenTag(string text, int pos, out string id, out int endPos)
    {
        // [hidden=X] 패턴 파싱
        ...
    }

    private static bool TryParseCloseTag(string text, int pos, out string id, out int endPos)
    {
        // [/hidden=X] 패턴 파싱
        ...
    }

    private static string ReplaceToggleIcons(string text, HashSet<string> expanded)
    {
        // [url=toggle:X]▶ → [url=toggle:X]▼ (expanded 상태일 때)
        ...
    }
}
```

---

## 스택 동작 규칙

### 확정

| 이벤트 | 동작 | 이유 |
|--------|------|------|
| 위치 이동 완료 | Clear → Push | 게임 상태 변경, 이전 화면 무의미 |
| 유닛 상세보기 | Push | 뒤로 가면 기본 화면 복귀 |
| 인벤토리 열기 | Push | 뒤로 가면 기본 화면 복귀 |
| 아이템 메뉴 | Push | 뒤로 가면 인벤토리 복귀 |
| 행동 결과 표시 | Push | 뒤로 가면 이전 화면 복귀 |
| "뒤로"/"완료"/"확인" 클릭 | Pop | 이전 화면으로 복귀 (스택 1개면 경고 출력 후 Pop, 0개면 무시) |
| 토글 클릭 | ExpandedToggles 토글 | 현재 화면 내 상태 변경 |

### 게임 상태 변경 액션

시간을 소모하거나 게임 상태를 변경하는 액션 후에는 스택 Clear:
- 이동 (`move:X:Y`)
- 휴식 (`idle:N`)
- 아이템 줍기/놓기 (`take:...`, `drop:...`)
- 행동 (`action:talk:N` 등)

---

## JSON 저장/복원

### 데이터 구조

```csharp
public class ScreenLayerJsonData
{
    [JsonPropertyName("text")]
    public string Text { get; set; } = "";

    [JsonPropertyName("expandedToggles")]
    public List<string> ExpandedToggles { get; set; } = new();
}

public class UIStateJsonData
{
    [JsonPropertyName("screenStack")]
    public List<ScreenLayerJsonData> ScreenStack { get; set; } = new();
}
```

### JSON 예시

**게임 진행 중 저장:**
```json
{
  "screenStack": [
    {
      "text": "[url=toggle:action]▶ 행동[/url][hidden=action]...[/hidden=action]",
      "expandedToggles": []
    },
    {
      "text": "[b]철수[/b]\n평범한 청년이다...",
      "expandedToggles": ["inventory"]
    }
  ]
}
```

**게임 시작 시 초기 데이터 (text_ui_data.json):**
```json
{
  "screenStack": []
}
```

### 게임 로드 동작

1. **게임 시작 시**: `text_ui_data.json` 로드 (빈 스택)
2. **게임 로드 시**: 저장된 `text_ui_data.json` 로드 → 스택 복원
3. **스택이 비어있으면**: `ShowSituation()` 호출하여 현재 상황 표시

---

## 기존 시스템 통합

### MetaActionHandler 변경

```csharp
// 변경 전: 직접 _textUi.Text 수정
_textUi.Text = text;

// 변경 후: TextUISystem을 통해 수정
_textUISystem.Push(text);           // 새 화면
_textUISystem.Pop();                // 뒤로
_textUISystem.ToggleExpand(id);     // 토글
_textUISystem.ShowSituation(...);   // 상황 화면 (Clear → Push)
```

**추가할 액션 (switch문):**
```csharp
case "toggle":
    HandleToggleAction(parts);  // toggle:toggleId
    break;
case "back":      // 기존
case "confirm":   // 신규 - "확인" 버튼
case "done":      // 신규 - "완료" 버튼
    _textUISystem.Pop();
    break;
```

### DescribeSystem 변경

- RichTextLabel 참조 제거 (순수 텍스트 생성만 담당)
- `[hidden=X]...[/hidden=X]` 마크업 생성
- 토글 헤더: `[url=toggle:X]▶ 제목[/url]`
- 토글 콘텐츠: `[hidden=X]내용[/hidden=X]`

**토글 마크업 적용 위치:**
- `GetSituationText()` - "행동" 섹션 (idle, rest 등의 하위 메뉴)
- `GetUnitLookText()` - "행동" 섹션 (talk, trade 등의 하위 메뉴)
- `GetInventoryText()` - 아이템 카테고리별 토글 (선택적)

### 뒤로 버튼 단순화

```csharp
// 변경 전: context별 다른 back URL
var backUrl = context switch { ... };

// 변경 후: 단일 back
lines.Add("[url=back]뒤로[/url]");
```

### GameEngine 변경

```csharp
// 변경 전
private RichTextLabel _textUi;
private MetaActionHandler _metaActionHandler;

// 변경 후
private TextUISystem _textUISystem;
private MetaActionHandler _metaActionHandler;

public override void _Ready()
{
    // ... 기존 시스템 초기화 ...

    var textUi = GetNode<RichTextLabel>("...");
    _textUISystem = new TextUISystem(textUi, _describeSystem);
    _world.RegisterSystem("textUISystem", _textUISystem);

    _metaActionHandler = new MetaActionHandler(_world, _playerSystem, _textUISystem);
}
```

---

## 구현 순서

1. **ScreenLayer, ScreenStack 클래스**
   - 기본 Push/Pop/Clear
   - JSON 직렬화 (ToList/FromList)
   - 파일: `scripts/morld/ui/ScreenLayer.cs`, `scripts/morld/ui/ScreenStack.cs`

2. **UIStateJsonFormat**
   - ScreenLayerJsonData, UIStateJsonData 클래스
   - 파일: `scripts/morld/ui/UIStateJsonFormat.cs`

3. **ToggleRenderer**
   - 스택 기반 `[hidden=X]` 파싱
   - ▶/▼ 아이콘 교체
   - 파일: `scripts/morld/ui/ToggleRenderer.cs`

4. **text_ui_data.json**
   - 초기 빈 데이터 파일 생성
   - 파일: `scripts/morld/json_data/text_ui_data.json`

5. **TextUISystem**
   - ECS System으로 구현 (Proc은 빈 구현)
   - RichTextLabel.Text 단일 수정 지점
   - DescribeSystem 호출하여 텍스트 생성
   - JSON Import/Export
   - 파일: `scripts/system/text_ui_system.cs`

6. **MetaActionHandler 리팩토링**
   - 직접 `_textUi.Text` 수정 제거
   - TextUISystem 메서드 호출로 대체
   - `toggle:X` 액션 처리 추가: `_textUISystem.ToggleExpand(parts[1])`
   - 파일: `scripts/MetaActionHandler.cs` (수정)

7. **DescribeSystem 수정**
   - `[hidden=X]...[/hidden=X]` 마크업 생성
   - back URL 단순화
   - 파일: `scripts/system/describe_system.cs` (수정)

8. **GameEngine 수정**
   - TextUISystem 등록
   - MetaActionHandler에 TextUISystem 주입
   - 게임 시작 시 text_ui_data.json 로드 후 스택이 비어있으면 ShowSituation() 호출
   - 파일: `scripts/GameEngine.cs` (수정)

---

## 파일 위치

```
scripts/
├─ GameEngine.cs (수정 - TextUISystem 등록)
├─ MetaActionHandler.cs (수정 - TextUISystem 사용)
├─ system/
│  ├─ text_ui_system.cs (신규 - ECS System)
│  └─ describe_system.cs (수정 - 토글 마크업)
└─ morld/
   ├─ json_data/
   │  └─ text_ui_data.json (신규 - 초기 빈 데이터)
   └─ ui/
      ├─ ScreenLayer.cs (신규)
      ├─ ScreenStack.cs (신규)
      ├─ ToggleRenderer.cs (신규)
      └─ UIStateJsonFormat.cs (신규)
```

---

## 참고

- Godot RichTextLabel BBCode: https://docs.godotengine.org/en/stable/tutorials/ui/bbcode_in_richtextlabel.html
- 기존 MetaClicked 처리: `GameEngine.cs`, `MetaActionHandler.cs`
