# 이동/은신 시스템 리팩터링 설계

## 현재 문제

"crouch = stealth" 가정이 엔진 전체에 퍼져있음.
- `posture:crouch` prop이 은신 상태와 이동 속도를 동시에 제어
- 은신 진입 시 강제로 crouch 자세 설정
- 은신 해제 시 강제로 standing 복원
- 감지 공식에서 posture coefficient가 은신과 결합

## 새 설계: 3축 분리

```
은신 (Stealth)     ← 독립 ON/OFF, 소리 기반 자동 해제
이동 모드 (Stance) ← 앉기/걷기/뛰기, 속도+소음+피로 결정
자세 (Posture)     ← 가구 전용 (sitting/lying), 기존 유지
```

### 1. 은신 (Stealth)

- **상태**: `status:stealth` = 0 (해제) / 1 (은신)
- **진입**: 플레이어 토글 (언제든 가능, 자세 무관)
- **해제 조건**:
  - 소리 강도 >= STEALTH_BREAK_THRESHOLD (30) → 자동 해제
  - 일어서기(crouch→standing) → **유일한 강제 해제** → 삭제 (더이상 crouch 없음)
  - NPC 감지 (시각 판정) → 기존 유지
- **감지 공식 변경**:
  ```
  기존: detection_rate = brightness × posture_coeff × cover × perception
  신규: detection_rate = brightness × stealth_visibility × cover × perception

  stealth_visibility:
    은신 OFF → 1.0 (완전 노출)
    은신 ON  → 0.3 (기본 은폐, 장비/스킬로 보정 가능)
  ```

### 2. 이동 모드 (Stance)

이동 중 캐릭터의 자세. prop: `stance:current`

| 모드 | prop 값 | 속도 | 소리 타입 | 강도 | 피로 배율 | 은신 영향 |
|------|---------|------|-----------|------|-----------|-----------|
| 앉기 | crouch | 50% | footstep_crouch | 10 | 0.5x | 유지 (10 < 30) |
| 걷기 | walk | 100% | footstep | 20 | 1.0x | 장비 의존 |
| 뛰기 | run | 150% | footstep_run | 40 | 2.0x | 해제 (40 >= 30) |

- **기본값**: walk (걷기)
- **UI**: 3단 토글 (앉기 ↔ 걷기 ↔ 뛰기)
- **가구 앉기/눕기**: stance와 별도 — 가구 사용 시 이동 불가 (기존 유지)

### 3. 자세 (Posture) — 기존 유지

- `posture:sitting`, `posture:lying` — 가구 상호작용 전용
- 이동 불가, stance 무관
- 은신과 무관 (가구에 앉아있으면 은신 유지/해제는 소리로 결정)

## 변경 상세

### engine/stealth.py

| 함수 | 변경 내용 |
|------|-----------|
| `POSTURE_DETECTION` | 삭제 → `STEALTH_VISIBILITY = {"hidden": 0.3, "visible": 1.0}` |
| `get_posture_coefficient()` | 삭제 → `get_stealth_visibility(unit_id)` (stealth prop만 확인) |
| `enter_stealth(unit_id)` | posture 조작 제거, `status:stealth=1`만 설정 |
| `exit_unit_stealth(unit_id)` | `stand_up` 파라미터 제거, posture 조작 제거 |
| `auto_exit_stealth_for_interaction()` | 삭제 (sound 시스템으로 대체 완료) |
| `is_stealth_posture()` | 삭제 (S02 ui.py) |
| `check_stealth_entry()` | 삭제 (S02 ui.py) — 은신 진입은 토글로 |
| `on_posture_changed()` | 삭제 (S02 ui.py) — posture와 stealth 분리 |
| `calculate_detection_rate()` | posture → stealth_visibility 교체 |

### C# Unit.cs

| 함수 | 변경 내용 |
|------|-----------|
| `GetPostureSpeedModifier()` | `posture:crouch` 체크 → `stance:current` prop 기반으로 변경 |
| | crouch=50, walk=100, run=150 |
| | posture:sitting/lying = 0 (이동 불가, 기존 유지) |

### UI (S02/S04)

| 항목 | 변경 내용 |
|------|-----------|
| 은신 토글 | `[url=stealth:toggle]` — ON/OFF 전환 |
| 이동 모드 | `[url=stance:cycle]` — 앉기→걷기→뛰기 순환 |
| 표시 | `[은신] 걷기` / `[은신] 앉기` / `뛰기` |

### sound.py — emit 시 stance 연동

이동 시 stance에 따라 소리 타입 자동 결정:
```python
def get_movement_sound(unit_id):
    stance = morld.get_unit_prop(unit_id, "stance:current") or "walk"
    return {
        "crouch": ("footstep_crouch", 10),
        "walk": ("footstep", 20),
        "run": ("footstep_run", 40),
    }.get(stance, ("footstep", 20))
```

### combat.py — 엄폐 보정

- 엄폐(cover)는 **stance:crouch일 때** 적용 (은신과 무관)
- 은신은 감지율에 영향, 엄폐는 전투 회피에 영향 → 독립 시스템

## 의류 소음 보정 (장비 연동)

이동/stance 변경 소리에 장비 `소음` equip_prop 적용:
- 소음 +N: 강도 × (1 + N×0.1) — 금속 갑옷
- 소음 -N: 강도 × (1 - N×0.1) — 천/가죽
- 예: 갑옷(소음+3) + 걷기(20) = 20×1.3 = 26 → 은신 유지
- 예: 갑옷(소음+3) + 뛰기(40) = 40×1.3 = 52 → 은신 해제

## 구현 순서

```
Phase A: engine/stealth.py 리팩터 (posture 분리)
Phase B: stance 시스템 신규 (prop + C# 속도)
Phase C: UI 업데이트 (S02/S04)
Phase D: combat.py 엄폐 기준 변경
Phase E: 테스트 + 정리
```

## 시나리오 호환성

- **S02**: 기존 crouch/standing 토글 → stealth 토글 + stance 토글로 분리
- **S03**: S02 기반이므로 동일
- **S04**: 파티 은신 콜백 유지, stance는 개인별

## 영향 받는 파일

### CRITICAL (반드시 변경)
- `engine/stealth.py` — posture 결합 제거
- `scenario02/python/ui.py` — 토글/표시 분리
- `scenario04/python/stealth.py` — 동일
- `scenario04/python/ui.py` — 동일

### IMPORTANT (변경 필요)
- `scripts/morld/unit/Unit.cs` — GetPostureSpeedModifier → stance 기반
- `engine/combat.py` — 엄폐 기준 변경
- `scenario04/python/chapters/__init__.py` — 콜백 등록

### MODERATE (조정 가능)
- `engine/sound.py` — stance 연동 헬퍼
- `engine/needs.py` — 뛰기 피로 (기존 `이동:달리기` 활용)
- `scenario02/python/settings.py` — 달리기 토글 → stance 통합
