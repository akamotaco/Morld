# 성인용품 시스템 (Adult Toys System)

> `assets/items/adult_toys.py`, `restraint.py`, `needs.py` — 순수 Python

성인용품 아이템 정의, 결박 메커니즘, 절정 상시 관리를 통합한 시스템.

**관련 문서**:
| 문서 | 설명 |
|------|------|
| [romance-actions.md](romance-actions.md) | 로맨스 행위 정의 (신규 액션 포함) |
| [life.md](life.md) | NPC 자위 시 성인용품 사용 |
| [system-gameplay.md](system-gameplay.md) | 장비 슬롯, 욕구 시스템 |

---

## 1. 아이템 분류

### 착용형 (equip system)

기존 장비 시스템과 동일한 `equip_props` 기반. 캐릭터에 장착하면 C#이 prop을 자동 적용.

| # | unique_id | 이름 | equip_props | 비고 |
|---|-----------|------|-------------|------|
| 1 | `penis_band` | 페니스 밴드 | `착용:하체장비`, `임시해부학:P` | V/C 있는 캐릭터만. 임시 P anatomy (사정 불가) |
| 2 | `ball_gag` | 볼개그 | `착용:구강장비`, `결박:입` | 말하기/구강행위/식사 차단 |
| 3 | `nipple_clamp` | 니플클램프 | `착용:유두장비`, `성인용품:자극=3` | +3 절정/h |
| 4 | `blindfold` | 안대 | `착용:안경`, `결박:눈` | 기존 안경 슬롯 공유 |
| 5 | `collar_leash` | 목줄 | `착용:목장비`, `성인용품:목줄` | 묘사 연출용 |
| 6 | `restraint_rope` | 결박 로프 | `착용:결박`, `결박:상체`, `결박:하체`, `결박:강도=30` | 전신 결박, 해제 난이도 낮음 |
| 7 | `handcuffs` | 수갑 | `착용:결박상체`, `결박:상체`, `결박:강도=60` | 상체 결박, 해제 난이도 높음 |
| 8 | `arm_cuffs` | 팔 결박구 | `착용:결박상체`, `결박:상체`, `결박:강도=40` | 상체 결박 |
| 9 | `leg_cuffs` | 다리 결박구 | `착용:결박하체`, `결박:하체`, `결박:강도=40` | 하체 결박 |
| 10 | `full_body_restraint` | 전신 결박구 | `착용:결박전신`, `결박:상체`, `결박:하체`, `결박:강도=100` | 전신 결박, 자력 해제 사실상 불가 |

### 삽입형 (prop-based 추적)

착용형과 달리 `equip`이 아닌 캐릭터 prop `삽입물:{부위}`에 item_id를 기록.
해당 오리피스의 자연 삽입(음경 등)을 차단.

| # | unique_id | 이름 | 삽입 가능 부위 | 효과 |
|---|-----------|------|---------------|------|
| 8 | `vibrator` | 바이브레이터 | 음부, 항문 | +10 절정/h (진동) |
| 9 | `dildo` | 딜도 | 음부, 항문 | +3 절정/h |
| 10 | `rotor` | 로터 | 클리토리스 | +5 절정/h (삽입 비차단) |
| 11 | `anal_plug` | 항문 플러그 | 항문 | +3 절정/h |

### 사용 도구

| # | unique_id | 이름 | equip_props | 비고 |
|---|-----------|------|-------------|------|
| 12 | `whip` | 채찍 | `장착:손`, `성인용품:채찍` | 로맨스 액션 전용 |

### 소모성

| # | unique_id | 이름 | category | 효과 |
|---|-----------|------|----------|------|
| 13 | `aphrodisiac` | 미약 | medicine | 6h 성욕 +5/h |
| 14 | `ovulation_inducer` | 배란유도제 | medicine | 24h 가임 100% |
| 15 | `stamina_potion` | 정력제 | medicine | 6h 절정 -5/h, 성욕 +3/h |
| 16 | `lubricant` | 윤활제 | medicine | 즉시 삽입 준비도 100% |
| 17 | `contraceptive_pill` | 피임약 | medicine | 24h 피임 |

---

## 2. 삽입형 메커니즘

### 삽입/제거

```python
# 삽입: 캐릭터 prop에 item_id 기록
morld.set_unit_prop(target_id, f"삽입물:{orifice}", item_id)

# 제거: prop 클리어
morld.clear_prop(target_id, f"삽입물:{orifice}")
```

### 오리피스 목록

