"""REACTIONS 변환 + dynamic slot 주입 테스트."""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine


def run_npc(name, context):
    eng = HybridEngine.load(
        character=name, context=context,
        dialogue_root=HERE / "dialogues")
    print(f"\n{'='*70}")
    print(f"  {name} ({eng.archetype}) / context={context}")
    print("=" * 70)
    for intent, data in eng.intents.items():
        print(f"  {intent:14s} {len(data.get('templates', []))} templates")

    scenarios = [
        ("호감_높음_흥분_중",    {"affinity": 0.8, "arousal": 0.3}),
        ("호감_높음_흥분_높음",  {"affinity": 0.8, "arousal": 0.8}),
        ("반발_강함",            {"affinity": -0.6, "arousal": 0.3}),
        ("극한_저항",            {"affinity": -0.8, "arousal": 0.0}),
    ]

    runtime_ctx = {"name": name}

    for intent in ["light", "medium", "strong"]:
        print(f"\n  -- intent: {intent} --")
        for label, st in scenarios:
            eng.set_seed(100, reset_history=True)
            outs = []
            for s in range(3):
                eng.set_seed(200 + s)
                outs.append(eng.generate(intent, st, context=runtime_ctx))
            print(f"    {label:18s}")
            for o in outs:
                print(f"       {o!r}")


run_npc("린", "romance_reactions")
run_npc("유카", "romance_reactions")

# Dynamic slot 주입 검증
print("\n" + "=" * 70)
print("  Dynamic slot 주입 검증 — context 없이 vs 있이")
print("=" * 70)
eng = HybridEngine.load(character="린", context="romance_reactions",
                        dialogue_root=HERE / "dialogues")
for seed in range(3):
    eng.set_seed(42 + seed, reset_history=True)
    without_ctx = eng.generate("light", {"affinity": 0.8, "arousal": 0.3})
    eng.set_seed(42 + seed, reset_history=True)
    with_ctx = eng.generate("light", {"affinity": 0.8, "arousal": 0.3},
                             context={"name": "린"})
    print(f"  seed {seed}:")
    print(f"    w/o ctx: {without_ctx!r}")
    print(f"    w/  ctx: {with_ctx!r}")
    assert "{name}" not in with_ctx, "name 치환 실패"
    assert "린" in with_ctx or "{name}" not in without_ctx or without_ctx == "", \
        "name 주입 동작 확인 실패"
print("  PASS — dynamic slot 주입 정상")
