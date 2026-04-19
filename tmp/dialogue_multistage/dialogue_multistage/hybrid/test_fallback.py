"""Intent fallback chain 검증.

시나리오:
  1. load_composite(["romance", "action_lines"]) — 행위 + 카테고리 동시 탑재
  2. 존재하는 action (hug) 호출 → action pool 사용
  3. 존재하지 않는 action (예: make_up_action) → category fallback or 빈 문자열
  4. ACTION_TO_CATEGORY 에 없는 action → 빈 문자열 (graceful)
"""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine, ACTION_TO_CATEGORY


passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}  {detail}")
        failed += 1


print("=" * 70)
print("TEST 1: load_composite 기본 로드")
print("=" * 70)

eng = HybridEngine.load_composite(
    character="린",
    contexts=["romance", "action_lines"],
    dialogue_root=HERE / "dialogues")

print(f"  Loaded: {eng.character} ({eng.archetype})")
print(f"  Intent 수: {len(eng.intents)}")

check("'light' intent 존재 (LINES category)", "light" in eng.intents)
check("'hug' intent 존재 (ACTION_LINES)", "hug" in eng.intents)
check("'deep_kiss' intent 존재", "deep_kiss" in eng.intents)

# 기본 호출
state = {"affinity": 0.8, "arousal": 0.3}
eng.set_seed(42, reset_history=True)
out_hug = eng.generate("hug", state, context={"name": "린"})
eng.set_seed(42, reset_history=True)
out_light = eng.generate("light", state, context={"name": "린"})
check("'hug' 호출로 대사 생성됨", len(out_hug) > 0)
check("'light' 호출로 대사 생성됨", len(out_light) > 0)
print(f"    hug: {out_hug!r}")
print(f"    light: {out_light!r}")

print()
print("=" * 70)
print("TEST 2: 미탑재 action → category fallback")
print("=" * 70)

# 'hug' 를 intent에서 제거 후 호출 시 'light' 로 fallback 해야 함
eng_no_hug = HybridEngine.load_composite(
    character="린",
    contexts=["romance"],  # LINES만 (action_lines 제외)
    dialogue_root=HERE / "dialogues")
check("'hug' intent 없음 (romance only)", "hug" not in eng_no_hug.intents)
check("'light' intent 있음 (fallback 목표)", "light" in eng_no_hug.intents)

# hug 호출 → light로 fallback
eng_no_hug.set_seed(42, reset_history=True)
out_fb = eng_no_hug.generate("hug", state, context={"name": "린"})
check("'hug' 미탑재 상태에서 fallback으로 대사 생성", len(out_fb) > 0,
      detail=f"output={out_fb!r}")
print(f"    hug fallback: {out_fb!r}")

# deep_kiss도 light category로 fallback
eng_no_hug.set_seed(42, reset_history=True)
out_kiss_fb = eng_no_hug.generate("deep_kiss", state, context={"name": "린"})
check("'deep_kiss' fallback 성공", len(out_kiss_fb) > 0)
print(f"    deep_kiss fallback: {out_kiss_fb!r}")

# ACTION_TO_CATEGORY 매핑 검증
check("ACTION_TO_CATEGORY['hug'] == 'light'",
      ACTION_TO_CATEGORY.get("hug") == "light")
check("ACTION_TO_CATEGORY['thrust_rough'] == 'rough'",
      ACTION_TO_CATEGORY.get("thrust_rough") == "rough")

print()
print("=" * 70)
print("TEST 3: 매핑 없는 intent → 빈 문자열 (graceful)")
print("=" * 70)

out_none = eng_no_hug.generate("nonexistent_action", state)
check("매핑 없는 intent → 빈 문자열 반환 (crash 없음)", out_none == "",
      detail=f"output={out_none!r}")

print()
print("=" * 70)
print("TEST 4: fallback 동작이 anti-rep 에도 정상 반영")
print("=" * 70)

# fallback 사용 시 history는 effective_intent (light) 로 기록되어야 함
eng_ar = HybridEngine.load_composite(
    character="린", contexts=["romance"],
    dialogue_root=HERE / "dialogues")
eng_ar.set_seed(100, reset_history=True)
outs_fb = []
for i in range(5):
    eng_ar.set_seed(100 + i)
    outs_fb.append(eng_ar.generate("hug", state, context={"name": "린"}))
unique_fb = len(set(outs_fb))
check("fallback 상태에서도 anti-rep 으로 다양성 확보 (5/5 unique 기대)",
      unique_fb >= 3, detail=f"unique={unique_fb}/5")
print(f"    fallback 5회 출력:")
for o in outs_fb:
    print(f"      {o!r}")

print()
print("=" * 70)
print(f"RESULT: {passed} passed / {failed} failed")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
