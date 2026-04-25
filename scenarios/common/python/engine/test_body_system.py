# test_body_system.py — body_state / injury / loss / body_gate 통합 검증
#
# 실행: python test_body_system.py
# (mock_morld 주입 → 모듈 import → 직접 호출 검증)

import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# Path 설정: scenarios/common/python + S02 tests (mock_morld)
HERE = Path(__file__).resolve().parent
COMMON_PY = HERE.parent  # scenarios/common/python
S02_TESTS = HERE.parent.parent.parent / "scenario02" / "python" / "tests"
if str(COMMON_PY) not in sys.path:
    sys.path.insert(0, str(COMMON_PY))
if str(S02_TESTS) not in sys.path:
    sys.path.insert(0, str(S02_TESTS))


from mock_morld import MockMorld

# MockMorld에 누락된 API 보강 (engine 테스트용)
def _mock_get_unit_name(self, unit_id):
    u = self._units.get(unit_id)
    return u["info"]["name"] if u else None

MockMorld.get_unit_name = _mock_get_unit_name

mock = MockMorld()
sys.modules["morld"] = mock

# Mock 주입 후 import
from engine import body_state, injury, loss, body_gate


passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        print(f"  PASS  {name}")
        passed += 1
    else:
        print(f"  FAIL  {name}: {detail}")
        failed += 1


def setup_unit(uid=10, name="테스트", vit=10, species=None):
    mock.reset()
    props = {"스탯:체력": vit}
    if species:
        props["종족"] = species
    mock.register_unit(uid, name=name, props=props)


# === T1: 부상 누적 ===
def test_injury_accumulate():
    print("\n[T1] 부상 누적/sparse cleanup")
    setup_unit(uid=10, vit=50)
    actual1 = injury.add_injury(10, "왼팔", 30, "타박")
    sev1 = injury.get_severity(10, "왼팔")
    check("T1.1 add_injury 정상 적용", sev1 == actual1, f"sev={sev1}, actual={actual1}")
    check("T1.2 종류 저장", injury.get_kind(10, "왼팔") == "타박")

    actual2 = injury.add_injury(10, "왼팔", 20, "출혈")
    sev2 = injury.get_severity(10, "왼팔")
    check("T1.3 누적", sev2 == actual1 + actual2, f"sev={sev2}, expect={actual1+actual2}")
    check("T1.4 종류 갱신", injury.get_kind(10, "왼팔") == "출혈")


# === T2: 체력 저항 ===
def test_resistance():
    print("\n[T2] 체력 저항 (침식 패턴)")
    setup_unit(uid=10, vit=10)
    actual_low = injury.add_injury(10, "왼팔", 100)  # 체력 10 → 80% 적용

    setup_unit(uid=11, vit=50)
    actual_high = injury.add_injury(11, "왼팔", 100)  # 체력 50 → 0% (clamp 10%)

    check("T2.1 약한 체력 더 큰 부상", actual_low > actual_high,
          f"vit10={actual_low}, vit50={actual_high}")
    check("T2.2 저항 floor 10%", actual_high >= 10,
          f"actual_high={actual_high}, expected >= 10")


# === T3: 회복 + sparse cleanup ===
def test_reduce_and_cleanup():
    print("\n[T3] 회복 + sparse cleanup")
    setup_unit(uid=10, vit=10)  # 저항 약하게 — actual 24 정도
    injury.add_injury(10, "왼팔", 30, "타박")
    cur = injury.get_severity(10, "왼팔")

    reduced = injury.reduce_injury(10, "왼팔", 10)
    check("T3.1 부분 회복 — sev 감소", injury.get_severity(10, "왼팔") == cur - 10,
          f"sev={injury.get_severity(10, '왼팔')}, expect={cur-10}")
    check("T3.2 reduce 반환값", reduced == 10, f"reduced={reduced}")

    injury.reduce_injury(10, "왼팔", 100)  # 0 도달
    check("T3.3 완전 회복 → 정도 prop None",
          mock.get_unit_prop(10, "부상:왼팔:정도") is None)
    check("T3.4 완전 회복 → 종류 prop None",
          mock.get_unit_prop(10, "부상:왼팔:종류") is None)


# === T4: 결손 + 보조구 ===
def test_loss_and_prosthetic():
    print("\n[T4] 결손 + 보조구")
    setup_unit(uid=10)
    loss.add_loss(10, "왼다리", "절단")
    check("T4.1 결손 부여", loss.has_loss(10, "왼다리"))
    check("T4.2 결손 종류", loss.get_kind(10, "왼다리") == "절단")
    check("T4.3 보조구 X → is_part_lost True", loss.is_part_lost(10, "왼다리"))

    # idempotent
    loss.add_loss(10, "왼다리", "재시도")
    check("T4.4 결손 재호출 — 종류 갱신 없음 (idempotent)",
          loss.get_kind(10, "왼다리") == "절단")

    loss.equip_prosthetic(10, "왼다리", item_uid=999)
    check("T4.5 보조구 장착 후 is_part_lost False",
          not loss.is_part_lost(10, "왼다리"))
    check("T4.6 has_prosthetic", loss.has_prosthetic(10, "왼다리"))


