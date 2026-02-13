# 애정 행위 시스템 (Romance Actions)

## 개요

플레이어/NPC 간 친밀한 신체 접촉 행위를 처리하는 시스템.
스킨십, 데이트, NPC 주도, 감각/자극, 탈의/노출, 은신/발각, 소음 등을 포함.

**시스템 구성**:
| 시스템 | 파일 | 설명 |
|--------|------|------|
| **스킨십 시스템** | `romance.py` | 플레이어 주도 친밀 행위 (토글/즉시) |
| **데이트 시스템** | `date.py` | 데이트 요청/종료 + 애정 표현 |
| **NPC 주도 시스템** | `npc_initiative.py` | NPC가 먼저 스킨십 시작 |
| **자극 시스템** | `stimulation.py` | 부위별 자극 → 절정/여운/불응기 |

---

## 1. 스킨십 시스템 (romance.py)

### 핵심 특징
- 행위 중 시간이 흐르고, 다른 NPC 도착 시 중단/합류 이벤트 발생
- 플레이어가 행위를 선택하고 NPC가 반응
- 토글형(유지)/즉시형(순간) 행위 구분
- 캐릭터별 반응 시스템 (ROMANCE_REACTIONS)

### 진입 조건
- 호감도 50 이상 (`ROMANCE_ENTRY_THRESHOLD`)
- 같은 Location에 있어야 함
- 호감도 낮은 제3자가 없어야 함

### 플로우
```
┌─────────────────────────────────────────────────────────────────┐
│ 연애 행위 진행 중                                                 │
│                                                                 │
│  [행위 선택] → [시간 경과] → [NPC 도착 체크] → [결과 처리]         │
│                    ↓              ↓                             │
│               게임 시간 진행   JobBehaviorSystem이                │
│               (예: 15분)      NPC를 이동시킴                      │
│                                   ↓                             │
│                          같은 Location 도착?                      │
│                           ↓           ↓                         │
│                         Yes          No                         │
│                          ↓            ↓                         │
│                    호감도 체크      행위 계속                      │
│                     ↓      ↓                                    │
│                   60+    60-                                    │
│                    ↓      ↓                                     │
│                  합류   중단 이벤트                                │
└─────────────────────────────────────────────────────────────────┘
```

### 행위 정의

#### 즉시형 행위 (INSTANT_ACTIONS)
| ID | 이름 | 시간 | 스태미나 | 효과 | 호감도 | 비고 |
|----|------|-----|---------|------|--------|------|
| head_pat | 머리 쓰다듬기 | 3분 | 1 | 호감+3 | 40 | |
| cheek_caress | 뺨 어루만지기 | 2분 | 1 | 호감+2 | 30 | |
| cheek_pinch | 뺨 꼬집기 | 2분 | 1 | 호감+1 | 35 | |
| ear_touch | 귀 만지기 | 3분 | 1 | 호감+2, 성욕+1 | 45 | |
| whisper | 사랑의 속삭임 | 2분 | 1 | 호감+5 | 50 | |
| lip_lick | 입술 핥기 | 3분 | 1 | 호감+2, 성욕+2 | 55 | **신규** |
| french_kiss | 프렌치 키스 | 5분 | 2 | 호감+3, 성욕+3 | 60 | |
| neck_kiss | 목 키스 | 3분 | 2 | 호감+2, 성욕+3 | 65 | **신규** |
| butt_caress | 엉덩이 쓰다듬기 | 3분 | 2 | 호감+1, 성욕+3, 욕망+1 | 70 | |
| breast_caress | 가슴 쓰다듬기 | 3분 | 2 | 호감+1, 성욕+3 | 75 | **신규** |
| nipple_stimulation | 유두 자극 | 5분 | 2 | 성욕+5, 욕망+2 | 85 | **신규**, requires_exposure: upper |
| genital_caress | 음부 쓰다듬기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+2 | 85 | requires_exposure: lower |
| clit_stimulation | 클리토리스 자극 | 5분 | 3 | 성욕+6, 욕망+3 | 90 | requires_exposure: lower |
| anal_stimulation | 항문 자극 | 5분 | 2 | 성욕+5, 욕망+3 | 90 | **신규**, requires_exposure: lower |
| penis_caress | 음경 쓰다듬기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+2 | 85 | requires_exposure: lower |
| penis_stimulation | 음경 자극 | 5분 | 3 | 성욕+6, 욕망+3 | 90 | requires_exposure: lower |
| hold_back | 참기 | 1분 | 2 | — | 0 | P stim ≥ 80일 때만 표시 |

#### 토글형 행위 (TOGGLE_ACTIONS)
| ID | 이름 | 틱당 시간 | 스태미나 | 효과 | 호감도 | 비고 |
|----|------|----------|---------|------|--------|------|
| hug | 껴안기 | 5분 | 1 | 호감+3 | 50 | |
| deep_kiss | 딥키스 | 5분 | 2 | 호감+3, 성욕+3 | 70 | |
| tongue_play | 혀 섞기 | 5분 | 2 | 호감+2, 성욕+4 | 75 | **신규** |
| butt_squeeze | 엉덩이 주무르기 | 5분 | 2 | 호감+1, 성욕+3, 욕망+1 | 75 | **신규** |
| breast_touch | 가슴 만지기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+1 | 80 | exposure_bonus: upper |
| breast_squeeze | 가슴 주무르기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+2 | 85 | **신규**, exposure_bonus: upper |
| breast_suck | 가슴 빨기 | 5분 | 3 | 성욕+6, 욕망+3 | 90 | **신규**, requires_exposure: upper |
| genital_touch | 음부 만지기 | 5분 | 3 | 호감+1, 성욕+5, 욕망+3 | 90 | exposure_bonus: lower |
| clit_rub | 클리토리스 문지르기 | 5분 | 3 | 성욕+7, 욕망+4 | 95 | exposure_bonus: lower |
| clit_lick | 클리토리스 핥기 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |
| cunnilingus | 커닐링구스 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |
| finger_insertion | 손가락 삽입 | 5분 | 3 | 성욕+7, 욕망+4, 복종+1 | 95 | **신규**, requires_exposure: lower |
| penis_touch | 음경 만지기 | 5분 | 3 | 호감+1, 성욕+5, 욕망+3 | 90 | exposure_bonus: lower |
| penis_rub | 음경 문지르기 | 5분 | 3 | 성욕+7, 욕망+4 | 95 | exposure_bonus: lower |
| fellatio | 펠라치오 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |

#### 부위별 행위 요약

| 부위 (카테고리) | 즉시형 | 토글형 | 삽입형 | 합계 |
|----------------|--------|--------|--------|------|
| 입술 (M) | 입술 핥기, 프렌치 키스 | 딥키스, 혀 섞기 | — | 4 |
| 가슴 (B) | 가슴 쓰다듬기, 유두 자극 | 가슴 만지기, 가슴 주무르기, 가슴 빨기 | — | 5 |
| 엉덩이 (A) | 엉덩이 쓰다듬기, 항문 자극 | 엉덩이 주무르기 | 항문 삽입, 피항문삽입 | 5 |
| 음부 (V) | 음부 쓰다듬기 | 음부 만지기, 커닐링구스, 손가락 삽입 | 삽입 | 5 |
| 클리토리스 (C) | 클리토리스 자극 | 클리토리스 문지르기, 클리토리스 핥기 | — | 3 |
| 음경 (P) | 음경 쓰다듬기, 음경 자극 | 음경 만지기, 음경 문지르기, 펠라치오 | 피삽입 | 6 |
| 얼굴/목 (F) | 목 키스, 귀 만지기, 뺨 어루만지기, 뺨 꼬집기 | — | — | 4 |

### 캐릭터별 반응 시스템

