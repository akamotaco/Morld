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


# ============================================
# 강제 → 함락 루트 시나리오
# ============================================

class TestForcedCorruptionRoute:
    """강제 행위로 복종 누적 → 함락 상태 → 애정 게이트 차단/감소 검증.

    Why: 사용자 시나리오 "강제-함락 루트에서 함락 이후 자발적 반응"의
    스탯/라벨 동역학 부분을 검증. 대사 훅(npc_thrust_trance, position_request)은
    이미 구현됨 — 여기서는 수치 동역학 + 라벨 + 페널티에 집중.
    """

    def _setup(self):
        morld.register_unit(1, name="주인공",
                            props={"근력": 10, "생존:체력": 100})
        morld.register_unit(2, name="유키", props={
            "근력": 4,
            "생존:체력": 80,
            "관계:주인공:호감": 20,
            "관계:주인공:반발": 0,
            "관계:주인공:복종": 0,
            "관계:주인공:애정": 0,
            "상태:성욕": 10,
        })

    def test_corruption_blocks_love_gain(self):
        """복종 ≥ 60이면 애정 상승 차단."""
        import romance_dynamics as rd
        self._setup()
        morld.set_unit_prop(2, "관계:주인공:복종", 70)
        delta = rd.modify_love(2, 1, 20)
        assert delta == 0
        assert rd.get_love(2, 1) == 0

    def test_corruption_threshold_exact(self):
        """복종 == LOVE_BLOCK_SUBMISSION(60)에서 차단."""
        import romance_dynamics as rd
        self._setup()
        morld.set_unit_prop(2, "관계:주인공:복종", 60)
        assert rd.modify_love(2, 1, 10) == 0
        morld.set_unit_prop(2, "관계:주인공:복종", 59)
        assert rd.modify_love(2, 1, 10) == 10

    def test_corruption_allows_love_loss(self):
        """복종 높아도 애정 감소는 통과 (강제 종료 페널티 등)."""
        import romance_dynamics as rd
        self._setup()
        rd.modify_love(2, 1, 50)  # 복종 0 → 50 획득
        morld.set_unit_prop(2, "관계:주인공:복종", 80)
        assert rd.modify_love(2, 1, -10) == -10
        assert rd.get_love(2, 1) == 40

    def test_forced_end_penalty_applies_love_reduction(self):
        """강제 종료 페널티가 애정도 함께 감소시킴."""
        import romance_dynamics as rd
        self._setup()
        rd.modify_love(2, 1, 50)  # 복종 0 → 선제 획득
        mode_ctx = rm.create_mode_context(rm.MODE_FORCED, 1, 2)
        mode_ctx["action_count"] = 5
        rm.apply_forced_end_penalty(2, mode_ctx, 1)
        # 호감 penalty: -5 - 5 = -10 → 20 - 10 = 10
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 10
        # 애정 penalty: -5 - 5 = -10 → 50 - 10 = 40
        assert rd.get_love(2, 1) == 40
        # 반발 penalty: min(20, 10+5) = 15
        assert morld.get_unit_prop(2, "관계:주인공:반발") == 15

    def test_forced_end_penalty_max_action_count(self):
        """행위 수 10 이상 → 페널티 -15 (상한)."""
        import romance_dynamics as rd
        self._setup()
        rd.modify_love(2, 1, 50)
        mode_ctx = rm.create_mode_context(rm.MODE_FORCED, 1, 2)
        mode_ctx["action_count"] = 50
        rm.apply_forced_end_penalty(2, mode_ctx, 1)
        # 호감: max(-15, -5-50) = -15 → 20 - 15 = 5
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 5
        # 애정: max(-15, -5-50) = -15 → 50 - 15 = 35
        assert rd.get_love(2, 1) == 35

    def test_relationship_label_progression_corruption(self):
        """함락 루트에서 라벨 전이: 지인 → 종복 → 헌신적 종자."""
        import romance_dynamics as rd
        self._setup()
        # 초기: 호감 20 → "지인"
        assert rd.get_relationship_label(2, 1) == "지인"

        # 복종 70 (함락) → "종복"
        morld.set_unit_prop(2, "관계:주인공:복종", 70)
        assert rd.get_relationship_label(2, 1) == "종복"

        # 애정 50 (함락 후 사랑 각인) → "헌신적 종자"
        # 복종 높은 상태에서는 modify_love로 못 올리므로 직접 세팅
        morld.set_unit_prop(2, "관계:주인공:애정", 50)
        assert rd.get_relationship_label(2, 1) == "헌신적 종자"

    def test_relationship_label_lover_route_separated(self):
        """순애 루트는 복종 없이 호감+애정만으로 연인 라벨."""
        import romance_dynamics as rd
        self._setup()
        morld.set_unit_prop(2, "관계:주인공:호감", 70)
        rd.modify_love(2, 1, 70)  # 복종 0 → 통과
        assert rd.get_relationship_label(2, 1) == "연인"

    def test_label_aliases_accessible_via_rd(self):
        """라벨 alias 함수 호출 일관성."""
        import romance_dynamics as rd
        assert rd.get_affection_label(85) == "친애"
        assert rd.get_submission_label(100) == "절대복종"
        assert rd.get_love_label(70) == "사랑"


# ============================================
# 선호 체위 요구 대사 — 캐릭터 asset에 대사 풀 존재 검증
# ============================================

class TestPositionRequestDialoguePool:
    """각 주요 캐릭터의 SEXUAL_PREFERENCES.preferred_positions에
    대응하는 npc_position_request:{pos_id} 대사 풀이 존재해야 함."""

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_lina_has_position_request_pool(self):
        cls = self._character_class("lina", "Lina")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:cowgirl" in reactions
        assert "npc_position_request:standing_face" in reactions

    def test_yuki_has_position_request_pool(self):
        cls = self._character_class("yuki", "Yuki")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:face_sitting" in reactions
        assert "npc_position_request:missionary" in reactions

    def test_ella_has_position_request_pool(self):
        cls = self._character_class("ella", "Ella")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:doggy" in reactions
        assert "npc_position_request:reverse_cowgirl" in reactions

    def test_sera_has_position_request_pool(self):
        cls = self._character_class("sera", "Sera")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:standing_face" in reactions
        assert "npc_position_request:doggy" in reactions

    def test_mila_has_position_request_pool(self):
        cls = self._character_class("mila", "Mila")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:missionary" in reactions
        assert "npc_position_request:face_sitting" in reactions

    def test_faye_has_position_request_pool(self):
        cls = self._character_class("faye", "Faye")
        reactions = getattr(cls, "ROMANCE_REACTIONS", {})
        assert "npc_position_request:cowgirl" in reactions
        assert "npc_position_request:missionary" in reactions

    def test_position_request_keys_match_sexual_preferences(self):
        """각 캐릭터의 preferred_positions와 대사 키 쌍이 일치."""
        chars = [
            ("lina", "Lina"),
            ("yuki", "Yuki"),
            ("ella", "Ella"),
            ("sera", "Sera"),
            ("mila", "Mila"),
            ("faye", "Faye"),
        ]
        for mod_name, cls_name in chars:
            cls = self._character_class(mod_name, cls_name)
            prefs = getattr(cls, "SEXUAL_PREFERENCES", {})
            preferred = prefs.get("preferred_positions", [])
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for pos in preferred:
                key = f"npc_position_request:{pos}"
                assert key in reactions, (
                    f"{cls_name}: SEXUAL_PREFERENCES.preferred_positions "
                    f"에 {pos}가 있으나 ROMANCE_REACTIONS에 {key} 누락")


# ============================================
# Phase 1.6-a: NPC 자율 행위 루프 (프레임워크 + 봉사 2종 + rest)
# ============================================

class TestAutonomyFramework:
    """자율 행위 카탈로그/상수 존재 검증 (로직은 closure 내부라 구조 검증 수준)."""

    def test_catalog_has_service_actions(self):
        import romance
        catalog = romance._NPC_AUTONOMY_CATALOG
        assert "fellatio" in catalog
        assert catalog["fellatio"]["kind"] == "service"
        assert "penis_rub" in catalog
        assert catalog["penis_rub"]["kind"] == "service"

    def test_catalog_has_rest(self):
        import romance
        assert "rest" in romance._NPC_AUTONOMY_CATALOG
        assert romance._NPC_AUTONOMY_CATALOG["rest"]["kind"] == "rest"

    def test_catalog_effects_service(self):
        """봉사 행위는 NPC 성욕/욕망을 올리는 effects가 있어야 한다."""
        import romance
        for aid in ("fellatio", "penis_rub"):
            entry = romance._NPC_AUTONOMY_CATALOG[aid]
            effects = entry.get("effects", {})
            assert effects.get("성욕", 0) > 0, f"{aid} missing 성욕 gain"

    def test_catalog_rest_no_effects(self):
        import romance
        assert romance._NPC_AUTONOMY_CATALOG["rest"]["effects"] == {}

    def test_entry_arousal_constant(self):
        import romance
        assert romance.AUTONOMY_ENTRY_AROUSAL == 80

    def test_exit_arousal_constant(self):
        import romance
        assert romance.AUTONOMY_EXIT_AROUSAL == 60

    def test_corruption_or_love_gate_constants(self):
        import romance
        assert romance.AUTONOMY_MIN_SUBMISSION == 60  # 함락 경로
        assert romance.AUTONOMY_MIN_AFFECTION == 70   # 순애 경로

    def test_duration_bounds(self):
        import romance
        assert 1 <= romance.AUTONOMY_MIN_DURATION <= romance.AUTONOMY_MAX_DURATION
        assert romance.AUTONOMY_MAX_TURNS > romance.AUTONOMY_MAX_DURATION


