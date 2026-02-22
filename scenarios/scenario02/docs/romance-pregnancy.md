# 임신과 출산 시스템 (Pregnancy & Childbirth)

## 개요

삽입 행위 → 임신 판정 → 임신 기간(40주) → 출산 → 아이 NPC 생성까지의
생명 주기 시스템. 현실적 타이밍을 기본으로 하되, 디버그 배율로 속도 조절 가능.

**관련 문서:**
| 문서 | 참조 내용 |
|------|----------|
| [romance-actions.md](romance-actions.md) | 삽입 행위 정의 (12절) |
| [romance-relationship.md](romance-relationship.md) | 관계 시스템 |
| [life.md](life.md) | NPC 욕구/생활 패턴 |

**파일 구조:**
```
scenarios/scenario02/python/
├── pregnancy.py            # 임신 시스템 (월경/수정/임신/출산)
├── needs.py                # 욕구 시스템 (임신 연동 hook)
├── think/
│   ├── __init__.py         # BaseAgent (Tier 4: 출산 인터럽트)
│   └── activities/
│       └── childbirth.py   # 출산 활동 핸들러
└── assets/characters/
    └── child.py            # 아이 NPC Asset + Agent 클래스
```

---

## 1. 시간 스케일 (Time Scale)

### 설계 원칙
- 기본 1.0 배율 = 현실 시간 (1게임 시간 = 1게임 시간)
- 디버그에서 배율 조절 가능 (예: 7.0 = 1주일 → 1일)
- 배율은 임신/월경 주기에만 적용 (일반 게임 시간은 불변)

### 상수
```python
PREGNANCY_TIME_SCALE = 1.0       # 기본 배율 (디버그에서 수정 가능)
MILLIS_PER_GAME_DAY = 24 * 60 * 60_000  # 86,400,000ms
```

### 디버그 API
```python
def set_time_scale(scale: float):
    """임신/월경 시간 배율 설정 (디버그 전용)"""
    global PREGNANCY_TIME_SCALE
    PREGNANCY_TIME_SCALE = max(0.1, scale)

def get_time_scale() -> float:
    return PREGNANCY_TIME_SCALE
```

### 시간 환산
```python
def scaled_days(real_days: int) -> int:
    """실제 일수 → 스케일 적용된 일수"""
    return max(1, round(real_days / PREGNANCY_TIME_SCALE))
```

---

## 2. 월경 주기 (Menstrual Cycle)

### 대상
- `has_anatomy(unit_id, "V")` = True인 캐릭터 (female, futanari)
- 플레이어 포함 (성별 선택에 따라)

### 주기 구조 (28일 기본)

```
Day 1-5:    월경기 (Menstrual)       — 가임 불가
Day 6-10:   여포기 (Follicular)      — 가임 불가
Day 11-17:  배란기 (Ovulation)       — 가임 가능 ★
Day 18-28:  황체기 (Luteal)          — 가임 불가
```

### 가임 확률

| 주기 단계 | 기본 수정 확률 |
|-----------|--------------|
| 월경기 | 0% |
| 여포기 | 0% |
| 배란기 (Day 11-13) | 15% |
| 배란일 (Day 14) | 30% |
| 배란기 (Day 15-17) | 15% |
| 황체기 | 0% |

### Prop 설계

```python
"생식:주기일"    # 현재 주기 일수 (1-28), 매일 +1, 28 도달 시 1로 리셋
"생식:주기길이"  # 개인별 주기 길이 (기본 28, 범위 25-35)
```

### 초기화

NPC 생성 시 랜덤 주기일 배정 (동기화 방지):
```python
def register_character(unit_id):
    """임신 시스템에 캐릭터 등록"""
    import gender as gender_mod
    if not gender_mod.has_anatomy(unit_id, "V"):
        return  # V 없으면 등록 불필요

    _registry.add(unit_id)

    # 이미 주기일이 있으면 스킵 (챕터 전환 복원)
    if morld.get_unit_prop(unit_id, "생식:주기일") is not None:
        return

    import random
    cycle_len = random.randint(25, 35)
    morld.set_unit_prop(unit_id, "생식:주기길이", cycle_len)
    morld.set_unit_prop(unit_id, "생식:주기일", random.randint(1, cycle_len))
```

