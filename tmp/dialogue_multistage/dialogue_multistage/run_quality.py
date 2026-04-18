"""Windows용 quality_test runner. 경로만 현재 폴더로 재설정."""
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "multistage"))

import quality_test

# quality_test.run_all 에서 하드코딩된 /home/claude/... 경로 리다이렉션
_orig = quality_test.run_all


def patched_run_all():
    import json
    from multistage.state_ms import load_character_ms
    from multistage.structural_ngram import build_structural_grammar, StructuralSampler
    from multistage.content_wfc import ContentWFC
    from multistage.function_wfc import FunctionWFC, assemble
    from wfc_v2 import LoadedCodebook
    from game_config import INTENTS
    from quality_test import (MultiStagePipeline, test_stage_ablation,
                              test_inner_outer_ablation, test_state_sensitivity,
                              test_diversity, test_latency)
    import numpy as np

    root = HERE
    characters = [
        ("시호", "01_shiho.yaml"),
        ("유카", "02_yuka.yaml"),
        ("린",   "05_rin.yaml"),
    ]

    results = {}
    pipes = {}
    for name, yaml_name in characters:
        npc, samples = load_character_ms(str(root / "examples" / yaml_name))
        cb = LoadedCodebook.load(str(root / "codebooks" / f"{name}.json"))
        pipes[name] = MultiStagePipeline(npc, samples, cb)

    print("=" * 70)
    print("TEST 1 — Stage-wise Ablation (정성적 예시)")
    print("=" * 70)
    for name, pipe in pipes.items():
        print(f"\n──── {name} ({pipe.npc.archetype}, divergence={pipe.npc.divergence():.2f}) ────")
        for intent in ["greet", "thank", "complain"]:
            print(f"\n  intent: {intent}")
            test_stage_ablation(pipe, intent, pipe.npc, n_samples=3)

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
        print(f"{'':10} {'Δ (n-a)':10} {'':4} {normal['avg_len'] - ablated['avg_len']:+8.2f} {normal['std_len'] - ablated['std_len']:+8.2f} {normal['distinct_2'] - ablated['distinct_2']:+6.3f} {normal['self_bleu'] - ablated['self_bleu']:+10.3f}")
        print()
    results["inner_outer_ablation"] = inner_outer_data

    print("\n" + "=" * 70)
    print("TEST 3 — State Sensitivity")
    print("=" * 70)
    sens_data = {}
    for name, pipe in pipes.items():
        print(f"\n── {name} ──")
        intent_sens = {}
        for intent in ["greet", "thank", "complain"]:
            d = test_state_sensitivity(pipe, intent)
            intent_sens[intent] = {"mean_edit": d["mean_edit"], "unique_outputs": d["unique_outputs"]}
            print(f"  {intent:10} mean_edit={d['mean_edit']:5.2f}  unique={d['unique_outputs']}/{len(d['outputs'])}")
            for out in d["outputs"]:
                print(f"    • {out!r}")
        sens_data[name] = intent_sens
    results["state_sensitivity"] = sens_data

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

    print("\n" + "=" * 70)
    print("TEST 5 — Latency (stage별, μs)")
    print("=" * 70)
    print(f"{'character':10} {'S1':8} {'S1+2':8} {'S1+2+3':8} {'Full':8} {'ΔS2':8} {'ΔS3':8} {'ΔS4':8}")
    print("-" * 70)
    lat_data = {}
    for name, pipe in pipes.items():
        d = test_latency(pipe, "greet", n_runs=50)
        lat_data[name] = d
        print(f"{name:10} {d['stage1_us']:<8} {d['stage1+2_us']:<8} {d['stage1+2+3_us']:<8} {d['full_us']:<8} {d['s2_delta_us']:+7.1f} {d['s3_delta_us']:+7.1f} {d['s4_delta_us']:+7.1f}")
    results["latency"] = lat_data

    print("\n" + "=" * 70)
    print("TEST 6 — Divergence 효과")
    print("=" * 70)
    print(f"{'character':10} {'div':6} {'avg_class_len':14} {'interj_ratio':14} {'addr_ratio':12}")
    print("-" * 70)
    div_struct = {}
    for name, pipe in pipes.items():
        all_classes = []
        for intent in INTENTS:
            for t in range(15):
                pipe.stage1.rng = np.random.default_rng(200 + t)
                cseq = pipe.run_stage1(pipe.npc, intent, max_len=6)
                all_classes.append(cseq[1:-1])
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

    out_path = root / "quality_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n→ saved {out_path}")
    return results


if __name__ == "__main__":
    patched_run_all()
