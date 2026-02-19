# 신규 캐릭터 제작 가이드

## 개요

Character 클래스(base.py)는 **mob NPC** — 서브클래스 없이 단독으로 인스턴스화해도 모든 상호작용이 에러 없이 동작하는 완전한 기반 클래스입니다.

신규 캐릭터는 이 base를 상속하고 **필요한 속성/메서드만 override**하여 개성을 부여합니다.

---

## 파일 구조

캐릭터 1명 = **2개 클래스** (같은 파일에 정의)

```
assets/characters/<name>.py
├── class <Name>(Character)   # 데이터 + 반응 (Asset 클래스)
│   ├── 기본 속성 (unique_id, name, type, props, actions ...)
│   ├── 텍스트 규칙 (TALK_RULES, DESCRIBE_RULES, FOCUS_RULES ...)
│   ├── 연애 반응 (ROMANCE_REACTIONS, REACTION_PROFILE ...)
│   ├── 시스템 설정 (INITIATIVE_CONFIG, STEALTH_REACTIONS ...)
│   └── 이벤트 메서드 (_first_meet_handler, on_bed_awake ...)
│
└── class <Name>Agent(BaseAgent)  # AI 행동 (think 시스템)
    ├── owner_unique_id = "<name>"  # Character와 연결
    ├── SCHEDULE / SCHEDULES        # 일과표
    └── 활동 핸들러 오버라이드       # 캐릭터 고유 행동
```

### 등록

```python
# assets/characters/__init__.py
from .<name> import <Name>

CHARACTER_CLASSES = {
    ...
    "<name>": <Name>,
}
```

---

## Character 클래스 속성 일람

### 필수 속성 (반드시 override)

| 속성 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `unique_id` | str | 고유 식별자 | `"sera"` |
| `name` | str | 표시 이름 | `"세라"` |
| `type` | str | 성별 (`"male"` / `"female"`) | `"female"` |
| `props` | dict | 초기 속성 (외모, 능력치, 상태) | 아래 참조 |
| `actions` | list | 포커스 메뉴 액션 목록 | 아래 참조 |

### 선택 속성 (override하지 않으면 기본값 사용)

#### 캐릭터 특성

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `sexual_orientation` | `"bisexual"` | 성적 지향 (`"bisexual"` / `"heterosexual"`) |
| `hearing_type` | `"normal"` | 청력 (`"normal"` / `"keen"` — 은신 감지) |
| `requires_condom` | `False` | 삽입 시 콘돔 요구 여부 |
| `mood` | `[]` | 초기 감정 상태 |

#### 텍스트 시스템

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `DESCRIBE_RULES` | `None` | 장소 묘사 규칙 (None이면 아키타입 기반 자동 생성) |
| `FOCUS_RULES` | `None` | 포커스 묘사 규칙 (None이면 아키타입 기반 자동 생성) |
| `TALK_TOPICS` | `None` | 대화 주제 목록 (None이면 주제 선택 없이 바로 대화) |
| `TALK_RULES` | `None` | 대화 규칙 dict/list (None이면 기본 대사) |
| `_DEFAULT_ARCHETYPE` | `"stoic"` | 텍스트 자동생성 아키타입 |

#### 연애 시스템

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `ROMANCE_REACTIONS` | 45개 기본 묘사 | 애정 행위별 반응 텍스트 |
| `ROMANCE_SOUND_PROFILE` | `{levels:[5,15,30], ecstasy:50}` | 소리 연출 프로필 |
| `REACTION_PROFILE` | `None` | 아키타입 기반 반응 생성기 설정 |
| `SEXUAL_PREFERENCES` | `None` | 체위/해부학 선호도 |
| `self_comfort_threshold` | `80` | 자위 성욕 임계치 |
| `self_comfort_max_length` | `150` | 자위 허용 장소 기준 길이 |

#### NPC 주도 (Initiative)

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `INITIATIVE_CONFIG` | `None` | 주도 트리거 조건 (None이면 주도 안 함, 욕망 ≥ 40 필수) |
| `NPC_INITIATIVE_ACTIONS` | `None` | 주도 시 행위 시퀀스 |
| `INITIATIVE_REACTIONS` | `None` | 주도 중 반응 텍스트 |
| `INITIATIVE_ACTION_FILTERS` | `None` | 주도 시 허용 행위 필터 |

