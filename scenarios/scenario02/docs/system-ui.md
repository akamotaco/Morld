# Morld UI 시스템

## TextUISystem

**역할:** RichTextLabel.Text 관리, 스택 기반 화면 전환, 토글 렌더링

### 3분할 UI 구조

TextUI는 3개의 독립된 RichTextLabel로 구성:
- `_textUiHeader`: 위치/시간/날씨 정보
- `_textUiContent`: 본문 (묘사, 행동 옵션, 대화 등)
- `_textUiFooter`: 인벤토리 링크, 상태바, 스탠스/자세 토글, X축 이동 화살표

```
┌─────────────────────────────┐
│ Header (위치/시간/날씨)      │
├─────────────────────────────┤
│                             │
│ Content (본문)              │
│                             │
├─────────────────────────────┤
│ Footer (인벤토리/상태/이동)  │
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
"[url=toggle:spend_time]▶시간 보내기[/url]"

# 펼침 시 표시되는 내용
"[hidden=spend_time]"
"  [url=wait:300000]누군가를 기다리기 (~5분)[/url]"
"  [url=idle:1800000]멍때리기 (30분)[/url]"
"  [url=idle:14400000]낮잠자기 (4시간)[/url]"
"[/hidden=spend_time]"
```

### Python ui.py 예시

```python
def get_action_text():
    lines = []

    # 시간 보내기 (토글 메뉴)
    lines.append("  [url=toggle:spend_time]▶시간 보내기[/url]")
    lines.append("[hidden=spend_time]")
    lines.append(f"    [url=wait:{5 * MILLIS_PER_MINUTE}]누군가를 기다리기 (~5분)[/url]")
    lines.append(f"    [url=idle:{30 * MILLIS_PER_MINUTE}]멍때리기 (30분)[/url]")
    if 6 <= hour < 18:
        lines.append(f"    [url=idle:{240 * MILLIS_PER_MINUTE}]낮잠자기 (4시간)[/url]")
    else:
        lines.append("    [color=gray]낮잠자기 (4시간)[/color]")
    lines.append("[/hidden=spend_time]")

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
    "call:debug_props:(디버그) 속성 보기#",            # can:debug_*로 허용
    "call:debug_affection_up:(디버그) 호감도 +10#",    # can:debug_*로 허용
    "call:debug_arousal_up:(디버그) 성욕 +20#",        # can:debug_*로 허용
    "call:debug_work_order:(디버그) 작업지시#",        # can:debug_*로 허용
]
```

> **동적 라벨**: `debug_work_order`는 `_apply_dynamic_action_labels()`로 포커스 메뉴에서
> `"(디버그) 작업지시 [벌목]"` 처럼 현재 NPC 활동이 동적으로 표시됩니다.

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
| Unit       | **표시** | 유닛/오브젝트 살펴보기 (이름 + X좌표 표시) |
| Dialog     | **레터박스** | 대화/이벤트 텍스트 |
| Animation  | **모드별** | normal: 표시, lock: 레터박스, block: 표시 |
| Inventory  | **레터박스** | 인벤토리 전체화면 |
| Item       | **레터박스** | 아이템 메뉴 |
| Result     | **레터박스** | 결과 메시지 |

### 포커스 유효성 자동 검사 (PopIfInvalid)

`FlushDisplay()` 호출 시 `PopIfInvalid()`로 현재 포커스의 유효성을 자동 검사:

- **Unit 포커스**: `LookUnit()`이 null 반환 (대상이 다른 위치로 이동) → 자동 Pop
- **Item 포커스**: 해당 아이템을 더 이상 소유하지 않음 → 자동 Pop

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

---

## 즉시 출력 헬퍼

`ui.py`에서 제공하는 유틸리티 함수들입니다.

### `divider(color, length)`

구분선을 즉시 출력합니다. `[!]` 태그로 감싸져 타이핑 없이 표시됩니다.

