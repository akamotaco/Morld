# 연애 시스템 (Romance System)

## 개요

플레이어와 호감도가 높은 NPC 간의 친밀한 상호작용 시스템.
**핵심 특징**: 행위 중 시간이 흐르고, 다른 NPC의 도착에 따라 중단/합류 이벤트 발생.

---

## 핵심 요구사항

### 1. 진입 조건
- 호감도 임계값 이상인 NPC와 같은 Location에 있어야 함
- 해당 Location에 호감도가 낮은 NPC가 없어야 함
- 1:1 또는 호감도 높은 NPC 2명까지 허용

### 2. 시간 흐름 & NPC 감지 (최우선 구현)
```
┌─────────────────────────────────────────────────────────────────┐
│ 연애 행위 진행 중                                                 │
│                                                                 │
│  [행위 선택] → [시간 경과] → [NPC 도착 체크] → [결과 처리]         │
│                    ↓              ↓                             │
│               게임 시간 진행   JobBehaviorSystem이                │
│               (예: 15분)      NPC를 이동시킴                      │
│                                   ↓                             │
│                          같은 Location 도착?                      │
│                           ↓           ↓                         │
│                         Yes          No                         │
│                          ↓            ↓                         │
│                    호감도 체크      행위 계속                      │
│                     ↓      ↓                                    │
│                   높음   낮음                                     │
│                    ↓      ↓                                     │
│                  합류   중단 이벤트                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3. 중단 이벤트 예시
```
플레이어 + 세라 (호감도 80) 거실에서 연애 행위 중
  ↓
15분 경과, 리나(호감도 30)가 거실에 도착
  ↓
중단 이벤트 발생:
  - 연애 UI 즉시 종료
  - 다이얼로그: "리나: 어머나! 이게 무슨 꼴이람!"
  - 세라: mood에 "부끄러움" 추가, 30분간 "도망" Job 설정
  - 리나: 호감도 -5 (목격 페널티)
  ↓
일반 UI(situation)로 복귀
```

---

## 시스템 설계

### 방안 A: Dialog + 시간 진행 콜백 (권장)

기존 Dialog 시스템을 확장하여 연애 모드 구현.

```python
# romance.py

# 상수 정의
ROMANCE_ENTRY_THRESHOLD = 50   # 연애 진입 최소 호감도
ROMANCE_JOIN_THRESHOLD = 60    # 합류 가능 최소 호감도
ROMANCE_STAMINA_KEY = "연애:스태미나"  # 생존:체력과 분리
DEFAULT_STAMINA = 10

def start_romance(player_id, partner_id):
    """연애 모드 시작 - Generator 기반"""

    # 플레이어 스태미나 조회 (연애 전용)
    player_props = morld.get_unit_props(player_id)
    initial_stamina = player_props.get(ROMANCE_STAMINA_KEY, DEFAULT_STAMINA)

    state = {
        "partner_id": partner_id,
        "active_toggles": set(),  # 현재 ON인 토글들 (복수 가능)
        "stamina": initial_stamina,  # 남은 체력
        "elapsed_time": 0,
        "interrupted": False,
        "interrupter_id": None,
        "exhausted": False,  # 체력 소진 종료
    }

    def apply_effects(action_def, active_toggle_defs):
        """행위 효과 적용 (즉시형 + 활성 토글들)"""
        partner_id = state["partner_id"]

        # 즉시형/토글 행위의 효과 (경험치 보정 포함)
        effects = calculate_effects(action_def, partner_id)

        # 활성 토글들의 효과도 합산
        for toggle_def in active_toggle_defs:
            toggle_effects = calculate_effects(toggle_def, partner_id)
            for stat, value in toggle_effects.items():
                effects[stat] = effects.get(stat, 0) + value

        # 효과 적용
        for stat, value in effects.items():
            morld.modify_prop(partner_id, stat, value)

    def proc(action):
        if action == "init":
            return render_romance_ui(state)

        # 종료
        if action == "exit":
            return True

        # 즉시형 행위
        if action.startswith("instant:"):
            action_id = action.split(":")[1]
            action_def = INSTANT_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 체력 계산: 즉시형 + 활성 토글들
            total_stamina = action_def["stamina"]
            total_time = action_def["time"]

            active_toggle_defs = []
            for toggle_id in state["active_toggles"]:
                toggle_def = TOGGLE_ACTIONS[toggle_id]
                total_stamina += toggle_def["stamina"]
                active_toggle_defs.append(toggle_def)

            # 체력 부족 체크
            if state["stamina"] < total_stamina:
                state["exhausted"] = True
                return True  # 체력 부족 종료

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            apply_effects(action_def, active_toggle_defs)

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 체력 0이면 종료
            if state["stamina"] <= 0:
                state["exhausted"] = True
                return True

            return render_romance_ui(state)

        # 토글형 행위
        if action.startswith("toggle:"):
            action_id = action.split(":")[1]
            action_def = TOGGLE_ACTIONS.get(action_id)
            if not action_def:
                return None

            # 토글 전환
            is_turning_on = action_id not in state["active_toggles"]

            # 체력 계산 (토글 ON/OFF 모두 시간 흐름)
            total_stamina = action_def["stamina"]
            total_time = action_def["time"]

            # 다른 활성 토글들도 체력 소모
            active_toggle_defs = []
            for toggle_id in state["active_toggles"]:
                if toggle_id != action_id:
                    toggle_def = TOGGLE_ACTIONS[toggle_id]
                    total_stamina += toggle_def["stamina"]
                    active_toggle_defs.append(toggle_def)

            # 체력 부족 체크
            if state["stamina"] < total_stamina:
                state["exhausted"] = True
                return True

            # 토글 상태 변경
            if is_turning_on:
                state["active_toggles"].add(action_id)
            else:
                state["active_toggles"].discard(action_id)

            # 효과 적용 (경험치 시스템 포함)
            state["stamina"] -= total_stamina
            apply_effects(action_def, active_toggle_defs)

            # 시간 경과 + NPC 도착 체크
            result = advance_time_and_check(state, total_time)
            if result["interrupted"]:
                state["interrupted"] = True
                state["interrupter_id"] = result["interrupter_id"]
                return True

            # 체력 0이면 종료
            if state["stamina"] <= 0:
                state["exhausted"] = True
                return True

            return render_romance_ui(state)

        return None

    # 연애 UI 시작
    yield morld.dialog(
        render_romance_ui(state),
        autofill="off",
        proc=proc,
        result=state
    )

    # 종료 처리
    if state["exhausted"]:
        yield morld.dialog("지쳤다...")
    elif state["interrupted"]:
        yield from handle_interruption(state)

def advance_time_and_check(state, minutes):
    """시간 경과 + NPC 도착 체크"""
    # 1. 시간 진행 + NPC 이동 시뮬레이션 (morld API 호출)
    morld.advance_time_simulate(minutes)
    state["elapsed_time"] += minutes

    # 2. 현재 Location의 NPC 목록 확인
    player_loc = morld.get_unit_location(morld.get_player_id())
    units_at_loc = morld.get_units_at_location(player_loc[0], player_loc[1])

    # 3. 새로 도착한 NPC 중 호감도 낮은 NPC 확인
    for unit_id in units_at_loc:
        if unit_id == state["partner_id"]:
            continue
        if unit_id == morld.get_player_id():
            continue

        # 호감도 체크
        props = morld.get_unit_props(unit_id)
        affection = props.get("호감", 0)
        if affection < ROMANCE_JOIN_THRESHOLD:
            return {"interrupted": True, "interrupter_id": unit_id}

    return {"interrupted": False}

