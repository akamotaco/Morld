# 전투 시스템 설계

## 개요

**전투는 별도 모드가 아니다.**
일반 게임플레이와 동일한 공간(Location)에서, 동일한 시간 시스템 위에서 전투가 진행된다.
적/아군 구분 없이 누구든 공격할 수 있고, 1D X 좌표 기반 거리가 사거리와 이동을 결정한다.

---

## 설계 철학

### 기존 시스템과의 통합

| 요소 | 일반 게임플레이 | 전투 |
|------|----------------|------|
| 공간 | Location (1D X 좌표) | 동일 |
| 시간 | 플레이어 액션 → 시간 경과 | 동일 (적이 인터럽트 가능) |
| 이동 | Gate를 통해 Location 간 이동 | Gate 방향 이동 = 도주 |
| NPC | think() → 스케줄 기반 행동 | think() → 전투 행동 |

### 핵심 원칙

1. **별도 전투 모드 없음** — 공격 액션이 있을 뿐, "전투 진입/종료"라는 상태 전환이 없다
2. **누구나 공격 대상** — 적뿐 아니라 동료도 공격 가능 (반격/적대화 포함)
3. **거리가 전부** — 교전 슬롯/용량 없음. X 좌표 차이 = 실제 거리 = 사거리 판정
4. **Location이 전장** — `length`가 전장 크기, `geometry`가 지형 특성을 결정
5. **몬스터도 NPC** — Monster는 Character의 서브클래스. 동일한 think() 기반으로 행동

### 적과 동료의 통합

몬스터와 동료 NPC는 **동일한 시스템**으로 행동한다:

| 구분 | 몬스터 | 동료 NPC |
|------|--------|----------|
| 기반 클래스 | Character | Character |
| 행동 결정 | think() | think() |
| 전투 스타일 | BATTLE_BEHAVIOR | BATTLE_BEHAVIOR |
| 적대 판정 | hostility | 호감도/신뢰도 기반 |

```python
# 몬스터도 Character를 상속
class Monster(Character):
    pass

# 고블린도, 세라도 동일한 방식으로 행동 결정
class Goblin(Monster):
    BATTLE_BEHAVIOR = {"combat_style": "aggressive", ...}

class Sera(Character):
    BATTLE_BEHAVIOR = {"combat_style": "aggressive", ...}
```

---

## 적대 유닛

### 표시

- 적대 NPC는 **붉은색 이름**으로 표시
- 중립 NPC는 기본 색상, 도발/공격 시 적대로 전환 가능

### 행동 유형

| 유형 | 행동 | 예시 |
|------|------|------|
| **호전적 (aggressive)** | 플레이어 감지 시 선제공격 | 고블린 정찰병, 늑대 |
| **영역 수호 (territorial)** | 일정 거리 내 접근 시 공격 | 동굴 골렘, 보스 |
| **소극적 (passive)** | 공격받아야 반격 | 슬라임, 초식 동물 |
| **도주형 (timid)** | 플레이어 감지 시 도망 | 토끼, 겁쟁이 고블린 |

### Monster 클래스

```python
class Monster(Character):
    # 기본 속성
    hostility: str = "aggressive"   # aggressive, territorial, passive, timid
    aggro_range: float = 100        # 감지 거리 (X 좌표 차이)
    territory_range: float = 50     # 영역 수호 범위

    # 쿨다운 시스템
    attack_cooldown: int = 8 * MILLIS_PER_SECOND  # 8초

    # AI 상태
    AI_STATE = {
        "idle": "대기",
        "chase": "추적",
        "attack": "공격",
        "flee": "도주",
        "return": "복귀",  # 영역 수호형: 영역 벗어나면 복귀
    }
```

### 몬스터 AI 로직

```python
def think_combat(self):
    """몬스터 전투 AI — think() 확장"""
    player_id = morld.get_player_id()
    distance = get_distance(self.unit_id, player_id)
    current_time = morld.get_current_time()

    # 쿨다운 체크
    last_attack = morld.get_unit_prop(self.unit_id, "_last_attack") or 0
    if current_time - last_attack < self.attack_cooldown:
        return None  # 대기

    # hostility별 분기
    if self.hostility == "aggressive":
        if distance <= self.aggro_range:
            return self._decide_attack_or_chase(player_id, distance)

    elif self.hostility == "territorial":
        if distance <= self.territory_range:
            return self._decide_attack_or_chase(player_id, distance)
        elif self._is_outside_home():
            return {"type": "return"}

    elif self.hostility == "passive":
        # 공격받은 적이 있으면 반격
        if morld.get_unit_prop(self.unit_id, "_was_attacked"):
            return self._decide_attack_or_chase(player_id, distance)

    elif self.hostility == "timid":
        if distance <= self.aggro_range:
            return {"type": "flee"}

    return None

def _decide_attack_or_chase(self, target_id, distance):
    """공격 또는 추적 결정"""
    weapon_range = morld.get_actual_prop(self.unit_id, "전투:사거리") or 30

    if distance <= weapon_range:
        return {"type": "attack", "target": target_id}
    else:
        return {"type": "chase", "target": target_id}
```

---

## 거리와 사거리

### 1D 거리 시스템

Location의 X 좌표 차이가 곧 전투 거리:

```
Location: 숲 입구 (length=1200, geometry="line")

X=0        X=200      X=500           X=900      X=1200
│          │          │               │          │
Gate ─── 플레이어 ── 고블린A ─────── 고블린B ── Gate
           ←── 300 ──→               ←── 400 ──→
              (근접 가능)              (원거리만 가능)
```

### 사거리 분류

