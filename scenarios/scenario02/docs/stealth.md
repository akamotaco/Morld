# 은신 시스템 (Stealth System)

> 플레이어와 NPC가 상대의 감지를 피해 행동할 수 있는 시스템

---

## 1. 개요

### 1.1 핵심 개념

- **2단계 자세**: 통상(standing) ↔ 은신(crouch) 이진 토글
- **플레이어 은신**: crouch 자세 + NPC 없는 Location에서 자동 진입
- **NPC 은신**: `status:stealth=1`인 NPC는 플레이어에게 보이지 않음
- **발각 판정**: 밝기, 자세, 엄폐물, 감지력 기반 확률 계산
- **행동별 은신 해제**: 공개 행동(대화, 거래) → 자동 해제 / 은밀 행동(소매치기) → 은신 유지
- **NPC 감지**: Location 도착 시 자동 판정 + 30분 주기 재판정

### 1.2 Props 구조

```python
# 플레이어/NPC 공통 props (2값 시스템)
status:stealth = 1   # 은신 중
# (0 또는 prop 없음)  # 일반 상태

posture:crouch = 1   # 은신 자세 (없으면 standing=통상)

# NPC props (선택)
perception:base = 100  # 감지력 (100 = 기본, 150 = 세라)
```

> **참고:** C# `GetProp()`은 prop이 없으면 `0`을 반환합니다. Python에서는 `0`과 prop 없음 모두 "일반 상태"로 취급합니다.

---

## 2. 자세 시스템

### 2.1 통상 ↔ 은신 토글

이동 가능 상태에서 UI 버튼 클릭 시 토글:

```
통상 ↔ 은신
```

### 2.2 자세별 속성

| 자세 | 이동 속도 | 은신 계수 | 비고 |
|------|----------|----------|------|
| standing | 100% | 1.0 | 통상 |
| crouch | 50% | 0.5 | 은신 |
| sitting | 0% (이동불가) | - | 오브젝트 착석 |
| lying | 0% (이동불가) | - | 오브젝트 눕기 |

### 2.3 이동 속도 계산

```python
실제_속도 = location.base_speed × character_speed × posture_speed_modifier

POSTURE_SPEED = {
    "standing": 1.0,   # 통상
    "crouch": 0.5,     # 은신
}
```

---

## 3. 은신 상태

### 3.1 플레이어 은신

#### 진입 조건

```python
# 은신 진입 조건
is_stealth_posture = posture == "crouch"
no_npcs_in_location = len(get_npcs_in_location(player_location)) == 0

if is_stealth_posture and no_npcs_in_location:
    set_prop(player_id, "status:stealth", 1)
```

#### 상태 전환

| 조건 | 동작 | 결과 |
|------|------|------|
| NPC 발각 | `status:stealth` 제거 + `clear_player_meetings` | 일반 상태 + on_meet 재발생 |
| 자발적 해제 (일어서기) | `status:stealth` 제거 + `clear_player_meetings` | 일반 상태 + on_meet 재발생 |
| 공개 행동 (대화, 스킨십) | `status:stealth` 제거 + `clear_player_meetings` | 일반 상태 + 행동 종료 후 on_meet |
| 휴대 광원 켜기 | `status:stealth` 제거 | 일반 상태 |
| 챕터 전환 | `status:stealth` 제거 | 일반 상태 |

### 3.2 NPC 은신

NPC도 `status:stealth=1` prop으로 은신 가능.

```python
# NPC 은신 진입
stealth.enter_stealth(npc_id)    # posture:crouch + status:stealth=1

# NPC 은신 해제
stealth.exit_unit_stealth(npc_id)  # prop 정리 + standing 복귀

# 은신 여부 확인
stealth.is_unit_stealthed(npc_id)  # True/False
```

