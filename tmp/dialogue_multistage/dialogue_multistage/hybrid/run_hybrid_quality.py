"""Hybrid 엔진에 Test 3/4/5 적용 + WFC baseline과 비교.

Test 1/2/6 은 hybrid 구조에 적용 불가 (stage 분리/class sequence 없음) → 생략.

출력:
  - hybrid_quality.json (현재 수치)
  - 콘솔에 WFC baseline 대비 나란히 비교
"""
import io
import json
import math
import sys
import time
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine


# ------------- 메트릭 (quality_test 와 동일 로직) -------------

def distinct_n(texts, n=2):
    grams = []
    for t in texts:
        toks = t.split()
        grams.extend([tuple(toks[i:i+n]) for i in range(len(toks)-n+1)])
    if not grams:
        return 0.0
    return len(set(grams)) / len(grams)


def self_bleu_lite(texts, n=3, sample=30):
    import random
    if len(texts) < 2:
        return 0.0
    rng = random.Random(0)
    idx = rng.sample(range(len(texts)), min(sample, len(texts)))
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
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def edit_distance(s1, s2):
    if len(s1) < len(s2):
        return edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + (c1 != c2)))
        prev = curr
    return prev[-1]


# ------------- 테스트 (hybrid 에 맞게 조정) -------------

def test_state_sensitivity(eng, intent):
    """Test 3: 여러 state 에서 출력 → 평균 edit distance."""
    state_variations = [
        {},
        {"affinity": 0.8, "trust": 0.7},
        {"embarrassment": 0.8, "affinity": 0.6},
        {"fatigue": 0.8},
        {"arousal": 0.9, "affinity": 0.8},
        {"hostility": 0.7},
        {"confidence": -0.6},
    ]
    eng.reset_history()
    outs = []
    for sv in state_variations:
        eng.set_seed(12345)
        outs.append(eng.generate(intent, sv))
    pairs = []
    for i in range(len(outs)):
        for j in range(i+1, len(outs)):
            pairs.append(edit_distance(outs[i], outs[j]))
    return {
        "outputs": outs,
        "mean_edit": round(sum(pairs)/len(pairs) if pairs else 0, 2),
        "unique_outputs": len(set(outs)),
    }


def test_diversity(eng, intents, n_trials=15):
    """Test 4: 다양한 state 에서 다양성 측정."""
    import random
    eng.reset_history()
    outs = []
    for intent in intents:
        for trial in range(n_trials):
            # 무작위 state
            r = random.Random(trial * 31 + 7)
            state = {
                "affinity": r.uniform(0, 1),
                "embarrassment": r.uniform(0, 1),
                "fatigue": r.uniform(0, 1),
                "arousal": r.uniform(0, 1),
            }
            eng.set_seed(77 + trial * 7)
            out = eng.generate(intent, state)
            if out:
                outs.append(out)
    lens = [len(o.split()) for o in outs]
    return {
        "n_total": len(outs),
        "n_unique": len(set(outs)),
        "distinct_1": round(distinct_n(outs, 1), 3),
        "distinct_2": round(distinct_n(outs, 2), 3),
        "self_bleu_3": round(self_bleu_lite(outs, 3), 3),
        "avg_len_words": round(sum(lens)/len(lens) if lens else 0, 2),
    }


def test_latency(eng, intent, n_runs=500):
    """Test 5: 단일 generate() 시간."""
    state = {"affinity": 0.5}
    for _ in range(50):
        eng.set_seed(0)
        eng.generate(intent, state)
    t0 = time.perf_counter()
    for i in range(n_runs):
        eng.set_seed(i)
        eng.generate(intent, state)
    t1 = time.perf_counter()
    return {"full_us": round((t1 - t0) / n_runs * 1e6, 1)}


# ------------- 메인 -------------

