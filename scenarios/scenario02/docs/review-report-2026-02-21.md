# 코드 검토 보고서 (2026-02-21)

## 1. 로맨스 라이프사이클

### BUG-1: `cur_mode` 미정의 — NameError 크래시 [CRITICAL]
- **위치**: romance.py:1097, 1113
- **내용**: pull_out_target 핸들러에서 `cur_mode` 미정의. 시간정지 모드 질외사정 시 NameError.
- **수정**: `cur_mode = state["mode_ctx"]["mode"]` 추가

### BUG-2: `apply_effects.__wrapped__` — 데드코드 [HIGH]
- **위치**: romance.py:1534
- **내용**: `apply_effects`는 데코레이터 없는 일반 함수 → `__wrapped__` 항상 없음 → ecstasy 항상 None
- **영향**: hold_back 실패 → 강제 절정 시 절정 반응 텍스트 미표시
- **수정**: `apply_effects(climax_info, active_toggle_defs)` 직접 호출

### BUG-3: `restrain_partner` / `unrestrain_partner` 미구현 [HIGH]
- **위치**: romance_actions.py:357-368 (정의), romance.py (핸들러 없음)
- **내용**: `requires_inventory_category`, `resistance_check` 필드 정의되었지만 체크하는 코드 없음
- **영향**: 액션 사용 시 효과만 적용, 실제 결박 미적용

### INFO-1: 포커스 메뉴 `loot_clothing` 잔존
- **위치**: base.py:1500-1539
- **내용**: 포커스 메뉴용 옷 강탈 (부위 선택 없음) vs 로맨스용 loot_upper/loot_lower (부위별)
- **상태**: 의도적 분리인지 확인 필요

---

## 2. NPC 스케줄 + 욕구 + 오브젝트

### BUG-4: safety net에 `laundry_phase` 누락 [LOW]
- **위치**: think/__init__.py:1380-1383
- **내용**: 세탁 진행 중 action 미설정 시 디버그 경고에 laundry_phase 미표시

### 오탐 확인
- `_ensure_standing()` → think/__init__.py:448에 정상 존재
- 스케줄/인터럽트 상태 분리 → 의도된 설계

---

## 3. 결박 시스템

### BUG-5: `restrained_phase` 메모리 미정리 [MEDIUM]
- **위치**: think/__init__.py:691-758
- **내용**: 외부 해제 시 phase 리셋 안 됨 → 재결박 시 stale 상태 재개 가능
- **수정**: 진입부 가드 또는 해방 시 대상 메모리 정리

### BUG-6: 상체 결박 wandering 복종도 미증가 [LOW]
- **위치**: think/__init__.py:803-810
- **내용**: 하체 결박은 +0.5/30분, 상체 결박은 0 → 불균형

### BUG-7: `can_use_hands()` 미사용 [MEDIUM]
- **위치**: restraint.py:72-79
- **내용**: 정의만 있고 호출처 0건 → 상체 결박 중 장비 제한 없음

### OK: NPC → NPC 해방
- think/__init__.py:819-857 `_check_restrained_nearby()` 정상 구현

### OK: 결박 + 탈출 확률 연동
- romance_mode.py:407 `get_escape_multiplier()` 정상 사용

---

## 요약

| # | 심각도 | 영역 | 문제 | 위치 |
|---|--------|------|------|------|
| BUG-1 | CRITICAL | 로맨스 | `cur_mode` NameError | romance.py:1097,1113 |
| BUG-2 | HIGH | 로맨스 | `__wrapped__` 데드코드 | romance.py:1534 |
| BUG-3 | HIGH | 로맨스 | restrain/unrestrain 미구현 | romance.py |
| BUG-4 | LOW | NPC | safety net laundry_phase 누락 | think/__init__.py:1380 |
| BUG-5 | MEDIUM | 결박 | restrained_phase 메모리 누수 | think/__init__.py:691+ |
| BUG-6 | LOW | 결박 | 상체 결박 복종도 미증가 | think/__init__.py:803 |
| BUG-7 | MEDIUM | 결박 | can_use_hands() 미사용 | restraint.py:72 |
| INFO-1 | 확인 필요 | 로맨스 | 포커스 메뉴 loot_clothing 잔존 | base.py:1500 |
