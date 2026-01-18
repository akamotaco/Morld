# 퀘스트 시스템 (Quest System)

## 개요

플레이어가 수행할 수 있는 목표 기반 퀘스트 시스템.
이벤트 또는 NPC 대화를 통해 퀘스트를 획득하고, 조건 충족 시 완료됩니다.

---

## 1. 시스템 구조

### 파일 구조
```
scenarios/scenario02/python/
├── quest/
│   ├── __init__.py         # 퀘스트 매니저 + morld API
│   ├── conditions.py       # 퀘스트 조건 정의 및 체크
│   ├── rewards.py          # 퀘스트 보상 처리
│   └── quests/             # 범용 퀘스트 정의 폴더
│       ├── __init__.py     # 퀘스트 등록
│       └── main_quests.py  # 메인 스토리 퀘스트
├── assets/
│   └── characters/
│       └── sera.py         # 캐릭터별 개인 퀘스트 (CHARACTER_QUESTS)
├── ui.py                   # UI (퀘스트 버튼 추가)
└── events/                 # 이벤트 (퀘스트 트리거)
```

### 설계 원칙: 캐릭터 파일 독립성

**문제**: 캐릭터는 단일 파일로 독립적이어야 하지만, 일부 퀘스트는 특정 캐릭터와 깊이 연관됨

**해결책: 하이브리드 구조**

| 퀘스트 유형 | 정의 위치 | 예시 |
|-------------|----------|------|
| 메인 스토리 | `quest/quests/main_quests.py` | 챕터 진행, 세계관 이벤트 |
| 범용 사이드 | `quest/quests/side_quests.py` | 수집, 탐험 등 |
| **캐릭터 개인 퀘스트** | `assets/characters/sera.py` | 세라 호감도 퀘스트, 개인 스토리 |

**캐릭터 개인 퀘스트 특징:**
- 해당 캐릭터 파일 내에 `CHARACTER_QUESTS` dict로 정의
- 캐릭터와 관련된 대화, 조건, 보상이 한 파일에 모임
- 캐릭터 삭제 시 관련 퀘스트도 자동으로 제거됨

### 핵심 컴포넌트

| 컴포넌트 | 파일 | 역할 |
|----------|------|------|
| QuestManager | `quest/__init__.py` | 퀘스트 상태 관리, 조건 체크, 완료 처리 |
| QuestCondition | `quest/conditions.py` | 퀘스트 조건 정의 및 판정 |
| QuestReward | `quest/rewards.py` | 보상 지급 처리 |
| Quest | `quest/quests/*.py` | 개별 퀘스트 정의 |

---

## 2. 퀘스트 상태

```python
class QuestStatus(Enum):
    LOCKED = "locked"           # 잠금 (조건 미충족)
    AVAILABLE = "available"     # 수락 가능
    IN_PROGRESS = "in_progress" # 진행 중
    COMPLETED = "completed"     # 완료 (보상 수령 전)
    FINISHED = "finished"       # 완료 (보상 수령 후)
```

### 상태 전이

```
LOCKED ──(선행 퀘스트 완료)──> AVAILABLE
           │
           ▼
AVAILABLE ──(퀘스트 수락)──> IN_PROGRESS
           │
           ▼
IN_PROGRESS ──(조건 충족)──> COMPLETED
           │
           ▼
COMPLETED ──(보상 수령)──> FINISHED
```

---

## 3. 퀘스트 정의

### Quest 클래스

```python
@register_quest
class FindSera(Quest):
    """세라 찾기 - 메인 퀘스트 예시"""

    unique_id = "main_find_sera"
    name = "세라를 찾아서"
    description = "숲 어딘가에 있다는 사냥꾼 세라를 찾아가자."
    category = "main"  # main, side, daily

    # 선행 조건 (이 퀘스트를 받으려면)
    prerequisites = []  # 선행 퀘스트 unique_id 리스트

    # 완료 조건
    conditions = [
        {"type": "reach", "region_id": 0, "location_id": 5},  # 숲 입구 도착
        {"type": "meet", "target": "sera"},  # 세라와 만남
    ]

    # 보상
    rewards = [
        {"type": "item", "item_id": "bread", "count": 3},
        {"type": "prop", "prop": "관계:세라:호감", "value": 10},
    ]

    # 퀘스트 지급자 (None이면 이벤트로 지급)
    giver = "mila"  # 밀라에게서 받음

    # 퀘스트 완료 보고 대상 (None이면 자동 완료)
    reporter = None  # 조건 충족 시 자동 완료

    # 퀘스트 대화
    dialogs = {
        "offer": [  # 퀘스트 제안 시
            "[밀라]",
            "저기... 혹시 세라를 찾아줄 수 있어요?",
            "숲 쪽에 있을 거예요...",
        ],
        "accept": [  # 수락 시
            "[밀라]",
            "고마워요! 조심해서 다녀오세요.",
        ],
        "decline": [  # 거절 시
            "[밀라]",
            "...그래요. 바쁘시겠죠.",
        ],
        "progress": [  # 진행 중 대화
            "[밀라]",
            "세라는 찾았어요...?",
        ],
        "complete": [  # 완료 시
            "[밀라]",
            "세라를 만났군요! 정말 다행이에요.",
        ],
    }
```