### 매일 업데이트

needs.py의 `_process_hourly()` 패턴과 유사하게,
pregnancy.py에서 `subscribe_time_elapsed`로 매시간 호출 → 자정(hour=0)에 하루치 처리:

```python
def _on_time_elapsed(millis):
    hour = morld.get_time_info().get("hour", -1)
    if hour != 0:
        return  # 자정에만 처리
    for unit_id in _registry:
        _daily_update(unit_id)

def _daily_update(unit_id):
    # 임신 중이면 주기 정지
    if morld.get_unit_prop(unit_id, "상태:임신"):
        _pregnancy_daily(unit_id)
        return

    # 주기일 진행
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일") or 1
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이") or 28

    cycle_day += 1
    if cycle_day > cycle_len:
        cycle_day = 1
    morld.set_unit_prop(unit_id, "생식:주기일", cycle_day)
```

### 월경 상태 표현 (Describe / Focus)

월경 중인 캐릭터는 포커스/묘사 규칙에서 아키타입별 텍스트가 표시된다.

**구현 파일:** `assets/base.py` — `_build_context()` + `_DESCRIBE_MENSTRUATION` / `_FOCUS_MENSTRUATION`

- `_build_context()`에서 `pregnancy.is_menstruating()` / `is_ovulating()` 호출 → `context["월경"]`, `context["배란"]`
- 10 아키타입별 describe/focus 텍스트 (1개씩)
- `_DEFAULT_DESCRIBE_ORDER` / `_DEFAULT_FOCUS_ORDER`에서 `"menstruation"`은 `"default"` 바로 앞 (낮은 우선순위)

### 월경 중 삽입 거부 시스템

월경 중(`주기일 1-5`)에 `vaginal_insert` 시도 시 NPC가 거부한다.
단, 반복 시도(동적 임계치)를 통해 강제 삽입 가능. 성격/욕망/흥분도에 따라 거부 강도 변동.

**구현 파일:** `romance.py` — `_check_insertion_hard_fail()`, `_get_menstruation_threshold()`

#### 동적 임계치

```python
def _get_menstruation_threshold(partner_id, mode, state):
    # 의식없음/시간정지: 항상 0 (즉시 삽입)
    # base: 합의 3 / 강제 1
    # 아키타입 보정: seductive/devoted -1, fierce/cold +1
    # 욕망 ≥ 60: -1
    # 성욕 ≥ 50 + V자극 ≥ 40: -1
    # 최솟값: 0
```

| 시나리오 | 계산 | 임계치 | 결과 |
|----------|------|--------|------|
| 기본 합의 | 3 | 3 | 3회 거부 후 삽입 |
| 기본 강제 | 1 | 1 | 1회 거부 후 삽입 |
| seductive + 높은 욕망 + 높은 자극 | 3-1-1-1=0 | 0 | 자발적 수용 |
| fierce + 낮은 욕망 | 3+1=4 | 4 | 4회 거부 필요 |
| 의식없음/시간정지 | — | 0 | 즉시 삽입 |

#### 임계치별 분기

- **threshold = 0 (자발적 수용)**: NPC가 월경 중임에도 괘념치 않음. 아키타입별 수용 대사 출력.
- **0 < failed < threshold (거부)**: 시도 횟수별 아키타입 거부 대사 (최대 3-4단계).
- **failed ≥ threshold (강제 삽입)**: 삽입 성공 + 아키타입별 reluctant 반응. 합의 모드 시 반발 +5.

#### UI 표시

- 로맨스 헤더: `[color=yellow]월경 중[/color]` (임신 아닌 경우)
- `vaginal_insert` 버튼: `[color=yellow]삽입 (월경 중{잔여횟수})[/color]` (threshold > 0일 때)
- threshold = 0: 정상 색상으로 표시 (자발적 수용)

#### NPC 자율 삽입 차단