`base.py`의 Character 클래스에 정의:
```python
ROMANCE_REACTIONS = {
    "action_id": {
        "start": "시작 시 텍스트",   # 행위 시작 (토글 ON, 즉시 실행)
        "during": "진행 중 텍스트",  # UI에 표시 (토글 ON 상태)
        "end": "종료 시 텍스트",     # 토글 OFF 시
    },
}
```

**세라 예시** (`sera.py`):
```python
ROMANCE_REACTIONS = {
    "hug": {
        "start": [
            ({"애정": 50}, ["...안아줘...", "...이대로 있자..."]),
            ({}, ["......", "...뭐냐.", "...싫진 않다."]),
        ],
        "during": [
            ({"성적흥분": 50}, ["세라의 심장이 빠르게 뛰는 게 느껴진다."]),
            ({}, ["세라가 뻣뻣하게 서 있다."]),
        ],
    },
    "ecstasy": {
        "start": [({}, ["......!!", "...으... 응...!"])],
    },
}
```

---

## 2. 데이트 시스템 (date.py)

### 핵심 특징
- 데이트 요청/종료로 상태 관리
- 데이트 중 NPC가 플레이어를 따라다님 (follow 스케줄)
- 애정 표현 액션의 조건이 데이트 중/외로 달라짐

### 상수
```python
DATE_MIN_AFFECTION = 30  # 데이트 수락 최소 호감도
```

### 애정 표현 조건 차이

| 액션 | 데이트 중 | 데이트 외 |
|------|----------|----------|
| 손 잡기 | 호감 30 (거부 가능) | 호감 50 (조건 충족 시만 표시) |
| 안아주기 | 호감 50 (거부 가능) | 호감 70 (조건 충족 시만 표시) |
| 키스 | 호감 60 (거부 가능) | 호감 80 (조건 충족 시만 표시) |

### 액션 '#' 처리
- `actions = ["call:hold_hands:손 잡기#"]`
- '#' 접미사: `can:hold_hands` prop이 0이면 버튼 숨김
- `update_affection_action_visibility()`: NPC focus 시 호출, 조건에 따라 can: prop 설정

### 플로우
```
데이트 신청 → NPC 수락/거절
        ↓ (수락)
데이트 시작:
  - can:date = 0, can:end_date = 1
  - NPC 스케줄 push(FOLLOW_SCHEDULE)
  - NPC follow job 설정
        ↓
데이트 중:
  - 플레이어 이동 시 NPC가 따라옴
  - 애정 표현 가능 (낮은 조건)
        ↓
데이트 종료 → NPC 스케줄 pop
```

---

## 3. NPC 주도 스킨십 시스템 (npc_initiative.py)

### 핵심 특징
- NPC가 조건 충족 시 스킨십을 먼저 시작
- 플레이어는 "빠져나가기"만 가능 (확률 기반)
- 실패 시 NPC가 계속 진행
- 플레이어 시점에서 수동태로 묘사
- **캐릭터별 허용 액션 필터링 (INITIATIVE_ACTION_FILTERS)**
- **행위 마스킹 (신체 부위 충돌 처리)**

### 트리거 조건 (INITIATIVE_CONFIG)

**필수 조건:**
- 플레이어와 NPC가 같은 Location에 **단 둘이** 있어야 함
- 다른 캐릭터가 있으면 NPC 주도 발동 안 함 (오브젝트는 무시)
- 이동 중인 캐릭터도 무시 (도착한 캐릭터만 체크)

캐릭터별로 다른 임계값 설정 가능:

| 캐릭터 | 성욕 임계값 | 호감도 임계값 | 욕망 임계값 | 쿨다운 | 성격 |
|--------|------------|--------------|------------|--------|------|
| 세라 | 70 | 60 | 0 | 8시간 | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | 50 | 40 | 0 | 6시간 | 다정/포근 - 연애 저돌적 |
| 리나 | 65 | 55 | 0 | 8시간 | 활발 - 연애엔 수줍음 |
| 유키 | 80 | 70 | 0 | 12시간 | 매우 수줍음 |
| 엘라 | 75 | 65 | 0 | 10시간 | 냉정함 |

```python
# 밀라 예시 - 저돌적인 성격 반영
INITIATIVE_CONFIG = {
    "arousal_threshold": 50,      # 낮은 성욕에서도 시작
    "affection_threshold": 40,    # 낮은 호감에서도 시작
    "desire_threshold": 0,        # 욕망 임계값 (0 = 체크 안 함)
    "cooldown_minutes": 360,      # 짧은 쿨다운
}
```

### 캐릭터별 허용 액션 필터 (INITIATIVE_ACTION_FILTERS)
NPC 주도 시 캐릭터 성격과 관계 진척도에 따라 허용되는 액션이 달라짐:

```python
# 밀라 - 저돌적 (낮은 조건에서도 다양한 액션)
INITIATIVE_ACTION_FILTERS = [
    ({"호감": 85}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "clit_rub"]),
    ({"호감": 70}, ["hug", "deep_kiss", "breast_touch", "genital_touch"]),
    ({"호감": 60}, ["hug", "deep_kiss", "breast_touch"]),
    ({"호감": 30}, ["hug", "deep_kiss"]),
    ({}, ["hug"]),
]

# 유키 - 매우 수줍음 (높은 호감에서도 제한적)
INITIATIVE_ACTION_FILTERS = [
    ({"호감": 98}, ["hug", "deep_kiss", "breast_touch", "genital_touch", "clit_rub"]),
    ({"호감": 90}, ["hug", "deep_kiss", "breast_touch", "genital_touch"]),
    ({"호감": 85}, ["hug", "deep_kiss", "breast_touch"]),
    ({"호감": 60}, ["hug"]),
    ({}, ["hug"]),
]
```

### 행위 마스킹 시스템 (신체 부위 충돌)
같은 신체 부위(exp_part)를 사용하는 행위는 충돌하여 이전 행위가 자동 해제됨:

```python
# 신체 부위 정의
NPC_TOGGLE_ACTIONS = {
    "hug": {..., "exp_part": None, ...},            # 충돌 없음
    "deep_kiss": {..., "exp_part": "입술", ...},
    "breast_touch": {..., "exp_part": "가슴", ...},
    "genital_touch": {..., "exp_part": "음부", ...},
    "clit_rub": {..., "exp_part": "클리토리스", ...},
    "penis_touch": {..., "exp_part": "음경", ...},
    "penis_rub": {..., "exp_part": "음경", ...},
}

PLAYER_INSTANT_ACTIONS = {
    "head_pat": {..., "exp_part": "머리", ...},
    "french_kiss": {..., "exp_part": "입술", ...},  # deep_kiss와 충돌
    "whisper": {..., "exp_part": None, ...},        # 충돌 없음
    "genital_caress": {..., "exp_part": "음부", ...},
    "penis_caress": {..., "exp_part": "음경", ...},
}
```

**충돌 처리 로직**:
- 토글 → 토글: 새 토글 활성화 시, 같은 exp_part의 기존 토글 비활성화
- 즉시 → 토글: 즉시 행위 실행 시, 같은 exp_part의 활성 토글 비활성화
- exp_part가 None인 행위는 충돌하지 않음

### 빠져나가기 확률
```python
ESCAPE_BASE_CHANCE = 0.3  # 기본 30%
ESCAPE_STRENGTH_BONUS = 0.05  # 힘 1당 +5%
ESCAPE_BODY_BONUS = {
    "왜소": -0.1,
    "보통": 0.0,
    "장신": 0.05,
    "거구": 0.15,
}
```

### 반응 텍스트 (INITIATIVE_REACTIONS)
캐릭터별로 성격을 반영한 반응 텍스트:

