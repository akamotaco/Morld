# 합류 시스템 (Join / Multi-Partner)

## 개요

연애 행위 중 제3자 NPC가 도착했을 때, 기존에는 **중단**(발각) 또는 **은신**(회피)만 가능했으나,
높은 호감도/욕망을 가진 NPC가 도착 시 **합류** 선택지를 제공하는 시스템.

**현재 흐름:**
```
제3자 도착 → 호감 < 60 → 은신 판정 → 성공/중단
           → 호감 ≥ 60 → (미구현, 현재 무시됨)
```

**합류 도입 후:**
```
제3자 도착 → 호감 < JOIN_THRESHOLD → 은신 판정 → 성공/중단
           → 호감 ≥ JOIN_THRESHOLD → 합류 조건 체크
                                      → 조건 충족 → 합류 선택지 UI
                                      → 조건 불충족 → 은신 판정 → 성공/중단
```

**관련 문서:**
| 문서 | 참조 내용 |
|------|----------|
| [romance-actions.md](romance-actions.md) | 스킨십/삽입 행위 정의 |
| [romance-relationship.md](romance-relationship.md) | 관계/욕망/복종 |

---

## 1. 합류 조건

### 기본 조건 (AND)

| 조건 | 상수 | 기본값 | 설명 |
|------|------|--------|------|
| 호감도 ≥ threshold | `JOIN_AFFECTION_THRESHOLD` | 60 | 기존 ROMANCE_JOIN_THRESHOLD |
| 욕망 ≥ threshold | `JOIN_DESIRE_THRESHOLD` | 30 | 욕망이 있어야 합류 의향 |
| 성욕 ≥ threshold | `JOIN_AROUSAL_THRESHOLD` | 40 | 최소 성적 흥분 |
| 반발 < threshold | `JOIN_REBELLION_MAX` | 30 | 반발이 높으면 합류 불가 |

### 캐릭터별 합류 의향 (JOIN_WILLINGNESS)

캐릭터 성격에 따라 합류에 대한 태도가 다름:

```python
# base.py Character 클래스에 추가
JOIN_WILLINGNESS = None  # None = 합류 불가 (기본)

# 캐릭터별 설정 예시:
# 밀라 - 높은 합류 의향 (저돌적)
JOIN_WILLINGNESS = {
    "affection_threshold": 50,    # 낮은 호감에서도 합류
    "desire_threshold": 20,
    "arousal_threshold": 30,
    "rebellion_max": 40,
}

# 세라 - 낮은 합류 의향 (쑥맥)
JOIN_WILLINGNESS = {
    "affection_threshold": 80,    # 매우 높은 호감 필요
    "desire_threshold": 50,
    "arousal_threshold": 60,
    "rebellion_max": 20,
}

# 유키 - 합류 불가
JOIN_WILLINGNESS = None  # 합류 자체를 거부
```

### 파트너 동의

현재 파트너(이미 세션 중인 NPC)도 합류에 동의해야 함:

```python
# base.py Character 클래스에 추가
JOIN_PARTNER_CONSENT = None  # None = 합류 동의 안 함 (기본)

# 캐릭터별 설정 예시:
# 밀라 - 동의하기 쉬움
JOIN_PARTNER_CONSENT = {
    "min_affection_to_joiner": 30,   # 합류자에 대한 최소 호감
    "min_desire": 40,                # 본인 욕망 최소
}

# 세라 - 동의하기 어려움
JOIN_PARTNER_CONSENT = {
    "min_affection_to_joiner": 60,
    "min_desire": 70,
}
```

---

## 2. 합류 판정 플로우

```
제3자(joiner) 도착
    │
    ▼
1. joiner 호감 ≥ JOIN_AFFECTION_THRESHOLD?
   ├─ No → 기존 은신/중단 로직
   └─ Yes ↓
    │
2. joiner의 JOIN_WILLINGNESS 존재?
   ├─ None → 기존 은신/중단 로직 (합류 불가 성격)
   └─ exists ↓
    │
3. joiner 개인 조건 충족? (desire, arousal, rebellion)
   ├─ No → 기존 은신/중단 로직
   └─ Yes ↓
    │
4. partner의 JOIN_PARTNER_CONSENT 존재?
   ├─ None → 기존 은신/중단 로직 (파트너 거부)
   └─ exists ↓
    │
5. partner 동의 조건 충족? (호감, 욕망)
   ├─ No → 기존 은신/중단 로직
   └─ Yes ↓
    │
6. 플레이어 선택 UI
   ├─ [합류 허용] → 합류 세션 시작
   ├─ [거절] → 기존 은신/중단 로직
   └─ [은신] → 은신 판정 (기존)
```

---

## 3. 합류 UI

### 선택 UI

합류 가능한 NPC 도착 시 세션이 일시 정지되고 선택지 표시:

```
───────────────────────────────
[밀라] ...나도... 괜찮을까요...?

  [url=@proc:join_accept]합류 허용[/url]
  [url=@proc:join_refuse]거절[/url]
  [url=@proc:join_hide]은신[/url]
───────────────────────────────
```

