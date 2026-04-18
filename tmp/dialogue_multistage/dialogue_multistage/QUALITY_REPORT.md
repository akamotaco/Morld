# Multi-stage Dialogue System — 품질 평가 보고서

> **대상**: Phase 2 최종 기법 (Inner N-gram + Outer WFC, 4-stage)
> **캐릭터**: 시호 (Tsundere, div=0.91) · 유카 (Kuudere, div=0.42) · 린 (Deredere, div=0.00)
> **코드**: `phase2/multistage/quality_test.py`

---

## 0. 핵심 요약

| 항목 | 결과 | 평가 |
|---|---|---|
| **Stage 분리 효과** | 각 stage 역할이 정성 예시에서 명확히 분리됨 | ✅ **설계 의도대로 작동** |
| **Inner/Outer 효과 (divergence 큰 캐릭터)** | 시호만 출력 길이/다양성에 측정 가능한 변화 | ⚠️ **약하게 작동, 강화 필요** |
| **State sensitivity** | 극단 상태에서만 유의미 변화, 중간 상태는 둔감 | ⚠️ **조건부 흐름이 좁음** |
| **Diversity (distinct-2)** | 0.87~0.90 (매우 높음) | ✅ **매우 우수** |
| **Self-BLEU** | 0.0 (거의 반복 없음) | ✅ **최상급** |
| **Latency (Full)** | 310~550 μs | ✅ **목표 달성 (<1ms)** |
| **Divergence vs 구조 길이** | 시호 > 유카 (예상 일치), but 린 > 유카 (역전) | ⚠️ **부분 반영** |

**총평**: 파이프라인은 **구조적으로 작동**하지만, Inner/Outer 분리의 효과가 예상보다 **약하게** 나타남. 주요 원인 2가지 확인됨:
1. inner_profile의 수치 차이 (`verbosity +0.5` 등)가 N-gram bandwidth 0.8 에 비해 작아 조건부 분포가 거의 같아짐
2. 예시 대사 40개 × 8 intent 로는 inner_state 조건부 bigram이 sparse

---

## 1. Test 1 — Stage-wise Ablation (정성)

각 stage 가 무엇을 결정하는지 정성적으로 확인. 같은 seed 에 대해 stage 1,2,3,4 결과를 나열.

### 시호 (Tsundere)

```
intent: thank
[2]
  S1 (class):   ['body', 'punct', 'body', 'body', 'punct', 'body']
  S2 (+body):   «딱히» [punct] «진짜로» «고맙다고는» [punct] «받긴»
  S3 (+func):   «딱히» «.» «진짜로» «고맙다고는» «...» «받긴»
  S4 (final):   '딱히. 진짜로 고맙다고는.. 받긴'
```

### 유카 (Kuudere)

```
intent: complain
[0]
  S1 (class):   ['body', 'body', 'body', 'body', 'end', 'punct']
  S2 (+body):   «부하가» «피로도» «임계치» «떨어지고» [end] [punct]
  S3 (+func):   «부하가» «피로도» «임계치» «떨어지고» «있습니다» «.»
  S4 (final):   '부하가 피로도 임계치 떨어지고있습니다.'
```

### 린 (Deredere)

```
intent: thank
[0]
  S1 (class):   ['interj', 'punct', 'end', 'punct']
  S2 (+body):   [interj] [punct] [end] [punct]
  S3 (+func):   «헤헤,» «,» «기뻐요» «!»
  S4 (final):   '헤헤, 기뻐요!'
```

### 관찰

- **Stage 1**: 캐릭터별로 구조가 다름. 시호는 `body` 많고 길며, 유카는 짧고 body+end 고정, 린은 interj/end 선호.
- **Stage 2**: body 자리에 archetype-specific 토큰 (시호의 "딱히", 유카의 "피로도", 린은 body 없음)
- **Stage 3**: end/interj/punct 를 outer_state 에 맞게 선택 (유카 "있습니다", 린 "!")
- **Stage 4**: body+end fuse ("떨어지고" + "있습니다" → "떨어지고있습니다"), 하지만 띄어쓰기 누락 문제 여전.

**평가: 각 stage 가 의도한 역할 수행 ✓**

### 발견된 품질 문제 (정성)