```python
# 밀라 - 따뜻하고 적극적
INITIATIVE_REACTIONS = {
    "start": [
        ({"성욕": 70}, ["...보고 싶었어요...", "...가만히 있어줘요..."]),
        ({}, ["...잠깐만요...", "...가까이 와도 될까요...?"]),
    ],
    "satisfied": [
        ({"호감": 50}, ["...사랑해요...", "...행복해요..."]),
        ({}, ["...고마워요...", "...기분이 좋아요..."]),
    ],
}

# 유키 - 조용하고 수줍음
INITIATIVE_REACTIONS = {
    "start": [
        ({"성욕": 80}, ["......", "...(말없이 다가온다)"]),
        ({}, ["......", "...저기요..."]),
    ],
}
```

### 플로우
```
on_meet 이벤트 발생
    │
    ▼
should_initiate_skinship() 체크
├─ 성욕 >= threshold?
├─ 호감도 >= threshold?
├─ 쿨다운 경과?
└─ 제3자 없음?
    │
    ├─ 조건 불충족 → 일반 on_meet 처리
    └─ 조건 충족 → start_npc_initiative()
                        │
                        ▼
         ┌─ render_npc_initiative_ui() ─┐
         │  - NPC 반응 텍스트           │
         │  - [빠져나가기] 버튼          │
         │  - [받아들이기] 버튼          │
         └──────────────┬───────────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
    [빠져나가기]                    [받아들이기]
         │                             │
    확률 판정                           │
    ├─ 성공 → 종료                     │
    └─ 실패 → 계속                     │
                        │              │
                        ├──────────────┘
                        │
                        ▼
          select_random_npc_action()
          (캐릭터별 필터 적용)
                        │
                        ▼
          remove_conflicting_toggles()
          (신체 부위 충돌 처리)
                        │
                        ▼
                  NPC 액션 실행
                        │
                        ▼
                  시간 경과 + 제3자 감지
                        │
          ┌─────────────┼─────────────┐
          │             │             │
     은신 성공      은신 실패        도착 없음
     (근접 경고)   (중단 이벤트)       │
          │             ↓             │
          └──────────> 종료           │
                                      ↓
                                NPC 만족? → 종료
                                      ↓
                                   다음 루프
```

### NPC 주도 중 은신 시스템

플레이어 주도와 동일한 은신 확률 시스템이 적용됩니다:

- **기본 확률**: 30%
- **은신 중**: +40% (총 70%)
- **최대**: 90%

**방해 이벤트 발생 시 (NPC 주도):**
- 목격자의 캐릭터별 발각 반응 (`on_romance_discovered()`)
- NPC에게 "부끄러움" mood 추가
- NPC가 플레이어로부터 도망 (`flee` job)
- 목격자 호감도 변화: `ROMANCE_DISCOVERY_REACTIONS`의 effects에 따라 (파트너별 분기)
- NPC 호감도 -3

---

## 4. 은신 시스템 (들키지 않을 확률)

제3자가 도착해도 확률적으로 들키지 않을 수 있습니다.

**은신 확률 계산:**
| 조건 | 확률 |
|------|------|
| 기본 | 30% |
| 은신 중 (hiding=True) | +40% (총 70%) |
| 최대 | 90% (항상 들킬 가능성 존재) |

**은신 결과:**
- **성공**: 근접 경고 표시 ("XXX(이)가 근처를 지나갔다... 들키지 않았다.")
- **실패**: 세션 조용히 종료 → 도착 NPC의 on_meet 이벤트 큐 재수집 → 자연 처리
  - `morld.queue_event("meet", player_id, [player_id, interrupter_id])`로 이벤트 큐에 수동 주입
  - `on_meet_player()` → `_check_room_privacy()` 등이 자연 실행됨
  - 예: 목욕하러 온 NPC → privacy 이벤트로 플레이어 추방

**중복 체크 방지:**
- 한 번 체크한 NPC는 `checked_npcs` set에 저장
- 같은 NPC에게 여러 번 들키지 않음

**관련 상수:**
```python
STEALTH_BASE_CHANCE = 0.3      # 기본 은신 확률 30%
STEALTH_HIDING_BONUS = 0.4     # 은신 중일 때 추가 확률 +40%
```

### 캐릭터별 은신 성공 반응 (STEALTH_REACTIONS)

은신 성공 시 캐릭터별로 다른 반응과 파라미터 변화가 적용됩니다.

**시스템 구조:**
```python
STEALTH_REACTIONS = {
    "text": [
        # 조건 기반 텍스트 선택
        ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
        ({"호감": 40}, ["......", "...조심해."]),
        ({}, ["......", "...(긴장한 표정)"]),
    ],
    "effects": {"성욕": 5},  # 은신 성공 시 파라미터 변화
}
```

**캐릭터별 은신 반응:**

| 캐릭터 | 반응 특징 | 효과 |
|--------|----------|------|
| 세라 | 스릴에 흥분 | 성욕 +5 |
| 밀라 | 부끄러워함 | (효과 없음) |
| 리나 | 무섭지만 흥분 | 호감 +1, 성욕 +3 |
| 유키 | 무서워서 더 매달림 | 호감 +2 |
| 엘라 | 차갑게 경계 | 호감 +1 |

**UI 표시:**
- 은신 성공 시 시안색(`[color=cyan]`)으로 캐릭터 반응 텍스트 표시
- 예: `[color=cyan][세라] ...위험했어...[/color]`

---

## 5. 발각 반응 시스템 (Discovery Reactions)

### 개요
애정행위 중 제3자에게 발각되었을 때, 목격자의 성격 + 파트너가 누구인지에 따라
다른 대사와 효과가 적용됨. 호감 감소 + 반발 증가, 나체 발각 시 추가 페널티.

### 플로우

#### 플레이어 주도 (romance.py)
```
중단 감지 → set_interrupted_context(partner_id)
         → handle_interruption()
         → 중단 로그 ("XX의 방해로 중단되었다.")
         → pop_to_situation()
         → queue_event("meet") → on_meet_player()
         → get_interrupted_context() → on_romance_discovered()
         → 파트너 노출 체크 → _romance_discovery_dialog(exposed=True/False)
```

#### NPC 주도 (npc_initiative.py)
```
중단 감지 → handle_npc_initiative_interruption()
         → interrupter.on_romance_discovered(player_id, npc_id)
         → NPC 부끄러움 + 도망 + 반발 증가
         → NPC 노출 시 추가 페널티 (호감-2, 반발+5)
```

### 캐릭터별 발각 반응 (ROMANCE_DISCOVERY_REACTIONS)

```python
ROMANCE_DISCOVERY_REACTIONS = {
    "default": {
        "text": ["...!"],
        "exposed_text": ["...!!"],         # 파트너 나체 시 대사 (선택적)
        "effects": {"호감": -3, "반발": 3},
    },
    "sera": {
        "text": ["...세라랑?!"],
        "exposed_text": ["...세라가 벗은 채로?!"],
        "effects": {"호감": -5, "반발": 5},
    },
}
```

| 캐릭터(목격자) | 성격 톤 | default | 특별 반응 파트너 |
|--------------|---------|---------|-----------------|
| 세라 | 침묵 → 한마디 | 호감-3, 반발+3 | 리나(-5/+5), 밀라(-4/+4) |
| 리나 | 큰 충격, 놀람 | 호감-5, 반발+5 | 세라(-8/+8), 밀라(-6/+6) |
| 밀라 | 조용히 상처 | 호감-3, 반발+3 | 세라(-4/+4), 리나(-5/+5) |
| 유키 | 얼어붙음 | 호감-3, 반발+3 | 엘라(-8/+8) |
| 엘라 | 차갑게 한마디 | 호감-3, 반발+3 | 유키(-10/+10), 세라(-4/+4) |

### 나체 발각 추가 페널티

파트너가 탈의 상태(상체 또는 하체 노출)일 때 기본 효과 위에 추가 적용:

```python
EXPOSURE_DISCOVERY_PENALTY = {"호감": -3, "반발": 5}  # base.py
```

