# Morld 문서 가이드

Morld는 하나의 엔진(C# ECS + Python 콘텐츠 레이어) 위에서 여러 시나리오를 구동하는 프로젝트입니다.

> **작업 시작 전**: 작업 대상 시나리오의 `docs/README.md`를 먼저 읽으세요. 각 시나리오 docs 폴더에 작업별 문서 인덱스가 있습니다.

---

## 시나리오 한눈에 보기

| 시나리오 | 이름/테마 | 상태 | 문서 인덱스 |
|----------|-----------|------|-------------|
| scenario01 | 방 탈출 퍼즐 (NPC 없음) | 🧊 동결 (레거시 프로토타입) | `scenarios/scenario01/DESIGN.md` |
| **scenario02** | **숲속 저택** — 연애 + 생활 시뮬레이션 | ✅ 메인 시나리오 (유지보수 활발) | [scenario02/docs/README.md](scenarios/scenario02/docs/README.md) |
| scenario03 | Mind The Gap: 하행선 — 지저철 원격지휘 스릴러 | ⏸️ 데모 완료, 휴면 | [scenario03/docs/README.md](scenarios/scenario03/docs/README.md) |
| **scenario04** | **마을과 던전** — JRPG 파티 로그라이트 | 🚧 신규 개발 중 (Hybrid 대화 통합) | [scenario04/docs/README.md](scenarios/scenario04/docs/README.md) |
| common | 공용 Python 엔진(Pi-World) + Hybrid 대화 데이터 | ✅ 모든 시나리오의 기반 | [docs/README.md](docs/README.md) |

**현재 활발한 작업 갈래**: ① scenario02 유지보수/버그픽스, ② Hybrid 대화 엔진(common) + scenario04 통합, ③ 엔진 승격(시나리오 코드 → common/engine).

---

## 프로젝트 공통 문서 (`docs/`)

전체 인덱스와 문서별 최신성 판정: [docs/README.md](docs/README.md)

| 문서 | 설명 |
|------|------|
| [dialogue-hybrid.md](docs/dialogue-hybrid.md) | **Hybrid 대화 엔진** — 아키타입 공용 풀 + 캐릭터 override + S02 어댑터 + S04 통합. 가장 최신·정확 |
| [pi-world-engine.md](docs/pi-world-engine.md) | Python 공통 엔진 레이어 아키텍처 — 의존성 규칙, 에셋 프레임워크 (원칙 유효, 모듈 목록은 코드 기준) |
| [architecture-v0.3.0.md](docs/architecture-v0.3.0.md) | v0.3.0 아키텍처 — 텍스트+플랫포머 통합 (진행 표는 stale) |

나머지(perception-system, engine-think-design, movement-stealth-refactor)는 완료된 설계 기록 — 역사적 맥락용.

---

## scenario02 필수 문서 (시스템 이해)

공용 시스템의 원산지가 scenario02이므로, 어느 시나리오를 작업하든 이 5개는 기본 배경지식입니다.

| 문서 | 설명 |
|------|------|
| [system-core.md](scenarios/scenario02/docs/system-core.md) | ECS 아키텍처, 시스템 구조, 챕터 전환 라이프사이클 |
| [system-api.md](scenarios/scenario02/docs/system-api.md) | morld Python API, Asset 클래스 |
| [dialog.md](scenarios/scenario02/docs/dialog.md) | 대화/리액션/묘사 시스템 (Lines, Rules 등) |
| [system-ui.md](scenarios/scenario02/docs/system-ui.md) | TextUI, 토글, 액션 필터링 |
| [system-gameplay.md](scenarios/scenario02/docs/system-gameplay.md) | 장비, 생존, 욕구, 연애, 온도, 습도, 혼잡도, 텃밭 등 |

작업별 상세 문서(지형/캐릭터/연애/아이템/이벤트)는 [scenario02/docs/README.md](scenarios/scenario02/docs/README.md)의 표에서 찾으세요.

---

## 개발 환경 / 테스트 실행

> **CPython 인터프리터: `C:\ProgramData\miniforge3\python.exe`** (3.12.x)
> 새로 설치하지 말 것 — 이 머신에는 이미 miniforge가 있다. PATH에는 없으므로 전체 경로로 호출.

```powershell
# 시나리오 테스트 (S02/S03: run_tests.py, S04: 파일별 직접 실행)
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario02\python\tests\run_tests.py
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario03\python\tests\run_tests.py
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario04\python\tests\test_quest_board.py

# 공용 엔진 테스트
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\tests\run_tests.py

# 대화 yaml 수정 후 — 반드시 재컴파일 (SharpPy는 컴파일본만 읽음)
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\dialogues\compile_dialogues.py
```

> **대화 데이터 규약**: `dialogues/*.yaml` 수정 → 컴파일 → yaml과 `dialogues_compiled/`를
> 같은 커밋에. 상세/진단: [docs/dialogue-data-pipeline.md](docs/dialogue-data-pipeline.md)

프로덕션 런타임은 SharpPy(Godot 내장, `util/sharpPy`)이며 CPython 3.12 시맨틱을 따른다.
테스트는 CPython + 공유 mock(`scenarios/common/python/testing/mock_morld.py`)으로 실행.

---

## 코드 경로 요약

| 구분 | 경로 |
|------|------|
| C# 시스템 (ECS) | `scripts/system/` |
| C# 데이터 구조 | `scripts/morld/` |
| C# 액션 핸들러 | `scripts/MetaActionHandler/` |
| **공용 Python 엔진** | `scenarios/common/python/engine/` (환경/생존/전투/AI/perception/body 시스템 등 ~50 모듈) |
| **Hybrid 대화 엔진** | `scenarios/common/python/engine/dialogue_hybrid/` |
| **Hybrid 대화 데이터** | `scenarios/common/python/dialogues/` (archetype_dialogues/ 10종 + characters/ yaml) |
| scenario02 콘텐츠 | `scenarios/scenario02/python/` (assets/, events/, think/, tone_templates/, tests/) |
| scenario03 콘텐츠 | `scenarios/scenario03/python/` |
| scenario04 콘텐츠 | `scenarios/scenario04/python/` (평면 모듈 구성, npc_dialogue.py가 대화 라우팅 허브) |

---

## 시나리오 간 호환성 원칙

> **공용 코드(C# 시스템, `common/python/engine/`) 수정 시 모든 시나리오 호환성을 고려하세요.**
> S03/S04는 S02의 핵심 시스템을 확장해서 사용합니다.

1. **선택적 속성**: 새로운 prop은 없어도 동작하도록 설계
2. **기본값 적용**: 속성이 없으면 최적/최상의 상태로 간주
3. **점진적 확장**: 기존 시스템을 수정하지 않고 확장 (서브클래스/오버라이드)

### ⚠️ prop 계약: 부재 시 0 (None 아님)

**실제 C# `get_unit_prop`은 prop이 없으면(유닛이 없어도) `None`이 아니라 `0`을 반환합니다**
(`script_system_data_api.cs`). 문자열 prop이 있으면 str을 반환합니다.
공유 mock(`scenarios/common/python/testing/mock_morld.py`)도 이 계약을 따릅니다.

```python
# GOOD: 0/None을 '부재'로 취급 (truthy 판정)
durability = morld.get_unit_prop(item_id, "내구도")
if not durability:
    durability = 100  # prop 미추적 아이템도 정상 동작

# BAD: is None 판정 — 실게임에서는 절대 None이 오지 않아 분기가 죽는다
if morld.get_unit_prop(item_id, "내구도") is None:  # 항상 False!
    ...
```

- 값 0과 부재는 **구분 불가능** — "명시적 0 오버라이드"가 필요한 설계는 별도 문자열
  prop이나 마커 prop을 사용할 것 (사례: `상점:초기화`)
- 1회 초기화 판정은 값 prop이 아닌 **마커 prop**으로
- 카운터/ID처럼 0이 유효값이 될 수 있는 prop은 1-based 설계 권장 (사례: `생식:주기일`)

참고: [scenario03/docs/compatibility.md](scenarios/scenario03/docs/compatibility.md) (선택적 prop 패턴의 상세 예시)

---

## 문서 관리 규칙

- 새 문서는 대상 레이어에 따라 배치: 엔진/공통 → `docs/`, 시나리오 전용 → `scenarios/scenarioNN/docs/`
- 추가/삭제 시 해당 폴더의 README 인덱스를 함께 갱신
- 설계 계획 문서가 구현 완료되면 README에서 "완료된 설계 기록"으로 분류 변경 (내용 갱신 대신 표시만)
