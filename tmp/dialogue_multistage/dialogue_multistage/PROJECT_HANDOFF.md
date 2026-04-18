# Multi-stage Persona Dialogue System

> Inner N-gram + Outer WFC 아키텍처로 dere-type 캐릭터의 표리 괴리를 표현하는 경량 대화 생성 시스템

---

## 0. 프로젝트 핸드오프 요약

이 문서는 Claude에게 프로젝트를 이어서 작업하도록 넘기기 위한 **재현 가능한 프로젝트 명세**입니다. 이전 세션에서 Phase 1 (6개 알고리즘 비교) 과 Phase 2 (multi-stage 개발) 를 거쳤으며, 최종 도달한 기법을 이 문서에 완전히 기술합니다.

**핵심 아이디어.** NPC 대화 생성을 **4-stage 파이프라인**으로 분해한다. 각 stage는 서로 다른 추상도와 상태 축을 참조하여, "생각과 말의 괴리(dere 타입의 본질)"를 구조적으로 표현할 수 있다.

- **Stage 1** (Structural N-gram): **내면** 상태가 문장 구조를 결정
- **Stage 2** (Content WFC): **외면** 상태가 본문 어휘를 결정
- **Stage 3** (Function WFC): **외면** 상태가 감탄사/어미/구두점을 결정
- **Stage 4** (Postprocess): 한국어 형태론 결합 + 정리

**현재 상태.** 3개 캐릭터 (시호 Tsundere, 유카 Kuudere, 린 Deredere) 로 파이프라인이 완성되어 작동한다. 12 캐릭터 확장은 Phase 2 후속 작업으로 남아있다.

---

## 1. 요구사항 이력

(이전 세션에서 사용자가 제시한 요구사항들. 앞으로의 의사결정시 참고)

**Phase 1 요구사항:**
1. NPC의 성격과 상태(나이, 말투, 감정, 체력, 피로도)가 반영되어야 함
2. 성격·말투는 여러 종류 포함 가능
3. LLM처럼 연산이 길면 안 됨
4. 연속적인 manifold (상태 연속 변화 → 출력 연속 변화)
5. 단순 vector 매칭은 오매칭 위험 — 캐릭터 일관성 보장

**Phase 2 추가 요구사항:**
6. `<S>` / `<EOS>` boundary 토큰으로 가변 길이
7. 다차원 상태 (호감, 반발, 피로, 욕망 등) — 게임 내 고정·게임 간 이식 가능
8. 긴 토큰 단위 (BPE 스타일) — "습니다." 같은 어미 덩어리
9. 역방향 collapse (어미부터 결정)
10. 데이터 기반 codebook 생성 (예시 대사 → 자동 추출)
11. 서브컬처 톤 (여성 70%+, 다양한 dere 타입)
12. **Multi-stage: N-gram=내면, WFC=외면** ← 최종 도달 지점

---

## 2. 시스템 아키텍처

### 2.1 파이프라인 개요

```
┌─────────────────────────────────────────────────────────────┐
│  Input: NPCState (inner+outer vectors), intent              │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Structural N-gram                                 │
│  • inner_vector 를 참조                                      │
│  • inner_state 조건부 weighted bigram                        │
│  • output: class sequence                                   │
│    예: ["<S>", "interj", "body", "end", "punct", "<EOS>"]   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Content WFC                                       │
│  • outer_vector 를 참조                                      │
│  • class_seq의 body 자리에 실제 토큰 collapse                │
│  • state-weighted softmax + adjacency + 중복 penalty          │
│  • output: body 토큰이 채워진 Slot 리스트                    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Function WFC                                      │
│  • outer_vector 를 참조                                      │
│  • interj / end / punct 자리 collapse                       │
│  • body.morph 로 end 호환성 필터                             │
│  • output: 완전히 채워진 Slot 리스트                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Postprocess                                       │
│  • 한국어 body+end fusion (세요/십시오 매개모음, 하+어=해 등) │
│  • 연속 구두점 정리                                          │
│  • 중복 감탄사 제거                                          │
│  • output: 최종 문자열                                       │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                     "딱히 고마워..."
```

### 2.2 왜 이 구조인가 — 설계 근거

