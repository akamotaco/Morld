# test_romance_core.py — romance_core.py 순수 함수 + mock 테스트
"""
순수 함수 위주 테스트 + mock_morld 기반 API 테스트.
equipment/gender/sound 등 2차 의존 모듈은 범위에서 제외.
"""
import sys
import math

import romance_core as rc
from romance_actions import (
    INSTANT_ACTIONS, TOGGLE_ACTIONS, SENSATION_MAP,
    SEMEN_PARTS, INTERNAL_SEMEN_PARTS,
    SEMEN_AMOUNT_BASE, SEMEN_AMOUNT_MIN, SEMEN_AMOUNT_MAX,
    PULL_OUT_STIM_THRESHOLD, PREPARATION_THRESHOLD,
    _THRUST_TOGGLE_IDS,
    VIRGINITY_CLEARING_ACTIONS, VIRGINITY_BONUS_AFFECTION, VIRGINITY_BONUS_EXP,
)
import stimulation as stim_mod

morld = sys.modules["morld"]


# ============================================
# get_effective_affection_req (순수 함수)
# ============================================

class TestEffectiveAffectionReq:
    def test_no_discount(self):
        """욕망/복종 0 → 할인 없음"""
        assert rc.get_effective_affection_req(100, 0, 0) == 100

    def test_desire_only_30_cap(self):
        """욕망 300 → 최대 30% 할인"""
        # desire_discount = min(100*0.3, 300*0.3) = min(30, 90) = 30
        # total = min(100*0.5, 30) = 30
        # result = max(20, 100-30) = 70
        assert rc.get_effective_affection_req(100, 300, 0) == 70

    def test_submission_only_30_cap(self):
        """복종 300 → 최대 30% 할인"""
        assert rc.get_effective_affection_req(100, 0, 300) == 70

    def test_both_50_cap(self):
        """욕망+복종 합산 최대 50%"""
        # desire_discount = min(100*0.3, 300*0.3) = 30
        # submission_discount = min(100*0.3, 300*0.3) = 30
        # total = min(100*0.5, 30+30) = min(50, 60) = 50
        # result = max(20, 100-50) = 50
        assert rc.get_effective_affection_req(100, 300, 300) == 50

    def test_absolute_minimum_20(self):
        """어떤 할인이든 최소 20 보장"""
        # req=30, 50% cap → 15, but min=20
        result = rc.get_effective_affection_req(30, 300, 300)
        assert result == 20

    def test_small_desire(self):
        """욕망 10 → 작은 할인"""
        # desire_discount = min(100*0.3, 10*0.3) = min(30, 3) = 3
        # total = min(100*0.5, 3) = 3
        # result = max(20, 100-3) = 97
        assert rc.get_effective_affection_req(100, 10, 0) == 97

    def test_req_zero(self):
        """요구치 0 → 할인 무의미, 최소 20"""
        assert rc.get_effective_affection_req(0, 100, 100) == 20

    def test_req_20_exactly(self):
        """요구치 20 → 할인 후에도 20 (최소값과 동일)"""
        assert rc.get_effective_affection_req(20, 0, 0) == 20


# ============================================
# get_sensation_level (mock 기반)
# ============================================

class TestSensationLevel:
    def test_zero_exp(self):
        """경험치 0 → 레벨 0"""
        morld.register_unit(10, props={})
        assert rc.get_sensation_level(10, "M") == 0

    def test_formula_sqrt(self):
        """sqrt(total/3) 검증"""
        # total=12 → sqrt(12/3) = sqrt(4) = 2
        # 구강 관련 exp_part들 찾기
        mouth_parts = [p for p, c in SENSATION_MAP.items() if c == "M"]
        if mouth_parts:
            props = {f"경험:{mouth_parts[0]}": 12}
            morld.register_unit(10, props=props)
            assert rc.get_sensation_level(10, "M") == 2

    def test_multiple_parts_sum(self):
        """같은 카테고리의 여러 부위 경험치 합산"""
        parts = [p for p, c in SENSATION_MAP.items() if c == "B"]
        if len(parts) >= 2:
            props = {f"경험:{parts[0]}": 6, f"경험:{parts[1]}": 6}
            morld.register_unit(10, props=props)
            # total=12, sqrt(12/3)=2
            assert rc.get_sensation_level(10, "B") == 2

    def test_level_cap_10(self):
        """레벨 상한 10"""
        parts = [p for p, c in SENSATION_MAP.items() if c == "V"]
        if parts:
            # sqrt(x/3) > 10 → x > 300
            props = {f"경험:{parts[0]}": 500}
            morld.register_unit(10, props=props)
            assert rc.get_sensation_level(10, "V") == 10

    def test_floor_rounding(self):
        """floor 반올림 확인"""
        parts = [p for p, c in SENSATION_MAP.items() if c == "A"]
        if parts:
            # total=10, sqrt(10/3) = sqrt(3.33) ≈ 1.826 → floor → 1
            props = {f"경험:{parts[0]}": 10}
            morld.register_unit(10, props=props)
            assert rc.get_sensation_level(10, "A") == 1


# ============================================
# is_action_available (mock 기반)
# ============================================

