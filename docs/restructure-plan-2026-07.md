# 전체 구조 정리 계획 (2026-07)

> 5대 원칙에 대한 전수 감사(2026-07-05) 결과와 단계별 실행 계획.
> 브랜치: `wip/dialogue-hybrid`

## 5대 원칙

1. **C# 코어 단일성** — 핵심 C# 엔진은 단일 코어로 여러 시나리오를 포괄한다
2. **Python 미들웨어** — 성능이 필요한 부분은 C#으로, 전체는 mock으로 테스트 가능해야 한다
3. **서로게이트 심 플레이** — 각 시나리오는 간략화된 서로게이트 모델로 심 플레이 가능 (좀보이드/울티마급 자유도를 ring world + TEXT UI로 옮김)
4. **콘텐츠/시스템 완전 분리** — 캐릭터 등 콘텐츠 파일과 시스템 파일의 완전 분리
5. **SharpPy 정합성** — SharpPy는 외부 라이브러리 제외 CPython 3.12와 동일 결과를 내야 하며, 문제는 SharpPy 쪽을 고친다

---

## 감사 결과 요약 (원칙별 현황)

### 원칙 1 — C# 코어: 대체로 양호, 위반 3건

- ✅ prop 기반 제네릭 코어 설계 유지. 캐릭터/장소/시나리오ID 하드코딩 분기 없음. 결박 API 승격(53a1050)은 C#이 아닌 Python 공용 엔진으로 승격한 모범 사례.
- 🔴 **`scripts/system/weather_system.cs`** — S02 날씨 콘텐츠(계절 온도, 전이 확률 매트릭스)가 C#에 이식되어 **모든 시나리오에 무조건 등록**됨 (`GameEngine.cs:126`)
- 🟠 `action_system.cs:449` — S03 전용 `driver_seat`/`drive` 액션 분기 (미구현 TODO 잔재)
- 🟠 `MetaActionHandler.Navigation.cs:684` — S04 전용 `party` 모듈명을 C#이 하드코딩 (`recruit:`/`dismiss:`)
- 🟡 한국어 prop 키 `"상태:이동중"` 8개 지점 직접 조회, 아이템 taxonomy/조사(을·를) 처리/UI 라벨이 엔진에 내장
- 🟡 시나리오 선택이 Godot `[Export]` 문자열 1개 → 런타임 전환 불가

### 원칙 2 — Python 미들웨어: mock 가능하나 인프라 분산, 성능 루프 잔존

