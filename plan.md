# Plan: Dialog 통합 API 구현

## 목표
`morld.dialog()` 단일 API로 모든 다이얼로그 기능 통합:
1. 단일/다중 페이지 지원
2. autofill 타입별 자동 버튼 생성
3. proc 콜백으로 동적 상호작용
4. result 파라미터로 상태 반환

---

## 최종 결정 사항

### 1. 단일 함수
- **`morld.dialog()`** - 모든 다이얼로그 통합
- `morld.dialogEx()` 제거 (dialog로 통합)

### 2. autofill 타입
| 타입 | 동작 | 용도 |
|------|------|------|
| `next` | [다음] 버튼만 (기본값) | 순차 모놀로그 |
| `book` | [이전][다음] 왕복 가능 | 일기, 문서 열람 |
| `scroll` | 텍스트 누적 + [다음] | 회상, 긴 독백 |
| `off` | 자동 버튼 없음 | 커스텀 UI |

### 3. URL 패턴 변경
| 패턴 | 동작 |
|------|------|
| `@finish` | 다이얼로그 종료, result 파라미터 값 반환 |
| `@proc:값` | proc(값) 호출, 반환값에 따라 동작 결정 |

**proc 콜백 반환값:**
| 반환값 | 동작 |
|--------|------|
| `문자열` | 해당 문자열로 텍스트 업데이트, 다이얼로그 유지 |
| `True` | 다이얼로그 즉시 종료, result 반환 |
| `None`/`False` | 변경 없음, 다이얼로그 유지 |

**proc('init') 자동 호출:**
- Dialog가 처음 표시될 때 `proc('init')` 자동 호출
- 문자열 반환 시 초기 텍스트로 사용
- `None` 반환 시 원래 텍스트 사용
- 다이얼로그 복귀 시 상태 기반 텍스트 갱신에 활용

### 4. 기존 패턴 호환성
| 패턴 | 동작 | 비고 |
|------|------|------|
| `@ret:값` | 다이얼로그 종료, 해당 값 반환 | 레거시 호환 |

---

## API 설계

### morld.dialog() - 통합 API
```python
result = yield morld.dialog(
    text_or_pages,      # str 또는 list - 필수
    autofill="next",    # "next", "book", "scroll", "off"
    proc=None,          # @proc:값 클릭 시 호출될 콜백
    result=None         # @finish 시 반환할 값 (dict/객체)
)
```

### 사용 예시

```python
# 1. 기본 멀티페이지 (autofill="next" 기본값)
yield morld.dialog([
    "페이지1",
    "페이지2",
    "페이지3"
])
# 자동 생성: [다음] → [다음] → [종료]

# 2. 책 열람 (앞뒤 이동)
yield morld.dialog([
    "1장: 시작",
    "2장: 전개",
    "3장: 결말"
], autofill="book")
# 자동 생성: [이전][다음] 네비게이션

# 3. 누적 텍스트
yield morld.dialog([
    "첫 번째 생각...",
    "두 번째 생각...",
    "세 번째 생각..."
], autofill="scroll")
# 텍스트가 누적되며 표시

# 4. 커스텀 UI (proc + result)
state = {"str": 5, "agi": 5, "points": 10}

def handle_action(action):
    if action == "str+" and state["points"] > 0:
        state["str"] += 1
        state["points"] -= 1
    elif action == "str-" and state["str"] > 1:
        state["str"] -= 1
        state["points"] += 1
    # ...
    return build_text()  # 새 텍스트 반환 (None이면 변경 없음)

result = yield morld.dialog(
    build_text(),
    autofill="off",
    proc=handle_action,
    result=state
)
# @finish 클릭 시 result = state

# 5. 선택 후 즉시 종료 (@proc + return True)
def handle_choice(action):
    state["choice"] = action
    return True  # 다이얼로그 즉시 종료

result = yield morld.dialog(
    "어디로 갈까?\n\n"
    "[url=@proc:town]마을[/url]\n"
    "[url=@proc:forest]숲[/url]\n"
    "[url=@proc:cave]동굴[/url]",
    autofill="off",
    proc=handle_choice,
    result=state
)
# @proc:town 클릭 → proc("town") 호출 → True 반환 → result = state 반환

# 6. 단순 확인 (레거시 호환)
result = yield morld.dialog(
    "저장하시겠습니까?\n\n"
    "[url=@ret:yes]예[/url]  [url=@ret:no]아니오[/url]",
    autofill="off"
)
# result = "yes" 또는 "no" (@ret: 패턴은 해당 값 직접 반환)
```

---

## autofill 버튼 자동 생성

### next (기본값)
```
페이지 1~N-1: 텍스트 + "\n\n[url=@next]다음[/url]"
페이지 N:    텍스트 + "\n\n[url=@finish]종료[/url]"
```

### book
```
페이지 1:    텍스트 + "\n\n[url=@next]다음[/url]"
페이지 2~N-1: 텍스트 + "\n\n[url=@prev]이전[/url]  [url=@next]다음[/url]"
페이지 N:    텍스트 + "\n\n[url=@prev]이전[/url]  [url=@finish]종료[/url]"
```

### scroll
```
페이지 1:    텍스트1 + "\n\n[url=@next]다음[/url]"
페이지 2:    텍스트1 + "\n\n" + 텍스트2 + "\n\n[url=@next]다음[/url]"
...
페이지 N:    텍스트1~N 누적 + "\n\n[url=@finish]종료[/url]"
```

### off
- 자동 버튼 없음
- Python에서 직접 BBCode 링크 작성

---

## 내부 URL 패턴 (C# 처리)

| 패턴 | 동작 | 비고 |
|------|------|------|
| `@next` | 다음 페이지로 이동 | autofill 전용 |
| `@prev` | 이전 페이지로 이동 | book 전용 |
| `@finish` | 다이얼로그 종료, result 반환 | |
| `@proc:값` | proc(값) 호출, 반환값에 따라 동작 | True→종료, 문자열→업데이트 |
| `@ret:값` | 다이얼로그 종료, 해당 값 반환 | 레거시 호환 |

---

## 구현 계획

### Phase 1: 기존 dialogEx 제거 및 통합 ✅
1. `PyDialogRequest`에 `Autofill`, `ResultObject` 속성 추가
2. `morld.dialog()` API 수정 (autofill, proc, result 파라미터)
3. `morld.dialogEx()` 제거

### Phase 2: 새 URL 패턴 처리 ✅
1. `MetaActionHandler`에 `@finish`, `@next`, `@prev` 처리 추가
2. `@ret:` 레거시 호환 유지
3. `@proc:` 콜백에서 `True` 반환 시 다이얼로그 종료 처리

### Phase 3: autofill 버튼 자동 생성 ✅
1. `PyDialogRequest.GetDisplayText()` 메서드 추가
2. autofill 타입별 버튼 텍스트 생성 로직

### Phase 4: 테스트 및 마이그레이션 ✅
1. scenario02 예제 새 API로 변환
2. 각 autofill 타입 테스트

### Phase 5: proc('init') 및 캐릭터 생성 ✅
1. `MetaActionHandler`에서 Dialog 초기 표시 시 `proc('init')` 자동 호출
2. `player_creation.py` 새 Dialog API로 리팩토링
3. 캐릭터 생성 플로우: 이름 → 나이 → 체격 → 장비 → 확인
4. `yield from run_character_creation()` 패턴으로 서브 제너레이터 위임
