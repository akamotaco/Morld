"""
Phase 2 - WFC v2 Engine
==========================
v1 대비 개선:
  1. <S> / <EOS> boundary 토큰
  2. 역방향 collapse (어미부터 결정) — hard reverse
  3. 가변 길이 (max_cells + EOS 조기 종료)
  4. 데이터 기반 adjacency (학습된 transition 행렬)
  5. 15축 sparse feature 와 state 내적
  6. codebook 을 JSON에서 로드
"""

from __future__ import annotations
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict

from game_config import AXIS_NAMES, AXIS_INDEX, N_DIM, to_vector
from state_v2 import NPCStateV2


# ------------------------------------------------------------------
# Codebook (JSON에서 로드한 형태)
# ------------------------------------------------------------------

@dataclass
class LoadedToken:
    text: str
    tclass: str
    morph: str
    feature_vec: np.ndarray   # dense (N_DIM,)
    base_w: float
    intents: List[str]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "LoadedToken":
        fv = to_vector(d.get("feature", {}))
        return LoadedToken(
            text=d["text"], tclass=d["tclass"],
            morph=d.get("morph", "none"),
            feature_vec=fv,
            base_w=float(d.get("base_w", 1.0)),
            intents=list(d.get("intents", [])),
        )


@dataclass
class LoadedCodebook:
    archetype: str
    tokens: List[LoadedToken]
    adjacency: Dict[str, Dict[str, int]]     # left_text → right_text → count
    schemas: Dict[str, List[List[str]]]      # intent → [class_seq, ...]

    # 파생 인덱스 (생성자에서 구축)
    by_class: Dict[str, List[LoadedToken]] = field(default_factory=lambda: defaultdict(list))
    text_to_token: Dict[str, LoadedToken] = field(default_factory=dict)

    @staticmethod
    def load(path: str) -> "LoadedCodebook":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        tokens = [LoadedToken.from_dict(t) for t in d["tokens"]]
        cb = LoadedCodebook(
            archetype=d["archetype"],
            tokens=tokens,
            adjacency=d.get("adjacency", {}),
            schemas=d.get("schemas", {}),
        )
        for t in tokens:
            cb.by_class[t.tclass].append(t)
            cb.text_to_token[t.text] = t
        return cb


# ------------------------------------------------------------------
# Schema 선택
# ------------------------------------------------------------------

def _normalize_schema(classes: List[str]) -> List[str]:
    """
    학습된 class 시퀀스를 canonical 형태로 정규화.
    - 연속된 body_X 들은 하나로 묶음 (body 는 한 번만)
    - 문두 punct 제거
    - <S>, <EOS> 자리 확보
    """
    if not classes:
        return classes
    # 문두 punct 제거
    while classes and classes[0] == "punct":
        classes = classes[1:]
    out = []
    seen_body = False
    for c in classes:
        if c.startswith("body_"):
            if seen_body:
                # 이전 body 와 이 body 를 합쳐 하나로.
                # 다만 intent 매칭을 위해 첫 body intent 를 유지.
                continue
            out.append(c)
            seen_body = True
        else:
            out.append(c)
    return out


def choose_schema(cb: LoadedCodebook, intent: str, rng: np.random.Generator,
                  target_length: Optional[str] = None) -> List[str]:
    """
    intent 에 대해 학습된 schema 중 하나를 샘플링.
    target_length: "short" | "normal" | "long" | None
    """
    raw_options = cb.schemas.get(intent, [])
    # 정규화
    options = [_normalize_schema(s) for s in raw_options]
    # 빈 schema 제거, 중복 제거
    seen_keys = set()
    unique = []
    for s in options:
        if not s:
            continue
        k = tuple(s)
        if k not in seen_keys:
            seen_keys.add(k)
            unique.append(s)
    options = unique

    if not options:
        return [f"body_{intent}", "end"]

    if target_length is None:
        idx = int(rng.integers(len(options)))
        return list(options[idx])

    lens = np.array([len(s) for s in options], dtype=np.float32)
    if target_length == "short":
        weights = 1.0 / (lens + 1e-6)
    elif target_length == "long":
        weights = lens
    else:
        # normal: 중앙값 근처
        med = np.median(lens)
        weights = np.exp(-np.abs(lens - med))
    weights = weights / weights.sum()
    idx = int(rng.choice(len(options), p=weights))
    return list(options[idx])


# ------------------------------------------------------------------
# WFC v2 Solver
# ------------------------------------------------------------------

@dataclass
class Cell:
    """superposition 을 유지하는 한 cell."""
    allowed: List[LoadedToken]
    collapsed: Optional[LoadedToken] = None


