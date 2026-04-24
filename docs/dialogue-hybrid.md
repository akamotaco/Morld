# Hybrid 대화 시스템

경량 Template + Slot 기반 대사 생성 엔진. **아키타입 공용 풀 + 캐릭터 override**
구조로 S02 `tone_templates` 를 포괄하며 S04 일상·퀘스트 대화까지 확장하도록 설계.

**위치**
- 엔진 코드: [`scenarios/common/python/engine/dialogue_hybrid/`](../scenarios/common/python/engine/dialogue_hybrid/)
- 데이터: [`scenarios/common/python/dialogues/`](../scenarios/common/python/dialogues/)

---

## 1. 목적과 설계 철학

### 기존 방식 대비 선택 이유

| 방식 | 완성도 | 다양성 | 상태 반응 | 작성 비용 |
|---|---|---|---|---|
| 템플릿 고정 (S02 tone_templates) | 100% (작가 보증) | 선형 증가 | 상태→좌표 매핑 | 중 |
| 토큰 조립 (WFC 프로토타입) | ~80% (어색 조합 잔존) | 매우 높음 | 약함 | 낮음 |
| **Hybrid (채택)** | **100%** | **중~높음** | **좋음** | **낮음~중** |

### 4대 설계 원칙

1. **Template = 완성 문장** — 작가가 쓴 문장이 조립 실패 없이 출력됨
2. **Slot = 제한적 치환** — `{name}`, `{end}` 같은 부분만 런타임 선택
3. **State-bias 확률 매칭** — 상태 축 거리 기반 softmax (엄격 규칙 + 확률적 다양성)
4. **아키타입 공유** — 같은 아키타입(cold, cheerful 등) 캐릭터는 공용 풀 상속, 고유한 부분만 override

---

## 2. 구조

### 디렉터리 레이아웃

```
scenarios/common/python/
├── dialogues/
│   ├── characters/
│   │   ├── 시호.yaml                 # 프로필 + (선택) dialogue_overrides
│   │   ├── 유카.yaml
│   │   └── 린.yaml
│   └── archetype_dialogues/
│       ├── cheerful/
│       │   ├── romance.yaml          # LINES (1인칭 대사)
│       │   ├── romance_reactions.yaml # REACTIONS (3인칭 묘사)
│       │   ├── action_lines.yaml     # ACTION_LINES
│       │   └── action_reactions.yaml # ACTION_REACTIONS
│       ├── cold/ ...
│       └── {8 more archetypes}
└── engine/dialogue_hybrid/
    ├── __init__.py
    ├── engine.py                     # HybridEngine core
    └── s02_adapter.py                # LineGenerator / ReactionGenerator 호환
```

### 표준 10 아키타입

`stoic · gentle · cheerful · timid · cold · seductive · fierce · proud · innocent · devoted`

### 표준 state 축 (state_bias / 러닝타임 state)

| 축 | 범위 | 의미 |
|---|---|---|
| `affinity` | `-1.0 ~ 1.0` | 호감 (음수면 반발) |
| `arousal` | `-1.0 ~ 1.0` | 흥분/욕구 (음수면 순수/억제) |
| `climax` | `0.0 ~ 1.0` | 절정 근접도 |
| 기타 (`fatigue`, `embarrassment`, `trust`...) | `-1.0 ~ 1.0` | yaml에서 자유 정의 가능 |

---

## 3. yaml 스키마

### (a) 캐릭터 프로필 — `characters/{이름}.yaml`

```yaml
character: 시호
archetype: tsundere          # 아키타입 (archetype_dialogues/{이 값}/ 을 상속)
era: modern
sex: F

# 외면 프로필 — Template state_bias 매칭에 사용
outer_profile:
  formality: -0.3
  warmth: -0.1
  aggression: 0.3
  verbosity: 0.1

# 내면 프로필 — Template inner_bias 매칭에 사용 (생략 시 outer 와 동일 = 표리일체)
inner_profile:
  formality: 0.1
  warmth: 0.4            # 속으론 따뜻
  verbosity: 0.6         # 속으론 말 많음

# 런타임 조건 boost (옵션)
interactions:
  - name: "츤모드 발동"
    conditions:
      - { axis: embarrassment, min: 0.5 }
      - { axis: affinity,      min: 0.4 }
    boost:
      aggression: +0.6
      verbosity:  +0.4

# 캐릭터 고유 대사 (옵션) — 섹션 5 참조
dialogue_overrides:
  daily:
    intents:
      greet:
        add_templates: [...]
        add_slots: {...}
```

### (b) 아키타입 대사 풀 — `archetype_dialogues/{아키타입}/{context}.yaml`