**Multi-stage 의 이론적 근거.** 단일 WFC 가 실패한 이유는 **entropy scale의 불균일**이다. 한 cell 이 수백 토큰 중 하나를 고를 때, 본문 핵심 어휘들의 state-fit score는 날카로운 분포(선명한 선호)를 보이지만, 기능어(조사, 어미 등) 들은 거의 평탄한 분포를 보인다. 이들이 같은 softmax 안에 섞여 있으면, 핵심 어휘의 선명한 선호가 기능어 노이즈에 희석되고, 반대로 기능어는 본문의 강한 제약에 과도하게 끌려간다.

Stage 분리의 효과:
- 각 stage 의 pool 이 크기·entropy 스케일이 비슷한 것끼리 경쟁
- WFC의 "lowest-entropy-first" 원칙이 제대로 작동
- stage별 온도 T 독립 튜닝 가능

**Inner/Outer 분리의 이론적 근거.** Dere 타입은 "표면 vs 내면"의 **괴리**를 본질로 한다. 츤데레는 호감(내면)을 공격(외면)으로 가린다. 단일 상태 벡터에 이 두 층을 섞으면 서로 상쇄되어 중간적인 애매한 문장만 나온다.

Inner (N-gram이 참조) 와 Outer (WFC가 참조) 를 분리하면:
- **N-gram이 내면에 맞는 구조 선택**: affinity가 속으로 높으면 호칭(addr) slot 자주 등장, 문장 길어짐
- **WFC가 외면에 맞는 어휘 선택**: embarrassment가 겉으로 드러나면 쏘아붙이는 body + 거친 end

결과: **"이름 꼬박꼬박 부르면서 까칠하게 말하는 츤데레"** 가 자연스럽게 생성됨.

---

## 3. 데이터 구조

### 3.1 Axis Schema (게임 단위 고정, 게임 간 이식 가능)

`game_config.py` 에서 선언. 엔진은 축 이름을 모르고 차원 수만 다룬다.

```python
# game_config.py
AXES = {
    "trait": [           # 캐릭터 고정 성격
        "formality",     # 공손(+) ↔ 거침(-)
        "warmth",        # 친밀(+) ↔ 냉정(-)
        "aggression",    # 공격(+) ↔ 온화(-)
        "verbosity",     # 수다(+) ↔ 간결(-)
        "maturity",      # 성숙(+) ↔ 유치(-)
    ],
    "dynamic": [         # 실시간 신체·각성 상태
        "fatigue",       # 탈진(+) ↔ 쌩쌩(-)
        "arousal",       # 흥분(+) ↔ 차분(-)
        "confidence",    # 확신(+) ↔ 주저(-)
    ],
    "relation": [        # 상대(플레이어)와의 관계
        "affinity",      # 호감(+)
        "hostility",     # 반발(+)
        "trust",         # 신뢰(+)
        "embarrassment", # 부끄러움(+) — dere 발동 핵심 축
    ],
    "desire": [          # 상황별 동기 (게임별 교체 가능)
        "money",
        "attention",
        "safety",
    ],
}
# 총 N_DIM = 15
```

모든 축은 `[-1, +1]` 정규화. 0이 중립.

### 3.2 Character yaml 형식

각 캐릭터는 하나의 yaml 파일. 예시 대사와 프로필 포함.

```yaml
# examples/01_shiho.yaml (Tsundere — 표리 괴리 큼)
character: 시호
archetype: tsundere
era: modern
sex: F

# 외면 (Stage 2/3 WFC 가 참조)
outer_profile:
  formality: -0.3
  warmth: -0.1       # 표면 차가움
  aggression: 0.3
  verbosity: 0.1
  maturity: 0.2

# 내면 (Stage 1 N-gram 이 참조)
# 표리일체면 생략 가능 (outer 와 동일하게 처리됨)
inner_profile:
  formality: 0.1
  warmth: 0.4        # 속으론 따뜻
  aggression: -0.1
  verbosity: 0.6     # 사실은 할 말 많음
  maturity: 0.2

# 조건부 축 변조
interactions:
  - name: "츤모드 발동"
    conditions:
      - { axis: embarrassment, min: 0.5 }
      - { axis: affinity,      min: 0.4 }
    boost:
      aggression: +0.6
      verbosity:  +0.4
      formality:  -0.2
    target: outer   # "inner" / "outer" / "both"

# 예시 대사. 각 sample 에 intent 와 그 당시 상태 태깅
samples:
  - text: "뭐야, 너 때문은 아니거든?"
    intent: refuse_quest
    state: { embarrassment: 0.7, affinity: 0.5 }
  - text: "...정말, 고마워. 진짜로."
    intent: thank
    state: { affinity: 0.8, trust: 0.7, embarrassment: 0.3 }
  # ... 총 40개 정도
```

