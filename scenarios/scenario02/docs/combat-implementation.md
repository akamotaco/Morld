# 전투 시스템 구현 명세

> **이 문서만으로 구현이 가능한 수준의 상세 명세서입니다.**
> 기존 battle.md의 설계를 기반으로, 현재 코드베이스와의 충돌을 해결하고 구현 가능한 형태로 재구성했습니다.

---

## 목차

- **Part A: 기반** — 1. 충돌 해결 / 2. combat.py 코어 / 3. 적대도
- **Part B: 플레이어** — 4. 전투 액션 / 5. 달리기
- **Part C: 장비/무기** — 6. prop 마이그레이션 / 7. 장비 인스턴스 / 8. 원거리+탄약 / 9. 방패 / 10. 밸런스
- **Part D: 몬스터** — 11. 몬스터 클래스+드롭 / 12. 스폰 / 13. 패트롤 / 14. 사망+루팅
- **Part E: NPC AI** — 15. think Tier 2 / 16. NPC 스탯 / 17. on_meet 분기
- **Part F: 부가** — 18. 디버프 / 19. 엄폐+지형 / 20. 간호+HP / 20.3. 내구도
- **Part G: 콘텐츠** — 21. 경찰서+광산
- **Part H: 통합** — 22. C# 연동 / 23. 파일 목록 / 24. 구현 순서 / 25. 테스트 / 26. 파티(Phase 2)
- **부록** — morld API 목록

---

# Part A: 기반

## 1. 코드베이스 충돌 해결

> **구현 완료**

### 1.1 HP Prop 통일

| battle.md 설계 | 현재 코드 (survival.py:78) | **결정** |
|----------------|--------------------------|---------|
| `전투:체력`, `전투:최대체력` | `생존:체력`, `생존:최대체력` | **`생존:체력` 사용** |

이유: survival.py의 기절/탈진/포만감 시스템이 `생존:체력`에 깊이 의존. 이중 HP는 혼란만 초래.

### 1.2 스탯 조회 API

| battle.md 설계 | 현재 코드 | **결정** |
|----------------|----------|---------|
| `morld.get_actual_prop(unit_id, key)` | **미존재** (singular 없음) | `get_combat_stat()` 헬퍼 생성 |

`morld.get_actual_props(unit_id)` (plural)는 존재 (ui.py:774,947에서 사용). 기본 props + 장비 equip_props를 합산한 dict 반환. `get_combat_stat()`은 이를 래핑.

### 1.3 X 좌표 키

| battle.md 설계 | 현재 코드 (script_system_morld_api.cs:549) | **결정** |
|----------------|-------------------------------------------|---------|
| `position_x` | `get_unit_info(unit_id)["x"]` | **`"x"` 사용** |

C# 코드 확인: `result.SetItem(new PyString("x"), new PyFloat(unit.PositionX))`

### 1.4 무기 equip_props 통일

현재 상태 (불일치):

| 파일 | 아이템 | 현재 키 |
|------|--------|---------|
| equipment.py:50 | OldKnife | `{"공격": 2, "사냥": 1, "장착:손": 1}` |
| equipment.py:70 | RusticDagger | `{"공격": 3, "사냥": 2, "장착:손": 1}` |
| equipment.py:379 | WoodenSword | `{"공격": 3, "장착:손": 1}` |
| tools.py:68 | KitchenKnife | `{"공격력": 2, "장착:손": 1}` |
| tools.py:133 | Axe | `{"can:chop": 1, "공격력": 3, "장착:손": 1, "날붙이": 1}` |
| tools.py:180 | HuntingBow | `{"공격력": 5, "사거리": 3, "장착:손": 1}` |

**마이그레이션 목표:**

| 현재 키 | 목표 키 | 비고 |
|---------|---------|------|
| `공격` | `전투:공격력` | equipment.py 3개 아이템 |
| `공격력` | `전투:공격력` | tools.py 3개 아이템 |
| `사거리: 3` | `전투:사거리: 300` | HuntingBow — px 단위로 변환 |
| `사냥` | `사냥` | 유지 (전투 외 시스템) |
| `날붙이` | `날붙이` | 유지 (전투 외 시스템) |

### 1.5 전투 스탯 vs 기존 캐릭터 스탯

| 기존 스탯 | 전투 스탯 | 관계 |
|----------|----------|------|
| `근력` | `전투:공격력` | **독립** — 근력은 기존 시스템 유지 |
| `체력` | `생존:체력` (HP) | **독립** — 체력(스태미나)과 HP는 다른 개념 |
| `체격` | `전투:방어력` | **독립** — 체격은 기존 시스템 유지 |

**원칙:** 기존 캐릭터 속성(`근력`, `체력`, `체격`)을 전투 스탯 계산에 사용하지 않음. `전투:` prefix 스탯은 완전 독립적.

---

## 2. combat.py — 전투 코어 모듈

> **구현 완료** — `scenarios/scenario02/python/combat.py`

**파일:** `scenarios/scenario02/python/combat.py` (신규)

### 2.1 상수

```python
import random
import morld

# ── 전투 스탯 기본값 ──
DEFAULT_STATS = {
    "전투:공격력": 1,          # 맨손
    "전투:방어력": 0,
    "전투:명중": 80,           # %
    "전투:회피": 5,            # %
    "전투:치명타": 5,          # %
    "전투:사거리": 50,         # px (맨손)
    "전투:공격속도": 1.0,      # 배율
}

# ── 데미지 공식 ──
CRIT_MULTIPLIER = 1.5
DAMAGE_VARIANCE = 0.10        # ±10%
MIN_DAMAGE = 1

# ── 명중률 범위 ──
HIT_CHANCE_MIN = 5
HIT_CHANCE_MAX = 95

# ── 공격 시간 (ms) ──
MELEE_ATTACK_DURATION = 6_000
RANGED_ATTACK_DURATION = 10_000

# ── 적대도 ──
HOSTILITY_NEUTRAL = 29
HOSTILITY_ALERT = 49
HOSTILITY_HOSTILE = 50
HOSTILITY_ATTACK_ON_SIGHT = 80
HOSTILITY_DECAY_PER_HOUR = 2

HOSTILITY_ON_ATTACK = 30
HOSTILITY_ON_FAINT = 50
HOSTILITY_ON_STEAL_SUCCESS = 20
HOSTILITY_ON_STEAL_FAIL = 40
HOSTILITY_ON_NURSING = -20

AFFECTION_ON_ATTACK = -10
AFFECTION_ON_FAINT = -25
AFFECTION_ON_STEAL_FAIL = -20
AFFECTION_ON_NURSING = 10

# ── 몬스터 적대 유형 ──
HOSTILITY_TYPE_MONSTER = "monster"
HOSTILITY_TYPE_AGGRESSIVE = "aggressive"
HOSTILITY_TYPE_TERRITORIAL = "territorial"
HOSTILITY_TYPE_PASSIVE = "passive"
HOSTILITY_TYPE_TIMID = "timid"

DEFAULT_AGGRO_RANGE = 100
DEFAULT_TERRITORY_RANGE = 50

# ── 디버프 ──
BLEEDING_DAMAGE_PER_HOUR = 3
BLEEDING_CHANCE_ON_CRIT = 50
BLEEDING_DURATION_HOURS = 3
SLOW_DURATION_HOURS = 2
SLOW_SPEED_PERCENT = 50

# ── 탄약 ──
RELOAD_DURATION = 5_000
JAM_BASE_CHANCE = 3

# ── 은신 기습 ──
STEALTH_CRIT_BONUS = 30
```

### 2.2 스탯 조회

```python
def get_combat_stat(unit_id: int, stat_name: str):
    """전투 스탯 조회 (base prop + equip_props 합산)

    구현:
        all_props = morld.get_actual_props(unit_id)
        if all_props and stat_name in all_props:
            return all_props[stat_name]
        return DEFAULT_STATS.get(stat_name, 0)
    """


def get_weapon_equip_props(unit_id: int) -> dict:
    """장착 무기의 equip_props만 추출

    대안: 장착된 무기 item_id를 알 때는
    morld.get_item_info(item_id)["equip_props"] 직접 사용 가능.
    """
```

### 2.3 거리 계산

```python
def get_distance(unit_a: int, unit_b: int) -> float:
    """두 유닛 간 거리 (px). 다른 Location → float('inf')."""

def is_in_range(attacker_id: int, target_id: int) -> bool:
    """공격 사거리 내 여부"""
```

### 2.4 명중/데미지

```python
def calculate_hit_chance(attacker_id, target_id) -> int:
    """명중률 = attacker_명중 - target_회피, clamp(5, 95)"""

def roll_hit(attacker_id, target_id) -> tuple:
    """Returns: (hit: bool, crit: bool)"""

def calculate_damage(attacker_id, target_id, is_crit=False) -> int:
    """공식: max(1, atk - def//2) × variance × crit_mult"""
```

### 2.5 데미지 적용

```python
def apply_damage(target_id: int, damage: int, attacker_id: int = None):
    """survival.add_health(target, -damage) → HP 0이면 기절 명시 호출

    주의: survival.add_health()는 기절을 자동 트리거하지 않음.
    - NPC 기절: survival._enter_faint(npc_id)
    - 플레이어 기절: survival._enter_player_faint()
    """
```

### 2.6 공격 실행

```python
def execute_attack(attacker_id: int, target_id: int) -> dict:
    """단일 공격 실행

    Returns: {"hit", "crit", "damage", "target_hp", "target_fainted", "message"}

    흐름:
    1. 사거리 체크
    2. 원거리: 탄약 체크 → 잼 판정 (화기만)
    3. roll_hit() → calculate_damage() → apply_damage()
    4. 치명타+출혈: BLEEDING_CHANCE_ON_CRIT% → apply_bleeding()
    5. 내구도 감소: degrade_durability(weapon_item_id)
    6. 소리: sound.emit_sound(attacker_id, "combat")
       화기: sound.emit_sound(attacker_id, "gunshot")
       (sound.py:20 SOUND_INTENSITIES 키 — 영문 사용)
    7. 원거리: 현재탄약 -1
    """


def check_npc_combat_join(location_id: int) -> list:
    """같은 Location에서 전투에 합류할 NPC 리스트 반환

    1. 파티 멤버: 호감도 체크 생략, combat_join_in_party만 확인
       → party-implementation.md Section 13에서 확장
    2. 비파티 NPC: BATTLE_BEHAVIOR.join_combat + join_threshold 체크

    Returns: [unit_id, ...]
    """


def can_fight(unit_id: int) -> bool:
    """전투 가능 상태 확인 (HP > 0, 기절 아님, 사망 아님)"""
```

