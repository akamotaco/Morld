# 프로젝트 공통 문서 인덱스

> 이 폴더는 특정 시나리오에 속하지 않는 **엔진/아키텍처 수준 문서**를 담습니다.
> 시나리오별 문서는 `scenarios/scenarioNN/docs/`를 보세요. (각 폴더에 README 인덱스 있음)

문서는 두 부류로 나뉩니다:

- **📗 살아있는 참조** — 현재 코드와 동기화 유지 대상. 시스템 수정 시 함께 갱신할 것.
- **📙 완료된 설계 기록** — 리팩터/설계가 이미 실행 완료된 뒤 남은 근거 기록. 역사적 맥락 참조용이며 갱신하지 않음. 코드가 문서보다 앞서 있을 수 있음.

| 문서 | 분류 | 설명 |
|------|------|------|
| [dialogue-hybrid.md](dialogue-hybrid.md) | 📗 살아있는 참조 | Hybrid 대화 엔진 완전 레퍼런스 — 아키타입 공용 풀 + 캐릭터 yaml override, state-bias 매칭, S02 어댑터, S04 통합(Phase A~D). 코드: `scenarios/common/python/engine/dialogue_hybrid/`, 데이터: `scenarios/common/python/dialogues/`. **가장 최신·정확한 문서.** |
| [dialogue-data-pipeline.md](dialogue-data-pipeline.md) | 📗 살아있는 참조 | **대화 데이터 파이프라인** — yaml 저작 → `compile_dialogues.py` 검증·컴파일 → `dialogues_compiled/`(SharpPy 런타임용). 검증 규칙, 증상→원인→조치 진단 표, 커밋 규약. **yaml 수정 시 반드시 재컴파일.** |
| [pi-world-engine.md](pi-world-engine.md) | 📗 살아있는 참조 | Python 공통 엔진 레이어(Pi-World Engine) 아키텍처 — 의존성 규칙(Engine → Scenario 금지), 에셋 프레임워크, `reset()` 계약. ⚠️ 모듈 일람은 실제 `engine/`보다 뒤처짐(body_state/fsm/quest/perception 등 신규 모듈 미기재) — 원칙은 유효, 카탈로그는 코드 기준으로 볼 것. |
| [architecture-v0.3.0.md](architecture-v0.3.0.md) | 📗/📙 혼합 | v0.3.0 아키텍처 — 텍스트(S02/03) + 플랫포머(S04) 통합, 물리 4-시스템 분리. 아키텍처 원칙 부분은 유효하나 하단 "구현 순서" 진행 표는 stale(문서상 미착수인 gravity/movement/collision/resolve 시스템이 실제로는 `scripts/system/`에 구현됨). |
| [perception-system.md](perception-system.md) | 📙 설계 기록 (부분 구현) | 감각 4채널(청각/시각/직감/후각) 통합 프레임워크 설계. `engine/perception.py`로 착수됨. Phase별 완성도는 코드 확인 필요. |
| [engine-think-design.md](engine-think-design.md) | 📙 완료된 설계 기록 | 엔진 레벨 think 시스템(registry+dispatcher) 설계. `engine/think.py`, `engine/think_base.py`로 구현 완료. |
| [movement-stealth-refactor.md](movement-stealth-refactor.md) | 📙 완료된 설계 기록 | Stealth/Stance/Posture 3축 분리 리팩터 설계. 실행 완료(`engine/stealth.py`의 `get_stealth_visibility()` 등). 일부 함수명은 코드가 문서와 다름(코드 우선). |
| [restructure-plan-2026-07.md](restructure-plan-2026-07.md) | 📗 진행 중 계획 | 5대 원칙(C# 단일 코어/미들웨어 테스트/서로게이트 심/콘텐츠 분리/SharpPy 정합) 전수 감사 결과 + P0~P5 단계별 정리 계획 |
| [infra-unification-plan-2026-07.md](infra-unification-plan-2026-07.md) | 📙 완료된 설계 기록 | **S02/03/04 인프라 통합 — U0~U6 전 단계 완료 (2026-07-05)**. 파티·스쿼드 단일화(engine/party), 플레이어 옵션화(부재=0 계약), think/asset 정본 채택, 캐릭터 파일 표준(①데이터+②yaml+③AI), 대화 정책 스위치(engine/dialogue_policy), 인수 검증(scenario_mini 콘텐츠 팩 심 구동). 잔여 콘텐츠 작업: S02 폴백 갭 채움([리포트](../scenarios/scenario02/docs/dialogue-fallback-coverage.md)) |

## 새 문서를 추가할 때

- 엔진/공통 레이어 대상 → 이 폴더에 추가하고 이 README와 루트 `CLAUDE.md`에 등록
- 특정 시나리오 대상 → `scenarios/scenarioNN/docs/`에 추가하고 해당 README에 등록
- 리팩터/설계 계획이 **실행 완료**되면 이 표의 분류를 📙로 바꿔 표시