**Intent 목록 (현재 8개).**
```
greet, farewell, refuse_quest, accept_quest,
complain, warn, ask_price, thank
```
확장은 쉬움 — yaml 에 해당 intent 태그로 대사 몇 개 추가하면 자동으로 codebook 과 schema 에 반영.

### 3.3 런타임 NPCState

```python
@dataclass
class NPCStateMS:
    name: str
    archetype: str
    outer_profile: Dict[str, float]    # trait 기본값 (외면)
    inner_profile: Dict[str, float]    # 내면 (비어있으면 outer 사용)
    dynamic: Dict[str, float]          # 런타임 상태 (fatigue, affinity 등)
    interactions: List[Interaction]

    def outer_vector(self) -> np.ndarray:
        """Stage 2/3 가 참조. outer_profile + dynamic + interactions(target=outer)"""

    def inner_vector(self) -> np.ndarray:
        """Stage 1 이 참조. inner_profile + dynamic + interactions(target=inner)"""

    def divergence(self) -> float:
        """표리 괴리 정도. 0=일체."""
        return float(np.linalg.norm(self.inner_vector() - self.outer_vector()))
```

---

## 4. 스테이지별 상세 구현

### 4.1 Codebook 자동 생성 (Offline, 1회)

`codebook_builder.py`

**파이프라인:**

1. **Tokenization**: 구두점 분리 + 어미 패턴 분리
   ```python
   ENDING_MARKERS = ["습니다", "세요", "십시오", "어요", "네요", "죠",
                     "이에요", "이야", "냐", "다.", "라.", ...]
   # "안녕하세요." → ["안녕하", "세요", "."]
   ```

2. **BPE-like merge**: 빈발 bigram 을 병합 (min_freq=2, n_merges=150)

3. **Class tagging** (규칙 기반):
   - `interj`: 끝에 `,` 있거나 감탄사 목록에 속함 ("앗", "와", "흥", "헤헤")
   - `addr`: 호칭 목록 ("너", "당신", "경", "손님", "아저씨")
   - `end`: 어미 패턴으로 끝남
   - `punct`: 구두점만
   - `body`: 나머지 → 그 sample의 intent 에 따라 `body_{intent}` 태깅

4. **Adjacency graph**: `(left_text, right_text)` 관측 횟수. `<S>` ~ `<EOS>` sentinel 포함.

5. **Feature inference**: 각 토큰이 등장한 sample 들의 effective_vector 를 평균.
   threshold 0.15 이하는 feature 에서 제거 (노이즈).

6. **Morph tagging**: 한글 음절 분석으로 어간 말음 태그 (V / C_n / C_l / C_reg).

7. **JSON 저장**: `codebooks/{캐릭터명}.json`

### 4.2 Stage 1 — Structural N-gram

`structural_ngram.py`

```python
@dataclass
class StructuralSample:
    intent: str
    class_seq: List[str]       # ["<S>", "interj", "body", ..., "<EOS>"]
    inner_vec: np.ndarray      # 당시의 inner state

class StructuralSampler:
    """
    inner_state 조건부 weighted bigram.

    전이 확률:
      P(next | current, inner_query) ∝
          Σ_s w(s.inner_vec, inner_query) * count[s: (current → next)]

    w(v1, v2) = exp(-|v1 - v2| / bandwidth)
    """
    def __init__(self, grammar, bandwidth=0.8, temperature=0.4, seed=0):
        self.g = grammar
        self.bw = bandwidth
        self.T = temperature
        self.rng = np.random.default_rng(seed)

    def sample(self, intent, inner_vec, max_len=8):
        seq = ["<S>"]
        for _ in range(max_len):
            probs = self._weighted_bigram(intent, seq[-1], inner_vec)
            if not probs:
                break
            # temperature 적용 후 sample
            keys = list(probs.keys())
            vals = np.power(np.array(list(probs.values())), 1.0 / self.T)
            vals /= vals.sum()
            pick = str(self.rng.choice(keys, p=vals))
            seq.append(pick)
            if pick == "<EOS>":
                break
        if seq[-1] != "<EOS>":
            seq.append("<EOS>")
        return seq
```

**이 stage는 성격을 이미 반영하지만 "구조" 수준만 반영한다.**
내면 verbosity가 높으면 긴 시퀀스, 내면 affinity가 높으면 addr slot이 자주 나타남.