### 합류 제안 텍스트 (JOIN_REACTIONS)

```python
# base.py Character 클래스에 추가
JOIN_REACTIONS = {
    "propose": [
        # 조건 기반 텍스트
        ({"욕망": 50}, ["...나도 끼어도 돼요...?", "...저도..."]),
        ({"호감": 60}, ["......", "...나도... 괜찮을까요...?"]),
        ({}, ["......?"]),
    ],
    "accepted": [
        ({"욕망": 50}, ["...(기쁜 표정)", "...고마워요..."]),
        ({}, ["......", "...그럼..."]),
    ],
    "refused": [
        ({"호감": 70}, ["...그래요... 알겠어요...", "...(실망한 표정)"]),
        ({}, ["......", "...미안해요..."]),
    ],
}
```

### 파트너 동의/거부 텍스트 (JOIN_CONSENT_REACTIONS)

```python
# base.py Character 클래스에 추가
JOIN_CONSENT_REACTIONS = {
    "accept": [
        ({"욕망": 50}, ["...괜찮아...", "...좋아..."]),
        ({}, ["......", "...응..."]),
    ],
    "refuse": [
        ({}, ["...싫어.", "...둘이만 있고 싶어..."]),
    ],
}
```

---

## 4. 합류 세션 구조

### 멀티파트너 state 확장

기존 state dict에 합류자 정보 추가:

```python
def create_join_state(existing_state, joiner_id):
    """기존 세션에 합류자 추가"""
    existing_state["partners"] = [
        existing_state["partner_id"],  # 원래 파트너
        joiner_id,                     # 합류자
    ]
    existing_state["active_toggles_multi"] = {
        existing_state["partner_id"]: existing_state["active_toggles"].copy(),
        joiner_id: set(),
    }
    existing_state["stim_multi"] = {
        existing_state["partner_id"]: existing_state["stim"],
        joiner_id: stimulation.create_state(
            male_mode=(gender_mod.get_gender(joiner_id) == "male")
        ),
    }
    # 합류자 스케줄 push
    joiner_agent = get_partner_agent(joiner_id)
    if joiner_agent:
        joiner_agent.push_schedule(FOLLOW_SCHEDULE)
```

### 행위 대상 선택

합류 후 행위 UI에 대상 선택 추가:

```
───────────────────────────────
[세라] 호감: 65  욕망: 30  성욕: 72
[밀라] 호감: 80  욕망: 45  성욕: 58

대상: [url=@proc:target:0]세라[/url] [url=@proc:target:1]밀라[/url]

[행위 목록...]
───────────────────────────────
```

- 행위는 선택된 대상에게만 적용
- 토글은 대상별 독립 (세라에게 딥키스 + 밀라에게 가슴 만지기 동시 가능)
- 자극 수치도 대상별 독립 (stim_multi)

### 시간 처리

- 모든 활성 토글이 동시에 진행 (기존과 동일)
- 각 대상의 반응 텍스트가 번갈아 표시
- 스태미나 소모: 대상별 토글 합산 (멀티파트너 시 더 빠른 소진)

---

## 5. 효과 처리

### 호감/욕망 효과

합류 세션에서 행위 효과는 대상별 개별 적용:
```python
# 세라에게 딥키스 → 세라만 호감+3, 성욕+3
# 밀라에게 가슴 만지기 → 밀라만 호감+1, 성욕+4, 욕망+1
```

### 합류 보너스

합류 상태에서 일부 효과에 보너스:
```python
JOIN_EFFECT_BONUS = {
    "욕망": 1.5,   # 욕망 증가 ×1.5 (합류 상황의 자극)
    "복종": 1.5,   # 복종 증가 ×1.5 (상황 압도감)
}
```

### 절정 처리

대상별 독립 절정:
- 세라 절정 시 → 세라의 절정 반응 텍스트 + 경험치
- 밀라 절정 시 → 밀라의 절정 반응 텍스트 + 경험치
- 동시 절정 시 → 양쪽 모두 처리

---

## 6. 공수 전환 (합류 중)

### 주도권 전환

합류 세션에서의 주도권:
- Player → NPC_A: NPC_A가 주도 (NPC_B는 대기/관전)
- NPC_A → Player: 플레이어가 복귀
- NPC 주도 중 다른 NPC로 전환 불가 (플레이어 경유만 가능)

### 전환 조건

```python
# 플레이어 → NPC 주도: 해당 NPC에 INITIATIVE_CONFIG 필요
# NPC 주도 중 다른 NPC에 대한 행위 불가
# NPC → 플레이어 복귀 시 양쪽 대상 행위 가능
```

---

## 7. 세션 종료

### 종료 조건

| 조건 | 처리 |
|------|------|
| 플레이어 종료 | 전체 세션 종료, 모든 파트너 스케줄 pop |
| 체력 소진 | 전체 세션 종료 |
| 은신 실패 (추가 제3자) | 전체 세션 중단, 모든 파트너 발각 |
| 파트너 A 만족 (NPC 주도) | 파트너 A만 이탈, 나머지 계속 |