class TestIsActionAvailable:
    def _setup_partner(self, affection=0, arousal=0, submission=0):
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "상태:성욕": arousal,
            "관계:주인공:복종": submission,
        })

    def test_affection_met(self):
        """호감 충족 → True"""
        self._setup_partner(affection=50)
        action_def = {"affection_req": 50, "effects": {}}
        assert rc.is_action_available(2, 1, action_def) is True

    def test_affection_not_met(self):
        """호감 미달 → False"""
        self._setup_partner(affection=30)
        action_def = {"affection_req": 50, "effects": {}}
        assert rc.is_action_available(2, 1, action_def) is False

    def test_arousal_discount_unlocks(self):
        """호감 미달이지만 성욕으로 할인 → True"""
        # req=50, arousal=100
        # arousal_discount = min(50*0.3, 100*0.3) = min(15, 30) = 15
        # total = min(50*0.5, 15) = 15
        # eff_req = max(20, 50-15) = 35
        # affection 35 >= 35 → True
        self._setup_partner(affection=35, arousal=100)
        action_def = {"affection_req": 50, "effects": {}}
        assert rc.is_action_available(2, 1, action_def) is True

    def test_zero_req_always_available(self):
        """요구치 0 → 최소 20이지만 호감 0이면 False"""
        self._setup_partner(affection=0)
        action_def = {"affection_req": 0, "effects": {}}
        # eff_req = max(20, 0) = 20, affection 0 < 20 → False
        assert rc.is_action_available(2, 1, action_def) is False

    def test_zero_req_with_min_affection(self):
        """요구치 0 + 호감 20 → True (최소 20 통과)"""
        self._setup_partner(affection=20)
        action_def = {"affection_req": 0, "effects": {}}
        assert rc.is_action_available(2, 1, action_def) is True


# ============================================
# calculate_availability_score + resolve_action_mode
# ============================================

class TestAvailabilityScore:
    def _setup_partner(self, affection=0, arousal=0, submission=0):
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "상태:성욕": arousal,
            "관계:주인공:복종": submission,
        })

    def test_score_at_threshold(self):
        """호감 == eff_req → 점수 0 (합의 가능 경계)"""
        self._setup_partner(affection=50)
        action_def = {"affection_req": 50}
        assert rc.calculate_availability_score(2, 1, action_def) == 0

    def test_score_negative_when_below(self):
        """호감 < eff_req → 점수 음수 (강제 필요)"""
        self._setup_partner(affection=30)
        action_def = {"affection_req": 50}
        assert rc.calculate_availability_score(2, 1, action_def) < 0

    def test_score_positive_with_surplus(self):
        """호감 > eff_req → 점수 양수"""
        self._setup_partner(affection=80)
        action_def = {"affection_req": 50}
        assert rc.calculate_availability_score(2, 1, action_def) > 0


class TestResolveActionMode:
    def _setup_partner(self, affection=0, arousal=0, submission=0,
                       partner_strength=5, player_strength=5):
        morld.register_unit(1, name="주인공", props={"근력": player_strength})
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "상태:성욕": arousal,
            "관계:주인공:복종": submission,
            "근력": partner_strength,
        })

    def test_consensual_when_affection_met(self):
        """호감 충족 → consensual"""
        self._setup_partner(affection=60)
        action_def = {"affection_req": 50}
        assert rc.resolve_action_mode(2, 1, action_def) == "consensual"

    def test_forced_when_below(self):
        """호감 미달 → forced"""
        self._setup_partner(affection=10)
        action_def = {"affection_req": 80}
        assert rc.resolve_action_mode(2, 1, action_def) == "forced"

    def test_unavailable_when_strength_advantage_missing(self):
        """strength_advantage 필요하나 플레이어 근력 <= 파트너 → unavailable"""
        self._setup_partner(affection=100, player_strength=3, partner_strength=5)
        action_def = {
            "affection_req": 0,
            "physical_req": {"strength_advantage": True},
        }
        assert rc.resolve_action_mode(2, 1, action_def) == "unavailable"

    def test_consensual_overrides_when_strength_advantage_met(self):
        """strength_advantage 충족 + 호감 충족 → consensual"""
        self._setup_partner(affection=100, player_strength=10, partner_strength=5)
        action_def = {
            "affection_req": 50,
            "physical_req": {"strength_advantage": True},
        }
        assert rc.resolve_action_mode(2, 1, action_def) == "consensual"

    def test_unavailable_takes_priority_over_forced(self):
        """물리 전제 미달 시 unavailable이 forced보다 우선 (hard gate)"""
        self._setup_partner(affection=10, player_strength=3, partner_strength=5)
        action_def = {
            "affection_req": 80,
            "physical_req": {"strength_advantage": True},
        }
        # 호감 미달(forced 후보)이지만 근력도 부족 → unavailable
        assert rc.resolve_action_mode(2, 1, action_def) == "unavailable"

    def test_min_strength_gate(self):
        """min_strength 미달 → unavailable"""
        self._setup_partner(affection=100, player_strength=5)
        action_def = {
            "affection_req": 0,
            "physical_req": {"min_strength": 10},
        }
        assert rc.resolve_action_mode(2, 1, action_def) == "unavailable"