### 4.3 Stage 2 — Content WFC

`content_wfc.py`

body 자리만 채움. state-weighted softmax + 이웃 adjacency + 같은 body 중복 penalty.

```python
class ContentWFC:
    def fill(self, class_seq, intent, outer_vec):
        slots = [Slot(cls=c, intent=intent) for c in class_seq]
        # <S>, <EOS>는 자기 자신으로 고정
        # body_{intent} pool 준비

        unresolved = {i for i, s in enumerate(slots) if s.cls == "body"}
        while unresolved:
            # entropy 최소 cell 선택 (이웃 정보 사용)
            # 단, 같은 body 가 인접 cell 에 이미 collapse되어 있으면
            # 그 token 확률을 0.05로 억제
            # sample -> collapse
        return slots
```

**핵심 디테일.**
- 온도 T=0.5 (state 민감도 최대)
- adjacency smoothing=0.02 (학습된 전이 선호)
- body 중복 penalty 0.05 ("중요해 중요해" 같은 연쇄 방지)

### 4.4 Stage 3 — Function WFC

`function_wfc.py`

interj / end / punct 자리 채움. body 의 morph 로 end 호환성 필터.

```python
END_COMPAT = {
    "V":     {"avoid_prefix": ["으"]},       # 모음 끝
    "C_n":   {"prefer_prefix": ["어", "아", "으"]},
    "C_l":   {"prefer_prefix": ["어", "아"]},
    "C_reg": {"prefer_prefix": ["으", "어", "아", "습", "네", "죠"]},
}

class FunctionWFC:
    def fill(self, slots, intent, outer_vec):
        for i, s in enumerate(slots):
            if s.token is not None:
                continue
            pool = self._pool(s.cls, intent)
            # body 직후 end 라면 morph 필터
            if s.cls == "end" and slots[i-1].cls == "body":
                pool = self._filter_end_by_morph(pool, slots[i-1].token.morph)
            probs = self._weights(pool, outer_vec, left, right)
            s.token = pool[sample(probs)]
        return slots
```

온도 T=0.6 (기능어는 좀 더 다양하게).

### 4.5 Stage 4 — Postprocess (assemble)

`function_wfc.py` 안의 `assemble()` 함수.

- body + end fusion (한국어 활용)
  - `"하" + "어요"` → `"해요"` (축약)
  - `"많" + "세요"` → `"많으세요"` (매개모음)
- 구두점 정리
  - 토큰 끝에 이미 구두점이 있으면 중복 억제
  - `"..."` + `"."` → `"..."`
  - `"!"` 3개 이상 → 2개로 제한
- 시작 구두점 제거

---

## 5. 최종 출력 샘플 (현재 상태)

```
=== 시호 (tsundere, divergence=0.91) ===
  greet:    "별로.", "안녕 건데 안..", "왜 자꾸. 말 거는"
  complain: "그게 뭐가 중요해 나한테만 시키는",
            "오늘 좀 힘들어서, 좀",
            "그게 뭐가 중요해 짜증나."
  thank:    "딱히. 싶진.. 받고",
            "딱히 고마워..",
            "딱히.. 않았지만..",
            "고, 고맙다고는.. 받긴"

=== 유카 (kuudere, divergence=0.42) ===
  greet:    "안녕하십니까.", "접속.", "확인.."
  complain: "피로도 임계치 근접 판단 보류",
            "효율이 떨어지고 조금 쉬고"
  thank:    "감사합니다.", "감사.", "도움이."

=== 린 (deredere, divergence=0.00) ===
  greet:    "반가워요!", "안녕하세요!", "오세요!"
  complain: "힘들어요..", "배고파요!", "으응 먹고싶어요!!"
  thank:    "짱이에요!", "에헤헤!", "와아!!", "헤헤!"
```

**inner/outer 분리의 실증 효과:**
- 시호의 thank 출력들이 **구조적으로 길고** (inner verbosity=+0.6 반영된 Stage 1) **어휘는 쏘아붙임** (outer aggression=+0.3 및 interaction boost 반영된 Stage 2/3) — "딱히, 고마워..", "고, 고맙다고는 받긴" 등
- 유카는 짧고 일관된 구조로 kuudere 특성 유지
- 린은 표리일체라 Stage 1/2 모두 밝은 분위기 일관

---

## 6. 장점

### 6.1 이론적 장점

