"""
Multi-stage Stage 1 - Structural N-gram
==========================================
class sequence 수준의 구조 생성.

원리:
  - 예시 대사들에서 class sequence 만 추출
    예: "어, 반가워요!" → [interj, body_greet, punct] (class 수준)
  - inner_state 조건부 weighted bigram 학습
    각 예시는 해당 character 의 inner_vector 를 tag 로 가짐
  - 런타임에 현 inner_state 와의 거리로 가중한 bigram 전이를 계산
  - 그 bigram LM 으로 class sequence 를 샘플

inner_state 를 학습에 쓰는 이유:
  "당시 캐릭터가 어떤 상태에서 그런 구조의 문장을 했는가" 를 기억.
  런타임에 같은 상태일 때 같은 구조 선호하도록.

표리 괴리 캐릭터의 경우:
  inner_vector 는 outer 와 다르므로, N-gram 은 inner 를 학습·참조.
  → "속마음 상태" 에 맞는 구조 (호칭 자주, 길게 말함 등) 가 나옴.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import numpy as np

from game_config import AXIS_NAMES, AXIS_INDEX, N_DIM, to_vector


# ------------------------------------------------------------------
# 데이터 구조
# ------------------------------------------------------------------

@dataclass
class StructuralSample:
    """학습에 쓰일 하나의 sample."""
    intent: str
    class_seq: List[str]       # 시작·종료 포함: ["<S>", "interj", ..., "<EOS>"]
    inner_vec: np.ndarray      # 그 대사 생성 당시의 inner state


@dataclass
class StructuralGrammar:
    """intent 별로 학습된 class sequence 데이터."""
    # intent → samples
    samples_by_intent: Dict[str, List[StructuralSample]] = field(default_factory=lambda: defaultdict(list))

    def add(self, s: StructuralSample):
        self.samples_by_intent[s.intent].append(s)


# ------------------------------------------------------------------
# 학습: 예시에서 class sequence 추출
# ------------------------------------------------------------------

def _classify_for_structural(tok: str, position: str) -> str:
    """간이 class 분류 (codebook_builder 와 일관).

    class 체계 (Stage 1 이 보는):
      interj, addr, body, end, punct
    의도 정보는 sample level 에서 관리하므로 body_X 로 쪼갤 필요 없음.
    """
    from codebook_builder import (
        _is_punct_only, _is_interjection, _is_address, _is_ending
    )
    if _is_punct_only(tok):
        return "punct"
    if position == "first" and _is_interjection(tok):
        return "interj"
    if _is_interjection(tok):
        return "interj"
    if _is_address(tok):
        return "addr"
    if position == "last" or _is_ending(tok):
        return "end"
    return "body"


def build_structural_grammar(npc, samples: List[Dict]) -> StructuralGrammar:
    """예시 대사에서 구조 학습.

    각 sample 에 대해 그 당시의 inner_vector 를 계산해 태깅.
    dynamic override 가 있으면 적용.
    """
    from codebook_builder import tokenize_raw

    grammar = StructuralGrammar()

    for s in samples:
        toks = tokenize_raw(s["text"])
        if not toks:
            continue
        classes = []
        for i, t in enumerate(toks):
            pos = "first" if i == 0 and len(toks) > 1 else \
                  "last" if i == len(toks) - 1 else "mid"
            classes.append(_classify_for_structural(t, pos))

        # <S> / <EOS> sentinel
        seq = ["<S>"] + classes + ["<EOS>"]

        # 이 sample 당시의 inner state
        # state: outer/inner 공통 dynamic, inner: inner 전용 override
        state_obj = npc.with_state(**s.get("state", {}))
        if s.get("inner"):
            state_obj = state_obj.with_inner(**s["inner"])
        iv = state_obj.inner_vector()

        grammar.add(StructuralSample(
            intent=s["intent"], class_seq=seq, inner_vec=iv,
        ))

    return grammar


# ------------------------------------------------------------------
# 샘플러: inner_state 가중 bigram 으로 class sequence 생성
# ------------------------------------------------------------------

class StructuralSampler:
    """
    weighted n-gram 샘플러.

    전이 확률:
      P(next | prev, inner) ∝ Σ_sample w(sample.inner, inner) * 1[sample has (prev→next)]

    w(s1, s2) = exp(-|s1 - s2| / bandwidth)  — Gaussian-like kernel.
    """

    def __init__(self, grammar: StructuralGrammar,
                 bandwidth: float = 0.3,
                 temperature: float = 0.4,
                 seed: int = 0):
        self.g = grammar
        self.bw = bandwidth
        self.T = temperature
        self.rng = np.random.default_rng(seed)

    def _weighted_bigram(self, intent: str,
                         current: str,
                         inner_vec: np.ndarray) -> Dict[str, float]:
        """현 state 에 가까운 예시들 기준 (current → ?) 의 전이 확률."""
        samples = self.g.samples_by_intent.get(intent, [])
        if not samples:
            return {}

        # 각 sample 의 inner 거리 → 가중치
        dists = np.array([
            float(np.linalg.norm(s.inner_vec - inner_vec)) for s in samples
        ])
        weights = np.exp(-dists / max(self.bw, 1e-6))

        # 전이 누적
        trans = defaultdict(float)
        for s, w in zip(samples, weights):
            for i in range(len(s.class_seq) - 1):
                if s.class_seq[i] == current:
                    trans[s.class_seq[i + 1]] += float(w)

        if not trans:
            return {}
        total = sum(trans.values())
        return {k: v / total for k, v in trans.items()}

    def sample(self, intent: str, inner_vec: np.ndarray,
               max_len: int = 8) -> List[str]:
        """class sequence 샘플. <S> / <EOS> sentinel 포함."""
        seq = ["<S>"]
        for _ in range(max_len):
            probs = self._weighted_bigram(intent, seq[-1], inner_vec)
            if not probs:
                break
            keys = list(probs.keys())
            vals = np.array(list(probs.values()))
            # 온도 적용
            vals = np.power(vals, 1.0 / max(self.T, 1e-6))
            vals = vals / vals.sum()
            pick = str(self.rng.choice(keys, p=vals))
            seq.append(pick)
            if pick == "<EOS>":
                break
        if seq[-1] != "<EOS>":
            seq.append("<EOS>")
        return seq


# ------------------------------------------------------------------
# 스모크 테스트
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.path.insert(0, "/home/claude/dialogue_study/phase2")

    from state_ms import load_character_ms
    from pathlib import Path

    root = Path("/home/claude/dialogue_study/phase2")
    for yaml_name in ["01_shiho.yaml", "02_yuka.yaml", "05_rin.yaml"]:
        npc, samples = load_character_ms(str(root / "examples" / yaml_name))
        g = build_structural_grammar(npc, samples)

        print(f"\n=== {npc.name} ({npc.archetype}) ===")
        print(f"  총 샘플: {sum(len(v) for v in g.samples_by_intent.values())}")
        print(f"  intent별: {[(k, len(v)) for k, v in g.samples_by_intent.items()]}")

        sampler = StructuralSampler(g, bandwidth=0.8, temperature=0.4, seed=42)

        # 기본 상태
        print(f"\n  [기본 상태 - inner]")
        for intent in ["greet", "complain", "thank"]:
            variations = set()
            for s in range(10):
                sampler.rng = np.random.default_rng(42 + s)
                seq = sampler.sample(intent, npc.inner_vector())
                variations.add(tuple(seq))
            print(f"    {intent}:")
            for v in list(variations)[:5]:
                print(f"      {list(v)}")

        # 변화된 상태: affinity 높음
        if npc.archetype == "tsundere":
            print(f"\n  [affinity=0.8, embarrassment=0.7 - 츤모드]")
            mod = npc.with_state(affinity=0.8, embarrassment=0.7)
            for intent in ["greet", "thank"]:
                variations = set()
                for s in range(10):
                    sampler.rng = np.random.default_rng(42 + s)
                    seq = sampler.sample(intent, mod.inner_vector())
                    variations.add(tuple(seq))
                print(f"    {intent}:")
                for v in list(variations)[:5]:
                    print(f"      {list(v)}")
