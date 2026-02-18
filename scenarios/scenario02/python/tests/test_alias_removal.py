# test_alias_removal.py — alias 제거 + thrust 동작 검증
"""
리네임된 데이터 키 무결성 + thrust_stop 정의 + UI 필터 로직 검증.
"""
import sys

from romance_actions import (
    INSTANT_ACTIONS, TOGGLE_ACTIONS,
    _THRUST_TOGGLE_IDS, _INSERTION_INSTANT_IDS, _INSERTION_EXP_MAP,
    ACTION_DESCRIPTIONS, MILLIS_PER_MINUTE,
)
from tone_templates import (
    ARCHETYPE_TEMPLATES, ACTION_LINE_TEMPLATES,
    CATEGORY_TEMPLATES, LINE_TEMPLATES,
)

morld = sys.modules["morld"]

# 구 키 목록 (존재하면 안 됨)
_OLD_ACTION_KEYS = {
    "vaginal_penetration", "anal_penetration",
    "rough_thrust", "genital_touch",
    "hard_anal", "receive_penetration", "receive_anal",
    "first_vaginal_penetration", "first_anal_penetration",
}

# 리네임된 신규 키 (존재해야 함)
_NEW_ARCHETYPE_KEYS = {"thrust_normal"}       # ACTION_REACTIONS → :during
_NEW_LINE_KEYS = {                            # ACTION_LINES → :start
    "vaginal_insert", "anal_insert", "thrust_rough",
    "genital_caress", "first_vaginal_insert", "first_anal_insert",
}


# ============================================
# 데이터 무결성: 구 키 부재 확인
# ============================================

class TestOldKeysAbsent:
    def test_archetype_templates_no_old_keys(self):
        """ARCHETYPE_TEMPLATES에 구 키(:during) 없음"""
        for old in _OLD_ACTION_KEYS:
            key = f"{old}:during"
            assert key not in ARCHETYPE_TEMPLATES, \
                f"ARCHETYPE_TEMPLATES still has old key: {key}"

    def test_action_line_templates_no_old_keys(self):
        """ACTION_LINE_TEMPLATES에 구 키(:start) 없음"""
        for old in _OLD_ACTION_KEYS:
            key = f"{old}:start"
            assert key not in ACTION_LINE_TEMPLATES, \
                f"ACTION_LINE_TEMPLATES still has old key: {key}"

    def test_no_old_variant_keys_in_archetype(self):
        """ARCHETYPE_TEMPLATES에 구 키 variant(:rebellion_* 등) 없음"""
        for key in ARCHETYPE_TEMPLATES:
            base = key.split(":")[0]
            assert base not in _OLD_ACTION_KEYS, \
                f"ARCHETYPE_TEMPLATES has old variant key: {key}"

    def test_no_old_variant_keys_in_action_lines(self):
        """ACTION_LINE_TEMPLATES에 구 키 variant 없음"""
        for key in ACTION_LINE_TEMPLATES:
            # key format: "action_id:start" or "action_id:variant:start"
            # after __init__.py processing, key = f"{_act}:start"
            # where _act comes from ACTION_LINES dict keys
            # So check if any old key name appears as a prefix
            for old in _OLD_ACTION_KEYS:
                assert not key.startswith(f"{old}:"), \
                    f"ACTION_LINE_TEMPLATES has old variant key: {key}"


# ============================================
# 데이터 무결성: 신규 키 존재 확인
# ============================================

class TestNewKeysPresent:
    def test_thrust_normal_in_archetype(self):
        """thrust_normal:during이 ARCHETYPE_TEMPLATES에 존재"""
        assert "thrust_normal:during" in ARCHETYPE_TEMPLATES

    def test_new_line_keys_present(self):
        """리네임된 신규 키가 ACTION_LINE_TEMPLATES에 존재"""
        for new_key in _NEW_LINE_KEYS:
            key = f"{new_key}:start"
            assert key in ACTION_LINE_TEMPLATES, \
                f"Missing new key in ACTION_LINE_TEMPLATES: {key}"

    def test_archetype_has_archetypes(self):
        """thrust_normal:during에 아키타입 데이터가 있음"""
        pool = ARCHETYPE_TEMPLATES.get("thrust_normal:during", {})
        # 최소 1개 아키타입
        assert len(pool) >= 1, "thrust_normal:during has no archetype data"

    def test_vaginal_insert_has_archetypes(self):
        """vaginal_insert:start에 아키타입 데이터가 있음"""
        pool = ACTION_LINE_TEMPLATES.get("vaginal_insert:start", {})
        assert len(pool) >= 1, "vaginal_insert:start has no archetype data"


# ============================================
# thrust_stop 정의 검증
# ============================================

