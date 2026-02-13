# 연애 관계 시스템 (Romance Relationship)

## 개요

NPC와의 관계를 수치화하고 관계 진행에 따라 행위를 해금하는 시스템.
호감/욕망/복종/반발 prop과 관계 라벨, 이중 경로 잠금 해제, 사적인 대화 시스템을 포함.

---

## 1. 관계 라벨 시스템

### 개요
호감 + 욕망 기반으로 관계 상태를 라벨로 표시. `애정` prop 제거 후 도입.

### 라벨 매핑

| 호감 | 욕망 | 라벨 |
|------|------|------|
| < 50 | < 40 | 타인 |
| ≥ 50 | < 40 | 친구 |
| < 50 | ≥ 40 | 정욕 |
| ≥ 50 | ≥ 40 | 애인 |

### Prop 구조 (v0.2.2)
- **제거**: `관계:{name}:애정` — 호감에 통합
- **추가**: `관계:{name}:반발` (0-100) — 관계별 저항/반발 수치
- **유지**: 호감, 욕망, 복종

### 반발 시스템
- 자극 계산 시 반발이 높으면 자극 증가량 감소: `max(0.2, 1.0 - rebellion * 0.008)`
- 절정 시 감각 경험치 억제: `max(0, base_gain - rebellion // 25)`
- UI: 반발 > 0일 때만 표시

---

## 2. 욕망 시스템 (Desire System)

### 개요

관계별 욕망(`관계:{name}:욕망`) prop으로 NPC에 대한 성적 욕구를 추적.
스킨십 행위의 effects에 `"욕망"` 키가 있으면 자동 반영됩니다.

### Prop 구조

`관계:{대상이름}:욕망` — 관계별 A-B 쌍 (호감/애정과 동일 패턴)

### 성욕 자연 상한 (Dynamic Arousal Cap)

욕망이 높을수록 성욕의 자연 상한이 상승:

```python
def _get_arousal_cap(unit_id):
    max_desire = max(관계:*:욕망 props)
    return min(100, 50 + max_desire * 0.5)
```

| 최고 욕망 | 성욕 자연 상한 |
|----------|--------------|
| 0 | 50 |
| 50 | 75 |
| 100 | 100 |

### NPC 주도 조건

`INITIATIVE_CONFIG`에 `desire_threshold` 추가:
- 욕망이 임계값 이상이어야 NPC 주도 발동
- 현재 모든 캐릭터 0 (체크 안 함)

---

## 3. 이중 경로 잠금 해제 (Dual-Path Unlock)

### 개요

액션의 `affection_req`(필요 호감도)를 애정 경로 **또는** 육욕 경로로 해금할 수 있는 시스템.
욕망이 높으면 호감도가 부족해도 NPC가 마지못해 허락합니다.

### 유효 호감 요구치 공식

```python
def get_effective_affection_req(req, desire=0, submission=0):
    """욕망/복종에 의한 호감 요구치 할인"""
    desire_discount = min(req * 0.3, desire * 0.3)
    submission_discount = min(req * 0.3, submission * 0.3)
    total = min(req * 0.5, desire_discount + submission_discount)
    return max(20, req - total)
```

**할인 규칙:**
- 욕망: 최대 30% 할인
- 복종: 최대 30% 할인 (디버그 전용 — 자연 증가 미구현)
- 합산: 최대 50% 할인
- 절대 최소: 20

### 할인 테이블 예시

| 액션 (req) | 욕망 0 | 욕망 50 | 욕망 100 | 욕망 100+복종 100 |
|-----------|--------|---------|----------|-----------------|
| breast_touch (80) | 80 | 65 | 56 | 40 |
| genital_caress (85) | 85 | 70 | 60 | 43 |
| genital_touch (90) | 90 | 75 | 63 | 45 |
| clit_rub (95) | 95 | 80 | 67 | 48 |

### 적용 위치 (6곳)

| 파일 | 위치 | 설명 |
|------|------|------|
| romance.py | render_romance_ui() 토글 표시 | 플레이어 주도 토글 해금 |
| romance.py | render_romance_ui() 즉시 표시 | 플레이어 주도 즉시 해금 |
| npc_initiative.py | render_npc_initiative_ui() | NPC 주도 중 플레이어 즉시 표시 |
| npc_initiative.py | get_available_npc_actions() | NPC 토글 선택 조건 |
| date.py | 데이트 중/외 애정 표현 | Phase C에서 적용 예정 |

### UI 색상 구분

| 해금 경로 | 색상 | 의미 |
|----------|------|------|
| 애정 해금 (호감 >= req) | 기본색 | 정상 해금 |
| 욕망 해금 (호감 < req, 할인으로 해금) | 핑크 (`[color=pink]`) | 마지못해 허락 |