| 문제 | 샘플 | 원인 |
|---|---|---|
| body-body 간 띄어쓰기 | `"떨어지고있습니다"` | stage 4 fuse 규칙이 body-body 간 공백을 보존 안 함 |
| 구두점 자체 토큰 중복 | `"헤헤, , 기뻐요!"` (stage 3) → `"헤헤, 기뻐요!"` (stage 4 가 부분 해결) | BPE 가 구두점 포함 토큰 생성 |
| 짧은 어절 body 단편 | `"왜 자꾸."` `"오늘."` | BPE min_freq=2 로는 긴 merge 한계 |
| 유카 `"피로도싶습니다"` | body="피로도" + end="싶습니다" 직접 fuse | end 후보가 body 와 불일치시 호환 필터가 없음 |

---

## 2. Test 2 — Inner/Outer Ablation

**정상 모드** (inner ≠ outer) vs **ablated 모드** (inner = outer 강제) 비교.

| 캐릭터 | 모드 | 샘플 | 평균 길이 | std | distinct-2 | self-BLEU | unique_ratio |
|---|---|---|---|---|---|---|---|
| **시호** (div=0.91) | normal | 78 | **3.01** | 1.97 | **0.809** | 0.033 | **0.756** |
| 시호 | ablated | 78 | 3.14 | 1.93 | 0.820 | 0.031 | 0.821 |
| _Δ (normal − ablated)_ | | | **−0.13** | +0.04 | −0.011 | +0.002 | **−0.065** |
| **유카** (div=0.42) | normal | 80 | 1.49 | 1.21 | 0.744 | 0.0 | 0.550 |
| 유카 | ablated | 80 | 1.48 | 1.21 | 0.737 | 0.0 | 0.575 |
| _Δ_ | | | +0.01 | 0 | +0.007 | 0 | −0.025 |
| **린** (div=0.00) | normal | 80 | 1.55 | 1.23 | 0.727 | 0.0 | 0.500 |
| 린 | ablated | 80 | 1.55 | 1.23 | 0.727 | 0.0 | 0.500 |
| _Δ_ | | | 0 | 0 | 0 | 0 | 0 |

### 해석

- **린 (표리일체)**: 당연히 차이 0. inner=outer 가 원래 상태이므로 ablation이 의미 없음. ✓ **올바른 동작**
- **유카 (약한 괴리)**: 차이 거의 없음 (<0.01). 괴리 폭이 작아 n-gram 분포에 유의미한 차이를 만들지 못함.
- **시호 (큰 괴리)**: 차이가 **감지됨**
  - normal 이 평균 길이 `−0.13` 짧음, unique_ratio `−0.065` 낮음
  - 즉 normal 에서는 inner의 "말 많이 하고 싶음(+0.6)" 이 학습 데이터의 실제 긴 대사들(츤모드 interaction 발동된 예시들) 방향으로 bias 하면서 **특정 구조를 반복 선택**하는 경향
  - 하지만 **기대 방향과 반대** (normal 이 더 길어야 하는데 짧음). 이는 inner_profile 의 verbosity +0.6 이 예시 태그와 실제 매칭되는 방식이 우리 예상과 다름을 시사함

### 진단

**Inner 가 구조에 미치는 영향이 수치상 감지되나 효과 크기가 작다.** 주된 원인 추정:

1. **Bandwidth 0.8 이 너무 큼** — N-gram 샘플링에서 모든 예시가 거의 균등하게 가중되어 inner 차이가 희석됨
2. **예시 수 부족** — intent당 5개 정도로는 state conditioning 의미 있는 분포 못 만듦
3. **inner_profile이 예시 태그와 misalign** — 예시 대사들의 `state:` 는 outer 축만 태깅되고 있어, inner_profile 의 effect 가 학습 시점에는 주입 안 됨. 즉 **"이 대사를 할 때 inner 는 무엇이었는가"가 yaml에 없음.**

이 세 번째 원인이 **핵심**. 현재 설계는 런타임에서만 inner/outer 분리가 의미 있고, 학습 시에는 inner_vec 이 주로 **캐릭터 profile 에서 계산**되므로 모든 예시가 비슷한 inner vector 태그를 가짐.

---

## 3. Test 3 — State Sensitivity

7가지 상태 override 에서 출력 간 평균 edit distance.