---

## 4. 퀘스트 조건 타입

### 4.1 위치 도착 (reach)

```python
{"type": "reach", "region_id": 0, "location_id": 5}
```

특정 위치에 도착하면 충족됩니다.

**이벤트 연동:** `on_reach` 이벤트에서 체크

### 4.2 NPC 만남 (meet)

```python
{"type": "meet", "target": "sera"}  # unique_id
```

특정 NPC와 만나면 충족됩니다.

**이벤트 연동:** `on_meet` 이벤트에서 체크

### 4.3 아이템 획득 (collect)

```python
{"type": "collect", "item": "apple", "count": 5}
```

특정 아이템을 지정 개수 이상 보유하면 충족됩니다.

**체크 시점:** 아이템 획득 시, 퀘스트 UI 열 때

### 4.4 아이템 전달 (deliver)

```python
{"type": "deliver", "item": "letter", "target": "sera", "count": 1}
```

특정 NPC에게 아이템을 전달하면 충족됩니다.

**처리 방식:**
1. 해당 NPC와 대화 시 전달 옵션 표시
2. 전달 선택 시 아이템 소모 + 조건 충족

### 4.5 대화 (talk)

```python
{"type": "talk", "target": "mila", "dialog_id": "about_forest"}
```

특정 NPC와 특정 대화를 나누면 충족됩니다.

**이벤트 연동:** 대화 완료 시 체크

### 4.6 처치 (defeat)

```python
{"type": "defeat", "target": "wolf", "count": 3}
```

특정 대상을 처치하면 충족됩니다 (전투 시스템 연동 시).

### 4.7 시간 경과 (wait)

```python
{"type": "wait", "hours": 24}
```

퀘스트 수락 후 일정 시간이 경과하면 충족됩니다.

### 4.8 복합 조건 (all/any)

```python
# 모든 조건 충족 (AND)
{"type": "all", "conditions": [
    {"type": "collect", "item": "apple", "count": 3},
    {"type": "collect", "item": "bread", "count": 2},
]}

# 하나라도 충족 (OR)
{"type": "any", "conditions": [
    {"type": "reach", "region_id": 0, "location_id": 1},
    {"type": "reach", "region_id": 0, "location_id": 2},
]}
```

---

## 5. 보상 타입

### 5.1 아이템 지급 (item)

```python
{"type": "item", "item": "gold_coin", "count": 10}
```

### 5.2 속성 변경 (prop)

```python
{"type": "prop", "target": "sera", "prop": "관계:플레이어:호감", "value": 10}
```

### 5.3 퀘스트 해금 (unlock_quest)

```python
{"type": "unlock_quest", "quest": "main_chapter2"}
```

### 5.4 위치 해금 (unlock_location)

```python
{"type": "unlock_location", "region_id": 1, "location_id": 0}
```

---

## 6. UI 시스템

### 6.1 퀘스트 버튼

`ui.py`의 `get_action_text()`에 퀘스트 버튼 추가:

```python
def get_action_text():
    lines = []

    # 기존 버튼들...
    lines.append("  [url=inventory]인벤토리[/url]")
    lines.append("  [url=quest]퀘스트[/url]")  # 새로 추가

    return "\n".join(lines)
```

### 6.2 퀘스트 UI (다이얼로그)

```
┌────────────────────────────────────────┐
│ [퀘스트]                                │
│                                        │
│ [진행 중]                               │
│   ▶ 세라를 찾아서                       │
│     - 숲 입구에 도착하기 (✓)            │
│     - 세라와 만나기 ( )                 │
│                                        │
│ [완료]                                  │
│   ▶ 밀라의 부탁 (보상 수령 가능)         │
│                                        │
│              [닫기]                     │
└────────────────────────────────────────┘
```

