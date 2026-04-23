# test_romance_mode.py — romance_mode.py 순수 함수 + mock 테스트
"""
4개 동작 모드의 컨텍스트 생성, 효과 배율, bool 함수 검증.
get_strength / calculate_force_chance / calculate_escape_chance는 mock 기반.
"""
import sys
import romance_mode as rm

# mock_morld에 접근
morld = sys.modules["morld"]


# ============================================
# create_mode_context
# ============================================

class TestCreateModeContext:
    def test_consensual_basic(self):
        ctx = rm.create_mode_context(rm.MODE_CONSENSUAL, 1, 2)
        assert ctx["mode"] == rm.MODE_CONSENSUAL
        assert ctx["actor_id"] == 1
        assert ctx["target_id"] == 2
        assert ctx["action_count"] == 0
        # consensual에는 resistance_meter 없음
        assert "resistance_meter" not in ctx

    def test_forced_has_resistance(self):
        ctx = rm.create_mode_context(rm.MODE_FORCED, 1, 2)
        assert ctx["mode"] == rm.MODE_FORCED
        assert ctx["resistance_meter"] == 0
        assert ctx["break_free_attempts"] == 0
        # is_futile 개념 제거됨
        assert "last_is_futile" not in ctx

    def test_unconscious_has_wake_check(self):
        ctx = rm.create_mode_context(rm.MODE_UNCONSCIOUS, 1, 2)
        assert "wake_check_accum" in ctx
        assert ctx["wake_check_accum"] == 0

    def test_frozen_has_deferred(self):
        ctx = rm.create_mode_context(rm.MODE_FROZEN, 1, 2)
        assert isinstance(ctx["deferred_effects"], list)
        assert isinstance(ctx["deferred_semen"], dict)
        assert isinstance(ctx["deferred_internal_semen"], dict)
        assert ctx["deferred_climax_count"] == 0


# ============================================
# get_effect_multipliers
# ============================================

class TestEffectMultipliers:
    def test_consensual_all_1(self):
        m = rm.get_effect_multipliers(rm.MODE_CONSENSUAL)
        assert m["affection"] == 1.0
        assert m["desire"] == 1.0
        assert m["rebellion"] == 1.0
        assert m["submission"] == 1.0
        assert m["arousal"] == 1.0
        assert m["sensation_exp"] == 1.0

    def test_forced_rebellion_doubled(self):
        m = rm.get_effect_multipliers(rm.MODE_FORCED)
        assert m["affection"] == 0.0
        assert m["rebellion"] == 2.0
        assert m["submission"] == 2.0
        assert m["arousal"] == 1.0

    def test_unconscious_emotions_zero(self):
        m = rm.get_effect_multipliers(rm.MODE_UNCONSCIOUS)
        assert m["affection"] == 0.0
        assert m["desire"] == 0.0
        assert m["rebellion"] == 0.0
        assert m["submission"] == 0.0
        assert m["arousal"] == 0.5

    def test_frozen_no_sensation(self):
        m = rm.get_effect_multipliers(rm.MODE_FROZEN)
        assert m["sensation_exp"] == 0.0
        # 나머지는 정상 (defer 후 감쇠)
        assert m["affection"] == 1.0

    def test_unknown_mode_empty(self):
        m = rm.get_effect_multipliers("unknown")
        assert m == {}


# ============================================
# 순수 bool 함수들
# ============================================