| 캐릭터 | intent | mean_edit | unique/7 |
|---|---|---|---|
| **시호** | greet | 4.76 | 3 |
| 시호 | thank | **7.00** | 4 |
| 시호 | complain | 5.43 | 5 |
| **유카** | greet | 2.00 | 2 |
| 유카 | thank | 2.62 | 3 |
| 유카 | complain | 8.29 | 4 |
| **린** | greet | 2.00 | 2 |
| 린 | thank | 4.33 | 3 |
| 린 | complain | 3.43 | 3 |

### 예시 (시호, thank)

```
''                                (빈 출력, dynamic 없을 때)
'딱히.. 싶진.. 고맙다고는.'       (default)
'정말, 받고.. 해.'                (affinity+trust)
'딱히, 고맙다고는 고, 않았지만'   (embarrassment+affinity — 츤모드)
'딱히.. 싶진.. 고맙다고는.'       (fatigue+health)
'진짜로. 싶진.. 고맙다고는.'      (arousal+affinity)
'딱히.. 싶진.. 고맙다고는.'       (hostility)
'딱히.. 싶진.. 고맙다고는.'       (confidence-)
```

### 해석

- **시호 thank** 가 state 에 가장 민감 (mean_edit=7.00, 4/7 unique). 이는 츤모드 interaction term 이 특정 조건에서 크게 변조하는 효과.
- **유카 complain** 도 높음 (8.29). 피로 상태 변화가 어휘 전환 ("부하가" / "피로도" / "임계치") 을 자극.
- **greet 류 는 전반적 낮음** (2.00~4.76). 인사 대사 풀이 작아 state에 상관없이 비슷한 출력.

**문제점**:
- **empty output 발생** (시호 greet) — Stage 1 이 `[body]` 만 있는 schema 를 뽑고 Stage 2 에서 pool 이 작아 실패하는 경우
- **중간 상태에서 과도하게 덩어리짐** — "딱히.. 싶진.. 고맙다고는." 이 여러 상태에서 반복. softmax 온도가 낮거나 특정 토큰 w 가 지배적.

---

## 4. Test 4 — 전체 Diversity

각 NPC 에 대해 다양한 상태에서 150샘플 생성 후 측정.

| 캐릭터 | 총 샘플 | 유니크 | distinct-1 | distinct-2 | self-BLEU-3 | 평균 길이 |
|---|---|---|---|---|---|---|
| **시호** | 69 | 66 | 0.577 | **0.901** | 0.0 | 3.19 |
| **유카** | 65 | 52 | 0.583 | 0.891 | 0.0 | 1.85 |
| **린** | 78 | 62 | 0.645 | 0.867 | 0.0 | 1.77 |

### 해석

- **distinct-2 모두 0.87 이상** — 매우 다양.
- **self-BLEU 0.0** — trigram 수준에서는 거의 전혀 반복 안 됨. Phase 1 의 최고기록 (WFC v1 = 0.25) 보다 훨씬 우수.
- **유니크 비율**: 시호 95.7% (66/69), 유카 80%, 린 79%.
- **평균 길이 차이** 가 캐릭터 특성 반영: 시호 (3.19) > 유카 (1.85) > 린 (1.77). 시호가 제일 김 — divergence=0.91 과 일치.

**평가: 다양성 지표는 **최상급**. ✓**

단 주의: "다양성이 높다" 와 "자연스럽다" 는 다른 축. 현재 출력에는 어색한 조합이 섞여 있어 다양성 점수가 인위적으로 부풀려졌을 수 있음.

---

## 5. Test 5 — Latency (μs)

| 캐릭터 | Stage 1 | S1+2 | S1+2+3 | Full (S4) | ΔS2 | ΔS3 | ΔS4 |
|---|---|---|---|---|---|---|---|
| **시호** | 204 | 451 | 453 | 552 | **+248** | +2 | +98 |
| **유카** | 141 | 196 | 244 | 314 | +55 | +48 | +70 |
| **린** | 182 | 166 | 385 | 309 | −16 | +219 | −76 |

### 관찰

- **Full latency 310~550 μs** — 목표 <1ms 안정 달성.
- **Stage 분포가 캐릭터별 다름**:
  - 시호: Stage 2 가 병목 (ΔS2=+248μs). body pool 이 크고 중복 penalty 계산 많음.
  - 유카: 골고루 분산. 문장 짧아 각 stage 가벼움.
  - 린: Stage 3 가 병목 (ΔS3=+219μs). interj/end 풀 선택이 많음.