- `romance.py`: `_check_npc_autonomous_action()` — 월경 중 vaginal 자율 삽입 차단
- `npc_initiative.py`: NPC 주도 삽입 시 `orifice = None` (질 → 건너뜀)

#### 헬퍼 함수 (pregnancy.py)

```python
def is_menstruating(unit_id):
    """월경 중 여부 (주기일 1-5). 임신 중이면 False."""

def is_ovulating(unit_id):
    """배란기 여부. 임신 중이면 False."""
```

---

## 3. 수정 판정 (Conception)

### 트리거

**P를 가진 쪽이 절정할 때만 수정 판정 발생.**

삽입 행위(`pregnancy_check: True`)가 활성 상태에서 P 보유자가 절정 도달 시 호출:

```python
def check_conception(player_id, partner_id):
    """P 보유자 절정 시 호출 — 수정 가능 여부 판정

    romance.py / npc_initiative.py의 절정 처리 블록에서 호출.
    삽입 행위(pregnancy_check=True)가 활성 토글일 때 + P 보유자 절정 시에만.
    """
    # P를 가진 쪽이 inseminator, V를 가진 쪽이 receiver
    import gender as gender_mod

    if gender_mod.has_anatomy(player_id, "P") and gender_mod.has_anatomy(partner_id, "V"):
        _try_conceive(partner_id, player_id)  # NPC가 receiver

    if gender_mod.has_anatomy(partner_id, "P") and gender_mod.has_anatomy(player_id, "V"):
        _try_conceive(player_id, partner_id)  # 플레이어가 receiver
```

**매 틱이 아닌 절정 시 1회 판정인 이유:**
- 현실적 (사정 = 수정 기회)
- 밸런스 (매 틱 판정 시 확률 과다 누적)
- 긴장감 (절정 순간에 임신 여부 결정)

### 수정 로직

```python
def _try_conceive(receiver_id, inseminator_id):
    """수정 시도"""
    # 이미 임신 중이면 스킵
    if morld.get_unit_prop(receiver_id, "상태:임신"):
        return

    # 가임 확률 계산
    chance = _get_fertility_chance(receiver_id)
    if chance <= 0:
        return

    # 확률 판정
    import random
    if random.random() < chance:
        _conceive(receiver_id, inseminator_id)

def _get_fertility_chance(unit_id):
    """현재 주기 기반 가임 확률"""
    cycle_day = morld.get_unit_prop(unit_id, "생식:주기일") or 1
    cycle_len = morld.get_unit_prop(unit_id, "생식:주기길이") or 28

    # 배란일 = 주기 중간점
    ovulation_day = cycle_len // 2

    # 배란기: 배란일 ±3일
    diff = abs(cycle_day - ovulation_day)
    if diff == 0:
        return 0.30   # 배란일
    elif diff <= 3:
        return 0.15   # 배란기
    else:
        return 0.0    # 비가임기
```

### 수정 성공 처리

```python
def _conceive(receiver_id, inseminator_id):
    """수정 성공 — 임신 시작"""
    morld.set_unit_prop(receiver_id, "상태:임신", 1)
    morld.set_unit_prop(receiver_id, "상태:임신주차", 0)

    time_info = morld.get_time_info()
    conception_day = time_info.get("day", 0)
    morld.set_unit_prop(receiver_id, "상태:수정일", conception_day)

    # 아버지 기록
    insem_info = morld.get_unit_info(inseminator_id)
    insem_name = insem_info.get("name", "???") if insem_info else "???"
    morld.set_unit_prop(receiver_id, "상태:아이아버지", insem_name)
    morld.set_unit_prop(receiver_id, "상태:아이아버지id", inseminator_id)
```

---

## 4. 임신 기간 (Gestation)

### 기간: 40주 (280일)

스케일 적용: `실제 소요 = 280 / PREGNANCY_TIME_SCALE` 일

### 임신 3분기 (Trimester)