class WFCv2:
    """
    역방향 collapse + <S>/<EOS> 기반 가변 길이 WFC.

    핵심 루프:
      1. 시작 cell 들 준비. 가장 오른쪽 cell 은 <EOS> 가 고정 (sentinel).
      2. 가장 오른쪽 미결정 cell 부터 entropy 로 선택.
         (동점시 더 오른쪽 우선, hard reverse.)
      3. state-weighted softmax 로 sample, collapse.
      4. 양옆 이웃의 superposition 을 adjacency 로 propagate.
      5. 어느 cell 이 <S> 로 collapse 되면, 그 왼쪽은 모두 <S> 연쇄로.
      6. 모든 cell 결정되면, <S> 이후 ~ <EOS> 이전의 토큰들만 출력.
    """

    def __init__(self, codebook: LoadedCodebook,
                 temperature: float = 0.5,
                 seed: int = 0,
                 max_cells: int = 8,
                 adj_smoothing: float = 0.02):
        self.cb = codebook
        self.T = float(temperature)
        self.rng = np.random.default_rng(seed)
        self.max_cells = max_cells
        # adjacency 미관측 쌍에 주는 기본 가중치 (hard-zero 대신)
        self.adj_smooth = adj_smoothing

        # EOS / S 토큰 캐시
        self.eos = codebook.text_to_token.get("<EOS>")
        self.s_tok = codebook.text_to_token.get("<S>")

    # ----------------------------------------------
    # 후보 pool 초기화
    # ----------------------------------------------
    def _pool_for_class(self, cls: str,
                        intent: Optional[str] = None) -> List[LoadedToken]:
        """
        클래스에 매칭되는 모든 후보.
        intent 가 주어지면 그 intent에 등장한 토큰 또는 intent 무관 토큰만 유지.
        body_X 형태 클래스는 정확히 매칭.
        end 등 범용 클래스는 intent 필터 + 범용 fallback.
        """
        if cls == "any":
            return list(self.cb.tokens)
        base = list(self.cb.by_class.get(cls, []))
        if intent is None:
            return base
        # intent 매칭: intents 가 비어있거나 intent 를 포함하면 통과
        filtered = [t for t in base if (not t.intents) or (intent in t.intents)]
        # fallback: 필터 결과 비어있으면 전체 반환
        return filtered if filtered else base

    # ----------------------------------------------
    # Adjacency lookup
    # ----------------------------------------------
    def _adj(self, left: str, right: str) -> float:
        """(left, right) 쌍의 가중치. 관측횟수 + smoothing."""
        obs = self.cb.adjacency.get(left, {}).get(right, 0)
        return float(obs) + self.adj_smooth

    # ----------------------------------------------
    # State-weighted 가중치 계산
    # ----------------------------------------------
    def _weights(self, tokens: List[LoadedToken],
                 state_vec: np.ndarray,
                 left_ctx: Optional[str],
                 right_ctx: Optional[str]) -> np.ndarray:
        """
        각 token 의 최종 가중치:
          w_i = base_w * exp(feat_i · state / T)
                 * adj(left_ctx, tok_i) * adj(tok_i, right_ctx)
        """
        if not tokens:
            return np.array([])
        feats = np.stack([t.feature_vec for t in tokens])  # (K, D)
        bases = np.array([t.base_w for t in tokens], dtype=np.float32)

        # state 정합도 (내적 / T)
        scores = feats @ state_vec / max(self.T, 1e-6)
        # numerical stability
        scores = scores - scores.max()
        probs = np.exp(scores) * bases

        # adjacency
        if left_ctx is not None:
            adj_l = np.array([self._adj(left_ctx, t.text) for t in tokens])
            probs = probs * adj_l
        if right_ctx is not None:
            adj_r = np.array([self._adj(t.text, right_ctx) for t in tokens])
            probs = probs * adj_r

        probs = np.clip(probs, 1e-12, None)
        probs = probs / probs.sum()
        return probs

    # ----------------------------------------------
    # Entropy
    # ----------------------------------------------
    @staticmethod
    def _entropy(probs: np.ndarray) -> float:
        p = probs[probs > 1e-12]
        if len(p) == 0:
            return 0.0
        return float(-np.sum(p * np.log(p)))

    # ----------------------------------------------
    # Propagation: 왼/오 이웃의 candidate 를 줄이기
    # ----------------------------------------------
    def _propagate(self, cells: List[Cell], idx: int):
        """cell[idx] 이 collapse 된 후 양옆 이웃 superposition 제한."""
        if cells[idx].collapsed is None:
            return
        chosen = cells[idx].collapsed

        # 왼쪽 이웃: ?→chosen 이 관측된 left 만 남기기
        if idx - 1 >= 0 and cells[idx - 1].collapsed is None:
            left_cell = cells[idx - 1]
            # smoothing 때문에 hard-filter 안 하고 soft weight 로 충분
            # 다만 (left, chosen.text) pair 가 관측이 0이고 smoothing 도 낮으면
            # 사실상 가중치 0 이 되는 효과
            pass  # soft 방식이라 아무것도 안 해도 됨

        # 오른쪽은 대칭
        # (여기서 hard pruning 을 넣고 싶으면 adj 관측=0 을 걸러내면 됨.
        #  일단 soft 만 사용.)

    # ----------------------------------------------
    # <S> collapse 시 왼쪽 연쇄 처리
    # ----------------------------------------------
    def _apply_S_cascade(self, cells: List[Cell], idx: int):
        """cell[idx] 이 <S> 로 collapse 되면, idx 왼쪽의 모든 cell 을 <S> 고정."""
        if self.s_tok is None:
            return
        if cells[idx].collapsed is not self.s_tok:
            return
        for j in range(idx):
            if cells[j].collapsed is None:
                cells[j].collapsed = self.s_tok
                cells[j].allowed = [self.s_tok]

    def _apply_EOS_cascade(self, cells: List[Cell], idx: int):
        """cell[idx] 이 <EOS> 로 collapse 되면, idx 오른쪽의 모든 cell 을 <EOS> 고정."""
        if self.eos is None:
            return
        if cells[idx].collapsed is not self.eos:
            return
        for j in range(idx + 1, len(cells)):
            if cells[j].collapsed is None:
                cells[j].collapsed = self.eos
                cells[j].allowed = [self.eos]

    # ----------------------------------------------
    # Pick the next cell to collapse (hard reverse)
    # ----------------------------------------------
    def _choose_next(self, cells: List[Cell],
                     state_vec: np.ndarray) -> Optional[int]:
        """
        오른쪽부터 미결정 cell 을 스캔. entropy 가 최소인 것 중
        가장 오른쪽 선택. (hard reverse 원칙)
        """
        best_idx = -1
        best_ent = float("inf")
        for i in range(len(cells) - 1, -1, -1):
            c = cells[i]
            if c.collapsed is not None:
                continue
            if not c.allowed:
                return i  # contradiction cell, 즉시 처리 필요
            left = cells[i - 1].collapsed.text if i > 0 and cells[i - 1].collapsed else None
            right = cells[i + 1].collapsed.text if i < len(cells) - 1 and cells[i + 1].collapsed else None
            probs = self._weights(c.allowed, state_vec, left, right)
            e = self._entropy(probs)
            if e < best_ent - 1e-9:
                best_ent = e
                best_idx = i
        return best_idx if best_idx >= 0 else None

    # ----------------------------------------------
    # Main generate
    # ----------------------------------------------
    def generate(self, npc: NPCStateV2, intent: str,
                 target_length: Optional[str] = None) -> str:
        """한 문장 생성."""
        sv = npc.effective_vector()

        # 1. schema 선택
        classes = choose_schema(self.cb, intent, self.rng, target_length)

        # 2. cells 구성: [<S>로 collapse 가능한 extensible area] + schema slots + [<EOS>]
        #    왼쪽에 padding 으로 "any" cell 을 max_cells 까지 확장해
        #    가변 시작 지점 구현. <S> 가 어디서 collapse 되느냐가 실제 시작점.
        #
        #    단순화: schema class 앞에 n 개의 "optional" cell (S 또는 해당 intent body)
        #    을 두지 않고, 그냥 schema 를 따라가되 각 cell 에 <S> 와 <EOS> 를 후보로
        #    추가. 실제 문장 길이는 이들의 collapse 결과로 결정.

        cells: List[Cell] = []
        for cls in classes:
            pool = self._pool_for_class(cls, intent=intent)
            # 각 cell 후보에 <S>, <EOS> 추가 (양쪽 끝 제외한 모든 자리에)
            extended = list(pool)
            # optional 마커 (클래스명에 ? 포함 시) 지원은 여기선 생략
            cells.append(Cell(allowed=extended))

        if not cells:
            return ""

        # 첫 cell 에는 <S> 후보를 강하게 넣음 (실제 시작점 선택용)
        # 마지막 cell 에는 <EOS> 후보를 강하게.
        if self.s_tok:
            # 첫 두 cell 에 <S> 옵션
            for i in range(min(2, len(cells))):
                if self.s_tok not in cells[i].allowed:
                    cells[i].allowed.append(self.s_tok)

        if self.eos:
            for i in range(max(0, len(cells) - 2), len(cells)):
                if self.eos not in cells[i].allowed:
                    cells[i].allowed.append(self.eos)
            # 정말 강제로 마지막 cell 은 <EOS> 로만 두자 (sentinel 역할)
            cells[-1].allowed = [self.eos]
            cells[-1].collapsed = self.eos

        # 3. WFC loop
        max_steps = self.max_cells * 3
        for _ in range(max_steps):
            idx = self._choose_next(cells, sv)
            if idx is None:
                break
            cell = cells[idx]
            if not cell.allowed:
                # contradiction: EOS 로 강제
                if self.eos:
                    cell.collapsed = self.eos
                    cell.allowed = [self.eos]
                continue

            left = cells[idx - 1].collapsed.text if idx > 0 and cells[idx - 1].collapsed else None
            right = cells[idx + 1].collapsed.text if idx < len(cells) - 1 and cells[idx + 1].collapsed else None
            probs = self._weights(cell.allowed, sv, left, right)
            pick_i = int(self.rng.choice(len(cell.allowed), p=probs))
            cell.collapsed = cell.allowed[pick_i]

            self._apply_S_cascade(cells, idx)
            self._apply_EOS_cascade(cells, idx)

        # 4. 조립
        return self._assemble(cells)

    # ----------------------------------------------
    # 조립: <S> 이후 ~ <EOS> 이전 토큰을 순서대로 연결
    # ----------------------------------------------
    def _assemble(self, cells: List[Cell]) -> str:
        active = []
        for c in cells:
            if c.collapsed is None:
                continue
            t = c.collapsed
            if t.tclass == "S":
                # 이전 누적 버리고 다시 시작
                active = []
                continue
            if t.tclass == "EOS":
                break
            active.append(t)

        # 토큰들을 이어붙임. 한국어 결합 규칙 간이 처리.
        out = []
        for i, t in enumerate(active):
            txt = t.text
            if not out:
                out.append(txt)
                continue
            prev = active[i - 1]
            # 구두점이면 공백 없이 이어붙임
            if t.tclass == "punct":
                out[-1] = out[-1] + txt
            # 어미가 body 바로 뒤에 오면 공백 없이 (fuse)
            elif t.tclass == "end" and prev.tclass.startswith("body_"):
                out[-1] = _fuse(out[-1], txt, prev.morph)
            # 호칭 뒤에는 공백
            else:
                out.append(txt)
        return " ".join(out).strip()