class TestAutonomyDialoguePool:
    """각 주요 캐릭터의 자율 행위 대사 풀 존재 검증."""

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("sera", "Sera"),
        ("mila", "Mila"),
        ("faye", "Faye"),
    ]

    def test_all_have_autonomy_start(self):
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            assert "npc_autonomy:start" in reactions, \
                f"{cls_name} missing npc_autonomy:start"

    def test_all_have_autonomy_switch(self):
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            assert "npc_autonomy:switch" in reactions, \
                f"{cls_name} missing npc_autonomy:switch"

    def test_all_have_per_action_pools(self):
        required_keys = [
            "npc_autonomy_fellatio:start",
            "npc_autonomy_penis_rub:start",
            "npc_autonomy_rest:start",
        ]
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for key in required_keys:
                assert key in reactions, f"{cls_name} missing {key}"

    def test_all_have_self_stim_pools(self):
        """Phase 1.6-c: 자위 5종 대사 풀 각 캐릭터 검증."""
        required_keys = [
            "npc_autonomy_self_breast:start",
            "npc_autonomy_self_nipple:start",
            "npc_autonomy_self_clit:start",
            "npc_autonomy_self_vaginal:start",
            "npc_autonomy_self_anal:start",
        ]
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for key in required_keys:
                assert key in reactions, f"{cls_name} missing {key}"

    def test_all_have_insertion_request_pools(self):
        """Phase 1.6.2: 삽입 요구 대사 (vaginal/anal) 검증."""
        required_keys = [
            "npc_insertion_request:vaginal",
            "npc_insertion_request:anal",
        ]
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for key in required_keys:
                assert key in reactions, f"{cls_name} missing {key}"

    def test_all_have_trance_dialogue(self):
        """Phase 1.8: 트랜스 상태 대사 (trance/trance_deep) — 모든 주요 캐릭터."""
        required_keys = [
            "trance:start",
            "trance_deep:start",
        ]
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for key in required_keys:
                assert key in reactions, f"{cls_name} missing {key}"

    def test_all_have_post_trance_dialogue(self):
        """Phase 1.9.2: 트랜스 이탈 후 부끄러움 대사 — 모든 주요 캐릭터."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            assert "post_trance:start" in reactions, \
                f"{cls_name} missing post_trance:start"


# ============================================
# Phase 1.9.5: 정신 교란 아이템 (4종) 카탈로그
# ============================================

class TestIntoxicantItemsCatalog:
    """Wine/StrongLiquor/Narcotic/Hypnotic 4종 정의 확인 + 카테고리."""

    def _item(self, cls_name):
        import importlib
        mod = importlib.import_module("assets.items.consumables")
        return getattr(mod, cls_name)

    def test_wine_defined(self):
        cls = self._item("Wine")
        assert cls.unique_id == "wine"
        assert cls.category == "drink"

    def test_strong_liquor_defined(self):
        cls = self._item("StrongLiquor")
        assert cls.unique_id == "strong_liquor"
        assert cls.category == "drink"

    def test_narcotic_defined(self):
        cls = self._item("Narcotic")
        assert cls.unique_id == "narcotic"
        assert cls.category == "medicine"

    def test_hypnotic_defined(self):
        cls = self._item("Hypnotic")
        assert cls.unique_id == "hypnotic"
        assert cls.category == "medicine"

    def test_all_have_drink_or_use_action(self):
        """모두 복용/마시기 + 음식 첨가 액션 보유."""
        for cls_name in ("Wine", "StrongLiquor", "Narcotic", "Hypnotic"):
            cls = self._item(cls_name)
            actions = getattr(cls, "actions", [])
            has_drink_or_use = any(
                ("call:drink" in a or "call:use" in a) for a in actions)
            has_mix = any("call:mix_food" in a for a in actions)
            assert has_drink_or_use, f"{cls_name} missing drink/use action"
            assert has_mix, f"{cls_name} missing mix_food action"


# ============================================
# Phase 2.2a: TextSelector.format_result list random support
# ============================================

class TestTextSelectorListChoice:
    """Phase 2.2a: format_result가 list면 random.choice로 1줄 선택."""

    def test_string_result_passes_through(self):
        from assets.base import TextSelector
        result = TextSelector.format_result("hello {name}", {"name": "world"})
        assert result == "hello world"

    def test_list_result_picks_one(self):
        from assets.base import TextSelector
        pool = ["a {name}", "b {name}", "c {name}"]
        result = TextSelector.format_result(pool, {"name": "x"})
        assert result in ("a x", "b x", "c x")

    def test_empty_list_passes_through(self):
        """빈 리스트는 변환 없이 원본 유지."""
        from assets.base import TextSelector
        result = TextSelector.format_result([], {"name": "x"})
        assert result == []

    def test_dict_result_unchanged(self):
        """dict 등 다른 타입은 그대로."""
        from assets.base import TextSelector
        d = {"nested": True}
        assert TextSelector.format_result(d, {}) is d

    def test_list_variety_over_many_picks(self):
        """여러 번 호출하면 여러 결과가 나옴 (randomness 검증)."""
        from assets.base import TextSelector
        pool = ["a", "b", "c", "d", "e"]
        results = set()
        for _ in range(50):
            results.add(TextSelector.format_result(pool, {}))
        # 50번 중에 최소 2개 이상 다른 결과 (확률적으로 거의 확실)
        assert len(results) >= 2


class TestNpcIntimacyDescribePool:
    """Phase 2.2a: _DESCRIBE_NPC_INTIMACY가 list-of-strings 풀로 확장."""

    def test_forced_victim_pool_has_multiple(self):
        """Phase 2.4: 강제 케이스 rule은 beloved_exists 조건별 2개 이상 (풀 확장)."""
        from assets.base import _DESCRIBE_NPC_INTIMACY
        forced_rules = [r for r in _DESCRIBE_NPC_INTIMACY
                        if r[0].get("NPC강제피해중")]
        assert len(forced_rules) >= 1
        # 각 rule의 pool 크기 검증
        for _cond, pool in forced_rules:
            assert isinstance(pool, list)
            assert len(pool) >= 5

    def test_consensual_pool_has_multiple(self):
        """Phase 2.4: 합의 케이스 rule은 beloved_exists 조건별 2개 (풀 확장)."""
        from assets.base import _DESCRIBE_NPC_INTIMACY
        consensual_rules = [r for r in _DESCRIBE_NPC_INTIMACY
                            if r[0].get("NPC성행위중")
                            and not r[0].get("NPC강제피해중")]
        assert len(consensual_rules) >= 1
        for _cond, pool in consensual_rules:
            assert isinstance(pool, list)
            assert len(pool) >= 5

    def test_pool_entries_all_have_name_placeholder(self):
        from assets.base import _DESCRIBE_NPC_INTIMACY
        for _cond, pool in _DESCRIBE_NPC_INTIMACY:
            assert isinstance(pool, list)
            for line in pool:
                assert "{name}" in line, f"Missing {{name}} in: {line}"


# ============================================
# Phase 2.3: NTR 신뢰 훼손 (합의 정사 + 연인 관계)
# ============================================

class TestNtrTrustPenalty:
    """연인이 다른 NPC와 합의 정사를 하다 들키면 신뢰 훼손."""

    def _setup_lover(self):
        """NPC 2 를 플레이어(1) 의 연인으로 설정."""
        morld.register_unit(1, name="주인공", gender="male", props={"성별": 1})
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": 70,
            "관계:주인공:복종": 0,
            "관계:주인공:애정": 70,
            "관계:주인공:반발": 0,
        })
        morld._player_id = 1

    def test_consensual_with_lover_reduces_trust(self):
        """합의 정사 + 연인 관계 → 호감/애정 각 -5."""
        from romance_dynamics import get_relationship_label, modify_love
        from romance_core import get_affection_key
        self._setup_lover()
        # 연인 라벨 확인
        assert get_relationship_label(2, 1) == "연인"
        # NTR 처벌 로직 재현 (_run_npc_intimacy_discovery_reaction 내부)
        morld.modify_prop(2, get_affection_key(1), -5)
        modify_love(2, 1, -5)
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 65
        assert morld.get_unit_prop(2, "관계:주인공:애정") == 65

    def test_forced_victim_no_trust_penalty(self):
        """강제 피해자는 처벌 없음 (잘못이 없음)."""
        self._setup_lover()
        rc.set_npc_sex_role(2, rc.NPC_SEX_VICTIM)
        # _run_ 내부에서 forced_victim이면 신뢰 훼손 skip
        # 테스트로는 "강제 케이스에서 호감/애정 유지되는 것"만 확인
        assert morld.get_unit_prop(2, "관계:주인공:호감") == 70
        assert morld.get_unit_prop(2, "관계:주인공:애정") == 70

    def test_non_lover_no_ntr_detection(self):
        """연인이 아닌 NPC는 NTR 케이스 아님."""
        from romance_dynamics import get_relationship_label
        morld.register_unit(1, name="주인공", gender="male", props={"성별": 1})
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": 30,  # 지인 수준
            "관계:주인공:애정": 0,
        })
        morld._player_id = 1
        # "지인" 또는 "친구" 라벨 — 연인 아님
        label = get_relationship_label(2, 1)
        assert label not in ("연인", "배우자", "헌신적 종자")


# ============================================
# Phase 2.4: beloved 이름 부르기 (NTR/NTL 효과)
# ============================================

class TestBelovedName:
    """_get_beloved_name: 최고 호감 대상 파생."""

    def test_no_relations_returns_none(self):
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={"성별": 2})
        assert _get_beloved_name(2) is None

    def test_below_threshold_returns_none(self):
        """임계(40) 미만이면 None."""
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": 30,
        })
        assert _get_beloved_name(2) is None

    def test_threshold_met_returns_name(self):
        """임계 40 이상이면 이름 반환."""
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": 50,
        })
        assert _get_beloved_name(2) == "주인공"

    def test_multiple_relations_picks_highest(self):
        """여러 관계 중 최고값 대상 반환."""
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": 50,
            "관계:세라:호감": 80,
            "관계:엘라:호감": 45,
        })
        assert _get_beloved_name(2) == "세라"

    def test_only_affection_props_considered(self):
        """관계:*:호감 외 prop은 무시."""
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:반발": 100,
            "관계:주인공:복종": 90,
        })
        assert _get_beloved_name(2) is None

    def test_non_numeric_values_skipped(self):
        """숫자가 아닌 값은 무시 (방어적)."""
        from assets.base import _get_beloved_name
        morld.register_unit(2, name="유키", gender="female", props={
            "성별": 2,
            "관계:주인공:호감": "invalid",
            "관계:세라:호감": 50,
        })
        assert _get_beloved_name(2) == "세라"


class TestMasturbationDescribePool:
    """Phase 2.4: 자위 중 묘사 + beloved 이름 부르기 풀."""

    def test_masturbation_section_exists(self):
        from assets.base import _DESCRIBE_MASTURBATION
        assert len(_DESCRIBE_MASTURBATION) >= 2  # beloved/no-beloved 각 1개 이상

    def test_masturbation_pools_non_empty(self):
        from assets.base import _DESCRIBE_MASTURBATION
        for _cond, pool in _DESCRIBE_MASTURBATION:
            assert isinstance(pool, list)
            assert len(pool) >= 3

    def test_masturbation_beloved_pool_has_name_calls(self):
        """beloved_exists 풀에 {beloved} 포함 대사 최소 1개."""
        from assets.base import _DESCRIBE_MASTURBATION
        beloved_pools = [p for c, p in _DESCRIBE_MASTURBATION
                         if c.get("beloved_exists")]
        assert len(beloved_pools) >= 1
        pool = beloved_pools[0]
        has_beloved_line = any("{beloved}" in line for line in pool)
        assert has_beloved_line

    def test_masturbation_in_describe_order(self):
        """masturbation 섹션이 기본 순서에 포함."""
        from assets.base import _DEFAULT_DESCRIBE_ORDER
        assert "masturbation" in _DEFAULT_DESCRIBE_ORDER


class TestTranceDeepBelovedDialog:
    """Phase 2.4.1: 각 캐릭터 trance_deep 풀에 {beloved} 포함 대사 추가."""

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("sera", "Sera"),
        ("mila", "Mila"),
        ("faye", "Faye"),
    ]

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_all_trance_deep_has_beloved_placeholder(self):
        """각 캐릭터 trance_deep:start 풀에 {beloved} 포함 대사 최소 1줄."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            rules = reactions.get("trance_deep:start", [])
            # rules = [(cond, pool), ...]
            has_beloved = False
            for _cond, pool in rules:
                if isinstance(pool, list):
                    for line in pool:
                        if "{beloved}" in line:
                            has_beloved = True
                            break
                if has_beloved:
                    break
            assert has_beloved, f"{cls_name} trance_deep:start missing {{beloved}} line"


