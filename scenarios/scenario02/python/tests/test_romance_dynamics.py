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

    def test_gain_blocked_by_submission_at_threshold(self):
        morld.set_unit_prop(2, get_submission_key(1), rd.LOVE_BLOCK_SUBMISSION)
        delta = rd.modify_love(2, 1, 10)
        assert delta == 0
        assert rd.get_love(2, 1) == 0

    def test_gain_blocked_by_submission_above_threshold(self):
        morld.set_unit_prop(2, get_submission_key(1), 80)
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
        assert morld.get_unit_prop(2, "상태:트랜스") is None


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
