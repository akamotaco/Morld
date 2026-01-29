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
- **실패**: 중단 이벤트 발생 (기존 로직)

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
        ({"애정": 40}, ["......", "...조심해."]),
        ({}, ["......", "...(긴장한 표정)"]),
    ],
    "effects": {"성욕": 5},  # 은신 성공 시 파라미터 변화
}
```

**캐릭터별 은신 반응:**

| 캐릭터 | 반응 특징 | 효과 |
|--------|----------|------|
| 세라 | 스릴에 흥분 | 성욕 +5 |
| 밀라 | 부끄러워하며 더 사랑함 | 호감 -1, 애정 +1 |
| 리나 | 무섭지만 흥분 | 호감 +1, 성욕 +3 |
| 유키 | 무서워서 더 매달림 | 호감 +2 |
| 엘라 | 차갑게 경계 | 애정 +1 |

**UI 표시:**
- 은신 성공 시 시안색(`[color=cyan]`)으로 캐릭터 반응 텍스트 표시
- 예: `[color=cyan][세라] ...위험했어...[/color]`

**세라 예시:**
```python
STEALTH_REACTIONS = {
    "text": [
        ({"성욕": 50}, ["...위험했어...", "...(숨을 거칠게 몰아쉰다)"]),
        ({"애정": 40}, ["......", "...조심해."]),
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
        ({"애정": 40}, ["...무서웠어요...", "...다행이에요..."]),
        ({}, ["...휴... 다행이에요...", "...(가슴을 쓸어내린다)"]),
    ],
    "effects": {"호감": -1, "애정": 1},  # 부끄럽지만 더 사랑함
}
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

**필수 조건:**
- 플레이어와 NPC가 같은 Location에 **단 둘이** 있어야 함
- 다른 캐릭터가 있으면 NPC 주도 발동 안 함 (오브젝트는 무시)
- 이동 중인 캐릭터도 무시 (도착한 캐릭터만 체크)

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

**방해 이벤트 발생 시:**
- 목격자가 놀람 반응 다이얼로그
- NPC에게 "부끄러움" mood 추가
- NPC가 플레이어로부터 도망 (`flee` job)
- 목격자 호감도 -5
- NPC 호감도 -3

---

## 4. 사적인 대화 시스템 (진척도)

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

## 5. 캐릭터별 구현 가이드

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
            ({"애정": 40}, ["......", "...조심해."]),
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

## 6. 구현 상태

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
| 사적인 대화 (진척도 1) | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 2) | 전체 NPC | ✅ 완료 |
| 사적인 대화 (진척도 3) | 전체 NPC | ✅ 완료 |
| 은신 시스템 (플레이어 주도) | romance.py | ✅ 완료 |
| 은신 시스템 (NPC 주도) | npc_initiative.py | ✅ 완료 |
| 제3자 방해 이벤트 (NPC 주도) | npc_initiative.py | ✅ 완료 |
| 캐릭터별 은신 반응 | base.py, 전체 NPC | ✅ 완료 |

### 지원 캐릭터

| 캐릭터 | 스킨십 반응 | NPC 주도 | 사적인 대화 | 은신 반응 | 특징 |
|--------|-----------|----------|-----------|----------|------|
| 세라 | ✅ | ✅ | ✅ | ✅ | 무뚝뚝/거친 - 연애 쑥맥 |
| 밀라 | ✅ | ✅ | ✅ | ✅ | 다정/포근 - 연애 저돌적 |
| 리나 | ✅ | ✅ | ✅ | ✅ | 활발 - 연애엔 수줍음 |
| 유키 | ✅ | ✅ | ✅ | ✅ | 매우 수줍음 |
| 엘라 | ✅ | ✅ | ✅ | ✅ | 냉정함 |

### 미구현/선택적 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| 합류 이벤트 | 호감 높은 NPC 합류 | 미구현 |
| 성적흥분 시간 감소 | 시간 경과 시 자동 감소 | 미구현 |
| 복수 파트너 UI | 3인 이상 연애 | 미구현 |

---

## 7. 관련 morld API

| API | 설명 | 사용처 |
|-----|------|--------|
| `get_units_at_location(r, l)` | Location의 유닛 ID 목록 | 제3자 체크 |
| `advance_time_simulate(min)` | 시간 + NPC 이동 시뮬레이션 | 행위 시간 경과 |
| `modify_prop(id, prop, delta)` | prop 상대값 변경 | 호감도/애정 증감 |
| `add_unit_mood(id, mood)` | mood 추가 | 부끄러움 등 |
| `set_npc_job(id, action, dur, target)` | NPC Job 설정 | flee, follow |
| `set_unit_prop(id, prop, value)` | prop 절대값 설정 | can: props |

---

## 8. 파일 구조

```
scenarios/scenario02/python/
├── romance.py              # 스킨십 시스템 (플레이어 주도)
├── date.py                 # 데이트 시스템 + 애정 표현
├── npc_initiative.py       # NPC 주도 스킨십 시스템 (행위 마스킹, 캐릭터 필터)
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