### 2.7 적대도 API

```python
def get_hostility(unit_id, target_name) -> int
def set_hostility(unit_id, target_name, value)    # 0-100 clamp
def modify_hostility(unit_id, target_name, delta)
def is_hostile_to(unit_id, target_id) -> bool
def clear_hostility(unit_id, target_name)
def get_hostility_level(unit_id, target_name) -> str  # "neutral"/"alert"/"hostile"/"attack_on_sight"
```

### 2.8 적대모드 (플레이어 전용)

```python
_hostile_mode = False

def is_hostile_mode() -> bool
def set_hostile_mode(enabled: bool)    # can:attack, can:steal 연동
```

### 2.9 전투 태세 표시 (describe/focus)

> **파일:** `assets/base.py` (`_get_combat_stance_info`, `get_describe_text`, `get_focus_text`)

플레이어에 대해 적대적인 유닛의 전투 태세를 describe/focus 텍스트에 자동 표시.

- **선공형** (`combat_style: "aggressive"`): `[color=red](전투 태세)[/color]` — 감지 즉시 공격
- **반격형** (그 외): `[color=yellow](평화 태세)[/color]` — 공격받아야 반격

판정 순서:
1. 플레이어 자신 → 미표시
2. 사망(HP ≤ 0) → 미표시
3. 세력 적대 OR 개인 적대도 ≥ HOSTILITY_HOSTILE → 표시
4. 비우호 세력(중립/적대) + 플레이어 전투 태세(`can:attack=1`) → 반응형 표시
5. `BATTLE_BEHAVIOR.combat_style == "aggressive"` → 전투 태세, 그 외 → 평화 태세

describe: 텍스트 끝에 `(전투 태세)` / `(평화 태세)` 태그 부착
focus: 텍스트 선두에 `전투 태세 — 선공형` / `평화 태세 — 반격형` 행 추가

**적대 행동 빨간색 표시:** 공격/소매치기/숨통 끊기/성추행 등 적대 행동은 focus 액션 목록에서 `[color=red]` 빨간색으로 표시 (`action_system.cs`)

### 2.10 디버프 API

```python
def apply_bleeding(unit_id, duration_hours=3)
def cure_bleeding(unit_id)
def apply_slow(unit_id, speed_percent=50, duration_hours=2)
    # 이동:부상 prop (Unit prop — actualProps에서 읽힘)
```

### 2.11 시간 구독 + 리셋

```python
def _on_time_elapsed(millis):
    """매 1시간: 적대도 감소 + 출혈 데미지 + 둔화 회복"""

def reset():
    """챕터 전환: _hostile_mode = False"""
```

---

## 3. 적대도 vs 반발 — 완전 분리

> **구현 완료**

| 구분 | 적대도 (`관계:{name}:적대`) | 반발 (`관계:{name}:반발`) |
|------|---------------------------|-------------------------|
| **용도** | 전투 판정 (공격 여부) | 로맨스 저항 (행위 거부) |
| **범위** | 0-100 | 0-100 |
| **증가** | 공격, 절도, 위협 | 강제 행위, 원치 않는 스킨십 |
| **감소** | -2/h, 간호 | 시간, 긍정 상호작용 |
| **임계** | 50+ 적대, 80+ 즉시공격 | romance_core.py 관리 |

**변화 규칙:**

| 이벤트 | 적대도 | 호감 |
|--------|--------|------|
| 플레이어 → NPC 공격 | +30 | -10 |
| NPC 기절시킴 | +50 | -25 |
| 절도 성공 | +20 | -15 |
| 절도 실패 | +40 | -20 |
| 간호 | -20 | +10 |
| 시간 경과 (비전투) | -2/h | — |

---

# Part B: 플레이어 전투

## 4. 플레이어 전투 액션

> **구현 완료** — `assets/base.py: attack(), steal(), _add_combat_actions()`

### 4.1 액션 시스템 구조

NPC를 포커스하면 NPC의 `actions` 리스트가 표시됨. `call:메서드명:표시명` 형식:
- **메서드 호출 대상**: 포커스된 NPC 인스턴스 (self = NPC)
- **허용 여부**: 플레이어의 `can:메서드명` prop으로 판정
- **`#` 마커**: can: 미충족 시 숨김

### 4.2 Character 기본 actions에 추가

**파일:** `assets/base.py` — Character 클래스

```python
"call:attack:공격#",          # can:attack 필요, 없으면 숨김
"call:steal:소매치기#",       # can:steal 필요, 없으면 숨김
```

### 4.3 Character.attack()

**파일:** `assets/base.py`

```python
def attack(self):
    """플레이어의 공격을 받는 핸들러 (self = 대상)"""
    import combat

    player_id = morld.get_player_id()
    player_name = morld.get_unit_info(player_id)["name"]

    if not combat.is_in_range(player_id, self.instance_id):
        morld.add_action_log("사거리 밖이다.")
        return

    result = combat.execute_attack(player_id, self.instance_id)
    morld.add_action_log(result["message"])

    # 적대도/호감 변화 (몬스터 제외)
    hostility_type = morld.get_unit_prop(self.instance_id, "전투:적대유형")
    if hostility_type != combat.HOSTILITY_TYPE_MONSTER:
        combat.modify_hostility(self.instance_id, player_name, combat.HOSTILITY_ON_ATTACK)
        affection_key = f"관계:{player_name}:호감"
        morld.modify_prop(self.instance_id, affection_key, combat.AFFECTION_ON_ATTACK)
        if result["target_fainted"]:
            combat.modify_hostility(self.instance_id, player_name, combat.HOSTILITY_ON_FAINT)
            morld.modify_prop(self.instance_id, affection_key, combat.AFFECTION_ON_FAINT)

    # 공격 시간 경과
    weapon_range = combat.get_combat_stat(player_id, "전투:사거리")
    is_ranged = weapon_range > 100
    base_dur = combat.RANGED_ATTACK_DURATION if is_ranged else combat.MELEE_ATTACK_DURATION
    attack_speed = combat.get_combat_stat(player_id, "전투:공격속도")
    morld.advance_time_des(int(base_dur * attack_speed))
```

### 4.4 Character.steal()

```python
def steal(self):
    """소매치기 시도 (self = 대상)

    성공률 = 손재주 × 3 (%), 기절/수면 +30%
    성공 → 인벤토리 랜덤 1개 획득
    실패 → 적대도 +40, 호감 -20
    5초 경과
    """
```

### 4.5 player.py 수정

```python
# props에 추가:
"전투:공격력": 3,
"전투:방어력": 1,
"전투:명중": 80,
"전투:회피": 5,
"전투:치명타": 5,
"전투:사거리": 50,
"전투:공격속도": 1.0,
"can:attack": 0,       # 적대모드 ON 시 활성화
"can:steal": 0,
"이동:달리기": 0,
```

### 4.6 settings.py — 적대모드 토글

```python
# render_settings_ui() 추가:
import combat
hostile_on = combat.is_hostile_mode()
hostile_status = "[color=red]ON[/color]" if hostile_on else "[color=gray]OFF[/color]"
lines.append(f"[url=@proc:toggle_hostile]적대 모드[/url]: {hostile_status}")

# proc() 핸들러:
if action == "toggle_hostile":
    import combat
    combat.set_hostile_mode(not combat.is_hostile_mode())
    return _render()
```

---

## 5. 달리기 시스템

> **구현 완료** — `settings.py`, `needs.py`, C# `Unit.cs`

### 5.1 개요

토글형 달리기. 활성 시 이동속도 **1.5배**, 피로 증가율 **2배**.

### 5.2 Props

```python
"이동:달리기": 0   # 0=보통, 1=달리기 (Unit prop, actualProps에서 읽힘)
```

### 5.3 C# 연동

**파일:** `scripts/morld/unit/Unit.cs:423-443` — `GetMovementSpeed()`

congestion 체크 후, `return` 전에 추가:

```csharp
// 달리기 가속 (Unit prop — actualProps에서 읽음)
var sprintMode = actualProps.GetProp("이동:달리기");
if (sprintMode > 0)
    result = result * 150 / 100;
```

> `이동:혼잡`은 `TraversalContext`(Location prop), `이동:달리기`는 `actualProps`(Unit prop). 출처 다름.

### 5.4 settings.py 토글

```python
# render_settings_ui():
sprint_on = morld.get_unit_prop(morld.get_player_id(), "이동:달리기") or 0
sprint_status = "[color=yellow]ON[/color]" if sprint_on else "[color=gray]OFF[/color]"
lines.append(f"[url=@proc:toggle_sprint]달리기[/url]: {sprint_status}")

# proc():
if action == "toggle_sprint":
    player_id = morld.get_player_id()
    current = morld.get_unit_prop(player_id, "이동:달리기") or 0
    if not current:
        fatigue = morld.get_unit_prop(player_id, "욕구:피로") or 0
        if fatigue >= 90:
            morld.add_action_log("너무 피곤해서 달릴 수 없다.")
            return _render()
    morld.set_unit_prop(player_id, "이동:달리기", 0 if current else 1)
    return _render()
```

### 5.5 피로 연동 (needs.py)

```python
# 달리기 중 피로 증가율 2배 (기존 4/h → 8/h)
# 피로 ≥ 90 → 달리기 자동 해제
```

### 5.6 전투 연동

- 도주: 달리기 ON + Gate 방향 이동
- NPC: BATTLE_BEHAVIOR에 `can_sprint` 옵션, `_handle_combat()`에서 토글

---

# Part C: 장비/무기

## 6. 무기 prop 마이그레이션

> **구현 완료**

### 6.1 equipment.py