class TestThrustStopDefinition:
    def test_in_instant_actions(self):
        """thrust_stop이 INSTANT_ACTIONS에 정의됨"""
        assert "thrust_stop" in INSTANT_ACTIONS

    def test_requires_active_insertion(self):
        """thrust_stop은 requires_active_insertion=True"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action.get("requires_active_insertion") is True

    def test_zero_stamina(self):
        """thrust_stop은 체력 소모 0"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action["stamina"] == 0

    def test_time_1_minute(self):
        """thrust_stop은 1분 소요"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action["time"] == 1 * MILLIS_PER_MINUTE

    def test_no_effects(self):
        """thrust_stop은 effects 비어있음"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action["effects"] == {}

    def test_in_action_descriptions(self):
        """thrust_stop이 ACTION_DESCRIPTIONS에 등록됨"""
        assert "thrust_stop" in ACTION_DESCRIPTIONS
        assert len(ACTION_DESCRIPTIONS["thrust_stop"]) > 0

    def test_no_exp_part(self):
        """thrust_stop은 exp_part=None"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action.get("exp_part") is None

    def test_affection_req_zero(self):
        """thrust_stop은 호감 요구치 0"""
        action = INSTANT_ACTIONS["thrust_stop"]
        assert action["affection_req"] == 0


# ============================================
# _THRUST_TOGGLE_IDS 검증
# ============================================

class TestThrustToggleIDs:
    def test_contains_three_thrusts(self):
        """3가지 강도의 thrust 토글 포함"""
        assert "thrust_gentle" in _THRUST_TOGGLE_IDS
        assert "thrust_normal" in _THRUST_TOGGLE_IDS
        assert "thrust_rough" in _THRUST_TOGGLE_IDS
        assert len(_THRUST_TOGGLE_IDS) == 3

    def test_all_in_toggle_actions(self):
        """모든 thrust 토글이 TOGGLE_ACTIONS에 정의됨"""
        for tid in _THRUST_TOGGLE_IDS:
            assert tid in TOGGLE_ACTIONS, \
                f"{tid} not found in TOGGLE_ACTIONS"

    def test_all_require_active_insertion(self):
        """모든 thrust 토글은 requires_active_insertion=True"""
        for tid in _THRUST_TOGGLE_IDS:
            action = TOGGLE_ACTIONS[tid]
            assert action.get("requires_active_insertion") is True, \
                f"{tid} missing requires_active_insertion"


# ============================================
# _INSERTION_INSTANT_IDS 검증
# ============================================

class TestInsertionInstantIDs:
    def test_contains_vaginal_and_anal(self):
        """vaginal_insert, anal_insert 포함"""
        assert "vaginal_insert" in _INSERTION_INSTANT_IDS
        assert "anal_insert" in _INSERTION_INSTANT_IDS

    def test_all_in_instant_actions(self):
        """모든 삽입 즉시형이 INSTANT_ACTIONS에 정의됨"""
        for aid in _INSERTION_INSTANT_IDS:
            assert aid in INSTANT_ACTIONS, \
                f"{aid} not found in INSTANT_ACTIONS"

    def test_all_are_insertion_attempts(self):
        """모든 삽입 즉시형은 is_insertion_attempt=True"""
        for aid in _INSERTION_INSTANT_IDS:
            action = INSTANT_ACTIONS[aid]
            assert action.get("is_insertion_attempt") is True


# ============================================
# 삽입 exp_part 매핑 검증
# ============================================

class TestInsertionExpMap:
    def test_vaginal_maps_to_음부(self):
        assert _INSERTION_EXP_MAP["vaginal"] == "음부"

    def test_anal_maps_to_엉덩이(self):
        assert _INSERTION_EXP_MAP["anal"] == "엉덩이"


# ============================================
# Thrust 토글 re-select 로직 (단위 테스트)
# ============================================

class TestThrustToggleReselect:
    """romance.py의 thrust 토글 재선택 로직을 모사하여 검증"""

    @staticmethod
    def _compute_is_turning_on(action_id, active_toggles):
        """romance.py의 토글 전환 로직 재현"""
        is_turning_on = action_id not in active_toggles
        # thrust 토글 재선택 시: OFF하지 않고 계속 유지
        if not is_turning_on and action_id in _THRUST_TOGGLE_IDS:
            is_turning_on = True
        return is_turning_on

    def test_new_thrust_turns_on(self):
        """비활성 thrust 선택 → ON"""
        active = set()
        assert self._compute_is_turning_on("thrust_normal", active) is True

    def test_same_thrust_stays_on(self):
        """활성 thrust 재선택 → 여전히 ON (OFF되지 않음)"""
        active = {"thrust_normal"}
        assert self._compute_is_turning_on("thrust_normal", active) is True

    def test_different_thrust_turns_on(self):
        """다른 thrust 선택 → ON"""
        active = {"thrust_normal"}
        assert self._compute_is_turning_on("thrust_rough", active) is True

    def test_non_thrust_toggle_toggles_off(self):
        """비thrust 토글 재선택 → OFF (기존 동작 유지)"""
        non_thrust = [tid for tid in TOGGLE_ACTIONS
                      if tid not in _THRUST_TOGGLE_IDS]
        if non_thrust:
            tid = non_thrust[0]
            active = {tid}
            assert self._compute_is_turning_on(tid, active) is False

    def test_non_thrust_toggle_new_turns_on(self):
        """비thrust 비활성 토글 선택 → ON"""
        non_thrust = [tid for tid in TOGGLE_ACTIONS
                      if tid not in _THRUST_TOGGLE_IDS]
        if non_thrust:
            tid = non_thrust[0]
            active = set()
            assert self._compute_is_turning_on(tid, active) is True


# ============================================
# thrust_stop 처리 로직 (단위 테스트)
# ============================================

class TestThrustStopLogic:
    """romance.py의 thrust_stop 처리 로직을 모사하여 검증"""

    @staticmethod
    def _apply_thrust_stop(active_toggles):
        """thrust_stop: 허리흔들기 토글 전부 해제"""
        for tid in list(active_toggles):
            if tid in _THRUST_TOGGLE_IDS:
                active_toggles.discard(tid)

    def test_clears_single_thrust(self):
        """thrust 1개 활성 → 전부 해제"""
        toggles = {"thrust_normal", "deep_kiss"}
        self._apply_thrust_stop(toggles)
        assert "thrust_normal" not in toggles
        assert "deep_kiss" in toggles  # 비thrust는 유지

    def test_clears_all_thrusts(self):
        """thrust 여러 개 활성 → 전부 해제"""
        toggles = {"thrust_normal", "thrust_rough"}
        self._apply_thrust_stop(toggles)
        assert len(toggles & _THRUST_TOGGLE_IDS) == 0

    def test_preserves_non_thrust_toggles(self):
        """비thrust 토글은 유지"""
        non_thrust = [tid for tid in TOGGLE_ACTIONS
                      if tid not in _THRUST_TOGGLE_IDS]
        if non_thrust:
            toggles = {"thrust_normal", non_thrust[0]}
            self._apply_thrust_stop(toggles)
            assert non_thrust[0] in toggles

    def test_no_thrust_active_noop(self):
        """thrust 없으면 아무것도 안 함"""
        non_thrust = [tid for tid in TOGGLE_ACTIONS
                      if tid not in _THRUST_TOGGLE_IDS]
        if len(non_thrust) >= 2:
            toggles = {non_thrust[0], non_thrust[1]}
            original = set(toggles)
            self._apply_thrust_stop(toggles)
            assert toggles == original


# ============================================
# thrust_stop UI 필터 로직 (단위 테스트)
# ============================================

class TestThrustStopUIFilter:
    """romance_ui.py의 thrust_stop 표시 조건을 모사하여 검증"""

    @staticmethod
    def _should_show_thrust_stop(active_toggles, insertion_active):
        """thrust_stop 표시 조건:
        1. requires_active_insertion → insertion_active
        2. thrust 활성일 때만 표시
        """
        if not insertion_active:
            return False
        if not any(t in _THRUST_TOGGLE_IDS for t in active_toggles):
            return False
        return True

    def test_show_when_thrust_active(self):
        """삽입 중 + thrust 활성 → 표시"""
        assert self._should_show_thrust_stop({"thrust_normal"}, True)

    def test_hide_when_no_thrust(self):
        """삽입 중이지만 thrust 비활성 → 숨김"""
        assert not self._should_show_thrust_stop(set(), True)

    def test_hide_when_no_insertion(self):
        """삽입 미상태 → 숨김"""
        assert not self._should_show_thrust_stop({"thrust_normal"}, False)

    def test_hide_when_non_thrust_only(self):
        """비thrust 토글만 활성 → 숨김"""
        non_thrust = [tid for tid in TOGGLE_ACTIONS
                      if tid not in _THRUST_TOGGLE_IDS]
        if non_thrust:
            assert not self._should_show_thrust_stop({non_thrust[0]}, True)

    def test_show_with_any_thrust_variant(self):
        """어떤 thrust든 활성이면 표시"""
        for tid in _THRUST_TOGGLE_IDS:
            assert self._should_show_thrust_stop({tid}, True), \
                f"thrust_stop should show when {tid} is active"


# ============================================
# Alias 코드 제거 확인
# ============================================

class TestAliasRemoved:
    def test_no_action_aliases_in_templates(self):
        """tone_templates/__init__.py에 _ACTION_ALIASES 없음"""
        import tone_templates
        assert not hasattr(tone_templates, '_ACTION_ALIASES'), \
            "tone_templates still has _ACTION_ALIASES"

    def test_generator_no_alias_dicts(self):
        """generator 모듈에 alias dict 없음"""
        import romance_reaction_generator as rrg
        import romance_line_generator as rlg
        assert not hasattr(rrg, '_CHAR_REACTION_ALIASES'), \
            "romance_reaction_generator still has _CHAR_REACTION_ALIASES"
        assert not hasattr(rlg, '_CHAR_LINE_ALIASES'), \
            "romance_line_generator still has _CHAR_LINE_ALIASES"