### 6.3 진행 상황 표시

```python
def render_quest_ui():
    """퀘스트 UI 렌더링"""
    lines = ["[b]퀘스트[/b]", ""]

    # 진행 중 퀘스트
    in_progress = quest_manager.get_quests_by_status(QuestStatus.IN_PROGRESS)
    if in_progress:
        lines.append("[진행 중]")
        for quest in in_progress:
            lines.append(f"  ▶ {quest.name}")
            for cond in quest.conditions:
                status = "✓" if cond.is_met() else " "
                lines.append(f"    - {cond.description} ({status})")
        lines.append("")

    # 완료 퀘스트 (보상 대기)
    completed = quest_manager.get_quests_by_status(QuestStatus.COMPLETED)
    if completed:
        lines.append("[완료 - 보상 수령 가능]")
        for quest in completed:
            lines.append(f"  ▶ [url=@proc:claim:{quest.unique_id}]{quest.name}[/url]")
        lines.append("")

    # 완료된 퀘스트 (접기/펼치기)
    finished = quest_manager.get_quests_by_status(QuestStatus.FINISHED)
    if finished:
        lines.append("[url=toggle:finished]▶ 완료된 퀘스트 ({len(finished)})[/url]")
        lines.append("[hidden=finished]")
        for quest in finished:
            lines.append(f"  - {quest.name}")
        lines.append("[/hidden=finished]")

    lines.append("")
    lines.append("[url=@ret:close]닫기[/url]")

    return "\n".join(lines)
```

---

## 7. 이벤트 연동

### 7.1 on_reach 이벤트

```python
# events/reach/quest_check.py
@register
class QuestReachCheck(OnReachEvent):
    def handle(self, region_id, location_id, **ctx):
        from quest import quest_manager
        quest_manager.check_reach_conditions(region_id, location_id)
```

### 7.2 on_meet 이벤트

```python
# events/meet/quest_check.py
@register
class QuestMeetCheck(OnMeetEvent):
    def handle(self, unit_id, other_id, **ctx):
        from quest import quest_manager
        quest_manager.check_meet_conditions(unit_id, other_id)
```

### 7.3 퀘스트 지급 (NPC 대화)

```python
# assets/characters/mila.py
class Mila(Character):
    def talk(self):
        from quest import quest_manager

        # 지급 가능한 퀘스트 체크
        available = quest_manager.get_available_quests_from(self.unique_id)

        if available:
            quest = available[0]
            # 퀘스트 제안 다이얼로그
            result = yield from quest.offer_dialog()
            if result == "accept":
                quest_manager.accept_quest(quest.unique_id)
            return

        # 진행 중 퀘스트 체크
        in_progress = quest_manager.get_in_progress_quests_for(self.unique_id)
        if in_progress:
            quest = in_progress[0]
            yield morld.dialog(quest.dialogs["progress"])
            return

        # 일반 대화
        yield morld.dialog(["안녕하세요~"])
```

---

## 8. morld API

### 퀘스트 관리

```python
import morld

# 퀘스트 지급
morld.give_quest(quest_id)

# 퀘스트 완료 체크 (수동)
morld.check_quest_conditions(quest_id)

# 퀘스트 강제 완료
morld.complete_quest(quest_id)

# 퀘스트 상태 조회
status = morld.get_quest_status(quest_id)

# 진행 중 퀘스트 목록
quests = morld.get_active_quests()

# 퀘스트 조건 진행률
progress = morld.get_quest_progress(quest_id)
# {"current": 2, "total": 3, "conditions": [...]}
```

### 조건 업데이트

```python
# 아이템 수집 조건 업데이트 (아이템 획득 시 자동 호출)
morld.update_collect_condition(player_id, item_id, count)

# 처치 조건 업데이트
morld.update_defeat_condition(player_id, target_id)
```

---

## 9. 데이터 저장

퀘스트 상태는 플레이어 props에 저장됩니다:

```python
# 퀘스트 상태
"퀘스트:main_find_sera:상태": "in_progress"

# 조건 진행 상황 (개수 기반)
"퀘스트:main_find_sera:collect:apple": 3

# 퀘스트 수락 시각 (wait 조건용)
"퀘스트:main_find_sera:수락시각": 1440
```

---

## 10. 구현 순서

### Phase 1: 기본 구조
1. `quest/__init__.py` - QuestManager 기본 구조
2. `quest/conditions.py` - 조건 클래스 정의
3. `quest/rewards.py` - 보상 클래스 정의