```python
INSERTABLE_ORIFICES = ["음부", "항문", "클리토리스"]
```

### 삽입 차단

삽입형 아이템이 있는 오리피스에는 자연 삽입(질삽입/항문삽입 등) 불가.
`romance_core.is_action_blocked_by_state()`에서 체크.

```python
# 예: 음부에 바이브레이터 삽입 상태 → vaginal_insert 차단
orifice = action_def.get("insertion_orifice")
if orifice and morld.get_unit_prop(target_id, f"삽입물:{mapped_orifice}"):
    return True  # 차단
```

### 유틸리티 함수

```python
from assets.items.adult_toys import (
    get_total_climax_rate,    # 삽입물 + 착용형의 총 절정 증가율/h
    get_insertable_info,      # 삽입형 아이템 정보 조회
    INSERTABLE_ORIFICES,      # 삽입 가능 부위 목록
)
```

---

## 3. 결박 시스템 (Restraint)

> `restraint.py` — 결박 상태 판별, 자력 해제, 타인 해제 API

### 결박 Props

| Prop | 설명 | 설정 주체 |
|------|------|----------|
| `결박:상체` | 상체(팔/손) 결박 — 장비 해제 불가, 저항 불가, 이동 가능 | 수갑, 팔 결박구, 로프, 전신 결박구 |
| `결박:하체` | 하체(다리) 결박 — 이동 불가, 장비 해제 가능, 저항 불가 | 다리 결박구, 로프, 전신 결박구 |
| `결박:입` | 입 결박 (말하기/구강/식사 차단) | ball_gag의 equip_props |
| `결박:눈` | 시각 차단 (감각 효과) | blindfold의 equip_props |
| `결박:강도` | 해제 난이도 (30=로프, 40=결박구, 60=수갑, 100=전신) | equip_props |

**상체+하체 동시 결박 = 탈출 불가** (별도 prop 불필요)

### 상태 판별 API

```python
import restraint

restraint.is_restrained(unit_id)        # 상체 또는 하체 결박 여부
restraint.is_upper_restrained(unit_id)  # 상체 결박 여부
restraint.is_lower_restrained(unit_id)  # 하체 결박 여부
restraint.is_fully_restrained(unit_id)  # 상체+하체 동시 (= 탈출 불가)
restraint.can_move(unit_id)             # 이동 가능 (하체 미결박)
restraint.can_use_hands(unit_id)        # 손 사용 가능 (상체 미결박)
restraint.can_escape_romance(unit_id)   # 로맨스 탈출 가능 (전신 아닐 때)
restraint.get_escape_multiplier(unit_id) # 탈출 배율 (0.0/0.3/1.0)
restraint.is_gagged(unit_id)            # 결박:입 여부
restraint.is_blindfolded(unit_id)       # 결박:눈 여부
restraint.get_restraint_strength(unit_id)  # 결박:강도 값
```

### 자력 해제 (NPC)

```python
restraint.attempt_self_escape(unit_id)  # True/False
```

확률 계산:
```
power = 근력×2 + 체격×3 + HP비율×50
difficulty = 결박강도 + 절정×0.3
chance = min(0.7, max(0.05, power / (difficulty + power)))
```

### 타인 해제

```python
restraint.release_unit(unit_id)  # 항상 성공, 모든 결박 prop 해제
```

### 결박 중 행동 제한

| 상태 | 이동 | 장비 해제 | 저항 | 로맨스 탈출 |
|------|------|---------|------|-----------|
| 상체만 (수갑/팔결박구) | O | X | X | 감소 (×0.3) |
| 하체만 (다리결박구) | X | O | X | 감소 (×0.3) |
| 상체+하체 (로프/전신결박구) | X | X | X | **불가** |
| `결박:입` | — | — | — | — (말하기/구강/식사/소리치기 차단) |
| `결박:눈` | — | — | — | — (감각 효과만) |

### NPC AI 연동

**Tier 0 (최고 우선순위)**: 결박 상태 분기
- **행동불능(기절/탈진) 또는 수면 중**: 탈출 시도 없이 해당 상태 job 삽입 → 상태 해제 후 탈출 재개
- **하체 포함** → `_handle_restrained()`: 3-phase (idle→escaping→waiting), 이동 불가
- **상체만** → `_handle_upper_restrained()`: 이동 가능, 배회하며 해제 시도
- 30분마다 자력 해제 시도
- 입 자유 시 소리 발생 (`sound.emit_sound("scream", 80)`)
- **결박 중 복종 소폭 상승**: waiting phase마다 플레이어에 대한 복종 +0.5 (30분당)