### 부분 이탈

NPC 주도 세션에서 만족한 NPC만 이탈:
```python
def handle_partner_leave(state, leaving_id):
    state["partners"].remove(leaving_id)
    del state["active_toggles_multi"][leaving_id]
    del state["stim_multi"][leaving_id]

    leaving_agent = get_partner_agent(leaving_id)
    if leaving_agent:
        leaving_agent.pop_schedule()

    # 파트너가 0명이면 전체 종료
    if not state["partners"]:
        return True  # 세션 종료
    # 1명이면 단일 세션으로 전환
    if len(state["partners"]) == 1:
        _convert_to_single(state)
    return False
```

---

## 8. 발각 처리 (합류 세션)

### 추가 제3자 도착

합류 세션 중 또 다른 NPC 도착 시:
- 합류 조건 재판정 (최대 인원 제한)
- 제한 초과 시 기존 은신/중단 로직

### 최대 인원

```python
MAX_PARTNERS = 2  # 최대 파트너 수 (플레이어 제외)
```

### 발각 시 처리

- 모든 파트너에게 발각 효과 적용
- 목격자: 파트너 수에 따라 반발 추가 증가
```python
# 복수 파트너 발각 추가 페널티
MULTI_PARTNER_DISCOVERY_PENALTY = {"반발": 3}  # 파트너 1명당 추가
```

---

## 9. 캐릭터별 설정 요약

| 캐릭터 | JOIN_WILLINGNESS | JOIN_PARTNER_CONSENT | 합류 성격 |
|--------|-----------------|---------------------|----------|
| 세라 | 높은 조건 (호감 80+) | 높은 조건 (호감 60+) | 극도로 소극적, 거의 불가 |
| 밀라 | 낮은 조건 (호감 50+) | 낮은 조건 (호감 30+) | 적극적, 쉽게 합류 |
| 리나 | 중간 (호감 70+) | 중간 (호감 50+) | 수줍지만 호기심 |
| 유키 | None (불가) | None (거부) | 합류 자체 거부 |
| 엘라 | 높은 조건 (호감 75+) | 중간 (호감 45+) | 냉정하게 판단 |

---

## 10. 상수 정리

| 상수 | 값 | 위치 | 설명 |
|------|---|------|------|
| `JOIN_AFFECTION_THRESHOLD` | 60 | romance.py | 합류 최소 호감 (기존 ROMANCE_JOIN_THRESHOLD) |
| `JOIN_DESIRE_THRESHOLD` | 30 | romance.py | 합류 최소 욕망 |
| `JOIN_AROUSAL_THRESHOLD` | 40 | romance.py | 합류 최소 성욕 |
| `JOIN_REBELLION_MAX` | 30 | romance.py | 합류 최대 반발 |
| `MAX_PARTNERS` | 2 | romance.py | 최대 파트너 수 |
| `JOIN_EFFECT_BONUS` | {욕망:1.5, 복종:1.5} | romance.py | 합류 효과 보너스 |
| `MULTI_PARTNER_DISCOVERY_PENALTY` | {반발:3} | base.py | 복수 파트너 발각 추가 |

---

## 11. 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `romance.py` | advance_time_and_check() 합류 분기, create_join_state(), render_multi_ui() |
| `npc_initiative.py` | NPC 주도 중 합류 처리 동일 로직 |
| `base.py` | JOIN_WILLINGNESS, JOIN_PARTNER_CONSENT, JOIN_REACTIONS 클래스 속성 |
| 5개 캐릭터 파일 | 캐릭터별 합류 설정 + 반응 텍스트 |
| `romance.md` | 구현 상태 업데이트 |

---

## 12. 구현 순서

| 단계 | 내용 |
|------|------|
| 1 | base.py에 합류 관련 클래스 속성 추가 |
| 2 | romance.py advance_time_and_check() 합류 판정 분기 |
| 3 | 합류 선택 UI (propose/accept/refuse) |
| 4 | create_join_state() + render_multi_ui() |
| 5 | 대상별 독립 효과/자극/절정 처리 |
| 6 | 부분 이탈 + 세션 종료 처리 |
| 7 | npc_initiative.py 합류 처리 |
| 8 | 캐릭터별 합류 설정 + 반응 텍스트 |

---

## 13. 미구현/향후 확장

| 기능 | 설명 | 상태 |
|------|------|------|
| NPC 간 합류 상호작용 | 합류 중 NPC-NPC 행위 (서로 만지기 등) | 미구현 |
| 3인 이상 합류 | MAX_PARTNERS 확장 | 미구현 (현재 2명 제한) |
| 합류 요청 (NPC 주도) | NPC가 먼저 합류 제안 (성욕 기반) | 미구현 |
| 파트너 간 질투 | 합류 후 파트너 간 호감도 변화 | 미구현 |
| 특수 합류 행위 | 멀티파트너 전용 행위 (향후) | 미구현 |