- 대사: `exposed_text` 필드가 있으면 해당 대사 사용, 없으면 기본 `text` 사용
- 효과: 기존 effects + EXPOSURE_DISCOVERY_PENALTY 합산 적용
- NPC 주도: NPC에게도 동일 추가 페널티 (호감-2, 반발+5)

### 관련 메서드 (base.py)
- `on_romance_discovered(player_id, partner_id)` → 파트너 노출 체크 → Generator 또는 None
- `_romance_discovery_dialog(player_id, reaction, exposed=False)` → 대사 + effects + 노출 페널티 적용

### 컨텍스트 전달 (romance.py)
- `set_interrupted_context(partner_id)` — 1회성 저장
- `get_interrupted_context()` — 소비 후 None 리셋

---

## 6. 소음 시스템 (Romance Sound)

### 개요
행위 중 캐릭터가 소음(신음)을 발생시켜 sound.py의 전파 시스템과 연동.
흥분도(성욕)에 따라 3단계로 소음 강도가 달라지며, 캐릭터별 프로필이 다름.

### 흥분도 단계
| 단계 | 성욕 범위 | 설명 |
|------|----------|------|
| 0 (low) | 0~34 | 조용 |
| 1 (mid) | 35~69 | 중간 |
| 2 (high) | 70+ | 시끄러움 |

### 캐릭터별 소음 프로필 (ROMANCE_SOUND_PROFILE)

```python
ROMANCE_SOUND_PROFILE = {"levels": [low, mid, high], "ecstasy": ecstasy_intensity}
```

| 캐릭터 | low | mid | high | 절정 | 특징 |
|--------|-----|-----|------|------|------|
| 세라 | 5 | 15 | 50 | 70 | 초반 조용, 후반 시끄러움 |
| 리나 | 25 | 40 | 60 | 80 | 처음부터 시끄러움 |
| 밀라 | 5 | 15 | 25 | 40 | 조용 → 중간 |
| 유키 | 10 | 20 | 35 | 50 | 중간 정도 |
| 엘라 | 3 | 10 | 20 | 35 | 전체적으로 조용 |

### 소음 발생 위치
- `romance.py` proc(): 즉시형/토글형 행위 실행 시 `emit_romance_sound()`, 절정 시 `emit_ecstasy_sound()`
- `npc_initiative.py`: NPC 주도 행위 중 플레이어 액션/수락 시 동일

### 관련 함수 (romance.py)
- `get_excitement_level(npc_id)` → 0/1/2
- `emit_romance_sound(partner_id)` → `sound.emit_sound(id, "moan", intensity)`
- `emit_ecstasy_sound(partner_id)` → 절정 강도로 emit

---

## 7. 감각 시스템 (Sensation System)

### 개요

부위별 경험치(`경험:{부위}`)를 M/B/A/V/C/P/F 감각 카테고리에 매핑하여
감각 레벨을 산출하고, 성욕 효과에 보정을 적용합니다.

### 감각 카테고리 매핑 (SENSATION_MAP)

| 부위 | 카테고리 | 설명 |
|------|----------|------|
| 입술 | M (Mouth) | 키스 계열 |
| 가슴 | B (Breast) | 가슴 계열 |
| 엉덩이 | A (Anal) | 엉덩이 계열 |
| 음부 | V (Vaginal) | 음부 계열 |
| 클리토리스 | C (Clitoral) | 클리토리스 계열 |
| 음경 | P (Penis) | 음경 계열 (male) |
| 목 | F (Face) | 얼굴/목 계열 |
| 귀 | F (Face) | 얼굴/목 계열 |
| 뺨 | F (Face) | 얼굴/목 계열 |
| 머리 | None | 비성적 |

### 감각 레벨 계산 (비선형 제곱 곡선)

```python
import math

def get_sensation_level(unit_id, category):
    """경험치 합산 기반 감각 레벨 (0-10) — 제곱 곡선"""
    total_exp = sum(
        morld.get_unit_prop(unit_id, f"경험:{part}") or 0
        for part, cat in SENSATION_MAP.items()
        if cat == category
    )
    return min(10, int(math.floor(math.sqrt(total_exp / 3))))
```

**레벨별 필요 경험치:**

| 레벨 | 필요 exp | 누적 기본절정 횟수 |
|------|---------|-------------------|
| 1 | 3 | 1회 |
| 3 | 27 | 9회 |
| 5 | 75 | 25회 |
| 7 | 147 | 49회 |
| 10 | 300 | 100회 |

저레벨은 빠르게 성장, 고레벨은 반복적인 절정(특히 연쇄 절정)이 필요.

### 감각 보정 (성욕 효과)

`calculate_effects()`에서 성욕 효과에 sensation bonus 추가:

```python
bonus = round(base_arousal_effect * sensation_level * 0.1)
```

- 감각 레벨 0: 보정 없음
- 감각 레벨 5: 성욕 효과 +50%
- 감각 레벨 10: 성욕 효과 +100%

### UI 표시

```
[애인] 호감: 45  욕망: 20  성욕: 60
자극: M:0 B:15 V:72  [여운]  절정: 1
감각: M:3 B:1 V:2 C:1
```

- 관계 라벨 + 호감/욕망/성욕 표시 (애정 제거)
- 자극: 대상 성별 기반으로 해당 카테고리만 표시 + 여운/절정 상태
- 반발 > 0일 때만 반발 표시
- 감각 레벨이 0 초과인 카테고리만 표시 (F/M/B/A/V/C/P 순서).

---

## 8. 자극 시스템 (stimulation.py)

### 개요
부위별 자극 수치를 관리하여 절정을 발생시키는 세션 스코프 시스템.
기존 성욕 임계값(100) 방식을 대체.

### 핵심 특성
- **세션 스코프**: romance 세션 state dict 안에만 존재, prop 아님
- **부위별 자극**: FMBAVCP 카테고리별 독립 자극 수치 (0-100)
- **절정**: 자극이 100 도달 시 발생, 해당 카테고리 자극 리셋
- **여운 (afterglow)**: 여성 절정 후 일시적 상태, 행위마다 감소
- **연쇄 절정**: 여운 중 재절정 시 자극 증폭 (×1.5)
- **불응기 (refractory)**: 남성 절정 후 자극 gain 90% 감소, 연쇄 불가

### 상수

| 상수 | 값 | 설명 |
|------|---|------|
| STIM_MAX | 100 | 절정 발생 임계값 |
| AFTERGLOW_INITIAL | 50 | 절정 시 부여되는 여운 초기값 (여성) |
| AFTERGLOW_DECAY | 10 | 행위 1회당 여운 감소량 |
| CHAIN_AMPLIFIER | 1.5 | 연쇄 절정 시 자극 배율 |
| CLIMAX_AROUSAL_REDUCTION | 30 | 절정 시 성욕 감소량 |
| CLIMAX_SENSATION_GAIN | 3 | 절정 부위 경험치 기본 보너스 |
| REFRACTORY_INITIAL | 60 | 불응기 초기값 (남성, 6턴 지속) |
| REFRACTORY_DECAY | 10 | 행위 1회당 불응기 감소량 |
| REFRACTORY_GAIN_FACTOR | 0.1 | 불응기 중 자극 gain 배율 |

### male_mode

`create_state(male_mode=False)` — 세션 생성 시 대상 성별에 따라 결정:
- `male_mode=True`: 남성 대상 → 절정 시 불응기 진입
- `male_mode=False`: 여성/후타나리 대상 → 절정 시 여운 진입

### 자극 증가량 계산

```python
def calc_gain(base, sensation_level, rebellion, afterglow, refractory=0):
    gain = base * (1.0 + sensation_level * 0.15)
    gain *= max(0.2, 1.0 - rebellion * 0.008)  # 반발 감소
    if refractory > 0:
        gain *= REFRACTORY_GAIN_FACTOR  # 0.1 — 불응기 중 대폭 감소
    elif afterglow > 0:
        gain *= CHAIN_AMPLIFIER  # 여운 중 증폭
    return max(1, round(gain))
```

