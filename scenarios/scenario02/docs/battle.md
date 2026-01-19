# 전투 시스템 설계

## 개요

**현장 전투 + 교전 상태** 방식을 채택합니다.
- 전투가 일반 시스템과 통합되어 자연스러운 NPC 참전/도주 가능
- **교전 슬롯** 시스템으로 "물량에 밀림" 문제 해결
- **Location 용량** 개념으로 지형과 전투가 융합

---

## 설계 철학

### 왜 "현장 전투"인가?

| 접근법 | 장점 | 단점 |
|--------|------|------|
| 별도 전투 시스템 | 관리 쉬움, 파티 확정 | NPC 참전 불가, 추상적 |
| **현장 전투** | 자연스러운 참전/도주, 지형 활용 | 다수 적 관리 필요 |

**현장 전투**를 선택하고, **교전 슬롯**으로 다수 적 문제를 해결합니다.

---

## Location 용량 시스템

### 개념

Location에 **용량(capacity)** 속성을 추가하여:
- 동시 교전 가능한 유닛 수 제한
- 지형의 좁고 넓음을 표현
- 전투 외 상황에서도 활용 (혼잡도, 숨기 등)

### Location 속성

```python
class Location:
    # 기존 속성들...

    # 용량 관련
    combat_capacity: int = 4      # 전투 시 동시 교전 가능 수
    presence_capacity: int = 10   # 최대 수용 인원 (선택적)
    terrain_type: str = "open"    # "open", "narrow", "cramped"
```

### 용량 예시

| Location | combat_capacity | terrain_type | 설명 |
|----------|-----------------|--------------|------|
| 넓은 들판 | 6 | open | 다수 전투 가능 |
| 숲길 | 4 | open | 기본 |
| 좁은 통로 | 2 | narrow | 1:1 또는 1:2 |
| 동굴 입구 | 3 | narrow | 제한적 |
| 절벽 다리 | 1 | cramped | 1:1만 가능 |
| 넓은 홀 | 8 | open | 대규모 전투 |

### Python 정의

```python
# assets/locations/forest.py
class ForestPath(Location):
    unique_id = "forest_path"
    name = "숲길"
    combat_capacity = 4
    terrain_type = "open"

class NarrowCave(Location):
    unique_id = "narrow_cave"
    name = "좁은 동굴"
    combat_capacity = 2
    terrain_type = "narrow"

    # 좁은 지형 특수 효과
    terrain_effects = {
        "회피": -10,      # 회피 어려움
        "대형무기": -20,  # 대형 무기 패널티
    }
```

### 용량 활용

```python
def get_effective_combat_capacity(location):
    """실제 교전 용량 계산"""
    base = location.combat_capacity

    # 날씨 영향 (선택적)
    if location.is_outdoor and get_weather() == "폭풍":
        base -= 1

    # 시간대 영향 (선택적)
    if is_night() and not has_light_source():
        base -= 1

    return max(1, base)
```

---

## 교전 상태 시스템

### 개념

```
┌─────────────────────────────────────────────────────────────────┐
│ Location: 숲 입구 (combat_capacity: 4)                          │
│                                                                 │
│  [교전 중] (4/4 슬롯 사용)                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 플레이어(1) + 세라(1) ←→ 고블린A(1) + 고블린B(1)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [대기 중]                                                       │
│  - 고블린C, 고블린D (슬롯 부족으로 대기)                           │
│                                                                 │
│  [비전투]                                                        │
│  - 리나 (따라오는 중, 3분 후 도착)                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 유닛 크기 (Combat Size)

큰 적은 더 많은 슬롯을 차지합니다:

| 크기 | 슬롯 | 예시 |
|------|------|------|
| small | 0.5 | 슬라임, 쥐 |
| medium | 1 | 인간, 고블린, 늑대 |
| large | 2 | 오거, 곰, 기사 |
| huge | 3 | 트롤, 골렘 |
| colossal | 4+ | 드래곤, 거인 |

```python
class Monster(Character):
    combat_size: float = 1.0  # 기본 medium