class TestCheckPhysicalReq:
    def _setup(self, player_str=5, partner_str=5):
        morld.register_unit(1, name="주인공", props={"근력": player_str})
        morld.register_unit(2, props={"근력": partner_str})

    def test_no_req_returns_true(self):
        """physical_req 없으면 항상 통과"""
        self._setup()
        ok, reason = rc.check_physical_req({"name": "test"}, 2, 1)
        assert ok is True
        assert reason is None

    def test_strength_advantage_met(self):
        """플레이어 근력 > 파트너 → 통과"""
        self._setup(player_str=10, partner_str=5)
        ok, _ = rc.check_physical_req(
            {"physical_req": {"strength_advantage": True}}, 2, 1)
        assert ok is True

    def test_strength_advantage_equal_fails(self):
        """동일 근력 → 강제 제압 실패 (strict greater)"""
        self._setup(player_str=5, partner_str=5)
        ok, reason = rc.check_physical_req(
            {"physical_req": {"strength_advantage": True}}, 2, 1)
        assert ok is False
        assert reason == "근력 부족"

    def test_min_strength_exact(self):
        """min_strength == player strength → 통과"""
        self._setup(player_str=10)
        ok, _ = rc.check_physical_req(
            {"physical_req": {"min_strength": 10}}, 2, 1)
        assert ok is True

    def test_min_strength_short(self):
        """min_strength > player → 실패"""
        self._setup(player_str=5)
        ok, reason = rc.check_physical_req(
            {"physical_req": {"min_strength": 10}}, 2, 1)
        assert ok is False
        assert "10" in reason


# ============================================
# get_conflicting_toggles (순수 함수)
# ============================================

class TestConflictingToggles:
    def test_same_exp_part_conflict(self):
        """같은 exp_part → 충돌"""
        # 같은 exp_part 토글 2개 찾기
        by_part = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            ep = tdef.get("exp_part")
            if ep:
                by_part.setdefault(ep, []).append(tid)
        # 충돌 가능한 쌍 찾기
        for part, ids in by_part.items():
            if len(ids) >= 2:
                new_id = ids[0]
                active = {ids[1]}
                conflicts = rc.get_conflicting_toggles(new_id, active)
                assert ids[1] in conflicts, \
                    f"Expected {ids[1]} to conflict with {new_id} on exp_part={part}"
                break

    def test_different_exp_part_no_conflict(self):
        """다른 exp_part → 비충돌"""
        parts = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            ep = tdef.get("exp_part")
            if ep and ep not in parts:
                parts[ep] = tid
            if len(parts) >= 2:
                break
        if len(parts) >= 2:
            ids = list(parts.values())
            conflicts = rc.get_conflicting_toggles(ids[0], {ids[1]})
            # 다른 부위이고 player_anatomy/mouth 충돌 없으면 비충돌
            d0 = TOGGLE_ACTIONS[ids[0]]
            d1 = TOGGLE_ACTIONS[ids[1]]
            if (not d0.get("uses_mouth") or not d1.get("uses_mouth")) and \
               (not d0.get("requires_player_anatomy") or
                d0.get("requires_player_anatomy") != d1.get("requires_player_anatomy")):
                assert ids[1] not in conflicts

    def test_none_exp_part_no_conflict(self):
        """exp_part=None 토글은 충돌하지 않음"""
        none_toggles = [tid for tid, tdef in TOGGLE_ACTIONS.items()
                        if tdef.get("exp_part") is None
                        and not tdef.get("uses_mouth")
                        and not tdef.get("requires_player_anatomy")]
        if none_toggles:
            # 아무 토글과도 exp_part 충돌 없어야
            any_toggle = list(TOGGLE_ACTIONS.keys())[0]
            active = {any_toggle}
            conflicts = rc.get_conflicting_toggles(none_toggles[0], active)
            # none exp_part 토글은 exp_part 기반 충돌 발생 안함
            # (단, player_anatomy나 mouth 충돌은 별개)

    def test_uses_mouth_conflict(self):
        """uses_mouth 양쪽 → 충돌"""
        mouth_toggles = [tid for tid, tdef in TOGGLE_ACTIONS.items()
                         if tdef.get("uses_mouth")]
        if len(mouth_toggles) >= 2:
            new_id = mouth_toggles[0]
            active = {mouth_toggles[1]}
            conflicts = rc.get_conflicting_toggles(new_id, active)
            assert mouth_toggles[1] in conflicts

    def test_player_anatomy_conflict(self):
        """같은 requires_player_anatomy → 충돌"""
        by_anatomy = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            req = tdef.get("requires_player_anatomy")
            if req:
                by_anatomy.setdefault(req, []).append(tid)
        for anatomy, ids in by_anatomy.items():
            if len(ids) >= 2:
                conflicts = rc.get_conflicting_toggles(ids[0], {ids[1]})
                assert ids[1] in conflicts, \
                    f"Expected anatomy conflict for {anatomy}"
                break

    def test_self_not_in_conflicts(self):
        """자기 자신은 충돌에 포함 안됨"""
        tid = list(TOGGLE_ACTIONS.keys())[0]
        conflicts = rc.get_conflicting_toggles(tid, {tid})
        assert tid not in conflicts

    def test_empty_active_no_conflicts(self):
        """활성 토글 없으면 충돌 없음"""
        tid = list(TOGGLE_ACTIONS.keys())[0]
        conflicts = rc.get_conflicting_toggles(tid, set())
        assert len(conflicts) == 0


# ============================================
# _remove_conflicting_toggles
# ============================================

