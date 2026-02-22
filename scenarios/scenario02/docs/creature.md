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
- **7. Creature 성별** — 수컷/암컷/무성
- **8. Bestiality 시스템** — 수간 모드 + 겁탈 AI + 플레이어 교미
- **9. Creature 반응** — 종별 묘사/대사 풀

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
    actions = ["call:attack:공격#", "call:mate:교미#"]   # 교미 = bestiality

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

    # 성별 분포: [(gender_str, weight), ...]
    # None = 무성 고정 (기본)
    GENDER_DISTRIBUTION = None
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

BaseAgent를 상속하되 survival/needs 등록 없이 단순화된 5-tier think 루프.

### NPC(BaseAgent) vs 생물(CreatureAgent)

| 항목 | NPC (BaseAgent) | 생물 (CreatureAgent) |
|------|----------------|---------------------|
| think() | 5-tier (기절→전투→생존→쾌적→스케줄) | 5-tier (사망→기절→전투→겁탈→스케줄) |
| survival 등록 | O (포만감/기절) | X (HP는 전투로만 관리) |
| needs 등록 | O (5개 욕구) | X |
| 전투 감지 | 세력 적대 + 관계 적대 | 세력 적대 + 관계 적대 |
| 세력 | "주민" (기본) | 종별 ("늑대"/"거미"/"박쥐") |
| home region | bed_owner 기반 | `전투:홈리전` prop |
| 스케줄 | 시간대별 복합 활동 | 종별 패턴 (순찰/휴식/수면/복귀) |
| 소멸 | 영구 | 수명 기반 자연 소멸 |
| 겁탈 | — | bestiality ON + 유성 + 무력화 대상 감지 시 |

### think() 5-tier 흐름

```
Tier 0: 운반 중      → carry.is_being_carried() → idle 60s
Tier 1: 사망          → 상태:사망 prop → idle 1h (spawner 디스폰 대기)
Tier 2: 기절          → survival.is_npc_fainted() → idle (잔여 시간)
Tier 3: 전투 위협     → _check_combat_threat() → 전투 처리
Tier 3.5: 겁탈 기회   → _check_assault_opportunity() → 겁탈 AI (Section 8)
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
4. 성별 배정: `GENDER_DISTRIBUTION`에 따라 랜덤 배정 (None이면 무성)
5. Props 설정: `전투:홈리전`, `생물:스폰위치`, `생물:탄생시각`
6. `CreatureAgent(monster_id, schedule=SCHEDULE)` → AI 등록

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
| 거미줄공격 | 명중 시 25% 확률로 거미줄 결박 (`전투:거미줄공격: 25`) |
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
| `전투:거미줄공격` | monster.py (Spider) | 명중 시 거미줄 결박 확률 (%) |
| `성별` | spawner.py | 생물 성별 (gender_to_int 값) |
| `상태:마비` | combat.py | 마비 디버프 잔여 시간 (h) |
| `상태:거미줄` | combat.py | 거미줄 결박 잔여 시간 (h) |
| `소재:{키}` | monster.py props | 수확 가능 수량 |

---

## 7. Creature 성별

### 파일: `gender.py`, `spawner.py`, `monster.py`

### 성별 종류

기존 NPC 성별 시스템 재사용 (male/female/asexual):

| 값 | NPC 표시 | 생물 표시 |
|----|---------|----------|
| `MALE` | 남성 | 수컷 |
| `FEMALE` | 여성 | 암컷 |
| `ASEXUAL` | 무성 | 무성 |

### API

```python
# gender.py
CREATURE_GENDER_DISPLAY = {MALE: "수컷", FEMALE: "암컷", ASEXUAL: "무성"}

def get_creature_gender_display(unit_id):
    """생물체 성별 한글 표시"""
    g = get_gender(unit_id)
    return CREATURE_GENDER_DISPLAY.get(g, "무성")
```

`get_gender()` — 생물체에 `성별` prop이 없으면 `ASEXUAL` 반환 (ValueError 대신).

### 종별 성별 분포

```python
class Wolf(Monster):
    GENDER_DISTRIBUTION = [("male", 0.5), ("female", 0.5)]

class Bear(Monster):
    GENDER_DISTRIBUTION = [("male", 0.5), ("female", 0.5)]

