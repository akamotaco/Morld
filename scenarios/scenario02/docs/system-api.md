# Morld Python API

## morld 모듈 API

```python
import morld

# ========================================
# 유닛 관련
# ========================================
morld.get_player_id()
morld.get_unit_info(unit_id)  # {name, region_id, location_id, activity, is_moving, is_traveling, ...}
morld.get_unit_location(unit_id)
morld.set_unit_location(unit_id, region_id, location_id)
morld.get_unit_props(unit_id)
morld.set_unit(unit_id, field, value)  # name, type 등

# ========================================
# JobList 관련
# ========================================
morld.fill_schedule_jobs_from(unit_id, schedule)
morld.set_npc_job(unit_id, action, duration)  # NPC Job 즉시 설정 (duration: ms)
morld.set_npc_time_consume(unit_id, action, duration)  # 시간 경과 포함 (duration: ms)

# ========================================
# 이벤트 관련
# ========================================
morld.queue_event(event_type, player_id, unit_ids)  # 이벤트 핸들러 큐에 수동 주입
# event_type: "meet" | "contact" | "npc_meet"
# 예: morld.queue_event("meet", player_id, [player_id, npc_id])

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
morld.get_game_time()  # 밀리초 단위 (0~86,399,999)
morld.get_time_info()  # 시간/위치/날씨 정보 dict 반환
morld.advance_time(millis)  # 밀리초 단위
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
# 자세/착석 관련 (Posture/Seat API)
# ========================================
morld.sit_on(unit_id, object_id, slot, posture)  # 오브젝트에 앉기/눕기
morld.stand_up(unit_id)                          # 일어나기

# ========================================
# Dialog API (Generator 전용)
# ========================================
# 권장: ui.dialog() 래퍼 사용
import ui
result = yield ui.dialog(
    text_or_pages,      # str 또는 list (연쇄 출력 지원)
    autofill="next",    # "next", "book", "off"
    proc=None,          # @proc:값 클릭 시 호출될 콜백
    result=None         # @finish 시 반환할 값
)

# 저수준 API (직접 사용 비권장)
result = yield morld.dialog(...)
```

---

## get_time_info() 반환값

시간, 날씨, 위치 정보를 포함하는 dict를 반환합니다.

```python
info = morld.get_time_info()
# {
#     "year": 1,
#     "month": 4,
#     "day": 1,
#     "weekday": "수",
#     "hour": 20,
#     "minute": 0,
#     "weather": "흐림",           # 실외일 때만
#     "region_name": "저택",
#     "location_name": "거실",
#
#     # Pi-World 정보 (디버깅용)
#     "geometry": 0,               # 0 = ring (원), 1 = line (선)
#     "position_x": 210.0,         # 플레이어 현재 X 좌표
#     "location_length": 360.0     # Location 길이
# }
```

### Pi-World 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `geometry` | int | 지형 형태 (0=ring, 1=line) |
| `position_x` | float | 플레이어 X 좌표 |
| `location_length` | float | Location 길이 |

### 사용 예시 (ui.py)

```python
geometry = time_info.get("geometry", 0)
position_x = time_info.get("position_x", 0)
location_length = time_info.get("location_length", 0)

geo_text = "선" if geometry == 1 else "원"
lines.append(f"[{geo_text}] X:{int(position_x)}/{int(location_length)}")
```

---

## Dialog 시스템

대화/리액션/묘사 시스템은 [dialog.md](dialog.md)에서 상세히 다룹니다.

### 개요

| 분류 | 타입 | 용도 |
|------|------|------|
| 대화 | Lines, Sequence, Conversation, Rules | NPC 대화, 이벤트 |
| 리액션 | ROMANCE_REACTIONS 등 | 행동 반응 |
| 묘사 | DESCRIBE_RULES, FOCUS_RULES | 상태 설명 |

### ui.dialog() - 저수준 API

```python
import ui

# 단일 페이지
yield ui.dialog("텍스트")

# 다 페이지 (연쇄 출력 지원)
yield ui.dialog([
    "첫 페이지",
    "+두 번째 (연쇄)",   # 이전 내용 유지
    "세 번째 (새로)"
])
```

### 연쇄 출력 병합 권장

연속 `yield ui.dialog()` 호출은 하나로 병합하여 코드 효율성을 높입니다.

