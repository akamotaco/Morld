# S02/03/04 인프라 통합 계획 (2026-07)

> 목표: **통합 시스템(C# 코어 + Python 인프라) + 콘텐츠 팩** 구조로 전환하여,
> 콘텐츠 확장만으로 다양한 텍스트 기반 게임을 제작하는 툴로 활용한다.
> [restructure-plan-2026-07.md](restructure-plan-2026-07.md)의 P1/P5를 구체화·확장하는 계획.
> 분석 일자: 2026-07-05 (4축 병렬 조사 결과 기반)

## 요구사항 (사용자 확정)

1. **통합 인프라** = C# 코어 + Python 인프라 시스템. 시나리오는 그 위의 콘텐츠 팩.
2. **대화 시스템은 선택 사항** — S02는 동적(hybrid) 대화 미사용으로 운용 가능해야 하며,
   이것이 통합 시스템의 커버리지(고정 대사 게임 ~ 동적 대사 게임)를 증명한다.
3. **캐릭터 = 독립 파일** — 확장성/독립성 확보. 향후 커스텀 시나리오·커스텀 캐릭터 제공 기반.
4. **스쿼드(S03)와 파티(S04)를 하나의 시스템으로** — 플레이어 캐릭터가 없는 경우(S03)에도
   동작해야 하고, S03에 플레이어 캐릭터를 추가하는 것도 가능해야 한다.

---

## 1. 현황 진단 (4축 조사 요약)

핵심 결론: **모든 축에서 engine 정본이 이미 존재한다. 통합은 신규 설계가 아니라
"이관 완성 + 계약 정리" 작업이다.** 채택 현황이 축·시나리오별로 제각각인 것이 문제의 전부.

### 1-A. Agent AI (think)

| | S02 | S03 | S04 |
|---|---|---|---|
| 코어 채택 | 부분 (`engine.think` re-export + Mixin 6종) | **미채택** (자체 registry + 자체 BaseAgent) | 완전 (`think.py` = `engine.think` alias) |

- 정본: `engine/think.py`(registry+dispatcher), `engine/think_base.py`(BaseAgent), `engine/fsm.py`, `engine/perception.py`
- C# 계약은 단 하나: `import think; think.think_all()` (`think_system.cs:54` → `script_system.cs:1272`)
- S02 고유물(공용화 불가): `_memory` 서사 필드, S02 모듈 직접 import, 한국어 activity 리터럴, prop 스키마
- 승격 후보(순수 구조): 스케줄 스택(push/pop/base), 5-Tier think 골격, activity 디스패치 루프, resolver 프레임

### 1-B. 파티/스쿼드

실체는 "3개 시스템"이 아니라 **엔진 2계열 + 독립 사본 1개**:

| | `engine/party_group` (S04) | `engine/party_squad` (S02) | `scenario03/squad.py` (사본) |
|---|---|---|---|
| 강점 | merge/split/리더 승계(`ensure_valid_leadership`), 콜백 확장점, "솔로도 파티" 원칙, leader-agnostic | follow 스케줄+FSM phase+gate 동기화, directive 7종, Order(duration 포함) | rank(전위/중위/후위), aggression 5단계(-2~+2), 플레이어 무관 다중 분대 |
| 결함 | follow/FSM 없음(텔레포트 임시), 지휘 상태 없음 | 승계/merge/split 없음 | 엔진 미편입, FSM 없음 |
| 리더 표현 | `members[0]` | `leader_id` 분리 | `leader_id` 분리 |
| 인원 상한 | 리더 **포함** 4 | 리더 **제외** 3 (=총 4) | 리더 제외 3 |

- C# 하드코딩: `MetaActionHandler.Navigation.cs:693,708`이 `"import party; party.add_member/remove_member"` 문자열 직결 — **recruit.py의 수락 판정을 우회**하는 버그성 결합 포함
- S04 `npc_party_ai.py`(몬스터 파티 추상 시뮬)는 엔진과 별개 레지스트리 — 통합 시 공존/흡수 결정 필요

### 1-C. Asset 프레임워크

- 정본: `engine/asset_base.py`(Template Method, `*Base` 계층) + `engine/asset_registry.py`(등록 데코레이터 + unique_id↔instance_id 맵)
- 채택: S04 완전(189줄 얇은 확장, **레퍼런스**) / S02 상속은 완료됐으나 base.py가 6,100줄 게임플레이 덩어리 / S03 미이주 스텁(113줄, 주석에 "공용 분리 전까지 임시" 명시) / S01 미이주 레거시(동결)
- C#은 unique_id를 불투명 문자열로만 소비 (`add_unit`/`add_item`/`call_instance_method`) → **Python 쪽 통합에 C# 변경 불필요**
- 캐릭터 분리의 실질 장애물은 S02: 캐릭터 파일 6종(1,000~2,050줄)에 데이터+대사+AI 파라미터+메서드 혼재, base.py 빌더 함수(`build_describe_rules` 등)에 강결합

### 1-D. 플레이어 캐릭터 가정

- 플레이어 지정 경로는 단 하나: `add_unit(unique_id="player")` → C#이 `PlayerId` 자동 설정 (`script_system_data_api.cs:1112`)
- 유닛 id는 1부터 발급(`IdGenerator.cs:12`) → **PlayerId=0 은 "부재"를 뜻하는 안전한 sentinel**
- **함정: `morld.get_player_id()`는 부재 시 `None`이 아니라 `0` 반환** (`script_system_morld_api.cs:63-72`) — prop 계약(부재=0)과 같은 패턴
  - `if player_id:` 가드(asset_base, fsm, party_squad 등)는 우연히 안전
  - `if player_id is None:` 가드 2곳은 **무력화 상태**: `engine/lighting.py:165,207`, `engine/fsm_dungeon.py:50`
- S03은 숨은 플레이어가 아니라 **플레이어 유닛이 아예 없음** + prologue가 C# 미결선(TODO) 상태.
  CRT 콘솔 `call:` 액션은 플레이어 위치 기준 Look UI로만 노출되므로, 실기 구동하려면
  ① 통신실에 비가시 관찰자 유닛 배치(저비용, S02/S04 파이프라인 재사용) 또는
  ② 오퍼레이터 전용 뷰 경로 신설(고비용) 중 하나가 필요
- 하드 크래시 1곳: `action_system.cs:266`(equip, 플레이어 null 시 throw) — 도달 가능성 낮으나 방어 필요

### 1-E. 대화 시스템 (요구 2 관련)

- S02는 현재 hybrid를 **폴백으로만** 사용 (Layer 1 고정 대사 우선, 미스 시 `s02_adapter` 호출)
- S03(이번 MVP)/S04는 hybrid 활성. 아키타입 풀 10종 × 8컨텍스트 커버리지 완비
- 즉 "대화 레이어 선택제"는 사실상 이미 구조가 갖춰져 있고, **시나리오 정책 스위치의 명문화**만 남음

---

## 2. 통합 설계

### 2-1. 파티/스쿼드 단일화 → `engine/party` (핵심 신규 설계)

**party_group을 데이터/생명주기 코어로 채택**하고, 나머지를 옵션 레이어로 흡수한다.

```
engine/party.py (단일 정본)
├─ 코어 (party_group 계승): Party, merge/split/transfer, ensure_valid_leadership,
│   콜백 세트(on_member_added/on_death/leadership_fn/...), "솔로도 파티" 원칙
├─ 통합 확장 (신규 필드):
│   ├─ stance: 지휘 자세 단일 축 — S03 aggression(5)과 S02 directive(7)를 흡수
│   │   {retreat, defensive, hold, engage, aggressive} + 옵션 모드(search/stealth)
│   ├─ rank: 대열 순번 1~3 (기본 2) — S03 계승, 미사용 시나리오는 무시(기본값)
│   └─ Order: party_squad 풀버전(duration_ms 포함) 계승 — 옵션
├─ follow 모듈 (party_squad 계승, opt-in): 스케줄 push/pop + FSM phase + gate 동기화
│   → 리더 실이동 시나리오(S02/S04)만 활성. S03(원격 지휘/텔레포트)은 비활성
└─ 플레이어 결합 제거: 코어는 leader-agnostic.
    "플레이어 파티" 편의 래퍼는 호환 shim으로만 유지 (player_id 부재 시 no-op)
```

**계약 정규화 (결정 사항)**
- 리더 표현: `leader_id` 프로퍼티로 통일하되 내부 저장은 `members[0]` (party_group 방식) —
  squad 계열 API(`assign_leader`/`change_leader`)는 그 위의 함수로 재구현
- 인원 상한: **"리더 포함 max_size"로 통일** (기본 4). squad 계열 `MAX_MEMBERS=3(제외)`과 수치상 동치
- stance 매핑: S03 `retreat/defensive/hold/combat_normal/combat_aggressive` → 그대로 코어 축.
  S02 directive의 `search/combat_stealth`는 모드 플래그로 분리, `auto/wait`는 stance `hold`+모드
- 시나리오 shim: `scenario02/party.py`, `scenario04/party.py`는 재배선,
  `scenario03/squad.py`는 `engine.party` shim으로 교체 (rank/aggression API 시그니처 유지)

**C# 계약 재정의**: `Navigation.cs`의 `party.add_member/remove_member` 문자열을
`party.request_recruit(unit_id)` / `party.request_dismiss(unit_id)` 단일 진입점으로 교체 —
시나리오가 이 함수를 통해 판정 로직(recruit.py 등)을 끼워 넣을 수 있게 한다
(현행 판정 우회 버그도 함께 해소).

### 2-2. 플레이어 옵션화 — "부재=0 (falsy)" 계약 채택

`get_player_id()`의 C# 반환을 바꾸지 않고, **기존 prop 계약(부재=0)과 동일한 규약으로 명문화**한다.
근거: 유닛 id는 1부터 발급되므로 0은 안전한 sentinel이고, 기존 `if player_id:` 가드 다수가
이미 이 계약에 맞게 동작 중이다. C#/SharpPy 무변경.

- [ ] `engine/lighting.py:165,207`, `engine/fsm_dungeon.py:50`의 `is None` 가드 → truthy 판정으로 수정
- [ ] `scenario03/assets/objects/construction.py:52` 등 S03의 `get_player_id()` 오용 수정
- [ ] `action_system.cs:266` equip throw → 무동작 반환 (유일한 C# 안전장치 수정)
- [ ] CLAUDE.md의 "prop 계약: 부재 시 0" 절에 player_id 계약 추가
- [ ] S03 실기 구동: 통신실(R0/L2)에 **비가시 관찰자 유닛**(`unique_id="player"`) 배치 —
  기존 Look/액션 파이프라인 무변경으로 CRT 조작 성립. 이것이 곧 "S03에 플레이어 캐릭터
  추가 가능" 요구의 실증이기도 함 (관찰자 유닛을 가시 캐릭터로 바꾸면 됨)
- 장기(선택): 오퍼레이터 전용 뷰(`set_view_mode("crt")`) — CRT 뷰 C# 확장과 함께 후속

### 2-3. think 단일화

- [ ] S03 `think/`를 S04 패턴으로 전환: `registry.py`·자체 BaseAgent 삭제 →
  `engine.think` re-export + `engine.think_base.BaseAgent` 상속 (기능 상향: perceive/evaluate 획득)
- [ ] S02 레거시 `think/registry.py` 잔재 제거 (이미 `__init__`이 engine 것을 사용)
- [ ] 승격 2종 (순수 구조만): ① 스케줄 스택(`set_base_schedule`/`push`/`pop`) →
  `engine/think_base.py` ② activity 디스패치 루프 골격 (핸들러 테이블은 시나리오 소유)
- 5-Tier 골격 승격은 **보류** — S02 tier 체커가 도메인 결합이 깊어 분리 비용 대비 효익 낮음.
  코어에는 `_on_think` 훅 유지, S02는 현행 오버라이드 지속

### 2-4. Asset 프레임워크 단일화 + 캐릭터 파일 표준

- [ ] S03 `assets/base.py` → `engine.asset_base` 재수출 shim (Rule 셀렉터/talk 골격 기능 상향)
- [ ] 인스턴스 등록 경로 단일화: `engine.asset_registry` 헬퍼로 통일 (S01 자동등록 방식은 동결 유지)
- [ ] S02 `assets/base.py` 분해 (restructure P1-2와 동일 작업, 최대 규모):
  프레임워크성 함수(`build_describe_rules` 등) → engine 승격, Character 확장부 중
  재사용 슬롯 → engine, S02 전용 → 얇은 서브클래스
- **캐릭터 표준 포맷** (콘텐츠 팩 규약):
  ```
  캐릭터 1명 =
    ① 데이터 파일 (필수): props/스탯/스케줄/선호 — 얇은 py 클래스 or yaml
    ② 대사 yaml (선택): dialogues/characters/{이름}.yaml — hybrid override
    ③ AI 클래스 (선택): think/agents/{이름}_agent.py — @register_agent_class
  ```
  참조 구현: S03 `SquadMember.configure()`(동적 정체성 주입), S04 `character_randomizer`
  (데이터 풀 + 순수 함수). S02 6종은 이 포맷으로 순차 분해.

### 2-5. 대화 레이어 선택제 (요구 2)

시나리오 정책을 명시적 스위치로: `DIALOGUE_POLICY = "fixed" | "fixed+fallback" | "hybrid"`.
- S02 = `fixed` (동적 생성 비활성 — 요구사항. 현행 폴백 사용처는 고정 대사 커버리지 확인 후 차단)
- S03/S04 = `hybrid`
- 스위치는 시나리오 부트스트랩(chapters)에서 선언 → 어댑터가 정책에 따라 폴백 경로 차단.
  ⚠️ S02 폴백 차단 시 Layer 1 미스가 빈 대사('...')로 노출될 수 있음 — 차단 전에
  커버리지 리포트(어떤 action_id가 폴백에 의존 중인지) 산출이 선행 조건.

---

## 3. 실행 단계 (위험 오름차순)

| 단계 | 내용 | 규모 | 선행 |
|------|------|------|------|
| **U0** | 플레이어 계약 정리 (§2-2: is None 가드 2곳, S03 오용, equip throw, 문서화) | 소 | — |
| **U1** | think 단일화 (§2-3: S03 전환 + 레거시 제거 + 스케줄 스택 승격) | 소 | — |
| **U2** | asset 단일화 1차 (§2-4: S03 shim + 등록 경로 통일) | 소 | — |
| **U3** | **파티 단일화** (§2-1: engine/party 신설 → S04 → S02 → S03 순 재배선, C# 진입점 교체) | 대 | U0 |
| **U4** | 캐릭터 파일 표준 + S02 base.py 분해 (§2-4 후반, restructure P1-2 통합 수행) | 대 | U2 |
| **U5** | 대화 정책 스위치 + S02 커버리지 리포트 (§2-5) | 중 | — |
| **U6** | 검증: S03 관찰자 유닛 실기 경로 + "S03에 가시 플레이어 추가" 스모크 + 전 스위트 그린 | 소 | U0~U3 |

U0/U1/U2는 독립적이므로 한 사이클에 묶어 진행 가능. U3가 리스크 중심(4개 스위트 전부 관통).

### 검증 기준 (각 단계 공통)

- 전 스위트 그린 유지: 엔진 30 · S02 1555 · S03 188 · S04 67 (+신규 계약 테스트)
- U3는 추가로: S02 파티 FSM/follow 회귀(동행 시나리오), S04 recruit/vote/승계 회귀,
  S03 다중 분대 + 무플레이어 회귀
- 최종 인수(툴화 증명): 미니 신규 시나리오를 콘텐츠 팩만으로 구성해 심 구동

### 리스크

1. **U3 파티 통합이 4개 스위트를 관통** — party_squad(FSM/follow)와 party_group(승계/merge)의
   상호 배타적 강점을 합치는 과정에서 S02 동행/S04 파티 회귀 가능성이 가장 높음.
   → 단계 내에서도 "코어 교체 → shim 유지 → 시나리오별 순차 재배선" 3단 진행
2. S02 base.py 분해(U4)는 물량이 크므로 캐릭터 1명 단위로 커밋 분할
3. SharpPy 시맨틱: 승격되는 모듈은 CPython 테스트 + 실기(Godot) 스모크 병행 (restructure P4-6)

---

## 진행 상태

- [x] **U0 플레이어 계약 — 완료 (2026-07-05)**
  - 죽은 `is None` 가드 17곳 truthy 전환 (lighting/fsm_dungeon/ui_base/temperature/
    survival/stealth/quest_reporter + S04 debug_pipeline)
  - 공유 mock 실계약화: 기본 player_id 0 + `add_unit(unique_id="player")` 자동 설정
    (S02 레거시 가정 'unit 1=주인공'은 S02 shim에서만 유지)
  - S03에 오퍼레이터 플레이어 유닛 배치 (통신실 상주, unique_id="player") —
    CRT 액션이 표준 Look 파이프라인으로 성립 + "S03에 플레이어 추가 가능" 실증
  - C#: equip 액션 플레이어 부재 시 throw → 미노출 (action_system.cs, describe_system.cs)
  - 계약 테스트 신설: common/tests/test_player_contract.py (7개)
  - CLAUDE.md prop 계약 절에 player_id 계약 추가
- [x] **U1 think 단일화 — 완료 (2026-07-05)**
  - S03 think/ → engine 정본 채택: registry 자체 사본 삭제(→re-export shim),
    자체 BaseAgent → engine.think_base 상속 (S03 잔여물: 텔레포트 이동 `_move_to_target`,
    60초 기본 duration만). 세 시나리오가 동일 think 코어 공유 달성
  - **잠복 버그 해소**: S02 think/registry.py가 별도 _agents 사본 보유 —
    party_squad.py:575 / combat_mixin.py:328의 `from think.registry import ...` 조회가
    항상 빈 사본을 보고 있었음 → engine.think 동일 객체 재수출 shim으로 교체
  - 스케줄 스택 승격: set_base_schedule/push/pop/get_current_schedule/
    fill_schedule_jobs_from/_remaining_millis_in_entry/_is_at/STAY_SCHEDULE +
    activity 슬롯 → engine/think_base.py (S02 중복 정의 제거, 상속 전환)
- [x] **U2 asset 단일화 1차 — 완료 (2026-07-05)**
  - S03 assets/base.py: 자체 최소 구현 → engine.asset_base 상속
    (Rule 셀렉터/talk 골격/Context 빌더 기능 상향, instantiate 시그니처 유지)
  - S03 assets/registry.py → engine.asset_registry 재수출 shim
  - S03 자재 4종 @register_item 등록 → get_or_create_item_id 싱글톤 생성이
    실동작 (기존 자체 구현은 조회 전용이라 항상 None → 자재 투입 불가였음)
  - S04 base.py 죽은 `player_id is None` 가드 1곳 정리 (U0 후속)
  - 남은 것(→U4): S02 base.py 6,100줄 분해, S01 이주(동결 — 보류)
- [x] **U3 파티 단일화 1·2단 — 완료 (2026-07-05)** (3단계 중 U3c 잔여)
  - `engine/party.py` 신설: party_group 코어 재수출 + stance(지휘 자세 5단계,
    search/stealth는 모드 플래그) + rank(유닛 귀속) + Order(party_squad 풀버전) +
    request_recruit/request_dismiss (시나리오 판정 핸들러 주입식)
  - S03 `squad.py` → engine.party shim: 분대가 실제 엔진 Party로 동작
    (플레이어 무관·다중 분대·리더 없는 편성 중 분대는 shim 메타데이터로 표현).
    기존 API/시맨틱 유지, 26개 squad 테스트 무수정 통과
  - S04 `party.py` alias 대상: party_group → **engine.party** (통합 facade),
    recruit.py 판정을 request_recruit 핸들러로 등록
  - C# Navigation.cs: `party.add_member/remove_member` 문자열 →
    `party.request_recruit/request_dismiss` (판정 우회 해소. 구 경로는 S02 계열과
    시그니처 불일치로 사문화 상태였음 — 어느 시나리오도 recruit:/dismiss: 액션 미생산 확인)
  - engine/party_squad에도 동일 request_* 인터페이스 추가 (S02 party alias 대응)
  - **U3c 잔여**: S02 party_squad의 directive/follow/FSM을 engine.party
    stance/모드로 재배선 + party_squad 코어를 party_group 위로 이전 (최고 리스크 —
    S02 동행/분대 회귀 스위트 확보 후 별도 사이클로)
- [ ] U4 캐릭터 파일 표준 / S02 분해
- [ ] U5 대화 정책 스위치
- [ ] U6 검증/인수

완료 시 이 문서를 docs/README.md에서 "완료된 설계 기록"으로 분류 변경할 것.