#### 이벤트 반응

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `STEALTH_REACTIONS` | `None` | 은신 성공 시 반응 + 파라미터 변화 |
| `EQUIP_CHANGE_REACTIONS` | `None` | 플레이어 장비 변경 반응 |
| `ROMANCE_DISCOVERY_REACTIONS` | `None` | 타인 애정행위 목격 반응 |
| `ROOM_PRIVACY_CONFIG` | `None` | 수면/목욕 프라이버시 이벤트 |

#### 대화/진행

| 속성 | 기본값 | 설명 |
|------|--------|------|
| `PROGRESS_DIALOGS` | `None` | 진척도별 일회성 대화 |
| `FRIENDLY_TALK_CONFIG` | `None` | 친밀도별 반복 대화 |
| `GIFT_PREFERENCES` | `{liked:[], favorite:[], ...}` | 선물 선호도 |

---

## Override 가능한 메서드

### 이벤트 핸들러 (모든 NPC가 override)

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `_first_meet_handler` | `(self, player_id)` | 첫 만남 이벤트 (generator) |
| `_handle_mode_aftermath` | `(self, player_id, event_key)` | 강제/무의식/시간정지 후 반응 (generator) |
| `_handle_pregnancy_event` | `(self, player_id, event_key)` | 임신 관련 이벤트 (generator) |
| `on_bed_awake` | `(self, bed, player_id, slot, affection, region_id, owner_id)` | 침대 반응 (깨어있을 때, generator) |
| `on_bed_sleeping` | `(self, bed, player_id, slot, affection, owner_id)` | 침대 반응 (잠자고 있을 때, generator) |

### 선택적 Override

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `on_meet_player` | `(self, player_id)` | 매 만남 이벤트 (기본: 첫 만남 + aftermath + pregnancy 체크) |
| `get_date_accept_text` | `(self)` | 데이트 수락 텍스트 |
| `get_date_reject_text` | `(self, reason)` | 데이트 거절 텍스트 |
| `get_casual_action_reaction` | `(self, action_id)` | 가벼운 애정 반응 텍스트 |
| `get_casual_action_reject` | `(self, action_id)` | 가벼운 애정 거절 텍스트 |

---

## props 템플릿

```python
props = {
    # 성별/외모
    "성별": "female",
    "성적지향": "bisexual",
    "외모:흑발": 1, "외모:장발": 1,
    "나이": 23,

    # 능력치
    "근력": 5, "체력": 5,
    "체격": 3, "가슴:크기": 2,

    # 상태
    "상태:성욕": 0, "상태:질투": 0,
    "상태:피로": 0, "상태:기분": 5,

    # 생존
    "생존:체력": 100, "생존:최대체력": 100,
    "생존:포만감": 80, "생존:최대포만감": 100,

    # 처녀성
    "처녀:구강": 1, "처녀:음부": 1, "처녀:항문": 1,

    # 능력
    "can:lie_down": 1,
    "can:sleep": 1,
    "can:bath": 1,
}
```

---

## actions 템플릿

```python
actions = [
    # 기본 상호작용
    "call:talk:대화",
    "call:errand:심부름#",          # 퀘스트 가능 시만
    "call:give_gift:선물하기",

    # 연애
    "call:romance:스킨십",
    "call:force_romance:강제 행위",

    # 데이트 (선택)
    "call:date:데이트 신청#",
    "call:end_date:데이트 종료#",
    "call:hold_hands:손 잡기#",
    "call:date_hug:안아주기#",
    "call:date_kiss:키스#",

    # 디버그
    "call:debug_props:(디버그) 속성 보기#",
    "call:debug_affection_up:(디버그) 호감도 +10#",
    "call:debug_affection_down:(디버그) 호감도 -10#",
    "call:debug_arousal_up:(디버그) 성욕 +20#",
    "call:debug_arousal_down:(디버그) 성욕 -20#",
    "call:debug_submission_up:(디버그) 복종 +20#",
    "call:debug_submission_down:(디버그) 복종 -20#",
    "call:debug_work_order:(디버그) 작업지시#",
    "call:debug_pregnancy_info:(디버그) 임신 정보#",
    "call:debug_force_conceive:(디버그) 강제 임신#",
    "call:debug_force_birth:(디버그) 강제 출산#",
]
```