```python
import ui

ui.divider()                    # 기본: 회색 20칸
ui.divider("white", 30)        # 흰색 30칸
```

### `loading_screen(callback, text)`

로딩 화면을 표시한 뒤 무거운 작업을 실행합니다. Animlog lock 모드 + callback 패턴을 사용합니다.

```python
import ui

def _do_load():
    load_chapter("chapter_1")
    morld.set_prop("chapter", 1)

yield ui.loading_screen(_do_load)           # 기본 텍스트: "로딩 중..."
yield ui.loading_screen(_do_load, "준비 중...")  # 커스텀 텍스트
```

**동작 원리:**
1. lock 모드로 header/footer 가림 (레터박스)
2. `speed=9999`로 로딩 텍스트 즉시 표시
3. `wait(0.1)`으로 최소 수 프레임 렌더링 보장
4. callback 실행 (동기, 화면은 로딩 텍스트 유지)

---

## Animlog (애니메이션 시퀀스)

실시간 기반 애니메이션 시퀀스 시스템입니다. 텍스트 타이핑, 대기, 화면 전환 등을 시간 기반으로 연출합니다.

### 기본 사용법

```python
import ui

anim = ui.Animlog()

# 텍스트 표시 (타이핑 효과)
anim.text("첫 번째 줄")
anim.text("두 번째 줄")  # 이전 텍스트에 누적

# 대기
anim.wait(1.0)  # 1초 대기

# 화면 교체 (append=False)
anim.text("새로운 장면", append=False)

# 실행
yield anim.play(mode="lock")
```

### text() 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `content` | str | 필수 | 표시할 텍스트 |
| `delay` | float | None | 글자당 초 (설정 시 speed 무시) |
| `speed` | float | 50.0 | 초당 글자 수 |
| `append` | bool | True | True: 이전 텍스트에 누적, False: 화면 교체 |

### UI 모드 (mode 파라미터)

| 모드 | Header/Footer | 입력 | 용도 |
|------|---------------|------|------|
| `"normal"` | 정상 표시 | 허용 | 일반 연출 |
| `"lock"` | 레터박스 (구분선) | 스킵만 | **집중 필요한 연출** (회고록, 컷씬) |
| `"block"` | 정상 표시 | 스킵만 | **전투** (HP 등 정보 필요) |

```python
# 회고록 (집중 필요 → lock)
yield anim.play(mode="lock")

# 전투 (정보 필요 → block)
yield anim.play(mode="block")
```

### 전체 예시: 챕터 전환 연출

```python
import ui

anim = ui.Animlog()

# 페이지 1: 회고록 시작
anim.text("[color=gray]『 누군가의 회고록 』[/color]", append=False)
anim.wait(1.0)
anim.text("")  # 빈 줄
anim.text("그날의 기억은 아직도 선명하다.")
anim.text("폐허가 된 저택, 차가운 바람...")
anim.text("그리고 그녀의 눈빛.")
anim.wait(1.5)

# 페이지 2: 화면 교체
anim.text("[color=gray]『 1년 전 』[/color]", append=False)
anim.wait(0.5)
anim.text("")
anim.text("모든 것이 시작된 그 날,")
anim.text("나는 아무것도 몰랐다.", delay=0.1)  # 천천히
anim.wait(2.0)

# lock 모드로 실행
yield anim.play(mode="lock")

# 이후 Dialog로 이어서...
yield ui.dialog(["눈을 떠보니...", "..."])
```

### 스킵 동작

- **클릭**: 즉시 모든 애니메이션 스킵 → 최종 텍스트 표시 → 종료
- 스킵 시 모든 `wait()`, `text()` 타이핑이 즉시 완료됨

### 콜백 (callback)

애니메이션 중간에 Python 함수를 호출할 수 있습니다:

```python
def apply_damage(target, damage):
    # 데미지 적용 로직
    pass

anim = ui.Animlog()
anim.text("공격!")
anim.wait(0.3)
anim.callback(apply_damage, target=enemy, damage=10)
anim.text("[color=red]-10[/color]")
anim.wait(0.5)
yield anim.play(mode="block")
```

### Dialog와의 차이점

| 특성 | Dialog | Animlog |
|------|--------|---------|
| 진행 방식 | 클릭으로 다음 페이지 | 시간 기반 자동 진행 |
| 타이밍 제어 | 페이지 단위 | `wait()`, `speed`, `delay` |
| 스킵 | 타이핑 스킵 → 다음 페이지 | 전체 스킵 → 종료 |
| 용도 | 대화, 선택지 | 연출, 컷씬, 전투 |

### FocusType.Animation

Animlog는 Dialog와 별도의 Focus 타입으로 관리됩니다:

| Focus Type | Header/Footer |
|------------|---------------|
| Dialog | 레터박스 (항상) |
| Animation | **모드에 따라 다름** |

### 파일 위치

- `scenarios/scenario02/python/ui.py` - `Animlog` 클래스
- `scripts/morld/ui/Animlog.cs` - `PyAnimlogRequest`, `AnimlogStep`
- `scripts/system/text_ui_system.cs` - 렌더링, 업데이트 로직

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

### ScrollFollowing 제어

RichTextLabel의 `ScrollFollowing`은 **타이핑 중에만** 활성화됩니다.

| 시점 | ScrollFollowing | 이유 |
|------|----------------|------|
| `StartTyping()` | `true` | 타이핑 텍스트가 자동 스크롤 |
| `FinishTyping()` | `false` | hover 등으로 인한 스크롤 점프 방지 |
| 타이핑 즉시 완료 (speed=0) | `false` | 즉시 꺼짐 |

hover 이벤트가 `Text` 재할당을 유발하는데, `ScrollFollowing = true` 상태에서 이를 방지합니다.

### UI Lock

챕터 0 등에서 인벤토리/퀘스트/설정 접근을 제한:

```python
import ui

ui.set_ui_lock(True)   # Lock (레터박스 강제, 메뉴 숨김)
ui.set_ui_lock(False)  # 일반 모드
```

---

---

## Tab 뷰 전환 시스템 (계획)

> **상태: 설계 완료, 미구현**
>
> Focus 내에서 Tab 키로 콘텐츠를 전환하는 기능.
> 윈도우 탭과 유사 — Focus 스택 변경 없이 같은 Focus 내에서 출력만 전환.

### 설계 원칙

- **C# = 메커니즘**: 탭 상태 저장, 입력 처리, Python 호출
- **Python = 콘텐츠**: 탭 개수, 탭별 렌더링, 탭 라벨 전부 Python이 결정
- **하위 호환**: Python이 `get_max_tab() → 0` 반환 시 탭 비활성화 (기존 동작 유지)

### C# 변경

#### Focus.cs — 상태 추가

```csharp
public class Focus {
    ...
    public int ViewTab { get; set; } = 0;   // 현재 탭 인덱스
}
```

#### text_ui_system.cs — 입력 + 렌더링

```csharp
void OnTabPressed() {
    var current = _stack.Current;
    if (current == null) return;

    int maxTab = GetMaxTabFromPython(current.Type, current.TargetUnitId);
    if (maxTab <= 0) return;  // 탭 1개 → 전환 불필요

    current.ViewTab = (current.ViewTab + 1) % (maxTab + 1);
    RequestUpdateDisplay();
}

private string RenderFocusContent(Focus focus) {
    // tab > 0이면 Python에 탭 콘텐츠 질의
    if (focus.ViewTab > 0) {
        var tabContent = GetTabContentFromPython(focus.Type, focus.ViewTab, focus.TargetUnitId);
        if (tabContent != null) return tabContent;
    }
    // tab == 0 또는 Python이 None → 기존 렌더링
    return focus.Type switch {
        FocusType.Situation => RenderSituation(),
        FocusType.Unit      => RenderUnit(focus.TargetUnitId ?? 0),
        ...
    };
}
```