**Tier 2 (Reactive)**: 같은 location에 결박된 NPC 발견 → 해제
- 2-phase: detect → releasing (3분)

---

## 4. 절정 상시 관리

> `needs.py`의 `_update_climax()` — 매시간 호출

### 개요

로맨스 세션 밖에서도 성인용품에 의한 절정 게이지(`상태:절정`)를 지속 추적.
로맨스 시작/종료 시 세션 게이지(`climax_gauge`)와 양방향 동기화.

### Prop

| Prop | 범위 | 설명 |
|------|------|------|
| `상태:절정` | 0-100 | 비로맨스 절정 게이지 |

### 매시간 업데이트

```python
def _update_climax(unit_id):
    delta = -3  # 자연 감소
    delta += adult_toys.get_total_climax_rate(unit_id)  # 삽입물 + 착용형
    # 정력제 효과: delta -= 5

    if new_climax >= 100:
        _trigger_passive_climax(unit_id)  # 비로맨스 절정
        new_climax = 0
```

### 비로맨스 절정 (`_trigger_passive_climax`)

- 성욕 -30
- 피로 +5
- 입 자유 시 신음 소리 발생 (`sound.emit_sound("moan", 30)`)

### 세션 동기화

```python
# 세션 시작 (romance.py, npc_initiative.py)
state["stim"]["climax_gauge"] = morld.get_unit_prop(npc_id, "상태:절정") or 0

# 세션 종료
morld.set_unit_prop(npc_id, "상태:절정", final_climax)
```

---

## 5. 약물 타이머

### 타이머 Props

| 약물 | 상태 Prop | 타이머 Prop | 지속 | 효과 |
|------|----------|------------|------|------|
| 미약 | `상태:미약` | `상태:미약남은시간` | 6h | 성욕 +5/h |
| 배란유도제 | `상태:배란유도` | `상태:배란유도남은시간` | 24h | 가임 100% |
| 정력제 | `상태:정력제` | `상태:정력제남은시간` | 6h | 절정 -5/h, 성욕 +3/h |
| 피임약 | `상태:피임` | `상태:피임남은시간` | 24h | 피임 |

### 음식 첨가

소모성 아이템을 음식에 섞을 수 있음. 음식 prop으로 기록:
- `상태:미약첨가` = 1
- `상태:배란유도제첨가` = 1
- `상태:정력제첨가` = 1

**발동 경로**:
- 플레이어 식사: `FoodItem.eat()` (food.py)
- NPC 식사: `_apply_food_drug_effects()` (think/handlers/eat.py)

---

## 6. 로맨스 통합

### 신규 액션 (romance_actions.py)

| ID | 이름 | 시간 | 스태미나 | 비고 |
|----|------|------|---------|------|
| `restrain_partner` | 결박 | 2분 | 2 | 저항 체크, 인벤토리 restraint 필요 |
| `unrestrain_partner` | 결박 해제 | 1분 | 0 | |
| `equip_toy_partner` | 성인용품 장착 | 2분 | 1 | 저항 체크, 인벤토리 adult_toy 필요 |
| `remove_toy_partner` | 성인용품 해제 | 1분 | 0 | |
| `force_feed` | 강제 투여 | 1분 | 1 | 인벤토리 medicine 필요, 입 자유 필요 |
| `use_whip` | 채찍질 | 2분 | 2 | 채찍 장착 필요, 반발+3/복종+2/성욕+2 |

### 행위 차단 로직 (romance_core.py)

`is_action_blocked_by_state(action_def, target_id)`:
- `uses_mouth` + 입 결박 → 차단
- `requires_no_gag` + 입 결박 → 차단
- `insertion_orifice` + 해당 부위 삽입물 존재 → 차단

### 결박 + 강제 모드

결박 상태에서 `romance_mode.check_resistance()`:
- 탈출 시도 불가 (`escape_chance = 0`)
- 항상 futile 판정
- 반발 수치는 계속 증가

### 임시 해부학 (gender.py)

```python
gender.has_anatomy(unit_id, "P")         # 자연 + 임시 해부학 포함
gender.has_natural_anatomy(unit_id, "P") # 자연 해부학만 (사정 체크용)
```

페니스밴드 착용 시 `임시해부학:P` prop → `has_anatomy()` True, `has_natural_anatomy()` False

---

## 7. NPC 자위 연동

> `think/handlers/self_comfort.py`