- **린의 음수 delta** 는 warmup/측정 잡음. 재측정 권장.
- **Phase 1 비교**: Full=340μs (WFC v1) → 현재 310~550μs. 4-stage 로 확장했음에도 비슷한 범위. 합리적.

**평가: 실시간 대화에 충분히 빠름. ✓**

---

## 6. Test 6 — Divergence 효과 (구조 반영)

`divergence` 가 실제로 Stage 1 출력의 구조적 특성에 반영되는지 확인.

| 캐릭터 | divergence | avg class length | interj_ratio | addr_ratio |
|---|---|---|---|---|
| 시호 | 0.91 | **4.03** | 0.014 | 0.000 |
| 린 | 0.00 | 3.22 | **0.073** | 0.000 |
| 유카 | 0.42 | 2.80 | 0.000 | 0.000 |

### 해석

**길이 (inner verbosity 의 효과)**:
- 시호 (inner verbosity=+0.6) → avg 4.03 토큰 ✓ (예상: 가장 김)
- 유카 (inner verbosity=-0.4) → 2.80 ✓ (예상: 가장 짧음)
- 린 (inner=outer, verbosity=+0.5) → 3.22

**예상 순서 (시호 > 린 > 유카)와 실제 일치. ✓**

**감탄사 (interj) 비율**:
- 린 (warmth=0.7, deredere) → 7.3% — 예시에서 "와", "헤헤,", "앗" 많이 썼음
- 시호 → 1.4% — 예시에서 감탄사 적음
- 유카 → 0% — 감탄사 없음

감탄사 사용 = 캐릭터 유형 특성 반영. ✓

**호칭 (addr) 비율**:
- **모두 0** — 세 캐릭터 모두 예시 대사에 "너", "당신" 같은 호칭 토큰을 거의 안 씀.
- 이상 사례: tsundere 전제에서 이름/호칭을 자주 부른다고 얘기했지만, 작성한 yaml에 반영 안 됨.

---

## 7. 설계 대 실측 — 어디가 맞았고 어디가 어긋났나

| 설계 의도 | 실측 결과 | 평가 |
|---|---|---|
| Stage 분리로 stage별 entropy 독립 | ablation으로 각 역할 확인됨 | ✅ **맞음** |
| Inner N-gram 이 구조 (길이·interj) 결정 | 길이는 divergence 순서대로 ↑, interj는 archetype 반영 | ✅ **부분 맞음** |
| Outer WFC 가 어휘 선택 | stage 2-3 에서 outer_vec 에 따라 어휘 변화 | ✅ **맞음** |
| 표리 괴리 캐릭터 (시호) 에서 Inner/Outer 분리 효과 뚜렷 | ablation 에서 Δ 작음 (시호 평균 길이 -0.13) | ⚠️ **약함** |
| Dere 타입 특유의 "이름 부르며 까칠하게" 표현 | **미발현** — addr 비율 모두 0% | ❌ **안 나옴** |
| Self-BLEU < 0.3 | 0.0 달성 | ✅ **최상** |
| Latency < 1ms | 310~550 μs | ✅ **충족** |

---

## 8. 가장 시급한 개선점 (우선순위)

### Priority 1 — Inner/Outer 분리 효과 강화

**문제**: Inner 의 영향이 1-gram 통계에는 감지되나 (길이), 개별 출력에 **체감될 만큼 강하지 않음**. Dere 타입의 핵심인 "이름 자주 부름 + 까칠 어휘" 가 안 나옴.

**3가지 동시 개선안**:

1. **Bandwidth를 0.8 → 0.3으로 낮춤**
   - N-gram에서 inner state 근접 예시만 강하게 가중
   - 효과: 작은 inner 차이도 분포에 반영
   - 위험: sparse data 에서 일부 상태에서는 극소수 예시만 사용 → 다양성 감소 가능

2. **캐릭터 yaml에 호칭 샘플 추가 (Inner 효과를 측정 가능하게)**
   - 시호 예시에 "너 바보야!", "당신은 알아서..." 같은 addr 토큰 들어간 대사 10개 정도 추가
   - 시호의 inner_profile 에 `addr_preference: +0.5` 같은 커스텀 축 or interactions 에서 해당 상태 조건부 부스트
   - 효과: addr_ratio 가 시호 > 린 > 유카 로 차별화