### 절정 처리 (여성)
1. 해당 카테고리 자극 리셋 (0)
2. 연쇄 판정 (여운 중이면 연쇄)
3. 여운 진입/갱신 (afterglow = 50)
4. 성욕 -30 (전액 초기화 대신)
5. 성적절정 +1
6. 절정 부위 감각 경험치 +3

### 절정 처리 (남성)
1. 해당 카테고리 자극 리셋 (0)
2. 불응기 진입 (refractory = 60)
3. 여운/연쇄 초기화 (afterglow = 0, chain_count = 0)
4. 성욕 -30
5. 성적절정 +1
6. 절정 부위 감각 경험치 +3

### UI 표시
```
자극: M:0 B:15 V:72  [여운 ×2]  절정: 1    # 여성
자극: M:0 B:15 P:72  [불응기]  절정: 1      # 남성
```
- 대상 성별 기반으로 해당 카테고리만 표시
- 여성 여운 중: `[color=pink][여운][/color]` + 연쇄 횟수 표시
- 남성 불응기 중: `[color=red][불응기][/color]` 표시
- 절정 누적 횟수 표시

---

## 9. 공수 전환 시스템 (Initiative Switching)

세션 도중 주도권을 전환 (플레이어 ↔ NPC).

### 전환 방향

| 방향 | 조건 | UI 텍스트 |
|------|------|-----------|
| Player→NPC | NPC에 `INITIATIVE_CONFIG` + 호감 ≥ affection_threshold | `주도권 넘기기` |
| NPC→Player | 호감 ≥ `ROMANCE_ENTRY_THRESHOLD` (50) | `주도권 빼앗기` |

### 보존 상태

전환 시 다음 상태가 유지됨:
- **자극 상태** (`stim`): M/B/A/V/C/P 수치, 여운, 연쇄, 절정 횟수
- **스태미나**: 남은 양
- **경과시간**: 세션 누적
- **감지 기록** (`checked_npcs`): 중복 판정 방지

### 메커니즘

`yield from` 체이닝 — 현재 세션 dialog 종료 후 반대편 시스템의 제너레이터 실행:

```python
# romance.py → npc_initiative.py
if state.get("switch_to") == "npc":
    preserved = _extract_preserved(state)
    yield from start_npc_initiative(player_id, partner_id, preserved=preserved)
```

- 전환 시 `pop_schedule()` 하지 않음 (파트너 고정 유지)
- 새 세션에서 `push_schedule()` 하지 않음 (`schedule_pushed` 플래그)
- 최종 세션 종료 시에만 `pop_schedule()` 실행
- `active_toggles`는 빈 set으로 초기화 (새 주도자가 선택)

---

## 10. 탈의/노출 시스템 (Undress/Exposure)

### 개요

연애 세션 중 NPC의 옷을 벗기는 행위를 추가. 노출 상태에 따라 행위 해금/효과 보정.
세션 종료 후 NPC 나체 → 기존 `_check_clothing()` 인터럽트가 자연 연계되어 재착의.

### 노출 상태 판정 (get_exposure_state)

장착 아이템의 `equip_props`를 검사하여 상/하체 노출 상태 반환:

| 노출 부위 | 조건 |
|----------|------|
| upper_exposed | `착용:상의`와 `착용:속옷상의` 모두 없음 |
| lower_exposed | `착용:하의`와 `착용:속옷하의` 모두 없음 |

실제 장비 기반 판정 → 세션 상태에 보존 불필요, 공수 전환 시 자동 유지.

### 탈의 순서

```python
UNDRESS_UPPER_SLOTS = ["착용:외투", "착용:상의", "착용:속옷상의"]
UNDRESS_LOWER_SLOTS = ["착용:하의", "착용:속옷하의"]
```

외투 → 상의 → 속옷상의 (상체), 하의 → 속옷하의 (하체) 순서로 1개씩 탈의.
원피스(착용:상의 + 착용:하의 동시 점유)는 어느 쪽 탈의로든 제거 가능.

### 탈의 행위 (INSTANT_ACTIONS)

| 행위 | 시간 | 효과 | 필요 호감도 |
|------|------|------|------------|
| 상체 옷 벗기기 | 3분 | 호감+1 | 70 |
| 하체 옷 벗기기 | 3분 | 호감+1 | 80 |

- 이미 완전 노출 시 탈의 버튼 자동 숨김
- proc 처리: `perform_undress()` → `equipment.unequip_item()` 호출

### 하드 락 (requires_exposure)

특정 행위는 해당 부위 노출 필수:

| 행위 | 필요 노출 |
|------|----------|
| 음부 쓰다듬기 (genital_caress) | lower |
| 클리토리스 자극 (clit_stimulation) | lower |
| 음경 쓰다듬기 (penis_caress) | lower |
| 음경 자극 (penis_stimulation) | lower |

미노출 시 `[color=gray]행위이름 (탈의 필요)[/color]` 표시.

### 소프트 보너스 (exposure_bonus)

노출 시 해당 행위 효과 ×1.5 (`EXPOSURE_BONUS`):

| 행위 | 보너스 부위 |
|------|-----------|
| 가슴 만지기 (breast_touch) | upper |
| 음부 만지기 (genital_touch) | lower |
| 클리토리스 문지르기 (clit_rub) | lower |
| 음경 만지기 (penis_touch) | lower |
| 음경 문지르기 (penis_rub) | lower |

UI에 `[color=pink]×1.5[/color]` 힌트 표시.

### UI 표시

```
복장: [color=pink]상체 노출[/color] [color=pink]하체 노출[/color]
```

감각 레벨 아래, divider 위에 표시. 노출 부위가 없으면 생략.

### 세션 종료 → 착의 연계

세션 종료 시 착의 쿨다운 리셋:
```python
partner_agent._memory["clothing_last_attempt"] = None
```

이후 NPC think() → Tier 4a `_check_clothing()` → `_is_dressed()` False 감지 → 착의 인터럽트 발동.

---

## 11. NPC 성욕 행동 시스템

### 성적흥분 상한 클램프

`needs.py`의 `_process_hourly()`에서 성욕이 동적 상한(`_get_arousal_cap()`) 초과 시 즉시 클램프.
욕망 감소 → 상한 하락 → 성욕 자동 조절.

### 은밀 장소 선정 (length 기반)

Location의 기존 `length` 속성으로 은밀도 판정 — 별도 속성 없음:

| 조건 | 설명 |
|------|------|
| 같은 region | 현재 NPC 위치와 동일 region |
| `length ≤ self_comfort_max_length` | 기본 150 (침실/욕실/화장실=150 포함, 부엌/식당/창고=180 제외) |
| 비어있는 location | 본인 외 아무도 없음 |
| 실내 (`is_indoor=True`) | 실외 location 제외 |
| 오염도 ≤ 10 | 오염이 심한 곳 제외 |

우선순위: 현재 위치 → 침실(sleep_location) → 화장실(toilet_location) → region 내 가장 가까운 후보.

### NPC 자위 (Self-Comfort)

Tier 4 comfort에 위치 (배변 → 피로 → **성욕** → 목욕 → 수면).

- 조건: `arousal ≥ self_comfort_threshold` + 2시간 쿨다운
- 우선순위: 플레이어 탐색 > 자위
- 은밀 장소: `length ≤ self_comfort_max_length` + 실내 + 혼자 + 저오염
- Phase: idle → going → performing (15분 job "자위") → finishing (결과 확인)
- **혼자일 때**: arousal -50, 정상 쿨다운 2시간
- **NPC 발각**: arousal 감소 없음, 짧은 쿨다운 30분 (재시도 유도)
- **플레이어 발각**: SELF_COMFORT_DISCOVERY_REACTIONS 반응
- Job 이름: 이동 중 "이동" (발각 안 됨), 수행 중 "자위" (발각 대상)

