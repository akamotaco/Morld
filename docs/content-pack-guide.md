# 콘텐츠 팩 제작 가이드 — 시나리오 / 캐릭터 / 대화

> 대상 독자: Morld 엔진 위에 새 시나리오(또는 기존 시나리오의 새 캐릭터)를
> 만드는 사람. 인프라 배경은
> [infra-unification-plan-2026-07.md](infra-unification-plan-2026-07.md) (완료 기록).
>
> **실전 예제 2개가 코드로 존재한다:**
> - 최소 시나리오 팩: [scenarios/scenario_mini/](../scenarios/scenario_mini/README.md) — 이 가이드의 §1~§3 전부를 8개 파일로 구현
> - 랜덤 생성 NPC: `scenarios/scenario03/python/recruit_pool.py` — §4의 참조 구현

---

## 0. 원칙: 시나리오 = 콘텐츠 팩

시나리오는 `scenarios/{이름}/python/` 아래의 **콘텐츠 팩**이다. 시스템(전투,
파티, 생존, 대화 생성, AI 골격)은 전부 `scenarios/common/python/engine/`에
있고, 팩은 그것을 **import해서 데이터를 채울 뿐** 시스템 코드를 복사하지
않는다. C#은 `[Export] _scenarioName` 하나로 팩을 선택한다.

C#이 팩에게 기대하는 계약은 두 가지뿐:
- `import think; think.think_all()` 이 동작할 것 (think/ 패키지)
- `initialize_scenario()` 전역 함수 (패키지 `__init__.py`에 노출)

## 1. 시나리오 팩 최소 골격

scenario_mini 기준 — 8개 파일이면 시나리오가 성립한다:

```
scenarios/{이름}/python/
  __init__.py          # C# 진입: from scenario import initialize_scenario
  scenario.py          # 부트스트랩: 대화 정책 선언 + initialize_scenario()
  think/__init__.py    # engine.think 재수출 + (하단) think.agents import
  think/agents/        # 캐릭터 AI (표준 ③) — 없으면 빈 패키지
  assets/characters.py # 캐릭터 데이터 (표준 ①)
  npc_dialogue.py      # hybrid 어댑터 (동적 대화를 쓸 때만)
  world.py             # 지형 + 배치 + 파티/에이전트 등록
  tests/               # 공유 mock 기반 테스트 (아래 §6)
```

부트스트랩에서 반드시 할 일 — **대화 정책 선언**:

```python
from engine import dialogue_policy
dialogue_policy.set_policy(dialogue_policy.POLICY_HYBRID)
# fixed          : 고정 대사 전용 (S02) — hybrid 폴백 전면 차단
# fixed+fallback : 고정 우선 + 미커버 지점만 hybrid (기본값)
# hybrid         : 동적 생성이 1차 레이어 (S03/S04/mini)
```

플레이어 지정은 `add_unit(unique_id="player")`가 유일한 경로 (C#이 PlayerId
자동 설정). **플레이어 없는 시나리오도 정상 동작한다** — `get_player_id()`는
부재 시 `0`을 반환하므로 가드는 반드시 truthy로 (`if not player_id:`).

## 2. 캐릭터 표준 — 캐릭터 1명 = 최대 3파일

| 파일 | 필수 | 내용 |
|------|------|------|
| ① 데이터 | ✅ | `assets/characters/{이름}.py` — props/스탯/아키타입/묘사 rule/선호 |
| ② 대사 yaml | 선택 | `scenarios/common/python/dialogues/characters/{이름}.yaml` — 아키타입 풀 override |
| ③ AI | 선택 | `think/agents/{이름}_agent.py` — `@register_agent_class("{unique_id}")` |

### ① 데이터 파일

`engine.asset_base.CharacterBase`를 상속하고, **아키타입 하나만 지정하면**
묘사(`engine.archetype_describe`)와 대사(아키타입 공용 풀)를 자동 상속한다:

```python
from engine.asset_base import CharacterBase
from engine.archetype_describe import build_describe_rules, build_focus_rules

class Mia(CharacterBase):
    unique_id = "mini_guide"
    name = "미아"
    archetype = "cheerful"   # 10종: stoic/gentle/cheerful/timid/cold/
                             #       seductive/fierce/proud/innocent/devoted
    props = {"생존:체력": 80, "생존:체력max": 80}
    DESCRIBE_RULES = build_describe_rules(
        "cheerful",
        activities=[("안내", "{name}가 광장에서 안내를 하고 있다.")],
        default_text="{name}가 광장에 서 있다.")
    FOCUS_RULES = build_focus_rules(
        "cheerful", activities=[], default_text="밝은 미소의 안내인.")
```