### 성인용품 사용

`performing` phase에서 `_try_use_toy(agent)`로 인벤토리의 삽입형 성인용품을 자동 선택/사용.

**사용 확률** (욕망 기반):
```
use_chance = (desire - 30) × 0.013 + (arousal - 50) × 0.003
```
- desire 40 → ~30%, desire 100 → ~95%
- 아이템이 없거나 확률 실패 시 성인용품 없이 자위

**선택 로직** (가중 랜덤):
1. 인벤토리 내 삽입형 아이템 수집
2. 각 아이템 가중치 계산: `base_pref × desire_bonus × sensation_bonus`
   - `base_pref`: 캐릭터별 `toy_preferences` dict (0.0~1.0)
   - `desire_bonus`: desire ≥ 80 → ×1.5, ≥ 60 → ×1.2, 그 외 ×1.0
   - `sensation_bonus`: `감각:{category}` prop × 0.01 + 1.0
3. 가중 랜덤으로 최종 선택

**캐릭터별 선호 (`toy_preferences`)**:

| NPC | vibrator | dildo | rotor | anal_plug | 성격 |
|-----|----------|-------|-------|-----------|------|
| 세라 | 0.3 | 0.6 | 0.2 | 0.1 | 실용적, 정적 선호 |
| 밀라 | 0.7 | 0.4 | 0.6 | 0.2 | 민감, 진동 선호 |
| 리나 | 0.6 | 0.3 | 0.5 | 0.3 | 호기심, 골고루 |
| 유키 | 0.2 | 0.5 | 0.3 | 0.1 | 소심, 자극 낮은 것 |
| 엘라 | 0.4 | 0.5 | 0.3 | 0.2 | 균형형 |

**처리 흐름**:
1. 아이템 선택 → 해부학 호환 오리피스 결정 → `삽입물:{orifice}` prop 설정
2. 15분 자위 job 실행
3. `_cleanup_toy(agent)`: 삽입물 prop 해제

### 효과 증가

- 성인용품 사용 시: 성욕 -70 (기본 -50보다 높음)

---

## 8. Describe / Focus 규칙

> `assets/base.py` — `_build_context()` 확장

### Context 키

```python
ctx["restrained"]         # 상체 또는 하체 결박 여부
ctx["upper_restrained"]   # 상체 결박 여부
ctx["lower_restrained"]   # 하체 결박 여부
ctx["gagged"]             # 결박:입 여부
ctx["blindfolded"]        # 결박:눈 여부
ctx["절정"]               # 상태:절정 수치 (0-100)
ctx["삽입물_음부"]        # 삽입물:음부 존재 여부
ctx["삽입물_항문"]        # 삽입물:항문 존재 여부
ctx["삽입물_클리토리스"]  # 삽입물:클리토리스 존재 여부
ctx["노출도"]             # 의상 노출도 (0-100)
ctx["상체노출"]           # 상체 노출 수준 (0=커버, 1=속옷, 2=누드)
ctx["하체노출"]           # 하체 노출 수준 (0=커버, 1=속옷, 2=누드)
ctx["수치심"]             # 노출도 × shame_sensitivity (0-100)
```

### 규칙 예시 (FOCUS_RULES)

```python
_FOCUS_RESTRAINT = [
    # 결박 + 성인용품 복합
    ({"restrained": True, "삽입물_음부": True, "절정": (60, None)},
     "{name}가 결박당한 채 ...에 의해 몸이 떨리고 있다."),
    # 결박 단독
    ({"restrained": True, "gagged": True},
     "{name}가 결박당해 입까지 막힌 채 움직이지 못하고 있다."),
    # 절정 높음
    ({"절정": (80, None)},
     "{name}의 얼굴이 상기되어 참을 수 없는 표정이다."),
    ...
]
```

### 톤 템플릿 반응

10개 아키타입에 상태 반응 + 액션 반응 추가:

**상태 반응 키** (3개):
- `"restrained_idle"` — 결박 상태 묘사/대사
- `"passive_climax"` — 비로맨스 절정 시 반응
- `"toy_equipped"` — 성인용품 장착 상태 반응

**액션 반응 키** (6개 × 2종):
- ACTION_REACTIONS (`:during` 3인칭 묘사): `restrain_partner`, `unrestrain_partner`, `equip_toy_partner`, `remove_toy_partner`, `force_feed`, `use_whip`
- ACTION_LINES (`:start` 1인칭 대사): 위 6개와 동일 키에 `:start` suffix

