# test_romance_mode.py — romance_mode.py 순수 함수 + mock 테스트
"""
4개 동작 모드의 컨텍스트 생성, 효과 배율, bool 함수 검증.
get_unit_power / calculate_force_chance는 mock 기반.
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
# get_unit_power (mock 기반)
# ============================================

class TestUnitPower:
    def test_default_stats(self):
        """기본 능력치 — 근력=5, 체격=2, HP=100/100"""
        morld.register_unit(10, props={
            "근력": 5, "체격": 2,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        power = rm.get_unit_power(10)
        # 5 + 2 + (100/100)*3 = 10
        assert power == 10.0

    def test_low_hp(self):
        """HP 50/100 → hp_ratio=0.5"""
        morld.register_unit(10, props={
            "근력": 5, "체격": 2,
            "생존:체력": 50, "생존:최대체력": 100,
        })
        power = rm.get_unit_power(10)
        # 5 + 2 + 0.5*3 = 8.5
        assert power == 8.5

    def test_missing_props_use_defaults(self):
        """prop 없으면 기본값 사용"""
        morld.register_unit(10, props={})
        power = rm.get_unit_power(10)
        # 근력=5, 체격=2, HP=100/100 (기본값)
        # 5 + 2 + 1.0*3 = 10
        assert power == 10.0


# ============================================
# calculate_force_chance (mock 기반)
# ============================================

class TestForceChance:
    def test_equal_power(self):
        """동일 능력치 → 50%"""
        morld.register_unit(1, props={
            "근력": 5, "체격": 2,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        morld.register_unit(2, props={
            "근력": 5, "체격": 2,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        chance = rm.calculate_force_chance(1, 2)
        assert abs(chance - 0.5) < 0.01

    def test_stronger_actor(self):
        """actor가 강하면 확률 상승"""
        morld.register_unit(1, props={
            "근력": 10, "체격": 3,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        morld.register_unit(2, props={
            "근력": 3, "체격": 1,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        chance = rm.calculate_force_chance(1, 2)
        assert chance > 0.5

    def test_stealth_bonus(self):
        """은신 상태 +20%"""
        morld.register_unit(1, props={
            "근력": 5, "체격": 2,
            "생존:체력": 100, "생존:최대체력": 100,
            "status:stealth": 1,
        })
        morld.register_unit(2, props={
            "근력": 5, "체격": 2,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        chance = rm.calculate_force_chance(1, 2)
        assert abs(chance - 0.7) < 0.01  # 0.5 + 0.2

    def test_clamp_min(self):
        """아무리 약해도 최소 0.1"""
        morld.register_unit(1, props={
            "근력": 1, "체격": 1,
            "생존:체력": 10, "생존:최대체력": 100,
        })
        morld.register_unit(2, props={
            "근력": 15, "체격": 5,
            "생존:체력": 100, "생존:최대체력": 100,
        })
        chance = rm.calculate_force_chance(1, 2)
        assert chance >= 0.1

    def test_clamp_max(self):
        """아무리 강해도 최대 0.95"""
        morld.register_unit(1, props={
            "근력": 20, "체격": 5,
            "생존:체력": 100, "생존:최대체력": 100,
            "status:stealth": 1,
        })
        morld.register_unit(2, props={
            "근력": 1, "체격": 1,
            "생존:체력": 10, "생존:최대체력": 100,
        })
        chance = rm.calculate_force_chance(1, 2)
        assert chance <= 0.95
