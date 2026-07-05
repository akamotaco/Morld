# test_romance_dynamics.py — 라벨/애정/관계 라벨 파생
import sys

import romance_dynamics as rd
from romance_core import get_affection_key, get_submission_key, get_rebellion_key

morld = sys.modules["morld"]


def _setup_pair():
    """player=1, target=2 등록."""
    morld.register_unit(1, name="주인공", gender="male")
    morld.register_unit(2, name="유키", gender="female")


# ============================================
# 라벨 조회
# ============================================

class TestAffectionLabel:
    def test_zero(self):
        assert rd.get_affection_label(0) == "무관심"

    def test_below_20(self):
        assert rd.get_affection_label(19) == "무관심"

    def test_20(self):
        assert rd.get_affection_label(20) == "지인"

    def test_40(self):
        assert rd.get_affection_label(40) == "친구"

    def test_60(self):
        assert rd.get_affection_label(60) == "신뢰"

    def test_80(self):
        assert rd.get_affection_label(80) == "친애"

    def test_max(self):
        assert rd.get_affection_label(100) == "친애"

    def test_none_handled(self):
        assert rd.get_affection_label(None) == "무관심"


class TestSubmissionLabel:
    def test_zero(self):
        assert rd.get_submission_label(0) == "자유"

    def test_30(self):
        assert rd.get_submission_label(30) == "순응"

    def test_60(self):
        assert rd.get_submission_label(60) == "충성"

    def test_80(self):
        assert rd.get_submission_label(80) == "복속"

    def test_100(self):
        assert rd.get_submission_label(100) == "절대복종"


class TestLoveLabel:
    def test_zero(self):
        assert rd.get_love_label(0) == "무"

    def test_20(self):
        assert rd.get_love_label(20) == "호의"

    def test_40(self):
        assert rd.get_love_label(40) == "애정"

    def test_60(self):
        assert rd.get_love_label(60) == "사랑"

    def test_80(self):
        assert rd.get_love_label(80) == "헌신"


# ============================================
# 애정 스탯 modify_love
# ============================================

class TestModifyLove:
    def setUp(self):
        _setup_pair()

    def test_gain_normal(self):
        delta = rd.modify_love(2, 1, 10)
        assert delta == 10
        assert rd.get_love(2, 1) == 10

    def test_gain_at_threshold_full(self):
        """복종 = LOVE_BLOCK_SUBMISSION — 감쇠 시작 지점에서는 아직 full (damp=1.0)."""
        morld.set_unit_prop(2, get_submission_key(1), rd.LOVE_BLOCK_SUBMISSION)
        delta = rd.modify_love(2, 1, 10)
        assert delta == 10
        assert rd.get_love(2, 1) == 10

    def test_gain_damped_above_threshold(self):
        """복종 80 → damp = (100-80)/40 = 0.5 → delta 20*0.5 = 10."""
        morld.set_unit_prop(2, get_submission_key(1), 80)
        delta = rd.modify_love(2, 1, 20)
        assert delta == 10

    def test_gain_fully_blocked_at_max(self):
        """복종 100 → damp = 0 → delta 0."""
        morld.set_unit_prop(2, get_submission_key(1), 100)
        delta = rd.modify_love(2, 1, 20)
        assert delta == 0

    def test_gain_allowed_below_threshold(self):
        morld.set_unit_prop(2, get_submission_key(1), rd.LOVE_BLOCK_SUBMISSION - 1)
        delta = rd.modify_love(2, 1, 10)
        assert delta == 10

    def test_loss_not_blocked_by_submission(self):
        # 복종 0일 때 애정 축적
        rd.modify_love(2, 1, 50)
        # 복종 끌어올려도 감소는 통과
        morld.set_unit_prop(2, get_submission_key(1), 80)
        delta = rd.modify_love(2, 1, -10)
        assert delta == -10
        assert rd.get_love(2, 1) == 40

    def test_clamped_to_max(self):
        morld.set_unit_prop(2, rd.get_love_key(1), 95)
        delta = rd.modify_love(2, 1, 20)
        assert delta == 5
        assert rd.get_love(2, 1) == 100

    def test_clamped_to_min(self):
        morld.set_unit_prop(2, rd.get_love_key(1), 5)
        delta = rd.modify_love(2, 1, -20)
        assert delta == -5
        assert rd.get_love(2, 1) == 0


