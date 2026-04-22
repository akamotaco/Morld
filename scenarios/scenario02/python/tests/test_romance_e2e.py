# test_romance_e2e.py — 성행위 모듈 통합 시나리오 테스트
"""
Phase 0.5/0.6 완료 후 검증:
- 수치 변화: consensual/forced/unconscious 모드별 효과 배율
- 대사 변화: 모드별 reaction prefix (consensual → "", forced → "forced_")
- harassment_exec 파이프라인: lift → grope → 절정 게이지
- 통합 시나리오: forced 세션에서 lift_upper → breast_grope 흐름

start_romance generator 전체 드라이브는 의존성 과다 — effect 적용 로직을
apply_effects와 동일한 순서로 직접 재현하여 end-to-end 효과 검증.
"""
import sys
import random as _random

import romance_core as rc
import romance_mode as rm
import stimulation as stim
import gender as gender_mod

morld = sys.modules["morld"]


def _apply_action_effects(action_def, partner_id, player_id, mode):
    """romance.apply_effects의 핵심 루프를 직접 재현.

    production 경로와 동일한 순서:
    1. calculate_effects로 base effects 산출
    2. get_effect_multipliers(mode)로 배율 적용
    3. modify_prop으로 실제 반영
    """
    effects = rc.calculate_effects(action_def, partner_id, player_id)
    multipliers = rm.get_effect_multipliers(mode)
    _STAT_MULT_MAP = {
        "호감": "affection", "욕망": "desire", "반발": "rebellion",
        "복종": "submission", "성욕": "arousal",
    }
    affection_key = rc.get_affection_key(player_id)

    for stat, value in effects.items():
        mult_key = _STAT_MULT_MAP.get(stat)
        if mult_key:
            value = round(value * multipliers.get(mult_key, 1.0))
        if value == 0:
            continue

        if stat in ("성욕", "성적절정"):
            prop_key = f"상태:{stat}"
        elif stat == "욕망":
            prop_key = "상태:성욕"
        else:
            prop_key = affection_key.replace(":호감", f":{stat}")
        morld.modify_prop(partner_id, prop_key, value)


# ============================================
# 수치 변화 — 모드별 효과 배율 검증
# ============================================

class TestEffectMultipliersPerMode:
    def _setup(self, affection=50, arousal=0, submission=0, rebellion=0):
        morld.register_unit(1, name="주인공", props={"근력": 10})
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "관계:주인공:반발": rebellion,
            "관계:주인공:복종": submission,
            "상태:성욕": arousal,
            "근력": 5,
        })

    def test_consensual_full_effect(self):
        """합의 모드: 배율 1.0 — effect 그대로 적용"""
        self._setup(affection=60)
        # hug 유사: {호감: +3}
        action = {"name": "포옹", "effects": {"호감": 3}, "exp_part": None,
                  "affection_req": 50}
        _apply_action_effects(action, 2, 1, rm.MODE_CONSENSUAL)
        # 호감 60 → 63
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 63

    def test_forced_zeros_affection_doubles_rebellion(self):
        """강제 모드: 호감 ×0 (변화 없음), 반발 ×2, 복종 ×2"""
        self._setup(affection=30, rebellion=10, submission=5)
        # 복합 효과: {호감: 5, 반발: 3, 복종: 2}
        action = {"name": "액션", "effects": {"호감": 5, "반발": 3, "복종": 2},
                  "exp_part": None, "affection_req": 0}
        _apply_action_effects(action, 2, 1, rm.MODE_FORCED)
        # 호감 30 유지 (변화 0)
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 30
        # 반발 10 + 3×2 = 16
        assert morld.get_unit_prop(2, "관계:주인공:반발") == 16
        # 복종 5 + 2×2 = 9
        assert morld.get_unit_prop(2, "관계:주인공:복종") == 9

    def test_forced_arousal_normal(self):
        """강제 모드: 성욕 배율은 1.0 (물리 자극은 그대로)"""
        self._setup(arousal=20)
        action = {"name": "액션", "effects": {"성욕": 5}, "exp_part": None,
                  "affection_req": 0}
        _apply_action_effects(action, 2, 1, rm.MODE_FORCED)
        # 성욕 20 + 5 = 25
        assert morld.get_unit_prop(2, "상태:성욕") == 25

    def test_unconscious_suppresses_emotions(self):
        """무의식 모드: 호감/욕망/반발/복종 전부 ×0, 성욕만 ×0.5 (물리 반사)"""
        self._setup(affection=50, rebellion=10, submission=5, arousal=20)
        action = {"name": "액션",
                  "effects": {"호감": 10, "반발": 5, "복종": 3, "성욕": 10},
                  "exp_part": None, "affection_req": 0}
        _apply_action_effects(action, 2, 1, rm.MODE_UNCONSCIOUS)
        # 감정 4종 모두 변화 없음
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 50
        assert morld.get_unit_prop(2, "관계:주인공:반발") == 10
        assert morld.get_unit_prop(2, "관계:주인공:복종") == 5
        # 성욕 20 + 10×0.5 = 25
        assert morld.get_unit_prop(2, "상태:성욕") == 25


# ============================================
# 대사 변화 — reaction prefix mode 분기
# ============================================

class TestReactionPrefixPerMode:
    def test_consensual_prefix_empty(self):
        """합의 모드: 접두사 없음 → 기본 대사 풀"""
        assert rm.get_reaction_prefix(rm.MODE_CONSENSUAL) == ""

    def test_forced_prefix_forced(self):
        """강제 모드: 'forced_' 접두사 → 전용 대사 풀"""
        assert rm.get_reaction_prefix(rm.MODE_FORCED) == "forced_"

    def test_unconscious_none(self):
        """무의식 모드: 접두사 None → 무반응 나레이션"""
        assert rm.get_reaction_prefix(rm.MODE_UNCONSCIOUS) is None

    def test_frozen_none(self):
        """시간정지 모드: 접두사 None → 무반응"""
        assert rm.get_reaction_prefix(rm.MODE_FROZEN) is None

    def test_reaction_key_derivation(self):
        """프로덕션 대사 조회 로직: prefix + action_id:timing 형태"""
        # 이는 base.Character.get_romance_reaction의 로직 개요.
        # forced 모드에서 "head_pat:start" 조회 시 "forced_head_pat:start" 우선 시도.
        def derive_key(action_id, timing, mode):
            prefix = rm.get_reaction_prefix(mode)
            if prefix is None:
                return None  # 무반응
            return f"{prefix}{action_id}:{timing}"

        assert derive_key("head_pat", "start", rm.MODE_CONSENSUAL) == "head_pat:start"
        assert derive_key("head_pat", "start", rm.MODE_FORCED) == "forced_head_pat:start"
        assert derive_key("head_pat", "start", rm.MODE_UNCONSCIOUS) is None


