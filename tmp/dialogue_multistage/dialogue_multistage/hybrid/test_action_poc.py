"""Action-specific intents smoke test (ACTION_LINES + ACTION_REACTIONS)."""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine


def check(name, char, context, intents_to_test):
    eng = HybridEngine.load(character=char, context=context,
                            dialogue_root=HERE / "dialogues")
    print(f"\n{'='*70}")
    print(f"  {char} / context={context}")
    print("=" * 70)

    runtime_ctx = {"name": char}
    states = [
        ("호감_높음_흥분_중", {"affinity": 0.8, "arousal": 0.3}),
        ("호감_높음_흥분_높음", {"affinity": 0.8, "arousal": 0.8}),
    ]
    for intent in intents_to_test:
        if intent not in eng.intents:
            print(f"  (intent '{intent}' not found — skip)")
            continue
        print(f"\n  -- {intent} ({len(eng.intents[intent].get('templates', []))} tpls) --")
        for label, st in states:
            eng.set_seed(42, reset_history=True)
            outs = [eng.generate(intent, st, context=runtime_ctx)
                    for _ in range(3) for __ in [eng.set_seed(100 + _)]]
            outs = []
            for s in range(3):
                eng.set_seed(100 + s)
                outs.append(eng.generate(intent, st, context=runtime_ctx))
            print(f"    {label:18s}")
            for o in outs:
                print(f"       {o!r}")


# 1인칭 대사 (ACTION_LINES)
check("action_lines 1인칭", "린", "action_lines",
      intents_to_test=["hug", "deep_kiss", "cheek_caress"])
check("action_lines 1인칭", "유카", "action_lines",
      intents_to_test=["hug", "deep_kiss", "genital_caress"])

# 3인칭 묘사 (ACTION_REACTIONS)
check("action_reactions 3인칭", "린", "action_reactions",
      intents_to_test=["hug", "deep_kiss", "thrust_gentle"])
check("action_reactions 3인칭", "유카", "action_reactions",
      intents_to_test=["hug", "deep_kiss", "sync_thrust"])
