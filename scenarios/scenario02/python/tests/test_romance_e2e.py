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
        """강제 세션 중 저항 게이지 누적 → 100 도달 시 탈출 플래그"""
        self._setup()
        # 반발 높은 NPC → 탈출 확률 상승, meter_delta 큼
        morld.set_unit_prop(2, "관계:주인공:반발", 80)

        mode_ctx = rm.create_mode_context(rm.MODE_FORCED, 1, 2)
        # 첫 저항 체크
        result = rm.check_resistance(mode_ctx, 2)
        assert result["attempted"] is True
        assert result["resistance_delta"] > 0
        # 게이지 누적 확인
        assert mode_ctx["resistance_meter"] >= result["resistance_delta"] or result["escaped"]

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