| 분류 | 사거리 | 예시 |
|------|--------|------|
| 근접 (melee) | ~30 | 검, 도끼, 단검 |
| 중거리 (mid) | ~150 | 창, 채찍 |
| 원거리 (ranged) | ~500 | 활, 석궁 |
| 장거리 (long) | ~1000+ | 마법, 저격 |

```python
# 무기별 사거리
class IronSword(Item):
    equip_props = {
        "장착:손": 1,
        "전투:공격력": 5,
        "전투:사거리": 30,      # 근접
    }

class ShortBow(Item):
    equip_props = {
        "장착:손": 1,
        "전투:공격력": 3,
        "전투:사거리": 500,     # 원거리
        "전투:명중": -5,        # 원거리 명중 패널티
    }
```

### Ring 지형에서의 거리

`geometry="ring"`인 Location은 순환형이므로 최단 거리를 사용:

```
Ring Location (length=360)

X=350 ── Gate ── X=10
  ↑                ↓
  │   플레이어     │
  │   (X=350)      │
  │                │
  │   고블린       │
  │   (X=10)       │
  ↓                ↑
X=180 ────────── X=180

거리 = min(|350-10|, 360-|350-10|) = min(340, 20) = 20
→ 근접 공격 가능
```

---

## 이동 속도 시스템

### 기본 상수

```python
BASE_SPEED = 100  # 100 좌표/분
MILLIS_PER_MINUTE = 60000
```

### 속도 계산

```python
def get_movement_speed(unit_id):
    """이동 속도 계산: 기본값 + 민첩 보정"""
    base = morld.get_actual_prop(unit_id, "전투:이동속도") or BASE_SPEED
    agility = morld.get_actual_prop(unit_id, "전투:민첩") or 10

    # 민첩 10 기준, ±1당 2% 보정
    agility_modifier = 1.0 + (agility - 10) * 0.02

    return base * agility_modifier

def calculate_move_time(unit_id, distance):
    """이동 시간 계산"""
    speed = get_movement_speed(unit_id)
    return int((distance / speed) * MILLIS_PER_MINUTE)
```

### 지형 보정 (선택적)

Location의 `terrain_speed` prop으로 이동 속도 보정:

```python
TERRAIN_SPEED_MODIFIER = {
    "normal": 1.0,
    "forest": 0.8,   # 숲: 20% 감소
    "swamp": 0.5,    # 늪: 50% 감소
    "road": 1.2,     # 도로: 20% 증가
}
```

---

## 동작 속도 시스템

### 액션별 기본 시간

```python
MILLIS_PER_SECOND = 1000

ACTION_DURATION = {
    "melee_attack": 6 * MILLIS_PER_SECOND,    # 6초
    "ranged_attack": 10 * MILLIS_PER_SECOND,  # 10초
    "defend": 3 * MILLIS_PER_SECOND,          # 3초
    "use_item": 5 * MILLIS_PER_SECOND,        # 5초
}
```

### 무기 속도 보정

```python
class Dagger(Item):
    equip_props = {
        "전투:공격력": 3,
        "전투:사거리": 20,
        "전투:공격속도": 0.7,  # 30% 빠름
    }

class GreatSword(Item):
    equip_props = {
        "전투:공격력": 12,
        "전투:사거리": 40,
        "전투:공격속도": 1.5,  # 50% 느림
    }
```

### 최종 공격 시간 계산

```python
def get_attack_duration(unit_id, attack_type):
    """공격 시간 = 기본 시간 × 공격속도 배율"""
    base = ACTION_DURATION[attack_type]
    speed_mod = morld.get_actual_prop(unit_id, "전투:공격속도") or 1.0
    return int(base * speed_mod)
```

### 영창 시스템 (마법)

마법은 스킬별로 영창 시간 직접 정의:

```python
class Fireball(Skill):
    cast_time = 30 * MILLIS_PER_SECOND  # 30초

class Heal(Skill):
    cast_time = 10 * MILLIS_PER_SECOND  # 10초
```

---

## 액션-시간 시스템

### 기본 흐름

```
플레이어 액션 선택 (예: "영창 10분 마법")
    ↓
시간 흐름 시작 (advance_time_des)
    ↓
적 인터럽트 체크 (매 시뮬레이션 틱)
    ├─ 적이 공격 범위 내에 없음 → 계속
    ├─ 적이 공격 → 인터럽트 발생
    │   ├─ 명중 → 액션 취소, 경과 시간만 반영
    │   └─ 회피 → 액션 로그에 표시, 계속 진행
    └─ 아무 일 없음 → 액션 완료, 전체 시간 경과
```

### 플레이어 액션

| 액션 | 시간 | 이동 | 설명 |
|------|------|------|------|
| **근접 공격** | 짧음 | 대상까지 접근 | 거리에 따라 소요 시간 증가 |
| **원거리 공격** | 중간 | 없음 | 사거리 내면 제자리 공격 |
| **마법 영창** | 길음 | 없음 | 인터럽트에 취약 |
| **이동** | 거리 비례 | 지정 위치로 | 순수 이동 (공격 없음) |
| **도주** | 거리 비례 | Gate 방향 | Gate 도달 시 Location 이동 |
| **방어** | 짧음 | 없음 | 다음 인터럽트 피해 감소 |
| **아이템 사용** | 짧음 | 없음 | 회복, 버프 등 |

### 공격에 이동 포함

근접 공격 시 대상까지 자동 접근:

```python
def calculate_melee_attack_time(attacker_x, target_x, weapon_range, speed):
    """근접 공격 총 소요 시간 = 이동 시간 + 공격 시간"""
    distance = abs(attacker_x - target_x)

    if distance <= weapon_range:
        # 이미 사거리 내 → 공격만
        return MELEE_ATTACK_DURATION

    # 접근 필요
    approach_distance = distance - weapon_range
    move_time = approach_distance / speed
    return move_time + MELEE_ATTACK_DURATION
```