| 라인 | 아이템 | 변경 전 → 변경 후 |
|------|--------|-------------------|
| ~50 | OldKnife | `"공격": 2` → `"전투:공격력": 2` |
| ~70 | RusticDagger | `"공격": 3` → `"전투:공격력": 3, "전투:사거리": 60` |
| ~379 | WoodenSword | `"공격": 3` → `"전투:공격력": 3, "전투:사거리": 70` |

### 6.2 tools.py

| 라인 | 아이템 | 변경 전 → 변경 후 |
|------|--------|-------------------|
| ~68 | KitchenKnife | `"공격력": 2` → `"전투:공격력": 2` |
| ~133 | Axe | `"공격력": 3` → `"전투:공격력": 3` |
| ~180 | HuntingBow | `"공격력": 5, "사거리": 3` → `"전투:공격력": 5, "전투:사거리": 300, "전투:탄약": "arrow", "전투:장탄수": 1, "can:reload": 1` |

### 6.3 참조 안전성

`공격` / `공격력` prop을 참조하는 코드가 equipment.py, tools.py 외에 발견되지 않음.

---

## 7. 장비 인스턴스 시스템

> **구현 완료**

### 7.1 소모품 vs 장비

| | 소모품 (기존) | 장비 (신규) |
|---|---|---|
| **ID** | 싱글톤 `get_or_create_item_id()` | 개별 `morld.create_id()` |
| **수량** | 스택 (count) | 1칸 = 1개 |
| **속성** | 공유 | 개별 props (내구도, 강화) |

### 7.2 생성 방식

```python
# 소모품:
item_id = get_or_create_item_id("apple")
morld.give_item(owner, item_id, count=3)

# 장비:
item_id = morld.create_id()  # C#이 인수 무시, 순차 ID 생성
weapon = Revolver()
weapon.instantiate_as_item(item_id)
morld.give_item(owner, item_id, count=1)
morld.set_unit_prop(item_id, "내구도", 100)
morld.set_unit_prop(item_id, "내구도:최대", 100)
morld.set_unit_prop(item_id, "강화", 0)
```

### 7.3 내구도

```python
"내구도"       # 현재 (0~최대)
"내구도:최대"  # 최대값

# 감소: 공격 -1, 발사 -1, 방어 -1, 채광 -1
# 파손 (0): 공격력 50% 감소, "상태:파손" prop, 수리 가능

def degrade_durability(item_id, amount=1):
    current = morld.get_unit_prop(item_id, "내구도") or 0
    new_val = max(0, current - amount)
    morld.set_unit_prop(item_id, "내구도", new_val)
    if new_val == 0:
        morld.set_unit_prop(item_id, "상태:파손", 1)
```

### 7.4 강화 (기본)

```python
"강화"    # 단계 (0, +1, +2, ...)
# 효과: 전투:공격력 등 +1/단계
# 재료: 광석 기반 (Section 21)
```

### 7.5 인벤토리

장비 = 고유 item_id → 1칸. 소모품 = 스택. 슬롯 제한 = base(5) + 근력×1.0.

---

## 8. 원거리 무기 + 탄약

> **구현 완료** — `weapons.py`, `ammo.py`, `combat.py: reload_weapon()`

### 8.1 분류

| 유형 | 사거리(px) | 탄약 | 예시 |
|------|-----------|------|------|
| 맨손 | 50 | 없음 | 주먹 |
| 근접 | 60-80 | 없음 | 단검, 삼단봉, 도끼, 검 |
| 원거리 | 200-300 | 필요 | 활(화살), 리볼버(탄약) |

### 8.2 탄약 (소모품 — 스택)

```python
class Arrow(Item):
    unique_id = "arrow"
    name = "화살"
    category = "ammo"

class PistolAmmo(Item):
    unique_id = "pistol_ammo"
    name = "권총탄"
    category = "ammo"
```

### 8.3 원거리 무기 equip_props

```python
# HuntingBow
equip_props = {
    "전투:공격력": 5, "전투:사거리": 300,
    "전투:탄약": "arrow", "전투:장탄수": 1,
    "can:reload": 1, "장착:손": 1,
}

# Revolver
equip_props = {
    "전투:공격력": 12, "전투:사거리": 200,
    "전투:명중": -10, "전투:치명타": 10,
    "전투:탄약": "pistol_ammo", "전투:장탄수": 6,
    "can:reload": 1, "장착:손": 1,
}
```

### 8.4 재장전

```python
def reload_weapon(player_id) -> bool:
    """재장전: 장비 equip_props에서 탄약타입/장탄수 조회 → 인벤토리 소모 → 현재탄약 설정

    장비 equip_props 접근:
    - morld.get_actual_props(player_id)에서 "전투:탄약", "전투:장탄수" 조회
    - 또는 장착 무기 item_id → morld.get_item_info(item_id)["equip_props"]

    현재탄약: 플레이어 prop "전투:현재탄약"으로 관리
    """
```

### 8.5 탄약 소모 (execute_attack 내부)

```
원거리 무기 → 전투:현재탄약 > 0 확인 → 공격 → -1
탄약 0 → "탄약이 없다!" 공격 불가
```

### 8.6 잼 (화기 전용)

```
발사 시: jam_chance = JAM_BASE_CHANCE + max(0, (50 - durability) // 10)
잼 → 공격 실패 + "상태:잼" prop → 재장전으로 해제
활은 잼 없음 (화기만)
```

### 8.7 재장전 액션

```python
# player.py actions: "call:reload:재장전#" (can:reload)
# → 잼 해제 + 탄약 장전 + RELOAD_DURATION 경과
```

---

## 9. 방패

> **Phase 1 구현 완료** — `shields.py` (Phase 2 블록은 미래)

### 9.1 Phase 1: 방어 장비

```python
class WoodenShield(Item):
    unique_id = "wooden_shield"
    name = "나무 방패"
    category = "weapon"
    equip_props = {"전투:방어력": 3, "전투:회피": -5, "장착:손": 1}

class IronShield(Item):
    unique_id = "iron_shield"
    name = "철제 방패"
    category = "weapon"
    equip_props = {"전투:방어력": 5, "전투:회피": -10, "장착:손": 1}
```

### 9.2 한손+방패 vs 양손무기

| 조합 | 공격력 | 방어력+ | 장착:손 |
|------|--------|--------|---------|
| 단검 + 나무방패 | 3 | +3 | 2 |
| 철검 + 철방패 | 7 | +5 | 2 |
| 양손도끼 | 6 | +0 | 2 |
| 리볼버 + 방패 | 12 | +3~5 | 2 |

### 9.3 Phase 2: 블록 (미래)

`전투:블록확률` → 피격 시 판정 → 성공 시 데미지 50% 감소 + 방패 내구도 -1.

---

## 10. 무기 밸런스

### 10.1 DPS 비교

| 무기 | 공격력 | 사거리 | 공속(ms) | DPS | 특수 |
|------|--------|--------|---------|-----|------|
| 맨손 | 1 | 50 | 3000 | 0.33 | 항상 사용 |
| 낡은 칼 | 2 | 50 | 4000 | 0.50 | 초기 |
| 부엌칼 | 2 | 50 | 4000 | 0.50 | 요리 겸용 |
| 단검 | 3 | 60 | 4000 | 0.75 | 사냥 겸용 |
| 삼단봉 | 5 | 60 | 5000 | 1.00 | 명중+10 |
| 도끼 | 3 | 70 | 6000 | 0.50 | 벌목 겸용 |
| 곡괭이 | 4 | 60 | 6000 | 0.67 | 채광 겸용 |
| 목검 | 3 | 70 | 5000 | 0.60 | |
| 구리검 | 5 | 70 | 5000 | 1.00 | 구리광석 제작 |
| 철검 | 7 | 80 | 5000 | 1.40 | 철광석 제작 |
| 활 | 5 | 300 | 10000 | 0.50 | 화살, 조용 |
| 리볼버 | 12 | 200 | 8000 | 1.50 | 탄약 희소, 잼, 소음 |

### 10.2 상황별

| 상황 | 근접 | 원거리 |
|------|------|--------|
| 좁은 실내 (L≤200) | 유리 (DPS) | 불리 (거리 유지 불가) |
| 넓은 야외 (L≥600) | 불리 (접근) | 유리 (일방 사격) |
| 보스전 | 유리 (DPS) | 불리 (좁은 방) |
| 다수전 | 불리 (1:1) | 유리 (안전 각개격파) |

### 10.3 밸런스 원칙

- 근접 = 고DPS + 위험 + 무한, 원거리 = 안전 + 저DPS + 소모
- 화살 = 제작 가능(지속적), 총알 = 경찰서 한정(희소)
- 총기 소음 → `sound.emit_sound("gunshot")` → 몬스터 유인
- 달리기로 근접의 접근 시간 단축, 피로 소모로 균형

---

# Part D: 몬스터

## 11. 몬스터 클래스 + 드롭/수확

> **구현 완료** — `assets/characters/monster.py`

### 11.1 Monster 기본 클래스

**파일:** `scenarios/scenario02/python/assets/characters/monster.py` (신규)

```python
from assets.base import Character


class Monster(Character):
    """몬스터 기본 클래스 — Character 서브클래스"""
    type = "character"

    props = {
        "전투:적대유형": "monster",
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

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 60,
        "retreat_threshold": 0.2,
    }

    # 포커스 시 공격만 가능 (대화/스킨십 불가)
    actions = [
        "call:attack:공격#",
    ]

    # ── 인벤토리 드롭 테이블 ──
    # 스폰 시 인벤토리에 아이템 생성 → 사망 후 루팅으로 획득
    DROP_TABLE = []
    # 형식: [{"item": "unique_id", "chance": 0.0~1.0, "count": int or (min,max), "equipment": False}]

    # ── Prop 수확 테이블 ──
    # 시체에서 도구로 수확하는 소재
    HARVEST_TABLE = {}
    # 형식: {"소재:키": {"item": "unique_id", "name": "표시명", "tool_prop": "날붙이", "time_ms": 10000}}
```

### 11.2 드롭 테이블 (인벤토리 기반)

몬스터 스폰 시 `_populate_inventory()`로 DROP_TABLE 평가 → 인벤토리에 아이템 생성.

