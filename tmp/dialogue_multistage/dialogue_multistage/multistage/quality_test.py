"""
Multi-stage Dialogue System — Quality Assessment
==================================================
현재 상태 품질 테스트. 다음을 측정:

1. Stage-wise ablation
   - Stage 1 only: class sequence 출력 (구조만)
   - Stage 1+2: body 까지만 (기능어 placeholder)
   - Stage 1+2+3: 전체 (fuse 전)
   - Full (Stage 1+2+3+4): 최종 출력

2. Inner/Outer 분리 효과
   - Normal: inner/outer 따로 사용
   - Ablated: inner = outer 강제 (표리일체처럼)
   - 각 출력의 distinct-2, 평균 길이, interj 비율 비교

3. State sensitivity
   - 같은 NPC, 여러 상태 override 에서 출력 변화량
   - edit distance로 측정

4. Divergence 효과
   - divergence 값 vs 문장 길이/구조 다양성 상관

5. Diversity
   - distinct-2, self-BLEU, unique ratio

6. Latency
   - stage 별 실행 시간 (μs)
"""

import sys
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter, defaultdict

sys.path.insert(0, "/home/claude/dialogue_study/phase2")
sys.path.insert(0, "/home/claude/dialogue_study/phase2/multistage")

from state_ms import load_character_ms
from structural_ngram import build_structural_grammar, StructuralSampler
from content_wfc import ContentWFC, Slot
from function_wfc import FunctionWFC, assemble
from wfc_v2 import LoadedCodebook
from game_config import AXIS_NAMES, INTENTS


# ------------------------------------------------------------------
# 메트릭
# ------------------------------------------------------------------

def distinct_n(texts: List[str], n: int = 2) -> float:
    grams = []
    for t in texts:
        toks = t.split()
        grams.extend([tuple(toks[i:i+n]) for i in range(len(toks)-n+1)])
    if not grams:
        return 0.0
    return len(set(grams)) / len(grams)


def self_bleu_lite(texts: List[str], n: int = 3, sample: int = 30) -> float:
    if len(texts) < 2:
        return 0.0
    idx = np.random.default_rng(0).choice(len(texts),
                                          size=min(sample, len(texts)),
                                          replace=False)
    sub = [texts[i] for i in idx]
    overlaps = []
    for i, hyp in enumerate(sub):
        hyp_grams = set(tuple(hyp.split()[j:j+n])
                        for j in range(len(hyp.split())-n+1))
        if not hyp_grams:
            continue
        best = 0.0
        for j, ref in enumerate(sub):
            if i == j:
                continue
            ref_grams = set(tuple(ref.split()[k:k+n])
                            for k in range(len(ref.split())-n+1))
            if not ref_grams:
                continue
            inter = len(hyp_grams & ref_grams)
            if len(hyp_grams) > 0:
                best = max(best, inter / len(hyp_grams))
        overlaps.append(best)
    return float(np.mean(overlaps)) if overlaps else 0.0


def edit_distance(s1: str, s2: str) -> int:
    """문자 단위 Levenshtein."""
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            ins = prev[j + 1] + 1
            dele = curr[j] + 1
            sub = prev[j] + (c1 != c2)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


# ------------------------------------------------------------------
# 파이프라인 래퍼 (ablation 용)
# ------------------------------------------------------------------