# ============================================
# 관계 라벨 파생
# ============================================

class TestRelationshipLabel:
    def setUp(self):
        _setup_pair()

    def _set(self, affection=0, submission=0, love=0, rebellion=0):
        morld.set_unit_prop(2, get_affection_key(1), affection)
        morld.set_unit_prop(2, get_submission_key(1), submission)
        morld.set_unit_prop(2, rd.get_love_key(1), love)
        morld.set_unit_prop(2, get_rebellion_key(1), rebellion)

    def test_stranger(self):
        self._set()
        assert rd.get_relationship_label(2, 1) == "타인"

    def test_acquaintance(self):
        self._set(affection=25)
        assert rd.get_relationship_label(2, 1) == "지인"

    def test_friend(self):
        self._set(affection=50)
        assert rd.get_relationship_label(2, 1) == "친구"

    def test_lover(self):
        self._set(affection=70, love=70)
        assert rd.get_relationship_label(2, 1) == "연인"

    def test_spouse(self):
        self._set(affection=70, love=85)
        assert rd.get_relationship_label(2, 1) == "배우자"

    def test_servant_pure_submission(self):
        self._set(submission=70)
        assert rd.get_relationship_label(2, 1) == "종복"

    def test_devoted_servant(self):
        # 복종 높지만 애정도 일정 이상 (함락 후 사랑 각인)
        self._set(submission=70, love=50)
        assert rd.get_relationship_label(2, 1) == "헌신적 종자"

    def test_enemy_overrides_affection(self):
        self._set(affection=70, love=70, rebellion=70)
        assert rd.get_relationship_label(2, 1) == "적대"

    def test_lover_blocked_by_high_submission(self):
        # 애정/호감 높지만 복종도 높으면 "연인" 아님 → "헌신적 종자"
        self._set(affection=70, love=70, submission=70)
        assert rd.get_relationship_label(2, 1) == "헌신적 종자"


# ============================================
# 트랜스 상태 (Phase 1.6.1)
# ============================================

