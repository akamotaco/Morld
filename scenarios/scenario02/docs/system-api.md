# Morld Python API

## morld 모듈 API

```python
import morld

# ========================================
# 유닛 관련
# ========================================
morld.get_player_id()
morld.get_unit_info(unit_id)  # {name, region_id, location_id, activity, is_on_edge, is_traveling, ...}
morld.get_unit_location(unit_id)
morld.set_unit_location(unit_id, region_id, location_id)
morld.get_unit_props(unit_id)
morld.set_unit(unit_id, field, value)  # name, type 등

# ========================================
# JobList 관련
# ========================================
morld.fill_schedule_jobs_from(unit_id, schedule)
morld.set_npc_job(unit_id, action, duration)  # NPC Job 즉시 설정
morld.set_npc_time_consume(unit_id, action, duration)  # 시간 경과 포함

# ========================================
# 아이템 관련
# ========================================
morld.give_item(unit_id, item_id, count)
morld.has_item(unit_id, item_id)
morld.lost_item(unit_id, item_id, count)

# ========================================
# Prop/로그
# ========================================
morld.get_prop(prop_name)
morld.set_prop(prop_name, value)
morld.clear_prop(prop_name)
morld.modify_prop(unit_id, prop_key, delta)  # 값 증감
morld.add_action_log(message)
morld.mark_all_logs_read()

# ========================================
# 시간 관련
# ========================================
morld.get_game_time()  # 분 단위 (0~1439)
morld.advance_time(minutes)
morld.set_time_frozen(frozen)  # 시간 정지 설정/해제
morld.is_time_frozen()

# ========================================
# 위치 관련
# ========================================
morld.get_location_name(region_id, location_id)
morld.get_units_at_location(region_id, location_id)
morld.set_location_ground_id(region_id, location_id, ground_unit_id)
morld.get_location_ground_id(region_id, location_id)

# ========================================
# Dialog API (Generator 전용)
# ========================================
result = yield morld.dialog(
    text_or_pages,      # str 또는 list
    autofill="next",    # "next", "book", "scroll", "off"
    proc=None,          # @proc:값 클릭 시 호출될 콜백
    result=None         # @finish 시 반환할 값
)
```

---

## Dialog 시스템

### autofill 타입

| 타입 | 동작 | 용도 |
|------|------|------|
| `next` | [다음] 버튼만 (기본값) | 순차 모놀로그 |
| `book` | [이전][다음] 왕복 가능 | 일기, 문서 열람 |
| `scroll` | 텍스트 누적 + [다음] | 회상, 긴 독백 |
| `off` | 자동 버튼 없음 | 커스텀 UI |

### URL 패턴

| 패턴 | 동작 |
|------|------|
| `@ret:값` | 다이얼로그 종료, yield에 값 반환 |
| `@finish` | 다이얼로그 종료, result 파라미터 값 반환 |
| `@proc:값` | proc(값) 호출, 반환값에 따라 동작 |
| `@next` | 다음 페이지로 이동 |
| `@prev` | 이전 페이지로 이동 (book 전용) |

### proc 콜백 반환값

| 반환값 | 동작 |
|--------|------|
| `문자열` | 해당 문자열로 텍스트 업데이트 |
| `True` | 다이얼로그 즉시 종료, result 반환 |
| `None`/`False` | 변경 없음 |

### 예시 - 멀티페이지 모놀로그

```python
yield morld.dialog([
    "...어디지, 여기는?",
    "머리가 지끈거린다.",
    "일단 저택에서 나가야 할 것 같다."
])
```

### 예시 - proc + 선택지

```python
state = {"choice": None}

def handle_choice(action):
    if action == "init":
        return None
    state["choice"] = action
    return True  # 다이얼로그 종료

result = yield morld.dialog(
    "어디로 갈까?\n\n"
    "[url=@proc:town]마을[/url]\n"
    "[url=@proc:forest]숲[/url]",
    autofill="off",
    proc=handle_choice,
    result=state
)
```

---

## Python Asset 시스템

### Asset 클래스 구조

```python
# assets/base.py
class Unit:
    unique_id: str = ""
    name: str = "Unknown"
    props: dict = {}
    actions: list = []

class Character(Unit):
    type: str = "male"  # "male", "female"
    mood: list = []

    def get_describe_text(self) -> str:
        """장소에 있을 때 묘사"""
        pass

    def get_focus_text(self) -> str:
        """클릭했을 때 묘사"""
        pass

    def on_meet_player(self, player_id):
        """플레이어와 만났을 때 이벤트 (Generator)"""
        pass
```

### NPC 캐릭터 정의 예시

```python
# assets/characters/sera.py
class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    props = {"힘": 7, "민첩": 8}
    actions = ["call:talk:대화"]

    SCHEDULE = [
        {"name": "순찰", "region_id": 0, "location_id": 1,
         "start": 360, "end": 720, "activity": "순찰"},
    ]

    def on_meet_player(self, player_id):
        yield morld.dialog("...일어났군.")
```

---

## 스크립트 시스템

### @morld.register_script 데코레이터

```python
@morld.register_script
def my_script(context_unit_id, *args):
    """context_unit_id는 Focus 대상 유닛"""
    result = yield morld.dialog("선택하세요\n\n[url=@ret:yes]예[/url]")
    if result == "yes":
        morld.give_item(context_unit_id, item_id)
```

### 액션 문자열 형식

| 형식 | 설명 | 예시 |
|------|------|------|
| `call:메서드명:표시명` | Asset 메서드 호출 | `call:talk:대화` |
| `call:메서드명:인자:표시명` | 인자 있는 메서드 | `call:sit:front:앉기` |

---

## ThinkSystem과 Agent

```python
# think/__init__.py
class BaseAgent:
    def __init__(self, unit_id):
        self.unit_id = unit_id

    def get_info(self):
        return morld.get_unit_info(self.unit_id)

    def fill_schedule_jobs_from(self, schedule):
        return morld.fill_schedule_jobs_from(self.unit_id, schedule)

    def think(self):
        """AI 로직 - 서브클래스에서 오버라이드"""
        pass

@register_agent_class("sera")
class SeraAgent(BaseAgent):
    def think(self):
        self.fill_schedule_jobs_from(Sera.SCHEDULE)
```

---

## 챕터 전환

```python
from chapters import load_chapter

# 챕터 로드 (플레이어 데이터 자동 유지)
load_chapter("chapter_1")

# 새 게임 (데이터 초기화)
load_chapter("chapter_0", preserve_player=False)
```

저장되는 데이터: name, props, mood, inventory (unique_id 기반)
