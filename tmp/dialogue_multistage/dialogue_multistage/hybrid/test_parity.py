"""S02 원본 vs Hybrid 텍스트 풀 parity 검증.

검증 목표:
  1. 변환 과정에서 텍스트 누락 없음 — S02 풀 전체가 Hybrid yaml에 포함
  2. 샘플링으로 같은 좌표에서 같은 텍스트가 선택됨 (kNN 정도 유사)
  3. Hybrid가 S02에 없는 텍스트 생성하지 않음

접근:
  - S02 pool_dict 의 모든 텍스트 수집 → S02_ALL (집합)
  - Hybrid intent 의 모든 template pattern 수집 → HYBRID_ALL (집합)
  - 샘플링 없이 집합 비교로 텍스트 손실 0 확인
  - 이후 좌표별 샘플링으로 kNN 유사도 스팟 체크
"""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Hybrid engine 먼저 import (S02 engine과 이름 충돌 방지)
import engine as _hybrid_engine
HybridEngine = _hybrid_engine.HybridEngine

# 이제 S02 engine 경로 추가 — sys.modules['engine']은 이미 hybrid 로 고정되어 있음
S02_PATH = Path("C:/Users/akamo/Desktop/work/morld/scenarios/common/python")
sys.path.insert(0, str(S02_PATH))

# sys.modules 의 'engine' 은 hybrid — S02 engine 은 dotted path 로 우회 import
import importlib
sys.modules.pop("engine", None)  # 임시 제거
s02_cheerful = importlib.import_module("engine.tone_templates.cheerful")
s02_cold = importlib.import_module("engine.tone_templates.cold")


def extract_s02_texts(section_dict):
    """S02 dict 에서 모든 텍스트 (sub-category 포함) 수집."""
    texts = set()
    for cat_key, pool_dict in section_dict.items():
        if not isinstance(pool_dict, dict):
            continue
        for coord, texts_list in pool_dict.items():
            if isinstance(texts_list, list):
                for t in texts_list:
                    if isinstance(t, str):
                        texts.add(t)
    return texts


def extract_hybrid_texts(eng):
    """Hybrid 엔진에서 모든 template pattern 수집."""
    texts = set()
    for intent, data in eng.intents.items():
        for tpl in data.get("templates", []) or []:
            pat = tpl.get("pattern", "")
            if pat:
                texts.add(pat)
    return texts


def compare_sets(label, s02, hyb):
    inter = s02 & hyb
    s02_only = s02 - hyb
    hyb_only = hyb - s02
    print(f"\n== {label} ==")
    print(f"  S02      texts: {len(s02):4d}")
    print(f"  Hybrid   texts: {len(hyb):4d}")
    print(f"  교집합   : {len(inter):4d}")
    print(f"  S02 only : {len(s02_only):4d} (누락)")
    print(f"  Hyb only : {len(hyb_only):4d} (Hybrid 측 신규)")
    coverage = len(inter) / len(s02) * 100 if s02 else 0
    print(f"  Coverage (S02→Hybrid): {coverage:5.1f}%")
    if s02_only:
        print(f"  S02 only 예시:")
        for t in list(s02_only)[:3]:
            print(f"    {t!r}")
    if hyb_only:
        print(f"  Hyb only 예시:")
        for t in list(hyb_only)[:3]:
            print(f"    {t!r}")
    return coverage, len(s02_only), len(hyb_only)


# =================================================================
# 텍스트 손실 0 검증
# =================================================================
print("=" * 72)
print("PARITY — 변환 후 텍스트 손실 확인")
print("=" * 72)

# cheerful LINES
s02_cheerful_lines = extract_s02_texts(s02_cheerful.LINES)
eng_rin_romance = HybridEngine.load(
    character="린", context="romance", dialogue_root=HERE / "dialogues")
hyb_cheerful_lines = extract_hybrid_texts(eng_rin_romance)
compare_sets("cheerful LINES", s02_cheerful_lines, hyb_cheerful_lines)