class TestTranceLevel:
    def setUp(self):
        _setup_pair()

    def _set_stats(self, arousal=0, gauge=0, restraint=50, external=0):
        morld.set_unit_prop(2, "상태:성욕", arousal)
        morld.set_unit_prop(2, "상태:절정", gauge)
        morld.set_unit_prop(2, "성격:자제심", restraint)
        morld.set_unit_prop(2, "트랜스:외부", external)

    def test_compute_zero_at_baseline(self):
        self._set_stats(arousal=0, gauge=0)
        assert rd.compute_trance_level(2) == 0

    def test_compute_base_half_of_sum(self):
        """자제심 50(기본)일 때 base = (성욕 + 게이지) / 2."""
        self._set_stats(arousal=80, gauge=40, restraint=50)
        assert rd.compute_trance_level(2) == 60

    def test_compute_high_restraint_strong_defense(self):
        """자제심 100 → 90% 방어 (factor 0.1)."""
        self._set_stats(arousal=80, gauge=40, restraint=100)
        # base=60, factor=max(0.1, 1.0 - 50×0.02)=0.1 → 6
        assert rd.compute_trance_level(2) == 6

    def test_compute_restraint_80_partial_defense(self):
        """자제심 80 → 60% 방어 (factor 0.4)."""
        self._set_stats(arousal=80, gauge=40, restraint=80)
        # base=60, factor=1.0 - 30×0.02 = 0.4 → 24
        assert rd.compute_trance_level(2) == 24

    def test_compute_low_restraint_no_boost(self):
        """자제심 0 → 방어 없음 (증폭도 없음, 비대칭)."""
        self._set_stats(arousal=80, gauge=40, restraint=0)
        # base=60, factor=1.0 (50 이하는 방어 없음) → 60
        assert rd.compute_trance_level(2) == 60

    def test_compute_restraint_50_neutral(self):
        """자제심 50(기본) → 방어 없음."""
        self._set_stats(arousal=80, gauge=40, restraint=50)
        # factor=1.0 → base 그대로
        assert rd.compute_trance_level(2) == 60

    def test_compute_external_bypasses_restraint(self):
        """외부 가산(세뇌/약물)은 자제심 방어를 우회."""
        self._set_stats(arousal=80, gauge=40, restraint=100, external=50)
        # base=60 × 0.1 = 6, external=50 → 56
        assert rd.compute_trance_level(2) == 56

    def test_compute_external_strong_overwhelms(self):
        """강한 외부 자극은 고자제심도 트랜스 진입 가능케 함."""
        self._set_stats(arousal=100, gauge=100, restraint=100, external=60)
        # base=100 × 0.1 = 10, external=60 → 70 (TRANCE_ENTRY 초과)
        assert rd.compute_trance_level(2) == 70

    def test_compute_external_adds(self):
        """외부 가산 (세뇌/약물)은 그대로 더해짐."""
        self._set_stats(arousal=40, gauge=20, restraint=50, external=30)
        # base=30 + 30 = 60
        assert rd.compute_trance_level(2) == 60

    def test_compute_clamped_to_100(self):
        self._set_stats(arousal=100, gauge=100, restraint=0, external=50)
        # base=100×1.25=125 +50=175 → clamp 100
        assert rd.compute_trance_level(2) == 100

    def test_compute_missing_restraint_defaults_50(self):
        morld.set_unit_prop(2, "상태:성욕", 80)
        morld.set_unit_prop(2, "상태:절정", 40)
        # 자제심 prop 없음 → 기본 50
        assert rd.compute_trance_level(2) == 60

    def test_update_writes_prop(self):
        self._set_stats(arousal=80, gauge=40, restraint=50)
        rd.update_trance_level(2)
        assert morld.get_unit_prop(2, "상태:트랜스") == 60

    def test_is_in_trance_threshold(self):
        morld.set_unit_prop(2, "상태:트랜스", 59)
        assert rd.is_in_trance(2) is False
        morld.set_unit_prop(2, "상태:트랜스", 60)
        assert rd.is_in_trance(2) is True

    def test_is_in_deep_trance_threshold(self):
        morld.set_unit_prop(2, "상태:트랜스", 79)
        assert rd.is_in_deep_trance(2) is False
        morld.set_unit_prop(2, "상태:트랜스", 80)
        assert rd.is_in_deep_trance(2) is True

    def test_trance_does_not_save_on_compute(self):
        """compute_ 는 저장하지 않음 (update_만 저장)."""
        self._set_stats(arousal=80, gauge=40, restraint=50)
        rd.compute_trance_level(2)
        # update 전엔 prop 없음 (mock이 None 반환)
        assert morld.get_unit_prop(2, "상태:트랜스") == 0  # 실 계약: 부재 시 0

    def test_apathy_halves_trance(self):
        """Phase 2 Slice K: 무관심 1 → 트랜스 진입 절반 감쇠."""
        self._set_stats(arousal=80, gauge=40, restraint=50)
        baseline = rd.compute_trance_level(2)  # 60
        morld.set_unit_prop(2, "성향:무관심", 1)
        dampened = rd.compute_trance_level(2)
        assert dampened == baseline // 2  # 30

    def test_numbness_halves_trance(self):
        """감정결여 1 → 동일 감쇠."""
        self._set_stats(arousal=80, gauge=40, restraint=50)
        morld.set_unit_prop(2, "성향:감정결여", 1)
        assert rd.compute_trance_level(2) == 30

    def test_apathy_also_dampens_external(self):
        """무관심 → external 가산도 절반 감쇠."""
        self._set_stats(arousal=0, gauge=0, restraint=50, external=50)
        assert rd.compute_trance_level(2) == 50
        morld.set_unit_prop(2, "성향:무관심", 1)
        assert rd.compute_trance_level(2) == 25


