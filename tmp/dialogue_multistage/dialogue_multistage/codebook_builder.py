"""
Phase 2 - Codebook Builder
============================
yaml 예시 대사 → WFC codebook 자동 생성.

파이프라인:
  1. 전체 대사 수집 → 문자 수준 / 어절 수준 n-gram 빈도 분석
  2. BPE-like subword 추출 (빈발 bigram 을 merge)
  3. 각 token 을 class 로 자동 분류 (규칙 기반)
  4. Adjacency graph (관측된 좌→우 쌍) 추출
  5. Feature 추론 (token 이 등장한 문장들의 상태값 평균)
  6. codebook JSON 출력

WFC 원리와 일치: 작가는 예시만 쓰고, 시스템이 패턴을 학습.
"""

from __future__ import annotations
import re
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

from game_config import AXIS_NAMES, AXIS_INDEX, N_DIM, to_vector
from state_v2 import load_character, NPCStateV2


# ------------------------------------------------------------------
# Token 정의
# ------------------------------------------------------------------

@dataclass
class CBToken:
    """Codebook 토큰. Phase 1 의 Token 을 확장."""
    text: str
    tclass: str                 # "interj" / "body" / "end" / "addr" / "EOS" / "S"
    morph: str = "none"         # 한국어 활용용 태그 (어간 끝 형태)
    feature: Dict[str, float] = field(default_factory=dict)  # sparse
    base_w: float = 1.0
    intents: List[str] = field(default_factory=list)   # 어느 intent에서 등장했는가

    def feature_vec(self) -> np.ndarray:
        return to_vector(self.feature)


# ------------------------------------------------------------------
# 1. 토큰화 (BPE-like)
# ------------------------------------------------------------------

# 구두점/감탄사 분리를 위한 규칙. 이들은 자체 토큰.
PUNCT_CHARS = set(",.!?~…")
ENDING_MARKERS = [   # 문장 끝어미로 자주 나오는 패턴 (우선순위 순)
    "습니다", "세요", "십시오", "어요", "아요", "네요", "죠", "다.",
    "어요.", "아요.", "네요.", "죠.", "세요.", "습니다.", "요.", "요!", "요?",
    "어!", "야!", "냐?", "냐.", "라.", "라!", "니?", "까?",
]


def split_punctuation(text: str) -> List[str]:
    """구두점을 독립 토큰으로 분리."""
    out = []
    buf = ""
    for ch in text:
        if ch in PUNCT_CHARS:
            if buf:
                out.append(buf); buf = ""
            # 연속 구두점은 묶어서 하나로
            if out and out[-1] and all(c in PUNCT_CHARS for c in out[-1]):
                out[-1] += ch
            else:
                out.append(ch)
        elif ch == " ":
            if buf:
                out.append(buf); buf = ""
        else:
            buf += ch
    if buf:
        out.append(buf)
    return out


def extract_endings(tokens: List[str]) -> List[str]:
    """마지막 토큰에서 어미 패턴을 분리해 별도 토큰으로."""
    if not tokens:
        return tokens
    last = tokens[-1]
    for end in ENDING_MARKERS:
        if last.endswith(end) and len(last) > len(end):
            stem = last[:-len(end)]
            return tokens[:-1] + [stem, end]
    return tokens


def tokenize_raw(text: str) -> List[str]:
    """초기 토큰화 - 구두점/감탄사/어미 분리."""
    tokens = split_punctuation(text)
    tokens = extract_endings(tokens)
    return [t for t in tokens if t]


def build_bpe_merges(corpus: List[List[str]],
                     min_freq: int = 2,
                     n_merges: int = 50) -> List[Tuple[str, str]]:
    """
    간이 BPE. 인접 토큰 쌍 중 빈발한 것을 merge 후보로.
    Returns 병합 순서 리스트.
    """
    tokens_lists = [list(t) for t in corpus]
    merges = []
    for _ in range(n_merges):
        pair_counts = Counter()
        for seq in tokens_lists:
            for i in range(len(seq) - 1):
                pair_counts[(seq[i], seq[i + 1])] += 1
        if not pair_counts:
            break
        (a, b), c = pair_counts.most_common(1)[0]
        if c < min_freq:
            break
        merges.append((a, b))
        # sequences 에서 해당 쌍을 병합
        new_lists = []
        for seq in tokens_lists:
            out, i = [], 0
            while i < len(seq):
                if i < len(seq) - 1 and seq[i] == a and seq[i + 1] == b:
                    out.append(a + b)
                    i += 2
                else:
                    out.append(seq[i])
                    i += 1
            new_lists.append(out)
        tokens_lists = new_lists
    return merges


def apply_merges(tokens: List[str], merges: List[Tuple[str, str]]) -> List[str]:
    for a, b in merges:
        merged_token = a + b
        out, i = [], 0
        while i < len(tokens):
            if i < len(tokens) - 1 and tokens[i] == a and tokens[i + 1] == b:
                out.append(merged_token)
                i += 2
            else:
                out.append(tokens[i])
                i += 1
        tokens = out
    return tokens


