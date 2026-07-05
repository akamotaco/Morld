# test_player_contract.py — 플레이어 부재 계약 (infra-unification-plan §2-2)
#
# 계약: get_player_id()는 플레이어 미등록 시 None이 아니라 0을 반환한다
# (유닛 id는 1부터 발급 → 0=부재 sentinel). 공용 엔진은 플레이어 없는
# 시나리오(S03 오퍼레이터형)에서도 안전하게 동작해야 한다.
import morld


class TestPlayerIdContract:
    def test_default_is_zero_not_none(self):
        """미등록 시 0 — None 반환 금지 (is None 가드는 죽은 분기)"""
        assert morld.get_player_id() == 0
        assert morld.get_player_id() is not None

    def test_add_unit_player_unique_id_sets_player(self):
        """add_unit(unique_id="player")가 유일한 플레이어 지정 경로"""
        morld.add_unit(42, "주인공", 0, 0, "male", unique_id="player")
        assert morld.get_player_id() == 42

    def test_other_unique_id_does_not_set_player(self):
        morld.add_unit(43, "행인", 0, 0, "male", unique_id="npc_a")
        assert morld.get_player_id() == 0


class TestPlayerlessEngineSafety:
    """플레이어 없는 상태에서 공용 엔진 모듈이 기본값으로 안전 동작"""

    def test_lighting_portable_light(self):
        from engine import lighting
        assert lighting.get_player_portable_light() == 0.0

    def test_lighting_brightness_default(self):
        from engine import lighting
        # 위치 미지정 + 플레이어 부재 → 최대 밝기 폴백
        assert lighting.get_location_brightness() == 1.0

    def test_stealth_visibility_default(self):
        from engine import stealth
        v = stealth.get_stealth_visibility()  # unit_id=None → player → 부재
        assert v == stealth.STEALTH_VISIBILITY_VISIBLE

    def test_stealth_cover_default(self):
        from engine import stealth
        assert stealth.get_cover_coefficient() == stealth.COVER_COEFFICIENT_NONE