class TestModeBooleans:
    def test_get_affection_req(self):
        assert rm.get_affection_req(rm.MODE_CONSENSUAL) is None
        assert rm.get_affection_req(rm.MODE_FORCED) == 0
        assert rm.get_affection_req(rm.MODE_UNCONSCIOUS) == 0
        assert rm.get_affection_req(rm.MODE_FROZEN) == 0

    def test_get_reaction_prefix(self):
        assert rm.get_reaction_prefix(rm.MODE_CONSENSUAL) == ""
        assert rm.get_reaction_prefix(rm.MODE_FORCED) == "forced_"
        assert rm.get_reaction_prefix(rm.MODE_UNCONSCIOUS) is None
        assert rm.get_reaction_prefix(rm.MODE_FROZEN) is None

    def test_should_advance_time(self):
        assert rm.should_advance_time(rm.MODE_CONSENSUAL) is True
        assert rm.should_advance_time(rm.MODE_FORCED) is True
        assert rm.should_advance_time(rm.MODE_UNCONSCIOUS) is True
        assert rm.should_advance_time(rm.MODE_FROZEN) is False

    def test_should_emit_sound(self):
        assert rm.should_emit_sound(rm.MODE_CONSENSUAL) is True
        assert rm.should_emit_sound(rm.MODE_FORCED) is True
        assert rm.should_emit_sound(rm.MODE_UNCONSCIOUS) is False
        assert rm.should_emit_sound(rm.MODE_FROZEN) is False

    def test_should_check_third_party(self):
        assert rm.should_check_third_party(rm.MODE_CONSENSUAL) is True
        assert rm.should_check_third_party(rm.MODE_FORCED) is True
        assert rm.should_check_third_party(rm.MODE_UNCONSCIOUS) is True
        assert rm.should_check_third_party(rm.MODE_FROZEN) is False

    def test_can_switch_initiative(self):
        assert rm.can_switch_initiative(rm.MODE_CONSENSUAL) is True
        assert rm.can_switch_initiative(rm.MODE_FORCED) is False
        assert rm.can_switch_initiative(rm.MODE_UNCONSCIOUS) is False
        assert rm.can_switch_initiative(rm.MODE_FROZEN) is False

    def test_can_target_resist(self):
        assert rm.can_target_resist(rm.MODE_CONSENSUAL) is False
        assert rm.can_target_resist(rm.MODE_FORCED) is True
        assert rm.can_target_resist(rm.MODE_UNCONSCIOUS) is False
        assert rm.can_target_resist(rm.MODE_FROZEN) is False

    def test_should_check_wakeup(self):
        assert rm.should_check_wakeup(rm.MODE_CONSENSUAL) is False
        assert rm.should_check_wakeup(rm.MODE_FORCED) is False
        assert rm.should_check_wakeup(rm.MODE_UNCONSCIOUS) is True
        assert rm.should_check_wakeup(rm.MODE_FROZEN) is False


# ============================================
# get_strength (mock 기반)
# ============================================

class TestGetStrength:
    def test_default_strength(self):
        """prop 없으면 기본값 5"""
        morld.register_unit(10, props={})
        assert rm.get_strength(10) == 5

    def test_explicit_strength(self):
        """명시된 근력 값 반환"""
        morld.register_unit(10, props={"근력": 12})
        assert rm.get_strength(10) == 12


# ============================================
# calculate_force_chance (근력차만, 체격/hp 제거됨)
# ============================================

class TestForceChance:
    def test_equal_strength(self):
        """동일 근력 → 50%"""
        morld.register_unit(1, props={"근력": 5})
        morld.register_unit(2, props={"근력": 5})
        chance = rm.calculate_force_chance(1, 2)
        assert abs(chance - 0.5) < 0.01

    def test_stronger_actor(self):
        """actor가 강하면 확률 상승 (근력차 1당 +5%)"""
        morld.register_unit(1, props={"근력": 10})
        morld.register_unit(2, props={"근력": 3})
        chance = rm.calculate_force_chance(1, 2)
        # 0.5 + (10-3)*0.05 = 0.85
        assert abs(chance - 0.85) < 0.01

    def test_stealth_bonus(self):
        """은신 상태 +20%"""
        morld.register_unit(1, props={"근력": 5, "status:stealth": 1})
        morld.register_unit(2, props={"근력": 5})
        chance = rm.calculate_force_chance(1, 2)
        assert abs(chance - 0.7) < 0.01  # 0.5 + 0.2

    def test_hp_no_longer_affects(self):
        """체력은 force_chance에 영향 없음 (escape로 역할 분리)"""
        morld.register_unit(1, props={"근력": 5, "생존:체력": 10})
        morld.register_unit(2, props={"근력": 5, "생존:체력": 100})
        chance = rm.calculate_force_chance(1, 2)
        assert abs(chance - 0.5) < 0.01  # 근력 동일이면 체력 무시

    def test_clamp_min(self):
        """아무리 약해도 최소 0.1"""
        morld.register_unit(1, props={"근력": 1})
        morld.register_unit(2, props={"근력": 15})
        chance = rm.calculate_force_chance(1, 2)
        assert chance >= 0.1

    def test_clamp_max(self):
        """아무리 강해도 최대 0.95"""
        morld.register_unit(1, props={"근력": 20, "status:stealth": 1})
        morld.register_unit(2, props={"근력": 1})
        chance = rm.calculate_force_chance(1, 2)
        assert chance <= 0.95


# ============================================
# calculate_escape_chance (체력차 + 모디파이어)
# ============================================