```python
# BAD: 연속 호출 (비효율)
yield ui.dialog(["손을 뻗어 가슴에 닿았다."])
yield ui.dialog(["[리나]", "히잇...!", "거기는...!"])
yield ui.dialog(["리나가 얼굴을 붉혔다.", "손을 밀어내지는 않았다."])

# GOOD: 병합 + 연쇄 출력
yield ui.dialog([
    "손을 뻗어 가슴에 닿았다.",
    "[리나]",
    "+히잇...!",       # 리나 대사 연쇄
    "+거기는...!",
    "리나가 얼굴을 붉혔다.",
    "+손을 밀어내지는 않았다."  # 묘사 연쇄
])
```

**패턴:**
- 같은 화자 대사: `+` 접두사로 한 페이지에 누적
- 묘사 연속: `+` 접두사로 흐름 유지
- 화자 변경: 새 페이지로 전환

### autofill 타입

| 타입 | 동작 | 용도 |
|------|------|------|
| `next` | [다음] 버튼만 (기본값) | 순차 모놀로그 |
| `book` | [이전][다음] 왕복 가능 | 일기, 문서 열람 |
| `off` | 자동 버튼 없음 | 커스텀 UI |

### URL 패턴

| 패턴 | 동작 |
|------|------|
| `@ret:값` | 다이얼로그 종료, yield에 값 반환 |
| `@finish` | 다이얼로그 종료, result 파라미터 값 반환 |
| `@proc:값` | proc(값) 호출 |
| `@next` / `@prev` | 페이지 이동 |

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
import ui

class Sera(Character):
    unique_id = "sera"
    name = "세라"
    type = "female"
    props = {"힘": 7, "민첩": 8}
    actions = ["call:talk:대화"]

    SCHEDULE = [
        {"name": "순찰", "region_id": 0, "location_id": 1,
         "start": 21_600_000, "end": 43_200_000, "activity": "순찰"},
    ]

    def on_meet_player(self, player_id):
        yield ui.dialog("...일어났군.")
```

---

## 스크립트 시스템

### @morld.register_script 데코레이터

```python
import ui

@morld.register_script
def my_script(context_unit_id, *args):
    """context_unit_id는 Focus 대상 유닛"""
    result = yield ui.dialog("선택하세요\n\n[url=@ret:yes]예[/url]")
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

---

## 자세/착석 API (Posture/Seat API)

캐릭터가 오브젝트에 앉거나 눕는 행동을 관리합니다.

### sit_on(unit_id, object_id, slot, posture)

오브젝트의 특정 슬롯에 앉거나 눕습니다.

```python
# 침대에 눕기
morld.sit_on(player_id, bed_id, "center", "lying")

# 의자에 앉기
morld.sit_on(player_id, chair_id, "front", "sitting")
```

**파라미터:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `unit_id` | int | 앉을 캐릭터 ID |
| `object_id` | int | 대상 오브젝트 ID |
| `slot` | str | 슬롯 이름 (오브젝트에 정의된 좌석 위치) |
| `posture` | str | 자세 ("sitting", "lying", "crouch", "prone") |

**반환값:** `True` (성공), `False` (실패 - 슬롯 점유됨 등)

**동작:**
1. 이미 다른 오브젝트에 앉아있으면 자동으로 일어남 (auto stand_up)
2. 캐릭터에 `posture:{posture}=1`, `seated_on:{object_id}={hash}` prop 설정
3. 오브젝트에 `seated_by:{slot}={unit_id}` prop 설정

### stand_up(unit_id)

현재 앉아있는/누워있는 상태에서 일어납니다.

```python
morld.stand_up(player_id)
```

**파라미터:**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `unit_id` | int | 일어날 캐릭터 ID |

**반환값:** `True` (성공), `False` (이미 서있음)

**동작:**
1. 캐릭터의 `posture:*`, `seated_on:*` prop 제거
2. 오브젝트의 해당 `seated_by:{slot}` prop 제거

### 자세(Posture) 종류

| 자세 | 이름 | 이동 가능 |
|------|------|----------|
| `standing` | 서기 | O (기본 상태, prop 없음) |
| `sitting` | 앉기 | X |
| `lying` | 눕기 | X |
| `crouch` | 웅크리기 | O |
| `prone` | 엎드리기 | O |

### Props 구조

```python
# 캐릭터 props
posture:sitting = 1       # 현재 자세 (없으면 standing)
seated_on:123 = 456       # object_id=123에 앉아있음 (hash=456)

# 오브젝트 props
seated_by:front = 1       # front 슬롯에 unit_id=1이 앉아있음
seated_by:center = 2      # center 슬롯에 unit_id=2가 앉아있음
```

### UI 표시

- Footer에 현재 자세 항상 표시
- 이동 불가 자세일 때 노란색으로 표시
- 이동 UI는 항상 표시하되, 이동 불가 시 회색으로 표시
- "행동" 섹션에 `[오브젝트명]에서 일어나기` 액션 표시
