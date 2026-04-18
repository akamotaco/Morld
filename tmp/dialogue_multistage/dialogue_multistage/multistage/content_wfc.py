"""
Multi-stage Stage 2 - Content WFC
====================================
Stage 1 에서 나온 class sequence 의 body 자리를 outer_vector 로 채운다.
여기가 **표현력의 주 무대** — state sensitivity 가 가장 강해야 함.

입력:
  class_seq: ["<S>", "interj", "body", "punct", "body", "end", "<EOS>"]
  outer_vec: 15차원 state vector
  codebook: LoadedCodebook (Phase 2 에서 만든 것)

출력:
  filled: [("<S>", "<S>"), ("interj", None), ("body", "반갑"), ...]
    — body 자리만 구체 토큰 결정, 나머지는 placeholder (None)
    interj, end 는 Stage 3 에서 채움.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
import numpy as np

import sys
sys.path.insert(0, "/home/claude/dialogue_study/phase2")
from wfc_v2 import LoadedCodebook, LoadedToken


@dataclass
class Slot:
    """class sequence 의 한 자리. stage 2 에서는 body 만 resolve."""
    cls: str                          # "interj" / "body" / "end" / "punct" / "<S>" / "<EOS>"
    intent: Optional[str] = None      # body 자리용: 이 자리의 의도 힌트
    token: Optional[LoadedToken] = None   # collapse 결과


class ContentWFC:
    """body-only WFC.

    원리:
      1. body slot 후보: codebook 에서 tclass == body_{intent} 인 토큰들
      2. state-weighted softmax + adjacency (좌/우 이웃의 cls 타입 고려)
      3. 가장 선명한 (entropy 최소) body slot 먼저 collapse
      4. 연쇄된 body slot 들은 adjacency 로 서로를 제약
    """

    def __init__(self, codebook: LoadedCodebook,
                 temperature: float = 0.5,
                 seed: int = 0,
                 adj_smoothing: float = 0.02):
        self.cb = codebook
        self.T = float(temperature)
        self.rng = np.random.default_rng(seed)
        self.adj_smooth = adj_smoothing

    def _body_pool(self, intent: str) -> List[LoadedToken]:
        """body_{intent} + body 로 태그된 토큰들."""
        cls_name = f"body_{intent}"
        pool = list(self.cb.by_class.get(cls_name, []))
        # fallback: 태그 무시한 body (혹시 mismatch)
        if not pool:
            # intent 태그를 포함하는 토큰을 아무 body class 에서 찾기
            for tcls, tlist in self.cb.by_class.items():
                if tcls.startswith("body_"):
                    for t in tlist:
                        if intent in t.intents:
                            pool.append(t)
        return pool

    def _adj(self, left: str, right: str) -> float:
        obs = self.cb.adjacency.get(left, {}).get(right, 0)
        return float(obs) + self.adj_smooth

    def _weights(self, tokens: List[LoadedToken],
                 state_vec: np.ndarray,
                 left_text: Optional[str] = None,
                 right_text: Optional[str] = None) -> np.ndarray:
        if not tokens:
            return np.array([])
        feats = np.stack([t.feature_vec for t in tokens])
        bases = np.array([t.base_w for t in tokens], dtype=np.float32)
        scores = feats @ state_vec / max(self.T, 1e-6)
        scores = scores - scores.max()
        probs = np.exp(scores) * bases
        # adjacency (이웃이 결정된 경우만)
        if left_text is not None:
            probs = probs * np.array([self._adj(left_text, t.text) for t in tokens])
        if right_text is not None:
            probs = probs * np.array([self._adj(t.text, right_text) for t in tokens])
        probs = np.clip(probs, 1e-12, None)
        probs /= probs.sum()
        return probs

    @staticmethod
    def _entropy(p: np.ndarray) -> float:
        pp = p[p > 1e-12]
        if len(pp) == 0:
            return 0.0
        return float(-np.sum(pp * np.log(pp)))

    def fill(self, class_seq: List[str], intent: str,
             outer_vec: np.ndarray) -> List[Slot]:
        """body 자리만 채워 Slot 리스트 반환."""
        slots = [Slot(cls=c, intent=intent) for c in class_seq]

        # 초기: S/EOS 는 자기 자신
        for s in slots:
            if s.cls == "<S>" or s.cls == "<EOS>":
                s.token = self.cb.text_to_token.get(s.cls)  # 그대로

        # body slot 인덱스들
        body_indices = [i for i, s in enumerate(slots) if s.cls == "body"]
        if not body_indices:
            return slots

        # body pool 미리
        pool = self._body_pool(intent)
        if not pool:
            return slots

        # 각 body slot 에 대해 iteration 으로 entropy-min 먼저 resolve
        unresolved = set(body_indices)
        max_steps = len(body_indices) * 2

        for _ in range(max_steps):
            if not unresolved:
                break

            # 각 미결정 body 의 현재 entropy 계산
            candidates = []
            for idx in unresolved:
                left_txt = None
                right_txt = None
                # 왼쪽 이웃이 결정된 토큰이면 text 전달
                if idx > 0 and slots[idx - 1].token is not None:
                    left_txt = slots[idx - 1].token.text
                if idx < len(slots) - 1 and slots[idx + 1].token is not None:
                    right_txt = slots[idx + 1].token.text
                p = self._weights(pool, outer_vec, left_txt, right_txt)
                # 이웃이 body 이고 같은 token 이면 penalty
                for i_tok, tok in enumerate(pool):
                    for nb_idx in (idx - 1, idx + 1):
                        if 0 <= nb_idx < len(slots) and slots[nb_idx].cls == "body":
                            if slots[nb_idx].token is not None and slots[nb_idx].token.text == tok.text:
                                p[i_tok] *= 0.05   # 같은 body 인접은 강한 억제
                if p.sum() > 0:
                    p = p / p.sum()
                e = self._entropy(p)
                candidates.append((e, idx, p))

            if not candidates:
                break
            candidates.sort(key=lambda x: x[0])
            _, pick_idx, probs = candidates[0]

            # collapse (방금 뽑은 토큰과 같은 body 가 인접 cell 에 오지 않도록 약한 규칙 적용)
            chosen_i = int(self.rng.choice(len(pool), p=probs))
            slots[pick_idx].token = pool[chosen_i]
            unresolved.remove(pick_idx)

        return slots


if __name__ == "__main__":
    from state_ms import load_character_ms
    from structural_ngram import build_structural_grammar, StructuralSampler
    from pathlib import Path

    root = Path("/home/claude/dialogue_study/phase2")

    for yaml_name in ["01_shiho.yaml", "02_yuka.yaml", "05_rin.yaml"]:
        npc, samples = load_character_ms(str(root / "examples" / yaml_name))
        cb = LoadedCodebook.load(str(root / "codebooks" / f"{npc.name}.json"))

        g = build_structural_grammar(npc, samples)
        stage1 = StructuralSampler(g, bandwidth=0.8, temperature=0.4, seed=42)
        stage2 = ContentWFC(cb, temperature=0.5, seed=42)

        print(f"\n=== {npc.name} ({npc.archetype}) ===")
        for intent in ["greet", "complain", "thank"]:
            print(f"  [{intent}]")
            for trial in range(4):
                stage1.rng = np.random.default_rng(42 + trial)
                stage2.rng = np.random.default_rng(100 + trial)
                class_seq = stage1.sample(intent, npc.inner_vector(), max_len=6)
                filled = stage2.fill(class_seq, intent, npc.outer_vector())
                # 출력 형식: class / body 토큰 표시
                out = []
                for s in filled:
                    if s.cls == "body" and s.token:
                        out.append(f"«{s.token.text}»")
                    elif s.cls in ("<S>", "<EOS>"):
                        pass
                    elif s.cls == "body":
                        out.append("«?»")
                    else:
                        out.append(f"[{s.cls}]")
                print(f"    {' '.join(out)}")