class TestEscapeChance:
    def test_equal_hp_no_modifiers(self):
        """체력 동일 + 모디파이어 0 → ESCAPE_BASE (10%)"""
        morld.register_unit(1, props={"생존:체력": 100})  # actor (player)
        morld.register_unit(2, props={"생존:체력": 100})  # target
        info = rm.calculate_escape_chance(2, 1)
        assert abs(info["chance"] - 0.10) < 0.001

    def test_target_higher_hp(self):
        """target 체력이 더 높으면 탈출 확률 증가"""
        morld.register_unit(1, props={"생존:체력": 50})
        morld.register_unit(2, props={"생존:체력": 100})
        info = rm.calculate_escape_chance(2, 1)
        # 0.10 + (100-50)*0.005 = 0.35
        assert abs(info["chance"] - 0.35) < 0.001

    def test_target_lower_hp(self):
        """target 체력이 더 낮으면 탈출 확률 감소"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={"생존:체력": 50})
        info = rm.calculate_escape_chance(2, 1)
        # 0.10 + (50-100)*0.005 = -0.15 → clamp to 0
        assert info["chance"] == 0.0

    def test_rebellion_bonus(self):
        """반발이 높으면 탈출 확률 상승"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "관계:주인공:반발": 50,
        })
        info = rm.calculate_escape_chance(2, 1)
        # 0.10 + 50*0.005 = 0.35
        assert abs(info["chance"] - 0.35) < 0.001

    def test_submission_penalty(self):
        """복종이 높으면 체념으로 탈출 확률 감소"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "관계:주인공:복종": 10,
        })
        info = rm.calculate_escape_chance(2, 1)
        # 0.10 - 10*0.01 = 0.00
        assert info["chance"] == 0.0

    def test_arousal_penalty(self):
        """성욕이 높으면 저항 약화"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "상태:성욕": 50,
        })
        info = rm.calculate_escape_chance(2, 1)
        # 0.10 - 50*0.002 = 0.00
        assert info["chance"] == 0.0

    def test_clamp_max(self):
        """최대 0.5로 제한"""
        morld.register_unit(1, props={"생존:체력": 1})
        morld.register_unit(2, props={
            "생존:체력": 200,
            "관계:주인공:반발": 200,
        })
        info = rm.calculate_escape_chance(2, 1)
        assert info["chance"] <= 0.5

    def test_trance_entry_penalty(self):
        """Phase 1.9.1: 트랜스 60~79 → -0.15 페널티."""
        morld.register_unit(1, props={"생존:체력": 50})
        morld.register_unit(2, props={
            "생존:체력": 100,       # +0.25 (체력 우위)
            "상태:트랜스": 60,       # entry 구간
        })
        info = rm.calculate_escape_chance(2, 1)
        # base 0.10 + 0.25 - 0.15 = 0.20
        assert abs(info["chance"] - 0.20) < 0.001

    def test_trance_deep_penalty(self):
        """Phase 1.9.1: 트랜스 80+ → -0.30 페널티."""
        morld.register_unit(1, props={"생존:체력": 50})
        morld.register_unit(2, props={
            "생존:체력": 100,       # +0.25
            "상태:트랜스": 90,       # deep 구간
        })
        info = rm.calculate_escape_chance(2, 1)
        # base 0.10 + 0.25 - 0.30 = 0.05
        assert abs(info["chance"] - 0.05) < 0.001

    def test_trance_deep_can_zero_chance(self):
        """깊은 트랜스 + 체력 동등 → 탈출 0."""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "상태:트랜스": 90,
        })
        info = rm.calculate_escape_chance(2, 1)
        # base 0.10 + 0 - 0.30 = -0.20 → clamp 0
        assert info["chance"] == 0.0

    def test_no_trance_no_penalty(self):
        """트랜스 prop 없거나 60 미만 → 페널티 없음."""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "상태:트랜스": 59,
        })
        info = rm.calculate_escape_chance(2, 1)
        assert abs(info["chance"] - 0.10) < 0.001

    def test_meter_delta_rebellion_accelerates(self):
        """반발 높으면 저항 게이지 빨리 누적"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={
            "생존:체력": 100,
            "관계:주인공:반발": 100,
        })
        info = rm.calculate_escape_chance(2, 1)
        assert info["meter_delta"] >= rm.METER_DELTA_BASE

    def test_no_is_futile_field(self):
        """is_futile 개념 제거됨 — 반환 dict에 없어야 함"""
        morld.register_unit(1, props={"생존:체력": 100})
        morld.register_unit(2, props={"생존:체력": 100})
        info = rm.calculate_escape_chance(2, 1)
        assert "is_futile" not in info
        assert "escape_power" not in info
        assert "suppression" not in info