```python
def _populate_inventory(self):
    """스폰 시 드롭 테이블 기반 인벤토리 생성"""
    import random
    from assets.registry import get_or_create_item_id

    for entry in self.DROP_TABLE:
        if random.random() > entry["chance"]:
            continue
        count = entry["count"]
        if isinstance(count, tuple):
            count = random.randint(count[0], count[1])

        if entry.get("equipment"):
            # 장비: 개별 ID 생성
            for _ in range(count):
                item_id = morld.create_id()  # C#이 인수 무시, 순차 ID 생성
                # asset class에서 instantiate_as_item
                # ... 장비 인스턴스 생성 로직 ...
                morld.give_item(self.instance_id, item_id, 1)
                morld.set_unit_prop(item_id, "내구도", 50)  # 중고 상태
                morld.set_unit_prop(item_id, "내구도:최대", 100)
        else:
            # 소모품: 싱글톤 ID
            item_id = get_or_create_item_id(entry["item"])
            morld.give_item(self.instance_id, item_id, count)
```

### 11.3 수확 테이블 (Prop 기반)

시체에서만 얻을 수 있는 소재류. 도구(날붙이 등) 필요. 포커스 후 "수확" 액션.

```python
# instantiate 시 props에 소재 수량 등록:
class Wolf(Monster):
    props = {
        **Monster.props,
        "소재:가죽": 2,     # 수확 가능 횟수
        "소재:이빨": 1,
    }

    HARVEST_TABLE = {
        "소재:가죽": {
            "item": "wolf_pelt",         # 생성할 아이템 unique_id
            "name": "늑대 가죽",          # 액션 표시명
            "tool_prop": "날붙이",        # 필요 equip_prop
            "time_ms": 10_000,           # 수확 소요 시간
        },
        "소재:이빨": {
            "item": "wolf_fang",
            "name": "늑대 이빨",
            "tool_prop": "날붙이",
            "time_ms": 5_000,
        },
    }
```

**수확 메서드 (Character.harvest):**

```python
def harvest(self):
    """시체에서 소재 수확 (첫 번째 수확 가능한 소재 처리)"""
    import combat
    from assets.registry import get_or_create_item_id

    player_id = morld.get_player_id()
    player_props = morld.get_actual_props(player_id)

    for prop_key, info in self.HARVEST_TABLE.items():
        amount = morld.get_unit_prop(self.instance_id, prop_key) or 0
        if amount <= 0:
            continue
        # 도구 체크
        if player_props.get(info["tool_prop"], 0) <= 0:
            morld.add_action_log(f"{info['tool_prop']} 도구가 필요하다.")
            return
        # 수확
        item_id = get_or_create_item_id(info["item"])
        morld.give_item(player_id, item_id, 1)
        morld.set_unit_prop(self.instance_id, prop_key, amount - 1)
        morld.add_action_log(f"{info['name']}을(를) 수확했다. (남은: {amount - 1})")
        morld.advance_time_des(info.get("time_ms", 10_000))
        return

    morld.add_action_log("더 이상 수확할 것이 없다.")
```

### 11.4 구체 몬스터 클래스 (구현 완료)

```python
class Bat(Monster):
    """박쥐 — 약한 몬스터, 광산 1층"""
    unique_id = "bat"
    name = "박쥐"
    props = {
        **Monster.props,
        "생존:체력": 15, "생존:최대체력": 15,
        "전투:공격력": 3, "전투:방어력": 1,
        "전투:명중": 65, "전투:회피": 25, "전투:치명타": 5,
        "전투:사거리": 50, "전투:감지거리": 80,
    }
    BATTLE_BEHAVIOR = {
        "combat_style": "evasive", "target_priority": "nearest",
        "preferred_range": 50, "retreat_threshold": 0.3,
    }
    DROP_TABLE = [{"item": "meat", "chance": 0.5, "count": 1}]


class Spider(Monster):
    """거미 — 중간 몬스터, 광산 2층/깊은 갱도"""
    unique_id = "spider"
    name = "거미"
    props = {
        **Monster.props,
        "생존:체력": 50, "생존:최대체력": 50,
        "전투:공격력": 6, "전투:방어력": 4,
        "전투:명중": 75, "전투:회피": 10, "전투:치명타": 8,
        "전투:사거리": 70, "전투:감지거리": 100,
        "전투:거미줄공격": 25,   # 명중 시 25% 거미줄 결박
        "소재:독낭": 1, "소재:거미줄": 2,
    }
    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive", "target_priority": "nearest",
        "preferred_range": 70, "retreat_threshold": 0.15,
    }
    HARVEST_TABLE = {
        "소재:독낭": {"item": "spider_venom", "name": "거미독", "tool_prop": "날붙이", "time_ms": 8_000},
        "소재:거미줄": {"item": "spider_silk", "name": "거미줄", "tool_prop": None, "time_ms": 3_000},
    }


class TrainingDummy(Character):
    """훈련용 허수아비 — 반격 없음, HP 999"""
    unique_id = "training_dummy"
    name = "허수아비"
    type = "character"
    props = {"생존:체력": 999, "생존:최대체력": 999, "전투:방어력": 0, "전투:회피": 0}
    actions = ["call:attack:공격#"]
    # BATTLE_BEHAVIOR 없음 → think에서 전투 안 함
```

### 11.5 전투 대사 시스템 (구현 완료)

> **파일:** `combat.py` (`_emit_combat_line`), `assets/characters/monster.py` (`COMBAT_LINES`)

몬스터별 `COMBAT_LINES` dict + `combat.py`의 `_emit_combat_line()` 함수로 전투 중 대사 자동 출력.

```python
# combat.py
def _emit_combat_line(unit_id, line_type):
    """전투 대사 출력 (COMBAT_LINES 보유 캐릭터만)"""
    from assets.characters import get_instance
    char = get_instance(unit_id)
    if not char:
        return
    combat_lines = getattr(char, 'COMBAT_LINES', None)
    if not combat_lines:
        return
    lines = combat_lines.get(line_type, [])
    if lines:
        import random as _rnd
        morld.add_action_log(_rnd.choice(lines))
```

**호출 위치:**

| 시점 | 위치 | line_type |
|------|------|-----------|
| 적 첫 발견 | `think/__init__.py` `_check_combat_threat()` | `"discover"` |
| 공격 적중 | `combat.py` `execute_attack()` | `"attack"` |
| 피격 | `combat.py` `execute_attack()` | `"hit"` |
| HP ≤ 30% | `combat.py` `execute_attack()` | `"low_hp"` |
| 사망(기절) | `combat.py` `execute_attack()` | `"death"` |
| 전투 이탈(도주) | `think/__init__.py` `_end_combat()` | `"flee"` |

- `combat_discovered` memory flag로 발견 대사 중복 방지
- 전투 종료 시 `_end_combat()`에서 flag 리셋

### 11.6 인간형/기생형 몬스터 (구현 완료)

> 상세: [creature.md](creature.md) Section 12-13

```
HumanoidCreature(Monster)       ← is_humanoid=1, 아키타입 보유
├── Arachne                     ← 거미줄+독, fierce, R5:L2
└── Succubus                    ← 마비(매혹), seductive, R5:L4

ParasiticCreature(Monster)      ← is_parasitic=1, 기생 AI (Tier 3.7)
├── BreastParasiteCreature      ← breast_parasite, R5:L2
└── GenitalParasiteCreature     ← genital_parasite, R5:L3
```

---

## 12. 스폰 시스템

> **구현 완료** — `spawner.py`

**파일:** `scenarios/scenario02/python/spawner.py` (신규)

```python
_spawn_sources = {}
# {source_id: {"class": Wolf, "max": 3, "interval_h": 4,
#              "region_id": int, "location_id": int,
#              "spawned": [], "last_spawn_hour": 0}}

def register_spawn_source(source_id, monster_class, max_count,
                          interval_hours, region_id, location_id):
    """스폰 소스 등록"""

def _on_time_elapsed(millis):
    """매 1시간: 스폰 체크 + 시체 정리

    스폰 체크:
    1. 현재 생존 수 < max_count
    2. 마지막 스폰 후 interval_hours 경과
    3. 몬스터 생성: morld.create_id() → instantiate → _populate_inventory()
    4. think agent 등록: think.register_agent(monster_id, MonsterAgent)

    시체 정리:
    1. 상태:사망 + 상태:사망시각 체크
    2. 4시간 경과 + 플레이어 부재 → morld.set_unit_location(corpse, -1, -1)
    """

def reset():
    global _spawn_sources
    _spawn_sources = {}
```

---

## 13. 몬스터 패트롤

> **구현 완료** — `think/__init__.py: _get_home_region()`, `creature_agent.py`

### 13.1 `_do_wander()` 재사용

기존 NPC 순찰 시스템 그대로 사용 (think/__init__.py:1851-1908).
- `_WANDER_ACTIVITIES`에 `"순찰"` 이미 포함
- home_region 내 랜덤 location → 10~30분 체류

### 13.2 home_region 확장

**파일:** `think/__init__.py:1653` — `_get_home_region()` 수정

```python
def _get_home_region(self):
    """NPC 홈 region (몬스터: 전투:홈리전, NPC: bed_owner)"""
    if self._home_region_id is not None:
        return self._home_region_id

    # 1. 전투:홈리전 prop (몬스터용)
    combat_home = morld.get_unit_prop(self.unit_id, "전투:홈리전")
    if combat_home is not None:
        self._home_region_id = int(combat_home)
        return self._home_region_id

    # 2. 기존 bed_owner 로직 (NPC용)
    owner = getattr(self, 'owner_unique_id', None)
    if owner:
        from think.facility_resolver import _find_facilities_by_prop
        beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
        if beds:
            self._home_region_id = beds[0]["region_id"]
            return self._home_region_id
    loc = self.get_location()
    return loc[0] if loc else 0
```

### 13.3 몬스터 스케줄

```python
# Monster 클래스 기본 스케줄 — 24시간 순찰
MONSTER_SCHEDULE = [
    {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
]
```

전투 위협 감지 시 Tier 2에서 순찰 중단 → 전투 행동 전환.

---

## 14. 몬스터 사망 + 루팅

> **구현 완료** — `base.py: finish_off(), loot(), harvest()`

### 14.1 기본: 기절 재활용

