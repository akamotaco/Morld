# Scenario 03: Mind The Gap — 하행선

## 문서 가이드

### 핵심 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [design.md](design.md) | 전체 컨셉, 세계관, 캐릭터, 조직문화, 게임루프, 개발철학, DLC | v0.2 |
| [demo.md](demo.md) | 데모 흐름, 14단계 시퀀스, 건축/진행 시스템, 구현 상태 | v0.2 |

### 시스템 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [agent.md](agent.md) | 분대원 성장(Vita/Sapientia), 약물, 인간성, 관계 | v0.2 |
| [combat.md](combat.md) | 1D 마이크로턴 전투, 적 설계(위협 분류 P/R/B/W), DES/FSM 구현 기반 | v0.2.5 |
| [squad.md](squad.md) | 분대 구성, 대열 순번(Rank), 분대장, party.py 구현 기반 | v0.2.5 |
| [mission.md](mission.md) | 탐사 구조, 동적 맵 연동, 기반 시스템 매핑 | v0.2.5 |
| [base.md](base.md) | 플랫폼(베이스캠프), CCTV 관찰, 시설 | v0.2 |
| [counseling.md](counseling.md) | 원격 상담, 심리/약물 시스템 연동 | v0.2 |
| [mia.md](mia.md) | MIA 처리, 구출, 유해 발견, 재활용 | v0.2 |
| [mapgen.md](mapgen.md) | 동적 맵 생성 (BSP, 2D→Location/Gate 변환) | v0.2.5 |

### 설계 배경 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [motif.md](motif.md) | 메타포 층위, 모티프 전환 배경, 관측 불가능성 (비시스템) | v0.2 |

### 기술 문서

| 문서 | 설명 | 상태 |
|------|------|------|
| [compatibility.md](compatibility.md) | 시나리오02 시스템 매핑, 호환성 원칙, 확장 패턴 | v0.2.5 |
| [shared-extensions.md](shared-extensions.md) | 시나리오02/03 공용 확장 목록 | v0.1 |
| [input.md](input.md) | 키보드 입력, 실시간 조작 | 계획 |

---

## 시나리오02 공유 시스템

시나리오03은 시나리오02의 기본 시스템을 활용한다. 대부분의 시나리오03 시스템은 **신규 구현이 아니라 기존 시스템의 확장**이다.

### 그대로 사용

| 시나리오02 시스템 | 시나리오03 활용 |
|-----------------|----------------|
| ECS 아키텍처 | 동일 |
| TextUI 시스템 | 동일 (CRT/CCTV 뷰 확장) |
| Dialog 시스템 | 동일 (원격 상담/취조에 활용) |
| DES (이산 사건 시뮬레이션) | 동일 (유일한 시간 진행 API) |
| FSM 스택 | 동일 (전투/분대 모두 FSM 기반) |
| Schedule/Agent AI | 동일 (분대원 자율 행동) |
| Region/Location/Gate | 동일 (동적 생성 추가) |
| 환경 시스템 (온도/습도/오염/혼잡/소리/조명) | 동일 |
| Asset Registry | 동일 |
| 이동/운반/연료 | 동일 |

### 확장하여 사용

| 시나리오03 시스템 | 기반 코드 | 변경 내용 |
|-----------------|----------|----------|
| 마이크로턴 전투 | CombatState (FSM) | MicroTurnCombatState 서브클래스 |
| 분대 시스템 | party.py (Squad/Order) | Rank 속성 + 공세 레벨 확장 |
| 동적 맵 생성 | Region/Location/Gate API | BSP → Location/Gate 변환 파이프라인 |
| 약물/인간성/성장 | needs.py + equip_props | prop 기반 확장 |
| MIA/보급/헌납 | survival.py + inventory.py | prop + 이벤트 확장 |

상세: [compatibility.md](compatibility.md)

참고: `scenarios/scenario02/docs/`

---

## 용어 규칙

| 맥락 | 용어 |
|------|------|
| 시스템/코드 | Agent (에이전트) |
| 문서 서술 (직책) | 분대원, 분대장 |
| 작중 호칭 | 시리얼 번호 (예: Echo-07) |
| 시설 | 플랫폼 (= 베이스캠프) |

---

## 개발 상태

- [x] 폴더 구조 생성
- [x] 기본 문서 작성
- [x] 세계관 구체화 (GDD v0.2 통합)
- [x] 시스템 문서 v0.2 갱신
- [x] 시나리오02 시스템 매핑 분석 (v0.2.5)
- [x] 구현 기반 문서화 — 전투/분대/탐사/맵생성 (v0.2.5)
- [ ] 시스템 상세 설계 (밸런스, 수치)
- [x] 데모 프로토타입 구현 (v0.2)
  - 챕터/월드 초기화, 진행 시스템, 건축 시스템
  - 이벤트 핸들러 (prologue/tutorial/mission/ending)
  - NPC/Agent 기본 구현, 테스트 79개 통과
- [ ] 분대/탐사/전투 구현

---

## 시나리오02와의 차이점 요약

| 항목 | 시나리오02 | 시나리오03 |
|------|-----------|-----------|
| 플레이어 역할 | 직접 행동 캐릭터 | 원격 지휘 오퍼레이터 |
| 시점 | 1인칭 | 3인칭 (관찰자) |
| 캐릭터 수 | 플레이어 1명 + NPC | 다수 분대원 관리 |
| 전투 | 직접 참여 (CombatState) | 간접 지시 (MicroTurnCombatState) |
| 분대 | party.py 기본 | party.py + Rank 확장 |
| 맵 | 수동 정의 | 동적 생성 (BSP) |
| 시간 | 액션 기반 | 자동 흐름 (AutoTimeFlow 적극 활용) |
