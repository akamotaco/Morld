# 은신 시스템 (Stealth System)

> 플레이어가 NPC의 감지를 피해 행동할 수 있는 시스템

---

## 1. 개요

### 1.1 핵심 개념

- **은신 상태**: 웅크리기/엎드리기 자세 + NPC 없는 Location에서 자동 진입
- **발각 판정**: NPC와 조우 시 밝기, 자세, 엄폐물, NPC 감지력 기반 확률 계산
- **이벤트 연동**: on_meet/on_contact 이벤트 발생 시 은신 판정으로 회피 가능

### 1.2 Props 구조

```python
# 플레이어 props
status:stealth = 1   # 은신 중
status:stealth = 0   # 발각됨
# (prop 없음)        # 일반 상태

# NPC props (선택)
perception:base = 100  # 감지력 (100 = 기본, 150 = 세라)
```

---

## 2. 자세 시스템 확장

### 2.1 자세 로테이션

이동 가능 상태에서 [자세] 클릭 시 순환:

```
서기 → 웅크리기 → 엎드리기 → 서기
```

### 2.2 자세별 속성

| 자세 | 이동 속도 | 은신 계수 | 비고 |
|------|----------|----------|------|
| standing | 100% | 1.0 | 기본 |
| crouch | 50% | 0.5 | 은신 가능 |
| prone | 25% | 0.3 | 최고 은신 |
| sitting | 0% (이동불가) | - | 오브젝트 착석 |
| lying | 0% (이동불가) | - | 오브젝트 눕기 |

### 2.3 이동 속도 계산

```python
실제_속도 = location.base_speed × character_speed × posture_speed_modifier

POSTURE_SPEED = {
    "standing": 1.0,
    "crouch": 0.5,
    "prone": 0.25,
}
```

---

## 3. 은신 상태

### 3.1 진입 조건

```python
# 은신 진입 조건
is_stealth_posture = posture in ["crouch", "prone"]
no_npcs_in_location = len(get_npcs_in_location(player_location)) == 0

if is_stealth_posture and no_npcs_in_location:
    set_prop(player_id, "status:stealth", 1)
```

### 3.2 상태 전환

| 조건 | 동작 | 결과 |
|------|------|------|
| 발각됨 | `status:stealth = 0` | [발각!] 표시 |
| 발각 후 Location 이동 | `status:stealth` 제거 | 일반 상태 복귀 |
| 자세 변경 (standing) | `status:stealth` 제거 | 일반 상태 |
| 수동 해제 | `status:stealth` 제거 | 일반 상태 |
| 챕터 전환 | `status:stealth` 제거 | 일반 상태 |

> **발각 상태 (`status:stealth = 0`)**: 현재 Location에서만 유지. 다른 Location으로 이동하면 자동 해제.

### 3.3 UI 표시 (Footer)

```
[서기]                    # 일반 상태
[웅크리기]                # 이동 가능 자세, NPC 있음
[웅크리기] [은신 중]      # 은신 상태
[웅크리기] [발각!]        # 발각됨
```

---

## 4. 발각 판정

### 4.1 기본 공식

```python
# 30분 기준 발각 확률
detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력

# 예시: 밝기 80% × 자세 0.5 × 엄폐 0.6 × 감지력 1.0 = 24%
```

### 4.2 변수 상세

#### 밝기 (0.0 ~ 1.0)

| 환경 | 밝기 |
|------|------|
| 대낮 (야외) | 1.0 |
| 황혼 | 0.5 |
| 밤 | 0.2 |
| 암흑 | 0.0 |
| 실내 (조명 있음) | 0.8 |
| 실내 (조명 없음) | 0.1 |

#### 자세 계수

| 자세 | 계수 |
|------|------|
| standing | 1.0 |
| crouch | 0.5 |
| prone | 0.3 |

#### 엄폐 계수

| 상황 | 계수 |
|------|------|
| 오브젝트 근접 (X 거리 ≤ 5) | 0.3 |
| 오브젝트 중간 (X 거리 ≤ 15) | 0.6 |
| 엄폐물 없음 | 1.0 |

#### NPC 감지력

| NPC | 감지력 |
|-----|--------|
| 기본 | 1.0 |
| 세라 (경비) | 1.5 |
| 잠든 NPC | 0.1 |

### 4.3 시간 경과 판정

```python
def check_detection_over_time(player_id, elapsed_minutes, npcs):
    """30분마다 발각 판정 (D&D 스타일)"""
    rounds = elapsed_minutes // 30
    base_rate = calculate_detection_rate(player_id)

    for _ in range(rounds):
        for npc in npcs:
            npc_perception = get_npc_perception(npc)
            final_rate = base_rate * npc_perception
            if random.random() < final_rate:
                return npc  # 발각한 NPC 반환
    return None  # 은신 성공
```

---

## 5. 이벤트 시스템 연동

### 5.1 이벤트 타입

