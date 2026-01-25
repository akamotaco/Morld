# 입력 시스템 (Input System)

## 개요

현재 Morld는 **마우스 클릭** 기반으로 동작합니다. 시나리오03의 실시간 미션 파트와 시나리오02의 편의성 향상을 위해 **키보드 입력**을 추가할 계획입니다.

---

## 현재 상태

### 마우스 입력 (구현됨)

- URL 클릭으로 모든 액션 수행
- `[url=@action]텍스트[/url]` 형식

### 키보드 입력 (미구현)

- Godot 키 등록 필요
- 향후 구현 예정

---

## 키보드 입력 계획

### 시나리오02 - 다이얼로그 단축키

자주 사용하는 다이얼로그 명령을 키보드로 입력:

| 키 | 동작 | 대응 URL |
|----|------|----------|
| `Enter` / `Space` | 다음 / 확인 | `@next`, `@finish` |
| `Escape` | 취소 / 닫기 | `@cancel`, `@ret:cancel` |
| `Backspace` | 이전 | `@prev` |
| `1` ~ `9` | 선택지 선택 | 순서대로 선택 |

#### 예시 화면

```
무엇을 할까?

1. [url=@proc:talk]대화하기[/url]
2. [url=@proc:trade]거래하기[/url]
3. [url=@proc:leave]떠나기[/url]
```

→ 숫자 키 `1`, `2`, `3`으로 선택 가능

### 시나리오03 - 실시간 미션 조작

미션 파트에서 실시간 명령:

| 키 | 동작 | 설명 |
|----|------|------|
| `Space` | 일시정지/재개 | 시간 흐름 토글 |
| `1` ~ `4` | 분대원 선택 | 개별 요원 지시 |
| `A` | 전체 선택 | 분대 전체 지시 |
| `W/A/S/D` | 이동 지시 | 방향 이동 (미정) |
| `E` | 상호작용 | 문 열기, 아이템 줍기 등 |
| `Q` | 엄폐 | 엄폐물 사용 |
| `R` | 재장전 | 무기 재장전 |
| `Tab` | 전술 화면 | 전체 맵 보기 |
| `Escape` | 메뉴 | 미션 메뉴 (철수 등) |

---

## 구현 방향

### Godot 키 등록

```
Project Settings > Input Map
- ui_accept: Enter, Space
- ui_cancel: Escape
- ui_prev: Backspace
- select_1 ~ select_9: 숫자키
- pause_toggle: Space (미션용)
- etc.
```

### TextUI 연동

키 입력을 URL 액션으로 변환:

```csharp
// 예시 (구현 예정)
public override void _Input(InputEvent @event)
{
    if (@event.IsActionPressed("ui_accept"))
    {
        // 현재 Focus에서 @next 또는 @finish 실행
        HandleDefaultAccept();
    }
    else if (@event.IsActionPressed("select_1"))
    {
        // 첫 번째 선택지 클릭
        HandleNumberSelect(1);
    }
}
```

### 선택지 번호 자동 부여

다이얼로그 렌더링 시 선택지에 번호 표시:

```
현재:
[url=@proc:talk]대화하기[/url]

키보드 지원 후:
1. [url=@proc:talk]대화하기[/url]
```

---

## 호환성

### 마우스와 키보드 병용

- 키보드 입력은 **추가** 옵션
- 기존 마우스 클릭 동작 유지
- 두 입력 방식 모두 지원

### 시나리오별 차이

| 시나리오 | 키보드 사용 |
|----------|-----------|
| 시나리오02 | 선택적 (편의 기능) |
| 시나리오03 | 필수 (실시간 조작) |

---

## 우선순위

### Phase 1 (공용)

- `Enter`/`Space` → 다음/확인
- `Escape` → 취소/닫기
- 숫자키 → 선택지 선택

### Phase 2 (시나리오03)

- `Space` → 일시정지 토글
- 분대원 선택 키
- 기본 전술 명령 키

### Phase 3 (확장)

- 커스텀 키 바인딩
- 게임패드 지원 (선택적)

---

## 미정 사항

- [ ] Godot Input Map 설정
- [ ] 키 바인딩 UI (설정 화면)
- [ ] 실시간 조작 키 최종 확정
- [ ] 선택지 번호 자동 표시 방식
- [ ] 키보드 포커스 관리