HP 0 → `survival._enter_faint()` → 8시간 후 자동 회복 → 순찰 재개.

### 14.2 숨통끊기 (Finish Off)

기절 상태 적을 포커스 + 무기 장비 중 → "숨통 끊기" 액션:

```python
# get_available_actions() 확장:
import survival
import combat

if survival.is_npc_fainted(self.instance_id):
    is_monster = morld.get_unit_prop(self.instance_id, "전투:적대유형") == "monster"
    if is_monster or combat.is_hostile_mode():
        player_id = morld.get_player_id()
        atk = combat.get_combat_stat(player_id, "전투:공격력")
        if atk > combat.DEFAULT_STATS["전투:공격력"]:  # 맨손보다 강하면 무기 있음
            dynamic_actions.append("call:finish_off:숨통 끊기#")
```

### 14.3 사망 처리

```python
def finish_off(self):
    """기절 → 사망 처리"""
    import survival
    from think import unregister_agent

    original_name = self.name

    # 사망 props
    morld.set_unit_prop(self.instance_id, "상태:사망", 1)
    morld.set_unit_prop(self.instance_id, "상태:사망시각", morld.get_current_time())

    # 이름 변경 (set_unit_name 미존재 → set_unit 사용)
    morld.set_unit(self.instance_id, "name", f"{original_name}의 시체")

    # think Agent 해제
    unregister_agent(self.instance_id)

    # 기절 해제
    survival._fainted_npcs.pop(self.instance_id, None)

    morld.add_action_log(f"{original_name}의 숨통을 끊었다.")
    morld.advance_time_des(5_000)
```

### 14.4 시체 루팅 (인벤토리)

```python
# get_available_actions()에서:
if morld.get_unit_prop(self.instance_id, "상태:사망"):
    inventory = morld.get_inventory(self.instance_id)
    if inventory:
        dynamic_actions.append("call:loot:뒤지기")
    # 수확 가능 체크
    if hasattr(self, 'HARVEST_TABLE'):
        player_props = morld.get_actual_props(morld.get_player_id())
        for prop_key, info in self.HARVEST_TABLE.items():
            amount = morld.get_unit_prop(self.instance_id, prop_key) or 0
            if amount > 0 and player_props.get(info["tool_prop"], 0) > 0:
                dynamic_actions.append("call:harvest:수확")
                break

def loot(self):
    """시체 인벤토리 루팅 — 전부 획득"""
    player_id = morld.get_player_id()
    inventory = morld.get_inventory(self.instance_id)
    if not inventory:
        morld.add_action_log("가진 것이 없다.")
        return
    for item_id, count in inventory.items():
        item_name = morld.get_item_info(item_id)["name"]
        morld.remove_item(self.instance_id, item_id, count)
        morld.give_item(player_id, item_id, count)
        morld.add_action_log(f"{item_name} ×{count} 획득")
    morld.advance_time_des(5_000)
```

### 14.5 시체 자동 소멸

spawner.py `_on_time_elapsed()`에서:
- `상태:사망시각` + 4시간 경과 + 플레이어 부재
- `morld.set_unit_location(corpse_id, -1, -1)` (보이지 않는 곳으로)

---

# Part E: NPC 전투 AI

## 15. think Tier 2 통합

> **구현 완료** — `think/__init__.py: _check_combat_threat(), _handle_combat()`

### 15.1 삽입 위치

**파일:** `think/__init__.py` (Tier 2 Reactive)

```python
# ── Tier 2: Reactive ──
if self._check_restrained_nearby():
    return
if self._check_combat_threat():
    return
```

### 15.2 `_check_combat_threat()`

전투 위협 감지 + 대응. BATTLE_BEHAVIOR 없으면 False (비전투 NPC).

1. 진행 중인 전투 (`combat_phase != None`) → `_handle_combat()`
   - **resignation/desperate**: `_scan_nearest_enemy()`로 적 전멸 감지 → regrouping 전환
   - **retreating/regrouping**: `_scan_nearest_enemy()`로 적 재감지 수행
   - **regrouping**: `_should_end_combat()` 전투 종료 판정 병행
2. 새 적 감지 → combat_style에 따라 engaging / retreating 분기

### 15.3 `_handle_combat()` Phase Machine

```
engaging    → 사거리 밖이면 이동, 안이면 attacking
attacking   → execute_attack() + 공격시간 job
retreating  → 안전 지역으로 이동 → regrouping / 포위 시 체념·필사
regrouping  → 회복 대기 (HP ≥ 75% 또는 전투 종료 시 종료)
resignation → 체념 (반격·이동 불가, 적 전멸 시 regrouping)
desperate   → 필사의 저항 (도주 불가, 적 전멸 시 regrouping)
```

- **engaging**: `_make_location_target()`로 적 위치를 dict 변환 → `_move_to()`
- **attacking**: 공격 후 대상 기절 시 `_should_end_combat()` 판정
- **retreating**: 최초 1회 `_pick_safe_location()` 결정 → `combat_flee_target`에 고정
  - 안전 도착 → regrouping 전환
  - 도착지에 적 + 포위 판정 → 체념/필사 전환
  - 안전 구역 없음 + 포위 → 체념/필사 전환
  - 안전 구역 없음 + 비포위 → 강제 attacking 전환
- **regrouping**: HP 충분 → 정비 완료. 적 재감지 시 combat_style에 따라 재개/유지
- **resignation**: idle job 반복. `_check_combat_threat`에서 적 전멸 감지 시 regrouping 전환
- **desperate**: 적에게 공격 지속. `_check_combat_threat`에서 적 전멸 감지 시 regrouping 전환

### 15.4 전투 종료 3-조건 (`_should_end_combat()`)

모두 AND 충족 시 전투 종료:

1. 현재 location에 적 없음 (`has_enemies_at_location()`)
2. 전투 소리 미청취 (`hears_combat_sound()`)
3. 마지막 적 목격/소리 + `COMBAT_END_COOLDOWN` 경과

조건 1, 2 불충족 시 `combat_last_enemy_ms` 자동 갱신.

### 15.5 안전 지역 선택 (`_pick_safe_location()`)

- Gate 기반 1~2 hop 인접 location 탐색 (home_region 내)
- 전투 소리 들리는 location 제외 (`get_combat_sound_locations()`)
- 1-hop 우선, 없으면 2-hop, 둘 다 없으면 위험 지역 포함

### 15.6 포위 판정 (`_is_surrounded()`)

포위 조건 (모두 AND):
1. 현재 location에 적 존재
2. 인접 **모든** location에서 전투 소리 청취 (`get_combat_sound_locations()`)

포위 시 `COMBAT_DESPERATE_CHANCE` 확률로 필사/체념 분기:
- 필사의 저항 (`desperate`): 현재 위치에서 전투 지속, 도주 불가
- 체념 (`resignation`): 반격·이동 불가, idle 상태

### 15.7 클래스 변수 (서브클래스 override 가능)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `COMBAT_ATTACK_DURATION` | 6,000ms | NPC 근접 공격 시간 |
| `COMBAT_END_COOLDOWN` | 600,000ms (10분) | 전투 종료 쿨다운 |
| `COMBAT_REGROUP_HP_THRESHOLD` | 0.75 (75%) | 정비 종료 HP 비율 |
| `COMBAT_DESPERATE_CHANCE` | 0.5 (50%) | 포위 시 필사의 저항 확률 |

**캐릭터별 COMBAT_DESPERATE_CHANCE:**

| NPC | 확률 | 설명 |
|-----|------|------|
| 세라 | 0.9 | 강인하지만 현실적 (90% 필사) |
| 밀라 | 1.0 | 숨겨진 고수 (100% 필사) |
| 리나 | 0.5 | 기본값 (50/50) |
| 유키 | 0.2 | 도주형 (80% 체념) |
| 엘라 | 0.7 | 방어적이지만 강인 (70% 필사) |

### 15.8 `_memory` 전투 키

```python
"combat_phase": None,          # None/engaging/attacking/retreating/regrouping/resignation/desperate
"combat_target_id": None,      # 전투 대상 unit_id
"combat_last_attack_ms": 0,    # 마지막 공격 시각 (ms)
"combat_last_enemy_ms": 0,     # 마지막 적 목격/소리 시각 (ms)
"combat_flee_target": None,    # 도주 목적지 dict (고정)
"combat_regroup_phase": None,  # 정비 단계 (None/recovering)
```

### 15.9 디버그 로그

`_log_combat_phase(detail)` — 페이즈 전환 시 로그 출력:
```
[combat_phase] 리나(id=272) phase=retreating | 도주 개시
[combat_phase] 리나(id=272) phase=resignation | 포위 → 체념
```

### 15.10 combat.py 헬퍼

| 함수 | 설명 |
|------|------|
| `has_enemies_at_location(unit_id, region_id, location_id)` | 해당 location에 적 존재 여부 |
| `hears_combat_sound(unit_id)` | 전투 소리 청취 여부 |
| `get_combat_sound_locations(unit_id)` | 전투 소리 source location 집합 |

---

## 16. NPC별 전투 스탯 + BATTLE_BEHAVIOR

> **구현 완료** — sera/mila/lina/yuki/ella.py

### sera.py (stoic, 전투적)

```python
# props 추가:
"전투:공격력": 8, "전투:방어력": 5, "전투:명중": 85,
"전투:회피": 10, "전투:치명타": 8, "전투:사거리": 60, "전투:공격속도": 0.8,

BATTLE_BEHAVIOR = {
    "combat_style": "aggressive", "target_priority": "strongest",
    "preferred_range": 60, "retreat_threshold": 0.15,
    "join_combat": True, "join_threshold": 20, "protect_player": True,
    "can_sprint": True,
}
```

### mila.py (gentle, 비전투)

```python
"전투:공격력": 2, "전투:방어력": 2, "전투:명중": 60,
"전투:회피": 5, "전투:치명타": 2, "전투:사거리": 50,

BATTLE_BEHAVIOR = {
    "combat_style": "evasive", "retreat_threshold": 0.8,
    "join_combat": False, "protect_player": False,
}
```

### lina.py (cheerful, 지원형)