- ✅ 엔진 모듈은 전부 `import morld`만 사용 → `sys.modules` 주입으로 모킹 가능
- 🔴 **mock 3벌 분산**: S02 `mock_morld.py`(578줄) / S03(254줄 별도 구현) / S04(테스트 파일마다 인라인). conftest.py 0건 → API 변경 시 drift. **HEAD 회귀 버그(c1b7348)의 근원이 바로 mock↔실API 계약 불일치** (`get_unit_prop` 부재 시 mock은 `None`, 실제 C#은 `PyInt(0)` — `script_system_data_api.cs:1586`)
- 🔴 `engine/quest_reporter.py` — 전역 핸들러 dict에 `reset()` 없음 (챕터 전환/테스트 간 상태 오염). reset 누락 모듈 15개
- 🟠 **C# 승격 후보 (성능)**: ① `engine/sound.py` BFS 전파(매 액션/이동마다) ② `engine/temperature.py` 시간틱 전체 로케이션×장비 순회 ③ `engine/pollution.py` 시간틱 3회 전체 순회 ④ `combat.py` 실시간 해석
- 🟠 `scenario03/python/build.py` — engine/build.py의 **분기된 포크**(shim 아님). S03은 `from engine import` 0건으로 엔진 계층 미편입 세대

### 원칙 4 — 콘텐츠/시스템 분리: 영역별 극단적 편차

- ✅ 아키타입 공용 대사는 yaml 이관 완료(87개). S04 호출부는 로직만 남김. 공용 시스템은 캐릭터 이름 비의존
- 🔴 **S02 캐릭터 파일 6종(1,000~2,050줄)** — 데이터 + 수백 줄 대사 + Agent AI/상점 알고리즘 삼중 혼재 (`faye.py`: 거래 UI 제너레이터 793~972행, 텔레포트 스케줄러, buyback FIFO까지)
- 🟠 **콘텐츠 딕셔너리가 .py로 위장**: `aftermath_templates.py`(203 문자열), `masturbation_templates.py`, `positive_memory_templates.py`, `combat_reactions.py`, `creature_reactions.py`, `romance_body_reaction.py` — 전부 archetype 키 구조라 yaml 체계와 동형
- 🟠 S02 캐릭터 고유 대사 yaml 스텁(`리나.yaml` 등)은 헤더만 존재 — 실 콘텐츠는 여전히 py에
- 🟡 `story.py:32-244` — `MANSION_MEMBERS`/`밀라` 특수 분기 등 캐릭터 이름 리터럴이 시스템 로직에 결합 (유일한 실위반)
- 🟡 `scenario04/quirk.py` QUIRKS, `character_randomizer.py` — 데이터+설명 in-code

### 원칙 5 — SharpPy: upstream 수정 대상 명확

- 런타임 이원화: 테스트=CPython(+pytest/run_tests.py), 프로덕션=SharpPy(Godot 내). 서브모듈 `util/sharpPy` @ v0.4.9(godot 브랜치)
- 우회 코드 목록: `inspect` 미지원(S02/S04 assets/__init__.py 중복 우회), `traceback.print_exc` 삼킴(think/registry.py:52), `deque` 회피(map_coords.py:134), 상수 풀 PyBool/PyInt 병합 방어(script_system_generator.cs:271)
- ⚠️ `dialogue_hybrid`가 **pyyaml 의존** — SharpPy 런타임 미탑재 시 크래시 위험. 콘텐츠 yaml 이관 확대와 충돌하는 지점 → **데이터 포맷 전략 결정 필요** (아래 P1 참고)

### 원칙 3 — 서로게이트 심 플레이: 설계 방향성 (감사 대상 아님)

ring world + TEXT UI 골격은 이미 엔진의 형태. 이 원칙은 P2(엔진 순화)와 P5(시나리오 로딩 일반화)의 **판단 기준**으로 사용: "이 코드가 없어도 새 시나리오가 심을 돌릴 수 있는가?"

---

## 실행 계획

### P0 — 테스트 신뢰성 회복 (즉시, 저위험)

| # | 작업 | 대상 |
|---|------|------|
| P0-1 | 공유 mock을 `scenarios/common/python/testing/mock_morld.py`로 통합, **실 C# API 계약과 일치화** (`get_unit_prop` 부재 시 0 반환 등) | mock 3벌 → 1벌 |
| P0-2 | 시나리오별 conftest.py 도입 (sys.path + mock 주입 일원화), S04 인라인 mock 제거 | tests/ |
| P0-3 | `quest_reporter.py` reset() 추가 + reset 누락 15개 모듈 빈 reset() 보강 | engine/ |
| P0-4 | 환경 시스템(temperature/humidity/pollution/sound/congestion) 엔진 직접 단위 테스트 신설 | engine/ (P3 승격 전 안전망) |

### P1 — 콘텐츠/시스템 분리 (파일 정리 본체)

| # | 작업 | 대상 |
|---|------|------|
| P1-0 | ~~데이터 포맷 결정~~ → **확정: yaml 저작 + 빌드타임 json/py-dict 컴파일** (런타임 pyyaml 비의존, 기존 87개 yaml 유지) | ✅ 결정됨 (2026-07-05) |
| P1-1 | `*_templates.py` 6종 → 아키타입 데이터 파일 이관 (구조 동형, 기계적) | scenario02 |
| P1-2 | S02 캐릭터 파일 3분할: ① props/스케줄 데이터 ② 대사 → `dialogues/characters/*.yaml` 스텁 채우기 ③ Agent/상점 로직 → `think/agents/` | sera/mila/lina/yuki/ella/faye.py |
| P1-3 | `story.py` 이름 리터럴 제거 → 캐릭터 prop(`저택멤버`, `목격:관용` 등) 기반 | scenario02 |
| P1-4 | `quirk.py`/`character_randomizer.py` 데이터부 분리 | scenario04 |
| P1-5 | 루트 잡동사니 정리 (`nul` 파일 등) | 루트 |

### P2 — C# 코어 순화

| # | 작업 | 대상 |
|---|------|------|
| P2-1 | WeatherSystem → Python 콘텐츠 환원 (또는 시나리오 opt-in 등록) | weather_system.cs |
| P2-2 | `driver_seat`/`drive`, `party` 하드코딩 → prop/콜백 기반 제네릭 액션 등록 메커니즘 | action_system.cs, MetaActionHandler |
| P2-3 | 한국어 prop 키 상수 추출, 문장 템플릿/taxonomy/라벨 콘텐츠 레이어 이관 | 8개 지점 |

### P3 — 성능 승격 (Python → C#)

우선순위: ① sound BFS ② temperature 시간틱 ③ pollution 시간틱 (④ combat은 보류).
방식: morld API 뒤에 C# 구현을 두고 Python 쪽은 얇은 호출부만 남김 → mock 테스트 가능성 유지 (P0-4의 테스트가 승격 전후 동일 결과 검증).

### P4 — SharpPy upstream 수정 (util/sharpPy, godot 브랜치)

1. `inspect.signature` 최소 지원 → S02/S04 `__code__` 우회 제거
2. `traceback` 안정화 → registry.py 예외 삼킴 제거
3. 상수 풀 PyBool/PyInt 병합 근본 수정 (+회귀 테스트) → generator.cs 방어 코드 제거
4. `collections.deque` 검증 → map_coords.py list 우회 제거
5. pyyaml 대응 (P1-0 결정에 종속)
6. CI: 핵심 엔진 테스트를 CPython과 SharpPy(run_tests.py) 양쪽에서 실행해 시맨틱 divergence 조기 검출

### P5 — 시나리오 정합 / 멀티 시나리오

1. `scenario03/build.py` 포크 해소 (engine shim 전환 또는 S03 엔진 편입)
2. 시나리오 선택 `[Export]` → 런타임 선택 메커니즘

---

## 진행 상태

- [x] **P0 테스트 신뢰성 — 완료 (2026-07-05, 커밋 662ad7e/f1efc9c/+)**
  - 공유 mock 단일본(`common/python/testing/mock_morld.py`) + S02/S03 shim 전환
  - `get_unit_prop` 실계약(부재=0) 일치 → **잠복 실버그 11건 수정**
    (월경 오판정·주기 미초기화, 다리부상 이동속도 0 고정, 세력관계 override 무력화,
    is_vehicle 전유닛 오판, 상점 재고 항상 0, 시작 소지금 미지급 등)
  - S03 테스트 부활: 109통과/46에러 → **153/153** (dungeon 경로 + expedition 3-튜플 프로덕션 수정)
  - reset 계약: quest_reporter/body_state 실질 reset + 누락 14개 모듈 보강,
    엔진 전 모듈 reset 준수를 강제하는 계약 테스트 추가
  - 엔진 환경 시스템 직접 테스트 신설: `common/python/tests/` (17개)
  - 발견: `engine/build.py`가 시나리오 `assets` 레이어 import (의존성 규칙 위반)
    — 톱레벨은 lazy로 임시 해소, 구조적 역전은 P5에서
  - 이월: S04 인라인 mock 전면 통합(계약만 일치시킴 — 테스트 본문이 mock 내부에 결합),
    CI에서 SharpPy 런타임으로도 테스트 실행(P4-6)
  - 최종: 엔진 17/17 · S02 1555/1555 · S03 153/153 · S04 67/67
- [ ] P1 콘텐츠/시스템 분리 (P1-0 포맷 확정됨: yaml + 빌드타임 컴파일)
- [ ] P2 C# 코어 순화
- [ ] P3 성능 승격
- [ ] P4 SharpPy upstream
- [ ] P5 시나리오 정합 (+ engine/build.py assets 의존 역전 추가)

완료 시 이 문서를 `docs/README.md`에서 "완료된 설계 기록"으로 분류 변경할 것.