### NPC→플레이어 탐색

arousal ≥ threshold + INITIATIVE_CONFIG 조건 충족 + 같은 region → 플레이어 location으로 이동.
도착 시 on_meet → should_initiate_skinship → NPC 주도 시작.

### 감각 기반 주도 제한 (INITIATIVE_SENSATION_REQS)

`get_allowed_initiative_actions()`에서 INITIATIVE_ACTION_FILTERS 매칭 후 독립 필터:

```python
INITIATIVE_SENSATION_REQS = {
    "deep_kiss": {"M": 1},       # 입 감각 레벨 1 이상
    "breast_touch": {"B": 1},    # 가슴 감각 레벨 1 이상
    "genital_touch": {"V": 2},   # 음부 감각 레벨 2 이상
    "clit_rub": {"C": 2},        # 클리토리스 감각 레벨 2 이상
}
```

감각 경험 부족 → 기본 행위(hug)만 주도 가능.

### 자위 발각

on_meet_player() 내 수면 체크 다음:
- job name "자위" → `_on_self_comfort_discovered()` → SELF_COMFORT_DISCOVERY_REACTIONS
- NPC 상태 리셋 + 조건부 대사 + 호감 감소

### 캐릭터별 설정

| 캐릭터 | self_comfort_threshold | max_length | 발각 호감 | 성격 |
|--------|----------------------|------------|----------|------|
| 세라 | 85 | 150 | -5 | 분노+수치 |
| 밀라 | 70 | 150 | -3 | 당혹+울먹임 |
| 리나 | 80 | 150 | -5 | 패닉 |
| 유키 | 90 | 150 | -3 | 공포+경직 |
| 엘라 | 85 | 150 | -5 | 냉정한 수습 |

---

## 12. 삽입 행위 시스템 (Intercourse)

### 개요

기존 스킨십 행위는 모두 외부 자극(만지기/쓰다듬기/문지르기)이었으나,
삽입 행위는 체내 결합을 수반하는 행위 카테고리. 임신 시스템의 전제 조건이자
연애 행위의 최종 단계.

### 새 필드: requires_player_anatomy

기존 행위는 NPC(대상)의 해부학만 체크했으나, 삽입은 **양쪽 모두** 필요:

| 필드 | 기존 | 삽입 행위에서 추가 |
|------|------|-------------------|
| `exp_part` → SENSATION_MAP → `has_anatomy(target)` | NPC 해부학 체크 | 동일 유지 |
| `requires_player_anatomy` | 없음 | 플레이어 해부학 추가 체크 |

```python
# 예: 삽입 (플레이어 P → NPC V)
"vaginal_penetration": {
    "exp_part": "음부",                    # NPC쪽 → has_anatomy(npc, "V") 체크
    "requires_player_anatomy": "P",        # 플레이어쪽 → has_anatomy(player, "P") 체크
}

# 예: 피삽입 (NPC P → 플레이어 V)
"receive_penetration": {
    "exp_part": "음경",                    # NPC쪽 → has_anatomy(npc, "P") 체크
    "requires_player_anatomy": "V",        # 플레이어쪽 → has_anatomy(player, "V") 체크
}
```

**is_anatomy_compatible() 확장:**
```python
def is_anatomy_compatible(action_def, target_id, player_id=None):
    # 기존: NPC 해부학 체크
    exp_part = action_def.get("exp_part")
    if exp_part:
        category = SENSATION_MAP.get(exp_part)
        if category and not has_anatomy(target_id, category):
            return False
    # 추가: 플레이어 해부학 체크
    player_req = action_def.get("requires_player_anatomy")
    if player_req and player_id:
        if not has_anatomy(player_id, player_req):
            return False
    return True
```

### 삽입 토글 행위 정의

삽입은 **토글형** (지속 행위). 시작 후 매 틱마다 자극/효과 누적.
즉시형 삽입은 없음 — 삽입은 본질적으로 지속 행위.

#### 전체 삽입 행위 목록

| 행위 ID | 이름 | 틱당 시간 | 스태미나 | exp_part | player_anatomy | 효과 | 호감도 | 비고 |
|---------|------|----------|---------|----------|---------------|------|--------|------|
| `vaginal_penetration` | 삽입 | 5분 | 4 | 음부 | P | 성욕+8, 욕망+5, 복종+1 | 98 | pregnancy_check |
| `receive_penetration` | 피삽입 | 5분 | 4 | 음경 | V | 성욕+8, 욕망+5 | 98 | pregnancy_check |
| `anal_penetration` | 항문 삽입 | 5분 | 4 | 엉덩이 | P | 성욕+8, 욕망+5, 복종+2 | 98 | **신규** |
| `receive_anal` | 피항문삽입 | 5분 | 4 | 음경 | A | 성욕+8, 욕망+5 | 98 | **신규** |

> **손가락 삽입**(`finger_insertion`)과 **커닐링구스/펠라치오**는
> 토글형 외부 자극으로 분류 (위 TOGGLE_ACTIONS 테이블 참조).
> 이들은 `pregnancy_check` 없음, requires_player_anatomy 없음.

#### 코드 예시

```python
"vaginal_penetration": {
    "name": "삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
    "effects": {"성욕": 8, "욕망": 5, "복종": 1},
    "exp_part": "음부", "affection_req": 98,
    "requires_player_anatomy": "P",
    "requires_exposure": "lower",
    "pregnancy_check": True,            # 절정 시 수정 판정
},
"receive_penetration": {
    "name": "피삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
    "effects": {"성욕": 8, "욕망": 5},
    "exp_part": "음경", "affection_req": 98,
    "requires_player_anatomy": "V",
    "requires_exposure": "lower",
    "pregnancy_check": True,
},
"anal_penetration": {
    "name": "항문 삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
    "effects": {"성욕": 8, "욕망": 5, "복종": 2},
    "exp_part": "엉덩이", "affection_req": 98,
    "requires_player_anatomy": "P",
    "requires_exposure": "lower",
    # pregnancy_check 없음 — 임신 불가
},
"receive_anal": {
    "name": "피항문삽입", "time": 5 * MILLIS_PER_MINUTE, "stamina": 4,
    "effects": {"성욕": 8, "욕망": 5},
    "exp_part": "음경", "affection_req": 98,
    "requires_player_anatomy": "A",     # A = 모든 성별 보유
    "requires_exposure": "lower",
},
```

### NPC 주도 삽입

NPC 주도 시스템(`npc_initiative.py`)에도 동일 4종 추가:

```python
NPC_TOGGLE_ACTIONS에 추가:
"vaginal_penetration": { ..., "pregnancy_check": True },
"receive_penetration": { ..., "pregnancy_check": True },
"anal_penetration": { ... },
"receive_anal": { ... },
```

**INITIATIVE_ACTION_FILTERS에 추가 (캐릭터별):**
- 최상위 필터 (가장 높은 호감 조건)에만 삽입 행위 포함
- 기존 액션 리스트 끝에 추가

**INITIATIVE_SENSATION_REQS에 추가:**
```python
"vaginal_penetration": {"V": 3},   # 음부 감각 레벨 3 이상
"receive_penetration": {"P": 3},   # 음경 감각 레벨 3 이상
"anal_penetration": {"A": 3},      # 엉덩이 감각 레벨 3 이상
"receive_anal": {"P": 3},          # 음경(NPC) 감각 레벨 3 이상
```

### 노출 요건

모든 삽입 행위는 **하체 노출** 필수 (하드 락):
- `requires_exposure: "lower"` — NPC 하체 노출 필수
- 미노출 시 `[color=gray]삽입 (탈의 필요)[/color]` 표시
- 노출 보너스(×1.5)는 이미 노출 필수이므로 적용 안 함

### 임신 판정 (pregnancy_check) — 절정 시 판정