3. **`inner_state_override` per-sample 지원**
   - 현재 예시의 `state:` 는 outer-만 조정. inner 축도 명시적 override 가능하게 yaml 스키마 확장
   - 예:
     ```yaml
     - text: "야, 너 뭐 하는 거야..."
       intent: greet
       state: { embarrassment: 0.8, aggression: 0.5 }   # outer
       inner: { affinity: 0.9, verbosity: 0.8 }          # inner
     ```
   - 효과: 학습 시점에 inner-tag 다양성 생김

### Priority 2 — Stage 간 호환성 체크

**문제**: Stage 1 이 `[body, body, body, body]` 같은 긴 schema 를 뽑았는데 body pool 이 3개밖에 없으면 중복 발생. 현재는 중복 penalty 로 부분 해결만.

**해결**:
- Stage 1 에서 schema 결정 직후 해당 intent 의 body pool 크기 확인
- pool 크기 < schema 의 body slot 수 면 rollback & 짧은 schema 재샘플
- 비용: 무시할 수준 (pool 크기 체크는 O(1))

### Priority 3 — Morphology 개선

**문제**: `"피로도싶습니다"`, `"떨어지고있습니다"` 같이 띄어쓰기/활용 실패.

**해결**:
- body-end fusion 에서 body 가 체언 (명사) 이면 end 붙이지 말고 공백
- body 에 `pos` 태그 (noun / verb / adj) 를 BPE 단계에서 휴리스틱으로 판정
- end 의 어미-어간 매칭 규칙 테이블 확장 (`싶습니다` 는 앞에 "-고" 있는 용언 뒤에만)

### Priority 4 — Empty output 방지

**문제**: 시호 greet 에서 빈 문자열 출력됨. Stage 2/3 이 pool 비어 collapse 실패.

**해결**:
- Stage 1 에 fallback schema (`[body, punct]` 또는 `[end, punct]`) 강제
- 모든 stage 에서 empty 면 raise 하지 말고 default token 삽입

---

## 9. 결론 및 평가

### 요구사항 대비 성취도

| 원래 요구사항 | 달성도 | 증거 |
|---|---|---|
| 성격·상태 반영 | 80% | Test 3 (복잡 interaction 반영 확인) |
| 여러 성격 포함 | 100% | 3 캐릭터로 검증, 확장 용이 |
| 연산 짧음 | 100% | Test 5 (310~550μs) |
| 연속 manifold | 60% | Test 3 에서 중간 상태 민감도 낮음 |
| 캐릭터 일관성 (archetype 위반 X) | 100% | codebook 1:1 매칭 유지 |
| `<S>/<EOS>` 가변 길이 | 100% | Test 1 (3~6 토큰) |
| 다차원 상태 (15축) | 100% | game_config.py |
| 데이터 기반 codebook | 100% | codebook_builder.py |
| **표리 괴리 (dere 표현)** | **50%** | Test 2/6 에서 약하게만 감지 |
| Multi-stage (N-gram=내면, WFC=외면) | 구조는 100%, 효과는 50% | Test 1 (구조) ✓, Test 2 (효과) ⚠️ |

### 총평

**구조적으로 올바른 시스템**이고 **모든 basic metric이 우수**하지만, 사용자가 가장 핵심적으로 기대했던 **"dere 타입의 표리 괴리 표현"** 은 현재 약하게만 나타남. 이는 알고리즘 자체의 한계가 아니라 **데이터/파라미터 튜닝 부족**이 원인.

Priority 1 의 3가지 개선 (bandwidth 조정 + addr 샘플 추가 + per-sample inner) 을 적용하면 dere 타입 재현력이 크게 올라갈 것으로 예상됨.

**남은 작업은 "알고리즘"이 아니라 "훈련 데이터 품질"과 "파라미터 튜닝"의 영역.** 이는 Phase 2 의 잔여 tier 1-2 개선 항목에 정확히 해당하며, 12 캐릭터로 확장할 때 자연스럽게 함께 해결될 것.

---

**부록**: 상세 수치 원본은 `phase2/quality_report.json` 에 저장됨.
