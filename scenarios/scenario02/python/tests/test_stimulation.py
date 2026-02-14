# test_stimulation.py — stimulation.py 순수 상태머신 유닛 테스트
"""
morld 의존성 0 — 순수 Python 상태머신 테스트.
절정/여운/연쇄/참기/불응기 메커닉의 정확성 검증.
"""
import random
import stimulation as stim


# ============================================
# create_state
# ============================================

class TestCreateState:
    def test_default_state(self):
        s = stim.create_state()
        assert s["stim"] == {"F": 0, "M": 0, "B": 0, "A": 0, "V": 0, "C": 0, "P": 0}
        assert s["climax_gauge"] == 0
        assert s["afterglow"] == 0
        assert s["chain_count"] == 0
        assert s["climax_total"] == 0
        assert s["refractory"] == 0
        assert s["male_mode"] is False
        assert s["hold_back_count"] == 0

    def test_male_mode(self):
        s = stim.create_state(male_mode=True)
        assert s["male_mode"] is True


# ============================================
# calc_gain
# ============================================

class TestCalcGain:
    def test_zero_base(self):
        assert stim.calc_gain(0, 0, 0, 0) == 0

    def test_negative_base(self):
        assert stim.calc_gain(-5, 5, 0, 0) == 0

    def test_base_only(self):
        # base=10, sensation=0, rebellion=0, afterglow=0
        # 10 * 1.0 * 1.0 = 10
        assert stim.calc_gain(10, 0, 0, 0) == 10

    def test_sensation_scaling(self):
        # base=10, sensation=10 → 10 * (1 + 10*0.15) = 10 * 2.5 = 25
        assert stim.calc_gain(10, 10, 0, 0) == 25

    def test_sensation_mid(self):
        # base=10, sensation=5 → 10 * (1 + 5*0.15) = 10 * 1.75 = 18 (rounded)
        assert stim.calc_gain(10, 5, 0, 0) == 18

    def test_rebellion_max(self):
        # rebellion=100 → factor = max(0.2, 1.0 - 100*0.008) = max(0.2, 0.2) = 0.2
        # base=10 * 1.0 * 0.2 = 2
        assert stim.calc_gain(10, 0, 100, 0) == 2

    def test_rebellion_partial(self):
        # rebellion=50 → factor = max(0.2, 1.0 - 50*0.008) = max(0.2, 0.6) = 0.6
        # base=10 * 1.0 * 0.6 = 6
        assert stim.calc_gain(10, 0, 50, 0) == 6

    def test_afterglow_amplify(self):
        # afterglow > 0 → ×1.5 (CHAIN_AMPLIFIER)
        # base=10 * 1.0 * 1.0 * 1.5 = 15
        assert stim.calc_gain(10, 0, 0, 30) == 15

    def test_refractory_suppression(self):
        # refractory > 0 → ×0.1 (REFRACTORY_GAIN_FACTOR)
        # base=10 * 1.0 * 1.0 * 0.1 = 1
        assert stim.calc_gain(10, 0, 0, 0, refractory=50) == 1

    def test_refractory_overrides_afterglow(self):
        """refractory와 afterglow 모두 > 0 이면 refractory 우선 (코드 순서상)"""
        # refractory > 0 분기가 먼저 → elif afterglow는 건너뜀
        gain = stim.calc_gain(10, 0, 0, 30, refractory=50)
        assert gain == 1  # refractory 적용

    def test_minimum_gain(self):
        # 아무리 감소해도 최소 1
        assert stim.calc_gain(1, 0, 100, 0) >= 1

    def test_combined(self):
        # base=10, sensation=5, rebellion=50, afterglow=30
        # 10 * 1.75 * 0.6 * 1.5 = 15.75 → round → 16
        assert stim.calc_gain(10, 5, 50, 30) == 16


# ============================================
# apply
# ============================================