# ============================================
# harassment_exec 파이프라인 — side-effect 검증
# ============================================

class TestHarassmentExecPipeline:
    def test_lift_upper_sets_임시노출(self):
        """lift_upper → 임시노출:상체 0→1 또는 0→2"""
        import harassment
        morld.register_unit(1, name="주인공", props={"근력": 10})
        morld.register_unit(2, props={"근력": 5})
        # 의류 없음 → 바로 노출 2
        from romance_actions import INSTANT_ACTIONS
        action = INSTANT_ACTIONS["lift_upper"]
        result = harassment.execute_lift(1, 2, action)
        assert result["success"] is True
        assert morld.get_unit_prop(2, "임시노출:상체") == 2

    def test_lift_repeat_caps_at_2(self):
        """이미 완전 노출인 경우 실패"""
        import harassment
        morld.register_unit(1, name="주인공", props={"근력": 10})
        morld.register_unit(2, props={"근력": 5, "임시노출:상체": 2})
        from romance_actions import INSTANT_ACTIONS
        action = INSTANT_ACTIONS["lift_upper"]
        result = harassment.execute_lift(1, 2, action)
        assert result["success"] is False

    def test_grope_with_exposure_increases_climax(self):
        """노출된 상태에서 grope → 상태:절정 climax_gain 만큼 증가"""
        import harassment
        morld.register_unit(1, name="주인공", props={"근력": 10})
        morld.register_unit(2, props={"근력": 5, "임시노출:상체": 2, "상태:절정": 0})
        from romance_actions import INSTANT_ACTIONS
        action = INSTANT_ACTIONS["breast_grope"]  # climax_gain: 8
        result = harassment.execute_grope(1, 2, action)
        assert result["success"] is True
        assert morld.get_unit_prop(2, "상태:절정") == 8


# ============================================
# 통합 시나리오 — forced 세션 액션 체인
# ============================================

class TestForcedSessionScenario:
    def _setup(self):
        """플레이어(근력 우위) + NPC 기본 상태"""
        morld.register_unit(1, name="주인공", props={"근력": 10, "생존:체력": 100})
        morld.register_unit(2, name="대상", props={
            "근력": 4,
            "생존:체력": 80,
            "관계:주인공:호감": 20,
            "관계:주인공:반발": 15,
            "관계:주인공:복종": 0,
            "상태:성욕": 10,
        })

    def test_lift_then_grope_climax_chain(self):
        """시나리오: 상체 들추기 → 유두 만지기 → 절정 게이지 누적"""
        import harassment
        from romance_actions import INSTANT_ACTIONS
        self._setup()

        # Step 1: 의류 없음 → lift_upper 바로 노출 2
        result = harassment.execute_lift(1, 2, INSTANT_ACTIONS["lift_upper"])
        assert result["success"]
        assert morld.get_unit_prop(2, "임시노출:상체") == 2

        # Step 2: nipple_grope (climax_gain: 10)
        result = harassment.execute_grope(1, 2, INSTANT_ACTIONS["nipple_grope"])
        assert result["success"]
        assert morld.get_unit_prop(2, "상태:절정") == 10

        # Step 3: breast_grope (climax_gain: 8) — 누적
        result = harassment.execute_grope(1, 2, INSTANT_ACTIONS["breast_grope"])
        assert result["success"]
        assert morld.get_unit_prop(2, "상태:절정") == 18

    def test_strength_advantage_required(self):
        """근력 부족 시 resolve_action_mode → unavailable"""
        morld.register_unit(1, name="주인공", props={"근력": 3})
        morld.register_unit(2, props={"근력": 5})
        from romance_actions import INSTANT_ACTIONS
        action = INSTANT_ACTIONS["lift_upper"]
        mode = rc.resolve_action_mode(2, 1, action)
        assert mode == "unavailable"

    def test_forced_resistance_meter_accumulation(self):
        """강제 세션 중 저항 실패 → meter 누적, 100 초과 시 강제 탈출 플래그"""
        self._setup()
        # 탈출 불가 조건: 복종 매우 높음 + 반발 0 → escape_chance 0 (체념)
        # 매번 실패하므로 meter는 매 호출 누적.
        morld.set_unit_prop(2, "관계:주인공:복종", 100)
        morld.set_unit_prop(2, "관계:주인공:반발", 0)

        mode_ctx = rm.create_mode_context(rm.MODE_FORCED, 1, 2)
        first = rm.check_resistance(mode_ctx, 2)
        assert first["attempted"] is True
        assert first["escaped"] is False  # 체념 상태 → 탈출 불가
        assert first["resistance_delta"] > 0
        delta1 = mode_ctx["resistance_meter"]
        assert delta1 > 0

        # 반복 호출 시 게이지 누적
        rm.check_resistance(mode_ctx, 2)
        assert mode_ctx["resistance_meter"] > delta1

        # meter 100+ 도달 시 강제 탈출 (반복 호출로 유도)
        for _ in range(20):
            if rm.check_resistance(mode_ctx, 2).get("escaped"):
                break
        assert mode_ctx["resistance_meter"] >= 100

    def test_escape_with_high_submission_impossible(self):
        """복종 높은 NPC는 체념 — 탈출 확률 0으로 감쇠"""
        self._setup()
        morld.set_unit_prop(2, "관계:주인공:복종", 50)  # 체념 다량
        morld.set_unit_prop(2, "관계:주인공:반발", 0)
        info = rm.calculate_escape_chance(2, 1)
        # 체력차 (-20) * 0.005 = -0.10
        # ESCAPE_BASE (0.10) + (-0.10) - 복종 50*0.01 (-0.5) = -0.50
        # clamp 0~0.5 → 0
        assert info["chance"] == 0.0


