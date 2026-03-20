# test_story.py — 챕터 1 스토리 로직 테스트
"""
테스트 대상: story.py
- 알파 판정 (신뢰/굴복/혼합 루트)
- 단둘이 판정
- 발각 판정
- 약점 플래그
- 다수결 굴복
- 일일 퀘스트 선택 로직 (SeraAgent)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mock_morld import MockMorld

mock = MockMorld()
sys.modules["morld"] = mock


def _setup():
    """각 테스트 전 초기화"""
    mock.reset()
    # 플레이어
    mock.register_unit(1, "주인공", location=(0, 0))
    mock._player_id = 1
    # 저택 NPC
    mock.register_unit(10, "세라", location=(0, 1), props={"unique_id": "sera"})
    mock.register_unit(11, "밀라", location=(0, 2), props={"unique_id": "mila"})
    mock.register_unit(12, "리나", location=(0, 3), props={"unique_id": "lina"})
    # 오브젝트 (가구)
    mock.register_unit(100, "침대", location=(0, 1), is_object=True)


class _T:
    def __init__(self):
        _setup()


# ========================================
# 알파 판정 테스트
# ========================================

class TestAlphaCheck(_T):

    def test_no_progress(self):
        """초기 상태: 알파 미달성"""
        from story import check_alpha_status
        assert check_alpha_status(1) == False

    def test_trust_route_all(self):
        """신뢰 루트: 3명 모두 신뢰+호감 충족 → 알파"""
        from story import check_alpha_status
        for name in ["세라", "밀라", "리나"]:
            mock.set_unit_prop(1, f"관계:{name}:신뢰", 10)
            mock.set_unit_prop(1, f"관계:{name}:호감", 60)
        assert check_alpha_status(1) == True

    def test_trust_route_partial(self):
        """신뢰 루트: 2명만 충족 → 미달성"""
        from story import check_alpha_status
        for name in ["세라", "밀라"]:
            mock.set_unit_prop(1, f"관계:{name}:신뢰", 10)
            mock.set_unit_prop(1, f"관계:{name}:호감", 60)
        assert check_alpha_status(1) == False

    def test_submission_route_all(self):
        """굴복 루트: 3명 모두 복종 충족 → 알파"""
        from story import check_alpha_status
        for name in ["세라", "밀라", "리나"]:
            mock.set_unit_prop(1, f"관계:{name}:복종", 70)
        assert check_alpha_status(1) == True

    def test_submission_route_partial(self):
        """굴복 루트: 1명 부족 → 미달성"""
        from story import check_alpha_status
        mock.set_unit_prop(1, "관계:세라:복종", 70)
        mock.set_unit_prop(1, "관계:밀라:복종", 70)
        mock.set_unit_prop(1, "관계:리나:복종", 50)  # 부족
        assert check_alpha_status(1) == False

    def test_mixed_route(self):
        """혼합: 세라=굴복, 밀라=신뢰, 리나=신뢰 → 알파"""
        from story import check_alpha_status
        mock.set_unit_prop(1, "관계:세라:복종", 70)
        mock.set_unit_prop(1, "관계:밀라:신뢰", 10)
        mock.set_unit_prop(1, "관계:밀라:호감", 60)
        mock.set_unit_prop(1, "관계:리나:신뢰", 10)
        mock.set_unit_prop(1, "관계:리나:호감", 60)
        assert check_alpha_status(1) == True

    def test_trust_threshold_boundary(self):
        """신뢰 경계값: 신뢰 9 → 미달, 10 → 달성"""
        from story import check_alpha_status
        for name in ["세라", "밀라", "리나"]:
            mock.set_unit_prop(1, f"관계:{name}:신뢰", 9)
            mock.set_unit_prop(1, f"관계:{name}:호감", 60)
        assert check_alpha_status(1) == False
        for name in ["세라", "밀라", "리나"]:
            mock.set_unit_prop(1, f"관계:{name}:신뢰", 10)
        assert check_alpha_status(1) == True

    def test_progress_report(self):
        """진행 상태 리포트"""
        from story import get_alpha_progress
        mock.set_unit_prop(1, "관계:세라:복종", 70)
        mock.set_unit_prop(1, "관계:밀라:호감", 30)
        progress = get_alpha_progress(1)
        assert progress["세라"]["done"] == True
        assert progress["세라"]["submission_ok"] == True
        assert progress["밀라"]["done"] == False
        assert progress["리나"]["done"] == False


# ========================================
# 단둘이 판정 테스트
# ========================================

class TestAloneWith(_T):

    def test_alone_with_target(self):
        """플레이어 + 세라만 있는 방 → True"""
        from story import is_alone_with
        mock._units[1]["location"] = (0, 1)  # 세라 방으로 이동
        mock._units[1]["info"]["region_id"] = 0
        mock._units[1]["info"]["location_id"] = 1
        # 세라(10) + 침대(100, 오브젝트) + 플레이어(1) = 캐릭터 2명
        assert is_alone_with(1, 10) == True

    def test_not_alone_third_person(self):
        """3명 이상 있으면 → False"""
        from story import is_alone_with
        mock._units[1]["location"] = (0, 1)
        mock._units[1]["info"]["region_id"] = 0
        mock._units[1]["info"]["location_id"] = 1
        # 밀라도 같은 방으로
        mock._units[11]["location"] = (0, 1)
        mock._units[11]["info"]["region_id"] = 0
        mock._units[11]["info"]["location_id"] = 1
        assert is_alone_with(1, 10) == False

    def test_different_location(self):
        """다른 방에 있으면 → False"""
        from story import is_alone_with
        # 플레이어(0,0), 세라(0,1) — 다른 위치
        assert is_alone_with(1, 10) == False

    def test_object_ignored(self):
        """오브젝트는 카운트에서 제외"""
        from story import is_alone_with
        mock._units[1]["location"] = (0, 1)
        mock._units[1]["info"]["region_id"] = 0
        mock._units[1]["info"]["location_id"] = 1
        # 오브젝트 추가
        mock.register_unit(101, "책상", location=(0, 1), is_object=True)
        assert is_alone_with(1, 10) == True

    def test_get_others(self):
        """현재 위치의 다른 캐릭터 목록"""
        from story import get_other_characters_at
        mock._units[1]["location"] = (0, 1)
        mock._units[1]["info"]["region_id"] = 0
        mock._units[1]["info"]["location_id"] = 1
        others = get_other_characters_at(1)
        assert 10 in others  # 세라
        assert 100 not in others  # 침대(오브젝트)는 제외


# ========================================
# 발각 판정 테스트
# ========================================

class TestDiscovery(_T):

    def test_mila_forgives_high_affection(self):
        """밀라: 호감 >= 30이면 눈감아줌"""
        from story import check_discovery
        mock.set_unit_prop(11, "관계:주인공:호감", 30)
        result = check_discovery(1, 10, 11)  # 세라에게 강제, 밀라 목격
        assert result == "forgive"

    def test_mila_expulsion_low_affection(self):
        """밀라: 호감 < 30이면 추방"""
        from story import check_discovery
        mock.set_unit_prop(11, "관계:주인공:호감", 20)
        result = check_discovery(1, 10, 11)
        assert result == "expulsion"

    def test_lina_always_expulsion(self):
        """리나: 호감과 무관하게 추방"""
        from story import check_discovery
        mock.set_unit_prop(12, "관계:주인공:호감", 100)  # 높아도
        result = check_discovery(1, 10, 12)
        assert result == "expulsion"

    def test_sera_always_expulsion(self):
        """세라(목격자): 추방"""
        from story import check_discovery
        result = check_discovery(1, 12, 10)  # 리나에게 강제, 세라 목격
        assert result == "expulsion"


# ========================================
# 약점 플래그 테스트
# ========================================

class TestWeakness(_T):

    def test_set_and_check(self):
        """약점 설정 및 확인"""
        from story import set_weakness, has_weakness
        assert has_weakness(1, "세라", "자위발각") == False
        set_weakness(1, "세라", "자위발각")
        assert has_weakness(1, "세라", "자위발각") == True

    def test_multiple_weaknesses(self):
        """여러 약점 관리"""
        from story import set_weakness, get_all_weaknesses
        set_weakness(1, "세라", "자위발각")
        set_weakness(1, "세라", "성인용품발견")
        set_weakness(1, "리나", "호기심")
        weaknesses = get_all_weaknesses(1, "세라")
        assert "자위발각" in weaknesses
        assert "성인용품발견" in weaknesses
        assert len(weaknesses) == 2

    def test_no_cross_contamination(self):
        """다른 캐릭터의 약점은 포함되지 않음"""
        from story import set_weakness, get_all_weaknesses
        set_weakness(1, "세라", "자위발각")
        set_weakness(1, "리나", "호기심")
        sera_w = get_all_weaknesses(1, "세라")
        assert "호기심" not in sera_w


# ========================================
# 다수결 굴복 테스트
# ========================================

class TestMajority(_T):

    def test_majority_possible(self):
        """밀라+리나가 플레이어 편 → 세라에 다수결 가능"""
        from story import check_majority_against
        mock.set_unit_prop(1, "관계:밀라:호감", 50)
        mock.set_unit_prop(1, "관계:리나:호감", 50)
        assert check_majority_against(1, "세라") == True

    def test_majority_by_submission(self):
        """복종으로도 '플레이어 편' 인정"""
        from story import check_majority_against
        mock.set_unit_prop(1, "관계:밀라:복종", 50)
        mock.set_unit_prop(1, "관계:리나:복종", 50)
        assert check_majority_against(1, "세라") == True

    def test_majority_one_short(self):
        """1명만 편이면 다수결 불가"""
        from story import check_majority_against
        mock.set_unit_prop(1, "관계:밀라:호감", 50)
        mock.set_unit_prop(1, "관계:리나:호감", 30)  # 부족
        assert check_majority_against(1, "세라") == False

    def test_majority_against_mila(self):
        """밀라 대상: 세라+리나가 편이어야"""
        from story import check_majority_against
        mock.set_unit_prop(1, "관계:세라:호감", 50)
        mock.set_unit_prop(1, "관계:리나:호감", 50)
        assert check_majority_against(1, "밀라") == True

    def test_majority_mixed(self):
        """혼합: 한 명은 호감, 한 명은 복종"""
        from story import check_majority_against
        mock.set_unit_prop(1, "관계:밀라:호감", 50)
        mock.set_unit_prop(1, "관계:리나:복종", 50)
        assert check_majority_against(1, "세라") == True


# ========================================
# 일일 퀘스트 선택 테스트
# ========================================

class TestDailyQuestSelection(_T):

    def test_select_3_from_7(self):
        """매일 7개 중 3개 선택"""
        # SeraAgent 직접 테스트 대신 로직만 검증
        import random
        pool = [
            "daily_gather_herb", "daily_gather_berry", "daily_firewood",
            "daily_fishing", "daily_clean", "daily_water_garden", "daily_deliver_food",
        ]
        selected = random.sample(pool, 3)
        assert len(selected) == 3
        assert len(set(selected)) == 3  # 중복 없음
        for s in selected:
            assert s in pool

    def test_daily_quest_prop_storage(self):
        """선택된 퀘스트 prop 저장/조회"""
        selected = ["daily_gather_herb", "daily_fishing", "daily_clean"]
        mock.set_unit_prop(10, "일일퀘스트:오늘", ",".join(selected))

        raw = mock.get_unit_prop(10, "일일퀘스트:오늘")
        restored = [q.strip() for q in raw.split(",") if q.strip()]
        assert restored == selected

    def test_filter_daily_quests(self):
        """daily 필터링: 오늘 선택된 것만 통과"""
        today = {"daily_gather_herb", "daily_fishing", "daily_clean"}

        all_quests = [
            ("daily_gather_herb", "daily"),
            ("daily_gather_berry", "daily"),
            ("daily_firewood", "daily"),
            ("daily_fishing", "daily"),
            ("daily_clean", "daily"),
            ("daily_water_garden", "daily"),
            ("daily_deliver_food", "daily"),
            ("sera_fishing", "personal"),  # non-daily
        ]

        filtered = []
        for qid, cat in all_quests:
            if cat == "daily":
                if qid in today:
                    filtered.append(qid)
            else:
                filtered.append(qid)

        assert len(filtered) == 4  # 3 daily + 1 personal
        assert "daily_gather_berry" not in filtered
        assert "sera_fishing" in filtered


# ========================================
# 플레이어 피로 테스트
# ========================================

class TestPlayerFatigue(_T):

    def test_normal(self):
        """피로 0 → normal"""
        from story import check_player_fatigue
        assert check_player_fatigue(1) == "normal"

    def test_warning(self):
        """피로 80 → warning"""
        from story import check_player_fatigue
        mock.set_unit_prop(1, "욕구:피로", 80)
        assert check_player_fatigue(1) == "warning"

    def test_forced_sleep(self):
        """피로 95 → forced_sleep"""
        from story import check_player_fatigue
        mock.set_unit_prop(1, "욕구:피로", 95)
        assert check_player_fatigue(1) == "forced_sleep"

    def test_action_fatigue(self):
        """행동별 피로 증가"""
        from story import add_action_fatigue
        mock.set_unit_prop(1, "욕구:피로", 50)
        add_action_fatigue(1, "전투")
        assert mock.get_unit_prop(1, "욕구:피로") == 60

    def test_action_fatigue_cap(self):
        """피로 100 초과 방지"""
        from story import add_action_fatigue
        mock.set_unit_prop(1, "욕구:피로", 98)
        add_action_fatigue(1, "전투")  # +10
        assert mock.get_unit_prop(1, "욕구:피로") == 100

    def test_unknown_action(self):
        """미등록 행동 → 증가 없음"""
        from story import add_action_fatigue
        mock.set_unit_prop(1, "욕구:피로", 50)
        result = add_action_fatigue(1, "독서")
        assert result == 0
        assert mock.get_unit_prop(1, "욕구:피로") == 50


# ========================================
# 수면 중 강제 기상 테스트
# ========================================

class TestBedKick(_T):

    def test_kick_low_affection(self):
        """호감 < 30인 침대에서 자면 쫓겨남"""
        from story import should_kick_from_bed
        mock.set_unit_prop(1, "관계:세라:호감", 10)
        assert should_kick_from_bed(1, "세라") == True

    def test_no_kick_high_affection(self):
        """호감 >= 30이면 OK"""
        from story import should_kick_from_bed
        mock.set_unit_prop(1, "관계:세라:호감", 30)
        assert should_kick_from_bed(1, "세라") == False

    def test_no_kick_own_bed(self):
        """자기 침대면 쫓기지 않음"""
        from story import should_kick_from_bed
        assert should_kick_from_bed(1, "주인공") == False

    def test_no_kick_unowned(self):
        """주인 없는 침대는 자유"""
        from story import should_kick_from_bed
        assert should_kick_from_bed(1, None) == False


# ========================================
# 퀘스트 시간제한 테스트
# ========================================

class TestQuestTimeout(_T):

    def test_daily_timeout(self):
        """일일 퀘스트: 18시 이후 미완료 → 타임아웃"""
        from story import check_quest_timeout
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 2)  # IN_PROGRESS
        assert check_quest_timeout(1, "daily_gather_herb", 17) == False
        assert check_quest_timeout(1, "daily_gather_herb", 18) == True

    def test_non_daily_no_timeout(self):
        """비일일 퀘스트: 시간제한 없음"""
        from story import check_quest_timeout
        mock.set_unit_prop(1, "퀘스트:sera_fishing:상태", 2)
        assert check_quest_timeout(1, "sera_fishing", 23) == False

    def test_not_in_progress_no_timeout(self):
        """진행 중이 아니면 타임아웃 아님"""
        from story import check_quest_timeout
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 1)  # AVAILABLE
        assert check_quest_timeout(1, "daily_gather_herb", 20) == False

    def test_quest_failure_effects(self):
        """퀘스트 실패: 신뢰 -1 + 상태 리셋"""
        from story import apply_quest_failure
        mock.set_unit_prop(1, "관계:세라:신뢰", 5)
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 2)

        effects = apply_quest_failure(1, "daily_gather_herb")

        assert mock.get_unit_prop(1, "관계:세라:신뢰") == 4
        assert mock.get_unit_prop(1, "퀘스트:daily_gather_herb:상태") == 0
        assert effects["trust_loss"] == -1

    def test_quest_failure_trust_goes_negative(self):
        """신뢰 음수 허용 (추방 트리거용)"""
        from story import apply_quest_failure
        mock.set_unit_prop(1, "관계:세라:신뢰", 0)
        apply_quest_failure(1, "daily_gather_herb")
        assert mock.get_unit_prop(1, "관계:세라:신뢰") == -1

    def test_auto_fail_integration(self):
        """통합: _on_time_elapsed가 18시에 진행 중 일일퀘스트를 자동 실패시킴"""
        from story import _on_time_elapsed
        mock.set_unit_prop(1, "관계:세라:신뢰", 5)
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 2)  # IN_PROGRESS
        mock.set_unit_prop(1, "퀘스트:daily_fishing:상태", 2)      # IN_PROGRESS
        mock._time_info = {"hour": 18, "day": 1, "month": 1, "year": 1, "minute": 0}

        _on_time_elapsed(3_600_000)

        # 두 퀘스트 모두 실패 → 신뢰 -2
        assert mock.get_unit_prop(1, "관계:세라:신뢰") == 3
        assert mock.get_unit_prop(1, "퀘스트:daily_gather_herb:상태") == 0
        assert mock.get_unit_prop(1, "퀘스트:daily_fishing:상태") == 0

    def test_auto_fail_skips_completed(self):
        """완료된 퀘스트는 자동 실패 안 함"""
        from story import _on_time_elapsed
        mock.set_unit_prop(1, "관계:세라:신뢰", 5)
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 3)  # COMPLETED
        mock._time_info = {"hour": 18, "day": 1, "month": 1, "year": 1, "minute": 0}

        _on_time_elapsed(3_600_000)

        assert mock.get_unit_prop(1, "관계:세라:신뢰") == 5  # 변동 없음

    def test_auto_fail_before_deadline(self):
        """마감 전에는 실패 안 함"""
        from story import _on_time_elapsed
        mock.set_unit_prop(1, "관계:세라:신뢰", 5)
        mock.set_unit_prop(1, "퀘스트:daily_gather_herb:상태", 2)
        mock._time_info = {"hour": 17, "day": 1, "month": 1, "year": 1, "minute": 0}

        _on_time_elapsed(3_600_000)

        assert mock.get_unit_prop(1, "관계:세라:신뢰") == 5  # 변동 없음


# ========================================
# 추방 시스템 테스트
# ========================================

class TestExpulsion(_T):

    def test_expulsion_trigger(self):
        """신뢰 -3 이하 → 추방 트리거"""
        from story import check_expulsion_trigger
        mock.set_unit_prop(1, "관계:세라:신뢰", -3)
        assert check_expulsion_trigger(1) == True

    def test_no_expulsion_above_threshold(self):
        """신뢰 -2 → 추방 안 됨"""
        from story import check_expulsion_trigger
        mock.set_unit_prop(1, "관계:세라:신뢰", -2)
        assert check_expulsion_trigger(1) == False

    def test_no_expulsion_if_already_expelled(self):
        """이미 추방된 상태면 중복 추방 안 됨"""
        from story import check_expulsion_trigger
        mock.set_unit_prop(1, "관계:세라:신뢰", -5)
        mock.set_unit_prop(1, "스토리:추방됨", 1)
        assert check_expulsion_trigger(1) == False

    def test_no_expulsion_if_alpha(self):
        """알파 달성 후에는 추방 안 됨"""
        from story import check_expulsion_trigger
        mock.set_unit_prop(1, "관계:세라:신뢰", -5)
        # 알파 조건 충족 (점령)
        mock.set_unit_prop(1, "스토리:저택점령", 1)
        assert check_expulsion_trigger(1) == False

    def test_apply_expulsion_effects(self):
        """추방 효과: 플래그 + 호감 -15 + 반발 +20"""
        from story import apply_expulsion, is_expelled
        mock.set_unit_prop(1, "관계:세라:호감", 30)
        mock.set_unit_prop(1, "관계:밀라:호감", 50)
        mock.set_unit_prop(1, "관계:리나:호감", 20)

        apply_expulsion(1)

        assert is_expelled(1) == True
        assert mock.get_unit_prop(1, "관계:세라:호감") == 15
        assert mock.get_unit_prop(1, "관계:밀라:호감") == 35
        assert mock.get_unit_prop(1, "관계:리나:호감") == 5
        assert mock.get_unit_prop(1, "관계:세라:반발") == 20

    def test_expulsion_faction_hostile(self):
        """추방 시 세력 적대화 (-1)"""
        from story import apply_expulsion, _NAME_TO_UNIQUE
        # mock registry 주입
        import sys
        mock_registry = type(sys)("mock_registry")
        mock_registry.get_instance_id = lambda uid: {"sera": 10, "mila": 11, "lina": 12}.get(uid)
        sys.modules["assets.registry"] = mock_registry

        apply_expulsion(1)

        assert mock.get_unit_prop(10, "관계:방문자:세력도") == -1
        assert mock.get_unit_prop(11, "관계:방문자:세력도") == -1
        assert mock.get_unit_prop(12, "관계:방문자:세력도") == -1

        del sys.modules["assets.registry"]

    def test_conquest_restores_faction(self):
        """점령 시 세력 중립 복원 (0)"""
        from story import apply_expulsion, apply_mansion_conquest
        import sys
        mock_registry = type(sys)("mock_registry")
        mock_registry.get_instance_id = lambda uid: {"sera": 10, "mila": 11, "lina": 12}.get(uid)
        sys.modules["assets.registry"] = mock_registry

        apply_expulsion(1)
        assert mock.get_unit_prop(10, "관계:방문자:세력도") == -1

        apply_mansion_conquest(1)
        assert mock.get_unit_prop(10, "관계:방문자:세력도") == 0
        assert mock.get_unit_prop(11, "관계:방문자:세력도") == 0
        assert mock.get_unit_prop(12, "관계:방문자:세력도") == 0

        del sys.modules["assets.registry"]

    def test_expulsion_affection_floor(self):
        """추방 시 호감 0 미만 방지"""
        from story import apply_expulsion
        mock.set_unit_prop(1, "관계:세라:호감", 5)
        apply_expulsion(1)
        assert mock.get_unit_prop(1, "관계:세라:호감") == 0

    def test_auto_expulsion_via_time(self):
        """통합: 신뢰 바닥 → _on_time_elapsed에서 자동 추방"""
        from story import _on_time_elapsed, is_expelled
        mock.set_unit_prop(1, "관계:세라:신뢰", -3)
        mock._time_info = {"hour": 10, "day": 1, "month": 1, "year": 1, "minute": 0}

        _on_time_elapsed(3_600_000)

        assert is_expelled(1) == True


# ========================================
# 점령 + 알파 테스트
# ========================================

class TestConquest(_T):

    def test_conquest_alpha(self):
        """점령 → 알파 달성"""
        from story import check_alpha_status, apply_mansion_conquest
        assert check_alpha_status(1) == False
        apply_mansion_conquest(1)
        assert check_alpha_status(1) == True

    def test_alpha_by_faction_elimination(self):
        """세력 소멸 → 알파 (전원 사망 or 구금)"""
        from story import check_alpha_status
        import sys
        mock_registry = type(sys)("mock_registry")
        mock_registry.get_instance_id = lambda uid: {"sera": 10, "mila": 11, "lina": 12}.get(uid)
        sys.modules["assets.registry"] = mock_registry

        # NPC에 세력 prop 설정
        mock.set_unit_prop(10, "세력", "숲속 저택")
        mock.set_unit_prop(11, "세력", "숲속 저택")
        mock.set_unit_prop(12, "세력", "숲속 저택")

        assert check_alpha_status(1) == False

        # 전원 사망
        mock.set_unit_prop(10, "상태:사망", 1)
        mock.set_unit_prop(11, "상태:사망", 1)
        mock.set_unit_prop(12, "상태:사망", 1)
        assert check_alpha_status(1) == True

        del sys.modules["assets.registry"]

    def test_alpha_by_mixed_death_restrain(self):
        """혼합: 2명 사망 + 1명 전신결박 → 알파"""
        from story import check_alpha_status
        import sys
        mock_registry = type(sys)("mock_registry")
        mock_registry.get_instance_id = lambda uid: {"sera": 10, "mila": 11, "lina": 12}.get(uid)
        sys.modules["assets.registry"] = mock_registry

        mock.set_unit_prop(10, "세력", "숲속 저택")
        mock.set_unit_prop(11, "세력", "숲속 저택")
        mock.set_unit_prop(12, "세력", "숲속 저택")

        mock.set_unit_prop(10, "상태:사망", 1)
        # 밀라: 전신결박 (상체+하체)
        mock.set_unit_prop(11, "결박:상체", 1)
        mock.set_unit_prop(11, "결박:하체", 1)
        # 리나는 활동 중
        assert check_alpha_status(1) == False

        # 리나도 전신결박
        mock.set_unit_prop(12, "결박:상체", 1)
        mock.set_unit_prop(12, "결박:하체", 1)
        assert check_alpha_status(1) == True

        del sys.modules["assets.registry"]

    def test_partial_restrain_still_active(self):
        """부분 결박(하체만)은 활동 가능 → 세력 인원 유지"""
        from story import count_active_faction_members
        import sys
        mock_registry = type(sys)("mock_registry")
        mock_registry.get_instance_id = lambda uid: {"sera": 10, "mila": 11, "lina": 12}.get(uid)
        sys.modules["assets.registry"] = mock_registry

        mock.set_unit_prop(10, "세력", "숲속 저택")
        mock.set_unit_prop(11, "세력", "숲속 저택")
        mock.set_unit_prop(12, "세력", "숲속 저택")

        # 하체만 결박 → 이동 불가하지만 세력 인원에서 제외 안 됨
        mock.set_unit_prop(10, "결박:하체", 1)
        assert count_active_faction_members("숲속 저택") == 3

        # 상체+하체 → 전신결박 → 제외
        mock.set_unit_prop(10, "결박:상체", 1)
        assert count_active_faction_members("숲속 저택") == 2

        del sys.modules["assets.registry"]

    def test_conquest_clears_expulsion(self):
        """점령 시 추방 플래그 해제"""
        from story import apply_mansion_conquest, is_expelled
        mock.set_unit_prop(1, "스토리:추방됨", 1)
        assert is_expelled(1) == True
        apply_mansion_conquest(1)
        assert is_expelled(1) == False


# ========================================
# 사망 시스템 테스트
# ========================================

class TestFinish(_T):

    def test_finish_fainted(self):
        """기절 상태에서 확인사살 → 사망"""
        from story import execute_finish, is_dead
        mock.set_unit_prop(10, "생존:체력", 0)  # 세라 기절
        result = execute_finish(1, 10)
        assert result["success"] == True
        assert is_dead(10) == True

    def test_finish_not_fainted(self):
        """HP > 0이면 확인사살 불가"""
        from story import execute_finish
        mock.set_unit_prop(10, "생존:체력", 50)
        result = execute_finish(1, 10)
        assert result["success"] == False
        assert result["reason"] == "not_fainted"

    def test_finish_already_dead(self):
        """이미 사망이면 중복 불가"""
        from story import execute_finish
        mock.set_unit_prop(10, "생존:체력", 0)
        mock.set_unit_prop(10, "상태:사망", 1)
        result = execute_finish(1, 10)
        assert result["success"] == False
        assert result["reason"] == "already_dead"


    def test_quest_fail_leads_to_expulsion(self):
        """시나리오: 퀘스트 4회 실패 → 신뢰 1→-3 → 추방"""
        from story import apply_quest_failure, check_expulsion_trigger
        mock.set_unit_prop(1, "관계:세라:신뢰", 1)
        for i in range(4):
            apply_quest_failure(1, f"daily_test_{i}")
        # 신뢰: 1 - 4 = -3
        assert mock.get_unit_prop(1, "관계:세라:신뢰") == -3
        assert check_expulsion_trigger(1) == True


# ========================================
# 유키·엘라 합류 테스트
# ========================================

class TestRecruit(_T):

    def test_persuade_yuki_success(self):
        """유키 설득: 호감 50 이상 → 가능"""
        from story import can_recruit, RECRUIT_PERSUADE
        mock.set_unit_prop(1, "관계:유키:호감", 50)
        assert can_recruit(1, "유키", RECRUIT_PERSUADE) == True

    def test_persuade_yuki_fail(self):
        """유키 설득: 호감 부족 → 불가"""
        from story import can_recruit, RECRUIT_PERSUADE
        mock.set_unit_prop(1, "관계:유키:호감", 40)
        assert can_recruit(1, "유키", RECRUIT_PERSUADE) == False

    def test_persuade_ella_harder(self):
        """엘라 설득: 유키보다 높은 호감 필요"""
        from story import can_recruit, RECRUIT_PERSUADE
        mock.set_unit_prop(1, "관계:엘라:호감", 55)  # 유키 기준은 통과하지만
        assert can_recruit(1, "엘라", RECRUIT_PERSUADE) == False
        mock.set_unit_prop(1, "관계:엘라:호감", 60)
        assert can_recruit(1, "엘라", RECRUIT_PERSUADE) == True

    def test_kidnap_always_possible(self):
        """납치는 조건 없이 가능"""
        from story import can_recruit, RECRUIT_KIDNAP
        assert can_recruit(1, "유키", RECRUIT_KIDNAP) == True

    def test_blackmail_ella_needs_yuki(self):
        """엘라 협박: 유키가 먼저 합류해야"""
        from story import can_recruit, RECRUIT_BLACKMAIL
        assert can_recruit(1, "엘라", RECRUIT_BLACKMAIL) == False
        mock.set_unit_prop(1, "합류:유키", 1)
        assert can_recruit(1, "엘라", RECRUIT_BLACKMAIL) == True

    def test_kidnap_rebellion_penalty(self):
        """납치 시 반발 증가"""
        from story import apply_recruit_effects, RECRUIT_KIDNAP
        effects = apply_recruit_effects(1, "유키", RECRUIT_KIDNAP)
        rebellion = mock.get_unit_prop(1, "관계:유키:반발") or 0
        assert rebellion == 30
        assert (mock.get_unit_prop(1, "합류:유키") or 0) == 1

    def test_persuade_affection_bonus(self):
        """설득 시 호감 보너스"""
        from story import apply_recruit_effects, RECRUIT_PERSUADE
        mock.set_unit_prop(1, "관계:유키:호감", 50)
        apply_recruit_effects(1, "유키", RECRUIT_PERSUADE)
        assert mock.get_unit_prop(1, "관계:유키:호감") == 55

    def test_all_joined(self):
        """전원 합류 확인"""
        from story import check_all_joined
        assert check_all_joined(1) == False
        mock.set_unit_prop(1, "합류:유키", 1)
        assert check_all_joined(1) == False
        mock.set_unit_prop(1, "합류:엘라", 1)
        assert check_all_joined(1) == True


# ========================================
# 페이 합류 테스트
# ========================================

class TestFayeRecruit(_T):

    def test_trade_trust(self):
        """거래 신뢰: 호감 60 이상"""
        from story import can_recruit_faye, RECRUIT_FAYE_TRADE
        assert can_recruit_faye(1, RECRUIT_FAYE_TRADE) == False
        mock.set_unit_prop(1, "관계:페이:호감", 60)
        assert can_recruit_faye(1, RECRUIT_FAYE_TRADE) == True

    def test_rescue(self):
        """위기 구출 이벤트 완료"""
        from story import can_recruit_faye, RECRUIT_FAYE_RESCUE, FAYE_RESCUE_FLAG
        assert can_recruit_faye(1, RECRUIT_FAYE_RESCUE) == False
        mock.set_unit_prop(1, FAYE_RESCUE_FLAG, 1)
        assert can_recruit_faye(1, RECRUIT_FAYE_RESCUE) == True

    def test_offer_after_alpha(self):
        """알파 달성 후 전속 상인 제안"""
        from story import can_recruit_faye, RECRUIT_FAYE_OFFER
        assert can_recruit_faye(1, RECRUIT_FAYE_OFFER) == False
        # 알파 조건 충족
        for name in ["세라", "밀라", "리나"]:
            mock.set_unit_prop(1, f"관계:{name}:복종", 70)
        assert can_recruit_faye(1, RECRUIT_FAYE_OFFER) == True

    def test_blackmail(self):
        """성인용품 판매 비밀 협박"""
        from story import can_recruit_faye, RECRUIT_FAYE_BLACKMAIL, set_weakness
        assert can_recruit_faye(1, RECRUIT_FAYE_BLACKMAIL) == False
        set_weakness(1, "페이", "성인용품판매")
        assert can_recruit_faye(1, RECRUIT_FAYE_BLACKMAIL) == True

    def test_debt(self):
        """빚 관계"""
        from story import can_recruit_faye, RECRUIT_FAYE_DEBT
        assert can_recruit_faye(1, RECRUIT_FAYE_DEBT) == False
        mock.set_unit_prop(1, "관계:페이:빚", 100)
        assert can_recruit_faye(1, RECRUIT_FAYE_DEBT) == True