`instantiate()`에서 `morld.add_unit(...)`을 호출하는 글루는 시나리오가
소유한다 (scenario_mini `MiniCharacter`, S03 `assets/base.py` 참조).

### ② 대사 yaml (선택)

캐릭터 고유 말투가 필요할 때만 작성 — 아키타입 풀을 캐릭터 이름 기준으로
override한다 (참조: `dialogues/characters/비서.yaml` — cold 아키타입 위에
안드로이드/시스템 톤). **yaml 수정 후 반드시 재컴파일**:

```powershell
& "C:\ProgramData\miniforge3\python.exe" scenarios\common\python\dialogues\compile_dialogues.py
```

yaml과 `dialogues_compiled/`를 같은 커밋에 (상세: [dialogue-data-pipeline.md](dialogue-data-pipeline.md)).

### ③ AI 클래스 (선택)

`engine.think_base.BaseAgent` 상속, `_on_think()`만 구현하면 FSM/인지/
safety-net은 엔진이 처리한다. `think/agents/__init__.py`가 모듈을 import하는
순간 데코레이터가 레지스트리에 등록되고, 스폰 측은
`think.create_agent_for(unique_id, unit_id)` → `think.register_agent(...)`.

```python
@register_agent_class("mini_guide")
class MiaAgent(BaseAgent):
    def _on_think(self):
        morld.insert_job(self.unit_id, {"name": "안내", "action": "stay",
                                        "duration": 30 * 60_000})
        self._action_taken = True
```

## 3. 대화 어댑터 — 고정/동적의 경계

규약: **핵심 대사(서사 고정 지점)는 이벤트 코드의 고정 문자열, 주변 대사
(전투 외침/인사/중얼거림)는 hybrid 동적 생성. 생성 실패(빈 문자열)는
조용히 생략.**

```python
from engine.dialogue_hybrid import stateless as _st

def daily_line(unit_id, intent, rng=None):        # intent: greet/thank/complain
    name, archetype = ...                          # props에서 조회
    line = _st.generate_daily_line(archetype, name, intent, rng=rng)
    return f"{name}: 「{line}」" if line else ""
```

state 축(`fatigue`/`confidence`/`affinity`, -1.0~1.0)을 넘기면 톤이 변한다 —
S03 `npc_dialogue.member_state()`가 props→state 매핑의 참조 구현.

## 4. 랜덤 생성 NPC vs UNIQUE 캐릭터

**두 방식은 별개 시스템이 아니다** — 같은 파이프라인에서 파일(②③)의 유무
차이일 뿐이다:

| | UNIQUE (세라, 비서, 미아) | 랜덤 생성 (S03 분대원, S04 마을 NPC) |
|---|---|---|
| 정체성 출처 | 데이터 파일에 직접 기술 | **spec 테이블에서 추첨** (`engine.character_gen`) |
| 아키타입 | 파일에 고정 | 후보 풀에서 가중 추첨 → `"아키타입"` prop 저장 |
| 대사 | 아키타입 풀 + ② yaml override | 아키타입 풀만 (prop 기준 톤 결정) |
| AI | 캐릭터 전용 ③ | 클래스 공용 Agent (예: `SquadMemberAgent`) |

### 랜덤 생성 만들기 (S03 recruit_pool 패턴)

1. **spec 작성** — 순수 데이터. 역할별 기본 스탯/아키타입 풀 + 티어별
   보정/편차/추가 풀:

```python
from engine import character_gen as cg

SPEC = {
    "roles": {
        "sniper": {"base_props": {"vita": 4, "sapientia": 5},
                   "archetypes": [("stoic", 60), ("cold", 30), ("proud", 10)]},
    },
    "tiers": {
        "standard":  {"variance": {"vita": (-1, 1)}},
        "prototype": {"prop_bonus": {"vita": 2}, "variance": {"vita": (-2, 2)},
                      "archetype_extra": [("cold", 15)],
                      "humanity_mod": -20},   # 엔진이 안 읽는 자유 키 — 시나리오가 소비
    },
}
```

2. **추첨 + 시드** — 재현성이 필요하면 결정적 시드로 rng를 만든다
   (S03: `cycle*1000 + serial` → 같은 주기·시리얼은 항상 같은 개체):

