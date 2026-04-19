"""S02 cheerful.py → 린 romance 로드 + smoke test."""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine


eng = HybridEngine.load(
    character="린", context="romance",
    dialogue_root=HERE / "dialogues")

print(f"Loaded: {eng.character} ({eng.archetype})")
print(f"Intents: {list(eng.intents.keys())}")
for intent, data in eng.intents.items():
    print(f"  {intent:20s} {len(data.get('templates', []))} templates")

# 상태 시나리오
scenarios = [
    ("초기_호감_낮음",      {"affinity": 0.3, "arousal": 0.2}),
    ("호감_중_흥분_중",     {"affinity": 0.3, "arousal": 0.6}),
    ("호감_높음_흥분_중",   {"affinity": 0.8, "arousal": 0.3}),
    ("호감_높음_흥분_높음", {"affinity": 0.8, "arousal": 0.8}),
    ("절정_접근",           {"affinity": 0.8, "arousal": 0.8, "climax": 0.6}),
    ("절정_직전",           {"affinity": 0.8, "arousal": 0.8, "climax": 0.8}),
    ("반발_약함",           {"affinity": -0.3, "arousal": 0.0}),
    ("반발_강함",           {"affinity": -0.6, "arousal": 0.3}),
    ("극한_저항",           {"affinity": -0.8, "arousal": 0.0}),
]

for intent in ["light", "medium", "strong", "penetration"]:
    print(f"\n{'=' * 70}")
    print(f"  intent: {intent}")
    print("=" * 70)
    for label, state in scenarios:
        eng.set_seed(42, reset_history=True)
        outs = []
        for s in range(3):
            eng.set_seed(100 + s)
            outs.append(eng.generate(intent, state))
        print(f"  {label:22s} state={state}")
        for o in outs:
            print(f"     {o!r}")