# ------------------------------------------------------------------
# 2. Class 태깅 (규칙 기반)
# ------------------------------------------------------------------

# 정규식 기반 class 결정. 복잡도를 낮추기 위해 단순 규칙만.
def _is_ending(tok: str) -> bool:
    """문장 끝 어미인가."""
    if any(tok.endswith(e) for e in
           ["다", "다.", "요", "요.", "요!", "요?",
            "니?", "니.", "까?", "오", "오.", "오!", "오?",
            "라", "라.", "라!", "소서", "오소서",
            "냐?", "냐.", "어", "어.", "어!", "어?",
            "야", "야.", "야!", "자", "자.",
            "!", "?", "~", "...", "…"]):
        return True
    return False

def _is_interjection(tok: str) -> bool:
    """감탄사. 끝에 comma가 붙어있거나 단독 짧은 감탄."""
    if tok.endswith(","):
        return True
    single_interj = {"아", "어", "와", "앗", "엣", "헉", "흥", "야", "음",
                     "에", "어머", "아이고", "으", "에헤헤", "헤헤"}
    if tok in single_interj:
        return True
    return False

def _is_address(tok: str) -> bool:
    """호칭. 간단 휴리스틱."""
    addrs = {"너", "당신", "그대", "님", "손님", "아저씨", "언니", "오빠",
             "형님", "짐", "경", "경은", "이놈", "자네"}
    if tok in addrs:
        return True
    if tok.endswith("은") or tok.endswith("는") or tok.endswith("이"):
        if len(tok) <= 3 and tok[:-1] in addrs:
            return True
    return False

def _is_punct_only(tok: str) -> bool:
    return all(c in PUNCT_CHARS for c in tok)


def classify_token(tok: str, position: str = "mid") -> str:
    """
    position: "first" / "mid" / "last" (문장 내 자리)
    반환: "interj" / "addr" / "body" / "end" / "punct"
    """
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


# ------------------------------------------------------------------
# 3. Morphology 태깅 (한국어 어간 말음 분석)
# ------------------------------------------------------------------

def _has_jongsung(ch: str) -> bool:
    if not ch:
        return False
    code = ord(ch)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def morph_tag(text: str) -> str:
    """
    토큰의 어간 말음 태그:
      V       - 모음으로 끝남
      C_n     - ㄴ 받침
      C_l     - ㄹ 받침
      C_reg   - 기타 자음 받침
      none    - 판정 불가
    """
    if not text:
        return "none"
    # 구두점 제거 후 마지막 한글 음절 체크
    for ch in reversed(text):
        if '가' <= ch <= '힣':
            code = ord(ch) - 0xAC00
            jong = code % 28
            if jong == 0:
                return "V"
            elif jong == 4:
                return "C_n"
            elif jong == 8:
                return "C_l"
            else:
                return "C_reg"
    return "none"


# ------------------------------------------------------------------
# 4. Codebook 빌더 메인
# ------------------------------------------------------------------

@dataclass
class Codebook:
    archetype: str
    tokens: List[CBToken] = field(default_factory=list)

    # adjacency[left_text][right_text] = count
    adjacency: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))

    # schemas: intent → list of class sequences 관찰됨
    schemas: Dict[str, List[List[str]]] = field(default_factory=lambda: defaultdict(list))

    # 각 토큰이 등장한 sentence state 들 (feature 추론용 보관)
    _token_states: Dict[str, List[np.ndarray]] = field(default_factory=lambda: defaultdict(list))
    _token_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


