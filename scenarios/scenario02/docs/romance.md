# 연애 시스템 (Romance System)

## 개요

플레이어와 호감도가 높은 NPC 간의 친밀한 상호작용 시스템.

**시스템 구성**:
| 시스템 | 파일 | 설명 |
|--------|------|------|
| **스킨십 시스템** | `romance.py` | 플레이어 주도 친밀 행위 (토글/즉시) |
| **데이트 시스템** | `date.py` | 데이트 요청/종료 + 애정 표현 |
| **NPC 주도 시스템** | `npc_initiative.py` | NPC가 먼저 스킨십 시작 |

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

### 은신 시스템 (들키지 않을 확률)

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

**세라 예시:**
```python
STEALTH_REACTIONS = {
    "text": [
        ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
        ({"호감": 40}, ["......", "...조심해."]),
        ({}, ["......", "...(긴장한 표정)"]),
    ],
    "effects": {"성욕": 5},  # 스릴에 더 흥분
}
```

**밀라 예시:**
```python
STEALTH_REACTIONS = {
    "text": [
        ({"성욕": 50}, ["...어떡해요... 심장이 너무 빨리 뛰어요...", "...(얼굴이 빨개진다)"]),
        ({"호감": 40}, ["...무서웠어요...", "...다행이에요..."]),
        ({}, ["...휴... 다행이에요...", "...(가슴을 쓸어내린다)"]),
    ],
    "effects": {},  # 부끄러워함
}
```

### 행위 정의

#### 즉시형 행위 (INSTANT_ACTIONS)
| 이름 | 시간 | 스태미나 | 효과 | 필요 호감도 |
|------|-----|---------|------|------------|
| 머리 쓰다듬기 | 3분 | 1 | 호감+3 | 40 |
| 뺨 어루만지기 | 2분 | 1 | 호감+2 | 30 |
| 뺨 꼬집기 | 2분 | 1 | 호감+1 | 35 |
| 귀 만지기 | 3분 | 1 | 호감+2, 성욕+1 | 45 |
| 사랑의 속삭임 | 2분 | 1 | 호감+5 | 50 |
| 프렌치 키스 | 5분 | 2 | 호감+3, 성욕+3 | 60 |
| 엉덩이 쓰다듬기 | 3분 | 2 | 호감+1, 성욕+3, 욕망+1 | 70 |
| 음부 쓰다듬기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+2 | 85 |
| 클리토리스 자극 | 5분 | 3 | 성욕+6, 욕망+3 | 90 |

#### 토글형 행위 (TOGGLE_ACTIONS)
| 이름 | 틱당 시간 | 틱당 스태미나 | 효과 | 필요 호감도 |
|------|----------|-------------|------|------------|
| 껴안기 | 5분 | 1 | 호감+3 | 50 |
| 딥키스 | 5분 | 2 | 호감+3, 성욕+3 | 70 |
| 가슴 만지기 | 5분 | 2 | 호감+1, 성욕+4, 욕망+1 | 80 |
| 음부 만지기 | 5분 | 3 | 호감+1, 성욕+5, 욕망+3 | 90 |
| 클리토리스 문지르기 | 5분 | 3 | 성욕+7, 욕망+4 | 95 |

### 절정 시스템 (자극 기반)
- **자극 기반 절정**: 부위별 자극(`stimulation.py`)이 100 도달 시 절정 발생 (성욕 임계값 방식 폐지)
- 절정 시: 성적절정 +1, 성욕 -30 (전액 초기화 대신 일부 감소)
- 절정 부위 감각 경험치 +3 (반발에 의해 억제 가능)
- 여운(afterglow) 상태 진입 → 연쇄 절정 가능
- 캐릭터별 절정 반응 (`ROMANCE_REACTIONS["ecstasy"]`)

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
    "genital_touch": {..., "exp_part": "음부", ...},      # NEW
    "clit_rub": {..., "exp_part": "클리토리스", ...},     # NEW
}