```python
rng = cg.make_rng(cycle * 1000 + serial)
identity = cg.roll_identity(SPEC, "sniper", tier, rng=rng)
# → {"role", "tier", "archetype", "props"}
```

3. **적용** — 추첨 결과를 캐릭터 configure에 주입하고, 아키타입은
   **문자열 prop**으로 저장해 대화 어댑터가 읽게 한다:

```python
npc.configure(uid, name, role, archetype=identity["archetype"],
              stat_overrides=identity["props"])   # props["아키타입"] 저장
# 대화 어댑터: prop 우선, 없으면 역할 고정 매핑 폴백
```

### 역할/티어 구조가 아닌 랜덤 (평면 속성)

`roll_identity`의 역할·티어 spec이 안 맞는 평면 캐릭터(성별/성격/클래스/
기벽/스탯을 독립 추첨)라면 프리미티브를 직접 조합한다 — 참조:
S04 `character_randomizer`. 엔진이 제공하는 순수 추첨 프리미티브:

- `weighted_choice(pool, rng)` — 균등/가중(`[(값, 가중치)]`) 혼합 추첨
- `roll_range((lo, hi), rng)` — 폐구간 정수 (스탯 편차)
- `sample_distinct(pool, count, rng, avoid)` — 중복 없는 다중 추첨
  (이름 중복 회피·기벽 다중 선택). 풀 고갈 시 있는 만큼 반환
- `make_rng(seed)` — 전역 random과 격리된 결정적 난수기

모든 프리미티브가 `rng`를 받으므로, 데이터 풀만 시나리오가 소유하면
결정적 재현(세이브/재실행)이 공짜로 따라온다.

### 랜덤 → UNIQUE 승격 경로

오래 생존한 랜덤 개체를 고유 캐릭터로 키우고 싶으면 **코드 변경 없이
② 대사 yaml만 추가**하면 된다 — hybrid는 캐릭터 이름 기준으로 yaml
override를 찾으므로, 해당 개체의 이름으로
`dialogues/characters/{이름}.yaml`을 작성 + 컴파일하는 순간 그 개체만의
말투가 생긴다. 전용 행동이 필요해지면 ③ AI 파일을 추가한다.

## 5. 파티/분대

`engine.party` 하나로 S02 분대(플레이어 리더) · S03 분대(무플레이어 NPC
리더×N) · S04 파티(merge/split/승계)를 모두 커버한다:

- 초기화: `party.initialize_party(player_id)` (플레이어형) 또는
  `party.create_solo_party(npc_id)` (무플레이어형)
- 모집/해제: C# 액션은 `party.request_recruit/request_dismiss`로 들어온다 —
  판정 로직은 `party.set_request_handlers(recruit_fn=..., dismiss_fn=...)`로 주입
- 지휘: `set_stance`(retreat/defensive/hold/combat_normal/combat_aggressive),
  `set_mode`(search/stealth), `set_member_rank`(1전위/2중위/3후위), Order

## 6. 테스트 — 공유 mock으로 심 구동

프로덕션은 SharpPy(Godot)지만 테스트는 CPython + 공유 mock
(`scenarios/common/python/testing/mock_morld.py`)으로 돈다. mock은 실 C#
계약을 따른다 (prop 부재=0, `add_unit(unique_id="player")` → PlayerId).

부트스트랩은 scenario_mini의
[test_acceptance.py](../scenarios/scenario_mini/python/tests/test_acceptance.py)를
복사해서 시작하면 된다. 엔진/공용 코드를 건드렸다면 인수 테스트도 함께:

```powershell
& "C:\ProgramData\miniforge3\python.exe" scenarios\scenario_mini\python\tests\test_acceptance.py
```

## 7. 체크리스트 (새 팩 출시 전)

- [ ] 대화 정책 선언했는가 (fixed/fixed+fallback/hybrid)
- [ ] `get_unit_prop`/`get_player_id` 가드가 전부 truthy인가 (`is None` 금지)
- [ ] 새 prop은 없어도 동작하는가 (선택적 속성 원칙 — 기본값=최상 상태)
- [ ] 대사 yaml을 추가/수정했으면 컴파일본을 같은 커밋에 넣었는가
- [ ] `reset()` 계약 — 팩의 상태 보유 모듈에 reset()이 있는가 (챕터 전환)
- [ ] 테스트가 공유 mock으로 그린인가 + scenario_mini 인수 테스트 그린인가