### 인터럽트 시스템

적이 플레이어 액션 도중 공격하는 구조:

```python
def process_player_action(action, duration):
    """플레이어 액션 처리 + 적 인터럽트"""

    elapsed = 0
    while elapsed < duration:
        # 시간 진행 (틱 단위)
        tick = min(TICK_SIZE, duration - elapsed)
        morld.advance_time_des(tick)
        elapsed += tick

        # 적 행동 체크
        for enemy in get_hostile_units_at_location():
            enemy_action = enemy.think_combat()
            if enemy_action and enemy_action.type == "attack":
                # 인터럽트 시도
                hit, damage, result_text = resolve_attack(enemy, player)
                if hit:
                    # 명중 → 플레이어 액션 취소
                    cancel_player_action()
                    return {"interrupted": True, "elapsed": elapsed, "damage": damage}
                else:
                    # 회피 → 액션 로그에 기록, 계속 진행
                    add_action_log(result_text)

    # 인터럽트 없이 완료
    return {"interrupted": False, "elapsed": duration}
```

---

## 지형과 전투

### Length의 의미

Location의 `length`가 전장 크기를 결정:

| Location | length | 전투 특성 |
|----------|--------|----------|
| 좁은 통로 | 100~200 | 근접전 강제. 원거리 의미 없음. 도주 어려움. |
| 일반 방/숲길 | 300~600 | 근접/원거리 혼합. |
| 넓은 들판 | 1000~2000 | 원거리 유리. 접근에 시간 소요. |
| 매우 넓은 지역 | 3000+ | 장거리 무기 필수. 근접은 접근만으로 상당 시간. |

### Geometry의 영향

| Geometry | 전투 특성 |
|----------|----------|
| **line** | 양쪽 끝이 막혀 있음. 양쪽 Gate로만 탈출 가능. 일직선 전투. |
| **ring** | 순환형. 적을 우회할 수 있음. 포위/배후 공격 가능. |

### 좁은 지형의 자연 효과

별도 `terrain_type` 없이, `length`만으로 지형 효과가 자연 발생:

```
좁은 동굴 (length=100):
- 모든 유닛이 사거리 30 내에 있음 → 근접 무기만으로 전체 공격 가능
- 도주 시 Gate까지 거리가 짧지만, 적이 가로막고 있으면 통과 불가
- 원거리 무기의 이점 없음

넓은 평원 (length=2000):
- 원거리 유닛이 거리를 유지하며 일방적 공격 가능
- 근접 전사가 접근하는 데만 수 분 소요
- 도주가 쉬움 (Gate까지 거리가 멀어도 적과도 멀리 떨어져 있으므로)
```

---

## 전투 스탯

### 기본 스탯

| 스탯 | 기본값 | 용도 |
|------|--------|------|
| `전투:체력` | 100 | 현재 HP |
| `전투:최대체력` | 100 | 최대 HP |
| `전투:공격력` | 5 | 데미지 기본값 |
| `전투:방어력` | 0 | 피해 감소 |
| `전투:민첩` | 10 | 이동 속도 보정, 회피 보정 |
| `전투:명중` | 80 | 명중률 (%) |
| `전투:회피` | 5 | 회피율 (%) |
| `전투:치명타율` | 5 | 크리티컬 확률 (%) |
| `전투:사거리` | 30 | 공격 거리 |
| `전투:이동속도` | 100 | 좌표/분 |
| `전투:공격속도` | 1.0 | 공격 시간 배율 |
| `전투:시야` | 100 | 감지 거리 (NPC용) |

```python
props = {
    "전투:체력": 100,
    "전투:최대체력": 100,
    "전투:공격력": 5,
    "전투:방어력": 0,
    "전투:민첩": 10,
    "전투:명중": 80,
    "전투:회피": 5,
    "전투:치명타율": 5,
    "전투:사거리": 30,
    "전투:이동속도": 100,   # 좌표/분
    "전투:공격속도": 1.0,   # 배율
    "전투:시야": 100,       # NPC 감지 거리
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
        "전투:사거리": 30,
    }
```

### 데미지 계산

```python
def resolve_attack(attacker_id, defender_id):
    """공격 판정"""
    distance = get_distance(attacker_id, defender_id)
    weapon_range = morld.get_actual_prop(attacker_id, "전투:사거리") or 30

    # 사거리 체크
    if distance > weapon_range:
        return False, 0, "사거리 밖"

    # 명중 판정
    hit = morld.get_actual_prop(attacker_id, "전투:명중") or 85
    eva = morld.get_actual_prop(defender_id, "전투:회피") or 0
    if random.randint(1, 100) > (hit - eva):
        return False, 0, "회피"

    # 데미지 계산
    atk = morld.get_actual_prop(attacker_id, "전투:공격력") or 1
    def_ = morld.get_actual_prop(defender_id, "전투:방어력") or 0
    base = max(1, atk - def_ // 2)

    # 치명타
    crit_rate = morld.get_actual_prop(attacker_id, "전투:치명타율") or 5
    is_crit = random.randint(1, 100) <= crit_rate
    if is_crit:
        base = int(base * 1.5)

    # 편차 ±10%
    damage = int(base * random.uniform(0.9, 1.1))
    return True, damage, "치명타" if is_crit else "일반"
```

---

## 전투 상태 판정

### 암묵적 전투 상태

별도 "전투 모드" 플래그 없이, 상황으로 판정:

```python
def is_in_combat(unit_id):
    """적대 유닛이 aggro 범위 내에 있으면 전투 중"""
    location_id = morld.get_unit_location(unit_id)
    hostiles = get_hostile_units_at_location(location_id)

    for h in hostiles:
        distance = get_distance(unit_id, h)
        aggro = morld.get_unit_prop(h, "aggro_range") or 100
        if distance <= aggro:
            return True
    return False

def get_combat_context(unit_id):
    """전투 컨텍스트 반환 (인터럽트 체크 여부 결정용)"""
    if not is_in_combat(unit_id):
        return None

    return {
        "hostiles": get_hostile_units_in_range(unit_id),
        "allies": get_allied_units_at_location(unit_id),
    }
```

### 인터럽트 체크 조건

플레이어 액션 처리 시:

```python
def process_player_action(action, duration):
    combat_ctx = get_combat_context(player_id)

    if combat_ctx is None:
        # 비전투 상황: 인터럽트 체크 없이 즉시 처리
        morld.advance_time(duration)
        return execute_action(action)

    # 전투 상황: 인터럽트 체크하며 시간 진행
    return process_action_with_interrupt(action, duration, combat_ctx)
```

---

## 도주

### Gate 기반 도주

도주 = Gate 방향으로 이동. Gate에 도달하면 Location 탈출:

```
Location: 숲길 (length=1200)

X=0(Gate)   X=400(플레이어)   X=800(고블린)   X=1200(Gate)
│           │                 │               │
Gate_A ←── 도주 ──             ── 추적 ──→     Gate_B
```

- 플레이어가 Gate_A(X=0) 방향으로 도주: 거리 400, 이동 시간 계산
- 이동 중 적이 인터럽트 가능 (추적 공격)
- Gate 도달 시 Location 전환 → 전투 이탈

### 도주 판정

```python
def attempt_flee(unit_id, gate_id):
    """도주 시도 판정"""
    distance_to_gate = get_distance_to_gate(unit_id, gate_id)
    flee_time = calculate_move_time(unit_id, distance_to_gate)

    # 근접 적이 가로막고 있는지 체크
    blocking_enemies = get_enemies_between(unit_id, gate_id)

    result = {
        "can_flee": True,
        "flee_time": flee_time,
        "risks": [],
    }

    if blocking_enemies:
        # 기회 공격 (opportunity attack) 받음
        result["risks"].append({
            "type": "opportunity_attack",
            "enemies": blocking_enemies,
        })

    # 원거리 적의 추격 공격
    ranged_enemies = get_ranged_enemies_in_range(unit_id)
    if ranged_enemies:
        result["risks"].append({
            "type": "pursuit_attack",
            "enemies": ranged_enemies,
        })

    return result
```

### 도주 실행

```python
def execute_flee(unit_id, gate_id):
    """도주 실행 - 인터럽트 가능"""
    flee_result = attempt_flee(unit_id, gate_id)

    # 도주 중 인터럽트 처리
    action_result = process_action_with_interrupt(
        unit_id,
        duration=flee_result["flee_time"],
        action_type="flee",
        interruptible=True,
    )

    if action_result["interrupted"]:
        # 도주 실패 - 현재 위치 유지
        return {"success": False, "reason": "interrupted"}

    # 도주 성공 - Location 이동
    new_location = get_gate_destination(gate_id)
    morld.set_unit_location(unit_id, new_location)
    return {"success": True, "new_location": new_location}
```

### 추적

적이 도주하는 플레이어를 추격:

```python
class Monster(Character):
    chase_chance: int = 30        # 추적 확률 (%)
    chase_distance: float = 500   # 최대 추적 거리 (같은 Location 내)
```

---

## NPC 전투 AI

### 전투 스타일 (combat_style)

모든 NPC(몬스터/동료)는 X축 기반 전투 스타일을 가진다:

| 스타일 | 설명 | X축 행동 | 예시 |
|--------|------|----------|------|
| **aggressive** | 선공형 | 적에게 접근, 먼저 공격 | 세라, 고블린, 늑대 |
| **defensive** | 수비형 | 거리 유지, 반격 위주 | 밀라, 동굴 골렘 |
| **evasive** | 도주형 | 위협 시 후퇴, 안전거리 확보 | 리나, 토끼, 겁쟁이 고블린 |

```python
def think_combat_movement(self):
    """전투 중 X축 이동 결정"""
    target = self._get_combat_target()
    if not target:
        return None

    distance = get_distance(self.unit_id, target)
    style = self.BATTLE_BEHAVIOR.get("combat_style", "defensive")

    if style == "aggressive":
        # 선공형: 사거리까지 접근
        weapon_range = morld.get_actual_prop(self.unit_id, "전투:사거리") or 30
        if distance > weapon_range:
            return {"type": "move", "direction": "toward", "target": target}

    elif style == "defensive":
        # 수비형: preferred_range 유지
        preferred = self.BATTLE_BEHAVIOR.get("preferred_range", 100)
        if distance < preferred * 0.7:
            return {"type": "move", "direction": "away", "target": target}
        # 적이 접근하면 반격

    elif style == "evasive":
        # 도주형: 위협 감지 시 즉시 후퇴
        danger_range = self.BATTLE_BEHAVIOR.get("danger_range", 150)
        if distance < danger_range:
            return {"type": "flee"}

    return None
```

### BATTLE_BEHAVIOR 전체 스펙

```python
class Character(Unit):
    BATTLE_BEHAVIOR: dict = {
        # 전투 스타일 (X축 행동)
        "combat_style": "defensive",    # aggressive, defensive, evasive

        # 타겟팅
        "target_priority": "nearest",   # nearest, weakest, strongest, random

        # 거리 설정
        "preferred_range": 30,          # 선호 교전 거리
        "danger_range": 150,            # evasive: 위협 감지 거리

        # 생존 본능
        "retreat_threshold": 20,        # HP% 이하면 후퇴 시도

        # 동료 전용
        "join_combat": True,            # 전투 합류 의지
        "join_threshold": 30,           # 합류에 필요한 호감도
        "protect_player": False,        # 플레이어 보호 우선
    }
```