# ============================================
# 일회성 강제 override 시뮬레이션
# ============================================

class TestForcedOverride:
    """consensual 세션 내에서 force_instant 클릭 시 동작.

    프로덕션의 모드 스왑 (mode_ctx 일시 변경) 로직과 동일한 시퀀스로 재현.
    """
    def _setup_session(self):
        morld.register_unit(1, name="주인공", props={"근력": 10})
        morld.register_unit(2, props={
            "관계:주인공:호감": 20,
            "관계:주인공:반발": 5,
            "관계:주인공:복종": 0,
            "상태:성욕": 0,
            "근력": 5,
        })
        return {"mode_ctx": rm.create_mode_context(rm.MODE_CONSENSUAL, 1, 2),
                "player_id": 1, "partner_id": 2}

    def test_override_uses_forced_multipliers(self):
        """consensual 세션에서 강제 액션 → forced 배율 적용"""
        state = self._setup_session()
        action = {"name": "키스", "effects": {"호감": 4, "반발": 2},
                  "exp_part": None, "affection_req": 60}

        # 스왑 시뮬레이션
        saved_mode = state["mode_ctx"]["mode"]
        state["mode_ctx"]["mode"] = rm.MODE_FORCED
        # FORCED 전용 필드 lazy init
        state["mode_ctx"].setdefault("resistance_meter", 0)
        state["mode_ctx"].setdefault("break_free_attempts", 0)
        state["mode_ctx"].setdefault("last_escape_chance", 0.0)

        try:
            _apply_action_effects(action, 2, 1, state["mode_ctx"]["mode"])
        finally:
            state["mode_ctx"]["mode"] = saved_mode

        # 호감 ×0 → 변화 없음
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 20
        # 반발 5 + 2×2 = 9
        assert morld.get_unit_prop(2, "관계:주인공:반발") == 9
        # 세션 모드는 consensual로 복원
        assert state["mode_ctx"]["mode"] == rm.MODE_CONSENSUAL


# ============================================
# resolve_action_mode 엔드 투 엔드 조합
# ============================================