# ============================================
# 트랜스 효과 배율 (Phase 1.8)
# ============================================

class TestTranceMultipliers:
    def setUp(self):
        _setup_pair()

    def test_no_trance_all_ones(self):
        """트랜스 없음 → 모든 배율 1.0."""
        morld.set_unit_prop(2, "상태:트랜스", 0)
        mult = rd.compute_trance_multipliers(2)
        for k in ("affection", "rebellion", "submission", "arousal",
                  "desire", "climax_gauge", "experience"):
            assert mult[k] == 1.0, f"{k} not 1.0"

    def test_trance_entry_reduces_affection(self):
        """트랜스 60 → 호감/반발 0.6."""
        morld.set_unit_prop(2, "상태:트랜스", 60)
        mult = rd.compute_trance_multipliers(2)
        assert mult["affection"] == 0.6
        assert mult["rebellion"] == 0.6

    def test_trance_entry_boosts_body(self):
        """트랜스 60 → 복종/성욕/절정/경험 증폭."""
        morld.set_unit_prop(2, "상태:트랜스", 60)
        mult = rd.compute_trance_multipliers(2)
        assert mult["submission"] == 1.2
        assert mult["arousal"] == 1.1
        assert mult["climax_gauge"] == 1.2
        assert mult["experience"] == 1.2

    def test_trance_deep_extreme_reduction(self):
        """트랜스 80 → 호감/반발 0.3 (의식 흐림)."""
        morld.set_unit_prop(2, "상태:트랜스", 80)
        mult = rd.compute_trance_multipliers(2)
        assert mult["affection"] == 0.3
        assert mult["rebellion"] == 0.3

    def test_trance_deep_body_maxed(self):
        """트랜스 80 → 복종/절정/경험 1.5."""
        morld.set_unit_prop(2, "상태:트랜스", 80)
        mult = rd.compute_trance_multipliers(2)
        assert mult["submission"] == 1.5
        assert mult["climax_gauge"] == 1.5
        assert mult["experience"] == 1.5

    def test_entry_threshold_exact(self):
        """트랜스 59 → 배율 1.0, 60 → 트랜스 구간."""
        morld.set_unit_prop(2, "상태:트랜스", 59)
        assert rd.compute_trance_multipliers(2)["submission"] == 1.0
        morld.set_unit_prop(2, "상태:트랜스", 60)
        assert rd.compute_trance_multipliers(2)["submission"] == 1.2

    def test_deep_threshold_exact(self):
        """트랜스 79 → entry 구간, 80 → deep 구간."""
        morld.set_unit_prop(2, "상태:트랜스", 79)
        assert rd.compute_trance_multipliers(2)["submission"] == 1.2
        morld.set_unit_prop(2, "상태:트랜스", 80)
        assert rd.compute_trance_multipliers(2)["submission"] == 1.5

    def test_missing_prop_defaults_zero(self):
        """트랜스 prop 없으면 0 취급 → 배율 1.0."""
        mult = rd.compute_trance_multipliers(2)
        assert mult["submission"] == 1.0


# ============================================
# 실질 자제심 — 복종 침잠 (Phase 1.9)
# ============================================