def handle_interruption(state):
    """중단 이벤트 처리"""
    interrupter_id = state["interrupter_id"]
    partner_id = state["partner_id"]

    # 목격자 반응 다이얼로그
    interrupter_name = morld.get_unit_info(interrupter_id)["name"]
    yield morld.dialog([
        f"[{interrupter_name}]",
        "어머나! 이게 무슨 꼴이람!"
    ])

    # 파트너 반응 (부끄러움 → 도망)
    partner_name = morld.get_unit_info(partner_id)["name"]
    yield morld.dialog([
        f"[{partner_name}]",
        "...!"
    ])

    # 파트너 상태 변경
    morld.add_unit_mood(partner_id, "부끄러움")
    morld.set_npc_job(partner_id, "flee", 30, morld.get_player_id())

    # 목격자 호감도 감소
    morld.modify_prop(interrupter_id, "호감", -5)
```

### 필요한 morld API 분석

| API | 상태 | 설명 |
|-----|------|------|
| `get_units_at_location(region_id, location_id)` | **새로 필요** | Location의 모든 유닛 ID 목록 반환 |
| `advance_time_simulate(minutes)` | **새로 필요** | 시간 진행 + NPC 이동 시뮬레이션 |
| `add_unit_mood(unit_id, mood)` | **새로 필요** | 기존 `set_unit_mood`는 덮어쓰기만 지원 |
| `modify_prop(unit_id, prop_name, delta)` | **새로 필요** | 상대값 변경 (예: 호감도 -5) |

```python
# 새로 추가할 API
morld.get_units_at_location(region_id, location_id)  # Location의 모든 유닛 ID 목록
morld.add_unit_mood(unit_id, mood)  # mood 추가 (기존 mood 유지)
morld.modify_prop(unit_id, prop_name, delta)  # prop 상대값 변경
morld.advance_time_simulate(minutes)  # 시간 진행 + NPC JobBehavior 실행
```

#### advance_time vs advance_time_simulate

| API | 동작 | 용도 |
|-----|------|------|
| `advance_time(minutes)` | 시간만 증가 | 일반 대화, 행동 |
| `advance_time_simulate(minutes)` | 시간 + NPC 이동 | 연애 모드 (NPC 도착 감지) |

`advance_time_simulate` 구현:
1. `GameTime.AddMinutes(minutes)`
2. `JobBehaviorSystem.Proc()` 직접 호출
3. `ThinkSystem`은 호출 안 함 (NPC AI 재계산 불필요)

---

## 행위 정의

### 자원 소모
- **시간**: 모든 행위에 시간 소모
- **체력**: 모든 행위에 체력 소모 (체력 0이면 연애 행위 강제 종료)

### 시간 흐름 규칙
| 행위 타입 | 시간 흐름 시점 |
|----------|---------------|
| 토글형 | 버튼 누를 때마다 (ON→OFF, OFF→ON 모두) |
| 즉시형 | 버튼 누르는 순간 |

### 효과 수치
행위마다 다음 3가지 수치에 영향:
- **호감**: 친밀감, 신뢰도 (장기적 관계)
- **애정**: 로맨틱한 감정 (연인 관계)
- **성적흥분**: 성적 자극 (즉각적, 시간 지나면 감소)

### 경험치 시스템
행위 반복 시 효과 증가 (곱연산):

| 경험 부위 | 관련 행위 | 효과 배율 |
|----------|----------|----------|
| 입술 | 프렌치 키스, 딥키스 | 1.0 + (경험:입술 × 0.1) |
| 귀 | 귀 만지기 | 1.0 + (경험:귀 × 0.1) |
| 가슴 | 가슴 만지기 | 1.0 + (경험:가슴 × 0.1) |
| 엉덩이 | 엉덩이 쓰다듬기 | 1.0 + (경험:엉덩이 × 0.1) |

**예시**: 입술 경험 5인 상태에서 프렌치 키스
- 기본 효과: 호감+1, 애정+2, 성적흥분+3
- 배율: 1.0 + (5 × 0.1) = 1.5
- 최종 효과: 호감+1, 애정+3, 성적흥분+4 (반올림)

경험치는 행위 실행 시 해당 부위에 +1 누적.

### 효과 중첩
- **토글형**: ON 상태에서 시간이 흐를 때 수치 상승
- **즉시형**: 버튼 누르는 순간 수치 상승
- **중첩**: 토글 ON 상태에서 즉시형 실행 시 합산
  - 예: 껴안기(ON) + 프렌치 키스 = 껴안기 효과 + 프렌치 키스 효과

### 즉시형 행위 (Instant Actions)
| 이름 | 시간 | 체력 | 호감 | 애정 | 성적흥분 | 경험 부위 | 필요 호감도 |
|------|-----|-----|-----|-----|---------|----------|------------|
| 머리 쓰다듬기 | 3분 | 1 | +2 | +1 | - | - | 40 |
| 뺨 어루만지기 | 2분 | 1 | +1 | +1 | - | - | 30 |
| 뺨 꼬집기 | 2분 | 1 | +1 | - | - | - | 35 |
| 귀 만지기 | 3분 | 1 | +1 | +1 | +1 | 귀 | 45 |
| 프렌치 키스 | 5분 | 2 | +1 | +2 | +3 | 입술 | 60 |
| 엉덩이 쓰다듬기 | 3분 | 2 | - | +1 | +3 | 엉덩이 | 70 |

### 토글형 행위 (Toggle Actions)
| 이름 | 틱당 시간 | 틱당 체력 | 호감 | 애정 | 성적흥분 | 경험 부위 | 필요 호감도 |
|------|----------|----------|-----|-----|---------|----------|------------|
| 껴안기 | 5분 | 1 | +1 | +2 | - | - | 50 |
| 딥키스 | 5분 | 2 | +1 | +2 | +3 | 입술 | 70 |
| 가슴 만지기 | 5분 | 2 | - | +1 | +4 | 가슴 | 80 |

### 행위 정의 (Python)
```python
INSTANT_ACTIONS = {
    "head_pat": {
        "name": "머리 쓰다듬기", "time": 3, "stamina": 1,
        "effects": {"호감": 2, "애정": 1},
        "exp_part": None, "affection_req": 40
    },
    "cheek_caress": {
        "name": "뺨 어루만지기", "time": 2, "stamina": 1,
        "effects": {"호감": 1, "애정": 1},
        "exp_part": None, "affection_req": 30
    },
    "cheek_pinch": {
        "name": "뺨 꼬집기", "time": 2, "stamina": 1,
        "effects": {"호감": 1},
        "exp_part": None, "affection_req": 35
    },
    "ear_touch": {
        "name": "귀 만지기", "time": 3, "stamina": 1,
        "effects": {"호감": 1, "애정": 1, "성적흥분": 1},
        "exp_part": "귀", "affection_req": 45
    },
    "french_kiss": {
        "name": "프렌치 키스", "time": 5, "stamina": 2,
        "effects": {"호감": 1, "애정": 2, "성적흥분": 3},
        "exp_part": "입술", "affection_req": 60
    },
    "butt_caress": {
        "name": "엉덩이 쓰다듬기", "time": 3, "stamina": 2,
        "effects": {"애정": 1, "성적흥분": 3},
        "exp_part": "엉덩이", "affection_req": 70
    },
}