class MultiStagePipeline:
    def __init__(self, npc, samples, cb):
        self.npc = npc
        self.cb = cb
        self.grammar = build_structural_grammar(npc, samples)
        self.stage1 = StructuralSampler(self.grammar, bandwidth=0.3, temperature=0.4)
        self.stage2 = ContentWFC(cb, temperature=0.5)
        self.stage3 = FunctionWFC(cb, temperature=0.6)

    def set_seed(self, seed: int):
        self.stage1.rng = np.random.default_rng(seed)
        self.stage2.rng = np.random.default_rng(seed + 100)
        self.stage3.rng = np.random.default_rng(seed + 200)

    def run_stage1(self, state, intent, max_len=6) -> List[str]:
        """class sequence 만 반환."""
        return self.stage1.sample(intent, state.inner_vector(), max_len=max_len)

    def run_stage2(self, state, intent, max_len=6) -> List[Slot]:
        """body 까지 채운 slots."""
        cseq = self.run_stage1(state, intent, max_len)
        return self.stage2.fill(cseq, intent, state.outer_vector())

    def run_stage3(self, state, intent, max_len=6) -> List[Slot]:
        """기능어까지 채운 slots (fuse 전)."""
        slots = self.run_stage2(state, intent, max_len)
        return self.stage3.fill(slots, intent, state.outer_vector())

    def run_full(self, state, intent, max_len=6) -> str:
        """최종 출력."""
        slots = self.run_stage3(state, intent, max_len)
        return assemble(slots)


# ------------------------------------------------------------------
# 테스트 1: Stage-wise Ablation 시각화
# ------------------------------------------------------------------

def describe_slots(slots: List[Slot]) -> str:
    """slots 를 사람이 읽을 형태로."""
    parts = []
    for s in slots:
        if s.cls in ("<S>", "<EOS>"):
            continue
        if s.token is None:
            parts.append(f"[{s.cls}]")
        else:
            parts.append(f"«{s.token.text}»")
    return " ".join(parts)


def test_stage_ablation(pipe, intent: str, state, n_samples: int = 5):
    """한 NPC의 한 intent 에서 각 stage 출력을 보여줌."""
    print(f"  === intent={intent} ===")
    for trial in range(n_samples):
        pipe.set_seed(42 + trial)
        s1 = pipe.run_stage1(state, intent)
        pipe.set_seed(42 + trial)
        s2 = pipe.run_stage2(state, intent)
        pipe.set_seed(42 + trial)
        s3 = pipe.run_stage3(state, intent)
        pipe.set_seed(42 + trial)
        full = pipe.run_full(state, intent)
        print(f"  [{trial}]")
        print(f"    S1 (class):  {s1[1:-1]}")                  # <S>, <EOS> 제거
        print(f"    S2 (+body):  {describe_slots(s2)}")
        print(f"    S3 (+func):  {describe_slots(s3)}")
        print(f"    S4 (final):  {full!r}")


# ------------------------------------------------------------------
# 테스트 2: Inner/Outer 분리 효과
# ------------------------------------------------------------------

def test_inner_outer_ablation(pipe, intents: List[str], n_trials: int = 12):
    """
    정상 (inner ≠ outer) vs ablated (inner=outer 강제) 비교.

    ablated 에서는 NPC의 inner_profile 을 outer_profile 로 강제.
    """
    # 정상 출력
    normal_outs = []
    for intent in intents:
        for trial in range(n_trials):
            pipe.set_seed(1000 + trial)
            out = pipe.run_full(pipe.npc, intent)
            if out:
                normal_outs.append(out)

    # ablated: inner를 outer로 강제
    ablated_npc = pipe.npc.__class__(
        name=pipe.npc.name, archetype=pipe.npc.archetype,
        era=pipe.npc.era, sex=pipe.npc.sex,
        outer_profile=dict(pipe.npc.outer_profile),
        inner_profile=dict(pipe.npc.outer_profile),  # inner=outer
        dynamic=dict(pipe.npc.dynamic),
        interactions=list(pipe.npc.interactions),
    )
    # 새 pipeline (grammar 다시 학습)
    from codebook_builder import tokenize_raw
    # 재학습은 비용 크고 효과 같으니, sampler 만 새 npc 참조하게 씀
    ablated_pipe = MultiStagePipeline(ablated_npc, [], pipe.cb)
    ablated_pipe.grammar = pipe.grammar  # grammar 재사용 (예시는 같으므로)
    ablated_pipe.stage1 = StructuralSampler(pipe.grammar, bandwidth=0.3, temperature=0.4)

    ablated_outs = []
    for intent in intents:
        for trial in range(n_trials):
            ablated_pipe.set_seed(1000 + trial)
            out = ablated_pipe.run_full(ablated_npc, intent)
            if out:
                ablated_outs.append(out)

    # 메트릭
    def analyze(outs):
        lens = [len(o.split()) for o in outs]
        return {
            "n": len(outs),
            "avg_len": round(np.mean(lens) if lens else 0, 2),
            "std_len": round(np.std(lens) if lens else 0, 2),
            "distinct_2": round(distinct_n(outs, 2), 3),
            "self_bleu": round(self_bleu_lite(outs, 3), 3),
            "unique_ratio": round(len(set(outs)) / len(outs) if outs else 0, 3),
        }

    return analyze(normal_outs), analyze(ablated_outs)