### Python API (ui.py)

```python
def get_max_tab(focus_type, target_unit_id=None):
    """해당 Focus에서 사용 가능한 최대 탭 인덱스 (0 = 탭 없음)"""
    if focus_type == "Situation":
        import party
        return 1 if party.has_any_squad() else 0
    elif focus_type == "Unit":
        import party
        return 1 if party.is_in_squad(target_unit_id) else 0
    return 0

def get_tab_content(focus_type, tab, target_unit_id=None):
    """탭별 콘텐츠 (None → 기존 렌더링 사용)"""
    if focus_type == "Situation" and tab == 1:
        return _render_squad_overview()
    elif focus_type == "Unit" and tab == 1:
        return _render_member_detail(target_unit_id)
    return None

def get_tab_labels(focus_type, target_unit_id=None):
    """Header에 표시할 탭 라벨 리스트"""
    if focus_type == "Situation":
        labels = ["상황"]
        import party
        if party.has_any_squad():
            labels.append("분대")
        return labels
    elif focus_type == "Unit":
        labels = ["정보"]
        import party
        if party.is_in_squad(target_unit_id):
            labels.append("분대원")
        return labels
    return []
```

### 화면 예시

```
Situation Tab 0 (기본):           Situation Tab 1 (분대):
┌──────────────────────┐         ┌──────────────────────┐
│ [▶상황] [분대]        │         │ [상황] [▶분대]        │
├──────────────────────┤         ├──────────────────────┤
│ 저택 거실.            │         │ ■ 1분대 (세라 지휘)   │
│ 벽난로에 불이 타고...  │         │   세라 — 경계 (85%) │
│                      │         │   밀라 — 수집 (92%) │
│ ▶이동               │         │   리나 — 휴식        │
│ ▶살펴보기            │         │                      │
├──────────────────────┤         ├──────────────────────┤
│ [Tab] 인벤토리 설정   │         │ [Tab] 인벤토리 설정   │
└──────────────────────┘         └──────────────────────┘
```

### 탭 지원 Focus 타입 (예상)

| Focus | Tab 0 (기본) | Tab 1+ (확장) | 활성화 조건 |
|-------|-------------|--------------|------------|
| Situation | 상황 화면 | 분대 현황 | 분대 존재 시 |
| Unit | NPC 정보 | 분대원 상태 | 분대 멤버 시 |
| Inventory | 내 인벤토리 | (향후 확장) | - |
| Dialog | 대화 | 탭 없음 | - |
| Animation | 연출 | 탭 없음 | - |

### 구현 순서

파티 시스템 Phase 4 (플레이어 UI)에 포함:
1. `Focus.cs`에 `ViewTab` 추가
2. `text_ui_system.cs`에 Tab 입력 + 렌더 디스패치
3. Python `ui.py`에 `get_max_tab` / `get_tab_content` / `get_tab_labels`
4. 분대 현황 탭 콘텐츠 구현 (`party_ui.py`)

---

## 파일 위치

- `scripts/system/text_ui_system.cs` - TextUISystem
- `scripts/morld/ui/FocusStack.cs` - 화면 스택
- `scripts/morld/ui/Focus.cs` - Focus 타입 정의
- `scripts/morld/ui/Animlog.cs` - Animlog 데이터 (PyAnimlogRequest, AnimlogStep)
- `scripts/morld/ui/Dialog.cs` - Dialog 데이터 (PyDialogRequest)
- `scripts/morld/ui/ToggleRenderer.cs` - 토글 렌더링
- `scripts/system/describe_system.cs` - 액션 필터링
- `scenarios/scenario02/python/ui.py` - Python UI 함수 (Animlog, dialog 등)