### 캐릭터별 예시

```python
# 세라 - 선공형 근접 전사
class Sera(Character):
    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",   # 적에게 돌진
        "target_priority": "strongest",
        "preferred_range": 30,          # 근접
        "retreat_threshold": 15,        # 위험해도 공격
        "protect_player": True,
        "join_combat": True,
        "join_threshold": 20,
    }

# 밀라 - 수비형 원거리 지원
class Mila(Character):
    BATTLE_BEHAVIOR = {
        "combat_style": "defensive",    # 거리 유지, 반격
        "target_priority": "weakest",
        "preferred_range": 300,         # 원거리 유지
        "retreat_threshold": 50,        # 안전 우선
        "join_combat": True,
        "join_threshold": 40,
    }

# 리나 - 도주형 (비전투원)
class Lina(Character):
    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",      # 위협 시 도주
        "danger_range": 200,            # 넓은 위협 감지
        "retreat_threshold": 80,        # 조금만 다쳐도 도주
        "join_combat": False,           # 전투 합류 안함
    }

# 고블린 - 선공형 적
class Goblin(Monster):
    hostility = "aggressive"
    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 30,
        "retreat_threshold": 10,        # 거의 죽기 전까지 공격
    }

# 동굴 골렘 - 수비형 영역 수호
class CaveGolem(Monster):
    hostility = "territorial"
    BATTLE_BEHAVIOR = {
        "combat_style": "defensive",
        "target_priority": "nearest",
        "preferred_range": 50,
        "retreat_threshold": 0,         # 죽을 때까지 수호
    }
```

### NPC 전투 합류

같은 Location에 있는 우호적 NPC의 전투 합류:

```python
def check_npc_combat_join(location_id):
    """전투 중인 Location에서 NPC 합류 체크"""
    npcs = get_friendly_npcs_at_location(location_id)
    joiners = []

    for npc in npcs:
        behavior = npc.BATTLE_BEHAVIOR
        if not behavior.get("join_combat"):
            continue

        # 호감도 체크
        affection = morld.get_unit_prop(npc.unit_id, "호감도") or 0
        if affection < behavior.get("join_threshold", 0):
            continue

        # 전투 가능 상태 체크 (HP, 상태이상 등)
        if not can_fight(npc.unit_id):
            continue

        joiners.append(npc)

    return joiners
```

**합류 타이밍:**
- 전투 시작 시 1회 체크
- 시간 경과 중 새 NPC 도착 시 추가 체크

### think() 통합 구조

몬스터와 동료 NPC 모두 동일한 think() 흐름:

```python
def think(self):
    """NPC AI 메인 루프"""
    # 1. 전투 상황 체크
    if self._is_in_combat_situation():
        combat_action = self.think_combat()
        if combat_action:
            return combat_action

    # 2. 일반 스케줄 (비전투 시)
    return self.think_schedule()

def think_combat(self):
    """전투 AI — 몬스터/동료 공통"""
    # 타겟 선정
    target = self._select_combat_target()
    if not target:
        return None

    # 쿨다운 체크
    if not self._can_attack():
        return None

    # combat_style에 따른 행동
    style = self.BATTLE_BEHAVIOR.get("combat_style", "defensive")
    distance = get_distance(self.unit_id, target)

    if style == "aggressive":
        return self._aggressive_behavior(target, distance)
    elif style == "defensive":
        return self._defensive_behavior(target, distance)
    elif style == "evasive":
        return self._evasive_behavior(target, distance)

    return None
```

---

## 전투 UI

### 일반 전투 (액션 로그 기반)

전투는 별도 UI가 아니라 **액션 로그**와 **상황 텍스트**로 표현:

```
═══ 숲 입구 ═══

[color=red]고블린 정찰병[/color]이 앞을 가로막고 있다.

──────────────────────
고블린 정찰병이 돌진해 온다!
세라: "...뒤는 맡겨."
──────────────────────

행동 선택:
  [공격 → 고블린 정찰병] (거리: 80, 접근 필요)
  [활 공격 → 고블린 정찰병] (거리: 80, 사거리 내)
  [아이템]
  [도주 → 저택 방면] (Gate까지 200)
  [도주 → 숲 깊은 곳] (Gate까지 1000)
```

### 인터럽트 발생 시

```
──────────────────────
마법 영창 시작... (10분)
  [3분 경과]
  고블린 정찰병의 공격! → 12 데미지
  영창이 풀렸다!
──────────────────────
```

### 인터럽트 회피 시

```
──────────────────────
마법 영창 시작... (10분)
  [3분 경과]
  고블린 정찰병의 공격! → 회피!
  [10분 경과]
  마법 발동! → 고블린 정찰병에게 35 데미지
──────────────────────
```

---

## 파일 구조

```
scenarios/scenario02/python/
├─ assets/
│   ├─ base.py              # Character: BATTLE_BEHAVIOR, hostility, aggro_range
│   ├─ locations/
│   │   └─ *.py             # length, geometry (기존 속성이 전투에도 활용)
│   └─ characters/
│       ├─ monsters/         # Monster 클래스 (적 유닛)
│       └─ *.py              # NPC별 BATTLE_BEHAVIOR
├─ think/
│   └─ __init__.py           # think_combat() — 전투 AI 확장
└─ docs/
    └─ battle.md             # 이 문서
```

---

## 구현 순서 (제안)

### Phase 1: 기반 시스템

```
├─ 전투 스탯 props 정의 (체력, 공격력, 사거리 등)
├─ 장비에 전투 스탯 추가
├─ 이동/동작 속도 상수 및 함수
│   ├─ get_movement_speed()
│   ├─ calculate_move_time()
│   └─ get_attack_duration()
└─ is_in_combat() 전투 상태 판정 함수
```