class Spider(Monster):
    GENDER_DISTRIBUTION = [("female", 0.7), ("male", 0.3)]

class Bat(Monster):
    GENDER_DISTRIBUTION = None   # 무성 고정

class Snake(Monster):
    GENDER_DISTRIBUTION = [("male", 0.5), ("female", 0.5)]
```

### 스폰 시 배정 (spawner.py)

```python
dist = getattr(monster_class, 'GENDER_DISTRIBUTION', None)
if dist:
    genders, weights = zip(*dist)
    chosen = random.choices(genders, weights=weights, k=1)[0]
    morld.set_unit_prop(monster_id, "성별", gender_to_int(chosen))
else:
    morld.set_unit_prop(monster_id, "성별", gender_to_int(ASEXUAL))
```

---

## 8. Bestiality 시스템

### 파일: `settings.py`, `think/creature_agent.py`, `monster.py`, `romance.py`, `romance_ui.py`

### 8.1 수간 모드 토글

```python
# settings.py
_bestiality_enabled = False

def is_bestiality_enabled() -> bool:
    """수간 모드 — 연애 모드 ON 필수"""
    return _bestiality_enabled and is_romance_enabled()
```

설정 UI에서 연애 모드 ON 시에만 수간 모드 토글이 표시됨.
플레이어 `can:bestiality` prop과 연동.

### 8.2 Creature → Character 겁탈 (CreatureAgent Tier 3.5)

#### 조건
1. bestiality 모드 ON
2. 생물이 유성 (수컷/암컷, 무성 제외)
3. 같은 Location에 무력화된 캐릭터 존재
4. 쿨다운 완료 (절대 시각 기반 4시간)

#### 무력화 조건

| 상태 | 판별 |
|------|------|
| 기절 (NPC) | `survival.is_npc_fainted(char_id)` |
| 기절 (Player) | `survival.is_player_fainted()` |
| 마비 | `combat.is_paralyzed(char_id)` |
| 거미줄 | `combat.is_web_bound(char_id)` |

#### 처리 흐름

```python
_check_assault_opportunity()
    → 대상 탐색 (NPC + Player) → assault_phase = "assaulting"
    → _handle_assault()
        → NPC 대상: 성욕 -30
        → 공통: aftermath (상태:수간피해=3) + 사정/임신 + 처녀해제 + 경험기록
        → Player 대상: HP -20% 추가 감소
        → 30분 idle + 쿨다운 4시간
    → _clear_assault()
```

#### aftermath 시스템

| Prop | 값 | 용도 |
|------|----|------|
| `상태:수간피해` | 3→-3→2→-2→1→-1→0 | 3단계 후유증 (수면 시 감소) |
| `기억:수간피해횟수` | 누적 int | 반복 피해 템플릿 선택용 |

NPC: `on_meet_player`에서 `_check_mode_aftermath()` → `aftermath_templates.py` "bestiality" 템플릿 표시.
Player: 기절 회복 시 (`handle_player_faint()`) 수간 피해 체크 → 회고적 aftermath 다이얼로그.

#### 사정/임신

- 정액: semen.py 미등록 → `get_semen()` = `SEMEN_MAX(100)` → **무한** (의도적 설계)
- 사정: 수컷(`has_anatomy("P")`) creature만, 고정량 50 (`_apply_internal_semen`)
- 임신: 암컷(`has_anatomy("V")`) 대상만, `father_type="unknown"`
- 처녀 해제: `처녀:음부` 직접 해제 (호감 보너스 없이, `check_and_clear_virginity` 미사용)

#### 경험 기록

겁탈 종료 시 `record_first_experience()` (부위별, 처녀 해제 시만) + `record_last_experience()` (항상).

| Prop | 값 | 설명 |
|------|----|------|
| `기억:첫경험:{부위}` | 1 | 부위별 첫경험 유무 (음부/항문/구강) |
| `기억:첫경험:{부위}:유형/상대/시각` | str/int/int | 부위별 첫경험 상세 |
| `기억:마지막경험:유형/상대/시각` | str/int/int | 마지막 성행위 상세 |

#### `_memory` 키

| 키 | 값 | 설명 |
|----|----|------|
| `assault_phase` | `"assaulting"` / `None` | 겁탈 진행 상태 |
| `assault_target` | unit_id | 겁탈 대상 |
| `assault_cooldown_until` | ms (절대 시각) | 쿨다운 종료 시각 |

### 8.3 Player → Creature 교미

#### 조건
1. bestiality 모드 ON
2. 생물체가 무력화 상태 (기절/마비/거미줄)

#### 액션

```python
# Monster.mate() — 포커스 액션 "교미#" (can:bestiality 필요)
def mate(self):
    # 무력화 확인 → romance.start_romance(mode=MODE_FORCED, is_bestiality=True)