class TestResolveActionModeEndToEnd:
    def _setup(self, affection=50, arousal=0, submission=0,
               player_strength=10, partner_strength=5):
        morld.register_unit(1, name="주인공", props={"근력": player_strength})
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "관계:주인공:복종": submission,
            "상태:성욕": arousal,
            "근력": partner_strength,
        })

    def test_high_affection_consensual_path(self):
        """고호감 + 물리 OK → consensual"""
        self._setup(affection=90)
        action = {"affection_req": 50, "effects": {}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"

    def test_low_affection_forced_path(self):
        """저호감 + 물리 OK → forced (호감 미달)"""
        self._setup(affection=10)
        action = {"affection_req": 80, "effects": {}}
        assert rc.resolve_action_mode(2, 1, action) == "forced"

    def test_arousal_compensates_low_affection(self):
        """성욕으로 할인 충당 → consensual 달성"""
        # req=80, arousal=200, submission=200
        # arousal_discount = min(80*0.3, 200*0.3) = 24
        # submission_discount = min(80*0.3, 200*0.3) = 24
        # total = min(80*0.5, 48) = 40
        # eff_req = max(20, 80-40) = 40
        # affection 50 >= 40 → consensual
        self._setup(affection=50, arousal=200, submission=200)
        action = {"affection_req": 80, "effects": {}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"

    def test_physical_req_trumps_affection(self):
        """근력 부족 → 호감 아무리 높아도 unavailable"""
        self._setup(affection=100, player_strength=3, partner_strength=5)
        action = {
            "affection_req": 0,
            "effects": {},
            "physical_req": {"strength_advantage": True},
        }
        assert rc.resolve_action_mode(2, 1, action) == "unavailable"


# ============================================
# 연쇄 절정 (chain climax) — stimulation 모듈
# ============================================

class TestChainClimaxFlow:
    """여운(afterglow) 상태에서 재자극 시 연쇄 절정 발동 검증.

    핵심 로직(stimulation.py):
    - 첫 절정 → afterglow=50, chain_count=0
    - 여운 중 자극 → CHAIN_AMPLIFIER 1.5x 배율
    - 여운 중 peaked → 즉시 연쇄 발동 (게이지 체크 건너뜀)
    - chain_count 누적, climax_total 증가
    - afterglow 행위당 -10 감쇠, 0 도달 시 chain_count 리셋
    """

    def test_first_climax_sets_afterglow(self):
        """첫 절정: afterglow=50 설정, chain_count=0"""
        state = stim.create_state(male_mode=False)
        # V 자극 peaked + 게이지 100 → 절정 트리거 조건 동시 충족
        state["stim"]["V"] = stim.STIM_MAX - 5  # 95
        state["climax_gauge"] = stim.CLIMAX_GAUGE_MAX  # 100
        # 자극 5만 추가 → V=100 peaked + gauge 이미 만충 → 절정
        result = stim.apply(state, "V", 10)
        assert result is not None, "자극 100 + 게이지 만충 → 절정 트리거"
        assert result["is_chain"] is False
        assert result["chain_count"] == 0
        assert state["afterglow"] == stim.AFTERGLOW_INITIAL  # 50
        assert state["climax_total"] == 1

    def test_chain_climax_during_afterglow(self):
        """여운 중 재자극 → 연쇄 절정 (chain_count 1)"""
        state = stim.create_state(male_mode=False)
        # 첫 절정 만들기
        state["stim"]["V"] = stim.STIM_MAX - 5
        state["climax_gauge"] = stim.CLIMAX_GAUGE_MAX
        first = stim.apply(state, "V", 10)
        assert first is not None
        assert state["afterglow"] > 0

        # 여운 중 다른 부위 자극 → peaked → 연쇄
        state["stim"]["C"] = stim.STIM_MAX - 5
        chain = stim.apply(state, "C", 20)
        assert chain is not None
        assert chain["is_chain"] is True
        assert chain["chain_count"] == 1
        assert state["climax_total"] == 2

    def test_chain_multiplier_on_afterglow_stim(self):
        """여운 중 자극 입력 시 CHAIN_AMPLIFIER(1.5) 배율 적용"""
        # calc_gain 직접 호출 — 여운 있을 때 vs 없을 때
        base = 10
        gain_normal = stim.calc_gain(base, sensation_level=0, rebellion=0, afterglow=0)
        gain_chain = stim.calc_gain(base, sensation_level=0, rebellion=0, afterglow=30)
        # 여운 중 1.5배 (반올림 차이 허용)
        assert gain_chain >= gain_normal * 1.4

    def test_afterglow_decay_resets_chain_count(self):
        """여운이 0으로 감쇠하면 chain_count 리셋"""
        state = stim.create_state(male_mode=False)
        state["afterglow"] = 20
        state["chain_count"] = 3
        # tick 1: afterglow 10
        stim.tick_afterglow(state)
        assert state["afterglow"] == 10
        assert state["chain_count"] == 3  # 아직 유지
        # tick 2: afterglow 0, chain_count 리셋
        stim.tick_afterglow(state)
        assert state["afterglow"] == 0
        assert state["chain_count"] == 0

    def test_chain_sensation_exp_bonus(self):
        """chain_count에 따른 감각 경험치 배율 — 0:x1, 1:x1.5, 2:x2, 3+:x2.5"""
        # base = CLIMAX_SENSATION_GAIN (3) - rebellion//25 = 3 (rebellion 0)
        assert stim.get_climax_sensation_gain(0, chain_count=0) == 3
        assert stim.get_climax_sensation_gain(0, chain_count=1) == round(3 * 1.5)  # 5
        assert stim.get_climax_sensation_gain(0, chain_count=2) == round(3 * 2.0)  # 6
        # chain 4도 3으로 cap
        assert stim.get_climax_sensation_gain(0, chain_count=4) == round(3 * 2.5)  # 8

    def test_male_mode_refractory_blocks_chain(self):
        """남성 모드: 절정 후 불응기 진입 → 자극 상승 ×0.1 → 연쇄 불가"""
        state = stim.create_state(male_mode=True)
        # P 자극 peaked + 게이지 만충 → 절정
        state["stim"]["P"] = stim.STIM_MAX
        state["climax_gauge"] = stim.CLIMAX_GAUGE_MAX
        stim.force_climax(state)
        assert state["refractory"] == stim.REFRACTORY_INITIAL  # 60
        # 불응기 중 자극 → 0.1배율만
        gain = stim.calc_gain(100, sensation_level=0, rebellion=0,
                              afterglow=0, refractory=60)
        assert gain <= 100 * stim.REFRACTORY_GAIN_FACTOR * 1.1  # 10 + 여유
        # afterglow는 male에서는 P 절정만일 때 미설정 (non_p_parts 없음)
        assert state["afterglow"] == 0


# ============================================
# 3 루트: 순애 / 성욕 / 강간
# ============================================

class TestRoutes:
    """호감도 기반 3 루트 분기 검증.

    - 순애: 호감 충분 → consensual
    - 성욕: 낮은 호감 + 높은 arousal/submission → 할인으로 consensual 달성
    - 강간: 낮은 호감 + 근력 우위 → forced (force_instant 경유)
    """

    def _setup(self, affection=0, arousal=0, submission=0,
               player_strength=5, partner_strength=5):
        morld.register_unit(1, name="주인공", props={"근력": player_strength, "성별": 1})
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "관계:주인공:복종": submission,
            "상태:성욕": arousal,
            "근력": partner_strength,
            "성별": 2,
        })

    def test_pure_love_route(self):
        """순애: 고호감(90) → consensual"""
        self._setup(affection=90)
        action = {"affection_req": 50, "effects": {"호감": 5}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"
        _apply_action_effects(action, 2, 1, rm.MODE_CONSENSUAL)
        # 호감 90 + 5 = 95
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 95

    def test_lust_route_arousal_discount(self):
        """성욕: 낮은 호감(25) + 높은 arousal(200) → 할인으로 consensual 달성"""
        # req=40, arousal=200
        # arousal_discount = min(40*0.3, 200*0.3) = min(12, 60) = 12
        # eff_req = max(20, 40-12) = 28
        # affection 30 >= 28 → consensual
        self._setup(affection=30, arousal=200)
        action = {"affection_req": 40, "effects": {"호감": 2, "성욕": 5}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"

    def test_lust_route_fails_if_min_affection_not_met(self):
        """최소 호감 20 미달 시 아무리 성욕 높아도 forced"""
        self._setup(affection=15, arousal=500, submission=500)
        action = {"affection_req": 80, "effects": {"호감": 2}}
        # eff_req = max(20, 80 - min(40, 15+15)) = max(20, 50) = 50
        # affection 15 < 50 → forced
        assert rc.resolve_action_mode(2, 1, action) == "forced"

    def test_submission_route_accumulates_forced(self):
        """강간 반복 → 복종 누적 → 점차 consensual 근접"""
        # 저호감 + 높은 복종(100)이면 할인 활용
        # req=50, submission=100
        # submission_discount = min(50*0.3, 100*0.3) = min(15, 30) = 15
        # eff_req = max(20, 50-15) = 35
        # affection 35 >= 35 → consensual
        self._setup(affection=35, submission=100)
        action = {"affection_req": 50, "effects": {"호감": 2}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"

    def test_rape_route_forced_override(self):
        """강간: 저호감 + 근력 우위 → forced 효과 배율 적용"""
        self._setup(affection=10, player_strength=10, partner_strength=5,
                    submission=0)
        morld.set_unit_prop(2, "관계:주인공:반발", 0)
        action = {"affection_req": 80, "effects": {"호감": 5, "반발": 3, "복종": 2}}
        # resolve → forced (호감 미달)
        assert rc.resolve_action_mode(2, 1, action) == "forced"
        # forced 효과 적용
        _apply_action_effects(action, 2, 1, rm.MODE_FORCED)
        # 호감 10 유지 (×0), 반발 0 + 3*2 = 6, 복종 0 + 2*2 = 4
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 10
        assert morld.get_unit_prop(2, "관계:주인공:반발") == 6
        assert morld.get_unit_prop(2, "관계:주인공:복종") == 4

    def test_rape_route_blocked_by_strength(self):
        """강간: 근력 열세 시 forced_only 액션은 unavailable (greyed)"""
        self._setup(affection=10, player_strength=3, partner_strength=10)
        from romance_actions import INSTANT_ACTIONS
        action = INSTANT_ACTIONS["lift_upper"]  # strength_advantage 필요
        assert rc.resolve_action_mode(2, 1, action) == "unavailable"


# ============================================
# 성별 조합: 남남 / 남녀 / 녀녀 해부학 호환성
# ============================================

class TestGenderCombos:
    """성별/해부학 기반 액션 가용성 검증.

    - male: M/B/A/P (페니스)
    - female: M/B/A/V/C (질/클리토리스)
    - futanari: 전부
    - asexual: M만

    is_anatomy_compatible(action, target, actor):
    - exp_part의 카테고리를 target이 보유해야 함
    - requires_player_anatomy를 actor가 보유해야 함
    - requires_both_anatomy를 양쪽 모두 보유해야 함
    """

    def _make_unit(self, uid, gender_str, orientation="bisexual"):
        gint = gender_mod.gender_to_int(gender_str)
        oint = {"heterosexual": 1, "bisexual": 2, "homosexual": 3}[orientation]
        morld.register_unit(uid, props={"성별": gint, "성적지향": oint})

    def test_mm_pair_anatomy_compat(self):
        """남-남: 페니스 자극(P) 가능, 질 자극(V) 불가"""
        self._make_unit(1, "male")  # player
        self._make_unit(2, "male")  # partner

        # exp_part=음경 (P) → partner 남 (P 보유) → compat
        penis_action = {"exp_part": "음경", "effects": {}}
        assert rc.is_anatomy_compatible(penis_action, 2, actor_id=1) is True

        # exp_part=음부 (V) → partner 남 (V 없음) → 불호환
        vagina_action = {"exp_part": "음부", "effects": {}}
        assert rc.is_anatomy_compatible(vagina_action, 2, actor_id=1) is False

        # 질삽입 (requires_player_anatomy=P + exp_part=음부) → actor 남 P, target 남 V 없음 → 불호환
        vaginal_insert = {"exp_part": "음부", "requires_player_anatomy": "P",
                          "effects": {}}
        assert rc.is_anatomy_compatible(vaginal_insert, 2, actor_id=1) is False

        # 항문삽입 (requires_player_anatomy=P + exp_part=항문 A) → 양쪽 A 보유 → 호환
        anal_insert = {"exp_part": "항문", "requires_player_anatomy": "P",
                       "effects": {}}
        assert rc.is_anatomy_compatible(anal_insert, 2, actor_id=1) is True

    def test_mf_pair_anatomy_compat(self):
        """남-녀: 질삽입 가능, 핸드잡(target P) 불가"""
        self._make_unit(1, "male")
        self._make_unit(2, "female")

        # 가슴(B) → 모두 보유 → compat
        breast_action = {"exp_part": "가슴", "effects": {}}
        assert rc.is_anatomy_compatible(breast_action, 2, actor_id=1) is True

        # 질삽입 → compat
        vaginal_insert = {"exp_part": "음부", "requires_player_anatomy": "P",
                          "effects": {}}
        assert rc.is_anatomy_compatible(vaginal_insert, 2, actor_id=1) is True

        # 핸드잡 (exp_part=음경) → partner=여 (P 없음) → 불호환
        handjob = {"exp_part": "음경", "effects": {}}
        assert rc.is_anatomy_compatible(handjob, 2, actor_id=1) is False

    def test_ff_pair_anatomy_compat(self):
        """녀-녀: 페니스 삽입 불가, tribadism(V-V) 가능"""
        self._make_unit(1, "female")
        self._make_unit(2, "female")

        # 질삽입 (requires_player_anatomy=P) → actor=녀 P 없음 → 불호환
        vaginal_insert = {"exp_part": "음부", "requires_player_anatomy": "P",
                          "effects": {}}
        assert rc.is_anatomy_compatible(vaginal_insert, 2, actor_id=1) is False

        # 상호 자위 (requires_both_anatomy=V) → 양쪽 V → 호환
        tribadism = {"exp_part": "음부", "requires_both_anatomy": "V",
                     "effects": {}}
        assert rc.is_anatomy_compatible(tribadism, 2, actor_id=1) is True

        # 클리토리스 자극 → 양쪽 C 보유 → 호환
        clit_action = {"exp_part": "클리토리스", "effects": {}}
        assert rc.is_anatomy_compatible(clit_action, 2, actor_id=1) is True

    def test_orientation_multiplier_hetero_mm(self):
        """이성애자 남 + 남 파트너 → 배율 0.5 (비호환)"""
        self._make_unit(1, "male", "heterosexual")
        self._make_unit(2, "male", "heterosexual")
        mult = gender_mod.get_orientation_multiplier(2, 1)
        assert mult == 0.5

    def test_orientation_multiplier_homo_mm(self):
        """동성애자 남 + 남 파트너 → 배율 1.1 (선호 일치)"""
        self._make_unit(1, "male", "homosexual")
        self._make_unit(2, "male", "homosexual")
        mult = gender_mod.get_orientation_multiplier(2, 1)
        assert abs(mult - 1.1) < 0.001

    def test_orientation_multiplier_bi(self):
        """양성애자는 항상 1.0"""
        self._make_unit(1, "male", "bisexual")
        self._make_unit(2, "female", "bisexual")
        mult = gender_mod.get_orientation_multiplier(2, 1)
        assert mult == 1.0

    def test_futanari_has_both_anatomy(self):
        """후타나리: P와 V 모두 보유"""
        self._make_unit(1, "futanari")
        assert gender_mod.has_anatomy(1, "P") is True
        assert gender_mod.has_anatomy(1, "V") is True
        assert gender_mod.has_anatomy(1, "C") is True


# ============================================
# Phase 1: 자제심/수치심 이중축
# ============================================

class TestRestraintAndShame:
    """자제심/수치심 모디파이어 — 내면 억제 + 사회 억제.

    영구 성격(자제심)과 상황 상태(수치심)를 점수 합산에 반영.
    """

    def _setup(self, affection=50, arousal=0, submission=0,
               restraint=0, shame=0, loc=(0, 0)):
        morld.register_location(*loc)
        morld.register_unit(1, name="주인공", props={"근력": 5, "성별": 1},
                            location=loc)
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "관계:주인공:복종": submission,
            "상태:성욕": arousal,
            "성격:자제심": restraint,
            "상태:수치심": shame,
            "근력": 5,
            "성별": 2,
        }, location=loc)

    def test_no_restraint_no_penalty(self):
        """자제심 0 → 모디파이어 0"""
        self._setup(restraint=0)
        assert rc.get_restraint_modifier(2) == 0

    def test_high_restraint_reduces_score(self):
        """자제심 100 → -30점 (기존 호감 50 - req 30 = +20 → -10 로 역전)"""
        self._setup(affection=50, restraint=100)
        action = {"affection_req": 30, "effects": {}}
        score = rc.calculate_availability_score(2, 1, action)
        # baseline = 50 - 30 = 20
        # restraint penalty = -100 * 0.3 = -30
        # total = -10
        assert score == -10
        # forced로 판정됨
        assert rc.resolve_action_mode(2, 1, action) == "forced"

    def test_restraint_blocks_lust_route(self):
        """자제심 높음 → 성욕 할인으로도 consensual 달성 어려움"""
        # req 50, arousal 200, restraint 100
        # eff_req = max(20, 50 - 15) = 35 (성욕 할인)
        # baseline = 40 - 35 = 5
        # restraint penalty = -30
        # total = -25 → forced
        self._setup(affection=40, arousal=200, restraint=100)
        action = {"affection_req": 50, "effects": {}}
        assert rc.resolve_action_mode(2, 1, action) == "forced"

    def test_low_restraint_allows_consensual(self):
        """자제심 낮음 (방종) → 낮은 호감에도 쉽게 consensual"""
        # 자제심 0 + 일반 호감 50 vs req 30 → +20 그대로 유지
        self._setup(affection=50, restraint=0)
        action = {"affection_req": 30, "effects": {}}
        assert rc.resolve_action_mode(2, 1, action) == "consensual"


class TestArchetypeRestraintDefaults:
    """아키타입 → 자제심 기본값 자동 적용.

    명시 `성격:자제심` prop 없어도 아키타입에 따라 값 결정.
    innocent는 강한 억제, seductive는 방종.
    """

    def test_no_archetype_no_restraint(self):
        """아키타입 설정 없음 → 0 (레거시 호환)"""
        morld.register_unit(1, name="주인공", props={"성별": 1})
        morld.register_unit(2, props={"성별": 2})
        assert rc.get_restraint_value(2) == 0

    def test_explicit_prop_overrides_archetype(self):
        """성격:자제심 prop 명시 → 아키타입 기본값 무시"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={
            "아키타입": "innocent",  # 기본 80
            "성격:자제심": 10,        # override
        })
        assert rc.get_restraint_value(2) == 10

    def test_innocent_archetype_high_restraint(self):
        """아키타입 prop = 'innocent' → 기본 80"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"아키타입": "innocent"})
        assert rc.get_restraint_value(2) == 80

    def test_seductive_archetype_low_restraint(self):
        """아키타입 prop = 'seductive' → 기본 10"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"아키타입": "seductive"})
        assert rc.get_restraint_value(2) == 10

    def test_personality_prop_maps_to_archetype(self):
        """성격 prop ('순진') → PERSONALITY_TO_ARCHETYPE → innocent → 80"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"성격": "순진"})
        # 성격 "순진" → archetype "innocent" → 기본 80
        assert rc.get_restraint_value(2) == 80

    def test_tsundere_archetype_restrained(self):
        """츤데레 → 겉 억제 (60)"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"아키타입": "tsundere"})
        assert rc.get_restraint_value(2) == 60

    def test_modifier_uses_archetype_default(self):
        """restraint_modifier도 아키타입 기본값 사용"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"아키타입": "innocent"})
        # 80 × -0.3 = -24
        assert rc.get_restraint_modifier(2) == -24.0

    def test_unknown_archetype_falls_back_to_50(self):
        """알 수 없는 아키타입 → 기본 50"""
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"아키타입": "nonexistent"})
        assert rc.get_restraint_value(2) == 50

    def test_all_archetypes_have_defaults(self):
        """모든 표준 아키타입에 기본값 정의되어 있음"""
        from engine import persona
        for archetype in persona.ARCHETYPES:
            assert archetype in rc.ARCHETYPE_RESTRAINT_DEFAULT, \
                f"archetype '{archetype}'에 자제심 기본값 누락"