class Slime(Monster):
    combat_size = 0.5

class CaveGolem(Monster):
    combat_size = 3.0
```

### 교전 규칙

```python
class Engagement:
    """교전 상태 관리"""

    def __init__(self, location):
        self.location = location
        self.capacity = location.combat_capacity

        self.allies = []         # (unit_id, size)
        self.active_enemies = [] # (unit_id, size)
        self.waiting_enemies = [] # 대기열

    def get_used_slots(self):
        """사용 중인 슬롯"""
        ally_slots = sum(size for _, size in self.allies)
        enemy_slots = sum(size for _, size in self.active_enemies)
        return ally_slots + enemy_slots

    def get_available_slots(self):
        """남은 슬롯"""
        return self.capacity - self.get_used_slots()

    def can_add_enemy(self, enemy_size):
        """적 추가 가능 여부"""
        return self.get_available_slots() >= enemy_size

    def add_enemy(self, enemy_id, size=1.0):
        """적 추가"""
        if self.can_add_enemy(size):
            self.active_enemies.append((enemy_id, size))
            return True
        else:
            self.waiting_enemies.append((enemy_id, size))
            return False

    def on_unit_removed(self, unit_id):
        """유닛 제거 시 대기열 처리"""
        # 활성 목록에서 제거
        self.active_enemies = [(u, s) for u, s in self.active_enemies if u != unit_id]
        self.allies = [(u, s) for u, s in self.allies if u != unit_id]

        # 대기열에서 진입 시도
        self._fill_from_waiting()

    def _fill_from_waiting(self):
        """대기열에서 슬롯 채우기"""
        entered = []
        remaining = []

        for enemy_id, size in self.waiting_enemies:
            if self.can_add_enemy(size):
                self.active_enemies.append((enemy_id, size))
                entered.append(enemy_id)
            else:
                remaining.append((enemy_id, size))

        self.waiting_enemies = remaining
        return entered  # UI 알림용
```

---

## 전투 흐름

### 턴 구조

```
1턴 = 1분 (게임 시간)

플레이어 턴
    ↓
아군 NPC 턴 (AI 자동)
    ↓
적 턴 (교전 중인 적만)
    ↓
시간 경과 (1분)
    ↓
도착 체크 (NPC 이동)
    ↓
대기열 처리
    ↓
다음 턴
```

### 턴 처리

```python
TURN_DURATION = 1  # 1턴 = 1분

def _process_turn(state, player_action):
    """한 턴 처리"""

    # 1. 플레이어 행동
    result = _process_player_action(state, player_action)
    if result:  # 전투 종료 조건
        return result

    # 2. 아군 NPC 행동 (AI)
    for ally_id, _ in state["engagement"].allies:
        if ally_id != morld.get_player_id():
            _process_ally_ai(state, ally_id)

    # 3. 적 행동
    for enemy_id, _ in state["engagement"].active_enemies:
        if _is_alive(enemy_id):
            _process_enemy_action(state, enemy_id)

    # 4. 승패 체크
    if _check_victory(state):
        state["victory"] = True
        return True
    if _check_defeat(state):
        state["defeat"] = True
        return True

    # 5. 시간 경과 + NPC 도착
    _process_time_and_arrivals(state, TURN_DURATION)

    # 6. 대기열 처리
    entered = state["engagement"]._fill_from_waiting()
    for enemy_id in entered:
        state["log"].append(f"{_get_name(enemy_id)}(이)가 전투에 뛰어들었다!")

    state["turn"] += 1
    return _render_battle(state)
