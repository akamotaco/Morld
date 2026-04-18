"""
Multi-stage Stage 3 - Function WFC
=====================================
Stage 2 결과의 placeholder (interj / end / punct) 를 채움.

핵심:
  - body 의 morph (V / C_n / C_l / C_reg) 를 참고해 end 후보 필터
  - state 축 중 verbosity, arousal, embarrassment 같은 micro 축만 사용
  - adjacency 가중치는 여기서도 유효 (이웃 body 토큰과의 관측 pair)
"""

from __future__ import annotations
from typing import List, Optional, Dict
import numpy as np

import sys
sys.path.insert(0, "/home/claude/dialogue_study/phase2")
from wfc_v2 import LoadedCodebook, LoadedToken
from content_wfc import Slot


# end 토큰의 morph 호환성 규칙 (완벽하지 않더라도 실용 수준)
# body의 morph → 허용되는 end 토큰 시작 문자 / 패턴
END_COMPAT = {
    # V (모음 끝): 대부분 가능하지만 일부 제한
    "V": {"avoid_prefix": ["으"]},   # "가" + "으세요" → 부자연스러움 방지
    "C_n": {"prefer_prefix": ["어", "아", "으"]},
    "C_l": {"prefer_prefix": ["어", "아"]},
    "C_reg": {"prefer_prefix": ["으", "어", "아", "습", "네", "죠"]},
    "none": {},
}


class FunctionWFC:
    def __init__(self, codebook: LoadedCodebook,
                 temperature: float = 0.6,
                 seed: int = 0,
                 adj_smoothing: float = 0.02):
        self.cb = codebook
        self.T = float(temperature)
        self.rng = np.random.default_rng(seed)
        self.adj_smooth = adj_smoothing

    def _pool(self, cls: str, intent: Optional[str] = None) -> List[LoadedToken]:
        base = list(self.cb.by_class.get(cls, []))
        if intent is None:
            return base
        filtered = [t for t in base if (not t.intents) or (intent in t.intents)]
        return filtered if filtered else base

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
        if left_text is not None:
            probs *= np.array([self._adj(left_text, t.text) for t in tokens])
        if right_text is not None:
            probs *= np.array([self._adj(t.text, right_text) for t in tokens])
        probs = np.clip(probs, 1e-12, None)
        probs /= probs.sum()
        return probs

    def _filter_end_by_morph(self, pool: List[LoadedToken],
                              body_morph: str) -> List[LoadedToken]:
        rules = END_COMPAT.get(body_morph, {})
        avoid = rules.get("avoid_prefix", [])
        if not avoid:
            return pool
        filtered = [t for t in pool if not any(t.text.startswith(p) for p in avoid)]
        return filtered if filtered else pool

    def fill(self, slots: List[Slot], intent: str,
             outer_vec: np.ndarray) -> List[Slot]:
        """interj / end / punct 자리를 채움. body 는 이미 결정되었음."""

        for i, s in enumerate(slots):
            if s.token is not None:
                continue
            if s.cls == "<S>" or s.cls == "<EOS>":
                s.token = self.cb.text_to_token.get(s.cls)
                continue

            pool = self._pool(s.cls, intent=intent)
            if not pool:
                continue

            # body 직후 end 인 경우 morph 호환성 필터
            if s.cls == "end" and i > 0 and slots[i - 1].token is not None \
               and slots[i - 1].cls == "body":
                body_tok = slots[i - 1].token
                pool = self._filter_end_by_morph(pool, body_tok.morph)

            # 이웃 텍스트 (adjacency용)
            left_txt = None
            right_txt = None
            if i > 0 and slots[i - 1].token is not None:
                left_txt = slots[i - 1].token.text
            if i < len(slots) - 1 and slots[i + 1].token is not None:
                right_txt = slots[i + 1].token.text

            probs = self._weights(pool, outer_vec, left_txt, right_txt)
            if len(probs) == 0:
                continue
            pick = int(self.rng.choice(len(pool), p=probs))
            s.token = pool[pick]

        return slots


# ------------------------------------------------------------------
# Stage 4: postprocess (한국어 fuse + 띄어쓰기 + 구두점 정리)
# ------------------------------------------------------------------