PLAYER_INSTANT_ACTIONS = {
    "head_pat": {..., "exp_part": "머리", ...},
    "french_kiss": {..., "exp_part": "입술", ...},  # deep_kiss와 충돌
    "whisper": {..., "exp_part": None, ...},        # 충돌 없음
    "genital_caress": {..., "exp_part": "음부", ...},     # NEW
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

## 4. 소음 시스템 (Romance Sound)

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

## 5. 발각 반응 시스템 (Discovery Reactions)

### 개요
애정행위 중 제3자에게 발각되었을 때, 목격자의 성격 + 파트너가 누구인지에 따라
다른 대사와 호감도 효과가 적용됨.

### 플로우

#### 플레이어 주도 (romance.py)
```
중단 감지 → set_interrupted_context(partner_id)
         → handle_interruption()
         → 중단 로그 ("XX의 방해로 중단되었다.")
         → pop_to_situation()
         → queue_event("meet") → on_meet_player()
         → get_interrupted_context() → on_romance_discovered()
```

#### NPC 주도 (npc_initiative.py)
```
중단 감지 → handle_npc_initiative_interruption()
         → interrupter.on_romance_discovered(player_id, npc_id)
         → NPC 부끄러움 + 도망
```

### 캐릭터별 발각 반응 (ROMANCE_DISCOVERY_REACTIONS)

```python
ROMANCE_DISCOVERY_REACTIONS = {
    "default": {"text": ["...!"], "effects": {"호감": -3}},
    "sera":    {"text": ["...세라랑?!"], "effects": {"호감": -5}},
}
```

| 캐릭터(목격자) | 성격 톤 | default | 특별 반응 파트너 |
|--------------|---------|---------|-----------------|
| 세라 | 침묵 → 한마디 | 호감-3 | 리나(-5), 밀라(-4) |
| 리나 | 큰 충격, 놀람 | 호감-5 | 세라(-8), 밀라(-6) |
| 밀라 | 조용히 상처 | 호감-3 | 세라(-4), 리나(-5) |
| 유키 | 얼어붙음 | 호감-3 | 엘라(-8) |
| 엘라 | 차갑게 한마디 | 호감-3 | 유키(-10), 세라(-4) |

### 관련 메서드 (base.py)
- `on_romance_discovered(player_id, partner_id)` → Generator 또는 None
- `_romance_discovery_dialog(player_id, reaction)` → 대사 + effects 적용

### 컨텍스트 전달 (romance.py)
- `set_interrupted_context(partner_id)` — 1회성 저장
- `get_interrupted_context()` — 소비 후 None 리셋

---

## 6. 감각 시스템 (Sensation System)

### 개요

부위별 경험치(`경험:{부위}`)를 M/B/A/V/C/P 감각 카테고리에 매핑하여
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
| 귀 | None | 비성적 |
| 뺨 | None | 비성적 |
| 머리 | None | 비성적 |

### 감각 레벨 계산

```python
def get_sensation_level(unit_id, category):
    """경험치 합산 기반 감각 레벨 (0-10)"""
    total_exp = sum(
        morld.get_unit_prop(unit_id, f"경험:{part}") or 0
        for part, cat in SENSATION_MAP.items()
        if cat == category
    )
    return min(10, total_exp // 5)
```

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
- 감각 레벨이 0 초과인 카테고리만 표시 (M/B/A/V/C/P 순서).

---

## 7. 욕망 시스템 (Desire System)

### 개요

관계별 욕망(`관계:{name}:욕망`) prop으로 NPC에 대한 성적 욕구를 추적.
스킨십 행위의 effects에 `"욕망"` 키가 있으면 자동 반영됩니다.

### Prop 구조

`관계:{대상이름}:욕망` — 관계별 A-B 쌍 (호감/애정과 동일 패턴)

### 성욕 자연 상한 (Dynamic Arousal Cap)

욕망이 높을수록 성욕의 자연 상한이 상승:

```python
def _get_arousal_cap(unit_id):
    max_desire = max(관계:*:욕망 props)
    return min(100, 50 + max_desire * 0.5)
```

| 최고 욕망 | 성욕 자연 상한 |
|----------|--------------|
| 0 | 50 |
| 50 | 75 |
| 100 | 100 |

### NPC 주도 조건

`INITIATIVE_CONFIG`에 `desire_threshold` 추가:
- 욕망이 임계값 이상이어야 NPC 주도 발동
- 현재 모든 캐릭터 0 (체크 안 함)

---

## 8. 이중 경로 잠금 해제 (Dual-Path Unlock)

### 개요

액션의 `affection_req`(필요 호감도)를 애정 경로 **또는** 육욕 경로로 해금할 수 있는 시스템.
욕망이 높으면 호감도가 부족해도 NPC가 마지못해 허락합니다.

### 유효 호감 요구치 공식

```python
def get_effective_affection_req(req, desire=0, submission=0):
    """욕망/복종에 의한 호감 요구치 할인"""
    desire_discount = min(req * 0.3, desire * 0.3)
    submission_discount = min(req * 0.3, submission * 0.3)
    total = min(req * 0.5, desire_discount + submission_discount)
    return max(20, req - total)
```

**할인 규칙:**
- 욕망: 최대 30% 할인
- 복종: 최대 30% 할인 (디버그 전용 — 자연 증가 미구현)
- 합산: 최대 50% 할인
- 절대 최소: 20

### 할인 테이블 예시

| 액션 (req) | 욕망 0 | 욕망 50 | 욕망 100 | 욕망 100+복종 100 |
|-----------|--------|---------|----------|-----------------|
| breast_touch (80) | 80 | 65 | 56 | 40 |
| genital_caress (85) | 85 | 70 | 60 | 43 |
| genital_touch (90) | 90 | 75 | 63 | 45 |
| clit_rub (95) | 95 | 80 | 67 | 48 |

### 적용 위치 (6곳)

| 파일 | 위치 | 설명 |
|------|------|------|
| romance.py | render_romance_ui() 토글 표시 | 플레이어 주도 토글 해금 |
| romance.py | render_romance_ui() 즉시 표시 | 플레이어 주도 즉시 해금 |
| npc_initiative.py | render_npc_initiative_ui() | NPC 주도 중 플레이어 즉시 표시 |
| npc_initiative.py | get_available_npc_actions() | NPC 토글 선택 조건 |
| date.py | 데이트 중/외 애정 표현 | Phase C에서 적용 예정 |

### UI 색상 구분

| 해금 경로 | 색상 | 의미 |
|----------|------|------|
| 애정 해금 (호감 >= req) | 기본색 | 정상 해금 |
| 욕망 해금 (호감 < req, 할인으로 해금) | 핑크 (`[color=pink]`) | 마지못해 허락 |

### 헬퍼 함수 (romance.py)

```python
def is_action_available(partner_id, player_id, action_def):
    """액션 해금 여부 (이중 경로 체크)"""

def get_submission_key(player_id):
    """복종 prop 키 생성"""

def is_desire_unlocked(affection, action_def, desire, submission=0):
    """욕망/복종에 의한 해금인지 (핑크색 표시용)"""
```

### INITIATIVE_ACTION_FILTERS context

base.py `get_allowed_initiative_actions()`의 context에 `"욕망"`, `"복종"` 포함:
```python
context = {
    "성욕": ..., "호감": ..., "반발": ...,
    "욕망": props.get(f"관계:{player_name}:욕망", 0),
    "복종": props.get(f"관계:{player_name}:복종", 0),
}
```

### 복종 시스템 (디버그 전용)

- **Prop**: `관계:{name}:복종` — 디버그 모드에서 +20/-20 수동 조정
- **할인 공식**: `get_effective_affection_req()`에 submission 파라미터 활성화 완료
- **UI**: 복종 > 0일 때만 스킨십 UI 헤더에 `복종: N` 표시
- **자연 증가**: 미구현 (향후 리더십/명령 수행 시 증가 예정)
- **date.py**: 이중 경로 미적용 (향후 적용 예정)

---

## 9. 사적인 대화 시스템 (진척도)

### 개요
호감도가 높아지면 NPC와 점점 깊은 대화를 나눌 수 있는 시스템.
대화할 때마다 "진척도"가 증가하고, 진척도에 따라 새로운 대화가 해금됩니다.

### 진척도 구조

| 진척도 | 필요 호감 | 대화 내용 | 일회성 |
|--------|----------|----------|--------|
| 1 | 50 | 자신에 대한 이야기 (소개, 가족) | ✅ |
| 2 | 60 | 좋아하는 것 (취미, 기호) | ✅ |
| 3 | 70 | 과거 이야기 (기억, 트라우마) | ✅ |

### TALK_RULES 설정

```python
TALK_RULES = [
    # 특수 상황 (최우선)
    ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

    # 진척도별 사적인 대화 (플래그로 일회성 체크)
    ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
    ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
    ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

    # 호감도 기반 (진척도 증가 로직 포함)
    ({"호감": 70}, "_talk_friendly_high"),
    ({"호감": 50}, "_talk_friendly_mid"),

    # 기본값
    ({}, {"pages": ["기본 대사..."]}),
]
```

### 진척도 증가 메서드

```python
def _talk_friendly_high(self, context):
    """호감도 70 이상 - 진척도 증가 기회"""
    name = context.get("name", self.name)
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    # 진척도 증가 (최대 3)
    props = morld.get_unit_props(self.instance_id)
    progress_key = f"관계:{player_name}:진척도"
    current_progress = props.get(progress_key, 0) if props else 0

    if current_progress < 3:
        morld.set_unit_prop(self.instance_id, progress_key, current_progress + 1)

    yield morld.dialog([f"[{name}]", "호감도 높은 대사..."])
```

### 사적인 대화 메서드 (일회성)

```python
def _talk_progress_1(self, context):
    """진척도 1 - 자신에 대한 이야기 (일회성)"""
    name = context.get("name", self.name)
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    # 플래그 체크 (이미 들었으면 일반 대화)
    flag_key = f"대화:{player_name}:진척도1"
    props = morld.get_unit_props(self.instance_id)
    if props and props.get(flag_key):
        yield morld.dialog([f"[{name}]", "이미 들은 후 대사..."])
        return

    # 플래그 설정 및 사적인 이야기
    morld.set_unit_prop(self.instance_id, flag_key, 1)
    yield morld.dialog([
        f"[{name}]",
        "자신에 대한 이야기...",
        "가족 소개...",
    ])
```

### 캐릭터별 대화 내용

| 캐릭터 | 진척도 1 (자신 소개) | 진척도 2 (좋아하는 것) | 진척도 3 (과거) |
|--------|---------------------|----------------------|---------------|
| **세라** | 사냥 담당, 혼자 있는 게 편함 | 숲, 사냥, 고요함 | 혼자 눈을 뜸, 기억 없음, 밀라/리나 만남 |
| **밀라** | 살림 담당, 세라/리나를 가족처럼 | 요리, 사람들이 맛있게 먹는 것, 티타임 | 저택에서 혼자 깨어남, 세라/리나 발견 |
| **리나** | 채집/빨래 담당, 세라/밀라 언니 | 채집, 숲, 베리잼, 사람들과 놀기 | 혼자서 무서웠음, 언니들 만남 |
| **유키** | 엘라와 둘이 삶, 엘라가 돌봐줌 | 책, 조용한 것, 다른 세계 | 혼자서 무서웠음, 엘라 만남 |
| **엘라** | 유키를 지킴, 그게 자신의 역할 | 조용한 밤, 유키가 웃는 것 | 도시에서 혼자 깨어남, 유키 발견 |

### 캐릭터별 말투 스타일

| 캐릭터 | 스타일 | 예시 |
|--------|--------|------|
| **세라** | 무뚝뚝, 짧은 문장 | "......", "...알고 싶지도 않아." |
| **밀라** | 다정, 존댓말 | "~해요", "~네요", "괜찮으세요?" |
| **리나** | 활발, 반말 | "~야!", "에헤헤~", "좋아좋아!" |
| **유키** | 수줍음, 말줄임표 많음 | "...네...", "...~요...", "...(고개를 숙인다)" |
| **엘라** | 냉정, 명령조 | "...~다.", "...~냐.", "...간단히 말해라." |

### 공통 스토리 설정
모든 NPC는 "기억이 없다"는 공통점을 가짐:
- 어느 날 혼자 눈을 뜸
- 누구인지, 왜 여기 있는지 모름
- 다른 NPC를 만나 함께 살기로 함
- 플레이어도 같은 상황임을 알게 됨

---

## 10. 캐릭터별 구현 가이드

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

## 12. 관계 라벨 시스템

### 개요
호감 + 욕망 기반으로 관계 상태를 라벨로 표시. `애정` prop 제거 후 도입.

### 라벨 매핑

| 호감 | 욕망 | 라벨 |
|------|------|------|
| < 50 | < 40 | 타인 |
| ≥ 50 | < 40 | 친구 |
| < 50 | ≥ 40 | 정욕 |
| ≥ 50 | ≥ 40 | 애인 |

### Prop 변경 (v0.2.2)
- **제거**: `관계:{name}:애정` — 호감에 통합
- **추가**: `관계:{name}:반발` (0-100) — 관계별 저항/반발 수치
- **유지**: 호감, 욕망, 복종

### 반발 시스템
- 자극 계산 시 반발이 높으면 자극 증가량 감소: `max(0.2, 1.0 - rebellion * 0.008)`
- 절정 시 감각 경험치 억제: `max(0, base_gain - rebellion // 25)`
- UI: 반발 > 0일 때만 표시

---

## 13. 성별 시스템 (gender.py)

### 개요
캐릭터의 성별에 따라 보유 감각 카테고리를 결정.

### 성별별 보유 감각

| 성별 | 감각 카테고리 |
|------|-------------|
| male | M, B, A, P |
| female | M, B, A, V, C |
| futanari | M, B, A, V, C, P |
| asexual | M |

### API
- `get_gender(unit_id)` → Character.type 기반 성별 반환
- `has_anatomy(unit_id, category)` → 해당 카테고리 보유 여부
- `get_anatomy(unit_id)` → 보유 감각 카테고리 frozenset

### 현재 캐릭터
Player=male, 모든 NPC=female. P감각은 male NPC 추가 시 활용.

---

## 14. 자극 시스템 (stimulation.py)

### 개요
부위별 자극 수치를 관리하여 절정을 발생시키는 세션 스코프 시스템.
기존 성욕 임계값(100) 방식을 대체.

### 핵심 특성
- **세션 스코프**: romance 세션 state dict 안에만 존재, prop 아님
- **부위별 자극**: MBAVCP 카테고리별 독립 자극 수치 (0-100)
- **절정**: 자극이 100 도달 시 발생, 해당 카테고리 자극 리셋
- **여운 (afterglow)**: 절정 후 일시적 상태, 행위마다 감소
- **연쇄 절정**: 여운 중 재절정 시 자극 증폭 (×1.5)

### 상수

| 상수 | 값 | 설명 |
|------|---|------|
| STIM_MAX | 100 | 절정 발생 임계값 |
| AFTERGLOW_INITIAL | 50 | 절정 시 부여되는 여운 초기값 |
| AFTERGLOW_DECAY | 10 | 행위 1회당 여운 감소량 |
| CHAIN_AMPLIFIER | 1.5 | 연쇄 절정 시 자극 배율 |
| CLIMAX_AROUSAL_REDUCTION | 30 | 절정 시 성욕 감소량 |
| CLIMAX_SENSATION_GAIN | 3 | 절정 부위 경험치 보너스 |

### 자극 증가량 계산

```python
def calc_gain(base, sensation_level, rebellion, afterglow):
    gain = base * (1.0 + sensation_level * 0.15)
    gain *= max(0.2, 1.0 - rebellion * 0.008)  # 반발 감소
    if afterglow > 0:
        gain *= CHAIN_AMPLIFIER  # 여운 중 증폭
    return max(1, round(gain))
```

- `base`: 행위의 기본 성욕 효과 값
- `sensation_level`: 해당 부위 감각 레벨 (0-10)
- `rebellion`: 반발 수치 (0-100)
- `afterglow`: 현재 여운 수치

### 절정 처리
1. 해당 카테고리 자극 리셋 (0)
2. 연쇄 판정 (여운 중이면 연쇄)
3. 여운 진입/갱신 (afterglow = 50)
4. 성욕 -30 (전액 초기화 대신)
5. 성적절정 +1
6. 절정 부위 감각 경험치 +3

### UI 표시
```
자극: M:0 B:15 V:72  [여운 ×2]  절정: 1
```
- 대상 성별 기반으로 해당 카테고리만 표시
- 여운 중: `[여운]` + 연쇄 횟수 표시
- 절정 누적 횟수 표시

---

## 15. 구현 상태

### 완료된 기능

| 기능 | 파일 | 상태 |
|------|------|------|
| 스킨십 UI | romance.py | ✅ 완료 |
| 토글/즉시형 행위 | romance.py | ✅ 완료 |
| 경험치 시스템 | romance.py | ✅ 완료 |
| 절정 시스템 | romance.py | ✅ 완료 |
| 중단 이벤트 (이벤트 큐 연동) | romance.py | ✅ 완료 |
| 캐릭터별 반응 | 전체 NPC | ✅ 완료 |
| 데이트 요청/종료 | date.py | ✅ 완료 |
| 데이트 중 애정 표현 | date.py | ✅ 완료 |
| 데이트 외 애정 표현 | date.py | ✅ 완료 |
| 애정 표현 '#' 처리 | date.py, player.py | ✅ 완료 |
| NPC 주도 기본 구조 | npc_initiative.py | ✅ 완료 |
| 빠져나가기 시스템 | npc_initiative.py | ✅ 완료 |
| NPC 주도 트리거 | base.py, 전체 NPC | ✅ 완료 |
| 행위 마스킹 (exp_part) | npc_initiative.py | ✅ 완료 |
| 캐릭터별 액션 필터 | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 1) | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 2) | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 3) | 전체 NPC | ✅ 완료 |
| 은신 시스템 (플레이어 주도) | romance.py | ✅ 완료 |
| 은신 시스템 (NPC 주도) | npc_initiative.py | ✅ 완료 |
| 제3자 방해 이벤트 (NPC 주도) | npc_initiative.py | ✅ 완료 |
| 캐릭터별 은신 반응 | base.py, 전체 NPC | ✅ 완료 |
| 소음 시스템 (흥분도 3단계) | romance.py, npc_initiative.py, sound.py | ✅ 완료 |
| 캐릭터별 소음 프로필 | 전체 NPC (ROMANCE_SOUND_PROFILE) | ✅ 완료 |
| 발각 반응 시스템 | base.py (on_romance_discovered) | ✅ 완료 |
| 캐릭터별 발각 반응 | 전체 NPC (ROMANCE_DISCOVERY_REACTIONS) | ✅ 완료 |
| 중단 액션 로그 | romance.py ("XX의 방해로 중단되었다.") | ✅ 완료 |
| 감각 시스템 (M/B/A/V/C) | romance.py (SENSATION_MAP, get_sensation_level) | ✅ 완료 |
| 감각 보정 (성욕 효과) | romance.py (calculate_effects) | ✅ 완료 |
| 욕망 prop 인프라 | romance.py (apply_effects), needs.py (동적 cap) | ✅ 완료 |
| NPC 주도 욕망 임계값 | base.py (desire_threshold) | ✅ 완료 |
| V/C 부위 액션 (4종) | romance.py, npc_initiative.py | ✅ 완료 |
| 이중 경로 잠금 해제 | romance.py, npc_initiative.py (욕망 할인) | ✅ 완료 |
| 욕망 효과 활성화 | romance.py, npc_initiative.py (butt_caress/breast_touch 욕망+1) | ✅ 완료 |
| FILTERS context 욕망 | base.py (get_allowed_initiative_actions) | ✅ 완료 |
| 복종 디버그 조정 | base.py (debug_submission_up/down), 전체 NPC | ✅ 완료 |
| 복종 이중 경로 | romance.py (is_action_available + submission) | ✅ 완료 |
| 관계 라벨 시스템 | romance.py | ✅ 완료 |
| 반발 시스템 | romance.py, base.py | ✅ 완료 |
| 성별 시스템 | gender.py | ✅ 완료 |
| 자극 시스템 (부위별) | stimulation.py, romance.py, npc_initiative.py | ✅ 완료 |
| 자극 UI (여운/연쇄/절정) | romance.py, npc_initiative.py | ✅ 완료 |
| 애정 prop 제거 (호감 통합) | romance.py, npc_initiative.py, date.py, 5캐릭터 | ✅ 완료 |