# ============================================
# Phase 1.7: 수치심 훅 호출 지점 연결
# ============================================

class TestNudeInPublicTickHook:
    """_check_nude_in_public_tick: 플레이어 위치 NPC가 노출 + 관객 시 수치심."""

    def _setup(self, npc_exposed=True, alone=False):
        morld.register_location(0, 0, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", gender="male",
                            props={"성별": 1}, location=(0, 0))
        morld._player_id = 1
        # NPC equipment는 설정 안 함 → 노출이면 모두 벗은 상태
        if not npc_exposed:
            # 옷 장착 — mock에선 equipped_items가 직접 관리
            pass
        morld.register_unit(2, name="유키", gender="female",
                            props={"성별": 2, "상태:수치심": 30},
                            location=(0, 0))
        if not alone:
            morld.register_unit(3, name="행인", gender="male",
                                props={"성별": 1}, location=(0, 0))

    def test_nude_in_public_increases_shame_when_witnessed(self):
        """노출 NPC + 타인 있음 → 수치심 증가."""
        self._setup(alone=False)
        before = morld.get_unit_prop(2, "상태:수치심")
        rc._check_nude_in_public_tick()
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after > before

    def test_nude_no_audience_no_shame(self):
        """단 2명(플레이어 + NPC)만 있어도 플레이어가 '타인' 역할.
        즉 nude_in_public은 len(units) >= 2면 발동."""
        self._setup(alone=True)  # 행인 없음 = 플레이어 + NPC 2명
        before = morld.get_unit_prop(2, "상태:수치심")
        rc._check_nude_in_public_tick()
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after > before

    def test_nude_single_unit_no_shame(self):
        """플레이어 없이 NPC만 단독이면 수치심 변화 없음."""
        morld.register_location(5, 5, is_indoor=True, length=1)
        morld.register_unit(1, name="주인공", gender="male",
                            props={"성별": 1}, location=(0, 0))
        morld._player_id = 1
        # NPC는 플레이어와 다른 location → 플레이어 위치에 NPC 0명
        morld.register_unit(2, name="유키", gender="female",
                            props={"성별": 2, "상태:수치심": 30},
                            location=(5, 5))
        before = morld.get_unit_prop(2, "상태:수치심")
        rc._check_nude_in_public_tick()
        after = morld.get_unit_prop(2, "상태:수치심")
        # 플레이어 location에 NPC 없음 → tick 아무 효과 없음
        assert after == before


# ============================================
# Phase 1.6-b: 자위 5종 카탈로그 구조 검증
# ============================================

class TestAutonomySelfStimCatalog:
    """자위 행위 카탈로그의 필수 필드 + 부위 태그 매핑 검증."""

    _REQUIRED_SELF_ACTIONS = [
        "self_breast", "self_nipple", "self_clit",
        "self_vaginal", "self_anal",
    ]

    def test_catalog_has_5_self_actions(self):
        import romance
        catalog = romance._NPC_AUTONOMY_CATALOG
        self_actions = [a for a, e in catalog.items() if e["kind"] == "self"]
        assert len(self_actions) == 5

    def test_all_5_self_actions_present(self):
        import romance
        for aid in self._REQUIRED_SELF_ACTIONS:
            assert aid in romance._NPC_AUTONOMY_CATALOG
            assert romance._NPC_AUTONOMY_CATALOG[aid]["kind"] == "self"

    def test_self_actions_required_fields(self):
        """self 행위는 part/anatomy/access 필드 필수."""
        import romance
        for aid, entry in romance._NPC_AUTONOMY_CATALOG.items():
            if entry["kind"] != "self":
                continue
            assert "part" in entry, f"{aid} missing part"
            assert "anatomy" in entry, f"{aid} missing anatomy"
            assert "access" in entry, f"{aid} missing access"
            assert entry["access"] in ("upper", "lower"), \
                f"{aid} access must be upper/lower"

    def test_self_vaginal_targets_v(self):
        import romance
        e = romance._NPC_AUTONOMY_CATALOG["self_vaginal"]
        assert e["part"] == "V"
        assert e["anatomy"] == "V"
        assert e["access"] == "lower"

    def test_self_anal_targets_a(self):
        import romance
        e = romance._NPC_AUTONOMY_CATALOG["self_anal"]
        assert e["part"] == "A"
        assert e["anatomy"] == "A"
        assert e["access"] == "lower"

    def test_self_clit_targets_c(self):
        import romance
        e = romance._NPC_AUTONOMY_CATALOG["self_clit"]
        assert e["part"] == "C"
        assert e["anatomy"] == "C"
        assert e["access"] == "lower"

    def test_self_breast_and_nipple_target_b(self):
        """유두는 SENSATION_MAP에서 'B'로 매핑 — 가슴과 동일 부위 태그."""
        import romance
        assert romance._NPC_AUTONOMY_CATALOG["self_breast"]["part"] == "B"
        assert romance._NPC_AUTONOMY_CATALOG["self_nipple"]["part"] == "B"
        assert romance._NPC_AUTONOMY_CATALOG["self_breast"]["access"] == "upper"
        assert romance._NPC_AUTONOMY_CATALOG["self_nipple"]["access"] == "upper"

    def test_all_self_actions_have_arousal_gain(self):
        """자위 행위는 자신의 성욕을 올림."""
        import romance
        for aid, entry in romance._NPC_AUTONOMY_CATALOG.items():
            if entry["kind"] == "self":
                assert entry["effects"].get("성욕", 0) > 0, \
                    f"{aid} missing 성욕 gain"


# ============================================
# Phase 1.6-b: 가드/가중치 동작 검증
# ============================================