은신 NPC는 다음에서 제외됨:
- **LookResult** (C#): `unit_system.cs` LookFromLocation() 필터
- **describe text** (Python): `get_all_describe_texts()` 필터
- **이벤트** (Python): meet/contact 핸들러 수집 시 제외

### 3.3 UI 표시 (Footer)

```
[웅크리기]                     # standing 상태 → 클릭하면 crouch 진입
[일어서기] (은신 중)           # crouch + 은신 중 → 클릭하면 standing 복귀
[일어서기]                     # crouch + 비은신 → 클릭하면 standing 복귀
자세: 앉기 (이동 불가)          # 앉기/눕기
```

---

## 4. 발각 판정

### 4.1 기본 공식 (NPC → 플레이어)

```python
# 30분 기준 발각 확률
detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력

# 예시: 밝기 80% × 자세 0.5 × 엄폐 0.6 × 감지력 1.0 = 24%
```

### 4.2 NPC 감지 공식 (플레이어 → 은신 NPC)

```python
# 플레이어가 은신 NPC를 발견할 확률
npc_detection_rate = 밝기 × NPC자세계수 × NPC엄폐계수 × 플레이어감지력
```

### 4.3 변수 상세

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
| standing (통상) | 1.0 |
| crouch (은신) | 0.5 |

#### 엄폐 계수

| 상황 | 계수 |
|------|------|
| 오브젝트 근접 (X 거리 ≤ 5) | 0.3 |
| 오브젝트 중간 (X 거리 ≤ 15) | 0.6 |
| 엄폐물 없음 | 1.0 |

#### 감지력

| 대상 | 감지력 |
|------|--------|
| 기본 | 1.0 |
| 세라 (경비) | 1.5 |
| 잠든 NPC | 0.1 |
| 플레이어 기본 | 1.0 |

### 4.4 NPC 감지 타이밍

| 타이밍 | 설명 |
|--------|------|
| Location 도착 | 플레이어가 Location에 도착하면 자동 감지 판정 |
| 30분 주기 | `subscribe_time_elapsed` 구독, 플레이어 위치 재판정 |

```python
# events/__init__.py on_reach에서
if unit_id == player_id:
    stealth_mod._ensure_initialized()  # 30분 주기 구독 등록
    stealth_mod.detect_stealthed_npcs(region_id, location_id)
```

---

## 5. 공개 행동 vs 은밀 행동

### 5.1 행동 분류

| 행동 | 분류 | 은신 해제 |
|------|------|----------|
| 대화 (`talk`) | 공개 | O |
| 스킨십 (`romance`, `casual_affection`) | 공개 | O |
| 거래 (향후) | 공개 | O |
| 소매치기 (향후) | 은밀 | X |
| 옷 강탈 (`loot_clothing`) | 은밀 | X |
| 오브젝트 조작 | 은밀 | X |

### 5.2 자동 해제 구현

```python
# base.py의 공개 행동 메서드에서 호출
import stealth as stealth_mod
stealth_mod.auto_exit_stealth_for_interaction()
```

`auto_exit_stealth_for_interaction()`은 `status:stealth` 제거 + posture를 standing으로 복귀.

---

## 6. 이벤트 시스템 연동

### 6.1 이벤트 타입

| 타입 | 은신 판정 | 예시 |
|------|----------|------|
| 일반 이벤트 | O | first_meet, on_contact |
| forced_event | X (무조건 발동) | 챕터 전환, 보스 등장 |

### 6.2 이벤트 큐 처리 흐름

```
[이벤트 큐]
  Lina(first_meet) → Sera(first_meet) → Mila(first_meet)

[Resolve 순서]
  1. Lina: 은신 판정 성공 → 큐에서 제거, 로그 "들키지 않았다"
  2. Sera: 은신 판정 실패 → 은신 해제 + clear_player_meetings, 이벤트 진행
  3. Mila: 은신 해제 상태 → 판정 없이 이벤트 진행
```

### 6.3 은신 해제 → on_meet 재발생

은신이 해제되면 `morld.clear_player_meetings()`를 호출하여 C# `_lastMeetings`에서 플레이어의 meeting key를 제거합니다. 이후 다음 스텝에서 `DetectMeetings()`가 "새로운 만남"으로 인식하여 on_meet을 자연스럽게 큐잉합니다.

```
은신 해제 (어떤 경로든)
  → morld.clear_player_meetings()
  → C# ClearMeetingsForUnit(playerId)
  → 다음 스텝: DetectMeetings() → meeting key 없음 → OnMeet Enqueue
  → FlushEvents() → collect_event_handlers → on_meet_player 호출
```

**서순 보장**: 공개 행동(대화 등)으로 은신이 해제된 경우, 해당 행동의 dialog가 끝난 다음 스텝에서 on_meet이 발생하므로 자연스러운 서순이 유지됩니다.

**호출 위치** (`stealth.py`):
- `set_detected()` — NPC 발각 시
- `exit_unit_stealth()` — 자발적 해제 시 (플레이어인 경우)
- `auto_exit_stealth_for_interaction()` — 공개 행동(대화, 스킨십) 시

### 6.4 은신 NPC 이벤트 필터

은신 NPC는 `collect_event_handlers()`에서 meet/contact 핸들러 수집 시 제외됨.

---

## 7. 행동별 소음

> 향후 구현 예정

### 7.1 소음 레벨

| 행동 | 소음 | 비고 |
|------|------|------|
| 대기 | 0.0 | 무음 |
| 이동 (은신) | 0.1 | 낮음 |
| 이동 (통상) | 0.3 | 중간 |
| 문 열기 | 0.3 | 중간 |
| 서랍 열기 | 0.4 | 중간 |
| 아이템 줍기 | 0.2 | 낮음 |
| 소매치기 | 0.5 | 높음 |
| 달리기 | 0.8 | 매우 높음 |

### 7.2 소음 전파

- 소음 레벨 0.5 이상: 인접 Location까지 전파
- 소음 레벨 0.8 이상: 2칸 떨어진 Location까지 전파

---

## 8. 챕터 전환 처리

### 8.1 상태 리셋

```python
# stealth.py
def reset():
    """챕터 전환 초기화 — 30분 주기 구독 해제"""
    global _initialized
    _initialized = False
```

플레이어 은신 상태는 `persistence.py`의 스킵 로직으로 자동 정리:

```python
# chapters/persistence.py - restore_player_data()
if (prop_name.startswith("posture:") or
    prop_name.startswith("seated_on:") or
    prop_name == "status:stealth"):
    skipped_props.append(prop_name)
    continue
```

---

## 9. 의존 시스템

### 9.1 필요한 기존 시스템

| 시스템 | 용도 |
|--------|------|
| 자세 시스템 | 통상/은신 자세 관리 |
| 이벤트 시스템 | on_meet/on_contact 판정 |
| 시간 시스템 | 30분 주기 판정 |
| 조명 시스템 | 밝기 기반 발각 확률 |

### 9.2 구현 상태

| 항목 | 상태 | 파일 |
|------|------|------|
| 밝기 시스템 | ✅ 완료 | `lighting.py` |
| 자세별 이동 속도 | ✅ 완료 | `ui.py`, `Unit.cs` |
| 이벤트 큐 은신 판정 | ✅ 완료 | `events/__init__.py`, `event_system.cs` |
| 30분 주기 판정 | ✅ 완료 | `stealth.py` (`subscribe_time_elapsed`) |
| NPC 은신 | ✅ 완료 | `stealth.py`, `unit_system.cs` |
| 공개 행동 자동 해제 | ✅ 완료 | `base.py` (talk, romance, casual_affection) |
| 은신 해제 → on_meet 재발생 | ✅ 완료 | `stealth.py`, `script_system_morld_api.cs` (`clear_player_meetings`) |
| 소음 시스템 | 미구현 | - |

---

## 10. 관련 문서

- [movement-system.md](movement-system.md) - 자세 시스템
- [event.md](event.md) - 이벤트 시스템
- [lighting.md](lighting.md) - 조명 시스템 (밝기)