```

### NPC 도착 처리

```python
def _process_time_and_arrivals(state, minutes):
    """시간 경과 및 도착 처리"""

    # 시간 진행 (내부 시뮬레이션)
    arrivals = morld.simulate_time_passage(minutes)

    for unit_id in arrivals:
        unit_loc = morld.get_unit_location(unit_id)
        if unit_loc != state["location"]:
            continue

        unit_info = morld.get_unit_info(unit_id)

        if _is_hostile(unit_id):
            # 적 도착
            size = _get_combat_size(unit_id)
            if state["engagement"].add_enemy(unit_id, size):
                state["log"].append(
                    f"[color=red]{unit_info['name']}(이)가 나타났다![/color]"
                )
            else:
                state["log"].append(
                    f"[color=gray]{unit_info['name']}(이)가 기회를 노리고 있다...[/color]"
                )

        elif _will_join_battle(unit_id):
            # 아군 합류
            size = _get_combat_size(unit_id)
            state["engagement"].allies.append((unit_id, size))
            state["log"].append(
                f"[color=cyan]{unit_info['name']}(이)가 합류했다![/color]"
            )

            # 합류로 용량 변화는 없지만, 아군 추가로 전력 증가
            # (선택적: 아군이 슬롯을 차지하지 않는 방식도 가능)
```

---

## 도주 시스템

### 도주 확률

```python
def _calculate_flee_chance(state):
    """도주 확률 계산"""
    player_id = morld.get_player_id()

    # 기본 확률 50%
    base_chance = 50

    # 민첩 비교
    player_agi = morld.get_actual_prop(player_id, "전투:민첩") or 10
    avg_enemy_agi = _get_avg_enemy_agility(state)
    agi_bonus = (player_agi - avg_enemy_agi) * 2

    # 지형 영향
    terrain = state["location"].terrain_type
    terrain_bonus = {
        "open": 10,      # 열린 지형: 도주 쉬움
        "narrow": -10,   # 좁은 지형: 도주 어려움
        "cramped": -20,  # 비좁은 지형: 매우 어려움
    }.get(terrain, 0)

    # 교전 중인 적 수 영향
    enemy_count = len(state["engagement"].active_enemies)
    crowd_penalty = (enemy_count - 1) * 5  # 적 1명당 -5%

    chance = base_chance + agi_bonus + terrain_bonus - crowd_penalty
    return max(10, min(90, chance))  # 10% ~ 90%
```

### 도주 처리

```python
def _attempt_flee(state):
    """도주 시도"""

    flee_chance = _calculate_flee_chance(state)

    if random.randint(1, 100) > flee_chance:
        state["log"].append("도망치지 못했다!")
        return None  # 턴 소모

    # 도주 성공 → 경로 선택
    routes = morld.get_available_routes(state["location"])
    if not routes:
        state["log"].append("도망칠 곳이 없다!")
        return None

    state["flee_routes"] = routes
    return _render_flee_ui(routes)

def _process_flee_destination(state, route_index):
    """도주 목적지 선택"""
    player_id = morld.get_player_id()
    route = state["flee_routes"][route_index]

    # 이동
    morld.set_unit_location(player_id, route.region_id, route.location_id)

    # 추적 판정
    for enemy_id, _ in state["engagement"].active_enemies:
        if _will_chase(enemy_id):
            morld.set_npc_job(enemy_id, "follow", duration=30, target=player_id)
            state["log"].append(f"{_get_name(enemy_id)}(이)가 추적해 온다!")

    state["fled"] = True
    return True
```

### 추적 시스템

```python
def _will_chase(enemy_id):
    """적의 추적 여부 판정"""
    enemy = get_unit_asset(enemy_id)

    # 기본 추적 확률
    chase_chance = enemy.chase_chance if hasattr(enemy, 'chase_chance') else 30

    # 몬스터 타입별 추적 성향
    chase_types = {
        "guardian": 0,    # 수호자: 추적 안 함 (영역 방어)
        "hunter": 80,     # 사냥꾼: 높은 추적률
        "beast": 50,      # 야수: 중간
        "undead": 20,     # 언데드: 낮음
        "boss": 100,      # 보스: 항상 추적
    }

    if hasattr(enemy, 'monster_type'):
        chase_chance = chase_types.get(enemy.monster_type, chase_chance)

    return random.randint(1, 100) <= chase_chance

