# Morld UI 시스템

## TextUISystem

**역할:** RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링

### 3분할 UI 구조

TextUI는 3개의 독립된 RichTextLabel로 구성:
- `_textUiHeader`: 위치/시간/날씨 정보
- `_textUiContent`: 본문 (묘사, 행동 옵션, 대화 등)
- `_textUiFooter`: 인벤토리 링크, 상태바

```
┌─────────────────────────────┐
│ Header (위치/시간/날씨)      │
├─────────────────────────────┤
│                             │
│ Content (본문)              │
│                             │
├─────────────────────────────┤
│ Footer (인벤토리/상태바)     │
└─────────────────────────────┘
```

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

    // Focus 타입에 따라 header/footer 결정
    // Content 렌더링 후 각 영역에 출력
    _textUiHeader.Text = headerText;
    _textUiContent.Text = contentText;
    _textUiFooter.Text = footerText;
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

### 액션 마커

액션 문자열에 마커를 붙여 `can:` 체크 동작을 변경할 수 있습니다.

| 마커 | 위치 | 형식 | 동작 | 조건 미충족 시 |
|------|------|------|------|---------------|
| 없음 | - | `call:메서드:표시명` | `can:메서드` 체크 | grey out (비활성화) |
| `#` | **문자열 끝** | `call:메서드:표시명#` | `can:메서드` 체크 | 숨김 (표시 안 함) |
| `*` | **메서드명 끝** | `call:메서드*:표시명` | `can:` 체크 안 함 | 항상 활성화 |

#### 마커 위치가 다른 이유

- **`#` (문자열 끝)**: 액션 파티셔닝 단계에서 처리. 전체 액션 문자열을 기준으로 숨김/표시 결정
- **`*` (메서드명 끝)**: can: 체크 단계에서 처리. 메서드명을 추출한 후 `*` 여부로 체크 스킵 결정

```python
# 예시
actions = [
    "call:talk:대화",                      # can:talk 필요, 없으면 grey out
    "call:debug_props:속성 보기#",         # can:debug_props 필요, 없으면 숨김
    "call:look*:살펴보기",                 # can: 체크 없이 항상 활성화
    "call:errand:심부름#",                 # can:errand 필요, 없으면 숨김
]
```

### Wildcard 매칭 (can: prop 그룹화)

`can:` prop에 `*` 와일드카드를 사용하여 여러 액션을 한 번에 제어할 수 있습니다.

```
can:debug_*  →  debug_로 시작하는 모든 액션 허용
             →  debug_props, debug_affection_up, debug_arousal_up 등
```

**동작 순서:**
1. 정확한 매칭: `can:debug_affection_up` 체크
2. 실패 시 와일드카드 매칭: `*`로 끝나는 prop 중 패턴 매칭

**와일드카드 규칙:**
- `can:prefix*` 형태의 prop은 `prefix`로 시작하는 모든 액션에 매칭
- 예: `can:debug_*` → `debug_props`, `debug_affection_up`, `debug_arousal_down` 등 모두 허용

**예시:**
```python
# 플레이어 props
"can:debug_*": 1    # debug_ 계열 모든 액션 허용

# NPC actions
actions = [
    "call:debug_props:(디버그) 속성 보기#",       # can:debug_*로 허용
    "call:debug_affection_up:(디버그) 호감도 +10#",  # can:debug_*로 허용
    "call:debug_arousal_up:(디버그) 성욕 +20#",      # can:debug_*로 허용
]
```

이를 통해 `can:debug_*` 하나로 모든 `debug_` 계열 액션을 제어할 수 있습니다.

**설정 UI와의 연동:**
```python
# settings.py
def set_debug_mode(enabled: bool):
    player_id = _get_player_id()
    value = 1 if enabled else 0
    morld.set_unit_prop(player_id, "can:debug_*", value)
```

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

Gate의 이동 조건을 검사하여 grey out 또는 숨김 처리

