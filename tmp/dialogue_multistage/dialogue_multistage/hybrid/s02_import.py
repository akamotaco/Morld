"""S02 tone_templates → Hybrid archetype_dialogues 자동 변환.

AST 기반 안전 추출. S02 의존성 없이 파일만 읽어 dict 리터럴 파싱.

변환 규칙:
  LINES[category][coord] → intents[category].templates
    coord 2-tuple (X, Y)       → state_bias {affinity: X/100, arousal: Y/100}
    coord 3-tuple (X, Y, Z)    → 위 + {climax: Z/100}
    category suffix ":high"    → state_bias.climax += 0.6 (없으면)
    category suffix ":extreme" → state_bias.climax += 0.8

    각 text → 별도 template, id = {cat}_{x}_{y}_{z}_{i}

Usage:
    python s02_import.py <source.py> <out.yaml> [--section LINES|REACTIONS]
"""
from __future__ import annotations
import argparse
import ast
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


CLIMAX_TIER_MAP = {
    "high": 0.6,
    "extreme": 0.8,
}


def _extract_top_dict(source: str, var_name: str) -> Dict[str, Any]:
    """소스에서 `var_name = {...}` 탑레벨 할당의 literal_eval."""
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == var_name:
                return ast.literal_eval(node.value)
    raise KeyError(f"top-level '{var_name}' not found")


def _split_category(cat_key: str) -> tuple[str, str | None]:
    """'light:high' → ('light', 'high'). 'light' → ('light', None)."""
    parts = cat_key.split(":", 1)
    return parts[0], (parts[1] if len(parts) > 1 else None)


def _coord_to_bias(coord: tuple, tier: str | None) -> Dict[str, float]:
    """(X, Y) 또는 (X, Y, Z) 좌표 → state_bias dict."""
    if len(coord) == 2:
        x, y = coord
        z = None
    elif len(coord) == 3:
        x, y, z = coord
    else:
        raise ValueError(f"unsupported coord: {coord}")

    bias: Dict[str, float] = {
        "affinity": round(x / 100.0, 3),
        "arousal": round(y / 100.0, 3),
    }
    # 명시적 Z → 우선 / 없으면 tier에서 추론
    if z is not None:
        bias["climax"] = round(z / 100.0, 3)
    elif tier in CLIMAX_TIER_MAP:
        bias["climax"] = CLIMAX_TIER_MAP[tier]
    return bias


def convert_section(section_dict: Dict[str, Any]) -> Dict[str, Any]:
    """LINES / REACTIONS dict → hybrid intents dict."""
    intents: Dict[str, Any] = {}

    for cat_key, pool_dict in section_dict.items():
        base_intent, tier = _split_category(cat_key)
        if base_intent not in intents:
            intents[base_intent] = {"templates": [], "slots": {}}

        if not isinstance(pool_dict, dict):
            continue

        for coord, texts in pool_dict.items():
            if not isinstance(coord, tuple) or not isinstance(texts, list):
                continue
            try:
                bias = _coord_to_bias(coord, tier)
            except ValueError:
                continue

            z_label = int(bias.get("climax", 0.0) * 100)
            coord_tag = f"{int(coord[0])}_{int(coord[1])}_{z_label}"
            for i, text in enumerate(texts):
                if not isinstance(text, str):
                    continue
                tid = f"{cat_key.replace(':','_')}_{coord_tag}_{i}"
                intents[base_intent]["templates"].append({
                    "id": tid,
                    "pattern": text,
                    "state_bias": bias,
                })
    return intents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="S02 tone_templates/*.py 파일")
    ap.add_argument("out", help="출력 yaml 경로")
    ap.add_argument("--section", default="LINES",
                    choices=["LINES", "REACTIONS", "ACTION_LINES", "ACTION_REACTIONS"])
    ap.add_argument("--archetype", required=True, help="아키타입 이름 (예: cheerful)")
    ap.add_argument("--context", default="romance", help="context 이름")
    args = ap.parse_args()

    source = Path(args.source).read_text(encoding="utf-8")
    section = _extract_top_dict(source, args.section)
    intents = convert_section(section)

    out_data = {
        "archetype": args.archetype,
        "context": args.context,
        "_source": f"S02 {Path(args.source).name}:{args.section}",
        "intents": intents,
    }

    header = (f"# {args.archetype} archetype — {args.context} context\n"
              f"# 자동 변환: S02 {Path(args.source).name} / {args.section}\n"
              f"# 수정 시 다음 재변환에서 덮어쓰임 — 커스텀은 character override로.\n\n")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        header + yaml.dump(out_data, allow_unicode=True,
                            sort_keys=False, default_flow_style=False),
        encoding="utf-8")

    stats_intents = {k: len(v["templates"]) for k, v in intents.items()}
    total = sum(stats_intents.values())
    print(f"{args.source} / {args.section}")
    print(f"  -> {out_path}")
    print(f"  intents: {len(intents)}")
    for k, n in stats_intents.items():
        print(f"    {k:12s} {n:4d} templates")
    print(f"  TOTAL: {total} templates")


if __name__ == "__main__":
    main()