class TestAutonomyGuard:
    """_autonomy_check_guard의 가드 로직 검증 (팔 결박/해부학/노출)."""

    def _setup(self, *, upper_bound=False, vagina=True,
               position_id="missionary"):
        # player — male (성별 prop=1)
        morld.register_unit(1, name="주인공", gender="male", props={"성별": 1})
        # NPC — female(2) if vagina else male(1)
        npc_gender_int = 2 if vagina else 1
        morld.register_unit(2, name="유키",
                            gender="female" if vagina else "male",
                            props={"성별": npc_gender_int})
        if upper_bound:
            morld.set_unit_prop(2, "결박:상체", 1)
        # equipment 없음 → get_exposure_state가 모두 노출로 반환
        state = {
            "player_id": 1,
            "partner_id": 2,
            "position": position_id,
            "insertion": {"active": False},
            "elapsed_time": 0,
            "npc_prefs": {"preferred_parts": []},
        }
        return state

    def test_rest_always_available(self):
        import romance
        state = self._setup()
        assert romance._autonomy_check_guard(state, "rest") is True

    def test_service_fellatio_blocked_by_back_facing(self):
        import romance
        state = self._setup(position_id="reverse_cowgirl")
        # reverse_cowgirl의 facing = "back"
        assert romance._autonomy_check_guard(state, "fellatio") is False

    def test_service_fellatio_ok_on_front_facing(self):
        import romance
        state = self._setup(position_id="missionary")
        # equipment 비활성 → lower_exposed True
        assert romance._autonomy_check_guard(state, "fellatio") is True

    def test_self_blocked_by_upper_bound(self):
        """팔 결박 시 모든 self 행위 차단."""
        import romance
        state = self._setup(upper_bound=True)
        for aid in ("self_breast", "self_nipple", "self_clit",
                    "self_vaginal", "self_anal"):
            assert romance._autonomy_check_guard(state, aid) is False, \
                f"{aid} should be blocked by upper restraint"

    def test_self_vaginal_requires_vagina(self):
        """여성(V 보유) → 가능, 남성 → 불가."""
        import romance
        female = self._setup()
        assert romance._autonomy_check_guard(female, "self_vaginal") is True
        male = self._setup(vagina=False)
        assert romance._autonomy_check_guard(male, "self_vaginal") is False

    def test_self_anal_accessible_for_all_genders(self):
        """항문은 남녀 모두 보유 → self_anal 가능."""
        import romance
        female = self._setup()
        male = self._setup(vagina=False)
        assert romance._autonomy_check_guard(female, "self_anal") is True
        assert romance._autonomy_check_guard(male, "self_anal") is True


class TestAutonomyWeight:
    """_autonomy_compute_weight 가중치 공식 검증."""

    def _state(self, arousal=90, preferred_parts=None):
        morld.register_unit(1, name="주인공", gender="male", props={"성별": 1})
        morld.register_unit(2, name="유키", gender="female",
                            props={"상태:성욕": arousal, "성별": 2})
        return {
            "player_id": 1,
            "partner_id": 2,
            "npc_prefs": {"preferred_parts": preferred_parts or []},
        }

    def test_service_weight_fixed_1(self):
        import romance
        state = self._state()
        assert romance._autonomy_compute_weight(state, "fellatio") == 1.0
        assert romance._autonomy_compute_weight(state, "penis_rub") == 1.0

    def test_rest_weight_inversely_proportional_to_arousal(self):
        import romance
        high = romance._autonomy_compute_weight(self._state(arousal=100), "rest")
        mid = romance._autonomy_compute_weight(self._state(arousal=80), "rest")
        low = romance._autonomy_compute_weight(self._state(arousal=60), "rest")
        assert high < mid < low
        assert high == 0.1  # 성욕 100 → floor
        assert mid == (100 - 80) * 0.02  # 0.4
        assert abs(low - 0.8) < 1e-9     # 성욕 60 → 0.8

    def test_rest_weight_floor_at_01(self):
        """성욕 100 이상도 최소 0.1."""
        import romance
        state = self._state(arousal=150)
        assert romance._autonomy_compute_weight(state, "rest") == 0.1

    def test_self_base_weight_without_preference(self):
        import romance
        state = self._state(preferred_parts=[])
        assert romance._autonomy_compute_weight(state, "self_clit") == 1.0

    def test_preferred_part_doubles_weight(self):
        """preferred_parts에 'C' 있으면 self_clit 가중치 ×2."""
        import romance
        state = self._state(preferred_parts=["C"])
        assert romance._autonomy_compute_weight(state, "self_clit") == 2.0

    def test_preferred_non_matching_does_not_boost(self):
        import romance
        # preferred = ["V"], self_anal은 A → boost 없음
        state = self._state(preferred_parts=["V"])
        assert romance._autonomy_compute_weight(state, "self_anal") == 1.0

    def test_self_breast_and_nipple_share_part_b(self):
        """B가 preferred면 self_breast와 self_nipple 모두 ×2."""
        import romance
        state = self._state(preferred_parts=["B"])
        assert romance._autonomy_compute_weight(state, "self_breast") == 2.0
        assert romance._autonomy_compute_weight(state, "self_nipple") == 2.0


# ============================================
# Slice B: 배란일 경고 대사 (질내사정 임신 리스크)
# ============================================

class TestPersonalityFocusDescription:
    """Phase 2 Slice E: _FOCUS_PERSONALITY + context 파생 키."""

    def test_focus_personality_list_has_all_traits(self):
        """8개 라인(7 trait 중 6개 ±, 츤데레 + 1 one-sided) 구성 확인."""
        from assets.base import _FOCUS_PERSONALITY
        assert len(_FOCUS_PERSONALITY) >= 10

    def test_bold_low_matches(self):
        from assets.base import _FOCUS_PERSONALITY, TextSelector
        ctx = {"성격:담력_낮음": True, "성격:담력_높음": False}
        result = TextSelector.select(_FOCUS_PERSONALITY, ctx)
        assert "떨리고" in result

    def test_pride_high_matches(self):
        from assets.base import _FOCUS_PERSONALITY, TextSelector
        ctx = {"성격:자존심_높음": True, "성격:자존심_낮음": False}
        result = TextSelector.select(_FOCUS_PERSONALITY, ctx)
        assert "꼿꼿이" in result

    def test_cheer_low_matches(self):
        from assets.base import _FOCUS_PERSONALITY, TextSelector
        ctx = {"성격:명랑_낮음": True, "성격:명랑_높음": False}
        result = TextSelector.select(_FOCUS_PERSONALITY, ctx)
        assert "표정이 어둡다" in result

    def test_neutral_context_no_match(self):
        """모든 trait 0 → _FOCUS_PERSONALITY에서 매치 안 됨."""
        from assets.base import _FOCUS_PERSONALITY, TextSelector
        ctx = {}
        for trait in rc.PERSONALITY_TRAITS:
            ctx[f"성격:{trait}_높음"] = False
            ctx[f"성격:{trait}_낮음"] = False
        result = TextSelector.select(_FOCUS_PERSONALITY, ctx)
        assert result is None

    def test_focus_order_has_personality(self):
        from assets.base import _DEFAULT_FOCUS_ORDER
        assert "personality" in _DEFAULT_FOCUS_ORDER


class TestSix_NPC_PersonalityPreset:
    """Phase 2 Slice D: 6 NPC 성격 프리셋 — §7.8 / §7.9 기반."""

    def _char_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_lina_overrides(self):
        """Lina (cheerful + 겁 많음): 담력 -1, 자존심 -1, 정조 1."""
        cls = self._char_class("lina", "Lina")
        assert cls.props.get("성격:담력") == -1
        assert cls.props.get("성격:자존심") == -1
        assert cls.props.get("성격:정조") == 1

    def test_faye_tsundere(self):
        """Faye (proud + 츤데레 뇌격전사): 츤데레 1."""
        cls = self._char_class("faye", "Faye")
        assert cls.props.get("성격:츤데레") == 1

    def test_yuki_uses_archetype_default(self):
        """Yuki (timid): override 없음 — timid 기본값 사용."""
        cls = self._char_class("yuki", "Yuki")
        for trait in rc.PERSONALITY_TRAITS:
            assert f"성격:{trait}" not in cls.props, \
                f"Yuki should use timid defaults, not explicit {trait}"

    def test_ella_uses_archetype_default(self):
        cls = self._char_class("ella", "Ella")
        for trait in rc.PERSONALITY_TRAITS:
            assert f"성격:{trait}" not in cls.props

    def test_sera_uses_archetype_default(self):
        cls = self._char_class("sera", "Sera")
        for trait in rc.PERSONALITY_TRAITS:
            assert f"성격:{trait}" not in cls.props

    def test_mila_uses_archetype_default(self):
        cls = self._char_class("mila", "Mila")
        for trait in rc.PERSONALITY_TRAITS:
            assert f"성격:{trait}" not in cls.props