```yaml
archetype: cheerful
context: romance

intents:
  light:                        # intent명 (행위 or 카테고리)
    templates:
      - id: light_80_30_0        # 고유 id (override 시 기준)
        pattern: "좋아!"            # 완성 문장, {slot} 치환 부분만 표기
        state_bias:                # 이 template이 가장 잘 맞는 상태
          affinity: 0.8
          arousal: 0.3
        inner_bias: {}              # 옵션 — inner 축 매칭 (tsundere 등 괴리 캐릭터용)

      - id: light_80_30_1
        pattern: "{emph}, 고마워{end}"
        state_bias: { affinity: 0.8, arousal: 0.3 }

    slots:                         # 해당 intent 전용 slot pool
      emph:
        - { token: "딱히", feature: { embarrassment: 0.6 } }  # feature 옵션 (state 기반 slot softmax)
        - "별로"                    # feature 없으면 uniform random
      end: [ ".", "..", "..." ]

  medium:
    templates: [...]
    slots: {...}
```

---

## 4. 동작 방식

### 런타임 흐름

```
HybridEngine.load(character="린", context="romance", ...)
  │
  ├─ characters/린.yaml 로드 → 프로필 + 아키타입 확인 ("cheerful")
  ├─ archetype_dialogues/cheerful/romance.yaml 로드 → base intents
  ├─ character.dialogue_overrides[romance] 병합 (add/replace/disable/add_slots)
  └─ HybridEngine 인스턴스

eng.generate(intent="light", state={"affinity": 0.8, "arousal": 0.3},
             context={"name": "린"})
  │
  ├─ intent 매칭 (또는 ACTION_TO_CATEGORY fallback: "hug" → "light")
  ├─ outer_state = outer_profile + state
  ├─ inner_state = inner_profile + state
  ├─ Template 선택:
  │    logit = -(‖outer_state - state_bias‖ + ‖inner_state - inner_bias‖) / σ
  │          - anti_repetition_penalty(recent_templates)
  │    softmax 샘플링
  ├─ Slot 채우기 (각 {slot} 위치):
  │    1. context[slot_name] 있으면 그대로 치환 ({name} → "린")
  │    2. 아니면 slot pool에서 state feature softmax 샘플
  │    3. feature 없으면 uniform
  └─ 문장 완성 → "에헤헤~ 안아줘!"
```

### Prior 레이어 3종

| Prior | 효과 | 구현 |
|---|---|---|
| **State bias** | 현재 상태에 맞는 template/slot 선호 | 가우시안 커널 + softmax |
| **Inner bias** | 외면/내면 괴리 캐릭터의 이중 매칭 | 별도 inner_profile + 거리 합산 |
| **Anti-repetition** | 최근 N턴의 template/slot 재선택 감점 | Recency-weighted logit penalty |

### Intent fallback chain

4단계 계층 폴백 (`engine._generate_intent`):

1. **exact match** — yaml `intents.{intent_name}.templates` 직접
2. **ACTION_TO_CATEGORY 폴백** — 기본 카테고리로 치환 (예: `hug → light`)
3. **접두사+카테고리** (Tone prefix) — 접두사 유지하며 카테고리로 치환
   - `forced_breast_grope` → `forced_medium`
   - `ecstasy_chain_2` → `ecstasy_penetration` (chain_2 의 base 인 chain 은
     `ACTION_TO_CATEGORY` 미등록이라 이 단계 skip)
4. **bare 접두사** — 접두사 trailing `_` 제거한 기본 인텐트
   - `ecstasy_chain_2` → `ecstasy`
   - `forced_hug` → (forced 는 카테고리 모르면 여기 먼저)

등록된 톤 접두사 (`_TONE_PREFIXES`): `forced_`, `trance_deep_`, `trance_`, `ecstasy_`.

`ACTION_TO_CATEGORY` 매핑 (S02 원본 77 액션 전수 커버):

```
# light
hug / deep_kiss / kiss / cheek_caress → light
# medium
breast_touch / nipple_stimulation / breast_grope → medium
# strong
clit_rub / fellatio / penis_caress / swallow_semen → strong
# penetration
vaginal_insert / thrust_gentle / tribadism → penetration
# rough
thrust_rough / tear_upper / use_whip / force_feed → rough
```

**호출자 측 자동 위임** (`base.py` Character):
- `ROMANCE_REACTIONS` 에 명시 rule 없으면서 키가 `_HYBRID_TONE_PREFIXES`
  (`forced_`, `trance_deep_`, `trance_`, `ecstasy_`) 로 시작하면 `_generate_dialogue`
  자동 호출 → hybrid 위임
- `INITIATIVE_REACTIONS` 에 명시 rule 없으면서 timing 이
  `during_<action>` / `forced_during_<action>` 패턴이면 hybrid `LineGenerator`
  자동 위임