### Phase 2: 플레이어 전투

```
├─ 공격 액션 (근접/원거리)
│   ├─ 거리 + 사거리 체크
│   └─ 근접 공격 시 자동 접근
├─ 데미지 계산
│   ├─ 명중/회피 판정
│   └─ 치명타 판정
└─ 도주 시스템
    ├─ attempt_flee() 판정
    └─ execute_flee() 실행
```

### Phase 3: 적 AI

```
├─ Monster 클래스
│   ├─ hostility 유형별 분기
│   ├─ aggro_range, territory_range
│   └─ attack_cooldown 쿨다운
├─ think_combat() 구현
│   └─ 공격/추적/도주 결정
└─ 인터럽트 시스템
    ├─ process_action_with_interrupt()
    └─ 명중 시 액션 취소
```

### Phase 4: 아군 AI

```
├─ BATTLE_BEHAVIOR 확장
│   ├─ join_combat, join_threshold
│   └─ protect_player
├─ check_npc_combat_join() 합류 로직
└─ 아군 전투 AI
    └─ target_priority, retreat_threshold
```

### Phase 5: 확장

```
├─ 오프스크린 전투
│   ├─ resolve_offscreen_combat()
│   └─ 결과 표시
├─ 상태이상 시스템
└─ 환경 상호작용
```

---

## 오프스크린 전투

플레이어가 없는 Location에서의 NPC 간 전투 처리.

### 설계 원칙

- 플레이어 Location만 상세 시뮬레이션
- 다른 Location은 간소화된 결과 계산
- 플레이어가 도착하면 결과 표시

### 간소화 처리

```python
def advance_time_des(millis):
    player_loc = morld.get_player_location()

    # 플레이어 Location: 상세 전투 시뮬레이션
    simulate_combat_detailed(player_loc, millis)

    # 다른 Location: 간소화 처리
    for loc in get_locations_with_combat():
        if loc != player_loc:
            resolve_offscreen_combat(loc, millis)

def resolve_offscreen_combat(location_id, duration):
    """오프스크린 전투 간소화 처리"""
    combatants = get_all_combatants_at(location_id)

    # 세력별 전투력 합산
    team_power = {}
    for unit in combatants:
        team = get_unit_team(unit)
        power = calculate_combat_power(unit)
        team_power[team] = team_power.get(team, 0) + power

    # 시간당 피해 교환 (간소화)
    ticks = duration // COMBAT_TICK
    for _ in range(ticks):
        for unit in combatants:
            if is_dead(unit):
                continue

            enemy_power = get_enemy_team_power(unit, team_power)
            if random.random() < 0.3:  # 30% 확률로 피해
                damage = estimate_damage(enemy_power, unit)
                apply_damage(unit, damage)

    # 결과 기록
    record_combat_result(location_id, combatants)
```

### 결과 표시

```python
def on_player_arrive(location_id):
    """플레이어가 Location에 도착했을 때"""
    combat_result = get_recent_combat_result(location_id)
    if combat_result:
        # "세라가 고블린 2마리를 처치했다. 세라가 부상을 입었다."
        yield ui.narration(format_combat_result(combat_result))
```

---

## 확장 가능성

### 상태이상

```python
# props로 관리
"상태:독": 5,        # 5턱 남음 → 틱마다 HP 감소
"상태:둔화": 3,      # 이동 속도 감소
"상태:출혈": 10,     # 피해 지속
```

### 환경 상호작용

Location 내 오브젝트 활용:
- 바위 뒤에 숨기 (회피 보너스)
- 함정 설치/활성화
- 좁은 문 지형지물로 근접전 유도

---

## 근거리/원거리 무기 시스템

> **시나리오 2/3 공용 설계**
> 시나리오 2(판타지: 검, 활, 마법)와 시나리오 3(현대: 총기, 실내 전투)의 핵심 시스템을 공유한다.

### 무기 분류

| 분류 | 시나리오 2 | 시나리오 3 | 특성 |
|------|-----------|-----------|------|
| **근접 (melee)** | 검, 도끼, 단검 | 나이프, 근접 격투 | 사거리 짧음, 엄폐 무시 |
| **원거리 (ranged)** | 활, 석궁 | 권총, 소총 | 사거리 김, 엄폐 영향 |
| **투척 (thrown)** | 투척 단검, 도끼 | 수류탄 | 포물선, 엄폐 부분 무시 |
| **특수** | 마법 | - | 시나리오별 고유 |

### 무기 속성

```python
class Weapon(Item):
    equip_props = {
        # 기본
        "전투:공격력": 10,
        "전투:사거리": 30,
        "전투:명중": 0,          # 기본 명중 보정

        # 무기 유형
        "무기:유형": "melee",    # melee, ranged, thrown
        "무기:양손": False,      # 양손 무기 여부

        # 원거리 전용
        "무기:탄약": None,       # 탄약 타입 (arrow, bullet, etc)
        "무기:장탄수": None,     # 최대 장탄수
        "무기:재장전시간": None, # 밀리초

        # 엄폐 관련
        "무기:엄폐관통": 0,      # 엄폐 무시율 (%)
    }
```

### 근접 vs 원거리 판정 차이

```python
def resolve_attack(attacker_id, defender_id, weapon):
    weapon_type = weapon.get("무기:유형", "melee")

    if weapon_type == "melee":
        # 근접: 엄폐 무시, 거리 내 100% 명중 가능
        return resolve_melee_attack(attacker_id, defender_id, weapon)

    elif weapon_type == "ranged":
        # 원거리: 엄폐/은폐 영향, 거리에 따른 명중 감소
        return resolve_ranged_attack(attacker_id, defender_id, weapon)

    elif weapon_type == "thrown":
        # 투척: 엄폐 부분 무시, 범위 피해 가능
        return resolve_thrown_attack(attacker_id, defender_id, weapon)
```

