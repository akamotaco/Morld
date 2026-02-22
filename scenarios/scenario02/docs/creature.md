# 생물(Creature) 시스템

> 생물 — 늑대, 박쥐, 거미 등 NPC가 아닌 야생 유닛.
> 인간급 섬세함(욕구/관계/대화)이 불필요한 단순 AI 유닛에 사용.

---

## 목차

- **1. UnitType.Creature** — C# 타입 구분
- **2. 세력(Faction) 시스템** — 적대 판별
- **3. Monster Asset 클래스** — 정의 구조
- **4. CreatureAgent** — AI 행동 루프
- **5. 스포너(Spawner)** — 생성/소멸 라이프사이클
- **6. 종별 명세** — Wolf / Bat / Spider

---

## 1. UnitType.Creature

### C# enum

```csharp
// scripts/morld/unit/UnitType.cs
public enum UnitType { Character, Object, Creature }
```

| UnitType | 의미 | IsObject | IsCreature | 이동/스케줄 | 이벤트 |
|----------|------|----------|------------|-----------|--------|
| Character | 플레이어/NPC | false | false | O | O |
| Creature | 생물 | false | true | O | O |
| Object | 오브젝트 | true | false | X | 수동 |

### Python Asset

```python
class Monster(Character):
    type = "creature"   # → C# UnitType.Creature 파싱
```

### API 영향

| API | 동작 |
|-----|------|
| `get_actor_ids()` | Character + Creature 반환 (Object 제외) |
| `get_units_at_location(type="character")` | Character만 (Creature 제외) |
| `get_units_at_location(type="creature")` | Creature만 |
| `get_units_at_location()` | 전체 (Character + Creature + Object) |

---

## 2. 세력(Faction) 시스템

### 개요

`전투:적대유형` (타입 기반) → `전투:세력` (세력 기반)으로 교체.
같은 세력끼리는 비적대, 다른 세력은 적대 테이블 참조.

### 적대 테이블

```python
# combat.py
FACTION_HOSTILITY = {
    "주민":   set(),               # NPC/플레이어 — 기본 비적대
    "늑대":   {"주민", "거미"},     # 사람+거미 공격
    "거미":   {"주민", "늑대"},     # 사람+늑대 공격
    "박쥐":   {"주민"},             # 사람만 공격
}
DEFAULT_FACTION = "주민"
```

### 판별 함수

```python
def is_faction_hostile(faction_a, faction_b) -> bool:
    """양방향 적대 체크 — 어느 한쪽이라도 상대를 적대 목록에 포함하면 True"""
    a = faction_a or DEFAULT_FACTION
    b = faction_b or DEFAULT_FACTION
    if a == b:
        return False
    return b in FACTION_HOSTILITY.get(a, set()) \
        or a in FACTION_HOSTILITY.get(b, set())

def is_creature_unit(unit_id) -> bool:
    """세력이 주민이 아닌 유닛 = 생물"""
    faction = morld.get_unit_prop(unit_id, "전투:세력")
    return faction is not None and faction != DEFAULT_FACTION
```

### 적대 매트릭스

| | 주민 | 늑대 | 거미 | 박쥐 |
|---|:---:|:---:|:---:|:---:|
| **주민** | - | **적대** | **적대** | **적대** |
| **늑대** | **적대** | - | **적대** | - |
| **거미** | **적대** | **적대** | - | - |
| **박쥐** | **적대** | - | - | - |

### NPC 전투와의 병행

세력 적대 외에도 **관계 적대** (`is_hostile_to`)가 병행 동작:

```python
# think/__init__.py _check_combat_threat()
is_enemy = combat.is_faction_hostile(my_faction, their_faction)
if not is_enemy:
    is_enemy = combat.is_hostile_to(self.unit_id, uid)
```

---

## 3. Monster Asset 클래스

### 구조

```
Monster(Character)       ← 생물 기본 클래스
├── Wolf                 ← 늑대 (숲)
├── Bat                  ← 박쥐 (광산 1층)
├── Spider               ← 거미 (광산 2-3층)
└── TrainingDummy        ← 허수아비 (type="character", 테스트용)
```

### 파일: `assets/characters/monster.py`

### Monster 기본 클래스

```python
class Monster(Character):
    type = "creature"
    owner = None
    actions = ["call:attack:공격#"]   # 대화/스킨십 불가

    props = {
        "전투:세력": "야생",          # 서브클래스에서 오버라이드
        "생존:체력": 30,
        "생존:최대체력": 30,
        "전투:공격력": 5,
        "전투:방어력": 2,
        "전투:명중": 70,
        "전투:회피": 10,
        "전투:치명타": 3,
        "전투:사거리": 60,
        "전투:공격속도": 1.0,
        "전투:감지거리": 100,
    }

    BATTLE_BEHAVIOR = { ... }   # 전투 AI 파라미터
    DROP_TABLE = []              # 스폰 시 인벤토리 생성
    HARVEST_TABLE = {}           # 시체에서 도구로 수확
    SCHEDULE = [...]             # 라이프사이클
```

### DROP_TABLE — 스폰 시 인벤토리 생성