class TestRemoveConflictingToggles:
    def test_removes_in_place(self):
        """충돌 토글 제거 (in-place)"""
        by_part = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            ep = tdef.get("exp_part")
            if ep:
                by_part.setdefault(ep, []).append(tid)
        for part, ids in by_part.items():
            if len(ids) >= 2:
                active = {ids[1]}
                removed = rc._remove_conflicting_toggles(ids[0], active)
                assert ids[1] in removed
                assert ids[1] not in active  # in-place 제거 확인
                break


# ============================================
# check_preparation (순수 함수)
# ============================================

class TestCheckPreparation:
    def test_low_intensity_always_true(self):
        """intensity < 3 → 항상 True"""
        stim_state = {"stim": {"V": 0}}
        action_def = {"intensity": 2, "exp_part": "음부"}
        assert rc.check_preparation(stim_state, action_def) is True

    def test_no_intensity_key_true(self):
        """intensity 키 없음 → 0 → True"""
        stim_state = {"stim": {"V": 0}}
        action_def = {"exp_part": "음부"}
        assert rc.check_preparation(stim_state, action_def) is True

    def test_high_intensity_stim_below_threshold(self):
        """intensity ≥ 3 + stim < threshold → False"""
        category = SENSATION_MAP.get("음부")
        if category:
            stim_state = {"stim": {category: PREPARATION_THRESHOLD - 1}}
            action_def = {"intensity": 3, "exp_part": "음부"}
            assert rc.check_preparation(stim_state, action_def) is False

    def test_high_intensity_stim_at_threshold(self):
        """intensity ≥ 3 + stim = threshold → True"""
        category = SENSATION_MAP.get("음부")
        if category:
            stim_state = {"stim": {category: PREPARATION_THRESHOLD}}
            action_def = {"intensity": 3, "exp_part": "음부"}
            assert rc.check_preparation(stim_state, action_def) is True

    def test_no_exp_part_always_true(self):
        """exp_part 없음 → True"""
        stim_state = {"stim": {}}
        action_def = {"intensity": 5}
        assert rc.check_preparation(stim_state, action_def) is True

    def test_unmapped_exp_part_true(self):
        """SENSATION_MAP에 없는 exp_part → True"""
        stim_state = {"stim": {}}
        action_def = {"intensity": 5, "exp_part": "nonexistent_part"}
        assert rc.check_preparation(stim_state, action_def) is True


# ============================================
# get_state_description (순수 함수)
# ============================================

class TestStateDescription:
    def test_high_stim_text(self):
        """stim ≥ 80 → high 텍스트"""
        stim_state = {"stim": {"V": 85}, "climax_gauge": 0}
        anatomy = {"V"}
        texts = rc.get_state_description(stim_state, anatomy)
        assert len(texts) >= 1
        assert "깊은 곳" in texts[0]  # _STIM_HIGH_TEXTS["V"]

    def test_mid_stim_text(self):
        """stim 50~79 → mid 텍스트"""
        stim_state = {"stim": {"B": 55}, "climax_gauge": 0}
        anatomy = {"B"}
        texts = rc.get_state_description(stim_state, anatomy)
        assert len(texts) >= 1
        assert "달아오르고" in texts[0]  # _STIM_MID_TEXTS["B"]

    def test_below_50_no_text(self):
        """stim < 50 → 묘사 없음"""
        stim_state = {"stim": {"M": 30}, "climax_gauge": 0}
        anatomy = {"M"}
        texts = rc.get_state_description(stim_state, anatomy)
        assert len(texts) == 0

    def test_max_2_lines(self):
        """최대 2줄 제한"""
        stim_state = {
            "stim": {"F": 90, "M": 90, "B": 90, "V": 90, "A": 90, "C": 90, "P": 90},
            "climax_gauge": 90,
        }
        anatomy = {"F", "M", "B", "V", "A", "C", "P"}
        texts = rc.get_state_description(stim_state, anatomy)
        assert len(texts) <= 2

    def test_anatomy_filter(self):
        """anatomy_set에 없는 카테고리 무시"""
        stim_state = {"stim": {"P": 90, "V": 90}, "climax_gauge": 0}
        anatomy = {"P"}  # V 미포함
        texts = rc.get_state_description(stim_state, anatomy)
        # P 텍스트만 있어야
        for t in texts:
            assert "깊은 곳" not in t  # V high text 없어야

    def test_climax_gauge_high(self):
        """climax_gauge ≥ 80 → 절정 접근 텍스트"""
        stim_state = {"stim": {}, "climax_gauge": 85}
        anatomy = set()
        texts = rc.get_state_description(stim_state, anatomy)
        assert any("절정" in t for t in texts)

    def test_climax_gauge_mid(self):
        """climax_gauge 50~79 → 자극 축적 텍스트"""
        stim_state = {"stim": {}, "climax_gauge": 60}
        anatomy = set()
        texts = rc.get_state_description(stim_state, anatomy)
        assert any("자극" in t for t in texts)

    def test_climax_gauge_low(self):
        """climax_gauge < 50 → 텍스트 없음"""
        stim_state = {"stim": {}, "climax_gauge": 30}
        anatomy = set()
        texts = rc.get_state_description(stim_state, anatomy)
        assert len(texts) == 0

    def test_order_follows_category_order(self):
        """카테고리 순서: F, M, B, A, V, C, P"""
        stim_state = {
            "stim": {"P": 80, "F": 80},
            "climax_gauge": 0,
        }
        anatomy = {"F", "P"}
        texts = rc.get_state_description(stim_state, anatomy)
        if len(texts) == 2:
            # F가 P보다 먼저
            assert "얼굴" in texts[0]