---

## 엄폐/은폐 시스템

> 시나리오 3(현대 총기전)의 핵심이지만, 시나리오 2(판타지 원거리)에도 적용 가능.

### 용어 정의

| 용어 | 영문 | 설명 | 효과 |
|------|------|------|------|
| **엄폐** | Cover | 물리적 차폐물 뒤에 숨음 | 피해 감소, 명중률 감소 |
| **은폐** | Concealment | 시야 차단 (연기, 어둠) | 명중률 감소만 |

### 엄폐 등급

```python
COVER_LEVEL = {
    "none": {
        "hit_modifier": 0,      # 명중 보정 없음
        "damage_reduction": 0,  # 피해 감소 없음
    },
    "partial": {  # 부분 엄폐 (낮은 벽, 나무)
        "hit_modifier": -20,    # 명중률 -20%
        "damage_reduction": 0.3, # 피해 30% 감소
    },
    "half": {  # 절반 엄폐 (창문, 차량)
        "hit_modifier": -40,
        "damage_reduction": 0.5,
    },
    "full": {  # 완전 엄폐 (벽 뒤)
        "hit_modifier": -80,    # 거의 맞지 않음
        "damage_reduction": 0.9,
    },
}
```

### 엄폐 오브젝트

Location 내 Ground 오브젝트로 엄폐물 배치:

```python
class CoverObject(Ground):
    cover_level: str = "partial"  # none, partial, half, full
    cover_hp: int = 100           # 파괴 가능 (총기전)
    cover_direction: str = "both" # 방어 방향 (left, right, both)

# 예시
class LowWall(CoverObject):
    name = "낮은 벽"
    cover_level = "half"
    cover_hp = 200

class Pillar(CoverObject):
    name = "기둥"
    cover_level = "partial"
    cover_direction = "both"  # 360도 방어
```

### 엄폐 행동

```python
# 플레이어/NPC 액션
ACTION_DURATION["take_cover"] = 2 * MILLIS_PER_SECOND  # 엄폐하기
ACTION_DURATION["leave_cover"] = 1 * MILLIS_PER_SECOND # 엄폐 해제

def take_cover(unit_id, cover_object_id):
    """엄폐 상태로 전환"""
    morld.set_unit_prop(unit_id, "_in_cover", cover_object_id)
    morld.set_unit_prop(unit_id, "_cover_level", get_cover_level(cover_object_id))

def is_in_cover(unit_id):
    return morld.get_unit_prop(unit_id, "_in_cover") is not None
```

### 엄폐 상태에서의 공격

```python
def attack_from_cover(attacker_id, target_id):
    """엄폐 상태에서 공격 - 잠시 노출됨"""
    # 공격 시 엄폐 효과 일시 해제
    # 적도 이 타이밍에 반격 가능 (인터럽트)

    cover_id = morld.get_unit_prop(attacker_id, "_in_cover")

    # 엄폐 해제 → 공격 → 엄폐 복귀
    return {
        "phases": [
            {"action": "expose", "duration": 1 * MILLIS_PER_SECOND},
            {"action": "attack", "duration": get_attack_duration(attacker_id)},
            {"action": "return_cover", "duration": 1 * MILLIS_PER_SECOND},
        ],
        "vulnerable_during": ["expose", "attack"],  # 이 구간에 인터럽트 가능
    }
```

---

## 회피 시스템

### 회피 유형

| 유형 | 설명 | 발동 조건 | 효과 |
|------|------|----------|------|
| **수동 회피** | 기본 회피율 | 항상 적용 | `전투:회피` 스탯 |
| **능동 회피** | 회피 동작 선택 | 플레이어 액션 | 높은 회피율, 반격 불가 |
| **구르기** | 위치 이동 + 회피 | 플레이어 액션 | 회피 + X축 이동 |

### 수동 회피 (기존)

```python
# 기본 명중/회피 판정
hit_chance = attacker_hit - defender_evasion
# 예: 80 - 15 = 65% 명중
```

### 능동 회피 동작

```python
ACTION_DURATION["dodge"] = 3 * MILLIS_PER_SECOND    # 회피 자세
ACTION_DURATION["roll"] = 4 * MILLIS_PER_SECOND     # 구르기 (이동 포함)

def execute_dodge(unit_id):
    """능동 회피 - 다음 공격 고회피, 반격 불가"""
    morld.set_unit_prop(unit_id, "_dodging", True)
    morld.set_unit_prop(unit_id, "_dodge_bonus", 50)  # +50% 회피
    # 회피 중에는 공격 불가

def execute_roll(unit_id, direction):
    """구르기 - 회피 + X축 이동"""
    roll_distance = 50  # 50 좌표 이동
    morld.set_unit_prop(unit_id, "_dodging", True)
    morld.set_unit_prop(unit_id, "_dodge_bonus", 30)

    # X축 이동
    current_x = morld.get_unit_prop(unit_id, "position_x")
    new_x = current_x + (roll_distance if direction == "right" else -roll_distance)
    morld.set_unit_prop(unit_id, "position_x", new_x)
```

### 회피 판정 통합

