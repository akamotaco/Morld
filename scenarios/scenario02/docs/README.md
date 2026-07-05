# Scenario02 문서 인덱스 — 숲속 저택

> **시나리오 개요**: 기억을 잃은 남자가 숲속 저택에서 여성들과 함께 생활하는 연애 + 생활 시뮬레이션.
> 프로젝트의 **메인 시나리오**이자 공용 시스템의 원산지 — S03/S04가 이 시나리오의 시스템을 확장해서 사용합니다.
>
> - 코드: `../python/` (약 230개 파일, tests 25개 포함)
> - 주요 캐릭터: 리나, 밀라, 세라, 엘라, 페이, 유키 (`../python/assets/characters/`)
> - 세계관/설계 철학: [design.md](design.md)

## 필수 문서 (시스템 이해)

| 문서 | 설명 |
|------|------|
| [system-core.md](system-core.md) | ECS 아키텍처, 시스템 구조, 챕터 전환 라이프사이클 |
| [system-api.md](system-api.md) | morld Python API, Asset 클래스 |
| [dialog.md](dialog.md) | 대화/리액션/묘사 시스템 (Lines, Rules 등) — Hybrid 엔진 연동은 루트 [docs/dialogue-hybrid.md](../../../docs/dialogue-hybrid.md) |
| [system-ui.md](system-ui.md) | TextUI, 토글, 액션 필터링 |
| [system-gameplay.md](system-gameplay.md) | 장비, 생존, 욕구, 연애, 온도, 습도, 혼잡도, 텃밭 등 게임플레이 시스템 |

## 작업별 참고 문서

### 지형/맵

| 작업 | 문서 |
|------|------|
| Region/Location/Gate 구조 | [terrain.md](terrain.md) |
| 환경 속성 (온도, 습도, 날씨) | [terrain_property.md](terrain_property.md) |
| 조명 (밝기, 광원) | [lighting.md](lighting.md) |
| 던전 | [dungeon.md](dungeon.md), [instant-dungeon.md](instant-dungeon.md) |
| 바닥 오브젝트 | [ground.md](ground.md) |

### 캐릭터/NPC

| 작업 | 문서 |
|------|------|
| 대화/리액션/묘사 | [dialog.md](dialog.md) |
| 대화 정책(fixed) hybrid 폴백 갭 | [dialogue-fallback-coverage.md](dialogue-fallback-coverage.md) (도구로 재생성) |
| 애니메이션 연출 (컷씬, 전투) | [system-ui.md#animlog](system-ui.md#animlog-애니메이션-시퀀스) |
| 자세/착석 (앉기, 눕기) | [movement-system.md#4](movement-system.md#4-자세posture-시스템) |
| 은신 (잠입, 발각) | [stealth.md](stealth.md) |
| NPC 스케줄/AI/Agent | [schedule.md](schedule.md) |
| NPC 생활/욕구/자율행동 | [life.md](life.md) |
| 행동 제어 (BaseAgent/CreatureAgent/FayeAgent) | [behavior-guide.md](behavior-guide.md) |
| 노화/성장 | [aging.md](aging.md) |
| 전투 | [battle.md](battle.md) (설계) + [combat-implementation.md](combat-implementation.md) (구현 명세) |
| 생물(Creature) | [creature.md](creature.md) |
| 파티 | [party-guide.md](party-guide.md) (사용 가이드), [party-design-notes.md](party-design-notes.md) (설계) |
| 퀘스트 | [quest.md](quest.md) |
| 캐릭터 만들기 | [make_character.md](make_character.md) |
| 활동(Activity) 만들기 | [make_activity.md](make_activity.md) |
| 차량 | [vehicle-system.md](vehicle-system.md) (설계) + [make_vehicle.md](make_vehicle.md) (제작 가이드) |

### 연애 시스템 (인덱스: [romance.md](romance.md))

| 작업 | 문서 |
|------|------|
| 관계 (라벨/욕망/해금/성별) | [romance-relationship.md](romance-relationship.md) |
| 애정 행위 (스킨십/자극/탈의/동작모드) | [romance-actions.md](romance-actions.md) |
| 임신과 출산 | [romance-pregnancy.md](romance-pregnancy.md) |
| 동참(합류) | [romance-join.md](romance-join.md) |
| 성인용품/결박/절정 | [adult-toys.md](adult-toys.md) |

### 아이템

| 작업 | 문서 |
|------|------|
| 의류/장비 | [clothes.md](clothes.md) |
| 음식/요리 | [food.md](food.md) |
| 크래프팅 | [craft.md](craft.md) |
| 건축/파괴 | [build.md](build.md) |

### 이벤트/시스템

| 작업 | 문서 |
|------|------|
| 이벤트 (on_meet, on_reach, on_leave) | [event.md](event.md) |
| 운반 (Limbo + 포인터 아이템) | [carry.md](carry.md) |
| 시간 정지 (Frozen) | [frozen.md](frozen.md) |
| 시간 흐름 | [time-flow.md](time-flow.md) |
| 테스트 | [test_morld.md](test_morld.md) ⚠️ 오래됨 — 실제 테스트는 `../python/tests/` 기준 |

## 설계·분석·이력 문서 (시점 기록 — 갱신하지 않음)

현재 코드 상태를 보증하지 않는 문서들입니다. 맥락 파악용으로만 참조하세요.

| 문서 | 성격 |
|------|------|
| [map.md](map.md) | ⚠️ **미구현 계획** — "지도 시스템 (계획)". Map 계층 구조를 제안했으나 실제 Location은 여전히 평면 구조 |
| [party-implementation.md](party-implementation.md) | 파티 시스템 v1 구현 명세 — [party-design-notes.md](party-design-notes.md)로 대체됨 |
| [chapter1-plan.md](chapter1-plan.md) / [chapter1-routes.md](chapter1-routes.md) | 챕터1 기획/루트 설계 |
| [romance-expansion-design.md](romance-expansion-design.md) | 연애 확장 설계 |
| [romance-stat-spec.md](romance-stat-spec.md) / [romance-trajectory-analysis.md](romance-trajectory-analysis.md) | 연애 수치 스펙/궤적 분석 |
| [era-series-analysis.md](era-series-analysis.md) | 레퍼런스 게임(Era 시리즈) 분석 |
| [review-report-2026-02-21.md](review-report-2026-02-21.md) | 2026-02-21 시점 코드 리뷰 스냅샷 |

## 문서 관리 규칙

- 새 문서 추가 시 이 README의 해당 절에 등록
- 계획 문서가 구현 완료되면: 내용을 해당 시스템 문서로 흡수하고, 원본은 "설계·분석·이력" 절로 이동