| 분기 | 주차 | 증상 | NPC 행동 영향 |
|------|------|------|--------------|
| 1분기 | 0-12 | 입덧 (식사 실패 확률 20%) | 식사 인터럽트 변형 |
| 2분기 | 13-27 | 안정기 (특별한 증상 없음) | 영향 없음 |
| 3분기 | 28-39 | 피로 증가 (+2/h), 이동 속도 감소 | 피로 인터럽트 조기 발동 |
| 만삭 | 40+ | 출산 | 출산 인터럽트 |

### 주간 업데이트

매일 업데이트에서 7일마다 주차 증가:

```python
def _pregnancy_daily(unit_id):
    """임신 중 매일 업데이트"""
    conception_day = morld.get_unit_prop(unit_id, "상태:수정일") or 0
    current_day = morld.get_time_info().get("day", 0)

    elapsed_days = current_day - conception_day
    scaled_days = round(elapsed_days * PREGNANCY_TIME_SCALE)
    week = scaled_days // 7

    morld.set_unit_prop(unit_id, "상태:임신주차", min(week, 42))
```

### 임신 증상 효과

```python
PREGNANCY_EFFECTS = {
    # 1분기 (0-12주)
    "trimester_1": {
        "morning_sickness_chance": 0.2,   # 식사 시 구토 확률 20%
        "fatigue_bonus": 0,               # 추가 피로 없음
        "speed_modifier": 1.0,            # 이동 속도 변화 없음
    },
    # 2분기 (13-27주)
    "trimester_2": {
        "morning_sickness_chance": 0.0,
        "fatigue_bonus": 0,
        "speed_modifier": 1.0,
    },
    # 3분기 (28-39주)
    "trimester_3": {
        "morning_sickness_chance": 0.0,
        "fatigue_bonus": 2,               # 피로 +2/h 추가
        "speed_modifier": 0.7,            # 이동 속도 30% 감소
    },
}

def get_trimester(unit_id):
    """현재 임신 분기 반환"""
    week = morld.get_unit_prop(unit_id, "상태:임신주차") or 0
    if week <= 12:
        return "trimester_1"
    elif week <= 27:
        return "trimester_2"
    else:
        return "trimester_3"
```

### 연애 행위 제한

| 주차 | 제한 |
|------|------|
| 0-27주 | 제한 없음 (기존 행위 모두 가능) |
| 28-39주 | 삽입 행위 비활성화 |
| 40주+ | 연애 행위 전체 비활성화 (출산 대기) |

### UI 표시

임신 중 NPC 포커스 시 상태 표시:
```
[임신 12주차] 입덧 증상
[임신 28주차] 만삭에 가까워지고 있다
[임신 40주차] 출산이 임박했다
```

---

## 5. 출산 (Childbirth)

### 트리거

Think 5-tier 우선순위에서 Tier 4 (Comfort) 내에 삽입:
```
Tier 4: 배변 → 피로 → 성욕 → 목욕 → 출산 → 수면
```

조건: `상태:임신주차 >= 40`

### 출산 핸들러 (think/activities/childbirth.py)

4-phase 구조 (기존 패턴 동일):

```python
def handle_childbirth(agent, entry):
    phase = agent._memory.get("childbirth_phase", "idle")

    if phase == "idle":
        # 출산 장소 결정 (침실 우선)
        target = _find_bed_location(agent) or _find_safe_location(agent)
        agent._memory["childbirth_target"] = target
        agent._memory["childbirth_phase"] = "going"
        # 이동 job 삽입

    elif phase == "going":
        if agent._is_at_location(target):
            agent._memory["childbirth_phase"] = "laboring"
            agent._insert_idle_job("출산", 8 * 60 * 60_000)  # 8시간

    elif phase == "laboring":
        # 출산 완료 → 아이 생성
        child_id = _spawn_child(agent)
        agent._memory["childbirth_child_id"] = child_id
        agent._memory["childbirth_phase"] = "recovery"
        agent._insert_idle_job("산후조리", 24 * 60 * 60_000)  # 24시간 회복

    elif phase == "recovery":
        # 회복 완료 → 상태 초기화
        _reset_pregnancy(agent.unit_id)
        agent._memory["childbirth_phase"] = None
```