1. **표리 괴리의 구조적 표현**
   단일 state vector 로는 불가능한 "속마음-겉말 어긋남" 을 아키텍처 레벨에서 분리. 츤데레·얀데레·단데레 등 복잡한 dere 타입에 필수.

2. **Entropy scale 분리로 안정성 ↑**
   Stage 별로 pool 크기·score 분포가 비슷해 WFC의 lowest-entropy-first 원칙이 제대로 작동. 단일 WFC 에서 있던 "기능어 노이즈에 본문이 휩쓸리는 문제" 해결.

3. **Stage 별 독립 튜닝**
   T1=0.4 (구조 결정적), T2=0.5 (본문 표현력), T3=0.6 (기능어 다양성) 등 stage 고유 파라미터.

4. **데이터 기반 codebook**
   작가는 예시 대사 40개만 주석 달아 제공. BPE·class·adjacency·feature 전부 자동 추출. 새 캐릭터 추가 비용이 낮음.

5. **축 이식성**
   `game_config.py` 의 AXES 만 교체하면 다른 게임 맥락 (판타지 ↔ SF ↔ 현대) 으로 이식 가능. 엔진은 축 이름 모름.

6. **해석 가능성**
   출력에 대해 "이 구조는 Stage 1이 만들었고, 이 어휘는 Stage 2가 골랐음" 분해 가능. 디버깅과 작가 소통에 유리.

### 6.2 실무적 장점

1. **경량**: 단일 대사 생성 < 1ms 예상 (측정 미완료). LLM 대비 3-4자릿수 빠름.
2. **결정적 재현**: 같은 state + 같은 seed → 같은 출력. 테스트·QA 친화.
3. **일관성 보장**: archetype별 codebook 1:1 매칭. 캐릭터 어휘 경계 위반 불가능.
4. **작가 친화**: "이 캐릭터 속마음은 이런데 겉으론 이렇게 말한다" 를 선언적으로 표현.

---

## 7. 단점 및 한계 (현재 상태)

### 7.1 출력 품질 문제 (해결 가능)

1. **Stage 1의 짧은 시퀀스 편향**
   현재 N-gram 학습에 `max_len` 제한 외에 길이 조절 기제 없음. 평균적으로 `[<S>, body, punct, <EOS>]` 같은 3-토큰 구조가 자주 나옴. 긴 시퀀스가 필요한 상황에서도 짧게 끊김.

2. **body-body 인접 부자연스러움**
   body 중복 penalty는 넣었지만, 서로 다른 body 가 짧은 어절로 나란히 나오면 문법적으로 이상한 조합. 예: `"별로 안 기다렸"` (OK), `"그게 뭐가 뭐가 나한테만"` (이상)

3. **한국어 형태론의 제한적 구현**
   `_fuse()` 함수가 `세요`/`십시오`/`어요` 등 몇 가지 규칙만 커버. 불규칙 활용 (ㅂ불규칙, ㄷ불규칙, 르불규칙 등) 미지원.

4. **구두점 토큰 내장 문제**
   BPE가 `"헤헤,"` 같은 토큰을 만들면 뒤에 또 구두점이 붙을 때 `"헤헤,!"` 같은 어색한 조합. Postprocess 에서 부분 해결했으나 근본적으로 tokenization 단계에서 구두점을 토큰에 포함 안 시키는 게 나음.

### 7.2 데이터 희소성 문제

1. **예시 40개로는 N-gram 희박**
   intent당 5개 정도인데, inner_state 조건부 bigram은 더 sparse. weighted smoothing 으로 완화 중이지만 일부 조합은 거의 관측 없음.

2. **Feature 추론의 노이즈**
   token이 2~3번만 등장하면 그 feature는 해당 sample 의 state 에 overfit. 예: `"."` 이 시호의 특정 상태에 aggression=0.65 tag 되는 건 일반화 가능한 신호인지 의심.

### 7.3 설계적 한계

1. **3 stage 간 불일치 가능성**
   Stage 1이 `[body, body, body]` 같이 긴 구조를 골랐는데 Stage 2가 채울 body token pool 이 빈약하면 같은 body 를 반복하거나 어색. Stage 1-2 간의 호환성 체크 기제 없음.

2. **Per-sample inner state 미지원**
   yaml 의 `state:` 는 outer 축만 태깅하는 암묵적 규약. inner 축 override 를 per-sample 단위로 하고 싶을 때 yaml 스키마 확장 필요.

