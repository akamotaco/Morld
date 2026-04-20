"""ROMANCE_REACTIONS rule 시스템 — single-layer + default value 동작 검증.

단위 테스트 (morld mock). 게임 플레이 없이 `_resolve_reaction_rules` 경로를
  1) 정규 rule 매치 (고정 텍스트 반환)
  2) 빈 dict catch-all 고정 텍스트
  3) 빈 dict catch-all 메서드 델리게이트 ("_method_name")
  4) 2D 좌표 rule (catch-all 있어도 먼저 매치)
  5) 매치 실패 + catch-all 없음 → None
로 분기 평가.
"""
import io
import sys
import types
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
# S02 python 경로
sys.path.insert(0, str(HERE.parent))
# common python (engine)
sys.path.insert(0, str(HERE.parent.parent.parent / "common" / "python"))


# ─── morld mock ───
_mock_props = {"관계:플레이어:호감": 80, "관계:플레이어:욕망": 70, "상태:성욕": 40}


def _mock_get_unit_props(uid):
    return _mock_props


def _mock_get_unit_info(uid):
    return {"name": "플레이어"}


def _mock_get_player_id():
    return 999


def _mock_modify_prop(*a, **kw):
    pass


morld_mock = types.ModuleType("morld")
morld_mock.get_unit_props = _mock_get_unit_props
morld_mock.get_unit_info = _mock_get_unit_info
morld_mock.get_player_id = _mock_get_player_id
morld_mock.modify_prop = _mock_modify_prop
sys.modules["morld"] = morld_mock


# ui mock (base.py import 용)
ui_mock = types.ModuleType("ui")
ui_mock.dialog = lambda *a, **kw: None
ui_mock.action_list = lambda *a, **kw: None
sys.modules["ui"] = ui_mock


# ui_style mock
ui_style_mock = types.ModuleType("ui_style")
for fn in ("style_muted", "style_highlight", "style_info", "style_danger", "style_success"):
    setattr(ui_style_mock, fn, lambda x: x)
sys.modules["ui_style"] = ui_style_mock


# ─── base.py import ───
import importlib
base = importlib.import_module("assets.base")
DialogueCoverageError = base.DialogueCoverageError


class FakeChar:
    """_resolve_reaction_rules / _generate_dialogue 테스트용 최소 fake."""
    name = "테스트"
    instance_id = 1
    REACTION_PROFILE = {"name": "테스트", "archetype": "stoic"}
    ROMANCE_REACTIONS = {}

    _resolve_reaction_rules = base.Character._resolve_reaction_rules
    _resolve_texts = base.Character._resolve_texts
    _nearest_2d = base.Character._nearest_2d
    _nearest_2d_raw = base.Character._nearest_2d_raw
    _check_reaction_condition = base.Character._check_reaction_condition

    def _build_reaction_state(self, stim_state=None):
        return {"호감": 80, "욕망": 70, "성욕": 40, "반발": 0}

    def _generate_dialogue(self, action_id, timing, stim_state):
        # 테스트에서는 실제 Hybrid 대신 고정 시그니처 반환
        return f"[GENERATED:{action_id}:{timing}]"


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
print("T1. 정규 dict rule 매치 — 고정 텍스트")
print("=" * 70)

c = FakeChar()
rules = [
    ({"호감": 90}, ["too_high"]),  # 호감 80 < 90, 미매치
    ({"호감": 50}, ["matched_mid"]),  # 매치
    ({}, ["catchall"]),  # 미도달
]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("첫 매치되는 rule 반환", result == "matched_mid", f"got={result!r}")


print()
print("=" * 70)
print("T2. 빈 dict catch-all 고정 텍스트")
print("=" * 70)

rules = [
    ({"호감": 200}, ["unreachable"]),  # 미매치
    ({}, ["catchall_fixed"]),
]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("catch-all 고정 텍스트 반환", result == "catchall_fixed", f"got={result!r}")


print()
print("=" * 70)
print("T3. 빈 dict catch-all 메서드 델리게이트")
print("=" * 70)

rules = [
    ({"호감": 200}, ["unreachable"]),
    ({}, "_generate_dialogue"),
]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("catch-all _generate_dialogue 호출",
      result == "[GENERATED:hug:start]", f"got={result!r}")


print()
print("=" * 70)
print("T4. 2D 좌표 rule — catch-all 있어도 먼저 매치")
print("=" * 70)

# 호감 80, 욕망 70 → (80,70) 에 가장 가까움
rules = [
    ({"호감": 200}, ["unreachable_dict"]),  # 미매치
    ((80, 70), ["coord_near"]),  # 매치 (nearest)
    ((20, 20), ["coord_far"]),
    ({}, "_generate_dialogue"),  # catch-all — 2D 매치되면 skip
]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("2D 좌표 rule 이 catch-all 보다 우선",
      result == "coord_near", f"got={result!r}")


print()
print("=" * 70)
print("T5. 2D 좌표 미정의 + catch-all — catch-all 사용")
print("=" * 70)

rules = [
    ({"호감": 200}, ["unreachable"]),
    ({}, "_generate_dialogue"),
]
result = c._resolve_reaction_rules(rules, rule_key="deep_kiss:start")
check("2D 없을 때 catch-all 메서드 델리게이트",
      result == "[GENERATED:deep_kiss:start]", f"got={result!r}")


print()
print("=" * 70)
print("T6. 모두 미매치 + catch-all 없음 → None (호출자가 raise 판정)")
print("=" * 70)

rules = [
    ({"호감": 200}, ["unreachable"]),
    ({"반발": 200}, ["unreachable2"]),
]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("매치 없음 → None", result is None, f"got={result!r}")


print()
print("=" * 70)
print("T7. 존재하지 않는 메서드 델리게이트 → DialogueCoverageError")
print("=" * 70)

rules = [({}, "_nonexistent_method")]
try:
    result = c._resolve_reaction_rules(rules, rule_key="hug:start")
    check("미존재 메서드 → raise", False, f"returned={result!r} (should raise)")
except DialogueCoverageError as e:
    check("미존재 메서드 → DialogueCoverageError raise", True)
    print(f"    msg: {e}")


print()
print("=" * 70)
print("T8. plain string list (rule 튜플 아님) — random.choice")
print("=" * 70)

rules = ["plain1", "plain2", "plain3"]
result = c._resolve_reaction_rules(rules, rule_key="hug:start")
check("plain string list → 그 중 하나 반환",
      result in ("plain1", "plain2", "plain3"), f"got={result!r}")


print()
print("=" * 70)
print(f"RESULT: {passed} passed / {failed} failed")
print("=" * 70)
sys.exit(0 if failed == 0 else 1)
