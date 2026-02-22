# 애정 행위 시스템 (Romance Actions)

## 개요

플레이어/NPC 간 친밀한 신체 접촉 행위를 처리하는 시스템.
스킨십, 데이트, NPC 주도, 감각/자극, 탈의/노출, 은신/발각, 소음 등을 포함.

**시스템 구성**:
| 시스템 | 파일 | 설명 |
|--------|------|------|
| **스킨십 시스템** | `romance.py` | 플레이어 주도 친밀 행위 (토글/즉시) |
| **행위 정의** | `romance_actions.py` | 행위 데이터 + 공유 상수 |
| **핵심 로직** | `romance_core.py` | 공유 함수 (25+) |
| **동작 모드** | `romance_mode.py` | 합의/강제/무의식/시간정지 |
| **UI 렌더링** | `romance_ui.py` | 연애 화면 텍스트 생성 |
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
- **4가지 동작 모드**: 합의/강제/무의식/시간정지 (→ [21. 동작 모드 시스템](#21-동작-모드-시스템-romance_modepy))

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
| genital_caress | 음부 쓰다듬기 | 5분 | 3 | 호감+1, 성욕+5, 욕망+3 | 90 | 즉시형 (INSTANT_ACTIONS) |
| clit_rub | 클리토리스 문지르기 | 5분 | 3 | 성욕+7, 욕망+4 | 95 | exposure_bonus: lower |
| clit_lick | 클리토리스 핥기 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |
| cunnilingus | 커닐링구스 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |
| finger_insertion | 손가락 삽입 | 5분 | 3 | 성욕+7, 욕망+4, 복종+1 | 95 | **신규**, requires_exposure: lower |
| penis_touch | 음경 만지기 | 5분 | 3 | 호감+1, 성욕+5, 욕망+3 | 90 | exposure_bonus: lower |
| penis_rub | 음경 문지르기 | 5분 | 3 | 성욕+7, 욕망+4 | 95 | exposure_bonus: lower |
| fellatio | 펠라치오 | 5분 | 3 | 성욕+8, 욕망+4 | 95 | **신규**, requires_exposure: lower |

#### 부위별 행위 요약

| 부위 (카테고리) | 즉시형 | 토글형 | 삽입 관련 | 합계 |
|----------------|--------|--------|----------|------|
| 입술 (M) | 입술 핥기, 프렌치 키스 | 딥키스, 혀 섞기 | — | 4 |
| 가슴 (B) | 가슴 쓰다듬기, 유두 자극 | 가슴 만지기, 가슴 주무르기, 가슴 빨기 | — | 5 |
| 엉덩이 (A) | 엉덩이 쓰다듬기, 항문 자극 | 엉덩이 주무르기 | 항문 삽입(즉시) | 4 |
| 음부 (V) | 음부 쓰다듬기, 삽입(즉시) | 커닐링구스, 손가락 삽입 | — | 4 |
| 클리토리스 (C) | 클리토리스 자극 | 클리토리스 문지르기, 클리토리스 핥기 | — | 3 |
| 음경 (P) | 음경 쓰다듬기, 음경 자극 | 음경 만지기, 음경 문지르기, 펠라치오 | — | 5 |
| 얼굴/목 (F) | 목 키스, 귀 만지기, 뺨 어루만지기, 뺨 꼬집기 | — | — | 4 |
| 삽입 전용 | thrust_stop, withdraw, thrust_deep 등 | thrust_gentle/normal/rough | — | 6+ |
| 성인용품/결박 | 결박, 결박 해제, 성인용품 장착/해제, 강제 투여, 채찍질 | — | — | 6 |

#### 성인용품/결박 액션 (INSTANT_ACTIONS)

> 상세: [adult-toys.md](adult-toys.md) 참조

| ID | 이름 | 시간 | 스태미나 | 효과 | 비고 |
|----|------|------|---------|------|------|
| restrain_partner | 결박 | 2분 | 2 | 반발+3, 복종+2 | 인벤토리 restraint 필요, 저항 체크 |
| unrestrain_partner | 결박 해제 | 1분 | 0 | — | |
| equip_toy_partner | 성인용품 장착 | 2분 | 1 | — | 인벤토리 adult_toy 필요, 저항 체크 |
| remove_toy_partner | 성인용품 해제 | 1분 | 0 | — | |
| force_feed | 강제 투여 | 1분 | 1 | — | 인벤토리 medicine 필요, 입 자유 필요 |
| use_whip | 채찍질 | 2분 | 2 | 반발+3, 복종+2, 성욕+2 | 채찍 장착 필요 |

#### 행위 차단 (결박/삽입물)

- `결박:입` → 구강 사용 행위 (펠라치오, 딥키스 등) 차단
- `삽입물:{부위}` → 해당 오리피스 삽입 행위 차단
- 결박 상태 → 강제 모드 탈출 불가

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

## 2-b. 가벼운 애정 행위 (CASUAL_ACTIONS)

> `assets/base.py` — 포커스 메뉴에서 직접 실행. 로맨스 세션 밖.

### 행위 목록

| action_type | 이름 | 호감 조건 | 욕망 조건 | 성욕 상승 |
|-------------|------|----------|----------|----------|
| `casual_kiss` | 가벼운 키스 | 60 | 50 | 5 |
| `casual_breast` | 가슴 만지기 | 70 | 60 | 10 |
| `casual_butt` | 엉덩이 만지기 | 70 | 60 | 8 |
| `casual_genital` | 음부 만지기 | 80 | 70 | 15 |
| `casual_penis` | 음경 만지기 | 80 | 70 | 15 |

해금 조건: 호감 OR 욕망 중 하나 이상 충족. 성별 필터 적용 (female→casual_genital, male→casual_penis).

### 성욕/절정 영향

NPC의 현재 성욕 수치에 따라 효과가 증폭됨:

| NPC 성욕 | 성욕 상승 배율 |
|----------|--------------|
| 0~39 | ×1.0 (기본) |
| 40~69 | ×1.2 |
| 70+ | ×1.5 |

절정 게이지(`상태:절정`)에도 소폭 기여:
- 기본: `arousal_gain / 3` (최대 5)
- NPC 성욕 ≥ 40일 때: ×1.5 추가 보너스

### 반응 스타일

| 조건 | 스타일 | 설명 |
|------|--------|------|
| 욕망 ≥ 70 | `addicted` | 중독적 반응 |
| 호감 ≥ 80 | `flirty` | 설레는 반응 |
| 그 외 | `default` | 기본 반응 |

캐릭터별 `CASUAL_REACTIONS` dict로 스타일별 텍스트 오버라이드.

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

### 플레이어 행동 제한 (NPC 주도 중)

NPC 주도 모드에서 호감 < 80 (`NPC_INITIATIVE_CONSENT_THRESHOLD`)일 때,
플레이어의 **능동적 행위**에 확률 기반 차단 판정 발생.

#### 행위 분류: 수동 vs 능동

**수동 행위** (`passive_in_npc_initiative: True`) — 항상 허용:
- `hold_back`, `ejaculate` — 자기 절제
- `sync_thrust` — NPC 리듬 맞추기
- `beg` — 애원하기 (NPC 주도 전용)
- `swallow_semen_*` — 정액 삼키기류
- `undress_upper`, `undress_lower` — 탈의

**능동 행위** — 차단 대상 (위 목록에 없는 모든 즉시 행위):
- 삽입 (`vaginal_insert`, `anal_insert`)
- 터치/애무 (`breast_touch`, `clit_rub` 등)
- 키스류 (`kiss`, `deep_kiss`, `french_kiss` 등)

#### 차단 확률

```python
NPC_BLOCK_BASE_CHANCE = 0.85        # 기본 85% 차단
NPC_BLOCK_STRENGTH_BONUS = 0.05     # 근력 1당 -5%
NPC_BLOCK_BODY_BONUS = {
    "왜소": 0.05,    # 오히려 막기 쉬움
    "보통": 0.0,
    "장신": -0.05,
    "거구": -0.15,
}
NPC_BLOCK_MIN_CHANCE = 0.30         # 최소 차단 확률
NPC_BLOCK_MAX_CHANCE = 0.95         # 최대 차단 확률
```

- 호감 ≥ 80: 합의 전환 → 차단 없음
- 차단 성공: NPC 반응 텍스트 + 턴 소비 (스태미나 -1)
- 차단 실패: 행위 정상 진행

#### UI 표시

- 능동 행위: `[color=yellow]행위이름[/color] [color=gray](제지 가능)[/color]`
- 수동 행위: 일반 색상 표시

#### 톤 템플릿 키

| 키 | 설명 |
|---|---|
| `npc_block_player` | NPC가 플레이어 행위 차단 시 반응 |
| `beg` | 플레이어 애원 시 NPC 반응 |

#### "애원하기" 즉시 행위 (beg)

NPC 주도 모드 전용 즉시 행위 (`npc_initiative_only: True`):

| 항목 | 값 |
|------|---|
| 시간 | 3분 |
| 스태미나 | 0 |
| 효과 | NPC 성욕 +5 |
| 특수 | `beg_boost` 에스컬레이션 유도 |

### NPC 여운 상태 체감 (Afterglow)

절정 후 NPC의 여운(afterglow) 상태가 UI와 반응에 반영됩니다.

#### 여운 UI 표시

```
[color=pink]여운 (80%)[/color]
```

afterglow × 2 = 퍼센트 표시 (50 → 100%, 10 → 20%).

#### 여운 중 행위 반응

afterglow > 0일 때 행위 시 강도별 추가 반응 텍스트:

| 조건 | 톤 템플릿 키 | 설명 |
|------|-------------|------|
| afterglow ≥ 40 | `afterglow_sensitive` | 절정 직후 극도 민감 |
| afterglow ≥ 20 | `afterglow_trembling` | 중간 여운, 여전히 떨림 |
| afterglow < 20 | `afterglow_fading` | 여운 사라져감 |

#### 여운 종료 반응

`tick_afterglow()`가 `"ended"` 반환 시 `afterglow_end` 반응 1회 출력.

#### NPC 주도 여운 행동

afterglow > 0일 때 `_npc_auto_advance()`에서:
- NPC는 새 행위를 선택하지 않음 (기존 토글만 유지)
- 자동 삽입 시도 안 함

적용 위치: `romance.py` (플레이어 주도) + `npc_initiative.py` (NPC 주도) 모두.

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
- **여운 (afterglow)**: 여성 절정 후 일시적 상태, 행위마다 감소. 여운 중 행위 시 강도별 반응, 종료 시 1회 반응
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

### 여운 감소 및 종료 (tick_afterglow)

`tick_afterglow(state)` — 매 행위 턴마다 호출:
- afterglow > 0이면 -10 감소
- afterglow가 0으로 전이 시 `"ended"` 반환 → 여운 종료 반응 트리거
- 여운 종료 시 `chain_count` 리셋

여운 중 행위 시 강도별 추가 반응 (→ [Section 3: NPC 여운 상태 체감](#npc-여운-상태-체감-afterglow)).

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
- **체력** (`stamina`, `initial_stamina`, `max_stamina`): 남은 HP + 초기값 + 최대값
- **경과시간**: 세션 누적
- **감지 기록** (`checked_npcs`): 중복 판정 방지

### 메커니즘

`yield from` 체이닝 — 현재 세션 dialog 종료 후 반대편 시스템의 제너레이터 실행:

```python
# romance.py → npc_initiative.py
if state.get("switch_to") == "npc":
    preserved = extract_preserved(state)
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

### 옷 강탈 (Clothing Loot)

탈의 후 NPC 인벤토리에 남아있는 **장착 해제된 의류**를 플레이어가 가져갈 수 있음.

**즉시 행위 정의** (`romance_actions.py`):
```python
"loot_clothing": {
    "name": "옷 강탈", "time": 1분, "stamina": 1,
    "effects": {}, "affection_req": 0, "loot": True,
}
```

**동작 흐름**:
1. 탈의 행위로 옷 벗기기 → 아이템은 NPC 인벤토리에 잔류 (unequipped)
2. "옷 강탈" 버튼 표시 (강탈 가능 의류 있을 때만)
3. 클릭 → 자동으로 1개 선택 → NPC → 플레이어 인벤토리 이동
4. 인벤토리 풀이면 바닥 드롭 (`safe_give_item`)

**헬퍼 함수** (`romance_core.py`):
- `get_next_loot_item(unit_id)` — 인벤토리에서 장착 해제된 의류 탐색
- `perform_loot(source_id, item_id, target_id)` — 아이템 이동

**통상 모드 강탈** (`assets/base.py`):

기절(`is_npc_fainted`) 또는 결박(`is_restrained`) 상태의 NPC에게서 **장착 중인 의류**를 강탈 가능.
수면 중인 NPC는 깨어날 수 있으므로 불가.

- 포커스 메뉴에 "옷 강탈" 동적 추가 (`_add_loot_clothing_action`)
- 클릭 → 장착 의류 선택 → 장착 해제 + 인벤토리 이동

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

우선순위: 현재 위치 → 침실(`bed_owner` prop 탐색) → 화장실(`action:toilet` prop 탐색) → region 내 가장 가까운 후보.

### NPC 자위 (Self-Comfort)

Tier 4 comfort에 위치 (배변 → 피로 → **성욕** → 목욕 → 수면).

- 조건: `arousal ≥ self_comfort_threshold` + 2시간 쿨다운
- 우선순위: 플레이어 탐색 > 자위
- 은밀 장소: `length ≤ self_comfort_max_length` + 실내 + 혼자 + 저오염
- Phase: idle → going → performing (15분 job "자위") → finishing (결과 확인)
- **혼자일 때**: arousal -50, 정상 쿨다운 2시간 (성인용품 사용 시: -70)
- **NPC 발각**: arousal 감소 없음, 짧은 쿨다운 30분 (재시도 유도)
- **플레이어 발각**: SELF_COMFORT_DISCOVERY_REACTIONS 반응
- Job 이름: 이동 중 "이동" (발각 안 됨), 수행 중 "자위" (발각 대상)
- **성인용품 자동 사용**: `_try_use_toy()` — 욕망 확률 + 캐릭터 선호 + 감각 가중 랜덤 선택 (→ [adult-toys.md](adult-toys.md#7-npc-자위-연동))

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

### 정액 연동

NPC 자위 시 P anatomy 캐릭터는 정액 소모 (→ 정액 시스템 참조):
- **idle 단계**: `can_erect()` false → 자위 포기
- **finishing 단계**: `can_ejaculate()` true → 정액 소모 + arousal -50, false → arousal -20

### 플레이어 자위

`call:masturbate:자위#` 액션 (연애 모드 ON 시 활성화):
- 조건: 주변 혼자 + `can_erect()` true
- `상태:자위중` prop 설정 → 15분 advance_time_des → 상태 해제
- 사정 가능: 정액 -15 + 성욕 -50, 불가: 성욕 -15

### 플레이어 자위 발각

on_meet_player()에서 `상태:자위중` prop 체크 → `_on_player_masturbation_discovered()`:

| 조건 | 반응 유형 | 효과 |
|------|----------|------|
| 호감≥70 + 욕망≥60 + 성욕≥50 | initiate | 욕망+5, NPC 주도 성행위 전환 |
| 호감≥70 + 욕망≥50 | intimate | 욕망+3 |
| 호감≥40 | embarrassed | 효과 없음 |
| 그 외 | disgusted | 호감-5 |

반응 텍스트: `masturbation_templates.py` (4 유형 × 10 아키타입).

---

## 11.5. 정액 시스템 (Semen Gauge)

### 개요

P anatomy 캐릭터(남성/후타나리)의 정액 축적/소모 관리. `semen.py` 모듈.
연애 시스템 활성화(`settings.is_romance_enabled()`) 시에만 동작.

### 상수

| 상수 | 값 | 설명 |
|------|-----|------|
| SEMEN_MAX | 100 | 정액 최대치 |
| SEMEN_REGEN_RATE | 5 | 시간당 회복 (0→100: 20시간) |
| SEMEN_MIN_ERECTION | 5 | 발기 최소치 (미만 → 삽입 불가) |
| SEMEN_MIN_EJACULATION | 10 | 사정 최소치 (미만 → 사정 불가) |
| EJACULATION_COST | 20 | 사정 1회 소모 |
| WET_DREAM_COST | 30 | 몽정 시 소모 |
| MASTURBATION_COST | 15 | 자위 사정 시 소모 |

### 로맨스 연동

- **삽입**: `can_erect()` false → 삽입 차단 (romance.py)
- **사정**: `can_ejaculate()` false → 사정 차단 (romance.py)
- **사정량**: 정액 < 50 → 비례 감소 (romance_core.py `calculate_ejaculation_amount`)
- **사정 후**: EJACULATION_COST 소모 (romance.py, npc_initiative.py)

### 몽정

수면 중 정액 만수(100) 시 자동 발생:
- **NPC**: `_process_memory_on_sleep()` — 정액 소모 + 성욕 감소 + 외부 정액 적용
- **플레이어**: `needs.py:_process_hourly()` — 수면 중 체크, 기상 후 `기억:몽정` prop → 연출

### 미등록 캐릭터

정액 시스템에 등록되지 않은 캐릭터는 제한 없음 (SEMEN_MAX 반환).

---

## 12. 삽입 행위 시스템 (Intercourse)

### 개요

삽입 행위는 **즉시형 삽입 시도** + **토글형 허리흔들기** 2단계로 구성.
삽입(정지 상태) → 허리흔들기(강도 선택) → 멈추기/빼기의 흐름.

**핵심 구조:**
- `vaginal_insert` / `anal_insert` — 즉시형 삽입 시도 (`is_insertion_attempt`)
- `thrust_gentle` / `thrust_normal` / `thrust_rough` — 토글형 허리흔들기 (`requires_active_insertion`)
- `thrust_stop` — 즉시형 멈추기 (삽입 유지, 허리흔들기 해제)
- `withdraw` — 즉시형 빼기 (삽입 해제)

**삽입 상태 추적**: `state["insertion"]["active"]`, `state["insertion"]["orifice"]`

### 새 필드: requires_player_anatomy

기존 행위는 NPC(대상)의 해부학만 체크했으나, 삽입은 **양쪽 모두** 필요:

| 필드 | 기존 | 삽입 행위에서 추가 |
|------|------|-------------------|
| `exp_part` → SENSATION_MAP → `has_anatomy(target)` | NPC 해부학 체크 | 동일 유지 |
| `requires_player_anatomy` | 없음 | 플레이어 해부학 추가 체크 |

```python
# 예: 삽입 (플레이어 P → NPC V)
"vaginal_insert": {
    "exp_part": "음부",                    # NPC쪽 → has_anatomy(npc, "V") 체크
    "requires_player_anatomy": "P",        # 플레이어쪽 → has_anatomy(player, "P") 체크
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

### 삽입 즉시형 행위 (Insertion Attempt)

삽입은 **즉시형** — 실행 시 삽입 상태로 전환. 이미 삽입 중이면 숨김.

| 행위 ID | 이름 | 시간 | 스태미나 | exp_part | player_anatomy | 효과 | 호감도 | 비고 |
|---------|------|------|---------|----------|---------------|------|--------|------|
| `vaginal_insert` | 삽입 | 3분 | 3 | 음부 | P | 성욕+5, 욕망+3, 복종+1 | 98 | pregnancy_check, `is_insertion_attempt` |
| `anal_insert` | 항문 삽입 | 3분 | 3 | 엉덩이 | P | 성욕+5, 욕망+3, 복종+2 | 98 | `is_insertion_attempt` |

```python
"vaginal_insert": {
    "name": "삽입", "time": 3 * MILLIS_PER_MINUTE, "stamina": 3,
    "effects": {"성욕": 5, "욕망": 3, "복종": 1},
    "exp_part": "음부", "affection_req": 98,
    "requires_player_anatomy": "P", "requires_exposure": "lower",
    "pregnancy_check": True,
    "is_insertion_attempt": True, "insertion_orifice": "vaginal",
},
"anal_insert": {
    "name": "항문 삽입", "time": 3 * MILLIS_PER_MINUTE, "stamina": 3,
    "effects": {"성욕": 5, "욕망": 3, "복종": 2},
    "exp_part": "엉덩이", "affection_req": 98,
    "requires_player_anatomy": "P", "requires_exposure": "lower",
    "is_insertion_attempt": True, "insertion_orifice": "anal",
},
```

삽입 성공 시 `state["insertion"] = {"active": True, "orifice": "vaginal"/"anal"}` 설정.

### 허리흔들기 토글 (Thrust Toggles)

삽입 상태에서만 활성화 가능한 토글형 행위. **3가지 강도**.

| 행위 ID | 이름 | 틱당 시간 | 스태미나 | 효과 | 호감도 | 강도 |
|---------|------|----------|---------|------|--------|------|
| `thrust_gentle` | 부드럽게 움직이기 | 5분 | 3 | 성욕+5, 호감+2, 욕망+2 | 98 | 1 |
| `thrust_normal` | 허리 흔들기 | 5분 | 4 | 성욕+8, 욕망+5, 복종+1 | 98 | 2 |
| `thrust_rough` | 거칠게 흔들기 | 5분 | 5 | 성욕+11, 욕망+7, 복종+2 | 100 | 3 (준비필요) |

**토글 동작 규칙:**
- `exp_part: None` — 삽입 부위(orifice)에서 동적 결정
- 같은 thrust 재선택 → **OFF되지 않고 계속 유지** (효과 재적용)
- 다른 thrust 선택 → 기존 thrust 해제 + 새 thrust 활성화
- **체위 변경 시**: 모든 thrust 토글 자동 해제 (물리적 재배치). 배면 전환 시 입 사용 토글도 추가 해제
- `_THRUST_TOGGLE_IDS = frozenset({"thrust_gentle", "thrust_normal", "thrust_rough"})`

### 삽입 관련 즉시형 (삽입 상태 필요)

| 행위 ID | 이름 | 시간 | 스태미나 | 효과 | 비고 |
|---------|------|------|---------|------|------|
| `thrust_stop` | 멈추기 | 1분 | 0 | — | thrust 활성일 때만 표시 |
| `withdraw` | 빼기 | 1분 | 0 | — | 삽입 상태 해제 |
| `thrust_deep` | 깊게 밀어넣기 | 3분 | 3 | 성욕+8, 욕망+4, 복종+1 | 강도 3 |
| `thrust_slow` | 느리게 움직이기 | 3분 | 2 | 성욕+4, 호감+2, 욕망+2 | 강도 1 |
| `grind` | 밀착 흔들기 | 3분 | 2 | 성욕+6, 욕망+3 | exp_part: 클리토리스 |

**thrust_stop 동작:**
- 허리흔들기 토글 전부 해제 (삽입은 유지)
- 사정 후 자동 멈춤 시에도 동일 처리
- UI: 삽입 중 + thrust 활성일 때만 표시

> **손가락 삽입**(`finger_insertion`, `finger_anal_insertion`)과 **커닐링구스/펠라치오**는
> 토글형 외부 자극으로 분류 (위 TOGGLE_ACTIONS 테이블 참조).
> 이들은 `is_insertion_attempt` 없음, requires_player_anatomy 없음.

### 노출 요건

모든 삽입 행위는 **하체 노출** 필수 (하드 락):
- `requires_exposure: "lower"` — NPC 하체 노출 필수
- 미노출 시 `[color=gray]삽입 (탈의 필요)[/color]` 표시

### 임신 판정 (pregnancy_check) — 절정 시 판정

**중요: 수정 판정은 매 틱이 아닌, P를 가진 쪽의 절정 시에만 발생.**

`vaginal_insert`의 `pregnancy_check: True` 플래그로 삽입 상태에서 절정 시 판정:

**판정 조건:**
1. 질 삽입 상태(`insertion.orifice == "vaginal"`)에서 진행 중
2. P를 보유한 쪽(삽입자)이 절정 도달
3. V를 보유한 쪽(피삽입자)의 월경 주기 기반 가임 확률 적용

- 항문 삽입(`anal_insert`)은 `pregnancy_check` 없으므로 판정 안 함
- 손가락/구강 행위도 판정 안 함
- 상세 메커니즘은 [romance-pregnancy.md](romance-pregnancy.md) 참조

### 삽입 부위 충돌

삽입은 한 번에 하나만 가능. `vaginal_insert` → `anal_insert` 선택 시 기존 삽입 해제 + 새 삽입.
허리흔들기 토글은 `exp_part: None`이므로 exp_part 충돌 없음 — 삽입 부위에서 동적 결정.

### 자극 시스템 연동

- 삽입 즉시형 (`vaginal_insert`) → exp_part 기반 자극 (음부/엉덩이)
- 허리흔들기 토글 → 삽입 orifice에서 동적으로 exp_part 결정
  - vaginal → 음부(V), anal → 엉덩이(A)
- 절정 시 기존 절정 처리 로직 그대로 적용

### 효과 밸런스

| 항목 | 질 삽입(즉시) | 허리 일반(토글) | 비교 (클리토리스 문지르기) |
|------|-------------|---------------|--------------------------|
| 성욕 | +5 | +8 | +7 |
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

삽입 관련 반응 키:

```python
ROMANCE_REACTIONS = {
    "vaginal_insert": {                # 삽입 즉시형
        "start": [...],
    },
    "thrust_normal": {                 # 허리흔들기 토글
        "during": [...],
    },
    "thrust_stop": {                   # 멈추기
        "start": [...],
    },
    "withdraw": {                      # 빼기
        "start": [...],
    },
    ...
}
```

**톤 템플릿 키 매핑:**
- `ACTION_REACTIONS` (`:during`) → 토글 묘사: `thrust_normal`, `thrust_gentle`, `thrust_rough`
- `ACTION_LINES` (`:start`) → 즉시형 대사: `vaginal_insert`, `anal_insert`, `thrust_rough`, `genital_caress`, `first_vaginal_insert`, `first_anal_insert`

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
                from npc_initiative import start_npc_initiative
                return start_npc_initiative(player_id, self.instance_id)
            return None

        # 첫 만남 이벤트
        self._event_flags["first_meet"] = True
        return self._run_event_dialog("first_meet", player_id=player_id)
```

---

## 18. 체력 시스템 (HP 통합)

### 개요

연애 세션의 스태미나를 전투/생존 체력(`생존:체력`)과 통합.
별도의 `연애:스태미나` prop을 제거하고, 실제 HP를 소비하는 방식.

### 핵심 메커니즘

| 항목 | 설명 |
|------|------|
| 세션 시작 | `survival.get_survival_stats(player_id)` → `health`, `max_health` 읽기 |
| 행위 소비 | 행위마다 `state["stamina"]` 차감 (기존과 동일) |
| 탈진 | `stamina ≤ total_stamina` → `stamina = 1` (HP 1 보존, 기절 방지) |
| 세션 종료 | `survival.set_health(player_id, state["stamina"])` — HP writeback |

### 체력 바 렌더링

10칸 정규화 — HP 범위에 관계없이 일관된 표시:

```python
def render_stamina_bar(stamina, max_stamina=100):
    BAR_WIDTH = 10
    ratio = stamina / max(1, max_stamina)
    filled = max(0, min(BAR_WIDTH, round(ratio * BAR_WIDTH)))
    empty = BAR_WIDTH - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {int(stamina)}/{int(max_stamina)}"
```

UI 라벨: `체력: ████████░░ 80/100`

### 사정량 HP 정규화

`calculate_ejaculation_amount(unit_id, stamina, max_stamina)`:
- `max_stamina > 10` → 0-10 스케일로 정규화 후 공식 적용
- 기존 0-10 범위에서의 공식 호환성 유지

### 세션 상태 보존

공수 전환 시 `extract_preserved(state)`:
- `initial_stamina`: 세션 시작 시점 HP
- `max_stamina`: 최대 HP
- `stamina`: 현재 HP

---

## 19. NPC 주도 종료 조건

### NPC 만족 종료

NPC가 절정 후 성욕이 임계치 미만으로 떨어지면 자발적 종료:

```python
NPC_SATISFACTION_AROUSAL = 20   # 성욕 임계치
NPC_SATISFACTION_CLIMAX = 1     # 최소 절정 횟수
```

조건: `climax_total ≥ 1` AND `성욕 < 20` → `state["npc_satisfied"] = True`

종료 반응: `INITIATIVE_REACTIONS["satisfied"]` (캐릭터별 텍스트)

### 조건부 쿨다운

NPC 주도 쿨다운(`mark_initiative_cooldown()`)을 세션 시작에서 종료로 이동:

| 조건 | 쿨다운 |
|------|--------|
| `stamina < initial_stamina` (행위 발생) | 정상 적용 (8시간 등) |
| `stamina == initial_stamina` (즉시 탈출) | 스킵 — 다음 on_meet에서 재시도 |

**HP 가드**: `should_initiate_skinship()`에서 플레이어 HP < 5면 NPC 주도 거부.

```python
INITIATIVE_MIN_HEALTH = 5
```

---

## 20. 행위 묘사 시스템

### 개요

행위 실행 시 **묘사 텍스트**(3인칭 나레이션)와 **NPC 대사**를 결합하여 표시.
NPC 대사가 없는 행위에도 묘사로 상황 전달.

### ACTION_DESCRIPTIONS (즉시형)

`romance_actions.py`에 정의. 행위 실행 시 대사 앞에 `[color=silver]` 태그로 표시:

```python
ACTION_DESCRIPTIONS = {
    "head_pat": "머리를 부드럽게 쓰다듬는다.",
    "french_kiss": "깊은 키스를 한다.",
    "breast_caress": "가슴을 부드럽게 어루만진다.",
    "thrust_deep": "깊숙이 밀어넣는다.",
    ...
}
```

### TOGGLE_DURING_DESCRIPTIONS (토글 진행 중)

활성 토글 행위의 상황 묘사. UI에서 토글마다 표시:

```python
TOGGLE_DURING_DESCRIPTIONS = {
    "hug": "서로를 껴안고 있다.",
    "deep_kiss": "깊은 키스가 이어지고 있다.",
    "thrust_normal": "허리를 흔들고 있다.",
    ...
}
```

### 자극 상태 자동 묘사 (get_state_description)

`romance_core.py`에서 부위별 자극 수치에 따라 자동 생성 (최대 2줄):

| 자극 수준 | 표시 |
|----------|------|
| ≥ 80 (high) | 강렬한 묘사 (`_STIM_HIGH_TEXTS`) |
| ≥ 50 (mid) | 중간 묘사 (`_STIM_MID_TEXTS`) |
| < 50 | 표시 안 함 |

절정 접근 시 추가: `gauge ≥ 80` → "절정이 가까워지고 있다."

### UI 통합

`last_reaction` 형식 변경 — 묘사 + 대사 결합:
```
[color=silver]깊은 키스를 한다.[/color]
[color=yellow]...끝나지 않게...[/color]
```

`render_romance_ui()`에서 `last_reaction`을 raw 출력 (자체 color 태그 포함).

---

## 21. 동작 모드 시스템 (romance_mode.py)

> 기존 18번 섹션에서 이동 (18→19→20 신규 추가로 번호 밀림)

### 개요

연애 세션은 4가지 **동작 모드**로 실행될 수 있다:

| 모드 | 상수 | 진입 조건 | 설명 |
|------|------|----------|------|
| 합의 | `MODE_CONSENSUAL` | 호감도 50+ | 기본 상호 동의 |
| 강제 | `MODE_FORCED` | 1:1 + 제압 판정 | 의식 있는 대상, NPC 저항 가능 |
| 무의식 | `MODE_UNCONSCIOUS` | NPC 기절 중 | 반응 없음, 각성 시 강제로 전이 |
| 시간정지 | `MODE_FROZEN` | 시간정지 상태 | 반응 없음, 효과 지연 |

### 모드 컨텍스트 (`state["mode_ctx"]`)

```python
{
    "mode": "forced",         # 현재 모드
    "actor_id": player_id,    # 주도자
    "target_id": partner_id,  # 대상
    "action_count": 0,        # 행위 횟수
    # FORCED
    "resistance_meter": 0,    # NPC 저항 축적 (100 도달 시 탈출)
    "break_free_attempts": 0, # 저항 시도 횟수
    # UNCONSCIOUS
    "wake_check_accum": 0,    # 각성 체크 누적
    # FROZEN
    "deferred_effects": [],   # 해제 후 적용할 효과
    "deferred_semen": {},     # 해제 후 적용할 정액
    "deferred_climax_count": 0,
}
```

### 모드별 동작 차이

| 훅 | consensual | forced | unconscious | frozen |
|----|-----------|--------|-------------|--------|
| affection_req | 정상 | 무시(0) | 무시(0) | 무시(0) |
| 효과 배율 | ×1.0 | 호감×0, 반발+보너스 | 감정×0, 물리×0.5 | 전부 지연 (30% 감쇠) |
| 반응 접두사 | `""` | `"forced_"` | None (나레이션) | None (나레이션) |
| 소음 발생 | O | O | X | X |
| 시간 경과 | O | O | O | X |
| 3자 감지 | O | O | X | X |
| NPC 저항 | X | O (매 행위 후) | X | X |
| 각성 체크 | X | X | O (기절 해제 시) | X |
| 주도권 전환 | O | X | X | X |

### 21.1 강제 모드 (Player→NPC)

#### 진입 흐름

1. 포커스 메뉴에서 "강제 행위" 선택 (`base.py force_romance()`)
2. 1:1 상황 체크 (`can_start_forced()` — 같은 location, 다른 의식있는 NPC 없음)
3. 제압 성공 확률 표시 + 확인
4. 성공 → 강제 세션 시작 / 실패 → 호감 -10, 반발 +15

#### 제압 성공 확률 (`calculate_force_chance()`)

```python
actor_power = 근력 + 체격 + (체력/최대체력) × 3
target_power = 동일 공식
base = 0.5 + (actor_power - target_power) × 0.05
# 은신 기습 보너스: status:stealth == 1 → +20%
chance = clamp(0.1, 0.95, base + stealth_bonus)
```

NPC 기본 스탯:

| NPC | 근력 | 체격 | 근거 |
|-----|------|------|------|
| 세라 | 6 | 3 | 장신, 활동적 |
| 밀라 | 4 | 2 | 보통 체격, 가사 |
| 리나 | 3 | 1 | 왜소, 약함 |
| 유키 | 3 | 1 | 왜소, 약함 |
| 엘라 | 5 | 3 | 장신, 단련됨 |

#### NPC 저항 (`check_resistance()`)

매 행위 후 `_post_action_mode_check()`에서 호출.

**탈출 확률 공식** (`calculate_escape_chance()`):
```python
base = 0.10 + 근력 × 0.02 + 반발 × 0.003
penalty = 성욕 × 0.002 + 절정게이지 × 0.002 + min(절정횟수, 3) × 0.03
chance = clamp(base - penalty, 0, 0.50)
```

**항상실패(futile) 판정** — 성적 각성이 육체적 저항력을 압도:
```python
escape_power = 근력 × 2 + 체격 × 3 + (체력/최대체력) × 5
suppression  = 성욕 × 0.2 + 절정게이지 × 0.2 + min(절정횟수, 3) × 5
is_futile = suppression >= escape_power   # → chance = 0
```

**저항 게이지 축적**:
- 일반: `max(3, int(근력 × 1.5))` / futile: `max(1, int(근력 × 0.5))`
- `resistance_meter ≥ 100` → futile 상태에서도 강제 탈출 (안전장치)

**NPC별 보정표**:

| NPC | 근력 | 체격 | escape_power | 성욕=0 확률 | 성욕=80+게이지=50 | futile 진입 기준 |
|-----|------|------|-------------|-----------|-----------------|----------------|
| 세라 | 6 | 3 | 26 | 22% | ~0% (futile) | 성욕80+게이지50 |
| 엘라 | 5 | 3 | 23 | 20% | ~0% (futile) | 성욕80+게이지35 |
| 밀라 | 4 | 2 | 19 | 18% | ~0% (futile) | 성욕70+게이지25 |
| 리나 | 3 | 1 | 14 | 16% | ~0% (futile) | 성욕50+게이지20 |
| 유키 | 3 | 1 | 14 | 16% | ~0% (futile) | 성욕50+게이지20 |

**체위 변경 시**: 탈출 확률로 저항 판정 → 성공 시 `resistance_meter` 초기화, 실패 시 축적.

**탈출 시도 메시지**: 실패 시 NPC가 저항하는 묘사 (일반/futile 풀 분리).

- 탈출 성공 → 세션 종료, `상태:강제피해` prop=3 설정, `기억:강제피해횟수` +1
- 탈출 시 NPC 반응: `forced_break_free:start`

#### 신체 반응 (`romance_body_reaction.py`)

강제 모드 중 성욕/절정게이지 변화에 따른 비자발적 신체 반응 묘사.

- **2차원 단계**: arousal_tier(low/medium/high/extreme) × gauge_tier(low/medium/high/critical)
- **10개 아키타입**: stoic/gentle/cheerful/timid/cold/seductive/fierce/proud/innocent/devoted
- **절정 후 반응**: climax_total ≥ 1 + arousal < 30 → 별도 풀
- **UI 표시**: `[color=magenta]` 태그, 저항 바 아래에 렌더링
- **fallback**: 정확한 키 없으면 gauge → arousal 순으로 한 단계 낮춰 검색

#### 효과 배율

- 호감: ×0, 욕망: ×0, 반발: ×2.0, 복종: ×2.0
- 성욕: ×0.5, 감각경험치: ×0.5
- 매 행위마다 반발 +1 추가

#### 반응 키

강제 모드 전용 반응: `"forced_{action_id}:start"` → fallback `"{action_id}:start"`

### 21.2 무의식 모드 (Player→기절NPC)

#### 진입

- `survival.is_npc_fainted(target_id)` 시 `base.py romance()`에서 자동 판별
- 포커스 메뉴에서 "애정 행위" 선택 시 기절 NPC면 자동으로 `MODE_UNCONSCIOUS`

#### 세션 중 동작

- NPC 반응 없음 → 나레이션: `"(반응 없이 축 늘어져 있다.)"`
- 소음 미발생
- 감정 효과 억제: 호감/욕망/반발 ×0
- 물리적 반사: 성욕 ×0.5, 감각경험치 ×0.5

#### 각성 전이

매 행위 후 `survival.get_faint_remaining_millis()` 확인:
- 기절 시간 만료 → `transition_to_forced()`: `MODE_UNCONSCIOUS` → `MODE_FORCED`
- 전이 시: resistance_meter 30으로 시작 (각성 직후 높은 저항)
- 세션 상태 보존 (자극/체력/경과시간)

### 21.3 시간정지 모드 (Player→정지NPC)

#### 진입

- `morld.is_time_frozen()` 시 `base.py romance()`에서 자동 판별

#### 지연 효과 시스템

- **시간 미경과**: `advance_time_and_check()` 스킵
- **효과 지연**: 관계 수치 변화를 `deferred_effects`에 축적
- **정액 지연**: `deferred_semen`에 축적
- **자극**: 정상 누적 (절정 카운팅용)
- **감각 경험치**: ×0 (신경계 정지)

#### 임신 판정

시간정지 중에도 정상 임신 판정 가능:
- `father_type="unknown"` 설정 (NPC는 상대를 모름)
- `상태:아이아버지 = "???"`, `상태:아이아버지id = 0`

#### 세션 종료 후

`apply_deferred_effects(target_id, mode_ctx, player_id)` 호출:
- 축적된 효과의 **30%만** 실제 적용 (DAMPENING = 0.3)
- `상태:시간정지피해` prop=3 설정, `기억:시간정지피해횟수` +1

### 21.4 NPC→Player 저항 모드

NPC 주도 세션(`npc_initiative.py`)에서 플레이어 선택:

| 선택 | 동작 |
|------|------|
| 수락 | `MODE_CONSENSUAL` (기존) |
| 저항 | 저항 모드 진입 — 매 턴 저항/포기 선택 |
| 탈출 시도 | 1회성 탈출 판정 (기존) |

#### 저항 메카닉

```python
resistance_gain = 15 + max(0, (player_power - npc_power)) × 3  # 5~40
# 매 턴: resistance_meter += gain
# resistance_meter ≥ 100 → 탈출 성공
# 포기 선택 → 합의로 전환
```

NPC는 저항 중에도 자동으로 행위 진행 (`_npc_auto_advance()`), 강제 반응 접두사 사용.

### 21.5 사후 이벤트 — 후유증 시스템 (on_meet)

강제/무의식/시간정지/수간 세션 종료 후 NPC와 재회 시 **3단계 후유증** 반응.

#### Prop 부호 규약

단일 prop으로 단계 + 표시 상태를 인코딩:

| 값 | 의미 |
|----|------|
| `3/2/1` (양수) | 반응 대기 (미표시) |
| `-3/-2/-1` (음수) | 이미 표시됨 (수면 시 감소 대상) |
| `0` | 후유증 없음 |

#### 라이프사이클

```
사건 발생 → prop=3, 기억:*피해횟수 += 1
만남 → prop>0 → 반응 표시 → prop 부호 반전 (-3)
수면 → prop<0 → abs-1 → prop=2 (양수, 대기)
만남 → 반응 → prop=-2
수면 → prop=1
만남 → 반응 → prop=-1
수면 → abs-1=0 → 해제
```

- **양수인 채로 수면** → 감소 안 함 (플레이어가 아직 반응을 보지 않았으므로 대기)
- **진행 중 새 사건** → prop=3 덮어쓰기 (최고 단계 리셋), count +1

#### Prop 목록

| prop | 트리거 | 누적 카운트 |
|------|--------|------------|
| `상태:강제피해` | 강제 종료 시 (값=3) | `기억:강제피해횟수` |
| `상태:무의식피해` | 무의식 종료 시 (값=3) | `기억:무의식피해횟수` |
| `상태:시간정지피해` | 시간정지 종료 시 (값=3) | `기억:시간정지피해횟수` |
| `상태:수간피해` | Creature 겁탈 후 (값=3) | `기억:수간피해횟수` |

#### 단계별 반응 톤

| 단계 | 이름 | 반응 톤 |
|------|------|---------|
| 3 | 충격 | 강한 감정 반응 (공포, 분노, 충격) |
| 2 | 경계 | 중간 반응 (경계, 불안, 회피) |
| 1 | 잔향 | 약한 반응 (여운, 미세한 변화) |

- **누적 횟수 ≥ 2**: stage 3에서 반복 전용 템플릿 사용 (체념, 무감각 등)

#### 아키타입 기반 템플릿 (`aftermath_templates.py`)

`REACTION_PROFILE["archetype"]`에 따라 10개 아키타입별 대사 자동 매칭:
- stoic / gentle / cheerful / timid / cold / seductive / fierce / proud / innocent / devoted
- 캐릭터별 override 불필요 (base.py fallback으로 통합)

#### 수면 시 기억 처리 (`_process_memory_on_sleep`)

`think/__init__.py`의 `_handle_sleep()` 도착 시점에서 호출. 수면을 기억 처리의 중심으로 사용:

1. **aftermath 단계 감소**: 음수(표시됨) → `abs-1` → 양수(대기) 또는 0(해제)
2. **긍정 기억 활성화**: `-1`(수면 전 대기) → `1`(on_meet 대상)

- `_check_fatigue()` 경유 비스케줄 수면에서도 동작

### 21.6 긍정 기억 (on_meet)

선물 수령 후 **1회 수면을 거친 뒤** NPC가 재회 시 선물을 기억하고 언급.

#### 라이프사이클

```
선물 수령 → 기억:긍정기억=-1 (수면 전 대기)
수면 → -1 → 1 (활성화)
만남 → 반응 표시 → 0 (해제)
```

#### Prop 목록

| prop | 설정 시점 | 설명 |
|------|----------|------|
| `기억:마지막선물이름` | give_gift() | 아이템 표시 이름 |
| `기억:마지막선물반응` | give_gift() | `"favorite"` / `"liked"` / `"normal"` |
| `기억:긍정기억` | give_gift() | `-1`=대기, `1`=활성, `0`=없음 |

- **비호감 선물(disliked)**: 긍정 기억 트리거 안 함
- **연속 선물**: 최신 선물로 덮어쓰기
- **favorite 반응**: 아이템명(`{item}`) 직접 언급

#### 아키타입 기반 템플릿 (`positive_memory_templates.py`)

`REACTION_PROFILE["archetype"]`에 따라 10개 아키타입별 자동 매칭.
gift_favorite / gift_liked / gift_normal 3종 × 10 아키타입.

### 21.7 임신 이벤트 (on_meet)

`pregnancy.check_pending_pregnancy_events(unit_id)` 호출:

| 이벤트 키 | 조건 | 설명 |
|-----------|------|------|
| `conception:discovery` | `이벤트:수정` flag | 수정 인지 (상대 알고 있음) |
| `conception:unknown_father` | `이벤트:수정` + 아버지=??? | 수정 인지 (상대 모름) |
| `pregnancy:announcement` | 12주차 + 미발표 | 임신 발표 |
| `pregnancy:unknown_father` | 12주차 + 미발표 + 아버지=??? | 상대 모르는 임신 발표 |

각 캐릭터 파일에서 `_handle_pregnancy_event()` 오버라이드로 성격별 반응.

### 21.8 경험 기록 시스템

성 경험을 부위별 첫경험 + 전체 마지막경험으로 추적. `romance_core.py`에 구현.

#### 부위별 첫경험 (`record_first_experience`)

처녀 해제 시점(`check_and_clear_virginity`)에서 자동 호출. 최초 1회만 기록.

| prop | 값 | 설명 |
|------|----|------|
| `기억:첫경험` | 1 | 전체 첫경험 유무 (기존 플래그 호환) |
| `기억:첫경험:유형` | str | 전체 첫 행위 유형 (consensual/forced/unconscious/frozen/bestiality) |
| `기억:첫경험:상대` | int | 전체 첫 행위 상대 (unit_id) |
| `기억:첫경험:시각` | int | 전체 첫 행위 시각 (game time ms) |
| `기억:첫경험:{부위}` | 1 | 부위별 첫경험 유무 (부위 = 음부/항문/구강) |
| `기억:첫경험:{부위}:유형` | str | 부위별 첫 행위 유형 |
| `기억:첫경험:{부위}:상대` | int | 부위별 첫 행위 상대 |
| `기억:첫경험:{부위}:시각` | int | 부위별 첫 행위 시각 |

- **Creature 겁탈**: `check_and_clear_virginity` 미사용 (호감 보너스 부적절). `creature_agent.py`에서 직접 `record_first_experience()` 호출.

#### 마지막 경험 (`record_last_experience`)

세션 종료 시점에 항상 갱신. 로맨스 세션/NPC 주도/Creature 겁탈 모두에서 호출.

| prop | 값 | 설명 |
|------|----|------|
| `기억:마지막경험:유형` | str | 마지막 행위 유형 |
| `기억:마지막경험:상대` | int | 마지막 행위 상대 (unit_id) |
| `기억:마지막경험:시각` | int | 마지막 행위 시각 (game time ms) |