### 헬퍼 함수 (romance.py)

```python
def is_action_available(partner_id, player_id, action_def):
    """액션 해금 여부 (이중 경로 체크)"""

def get_submission_key(player_id):
    """복종 prop 키 생성"""

def is_desire_unlocked(affection, action_def, desire, submission=0):
    """욕망/복종에 의한 해금인지 (핑크색 표시용)"""
```

### INITIATIVE_ACTION_FILTERS context

base.py `get_allowed_initiative_actions()`의 context에 `"욕망"`, `"복종"` 포함:
```python
context = {
    "성욕": ..., "호감": ..., "반발": ...,
    "욕망": props.get(f"관계:{player_name}:욕망", 0),
    "복종": props.get(f"관계:{player_name}:복종", 0),
}
```

### 복종 시스템

- **Prop**: `관계:{name}:복종` (0-100)
- **할인 공식**: `get_effective_affection_req()`에 submission 파라미터 활성화 완료
- **UI**: 복종 > 0일 때만 스킨십 UI 헤더에 `복종: N` 표시
- **디버그**: `debug_submission_up/down` (+/-20 수동 조정)
- **date.py**: 이중 경로 미적용 (향후 적용 예정)

#### 자연 증가

| 조건 | 증가량 | 비고 |
|------|--------|------|
| 행위 수행 (affection_req ≥ 80) | +1 | 반발 50 미만일 때만 |
| NPC 절정 (반발 0-24) | +2 | 반발에 의해 억제 |
| NPC 절정 (반발 25-49) | +1 | |
| NPC 절정 (반발 50+) | +0 | 증가 없음 |

#### 적용 위치

| 파일 | 함수 | 설명 |
|------|------|------|
| romance.py | `apply_effects()` | 플레이어 주도: 행위 +1, 절정 +2 |
| npc_initiative.py | `apply_action_effects()` | NPC 주도: 동일 |
| needs.py | `_process_hourly()` | 관계 항상성 (아래 참조) |

---

## 4. 관계 항상성 (Homeostasis)

### 개요

호감/반발/복종이 시간에 따라 basin(끌개)으로 자연 수렴.
기존의 "복종 -1/2h" 단순 감소 대신, 현재 값에 따라 수렴 방향이 달라지는 항상성 시스템.

### 수렴 공식

```python
HOMEOSTASIS_RATE = 0.5  # 시간당 최대 ±0.5

def _apply_homeostasis(unit_id, prop_key, basins):
    current = get_prop(unit_id, prop_key) or 0
    attractor = basins[-1][1]  # 기본: 최상위 basin
    for threshold, target in basins:
        if current < threshold:
            attractor = target
            break
    delta = sign(attractor - current) * min(abs(attractor - current), 0.5)
    new_value = clamp(0, 100, current + delta)
```

### Basin 정의

| Prop | 구간 | attractor | 의미 |
|------|------|-----------|------|
| 호감 | < 35 | 0 | 소원 → 0으로 수렴 |
| 호감 | 35-75 | 50 | 중립 → 50으로 수렴 |
| 호감 | > 75 | 100 | 친밀 → 100으로 수렴 |
| 반발 | < 25 | 0 | 저반발 → 0으로 수렴 |
| 반발 | 25-50 | 35 | 중반발 → 35로 수렴 |
| 반발 | > 50 | 75 | 고반발 → 75로 수렴 |
| 복종 | < 20 | 0 | 저복종 → 0으로 수렴 |
| 복종 | 20-60 | 40 | 중복종 → 40으로 수렴 |
| 복종 | > 60 | 80 | 고복종 → 80으로 수렴 |

### 설계 의도

- **무조건적 감소 방지**: 기존에는 복종이 무조건 -1/2h로 감소했으나, 이제 basin 내에서 유지
- **관계 안정성**: 호감 60이면 50으로 수렴 (10 감소), 호감 80이면 100으로 수렴 (20 증가)
- **외부 행위로만 basin 이동**: 스킨십/이벤트로 경계(35, 75)를 넘어야 basin 변경
- **극단적 반발 안정화**: 반발 100은 75로 서서히 감소, 반발 20은 0으로 감소

---

## 5. 사적인 대화 시스템 (진척도)

### 개요
호감도가 높아지면 NPC와 점점 깊은 대화를 나눌 수 있는 시스템.
대화할 때마다 "진척도"가 증가하고, 진척도에 따라 새로운 대화가 해금됩니다.

### 진척도 구조

| 진척도 | 필요 호감 | 대화 내용 | 일회성 |
|--------|----------|----------|--------|
| 1 | 50 | 자신에 대한 이야기 (소개, 가족) | ✅ |
| 2 | 60 | 좋아하는 것 (취미, 기호) | ✅ |
| 3 | 70 | 과거 이야기 (기억, 트라우마) | ✅ |