`#` 접미사: 조건부 표시 (get_available_actions()에서 필터링)

---

## 최소 구현 예제

```python
# assets/characters/noel.py
from assets.base import Character, build_describe_rules, build_focus_rules
import ui

class Noel(Character):
    unique_id = "noel"
    name = "노엘"
    type = "female"
    sexual_orientation = "heterosexual"

    props = {
        "성별": "female", "성적지향": "heterosexual",
        "나이": 20,
        "근력": 3, "체력": 4, "체격": 2, "가슴:크기": 2,
        "상태:성욕": 0, "상태:기분": 5,
        "생존:체력": 100, "생존:최대체력": 100,
        "생존:포만감": 80, "생존:최대포만감": 100,
        "처녀:구강": 1, "처녀:음부": 1, "처녀:항문": 1,
        "can:lie_down": 1, "can:sleep": 1,
    }

    actions = [
        "call:talk:대화",
        "call:give_gift:선물하기",
        "call:romance:스킨십",
        "call:force_romance:강제 행위",
        "call:debug_props:(디버그) 속성 보기#",
    ]

    mood = []

    # 첫 만남
    def _first_meet_handler(self, player_id):
        yield ui.dialog(f"[{self.name}]\n...안녕하세요. 저는 노엘이에요.")
        self.mark_first_meet_done(player_id)
```

이것만으로 동작하는 NPC가 생성됩니다:
- 장소 묘사: `_DEFAULT_ARCHETYPE`("stoic") 기반 자동 생성
- 대화: 기본 대사 fallback
- 연애: 45개 기본 반응 텍스트
- 침대: 기본 반응 (호감도 기반)

---

## 커스텀 예제 (전체 override)