def build_codebook(npc: NPCStateV2, samples: List[Dict[str, Any]],
                   min_freq: int = 2, n_merges: int = 150) -> Codebook:
    """
    NPC 한 명의 예시 대사에서 codebook 을 구축.
    """
    cb = Codebook(archetype=npc.archetype)

    # 1. 각 샘플 raw tokenize
    raw_per_sample = []
    for s in samples:
        toks = tokenize_raw(s["text"])
        raw_per_sample.append(toks)

    # 2. BPE merges 학습
    merges = build_bpe_merges(raw_per_sample, min_freq=min_freq, n_merges=n_merges)

    # 3. 각 샘플에 merges 적용, class 태깅, adjacency/feature 추출
    token_texts = set()
    token_meta: Dict[str, Dict[str, Any]] = {}  # text → {tclass, morph, intents}

    for s, raw in zip(samples, raw_per_sample):
        merged = apply_merges(raw, merges)
        if not merged:
            continue

        # sample 의 상태를 벡터화. 단, trait + dynamic 은 npc 기본값 위에 override
        state_obj = npc.with_state(**s.get("state", {}))
        sv = state_obj.effective_vector()
        intent = s["intent"]

        # position별 class 태깅
        classes = []
        for i, tok in enumerate(merged):
            if i == 0 and len(merged) > 1:
                pos = "first"
            elif i == len(merged) - 1:
                pos = "last"
            else:
                pos = "mid"
            cls = classify_token(tok, pos)
            # body 토큰에 intent 태그 부여 (WFC schema 에서 body_greet 등으로 쓸 수 있게)
            if cls == "body":
                cls = f"body_{intent}"
            classes.append(cls)

            # 메타데이터 누적
            if tok not in token_meta:
                token_meta[tok] = {
                    "tclass": cls,
                    "morph": morph_tag(tok),
                    "intents": set([intent]),
                }
            else:
                # class 가 다른 intent에서 다르게 분류될 수 있음.
                # body_X 는 intent 마다 다를 수 있으니, 같은 class 만 유지
                if token_meta[tok]["tclass"] != cls:
                    # body_* 는 intent 따라 다중 tag 가능
                    if cls.startswith("body_") and token_meta[tok]["tclass"].startswith("body_"):
                        # 여러 intent 에 걸친 body 는 첫 번째만 유지 (일단)
                        pass
                token_meta[tok]["intents"].add(intent)
            token_texts.add(tok)

            cb._token_states[tok].append(sv.copy())
            cb._token_count[tok] += 1

        # adjacency 누적 (좌→우 방향). <S> 와 <EOS> 경계도 포함.
        ordered = ["<S>"] + merged + ["<EOS>"]
        for i in range(len(ordered) - 1):
            cb.adjacency[ordered[i]][ordered[i + 1]] += 1

        # schema 관찰 (intent 별 class 시퀀스)
        cb.schemas[intent].append(classes)

    # 4. Token 객체 생성 + feature 추론
    for tok, meta in token_meta.items():
        states = cb._token_states[tok]
        count = cb._token_count[tok]
        if count == 0:
            continue
        # 평균 상태 벡터
        mean_state = np.mean(np.stack(states), axis=0)

        # threshold 넘는 축만 feature 로. 노이즈 제거.
        feature = {}
        for i, name in enumerate(AXIS_NAMES):
            v = float(mean_state[i])
            if abs(v) >= 0.15:  # 노이즈 제거 threshold
                feature[name] = round(v, 3)

        cb.tokens.append(CBToken(
            text=tok,
            tclass=meta["tclass"],
            morph=meta["morph"],
            feature=feature,
            base_w=1.0 + np.log1p(count),  # 자주 쓴 토큰에 소폭 가중
            intents=sorted(meta["intents"]),
        ))

    # <S>, <EOS> 는 예외 토큰으로 추가
    cb.tokens.append(CBToken(
        text="<S>", tclass="S", morph="none",
        feature={"verbosity": -0.3},   # <S> 가 빨리 나오면 문장이 짧다는 의미
        base_w=1.0, intents=[],
    ))
    cb.tokens.append(CBToken(
        text="<EOS>", tclass="EOS", morph="none",
        feature={"verbosity": -0.3},   # 일찍 끝나고픈 상태일수록 EOS 가중
        base_w=1.0, intents=[],
    ))

    return cb


# ------------------------------------------------------------------
# Codebook 저장/로드
# ------------------------------------------------------------------

def codebook_to_dict(cb: Codebook) -> Dict[str, Any]:
    return {
        "archetype": cb.archetype,
        "tokens": [asdict(t) for t in cb.tokens],
        "adjacency": {l: dict(rs) for l, rs in cb.adjacency.items()},
        "schemas": dict(cb.schemas),
    }


def save_codebook(cb: Codebook, path: str):
    d = codebook_to_dict(cb)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# 스모크 테스트
# ------------------------------------------------------------------

if __name__ == "__main__":
    root = Path("/home/claude/dialogue_study/phase2")
    out_dir = root / "codebooks"
    out_dir.mkdir(exist_ok=True)

    for yaml_path in sorted((root / "examples").glob("*.yaml")):
        npc, samples = load_character(str(yaml_path))
        cb = build_codebook(npc, samples)

        print(f"\n=== {npc.name} ({npc.archetype}) ===")
        print(f"  samples:  {len(samples)}")
        print(f"  tokens:   {len(cb.tokens)}")
        by_class = Counter(t.tclass for t in cb.tokens)
        print(f"  classes:  {dict(by_class)}")
        print(f"  intents schemas: {[(k, len(v)) for k, v in cb.schemas.items()]}")

        # 상위 빈도 토큰 몇 개 출력
        print(f"  top tokens (w/ features):")
        for tok in sorted(cb.tokens, key=lambda x: -x.base_w)[:8]:
            feats = {k: v for k, v in tok.feature.items()}
            print(f"    '{tok.text}' [{tok.tclass}] morph={tok.morph} w={tok.base_w:.2f} feat={feats}")

        save_codebook(cb, str(out_dir / f"{npc.name}.json"))
        print(f"  → saved {out_dir / npc.name}.json")