### 지원 캐릭터

| 캐릭터 | 스킨십 반응 | NPC 주도 | 사적인 대화 | 은신 반응 | 소음 | 발각 반응 | 특징 |
|--------|-----------|----------|-----------|----------|------|---------|------|
| 세라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 다정/포근 - 연애 저돌적 |
| 리나 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 활발 - 연애엔 수줍음 |
| 유키 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 매우 수줍음 |
| 엘라 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 냉정함 |

### 미구현/선택적 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| ~~캐릭터별 목격 반응~~ | ~~목격자 × 파트너 분기~~ | ✅ 완료 (ROMANCE_DISCOVERY_REACTIONS) |
| 합류 이벤트 | 호감 높은 NPC 합류 | 취소 |
| ~~성적흥분 상한 클램프~~ | ~~동적 cap 초과 시 즉시 클램프~~ | ✅ 완료 (needs.py) |
| 복수 파트너 UI | 3인 이상 연애 | 취소 |
| ~~자위 행동~~ | ~~NPC self-comfort think 핸들러~~ | ✅ 완료 (think/__init__.py) |
| ~~NPC→플레이어 탐색~~ | ~~고욕망+고관계+고성욕 시 플레이어 찾기~~ | ✅ 완료 (think/__init__.py) |
| ~~감각 기반 주도 제한~~ | ~~INITIATIVE_SENSATION_REQS 필터~~ | ✅ 완료 (base.py) |
| ~~자위 발각~~ | ~~on_meet 시 자위 중 발각 처리~~ | ✅ 완료 (base.py) |
| ~~은밀 장소 판정~~ | ~~length 기반 은밀 장소 선정~~ | ✅ 완료 (length 기반) |
| ~~화장실 프라이버시~~ | ~~ROOM_PRIVACY_CONFIG "화장실" 추가~~ | ✅ 완료 (5캐릭터) |
| NPC-NPC 대화 | 사회욕 기반 대화 시스템 + describe text | 미구현 |
| NPC-NPC 행위 발각 | 행위 중 플레이어 개입 이벤트 | 미구현 |
| NPC-NPC 자위 발각 상호작용 | 연인 NPC 발각 시 상호 애정 행위 전환 | 미구현 (현재: NPC 방해 → 짧은 쿨다운) |
| ~~V 부위 액션~~ | ~~Vaginal 카테고리 액션 추가~~ | ✅ 완료 (V/C 4종 추가) |
| ~~복종 시스템~~ | ~~관계:{name}:복종 prop + 이중 경로 submission~~ | ✅ 디버그 전용 (자연 증가 미구현) |

