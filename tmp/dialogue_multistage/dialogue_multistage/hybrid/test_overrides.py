"""Override 4 연산자 검증 테스트.

검증:
  1. add_templates — base 이후에 append
  2. add_slots     — 기존 pool에 append
  3. replace_templates — 같은 id 찾아 교체
  4. disable_templates — id로 제거
  + 정상 generate() 출력에 시호 고유 대사 등장
"""
import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import HybridEngine, _merge_intents


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


# =============================
# Unit tests (merge 로직)
# =============================
print("=" * 60)
print("UNIT — _merge_intents 4 연산자")
print("=" * 60)

base = {
    "greet": {
        "templates": [
            {"id": "base_a", "pattern": "A{end}", "state_bias": {}},
            {"id": "base_b", "pattern": "B{end}", "state_bias": {}},
            {"id": "base_c", "pattern": "C{end}", "state_bias": {}},
        ],
        "slots": {"end": [".", "!"]},
    }
}

# (1) add_templates
overrides = {"greet": {"add_templates": [{"id": "new_d", "pattern": "D"}]}}
merged = _merge_intents(base, overrides)
ids = [t["id"] for t in merged["greet"]["templates"]]
check("add_templates: id 'new_d' 포함", "new_d" in ids)
check("add_templates: 기존 3개 유지", all(x in ids for x in ["base_a", "base_b", "base_c"]))
check("add_templates: 순서 (기존 → 신규)", ids[-1] == "new_d")

# (2) replace_templates
overrides = {"greet": {"replace_templates": [
    {"id": "base_b", "pattern": "B_NEW", "state_bias": {}}]}}
merged = _merge_intents(base, overrides)
b_template = next(t for t in merged["greet"]["templates"] if t["id"] == "base_b")
check("replace_templates: 같은 id 패턴 교체", b_template["pattern"] == "B_NEW")
check("replace_templates: 개수 불변", len(merged["greet"]["templates"]) == 3)

# (3) disable_templates
overrides = {"greet": {"disable_templates": ["base_a"]}}
merged = _merge_intents(base, overrides)
ids = [t["id"] for t in merged["greet"]["templates"]]
check("disable_templates: 'base_a' 제거", "base_a" not in ids)
check("disable_templates: 나머지 유지", set(ids) == {"base_b", "base_c"})

# (4) add_slots
overrides = {"greet": {"add_slots": {"end": ["..."], "new_slot": ["X"]}}}
merged = _merge_intents(base, overrides)
check("add_slots: 기존 end에 '...' append", "..." in merged["greet"]["slots"]["end"])
check("add_slots: end 기존 값 유지", "." in merged["greet"]["slots"]["end"])
check("add_slots: 새 slot 'new_slot' 추가", "new_slot" in merged["greet"]["slots"])

# (5) 복합 — 연산자 조합
overrides = {"greet": {
    "disable_templates": ["base_a"],
    "replace_templates": [{"id": "base_b", "pattern": "B2"}],
    "add_templates": [{"id": "new_x"}],
    "add_slots": {"end": ["..."]},
}}
merged = _merge_intents(base, overrides)
ids = [t["id"] for t in merged["greet"]["templates"]]
check("조합: base_a 제거", "base_a" not in ids)
check("조합: base_b 교체 확인", next(t for t in merged["greet"]["templates"]
                                      if t["id"] == "base_b")["pattern"] == "B2")
check("조합: new_x 추가", "new_x" in ids)
check("조합: slots '...' 추가", "..." in merged["greet"]["slots"]["end"])

# =============================
# Integration — 실제 시호 yaml 로드
# =============================
print()
print("=" * 60)
print("INTEGRATION — 시호 캐릭터 override 실제 로드")
print("=" * 60)

eng = HybridEngine.load(
    character="시호", context="daily",
    dialogue_root=HERE / "dialogues")

greet = eng.intents.get("greet", {})
ids = [t.get("id") for t in greet.get("templates", [])]
check("시호 greet에 'shiho_specific_wait' 추가됨", "shiho_specific_wait" in ids)
check("원본 archetype template 유지 (tsun_wait)", "tsun_wait" in ids)
check("slot 'shiho_wait_expr' 추가됨", "shiho_wait_expr" in greet.get("slots", {}))

# 실 generate로 시호 고유 대사가 나오는지 확인 (높은 affinity + embarrassment 상태)
print("\n  시호 고유 dialogue 샘플 출력 (affinity=0.8, embarrassment=0.6):")
hits = 0
for seed in range(30):
    eng.set_seed(seed, reset_history=True)
    out = eng.generate("greet", {"affinity": 0.8, "embarrassment": 0.6})
    is_shiho_line = ("한참 기다렸잖아" in out or
                      "늦었다니까" in out or
                      "왜 이렇게 늦어" in out)
    if is_shiho_line:
        hits += 1
        if hits <= 3:
            print(f"    seed {seed}: {out!r}")

check("시호 고유 template이 실제 선택됨 (30 시도 중 ≥3회)", hits >= 3,
      detail=f"hits={hits}")

# =============================
# Summary
# =============================
print()
print("=" * 60)
print(f"RESULT: {passed} passed / {failed} failed / {passed+failed} total")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
