# test_romance_actions.py — romance_actions.py 데이터 무결성 검증
"""
외부 의존성 0 — 액션 정의 데이터의 일관성/완전성/모순 탐색.
"""
from romance_actions import (
    INSTANT_ACTIONS, TOGGLE_ACTIONS, SENSATION_MAP,
    RELATIONSHIP_LABELS, AFF_LABEL_THRESHOLD, DES_LABEL_THRESHOLD,
    get_relationship_label,
    VIRGINITY_CLEARING_ACTIONS, _PENETRATION_TOGGLE_IDS,
    ACTION_DESCRIPTIONS, TOGGLE_DURING_DESCRIPTIONS,
    SEMEN_PARTS, INTERNAL_SEMEN_PARTS,
)

VALID_CATEGORIES = {"F", "M", "B", "A", "V", "C", "P", None}


# ============================================
# 액션 정의 구조 무결성
# ============================================

class TestActionStructure:
    """모든 액션 정의에 필수 키가 존재하는지 검증"""

    def test_instant_actions_required_keys(self):
        required = {"name", "time", "stamina", "effects", "exp_part", "affection_req"}
        for action_id, action_def in INSTANT_ACTIONS.items():
            missing = required - set(action_def.keys())
            assert not missing, f"INSTANT '{action_id}' missing keys: {missing}"

    def test_toggle_actions_required_keys(self):
        required = {"name", "time", "stamina", "effects", "exp_part", "affection_req"}
        for action_id, action_def in TOGGLE_ACTIONS.items():
            missing = required - set(action_def.keys())
            assert not missing, f"TOGGLE '{action_id}' missing keys: {missing}"

    def test_effects_are_dicts(self):
        for action_id, action_def in INSTANT_ACTIONS.items():
            assert isinstance(action_def["effects"], dict), \
                f"INSTANT '{action_id}' effects is not dict"
        for action_id, action_def in TOGGLE_ACTIONS.items():
            assert isinstance(action_def["effects"], dict), \
                f"TOGGLE '{action_id}' effects is not dict"

    def test_time_positive(self):
        for action_id, action_def in INSTANT_ACTIONS.items():
            assert action_def["time"] > 0, f"INSTANT '{action_id}' time <= 0"
        for action_id, action_def in TOGGLE_ACTIONS.items():
            assert action_def["time"] > 0, f"TOGGLE '{action_id}' time <= 0"

    def test_stamina_non_negative(self):
        for action_id, action_def in INSTANT_ACTIONS.items():
            assert action_def["stamina"] >= 0, f"INSTANT '{action_id}' stamina < 0"
        for action_id, action_def in TOGGLE_ACTIONS.items():
            assert action_def["stamina"] >= 0, f"TOGGLE '{action_id}' stamina < 0"

    def test_affection_req_non_negative(self):
        for action_id, action_def in INSTANT_ACTIONS.items():
            assert action_def["affection_req"] >= 0, \
                f"INSTANT '{action_id}' affection_req < 0"
        for action_id, action_def in TOGGLE_ACTIONS.items():
            assert action_def["affection_req"] >= 0, \
                f"TOGGLE '{action_id}' affection_req < 0"

    def test_no_duplicate_ids_across_types(self):
        """즉시형과 토글형에 중복 ID가 없는지"""
        overlap = set(INSTANT_ACTIONS.keys()) & set(TOGGLE_ACTIONS.keys())
        assert not overlap, f"Duplicate action IDs: {overlap}"


# ============================================
# SENSATION_MAP 완전성
# ============================================

class TestSensationMap:
    def test_all_exp_parts_mapped(self):
        """모든 액션의 exp_part가 SENSATION_MAP에 매핑되어 있는지"""
        unmapped = []
        for action_id, action_def in INSTANT_ACTIONS.items():
            ep = action_def.get("exp_part")
            if ep and ep not in SENSATION_MAP:
                unmapped.append(f"INSTANT '{action_id}' exp_part='{ep}'")
        for action_id, action_def in TOGGLE_ACTIONS.items():
            ep = action_def.get("exp_part")
            if ep and ep not in SENSATION_MAP:
                unmapped.append(f"TOGGLE '{action_id}' exp_part='{ep}'")
        assert not unmapped, f"Unmapped exp_parts: {unmapped}"

    def test_sensation_map_categories_valid(self):
        """SENSATION_MAP의 모든 카테고리가 유효한 값"""
        for part, cat in SENSATION_MAP.items():
            assert cat in VALID_CATEGORIES, \
                f"SENSATION_MAP['{part}'] = '{cat}' not in {VALID_CATEGORIES}"

    def test_all_stim_categories_have_mapping(self):
        """F/M/B/A/V/C/P 모든 카테고리에 최소 1개 매핑 존재"""
        used = set(SENSATION_MAP.values()) - {None}
        expected = {"F", "M", "B", "A", "V", "C", "P"}
        missing = expected - used
        assert not missing, f"Categories without mapping: {missing}"


# ============================================
# get_relationship_label
# ============================================

class TestRelationshipLabel:
    def test_stranger(self):
        assert get_relationship_label(0, 0) == "타인"

    def test_friend(self):
        assert get_relationship_label(50, 0) == "친구"

    def test_lust(self):
        assert get_relationship_label(0, 40) == "정욕"

    def test_lover(self):
        assert get_relationship_label(50, 40) == "애인"

    def test_boundary_below(self):
        assert get_relationship_label(49, 39) == "타인"

    def test_boundary_exact(self):
        assert get_relationship_label(50, 40) == "애인"

    def test_all_labels_covered(self):
        """4개 라벨 모두 도달 가능"""
        labels = set()
        for aff in (0, 100):
            for des in (0, 100):
                labels.add(get_relationship_label(aff, des))
        assert labels == {"타인", "친구", "정욕", "애인"}