class TestEffectiveRestraint:
    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_no_submission_returns_raw(self):
        morld.set_unit_prop(2, "성격:자제심", 80)
        assert rd.get_effective_restraint(2) == 80

    def test_submission_below_threshold_no_erosion(self):
        """복종 60 미만은 감쇠 없음."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 50)
        assert rd.get_effective_restraint(2) == 80

    def test_submission_at_threshold_no_erosion(self):
        """복종 60 정확히 경계 — 감쇠 0."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 60)
        assert rd.get_effective_restraint(2) == 80

    def test_submission_70_small_erosion(self):
        """복종 70 → -7.5 → 72 (int)."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 70)
        # erosion = 10 × 0.75 = 7.5 → int(80 - 7.5) = 72
        assert rd.get_effective_restraint(2) == 72

    def test_submission_80_partial_erosion(self):
        """복종 80 → -15 → 65."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 80)
        assert rd.get_effective_restraint(2) == 65

    def test_submission_100_max_erosion(self):
        """복종 100 → -30 → 50."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 100)
        assert rd.get_effective_restraint(2) == 50

    def test_floor_at_zero(self):
        """감쇠가 raw보다 크면 0으로 clamp."""
        morld.set_unit_prop(2, "성격:자제심", 20)
        morld.set_unit_prop(2, get_submission_key(1), 100)
        # erosion 30, raw 20 → -10 → clamp 0
        assert rd.get_effective_restraint(2) == 0


class TestTranceInfluencedByCorruption:
    """Phase 1.9: 복종 누적이 트랜스 진입을 쉽게 만드는지."""

    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_high_restraint_no_submission_defends(self):
        """고자제심 + 복종 0 → 트랜스 방어."""
        morld.set_unit_prop(2, "성격:자제심", 90)
        morld.set_unit_prop(2, "상태:성욕", 100)
        morld.set_unit_prop(2, "상태:절정", 80)
        # effective = 90, factor = max(0.1, 1 - 40×0.02) = 0.2
        # base = 90 × 0.2 = 18
        trance = rd.compute_trance_level(2)
        assert trance < 60, f"expected <60, got {trance}"

    def test_corrupted_high_restraint_loses_defense(self):
        """고자제심이어도 복종 100이면 트랜스 방어 소실."""
        morld.set_unit_prop(2, "성격:자제심", 90)
        morld.set_unit_prop(2, get_submission_key(1), 100)
        morld.set_unit_prop(2, "상태:성욕", 100)
        morld.set_unit_prop(2, "상태:절정", 80)
        # erosion 30, effective = 60
        # factor = max(0.1, 1 - 10×0.02) = 0.8
        # base = 90 × 0.8 = 72
        trance = rd.compute_trance_level(2)
        assert trance >= 60, f"expected >=60 (entry), got {trance}"

    def test_corruption_cascade_to_deep_trance(self):
        """복종 극한 + 고흥분 → 깊은 트랜스 진입."""
        morld.set_unit_prop(2, "성격:자제심", 80)
        morld.set_unit_prop(2, get_submission_key(1), 100)
        morld.set_unit_prop(2, "상태:성욕", 100)
        morld.set_unit_prop(2, "상태:절정", 100)
        # erosion 30, effective = 50 → factor 1.0
        # base = 100 × 1.0 = 100 → trance_deep
        trance = rd.compute_trance_level(2)
        assert trance >= 80, f"expected deep trance, got {trance}"


# ============================================
# 절정 경험 / 일시 자제심 상실 (Phase 1.9.1)
# ============================================

class TestClimaxExperienceBonus:
    """누적 절정 경험이 트랜스 base에 소폭 기여 (era 快楽 근사)."""

    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_no_experience_no_bonus(self):
        """절정 경험 0 → bonus 0."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 0)
        # base = 30 + 0 = 30, factor 1.0 → 30
        assert rd.compute_trance_level(2) == 30

    def test_modest_experience_small_bonus(self):
        """경험 10회 (부위 무관) → bonus 3."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "경험:절정:V", 10)
        # bonus = min(15, 10 × 0.3) = 3
        # base = 30 + 3 = 33
        assert rd.compute_trance_level(2) == 33

    def test_experience_bonus_capped(self):
        """경험 합산 매우 많아도 cap 15."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "경험:절정:V", 100)
        morld.set_unit_prop(2, "경험:절정:C", 100)
        # sum 200, bonus = min(15, 60) = 15
        # base = 30 + 15 = 45
        assert rd.compute_trance_level(2) == 45

    def test_experience_sums_across_parts(self):
        """여러 부위 합산."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "경험:절정:V", 10)
        morld.set_unit_prop(2, "경험:절정:A", 10)
        morld.set_unit_prop(2, "경험:절정:C", 10)
        # sum 30, bonus = min(15, 9) = 9
        # base = 30 + 9 = 39
        assert rd.compute_trance_level(2) == 39


class TestTemporaryRestraintLossViaExternal:
    """절정 발동 → 트랜스:외부 +20 (일시 자제심 상실 시뮬레이션)."""

    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_external_boosts_trance_even_high_restraint(self):
        """고자제심 NPC에 외부 가산이 있으면 트랜스 진입 가능."""
        morld.set_unit_prop(2, "성격:자제심", 90)
        morld.set_unit_prop(2, "상태:성욕", 80)
        morld.set_unit_prop(2, "상태:절정", 40)
        # base = 60 × 0.2 = 12 → 평상 시 진입 불가
        assert rd.compute_trance_level(2) < 60
        # 연속 절정 3회분 외부 가산 (60)
        morld.set_unit_prop(2, "트랜스:외부", 60)
        # value = 12 + 60 = 72 → 진입
        assert rd.compute_trance_level(2) >= 60

    def test_external_recovers_after_decay(self):
        """외부 가산이 감쇠되면 트랜스에서 이탈."""
        morld.set_unit_prop(2, "성격:자제심", 90)
        morld.set_unit_prop(2, "상태:성욕", 80)
        morld.set_unit_prop(2, "상태:절정", 40)
        morld.set_unit_prop(2, "트랜스:외부", 60)
        high = rd.compute_trance_level(2)
        # 자연 감쇠 후 (예: 외부 10으로 감소)
        morld.set_unit_prop(2, "트랜스:외부", 10)
        low = rd.compute_trance_level(2)
        assert low < high
        assert low < 60  # 미진입 구간으로 복귀


# ============================================
# 트랜스 이탈 훅 (Phase 1.9.2) — 회복 후 부끄러움
# ============================================

class TestPostTranceReturn:
    """트랜스 이탈 감지 → `on_post_trance_return` 수치심 발동."""

    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_deep_trance_exit_triggers_shame(self):
        """깊은 트랜스(80+)에서 이탈 → 수치심 +25."""
        morld.set_unit_prop(2, "상태:트랜스", 85)
        morld.set_unit_prop(2, "상태:수치심", 10)
        # 다음 update에서 저흥분 → 이탈
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 30)
        morld.set_unit_prop(2, "상태:절정", 0)
        rd.update_trance_level(2)
        after = morld.get_unit_prop(2, "상태:수치심")
        # 수치심 10 + 25 = 35
        assert after == 35

    def test_entry_trance_exit_triggers_smaller_shame(self):
        """일반 트랜스(60~79)에서 이탈 → 수치심 +15."""
        morld.set_unit_prop(2, "상태:트랜스", 65)
        morld.set_unit_prop(2, "상태:수치심", 10)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 30)
        morld.set_unit_prop(2, "상태:절정", 0)
        rd.update_trance_level(2)
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after == 25  # 10 + 15

    def test_no_exit_no_shame(self):
        """트랜스 상승 중이거나 유지 중이면 훅 발동 안 함."""
        morld.set_unit_prop(2, "상태:트랜스", 30)
        morld.set_unit_prop(2, "상태:수치심", 10)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 40)
        rd.update_trance_level(2)
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after == 10  # 변화 없음 (트랜스 <60 → 미진입)

    def test_staying_in_trance_no_hook(self):
        """트랜스 유지 중(entry 이상 → entry 이상)이면 훅 발동 안 함."""
        morld.set_unit_prop(2, "상태:트랜스", 75)
        morld.set_unit_prop(2, "상태:수치심", 10)
        # 새 계산값도 entry 이상이 되도록
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 100)
        morld.set_unit_prop(2, "상태:절정", 60)
        rd.update_trance_level(2)
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after == 10  # 훅 발동 안 함

    def test_below_entry_to_below_entry_no_hook(self):
        """처음부터 트랜스 없음 → 변화 없음 시 훅 발동 안 함."""
        morld.set_unit_prop(2, "상태:트랜스", 40)
        morld.set_unit_prop(2, "상태:수치심", 10)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 30)
        morld.set_unit_prop(2, "상태:절정", 0)
        rd.update_trance_level(2)
        after = morld.get_unit_prop(2, "상태:수치심")
        assert after == 10


class TestTranceExitRegistry:
    """Phase 1.9.3: 세션 대사 삽입용 이탈 정보 레지스트리."""

    def setUp(self):
        _setup_pair()
        morld._player_id = 1
        # Registry clear
        rd._LAST_TRANCE_EXITS.clear()

    def test_registry_populated_on_exit(self):
        """트랜스 이탈 → registry에 정보 저장."""
        morld.set_unit_prop(2, "상태:트랜스", 85)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 30)
        morld.set_unit_prop(2, "상태:절정", 0)
        rd.update_trance_level(2)
        info = rd.pop_last_trance_exit(2)
        assert info is not None
        assert info["prev_peak"] == 85
        assert info["shame_gain"] == 25

    def test_registry_pop_consumes(self):
        """pop 후 두 번째 pop은 None (1회성)."""
        morld.set_unit_prop(2, "상태:트랜스", 70)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 30)
        morld.set_unit_prop(2, "상태:절정", 0)
        rd.update_trance_level(2)
        first = rd.pop_last_trance_exit(2)
        second = rd.pop_last_trance_exit(2)
        assert first is not None
        assert first["shame_gain"] == 15
        assert second is None

    def test_registry_empty_when_no_exit(self):
        """이탈 안 하면 registry 비어 있음."""
        morld.set_unit_prop(2, "상태:트랜스", 30)
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 60)
        morld.set_unit_prop(2, "상태:절정", 40)
        rd.update_trance_level(2)
        assert rd.pop_last_trance_exit(2) is None


# ============================================
# 상태:취기 통합 (Phase 1.9.4)
# ============================================

class TestDrunkennessAxis:
    def setUp(self):
        _setup_pair()
        morld._player_id = 1

    def test_drunk_alone_adds_to_trance(self):
        """취기만 있어도 트랜스에 기여."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 0)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "상태:취기", 40)
        # base=0, factor 1.0, external=0+drunk=40 → trance 40
        assert rd.compute_trance_level(2) == 40

    def test_drunk_plus_external_sums(self):
        """트랜스:외부 + 상태:취기 합산."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 20)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "트랜스:외부", 20)
        morld.set_unit_prop(2, "상태:취기", 30)
        # base=10, external 20+30=50 → 60
        assert rd.compute_trance_level(2) == 60

    def test_drunk_bypasses_restraint(self):
        """고자제심도 취기로 트랜스 진입 가능."""
        morld.set_unit_prop(2, "성격:자제심", 100)
        morld.set_unit_prop(2, "상태:성욕", 20)
        morld.set_unit_prop(2, "상태:절정", 0)
        morld.set_unit_prop(2, "상태:취기", 70)
        # base=10 × 0.1 = 1, +취기 70 → 71 (진입!)
        assert rd.compute_trance_level(2) >= 60

    def test_drunk_clamped_at_100(self):
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 100)
        morld.set_unit_prop(2, "상태:절정", 100)
        morld.set_unit_prop(2, "상태:취기", 100)
        # 200 초과 → clamp 100
        assert rd.compute_trance_level(2) == 100

    def test_drunk_missing_defaults_zero(self):
        """취기 prop 없으면 0 취급, 기존 공식과 동일."""
        morld.set_unit_prop(2, "성격:자제심", 50)
        morld.set_unit_prop(2, "상태:성욕", 80)
        morld.set_unit_prop(2, "상태:절정", 40)
        # base=60, external 0, drunk 0 → 60
        assert rd.compute_trance_level(2) == 60
