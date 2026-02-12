# 나이 시스템 (Aging System)

## 개요

모든 캐릭터(플레이어 + NPC + 아이)의 나이를 추적하고,
게임 내 1년 경과 시 나이를 +1 증가시키는 시스템.

**설계 원칙:**
- 현재 사망(노화)은 구현하지 않음
- 나이는 UI 표시 + 이벤트 트리거 용도
- 아이 NPC의 성장(모델/행동 변화)은 향후 확장

---

## 1. 현재 상태

### 플레이어

- `props = {"나이": 22}` (player.py)
- `AGE_OPTIONS = [17, 22, 30]` (캐릭터 생성 시 선택)
- 플레이어 나이 변경 메커니즘: 없음 (고정)

### NPC

- 나이 prop 없음 (코드 주석에 "나이: 불명" 등으로만 기재)
- 설정상 나이가 있으나 시스템으로 추적되지 않음

### 시간 API

- `morld.get_time_info()` → `{"year": 1, "month": 4, "day": 1, ...}`
- 연도(year) 추적 가능

---

## 2. 나이 초기화

### NPC 나이 prop 추가

각 캐릭터 파일의 props에 `나이` 추가:

```python
# sera.py
props = {
    "나이": 18,  # 설정 기반
    ...
}

# mila.py
props = {
    "나이": 22,
    ...
}

# 기타 NPC 동일
```

### 아이 NPC

- 출산 시 `나이: 0`으로 생성 (pregnancy.py의 _spawn_child)
- 이후 연간 업데이트로 자동 증가

---

## 3. 연간 나이 증가

### 트리거

needs.py 또는 pregnancy.py의 `subscribe_time_elapsed`에서 **연도 변경 감지**:

```python
_last_year = None

def _on_time_elapsed(millis):
    global _last_year
    time_info = morld.get_time_info()
    current_year = time_info.get("year", 0)

    if _last_year is None:
        _last_year = current_year
        return

    if current_year != _last_year:
        _last_year = current_year
        _age_all_characters()
```

### 나이 증가 처리

```python
def _age_all_characters():
    """모든 등록 캐릭터 나이 +1"""
    # 플레이어
    player_id = morld.get_player_id()
    if player_id:
        current_age = morld.get_unit_prop(player_id, "나이") or 0
        morld.set_unit_prop(player_id, "나이", current_age + 1)

    # NPC (needs._npc_registry 활용)
    import needs
    for unit_id in needs._npc_registry:
        current_age = morld.get_unit_prop(unit_id, "나이")
        if current_age is not None:
            morld.set_unit_prop(unit_id, "나이", current_age + 1)
```

### 위치 결정

나이 시스템은 독립 모듈보다 **기존 모듈에 통합**하는 것이 적절:
- 별도 aging.py 생성 가능하지만, 로직이 단순하므로 needs.py에 통합 권장
- pregnancy.py에 시간 스케일이 있으므로 연동 필요 시 참조

---

## 4. UI 표시

### NPC 포커스 시

FOCUS_RULES 또는 describe에서 나이 표시:
```python
# 기존 DESCRIBE_RULES에서 나이 참조 가능
age = morld.get_unit_prop(unit_id, "나이")
# "밀라 (22세)" 등으로 표시
```

### 생일 이벤트 (향후)

- 캐릭터별 `생일:월`, `생일:일` prop 추가 가능
- 해당 날짜에 생일 이벤트 트리거

---

## 5. 챕터 전환

- 나이는 `나이` prop이므로 챕터 전환 시 자동 보존
- `_last_year` 모듈 변수는 reset()에서 초기화

```python
def reset():
    global _last_year
    _last_year = None
```

---

## 6. Prop 정리

| Prop | 타입 | 범위 | 대상 | 설명 |
|------|------|------|------|------|
| `나이` | int | 0+ | 전체 캐릭터 | 현재 나이 |

---

## 7. 구현 순서

| 단계 | 내용 | 파일 |
|------|------|------|
| 1 | NPC 캐릭터 파일에 `나이` prop 추가 | sera.py, mila.py, lina.py, yuki.py, ella.py |
| 2 | needs.py에 연도 변경 감지 + 나이 증가 로직 추가 | needs.py |
| 3 | UI 표시 (포커스 시 나이) | base.py 또는 각 캐릭터 |

---

## 8. 미구현/향후 확장

| 기능 | 설명 | 상태 |
|------|------|------|
| 노화 사망 | 특정 나이 이상 사망 | 미구현 (당분간 불멸) |
| 아이 성장 단계 | 나이별 모델/행동/스케줄 변화 | 미구현 |
| 생일 이벤트 | 생일날 특별 이벤트/대화 | 미구현 |
| NPC 외모 노화 | 나이에 따른 외모 변화 | 미구현 |