# ------------------------------------------------------------------
# 한국어 어미 결합 보조
# ------------------------------------------------------------------

def _fuse(stem: str, ending: str, stem_morph: str = "none") -> str:
    """
    body + end fusion.
    실용 수준 규칙만 (완벽 활용은 X).
    """
    if not stem or not ending:
        return stem + ending
    # 어미가 구두점이면 바로 붙임
    if ending[0] in ",.!?~…":
        return stem + ending

    # 특정 패턴
    if ending in ("세요", "십시오") and stem_morph in ("C_n", "C_reg", "C_l"):
        return stem + "으" + ending

    # 기본
    return stem + ending


# ------------------------------------------------------------------
# 스모크 테스트
# ------------------------------------------------------------------

if __name__ == "__main__":
    root = Path("/home/claude/dialogue_study/phase2")

    # 세 캐릭터 테스트
    for name in ["시호", "유카", "린"]:
        cb = LoadedCodebook.load(str(root / "codebooks" / f"{name}.json"))

        # 캐릭터 로드
        yaml_path = {
            "시호": "01_shiho.yaml", "유카": "02_yuka.yaml", "린": "05_rin.yaml",
        }[name]
        from state_v2 import load_character
        npc, _ = load_character(str(root / "examples" / yaml_path))

        engine = WFCv2(cb, temperature=0.4, seed=42)

        print(f"\n=== {name} ({npc.archetype}) ===")

        # 다양한 상태
        tests = [
            ("기본", {}, "greet"),
            ("기본", {}, "complain"),
            ("기본", {}, "thank"),
        ]
        if name == "시호":
            tests += [
                ("츤 모드", {"affinity": 0.7, "embarrassment": 0.8}, "thank"),
                ("솔직", {"affinity": 0.8, "embarrassment": 0.1}, "farewell"),
            ]
        if name == "유카":
            tests += [
                ("피로", {"fatigue": 0.8}, "complain"),
                ("높은 호감", {"affinity": 0.9, "trust": 0.8}, "greet"),
            ]
        if name == "린":
            tests += [
                ("흥분", {"arousal": 0.8, "affinity": 0.8}, "thank"),
                ("피로", {"fatigue": 0.7}, "complain"),
            ]

        for label, override, intent in tests:
            state = npc.with_state(**override) if override else npc
            outs = set()
            for s in range(6):
                engine.rng = np.random.default_rng(42 + s)
                outs.add(engine.generate(state, intent))
            print(f"  [{intent} / {label}] {outs}")