```python
def calculate_hit_chance(attacker_id, defender_id, weapon):
    """최종 명중률 계산"""
    # 기본
    base_hit = morld.get_actual_prop(attacker_id, "전투:명중") or 80
    base_eva = morld.get_actual_prop(defender_id, "전투:회피") or 5

    # 무기 보정
    weapon_hit = weapon.get("전투:명중", 0)

    # 거리 보정 (원거리만)
    distance = get_distance(attacker_id, defender_id)
    range_penalty = calculate_range_penalty(distance, weapon)

    # 엄폐 보정 (원거리만)
    cover_penalty = 0
    if weapon.get("무기:유형") == "ranged":
        cover_level = morld.get_unit_prop(defender_id, "_cover_level")
        if cover_level:
            cover_penalty = COVER_LEVEL[cover_level]["hit_modifier"]
            # 엄폐 관통 적용
            penetration = weapon.get("무기:엄폐관통", 0)
            cover_penalty = int(cover_penalty * (1 - penetration / 100))

    # 능동 회피 보정
    dodge_bonus = morld.get_unit_prop(defender_id, "_dodge_bonus") or 0

    # 최종 계산
    final_hit = base_hit + weapon_hit - base_eva - range_penalty - cover_penalty - dodge_bonus
    return max(5, min(95, final_hit))  # 5% ~ 95% 범위
```

---

## 시나리오별 차이점

| 요소 | 시나리오 2 (판타지) | 시나리오 3 (현대) |
|------|-------------------|-----------------|
| **주요 원거리** | 활, 석궁 | 권총, 소총, 산탄총 |
| **엄폐 중요도** | 낮음 (근접 위주) | 높음 (필수) |
| **탄약 시스템** | 화살 (단순) | 탄창, 재장전 (복잡) |
| **엄폐물 파괴** | 드묾 | 흔함 (총기 관통) |
| **특수 무기** | 마법 (엄폐 무시 가능) | 수류탄 (범위 피해) |

### 시나리오 3 전용 확장

```python
# 탄약 시스템 (시나리오 3)
class ModernWeapon(Weapon):
    equip_props = {
        "무기:탄약타입": "9mm",
        "무기:장탄수": 15,
        "무기:재장전시간": 3 * MILLIS_PER_SECOND,
        "무기:연사": True,       # 자동/반자동
        "무기:연사속도": 3,      # 초당 발사 수
    }

# 재장전 액션
ACTION_DURATION["reload"] = 3 * MILLIS_PER_SECOND

# 엄폐물 파괴
def damage_cover(cover_id, damage, penetration):
    """엄폐물에 피해 - 파괴 가능"""
    cover_hp = morld.get_unit_prop(cover_id, "cover_hp")
    effective_damage = damage * (penetration / 100)
    new_hp = cover_hp - effective_damage

    if new_hp <= 0:
        destroy_cover(cover_id)
```

### Location 용량 제한 (미정)

현재는 동일한 X 좌표에 무한한 캐릭터가 위치할 수 있다.
향후 필요 시 Location 내 캐릭터 수를 제한하는 시스템 고려:

```python
# 잠재적 구현 방향
class Location:
    capacity: int = None  # None = 무제한, 숫자 = 최대 인원

# 또는 X 좌표 점유 시스템
# - 같은 X 좌표에는 N명까지만 위치 가능
# - 좁은 통로에서 병목 효과
# - "밀어내기" 메커니즘
```

### 동료 공격과 적대화

시스템상 플레이어는 동료 NPC도 공격할 수 있다. 공격받은 NPC는 호감도/신뢰도에 따라 반응한다.

#### 적대화 판정

```python
def on_attacked_by_player(npc_id, damage):
    """동료 NPC가 플레이어에게 공격받았을 때"""
    affection = morld.get_unit_prop(npc_id, "호감도") or 0
    trust = morld.get_unit_prop(npc_id, "신뢰도") or 0

    # 호감도/신뢰도 감소
    morld.modify_prop(npc_id, "호감도", -30)
    morld.modify_prop(npc_id, "신뢰도", -50)

    # 적대화 판정
    new_affection = affection - 30
    new_trust = trust - 50

    if new_trust <= -50:
        # 완전 적대화: 적으로 전환
        return {"reaction": "hostile", "attacks_back": True}

    elif new_affection <= 0:
        # 반격 후 관계 단절
        return {"reaction": "defensive", "attacks_back": True, "leaves_party": True}

    else:
        # 경고 또는 방어 자세
        return {"reaction": "warning", "attacks_back": False}
```

#### 반응 유형

| 반응 | 조건 | 행동 |
|------|------|------|
| **warning** | 호감도 > 0 | "왜 이러는 거야?" 경고만 |
| **defensive** | 호감도 ≤ 0 | 반격 후 파티 이탈 |
| **hostile** | 신뢰도 ≤ -50 | 완전 적대화, 적으로 전환 |

#### 캐릭터별 반응 차이

```python
class Sera(Character):
    HOSTILITY_THRESHOLD = {
        "warning_affection": 30,    # 높은 호감도까지 경고만
        "defensive_trust": -30,     # 쉽게 적대화하지 않음
        "combat_style_on_hostile": "aggressive",  # 적대화 시 공격적
    }

class Lina(Character):
    HOSTILITY_THRESHOLD = {
        "warning_affection": 50,    # 금방 겁먹음
        "defensive_trust": 0,       # 신뢰 잃으면 바로 도주
        "combat_style_on_hostile": "evasive",  # 적대화 시 도망
    }
```

#### NPC 간 전투

동료 NPC끼리 또는 동료-적 간 자동 전투:

```python
def think_combat(self):
    """전투 AI - 타겟 선정"""
    # 1. 적대 유닛 우선
    hostiles = self._get_hostile_units()
    if hostiles:
        return self._decide_combat_action(hostiles)

    # 2. 자신을 공격한 유닛 (동료라도)
    attacker = morld.get_unit_prop(self.unit_id, "_last_attacker")
    if attacker and self._should_retaliate(attacker):
        return self._decide_combat_action([attacker])

    return None
```