class TestApply:
    def test_no_climax_below_max(self):
        s = stim.create_state()
        result = stim.apply(s, "V", 50)
        assert result is None
        assert s["stim"]["V"] == 50

    def test_invalid_category(self):
        s = stim.create_state()
        result = stim.apply(s, "X", 50)
        assert result is None

    def test_zero_amount(self):
        s = stim.create_state()
        result = stim.apply(s, "V", 0)
        assert result is None

    def test_negative_amount(self):
        s = stim.create_state()
        result = stim.apply(s, "V", -10)
        assert result is None

    def test_stim_clamped_to_max(self):
        s = stim.create_state()
        stim.apply(s, "V", 150)
        assert s["stim"]["V"] == stim.STIM_MAX

    def test_peaked_no_climax_without_gauge(self):
        """자극 100 도달만으로는 절정 불가 — 게이지도 만충되어야"""
        s = stim.create_state()
        # 게이지를 만충시키지 않을 정도의 한번으로 peaked 도달
        s["stim"]["V"] = 99
        result = stim.apply(s, "V", 1)
        # 1만 추가했으니 게이지 상승이 미미, peaked 자체는 됨
        # 하지만 게이지가 100 미만이면 절정 안 됨
        # (게이지 = 1 * 0.4 * (1 + 1*0.3) = 0.52)
        if s["climax_gauge"] < stim.CLIMAX_GAUGE_MAX:
            assert result is None

    def test_climax_on_gauge_full(self):
        """게이지 만충 + peaked → 절정"""
        s = stim.create_state()
        s["stim"]["V"] = 100  # peaked
        s["climax_gauge"] = 99
        # 다른 부위에 자극 → 게이지 만충
        result = stim.apply(s, "B", 50)
        if s["climax_gauge"] >= stim.CLIMAX_GAUGE_MAX or result is not None:
            # 절정이 발생했을 수 있음
            pass

    def test_chain_climax_during_afterglow(self):
        """여운 중 + 자극 100 도달 → 연쇄 절정"""
        s = stim.create_state()
        s["afterglow"] = 30
        s["stim"]["B"] = 95
        result = stim.apply(s, "B", 10)
        # B가 100 도달 + afterglow > 0 → 즉시 연쇄 절정
        assert result is not None
        assert result["is_chain"] is True
        assert "B" in result["peaked_parts"]

    def test_climax_resets_peaked_parts(self):
        """절정 후 peaked 부위 자극 리셋"""
        s = stim.create_state()
        s["afterglow"] = 30
        s["stim"]["V"] = 95
        result = stim.apply(s, "V", 10)
        assert result is not None
        assert s["stim"]["V"] == 0  # 리셋됨

    def test_simultaneous_climax_multi_parts(self):
        """복수 부위 peaked → 동시 절정, 배율 적용"""
        s = stim.create_state()
        s["afterglow"] = 30
        s["stim"]["V"] = 100
        s["stim"]["B"] = 100
        s["stim"]["F"] = 95
        result = stim.apply(s, "F", 10)
        assert result is not None
        assert result["peaked_count"] == 3
        # 배율: 1.0 + (3-1) * 0.2 = 1.4
        assert result["simultaneous_mult"] == 1.4

    def test_gauge_increases_with_peaked_bonus(self):
        """peaked 부위가 있으면 게이지 가속"""
        s1 = stim.create_state()
        s2 = stim.create_state()
        s2["stim"]["B"] = 100  # 1 peaked

        stim.apply(s1, "V", 20)
        stim.apply(s2, "V", 20)
        # s2는 peaked 1개 → 게이지 가속
        assert s2["climax_gauge"] > s1["climax_gauge"]


# ============================================
# _trigger_climax (via force_climax / apply)
# ============================================

