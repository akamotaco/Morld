"""전체 10 아키타입 parity 검증."""
import io
import sys
import importlib
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import engine as _hybrid_engine
HybridEngine = _hybrid_engine.HybridEngine
_merge_intents = _hybrid_engine._merge_intents

S02_PATH = Path("C:/Users/akamo/Desktop/work/morld/scenarios/common/python")
sys.path.insert(0, str(S02_PATH))
sys.modules.pop("engine", None)

ARCHETYPES = ["stoic", "gentle", "cheerful", "timid", "cold",
              "seductive", "fierce", "proud", "innocent", "devoted"]

SECTIONS = [
    ("LINES", "romance.yaml"),
    ("REACTIONS", "romance_reactions.yaml"),
    ("ACTION_LINES", "action_lines.yaml"),
    ("ACTION_REACTIONS", "action_reactions.yaml"),
]


def extract_s02_texts(section_dict):
    texts = set()
    for pool_dict in section_dict.values():
        if not isinstance(pool_dict, dict):
            continue
        for texts_list in pool_dict.values():
            if isinstance(texts_list, list):
                for t in texts_list:
                    if isinstance(t, str):
                        texts.add(t)
    return texts


def extract_yaml_texts(yaml_path):
    import yaml
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    texts = set()
    for intent_data in data.get("intents", {}).values():
        for tpl in intent_data.get("templates", []) or []:
            pat = tpl.get("pattern", "")
            if pat:
                texts.add(pat)
    return texts


print(f"{'archetype':12s} {'section':20s} {'S02':>5s} {'Hyb':>5s} {'missing':>8s} {'extra':>5s} {'%cov':>6s}")
print("-" * 70)

fails = 0
total_s02 = 0
total_hyb = 0
total_missing = 0

for arch in ARCHETYPES:
    mod = importlib.import_module(f"engine.tone_templates.{arch}")
    for section, yaml_name in SECTIONS:
        s02 = extract_s02_texts(getattr(mod, section))
        yaml_path = HERE / "dialogues" / "archetype_dialogues" / arch / yaml_name
        if not yaml_path.exists():
            print(f"{arch:12s} {section:20s} MISSING FILE: {yaml_path}")
            fails += 1
            continue
        hyb = extract_yaml_texts(yaml_path)
        missing = s02 - hyb
        extra = hyb - s02
        cov = len(s02 & hyb) / len(s02) * 100 if s02 else 100.0
        total_s02 += len(s02)
        total_hyb += len(hyb)
        total_missing += len(missing)
        status = "" if (len(missing) == 0 and len(extra) == 0) else " ⚠"
        print(f"{arch:12s} {section:20s} {len(s02):5d} {len(hyb):5d} "
              f"{len(missing):8d} {len(extra):5d} {cov:5.1f}%{status}")
        if missing or extra:
            fails += 1

print("-" * 70)
print(f"{'TOTAL':12s} {'':20s} {total_s02:5d} {total_hyb:5d} {total_missing:8d}")
print()
if fails == 0:
    print(f"✅ ALL 40 CHECKS PASSED — 텍스트 손실 0, 신규 0")
else:
    print(f"❌ {fails} CHECKS FAILED")
    sys.exit(1)