### 조건 키 형식

| 형식 | 조건 미충족 시 |
|------|---------------|
| `"조건명"` | grey out |
| `"조건명#"` | 숨김 |

```python
# 일반 조건 - grey out
Gate(0, 1, conditions={"열쇠:대문": 1})

# 숨김 조건 - 완전히 숨김
Gate(0, 2, conditions={"비밀통로#": 1})
```

---

## UI 표시 제어

### Focus 타입별 Header/Footer 동작

| Focus Type | Header/Footer | 설명 |
|------------|---------------|------|
| Situation  | **표시** | 기본 화면 (Python get_header/footer) |
| Unit       | **표시** | 유닛/오브젝트 살펴보기 |
| Dialog     | **레터박스** | 대화/이벤트 텍스트 |
| Inventory  | **레터박스** | 인벤토리 전체화면 |
| Item       | **레터박스** | 아이템 메뉴 |
| Result     | **레터박스** | 결과 메시지 |

### 레터박스 스타일 (Dialog)

Dialog 모드에서는 영화 레터박스처럼 Header/Footer에 구분선을 표시하여 Content에 집중:

```
┌─────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━  │  ← Header (구분선)
├─────────────────────────────┤
│                             │
│ 대화 텍스트...               │  ← Content (대화 내용만)
│                             │
├─────────────────────────────┤
│ ━━━━━━━━━━━━━━━━━━━━━━━━━  │  ← Footer (구분선)
└─────────────────────────────┘
```

- Dialog 진입 시 자동으로 레터박스 스타일 적용
- 타이핑 효과는 Content 영역에만 적용
- `[!][/!]` 태그는 Content에서만 동작 (Header/Footer에서 자동 제거)

### 헤더/푸터 Visible 제어 (선택적)

```python
import ui

# Python에서 visible 상태 제어 (선택적 사용)
ui.set_show_header(True)   # 헤더 표시
ui.set_show_header(False)  # 헤더 숨김
ui.set_show_footer(True)   # 푸터 표시
ui.set_show_footer(False)  # 푸터 숨김
```

> **참고**: 대부분의 경우 Focus 타입에 따라 자동으로 처리되므로 직접 호출할 필요 없음.
> Dialog 모드에서는 레터박스 스타일이 자동 적용됨.

### 활성화/비활성화 표현

```python
# 활성화
"[url=action:param]표시명[/url]"

# 비활성화 (회색, 링크 없음)
"[color=gray]표시명[/color]"
```

---

## 타이핑 효과

### `[!][/!]` 태그

Dialog Focus에서 타이핑 연출 제어용 태그입니다.

```
[!]즉시 출력되는 텍스트[/!]

타이핑되는 텍스트
```

**동작:**
- `[!]...[/!]` 안의 내용: 즉시 전체 표시
- 태그 밖의 내용: 타이핑 연출 적용
- `[url=...]...[/url]`: 자동으로 즉시 표시 (태그 없이도)

**사용 예:**
```python
# Conversation 클래스 내부에서 자동 처리
# 선택지 클릭 후 이전 내용은 [!][/!]로 감싸짐
f"[!]{이전_대화_히스토리}[/!]\n\n{새_응답_내용}"
```

### UI Lock

챕터 0 등에서 인벤토리/퀘스트/설정 접근을 제한:

```python
import ui

ui.set_ui_lock(True)   # Lock (레터박스 강제, 메뉴 숨김)
ui.set_ui_lock(False)  # 일반 모드
```

---

## 파일 위치

- `scripts/system/text_ui_system.cs` - TextUISystem
- `scripts/morld/ui/FocusStack.cs` - 화면 스택
- `scripts/morld/ui/ToggleRenderer.cs` - 토글 렌더링
- `scripts/system/describe_system.cs` - 액션 필터링
- `scenarios/scenario02/python/ui.py` - Python UI 함수