### TALK_RULES 설정

```python
TALK_RULES = [
    # 특수 상황 (최우선)
    ({"activity": "수면"}, {"pages": ["(자고 있다)", "...zzZ"]}),

    # 진척도별 사적인 대화 (플래그로 일회성 체크)
    ({"호감": 70, "진척도": 3}, "_talk_progress_3"),
    ({"호감": 60, "진척도": 2}, "_talk_progress_2"),
    ({"호감": 50, "진척도": 1}, "_talk_progress_1"),

    # 호감도 기반 (진척도 증가 로직 포함)
    ({"호감": 70}, "_talk_friendly_high"),
    ({"호감": 50}, "_talk_friendly_mid"),

    # 기본값
    ({}, {"pages": ["기본 대사..."]}),
]
```

### 진척도 증가 메서드

```python
def _talk_friendly_high(self, context):
    """호감도 70 이상 - 진척도 증가 기회"""
    name = context.get("name", self.name)
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    # 진척도 증가 (최대 3)
    props = morld.get_unit_props(self.instance_id)
    progress_key = f"관계:{player_name}:진척도"
    current_progress = props.get(progress_key, 0) if props else 0

    if current_progress < 3:
        morld.set_unit_prop(self.instance_id, progress_key, current_progress + 1)

    yield morld.dialog([f"[{name}]", "호감도 높은 대사..."])
```

### 사적인 대화 메서드 (일회성)

```python
def _talk_progress_1(self, context):
    """진척도 1 - 자신에 대한 이야기 (일회성)"""
    name = context.get("name", self.name)
    player_id = morld.get_player_id()
    player_info = morld.get_unit_info(player_id)
    player_name = player_info.get("name", "주인공") if player_info else "주인공"

    # 플래그 체크 (이미 들었으면 일반 대화)
    flag_key = f"대화:{player_name}:진척도1"
    props = morld.get_unit_props(self.instance_id)
    if props and props.get(flag_key):
        yield morld.dialog([f"[{name}]", "이미 들은 후 대사..."])
        return

    # 플래그 설정 및 사적인 이야기
    morld.set_unit_prop(self.instance_id, flag_key, 1)
    yield morld.dialog([
        f"[{name}]",
        "자신에 대한 이야기...",
        "가족 소개...",
    ])
```

### 캐릭터별 대화 내용

| 캐릭터 | 진척도 1 (자신 소개) | 진척도 2 (좋아하는 것) | 진척도 3 (과거) |
|--------|---------------------|----------------------|---------------|
| **세라** | 사냥 담당, 혼자 있는 게 편함 | 숲, 사냥, 고요함 | 혼자 눈을 뜸, 기억 없음, 밀라/리나 만남 |
| **밀라** | 살림 담당, 세라/리나를 가족처럼 | 요리, 사람들이 맛있게 먹는 것, 티타임 | 저택에서 혼자 깨어남, 세라/리나 발견 |
| **리나** | 채집/빨래 담당, 세라/밀라 언니 | 채집, 숲, 베리잼, 사람들과 놀기 | 혼자서 무서웠음, 언니들 만남 |
| **유키** | 엘라와 둘이 삶, 엘라가 돌봐줌 | 책, 조용한 것, 다른 세계 | 혼자서 무서웠음, 엘라 만남 |
| **엘라** | 유키를 지킴, 그게 자신의 역할 | 조용한 밤, 유키가 웃는 것 | 도시에서 혼자 깨어남, 유키 발견 |

### 캐릭터별 말투 스타일

| 캐릭터 | 스타일 | 예시 |
|--------|--------|------|
| **세라** | 무뚝뚝, 짧은 문장 | "......", "...알고 싶지도 않아." |
| **밀라** | 다정, 존댓말 | "~해요", "~네요", "괜찮으세요?" |
| **리나** | 활발, 반말 | "~야!", "에헤헤~", "좋아좋아!" |
| **유키** | 수줍음, 말줄임표 많음 | "...네...", "...~요...", "...(고개를 숙인다)" |
| **엘라** | 냉정, 명령조 | "...~다.", "...~냐.", "...간단히 말해라." |

### 공통 스토리 설정
모든 NPC는 "기억이 없다"는 공통점을 가짐:
- 어느 날 혼자 눈을 뜸
- 누구인지, 왜 여기 있는지 모름
- 다른 NPC를 만나 함께 살기로 함
- 플레이어도 같은 상황임을 알게 됨

---

## 6. 성별 시스템 (gender.py)

### 개요
캐릭터의 성별에 따라 보유 감각 카테고리를 결정.