```python
DROP_TABLE = [
    {"item": "meat", "chance": 0.8, "count": (1, 2)},
]
```

- `chance`: 드롭 확률 (0.0~1.0)
- `count`: 고정 int 또는 (min, max) 범위
- `_populate_inventory()`: 스폰 시 호출 → `morld.give_item()`

### HARVEST_TABLE — 시체 소재 수확

```python
HARVEST_TABLE = {
    "소재:가죽": {
        "item": "wolf_pelt",        # 아이템 unique_id
        "name": "늑대 가죽",        # 표시명
        "tool_prop": "날붙이",      # 필요 장비 prop (None=도구 불필요)
        "time_ms": 10_000,          # 수확 소요 시간
    },
}
```

- 수확 가능 수량: `props["소재:가죽"]` = 2 → 최대 2회 수확
- 수확 시 prop 감소 → 0이면 해당 소재 소진
- `base.py:harvest()` 에서 처리

### BATTLE_BEHAVIOR — 전투 AI

```python
BATTLE_BEHAVIOR = {
    "combat_style": "aggressive",   # aggressive/defensive/evasive
    "target_priority": "nearest",   # nearest/weakest/strongest
    "preferred_range": 70,          # 선호 교전 거리 (px)
    "retreat_threshold": 0.2,       # HP 20% 이하 시 도주
}
```

---

## 4. CreatureAgent

### 파일: `think/creature_agent.py`

BaseAgent를 상속하되 survival/needs 등록 없이 단순화된 4-tier think 루프.

### NPC(BaseAgent) vs 생물(CreatureAgent)

| 항목 | NPC (BaseAgent) | 생물 (CreatureAgent) |
|------|----------------|---------------------|
| think() | 5-tier (기절→전투→생존→쾌적→스케줄) | 4-tier (사망→기절→전투→스케줄) |
| survival 등록 | O (포만감/기절) | X (HP는 전투로만 관리) |
| needs 등록 | O (5개 욕구) | X |
| 전투 감지 | 세력 적대 + 관계 적대 | 세력 적대 + 관계 적대 |
| 세력 | "주민" (기본) | 종별 ("늑대"/"거미"/"박쥐") |
| home region | bed_owner 기반 | `전투:홈리전` prop |
| 스케줄 | 시간대별 복합 활동 | 종별 패턴 (순찰/휴식/수면/복귀) |
| 소멸 | 영구 | 수명 기반 자연 소멸 |

### think() 4-tier 흐름

```
Tier 0: 운반 중      → carry.is_being_carried() → idle 60s
Tier 1: 사망          → 상태:사망 prop → idle 1h (spawner 디스폰 대기)
Tier 2: 기절          → survival.is_npc_fainted() → idle (잔여 시간)
Tier 3: 전투 위협     → _check_combat_threat() → 전투 처리
Tier 4: 스케줄        → _get_creature_entry() → 활동별 분기
Safety net: 할 일 없음 → idle 60s
```

### 스케줄 활동 분기

| 활동 | 처리 |
|------|------|
| 순찰 | `_do_wander(entry)` — home_region 내 랜덤 이동 + 10~30분 휴식 |
| 휴식 | `_insert_idle_job("휴식", remaining_ms)` — 제자리 대기 |
| 수면 | `_insert_idle_job("수면", remaining_ms)` — lair에서 대기 |
| 복귀 | `_do_return_to_lair(entry)` — spawn location으로 이동 |

### 복귀 행동

```python
def _do_return_to_lair(self, entry):
    spawn_region = morld.get_unit_prop(self.unit_id, "전투:홈리전")
    spawn_loc = morld.get_unit_prop(self.unit_id, "생물:스폰위치")
    target = {"region_id": int(spawn_region), "location_id": int(spawn_loc)}
    if not self._is_at(target):
        self._move_to(target, entry["name"])
    else:
        self._insert_idle_job(entry["name"], remaining)
```

---

## 5. 스포너(Spawner) 시스템

### 파일: `spawner.py`

### 라이프사이클

```
register_spawn_source()          # 스폰 소스 등록
    ↓
_on_time_elapsed() [매 1시간]    # 시간 구독 콜백
    ├─ _update_spawned_list()    # 사망/맵밖/수명만료 정리
    ├─ _try_spawn()              # 조건 충족 시 생물 생성
    └─ _cleanup_corpses()        # 시체 4h 후 디스폰
```

### 스폰 소스 등록

```python
register_spawn_source(
    source_id="forest_wolves",   # 고유 ID
    monster_class=Wolf,          # Asset 클래스
    max_count=2,                 # 최대 동시 존재 수
    interval_hours=6,            # 스폰 간격
    region_id=3,                 # 스폰 Region
    location_id=4,               # 스폰 Location
    lifespan_hours=72,           # 수명 (기본 72h = 3일)
)
```

### 생물 생성 과정 (`_try_spawn`)

1. `morld.create_id("unit")` → 새 unit_id
2. `monster_class().instantiate(monster_id, region_id, location_id)` → Asset 등록
3. `_populate_inventory()` → DROP_TABLE 기반 인벤토리
4. Props 설정: `전투:홈리전`, `생물:스폰위치`, `생물:탄생시각`
5. `CreatureAgent(monster_id, schedule=SCHEDULE)` → AI 등록