class Monster(Character):
    monster_type: str = "beast"  # 기본 타입
    chase_chance: int = 30       # 기본 추적 확률
```

---

## 전투 스탯

### 기본 스탯

```python
# props 형식
props = {
    "전투:체력": 100,
    "전투:최대체력": 100,
    "전투:공격력": 10,
    "전투:방어력": 5,
    "전투:민첩": 10,
    "전투:명중": 85,
    "전투:회피": 10,
    "전투:치명타율": 5,
}
```

### 장비 효과

기존 장비 시스템 활용:

```python
class IronSword(Item):
    unique_id = "iron_sword"
    name = "철검"
    equip_props = {
        "장착:손": 1,
        "전투:공격력": 5,
        "전투:명중": 5,
    }
```

### 데미지 계산

```python
def calculate_damage(attacker_id, defender_id):
    """데미지 계산"""
    atk = morld.get_actual_prop(attacker_id, "전투:공격력")
    def_ = morld.get_actual_prop(defender_id, "전투:방어력")

    # 기본 데미지 = 공격력 - 방어력/2
    base = max(1, atk - def_ // 2)

    # 명중 판정
    hit = morld.get_actual_prop(attacker_id, "전투:명중")
    eva = morld.get_actual_prop(defender_id, "전투:회피")
    if random.randint(1, 100) > (hit - eva):
        return 0, "회피"

    # 치명타 판정
    crit_rate = morld.get_actual_prop(attacker_id, "전투:치명타율") or 5
    is_crit = random.randint(1, 100) <= crit_rate
    if is_crit:
        base = int(base * 1.5)

    # 랜덤 편차 ±10%
    damage = int(base * random.uniform(0.9, 1.1))

    return damage, "치명타" if is_crit else "일반"
```

---

## NPC 전투 AI

### 캐릭터별 전투 행동

연애 시스템의 `ROMANCE_REACTIONS` 패턴 활용:

```python
class Character(Unit):
    # 전투 행동 설정
    BATTLE_BEHAVIOR: dict = {
        "target_priority": "weakest",  # "weakest", "strongest", "random"
        "heal_threshold": 30,          # HP 30% 이하면 회복 시도
        "skill_preference": 0.3,       # 30% 확률로 스킬 사용
    }

    # 전투 대사
    BATTLE_QUOTES: dict = {
        "join": ["전투에 합류한다!"],
        "attack": ["공격!"],
        "hit": ["윽!"],
        "victory": ["이겼다!"],
    }
```

### 캐릭터별 설정 예시

```python
# 세라 - 공격적
class Sera(Character):
    BATTLE_BEHAVIOR = {
        "target_priority": "strongest",  # 강한 적 우선
        "heal_threshold": 20,            # 위험해도 공격
        "skill_preference": 0.5,
        "protect_player": True,          # 플레이어 보호
    }

    BATTLE_QUOTES = {
        "join": ["...뒤는 맡겨.", "...시작하지."],
        "attack": ["...이것이다.", "..."],
        "hit": ["...읏.", "..."],
        "victory": ["...끝났어.", "...괜찮아?"],
        "protect": ["...위험해!", "...물러서!"],
    }

# 밀라 - 지원형
class Mila(Character):
    BATTLE_BEHAVIOR = {
        "target_priority": "weakest",
        "heal_threshold": 50,
        "skill_preference": 0.7,         # 스킬 선호
        "support_priority": True,        # 회복/버프 우선
    }

    BATTLE_QUOTES = {
        "join": ["제가 도와드릴게요!", "괜찮으세요?"],
        "heal": ["치유해 드릴게요.", "조금만 참으세요."],
        "victory": ["다행이에요...", "다친 데 없으세요?"],
    }
```

---

## 전투 UI

### 기본 UI

```
═══ 전투 (턴 3) ═══

[숲길] 용량: 4/4

[교전 중]
  고블린 정찰병  [████████░░] 80/100  (1슬롯)
  고블린 궁수    [██████░░░░] 60/100  (1슬롯)

[대기 중: 2마리]
  고블린 전사, 고블린 전사

[아군]
  플레이어      [██████████] 100/100
  세라          [████████░░] 85/100

──────────────────────
고블린 정찰병의 공격! → 12 데미지
세라: "...뒤는 맡겨."
──────────────────────

행동 선택:
  [공격 → 고블린 정찰병]
  [공격 → 고블린 궁수]
  [스킬]
  [아이템]
  [방어]
  [도주] (성공률: 45%)

[color=gray]리나가 접근 중 (2분 후 도착)[/color]
```

### 좁은 지형 UI

```
═══ 전투 (턴 1) ═══

[좁은 동굴 통로] 용량: 2/2

[교전 중]
  동굴 골렘     [██████████] 100/100  (3슬롯 → 2로 제한)

[아군]
  플레이어      [██████████] 100/100

[지형 효과]
  - 회피 -10%
  - 대형무기 -20%

──────────────────────
좁은 통로라 움직이기 어렵다...
──────────────────────

행동 선택:
  [공격]
  [스킬]
  [아이템]
  [방어]
  [도주] (성공률: 25%)  ← 좁은 지형 패널티
```

---

## 파일 구조

```
scenarios/scenario02/python/
├─ battle/
│   ├─ __init__.py          # start_battle() API
│   ├─ engagement.py        # Engagement 클래스
│   ├─ combat.py            # 데미지 계산, 턴 처리
│   ├─ flee.py              # 도주/추적 시스템
│   └─ ai.py                # NPC 전투 AI
├─ assets/
│   ├─ base.py              # BATTLE_BEHAVIOR, combat_size 추가
│   ├─ locations/
│   │   └─ *.py             # combat_capacity, terrain_type 추가
│   └─ characters/
│       └─ monsters.py      # Monster 클래스
└─ docs/
    └─ battle.md            # 이 문서
```

---

## 구현 순서 (제안)

1. **Location 용량 시스템**
   - Location에 combat_capacity, terrain_type 속성 추가
   - C# Location 클래스 확장

2. **Engagement 클래스**
   - 교전 상태 관리
   - 슬롯 계산, 대기열

3. **기본 전투 루프**
   - start_battle()
   - 턴 처리
   - 승패 판정

4. **도주/추적**
   - 도주 확률 계산
   - 경로 선택
   - 적 추적 AI

5. **NPC 합류**
   - 시간 경과 연동
   - 아군 AI

6. **지형 효과**
   - terrain_effects 적용
   - UI 표시

---

## 확장 가능성

### 환경 상호작용

```python
# 지형 오브젝트 활용
class BattleEnvironment:
    """전투 중 환경 요소"""

    def get_cover_objects(self, location):
        """엄폐물 목록"""
        # 바위, 나무 등 → 회피 보너스

    def get_hazards(self, location):
        """위험 요소"""
        # 함정, 불길 등 → 추가 데미지
```

### 다중 전선

```python
# 넓은 Location에서 여러 교전 그룹
engagement_groups = [
    Engagement(allies=[player], enemies=[goblin_a, goblin_b]),
    Engagement(allies=[sera], enemies=[goblin_c]),
]
```

### 전투 중 이벤트

```python
# 특정 조건에서 이벤트 발생
if state["turn"] == 5 and not state.get("reinforcement_arrived"):
    # 증원 도착 이벤트
    yield morld.dialog("[color=red]적 증원이 도착했다![/color]")
    state["reinforcement_arrived"] = True
```
