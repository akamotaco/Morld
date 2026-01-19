# Morld UI 시스템

## TextUISystem

**역할:** RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링

### Lazy Update 패턴

```csharp
// UI 업데이트 요청 (lazy)
public void RequestUpdateDisplay()
{
    _needsUpdateDisplay = true;
}

// 대기 중인 업데이트 수행 (프레임 끝에서 호출)
public void FlushDisplay()
{
    if (!_needsUpdateDisplay) return;
    _needsUpdateDisplay = false;

    var text = RenderFocus(_stack.Current);
    _textUi.Text = ToggleRenderer.Render(text, toggles, hoveredMeta);
}
```

### Hover 이벤트 처리

- `SetHoveredMeta()`: hover 상태만 저장, `RequestUpdateDisplay()` 호출
- `FlushDisplay()`는 `_Process`에서만 호출
- 즉시 flush 시 무한 루프 발생 가능

---

## 토글 메뉴 시스템

### 마크업 형식

```python
# 토글 버튼
"[url=toggle:idle]▶멍때리기[/url]"

# 펼침 시 표시되는 내용
"[hidden=idle]"
"  [url=idle:15]15분[/url]"
"  [url=idle:30]30분[/url]"
"[/hidden=idle]"
```

### Python ui.py 예시

```python
def get_action_text():
    lines = []

    # 멍때리기 (토글 메뉴)
    lines.append("  [url=toggle:idle]▶멍때리기[/url]")
    lines.append("[hidden=idle]")
    lines.append("    [url=idle:15]15분[/url]")
    lines.append("    [url=idle:30]30분[/url]")
    lines.append("    [url=idle:60]1시간[/url]")
    lines.append("[/hidden=idle]")

    return "\n".join(lines)
```

---

## 액션 필터링 시스템

### can: prop 기반 필터링

**Whitelist 방식**: `can:액션명` prop이 있어야 해당 액션 버튼이 표시됨

```python
# Player props
props = {
    "can:talk": 1,   # NPC 대화 가능
    "can:take": 1,   # 가져오기 가능
}

# Target NPC actions
actions = ["call:talk:대화", "call:trade:거래"]

# 필터링 결과: ["call:talk:대화"]
# (can:trade가 없으므로 거래 버튼 숨김)
```

### 액션 이름 추출 규칙

| 액션 형식 | 추출되는 이름 |
|-----------|--------------|
| `call:메서드명:표시명` | 메서드명 |
| `call:메서드명:인자:표시명` | 메서드명 |
| 단순 액션 | 그대로 |

---

## 상태 기반 액션 필터링 (NPC 상태 제한)

NPC의 현재 상태(activity, mood)에 따라 가능한 액션을 동적으로 필터링

```python
# assets/base.py - Character 클래스
ACTION_AVAILABILITY: dict = {
    "수면": {
        "allowed": ["talk", "debug_props", "wake_up"],  # 허용만 표시
        "blocked_message": "자고 있다...",
    },
    "식사": {
        "blocked": ["romance", "date"],  # 이것만 숨김
    },
}
```

---

## 이동 경로 조건 필터링

Edge의 이동 조건을 검사하여 grey out 또는 숨김 처리

### 조건 키 형식

| 형식 | 조건 미충족 시 |
|------|---------------|
| `"조건명"` | grey out |
| `"조건명#"` | 숨김 |

```python
# 일반 조건 - grey out
Edge(0, 1, conditions={"열쇠:대문": 1})

# 숨김 조건 - 완전히 숨김
Edge(0, 2, conditions={"비밀통로#": 1})
```

---

## UI 표시 제어

### 헤더/푸터 표시 설정

```python
import ui

ui.set_show_header(True)   # 헤더 표시
ui.set_show_header(False)  # 헤더 숨김
ui.set_show_footer(True)   # 푸터 표시
ui.set_show_footer(False)  # 푸터 숨김
```

### 활성화/비활성화 표현

```python
# 활성화
"[url=action:param]표시명[/url]"

# 비활성화 (회색, 링크 없음)
"[color=gray]표시명[/color]"
```

---

## 파일 위치

- `scripts/system/text_ui_system.cs` - TextUISystem
- `scripts/morld/ui/FocusStack.cs` - 화면 스택
- `scripts/morld/ui/ToggleRenderer.cs` - 토글 렌더링
- `scripts/system/describe_system.cs` - 액션 필터링
- `scenarios/scenario02/python/ui.py` - Python UI 함수