class TestHarassmentSessionRestored:
    """성추행 루프 복원 검증 — 4단계 대칭 (Phase 0.6 롤백, 2026-04-23).

    성추행은 가벼운 비합의 루프 (lift/tear/grope, 삽입 없음).
    풀 강제 행위는 force_romance/start_romance(FORCED) — 별개.
    """

    def test_harassment_session_is_generator(self):
        """harassment_session이 generator로 복원되어 있음"""
        import harassment
        assert callable(harassment.harassment_session)
        # 생성 시 generator 반환
        morld.register_unit(1, name="주인공")
        morld.register_unit(2, props={"성별": 2})
        gen = harassment.harassment_session(1, 2)
        # generator 객체
        assert hasattr(gen, "__next__")

    def test_build_session_ui_renders_exposure(self):
        """_build_session_ui가 노출 상태를 표시"""
        import harassment
        morld.register_unit(2, props={
            "임시노출:상체": 2, "임시노출:하체": 0, "상태:절정": 25,
        })
        lines = harassment._build_session_ui(2, [], "")
        joined = "\n".join(lines)
        assert "노출" in joined
        assert "25" in joined

    def test_harassment_actions_catalog_unchanged(self):
        """HARASSMENT_ACTIONS 카탈로그는 유지 (8개)"""
        import harassment
        expected = {
            "lift_upper", "lift_lower", "tear_upper", "tear_lower",
            "breast_grope", "nipple_grope", "butt_grope", "genital_grope",
        }
        assert set(harassment.HARASSMENT_ACTIONS.keys()) == expected

    def test_instant_actions_forced_only_entries_exist(self):
        """romance INSTANT_ACTIONS에도 성추행 행위 엔트리 유지 (forced_only).

        풀 강제 세션(force_romance) 내에서는 여전히 접근 가능.
        """
        from romance_actions import INSTANT_ACTIONS
        for aid in ("lift_upper", "tear_upper", "breast_grope"):
            assert aid in INSTANT_ACTIONS
            assert INSTANT_ACTIONS[aid].get("forced_only") is True