### Phase 2: UI
1. `ui.py`에 퀘스트 버튼 추가
2. 퀘스트 다이얼로그 UI 구현
3. `MetaActionHandler`에 `quest` 액션 추가

### Phase 3: 조건 시스템
1. reach 조건 (on_reach 이벤트 연동)
2. meet 조건 (on_meet 이벤트 연동)
3. collect 조건 (아이템 획득 연동)
4. deliver 조건 (NPC 대화 연동)

### Phase 4: NPC 연동
1. Character 클래스에 퀘스트 대화 메서드 추가
2. 퀘스트 지급/보고 대화 처리
3. 전달 조건 UI

### Phase 5: 테스트 퀘스트
1. 메인 퀘스트 1개 작성
2. 사이드 퀘스트 1개 작성
3. 테스트 및 디버깅

---

## 11. 수정/생성 파일 목록

| 파일 | 작업 |
|------|------|
| `quest/__init__.py` | 신규 생성 - QuestManager |
| `quest/conditions.py` | 신규 생성 - 조건 클래스 |
| `quest/rewards.py` | 신규 생성 - 보상 클래스 |
| `quest/quests/__init__.py` | 신규 생성 - 퀘스트 등록 |
| `quest/quests/main_quests.py` | 신규 생성 - 메인 퀘스트 |
| `ui.py` | 수정 - 퀘스트 버튼 추가 |
| `assets/base.py` | 수정 - Character에 퀘스트 대화 메서드 |
| `events/reach/quest_check.py` | 신규 생성 - reach 조건 체크 |
| `events/meet/quest_check.py` | 신규 생성 - meet 조건 체크 |
| `scripts/MetaActionHandler/` | 수정 - quest 액션 핸들러 |

---

## 12. 예시 퀘스트

### 메인 퀘스트: 세라를 찾아서

```python
@register_quest
class MainFindSera(Quest):
    unique_id = "main_find_sera"
    name = "세라를 찾아서"
    description = "밀라의 부탁으로 숲에 있는 세라를 찾아가자."
    category = "main"

    giver = "mila"
    reporter = None  # 자동 완료

    conditions = [
        {"type": "meet", "target": "sera"},
    ]

    rewards = [
        {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 5},
    ]

    dialogs = {
        "offer": [
            "[밀라]",
            "저기... 부탁 하나만 해도 될까요?",
            "세라가 숲에 사냥 나갔는데, 너무 오래 안 오네요...",
            "한번 찾아봐 주실 수 있어요?",
        ],
        "accept": ["[밀라]", "감사해요! 조심해서 다녀오세요."],
        "decline": ["[밀라]", "...그래요. 바쁘시겠죠."],
        "complete": ["세라를 만났다. 밀라에게 알려줘야겠다."],
    }
```

### 사이드 퀘스트: 사과 수집

```python
@register_quest
class SideCollectApples(Quest):
    unique_id = "side_collect_apples"
    name = "밀라의 요리 재료"
    description = "밀라가 요리에 쓸 사과 5개를 모아오자."
    category = "side"

    prerequisites = ["main_find_sera"]  # 세라 찾기 이후 해금
    giver = "mila"
    reporter = "mila"  # 밀라에게 보고

    conditions = [
        {"type": "collect", "item": "apple", "count": 5},
    ]

    rewards = [
        {"type": "item", "item": "apple_pie", "count": 1},
        {"type": "prop", "target": "player", "prop": "관계:밀라:호감", "value": 3},
    ]

    dialogs = {
        "offer": [
            "[밀라]",
            "저... 사과를 좀 구해올 수 있어요?",
            "파이를 만들고 싶은데, 재료가 부족해서요.",
            "5개만 있으면 될 것 같아요!",
        ],
        "accept": ["[밀라]", "고마워요! 숲에 사과나무가 있을 거예요."],
        "decline": ["[밀라]", "...알겠어요."],
        "progress": ["[밀라]", "사과는 모았어요...?"],
        "complete": [
            "[밀라]",
            "와! 고마워요!",
            "이걸로 맛있는 파이를 만들어 드릴게요!",
        ],
    }
```

---

## 13. 캐릭터 개인 퀘스트 (CHARACTER_QUESTS)

캐릭터와 깊이 연관된 퀘스트는 해당 캐릭터 파일에 직접 정의합니다.

### 13.1 캐릭터 파일 내 정의