```python
from assets.base import Character, build_describe_rules, build_focus_rules
import ui


class Noel(Character):
    unique_id = "noel"
    name = "노엘"
    type = "female"
    sexual_orientation = "heterosexual"
    hearing_type = "normal"

    props = { ... }  # 위 템플릿 참조
    actions = [ ... ]
    mood = []

    # ========================================
    # 텍스트 규칙
    # ========================================

    TALK_TOPICS = ["잡담", "자기소개"]

    TALK_RULES = {
        "잡담": [
            ({"mood": "분노"}, {"pages": ["...지금은 말 걸지 마세요..."]}),
            ({"호감": 50}, {"pages": ["...오늘 날씨가 좋네요.", "...같이 걸을래요?"]}),
            ({}, {"pages": ["...안녕하세요.", "...무슨 일이세요?"]}),
        ],
        "자기소개": [
            ({}, {"pages": ["저는 노엘이에요.", "...그냥 평범한 사람이에요."]}),
        ],
    }

    DESCRIBE_RULES = build_describe_rules(
        "gentle",  # 아키타입: stoic/gentle/cheerful/timid/cold
        default_text="노엘이 조용히 서 있다.",
    )

    FOCUS_RULES = build_focus_rules(
        "gentle",
        activities=["독서", "산책"],
        default_text="노엘이 당신을 바라본다.",
    )

    # ========================================
    # 연애 반응
    # ========================================

    ROMANCE_SOUND_PROFILE = {"levels": [5, 15, 25], "ecstasy": 40}

    REACTION_PROFILE = {
        "archetype": "gentle",
        "name": "노엘",
        # 3D 좌표 기반 대사/묘사 자동 생성 (tone_templates/)
        # 캐릭터 오버레이로 일부 좌표 대체 가능:
        # "char_reactions": CHARACTER_REACTIONS,  # :during 3인칭
        # "char_lines": CHARACTER_LINES,          # :start 1인칭
    }

    # 개별 반응 override (지정하지 않은 키는 base 기본값 사용)
    ROMANCE_REACTIONS = {
        **Character.ROMANCE_REACTIONS,  # base 기본값 상속
        "hug:start": [
            # once: 세션 내 첫 포옹에만 출력, 이후 Generator fallback
            ({"once": True, "호감": 50}, ["...처음으로 안아주는 거예요...?"]),
            ({"호감": 50}, ["...따뜻해요..."]),
        ],
        "hug:during": [
            ({"호감": 50}, ["...따뜻해요...", "...이대로 있고 싶어요..."]),
            ({}, ["...!", "...(몸이 굳는다)"]),
        ],
        "ecstasy:start": [
            ({}, ["...아...!", "...(몸을 떤다)"]),
        ],
    }

    SEXUAL_PREFERENCES = {
        "preferred_positions": ["missionary", "side"],
        "disliked_positions": ["standing"],
    }

    # ========================================
    # NPC 주도
    # ========================================

    INITIATIVE_CONFIG = {
        "arousal_threshold": 80,
        "affection_threshold": 60,
        "cooldown_minutes": 360,
    }

    INITIATIVE_REACTIONS = {
        "start": [({}, ["...저기... 좀 더 가까이 와 주세요..."])],
        "satisfied": [({}, ["...감사해요... 이제 괜찮아요..."])],
    }

    INITIATIVE_ACTION_FILTERS = [
        ({"호감": 80}, ["hug", "deep_kiss", "breast_touch"]),
        ({"호감": 50}, ["hug", "deep_kiss"]),
        ({}, ["hug"]),
    ]

    self_comfort_threshold = 75
    self_comfort_max_length = 150

    # ========================================
    # 이벤트 반응
    # ========================================

    STEALTH_REACTIONS = {
        "text": [
            ({"호감": 40}, ["...다행이에요...", "...(안도의 한숨)"]),
            ({}, ["...!", "...(놀란다)"]),
        ],
        "effects": {"호감": 1},
    }

    EQUIP_CHANGE_REACTIONS = {
        "equip": "노엘이 무기를 걱정스럽게 바라본다.",
        "unequip": "노엘이 안심한 듯 미소 짓는다.",
    }

    GIFT_PREFERENCES = {
        "liked_categories": ["food", "flower"],
        "favorite_items": ["herb_tea"],
        "disliked_categories": ["weapon"],
        "favorite_foods": ["potato_soup"],
    }

    PROGRESS_DIALOGS = {
        1: {
            "fallback": ["...안녕하세요...", "...무슨 일이세요?"],
            "dialog": ["...저는 노엘이에요.", "...여기서 지내고 있어요."],
        },
    }

    FRIENDLY_TALK_CONFIG = {
        "high": {
            "dialog": ["...같이 있으면 편해요.", "...오늘도 좋은 하루에요."],
            "progress_cap": 3,
        },
        "mid": {
            "dialog": ["...안녕하세요.", "...오늘은 어떠세요?"],
            "progress_cap": 2,
        },
    }

    ROOM_PRIVACY_CONFIG = {
        "수면": {
            "threshold": 50,
            "high": {"dialog": ["[노엘]", "...어서 오세요..."]},
            "low": {
                "dialog": ["[노엘]", "...저기... 나가 주세요..."],
                "teleport": 1,
                "after": "노엘의 방에서 나왔다.",
            },
        },
    }

    ROMANCE_DISCOVERY_REACTIONS = {
        "default": {
            "text": ["...!", "...뭐... 뭘 하고 있는 거예요...?!"],
            "effects": {"호감": -3},
        },
    }

    # ========================================
    # 이벤트 메서드
    # ========================================

    def _first_meet_handler(self, player_id):
        yield ui.dialog([
            f"[{self.name}]",
            "...안녕하세요.",
            "...저는 노엘이에요.",
            "...앞으로 잘 부탁드려요.",
        ])
        self.mark_first_meet_done(player_id)

    def _handle_mode_aftermath(self, player_id, event_key):
        texts = {
            "forced_aftermath": "...무서웠어요...",
            "unconscious_aftermath": "...이상한 기분이 들어요...",
            "frozen_aftermath": "...뭔가... 기억이 이상해요...",
        }
        yield ui.dialog([f"[{self.name}]", texts.get(event_key, "...")])

    def _handle_pregnancy_event(self, player_id, event_key):
        yield ui.dialog([f"[{self.name}]", "...저... 할 말이 있어요..."])

    def on_bed_awake(self, bed, player_id, slot, affection, region_id, owner_id):
        import morld
        success = morld.sit_on(player_id, bed.instance_id, slot)
        if success:
            if affection >= 60:
                yield ui.dialog([f"[{self.name}]", "...어서 오세요... 옆에 앉아요."])
            elif affection >= 30:
                yield ui.dialog([f"[{self.name}]", "...뭐... 뭘 하는 거예요...?"])
            else:
                yield ui.dialog([f"[{self.name}]", "...저기... 여긴 제 침대인데요..."])

    def on_bed_sleeping(self, bed, player_id, slot, affection, owner_id):
        import morld
        success = morld.sit_on(player_id, bed.instance_id, slot)
        if success:
            yield ui.dialog(["노엘이 자고 있다.", "조심스럽게 옆에 누웠다."])
```