# ------------------------------------------------------------------
# 테스트 3: State Sensitivity
# ------------------------------------------------------------------

def test_state_sensitivity(pipe, intent: str) -> Dict:
    """여러 state 에서 출력을 얻고, 서로 간 평균 edit distance 측정."""
    state_variations = [
        {},
        {"affinity": 0.8, "trust": 0.7},
        {"embarrassment": 0.8, "affinity": 0.6},
        {"fatigue": 0.8, "health": 0.3},
        {"arousal": 0.9, "affinity": 0.8},
        {"hostility": 0.7},
        {"confidence": -0.6},
    ]
    outs = []
    for sv in state_variations:
        state = pipe.npc.with_state(**sv)
        pipe.set_seed(12345)
        outs.append(pipe.run_full(state, intent))

    # 서로 다른 state 쌍 간 평균 edit distance
    pairs = []
    for i in range(len(outs)):
        for j in range(i + 1, len(outs)):
            pairs.append(edit_distance(outs[i], outs[j]))
    return {
        "outputs": outs,
        "mean_edit": round(float(np.mean(pairs)) if pairs else 0, 2),
        "unique_outputs": len(set(outs)),
    }


# ------------------------------------------------------------------
# 테스트 4: Diversity 전반
# ------------------------------------------------------------------

def test_diversity(pipe, intents: List[str], n_trials: int = 15) -> Dict:
    """NPC별 전체 다양성 측정."""
    outs = []
    for intent in intents:
        for trial in range(n_trials):
            pipe.set_seed(77 + trial * 7)
            # 다양한 상태에서
            state = pipe.npc.with_state(
                affinity=float(np.random.default_rng(trial).uniform(0, 1)),
                embarrassment=float(np.random.default_rng(trial+1).uniform(0, 1)),
                fatigue=float(np.random.default_rng(trial+2).uniform(0, 1)),
            )
            out = pipe.run_full(state, intent)
            if out:
                outs.append(out)
    return {
        "n_total": len(outs),
        "n_unique": len(set(outs)),
        "distinct_1": round(distinct_n(outs, 1), 3),
        "distinct_2": round(distinct_n(outs, 2), 3),
        "self_bleu_3": round(self_bleu_lite(outs, 3), 3),
        "avg_len_words": round(np.mean([len(o.split()) for o in outs]) if outs else 0, 2),
    }


# ------------------------------------------------------------------
# 테스트 5: Latency
# ------------------------------------------------------------------