# cold LINES
s02_cold_lines = extract_s02_texts(s02_cold.LINES)
eng_yuka_romance = HybridEngine.load(
    character="유카", context="romance", dialogue_root=HERE / "dialogues")
hyb_cold_lines = extract_hybrid_texts(eng_yuka_romance)
compare_sets("cold LINES", s02_cold_lines, hyb_cold_lines)

# cheerful REACTIONS
s02_cheerful_reactions = extract_s02_texts(s02_cheerful.REACTIONS)
eng_rin_react = HybridEngine.load(
    character="린", context="romance_reactions",
    dialogue_root=HERE / "dialogues")
hyb_cheerful_reactions = extract_hybrid_texts(eng_rin_react)
compare_sets("cheerful REACTIONS", s02_cheerful_reactions, hyb_cheerful_reactions)

# cold REACTIONS
s02_cold_reactions = extract_s02_texts(s02_cold.REACTIONS)
eng_yuka_react = HybridEngine.load(
    character="유카", context="romance_reactions",
    dialogue_root=HERE / "dialogues")
hyb_cold_reactions = extract_hybrid_texts(eng_yuka_react)
compare_sets("cold REACTIONS", s02_cold_reactions, hyb_cold_reactions)

# cheerful ACTION_LINES
s02_cheerful_al = extract_s02_texts(s02_cheerful.ACTION_LINES)
eng_rin_al = HybridEngine.load(
    character="린", context="action_lines", dialogue_root=HERE / "dialogues")
hyb_cheerful_al = extract_hybrid_texts(eng_rin_al)
compare_sets("cheerful ACTION_LINES", s02_cheerful_al, hyb_cheerful_al)

# cold ACTION_LINES
s02_cold_al = extract_s02_texts(s02_cold.ACTION_LINES)
eng_yuka_al = HybridEngine.load(
    character="유카", context="action_lines", dialogue_root=HERE / "dialogues")
hyb_cold_al = extract_hybrid_texts(eng_yuka_al)
compare_sets("cold ACTION_LINES", s02_cold_al, hyb_cold_al)

# cheerful ACTION_REACTIONS
s02_cheerful_ar = extract_s02_texts(s02_cheerful.ACTION_REACTIONS)
eng_rin_ar = HybridEngine.load(
    character="린", context="action_reactions",
    dialogue_root=HERE / "dialogues")
hyb_cheerful_ar = extract_hybrid_texts(eng_rin_ar)
compare_sets("cheerful ACTION_REACTIONS", s02_cheerful_ar, hyb_cheerful_ar)

# cold ACTION_REACTIONS
s02_cold_ar = extract_s02_texts(s02_cold.ACTION_REACTIONS)
eng_yuka_ar = HybridEngine.load(
    character="유카", context="action_reactions",
    dialogue_root=HERE / "dialogues")
hyb_cold_ar = extract_hybrid_texts(eng_yuka_ar)
compare_sets("cold ACTION_REACTIONS", s02_cold_ar, hyb_cold_ar)

print()
print("=" * 72)
print("FINAL")
print("=" * 72)
total_s02 = len(s02_cheerful_lines) + len(s02_cold_lines) + \
            len(s02_cheerful_reactions) + len(s02_cold_reactions) + \
            len(s02_cheerful_al) + len(s02_cold_al) + \
            len(s02_cheerful_ar) + len(s02_cold_ar)
total_hyb = len(hyb_cheerful_lines) + len(hyb_cold_lines) + \
            len(hyb_cheerful_reactions) + len(hyb_cold_reactions) + \
            len(hyb_cheerful_al) + len(hyb_cold_al) + \
            len(hyb_cheerful_ar) + len(hyb_cold_ar)
print(f"  총 S02 unique texts:    {total_s02}")
print(f"  총 Hybrid unique texts: {total_hyb}")