class TestHarassmentEnabledAlias:
    """settings.is_harassment_enabled가 is_romance_enabled의 alias로 동작 (Phase 0.6+)."""

    def test_harassment_follows_romance_toggle(self):
        """connect 후 romance가 ON이면 harassment도 ON"""
        import settings
        # 플레이어 ID 필요
        morld.register_unit(1, name="주인공")
        morld._player_id = 1
        settings.set_romance_enabled(True)
        assert settings.is_romance_enabled() is True
        assert settings.is_harassment_enabled() is True
        settings.set_romance_enabled(False)
        assert settings.is_harassment_enabled() is False


class TestShameEventHooks:
    """수치심 변동 이벤트 — romance 발각 / near_miss / 자위 목격."""

    def _make_npc(self, shame=0, exposure_upper=0, exposure_lower=0):
        morld.register_unit(2, props={
            "상태:수치심": shame,
            "임시노출:상체": exposure_upper,
            "임시노출:하체": exposure_lower,
        })

    def test_apply_shame_clamps_max(self):
        """수치심 100 이상으로 증가 안 됨"""
        self._make_npc(shame=90)
        result = rc.apply_shame(2, 30)
        assert result == 100

    def test_apply_shame_clamps_min(self):
        """수치심 0 이하로 감소 안 됨"""
        self._make_npc(shame=5)
        result = rc.apply_shame(2, -20)
        assert result == 0

    def test_apply_shame_positive_delta(self):
        """수치심 중간 증가"""
        self._make_npc(shame=30)
        result = rc.apply_shame(2, 15)
        assert result == 45
        assert morld.get_unit_prop(2, "상태:수치심") == 45

    def test_on_romance_discovered_nude_state(self):
        """나체 상태로 들킴 → +20 (base) +10 (nude) = +30 적용.

        테스트 mock은 equipment 없음 → get_exposure_state가 nude 반환.
        실제 production에서 의류 장착 시 nude_bonus 없이 +20만 적용됨.
        """
        self._make_npc(shame=10)
        result = rc.on_romance_discovered(2)
        # mock에선 default nude → 10 + 30 = 40
        assert result == 40

    def test_on_stealth_near_miss_small_gain(self):
        """은신 성공 스릴 → +3 (약한 증가)"""
        self._make_npc(shame=50)
        result = rc.on_stealth_near_miss(2)
        assert result == 53

    def test_on_masturbation_witnessed_big_gain(self):
        """자위 목격 → +25 (큰 증가)"""
        self._make_npc(shame=20)
        result = rc.on_masturbation_witnessed(2)
        assert result == 45

    def test_on_nude_in_public_small_gain(self):
        """공공장소 노출 진입 → +5"""
        self._make_npc(shame=0)
        result = rc.on_nude_in_public(2)
        assert result == 5

    def test_shame_chain_multiple_events(self):
        """여러 이벤트 중첩 시 누적 (100 cap까지). mock은 default nude."""
        self._make_npc(shame=0)
        rc.on_nude_in_public(2)         # +5 → 5
        rc.on_stealth_near_miss(2)      # +3 → 8
        rc.on_masturbation_witnessed(2) # +25 → 33
        rc.on_romance_discovered(2)     # +30 (nude bonus) → 63
        assert morld.get_unit_prop(2, "상태:수치심") == 63

    def test_shame_decay_tick_reduces(self):
        """수치심 감쇠 tick 1회 → -5"""
        self._make_npc(shame=30)
        rc.apply_shame(2, 0)  # 레지스트리 등록 트리거 (값 동일)
        # 직접 등록 (apply_shame(0)은 값 변경 없이 레지스트리 업데이트)
        rc._SHAME_REGISTRY.add(2)
        rc._decay_shame_tick()
        assert morld.get_unit_prop(2, "상태:수치심") == 25

    def test_shame_decay_clamps_at_zero(self):
        """수치심 5 → tick 1회 → 0, 레지스트리에서 제거"""
        self._make_npc(shame=3)
        rc._SHAME_REGISTRY.add(2)
        rc._decay_shame_tick()
        assert morld.get_unit_prop(2, "상태:수치심") == 0
        assert 2 not in rc._SHAME_REGISTRY

    def test_shame_registry_tracks_apply(self):
        """apply_shame 호출 시 레지스트리에 자동 등록"""
        self._make_npc(shame=0)
        rc._SHAME_REGISTRY.discard(2)  # 선제 정리
        rc.apply_shame(2, 20)
        assert 2 in rc._SHAME_REGISTRY
        # 0까지 감소 시 자동 제거
        rc.apply_shame(2, -100)
        assert 2 not in rc._SHAME_REGISTRY

    def test_shame_affects_gate_after_event(self):
        """수치심 상승 이후 관객 상황에서 게이트 점수 감소"""
        loc = (0, 0)
        morld.register_location(*loc, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", props={"성별": 1}, location=loc)
        morld.register_unit(2, props={
            "관계:주인공:호감": 50,
            "성별": 2,
        }, location=loc)
        morld.register_unit(3, name="행인", location=loc)

        action = {"affection_req": 30, "effects": {}}
        score_before = rc.calculate_availability_score(2, 1, action)
        assert score_before == 20

        # 발각 이벤트 → 수치심 상승 (mock nude → +30)
        rc.on_romance_discovered(2)
        score_after = rc.calculate_availability_score(2, 1, action)
        # baseline 20 - 수치심(30) × 0.2 × 0.7 = 20 - 4.2 = 15.8
        assert abs(score_after - 15.8) < 0.1


class TestAudienceFactor:
    """관객 계수 — 같은 location의 제3자 존재 여부."""

    def test_solo_location_no_audience(self):
        """같은 location에 플레이어 + 파트너만 → 관객 0"""
        morld.register_location(0, 0)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        assert rc.get_audience_factor(2) == 0.0

    def test_third_party_triggers_audience(self):
        """같은 location에 제3자 → 관객 factor > 0 (은신 기본 30% 차감)"""
        morld.register_location(0, 0, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        morld.register_unit(3, name="행인", location=(0, 0))
        # density 1.0 × indoor 1.0 × (1 - 0.3 stealth) = 0.7
        assert abs(rc.get_audience_factor(2) - 0.7) < 0.001

    def test_audience_scales_with_density(self):
        """좁은 공간 (length=1) vs 넓은 공간 (length=5) 밀도 차이"""
        morld.register_location(0, 0, is_indoor=True, length=5)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        morld.register_unit(3, name="행인", location=(0, 0))
        # density 1/5 = 0.2 × 1.0 × 0.7 = 0.14
        assert abs(rc.get_audience_factor(2) - 0.14) < 0.01

    def test_outdoor_increases_factor(self):
        """야외: visibility_mult 1.2 적용"""
        morld.register_location(0, 0, is_indoor=False, length=1)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        morld.register_unit(3, name="행인", location=(0, 0))
        # density 1.0 × outdoor 1.2 × 0.7 = 0.84
        assert abs(rc.get_audience_factor(2) - 0.84) < 0.01

    def test_stealth_reduces_factor(self):
        """플레이어 은신 상태 → factor 감소 (은신 성공률 70%)"""
        morld.register_location(0, 0, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", location=(0, 0),
                            props={"status:stealth": 1})
        morld.register_unit(2, location=(0, 0))
        morld.register_unit(3, name="행인", location=(0, 0))
        # density 1.0 × indoor 1.0 × (1 - 0.7 stealth) = 0.3
        assert abs(rc.get_audience_factor(2) - 0.3) < 0.001

    def test_multiple_third_parties_saturate_density(self):
        """좁은 공간 + 다수 관객 → density cap 1.0"""
        morld.register_location(0, 0, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        for i in range(3, 8):  # 5명 행인
            morld.register_unit(i, name=f"행인{i}", location=(0, 0))
        # density min(1.0, 5/1) = 1.0, factor = 0.7 (length 1에 cap)
        assert abs(rc.get_audience_factor(2) - 0.7) < 0.001

    def test_different_location_no_audience(self):
        """다른 location의 NPC는 관객 아님"""
        morld.register_location(0, 0)
        morld.register_location(0, 1)
        morld.register_unit(1, name="주인공", location=(0, 0))
        morld.register_unit(2, location=(0, 0))
        morld.register_unit(3, name="행인", location=(0, 1))
        assert rc.get_audience_factor(2) == 0.0


class TestShameModifier:
    """수치심 × 관객 계수 — 상황적 억제."""

    def _setup_with_audience(self, affection=50, shame=0, with_audience=False,
                              is_indoor=True, length=1):
        loc = (0, 0)
        morld.register_location(*loc, is_indoor=is_indoor, length=length)
        morld.register_unit(1, name="주인공", props={"성별": 1}, location=loc)
        morld.register_unit(2, props={
            "관계:주인공:호감": affection,
            "상태:수치심": shame,
            "성별": 2,
        }, location=loc)
        if with_audience:
            morld.register_unit(3, name="행인", props={"성별": 1}, location=loc)

    def test_shame_without_audience_no_penalty(self):
        """관객 없으면 수치심이 아무리 높아도 페널티 0"""
        self._setup_with_audience(shame=100, with_audience=False)
        assert rc.get_shame_modifier(2) == 0.0

    def test_shame_with_audience_penalizes(self):
        """수치심 100 + 좁은 실내 + 비은신 관객 → -14점 (0.7 factor)"""
        self._setup_with_audience(shame=100, with_audience=True)
        # shame × 0.2 × factor(0.7) = 100 × 0.2 × 0.7 = 14
        assert abs(rc.get_shame_modifier(2) - (-14.0)) < 0.01

    def test_shame_in_wide_space_smaller_penalty(self):
        """넓은 공간 (length 5) → 밀도 감소 → 페널티 감소"""
        self._setup_with_audience(shame=100, with_audience=True, length=5)
        # factor = 0.2 (density) × 1.0 × 0.7 = 0.14
        # penalty = 100 × 0.2 × 0.14 = 2.8
        assert abs(rc.get_shame_modifier(2) - (-2.8)) < 0.1

    def test_shame_outdoor_stronger_penalty(self):
        """야외 시야 보너스 → 페널티 1.2배"""
        self._setup_with_audience(shame=100, with_audience=True, is_indoor=False)
        # factor = 1.0 × 1.2 × 0.7 = 0.84
        # penalty = 100 × 0.2 × 0.84 = 16.8
        assert abs(rc.get_shame_modifier(2) - (-16.8)) < 0.1

    def test_shame_with_audience_blocks_consensual(self):
        """호감 경계값 + 수치심 + 관객 → 페널티로 forced 분기"""
        self._setup_with_audience(affection=45, shame=100, with_audience=True)
        action = {"affection_req": 30, "effects": {}}
        # baseline = 45 - 30 = 15
        # shame penalty = -100 × 0.2 × 0.7 = -14
        # total = 1 (consensual 경계)
        assert rc.resolve_action_mode(2, 1, action) == "consensual"
        # 조금 낮추면 forced
        morld.set_unit_prop(2, "관계:주인공:호감", 43)
        assert rc.resolve_action_mode(2, 1, action) == "forced"

    def test_restraint_and_shame_stack(self):
        """자제심 + 수치심(관객) 양쪽 페널티 누적"""
        loc = (0, 0)
        morld.register_location(*loc, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", props={"성별": 1}, location=loc)
        morld.register_unit(2, props={
            "관계:주인공:호감": 80,
            "성격:자제심": 50,      # -15점
            "상태:수치심": 50,      # shame × 0.2 × 0.7 = -7
            "성별": 2,
        }, location=loc)
        morld.register_unit(3, name="행인", location=loc)
        action = {"affection_req": 30, "effects": {}}
        score = rc.calculate_availability_score(2, 1, action)
        # baseline = 80 - 30 = 50
        # restraint = -15
        # shame = -7
        # total = 28
        assert abs(score - 28) < 0.1
        assert rc.resolve_action_mode(2, 1, action) == "consensual"