---

## 16. 관련 morld API

| API | 설명 | 사용처 |
|-----|------|--------|
| `get_units_at_location(r, l)` | Location의 유닛 ID 목록 | 제3자 체크 |
| `advance_time_des(millis)` | DES 시뮬레이션 (think + 이동 + 이벤트) | 행위 시간 경과 |
| `modify_prop(id, prop, delta)` | prop 상대값 변경 | 호감도/애정 증감 |
| `add_unit_mood(id, mood)` | mood 추가 | 부끄러움 등 |
| `set_npc_job(id, action, dur, target)` | NPC Job 설정 | flee, follow |
| `set_unit_prop(id, prop, value)` | prop 절대값 설정 | can: props |

---

## 17. 파일 구조

```
scenarios/scenario02/python/
├── romance.py              # 스킨십 시스템 (플레이어 주도)
├── date.py                 # 데이트 시스템 + 애정 표현
├── npc_initiative.py       # NPC 주도 스킨십 시스템 (행위 마스킹, 캐릭터 필터)
├── gender.py               # 성별 시스템 (anatomy 매핑)
├── stimulation.py           # 자극 시스템 (절정/여운/연쇄)
├── assets/
│   ├── base.py             # Character 클래스 (ROMANCE_REACTIONS, INITIATIVE_*, STEALTH_REACTIONS)
│   │                       # - should_initiate_skinship()
│   │                       # - get_initiative_reaction()
│   │                       # - get_allowed_initiative_actions()
│   │                       # - get_stealth_success_reaction()
│   │                       # - apply_stealth_success_effects()
│   └── characters/
│       ├── player.py       # 플레이어 (can: props)
│       ├── sera.py         # 세라 - 무뚝뚝/거친, 연애 쑥맥
│       ├── mila.py         # 밀라 - 다정/포근, 연애 저돌적
│       ├── lina.py         # 리나 - 활발, 연애엔 수줍음
│       ├── yuki.py         # 유키 - 매우 수줍음
│       └── ella.py         # 엘라 - 냉정함
└── think/
    └── __init__.py         # BaseAgent (STAY_SCHEDULE, push/pop)
```