### 출산 결과

```python
def _reset_pregnancy(unit_id):
    """출산 후 임신 상태 초기화"""
    morld.set_unit_prop(unit_id, "상태:임신", 0)
    morld.set_unit_prop(unit_id, "상태:임신주차", 0)
    morld.set_unit_prop(unit_id, "상태:수정일", None)
    # 월경 주기 재시작
    morld.set_unit_prop(unit_id, "생식:주기일", 1)
```

---

## 6. 아이 NPC (Child)

### 생성

```python
def _spawn_child(mother_agent):
    """출산 시 아이 NPC 동적 생성"""
    mother_id = mother_agent.unit_id
    mother_info = morld.get_unit_info(mother_id)
    father_name = morld.get_unit_prop(mother_id, "상태:아이아버지") or "???"

    # 1. Asset 생성
    from assets.characters.child import Child
    child = Child()
    child_id = morld.create_id("unit")

    # 2. 아이 속성 결정 (간단 PCG)
    child.name = _generate_child_name()
    child.props["나이"] = 0
    child.props["부모:어머니"] = mother_info.get("name", "???")
    child.props["부모:아버지"] = father_name
    child.type = _determine_child_gender()

    # 3. 어머니 위치에 배치
    # bed_owner:{mother} prop으로 어머니 침대 위치 탐색
    loc = _find_bed_location(mother_agent)
    child.instantiate(child_id, loc["region_id"], loc["location_id"])

    # 4. Agent 등록
    from think import register_agent
    from think.agents.child_agent import ChildAgent
    agent = ChildAgent(child_id)
    register_agent(child_id, agent)
    needs.register_character(child_id)

    return child_id
```

### Child Asset 클래스

```python
# assets/characters/child.py

class Child(Character):
    unique_id = "child"     # 동적 생성이므로 고유값 필요 없음
    name = "아이"
    type = "male"           # 출산 시 랜덤 결정

    props = {
        "나이": 0,
        "생존:체력": 50,
        "생존:최대체력": 50,
        "생존:포만감": 100,
        "부모:어머니": "",
        "부모:아버지": "",
    }
```

### ChildAgent 클래스

최소 욕구 행동 (먹고/씻고/자고):

```python
# think/agents/child_agent.py

class ChildAgent(BaseAgent):
    """아이 NPC — 최소 욕구 행동만"""

    # 기본 스케줄 (부모 근처에서 생활)
    DEFAULT_SCHEDULE = [
        {"start": "06:00", "activity": "기상", "location": None},
        {"start": "07:00", "activity": "식사", "location": None},
        {"start": "12:00", "activity": "식사", "location": None},
        {"start": "18:00", "activity": "식사", "location": None},
        {"start": "20:00", "activity": "수면", "location": None},
    ]

    def think(self):
        # Tier 1: 기절 체크
        # Tier 3: 배고픔 체크
        # Tier 4: 배변 → 피로 → 수면
        # Tier 5: 스케줄 (위 DEFAULT_SCHEDULE)
        pass
```

### 수면 위치

- 출산 직후: 어머니의 침대(`bed_owner:{mother}` prop)에서 함께 수면 (어머니 침대에 `bed_owner:{child}` prop 자동 추가)
- 이후: 아이 침대(craftable) 배치 시 별도 위치

---

## 7. 간단 PCG (Procedural Child Generation)

### 이름 생성

```python
# 이름 후보 풀 (성별별)
CHILD_NAMES_MALE = ["카이", "레오", "유진", "하루", "소라"]
CHILD_NAMES_FEMALE = ["하나", "미유", "유리", "사쿠라", "린"]

def _generate_child_name():
    import random
    names = CHILD_NAMES_MALE + CHILD_NAMES_FEMALE
    return random.choice(names)
```

### 성별 결정

```python
def _determine_child_gender():
    import random
    return "female" if random.random() < 0.5 else "male"
```

### 외모 상속 (향후 확장)