---

## Agent 클래스 (AI 행동)

Character와 별도로 `think/` 시스템의 Agent를 정의합니다.

```python
# assets/characters/noel.py (Character 클래스 아래에 정의)
from think import BaseAgent


class NoelAgent(BaseAgent):
    owner_unique_id = "noel"  # Character.unique_id와 일치

    # 일과표 (시간 → 활동)
    SCHEDULE = [
        (6, 0, "기상"),
        (7, 0, "식사"),
        (8, 0, "독서"),
        (12, 0, "식사"),
        (13, 0, "산책"),
        (18, 0, "식사"),
        (19, 0, "휴식"),
        (22, 0, "수면"),
    ]

    # 또는 요일/계절별 다중 스케줄
    # SCHEDULES = {
    #     "평일_봄": [...],
    #     "주말_봄": [...],
    # }
```

Agent의 상세 구조는 [schedule.md](schedule.md)와 [life.md](life.md)를 참조하세요.

---

## 아키타입 목록

텍스트 자동생성(`build_describe_rules`, `build_focus_rules`, `REACTION_PROFILE`)에 사용되는 기본 5가지 아키타입 + 톤 전환용 5가지:

| 아키타입 | 한국어 | 캐릭터 | 말투 특징 |
|----------|--------|--------|-----------|
| `stoic` | 과묵형 | 세라 | "......", "...뭐냐." |
| `gentle` | 온화형 | 밀라 | "...괜찮으세요?", "...조심하세요." |
| `cheerful` | 활발형 | 리나 | "안녕~!", "재밌겠다!" |
| `timid` | 소심형 | 유키 | "...저기...", "...죄송해요..." |
| `cold` | 냉담형 | 엘라 | "......", "...필요 없어요." |

---

## 톤 템플릿 시스템 (3D 좌표)

연애 반응(`:during` 묘사, `:start` 대사)은 **3D 좌표 기반**으로 자동 생성됩니다.

### 좌표 축

| 축 | 계산 | 의미 |
|----|------|------|
| X (호감-반발) | `affection - rebellion` | 감정 방향 |
| Y (욕망+성욕-순수도) | `arousal + desire - innocence` | 성적 각성도 |
| Z (자극 강도) | `gauge × 0.6 + total × 10` | 현재 자극 수준 |

### innocence (순수도)

아키타입 기본치 + 경험 기반 감소:

```python
ARCHETYPE_BASE_INNOCENCE = {
    "stoic": 30, "gentle": 50, "cheerful": 40,
    "timid": 70, "cold": 60,
}
# 경험에 따라 자동 감소 (experience_factor = total_gauge_exp / 1000)
innocence = base × max(0, 1 - experience_factor)
```

### 아키타입 → 톤 템플릿

10개 톤 템플릿 (`tone_templates/`):

| 톤 | 특징 | 사용 아키타입 |
|----|------|-------------|
| `stoic` | 과묵, 무심 | stoic |
| `gentle` | 온화, 배려 | gentle |
| `cheerful` | 활발, 솔직 | cheerful |
| `timid` | 수줍, 불안 | timid |
| `cold` | 냉담, 경계 | cold |
| `seductive` | 도발, 유혹 | (순수→욕망 전환 시) |
| `fierce` | 격렬, 투쟁 | (고반발 시) |
| `proud` | 오만, 통제 | (고자존 시) |
| `innocent` | 순수, 무지 | (고순수 시) |
| `devoted` | 헌신, 맹종 | (고복종 시) |