def test_latency(pipe, intent: str, n_runs: int = 100) -> Dict:
    """Stage별 실행 시간 측정."""
    state = pipe.npc

    # warmup
    for _ in range(5):
        pipe.set_seed(0)
        pipe.run_full(state, intent)

    # Stage 1 only
    t0 = time.perf_counter()
    for i in range(n_runs):
        pipe.set_seed(i)
        pipe.run_stage1(state, intent)
    t1 = time.perf_counter()

    # Stage 1+2
    t2 = time.perf_counter()
    for i in range(n_runs):
        pipe.set_seed(i)
        pipe.run_stage2(state, intent)
    t3 = time.perf_counter()

    # Stage 1+2+3
    t4 = time.perf_counter()
    for i in range(n_runs):
        pipe.set_seed(i)
        pipe.run_stage3(state, intent)
    t5 = time.perf_counter()

    # Full
    t6 = time.perf_counter()
    for i in range(n_runs):
        pipe.set_seed(i)
        pipe.run_full(state, intent)
    t7 = time.perf_counter()

    return {
        "stage1_us": round((t1 - t0) / n_runs * 1e6, 1),
        "stage1+2_us": round((t3 - t2) / n_runs * 1e6, 1),
        "stage1+2+3_us": round((t5 - t4) / n_runs * 1e6, 1),
        "full_us": round((t7 - t6) / n_runs * 1e6, 1),
        "s2_delta_us": round(((t3 - t2) - (t1 - t0)) / n_runs * 1e6, 1),
        "s3_delta_us": round(((t5 - t4) - (t3 - t2)) / n_runs * 1e6, 1),
        "s4_delta_us": round(((t7 - t6) - (t5 - t4)) / n_runs * 1e6, 1),
    }


# ------------------------------------------------------------------
# 메인
# ------------------------------------------------------------------

