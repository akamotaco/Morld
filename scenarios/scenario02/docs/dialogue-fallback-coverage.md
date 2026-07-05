# S02 hybrid 폴백 의존 커버리지 리포트

> 생성 도구: `python/tests/dialogue_coverage_report.py` (재생성 가능)
> 배경: [infra-unification-plan-2026-07.md](../../../docs/infra-unification-plan-2026-07.md) §2-5

S02 는 대화 정책 **fixed** 를 선언한다 (`python/__init__.py`) — hybrid
동적 생성 폴백 3경로(톤 접두사 위임 / `_generate_dialogue` catch-all /
initiative `during_` 폴백)가 프로덕션에서 차단된다.

**침묵 갭**(catch-all 앞에 무조건 매칭 fallback — top-level 2D 좌표나
빈 dict 고정 텍스트 — 이 없어 fixed 에서 실제로 대사가 사라지는 키)은
모두 고정 대사로 채워졌다. 아래 표의 `hybrid catch-all` 키는 catch-all 이
구조상 최종 기본값이지만, 앞선 2D 좌표 rule 이 항상 nearest 매칭되므로
fixed 에서도 대사가 나온다 (침묵 아님).

동작 보증: 게이트는 대사만 생략하며 흐름은 유지된다 — romance 호출부는
None 을 조용히 건너뛰고, 접두사 키는 기본 키의 고정 rule 로, 트랜스는
공용 트랜스 풀로 폴백한다.

## 1. 캐릭터별 ROMANCE_REACTIONS 정적 분석

| 캐릭터 | 고정 rule 키 | hybrid catch-all 키 | **침묵 갭** | initiative during_ 갭 |
|--------|------------:|--------------------:|----------:|----------------------:|
| 세라 | 51 | 2 | 0 | 0 |
| 밀라 | 52 | 1 | 0 | 0 |
| 리나 | 52 | 1 | 0 | 0 |
| 유키 | 53 | 0 | 0 | 0 |
| 엘라 | 54 | 0 | 0 | 0 |
| 페이 | 48 | 0 | 0 | 0 |

**전체 침묵 갭: 0** (0 = fixed 정책에서 대사가 사라지는 지점 없음).
hybrid catch-all 키 = 최종 기본값이 `_generate_dialogue` 인 키. 이 중
무조건 fallback(2D 좌표/빈 dict 텍스트)이 없는 것만 침묵 갭으로 집계된다.

## 2. hybrid catch-all 키 상세 (캐릭터별)

### 세라

- catch-all 최종값이나 2D fallback 있어 안전: `deep_kiss:start`, `french_kiss:start`

### 밀라

- catch-all 최종값이나 2D fallback 있어 안전: `thrust_normal:during`

### 리나

- catch-all 최종값이나 2D fallback 있어 안전: `thrust_normal:during`

### 유키

- catch-all 의존 없음

### 엘라

- catch-all 의존 없음

### 페이

- catch-all 의존 없음

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

## 4. 갭 채움 가이드 (신규 catch-all 키 추가 시)

초기 44개 침묵 갭은 각 캐릭터 아키타입 톤의 고정 대사로 채워졌다
(hug/ecstasy/사정계/유두계/thrust). 이후 새 catch-all 키를 추가할 때:

1. `({}, "_generate_dialogue")` catch-all 앞에 무조건 매칭 rule 을 둘 것 —
   ① 2D 좌표 rule `((호감, 성욕), [...])` 여러 개 (상태별 톤) 또는
   ② 빈 dict 고정 텍스트 `({}, ["...", "..."])` (상태 중립 기본 대사)
2. 톤 접두사(forced_/trance_/ecstasy_) 키는 개별 rule 대신 기본 키의
   고정 rule 이 폴백으로 쓰인다 — 톤 구분이 필요할 때만 접두사 키를 명시
3. initiative 갭은 `INITIATIVE_REACTIONS["during_<action>"]` 추가
4. 이 도구를 재실행해 **침묵 갭 0** 을 확인할 것