**중요: 수정 판정은 매 틱이 아닌, P를 가진 쪽의 절정 시에만 발생.**

`pregnancy_check: True` 플래그가 있는 삽입 행위가 활성 상태에서 절정이 발생할 때:

```python
# 절정 처리 블록 내 (romance.py, npc_initiative.py):
if climax_info and any_active_intercourse_with_pregnancy_check(state):
    # P를 가진 쪽이 절정했을 때만 수정 판정
    if is_p_side_climax(climax_info, state):
        import pregnancy
        pregnancy.check_conception(player_id, partner_id)
```

**판정 조건:**
1. 삽입 행위(`pregnancy_check: True`)가 활성 토글로 진행 중
2. P를 보유한 쪽(삽입자)이 절정 도달
3. V를 보유한 쪽(피삽입자)의 월경 주기 기반 가임 확률 적용

- 항문 삽입(`anal_penetration`, `receive_anal`)은 `pregnancy_check` 없으므로 판정 안 함
- 손가락/구강 행위도 판정 안 함
- 상세 메커니즘은 [romance-pregnancy.md](romance-pregnancy.md) 참조

### 부위 충돌 (exp_part)

| 행위 | exp_part | 충돌 대상 |
|------|----------|----------|
| 삽입 (vaginal_penetration) | 음부 | 음부 만지기, 커닐링구스, 손가락 삽입 |
| 피삽입 (receive_penetration) | 음경 | 음경 만지기, 펠라치오 |
| 항문 삽입 (anal_penetration) | 엉덩이 | 엉덩이 주무르기 |
| 피항문삽입 (receive_anal) | 음경 | 음경 만지기, 펠라치오 |

삽입 활성화 시 같은 부위의 기존 토글 자동 해제.

### 플레이어 신체 충돌 (requires_player_anatomy)

exp_part 기반 충돌은 **NPC쪽 부위** 기준이므로,
**플레이어 신체 1개를 여러 행위에 동시 사용**하는 모순을 방지하지 못함.

예: `vaginal_penetration`(P 필요) + `anal_penetration`(P 필요) 동시 활성화 → 물리적 불가능

**규칙**: 같은 `requires_player_anatomy` 값을 가진 행위는 상호 배타.

```python
def get_conflicting_toggles(new_action_id, active_toggles, new_action_dict=None):
    # 기존: exp_part 충돌 검사
    ...
    # 추가: requires_player_anatomy 충돌 검사
    new_player_req = new_def.get("requires_player_anatomy")
    if new_player_req:
        for toggle_id in active_toggles:
            toggle_def = get_toggle_def(toggle_id)
            if toggle_def and toggle_def.get("requires_player_anatomy") == new_player_req:
                conflicting.add(toggle_id)
    return conflicting
```

| 충돌 그룹 | requires_player_anatomy | 대상 행위 |
|-----------|------------------------|-----------|
| P 사용 | P | vaginal_penetration, anal_penetration |
| V 사용 | V | receive_penetration |
| A 사용 | A | receive_anal |

**결과**: 질 삽입 활성 중 항문 삽입 선택 시, 질 삽입이 자동 해제되고 항문 삽입으로 전환.

### 자극 시스템 연동

삽입은 exp_part 기반으로 기존 자극 시스템과 동일하게 연동:
- `vaginal_penetration` → V 카테고리 자극 증가
- `receive_penetration` → P 카테고리 자극 증가
- `anal_penetration` → A 카테고리 자극 증가
- `receive_anal` → P 카테고리 자극 증가
- 절정 시 기존 절정 처리 로직 그대로 적용

### 효과 밸런스

| 항목 | 질 삽입 | 항문 삽입 | 비교 (클리토리스 문지르기) |
|------|---------|----------|--------------------------|
| 성욕 | +8 | +8 | +7 |
| 욕망 | +5 | +5 | +4 |
| 복종 | +1 | +2 | 없음 |
| 스태미나 | 4 | 4 | 3 |
| 필요 호감도 | 98 | 98 | 95 |
| 노출 | 필수 | 필수 | 보너스 (×1.5) |
| 임신 | 절정 시 판정 | 없음 | 없음 |

항문 삽입은 복종 효과가 더 높고(+2), 임신 판정 없음.

### 소음 연동

삽입 행위 중에도 기존 소음 시스템 동일 적용:
- `emit_romance_sound()` → 흥분도 기반 3단계
- 절정 시 `emit_ecstasy_sound()`

### 캐릭터별 반응 (ROMANCE_REACTIONS)

각 캐릭터 파일에 삽입 4종 + 신규 행위 반응 추가 필요:

```python
ROMANCE_REACTIONS = {
    "vaginal_penetration": {
        "start": [...], "during": [...], "end": [...],
    },
    "receive_penetration": {
        "start": [...], "during": [...], "end": [...],
    },
    "anal_penetration": {
        "start": [...], "during": [...], "end": [...],
    },
    "receive_anal": {
        "start": [...], "during": [...], "end": [...],
    },
    # 신규 외부 행위도 동일 패턴
    "tongue_play": { "start": [...], "during": [...] },
    "breast_suck": { "start": [...], "during": [...] },
    "cunnilingus": { "start": [...], "during": [...] },
    "fellatio": { "start": [...], "during": [...] },
    "finger_insertion": { "start": [...], "during": [...] },
    ...
}
```

---

## 12.5. 절정 묘사 시스템 (Climax Description)

### 개요

기존 절정은 `"ecstasy"` 키 하나로 모든 절정을 동일 묘사했으나,
절정 부위(카테고리)와 연쇄 여부에 따라 다른 묘사를 제공.

### 구조 확장: CLIMAX_REACTIONS

기존 `"ecstasy"` 키를 카테고리별로 세분화:

```python
ROMANCE_REACTIONS = {
    # 기존 (하위 호환 유지)
    "ecstasy": {
        "start": [({}, ["......!!", "...이상해..."])],
    },

    # 카테고리별 절정 묘사 (있으면 우선 사용, 없으면 ecstasy fallback)
    "ecstasy_V": {
        "start": [
            ({"성적절정": 3}, ["...또... 이러면... 안 돼...!!"]),
            ({}, ["...안에서... 뭔가......!!"]),
        ],
    },
    "ecstasy_M": {
        "start": [({}, ["...입술이... 녹을 것 같아......"])],
    },
    "ecstasy_B": {
        "start": [({}, ["...가슴이... 이상해......!"])],
    },
    "ecstasy_P": {
        "start": [({}, ["......!!", "...나... 나올 것 같아...!"])],
    },
    "ecstasy_A": {
        "start": [({}, ["...뒤에서... 이상해......!!"])],
    },

    # 연쇄 절정 전용 (chain_count > 0일 때 우선 사용)
    "ecstasy_chain": {
        "start": [
            ({"성적절정": 5}, ["...멈... 멈춰... 더 이상... 못...!!!"]),
            ({}, ["...또... 가......!!", "...연속으로... 안 돼...!!"]),
        ],
    },

    # 삽입 중 절정 (pregnancy_check 활성 상태에서 절정)
    "ecstasy_intercourse": {
        "start": [
            ({}, ["...안에서... 느껴져......!!", "...깊이... 오고 있어...!!"]),
        ],
    },
}
```

### 절정 텍스트 선택 우선순위

```
1. ecstasy_intercourse  — 삽입 중 절정 (pregnancy_check 활성)
2. ecstasy_chain        — 연쇄 절정 (chain_count > 0)
3. ecstasy_{category}   — 카테고리별 (ecstasy_V, ecstasy_B 등)
4. ecstasy              — 기본 fallback
```

