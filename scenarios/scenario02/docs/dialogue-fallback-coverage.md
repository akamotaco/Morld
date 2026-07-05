# S02 hybrid 폴백 의존 커버리지 리포트

> 생성 도구: `python/tests/dialogue_coverage_report.py` (재생성 가능)
> 배경: [infra-unification-plan-2026-07.md](../../../docs/infra-unification-plan-2026-07.md) §2-5

S02 는 대화 정책 **fixed** 를 선언한다 (`python/__init__.py`) — hybrid
동적 생성 폴백 3경로(톤 접두사 위임 / `_generate_dialogue` catch-all /
initiative `during_` 폴백)가 프로덕션에서 차단된다. 아래는 차단으로
대사가 생략되는 지점의 전수 목록이다. **갭을 메우려면 해당 키에 고정
rule 을 추가하면 된다** (차단 지점은 런타임에 `[DialoguePolicy]` 로그로도
키당 1회 출력됨).

동작 보증: 게이트는 대사만 생략하며 흐름은 유지된다 — romance 호출부는
None 을 조용히 건너뛰고, 접두사 키는 기본 키의 고정 rule 로, 트랜스는
공용 트랜스 풀로 폴백한다.

## 1. 캐릭터별 ROMANCE_REACTIONS 정적 분석

| 캐릭터 | 고정 rule 키 | hybrid catch-all 키 | initiative during_ 갭 |
|--------|------------:|--------------------:|----------------------:|
| 세라 | 42 | 11 | 0 |
| 밀라 | 45 | 8 | 0 |
| 리나 | 45 | 8 | 0 |
| 유키 | 44 | 9 | 0 |
| 엘라 | 47 | 7 | 0 |
| 페이 | 43 | 5 | 0 |

hybrid catch-all 키 = 고정 rule 이 일부 있어도 최종 기본값이
`_generate_dialogue` 인 키. fixed 정책에서는 앞선 고정 rule 미매치 시
대사가 생략된다.

## 2. hybrid catch-all 키 상세 (캐릭터별)

### 세라

- catch-all 의존: `deep_kiss:start`, `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `french_kiss:start`, `hug:start`, `nipple_lick:start`, `nipple_suck:during`, `nipple_suck:start`, `thrust_normal:during`

### 밀라

- catch-all 의존: `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `hug:start`, `nipple_lick:start`, `nipple_suck:start`, `thrust_normal:during`

### 리나

- catch-all 의존: `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `hug:start`, `nipple_lick:start`, `nipple_suck:start`, `thrust_normal:during`

### 유키

- catch-all 의존: `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `hug:start`, `nipple_lick:start`, `nipple_suck:during`, `nipple_suck:start`, `thrust_normal:during`

### 엘라

- catch-all 의존: `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `hug:start`, `nipple_lick:start`, `nipple_suck:start`

### 페이

- catch-all 의존: `ecstasy:start`, `ejaculation_internal_구강:start`, `ejaculation_internal_음부:start`, `ejaculation_internal_항문:start`, `hug:start`

## 3. 동적 캡처 — 테스트 스위트에서 실제 hybrid 도달 지점

기본 정책(fixed+fallback)으로 전체 스위트를 돌렸을 때 hybrid 생성기에
실제 도달한 지점. **실플레이에서 빈발하는 경로이므로 고정 rule 채움
우선순위가 가장 높다.**

> 참고: 동적 캡처는 테스트 커버리지 기준의 **하한선**이다 — e2e 테스트
> 다수가 생성기를 스텁으로 대체하므로, 실플레이 노출 범위는 §1·§2 의
> 정적 목록 전체로 간주할 것.

| 캐릭터 | action_id | timing | 도달 횟수 |
|--------|-----------|--------|----------:|
| 세라 | `breast_caress` | start | 1 |
| 세라 | `forced_breast_grope` | start | 1 |

## 4. 갭 채움 가이드

1. §3 (테스트 도달) 키부터: 해당 캐릭터 `ROMANCE_REACTIONS[key]` 의
   `({}, "_generate_dialogue")` 를 고정 텍스트 rule 로 교체하거나 앞에 추가
2. 톤 접두사(forced_/trance_/ecstasy_) 키는 개별 rule 대신 기본 키의
   고정 rule 이 폴백으로 쓰인다 — 톤 구분이 필요할 때만 접두사 키를 명시
3. initiative 갭은 `INITIATIVE_REACTIONS["during_<action>"]` 추가