---

## 9. 성추행 시스템 (Harassment)

> `harassment.py`, `settings.py`, `think/__init__.py` — 순수 Python

전투/비전투 양방향 성추행 시스템. 옷 들추기/찢기 → 신체 노출 → 만지기 → 절정.

### 설정

```python
# settings.py
settings.is_harassment_enabled()   # 성추행 모드 ON/OFF
settings.set_harassment_enabled()  # can:harassment + can:self_expose prop 연동
```

### 액션 체계

| 타입 | 액션 | 효과 | 비전투 시간 | 전투 시간 |
|------|------|------|-----------|----------|
| lift | 상체/하체 옷 들추기 | 임시노출 prop 설정 (지속) | 3분 | 6초 |
| tear | 상체/하체 옷 찢기 | 최외곽 의류 내구도 -5 | 5분 | 8초 |
| grope | 가슴/유두/엉덩이/음부 만지기 | 절정 게이지 상승 (노출 필요) | 5분 | 10초 |

### 임시노출 Props

| Prop | 범위 | 설명 |
|------|------|------|
| `임시노출:상체` | 0-2 | 0=없음, 1=옷 위로 들추기, 2=완전 노출 |
| `임시노출:하체` | 0-2 | 동일 |
| `상태:자발적노출` | 0/1 | NPC 자발적 유혹 여부 (describe 분기용) |

`_calculate_exposure()`에서 `max(실제착의, 임시노출)` 적용.

### 관계 기반 반응 분기

| 모드 | 조건 | 효과 |
|------|------|------|
| welcome | 호감 ≥60 | 성욕 상승 (CASUAL_REACTIONS 재활용) |
| unwanted | 호감 <60 + 반발 <30 | 호감 감소 + 반발 소폭 증가 |
| hostile | 반발 ≥30 | 적대치 대폭 증가 (전투 유발 가능) |

### NPC 옷매무새 복구

think() Tier 4a-pre에서 임시노출 감지 → 1분 "옷매무새 정리" → prop 클리어.
결박 상태(`can_use_hands = False`)면 복구 불가.

### NPC 유혹 (자발적 노출)

- think() Tier 4d `_check_arousal()` 내 `_try_self_exposure()`
- 조건: 성욕 임계 + 호감 ≥60 + 같은 Location + **다른 NPC 있을 때**
- 확률 50%, 쿨다운 1시간, 성욕 -10 (유혹 만족감)
- 단둘일 때는 NPC 주도 로맨스(`_can_seek_player`)가 우선

### NPC → 플레이어 성추행

- think() Tier 4d `_try_harass_player()`
- 조건: 호감 ≥60 + 같은 Location, 쿨다운 2시간
- 랜덤 액션 선택 → `harassment.execute_action()` → action_log 출력

### 비로맨스 절정 + 탈진

`_trigger_passive_climax()`:
- 성욕 -30, 피로 +5
- 입 자유 시 신음 (`sound.emit_sound("moan", 30)`)
- HP 기반 확률적 짧은 탈진 (1시간): `chance = 1.0 - hp_ratio`

### 플레이어 자기 노출

Player 액션 "옷 들추기#" → 상체/하체 선택 → 임시노출 설정.
NPC가 `on_meet_player()`에서 `상태:자발적노출` 감지 → 관계 모드별 반응.

### NPC 간호 행동

think() Tier 2에서 탈진된 캐릭터 발견 → 30분 간호 + HP +10.
아키타입별 간호 대사 (10종).

---

## 10. 파일 구조

```
scenarios/scenario02/python/
├── assets/items/
│   └── adult_toys.py          # 17개 아이템 정의 + 유틸리티
├── harassment.py              # 성추행 시스템 (액션, 관계 분기, 세션 UI)
├── restraint.py               # 결박 상태 API
├── needs.py                   # _update_climax() 절정 상시 관리 + 비로맨스 절정/탈진
├── gender.py                  # has_natural_anatomy() 임시 해부학
├── romance_actions.py         # 신규 6개 액션 정의
├── romance_core.py            # is_action_blocked_by_state()
├── romance_mode.py            # 결박 시 탈출 불가
├── think/
│   ├── __init__.py            # Tier 0 결박 + Tier 2 구출
│   └── handlers/
│       ├── self_comfort.py    # NPC 자위 성인용품 연동
│       └── eat.py             # NPC 식사 약물 첨가 체크
└── tone_templates/            # 10개 아키타입 × 3개 상태 반응
```
