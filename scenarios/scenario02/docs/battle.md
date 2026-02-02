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
2. **누구나 공격 대상** — 적뿐 아니라 동료도 공격 가능 (반격 포함)
3. **거리가 전부** — 교전 슬롯/용량 없음. X 좌표 차이 = 실제 거리 = 사거리 판정
4. **Location이 전장** — `length`가 전장 크기, `geometry`가 지형 특성을 결정

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

```python
class Monster(Character):
    hostility: str = "aggressive"   # aggressive, territorial, passive, timid
    aggro_range: float = 100        # 감지 거리 (X 좌표 차이)
    territory_range: float = 50     # 영역 수호 범위
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

## 액션-시간 시스템

### 기본 흐름

```
플레이어 액션 선택 (예: "영창 10분 마법")
    ↓
시간 흐름 시작 (advance_time_simulate)
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
        morld.advance_time_simulate(tick)
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

```python
props = {
    "전투:체력": 100,
    "전투:최대체력": 100,
    "전투:공격력": 10,
    "전투:방어력": 5,
    "전투:민첩": 10,       # 이동 속도, 회피에 영향
    "전투:명중": 85,
    "전투:회피": 10,
    "전투:치명타율": 5,
    "전투:사거리": 30,     # 기본 사거리 (맨손)
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

### 추적

적이 도주하는 플레이어를 추격:

```python
class Monster(Character):
    chase_chance: int = 30        # 추적 확률 (%)
    chase_distance: float = 500   # 최대 추적 거리 (같은 Location 내)
```

---

## NPC 전투 AI

### 캐릭터별 행동

```python
class Character(Unit):
    BATTLE_BEHAVIOR: dict = {
        "target_priority": "nearest",   # nearest, weakest, strongest, random
        "retreat_threshold": 20,        # HP 20% 이하면 후퇴 시도
        "preferred_range": 30,          # 선호 교전 거리
    }
```

### 캐릭터별 예시

```python
# 세라 - 근접 공격적
class Sera(Character):
    BATTLE_BEHAVIOR = {
        "target_priority": "strongest",
        "retreat_threshold": 15,     # 위험해도 공격
        "preferred_range": 30,       # 근접
        "protect_player": True,
    }

# 밀라 - 원거리 지원
class Mila(Character):
    BATTLE_BEHAVIOR = {
        "target_priority": "weakest",
        "retreat_threshold": 50,     # 안전 우선
        "preferred_range": 300,      # 거리 유지
        "support_priority": True,
    }
```

### 적 AI

```python
def think_combat(self):
    """적 전투 AI — think() 확장"""
    player_id = morld.get_player_id()
    distance = get_distance(self.unit_id, player_id)

    if self.hostility == "aggressive":
        if distance <= self.aggro_range:
            return self._decide_attack(player_id, distance)

    elif self.hostility == "territorial":
        if distance <= self.territory_range:
            return self._decide_attack(player_id, distance)

    elif self.hostility == "timid":
        if distance <= self.aggro_range:
            return {"type": "flee"}  # 도주

    return None  # 행동 없음
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

1. **전투 스탯 기반**
   - 전투 관련 props 정의 (체력, 공격력, 사거리 등)
   - 장비에 전투 스탯 추가

2. **공격 액션**
   - 플레이어 공격 액션 (근접/원거리)
   - 데미지 계산, 명중/회피 판정
   - 거리 + 사거리 체크

3. **적 유닛**
   - Monster 클래스 (hostility, aggro_range)
   - 적 think() — 선제공격, 영역 수호 등

4. **인터럽트 시스템**
   - 플레이어 액션 중 적 행동 체크
   - 인터럽트 성공/회피 처리

5. **도주/추적**
   - Gate 방향 이동
   - 적 추적 AI

6. **NPC 전투 참여**
   - 아군 NPC AI (BATTLE_BEHAVIOR)
   - 시간 경과 중 NPC 도착/합류

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

### 동료 공격/반격

향후 구현:
- 플레이어가 동료를 공격하면 호감도 급감 + 반격
- NPC 간 전투 (적대 NPC vs 아군 NPC)
- 오인 사격 (원거리 공격이 아군에게 맞을 확률)