def main():
    characters = [
        ("시호", "shiho_hybrid.yaml"),
        ("유카", "yuka_hybrid.yaml"),
        ("린",   "rin_hybrid.yaml"),
    ]
    intents_common = ["greet", "thank", "complain"]

    engines = {}
    for name, yaml_name in characters:
        engines[name] = HybridEngine(str(HERE / "examples" / yaml_name))

    results = {}

    # Test 3
    print("=" * 72)
    print("TEST 3 — State Sensitivity (Hybrid)")
    print("=" * 72)
    sens_data = {}
    for name, eng in engines.items():
        print(f"\n── {name} ──")
        intent_sens = {}
        for intent in intents_common:
            d = test_state_sensitivity(eng, intent)
            intent_sens[intent] = {"mean_edit": d["mean_edit"],
                                    "unique_outputs": d["unique_outputs"]}
            print(f"  {intent:10} mean_edit={d['mean_edit']:5.2f}  unique={d['unique_outputs']}/{len(d['outputs'])}")
            for out in d["outputs"]:
                print(f"    • {out!r}")
        sens_data[name] = intent_sens
    results["state_sensitivity"] = sens_data

    # Test 4
    print("\n" + "=" * 72)
    print("TEST 4 — Diversity (Hybrid)")
    print("=" * 72)
    print(f"{'npc':10} {'n':5} {'unique':7} {'d1':7} {'d2':7} {'self_bleu':10} {'avg_len':8}")
    div_data = {}
    for name, eng in engines.items():
        d = test_diversity(eng, intents_common, n_trials=15)
        div_data[name] = d
        print(f"{name:10} {d['n_total']:<5} {d['n_unique']:<7} {d['distinct_1']:<7} {d['distinct_2']:<7} {d['self_bleu_3']:<10} {d['avg_len_words']:<8}")
    results["diversity"] = div_data

    # Test 5
    print("\n" + "=" * 72)
    print("TEST 5 — Latency (Hybrid, μs)")
    print("=" * 72)
    print(f"{'npc':10} {'full_us':>12}")
    lat_data = {}
    for name, eng in engines.items():
        d = test_latency(eng, "greet", n_runs=500)
        lat_data[name] = d
        print(f"{name:10} {d['full_us']:>12.1f}")
    results["latency"] = lat_data

    out_path = HERE / "hybrid_quality.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"\n→ saved {out_path}")

    # --------- WFC baseline 과 나란히 비교 ---------
    print("\n" + "=" * 72)
    print("WFC baseline vs Hybrid (핵심 지표만)")
    print("=" * 72)
    try:
        base = json.loads((ROOT / "quality_baseline.json").read_text(encoding="utf-8"))
    except Exception as e:
        print(f"WFC baseline 로드 실패: {e}")
        return

    print(f"\n-- Test 3: State Sensitivity (mean_edit 평균 over 3 intents) --")
    print(f"{'npc':10} {'WFC':>10} {'Hybrid':>10} {'Δ':>10}")
    for name in div_data:
        b = base.get("state_sensitivity", {}).get(name, {})
        h = sens_data.get(name, {})
        b_avg = sum(v["mean_edit"] for v in b.values()) / max(len(b), 1)
        h_avg = sum(v["mean_edit"] for v in h.values()) / max(len(h), 1)
        print(f"{name:10} {b_avg:>10.2f} {h_avg:>10.2f} {h_avg - b_avg:>+10.2f}")

    print(f"\n-- Test 4: Diversity --")
    print(f"{'npc':10} {'metric':15} {'WFC':>10} {'Hybrid':>10} {'Δ':>10}")
    for name in div_data:
        b = base.get("diversity", {}).get(name, {})
        h = div_data.get(name, {})
        for key in ("distinct_2", "self_bleu_3", "avg_len_words", "n_unique"):
            bv, hv = b.get(key, 0), h.get(key, 0)
            print(f"{name:10} {key:15} {bv:>10} {hv:>10} {hv - bv:>+10.3f}" if isinstance(bv, float) else
                  f"{name:10} {key:15} {bv:>10} {hv:>10} {hv - bv:>+10}")

    print(f"\n-- Test 5: Latency (μs) --")
    print(f"{'npc':10} {'WFC':>10} {'Hybrid':>10} {'speedup':>10}")
    for name in div_data:
        bv = base.get("latency", {}).get(name, {}).get("full_us", 0)
        hv = lat_data.get(name, {}).get("full_us", 0)
        speedup = bv / hv if hv > 0 else 0
        print(f"{name:10} {bv:>10.0f} {hv:>10.1f} {speedup:>9.1f}x")


if __name__ == "__main__":
    main()
