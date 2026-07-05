# Scenario 03 MVP — 반복 운영 루프

> 2026-07-05 구현. 데모(14단계)를 튜토리얼로 재해석하고, 그 뒤에 로그라이트
> 코어 루프를 붙인 MVP. 설계 원본은 [design.md](design.md) §6 게임 루프.
> MVP 범위 결정: 헌납/취조/상담/MIA/마이크로턴 전투는 **범위 외** (후속 단계).

## 루프 구조

```
튜토리얼 (기존 데모 Step 1~13)
  → Step 14: 정규 운영 개시 (ending.py → cycle.start_operations())
  → ┌─────────────────────────────────────────────┐
    │ ready    : 분대 편성/정비, CRT [탐사 출발]    │
    │ expedition: 진군/전투/수집, CRT [진군][퇴각]  │
    │ debrief  : 사후 운용 보고서 (자동)            │
    │ supply   : 정기 배급 + 결번 대체 개체 (자동)   │
    └────────────── 다음 운행 주기로 ──────────────┘
```

퇴각 명령 한 번에 `귀환 → 보고서 → 보급 → 다음 주기 ready`까지 자동 진행된다.

## 신규/변경 모듈

| 모듈 | 역할 |
|------|------|
| `cycle.py` (신규) | 운행 주기 상태 머신, 결번 처리, 차기 시리얼 재보급, 자재 재고, 보고서 |
| `npc_dialogue.py` (신규) | Hybrid 대화 어댑터 — 분대원(아키타입 풀) + 비서(cold+비서.yaml) |
| `mapgen.py` | `_populate_rooms` 실구현 — 위협(난이도별 가중치)/전리품 배치, `get_room_content()` |
| `combat.py` | 사망(HP 0 → deaths), vita 성장(승리 +1, 상한 10), 인간성 마모, prop 계약(`is None`) 버그 수정 |
| `expedition.py` | room dict에 threat/loot 반영, `collect_room_loot()`, summary 확장 |
| `squad_member.py` | `생존:체력`/`생존:체력max`/`인간성` prop, `base_hp_for_vita()` |
| `events/first_mission.py` | 방 진입: 전투 집계 + 결번 + 자동 수집 + hybrid 주변 대사 |
| `events/ending.py` | Step 14 = 데모 종료 → **정규 운영 개시** |
| `assets/objects/train.py` | CRT 액션 추가: 탐사 출발 / 운용 보고서. 퇴각 명령에 주기 마감 연결 |

## 핵심 규칙 (수치)

- **난이도 램프**: 주기 1–2 easy, 3–4 normal, 5+ hard (`cycle.difficulty_for_cycle`)
- **위협 가중치**: easy P5/B4/R1, normal P3/B3/R3/W1, hard R4/W3/B2/P1.
  입구는 항상 안전, 목표 지점은 위협+전리품 확정
- **체력**: `생존:체력 = 30 + vita*5`. HP 0 → 결번 (deaths)
- **성장**: 승리 시 생존자 vita +1 (상한 10)
- **인간성(H.I)**: 전투당 -2, 동료 결번 목격 시 추가 -5. **1-based** (0=미추적,
  하한 1) — prop 계약(부재=0) 준수
- **재보급**: 결번 역할의 차기 시리얼(`Echo-05`부터 전역 카운터)이 다음 보급에 도착.
  인간성 = `100 - 10 × 해당 역할 누적 결번 수` (하한 30) — 트라우마 계승(design §4.3)
- **정기 배급**: plank 5, concrete_block 3, metal_pipe 2, wire 2 / 주기
- **재고**: `cycle` 모듈 내 서로게이트 dict (아이템 인스턴스화는 후속 단계)

## Hybrid 대화 통합 (핵심=고정 / 주변=dynamic)

- **핵심 대사** (브리핑/계약/보고서/보급 안내): 이벤트 코드의 고정 문자열 유지
- **주변 대사** (동적 생성, 빈 문자열이면 조용히 생략):
  - 출발: `floor_descent` / 방 진입(안전): `dungeon_ambient`
  - 전투: `combat_engage` → 로그 → `combat_victory`/`combat_defeat`, 결번 시 `combat_ally_down`
  - 귀환: `vote_return` / 보급 도착 개체: daily `greet`
  - 비서: daily `greet` (characters/비서.yaml 시스템 톤 override 적용)
- **역할 → 아키타입**: assault→fierce, support→cheerful, sniper→stoic, medic→gentle
- **state 매핑** (`npc_dialogue.member_state`): fatigue=부상률, confidence=(vita-5)/5,
  affinity=(인간성-50)/50 (미추적 시 생략)

## 전멸 처리

분대 전원 결번 → 분대 자동 해산. CRT 퇴각 명령이 분대 없이 남은 원정도 회수
(`get_active_expeditions` 폴백). 보급에서 전원 차기 시리얼로 재보급되나 분대는
플레이어가 분대 관리에서 재편성해야 한다.

## 테스트

```powershell
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario03\python\tests\run_tests.py
```

15 modules, 188 tests. 신규: `test_cycle.py` (라이프사이클/결번/재보급/보고서/전체
루프 통합), `test_npc_dialogue.py` (아키타입 매핑/state/대사 생성/비서 톤).
combat 사망·성장·prop 계약 테스트는 `test_combat.py`에 추가.

## 후속 후보 (범위 외로 미룬 것)

- 헌납(운행 기여), 취조실, 원격 상담, MIA/구출
- 마이크로턴 전투 (현행: 자동 해결)
- 수집 자재의 실제 아이템 인스턴스화 + 건축 소비 연동
- CRT 뷰 C# UI (`set_view_mode("crt")`)
- 사후 운용 보고서의 회차 종합판 (관리 성향 분석, '하지 않음'의 기록)
