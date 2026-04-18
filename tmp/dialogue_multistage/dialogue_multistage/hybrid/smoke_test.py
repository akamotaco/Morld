"""Hybrid 엔진 smoke test + 정성 출력 샘플."""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine

eng = HybridEngine(str(HERE / "examples" / "shiho_hybrid.yaml"))


def run(intent, state, n=6, label=""):
    print(f"\n  [{intent}] {label}  state={state}")
    for s in range(n):
        eng.set_seed(s)
        out = eng.generate(intent, state)
        print(f"    {s}: {out!r}")


print("=" * 68)
print(f"Hybrid Engine — {eng.character} ({eng.archetype})")
print("=" * 68)

# ------------ thank intent (6 상태) ------------
print("\n### thank — 상태별 template 분포 확인")
run("thank", {"affinity": 0.6, "embarrassment": 0.1}, label="기본 감사")
run("thank", {"affinity": 0.6, "embarrassment": 0.3}, label="약한 감사")
run("thank", {"embarrassment": 0.8, "affinity": 0.6}, label="츤모드")
run("thank", {"embarrassment": 0.9, "affinity": 0.7}, label="극단 츤")
run("thank", {"affinity": 0.8, "trust": 0.7, "embarrassment": 0.2}, label="솔직")
run("thank", {"affinity": 0.5, "verbosity": 0.5, "embarrassment": 0.7}, label="장황 츤")

# ------------ greet intent ------------
print("\n### greet — 상태별 template 분포")
run("greet", {"affinity": 0.3, "arousal": 0.2}, label="저친밀")
run("greet", {"affinity": 0.5, "aggression": 0.3}, label="짜증")
run("greet", {"embarrassment": 0.5, "affinity": 0.4}, label="약한 츤")
run("greet", {"affinity": 0.7, "embarrassment": 0.6}, label="풀 츤 웨이팅")

# ------------ complain intent ------------
print("\n### complain — 상태별 template 분포")
run("complain", {"arousal": 0.6, "aggression": 0.5}, label="짜증")
run("complain", {"fatigue": 0.7}, label="피로")
run("complain", {"fatigue": 0.6, "affinity": 0.5, "embarrassment": 0.4}, label="소프트 벤트")
run("complain", {"aggression": 0.3}, label="중립 디스미스")

# ------------ 다양성 확인 — 동일 상태 10회 ------------
print("\n### 다양성 — 동일 state 10회 (thank, 츤모드)")
for s in range(10):
    eng.set_seed(s)
    out = eng.generate("thank", {"embarrassment": 0.8, "affinity": 0.6})
    print(f"    {s}: {out!r}")