# ============================================
# _has_active_penetration (순수 함수)
# ============================================

class TestHasActivePenetration:
    def test_with_penetration(self):
        """삽입 토글 활성 → True"""
        if _THRUST_TOGGLE_IDS:
            tid = list(_THRUST_TOGGLE_IDS)[0]
            assert rc._has_active_penetration({tid}) is True

    def test_without_penetration(self):
        """삽입 토글 없음 → False"""
        assert rc._has_active_penetration(set()) is False

    def test_non_penetration_only(self):
        """비삽입 토글만 → False"""
        non_pen = set(TOGGLE_ACTIONS.keys()) - _THRUST_TOGGLE_IDS
        if non_pen:
            tid = list(non_pen)[0]
            assert rc._has_active_penetration({tid}) is False


# ============================================
# _has_active_intercourse_from_state (순수 함수)
# ============================================

class TestHasActiveIntercourse:
    def test_vaginal_insertion(self):
        """질 삽입 중 → True"""
        state = {"insertion": {"active": True, "orifice": "vaginal"}}
        assert rc._has_active_intercourse_from_state(state) is True

    def test_anal_insertion(self):
        """항문 삽입 → False (질 삽입만 True)"""
        state = {"insertion": {"active": True, "orifice": "anal"}}
        assert rc._has_active_intercourse_from_state(state) is False

    def test_empty_toggles(self):
        """삽입 없음 → falsy"""
        assert not rc._has_active_intercourse_from_state({})


# ============================================
# get_action_exp_part (순수 함수)
# ============================================

class TestGetActionExpPart:
    def test_from_dict(self):
        """action_dict에서 직접 조회"""
        assert rc.get_action_exp_part("x", {"exp_part": "가슴"}) == "가슴"

    def test_from_toggle_actions(self):
        """TOGGLE_ACTIONS에서 조회"""
        tid = list(TOGGLE_ACTIONS.keys())[0]
        expected = TOGGLE_ACTIONS[tid].get("exp_part")
        assert rc.get_action_exp_part(tid) == expected

    def test_from_instant_actions(self):
        """INSTANT_ACTIONS에서 조회"""
        aid = list(INSTANT_ACTIONS.keys())[0]
        expected = INSTANT_ACTIONS[aid].get("exp_part")
        assert rc.get_action_exp_part(aid) == expected

    def test_unknown_id(self):
        """존재하지 않는 ID → None"""
        assert rc.get_action_exp_part("nonexistent_action") is None


# ============================================
# calculate_stealth_chance (순수 함수)
# ============================================

class TestStealthChance:
    def test_base_chance(self):
        """기본 은신 확률 30%"""
        from romance_actions import STEALTH_BASE_CHANCE
        chance = rc.calculate_stealth_chance({})
        assert abs(chance - STEALTH_BASE_CHANCE) < 0.001

    def test_hiding_bonus(self):
        """은신 중 +40%"""
        from romance_actions import STEALTH_BASE_CHANCE, STEALTH_HIDING_BONUS
        chance = rc.calculate_stealth_chance({"hiding": True})
        expected = min(STEALTH_BASE_CHANCE + STEALTH_HIDING_BONUS, 0.9)
        assert abs(chance - expected) < 0.001

    def test_max_90(self):
        """최대 90%"""
        chance = rc.calculate_stealth_chance({"hiding": True})
        assert chance <= 0.9


# ============================================
# get_climax_reaction_key (순수 함수)
# ============================================