TOGGLE_ACTIONS = {
    "hug": {
        "name": "껴안기", "time": 5, "stamina": 1,
        "effects": {"호감": 1, "애정": 2},
        "exp_part": None, "affection_req": 50
    },
    "deep_kiss": {
        "name": "딥키스", "time": 5, "stamina": 2,
        "effects": {"호감": 1, "애정": 2, "성적흥분": 3},
        "exp_part": "입술", "affection_req": 70
    },
    "breast_touch": {
        "name": "가슴 만지기", "time": 5, "stamina": 2,
        "effects": {"애정": 1, "성적흥분": 4},
        "exp_part": "가슴", "affection_req": 80
    },
}

def calculate_effects(action_def, partner_id):
    """경험치 보정된 효과 계산"""
    base_effects = action_def["effects"].copy()
    exp_part = action_def.get("exp_part")

    if exp_part:
        # 경험치 조회 (NPC별로 저장)
        exp_key = f"경험:{exp_part}"
        partner_props = morld.get_unit_props(partner_id)
        exp_value = partner_props.get(exp_key, 0)

        # 배율 계산: 1.0 + (경험 × 0.1)
        multiplier = 1.0 + (exp_value * 0.1)

        # 효과 적용 (반올림)
        for stat, value in base_effects.items():
            base_effects[stat] = round(value * multiplier)

        # 경험치 +1
        morld.modify_prop(partner_id, exp_key, 1)

    return base_effects
```

### 캐릭터별 반응 시스템

각 NPC가 연애 행위에 대해 다른 반응을 보이도록 Python Asset 클래스에서 정의.

#### 반응 타이밍
| 타이밍 | 설명 | 용도 |
|--------|------|------|
| `start` | 행위 시작 시 (토글 ON, 즉시 시작) | 첫 반응 대사 |
| `during` | 행위 진행 중 (UI에 표시) | 현재 상태 묘사 |
| `end` | 행위 종료 시 (토글 OFF) | 마무리 대사 |

#### 베이스 클래스 정의
```python
# assets/base.py
class Character(Unit):
    # 기본 반응 (모든 캐릭터 공통 - 미정의 시 사용)
    ROMANCE_REACTIONS = {
        "hug": {
            "during": "상대가 당신을 안고 있다.",
        },
        "deep_kiss": {
            "during": "상대가 키스에 응하고 있다.",
        },
        "breast_touch": {
            "during": "상대가 숨을 참고 있다.",
        },
    }

    def get_romance_reaction(self, action_id, timing="during"):
        """연애 행위 반응 텍스트 반환 - 서브클래스에서 오버라이드 가능"""
        reactions = getattr(self, 'ROMANCE_REACTIONS', {})
        action_reactions = reactions.get(action_id, {})
        return action_reactions.get(timing)
```

#### NPC별 반응 정의 예시
```python
# assets/characters/sera.py
class Sera(Character):
    unique_id = "sera"
    name = "세라"

    ROMANCE_REACTIONS = {
        "hug": {
            "start": "...괜찮아.",
            "during": "세라가 조용히 몸을 맡긴다.",
            "end": "...충분해."
        },
        "french_kiss": {
            "start": "...!",
            "during": "세라가 살짝 눈을 감는다.",
        },
        "deep_kiss": {
            "during": "세라의 숨결이 거칠어진다.",
        },
        "breast_touch": {
            "start": "...하지 마.",
            "during": "세라가 이를 악문다.",
        },
    }

# assets/characters/mila.py
class Mila(Character):
    unique_id = "mila"
    name = "밀라"

    ROMANCE_REACTIONS = {
        "hug": {
            "start": "어머, 갑자기~?",
            "during": "밀라가 기분 좋게 웃는다.",
            "end": "아쉬워~"
        },
        "french_kiss": {
            "start": "음~♥",
            "during": "밀라가 장난스럽게 혀를 내민다.",
        },
        "deep_kiss": {
            "during": "밀라가 적극적으로 응한다.",
        },
        "breast_touch": {
            "start": "으응...♥",
            "during": "밀라가 몸을 밀착시킨다.",
        },
    }
```

#### 동적 반응 (상태 기반) 예시
```python
# assets/characters/sera.py
class Sera(Character):
    def get_romance_reaction(self, action_id, timing="during"):
        """상태에 따라 다른 반응"""
        props = morld.get_unit_props(self.instance_id)
        arousal = props.get("성적흥분", 0)

        # 성적흥분 높을 때 다른 반응
        if action_id == "deep_kiss" and timing == "during":
            if arousal > 30:
                return "세라가... 적극적으로 응한다."
            return "세라의 숨결이 거칠어진다."

        # 기본 반응 사용
        return super().get_romance_reaction(action_id, timing)
```

#### romance.py에서 호출
```python
def render_romance_ui(state):
    partner_id = state["partner_id"]

    # Python Asset 인스턴스 가져오기
    partner_asset = morld.get_asset_instance(partner_id)

    # 활성 토글들의 반응 수집
    reaction_lines = []
    for toggle_id in state["active_toggles"]:
        reaction = partner_asset.get_romance_reaction(toggle_id, "during")
        if reaction:
            reaction_lines.append(reaction)

    # UI 구성
    lines = []
    lines.append(f"[{partner_info['name']}와 함께]")
    # ... 헤더 ...

    # 반응 텍스트 표시
    if reaction_lines:
        lines.append("")
        for reaction in reaction_lines:
            lines.append(f"({reaction})")

    # ... 버튼 등 ...
    return "\n".join(lines)


def handle_action_reaction(state, action_id, timing):
    """행위 시작/종료 시 반응 다이얼로그"""
    partner_asset = morld.get_asset_instance(state["partner_id"])
    reaction = partner_asset.get_romance_reaction(action_id, timing)

    if reaction:
        # 짧은 반응은 UI에 바로 표시, 긴 반응은 다이얼로그로
        return reaction
    return None
```

### 예시 시나리오: 효과 중첩 + 경험치

```
상황: 껴안기(ON), 세라의 입술 경험 = 3

1. [프렌치 키스] 클릭
   → 시간 5분 경과
   → 체력 소모: 껴안기(1) + 프렌치 키스(2) = 3

   껴안기 효과 (경험 부위 없음):
   → 호감+1, 애정+2

   프렌치 키스 효과 (입술 경험 3):
   → 배율: 1.0 + (3 × 0.1) = 1.3
   → 호감: 1 × 1.3 = 1 (반올림)
   → 애정: 2 × 1.3 = 3 (반올림)
   → 성적흥분: 3 × 1.3 = 4 (반올림)

   합계:
   → 호감+2, 애정+5, 성적흥분+4
   → 세라의 입술 경험: 3 → 4
```

### 체력 부족 시
```
상황: 체력 2 남음, 껴안기(ON) 상태