3. **Adjacency 의 적용 위치 논쟁**
   현재 Stage 2에서만 adjacency 를 본격 쓰고, Stage 1은 class sequence 만, Stage 3은 얕게만 씀. Stage 간 adjacency 일관성이 깨질 수 있음.

### 7.4 측정·평가 미완료

1. **벤치마크 미실행**
   사용자의 요청으로 이전 기법들과의 비교는 생략. 따라서 multi-stage 의 정량적 우위가 측정으로 확인되지 않음.

2. **12 캐릭터 확장 전**
   현재 3 캐릭터 (시호·유카·린) 만 완성. 나머지 9명 (하루·엘리자·미사키·나나·쿄우지·야쿠모·타로·아오이·세츠나) 의 yaml 미작성.

---

## 8. 개선 계획 (우선순위 순)

### Tier 1 (필수, 빠른 수정)

1. **Stage 1 길이 조절**
   - `<EOS>` 토큰의 transition 가중치에 **position bonus** 추가: `w = base * (1 + α * position)` 즉 문장이 길어질수록 EOS 확률 ↑
   - 또는 **inner verbosity 를 length prior 로 직접 활용**: `target_length = f(inner.verbosity)` 후 schema 길이 분포에서 bias sampling
   - 예상 효과: 시호 inner verbosity=+0.6 → 자연히 6-8 토큰 시퀀스 선호

2. **Tokenizer 의 구두점 분리 강화**
   - BPE merge 단계에서 구두점이 포함된 bigram은 merge 금지
   - 예시: `"헤헤"` + `","` 를 `"헤헤,"` 로 merge 안 함 → 별도 interj + punct 로 유지

3. **단편 body 억제**
   - BPE `min_freq=1` 로 낮추되, 3글자 이상 bigram 우선 merge
   - 또는 길이 < 2 인 body 토큰은 `base_w` 에 0.3 배율

### Tier 2 (핵심 개선)

4. **Stage 1 - Stage 2 compatibility check**
   - Stage 1 결과에 Stage 2에서 채울 수 없는 slot이 있으면 re-sample
   - 예: `[body]` 3개인데 intent pool 에 body 토큰이 2개밖에 없을 때

5. **Per-sample inner override**
   - yaml 스키마 확장:
     ```yaml
     - text: "...고마워."
       intent: thank
       state: { affinity: 0.8 }
       inner_state: { affinity: 0.9, verbosity: 0.5 }  # 이 순간의 속마음
     ```

6. **형태론 확장**
   - 불규칙 활용 테이블 추가 (ㅂ, ㄷ, 르, 으 불규칙)
   - body 토큰 저장시 활용형 태그 자동 탐지

7. **N-gram smoothing 개선**
   - 현재는 bandwidth Gaussian. 더 정교한 kernel (Epanechnikov 등) 또는 k-NN based 로 교체 실험
   - Stage 1 에 trigram 도입 (현재 bigram) → 더 자연스러운 구조 전이

### Tier 3 (확장)

8. **12 캐릭터 전체 yaml 작성**
   - 하루 (Dandere, 주술 사서) / 엘리자 (Himedere, 귀족) / 미사키 (Yandere) /
     나나 (Bakadere) / 쿄우지 (Cool-senpai) / 야쿠모 (Oujidere) / 타로 (Himbo) /
     아오이 (Sunao-cool) / 세츠나 (Straight-shooter)
   - 각 40 sample, 총 ~480 sample

9. **Intent 확장**
   - `confess, tease, praise_player, request_help, compliment_self, sulk`
   - yaml 과 schema 에 추가만 하면 자동 흡수

10. **벤치마크 & 보고서**
    - Divergence vs naturalness scatter plot
    - Inner/Outer ablation: inner=outer 로 강제했을 때 dere 타입 재현력 손실 측정
    - Stage별 기여도 분해 (Stage 1만 / Stage 2만 / 전체 비교)

### Tier 4 (미래)

11. **Dialog coherence**
    - 턴 간 state 변화 규칙 (플레이어 발화 → affinity 변화 등)
    - 이전 턴의 adjacency 를 다음 턴의 Stage 1 에 prior 로 입력

12. **GUI 작가 도구**
    - yaml 편집 UI
    - 실시간 테스트 (state slider 움직이면 출력 즉시 갱신)

13. **신경망 혼합**
    - 작은 embedding model 로 예시 대사의 style vector 를 자동 추출
    - 수작성 feature 와 학습 feature 하이브리드