def _has_jongsung(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def _fuse(stem: str, ending: str, stem_morph: str = "none") -> str:
    """body + end 결합. 실용 수준 규칙만."""
    if not stem or not ending:
        return stem + ending
    if ending[0] in ",.!?~…":
        return stem + ending
    # 세요/십시오: 받침 있으면 '으' 삽입
    if ending in ("세요", "십시오", "시오"):
        if stem_morph in ("C_n", "C_reg", "C_l"):
            return stem + "으" + ending
        return stem + ending
    # 어요/아요: 모음 어간은 축약 시도
    if ending == "어요" and stem_morph == "V":
        last = stem[-1] if stem else ""
        # 하 + 어요 → 해요
        if last == "하":
            return stem[:-1] + "해요"
        # 가/오 등은 그대로 + 요
        if last in "가나다라마바사자차카타파":
            return stem + "요"
    return stem + ending


def assemble(slots: List[Slot]) -> str:
    """Stage 1-3 결과 slots → 최종 문자열."""
    toks = []
    for s in slots:
        if s.token is None:
            continue
        if s.cls == "<S>":
            toks = []
            continue
        if s.cls == "<EOS>":
            break
        toks.append(s)

    if not toks:
        return ""

    # 조립
    out = []
    for i, s in enumerate(toks):
        text = s.token.text
        if not out:
            out.append(text)
            continue
        prev = toks[i - 1]
        # 구두점은 바로 붙임
        if s.cls == "punct":
            # 이전 토큰 끝에 이미 구두점이 있으면 합치되 중복 방지
            last_char = out[-1][-1] if out[-1] else ""
            if last_char in ",.!?~…":
                # 같은 계열 (예: , 다음 ,) 이면 무시
                if last_char == text:
                    continue
                # . + ! 같은 상충은 뒤의 것으로 대체
                if (last_char in ",.") and (text in "!?"):
                    out[-1] = out[-1][:-1] + text
                    continue
                # ! + . → ! 유지
                if (last_char in "!?") and (text in ",."):
                    continue
                # 그 외는 중복 붙임 허용 (!!, !?, ... 등)
                combined = out[-1] + text
                if combined.count("!") > 2:
                    combined = combined.replace("!", "", combined.count("!") - 2)
                out[-1] = combined
            else:
                out[-1] = out[-1] + text
        # end 가 body 뒤에 오면 fuse
        elif s.cls == "end" and prev.cls == "body":
            out[-1] = _fuse(out[-1], text, prev.token.morph)
        # body/end 가 interj 뒤 (interj text 가 이미 구두점 포함하면 공백)
        else:
            out.append(text)

    result = " ".join(out).strip()
    # 후처리: 연속 공백, 시작 구두점 제거
    import re
    result = re.sub(r"\s+", " ", result)
    # 앞 구두점 제거
    result = re.sub(r"^[,.!?~…\s]+", "", result)
    # 중복 감탄사 정리 (interj_A + interj_B 간 여분)
    result = re.sub(r"([!?.]){3,}", r"\1\1", result)
    return result.strip()


# ------------------------------------------------------------------
# 스모크 테스트
# ------------------------------------------------------------------

if __name__ == "__main__":
    from state_ms import load_character_ms
    from structural_ngram import build_structural_grammar, StructuralSampler
    from content_wfc import ContentWFC
    from pathlib import Path

    root = Path("/home/claude/dialogue_study/phase2")

    for yaml_name in ["01_shiho.yaml", "02_yuka.yaml", "05_rin.yaml"]:
        npc, samples = load_character_ms(str(root / "examples" / yaml_name))
        cb = LoadedCodebook.load(str(root / "codebooks" / f"{npc.name}.json"))

        g = build_structural_grammar(npc, samples)
        stage1 = StructuralSampler(g, bandwidth=0.8, temperature=0.4, seed=42)
        stage2 = ContentWFC(cb, temperature=0.5, seed=42)
        stage3 = FunctionWFC(cb, temperature=0.6, seed=42)

        print(f"\n=== {npc.name} ({npc.archetype}) ===")
        for intent in ["greet", "complain", "thank"]:
            print(f"  [{intent}]")
            outs = set()
            for trial in range(8):
                stage1.rng = np.random.default_rng(42 + trial)
                stage2.rng = np.random.default_rng(100 + trial)
                stage3.rng = np.random.default_rng(200 + trial)
                cseq = stage1.sample(intent, npc.inner_vector(), max_len=5)
                filled = stage2.fill(cseq, intent, npc.outer_vector())
                filled = stage3.fill(filled, intent, npc.outer_vector())
                result = assemble(filled)
                if result:
                    outs.add(result)
            for o in outs:
                print(f"    {o}")