```

### 8.4 로맨스 시스템 Creature 호환

| 항목 | NPC 로맨스 | Creature 로맨스 |
|------|-----------|----------------|
| state 플래그 | `is_bestiality=False` | `is_bestiality=True` |
| 차단 액션 | — | head_pat, french_kiss, lip_kiss, hug 등 11종 |
| 파트너 반응 | 아키타입 기반 대사 | 종별 묘사 (Section 9) |
| 콘돔 | 표시 | 숨김 |
| idle 텍스트 | "당신을 바라보고 있다" | "꿈틀거리고 있다" |

차단 액션 (`_BESTIALITY_BLOCKED_ACTIONS`):
`head_pat`, `french_kiss`, `lip_kiss`, `hug`, `deep_kiss`, `fellatio`,
`cunnilingus`, `condom_on`, `condom_off`, `ear_whisper`, `neck_kiss`

---

## 9. Creature 반응

### 파일: `creature_reactions.py`

### 개요

NPC 아키타입 시스템 대신 **종별(species)** 반응 풀 사용.
`morld.get_unit_info(partner_id)["unique_id"]` → species 결정.

### 종별 풀

| species | unique_id | 특징 |
|---------|-----------|------|
| wolf | `wolf` | 거친, 공격적 |
| spider | `spider` | 기괴한, 곤충적 |
| bat | `bat` | 날카로운, 날갯짓 |
| default | (그 외) | 범용 묘사 |

### 반응 종류

| 유형 | 함수 | 용도 |
|------|------|------|
| 토글 반응 | `get_creature_toggle_reaction()` | 진행 중인 행위 묘사 (thrust 등) |
| 즉시 반응 | `get_creature_instant_reaction()` | 행위 시작 대사 (삽입, 애무 등) |
| 절정 반응 | `get_creature_climax_reaction()` | 절정 묘사 |

### 토글 반응 키

`(arousal_tier, gauge_tier)` 조합:
- arousal_tier: `"low"` (<30), `"medium"` (30-59), `"high"` (≥60)
- gauge_tier: `"low"` (<40), `"medium"` (40-69), `"high"` (≥70)

Fallback: species pool → gauge 한 단계 낮춤 → arousal 한 단계 낮춤 → default pool

### 즉시 반응 액션

`vaginal_insert`, `anal_insert`, `thrust_gentle`, `thrust_normal`, `thrust_rough`,
`genital_caress`, `breast_caress`, `withdraw`

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `assets/characters/monster.py` | Monster/Wolf/Bat/Spider Asset 정의 + GENDER_DISTRIBUTION + mate() |
| `think/creature_agent.py` | CreatureAgent (5-tier think + 겁탈 AI) |
| `spawner.py` | 스폰/디스폰 관리 + 성별 배정 |
| `combat.py` | 세력 시스템 + 전투 코어 + 마비/거미줄 API |
| `gender.py` | 생물 성별 표시 (`get_creature_gender_display`) |
| `settings.py` | 수간 모드 토글 |
| `creature_reactions.py` | 종별 묘사/반응 풀 |
| `romance.py` | `start_romance(is_bestiality=True)` |
| `romance_ui.py` | bestiality 액션 필터 + creature 반응 통합 |
| `restraint.py` | `can_move()` 마비/거미줄 체크 |
| `think/__init__.py` | `_check_combat_threat()` (세력 적대 감지) |
| `world/forest.py` | 숲 스폰 소스 등록 |
| `world/mine.py` | 광산 스폰 소스 등록 |
| `chapters/chapter_1.py` | 스폰 호출 |
| `scripts/morld/unit/UnitType.cs` | UnitType.Creature enum |
| `scripts/morld/unit/Unit.cs` | IsCreature 속성 |