→ 캐릭터 파일에 77 액션 × 모드별 수작업 rule 작성 없이도 아키타입 풀에서
톤 유지 대사 생성.

---

## 5. 새 캐릭터 추가 방법

### 5.1 최소 설정 (아키타입 상속만)

아키타입 공용 대사를 그대로 쓰는 경우 — **1분 이내**.

```yaml
# scenarios/common/python/dialogues/characters/미나.yaml
character: 미나
archetype: cheerful
era: modern
sex: F

outer_profile:
  warmth: 0.6
  verbosity: 0.4
```

이것만으로 `HybridEngine.load(character="미나", context="romance")` 가 작동.
미나의 대사는 **cheerful 풀 전체**가 사용됨.

### 5.2 아키타입 선택 가이드

| 특성 | 추천 아키타입 |
|---|---|
| 밝고 에너지 넘침, 과장 | `cheerful` |
| 존댓말, 감정 억제, 차가움 | `cold` |
| 과묵, 담담, 짧은 응답 | `stoic` |
| 겁쟁이, 조심성 | `timid` |
| 순진, 어린 느낌 | `innocent` |
| 공격적, 용감 | `fierce` |
| 고고/자존심 | `proud` |
| 유혹/능숙 | `seductive` |
| 충직/헌신 | `devoted` |
| 부드러운 존댓말 | `gentle` |

### 5.3 새 아키타입 필요 시

예: `tsundere`, `yandere` 같이 10 표준에 없는 아키타입 → 새 폴더 생성:

```bash
mkdir scenarios/common/python/dialogues/archetype_dialogues/tsundere
# 각 context yaml을 수동 작성 또는 기존 아키타입에서 파생
```

---

## 6. 캐릭터 고유 override

캐릭터의 `dialogue_overrides` 에서 **4 연산자** 사용:

```yaml
# characters/시호.yaml
dialogue_overrides:
  daily:                           # context 단위
    intents:
      greet:                        # intent 단위
        # (1) 아키타입에 없는 대사 추가
        add_templates:
          - id: shiho_specific_wait
            pattern: "{wait_expr}, 너 {late_note}"
            state_bias: { affinity: 0.75, embarrassment: 0.5 }
            inner_bias: { affinity: 0.85, warmth: 0.7 }

        # (2) 아키타입 template을 캐릭터 고유 변형으로 교체 (id 일치)
        replace_templates:
          - id: tsundere_hug_default
            pattern: "...(시호 버전)"

        # (3) 특정 아키타입 template을 이 캐릭터에 한해 비활성
        disable_templates: [ tsundere_hug_generic ]

        # (4) 슬롯 풀 확장 (합집합, append)
        add_slots:
          wait_expr: [ "...한참 기다렸잖아", "...늦었다니까" ]
          late_note: [ "또 어디 가 있었어", "연락이라도 좀 해줘" ]
```

### 병합 순서
1. `archetype_dialogues/{아키타입}/{context}.yaml` 로드 → base
2. `disable_templates` 적용 (제거)
3. `replace_templates` 적용 (id 일치 교체)
4. `add_templates` append
5. `add_slots` pool 합집합

### 권장 패턴

| 상황 | 연산자 |
|---|---|
| 캐릭터 특유 대사 1-2개만 추가 | `add_templates` |
| 아키타입 표준이 어색함 → 캐릭터 맞춤 | `replace_templates` |
| 이 캐릭터는 이 표현 절대 안 함 | `disable_templates` |
| 슬롯 풀 확장 (고유 감탄사 등) | `add_slots` |

---

## 7. S02 호환 adapter

### 기존 S02 호출 코드 변경 없이 Hybrid 위에 올리기

```python
# 기존 S02 코드 (수정 없음)
from engine.dialogue_hybrid import LineGenerator, ReactionGenerator

profile = {
    "name": "린",
    "archetype": "cheerful",
    "vars": {},
}
state = {"호감": 80, "반발": 0, "성욕": 30, "욕망": 30,
         "순수도": 20, "climax_gauge": 0, "climax_total": 0}

line_gen = LineGenerator(profile)
text = line_gen.generate("hug", state)
# → "따뜻해!" / "에헤헤~ 안아줘!" 등

react_gen = ReactionGenerator(profile)
reaction = react_gen.generate("thrust_gentle", "during", state)
# → "린가 부드러운 움직임에 눈을 감고 젖어들고 있다."
```

내부적으로:
- S02 좌표 공식 (`X=호감-반발*0.8`, `Y=(성욕+욕망)/2-순수도/2`, `Z=gauge*0.6 + min(total,4)*10`) → Hybrid `state_bias` 변환
- 엔진 인스턴스는 character별 캐시됨 (재생성 비용 0)
- `{name}` 자동 주입