def run_all():
    root = Path("/home/claude/dialogue_study/phase2")
    characters = [
        ("시호", "01_shiho.yaml"),
        ("유카", "02_yuka.yaml"),
        ("린",   "05_rin.yaml"),
    ]

    results = {}

    # 각 캐릭터별 파이프라인
    pipes = {}
    for name, yaml_name in characters:
        npc, samples = load_character_ms(str(root / "examples" / yaml_name))
        cb = LoadedCodebook.load(str(root / "codebooks" / f"{name}.json"))
        pipes[name] = MultiStagePipeline(npc, samples, cb)

    # ================================
    # Test 1: Stage ablation (정성)
    # ================================
    print("=" * 70)
    print("TEST 1 — Stage-wise Ablation (정성적 예시)")
    print("=" * 70)
    for name, pipe in pipes.items():
        print(f"\n──── {name} ({pipe.npc.archetype}, divergence={pipe.npc.divergence():.2f}) ────")
        for intent in ["greet", "thank", "complain"]:
            print(f"\n  intent: {intent}")
            test_stage_ablation(pipe, intent, pipe.npc, n_samples=3)

    # ================================
    # Test 2: Inner/Outer ablation
    # ================================
    print("\n" + "=" * 70)
    print("TEST 2 — Inner/Outer 분리 효과 (ablation)")
    print("=" * 70)
    print(f"{'character':10} {'mode':10} {'n':4} {'avg_len':8} {'std_len':8} {'d2':6} {'self_bleu':10} {'unique':6}")
    print("-" * 70)
    inner_outer_data = {}
    for name, pipe in pipes.items():
        normal, ablated = test_inner_outer_ablation(pipe, INTENTS, n_trials=10)
        inner_outer_data[name] = {"normal": normal, "ablated": ablated}
        print(f"{name:10} {'normal':10} {normal['n']:4} {normal['avg_len']:<8} {normal['std_len']:<8} {normal['distinct_2']:<6} {normal['self_bleu']:<10} {normal['unique_ratio']:<6}")
        print(f"{name:10} {'ablated':10} {ablated['n']:4} {ablated['avg_len']:<8} {ablated['std_len']:<8} {ablated['distinct_2']:<6} {ablated['self_bleu']:<10} {ablated['unique_ratio']:<6}")
        # 차이
        print(f"{'':10} {'Δ (n-a)':10} {'':4} {normal['avg_len'] - ablated['avg_len']:+8.2f} {normal['std_len'] - ablated['std_len']:+8.2f} {normal['distinct_2'] - ablated['distinct_2']:+6.3f} {normal['self_bleu'] - ablated['self_bleu']:+10.3f}")
        print()
    results["inner_outer_ablation"] = inner_outer_data

    # ================================
    # Test 3: State Sensitivity
    # ================================
    print("\n" + "=" * 70)
    print("TEST 3 — State Sensitivity (다른 상태 → 다른 출력)")
    print("=" * 70)
    sens_data = {}
    for name, pipe in pipes.items():
        print(f"\n── {name} ──")
        intent_sens = {}
        for intent in ["greet", "thank", "complain"]:
            d = test_state_sensitivity(pipe, intent)
            intent_sens[intent] = {
                "mean_edit": d["mean_edit"],
                "unique_outputs": d["unique_outputs"],
            }
            print(f"  {intent:10} mean_edit={d['mean_edit']:5.2f}  unique={d['unique_outputs']}/{len(d['outputs'])}")
            for out in d["outputs"]:
                print(f"    • {out!r}")
        sens_data[name] = intent_sens
    results["state_sensitivity"] = sens_data

    # ================================
    # Test 4: Diversity
    # ================================
    print("\n" + "=" * 70)
    print("TEST 4 — Diversity (전체)")
    print("=" * 70)
    print(f"{'character':10} {'n':5} {'unique':7} {'d1':7} {'d2':7} {'self_bleu':10} {'avg_len':8}")
    print("-" * 70)
    div_data = {}
    for name, pipe in pipes.items():
        d = test_diversity(pipe, INTENTS, n_trials=10)
        div_data[name] = d
        print(f"{name:10} {d['n_total']:<5} {d['n_unique']:<7} {d['distinct_1']:<7} {d['distinct_2']:<7} {d['self_bleu_3']:<10} {d['avg_len_words']:<8}")
    results["diversity"] = div_data

    # ================================
    # Test 5: Latency
    # ================================
    print("\n" + "=" * 70)
    print("TEST 5 — Latency (stage별 기여, μs)")
    print("=" * 70)
    print(f"{'character':10} {'S1':8} {'S1+2':8} {'S1+2+3':8} {'Full':8} {'ΔS2':8} {'ΔS3':8} {'ΔS4':8}")
    print("-" * 70)
    lat_data = {}
    for name, pipe in pipes.items():
        d = test_latency(pipe, "greet", n_runs=50)
        lat_data[name] = d
        print(f"{name:10} {d['stage1_us']:<8} {d['stage1+2_us']:<8} {d['stage1+2+3_us']:<8} {d['full_us']:<8} {d['s2_delta_us']:+7.1f} {d['s3_delta_us']:+7.1f} {d['s4_delta_us']:+7.1f}")
    results["latency"] = lat_data

    # ================================
    # Test 6: Divergence vs Outputs (새로운 관찰)
    # ================================
    print("\n" + "=" * 70)
    print("TEST 6 — Divergence 효과 (표리 괴리가 실제 출력에 반영?)")
    print("=" * 70)
    print(f"{'character':10} {'div':6} {'avg_class_len':14} {'interj_ratio':14} {'addr_ratio':12}")
    print("-" * 70)
    div_struct = {}
    for name, pipe in pipes.items():
        # class sequence 100개 샘플링
        all_classes = []
        for intent in INTENTS:
            for t in range(15):
                pipe.stage1.rng = np.random.default_rng(200 + t)
                cseq = pipe.run_stage1(pipe.npc, intent, max_len=6)
                all_classes.append(cseq[1:-1])  # <S>, <EOS> 제외
        flat = [c for seq in all_classes for c in seq]
        avg_len = np.mean([len(s) for s in all_classes])
        interj_ratio = flat.count("interj") / max(len(flat), 1)
        addr_ratio = flat.count("addr") / max(len(flat), 1)
        div_struct[name] = {
            "divergence": round(pipe.npc.divergence(), 3),
            "avg_class_len": round(float(avg_len), 2),
            "interj_ratio": round(interj_ratio, 3),
            "addr_ratio": round(addr_ratio, 3),
        }
        print(f"{name:10} {pipe.npc.divergence():<6.2f} {avg_len:<14.2f} {interj_ratio:<14.3f} {addr_ratio:<12.3f}")
    results["divergence_structure"] = div_struct

    # 저장
    with open("/home/claude/dialogue_study/phase2/quality_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n→ saved quality_report.json")

    return results


if __name__ == "__main__":
    run_all()