```python
"전투:공격력": 4, "전투:방어력": 2, "전투:명중": 80,
"전투:회피": 15, "전투:치명타": 10, "전투:사거리": 50,

BATTLE_BEHAVIOR = {
    "combat_style": "evasive", "target_priority": "weakest",
    "retreat_threshold": 0.3,
    "join_combat": True, "join_threshold": 40, "protect_player": True,
}
```

### yuki.py (timid, 은신/도주)

```python
"전투:공격력": 3, "전투:방어력": 1, "전투:명중": 70,
"전투:회피": 20, "전투:치명타": 5, "전투:사거리": 50,

BATTLE_BEHAVIOR = {
    "combat_style": "evasive", "retreat_threshold": 0.9,
    "join_combat": False, "protect_player": False,
}
```

### ella.py (cold, 방어적)

```python
"전투:공격력": 7, "전투:방어력": 6, "전투:명중": 80,
"전투:회피": 12, "전투:치명타": 5, "전투:사거리": 60, "전투:공격속도": 1.2,

BATTLE_BEHAVIOR = {
    "combat_style": "defensive", "target_priority": "nearest",
    "preferred_range": 60, "retreat_threshold": 0.2,
    "join_combat": True, "join_threshold": 30, "protect_player": False,
    "can_sprint": True,
}
```

---

## 17. on_meet_player 전투 분기

> **구현 완료** — `base.py: on_meet_player(), _on_meet_hostile()`

### 17.1 삽입 위치

**파일:** `assets/base.py:3277-3338` — `on_meet_player()`

기절/탈진/수면 (항목 2) **직후**, 자위 발각 (항목 3) **직전**:

```python
# 2.5. 적대 상태 → 전투 반응
import combat
player_id = morld.get_player_id()
player_name = morld.get_unit_info(player_id)["name"]
hostility = combat.get_hostility(self.instance_id, player_name)
if hostility >= combat.HOSTILITY_HOSTILE:
    return self._on_meet_hostile(player_id, hostility)
```

### 17.2 `_on_meet_hostile()`

```python
def _on_meet_hostile(self, player_id, hostility):
    if hostility >= combat.HOSTILITY_ATTACK_ON_SIGHT:
        morld.add_action_log(f"{self.name}이(가) 적의를 드러낸다!")
        return None  # think Tier 2에서 공격 처리
    morld.add_action_log(f"{self.name}이(가) 경계하며 거리를 둔다.")
    return None
```

---

# Part F: 전투 부가 시스템

## 18. 전투 디버프

> **구현 완료** — `combat.py`, `_tick_debuffs()` 통합 처리

### 18.1 종류

| 디버프 | prop | 효과 | 지속 | 치료 | 구현 |
|--------|------|------|------|------|------|
| 출혈 | `상태:출혈` (잔여 h) | HP -3/h | 3h | 붕대 | O |
| 둔화 | `둔화:속도` (%) + `상태:둔화` (h) | 이동속도 감소 | 2h | 자연 회복 | O |
| 독 | `상태:독` (잔여 h) | HP -2/h | 4h | 해독제 | O |
| 부위 부상 | `부상:{부위}` (잔여 h) | 부위별 페널티 | 4h | 자연 회복 / `cure_body_injury()` | O |
| 마비 | `상태:마비` (잔여 h) | 이동+전투 불가, 의식 유지 | 2h | 자연 회복 | O |
| 거미줄 | `상태:거미줄` (잔여 h) | 이동 불가, 자력 탈출 가능 | 2h | 자력 탈출 / 자연 회복 | O |

### 18.2 출혈

- 치명타 시 `BLEEDING_CHANCE_ON_CRIT`% (50%)로 발생
- 매 시간 HP -3, 잔여시간 -1
- 치료: 붕대 아이템 사용 → `combat.cure_bleeding()`

### 18.3 둔화

- `둔화:속도` prop = 속도% (50 = 반감) — 실제 속도값 추적
- `상태:둔화` = 잔여 시간 (h)
- `이동:부상` = min(둔화:속도, 다리부상속도) — `_recompute_movement_injury()`로 재계산
- 자연 회복: 매 시간 -1, 0이 되면 `둔화:속도` + `이동:부상` 재계산

### 18.4 독

- 거미 공격 시 `전투:독공격`% (30%) 확률로 발생
- 매 시간 HP -2, 잔여시간 -1
- 치료: 해독제 아이템 사용 → `combat.cure_poison()`

### 18.5 부위 부상

치명타 시 `INJURY_CHANCE_ON_CRIT`% (30%) 확률로 랜덤 부위 부상 발생.
조준 공격 명중 시 해당 부위 부상 **확정**.

| 부위 | prop | 효과 | 적용 방식 |
|------|------|------|----------|
| 머리 | `부상:머리` | 명중 -15 | `get_combat_stat()` Python 감산 |
| 팔 | `부상:팔` | 공격력 -30% | `get_combat_stat()` Python 감산 |
| 다리 | `부상:다리` | 속도 60% | `이동:부상` → C# `GetMovementSpeed()` |
| 몸통 | — | 무효 | — |

자연 회복: 매 시간 -1, 0이 되면 prop 제거.
다리 부상 + 둔화 겹침: `이동:부상 = min(둔화:속도, LEG_INJURY_SPEED)`

### 18.6 조준 공격

| 항목 | 값 |
|------|-----|
| 명중률 페널티 | -20 |
| 공격속도 배율 | ×1.2 (20% 느림) |
| 부위 부상 | 명중 시 확정 (몸통 제외) |

**UI 액션**: `_add_combat_actions()` → `조준: 머리#` / `조준: 팔#` / `조준: 다리#`
`#` 접미사 → hostile mode OFF 시 자동 숨김.

### 18.7 치료 아이템

| 아이템 | unique_id | 효과 | 배치 |
|--------|-----------|------|------|
| 붕대 | `bandage` | 출혈 치료 + HP 10 | 경찰서 구급함 ×3 |
| 해독제 | `antidote` | 독 치료 + HP 5 | 경찰서 구급함 ×1 |

**크래프팅**: `antidote` = `spider_venom` ×1 + `food_herb` ×2 (제작대)

### 18.8 디버프 시간 처리

`_tick_debuffs(unit_id, is_player)` — 모든 디버프를 단일 함수에서 처리:

1. 출혈 데미지 → 만료 체크
2. 독 데미지 → 만료 체크
3. 둔화 회복 → `_recompute_movement_injury()`
4. 부위 부상 자연 회복 → 다리 만료 시 `_recompute_movement_injury()`

`_on_time_elapsed()` → NPC 루프 + 플레이어 각각 `_tick_debuffs()` 호출.

### 18.9 마비

- 상수: `PARALYSIS_DURATION_HOURS = 2`
- 특수 공격 (`전투:마비공격` prop)으로 부여 가능
- 효과: `can_fight()` False, `restraint.can_move()` False, 의식 유지
- 매 시간 -1, 0이면 `cure_paralysis()`

```python
def apply_paralysis(unit_id, duration_hours=None)
def cure_paralysis(unit_id)
def is_paralyzed(unit_id) -> bool
```

### 18.10 거미줄 결박

- 상수: `WEB_BIND_DURATION_HOURS = 2`, `WEB_BIND_ESCAPE_DIFFICULTY = 20`
- Spider `전투:거미줄공격: 25` — 명중 시 25% 확률로 부여
- 효과: `restraint.can_move()` False
- 자력 탈출: `attempt_web_escape()` — 근력/체격/HP 비율 기반 확률 (5%-70%)
- 매 시간 -1, 0이면 `cure_web_bind()`

```python
def apply_web_bind(unit_id, duration_hours=None)
def cure_web_bind(unit_id)
def is_web_bound(unit_id) -> bool
def attempt_web_escape(unit_id) -> bool
```

### 18.11 특수 공격 범용 시스템

하드코딩된 독/거미줄 블록 대신 **`SPECIAL_ATTACKS`** dict 패턴:

```python
SPECIAL_ATTACKS = {
    "전투:독공격":     lambda tid: apply_poison(tid),
    "전투:거미줄공격": lambda tid: apply_web_bind(tid),
    "전투:마비공격":   lambda tid: apply_paralysis(tid),
    # 향후 확장: "전투:포박공격" 등
}
```

`execute_attack()` 내 명중 시 루프로 모든 특수 공격 자동 처리.
새 능력 추가 = dict에 1줄 + creature props에 확률 1줄.

### 18.12 C# 연동: `이동:부상`

**파일:** `scripts/morld/unit/Unit.cs:423-443` — `GetMovementSpeed()`

```csharp
// 부상 감속 (Unit prop — actualProps에서 읽음)
var injurySpeed = actualProps.GetProp("이동:부상");
if (injurySpeed > 0 && injurySpeed < 100)
    result = result * injurySpeed / 100;
```

> `이동:혼잡` = `TraversalContext` (Location prop)
> `이동:부상` = `actualProps` (Unit prop) — 출처가 다름!

---

## 19. 엄폐/은폐/지형 효과

### 19.1 Phase 1: 지형 자동 효과

Location의 `length`가 자연스러운 전투 환경 결정:

| length | geometry | 전투 특성 |
|--------|----------|----------|
| ≤200 (좁은 실내) | line | 근접 강제, 원거리 이점 없음 |
| 200-600 (중간) | line/ring | 원거리 약간 유리 |
| ≥600 (넓은 야외) | line | 원거리 크게 유리, 접근에 시간 |
| ring | ring | 우회/포위 가능, 도주 용이 |

### 19.2 은신 연동

기존 stealth.py 활용:
- 전투 전 은신 상태 → 첫 공격 **기습**: 치명타 + `STEALTH_CRIT_BONUS`% (30%)
- 전투 시작 시 은신 자동 해제

### 19.3 간이 엄폐 시스템

> **구현 완료** — `combat.py: get_cover_bonus()`

battle.md의 풀 엄폐 시스템(CoverObject, take_cover 액션) 대신
기존 인프라만으로 구현하는 간이 버전:

**조건**: `posture:crouch` (웅크리기) + 가장 가까운 오브젝트 거리 ≤ 15px + `cover:level` prop