각 톤 파일은 `CATEGORY_TEMPLATES`(카테고리별 좌표→텍스트)와 `ACTION_TEMPLATES`(행위별 좌표→텍스트) 풀을 정의합니다.

### 특수 ACTION_LINES 키

톤 템플릿의 `ACTION_LINES`에는 행위별 대사 외에 시스템 이벤트 반응 키도 포함됩니다:

| 키 | 발생 조건 | 설명 |
|---|---|---|
| `npc_block_player` | NPC 주도 중 플레이어 능동 행위 차단 시 | NPC가 제지하는 대사 |
| `beg` | 플레이어가 "애원하기" 실행 시 | NPC의 애원 반응 |
| `afterglow_sensitive` | afterglow ≥ 40일 때 행위 시 | 절정 직후 극도 민감 |
| `afterglow_trembling` | afterglow ≥ 20일 때 행위 시 | 중간 여운 떨림 |
| `afterglow_fading` | afterglow < 20일 때 행위 시 | 여운 사라져감 |
| `afterglow_end` | afterglow가 0으로 전이 시 | 여운 완전 종료 |

이 키들은 `ROMANCE_REACTIONS`에서 캐릭터별 오버라이드도 가능합니다:

```python
ROMANCE_REACTIONS = {
    **Character.ROMANCE_REACTIONS,
    "npc_block_player:start": [
        ({"반발": 30}, ["...건드리면 죽인다."]),
        ({}, ["...건드리지 마."]),
    ],
    "beg:start": [
        ({"성욕": 70}, ["...알았다... 한 번만이다."]),
        ({}, ["...소용없다."]),
    ],
    "afterglow_sensitive:start": ["...만지지 마... 아직..."],
    "afterglow_end:start": ["...됐다."],
}
```

### 선택 알고리즘

`select_by_coord(pool, sx, sy, sz, k=3)` — K-nearest 방식:
1. 풀의 좌표 (x, y, z)와 현재 좌표 (sx, sy, sz)의 거리 계산 (Z_WEIGHT=2.0)
2. 가장 가까운 k=3개 후보 중 랜덤 선택
3. 3단계 fallback: 행위별 → 카테고리별 → 기본 텍스트

### 카테고리

행위는 5가지 카테고리로 분류:

| 카테고리 | 행위 예시 |
|---------|---------|
| `light` | hug, pat_head, ear_touch |
| `medium` | deep_kiss, breast_touch |
| `strong` | genital_caress, clit_rub |
| `penetration` | vaginal_penetration, anal_penetration |
| `rough` | hair_pull, slap |

---

## CHARACTER_REACTIONS / CHARACTER_LINES (캐릭터 오버레이)

캐릭터 고유 반응을 좌표 풀에 오버레이하여 아키타입 기본 텍스트를 부분 대체합니다.

### 구조

```python
CHARACTER_REACTIONS = {
    # 카테고리별 오버레이 (:during 3인칭 묘사)
    "light": [
        (30, 40, 0, "세라가 시선을 돌린다."),
        (70, 60, 0, "세라가 조용히 눈을 감는다."),
    ],
    # 행위별 오버레이
    "hug": [
        (50, 30, 0, "세라가 어색하게 팔을 내린다."),
    ],
}

CHARACTER_LINES = {
    # 카테고리별 오버레이 (:start 1인칭 대사)
    "light": [
        (30, 40, 0, "......뭐하는 거냐."),
    ],
    "hug": [
        (50, 30, 0, "...좋아서 하는 건 아니다."),
    ],
}
```

### REACTION_PROFILE 설정

```python
REACTION_PROFILE = {
    "archetype": "stoic",          # 기본 톤 템플릿
    "name": "세라",                # 3인칭 묘사용 이름
    "char_reactions": CHARACTER_REACTIONS,  # :during 오버레이
    "char_lines": CHARACTER_LINES,         # :start 오버레이
}
```

**병합 순서**: 캐릭터 오버레이와 아키타입 풀이 같은 좌표면 캐릭터 쪽이 우선, 나머지는 아키타입 유지.