| 타입 | 은신 판정 | 예시 |
|------|----------|------|
| 일반 이벤트 | O | first_meet, on_contact |
| forced_event | X (무조건 발동) | 챕터 전환, 보스 등장 |

### 5.2 이벤트 큐 처리 흐름

```
[이벤트 큐]
  Lina(first_meet) → Sera(first_meet) → Mila(first_meet)

[Resolve 순서]
  1. Lina: 은신 판정 성공 → 큐에서 제거, 로그 "들키지 않았다"
  2. Sera: 은신 판정 실패 → status:stealth=0, 이벤트 진행
  3. Mila: 은신 해제 상태 → 판정 없이 이벤트 진행
```

### 5.3 구현 예시

```python
def resolve_event_with_stealth(event, player_id, npc_id):
    """이벤트 resolve 시 은신 판정"""

    # forced_event는 은신 무시
    if event.is_forced:
        return True  # 이벤트 진행

    # 은신 상태가 아니면 바로 진행
    stealth = get_prop(player_id, "status:stealth")
    if stealth != 1:
        return True  # 이벤트 진행

    # 은신 판정
    if detection_check(player_id, npc_id):
        # 발각
        set_prop(player_id, "status:stealth", 0)
        add_action_log(f"{get_name(npc_id)}에게 발각되었다!")
        return True  # 이벤트 진행
    else:
        # 은신 성공
        add_action_log("들키지 않은 것 같다.")
        return False  # 이벤트 스킵
```

---

## 6. 행동별 소음

> 향후 구현 예정

### 6.1 소음 레벨

| 행동 | 소음 | 비고 |
|------|------|------|
| 대기 | 0.0 | 무음 |
| 이동 (crouch) | 0.1 | 낮음 |
| 이동 (standing) | 0.3 | 중간 |
| 문 열기 | 0.3 | 중간 |
| 서랍 열기 | 0.4 | 중간 |
| 아이템 줍기 | 0.2 | 낮음 |
| 소매치기 | 0.5 | 높음 |
| 달리기 | 0.8 | 매우 높음 |

### 6.2 소음 전파

- 소음 레벨 0.5 이상: 인접 Location까지 전파
- 소음 레벨 0.8 이상: 2칸 떨어진 Location까지 전파

---

## 7. 챕터 전환 처리

### 7.1 상태 리셋 함수

```python
def reset_player_state(player_id):
    """챕터 전환 시 자세/은신 상태 초기화"""

    # 1. 앉아있으면 일어나기 (seated_on, seated_by 정리)
    morld.stand_up(player_id)

    # 2. 웅크리기/엎드리기 → 서기
    posture_props = morld.get_unit_props_by_type(player_id, "posture")
    for prop_name in posture_props:
        morld.clear_unit_prop(player_id, f"posture:{prop_name}")

    # 3. 은신 상태 제거
    morld.clear_unit_prop(player_id, "status:stealth")
```

### 7.2 persistence.py 연동

챕터 전환 시 아래 props는 복원하지 않음 (이미 구현됨):

```python
# chapters/persistence.py - restore_player_data()
if (prop_name.startswith("posture:") or
    prop_name.startswith("seated_on:") or
    prop_name == "status:stealth"):
    skipped_props.append(prop_name)
    continue
```

> **참고**: `reset_player_state()` 함수는 명시적 초기화가 필요할 때 사용.
> 일반적인 챕터 전환에서는 persistence.py의 스킵 로직으로 충분함.

---

## 8. 의존 시스템

### 8.1 필요한 기존 시스템

| 시스템 | 용도 |
|--------|------|
| 자세 시스템 | crouch/prone 자세 관리 |
| 이벤트 시스템 | on_meet/on_contact 판정 |
| 시간 시스템 | 경과 시간 기반 판정 |

### 8.2 신규 구현 필요

| 항목 | 설명 |
|------|------|
| 밝기 시스템 | Region/Location 밝기, 조명 오브젝트 |
| 자세별 이동 속도 | posture_speed_modifier 적용 |
| 이벤트 큐 은신 판정 | resolve 시 판정 로직 |

---

## 9. 구현 순서 (권장)

1. **자세 전환 + 이동 속도**
   - crouch/prone 자세 전환 기능 (posture prop 설정)
   - Footer [자세] 클릭 시 로테이션 (서기 → 웅크리기 → 엎드리기 → 서기)
   - 자세별 이동 속도 계수 적용 (crouch 50%, prone 25%)
2. **은신 상태 관리** - status:stealth prop 관리
3. **밝기 시스템** - Region/Location 밝기 구현
4. **발각 판정** - 기본 공식 구현
5. **이벤트 연동** - on_meet 은신 판정
6. **시간 경과 판정** - 30분 단위 판정
7. **소음 시스템** - 행동별 소음 (향후)

---

## 10. 관련 문서

- [movement-system.md](movement-system.md) - 자세 시스템
- [event.md](event.md) - 이벤트 시스템
- [terrain_property.md](terrain_property.md) - 환경 속성 (밝기)