현재 단순 구현. 향후 부모 외모 prop 기반 상속 가능:
```python
# 향후:
# child.props["외모:머리색"] = random.choice([mother_hair, father_hair])
# child.props["외모:눈색"] = random.choice([mother_eyes, father_eyes])
```

---

## 8. Prop 설계 총정리

### 생식 관련 Prop

| Prop | 타입 | 범위 | 설명 |
|------|------|------|------|
| `생식:주기일` | int | 1-35 | 현재 월경 주기 일수 |
| `생식:주기길이` | int | 25-35 | 개인별 주기 길이 |

### 임신 관련 Prop

| Prop | 타입 | 범위 | 설명 |
|------|------|------|------|
| `상태:임신` | int | 0/1 | 임신 여부 |
| `상태:임신주차` | int | 0-42 | 현재 임신 주차 |
| `상태:수정일` | int | - | 수정된 게임 일수 |
| `상태:아이아버지` | str | - | 아버지 이름 |
| `상태:아이아버지id` | int | - | 아버지 unit_id |

### 아이 관련 Prop

| Prop | 타입 | 범위 | 설명 |
|------|------|------|------|
| `부모:어머니` | str | - | 어머니 이름 |
| `부모:아버지` | str | - | 아버지 이름 |
| `나이` | int | 0+ | 나이 (→ 나이 시스템 참조) |

---

## 9. 시스템 연동

### needs.py 연동

```python
# _process_hourly() 내 추가:
# 임신 3분기 → 피로 추가 증가
import pregnancy
trimester = pregnancy.get_trimester(unit_id)
if trimester == "trimester_3":
    fatigue_bonus = PREGNANCY_EFFECTS["trimester_3"]["fatigue_bonus"]
    current_fatigue = morld.get_unit_prop(unit_id, PROP_FATIGUE) or 0
    morld.set_unit_prop(unit_id, PROP_FATIGUE, min(100, current_fatigue + fatigue_bonus))
```

### romance.py / npc_initiative.py 연동

**절정 처리 블록** 내에서 호출 (매 틱이 아님):
```python
# 절정 발생 시 (climax_info가 반환된 경우):
if climax_info:
    # pregnancy_check 활성 삽입 행위가 진행 중인지 확인
    active_intercourse = [
        tid for tid in state["active_toggles"]
        if TOGGLE_ACTIONS.get(tid, {}).get("pregnancy_check")
    ]
    if active_intercourse:
        # P 보유자가 절정했는지 확인
        import gender as gender_mod
        climaxing_id = partner_id  # NPC가 절정한 경우
        if gender_mod.has_anatomy(climaxing_id, "P"):
            import pregnancy
            pregnancy.check_conception(player_id, partner_id)
```

### think 인터럽트 연동

```python
# BaseAgent.think() — Tier 4에 추가:
def _check_childbirth(self):
    """출산 인터럽트 체크"""
    week = morld.get_unit_prop(self.unit_id, "상태:임신주차") or 0
    if week >= 40:
        return True
    if self._memory.get("childbirth_phase"):
        return True  # 진행 중인 출산
    return False
```

### 챕터 전환 연동

```python
# chapters/__init__.py load_chapter() 내:
import pregnancy
pregnancy.reset()  # 레지스트리 초기화 (NPC 재등록 필요)

# pregnancy prop은 unit prop이므로 챕터 전환 시 자동 보존
```

### 이벤트 구독

```python
# pregnancy.py 모듈 초기화:
from events import subscribe_time_elapsed
subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)  # 1시간
```

---

## 10. UI 표시

### NPC 포커스 시 임신 상태

FOCUS_RULES 또는 footer에 임신 상태 표시:

```python
def get_pregnancy_status_text(unit_id):
    if not morld.get_unit_prop(unit_id, "상태:임신"):
        return None

    week = morld.get_unit_prop(unit_id, "상태:임신주차") or 0
    trimester = get_trimester(unit_id)

    if week >= 40:
        return "[color=red]출산이 임박했다[/color]"
    elif trimester == "trimester_3":
        return f"[color=yellow]임신 {week}주차 — 만삭에 가까워지고 있다[/color]"
    elif trimester == "trimester_1":
        return f"임신 {week}주차 — 입덧 증상"
    else:
        return f"임신 {week}주차"
```