```python
# assets/characters/sera.py
from assets.base import Character
from quest import Quest

class Sera(Character):
    unique_id = "sera"
    name = "세라"

    # 캐릭터 개인 퀘스트 정의
    CHARACTER_QUESTS = [
        {
            "unique_id": "sera_trust_1",
            "name": "세라의 신뢰 I",
            "description": "세라와 더 친해지자.",
            "category": "personal",

            "prerequisites": ["main_find_sera"],
            "giver": "sera",
            "reporter": "sera",

            "conditions": [
                {"type": "prop", "target": "player", "prop": "관계:세라:호감", "min_value": 30},
            ],

            "rewards": [
                {"type": "item", "item": "sera_pendant", "count": 1},
                {"type": "prop", "target": "player", "prop": "관계:세라:신뢰", "value": 1},
            ],

            "dialogs": {
                "offer": [
                    "[세라]",
                    "......",
                    "...네가 조금은 믿어지기 시작했어.",
                ],
                "accept": ["[세라]", "...나를 계속 찾아와."],
                "complete": [
                    "[세라]",
                    "......",
                    "...이거.",
                    "(세라가 무언가를 건넨다)",
                    "...어머니가 주신 거야. 너한테 주고 싶었어.",
                ],
            },
        },
        {
            "unique_id": "sera_hunt_together",
            "name": "함께하는 사냥",
            "description": "세라와 함께 사냥을 나가자.",
            "category": "personal",

            "prerequisites": ["sera_trust_1"],
            "giver": "sera",
            "reporter": "sera",

            "conditions": [
                {"type": "meet", "target": "sera"},
                {"type": "reach", "region_id": 0, "location_id": 3},  # 숲 깊은 곳
            ],

            "rewards": [
                {"type": "prop", "target": "player", "prop": "관계:세라:호감", "value": 15},
                {"type": "item", "item": "wolf_pelt", "count": 1},
            ],

            "dialogs": {
                "offer": [
                    "[세라]",
                    "...나랑 같이 사냥 갈래?",
                    "숲 깊은 곳에 좋은 사냥터가 있어.",
                ],
                "accept": ["[세라]", "...따라와. 뒤처지지 마."],
                "progress": ["[세라]", "...아직 멀었어. 서둘러."],
                "complete": [
                    "[세라]",
                    "...잘했어.",
                    "(세라가 희미하게 미소 짓는다)",
                    "...다음에 또 가자.",
                ],
            },
        },
    ]
```

### 13.2 base.py의 Character 클래스 수정

```python
# assets/base.py
class Character(Unit):
    # 캐릭터 개인 퀘스트 (서브클래스에서 오버라이드)
    CHARACTER_QUESTS: list = []

    @classmethod
    def get_character_quests(cls) -> list:
        """캐릭터 개인 퀘스트 목록 반환"""
        return cls.CHARACTER_QUESTS
```

### 13.3 퀘스트 자동 등록

```python
# quest/__init__.py
def register_character_quests():
    """모든 캐릭터의 개인 퀘스트를 등록"""
    from assets import get_all_character_classes

    for char_cls in get_all_character_classes():
        for quest_data in char_cls.get_character_quests():
            # dict를 Quest 객체로 변환하여 등록
            quest = Quest.from_dict(quest_data)
            quest_registry[quest.unique_id] = quest
```

### 13.4 장점

| 장점 | 설명 |
|------|------|
| **파일 독립성** | 캐릭터 파일 하나만 보면 그 캐릭터의 모든 것을 알 수 있음 |
| **자동 삭제** | 캐릭터 파일 삭제 시 관련 퀘스트도 자동으로 제거됨 |
| **응집도** | 대화, 조건, 보상이 캐릭터와 함께 관리됨 |
| **확장성** | 새 캐릭터 추가 시 퀘스트도 함께 추가 가능 |

### 13.5 퀘스트 분류 기준

| 분류 | 정의 위치 | 기준 |
|------|----------|------|
| 메인 퀘스트 | `quest/quests/main_quests.py` | 스토리 진행, 여러 캐릭터 관련 |
| 범용 사이드 | `quest/quests/side_quests.py` | 특정 캐릭터에 귀속되지 않음 |
| 개인 퀘스트 | `assets/characters/*.py` | 특정 캐릭터와 깊이 연관, 호감도/신뢰 퀘스트 |

---

## 14. 퀘스트 수락 시스템

### 14.1 NPC 심부름 메뉴 (권장)

퀘스트는 **NPC와의 대화**를 통해서만 수락할 수 있습니다.
퀘스트 UI에서 직접 수락하는 것은 금지됩니다.