### 성별별 보유 감각

| 성별 | 감각 카테고리 |
|------|-------------|
| male | M, B, A, P |
| female | M, B, A, V, C |
| futanari | M, B, A, V, C, P |
| asexual | M |

### API
- `get_gender(unit_id)` → Character.type 기반 성별 반환
- `has_anatomy(unit_id, category)` → 해당 카테고리 보유 여부
- `get_anatomy(unit_id)` → 보유 감각 카테고리 frozenset

### 플레이어 성별 선택
캐릭터 생성 시 성별 선택 가능 (male/female/futanari).
`player_creation.py`에서 gender 단계 → `Player.type` + `morld.set_unit(type)` 반영.

### 현재 캐릭터
Player=선택 가능(male/female/futanari), 모든 NPC=female.

### 행위 해부학 필터링

`is_anatomy_compatible(action_def, target_id)`: 행위의 `exp_part`가 대상의 anatomy와 호환되는지 확인.

- V/C 행위 (음부/클리토리스): female/futanari에게만 표시
- P 행위 (음경): male/futanari에게만 표시
- 비성적 부위 (귀, 뺨, 머리) 및 exp_part 없는 행위: 항상 표시

**필터 적용 지점:**
- `romance.py render_romance_ui()`: 파트너 anatomy 기준 (플레이어→파트너)
- `npc_initiative.py get_available_npc_actions()`: 플레이어 anatomy 기준 (NPC→플레이어)
- `npc_initiative.py render_npc_initiative_ui()`: NPC anatomy 기준 (플레이어 즉시행위)

---

## 7. 성적 지향성 (Sexual Orientation)

### 개요
NPC별 성적 지향에 따라 호감/성욕 효과에 배율 적용.

### 지향성 종류 및 배율

| 지향 | 조건 | 배율 |
|------|------|------|
| bisexual (양성애) | 항상 | ×1.0 |
| heterosexual (이성애) | 이성 파트너 | ×1.1 |
| heterosexual (이성애) | 동성 파트너 | ×0.5 |
| homosexual (동성애) | 동성 파트너 | ×1.1 |
| homosexual (동성애) | 이성 파트너 | ×0.5 |

- futanari는 female 기반으로 취급
- 배율은 `calculate_effects()` 결과 전체에 곱셈
- 성욕 자연 증가에도 적용 (`needs.py`)

### 캐릭터별 지향

| 캐릭터 | 지향 |
|--------|------|
| 세라 | bisexual (양성애) |
| 밀라 | heterosexual (이성애) |
| 리나 | bisexual (양성애) |
| 유키 | bisexual (양성애) |
| 엘라 | heterosexual (이성애) |

### API

```python
import gender

gender.register_orientation(unit_id, "heterosexual")
gender.get_orientation(unit_id)                    # → str
gender.get_orientation_multiplier(npc_id, player_id)  # → float
gender.reset_orientation()                         # 챕터 전환
```

---

## 8. 체격/음경 크기 호환성 (Penetration Compatibility)

### 개요
삽입 행위 시 체격 차이 + 음경 크기로 준비 필요/통증/자극 배율을 결정.

### 체격 (Body Size)

모든 캐릭터에 `체격` prop 설정:

| 캐릭터 | 체격값 | 라벨 |
|--------|--------|------|
| 리나 | 1 | 왜소 |
| 유키 | 1 | 왜소 |
| 밀라 | 2 | 보통 |
| 세라 | 3 | 장신 |
| 엘라 | 3 | 장신 |
| 플레이어 | 1-4 | 선택 |

### 음경 크기 (Penis Size)

남성/후타나리 플레이어만 캐릭터 생성 시 선택 (3단계):

| 값 | 라벨 |
|---|------|
| 1 | 작음 |
| 2 | 보통 |
| 3 | 큼 |

Prop: `음경:크기` — `get_penis_size()` 기본값 2.

### 호환성 체크

`check_penetration_compatibility(actor_id, target_id)`:
- `diff = penis_size - body_size`

| diff | needs_prep | pain | stim_mod |
|------|-----------|------|----------|
| ≥ 2 | 60 (stim) | True | ×1.3 |
| 1 | 30 (stim) | False | ×1.1 |
| 0 | 0 | False | ×1.0 |
| -1 | 0 | False | ×0.85 |
| ≤ -2 | 0 | False | ×0.7 |

- **needs_prep**: 대상 부위 자극이 이 값 미만이면 삽입 차단 + 메시지
- **pain**: True면 삽입 시 반발 +3, 삽입 중 NPC에 `크기통증` prop → 통증+쾌감 혼재 반응
- **stim_mod**: 삽입 토글 활성 동안 자극 계산에 곱셈