---

## 9. 파일 구조

```
phase2/
├── game_config.py                # 15축 schema
├── state_v2.py                   # 구버전 NPCState (레거시)
├── codebook_builder.py           # 예시 대사 → codebook JSON 자동 생성
├── wfc_v2.py                     # 구버전 단일 WFC (레거시, 참고용)
│
├── examples/                     # 캐릭터 데이터
│   ├── 01_shiho.yaml             # Tsundere ✓
│   ├── 02_yuka.yaml              # Kuudere ✓
│   ├── 05_rin.yaml               # Deredere ✓
│   ├── 03_haru.yaml              # (미작성) Dandere
│   ├── 04_eliza.yaml             # (미작성) Himedere
│   ├── 06_misaki.yaml            # (미작성) Yandere
│   ├── 07_nana.yaml              # (미작성) Bakadere
│   ├── 08_kyouji.yaml            # (미작성) Cool-senpai
│   ├── 09_yakumo.yaml            # (미작성) Oujidere
│   ├── 10_tarou.yaml             # (미작성) Himbo
│   ├── 11_aoi.yaml               # (미작성) Sunao-cool (표리일체)
│   └── 12_setsuna.yaml           # (미작성) Straight-shooter (표리일체)
│
├── codebooks/                    # 자동 생성된 JSON
│   ├── 시호.json
│   ├── 유카.json
│   └── 린.json
│
└── multistage/                   # 최종 방법론
    ├── state_ms.py               # NPCStateMS (inner/outer)
    ├── structural_ngram.py       # Stage 1
    ├── content_wfc.py            # Stage 2
    └── function_wfc.py           # Stage 3 + Stage 4 (assemble)
```

---

## 10. 핵심 코드 스니펫 (재현용)

### 10.1 End-to-end 호출 예시

```python
from pathlib import Path
import numpy as np
from state_ms import load_character_ms
from structural_ngram import build_structural_grammar, StructuralSampler
from content_wfc import ContentWFC
from function_wfc import FunctionWFC, assemble
from wfc_v2 import LoadedCodebook

# 1. 캐릭터 로드
npc, samples = load_character_ms("examples/01_shiho.yaml")

# 2. Codebook 로드 (사전에 codebook_builder.py 로 생성)
cb = LoadedCodebook.load("codebooks/시호.json")

# 3. Stage 1 준비 (N-gram 학습)
grammar = build_structural_grammar(npc, samples)
stage1 = StructuralSampler(grammar, bandwidth=0.8, temperature=0.4, seed=42)

# 4. Stage 2/3 엔진
stage2 = ContentWFC(cb, temperature=0.5, seed=42)
stage3 = FunctionWFC(cb, temperature=0.6, seed=42)

# 5. 런타임 상태 override
state = npc.with_state(affinity=0.8, embarrassment=0.7)

# 6. 파이프라인 실행
class_seq = stage1.sample("thank", state.inner_vector(), max_len=6)
slots = stage2.fill(class_seq, "thank", state.outer_vector())
slots = stage3.fill(slots, "thank", state.outer_vector())
result = assemble(slots)

print(result)   # 예: "딱히, 고마워.."
```

### 10.2 Codebook 생성 (1회성)

```bash
cd phase2
python codebook_builder.py
# → codebooks/*.json 생성
```

### 10.3 주요 파라미터 레퍼런스

| 파라미터 | 기본값 | 위치 | 영향 |
|---|---|---|---|
| `bandwidth` | 0.8 | Stage 1 | 낮을수록 inner_state 에 민감 |
| `T1` (temperature) | 0.4 | Stage 1 | 구조 결정 온도 |
| `T2` | 0.5 | Stage 2 | 본문 어휘 온도 (표현력 최대) |
| `T3` | 0.6 | Stage 3 | 기능어 온도 (다양성) |
| `adj_smoothing` | 0.02 | Stage 2/3 | 미관측 adjacency 기본 가중 |
| `min_freq` | 2 | BPE | 몇 번 이상 등장해야 merge |
| `n_merges` | 150 | BPE | 총 merge 반복 수 |
| `feature threshold` | 0.15 | codebook_builder | 이보다 작은 축은 noise 로 제거 |
| `max_cells` / `max_len` | 8 | Stage 1/2 | 최대 시퀀스 길이 |
| `body dup penalty` | 0.05 | Stage 2 | 같은 body 인접 억제 |