**심부름 액션:**
- NPC를 클릭(Focus)하면 `[심부름]` 버튼이 표시됩니다
- 단, 해당 NPC가 제공할 수 있는 퀘스트가 있을 때만 표시 (`#` 조건부)
- `can:errand` prop으로 동적 관리

**작동 방식:**
1. NPC Focus 시 `assets/__init__.py`의 `_update_errand_visibility()` 호출
2. `quest_manager.get_available_quests_from(npc_id)` 체크
3. 퀘스트가 있으면 `can:errand = 1`, 없으면 `can:errand = 0`
4. `심부름#` 액션은 `can:errand >= 1`일 때만 표시

**코드 위치:**
- `assets/base.py` - `Character.errand()` 메서드
- `assets/__init__.py` - `_update_errand_visibility()` 함수
- 각 캐릭터 파일 - `"call:errand:심부름#"` 액션

### 14.2 첫 만남 판정 시스템

NPC와의 첫 만남 여부는 `관계:XX:진척도` prop으로 판정합니다.

**판정 기준:**
- `관계:{NPC이름}:진척도 <= 0` → 첫 만남
- 첫 만남 이벤트 완료 후 `진척도 = 1`로 설정

**"아무 NPC와 만남" 조건:**
- 모든 `관계:*:진척도` 합산 >= 1 이면 누군가를 만난 것
- `quest/conditions.py`의 `meet_anyone` 조건 타입 사용

**코드 위치:**
- `assets/base.py` - `Character.is_first_meet()`, `mark_first_meet_done()`
- `quest/conditions.py` - `_check_meet_anyone()`
- 각 캐릭터 파일 - `_first_meet_handler()` Generator

### 14.3 챕터1 시작 퀘스트

챕터1 시작 시 자동으로 "현재 상황을 파악하자" 퀘스트가 부여됩니다.

**퀘스트 정보:**
- `unique_id`: `main_understand_situation`
- 조건: `meet_anyone` (아무 NPC와 만남)
- 보상: `main_meet_everyone` 퀘스트 해금

**자동 부여 시점:**
- `chapters/chapter_1.py`의 `post_restore()`에서 `_start_chapter_quest()` 호출
- `quest_manager.start_quest()` 실행

---

## 15. 테스트 절차

### 15.1 퀘스트 수락 방법

퀘스트는 두 가지 방법으로 수락됩니다:

| 방법 | `giver` 설정 | 수락 방식 |
|------|-------------|----------|
| **자동 지급** | `giver = None` | 선행 조건 충족 시 자동으로 IN_PROGRESS |
| **NPC 대화** | `giver = "npc_id"` | NPC와 대화 → 제안 → 수락/거절 |

**현재 정의된 퀘스트 수락 방식:**

| 퀘스트 | giver | 수락 방식 |
|--------|-------|----------|
| `main_meet_everyone` | None | 게임 시작 시 자동 (챕터 1) |
| `sub_meet_mila/sera/lina` | None | `main_meet_everyone` 수락 시 자동 |
| `main_journey_to_city` | `"mila"` | 밀라와 대화하여 수락 |
| `sub_meet_yuki/ella` | None | 도시 도착 퀘스트 완료 시 자동 |
| 사이드 퀘스트들 | None | 선행 조건 충족 시 자동 |

### 15.2 테스트 시나리오 A: 자동 지급 퀘스트 (giver = None)

**테스트 대상:** `main_meet_everyone`, `sub_meet_mila`, `sub_meet_sera`, `sub_meet_lina`

**절차:**

1. **게임 시작 (챕터 1)**
   - 프롤로그(챕터 0) 완료 후 챕터 1 진입
   - 또는 디버그로 챕터 1 직접 시작

2. **퀘스트 UI 확인**
   - 화면 하단의 `[퀘스트]` 버튼 클릭
   - `[진행 중]` 섹션에 다음 퀘스트가 있어야 함:
     - `저택 식구들`
     - `밀라 만나기`
     - `세라 만나기`
     - `리나 만나기`

3. **퀘스트 완료 테스트**
   - 밀라가 있는 위치(주방)로 이동
   - 밀라와 만남 → `sub_meet_mila` 완료
   - 퀘스트 UI에서 완료 확인

**예상 결과:**
- `giver = None` + `prerequisites` 충족 → 자동으로 IN_PROGRESS
- NPC 만남 시 `on_meet` 이벤트 → 조건 체크 → 완료 처리

### 15.3 테스트 시나리오 B: NPC 대화 수락 퀘스트 (giver = "npc")