class TestClimaxReactionKey:
    def test_basic_ecstasy(self):
        """기본 fallback → 'ecstasy'"""
        climax_info = {"is_chain": False, "chain_count": 0, "category": "V"}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, {})
        assert result == "ecstasy"

    def test_category_specific(self):
        """ecstasy_{category} 존재 시"""
        climax_info = {"is_chain": False, "chain_count": 0, "category": "V"}
        reactions = {"ecstasy_V:start": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_V"

    def test_chain_generic(self):
        """연쇄 + ecstasy_chain 존재"""
        climax_info = {"is_chain": True, "chain_count": 1, "category": "B"}
        reactions = {"ecstasy_chain:start": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_chain"

    def test_chain_count_2(self):
        """chain_count ≥ 1 → ecstasy_chain_2"""
        climax_info = {"is_chain": True, "chain_count": 1, "category": "V"}
        reactions = {"ecstasy_chain_2:start": "...", "ecstasy_chain:start": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_chain_2"

    def test_chain_count_3(self):
        """chain_count ≥ 2 → ecstasy_chain_3"""
        climax_info = {"is_chain": True, "chain_count": 2, "category": "V"}
        reactions = {"ecstasy_chain_3:start": "...", "ecstasy_chain_2:start": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_chain_3"

    def test_chain_category_specific(self):
        """ecstasy_chain_{cat}"""
        climax_info = {"is_chain": True, "chain_count": 0, "category": "B"}
        reactions = {"ecstasy_chain_B:start": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_chain_B"

    def test_intercourse_priority(self):
        """삽입 중 절정 → ecstasy_intercourse (최우선)"""
        preg_toggles = [tid for tid, tdef in TOGGLE_ACTIONS.items()
                        if tdef.get("pregnancy_check")]
        if preg_toggles:
            climax_info = {"is_chain": True, "chain_count": 3, "category": "V"}
            reactions = {
                "ecstasy_intercourse:start": "...",
                "ecstasy_chain_3:start": "...",
            }
            result = rc.get_climax_reaction_key(
                climax_info, {preg_toggles[0]}, TOGGLE_ACTIONS, reactions)
            assert result == "ecstasy_intercourse"

    def test_intercourse_fallback(self):
        """삽입 중이지만 ecstasy_intercourse 미등록 → chain 우선"""
        preg_toggles = [tid for tid, tdef in TOGGLE_ACTIONS.items()
                        if tdef.get("pregnancy_check")]
        if preg_toggles:
            climax_info = {"is_chain": True, "chain_count": 1, "category": "V"}
            reactions = {"ecstasy_chain_2:start": "..."}
            result = rc.get_climax_reaction_key(
                climax_info, {preg_toggles[0]}, TOGGLE_ACTIONS, reactions)
            assert result == "ecstasy_chain_2"

    def test_has_key_checks_both_forms(self):
        """_has_key는 'key:start'와 'key' 모두 체크"""
        climax_info = {"is_chain": False, "chain_count": 0, "category": "V"}
        # key 직접 존재
        reactions = {"ecstasy_V": "..."}
        result = rc.get_climax_reaction_key(climax_info, set(), TOGGLE_ACTIONS, reactions)
        assert result == "ecstasy_V"


# ============================================
# 관계 Prop 키 생성 (mock 기반)
# ============================================

class TestRelationshipKeys:
    def test_affection_key(self):
        morld.register_unit(1, name="주인공")
        key = rc.get_affection_key(1)
        assert key == "관계:주인공:호감"

    def test_rebellion_key(self):
        morld.register_unit(1, name="A")
        assert rc.get_rebellion_key(1) == "관계:A:반발"

    def test_submission_key(self):
        morld.register_unit(1, name="A")
        assert rc.get_submission_key(1) == "관계:A:복종"

    def test_missing_unit_fallback(self):
        """유닛 미등록 → '주인공' 기본값"""
        key = rc.get_affection_key(999)
        assert key == "관계:주인공:호감"


# ============================================
# 정액 시스템 (mock 기반)
# ============================================

class TestSemenSystem:
    def test_semen_total_zero(self):
        """초기 상태 → 정액 합산 0"""
        morld.register_unit(10, props={})
        assert rc.get_semen_total(10) == 0

    def test_semen_total_sum(self):
        """부위별 정액 합산"""
        props = {}
        for i, p in enumerate(SEMEN_PARTS):
            props[f"오염물:정액:{p}"] = 10 + i
        morld.register_unit(10, props=props)
        expected = sum(10 + i for i in range(len(SEMEN_PARTS)))
        assert rc.get_semen_total(10) == expected

    def test_apply_semen(self):
        """정액 적용"""
        morld.register_unit(10, props={})
        rc._apply_semen(10, SEMEN_PARTS[0], 30)
        prop_key = f"오염물:정액:{SEMEN_PARTS[0]}"
        assert morld.get_unit_prop(10, prop_key) == 30

    def test_apply_semen_clamp_100(self):
        """정액 상한 100"""
        morld.register_unit(10, props={f"오염물:정액:{SEMEN_PARTS[0]}": 80})
        rc._apply_semen(10, SEMEN_PARTS[0], 50)
        assert morld.get_unit_prop(10, f"오염물:정액:{SEMEN_PARTS[0]}") == 100

    def test_clear_all_semen(self):
        """전부위 정액 제거"""
        props = {f"오염물:정액:{p}": 50 for p in SEMEN_PARTS}
        props.update({f"체내:정액:{p}": 50 for p in INTERNAL_SEMEN_PARTS})
        morld.register_unit(10, props=props)
        rc.clear_all_semen(10)
        for p in SEMEN_PARTS:
            assert morld.get_unit_prop(10, f"오염물:정액:{p}") is None
        for p in INTERNAL_SEMEN_PARTS:
            assert morld.get_unit_prop(10, f"체내:정액:{p}") is None

    def test_internal_semen(self):
        """체내 정액 조회"""
        morld.register_unit(10, props={f"체내:정액:{INTERNAL_SEMEN_PARTS[0]}": 25})
        assert rc.get_internal_semen(10, INTERNAL_SEMEN_PARTS[0]) == 25

    def test_internal_semen_total(self):
        """체내 정액 합산"""
        props = {f"체내:정액:{p}": 10 for p in INTERNAL_SEMEN_PARTS}
        morld.register_unit(10, props=props)
        assert rc.get_internal_semen_total(10) == 10 * len(INTERNAL_SEMEN_PARTS)

    def test_apply_internal_semen(self):
        """체내 정액 적용 + 상한"""
        from romance_actions import INTERNAL_SEMEN_MAX
        morld.register_unit(10, props={})
        rc._apply_internal_semen(10, INTERNAL_SEMEN_PARTS[0], INTERNAL_SEMEN_MAX + 50)
        assert morld.get_unit_prop(10, f"체내:정액:{INTERNAL_SEMEN_PARTS[0]}") == INTERNAL_SEMEN_MAX

    def test_clear_all_internal_semen(self):
        """체내 정액 전체 제거"""
        props = {f"체내:정액:{p}": 30 for p in INTERNAL_SEMEN_PARTS}
        morld.register_unit(10, props=props)
        rc.clear_all_internal_semen(10)
        for p in INTERNAL_SEMEN_PARTS:
            assert morld.get_unit_prop(10, f"체내:정액:{p}") is None


# ============================================
# calculate_ejaculation_amount (mock 기반)
# ============================================

class TestEjaculationAmount:
    def test_base_amount(self):
        """기본 사정량 (P 경험 0, 체력 5)"""
        morld.register_unit(10, props={})
        amount = rc.calculate_ejaculation_amount(10, 5)
        # base + p_sensation(0)*3 + stamina(5)*2 = base + 0 + 10
        expected = SEMEN_AMOUNT_BASE + 10
        assert amount == max(SEMEN_AMOUNT_MIN, min(SEMEN_AMOUNT_MAX, expected))

    def test_with_p_sensation(self):
        """P 감각 보너스"""
        p_parts = [p for p, c in SENSATION_MAP.items() if c == "P"]
        if p_parts:
            # sqrt(48/3) = sqrt(16) = 4
            morld.register_unit(10, props={f"경험:{p_parts[0]}": 48})
            amount = rc.calculate_ejaculation_amount(10, 5)
            # base + 4*3 + 5*2 = base + 12 + 10
            expected = SEMEN_AMOUNT_BASE + 12 + 10
            assert amount == max(SEMEN_AMOUNT_MIN, min(SEMEN_AMOUNT_MAX, expected))

    def test_clamp_min(self):
        """최소값 클램프"""
        morld.register_unit(10, props={})
        amount = rc.calculate_ejaculation_amount(10, 0)
        assert amount >= SEMEN_AMOUNT_MIN

    def test_clamp_max(self):
        """최대값 클램프"""
        p_parts = [p for p, c in SENSATION_MAP.items() if c == "P"]
        if p_parts:
            morld.register_unit(10, props={f"경험:{p_parts[0]}": 500})
            amount = rc.calculate_ejaculation_amount(10, 100, 100)
            assert amount <= SEMEN_AMOUNT_MAX

    def test_max_stamina_normalization(self):
        """max_stamina > 10 → 정규화"""
        morld.register_unit(10, props={})
        # stamina=50, max=100 → normalized = 5.0
        amount1 = rc.calculate_ejaculation_amount(10, 50, 100)
        # stamina=5, max=None → normalized = 5
        morld.register_unit(10, props={})
        amount2 = rc.calculate_ejaculation_amount(10, 5)
        assert amount1 == amount2


# ============================================
# check_and_clear_virginity (mock 기반)
# ============================================

class TestVirginityCheck:
    def test_no_virginity_action(self):
        """처녀 해제 액션이 아님 → None"""
        morld.register_unit(10, props={})
        morld.register_unit(1, name="주인공")
        result = rc.check_and_clear_virginity(10, 1, "kiss")
        assert result is None

    def test_clear_virginity(self):
        """처녀 해제 성공"""
        if VIRGINITY_CLEARING_ACTIONS:
            action_id = list(VIRGINITY_CLEARING_ACTIONS.keys())[0]
            virginity_prop = VIRGINITY_CLEARING_ACTIONS[action_id]
            morld.register_unit(1, name="주인공")
            morld.register_unit(10, props={
                virginity_prop: 1,
                "관계:주인공:호감": 50,
            })
            result = rc.check_and_clear_virginity(10, 1, action_id)
            assert result == f"first_{action_id}"
            # 처녀 해제됨
            assert morld.get_unit_prop(10, virginity_prop) == 0
            # 호감 보너스
            assert morld.get_unit_prop(10, "관계:주인공:호감") == 50 + VIRGINITY_BONUS_AFFECTION

    def test_already_cleared(self):
        """이미 해제됨 → None"""
        if VIRGINITY_CLEARING_ACTIONS:
            action_id = list(VIRGINITY_CLEARING_ACTIONS.keys())[0]
            virginity_prop = VIRGINITY_CLEARING_ACTIONS[action_id]
            morld.register_unit(1, name="주인공")
            morld.register_unit(10, props={virginity_prop: 0})
            result = rc.check_and_clear_virginity(10, 1, action_id)
            assert result is None


# ============================================
# get_excitement_level (mock 기반)
# ============================================

class TestExcitementLevel:
    def test_low(self):
        """성욕 < 35 → 0"""
        morld.register_unit(10, props={"상태:성욕": 20})
        assert rc.get_excitement_level(10) == 0

    def test_mid(self):
        """성욕 35~69 → 1"""
        morld.register_unit(10, props={"상태:성욕": 50})
        assert rc.get_excitement_level(10) == 1

    def test_high(self):
        """성욕 ≥ 70 → 2"""
        morld.register_unit(10, props={"상태:성욕": 80})
        assert rc.get_excitement_level(10) == 2

    def test_boundary_35(self):
        """경계값 35 → 1"""
        morld.register_unit(10, props={"상태:성욕": 35})
        assert rc.get_excitement_level(10) == 1

    def test_boundary_70(self):
        """경계값 70 → 2"""
        morld.register_unit(10, props={"상태:성욕": 70})
        assert rc.get_excitement_level(10) == 2

    def test_no_arousal_prop(self):
        """성욕 prop 없음 → 0"""
        morld.register_unit(10, props={})
        assert rc.get_excitement_level(10) == 0


# ============================================
# is_pull_out_available (순수 함수 + stim)
# ============================================

class TestPullOutAvailable:
    def test_no_penetration(self):
        """삽입 없음 → False"""
        state = {"active_toggles": set(), "stim": {"stim": {"P": 100}}}
        assert rc.is_pull_out_available(state) is False

    def test_penetration_low_stim(self):
        """삽입 중이지만 P stim 미달 → False"""
        if _THRUST_TOGGLE_IDS:
            # pregnancy_check 가진 토글 찾기
            preg_id = None
            for tid in _THRUST_TOGGLE_IDS:
                if TOGGLE_ACTIONS[tid].get("pregnancy_check"):
                    preg_id = tid
                    break
            if preg_id:
                state = {
                    "active_toggles": {preg_id},
                    "stim": {"stim": {"P": PULL_OUT_STIM_THRESHOLD - 1}},
                }
                assert rc.is_pull_out_available(state) is False

    def test_penetration_stim_met(self):
        """삽입 중 + P stim ≥ threshold → True"""
        if _THRUST_TOGGLE_IDS:
            preg_id = None
            for tid in _THRUST_TOGGLE_IDS:
                if TOGGLE_ACTIONS[tid].get("pregnancy_check"):
                    preg_id = tid
                    break
            if preg_id:
                state = {
                    "active_toggles": {preg_id},
                    "stim": {"stim": {"P": PULL_OUT_STIM_THRESHOLD}},
                }
                assert rc.is_pull_out_available(state) is True


# ============================================
# is_hold_back_available
# ============================================

class TestHoldBackAvailable:
    def test_no_stim(self):
        """stim 없음 → False"""
        assert rc.is_hold_back_available({}) is False

    def test_no_peaked(self):
        """peaked 없음 → False"""
        s = stim_mod.create_state()
        assert rc.is_hold_back_available({"stim": s}) is False

    def test_peaked_no_gauge(self):
        """peaked 있지만 gauge 0 → False"""
        s = stim_mod.create_state()
        s["stim"]["F"] = 100
        # gauge는 0이므로 False
        assert rc.is_hold_back_available({"stim": s}) is False

    def test_peaked_with_gauge(self):
        """peaked + gauge > 0 → True"""
        s = stim_mod.create_state()
        s["stim"]["F"] = 100
        s["climax_gauge"] = 50
        assert rc.is_hold_back_available({"stim": s}) is True


# ============================================
# extract_preserved (순수 함수)
# ============================================

class TestExtractPreserved:
    def test_basic_extraction(self):
        """기본 상태 추출"""
        state = {
            "stim": {"stim": {}},
            "stamina": 80,
            "initial_stamina": 100,
            "max_stamina": 100,
            "elapsed_time": 5000,
            "checked_npcs": {3, 4},
            "lubricated": True,
            "position": "cowgirl",
            "condom_active": True,
            "condom_punctured": False,
            "condom_removed_in_trance": False,
        }
        p = rc.extract_preserved(state)
        assert p["stim"] == state["stim"]
        assert p["stamina"] == 80
        assert p["initial_stamina"] == 100
        assert p["max_stamina"] == 100
        assert p["elapsed_time"] == 5000
        assert p["checked_npcs"] == {3, 4}
        assert p["lubricated"] is True
        assert p["schedule_pushed"] is True
        assert p["position"] == "cowgirl"
        assert p["condom_active"] is True

    def test_defaults(self):
        """누락 키에 기본값 사용"""
        state = {
            "stim": {},
            "stamina": 50,
            "elapsed_time": 0,
        }
        p = rc.extract_preserved(state)
        assert p["initial_stamina"] == 50  # stamina 기본값
        assert p["max_stamina"] == 100
        assert p["checked_npcs"] == set()
        assert p["lubricated"] is False
        assert p["position"] == "missionary"
        assert p["condom_active"] is False

    def test_mode_ctx_preserved(self):
        """mode_ctx 존재 시 보존"""
        state = {
            "stim": {},
            "stamina": 50,
            "elapsed_time": 0,
            "mode_ctx": {"mode": "forced"},
        }
        p = rc.extract_preserved(state)
        assert p["mode_ctx"]["mode"] == "forced"

    def test_mode_ctx_absent(self):
        """mode_ctx 없으면 키 자체 없음"""
        state = {
            "stim": {},
            "stamina": 50,
            "elapsed_time": 0,
        }
        p = rc.extract_preserved(state)
        assert "mode_ctx" not in p


# ============================================
# get_insertion_exp_part (순수 함수)
# ============================================

class TestPenetrationExpPart:
    def test_vaginal(self):
        """질 삽입 → '음부'"""
        state = {"insertion": {"active": True, "orifice": "vaginal"}}
        assert rc.get_insertion_exp_part(state) == "음부"

    def test_anal(self):
        """항문 삽입 → '엉덩이'"""
        state = {"insertion": {"active": True, "orifice": "anal"}}
        assert rc.get_insertion_exp_part(state) == "엉덩이"

    def test_no_match(self):
        """삽입 없음 → None"""
        assert rc.get_insertion_exp_part({}) is None

    def test_inactive(self):
        """삽입 비활성 → None"""
        state = {"insertion": {"active": False, "orifice": "vaginal"}}
        assert rc.get_insertion_exp_part(state) is None