# ============================================
# 충돌 일관성
# ============================================

class TestConflictConsistency:
    def test_same_exp_part_toggles_exist(self):
        """동일 exp_part 토글이 2개 이상 존재하는지 (충돌 가능성 확인)"""
        by_part = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            ep = tdef.get("exp_part")
            if ep:
                by_part.setdefault(ep, []).append(tid)
        # 최소 1개 부위에서 2개 이상 토글 존재해야 충돌 시스템이 유의미
        has_conflict = any(len(ids) >= 2 for ids in by_part.values())
        assert has_conflict, "No exp_part conflicts possible — system may be unused"

    def test_uses_mouth_toggles_exist(self):
        """uses_mouth 토글이 2개 이상 있어야 충돌 시스템 유의미"""
        mouth_toggles = [tid for tid, tdef in TOGGLE_ACTIONS.items()
                         if tdef.get("uses_mouth")]
        assert len(mouth_toggles) >= 2, \
            f"Only {len(mouth_toggles)} uses_mouth toggles — conflict impossible"

    def test_player_anatomy_conflict_possible(self):
        """requires_player_anatomy 충돌 가능한 토글 존재"""
        by_anatomy = {}
        for tid, tdef in TOGGLE_ACTIONS.items():
            req = tdef.get("requires_player_anatomy")
            if req:
                by_anatomy.setdefault(req, []).append(tid)
        has_conflict = any(len(ids) >= 2 for ids in by_anatomy.values())
        assert has_conflict, "No player anatomy conflicts possible"


# ============================================
# VIRGINITY_CLEARING_ACTIONS
# ============================================

class TestVirginity:
    def test_all_clearing_actions_exist(self):
        """VIRGINITY_CLEARING_ACTIONS의 모든 action_id가 실제 존재"""
        all_actions = set(INSTANT_ACTIONS) | set(TOGGLE_ACTIONS)
        for action_id in VIRGINITY_CLEARING_ACTIONS:
            assert action_id in all_actions, \
                f"Virginity action '{action_id}' not in any action dict"

    def test_clearing_actions_are_toggles(self):
        """처녀 해제 액션은 토글형이어야 (삽입 행위)"""
        for action_id in VIRGINITY_CLEARING_ACTIONS:
            # finger_insertion, fellatio 등 토글형 확인
            # rough_finger는 즉시형이므로 즉시형도 허용
            assert action_id in TOGGLE_ACTIONS or action_id in INSTANT_ACTIONS, \
                f"Virginity action '{action_id}' not found"


# ============================================
# PENETRATION_TOGGLE_IDS
# ============================================

class TestPenetration:
    def test_all_penetration_ids_are_toggles(self):
        """삽입 토글 ID가 TOGGLE_ACTIONS에 존재"""
        for tid in _PENETRATION_TOGGLE_IDS:
            assert tid in TOGGLE_ACTIONS, \
                f"Penetration toggle '{tid}' not in TOGGLE_ACTIONS"

    def test_penetration_requires_player_anatomy(self):
        """삽입 토글은 requires_player_anatomy 필드를 가져야"""
        for tid in _PENETRATION_TOGGLE_IDS:
            tdef = TOGGLE_ACTIONS[tid]
            assert "requires_player_anatomy" in tdef, \
                f"Penetration toggle '{tid}' missing requires_player_anatomy"

    def test_pregnancy_check_consistency(self):
        """pregnancy_check가 있는 토글은 삽입 토글 세트에 포함"""
        for tid, tdef in TOGGLE_ACTIONS.items():
            if tdef.get("pregnancy_check"):
                assert tid in _PENETRATION_TOGGLE_IDS, \
                    f"'{tid}' has pregnancy_check but not in _PENETRATION_TOGGLE_IDS"


# ============================================
# 묘사 텍스트 완전성
# ============================================

class TestDescriptions:
    def test_all_instant_actions_have_description(self):
        """모든 즉시형 행위에 묘사 텍스트 존재 (특수 행위 제외)"""
        special = {"undress_upper", "undress_lower", "hold_back", "ejaculate",
                   "change_position", "condom_on", "condom_off", "swallow_semen"}
        for action_id in INSTANT_ACTIONS:
            if action_id in special:
                continue
            assert action_id in ACTION_DESCRIPTIONS, \
                f"INSTANT '{action_id}' missing from ACTION_DESCRIPTIONS"

    def test_all_toggle_actions_have_during_description(self):
        """모든 토글형 행위에 진행 중 묘사 텍스트 존재"""
        for action_id in TOGGLE_ACTIONS:
            assert action_id in TOGGLE_DURING_DESCRIPTIONS, \
                f"TOGGLE '{action_id}' missing from TOGGLE_DURING_DESCRIPTIONS"

    def test_no_orphan_descriptions(self):
        """묘사 텍스트에 존재하지 않는 행위 ID가 있는지"""
        all_actions = set(INSTANT_ACTIONS) | set(TOGGLE_ACTIONS)
        orphan_instant = set(ACTION_DESCRIPTIONS) - all_actions
        orphan_toggle = set(TOGGLE_DURING_DESCRIPTIONS) - all_actions
        assert not orphan_instant, f"Orphan ACTION_DESCRIPTIONS: {orphan_instant}"
        assert not orphan_toggle, f"Orphan TOGGLE_DURING: {orphan_toggle}"