### 연애 UI 행위 제한 표시

임신 후기(28주+) 삽입 불가:
```
[color=gray]삽입 (임신 후기)[/color]
```

---

## 11. 밸런스 정리

### 핵심 수치

| 항목 | 값 | 비고 |
|------|---|------|
| 월경 주기 | 25-35일 (기본 28) | 캐릭터별 랜덤 |
| 배란기 | 주기 중간 ±3일 | 7일간 가임 |
| 배란일 수정률 | 30% /틱 | 최대 확률 |
| 배란기 수정률 | 15% /틱 | 중간 확률 |
| 임신 기간 | 40주 (280일) | 스케일 적용 |
| 출산 소요 | 8시간 (게임 시간) | 고정 |
| 산후 회복 | 24시간 (게임 시간) | 고정 |

### 타임라인 예시 (배율 1.0)

```
Day 0:     수정
Week 0-12: 1분기 (입덧)
Week 13-27: 2분기 (안정기)
Week 28-39: 3분기 (피로 증가, 삽입 불가)
Week 40:    출산 인터럽트 → 8시간 출산 → 24시간 회복
Week 41:    아이 NPC 등장, 어머니 복귀
```

### 타임라인 예시 (배율 7.0, 디버그)

```
Day 0:     수정
Day 6-12:  1분기 (입덧)
Day 13-27: 2분기
Day 28-40: 3분기
Day 40:    출산
```

---

## 12. 디버그 기능

| 기능 | 설명 |
|------|------|
| `pregnancy.set_time_scale(scale)` | 시간 배율 변경 |
| `pregnancy.force_conceive(unit_id, father_id)` | 강제 임신 |
| `pregnancy.set_week(unit_id, week)` | 임신 주차 직접 설정 |
| `pregnancy.force_birth(unit_id)` | 즉시 출산 |
| `pregnancy.get_cycle_info(unit_id)` | 월경 주기 정보 출력 |

포커스 메뉴에 디버그 액션 추가:
```python
actions = [
    "call:debug_pregnancy_info:임신 정보",
    "call:debug_force_conceive:강제 임신",
    "call:debug_force_birth:강제 출산",
]
```

---

## 13. 출산 후 모성 행동 (Post-Birth Maternal Behavior)

### 개요

출산 후 어머니 NPC는 아이 NPC에 대한 **모성 욕구**를 가짐.
아이의 위치를 추적하고, 주기적으로 아이를 찾아가 대화/돌봄 행위를 수행.
NPC-NPC 대화 시스템의 첫 응용 사례.

### 모성 욕구 (Prop)

```python
"욕구:모성"   # 0-100, 출산 직후 0에서 시작, 시간 경과에 따라 증가
```

- 증가율: +3/h (아이와 떨어져 있을 때)
- 감소: 아이와 대화 시 -30
- 임계치: 60 이상이면 아이 탐색 인터럽트 발동

### Think 인터럽트 위치

Tier 4 (Comfort) 내, 수면 앞에 삽입:
```
Tier 4: 배변 → 피로 → 성욕 → 목욕 → 출산 → 모성(아이 탐색) → 수면
```

### 아이 위치 추적

```python
def _find_child_location(mother_id):
    """어머니의 아이 NPC 위치 반환"""
    # mother의 마지막 출산 아이 ID를 추적
    child_id = mother._memory.get("last_child_id")
    if not child_id:
        return None
    child_loc = morld.get_unit_location(child_id)
    if child_loc:
        return {"region_id": child_loc[0], "location_id": child_loc[1]}
    return None
```

### 모성 핸들러 (handle_maternal)

3-phase 구조:

```python
def handle_maternal(agent, entry):
    phase = agent._memory.get("maternal_phase", "idle")

    if phase == "idle":
        child_loc = _find_child_location(agent)
        if not child_loc:
            agent._memory["maternal_phase"] = None
            return
        agent._memory["maternal_target"] = child_loc
        agent._memory["maternal_phase"] = "going"
        # 이동 job 삽입

    elif phase == "going":
        if agent._is_at_location(target):
            agent._memory["maternal_phase"] = "interacting"
            agent._insert_idle_job("육아", 30 * 60_000)  # 30분 대화/돌봄

    elif phase == "interacting":
        # 대화 완료 → 모성 욕구 감소
        morld.modify_prop(agent.unit_id, "욕구:모성", -30)
        agent._memory["maternal_phase"] = None
```

### NPC-NPC 대화 연동

모성 핸들러의 "interacting" phase에서 NPC-NPC 대화 시스템 활용:
- 어머니 → 아이 방향 대화 (아이가 반응 텍스트 생성)
- describe 텍스트: `"{어머니이름}(이)가 {아이이름}와 이야기하고 있다."`
- 주변 NPC/플레이어에게 location describe로 표시

```python
# 대화 describe 텍스트 (location에 있는 다른 유닛이 볼 수 있는 묘사)
def get_maternal_describe(mother_name, child_name):
    return f"{mother_name}(이)가 {child_name}에게 다정하게 말을 걸고 있다."
```

### 어머니 기억

```python
# agent._memory 추가 키:
"last_child_id": int        # 마지막 출산 아이 unit_id
"maternal_phase": str       # None/idle/going/interacting
"maternal_target": dict     # 아이 위치
```

### needs.py 연동

```python
# _process_hourly() 내 추가:
# 모성 욕구 증가 (아이가 있는 경우)
child_id = ...  # 어머니의 아이 ID
if child_id:
    mother_loc = morld.get_unit_location(unit_id)
    child_loc = morld.get_unit_location(child_id)
    if mother_loc != child_loc:
        # 떨어져 있으면 모성 욕구 증가
        current = morld.get_unit_prop(unit_id, "욕구:모성") or 0
        morld.set_unit_prop(unit_id, "욕구:모성", min(100, current + 3))
    else:
        # 같은 위치면 느리게 증가
        current = morld.get_unit_prop(unit_id, "욕구:모성") or 0
        morld.set_unit_prop(unit_id, "욕구:모성", min(100, current + 1))
```

---

## 14. 구현 순서

| 단계 | 내용 | 파일 |
|------|------|------|
| 1 | pregnancy.py 모듈 생성 (월경 주기 + 수정 판정) | pregnancy.py |
| 2 | 삽입 행위 추가 (romance.py, npc_initiative.py) | romance.py, npc_initiative.py |
| 3 | 절정 시 수정 판정 연동 | romance.py, npc_initiative.py |
| 4 | 임신 기간 관리 (주간 업데이트, 증상) | pregnancy.py, needs.py |
| 5 | 출산 핸들러 (think 인터럽트) | think/activities/childbirth.py |
| 6 | 아이 NPC 생성 (Child Asset + ChildAgent) | assets/characters/child.py |
| 7 | 모성 행동 (아이 탐색 + NPC-NPC 대화 기초) | think/activities/, needs.py |
| 8 | UI 표시 (임신 상태, 행위 제한) | romance.py, player.py |
| 9 | 디버그 기능 | pregnancy.py, base.py |
| 10 | 챕터 전환 연동 | chapters/__init__.py |

---

## 14. 미구현/향후 확장

| 기능 | 설명 | 상태 |
|------|------|------|
| 쌍둥이/다태 | 다태 임신 확률 + 복수 아이 생성 | 미구현 |
| 유산 | 외부 충격/영양실조에 의한 유산 | 미구현 |
| 피임 | 피임약/피임구 아이템 | 미구현 |
| 아이 성장 | 나이에 따른 아이 모델/행동 변화 | 미구현 (나이 시스템 참조) |
| 아이 침대 | 크래프팅 가능한 아이 침대 | 미구현 |
| 부모-자녀 관계 | 부모-자녀 간 호감도/이벤트 | 미구현 |
| NPC 간 임신 | NPC-NPC 행위에서 임신 판정 | 미구현 (NPC-NPC 행위 시스템 선행) |