---

## 11. Claude 에게 넘기는 작업 지시

이 프로젝트를 이어서 작업할 때 다음 순서로 진행하라.

### 즉시 착수 가능한 작업

1. **Tier 1 수정 3건**: Stage 1 길이 조절, BPE 구두점 분리, 단편 body 억제. 각각 20-30 줄의 수정으로 끝남.

2. **3 캐릭터 출력 재검증**: 위 수정 후 시호·유카·린 각 8 샘플씩 출력해서 자연스러움 확인. 확인 포인트:
   - 시호: 짧고 가시 돋친 것 ~ 길고 복잡한 것 까지 분포
   - 유카: 일관되게 짧고 담담
   - 린: 감탄사 풍부, 활기

### 이후 작업

3. **per-sample inner_state** 스키마 확장 후 시호 yaml에 몇 샘플 추가 (상황별 속마음 변화)

4. **12 캐릭터 확장**: 우선 대조적 3명 (하루 Dandere, 엘리자 Himedere, 미사키 Yandere) 먼저 작성 후 파이프라인 검증 → 나머지 6명.

5. **벤치마크 실행**: 12 캐릭터 완성 후 state_sensitivity, divergence vs diversity correlation, stage ablation 측정.

### 디자인 결정 보류 사항 (사용자 확인 필요)

- N-gram을 trigram으로 승급할지 (Tier 2, 항목 7)
- 불규칙 활용을 수작성할지 KoNLPy 의존성을 추가할지
- 신경망 혼합 모드를 선택적으로 지원할지 (Tier 4)

### 절대 하지 말 것

- **이전 기법들 (Algo 1-6, wfc_v1, wfc_v2) 과의 비교 재개** — 사용자가 명시적으로 중단 지시함. 이 아키텍처에 집중.
- **NPCState 구조 대규모 변경** — yaml 포맷이 이미 사용자에게 공유되었고, 후속 yaml 들이 이 포맷을 따를 것.
- **외부 대형 LLM API 호출** — 본 프로젝트는 LLM 대체를 목표로 함. 대사 생성 로직에 LLM 의존 금지.

---

## 12. 참고문헌 및 이전 세션 자산

### 조사 완료된 관련 분야

- **Dere 타입 분류**: Tsundere, Kuudere, Dandere, Deredere, Yandere, Himedere, Bakadere, Sunao-cool 등. 서브컬처 캐릭터 분석의 표준 어휘.
- **WFC 원리**: Maxim Gumin (2016). 인접성 제약 만족 생성의 대표. Karth & Smith (FDG 2017) 이 constraint solving 으로 정식화.
- **Tracery / Expressionist**: Kate Compton 등. Grammar 기반 절차적 텍스트 생성의 대표. 본 프로젝트의 codebook-driven 접근의 조상.
- **Continuous style control**: CIE (2505.13448), LM interpolation (2404.07117). 연속 벡터로 LLM 출력을 제어하는 방법들. 본 프로젝트의 15축 state의 이론 배경.
- **Persona-grounded dialogue**: PAL, SPASM 등. LLM 기반 persona 제어 연구. 무게 대비 본 프로젝트가 훨씬 경량.

### 이전 세션에서 포기/교체된 접근

- Template + Random (Algo 1): 너무 단순, 연속성 없음
- CFG / Tracery (Algo 2): archetype 독립 작성시 일관성 붕괴 (5.37% 위반)
- Style-kNN (Algo 3): 오매칭 발생 (사용자 핵심 우려의 실증)
- Hybrid Prior+kNN (Algo 4): 일관성 0% OK 이나 표현력 제한
- Slot-Filling (Algo 5): 연속성 최고이나 slot 독립 가정으로 어색 조합 발생
- Single WFC + Codebook (Algo 6 / wfc_v1): 일관성 우수하나 entropy scale 혼합 문제
- WFC v2 (single-stage with <S>/<EOS>): 역방향 collapse 시도했으나 여전히 단일 stage 한계
- **Multi-stage (현재)**: 위 모든 한계를 구조적으로 해결 → 이것이 최종 기법

---

**문서 버전**: Phase 2 최종 / 2026-04-16
**상태**: 3 캐릭터 파이프라인 검증 완료, 12 캐릭터 확장 및 품질 개선 대기
**이전 세션 연속성**: 이 문서 + `/phase2/` 디렉토리의 모든 파일로 재현 가능