---

## 8. API 레퍼런스

### HybridEngine.load

```python
HybridEngine.load(
    character: str,           # characters/{character}.yaml 기준
    context: str,             # archetype_dialogues/{arch}/{context}.yaml 기준
    dialogue_root: str | Path = "dialogues",
    **engine_kwargs,
) -> HybridEngine
```

단일 context 로드. 예: `load("시호", "daily")`.

### HybridEngine.load_composite

```python
HybridEngine.load_composite(
    character: str,
    contexts: List[str],      # 여러 context 병합 로드
    dialogue_root: str | Path = "dialogues",
    **engine_kwargs,
) -> HybridEngine
```

여러 yaml 병합 → action ↔ category intent fallback 가능. 예:

```python
eng = HybridEngine.load_composite("린", ["romance", "action_lines"])
eng.generate("hug", ...)   # action_lines.yaml의 hug intent 사용
eng.generate("light", ...) # romance.yaml의 light intent 사용
```

### HybridEngine.generate

```python
eng.generate(
    intent: str,                              # 없으면 ACTION_TO_CATEGORY fallback
    state: Dict[str, float] | None = None,    # 런타임 축 값 (affinity 등)
    context: Dict[str, Any] | None = None,    # 런타임 치환 ({name} 등)
    record: bool = True,                      # anti-rep 히스토리 기록 여부
) -> str
```

### HybridEngine 기타

| 메서드 | 용도 |
|---|---|
| `set_seed(seed, reset_history=False)` | rng 시드 설정 (+ 옵션 히스토리 초기화) |
| `reset_history()` | anti-repetition 히스토리 비우기 (턴/세션 경계) |

---

## 9. 튜닝 파라미터

`HybridEngine.__init__(...)` 인자:

| 파라미터 | 기본값 | 효과 |
|---|---|---|
| `template_sigma` | 0.6 | 낮을수록 state 근접 template만 선택 (민감도 ↑) |
| `template_temp` | 0.5 | 낮을수록 결정적 (top logit 선호) |
| `slot_sigma` | 0.6 | slot feature softmax bandwidth |
| `slot_temp` | 0.5 | slot softmax 온도 |
| `history_size` | 5 | anti-rep 히스토리 길이 |
| `repetition_penalty` | 1.5 | logit 감점 강도 (0=비활성, 1~2 권장) |
| `seed` | 0 | 초기 rng 시드 |

예: 결정적 재현이 필요한 테스트에서는 `template_temp=0.01`.

---

## 10. 확장 계획

### 미구현 (필요 시점에 추가)

| 항목 | 용도 |
|---|---|
| **Speech / style 축** | S02 CASUAL_LINE_TEMPLATES 의 `archetype × speech × style × default/flirty/addicted` 4중 구조 대응 |
| **Hard filter** | `{"activity": "사냥"}` 같은 카테고리컬 조건 (TALK_RULES 전체 이식용) |
| **First-match 모드** | S02 `TextSelector.select` 결정적 동작 호환 (Rules 계승) |
| **SharpPy 대응** | 런타임 pyyaml 의존 제거 — yaml → JSON 또는 Python dict 모듈 pre-compile |

### 캐릭터 이관 대상 (Phase 3)

S02 `assets/characters/*.py` 의 다음 데이터를 해당 캐릭터 `dialogue_overrides` 로 이관:
- `ROMANCE_REACTIONS` (특수 조건 반응)
- `TALK_RULES` (일상 대화)
- `DESCRIBE_RULES` / `FOCUS_RULES` (묘사)
- `char_lines` / `line_overrides`

빌더 기반 Rules (`build_describe_rules()`) 는 런타임 실행 후 결과 캡처 필요.

---

## 11. 성능

실측 (CPython 3.12, Windows):

| 연산 | Latency |
|---|---|
| `generate()` 1회 | 40~150 μs (character 당 캐시 워밍 후) |
| `load_composite()` 초기화 | ~5 ms (yaml 파싱 + 병합) |

초당 **수천 회 대사 생성 가능** — 실제 게임 사용량의 수천 배 여유.
SharpPy 런타임에서는 yaml 파싱 비용만 주의 (데이터를 pre-compile 하면 해결).

---

## 12. 참고

- 프로토타입 기록: [`tmp/dialogue_multistage/`](../tmp/dialogue_multistage/) (wip 브랜치 `wip/dialogue-hybrid-proto`)
- S02 원본 데이터: [`scenarios/common/python/engine/tone_templates/`](../scenarios/common/python/engine/tone_templates/)
- S02 대화 시스템 문서: [`scenarios/scenario02/docs/dialog.md`](../scenarios/scenario02/docs/dialog.md)
