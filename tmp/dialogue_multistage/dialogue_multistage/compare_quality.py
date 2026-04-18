"""Baseline 대비 현재 quality_report 비교.

Usage:
    python compare_quality.py                        # baseline vs 최신 report
    python compare_quality.py <report1> <report2>   # 임의 두 리포트 비교
"""
import io
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def fmt_delta(a, b, fmt=".3f", better="higher"):
    """a → b 변화. better='higher'면 +가 좋음, 'lower'면 -가 좋음, 'neutral'이면 기호만."""
    if a is None or b is None:
        return ""
    d = b - a
    if abs(d) < 1e-9:
        mark = "="
    elif better == "higher":
        mark = "↑" if d > 0 else "↓"
    elif better == "lower":
        mark = "↓(+)" if d < 0 else "↑(-)"
    else:
        mark = "+" if d > 0 else ""
    return f"{d:+{fmt}} {mark}"


def compare(base_path, curr_path):
    base = load(base_path)
    curr = load(curr_path)
    print(f"BASE: {base_path}")
    print(f"CURR: {curr_path}")
    print()

    # -------- Inner/Outer Ablation --------
    print("=" * 72)
    print("Test 2 — Inner/Outer Ablation (normal vs ablated)")
    print("   핵심: normal의 avg_len · unique_ratio가 ablated와 달라질수록 inner 효과 ↑")
    print("=" * 72)
    io_b = base.get("inner_outer_ablation", {})
    io_c = curr.get("inner_outer_ablation", {})
    hdr = f"{'npc':6} {'mode':8} {'avg_len':>14} {'d2':>14} {'unique':>14}"
    print(hdr)
    for npc in io_c:
        for mode in ("normal", "ablated"):
            b_m = io_b.get(npc, {}).get(mode, {})
            c_m = io_c.get(npc, {}).get(mode, {})
            al = f"{c_m.get('avg_len', 0):.2f} ({fmt_delta(b_m.get('avg_len'), c_m.get('avg_len'), '.2f', 'neutral')})"
            d2 = f"{c_m.get('distinct_2', 0):.3f} ({fmt_delta(b_m.get('distinct_2'), c_m.get('distinct_2'), '.3f', 'higher')})"
            un = f"{c_m.get('unique_ratio', 0):.3f} ({fmt_delta(b_m.get('unique_ratio'), c_m.get('unique_ratio'), '.3f', 'higher')})"
            print(f"{npc:6} {mode:8} {al:>14} {d2:>14} {un:>14}")
        # Δ(normal - ablated) 변화량 — 핵심 지표
        for key, fmt, label in [("avg_len", ".2f", "Δavg_len"),
                                 ("unique_ratio", ".3f", "Δunique")]:
            b_delta = io_b.get(npc, {}).get("normal", {}).get(key, 0) - io_b.get(npc, {}).get("ablated", {}).get(key, 0)
            c_delta = io_c.get(npc, {}).get("normal", {}).get(key, 0) - io_c.get(npc, {}).get("ablated", {}).get(key, 0)
            change = c_delta - b_delta
            print(f"  {npc} {label}:  base={b_delta:+{fmt}}  curr={c_delta:+{fmt}}  change={change:+{fmt}}")
        print()

    # -------- State Sensitivity --------
    print("=" * 72)
    print("Test 3 — State Sensitivity (mean_edit · unique/7)")
    print("   핵심: mean_edit ↑, unique ↑ 면 상태 반응성 ↑")
    print("=" * 72)
    ss_b = base.get("state_sensitivity", {})
    ss_c = curr.get("state_sensitivity", {})
    print(f"{'npc':6} {'intent':10} {'mean_edit':>20} {'unique/7':>14}")
    for npc in ss_c:
        for intent in ss_c[npc]:
            b_m = ss_b.get(npc, {}).get(intent, {})
            c_m = ss_c.get(npc, {}).get(intent, {})
            me = f"{c_m.get('mean_edit', 0):.2f} ({fmt_delta(b_m.get('mean_edit'), c_m.get('mean_edit'), '.2f', 'higher')})"
            uq = f"{c_m.get('unique_outputs', 0)} ({fmt_delta(b_m.get('unique_outputs'), c_m.get('unique_outputs'), '.0f', 'higher')})"
            print(f"{npc:6} {intent:10} {me:>20} {uq:>14}")
        print()

    # -------- Diversity --------
    print("=" * 72)
    print("Test 4 — Diversity (전체)")
    print("=" * 72)
    dv_b = base.get("diversity", {})
    dv_c = curr.get("diversity", {})
    print(f"{'npc':6} {'d2':>16} {'self_bleu':>18} {'avg_len':>16} {'unique':>16}")
    for npc in dv_c:
        b_m = dv_b.get(npc, {})
        c_m = dv_c.get(npc, {})
        d2 = f"{c_m.get('distinct_2', 0):.3f} ({fmt_delta(b_m.get('distinct_2'), c_m.get('distinct_2'), '.3f', 'higher')})"
        sb = f"{c_m.get('self_bleu_3', 0):.3f} ({fmt_delta(b_m.get('self_bleu_3'), c_m.get('self_bleu_3'), '.3f', 'lower')})"
        al = f"{c_m.get('avg_len_words', 0):.2f} ({fmt_delta(b_m.get('avg_len_words'), c_m.get('avg_len_words'), '.2f', 'neutral')})"
        un = f"{c_m.get('n_unique', 0)} ({fmt_delta(b_m.get('n_unique'), c_m.get('n_unique'), '.0f', 'higher')})"
        print(f"{npc:6} {d2:>16} {sb:>18} {al:>16} {un:>16}")
    print()

    # -------- Latency --------
    print("=" * 72)
    print("Test 5 — Latency (Full, μs)")
    print("=" * 72)
    lt_b = base.get("latency", {})
    lt_c = curr.get("latency", {})
    print(f"{'npc':6} {'full_us':>20}")
    for npc in lt_c:
        b_m = lt_b.get(npc, {})
        c_m = lt_c.get(npc, {})
        fu = f"{c_m.get('full_us', 0):.0f} ({fmt_delta(b_m.get('full_us'), c_m.get('full_us'), '.0f', 'lower')})"
        print(f"{npc:6} {fu:>20}")
    print()

    # -------- Divergence Structure --------
    print("=" * 72)
    print("Test 6 — Divergence Structure (avg_class_len, interj/addr ratio)")
    print("=" * 72)
    ds_b = base.get("divergence_structure", {})
    ds_c = curr.get("divergence_structure", {})
    print(f"{'npc':6} {'avg_class_len':>20} {'interj_ratio':>18} {'addr_ratio':>18}")
    for npc in ds_c:
        b_m = ds_b.get(npc, {})
        c_m = ds_c.get(npc, {})
        al = f"{c_m.get('avg_class_len', 0):.2f} ({fmt_delta(b_m.get('avg_class_len'), c_m.get('avg_class_len'), '.2f', 'neutral')})"
        ir = f"{c_m.get('interj_ratio', 0):.3f} ({fmt_delta(b_m.get('interj_ratio'), c_m.get('interj_ratio'), '.3f', 'neutral')})"
        ar = f"{c_m.get('addr_ratio', 0):.3f} ({fmt_delta(b_m.get('addr_ratio'), c_m.get('addr_ratio'), '.3f', 'higher')})"
        print(f"{npc:6} {al:>20} {ir:>18} {ar:>18}")
    print()


if __name__ == "__main__":
    if len(sys.argv) == 3:
        compare(sys.argv[1], sys.argv[2])
    else:
        compare(HERE / "quality_baseline.json", HERE / "quality_report.json")