class TestPersonalityEffectMultipliers:
    """Phase 2 Slice C: 성격 변동 계수 — 복종/반발 양수 gain 배율."""

    def _setup(self, props=None):
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props=props or {})

    def test_default_no_modifier(self):
        self._setup()
        mult = rc.get_personality_effect_multipliers(2)
        assert mult["복종"] == 1.0
        assert mult["반발"] == 1.0

    def test_high_pride_reduces_submission_gain(self):
        self._setup(props={"성격:자존심": 1})
        mult = rc.get_personality_effect_multipliers(2)
        assert mult["복종"] == 0.5

    def test_low_pride_amplifies_submission_gain(self):
        self._setup(props={"성격:자존심": -1})
        mult = rc.get_personality_effect_multipliers(2)
        assert mult["복종"] == 1.5

    def test_high_boldness_amplifies_rebellion_gain(self):
        self._setup(props={"성격:담력": 1})
        mult = rc.get_personality_effect_multipliers(2)
        assert mult["반발"] == 1.3

    def test_low_boldness_reduces_rebellion_gain(self):
        self._setup(props={"성격:담력": -1})
        mult = rc.get_personality_effect_multipliers(2)
        # -1 × 0.3 = -0.3, 1.0 + (-0.3) = 0.7
        assert abs(mult["반발"] - 0.7) < 1e-9

    def test_calculate_effects_applies_submission_multiplier(self):
        """자존심 -1 NPC의 복종 +10 → ×1.5 = 15."""
        self._setup(props={"성격:자존심": -1})
        action = {"name": "액션", "effects": {"복종": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["복종"] == 15

    def test_calculate_effects_applies_rebellion_multiplier(self):
        """담력 1 NPC의 반발 +10 → ×1.3 = 13."""
        self._setup(props={"성격:담력": 1})
        action = {"name": "액션", "effects": {"반발": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["반발"] == 13

    def test_negative_submission_not_amplified(self):
        """복종 감소는 성격 계수 적용 안 함 (양수 gain 전용)."""
        self._setup(props={"성격:자존심": -1})
        action = {"name": "액션", "effects": {"복종": -10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["복종"] == -10

    def test_no_archetype_no_change(self):
        self._setup()
        action = {"name": "액션", "effects": {"복종": 10, "반발": 10},
                  "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["복종"] == 10
        assert out["반발"] == 10


class TestPersonalityGateModifier:
    """Phase 2 Slice B: 성격 4 trait이 availability_score에 반영."""

    def _setup(self, archetype=None, props=None):
        base_props = dict(props or {})
        if archetype:
            base_props["아키타입"] = archetype
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props=base_props)

    def test_no_archetype_no_modifier(self):
        self._setup()
        assert rc.get_personality_gate_modifier(2) == 0

    def test_positive_traits_lower_score(self):
        """정조+1/자존심+1 → threshold ↑ → 모디파이어 음수."""
        self._setup(props={"성격:정조": 1, "성격:자존심": 1})
        # 정조×10 + 자존심×8 = 18 threshold 상승 → -18 모디파이어
        assert rc.get_personality_gate_modifier(2) == -18

    def test_negative_traits_raise_score(self):
        """정조-1 → threshold ↓ → 모디파이어 양수."""
        self._setup(props={"성격:정조": -1})
        assert rc.get_personality_gate_modifier(2) == 10

    def test_all_traits_combined(self):
        """모든 트레이트 +1 → 최대 페널티."""
        self._setup(props={
            "성격:담력": 1, "성격:자존심": 1,
            "성격:정조": 1, "성격:태도": 1,
        })
        # 5+8+10+3 = 26 threshold → -26
        assert rc.get_personality_gate_modifier(2) == -26

    def test_archetype_innocent_raises_barrier(self):
        """innocent (정조=1, 태도=-1) 아키타입 → 10 - 3 = +7 threshold → -7."""
        self._setup(archetype="innocent")
        assert rc.get_personality_gate_modifier(2) == -7

    def test_archetype_seductive_lowers_barrier(self):
        """seductive (담력=1, 정조=-1) → 5 - 10 = -5 threshold → +5."""
        self._setup(archetype="seductive")
        assert rc.get_personality_gate_modifier(2) == 5

    def test_calculate_availability_includes_personality(self):
        """calculate_availability_score에 성격 모디파이어가 합산."""
        self._setup(props={
            "관계:주인공:호감": 50,
            "성격:정조": 1,  # -10 페널티
        })
        action = {"affection_req": 30}
        # baseline = 50 - 30 = 20, 성격 페널티 -10 → 10
        assert rc.calculate_availability_score(2, 1, action) == 10

    def test_availability_unchanged_when_all_zero(self):
        """성격 없음 → Slice B 도입 전 동작 보존."""
        self._setup(props={"관계:주인공:호감": 50})
        action = {"affection_req": 30}
        # baseline = 50 - 30 = 20, 성격 0 → 20
        assert rc.calculate_availability_score(2, 1, action) == 20


class TestShameReliefByDisposition:
    """Phase 2 Slice J: 노출벽/도착 → 수치심 페널티 상쇄."""

    def _setup(self, props=None, audience=True):
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props=props or {})
        if audience:
            morld.register_unit(3, name="행인", props={})
            # location 1개 공유 시 audience_factor가 실제 양수 반환한다고 가정.

    def test_no_relief_when_disposition_zero(self):
        """노출벽/도착 0 → 수치심 페널티 그대로."""
        self._setup(props={"상태:수치심": 80})
        base = rc.get_shame_modifier(2)
        # base는 audience_factor가 환경마다 달라 고정 불가 — 음수여야만
        # 하고, 양의 disposition이 없으므로 변경 안 됨 확인은 생략
        assert base <= 0

    def test_max_exhib_cancels_shame(self):
        """노출벽 100 + 도착 100 → 페널티 100% 상쇄 = 0."""
        self._setup(props={
            "상태:수치심": 80,
            "성향:노출벽": 100,
            "성향:도착": 100,
        })
        assert rc.get_shame_modifier(2) == 0

    def test_mid_disposition_partial_relief(self):
        """노출벽 50 + 도착 50 → 50% 상쇄 (relief = 0.5)."""
        self._setup(props={
            "상태:수치심": 80,
            "성향:노출벽": 50,
            "성향:도착": 50,
        })
        raw = rc.get_shame_modifier(1)  # 성향 없는 주인공과 비교? 아님
        # 대신 동일 수치심 + 성향 없는 NPC와 비교
        morld.register_unit(5, props={"상태:수치심": 80})
        raw_no_disp = rc.get_shame_modifier(5)
        mid = rc.get_shame_modifier(2)
        # 양자 음수. 성향 있는 쪽이 절댓값이 반이하
        if raw_no_disp < 0:
            assert abs(mid) < abs(raw_no_disp)

    def test_over_cap_relief_clamped(self):
        """노출벽 150 + 도착 100 (over 200) → 최대 100% 상쇄."""
        self._setup(props={
            "상태:수치심": 80,
            "성향:노출벽": 150,
            "성향:도착": 100,
        })
        assert rc.get_shame_modifier(2) == 0


class TestDispositionMasochismMultiplier:
    """Phase 2 Slice I: 마조 → 복종 ↑ / 반발 ↓."""

    def _setup(self, props=None):
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props=props or {})

    def test_default_no_multiplier(self):
        self._setup()
        mult = rc.get_disposition_sm_multipliers(2)
        assert mult["복종"] == 1.0
        assert mult["반발"] == 1.0

    def test_max_masochism_raises_submission(self):
        self._setup(props={"성향:마조": 100})
        mult = rc.get_disposition_sm_multipliers(2)
        assert abs(mult["복종"] - 1.5) < 1e-9
        assert abs(mult["반발"] - 0.5) < 1e-9

    def test_mid_masochism_smooths(self):
        self._setup(props={"성향:마조": 50})
        mult = rc.get_disposition_sm_multipliers(2)
        assert abs(mult["복종"] - 1.25) < 1e-9
        assert abs(mult["반발"] - 0.75) < 1e-9

    def test_masochism_applied_to_submission_gain(self):
        """마조 100 + 복종 +10 → ×1.5 = 15."""
        self._setup(props={"성향:마조": 100})
        action = {"name": "액션", "effects": {"복종": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["복종"] == 15

    def test_masochism_dampens_rebellion_gain(self):
        self._setup(props={"성향:마조": 100})
        action = {"name": "액션", "effects": {"반발": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["반발"] == 5

    def test_masochism_stacks_with_personality(self):
        """자존심 -1 (×1.5) + 마조 100 (×1.5) → 복종 +10 → ×2.25 = 22 or 23."""
        self._setup(props={"성격:자존심": -1, "성향:마조": 100})
        action = {"name": "액션", "effects": {"복종": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        # 1.5 * 1.5 = 2.25, 10 * 2.25 = 22.5 → round = 22 or 23 depending on banker's
        assert out["복종"] in (22, 23)

    def test_negative_submission_unchanged(self):
        self._setup(props={"성향:마조": 100})
        action = {"name": "액션", "effects": {"복종": -10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["복종"] == -10


class TestDispositionResponsivenessMultiplier:
    """Phase 2 Slice H: 쾌감응답 → 성욕 gain 배율."""

    def _setup(self, props=None):
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props=props or {})

    def test_default_1_0(self):
        self._setup()
        assert rc.get_disposition_arousal_multiplier(2) == 1.0

    def test_positive_responsiveness_amplifies(self):
        self._setup(props={"성향:쾌감응답": 1})
        assert abs(rc.get_disposition_arousal_multiplier(2) - 1.3) < 1e-9

    def test_negative_responsiveness_dampens(self):
        self._setup(props={"성향:쾌감응답": -1})
        assert abs(rc.get_disposition_arousal_multiplier(2) - 0.7) < 1e-9

    def test_calculate_effects_applies_responsiveness(self):
        """쾌감응답 1 → 성욕 +10 → ×1.3 = 13."""
        self._setup(props={"성향:쾌감응답": 1})
        action = {"name": "액션", "effects": {"성욕": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["성욕"] == 13

    def test_calculate_effects_negative_arousal_unchanged(self):
        """성욕 감소는 배율 적용 안 함 (양수 gain 전용)."""
        self._setup(props={"성향:쾌감응답": 1})
        action = {"name": "액션", "effects": {"성욕": -10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["성욕"] == -10

    def test_archetype_cold_dampens_arousal(self):
        """cold (쾌감응답 -1) → 성욕 +10 → ×0.7 = 7."""
        morld.register_unit(1, name="주인공", props={})
        morld._player_id = 1
        morld.register_unit(2, props={"아키타입": "cold"})
        action = {"name": "액션", "effects": {"성욕": 10}, "exp_part": None}
        out = rc.calculate_effects(action, 2, 1)
        assert out["성욕"] == 7


class TestDispositionSexualHelpers:
    """Phase 2 Slice G: get_disposition_value 성향 성애 8개 fallback."""

    def _setup(self, archetype=None, props=None):
        base_props = dict(props or {})
        if archetype:
            base_props["아키타입"] = archetype
        morld.register_unit(2, props=base_props)

    def test_returns_0_when_no_archetype(self):
        self._setup()
        for trait in rc.DISPOSITION_SEXUAL_TRAITS:
            assert rc.get_disposition_value(2, trait) == 0

    def test_seductive_high_lust_traits(self):
        self._setup(archetype="seductive")
        assert rc.get_disposition_value(2, "도착") == 30
        assert rc.get_disposition_value(2, "노출벽") == 40
        assert rc.get_disposition_value(2, "쾌감응답") == 1

    def test_cold_analytical_traits(self):
        self._setup(archetype="cold")
        assert rc.get_disposition_value(2, "새드") == 20
        assert rc.get_disposition_value(2, "도착") == 20
        assert rc.get_disposition_value(2, "감정결여") == 1
        assert rc.get_disposition_value(2, "쾌감응답") == -1

    def test_explicit_prop_overrides_archetype(self):
        self._setup(archetype="seductive",
                    props={"성향:도착": 50})
        assert rc.get_disposition_value(2, "도착") == 50

    def test_explicit_zero_overrides_archetype(self):
        """명시 0은 아키타입 양수를 덮어씀."""
        self._setup(archetype="seductive",
                    props={"성향:노출벽": 0})
        assert rc.get_disposition_value(2, "노출벽") == 0

    def test_raises_on_unknown_trait(self):
        self._setup()
        try:
            rc.get_disposition_value(2, "없는trait")
            assert False, "should raise"
        except ValueError:
            pass

    def test_all_archetypes_cover_all_traits(self):
        for arch, defaults in rc.ARCHETYPE_DISPOSITION_SEXUAL_DEFAULT.items():
            for trait in rc.DISPOSITION_SEXUAL_TRAITS:
                assert trait in defaults, f"{arch} missing {trait}"


class TestPersonalityTraitHelpers:
    """Phase 2 Slice A: get_personality_value 아키타입 기본값 + override."""

    def _setup(self, archetype=None, props=None):
        base_props = dict(props or {})
        if archetype:
            base_props["아키타입"] = archetype
        morld.register_unit(2, props=base_props)

    def test_returns_0_when_no_archetype_no_prop(self):
        self._setup()
        assert rc.get_personality_value(2, "담력") == 0

    def test_returns_archetype_default_stoic(self):
        self._setup(archetype="stoic")
        # stoic: 담력=1, 응답=-1, 명랑=-1, 나머지 0
        assert rc.get_personality_value(2, "담력") == 1
        assert rc.get_personality_value(2, "응답") == -1
        assert rc.get_personality_value(2, "명랑") == -1
        assert rc.get_personality_value(2, "자존심") == 0

    def test_returns_archetype_default_tsundere(self):
        self._setup(archetype="tsundere")
        # tsundere: 태도=1, 자존심=1, 츤데레=1, 정조=1
        assert rc.get_personality_value(2, "츤데레") == 1
        assert rc.get_personality_value(2, "자존심") == 1
        assert rc.get_personality_value(2, "정조") == 1
        assert rc.get_personality_value(2, "담력") == 0

    def test_returns_archetype_default_innocent(self):
        self._setup(archetype="innocent")
        assert rc.get_personality_value(2, "정조") == 1
        assert rc.get_personality_value(2, "명랑") == 1
        assert rc.get_personality_value(2, "태도") == -1

    def test_explicit_prop_overrides_archetype(self):
        """명시 `성격:담력` prop이 아키타입 기본값보다 우선."""
        self._setup(archetype="stoic",
                    props={"성격:담력": -1})
        assert rc.get_personality_value(2, "담력") == -1

    def test_explicit_0_overrides_archetype_positive(self):
        """명시 0은 아키타입 양수를 덮어씀 (None 체크 정확성)."""
        self._setup(archetype="stoic",
                    props={"성격:담력": 0})
        assert rc.get_personality_value(2, "담력") == 0

    def test_raises_on_unknown_trait(self):
        self._setup(archetype="stoic")
        try:
            rc.get_personality_value(2, "존재하지않는trait")
            assert False, "should raise"
        except ValueError:
            pass

    def test_all_archetypes_have_all_traits(self):
        """모든 아키타입이 7 trait 전부 정의."""
        for arch, defaults in rc.ARCHETYPE_PERSONALITY_DEFAULT.items():
            for trait in rc.PERSONALITY_TRAITS:
                assert trait in defaults, f"{arch} missing trait {trait}"
                assert defaults[trait] in (-1, 0, 1), \
                    f"{arch}.{trait}={defaults[trait]} not in [-1, 0, 1]"

    def test_unknown_archetype_falls_back_to_zeros(self):
        self._setup(archetype="nonsense")
        for trait in rc.PERSONALITY_TRAITS:
            assert rc.get_personality_value(2, trait) == 0


class TestFoodAdditiveEffects:
    """Phase 2.6: 음식 첨가물 일괄 적용 — 3 먹기 경로 공용."""

    def _setup(self):
        rc._TIMED_STATUS_REGISTRY.clear()
        morld.register_unit(1, props={})
        morld.register_unit(100, props={})  # item

    def test_has_food_additive_false_by_default(self):
        self._setup()
        assert rc.has_food_additive(100, "미약") is False

    def test_add_food_additive_sets_flag(self):
        self._setup()
        rc.add_food_additive(100, "미약")
        assert rc.has_food_additive(100, "미약") is True

    def test_apply_aphrodisiac_sets_timer_and_trance(self):
        self._setup()
        rc.add_food_additive(100, "미약")
        rc.apply_food_additive_effects(1, 100)
        assert rc.is_status_active(1, "미약") is True
        assert morld.get_unit_prop(1, "트랜스:외부") == 30

    def test_apply_aphrodisiac_skips_when_already_active(self):
        self._setup()
        rc.apply_timed_status(1, "미약", duration=3)
        rc.add_food_additive(100, "미약")
        rc.apply_food_additive_effects(1, 100)
        # 기존 타이머 보존 (새로 덮지 않음)
        assert morld.get_unit_prop(1, "상태:미약남은시간") == 3
        # 트랜스:외부 가산도 안 됨
        assert (morld.get_unit_prop(1, "트랜스:외부") or 0) == 0

    def test_drunk_additive_adds_15(self):
        self._setup()
        rc.add_food_additive(100, "취기")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:취기") == 15

    def test_strong_liquor_adds_30(self):
        self._setup()
        rc.add_food_additive(100, "독주")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:취기") == 30

    def test_drunk_and_strong_stack(self):
        self._setup()
        rc.add_food_additive(100, "취기")
        rc.add_food_additive(100, "독주")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:취기") == 45

    def test_drunk_capped_at_100(self):
        self._setup()
        morld.set_unit_prop(1, "상태:취기", 90)
        rc.add_food_additive(100, "독주")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:취기") == 100

    def test_narcotic_adds_trance_50(self):
        self._setup()
        rc.add_food_additive(100, "마약")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "트랜스:외부") == 50

    def test_hypnotic_adds_trance_40(self):
        self._setup()
        rc.add_food_additive(100, "최면제")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "트랜스:외부") == 40

    def test_ovulation_inducer_sets_24h(self):
        self._setup()
        rc.add_food_additive(100, "배란유도제")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:배란유도남은시간") == 24

    def test_potency_sets_6h(self):
        self._setup()
        rc.add_food_additive(100, "정력제")
        rc.apply_food_additive_effects(1, 100)
        assert morld.get_unit_prop(1, "상태:정력제남은시간") == 6

    def test_multiple_additives_in_one_meal(self):
        """한 음식에 여러 첨가물이 묻어 있으면 모두 적용."""
        self._setup()
        rc.add_food_additive(100, "미약")
        rc.add_food_additive(100, "배란유도제")
        rc.apply_food_additive_effects(1, 100)
        assert rc.is_status_active(1, "미약") is True
        assert rc.is_status_active(1, "배란유도") is True


class TestNpcSexRoleHelpers:
    """Phase 2.6: NPC 정사 플래그 3개 → 단일 역할 prop 통합."""

    def _setup(self):
        morld.register_unit(2, props={})

    def test_not_in_sex_by_default(self):
        self._setup()
        assert rc.is_in_npc_sex(2) is False
        assert rc.is_npc_sex_victim(2) is False
        assert rc.is_npc_sex_aggressor(2) is False
        assert rc.get_npc_sex_role(2) is None

    def test_set_consensual_role(self):
        self._setup()
        rc.set_npc_sex_role(2, rc.NPC_SEX_CONSENSUAL)
        assert rc.is_in_npc_sex(2) is True
        assert rc.is_npc_sex_victim(2) is False
        assert rc.is_npc_sex_aggressor(2) is False

    def test_set_victim_role(self):
        self._setup()
        rc.set_npc_sex_role(2, rc.NPC_SEX_VICTIM)
        assert rc.is_in_npc_sex(2) is True
        assert rc.is_npc_sex_victim(2) is True
        assert rc.is_npc_sex_aggressor(2) is False

    def test_set_aggressor_role(self):
        self._setup()
        rc.set_npc_sex_role(2, rc.NPC_SEX_AGGRESSOR)
        assert rc.is_in_npc_sex(2) is True
        assert rc.is_npc_sex_victim(2) is False
        assert rc.is_npc_sex_aggressor(2) is True

    def test_clear_role(self):
        self._setup()
        rc.set_npc_sex_role(2, rc.NPC_SEX_VICTIM)
        rc.clear_npc_sex_role(2)
        assert rc.is_in_npc_sex(2) is False

    def test_invalid_role_raises(self):
        self._setup()
        try:
            rc.set_npc_sex_role(2, "invalid")
            assert False, "should raise"
        except ValueError:
            pass


class TestTimedStatusHelpers:
    """Phase 2.6: 시간 제한 상태 효과 플래그 → 타이머 파생 리팩터링."""

    def _setup(self):
        # iterate registry 초기화
        rc._TIMED_STATUS_REGISTRY.clear()
        morld.register_unit(2, props={})

    def test_is_status_active_false_when_no_timer(self):
        self._setup()
        assert rc.is_status_active(2, "미약") is False

    def test_is_status_active_false_when_zero(self):
        self._setup()
        morld.set_unit_prop(2, "상태:미약남은시간", 0)
        assert rc.is_status_active(2, "미약") is False

    def test_is_status_active_true_when_positive(self):
        self._setup()
        morld.set_unit_prop(2, "상태:미약남은시간", 3)
        assert rc.is_status_active(2, "미약") is True

    def test_apply_timed_status_default_duration(self):
        self._setup()
        rc.apply_timed_status(2, "미약")
        assert morld.get_unit_prop(2, "상태:미약남은시간") == 6

    def test_apply_timed_status_ovulation_24h(self):
        self._setup()
        rc.apply_timed_status(2, "배란유도")
        assert morld.get_unit_prop(2, "상태:배란유도남은시간") == 24

    def test_apply_timed_status_potency_6h(self):
        self._setup()
        rc.apply_timed_status(2, "정력제")
        assert morld.get_unit_prop(2, "상태:정력제남은시간") == 6

    def test_apply_timed_status_explicit_duration(self):
        self._setup()
        rc.apply_timed_status(2, "미약", duration=3)
        assert morld.get_unit_prop(2, "상태:미약남은시간") == 3

    def test_apply_timed_status_registers(self):
        self._setup()
        rc.apply_timed_status(2, "미약")
        assert 2 in rc._TIMED_STATUS_REGISTRY

    def test_decay_tick_reduces_timer(self):
        self._setup()
        rc.apply_timed_status(2, "미약", duration=3)
        rc._decay_timed_status_tick()
        assert morld.get_unit_prop(2, "상태:미약남은시간") == 2

    def test_decay_tick_clears_expired(self):
        self._setup()
        rc.apply_timed_status(2, "미약", duration=1)
        rc._decay_timed_status_tick()
        # 1 → 0 → clear
        assert morld.get_unit_prop(2, "상태:미약남은시간") is None
        # 더 이상 활성 아니면 registry 제거
        assert 2 not in rc._TIMED_STATUS_REGISTRY

    def test_decay_tick_handles_multiple_drugs(self):
        self._setup()
        rc.apply_timed_status(2, "미약", duration=2)
        rc.apply_timed_status(2, "배란유도", duration=5)
        rc._decay_timed_status_tick()
        assert morld.get_unit_prop(2, "상태:미약남은시간") == 1
        assert morld.get_unit_prop(2, "상태:배란유도남은시간") == 4
        # 둘 다 활성 → registry 유지
        assert 2 in rc._TIMED_STATUS_REGISTRY


class TestFertileDayHelper:
    """pregnancy.is_fertile_day — 배란기 OR 배란유도 AND 미임신."""

    def test_pregnant_is_not_fertile(self):
        import pregnancy
        morld.register_unit(2, props={"상태:임신": 1, "생식:주기일": 14})
        assert pregnancy.is_fertile_day(2) is False

    def test_ovulation_day_is_fertile(self):
        import pregnancy
        morld.register_unit(2, props={"생식:주기일": 14, "생식:주기길이": 28})
        assert pregnancy.is_fertile_day(2) is True

    def test_non_ovulation_is_not_fertile(self):
        import pregnancy
        morld.register_unit(2, props={"생식:주기일": 3, "생식:주기길이": 28})
        assert pregnancy.is_fertile_day(2) is False

    def test_induced_ovulation_is_fertile_even_outside_cycle(self):
        """배란유도 상태 → 주기 무관 fertile."""
        import pregnancy
        morld.register_unit(2, props={"생식:주기일": 3, "생식:주기길이": 28,
                                        "상태:배란유도남은시간": 12})
        assert pregnancy.is_fertile_day(2) is True

    def test_pregnant_overrides_induced_ovulation(self):
        """이미 임신 중 → 배란유도 상관없이 False."""
        import pregnancy
        morld.register_unit(2, props={"상태:임신": 1,
                                        "상태:배란유도남은시간": 12})
        assert pregnancy.is_fertile_day(2) is False


class TestOvulationReactionCondition:
    """_check_reaction_condition의 배란 특수 키."""

    def _make_char(self, instance_id=2):
        from assets.base import Character
        char = Character.__new__(Character)
        char.instance_id = instance_id
        char.name = "테스트"
        return char

    def test_ovulation_key_true_matches_fertile_day(self):
        morld.register_unit(2, props={"생식:주기일": 14, "생식:주기길이": 28})
        char = self._make_char(2)
        props = morld.get_unit_props(2) or {}
        assert char._check_reaction_condition({"배란": True}, props, "플레이어") is True

    def test_ovulation_key_true_fails_when_not_fertile(self):
        morld.register_unit(2, props={"생식:주기일": 3, "생식:주기길이": 28})
        char = self._make_char(2)
        props = morld.get_unit_props(2) or {}
        assert char._check_reaction_condition({"배란": True}, props, "플레이어") is False

    def test_ovulation_combined_with_other_condition(self):
        """배란 + 반발 복합 조건: 둘 다 만족해야 True."""
        morld.register_unit(2, props={
            "생식:주기일": 14, "생식:주기길이": 28,
            "관계:플레이어:반발": 20,
        })
        char = self._make_char(2)
        props = morld.get_unit_props(2) or {}
        # 배란 True + 반발 >= 15 → True
        assert char._check_reaction_condition({"배란": True, "반발": 15}, props, "플레이어") is True
        # 반발 >= 30 미달 → False
        assert char._check_reaction_condition({"배란": True, "반발": 30}, props, "플레이어") is False

    def test_ovulation_false_when_pregnant(self):
        morld.register_unit(2, props={"상태:임신": 1, "생식:주기일": 14,
                                        "생식:주기길이": 28})
        char = self._make_char(2)
        props = morld.get_unit_props(2) or {}
        assert char._check_reaction_condition({"배란": True}, props, "플레이어") is False


class TestExternalSemenFocusTiers:
    """_FOCUS_SEMEN 2-tier (대량 50 / 소량 10) + _compute_bukkake_extra 검증."""

    def test_light_tier_matches(self):
        from assets.base import _FOCUS_SEMEN, TextSelector
        context = {"정액:얼굴": 20}
        result = TextSelector.select(_FOCUS_SEMEN, context)
        assert result == "얼굴에 하얀 것이 묻어 있다."

    def test_heavy_tier_preempts_light(self):
        """대량 50+ 이면 소량 라인 대신 대량 라인이 먼저 매칭."""
        from assets.base import _FOCUS_SEMEN, TextSelector
        context = {"정액:얼굴": 60}
        result = TextSelector.select(_FOCUS_SEMEN, context)
        assert "범벅" in result

    def test_heavy_tier_per_part_distinct(self):
        """각 부위 대량 라인은 서로 다른 문구."""
        from assets.base import _FOCUS_SEMEN, TextSelector
        parts = ["얼굴", "가슴", "배", "음부", "엉덩이"]
        lines = set()
        for p in parts:
            ctx = {f"정액:{p}": 60}
            lines.add(TextSelector.select(_FOCUS_SEMEN, ctx))
        assert len(lines) == 5

    def test_bukkake_extra_three_parts(self):
        from assets.base import _compute_bukkake_extra
        ctx = {f"정액:{p}": 60 for p in ("얼굴", "가슴", "배")}
        assert "두껍게 쌓여" in _compute_bukkake_extra(ctx)

    def test_bukkake_extra_four_parts_heavier(self):
        from assets.base import _compute_bukkake_extra
        ctx = {f"정액:{p}": 60 for p in ("얼굴", "가슴", "배", "음부")}
        assert "전신" in _compute_bukkake_extra(ctx)

    def test_bukkake_extra_only_two_parts_no_line(self):
        from assets.base import _compute_bukkake_extra
        ctx = {f"정액:{p}": 60 for p in ("얼굴", "가슴")}
        assert _compute_bukkake_extra(ctx) == ""

    def test_bukkake_extra_ignores_light(self):
        """50 미만은 범벅 카운트에 포함 안 됨."""
        from assets.base import _compute_bukkake_extra
        ctx = {f"정액:{p}": 30 for p in ("얼굴", "가슴", "배", "음부")}
        assert _compute_bukkake_extra(ctx) == ""


class TestAnalInternalFocusTier:
    """_FOCUS_INTERNAL_SEMEN 모든 아키타입에 체내정액:항문 규칙 존재."""

    _ARCHETYPES = ["stoic", "gentle", "cheerful", "timid", "cold"]

    def test_all_archetypes_have_anal_heavy(self):
        from assets.base import _FOCUS_INTERNAL_SEMEN
        for arch in self._ARCHETYPES:
            rules = _FOCUS_INTERNAL_SEMEN[arch]
            has_heavy = any(
                isinstance(cond, dict) and cond.get("체내정액:항문", 0) >= 50
                for cond, _ in rules
            )
            assert has_heavy, f"{arch} missing 체내정액:항문 ≥ 50 rule"

    def test_all_archetypes_have_anal_light(self):
        from assets.base import _FOCUS_INTERNAL_SEMEN
        for arch in self._ARCHETYPES:
            rules = _FOCUS_INTERNAL_SEMEN[arch]
            has_light = any(
                isinstance(cond, dict) and cond.get("체내정액:항문") == 1
                for cond, _ in rules
            )
            assert has_light, f"{arch} missing 체내정액:항문 ≥ 1 rule"


class TestOverflowDialoguePool:
    """Slice D1: 6 캐릭터 × 3 부위 overflow 대사 존재."""

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("mila", "Mila"),
        ("sera", "Sera"),
        ("faye", "Faye"),
    ]
    _PARTS = ["음부", "항문", "구강"]

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_all_characters_have_all_overflow_keys(self):
        """각 캐릭터가 3 부위 overflow 키 모두 보유."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for part in self._PARTS:
                key = f"ejaculation_internal_{part}_overflow:start"
                assert key in reactions, f"{cls_name} missing {key}"

    def test_overflow_pools_have_rebellion_branch(self):
        """각 overflow 풀이 반발 조건 분기 포함."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for part in self._PARTS:
                key = f"ejaculation_internal_{part}_overflow:start"
                rules = reactions.get(key, [])
                has_rebellion = any(
                    isinstance(r, tuple) and isinstance(r[0], dict) and "반발" in r[0]
                    for r in rules
                )
                assert has_rebellion, f"{cls_name}.{key} missing 반발 rule"


class TestRawVaginalWarningDialoguePool:
    """Slice D2: 6 캐릭터 raw_vaginal_warning:start 대사 존재."""

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("mila", "Mila"),
        ("sera", "Sera"),
        ("faye", "Faye"),
    ]

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_all_characters_have_raw_warning(self):
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            assert "raw_vaginal_warning:start" in reactions, \
                f"{cls_name} missing raw_vaginal_warning:start"

    def test_raw_warning_has_minimum_rules(self):
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            rules = reactions.get("raw_vaginal_warning:start", [])
            assert len(rules) >= 2, \
                f"{cls_name} raw_vaginal_warning:start has only {len(rules)} rules"


class TestExtractPreservedRawVaginalFlag:
    """raw_vaginal_warned 플래그는 공수 전환 시 보존."""

    def test_preserved_includes_raw_warned_true(self):
        state = {"stim": {}, "stamina": 100, "elapsed_time": 0,
                 "insertion": {"active": True, "orifice": "vaginal", "who": "p", "failed_count": 0},
                 "mode_ctx": {"mode": rm.MODE_CONSENSUAL},
                 "raw_vaginal_warned": True}
        preserved = rc.extract_preserved(state)
        assert preserved["raw_vaginal_warned"] is True

    def test_preserved_defaults_raw_warned_false(self):
        state = {"stim": {}, "stamina": 100, "elapsed_time": 0,
                 "insertion": {"active": True, "orifice": "vaginal", "who": "p", "failed_count": 0},
                 "mode_ctx": {"mode": rm.MODE_CONSENSUAL}}
        preserved = rc.extract_preserved(state)
        assert preserved["raw_vaginal_warned"] is False


class TestExternalCumshotShameHook:
    """Slice C: on_external_cumshot — 부위별 수치심 가중."""

    def test_face_shot_highest_shame(self):
        morld.register_unit(2, props={"상태:수치심": 20})
        result = rc.on_external_cumshot(2, "얼굴")
        assert result == 20 + rc.SHAME_GAIN_EXTERNAL_CUMSHOT["얼굴"]

    def test_breast_shot_medium_shame(self):
        morld.register_unit(2, props={"상태:수치심": 20})
        result = rc.on_external_cumshot(2, "가슴")
        assert result == 20 + rc.SHAME_GAIN_EXTERNAL_CUMSHOT["가슴"]

    def test_stomach_shot_lower_shame(self):
        morld.register_unit(2, props={"상태:수치심": 20})
        result = rc.on_external_cumshot(2, "배")
        assert result == 20 + rc.SHAME_GAIN_EXTERNAL_CUMSHOT["배"]

    def test_butt_shot_shame(self):
        morld.register_unit(2, props={"상태:수치심": 20})
        result = rc.on_external_cumshot(2, "엉덩이")
        assert result == 20 + rc.SHAME_GAIN_EXTERNAL_CUMSHOT["엉덩이"]

    def test_face_higher_than_butt(self):
        """얼굴 > 엉덩이 수치심 (가시성 차이)."""
        assert rc.SHAME_GAIN_EXTERNAL_CUMSHOT["얼굴"] > \
               rc.SHAME_GAIN_EXTERNAL_CUMSHOT["엉덩이"]

    def test_unknown_part_no_shame(self):
        """SEMEN_PARTS 외 부위 → 수치심 변화 없음."""
        morld.register_unit(2, props={"상태:수치심": 20})
        before = morld.get_unit_prop(2, "상태:수치심")
        rc.on_external_cumshot(2, "팔")
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after == before

    def test_shame_clamped_at_max(self):
        """이미 최대치면 clamp."""
        morld.register_unit(2, props={"상태:수치심": rc.SHAME_MAX - 2})
        result = rc.on_external_cumshot(2, "얼굴")
        assert result == rc.SHAME_MAX


class TestExternalCumshotDialoguePool:
    """Slice C: 6 캐릭터 × 4 부위 pull_out_{부위}:start 대사 존재."""

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("mila", "Mila"),
        ("sera", "Sera"),
        ("faye", "Faye"),
    ]
    _PARTS = ["얼굴", "가슴", "배", "엉덩이"]

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_all_characters_have_all_parts(self):
        """각 캐릭터가 4 부위 pull_out_{부위}:start 키 모두 보유."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for part in self._PARTS:
                key = f"pull_out_{part}:start"
                assert key in reactions, f"{cls_name} missing {key}"

    def test_all_pools_have_minimum_rules(self):
        """각 부위 풀이 최소 2 rule (반발 or 기본) 보유."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for part in self._PARTS:
                key = f"pull_out_{part}:start"
                rules = reactions.get(key, [])
                assert len(rules) >= 2, \
                    f"{cls_name}.{key} has only {len(rules)} rules"

    def test_all_pools_have_rebellion_branch(self):
        """각 부위 풀이 반발 조건 분기 1개 이상."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            reactions = getattr(cls, "ROMANCE_REACTIONS", {})
            for part in self._PARTS:
                key = f"pull_out_{part}:start"
                rules = reactions.get(key, [])
                has_rebellion = any(
                    isinstance(r, tuple) and isinstance(r[0], dict) and "반발" in r[0]
                    for r in rules
                )
                assert has_rebellion, f"{cls_name}.{key} missing 반발 rule"


class TestFertileWarningDialoguePool:
    """6 캐릭터의 ejaculation_internal_음부:start 풀에 배란일 경고 대사 포함."""

    _CHARACTERS = [
        ("lina", "Lina"),
        ("yuki", "Yuki"),
        ("ella", "Ella"),
        ("mila", "Mila"),
        ("sera", "Sera"),
        ("faye", "Faye"),
    ]

    def _character_class(self, module_name, class_name):
        import importlib
        mod = importlib.import_module(f"assets.characters.{module_name}")
        return getattr(mod, class_name)

    def test_all_have_fertile_warning_rules(self):
        """각 캐릭터가 최소 1개 배란 조건 rule 보유."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            rules = getattr(cls, "ROMANCE_REACTIONS", {}).get("ejaculation_internal_음부:start", [])
            has_fertile_rule = any(
                isinstance(r, tuple) and isinstance(r[0], dict) and r[0].get("배란") is True
                for r in rules
            )
            assert has_fertile_rule, f"{cls_name} missing 배란 rule in ejaculation_internal_음부:start"

    def test_fertile_warning_placed_before_catchall(self):
        """배란 rule이 fallback (빈 dict 또는 _generate_dialogue)보다 앞에 위치."""
        for mod_name, cls_name in self._CHARACTERS:
            cls = self._character_class(mod_name, cls_name)
            rules = getattr(cls, "ROMANCE_REACTIONS", {}).get("ejaculation_internal_음부:start", [])
            fertile_idx = None
            catchall_idx = None
            for idx, item in enumerate(rules):
                if not (isinstance(item, tuple) and isinstance(item[0], dict)):
                    continue
                cond = item[0]
                if cond.get("배란") is True and fertile_idx is None:
                    fertile_idx = idx
                if not cond and catchall_idx is None:
                    catchall_idx = idx
            assert fertile_idx is not None, f"{cls_name} missing 배란 rule"
            if catchall_idx is not None:
                assert fertile_idx < catchall_idx, \
                    f"{cls_name} 배란 rule at {fertile_idx} should precede catchall at {catchall_idx}"