**테스트 대상:** `main_journey_to_city` (giver = "mila")

**절차:**

1. **선행 조건 확인**
   - `prerequisites = []` 이므로 즉시 AVAILABLE 상태

2. **밀라와 대화**
   - 밀라가 있는 위치로 이동
   - 밀라 클릭 → `[대화]` 선택
   - 퀘스트 제안 다이얼로그 표시:
     ```
     [밀라]
     저택에서 조금 더 가면 도시가 있어요...

     [수락]  [거절]
     ```

3. **수락 시**
   - `[수락]` 클릭 → IN_PROGRESS 상태로 변경
   - 퀘스트 UI에서 `도시로의 여정` 확인

4. **거절 시**
   - `[거절]` 클릭 → AVAILABLE 상태 유지
   - 다시 대화하면 재제안

**예상 결과:**
- NPC talk() 메서드에서 `quest_manager.get_available_quests_from()` 호출
- 퀘스트 제안 → 수락/거절 선택 → 상태 변경

### 15.4 테스트 시나리오 C: 조건 충족 및 보상 수령

**테스트 대상:** `sub_meet_mila` (reporter = None, 자동 완료)

**절차:**

1. **퀘스트 진행 중 상태 확인**
   - 퀘스트 UI → `밀라 만나기` 클릭
   - 조건 표시: `○ 밀라와 만나기`

2. **조건 충족**
   - 밀라가 있는 위치로 이동
   - `on_meet` 이벤트 발생 → 조건 체크

3. **자동 완료 확인** (reporter = None)
   - 조건 충족 시 자동으로 COMPLETED → 보상 지급 → FINISHED
   - 행동 로그: "퀘스트 '밀라 만나기' 완료! 보상 수령."

**예상 결과:**
- reporter가 None이면 자동 완료 및 보상 지급
- reporter가 있으면 COMPLETED 상태 유지, NPC에게 보고해야 FINISHED

### 15.5 테스트 시나리오 D: 반복 퀘스트 (repeatable = True)

**테스트 대상:** `daily_patrol`, `daily_fishing`

**절차:**

1. **선행 조건 충족**
   - `daily_patrol`은 `sub_meet_sera` 완료 필요
   - 세라를 먼저 만나서 선행 퀘스트 완료

2. **퀘스트 수락 확인**
   - 퀘스트 UI에서 `저택 순찰` 확인 (AVAILABLE → IN_PROGRESS)

3. **조건 충족 및 완료**
   - 앞마당, 뒷마당, 숲 입구 방문
   - 세라에게 보고 (reporter = "sera")

4. **반복 확인**
   - 완료 후 `완료된 퀘스트` 목록이 아닌 `수락 가능`으로 복귀
   - 다음 날(게임 내 시간) 다시 수락 가능

**예상 결과:**
- `repeatable = True` → FINISHED 대신 AVAILABLE로 복귀
- 같은 날 재수락 불가 (완료일 체크)

### 15.6 테스트 시나리오 E: 챕터1 시작 퀘스트

**테스트 대상:** `main_understand_situation` (현재 상황을 파악하자)

**절차:**

1. **챕터1 진입**
   - 프롤로그(챕터 0) 완료 후 챕터 1 전환
   - 또는 디버그로 챕터 1 직접 로드

2. **퀘스트 자동 부여 확인**
   - 퀘스트 UI → `[진행 중]` 섹션에 `현재 상황을 파악하자` 표시
   - 조건: `누군가와 만나기`

3. **아무 NPC와 만남**
   - 밀라/세라/리나 중 아무 NPC 있는 곳으로 이동
   - NPC와 만남 → `관계:XX:진척도 = 1` 설정됨

4. **퀘스트 완료 확인**
   - `meet_anyone` 조건 충족 → 자동 완료
   - `main_meet_everyone` 퀘스트 해금 확인

**예상 결과:**
- 챕터1 시작 시 자동으로 퀘스트 부여
- 아무 NPC와 만나면 완료, 다음 퀘스트 해금

### 15.7 테스트 시나리오 F: 심부름 메뉴

**테스트 대상:** NPC `errand()` 메서드 및 `can:errand` prop 관리

**절차:**

1. **퀘스트가 없는 NPC Focus**
   - 현재 제공 가능한 퀘스트가 없는 NPC 클릭
   - `[심부름]` 버튼이 **표시되지 않음** 확인

