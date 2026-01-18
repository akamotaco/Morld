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

### 행위 정의

#### 즉시형 행위 (INSTANT_ACTIONS)
| 이름 | 시간 | 스태미나 | 효과 | 필요 호감도 |
|------|-----|---------|------|------------|
| 머리 쓰다듬기 | 3분 | 1 | 호감+2, 애정+1 | 40 |
| 뺨 어루만지기 | 2분 | 1 | 호감+1, 애정+1 | 30 |
| 뺨 꼬집기 | 2분 | 1 | 호감+1 | 35 |
| 귀 만지기 | 3분 | 1 | 호감+1, 애정+1, 성적흥분+1 | 45 |
| 사랑의 속삭임 | 2분 | 1 | 호감+2, 애정+3 | 50 |
| 프렌치 키스 | 5분 | 2 | 호감+1, 애정+2, 성적흥분+3 | 60 |
| 엉덩이 쓰다듬기 | 3분 | 2 | 애정+1, 성적흥분+3 | 70 |

#### 토글형 행위 (TOGGLE_ACTIONS)
| 이름 | 틱당 시간 | 틱당 스태미나 | 효과 | 필요 호감도 |
|------|----------|-------------|------|------------|
| 껴안기 | 5분 | 1 | 호감+1, 애정+2 | 50 |
| 딥키스 | 5분 | 2 | 호감+1, 애정+2, 성적흥분+3 | 70 |
| 가슴 만지기 | 5분 | 2 | 애정+1, 성적흥분+4 | 80 |

### 절정 시스템
- 성적흥분 >= 100 도달 시 절정 발생
- 절정 시: 성적절정 +1, 성적흥분 = 0으로 리셋
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
캐릭터별로 다른 임계값 설정 가능:

| 캐릭터 | 성욕 임계값 | 호감도 임계값 | 쿨다운 | 성격 |
|--------|------------|--------------|--------|------|
| 세라 | 70 | 60 | 8시간 | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | 50 | 40 | 6시간 | 다정/포근 - 연애 저돌적 |
| 리나 | 65 | 55 | 8시간 | 활발 - 연애엔 수줍음 |
| 유키 | 80 | 70 | 12시간 | 매우 수줍음 |
| 엘라 | 75 | 65 | 10시간 | 냉정함 |

```python
# 밀라 예시 - 저돌적인 성격 반영
INITIATIVE_CONFIG = {
    "arousal_threshold": 50,      # 낮은 성욕에서도 시작
    "affection_threshold": 40,    # 낮은 호감에서도 시작
    "cooldown_minutes": 360,      # 짧은 쿨다운
}
```

### 캐릭터별 허용 액션 필터 (INITIATIVE_ACTION_FILTERS)
NPC 주도 시 캐릭터 성격과 관계 진척도에 따라 허용되는 액션이 달라짐:

```python
# 밀라 - 저돌적 (낮은 조건에서도 다양한 액션)
INITIATIVE_ACTION_FILTERS = [
    ({"애정": 60}, ["hug", "deep_kiss", "breast_touch"]),
    ({"애정": 30}, ["hug", "deep_kiss"]),
    ({}, ["hug"]),
]

# 유키 - 매우 수줍음 (높은 애정에서도 제한적)
INITIATIVE_ACTION_FILTERS = [
    ({"애정": 85}, ["hug", "deep_kiss"]),  # breast_touch 없음
    ({"애정": 60}, ["hug"]),
    ({}, ["hug"]),
]
```

### 행위 마스킹 시스템 (신체 부위 충돌)
같은 신체 부위(exp_part)를 사용하는 행위는 충돌하여 이전 행위가 자동 해제됨:

```python
# 신체 부위 정의
NPC_TOGGLE_ACTIONS = {
    "hug": {..., "exp_part": None, ...},        # 충돌 없음
    "deep_kiss": {..., "exp_part": "입술", ...},
    "breast_touch": {..., "exp_part": "가슴", ...},
}

PLAYER_INSTANT_ACTIONS = {
    "head_pat": {..., "exp_part": "머리", ...},
    "french_kiss": {..., "exp_part": "입술", ...},  # deep_kiss와 충돌
    "whisper": {..., "exp_part": None, ...},        # 충돌 없음
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
        ({"애정": 50}, ["...사랑해요...", "...행복해요..."]),
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
                  NPC 만족? → 종료
                        ↓
                     다음 루프
```

---

## 4. 캐릭터별 구현 가이드

### Character 클래스 속성 (base.py)

```python
class Character(Unit):
    # 스킨십 반응
    ROMANCE_REACTIONS: dict = None

    # NPC 주도 설정
    INITIATIVE_CONFIG: dict = None
    NPC_INITIATIVE_ACTIONS: list = None
    INITIATIVE_REACTIONS: dict = None
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

## 5. 구현 상태

### 완료된 기능

| 기능 | 파일 | 상태 |
|------|------|------|
| 스킨십 UI | romance.py | ✅ 완료 |
| 토글/즉시형 행위 | romance.py | ✅ 완료 |
| 경험치 시스템 | romance.py | ✅ 완료 |
| 절정 시스템 | romance.py | ✅ 완료 |
| 중단 이벤트 | romance.py | ✅ 완료 |
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

### 지원 캐릭터

| 캐릭터 | 스킨십 반응 | NPC 주도 | 특징 |
|--------|-----------|----------|------|
| 세라 | ✅ | ✅ | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | ✅ | ✅ | 다정/포근 - 연애 저돌적 |
| 리나 | ✅ | ✅ | 활발 - 연애엔 수줍음 |
| 유키 | ✅ | ✅ | 매우 수줍음 |
| 엘라 | ✅ | ✅ | 냉정함 |

### 미구현/선택적 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| 합류 이벤트 | 호감 높은 NPC 합류 | 미구현 |
| 성적흥분 시간 감소 | 시간 경과 시 자동 감소 | 미구현 |
| 복수 파트너 UI | 3인 이상 연애 | 미구현 |

---

## 6. 관련 morld API

| API | 설명 | 사용처 |
|-----|------|--------|
| `get_units_at_location(r, l)` | Location의 유닛 ID 목록 | 제3자 체크 |
| `advance_time_simulate(min)` | 시간 + NPC 이동 시뮬레이션 | 행위 시간 경과 |
| `modify_prop(id, prop, delta)` | prop 상대값 변경 | 호감도/애정 증감 |
| `add_unit_mood(id, mood)` | mood 추가 | 부끄러움 등 |
| `set_npc_job(id, action, dur, target)` | NPC Job 설정 | flee, follow |
| `set_unit_prop(id, prop, value)` | prop 절대값 설정 | can: props |

---

## 7. 파일 구조

```
scenarios/scenario02/python/
├── romance.py              # 스킨십 시스템 (플레이어 주도)
├── date.py                 # 데이트 시스템 + 애정 표현
├── npc_initiative.py       # NPC 주도 스킨십 시스템 (행위 마스킹, 캐릭터 필터)
├── assets/
│   ├── base.py             # Character 클래스 (ROMANCE_REACTIONS, INITIATIVE_*)
│   │                       # - should_initiate_skinship()
│   │                       # - get_initiative_reaction()
│   │                       # - get_allowed_initiative_actions()
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
