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

```python
# GOOD: prop이 없으면 기본값 사용
def get_durability(item_id: int) -> float:
    durability = morld.get_unit_prop(item_id, "durability")
    if durability is None:
        return 1.0  # prop 없는 시나리오도 정상 동작
    return durability

# BAD: prop이 없으면 에러
durability = morld.get_unit_prop(item_id, "durability")
durability -= 0.1  # None이면 에러!
```

참고: [scenario03/docs/compatibility.md](scenarios/scenario03/docs/compatibility.md) (선택적 prop 패턴의 상세 예시)

---

## 문서 관리 규칙

- 새 문서는 대상 레이어에 따라 배치: 엔진/공통 → `docs/`, 시나리오 전용 → `scenarios/scenarioNN/docs/`
- 추가/삭제 시 해당 폴더의 README 인덱스를 함께 갱신
- 설계 계획 문서가 구현 완료되면 README에서 "완료된 설계 기록"으로 분류 변경 (내용 갱신 대신 표시만)