1. [프렌치 키스] 클릭
   → 필요 체력: 껴안기(1) + 프렌치 키스(2) = 3
   → 현재 체력: 2
   → "체력이 부족합니다" 메시지
   → 행위 실행 불가

또는

1. [프렌치 키스] 클릭
   → 체력 2 모두 소모
   → 행위 일부 실행 후 연애 모드 강제 종료
   → "지쳤다..." 메시지
```

---

## UI 구조

```
┌──────────────────────────────────────────────────┐
│ [세라와 함께]                 체력: ████████░░ 8  │
│                                                  │
│ (세라가 당신을 바라보고 있다.)                     │
│ 호감: 65  애정: 42  성적흥분: 8                    │
│                                                  │
│ ─────────────────────────────────────────────── │
│                                                  │
│ [토글 행위]                                       │
│   [url=@proc:toggle:hug]▶ 껴안기[/url]            │  ← ON이면 "■ 껴안기"
│   [url=@proc:toggle:deep_kiss]딥키스[/url]        │
│   [color=gray]가슴 만지기[/color]                 │  ← 호감도 부족 (80 필요)
│                                                  │
│ [즉시 행위]                                       │
│   [url=@proc:instant:head_pat]머리 쓰다듬기[/url] │
│   [url=@proc:instant:cheek_caress]뺨 어루만지기[/url]│
│   [url=@proc:instant:cheek_pinch]뺨 꼬집기[/url]  │
│   [url=@proc:instant:ear_touch]귀 만지기[/url]    │
│   [url=@proc:instant:french_kiss]프렌치 키스[/url]│
│   [color=gray]엉덩이 쓰다듬기[/color]             │  ← 호감도 부족 (70 필요)
│                                                  │
│ ─────────────────────────────────────────────── │
│ [url=@proc:exit]그만두기[/url]                    │
└──────────────────────────────────────────────────┘
```

### UI 렌더링 로직
```python
def render_romance_ui(state):
    partner_id = state["partner_id"]
    partner_info = morld.get_unit_info(partner_id)
    partner_props = morld.get_unit_props(partner_id)
    player_stamina = state["stamina"]

    lines = []

    # 헤더
    lines.append(f"[{partner_info['name']}와 함께]                 체력: {render_stamina_bar(player_stamina)}")
    lines.append("")
    lines.append(f"({partner_info['name']}(이)가 당신을 바라보고 있다.)")

    # 호감, 애정, 성적흥분 표시
    affection = partner_props.get("호감", 0)
    love = partner_props.get("애정", 0)
    arousal = partner_props.get("성적흥분", 0)
    lines.append(f"호감: {affection}  애정: {love}  성적흥분: {arousal}")
    lines.append("")
    lines.append("───────────────────────────────────")
    lines.append("")

    # 토글 행위
    lines.append("[토글 행위]")
    for action_id, action in TOGGLE_ACTIONS.items():
        is_on = action_id in state["active_toggles"]
        if affection >= action["affection_req"]:
            prefix = "■" if is_on else "▶"
            lines.append(f"  [url=@proc:toggle:{action_id}]{prefix} {action['name']}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 즉시 행위
    lines.append("[즉시 행위]")
    for action_id, action in INSTANT_ACTIONS.items():
        if affection >= action["affection_req"]:
            lines.append(f"  [url=@proc:instant:{action_id}]{action['name']}[/url]")
        else:
            lines.append(f"  [color=gray]{action['name']} (호감 {action['affection_req']} 필요)[/color]")
    lines.append("")

    # 푸터
    lines.append("───────────────────────────────────")
    lines.append("[url=@proc:exit]그만두기[/url]")

    return "\n".join(lines)

def render_stamina_bar(stamina, max_stamina=10):
    """체력 바 렌더링"""
    filled = int(stamina)
    empty = max_stamina - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {stamina}"
```

---

## 구현 순서

### Phase 1: C# API 구현
**목표**: 연애 시스템에 필요한 morld API 추가

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 1.1 `get_units_at_location(r, l)` | script_system_morld_api.cs | Location의 유닛 ID 목록 반환 | Test 1.1 |
| [ ] 1.2 `modify_prop(unit_id, prop, delta)` | script_system_morld_api.cs | prop 상대값 변경 (+/-) | Test 1.2 |
| [ ] 1.3 `add_unit_mood(unit_id, mood)` | script_system_data_api.cs | mood 추가 (기존 유지) | Test 1.3 |
| [ ] 1.4 `advance_time_simulate(minutes)` | script_system_data_api.cs | 시간 진행 + NPC JobBehavior 실행 | Test 1.4 |

**구현 상세**:
```csharp
// 1.1 get_units_at_location
// UnitSystem에서 CurrentLocation이 일치하는 유닛 필터링
// IsObject=true 포함 여부 결정 필요 (기본: 제외 권장)

// 1.2 modify_prop
// 기존 값 조회 후 delta 적용
// 존재하지 않는 prop은 0에서 시작

// 1.3 add_unit_mood
// Unit.Mood.Add() 호출 (HashSet이므로 중복 자동 무시)

// 1.4 advance_time_simulate
// 1. GameTime.AddMinutes()
// 2. JobBehaviorSystem.Proc() 직접 호출 또는 유사 로직
// 3. ThinkSystem은 호출하지 않음 (NPC AI 재계산 불필요)
```

### Phase 2: Python 연애 모듈 기본 구조
**목표**: romance.py 생성, 기본 UI 및 즉시형 행위

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 2.1 상수 정의 | romance.py | THRESHOLD, ACTION 테이블 | - |
| [ ] 2.2 `can_start_romance()` | romance.py | 진입 조건 체크 | - |
| [ ] 2.3 `render_romance_ui()` | romance.py | UI 텍스트 생성 | Test 2.1 |
| [ ] 2.4 `calculate_effects()` | romance.py | 경험치 보정 효과 계산 | Test 2.5 |
| [ ] 2.5 `start_romance()` 기본 | romance.py | Dialog + proc 기본 구조 | Test 2.1 |
| [ ] 2.6 즉시형 행위 처리 | romance.py | instant: 핸들링 | Test 2.2 |

**파일 구조**:
```
scenarios/scenario02/python/
├── romance.py          # 연애 시스템 메인
└── assets/characters/
    └── *.py            # NPC별 start_romance 메서드 (Phase 4)
```

**상수 정의**:
```python
# romance.py
ROMANCE_ENTRY_THRESHOLD = 50   # 연애 진입 최소 호감도
ROMANCE_JOIN_THRESHOLD = 60    # 합류 가능 최소 호감도
ROMANCE_STAMINA_KEY = "연애:스태미나"  # 생존:체력과 분리
DEFAULT_STAMINA = 10
```

### Phase 3: 토글 행위 및 시간 경과
**목표**: 토글 상태 관리, 효과 중첩, 시간 시뮬레이션

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 3.1 토글 상태 관리 | romance.py | active_toggles set 관리 | Test 2.3 |
| [ ] 3.2 효과 중첩 계산 | romance.py | apply_effects() 토글+즉시 합산 | Test 2.4 |
| [ ] 3.3 `advance_time_and_check()` | romance.py | 시간 경과 + NPC 감지 | Test 3.2 |
| [ ] 3.4 체력 소진 종료 | romance.py | stamina 0 시 종료 | Test 3.1 |

### Phase 4: 중단 이벤트
**목표**: 제3자 도착 시 중단 처리

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 4.1 중단 감지 로직 | romance.py | 호감도 < THRESHOLD NPC 감지 | Test 3.2 |
| [ ] 4.2 `handle_interruption()` | romance.py | 중단 다이얼로그, 상태 변경 | Test 3.2 |
| [ ] 4.3 파트너 반응 | romance.py | mood 추가, flee Job 설정 | Test 3.2 |
| [ ] 4.4 목격자 패널티 | romance.py | 호감도 -5 | Test 3.2 |

### Phase 5: NPC 연동 및 진입점
**목표**: NPC 액션에서 연애 시작

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 5.1 NPC actions 추가 | sera.py 등 | `call:start_romance:연애` | - |
| [ ] 5.2 `start_romance()` 메서드 | Character 클래스 | 연애 진입점 | Test 2.1 |
| [ ] 5.3 진입 조건 UI 피드백 | romance.py | 조건 불충족 시 메시지 | - |

**NPC 액션 예시**:
```python
# assets/characters/sera.py
class Sera(Character):
    actions = [
        "call:talk:대화",
        "call:start_romance:연애",  # 호감도 50 이상 시 표시
    ]

    def start_romance(self):
        from romance import start_romance
        player_id = morld.get_player_id()
        yield from start_romance(player_id, self.instance_id)
```

### Phase 6: 합류 이벤트 (선택)
**목표**: 호감도 높은 NPC 합류 처리

| 작업 | 파일 | 설명 | 테스트 |
|------|------|------|--------|
| [ ] 6.1 합류 감지 로직 | romance.py | 호감도 >= THRESHOLD NPC | Test 3.3 |
| [ ] 6.2 `handle_join()` | romance.py | 합류 다이얼로그 | Test 3.3 |
| [ ] 6.3 복수 파트너 state | romance.py | partners 리스트 관리 | Test 3.3 |
| [ ] 6.4 복수 파트너 UI | romance.py | 2인 이상 UI 렌더링 | Test 3.3 |

### Phase 7: 추가 기능 (선택)
**목표**: 성적흥분 감소, NPC별 커스터마이징

| 작업 | 파일 | 설명 |
|------|------|------|
| [ ] 7.1 성적흥분 감소 | romance.py 또는 events | 시간 경과 시 감소 |
| [ ] 7.2 NPC별 행위 제한 | sera.py 등 | 캐릭터별 허용 행위 |
| [ ] 7.3 NPC별 반응 텍스트 | sera.py 등 | 행위별 대사 |
| [ ] 7.4 특수 행위 | sera.py 등 | NPC 고유 행위 |

---

## 마일스톤

### MVP (Minimum Viable Product)
**Phase 1~4 완료 시 달성**

- [x] 설계 문서 완료
- [ ] C# API 4개 구현
- [ ] 연애 UI 표시
- [ ] 즉시형/토글형 행위 동작
- [ ] 경험치 시스템 동작
- [ ] 체력 소진 종료
- [ ] 중단 이벤트 동작

### Full Feature
**Phase 5~7 완료 시 달성**

- [ ] NPC 액션으로 연애 진입
- [ ] 합류 이벤트
- [ ] 성적흥분 시간 감소
- [ ] NPC별 커스터마이징

---

## UI 및 Generator 구조

### Dialog 기반 확장 가능 여부

**결론: 가능하다.**

현재 Dialog 시스템은 `proc` 콜백을 통해 상태 기반 UI를 지원하며, 이를 연애 모드에 활용 가능:

```python
# 현재 Dialog 시스템 흐름
yield morld.dialog(text, autofill="off", proc=callback, result=state)
    ↓
[사용자 클릭 @proc:값]
    ↓
callback(값) 호출
    ↓
반환값에 따라:
  - 문자열 → 텍스트 업데이트, Dialog 유지
  - True → Dialog 종료, Generator 재개
  - None/False → 변경 없음
```

연애 UI도 동일한 패턴으로 구현:
- `autofill="off"`: 커스텀 버튼만 표시
- `proc`: 행위 선택, 시간 경과, 중단 체크 처리
- `return True`: 중단 이벤트 발생 시 Dialog 종료

### 중단 이벤트와 Generator 구조

**문제**: 중단 시 새로운 Dialog(목격자 반응)를 표시해야 함

**해결책**: 중첩 Generator 대신, **순차 yield**

```python
def start_romance(player_id, partner_id):
    state = {"interrupted": False, "interrupter_id": None, ...}

    def proc(action):
        # 시간 경과 + NPC 도착 체크
        result = advance_time_and_check(state, time_cost)
        if result["interrupted"]:
            state["interrupted"] = True
            state["interrupter_id"] = result["interrupter_id"]
            return True  # ← Dialog 종료 신호
        return render_ui(state)

    # 1단계: 연애 UI (proc가 True 반환하면 종료)
    yield morld.dialog(render_ui(state), autofill="off", proc=proc, result=state)

    # 2단계: 중단된 경우 후속 Dialog
    if state["interrupted"]:
        # 순차적으로 yield (중첩 아님)
        yield morld.dialog(f"[{interrupter_name}]\n어머나!")
        yield morld.dialog(f"[{partner_name}]\n...!")

        # 상태 변경
        morld.add_unit_mood(partner_id, "부끄러움")
        morld.modify_prop(interrupter_id, "호감", -5)
```

**흐름도**:
```
┌─────────────────────────────────────────────────────────────┐
│ start_romance() Generator                                    │
│                                                             │
│  yield Dialog(연애 UI)  ←──────────────────────────┐        │
│         ↓                                          │        │
│  [사용자 클릭] → proc(action)                       │        │
│         ↓                                          │        │
│  중단 발생? ─No→ return render_ui() ───────────────┘        │
│         ↓ Yes                                               │
│  return True (Dialog 종료)                                   │
│         ↓                                                    │
│  ┌──────────────────────────────────┐                       │
│  │ Generator.Send() 호출            │                       │
│  │ → 다음 yield로 진행              │                       │
│  └──────────────────────────────────┘                       │
│         ↓                                                    │
│  yield Dialog(목격자 반응) ← 새 Dialog 표시                  │
│         ↓                                                    │
│  yield Dialog(파트너 반응) ← 순차 진행                       │
│         ↓                                                    │
│  상태 변경 (mood, Job, 호감도)                               │
│         ↓                                                    │
│  Generator 종료 → 일반 UI 복귀                               │
└─────────────────────────────────────────────────────────────┘
```

**핵심 원리**:
1. `proc`가 `True` 반환 → C#이 `Generator.Send(result)` 호출
2. Generator는 다음 `yield` 문으로 진행
3. 새 Dialog 반환 → C#이 다시 Dialog 표시
4. 중첩 Generator 없이 순차 진행

### yield from 사용 가능 여부

**가능하다.** 현재 시스템은 `yield from` 지원:

```python
def start_romance(player_id, partner_id):
    ...
    yield morld.dialog(render_ui(state), autofill="off", proc=proc, result=state)

    if state["interrupted"]:
        # 별도 함수로 분리 가능
        yield from handle_interruption(state)

def handle_interruption(state):
    """중단 이벤트 처리 - Sub-generator"""
    interrupter_id = state["interrupter_id"]
    partner_id = state["partner_id"]

    yield morld.dialog(f"[{interrupter_name}]\n어머나!")
    yield morld.dialog(f"[{partner_name}]\n...!")

    morld.add_unit_mood(partner_id, "부끄러움")
    morld.modify_prop(interrupter_id, "호감", -5)
```

`yield from`은 sub-generator의 모든 yield를 호출자에게 전달하므로,
C# 입장에서는 단일 Generator로 보임 (중첩 아님).

---

## 기술적 고려사항

### 시간 진행 방식
현재 `morld.advance_time()`은 단순 시간 증가만 수행.
연애 모드에서는:
1. 시간 증가
2. JobBehaviorSystem 실행 (NPC 이동)
3. 결과 반환

→ **새로운 API 필요**: `morld.advance_time_simulate(minutes)` (신규 구현)

### NPC 도착 감지 타이밍
- 매 행위 후 체크 (순간 행위)
- 매 틱 후 체크 (토글 행위)
- 실시간 체크 불가 → 이산적 체크

### 합류 vs 중단 판정
```python
# ROMANCE_JOIN_THRESHOLD = 60  # 상단에서 정의됨

def check_arrival(state, unit_id):
    props = morld.get_unit_props(unit_id)
    affection = props.get("호감", 0)

    if affection >= ROMANCE_JOIN_THRESHOLD:
        return "join"  # 합류 가능
    else:
        return "interrupt"  # 중단
```

---

## 예시 시나리오

### 시나리오 1: 정상 진행 + 효과 계산
```
초기 상태: 세라 - 호감 65, 애정 40, 성적흥분 0, 경험:입술 3
플레이어 체력: 10

플레이어: 세라와 거실에서 연애 모드 시작

1. [껴안기] ON 클릭
   → 시간 5분 경과, 체력 1 소모 (남은 체력: 9)
   → 껴안기 효과 (경험 부위 없음): 호감+1, 애정+2
   → 세라: 호감 66, 애정 42, 성적흥분 0

2. [프렌치 키스] 클릭 (껴안기 ON 상태)
   → 시간 5분 경과, 체력 3 소모: 껴안기(1) + 프렌치키스(2) (남은 체력: 6)

   껴안기 효과: 호감+1, 애정+2
   프렌치 키스 효과 (입술 경험 3):
     → 배율: 1.0 + (3 × 0.1) = 1.3
     → 호감: round(1 × 1.3) = 1
     → 애정: round(2 × 1.3) = 3
     → 성적흥분: round(3 × 1.3) = 4
     → 경험:입술 3 → 4

   합계: 호감+2, 애정+5, 성적흥분+4
   → 세라: 호감 68, 애정 47, 성적흥분 4

3. [딥키스] ON 클릭 (껴안기 ON 상태)
   → 시간 5분 경과, 체력 3 소모: 껴안기(1) + 딥키스(2) (남은 체력: 3)

   껴안기 효과: 호감+1, 애정+2
   딥키스 효과 (입술 경험 4):
     → 배율: 1.0 + (4 × 0.1) = 1.4
     → 호감: round(1 × 1.4) = 1
     → 애정: round(2 × 1.4) = 3
     → 성적흥분: round(3 × 1.4) = 4
     → 경험:입술 4 → 5

   합계: 호감+2, 애정+5, 성적흥분+4
   → 세라: 호감 70, 애정 52, 성적흥분 8

4. [그만두기] 클릭
   → 일반 UI 복귀

최종 상태: 세라 - 호감 70, 애정 52, 성적흥분 8, 경험:입술 5
경과 시간: 15분, 소모 체력: 7
```

### 시나리오 2: 중단 이벤트
```
초기 상태: 세라 - 호감 75, 리나 - 호감 30

플레이어: 세라와 세라의 방에서 연애 모드 시작
→ 딥키스 토글 시작 (5분 경과)
→ [귀 만지기] 클릭 (5분 경과) - 효과 적용
→ 리나가 세라의 방에 도착 (스케줄상 이동)
→ 리나 호감 30 < 60 (THRESHOLD)
→ 중단 이벤트 발생:
   - Dialog: "리나: 어머나!"
   - Dialog: "세라: ...!"
   - 세라 mood += "부끄러움"
   - 세라 Job = flee (30분)
   - 리나 호감 -= 5 (호감 25로 감소)
→ 일반 UI 복귀
```

### 시나리오 3: 합류
```
초기 상태: 세라 - 호감 80, 밀라 - 호감 70

플레이어: 세라(호감 80)와 거실에서 연애 모드 시작
→ 허그 토글 시작 (5분 경과)
→ 밀라(호감 70)가 거실에 도착
→ 밀라 호감 70 >= 60 (THRESHOLD)
→ 합류 이벤트:
   - Dialog: "밀라: 어머, 저도 끼워주세요~"
   - 파트너 목록에 밀라 추가
   - UI 업데이트 (2인 → 3인 행위 가능)
→ 연애 모드 계속
```

### 시나리오 4: 체력 소진
```
초기 상태: 세라 - 호감 80, 플레이어 체력 3

플레이어: 세라와 연애 모드 시작
→ [껴안기] ON (체력 1 소모, 남은 2)
→ [딥키스] ON 시도
   → 필요 체력: 껴안기(1) + 딥키스(2) = 3
   → 현재 체력: 2
   → 체력 부족으로 연애 모드 강제 종료
→ Dialog: "지쳤다..."
→ 일반 UI 복귀
```

---

## 누락/모순점 분석

> **마지막 검토**: 문서 내 일관성 검사 완료
> - ✅ API 명칭 통일 (`advance_time_simulate`)
> - ✅ 상수 명칭 통일 (`ROMANCE_JOIN_THRESHOLD`)
> - ✅ 테스트 케이스 수치 정정

### 1. API 현황 vs 설계 요구

| API | 설계 요구 | 현재 구현 | 상태 |
|-----|----------|----------|------|
| `get_unit_props(unit_id)` | props dict 반환 | ✅ 구현됨 (script_system_morld_api.cs:606) | OK |
| `get_units_at_location(r, l)` | 유닛 ID 목록 | ❌ 없음 | **Phase 1에서 구현** |
| `advance_time_simulate(minutes)` | 시간 + NPC 시뮬 | ❌ 없음 (`advance_time`은 시간만 진행) | **Phase 1에서 구현** |
| `add_unit_mood(unit_id, mood)` | mood 추가 | ❌ 없음 (`set_unit_mood`는 덮어쓰기) | **Phase 1에서 구현** |
| `modify_prop(unit_id, prop, delta)` | 상대값 변경 | ❌ 없음 (`set_unit_prop`는 절대값) | **Phase 1에서 구현** |
| `set_npc_job(unit_id, action, duration, target_id)` | Job 설정 | ✅ 구현됨 (script_system_npc_api.cs:29) | OK |

### 2. 체력 시스템 ~~모순~~ (해결됨)

~~**문제**: 설계에서 "플레이어 체력"을 사용하지만, 기존 survival.py의 체력 시스템과 충돌 가능~~

**✅ 해결**: 연애 전용 속성 `연애:스태미나` 사용

| 구분 | romance.md 설계 | survival.py 구현 |
|------|----------------|------------------|
| 속성 이름 | `연애:스태미나` | `생존:체력` |
| 기본값 | 10 | 100 |
| 용도 | 연애 행위 전용 | 생존 (굶주림/회복) |

### 3. 연애 진입 조건 함수 (Phase 2에서 구현 예정)

```python
def can_start_romance(player_id, target_id):
    """연애 진입 가능 여부 확인"""
    # 1. 대상 호감도 >= ROMANCE_ENTRY_THRESHOLD (50)
    # 2. 같은 Location 확인
    # 3. 호감도 낮은 제3자 없음 확인
    pass
```

**상수 정의 완료**:
```python
ROMANCE_ENTRY_THRESHOLD = 50   # 연애 진입 최소 호감도
ROMANCE_JOIN_THRESHOLD = 60    # 합류 가능 최소 호감도
ROMANCE_STAMINA_KEY = "연애:스태미나"
DEFAULT_STAMINA = 10
```

### 4. 합류(Join) 이벤트 (Phase 6에서 구현 예정)

MVP 범위 외, Phase 6에서 선택적 구현:

```python
# advance_time_and_check()에서 합류도 처리
if affection >= ROMANCE_JOIN_THRESHOLD:
    return {"joined": True, "joiner_id": unit_id}
```

**추가 필요** (Phase 6):
- `state["partners"]` → 복수 파트너 지원
- `handle_join(state, joiner_id)` → 합류 이벤트 처리

### 5. 성적흥분 감소 로직 (Phase 7에서 구현 예정)

설계에 명시: "성적흥분: 즉각적, **시간 지나면 감소**"

**현재**: 감소 로직 없음 (MVP 범위 외)

**Phase 7에서 구현**:
```python
# on_time_elapsed에서 감소 처리 또는 연애 종료 후 감소
def decay_arousal(unit_id, elapsed_minutes):
    # 예: 10분마다 성적흥분 -1
    pass
```

### 6. ~~advance_time vs advance_time_simulate 명칭~~ (해결됨)

~~설계 문서 내 혼용~~

**✅ 해결**: 문서 전체에서 `advance_time_simulate(minutes)` 신규 API로 통일

---

## 게임 내 테스트 과정

### Phase 1: API 구현 테스트

#### Test 1.1: `get_units_at_location` API
```
[전제조건]
- API 구현 완료

[테스트 절차]
1. 시나리오 시작
2. Python 콘솔에서 실행:
   >>> import morld
   >>> player_loc = morld.get_unit_location(morld.get_player_id())
   >>> units = morld.get_units_at_location(player_loc[0], player_loc[1])
   >>> print(units)

[예상 결과]
- 현재 Location의 유닛 ID 목록 반환 (플레이어 포함)

[확인 사항]
- [ ] 플레이어 ID 포함 확인
- [ ] 같은 위치의 NPC ID 포함 확인
- [ ] 다른 위치의 NPC ID 미포함 확인
```

#### Test 1.2: `modify_prop` API
```
[전제조건]
- API 구현 완료

[테스트 절차]
1. 테스트 NPC(세라) 호감도 확인:
   >>> sera_id = morld.get_unit_by_unique_id("sera")
   >>> props = morld.get_unit_props(sera_id)
   >>> print(props.get("호감", 0))  # 예: 50

2. 상대값 변경:
   >>> morld.modify_prop(sera_id, "호감", 10)

3. 결과 확인:
   >>> props = morld.get_unit_props(sera_id)
   >>> print(props.get("호감", 0))  # 예: 60

[예상 결과]
- 호감도가 +10 증가

[확인 사항]
- [ ] 양수 delta 정상 동작
- [ ] 음수 delta 정상 동작 (호감도 감소)
- [ ] 존재하지 않는 prop 초기값 0에서 시작
```

#### Test 1.3: `add_unit_mood` API
```
[전제조건]
- API 구현 완료

[테스트 절차]
1. 현재 mood 확인:
   >>> morld.get_unit_info(sera_id)["mood"]  # 예: []

2. mood 추가:
   >>> morld.add_unit_mood(sera_id, "부끄러움")

3. 결과 확인:
   >>> morld.get_unit_info(sera_id)["mood"]  # 예: ["부끄러움"]

4. 추가 mood:
   >>> morld.add_unit_mood(sera_id, "행복")
   >>> morld.get_unit_info(sera_id)["mood"]  # 예: ["부끄러움", "행복"]

[예상 결과]
- 기존 mood 유지하면서 새 mood 추가

[확인 사항]
- [ ] 기존 mood 유지 확인
- [ ] 중복 mood 처리 (중복 허용? 무시?)
```

#### Test 1.4: `advance_time_simulate` API
```
[전제조건]
- API 구현 완료
- NPC 스케줄 설정됨

[테스트 절차]
1. 현재 시간 및 NPC 위치 기록:
   >>> time_before = morld.get_game_time()
   >>> sera_loc_before = morld.get_unit_location(sera_id)

2. 시간 시뮬레이션 (60분):
   >>> morld.advance_time_simulate(60)

3. 결과 확인:
   >>> time_after = morld.get_game_time()
   >>> sera_loc_after = morld.get_unit_location(sera_id)

[예상 결과]
- 시간 +60분
- NPC가 스케줄에 따라 이동했을 수 있음

[확인 사항]
- [ ] 시간 정상 증가
- [ ] NPC JobList 처리됨
- [ ] NPC 위치 변경 가능 (스케줄에 따라)
```

### Phase 2: 연애 모드 기본 테스트

#### Test 2.1: 연애 UI 렌더링
```
[전제조건]
- romance.py 모듈 생성
- render_romance_ui 구현

[테스트 절차]
1. 연애 진입 가능한 NPC 옆으로 이동
2. 연애 시작 액션 실행 (call:start_romance:연애)

[예상 결과]
- 연애 UI 다이얼로그 표시
- 파트너 이름, 체력 바, 호감/애정/성적흥분 표시
- 토글 행위, 즉시 행위 버튼 표시

[확인 사항]
- [ ] 헤더 정보 정확
- [ ] 호감도 부족 행위 회색 표시
- [ ] 토글 ON/OFF 아이콘 구분
```

#### Test 2.2: 즉시형 행위 실행
```
[전제조건]
- 연애 UI 표시 상태

[테스트 절차]
1. [머리 쓰다듬기] 클릭

[예상 결과]
- 체력 -1
- 파트너 호감 +2, 애정 +1
- UI 갱신

[확인 사항]
- [ ] 체력 바 감소
- [ ] 호감/애정 수치 증가
- [ ] 시간 경과 (3분)
```

#### Test 2.3: 토글형 행위 실행
```
[전제조건]
- 연애 UI 표시 상태

[테스트 절차]
1. [껴안기] 클릭 (OFF → ON)
2. 아이콘 변경 확인 (▶ → ■)
3. [껴안기] 다시 클릭 (ON → OFF)
4. 아이콘 변경 확인 (■ → ▶)

[예상 결과]
- 토글 상태 정상 전환
- ON/OFF 모두 체력, 효과 적용

[확인 사항]
- [ ] ON 시 아이콘 ■
- [ ] OFF 시 아이콘 ▶
- [ ] 양쪽 모두 효과 적용
```

#### Test 2.4: 효과 중첩 테스트
```
[전제조건]
- 껴안기 ON 상태

[테스트 절차]
1. 현재 스탯 기록:
   - 체력: X
   - 호감: Y
   - 애정: Z
2. [프렌치 키스] 클릭
3. 스탯 변화 확인

[예상 결과]
- 체력: X - 3 (껴안기 1 + 프렌치키스 2)
- 호감: Y + 2 (껴안기 1 + 프렌치키스 1)
- 애정: Z + 4 이상 (껴안기 2 + 프렌치키스 2~3)

[확인 사항]
- [ ] 체력 합산 소모
- [ ] 효과 합산 적용
- [ ] 경험치 증가 (입술)
```

#### Test 2.5: 경험치 시스템 테스트
```
[전제조건]
- 파트너의 경험:입술 = 0

[테스트 절차]
1. [프렌치 키스] 5회 반복 실행
2. 매 실행마다 성적흥분 증가량 기록

[예상 결과]
- 1회: 성적흥분 +3 (배율 1.0)
- 2회: 성적흥분 +3 (배율 1.1, round(3.3)=3)
- 3회: 성적흥분 +4 (배율 1.2, round(3.6)=4)
- ...

[확인 사항]
- [ ] 경험치 누적 확인
- [ ] 배율 효과 확인
- [ ] 반올림 정확성
```

### Phase 3: 이벤트 테스트

#### Test 3.1: 체력 소진 종료
```
[전제조건]
- 플레이어 연애:스태미나를 3으로 설정

[테스트 절차]
1. 연애 모드 진입
2. [껴안기] ON (스태미나 1 소모, 남은 스태미나: 2)
3. [딥키스] ON 시도 (필요: 껴안기 1 + 딥키스 2 = 3)

[예상 결과]
- 연애 모드 강제 종료
- "지쳤다..." 다이얼로그

[확인 사항]
- [ ] 체력 부족 감지
- [ ] 종료 다이얼로그 표시
- [ ] 일반 UI 복귀
```

#### Test 3.2: 중단 이벤트
```
[전제조건]
- 플레이어 + 세라 (호감 80) 같은 위치
- 리나 (호감 30) 스케줄상 곧 도착 예정

[테스트 절차]
1. 세라와 연애 모드 진입
2. 행위 실행 (시간 경과)
3. 리나 도착 대기

[예상 결과]
- 연애 UI 종료
- 리나 반응 다이얼로그
- 세라 반응 다이얼로그
- 세라 mood += "부끄러움"
- 세라 Job = flee
- 리나 호감 -5

[확인 사항]
- [ ] 중단 감지 정확
- [ ] 다이얼로그 순서 정확
- [ ] 상태 변경 적용
```

#### Test 3.3: 합류 이벤트 (Phase 4에서 구현 시)
```
[전제조건]
- 플레이어 + 세라 (호감 80) 같은 위치
- 밀라 (호감 70) 스케줄상 곧 도착 예정

[테스트 절차]
1. 세라와 연애 모드 진입
2. 행위 실행 (시간 경과)
3. 밀라 도착 대기

[예상 결과]
- 합류 다이얼로그
- 파트너 목록에 밀라 추가
- UI 갱신 (2인 → 3인)

[확인 사항]
- [ ] 합류 감지
- [ ] 파트너 추가
- [ ] UI 정상 갱신
```

---

## 테스트 데이터 설정

```python
# test_romance_setup.py - 테스트용 데이터 설정

import morld

def setup_romance_test():
    """연애 시스템 테스트 환경 설정"""
    player_id = morld.get_player_id()
    sera_id = morld.get_unit_by_unique_id("sera")

    # 1. 플레이어 스태미나 설정 (연애 전용)
    morld.set_unit_prop(player_id, "연애:스태미나", 10)

    # 2. 세라 호감도 설정
    morld.set_unit_prop(sera_id, "호감", 80)
    morld.set_unit_prop(sera_id, "애정", 40)
    morld.set_unit_prop(sera_id, "성적흥분", 0)

    # 3. 경험치 초기화
    morld.set_unit_prop(sera_id, "경험:입술", 0)
    morld.set_unit_prop(sera_id, "경험:귀", 0)
    morld.set_unit_prop(sera_id, "경험:가슴", 0)
    morld.set_unit_prop(sera_id, "경험:엉덩이", 0)

    # 4. 세라를 플레이어 위치로 이동
    player_loc = morld.get_unit_location(player_id)
    morld.set_unit_location(sera_id, player_loc[0], player_loc[1])

    print("Romance test setup complete!")
    print(f"  Player stamina: 10")
    print(f"  Sera affection: 80")
    print(f"  Same location: {player_loc}")


def setup_interrupt_test():
    """중단 이벤트 테스트 환경"""
    setup_romance_test()

    lina_id = morld.get_unit_by_unique_id("lina")

    # 리나 호감도를 낮게 설정 (중단 트리거)
    morld.set_unit_prop(lina_id, "호감", 30)

    # 리나를 플레이어 위치 근처로 이동 예정 설정
    # (스케줄 또는 수동 Job 설정)
    player_loc = morld.get_unit_location(morld.get_player_id())
    # 리나가 10분 후 도착하도록 Job 설정
    morld.set_npc_job(lina_id, "move", 10)  # 실제로는 location 지정 필요

    print(f"  Lina affection: 30 (interrupt trigger)")


def setup_join_test():
    """합류 이벤트 테스트 환경"""
    setup_romance_test()

    mila_id = morld.get_unit_by_unique_id("mila")

    # 밀라 호감도를 높게 설정 (합류 트리거)
    morld.set_unit_prop(mila_id, "호감", 70)

    print(f"  Mila affection: 70 (join trigger)")
```

## 디버그 명령어

```python
# 연애 시스템 디버그 명령어

def debug_romance_state(partner_id):
    """파트너의 연애 관련 상태 출력"""
    props = morld.get_unit_props(partner_id)
    info = morld.get_unit_info(partner_id)
    print(f"=== {info['name']} Romance State ===")
    print(f"호감: {props.get('호감', 0)}")
    print(f"애정: {props.get('애정', 0)}")
    print(f"성적흥분: {props.get('성적흥분', 0)}")
    print(f"경험:입술: {props.get('경험:입술', 0)}")
    print(f"경험:귀: {props.get('경험:귀', 0)}")
    print(f"경험:가슴: {props.get('경험:가슴', 0)}")
    print(f"경험:엉덩이: {props.get('경험:엉덩이', 0)}")
    print(f"mood: {info.get('mood', [])}")


def debug_location_units():
    """현재 플레이어 위치의 모든 유닛 출력"""
    player_id = morld.get_player_id()
    loc = morld.get_unit_location(player_id)
    units = morld.get_units_at_location(loc[0], loc[1])

    print(f"=== Units at {loc} ===")
    for uid in units:
        info = morld.get_unit_info(uid)
        props = morld.get_unit_props(uid)
        affection = props.get("호감", 0)
        marker = "(player)" if uid == player_id else ""
        print(f"  [{uid}] {info['name']} - 호감: {affection} {marker}")
```