2. **퀘스트가 있는 NPC Focus**
   - 세라에게 `sera_fishing` 퀘스트 활성화 (선행조건: `sub_meet_sera` 완료)
   - 세라 클릭 → `[심부름]` 버튼 표시 확인

3. **심부름 클릭**
   - `[심부름]` 클릭 → 퀘스트 목록 다이얼로그 표시
   - 퀘스트 선택 → 제안 다이얼로그 → 수락/거절

4. **퀘스트 수락 후**
   - 수락 시 IN_PROGRESS 상태로 변경
   - 다시 세라 클릭 → `[심부름]` 버튼 숨김 (제공할 퀘스트 없음)

**예상 결과:**
- `_update_errand_visibility()`가 NPC Focus 시 호출됨
- `can:errand` prop이 동적으로 관리됨
- 퀘스트가 없으면 심부름 버튼 숨김

### 15.8 테스트 시나리오 G: 첫 만남 판정

**테스트 대상:** `관계:XX:진척도` 기반 first meet 판정

**절차:**

1. **초기 상태 확인**
   - 플레이어 props에 `관계:세라:진척도` 없음 (= 0)
   - `is_first_meet(player_id)` → True

2. **세라와 첫 만남**
   - 세라가 있는 위치로 이동
   - `on_meet` 이벤트 → `on_meet_player()` 호출
   - 첫 만남 다이얼로그 표시

3. **첫 만남 완료 후**
   - `관계:세라:진척도 = 1` 설정됨
   - `is_first_meet(player_id)` → False

4. **재만남**
   - 다시 세라와 만남
   - 첫 만남 다이얼로그 **표시되지 않음**
   - (NPC 주도 스킨십 조건 체크로 넘어감)

**예상 결과:**
- 첫 만남 여부가 `관계:XX:진척도`로 영구 저장됨
- 첫 만남 이벤트는 한 번만 발생

### 15.9 디버그 명령어

퀘스트 상태를 직접 확인/조작하려면 Python 콘솔 사용:

```python
# 퀘스트 상태 확인
from quest import quest_manager, QuestStatus
status = quest_manager.get_quest_status("main_meet_everyone")
print(f"상태: {status}")

# 퀘스트 강제 지급 (AVAILABLE → IN_PROGRESS)
quest_manager.give_quest("main_meet_everyone")

# 퀘스트 강제 완료 (IN_PROGRESS → COMPLETED)
quest_manager.complete_quest("main_meet_everyone")

# 보상 수령 (COMPLETED → FINISHED)
quest_manager.claim_reward("main_meet_everyone")

# 진행 중 퀘스트 목록
for q in quest_manager.get_active_quests():
    print(f"- {q.name} ({q.unique_id})")

# 모든 퀘스트 상태 출력
from quest import _quest_registry
for quest_id in _quest_registry:
    status = quest_manager.get_quest_status(quest_id)
    print(f"{quest_id}: {status.value}")
```

### 15.10 현재 미구현 사항

| 기능 | 상태 | 설명 |
|------|------|------|
| NPC 대화에서 퀘스트 제안 | ❌ 미구현 | `talk()` 메서드에서 `get_available_quests_from()` 호출 필요 |
| 퀘스트 UI에서 직접 수락 | ❌ 미구현 | 디버그 모드에서만 표시, 클릭해도 수락 안 됨 |
| 자동 지급 트리거 | ⚠️ 부분 구현 | 챕터 시작 시 자동 지급 이벤트 필요 |

### 15.11 NPC 대화 퀘스트 구현 예시

밀라의 `talk()` 메서드에 퀘스트 제안 로직 추가:

```python
# assets/characters/mila.py
def talk(self):
    from quest import quest_manager

    # 1. 지급 가능한 퀘스트 체크
    available = quest_manager.get_available_quests_from(self.unique_id)
    if available:
        quest = available[0]
        result = yield from quest.offer_dialog()
        if result == "accept":
            quest_manager.accept_quest(quest.unique_id)
        return

    # 2. 완료 보고 가능한 퀘스트 체크
    completable = quest_manager.get_completable_quests_for(self.unique_id)
    if completable:
        quest = completable[0]
        yield from quest.complete_dialog()
        quest_manager.claim_reward(quest.unique_id)
        return

    # 3. 진행 중 퀘스트 체크
    in_progress = quest_manager.get_in_progress_quests_for(self.unique_id)
    if in_progress:
        quest = in_progress[0]
        yield from quest.progress_dialog()
        return

    # 4. 일반 대화
    yield morld.dialog(["[밀라]", "안녕하세요~"])
```