---

## 순수/욕망 행동 게이팅

4축 관계(호감/반발/순수/욕망)가 NPC 행동 허용/거절에 영향:

### 4분면 매트릭스

| 상태 | 호감행동(선물/대화/데이트) | 애정행동(스킨십) | NPC 주도 | 강제 저항 |
|------|--------------------------|-----------------|---------|---------|
| 애인 (호감↑ + 욕망↑) | ✅ 허용 | ✅ 허용 | ✅ 발생 | 정상 |
| 정욕 (반발↑ + 욕망↑) | ❌ 거절 | ✅ 거부불가 | ✅ 발생 | ❌ 저항X |
| 친구 (호감↑ + 순수↑) | ✅ 허용 | ❌ 거절 | ❌ 없음 | 정상 |
| 타인 (반발↑ + 순수↑) | ❌ 거절 | ❌ 거절 | ❌ 없음 | 정상 |

**경계값**: 호감 ≥ 50 (ROMANCE_ENTRY_THRESHOLD), 욕망 ≥ 40 (DES_LABEL_THRESHOLD)

### 적용 위치

| 파일 | 함수 | 게이팅 |
|------|------|--------|
| `romance.py` | `can_start_romance()` | 욕망 < 40 → 스킨십 진입 거절 |
| `npc_initiative.py` | `calculate_resistance_gain()` | 욕망 ≥ 40 → 강제 저항 0 |
| `base.py` | `should_initiate_skinship()` | 욕망 < 40 → NPC 주도 불가 |
| `date.py` | `will_accept_date()` | 반발 ≥ 50 → 데이트 거절 |

---

## 퀘스트 등록

캐릭터 개인 퀘스트는 클래스 외부에서 할당합니다.

```python
# assets/characters/noel.py 파일 하단
Noel.CHARACTER_QUESTS = [
    # quest.py의 Quest 인스턴스 리스트
]
```

퀘스트가 없는 캐릭터는 생략 가능 (base.py에서 `CHARACTER_QUESTS: list = []` 기본값 제공).

---

## 속성 정의 순서 (권장)

NPC 파일 내 속성 배치 순서를 통일하면 유지보수가 쉬워집니다.

```
1. 기본 속성        unique_id, name, type, sexual_orientation, hearing_type
2. props            초기 속성 dict
3. actions          포커스 메뉴 액션 목록
4. mood             초기 감정
5. TALK_TOPICS      대화 주제
6. TALK_RULES       대화 규칙
7. DESCRIBE_RULES   장소 묘사
8. FOCUS_RULES      포커스 묘사
9. self_comfort_*   자위 설정
10. INITIATIVE_*    NPC 주도 설정
11. STEALTH_*       은신 반응
12. EQUIP_CHANGE_*  장비 변경 반응
13. FRIENDLY_TALK_* 친밀 대화
14. PROGRESS_*      진척 대화
15. ROOM_PRIVACY_*  프라이버시
16. ROMANCE_SOUND_* 소리 프로필
17. ROMANCE_DISCOVERY_* 목격 반응
18. GIFT_PREFERENCES 선물 선호
19. SEXUAL_PREFERENCES 성적 선호
20. REACTION_PROFILE 반응 생성 프로필
21. ROMANCE_REACTIONS 연애 반응
22. 메서드           _first_meet_handler, _handle_mode_aftermath, ...
23. on_bed_*        침대 반응
```

---

## 체크리스트

신규 캐릭터 추가 시 확인사항:

- [ ] `unique_id` 고유성 확인
- [ ] `props`에 필수 키 포함 (성별, 생존:체력/최대체력/포만감/최대포만감)
- [ ] `_first_meet_handler` 구현 (generator, `mark_first_meet_done()` 호출)
- [ ] `_handle_mode_aftermath` 구현
- [ ] `_handle_pregnancy_event` 구현
- [ ] `on_bed_awake` / `on_bed_sleeping` 구현
- [ ] `assets/characters/__init__.py`에 등록
- [ ] Agent 클래스 정의 (`owner_unique_id` 일치)
- [ ] 테스트 실행: `python tests/run_tests.py -v`