| cover:level | 회피 보너스 | 피해 감소 | 예시 오브젝트 |
|-------------|-----------|----------|-------------|
| partial | +10 | 20% | 나무, 정원 벤치, 거리 벤치 |
| half | +20 | 40% | 식탁 |
| full | +40 | 70% | (미래: 바리케이드) |

**적용 위치**:
- `calculate_hit_chance()` → 회피에 엄폐 보너스 가산
- `calculate_damage()` → 최종 데미지에 피해 감소 적용

별도 액션 불필요 — 웅크리기 자세 + 위치만으로 자동 적용.
공격 시에도 엄폐 유지 (풀 버전의 expose/return_cover 없음).

---

## 20. 간호 + HP 회복

### 20.1 간호

기존 `carry.py` 활용 — 기절 NPC 운반 → 침대 → 치료.

**효과:**
- 적대도: -20 (`HOSTILITY_ON_NURSING`)
- 호감: +10 (`AFFECTION_ON_NURSING`)

### 20.2 NPC HP 회복 (think Tier 3)

> **구현 완료** — `think/__init__.py: _check_hp_recovery() + _handle_hp_recovery()`

HP < 50% → 음식 섭취로 HP 회복 (multi-phase).
NPC는 평소 음식을 소지하지 않으므로 `_handle_eat`과 동일한 패턴:

```
Phase 1: idle — 인벤토리 체크 → storage 위치 탐색 (resolve_storage_container)
Phase 2: going → storage로 이동
Phase 3: eating → 음식 꺼내기 + 섭취 (HP += satiety//2, 최소 5)
```

`_memory` 키: `hp_recovery_phase`, `hp_recovery_target`
Tier 3 우선순위: 배고픔 → 추위 → 더위 → **HP 회복**

### 20.3 장비 내구도 시스템

> **구현 완료** — `combat.py: degrade_durability(), get_equipped_weapon()`

#### Props

| prop | 설명 | 설정 시점 |
|------|------|----------|
| `내구도` | 현재 내구도 (정수) | `Item.instantiate()` 시 `self.durability` 값으로 초기화 |
| `상태:파손` | 파손 여부 (1=파손) | `degrade_durability()` 에서 내구도 0 시 설정 |

#### 기본 내구도

| 카테고리 | 클래스 | durability | 비고 |
|---------|--------|-----------|------|
| 의류 기본 | `Clothing` | 20 | 전체 의류 상속 |
| 속옷 | `SimpleBra`, `LaceBra` 등 | 10 | 취약 |
| 외투/코트 | `WarmCoat`, `HoodedCloak` 등 | 30 | 견고 |
| 군용 | `TacticalVest`, `CamouflagePants` 등 | 40 | 강화 |
| 누더기 | `RaggedClothes` 등 | 5 | 이미 해진 옷 |
| 무기/도구 | `Item` (equipment.py) | 50 | 기본값 |

`durability = None` → 내구도 없는 아이템 (시나리오03 호환, 파괴 불가).

#### `degrade_durability(item_id, amount=1, owner_id=None)`

```python
def degrade_durability(item_id, amount=1, owner_id=None):
    """내구도 감소. 0이면 장착 해제 + 파손 표시 (인벤토리 유지, 향후 복구 가능)."""
    current = morld.get_unit_prop(item_id, "내구도")
    if current is None:
        return  # 내구도 없는 아이템
    new_val = max(0, current - amount)
    morld.set_unit_prop(item_id, "내구도", new_val)
    if new_val == 0:
        morld.set_unit_prop(item_id, "상태:파손", 1)
        item_info = morld.get_item_info(item_id)
        item_name = item_info.get("name", "아이템") if item_info else "아이템"
        if owner_id is not None:
            import equipment
            if equipment.is_equipped(owner_id, item_id):
                equipment.unequip_item(owner_id, item_id)
        morld.add_action_log(f"{item_name}이(가) 파손되었다.")
```

**핵심:** 파손 시 아이템은 인벤토리에 유지됨 (`lost_item` 미호출). 향후 수리 시스템 대비.

#### `get_equipped_weapon(unit_id)`

```python
def get_equipped_weapon(unit_id: int):
    """장착된 무기 item_id 반환 (없으면 None)"""
    import equipment
    items = equipment.get_equipped_items(unit_id)
    for item_id in (items or []):
        info = morld.get_item_info(item_id)
        if not info:
            continue
        equip_props = info.get("equip_props") or {}
        if "전투:공격력" in equip_props:
            return item_id
    return None
```

#### 전투 내구도 감소 호출

| 함수 | 호출 방법 |
|------|----------|
| `execute_attack()` | `weapon_id = get_equipped_weapon(attacker_id)` → `degrade_durability(weapon_id, 1, attacker_id)` |
| `execute_aimed_attack()` | 동일 |
| `harassment.execute_tear()` | 의류 내구도 감소 → `degrade_durability(clothing_id, TEAR_DURABILITY_DAMAGE, target_id)` |

#### 무기 고장 (jam_chance)

내구도 기반 무기 고장 확률:
```python
weapon_id = get_equipped_weapon(attacker_id)
durability = morld.get_unit_prop(weapon_id, "내구도") if weapon_id else 100
if durability is None:
    durability = 100
jam_chance = max(0, (100 - durability) * 0.5 - 10)  # 내구도 80부터 고장 확률 발생
```

#### 맨손 전투

무기가 없거나 모두 파손된 상태에서도 `DEFAULT_STATS` fallback으로 맨손 전투 가능:
```python
DEFAULT_STATS = {
    "전투:공격력": 1, "전투:방어력": 0, "전투:명중": 80,
    "전투:회피": 5, "전투:치명타": 2, "전투:사거리": 50,
}
```

---

# Part G: 신규 콘텐츠

## 21. 폐 경찰서 + 광산

> **구현 완료** — `city.py`, `mine.py`, `mining.py`, `world/mine.py`

### 21.1 폐 경찰서

**Region 2 (도시)에 Location 추가:**

```python
class AbandonedPoliceStation(Location):
    name = "폐 경찰서"
    length = 400
    geometry = "line"
    indoor = True
```

**배치 아이템:**

| 아이템 | 컨테이너 | 수량 | 타입 |
|--------|---------|------|------|
| 리볼버 | 사무실 서랍 | 1 | 장비 인스턴스 |
| 권총탄 | 서랍 | 12 | 소모품 스택 |
| 삼단봉 | 장비함 | 1 | 장비 인스턴스 |
| 붕대 | 구급함 | 3 | 소모품 스택 |

### 21.2 신규 무기류

```python
class Revolver(Item):
    unique_id = "revolver"
    name = "리볼버"
    category = "weapon"
    equip_props = {
        "전투:공격력": 12, "전투:사거리": 200,
        "전투:명중": -10, "전투:치명타": 10,
        "전투:탄약": "pistol_ammo", "전투:장탄수": 6,
        "can:reload": 1, "장착:손": 1,
    }

class Baton(Item):
    unique_id = "baton"
    name = "삼단봉"
    category = "weapon"
    equip_props = {
        "전투:공격력": 5, "전투:사거리": 60,
        "전투:명중": 10, "장착:손": 1,
    }
```

### 21.3 광산 Region (구현 완료)

**Region 4 — 도시 주차장(R2:4)에서 Gate 연결 (~30분 도보):**

| Location ID | 이름 | length | indoor | 오브젝트 | 몬스터 |
|-------------|------|--------|--------|---------|--------|
| 0 | 광산 입구 | 300 | False | 벤치, 곡괭이(바닥) | — |
| 1 | 1층 갱도 | 500 | True | CopperOreNode×2 | 박쥐 (max 2, 4h) |
| 2 | 2층 갱도 | 400 | True | CopperOreNode×1, IronOreNode×1 | 거미 (max 1, 6h) |
| 3 | 깊은 갱도 | 300 | True | IronOreNode×2 | 거미 (max 2, 8h) |

**몬스터 (동시 최대 5마리):**

| 몬스터 | HP | ATK | DEF | 명중 | 회피 | 스타일 | 드롭/수확 |
|--------|-----|-----|-----|------|------|--------|----------|
| Bat (박쥐) | 15 | 3 | 1 | 65 | 25 | evasive | meat(50%) |
| Spider (거미) | 50 | 6 | 4 | 75 | 10 | aggressive | 독낭(수확,날붙이), 거미줄(수확,맨손) |

**제작대**: 광산에 배치하지 않음 — 건축 시스템으로 플레이어가 직접 건축하도록 유도.

### 21.4 채광 시스템 (구현 완료)

**OreNode** (`assets/objects/mining.py`): Object 서브클래스, props 기반 자원 관리 + 시간구독 자동 재생.

| 서브클래스 | resource_type | amount/max | regen | 위치 |
|-----------|---------------|------------|-------|------|
| CopperOreNode | copper_ore | 5/5 | 24h | 1층(×2), 2층(×1) |
| IronOreNode | iron_ore | 3/3 | 48h | 2층(×1), 깊은(×2) |

```python
class Pickaxe(Item):
    unique_id = "pickaxe"
    name = "곡괭이"
    category = "tool"
    passive_props = {"can:mine": 1}
    equip_props = {
        "전투:공격력": 4, "전투:사거리": 60, "장착:손": 1,
    }
```

### 21.5 광석 크래프팅 (구현 완료)

```python
# crafting_recipes.py — WORKBENCH_RECIPE_LIST에 등록:
"copper_sword":  {"materials": {"copper_ore": 3, "branch": 1}, "craft_time": 15, "category": "무기"}
"copper_shield": {"materials": {"copper_ore": 4},               "craft_time": 20, "category": "무기"}
"iron_sword":    {"materials": {"iron_ore": 3, "branch": 1},    "craft_time": 20, "category": "무기"}
"iron_shield":   {"materials": {"iron_ore": 5},                 "craft_time": 30, "category": "무기"}
"pickaxe":       {"materials": {"iron_ore": 2, "branch": 1},    "craft_time": 15, "category": "도구"}
```

**무기 등급 비교:**

| 무기 | 공격력 | 사거리 | 특수 |
|------|--------|--------|------|
| 구리검 | 5 | 70 | 하위 등급 |
| 철검 | 7 | 80 | 상위 등급 |
| 구리방패 | 방어 3, 회피 -5 | — | 하위 등급 |
| 철제방패 | 방어 5, 회피 -10 | — | 상위 등급 |