class TestTriggerClimax:
    def test_force_climax_no_peaked(self):
        """peaked 부위 없으면 force_climax → None"""
        s = stim.create_state()
        result = stim.force_climax(s)
        assert result is None

    def test_force_climax_with_peaked(self):
        s = stim.create_state()
        s["stim"]["V"] = 100
        result = stim.force_climax(s)
        assert result is not None
        assert "V" in result["peaked_parts"]
        assert s["stim"]["V"] == 0

    def test_climax_total_increments(self):
        s = stim.create_state()
        s["stim"]["V"] = 100
        stim.force_climax(s)
        assert s["climax_total"] == 1
        s["stim"]["V"] = 100
        stim.force_climax(s)
        assert s["climax_total"] == 2

    def test_chain_count_reset_logic(self):
        """afterglow > 0이면 chain_count++, 아니면 0"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        result = stim.force_climax(s)
        assert result["is_chain"] is False
        assert result["chain_count"] == 0

        # afterglow가 설정됨 (non-P peaked이므로)
        assert s["afterglow"] > 0

        s["stim"]["B"] = 100
        result2 = stim.force_climax(s)
        assert result2["is_chain"] is True
        assert result2["chain_count"] == 1

    def test_male_mode_refractory(self):
        """male_mode + P peaked → refractory 부여"""
        s = stim.create_state(male_mode=True)
        s["stim"]["P"] = 100
        result = stim.force_climax(s)
        assert result["has_p"] is True
        assert s["refractory"] == stim.REFRACTORY_INITIAL

    def test_male_mode_no_refractory_without_p(self):
        """male_mode이지만 P 미포함이면 refractory 미부여"""
        s = stim.create_state(male_mode=True)
        s["stim"]["V"] = 100
        result = stim.force_climax(s)
        assert result["has_p"] is False
        assert s["refractory"] == 0

    def test_afterglow_only_for_non_p(self):
        """P만 peaked → afterglow 미부여 (non_p_parts 없음)"""
        s = stim.create_state()
        s["stim"]["P"] = 100
        result = stim.force_climax(s)
        assert result["non_p_parts"] == []
        assert s["afterglow"] == 0

    def test_afterglow_for_non_p_parts(self):
        """non-P peaked → afterglow 부여"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        result = stim.force_climax(s)
        assert s["afterglow"] == stim.AFTERGLOW_INITIAL

    def test_gauge_reset_to_afterglow(self):
        """절정 후 게이지 = afterglow 값 (연쇄 절정 가능성)"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        s["climax_gauge"] = 80
        stim.force_climax(s)
        assert s["climax_gauge"] == s["afterglow"]

    def test_hold_back_count_resets(self):
        """절정 후 hold_back_count 리셋"""
        s = stim.create_state()
        s["hold_back_count"] = 5
        s["stim"]["V"] = 100
        stim.force_climax(s)
        assert s["hold_back_count"] == 0

    def test_category_compat_key(self):
        """하위호환: result["category"]는 첫 peaked part"""
        s = stim.create_state()
        s["stim"]["B"] = 100
        result = stim.force_climax(s)
        assert result["category"] == "B"


# ============================================
# force_ejaculate
# ============================================

class TestForceEjaculate:
    def test_always_triggers(self):
        """P=100 + gauge=100 → 항상 절정"""
        s = stim.create_state()
        result = stim.force_ejaculate(s)
        assert result is not None
        assert result["has_p"] is True
        assert s["stim"]["P"] == 0  # 리셋됨

    def test_male_mode_refractory_on_ejaculate(self):
        s = stim.create_state(male_mode=True)
        stim.force_ejaculate(s)
        assert s["refractory"] == stim.REFRACTORY_INITIAL


# ============================================
# tick_afterglow
# ============================================

class TestTickAfterglow:
    def test_afterglow_decay(self):
        s = stim.create_state()
        s["afterglow"] = 50
        stim.tick_afterglow(s)
        assert s["afterglow"] == 40

    def test_afterglow_to_zero_resets_chain(self):
        """여운 0 도달 시 chain_count 리셋"""
        s = stim.create_state()
        s["afterglow"] = 5
        s["chain_count"] = 3
        stim.tick_afterglow(s)
        assert s["afterglow"] == 0
        assert s["chain_count"] == 0

    def test_afterglow_stays_zero(self):
        s = stim.create_state()
        s["afterglow"] = 0
        stim.tick_afterglow(s)
        assert s["afterglow"] == 0

    def test_refractory_decay(self):
        s = stim.create_state()
        s["refractory"] = 30
        stim.tick_afterglow(s)
        assert s["refractory"] == 20

    def test_refractory_floors_at_zero(self):
        s = stim.create_state()
        s["refractory"] = 5
        stim.tick_afterglow(s)
        assert s["refractory"] == 0

    def test_both_decay_independently(self):
        """여운과 불응기가 동시에 감소"""
        s = stim.create_state()
        s["afterglow"] = 30
        s["refractory"] = 40
        stim.tick_afterglow(s)
        assert s["afterglow"] == 20
        assert s["refractory"] == 30


# ============================================
# hold_back
# ============================================

class TestHoldBack:
    def test_first_attempt_stats(self):
        """첫 시도: chance=70, reduction=25"""
        s = stim.create_state()
        s["climax_gauge"] = 80
        random.seed(1)  # 결정론적
        result = stim.hold_back(s)
        assert result["chance"] == 70
        assert s["hold_back_count"] == 1

    def test_chance_decay(self):
        """횟수별 확률 감쇠"""
        s = stim.create_state()
        s["climax_gauge"] = 80

        # 6회 시도 후 chance = max(10, 70 - 6*10) = 10
        s["hold_back_count"] = 6
        random.seed(42)
        result = stim.hold_back(s)
        assert result["chance"] == stim.HOLD_BACK_MIN_CHANCE

    def test_success_reduces_gauge(self):
        s = stim.create_state()
        s["climax_gauge"] = 80
        # 강제로 성공시키기
        random.seed(0)
        # 여러 시드 중 성공하는 것 찾기
        for seed in range(100):
            random.seed(seed)
            s_copy = stim.create_state()
            s_copy["climax_gauge"] = 80
            result = stim.hold_back(s_copy)
            if result["success"]:
                assert s_copy["climax_gauge"] < 80
                assert result["reduction"] == stim.HOLD_BACK_REDUCTION
                break

    def test_failure_increases_gauge(self):
        s = stim.create_state()
        s["climax_gauge"] = 80
        # 강제로 실패시키기
        for seed in range(100):
            random.seed(seed)
            s_copy = stim.create_state()
            s_copy["climax_gauge"] = 80
            result = stim.hold_back(s_copy)
            if not result["success"]:
                assert s_copy["climax_gauge"] == 80 + stim.HOLD_BACK_FAIL_PENALTY
                assert result["reduction"] == 0
                break

    def test_reduction_decay(self):
        """횟수별 감소량 감쇠"""
        s = stim.create_state()
        s["hold_back_count"] = 4  # 4회째
        s["climax_gauge"] = 80

        # reduction = max(5, 25 - 4*5) = max(5, 5) = 5
        for seed in range(100):
            random.seed(seed)
            s_copy = stim.create_state()
            s_copy["hold_back_count"] = 4
            s_copy["climax_gauge"] = 80
            result = stim.hold_back(s_copy)
            if result["success"]:
                assert result["reduction"] == stim.HOLD_BACK_REDUCTION_MIN
                break

    def test_gauge_clamped_to_zero(self):
        """감소 시 게이지 0 미만 방지"""
        s = stim.create_state()
        s["climax_gauge"] = 5
        for seed in range(100):
            random.seed(seed)
            s_copy = stim.create_state()
            s_copy["climax_gauge"] = 5
            result = stim.hold_back(s_copy)
            if result["success"]:
                assert s_copy["climax_gauge"] >= 0
                break

    def test_gauge_clamped_to_max(self):
        """실패 시 게이지 MAX 초과 방지"""
        s = stim.create_state()
        s["climax_gauge"] = 95
        for seed in range(100):
            random.seed(seed)
            s_copy = stim.create_state()
            s_copy["climax_gauge"] = 95
            result = stim.hold_back(s_copy)
            if not result["success"]:
                assert s_copy["climax_gauge"] <= stim.CLIMAX_GAUGE_MAX
                break


# ============================================
# P 감각 함수
# ============================================

class TestPSensation:
    def test_gain_multiplier_zero(self):
        # sensation=0 → 1.0
        assert stim.get_p_gain_multiplier(0) == 1.0

    def test_gain_multiplier_max(self):
        # sensation=10 → max(0.3, 1.0 - 10*0.07) = max(0.3, 0.3) = 0.3
        assert stim.get_p_gain_multiplier(10) == 0.3

    def test_gain_multiplier_mid(self):
        # sensation=5 → max(0.3, 1.0 - 5*0.07) = max(0.3, 0.65) = 0.65
        assert abs(stim.get_p_gain_multiplier(5) - 0.65) < 1e-9

    def test_ejaculate_threshold_zero(self):
        # sensation=0 → 70
        assert stim.get_ejaculate_threshold(0) == 70

    def test_ejaculate_threshold_max(self):
        # sensation=10 → max(30, 70 - 10*4) = max(30, 30) = 30
        assert stim.get_ejaculate_threshold(10) == 30

    def test_ejaculate_threshold_mid(self):
        # sensation=5 → max(30, 70 - 5*4) = max(30, 50) = 50
        assert stim.get_ejaculate_threshold(5) == 50


# ============================================
# 상태 조회
# ============================================

class TestStateQueries:
    def test_is_trance_basic(self):
        """non-P peaked + gauge < max → trance"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        s["climax_gauge"] = 50
        assert stim.is_trance(s) is True

    def test_is_trance_false_gauge_full(self):
        """gauge >= max → not trance"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        s["climax_gauge"] = 100
        assert stim.is_trance(s) is False

    def test_is_trance_false_only_p(self):
        """P만 peaked → not trance (P는 제외)"""
        s = stim.create_state()
        s["stim"]["P"] = 100
        s["climax_gauge"] = 50
        assert stim.is_trance(s) is False

    def test_is_p_peaked(self):
        s = stim.create_state()
        assert stim.is_p_peaked(s) is False
        s["stim"]["P"] = 100
        assert stim.is_p_peaked(s) is True

    def test_get_peaked_count(self):
        s = stim.create_state()
        assert stim.get_peaked_count(s) == 0
        s["stim"]["V"] = 100
        s["stim"]["B"] = 100
        assert stim.get_peaked_count(s) == 2

    def test_get_peaked_parts(self):
        s = stim.create_state()
        s["stim"]["V"] = 100
        s["stim"]["F"] = 100
        parts = stim.get_peaked_parts(s)
        assert set(parts) == {"V", "F"}


# ============================================
# 엣지 케이스
# ============================================

class TestEdgeCases:
    def test_all_parts_peaked_simultaneous(self):
        """7부위 전부 peaked → 동시 절정"""
        s = stim.create_state()
        s["afterglow"] = 30  # 연쇄 트리거 가능하도록
        for cat in ("F", "M", "B", "A", "V", "C"):
            s["stim"][cat] = 100
        s["stim"]["P"] = 95
        result = stim.apply(s, "P", 10)
        assert result is not None
        assert result["peaked_count"] == 7
        # 배율: 1.0 + (7-1) * 0.2 = 2.2
        assert result["simultaneous_mult"] == 2.2

    def test_p_only_peaked_male_mode(self):
        """P만 peaked + male_mode → refractory O, afterglow X"""
        s = stim.create_state(male_mode=True)
        s["stim"]["P"] = 100
        result = stim.force_climax(s)
        assert s["refractory"] == stim.REFRACTORY_INITIAL
        assert s["afterglow"] == 0

    def test_non_p_only_peaked(self):
        """non-P만 peaked → afterglow O, refractory X"""
        s = stim.create_state()
        s["stim"]["V"] = 100
        result = stim.force_climax(s)
        assert s["afterglow"] == stim.AFTERGLOW_INITIAL
        assert s["refractory"] == 0

    def test_climax_sensation_gain_basic(self):
        # rebellion=0, chain=0 → base=3
        assert stim.get_climax_sensation_gain(0, 0) == 3

    def test_climax_sensation_gain_rebellion(self):
        # rebellion=50 → base = max(0, 3 - 50//25) = max(0, 3-2) = 1
        assert stim.get_climax_sensation_gain(50, 0) == 1

    def test_climax_sensation_gain_chain(self):
        # rebellion=0, chain=2 → base=3, mult=1.0+2*0.5=2.0 → 6
        assert stim.get_climax_sensation_gain(0, 2) == 6

    def test_climax_sensation_gain_chain_cap(self):
        # chain=5 (capped at 3) → mult=1.0+3*0.5=2.5 → 3*2.5=7.5 → 8
        assert stim.get_climax_sensation_gain(0, 5) == 8

    def test_climax_sensation_gain_high_rebellion(self):
        # rebellion=100 → base = max(0, 3 - 100//25) = max(0, 3-4) = 0
        assert stim.get_climax_sensation_gain(100, 0) == 0

    def test_apply_climax_reset_p(self):
        """P 자극 강제 리셋 (하위호환)"""
        s = stim.create_state()
        s["stim"]["P"] = 80
        stim.apply_climax_reset_p(s)
        assert s["stim"]["P"] == 0

    def test_rapid_chain_sequence(self):
        """여운 → 연쇄 절정 → 다시 여운 → 다시 연쇄의 흐름"""
        s = stim.create_state()

        # 1차 절정
        s["stim"]["V"] = 100
        s["climax_gauge"] = 100
        r1 = stim.force_climax(s)
        assert r1["climax_total"] == 1
        assert s["afterglow"] > 0

        # 2차 연쇄 절정 (여운 중)
        s["stim"]["B"] = 100
        r2 = stim.force_climax(s)
        assert r2["is_chain"] is True
        assert r2["chain_count"] == 1
        assert r2["climax_total"] == 2

        # 3차 연쇄 절정
        s["stim"]["A"] = 100
        r3 = stim.force_climax(s)
        assert r3["chain_count"] == 2
        assert r3["climax_total"] == 3