### 자연 소멸 (수명)

- 매 1시간 `_update_spawned_list()`에서 체크
- 조건: `현재시각 - 생물:탄생시각 > lifespan_hours`
- 추가 조건: **spawn location에 위치** (순찰 중이면 소멸 보류)
- 소멸: `morld.set_unit_location(-1, -1)` + `think.unregister_agent()`

### 시체 처리

- 사망 유닛 → `_corpses` 리스트로 이관
- 4시간 경과 + 플레이어 부재 시 디스폰
- 플레이어가 같은 Location에 있으면 정리 보류 (루팅 기회 보장)

### 챕터 전환

```python
# chapters/__init__.py
spawner.reset()   # _spawn_sources, _corpses, _initialized 초기화
```

---

## 6. 종별 명세

### Wolf (늑대)

| 항목 | 값 |
|------|---|
| 서식지 | R3 숲 — L4 늑대굴 |
| HP | 40 |
| 공격력/방어력 | 8 / 3 |
| 명중/회피 | 75% / 15% |
| 세력 | 늑대 |
| 전투 스타일 | aggressive (공격적) |
| 도주 임계 | HP 20% |
| 드롭 | 고기 ×1~2 (80%) |
| 수확 | 늑대 가죽 ×2 (날붙이), 늑대 이빨 ×1 (날붙이) |
| 최대 수 | 2마리, 6시간 간격, 수명 72h |

**스케줄 (박명박모성):**
```
00:00-05:00  수면 (늑대굴)
05:00-12:00  순찰 (숲 내 배회)
12:00-15:00  휴식
15:00-21:00  순찰
21:00-23:00  복귀 (늑대굴로)
23:00-24:00  수면
```

### Bat (박쥐)

| 항목 | 값 |
|------|---|
| 서식지 | R4 광산 — L1 입구 |
| HP | 15 |
| 공격력/방어력 | 3 / 1 |
| 명중/회피 | 65% / 25% |
| 세력 | 박쥐 |
| 전투 스타일 | evasive (회피형) |
| 도주 임계 | HP 30% |
| 드롭 | 고기 ×1 (50%) |
| 최대 수 | 2마리, 4시간 간격, 수명 72h |

**스케줄 (야행성):**
```
00:00-18:00  수면
18:00-23:00  순찰 (광산 내 배회)
23:00-24:00  복귀 (입구로)
```

### Spider (거미)

| 항목 | 값 |
|------|---|
| 서식지 | R4 광산 — L2 1층, L3 2층 |
| HP | 50 |
| 공격력/방어력 | 6 / 4 |
| 명중/회피/치명타 | 75% / 10% / 8% |
| 독공격 | 명중 시 30% 확률로 독 부여 (`전투:독공격: 30`) |
| 세력 | 거미 |
| 전투 스타일 | aggressive (공격적) |
| 도주 임계 | HP 15% |
| 수확 | 거미독 ×1 (날붙이), 거미줄 ×2 (도구 불필요) |
| 최대 수 | L2: 1마리 6h, L3: 2마리 8h, 수명 72h |

**스케줄 (매복형):**
```
00:00-12:00  순찰
12:00-16:00  휴식
16:00-24:00  순찰
```

### 총 생물 인구

| Region | 종류 | 최대 수 | 스폰 간격 |
|--------|------|--------|----------|
| R3 숲 L4 | Wolf | 2 | 6h |
| R4 광산 L1 | Bat | 2 | 4h |
| R4 광산 L2 | Spider | 1 | 6h |
| R4 광산 L3 | Spider | 2 | 8h |
| **합계** | | **7** | |

---

## 생물 관련 Props

| Prop | 설정 주체 | 용도 |
|------|----------|------|
| `전투:세력` | monster.py (종별) | 세력 적대 판별 |
| `전투:홈리전` | spawner.py | 순찰 범위 + 복귀 region |
| `생물:스폰위치` | spawner.py | 복귀 location |
| `생물:탄생시각` | spawner.py | 수명 체크 |
| `상태:사망` | combat.py | 사망 여부 |
| `상태:사망시각` | base.py finish_off() | 시체 정리 타이머 |
| `전투:독공격` | monster.py (Spider) | 명중 시 독 부여 확률 (%) |
| `소재:{키}` | monster.py props | 수확 가능 수량 |

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `assets/characters/monster.py` | Monster/Wolf/Bat/Spider Asset 정의 |
| `think/creature_agent.py` | CreatureAgent (4-tier think) |
| `spawner.py` | 스폰/디스폰 관리 |
| `combat.py` | 세력 시스템 + 전투 코어 |
| `think/__init__.py` | `_check_combat_threat()` (세력 적대 감지) |
| `world/forest.py` | 숲 스폰 소스 등록 |
| `world/mine.py` | 광산 스폰 소스 등록 |
| `chapters/chapter_1.py` | 스폰 호출 |
| `scripts/morld/unit/UnitType.cs` | UnitType.Creature enum |
| `scripts/morld/unit/Unit.cs` | IsCreature 속성 |