---

# Part H: 통합

## 22. C# 연동 사항

> **구현 완료** — `Unit.cs: GetMovementSpeed()` (이동:부상, 이동:달리기)

### 22.1 Unit.GetMovementSpeed() 확장

**파일:** `scripts/morld/unit/Unit.cs:423-443`

기존 congestion 체크 (line 438-440) 뒤에 추가:

```csharp
// 부상 감속 (Unit prop)
var injurySpeed = actualProps.GetProp("이동:부상");
if (injurySpeed > 0 && injurySpeed < 100)
    result = result * injurySpeed / 100;

// 달리기 가속 (Unit prop)
var sprintMode = actualProps.GetProp("이동:달리기");
if (sprintMode > 0)
    result = result * 150 / 100;
```

> `이동:혼잡` = TraversalContext (Location), `이동:부상`/`이동:달리기` = actualProps (Unit)

### 22.2 챕터 리셋

**파일:** `scenarios/scenario02/python/chapters/__init__.py` — `load_chapter()`

기존 리셋 체인 끝에 추가:

```python
import combat
import spawner
combat.reset()
spawner.reset()
```

---

## 23. 파일별 수정 사항

### 신규 파일

| 파일 | 설명 | 예상 줄 |
|------|------|---------|
| `combat.py` | 전투 코어 | ~350 |
| `spawner.py` | 몬스터 스폰 | ~120 |
| `assets/characters/monster.py` | Monster/Bat/Spider/TrainingDummy | ~200 |
| `assets/items/weapons.py` | Revolver, Baton, CopperSword, IronSword, Pickaxe | ~150 |
| `assets/items/shields.py` | WoodenShield, CopperShield, IronShield | ~50 |
| `assets/items/ammo.py` | Arrow, PistolAmmo | ~20 |
| `assets/items/ores.py` | CopperOre, IronOre | ~50 |
| `assets/objects/mining.py` | OreNode, CopperOreNode, IronOreNode + regen | ~165 |
| `assets/locations/mine.py` | MineEntrance, MineFloor1/2, MineDeep | ~130 |
| `world/mine.py` | Region 4 + spawn 등록 | ~110 |
| `tests/test_combat.py` | 테스트 | ~200 |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `assets/base.py` | attack()/steal()/finish_off()/loot()/harvest() + actions + on_meet 분기 + get_available_actions |
| `assets/characters/player.py` | 전투 스탯 props + can:attack/steal + 이동:달리기 |
| `assets/characters/sera.py` | 전투 스탯 + BATTLE_BEHAVIOR |
| `assets/characters/mila.py` | 전투 스탯 + BATTLE_BEHAVIOR |
| `assets/characters/lina.py` | 전투 스탯 + BATTLE_BEHAVIOR |
| `assets/characters/yuki.py` | 전투 스탯 + BATTLE_BEHAVIOR |
| `assets/characters/ella.py` | 전투 스탯 + BATTLE_BEHAVIOR |
| `assets/items/equipment.py` | 공격→전투:공격력 마이그레이션 |
| `assets/items/tools.py` | 공격력/사거리→전투: 마이그레이션 |
| `assets/items/consumables.py` | Bandage 추가 |
| `settings.py` | 적대모드 + 달리기 토글 |
| `think/__init__.py` | Tier 2 전투 + _memory 키 + _get_home_region 확장 |
| `needs.py` | 달리기 피로 2배 |
| `chapters/__init__.py` | combat.reset() + spawner.reset() |
| `crafting_recipes.py` | 광석 레시피 |
| C# `Unit.cs` | GetMovementSpeed() — 이동:부상, 이동:달리기 |

---

## 24. 구현 순서

```
Phase 1: 기반
  1. 무기 prop 마이그레이션 (equipment.py, tools.py)
  2. combat.py 생성 (스탯, 데미지, 적대도, 디버프, 시간구독)
  3. player.py 전투 스탯 + 달리기 prop

Phase 2: 플레이어 전투
  4. base.py — attack()/steal() + actions
  5. settings.py — 적대모드 + 달리기 토글
  6. C# Unit.cs — GetMovementSpeed() 확장 (부상+달리기)

Phase 3: 장비 인프라
  7. 장비 인스턴스 생성 로직 (create_id 패턴)
  8. 원거리 무기 + 탄약 (Arrow, PistolAmmo, reload)
  9. 방패 (WoodenShield, IronShield)

Phase 4: 몬스터
  10. monster.py (Monster/Wolf/TrainingDummy)
  11. spawner.py
  12. think _get_home_region 확장 + 패트롤

Phase 5: NPC 전투 AI
  13. think Tier 2 — _check_combat_threat + _handle_combat
  14. NPC별 전투 스탯 + BATTLE_BEHAVIOR (5 캐릭터)
  15. on_meet 전투 분기

Phase 6: 사망/루팅
  16. finish_off + loot + harvest
  17. spawner 시체 정리

Phase 7: 디버프/콘텐츠
  18. 붕대 아이템 + 디버프 시간 처리
  19. 경찰서 Location + 무기 배치
  20. 광산 Region + 채광 + 크래프팅

Phase 8: 통합
  21. chapters/__init__.py 리셋
  22. needs.py 달리기 피로
  23. 테스트 (test_combat.py)
```

---

## 25. 테스트 계획

### MockMorld 보완

`tests/mock_morld.py`에 `get_actual_props()`, `set_unit()`, `get_current_time()` 추가 필요.
상세 구현은 party-implementation.md Section 23.0 참조.

### 테스트 케이스

```python
# ── 스탯 ──
test_get_combat_stat_default()
test_get_combat_stat_with_props()
test_get_combat_stat_with_equip()

# ── 거리 ──
test_get_distance_same_location()
test_get_distance_different_location()

# ── 데미지 ──
test_calculate_damage_basic()        # atk - def/2
test_calculate_damage_min()          # 최소 1
test_calculate_damage_crit()         # 1.5배
test_calculate_hit_chance_clamp()    # 5-95%

# ── 공격 ──
test_execute_attack_hit()
test_execute_attack_miss()
test_execute_attack_faint()
test_execute_attack_ranged_no_ammo()

# ── 적대도 ──
test_hostility_modify()
test_hostility_clamp()
test_is_hostile_to_monster()
test_hostility_decay()

# ── 적대모드 ──
test_hostile_mode_toggle()
test_hostile_mode_can_props()

# ── 디버프 ──
test_apply_bleeding()
test_cure_bleeding()
test_bleeding_damage_over_time()

# ── 장비 인스턴스 ──
test_equipment_unique_ids()
test_durability_degrade()

# ── 드롭/수확 ──
test_monster_drop_table()
test_harvest_requires_tool()
```

```bash
# syntax check
"C:\ProgramData\miniforge3\python.exe" -c "import ast; ast.parse(open('scenarios/scenario02/python/combat.py', encoding='utf-8').read())"

# 전체 테스트
"C:\ProgramData\miniforge3\python.exe" tests/run_tests.py -v
```

---

## 26. 파티 시스템 (Phase 2 — 별도 문서)

> **상세 구현 명세:** [party-implementation.md](party-implementation.md)

요약:
- 최대 4인 (리더 포함), 리더 = 플레이어 또는 NPC
- `party.py` 신규 모듈 (date.py follow 패턴 확장)
- 가입: 호감 일정 이상 + `PARTY_BEHAVIOR.recruitable`
- 명령: 따라와 / 대기 / 집결 / 공격해 / 물러나
- 전투 정책: aggressive / defensive / pacifist
- think Tier 2.5: 파티 follow (Reactive와 Survival 사이)
- NPC 리더: 이벤트/퀘스트 기반, 플레이어 참여/이탈
- combat.py 연동: 파티 멤버 우선 합류 (호감도 체크 생략)
- Scenario 03 확장: NPC 전용 분대, 거시/미시 명령, 전술 AI

---

## 부록: morld API 목록

| API | 용도 | 확인 |
|-----|------|------|
| `morld.get_unit_info(id)` | name, region_id, location_id, x, is_object, is_creature | cs:549 |
| `morld.get_unit_prop(id, key)` | 단일 prop 조회 | O |
| `morld.set_unit_prop(id, key, val)` | prop 설정 | O |
| `morld.modify_prop(id, key, delta)` | prop 증감 | O |
| `morld.clear_prop(id, key)` | prop 제거 | O |
| `morld.get_actual_props(id)` | base + equip 합산 dict | ui.py:774 |
| `morld.get_item_info(id)` | name, equip_props 등 | O |
| `morld.get_player_id()` | 플레이어 ID | O |
| `morld.advance_time_des(ms)` | DES 시간 경과 | O |
| `morld.add_action_log(text)` | 액션 로그 | O |
| `morld.create_id()` | 유닛/아이템 ID 생성 (인수 무시됨) | cs:75 |
| `morld.subscribe_time_elapsed(cb, min)` | 시간 이벤트 구독 | O |
| `morld.get_inventory(id)` | {item_id: count} dict | O |
| `morld.give_item(owner, item, count)` | 아이템 부여 | O |
| `morld.remove_item(owner, item, count)` | 아이템 제거 | O |
| `morld.lost_item(owner, item)` | 소모품 소비 | O |
| `morld.set_unit_location(id, r, l)` | 위치 변경 | O |
| `morld.set_unit(id, key, value)` | 유닛 속성 변경 (name 등) | cs:1367 |
| `morld.get_current_time()` | 현재 시간 (ms) | O |
| `morld.get_units_at_location(r, l)` | Location 내 유닛 목록 | O |
| `sound.emit_sound(id, type, intensity)` | 소리 발생 ("combat"/"gunshot") | sound.py:267 |
| `survival.is_npc_fainted(id)` | NPC 기절 여부 | survival.py:142 |
| `survival._enter_faint(id)` | NPC 기절 처리 | survival.py:241 |
| `survival._enter_player_faint()` | 플레이어 기절 | survival.py:278 |
| `think.get_agent(id)` | think agent 조회 | think:2432 |
| `think.unregister_agent(id)` | think agent 해제 | think:2426 |