# === T5: gate "any" 룰 — 한쪽만 결손 → 능력 유지 ===
def test_gate_any_rule():
    print("\n[T5] gate any 룰 — 한쪽 결손 시 능력 유지")
    setup_unit(uid=10)
    loss.add_loss(10, "왼다리")
    check("T5.1 한쪽 결손 — can_move True (any)", body_gate.can_move(10))
    check("T5.2 한쪽 결손 — mobility_factor 1.0 (any: max)",
          body_gate.get_mobility_factor(10) == 1.0,
          f"f={body_gate.get_mobility_factor(10)}")

    loss.add_loss(10, "오른다리")
    check("T5.3 양쪽 결손 — can_move False",
          not body_gate.can_move(10))
    check("T5.4 양쪽 결손 — mobility_factor 0.0",
          body_gate.get_mobility_factor(10) == 0.0)


# === T6: 부상 페널티 (차단 X, factor만) ===
def test_factor_injury_penalty():
    print("\n[T6] 부상 페널티 — factor 만, 차단 없음")
    setup_unit(uid=10, vit=10)
    injury.add_injury(10, "왼팔", 50)
    injury.add_injury(10, "오른팔", 50)
    sev_l = injury.get_severity(10, "왼팔")
    sev_r = injury.get_severity(10, "오른팔")
    f = body_gate.get_hand_factor(10)
    check("T6.1 양 팔 부상 — factor < 1.0", f < 1.0,
          f"f={f}, sev_l={sev_l}, sev_r={sev_r}")
    check("T6.2 부상 차단 없음 — can_use_hands True",
          body_gate.can_use_hands(10))


# === T7: aggregation 룰 override ===
def test_aggregation_override():
    print("\n[T7] aggregation 룰 override")
    setup_unit(uid=10)
    body_state.ABILITY_AGGREGATION["mobility"] = "all"
    try:
        loss.add_loss(10, "왼다리")
        check("T7.1 all 룰 — 한쪽 결손도 차단",
              not body_gate.can_move(10))
        check("T7.2 all 룰 — factor=min(0,1)=0.0",
              body_gate.get_mobility_factor(10) == 0.0)
    finally:
        body_state.ABILITY_AGGREGATION.pop("mobility", None)


# === T8: 결박 + 결손 통합 ===
def test_restraint_integration():
    print("\n[T8] 결박 + 결손 통합 차단")
    setup_unit(uid=10)
    mock.set_unit_prop(10, "결박:상체", 1)
    check("T8.1 결박:상체 → can_use_hands False",
          not body_gate.can_use_hands(10))
    mock.set_unit_prop(10, "결박:상체", None)
    check("T8.2 결박 해제 → 복원", body_gate.can_use_hands(10))

    loss.add_loss(10, "왼팔")
    loss.add_loss(10, "오른팔")
    check("T8.3 양 팔 결손 → can_use_hands False",
          not body_gate.can_use_hands(10))


# === T9: 머리 1 부위 → 다중 능력 ===
def test_head_multi_ability():
    print("\n[T9] 머리 — 다중 능력 매핑")
    setup_unit(uid=10)
    loss.add_loss(10, "머리")
    check("T9.1 머리 결손 → can_speak False", not body_gate.can_speak(10))
    check("T9.2 머리 결손 → can_see False", not body_gate.can_see(10))
    check("T9.3 머리 결손 → can_hear False", not body_gate.can_hear(10))


# === T10: 부상 목록 ===
def test_get_injuries():
    print("\n[T10] get_injuries — 부상 부위 enumerate")
    setup_unit(uid=10, vit=50)
    injury.add_injury(10, "왼팔", 20)
    injury.add_injury(10, "몸통", 30)
    items = injury.get_injuries(10)
    parts = [it[0] for it in items]
    check("T10.1 부상 부위 포함", "왼팔" in parts and "몸통" in parts,
          f"parts={parts}")
    check("T10.2 부상 없는 부위 제외", "오른팔" not in parts and "머리" not in parts)


# === T11: 종족별 layout ===
def test_species_layout():
    print("\n[T11] 종족별 layout 등록")
    body_state.register_layout("tentacle", {
        "hands": ["촉수1", "촉수2", "촉수3", "촉수4"],
        "mobility": ["촉수1", "촉수2", "촉수3", "촉수4"],
    })
    setup_unit(uid=20, species="tentacle")
    layout = body_state.get_body_layout(20)
    check("T11.1 종족 layout 조회",
          layout["hands"] == ["촉수1", "촉수2", "촉수3", "촉수4"])

    # 1개만 결손 — any 룰이라 능력 유지
    loss.add_loss(20, "촉수1")
    check("T11.2 4 촉수 중 1 결손 — can_use_hands True (any)",
          body_gate.can_use_hands(20))


# === run ===
test_injury_accumulate()
test_resistance()
test_reduce_and_cleanup()
test_loss_and_prosthetic()
test_gate_any_rule()
test_factor_injury_penalty()
test_aggregation_override()
test_restraint_integration()
test_head_multi_ability()
test_get_injuries()
test_species_layout()

print()
print("=" * 50)
print(f"TOTAL: {passed + failed} tests, {passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