```python
def get_climax_reaction_key(climax_info, state):
    """절정 묘사 키 결정"""
    # 1. 삽입 중 절정
    if _has_active_intercourse(state):
        key = "ecstasy_intercourse"
        if key in reactions:
            return key

    # 2. 연쇄 절정
    if climax_info.get("is_chain"):
        key = "ecstasy_chain"
        if key in reactions:
            return key

    # 3. 카테고리별
    cat = climax_info.get("category")
    if cat:
        key = f"ecstasy_{cat}"
        if key in reactions:
            return key

    # 4. 기본
    return "ecstasy"
```

### 남성 절정 묘사 (불응기 진입)

P 보유자가 절정 시 추가 묘사:
```python
"ecstasy_P_male": {
    "start": [
        ({}, ["...(거친 숨)... 나왔어......", "...!!"]),
    ],
}
```

### UI 표시

절정 시 기존보다 풍부한 표시:
```
[color=pink]──── 절정 (V) ────[/color]
[세라] ...안에서... 뭔가......!!
[color=pink]연쇄 절정 ×3[/color]
```

- 절정 부위 카테고리 표시
- 연쇄 횟수 강조
- 삽입 중 절정 시 특별 연출

---

## 13. 연쇄 절정 경험치 배율 (Chain Climax Exp)

### 개요
연쇄 절정(여운 중 재절정) 시 감각 경험치 보너스에 배율 적용.
고레벨 감각 달성의 주된 수단.

### 공식

```python
def get_climax_sensation_gain(rebellion, chain_count=0):
    base = max(0, 3 - rebellion // 25)
    chain_mult = 1.0 + min(chain_count, 3) * 0.5
    return max(0, round(base * chain_mult))
```

| chain_count | 배율 | 결과 (반발 0) |
|-------------|------|--------------|
| 0 | ×1.0 | 3 exp |
| 1 | ×1.5 | 4 exp |
| 2 | ×2.0 | 6 exp |
| 3+ | ×2.5 | 7 exp |

연쇄 절정 3회 이상에서 최대 배율. 반발이 높으면 base 자체가 감소.

---

## 14. M 감각 삼키기 게이트 (Swallow Gate)

### 개요
구강 내 사정(swallow_semen) 시 M 감각 레벨에 따라 삼키기/뱉기/흘림/구역질 분기.

### M 레벨별 분기

| M 감각 | 행동 | 반응 키 | 메커니즘 |
|--------|------|---------|---------|
| ≥ 5 | 삼키기 (정상) | `swallow_semen:start` | 구강 정액 제거, 체내 흡수 |
| 3-4 | 뱉기 | `swallow_semen_spit:start` | 구강 제거, 일부 외부(가슴) 적용 |
| 1-2 | 흘림 | `swallow_semen_drip:start` | 절반 제거, 나머지 외부 |
| 0 | 구역질 | `swallow_semen_vomit:start` | 구강 유지, 반발 +2 |

### 상수
```python
SWALLOW_M_THRESHOLD = 5
```

---

## 15. 준비부족 강도 행위 페널티 (Unprepared Penalty)

### 개요
intensity ≥ 3인 행위를 대상 부위 자극이 낮은 상태에서 시도하면 페널티 적용.

### 메커니즘

| 항목 | 값 |
|------|---|
| 적용 조건 | `intensity ≥ 3` and 대상 부위 stim < 30 |
| 효과 배율 | ×0.5 (`UNPREPARED_EFFECT_MULT`) |
| 반발 증가 | +2 (`UNPREPARED_REBELLION`) |
| 경험치 | 미지급 (`suppress_exp=True`) |

### 상수
```python
PREPARATION_THRESHOLD = 30
UNPREPARED_EFFECT_MULT = 0.5
UNPREPARED_REBELLION = 2
```

### 적용 범위
- 즉시형/토글형 행위 모두 적용
- 플레이어 주도 (romance.py) + NPC 주도 (npc_initiative.py) 모두

---

## 16. 사정감 참기 (Hold Back)

### 개요
P 보유 플레이어가 P 자극 80+ 상태에서 사정을 참는 즉시 행위.
확률적 성공/실패 → 실패 시 강제 사정.

### 조건
- `requires_player_anatomy_self: "P"` — P 보유 플레이어만
- P stim ≥ 80 (`HOLD_BACK_P_THRESHOLD`)일 때만 UI에 표시

### 성공 확률 계산

```python
def _calculate_hold_back_chance(player_id, stim_state):
    p_stim = stim_state["stim"].get("P", 0)
    p_sensation = get_sensation_level(player_id, "P")
    chance = 40 - (p_stim - 80) * 2 + p_sensation * 5
    return max(5, min(90, chance))
```

| P stim | P 감각 0 | P 감각 5 | P 감각 10 |
|--------|---------|---------|----------|
| 80 | 40% | 65% | 90% |
| 90 | 20% | 45% | 70% |
| 100 | 0%→5% | 25% | 50% |

### 결과

| 결과 | 처리 |
|------|------|
| 성공 | P stim → 60, 반응 `hold_back_success:start` |
| 실패 | 강제 P 절정 + 삽입 중이면 체내 사정 + 임신 판정, 반응 `hold_back_failure:start` |

### P stim 누적

삽입 토글 활성 중 매 행위 실행 시 P stim 자동 증가:
```python
p_gain = max(3, base_arousal_effect // 2)
```

UI: `참기 (X%)` 버튼으로 현재 성공률 표시.

### pull_out 버그 수정

기존 `is_pull_out_available()`에서 `stim.get("level", 0)` → `stim["stim"].get("P", 0)` 수정.
(항상 0을 반환하여 빼기가 불가능했던 버그)

---

## 17. 캐릭터별 구현 가이드

### Character 클래스 속성 (base.py)

```python
class Character(Unit):
    # 스킨십 반응
    ROMANCE_REACTIONS: dict = None

    # NPC 주도 설정
    INITIATIVE_CONFIG: dict = None
    NPC_INITIATIVE_ACTIONS: list = None
    INITIATIVE_REACTIONS: dict = None

    # 은신 성공 반응
    STEALTH_REACTIONS: dict = None

    # 소음 프로필
    ROMANCE_SOUND_PROFILE: dict = None

    # 발각 반응 (목격자로서)
    ROMANCE_DISCOVERY_REACTIONS: dict = None
```

### 세라 구현 예시 (sera.py)

```python
class Sera(Character):
    # 스킨십 반응 (플레이어 주도)
    ROMANCE_REACTIONS = {
        "hug": {"during": [({}, ["세라가 조용히 안겨 있다."])]},
        "deep_kiss": {"during": [({}, ["세라의 숨결이 거칠어진다."])]},
        "ecstasy": {"start": [({}, ["......!!", "...이상해..."])]},
    }

    # NPC 주도 설정
    INITIATIVE_CONFIG = {
        "arousal_threshold": 70,
        "affection_threshold": 60,
        "cooldown_minutes": 480,
    }

    NPC_INITIATIVE_ACTIONS = [
        ({"성욕": 90, "호감": 50}, [
            {"action": "hug", "duration": 10},
            {"action": "deep_kiss", "duration": 15},
        ]),
        ({}, [{"action": "hug", "duration": 20}]),
    ]

    INITIATIVE_REACTIONS = {
        "start": [({}, ["......", "...가만히 있어."])],
        "escape_fail": [({}, ["...도망가려고?"])],
        "satisfied": [({}, ["...끝이다."])],
    }

    # 은신 성공 반응
    STEALTH_REACTIONS = {
        "text": [
            ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
            ({"호감": 40}, ["......", "...조심해."]),
            ({}, ["......", "...(긴장한 표정)"]),
        ],
        "effects": {"성욕": 5},  # 스릴에 더 흥분
    }

    def on_meet_player(self, player_id):
        """플레이어와 만났을 때"""
        # 첫 만남 이후 NPC 주도 체크
        if self._event_flags.get("first_meet"):
            if self.should_initiate_skinship(player_id):
                self.mark_initiative_cooldown()
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트
        self._event_flags["first_meet"] = True
        return self._run_event_dialog("first_meet", player_id=player_id)
```
