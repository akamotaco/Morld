# test_mob_character.py — Character(base) 단독 인스턴스 (mob NPC) 테스트
"""
Character 클래스를 서브클래스 없이 단독 생성했을 때
모든 상호작용이 에러 없이 동작하는지 검증.

핵심: "모브만 가지고 게임 내에 생성하였을 때,
상호작용의 내용은 다르더라도 에러가 발생해서는 안 됨"
"""
import sys
import types

# mock_morld 접근 (run_tests.py가 주입)
morld = sys.modules["morld"]

# ============================================
# stub 모듈 주입 (Character import 전에 필요)
# ============================================

# quest stub — mark_first_meet_done()에서 lazy import
_quest_stub = types.ModuleType("quest")


class _StubQuestManager:
    def check_meet_conditions(self, *a):
        pass


_quest_stub.quest_manager = _StubQuestManager()
sys.modules.setdefault("quest", _quest_stub)

# date stub — _build_context()에서 lazy import
_date_stub = types.ModuleType("date")
_date_stub.is_on_date = lambda pid: False
_date_stub.get_date_partner = lambda pid: None
sys.modules.setdefault("date", _date_stub)

# romance stub — on_meet_player()에서 lazy import
_romance_stub = types.ModuleType("romance")
_romance_stub.get_interrupted_context = lambda: None
sys.modules.setdefault("romance", _romance_stub)

# npc_initiative stub — on_meet_player()에서 lazy import
_npc_init_stub = types.ModuleType("npc_initiative")
_npc_init_stub.start_npc_initiative = lambda pid, nid: None
sys.modules.setdefault("npc_initiative", _npc_init_stub)

# sound stub — instantiate()에서 lazy import
_sound_stub = types.ModuleType("sound")
_sound_stub.register_hearing = lambda uid, ht: None
sys.modules.setdefault("sound", _sound_stub)

# survival stub — should_initiate_skinship()에서 lazy import
_survival_stub = types.ModuleType("survival")
_survival_stub.get_survival_stats = lambda uid: {"체력": 100, "최대체력": 100}
_survival_stub.is_npc_fainted = lambda uid: False
_survival_stub.is_npc_exhausted = lambda uid: False
_survival_stub.is_npc_sleeping = lambda uid: False
sys.modules.setdefault("survival", _survival_stub)

# think stub — date.py에서 import
_think_stub = types.ModuleType("think")
_think_stub.get_agent = lambda uid: None
sys.modules.setdefault("think", _think_stub)

# pregnancy stub — on_meet_player()에서 lazy import
_pregnancy_stub = types.ModuleType("pregnancy")
_pregnancy_stub.is_pregnant = lambda uid: False
_pregnancy_stub.check_pending_pregnancy_events = lambda uid: None
sys.modules.setdefault("pregnancy", _pregnancy_stub)

# equipment stub — _calculate_exposure()에서 lazy import
_equipment = sys.modules.get("equipment") or types.ModuleType("equipment")
_equipment.get_equipped_items = lambda uid: [9901, 9902]  # 기본 착의
_equipment.equip_item = lambda uid, iid: True
_equipment.unequip_item = lambda uid, iid: True
sys.modules.setdefault("equipment", _equipment)

# restraint stub — _build_context()에서 lazy import
_restraint = sys.modules.get("restraint") or types.ModuleType("restraint")
_restraint.is_restrained = lambda uid: False
_restraint.is_upper_restrained = lambda uid: False
_restraint.is_lower_restrained = lambda uid: False
_restraint.is_gagged = lambda uid: False
_restraint.is_blindfolded = lambda uid: False
_restraint.get_restrained_units_at = lambda rid, loc: []
_restraint.release = lambda uid: None
sys.modules.setdefault("restraint", _restraint)

# carry stub — _build_context() + think/__init__에서 lazy import
_carry_stub = sys.modules.get("carry") or types.ModuleType("carry")
_carry_stub.is_being_carried = lambda uid: False
_carry_stub.get_carrier = lambda uid: None
_carry_stub.is_carrying = lambda uid: False
_carry_stub.get_carried_unit = lambda uid: None
_carry_stub.get_carry_method = lambda uid: None
sys.modules.setdefault("carry", _carry_stub)

# now import Character
from assets.base import Character, build_describe_rules, build_focus_rules


# ============================================
# 테스트 헬퍼
# ============================================

def _create_mob(name="모브", unit_id=100, player_id=1):
    """테스트용 mob Character 생성 (instantiate 우회)"""
    mob = Character()
    mob.name = name
    mob.unique_id = f"mob_{unit_id}"
    mob.instance_id = unit_id
    mob._instantiated = True
    mob.region_id = 0
    mob.location_id = 0

    # mock_morld에 유닛 등록
    morld.register_unit(unit_id, name=name, location=(0, 0), gender="female")
    morld.register_unit(player_id, name="주인공", location=(0, 0), gender="male")
    morld.register_location(0, 0, is_indoor=True)

    # 기본 의류 등록 (노출도=0 → exposure 규칙 방지)
    morld.register_item(9901, "기본상의",
                        equip_props={"착용:상의": 1, "착용:속옷상의": 1})
    morld.register_item(9902, "기본하의",
                        equip_props={"착용:하의": 1, "착용:속옷하의": 1})

    return mob


# ============================================
# 클래스 속성 기본값 검증
# ============================================

class TestClassAttributes:
    def test_default_archetype(self):
        """_DEFAULT_ARCHETYPE이 stoic"""
        assert Character._DEFAULT_ARCHETYPE == "stoic"

    def test_romance_sound_profile(self):
        """ROMANCE_SOUND_PROFILE 기본값 존재"""
        profile = Character.ROMANCE_SOUND_PROFILE
        assert isinstance(profile, dict)
        assert "levels" in profile
        assert "ecstasy" in profile
        assert len(profile["levels"]) == 3

    def test_romance_reactions_defaults(self):
        """ROMANCE_REACTIONS에 모든 기본 키 존재"""
        reactions = Character.ROMANCE_REACTIONS
        assert isinstance(reactions, dict)
        # 토글 during 키 확인
        assert "hug:during" in reactions
        assert "deep_kiss:during" in reactions
        # 즉시 start 키 확인
        assert "head_pat:start" in reactions
        assert "french_kiss:start" in reactions
        # 삽입 키 확인
        assert "vaginal_insert:start" in reactions
        assert "thrust_normal:during" in reactions
        # 절정 키 확인
        assert "ecstasy:start" in reactions

    def test_romance_reactions_all_have_defaults(self):
        """ROMANCE_REACTIONS 모든 값이 비어있지 않음"""
        for key, rules in Character.ROMANCE_REACTIONS.items():
            assert isinstance(rules, list), f"{key}: not list"
            assert len(rules) > 0, f"{key}: empty"

    def test_describe_rules_none(self):
        """DESCRIBE_RULES는 None (lazy fallback)"""
        assert Character.DESCRIBE_RULES is None

    def test_focus_rules_none(self):
        """FOCUS_RULES는 None (lazy fallback)"""
        assert Character.FOCUS_RULES is None

    def test_talk_rules_none(self):
        """TALK_RULES는 None (fallback 대화)"""
        assert Character.TALK_RULES is None

    def test_initiative_config_none(self):
        """INITIATIVE_CONFIG None → should_initiate_skinship False"""
        assert not hasattr(Character, 'INITIATIVE_CONFIG') or \
               Character.INITIATIVE_CONFIG is None

    def test_gift_preferences_default(self):
        """GIFT_PREFERENCES 기본값 존재"""
        prefs = Character.GIFT_PREFERENCES
        assert isinstance(prefs, dict)
        assert "liked_categories" in prefs
        assert "favorite_items" in prefs


# ============================================
# mob 인스턴스 생성
# ============================================

class TestMobCreation:
    def test_create_instance(self):
        """Character 직접 생성 — 에러 없음"""
        mob = _create_mob()
        assert mob.instance_id == 100
        assert mob.name == "모브"

    def test_has_first_meet_handler(self):
        """_first_meet_handler 메서드 존재"""
        mob = _create_mob()
        assert hasattr(mob, '_first_meet_handler')
        assert callable(mob._first_meet_handler)


# ============================================
# _first_meet_handler (크래시 수정 검증)
# ============================================

class TestFirstMeetHandler:
    def test_returns_generator(self):
        """_first_meet_handler가 generator 반환"""
        mob = _create_mob()
        result = mob._first_meet_handler(1)
        # generator인지 확인
        assert hasattr(result, '__next__')

    def test_no_crash(self):
        """_first_meet_handler 실행 시 크래시 없음"""
        mob = _create_mob()
        gen = mob._first_meet_handler(1)
        # generator를 소진
        results = list(gen)
        assert len(results) >= 1  # 최소 1개 yield (dialog)

    def test_sets_progress(self):
        """_first_meet_handler 후 진척도 설정"""
        mob = _create_mob()
        gen = mob._first_meet_handler(1)
        list(gen)  # 소진
        # player_id=1의 "관계:모브:진척도" prop이 1로 설정되었는지
        progress = morld.get_unit_prop(1, "관계:모브:진척도")
        assert progress == 1


# ============================================
# get_describe_text lazy fallback
# ============================================

class TestDescribeText:
    def test_lazy_fallback_not_empty(self):
        """DESCRIBE_RULES=None이어도 기본 텍스트 반환"""
        mob = _create_mob()
        text = mob.get_describe_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_lazy_fallback_contains_name(self):
        """기본 describe 텍스트에 NPC 이름 포함"""
        mob = _create_mob(name="테스트NPC")
        text = mob.get_describe_text()
        assert "테스트NPC" in text

    def test_lazy_rules_cached(self):
        """기본 describe 규칙이 캐싱됨"""
        mob = _create_mob()
        mob.get_describe_text()
        assert hasattr(mob, '_default_describe_rules')
        rules1 = mob._default_describe_rules
        mob.get_describe_text()
        rules2 = mob._default_describe_rules
        assert rules1 is rules2  # 같은 객체

    def test_semen_describe(self):
        """정액 오염 시 정액 관련 묘사 출력"""
        mob = _create_mob()
        morld.set_unit_prop(100, "오염물:정액:얼굴", 25)
        text = mob.get_describe_text()
        assert "정액" in text

    def test_explicit_rules_override(self):
        """DESCRIBE_RULES가 있으면 lazy fallback 미사용"""
        mob = _create_mob()
        mob.DESCRIBE_RULES = [({}, "명시적 규칙 텍스트")]
        text = mob.get_describe_text()
        assert text == "명시적 규칙 텍스트"
        assert not hasattr(mob, '_default_describe_rules')


# ============================================
# get_focus_text lazy fallback
# ============================================

class TestFocusText:
    def test_lazy_fallback_not_empty(self):
        """FOCUS_RULES=None이어도 기본 텍스트 반환"""
        mob = _create_mob()
        text = mob.get_focus_text()
        assert isinstance(text, str)
        assert len(text) > 0

    def test_lazy_fallback_contains_name(self):
        """기본 focus 텍스트에 NPC 이름 포함"""
        mob = _create_mob(name="포커스NPC")
        text = mob.get_focus_text()
        assert "포커스NPC" in text

    def test_lazy_rules_cached(self):
        """기본 focus 규칙이 캐싱됨"""
        mob = _create_mob()
        mob.get_focus_text()
        assert hasattr(mob, '_default_focus_rules')
        rules1 = mob._default_focus_rules
        mob.get_focus_text()
        rules2 = mob._default_focus_rules
        assert rules1 is rules2

    def test_explicit_rules_override(self):
        """FOCUS_RULES가 있으면 lazy fallback 미사용"""
        mob = _create_mob()
        mob.FOCUS_RULES = [({}, "명시적 포커스")]
        text = mob.get_focus_text()
        assert text == "명시적 포커스"
        assert not hasattr(mob, '_default_focus_rules')


# ============================================
# talk() fallback
# ============================================

class TestTalk:
    def test_talk_no_rules_returns_generator(self):
        """TALK_RULES=None일 때 talk()이 generator 반환"""
        mob = _create_mob()
        gen = mob.talk()
        assert hasattr(gen, '__next__')

    def test_talk_no_rules_no_crash(self):
        """TALK_RULES=None일 때 에러 없이 대화"""
        mob = _create_mob()
        gen = mob.talk()
        results = list(gen)
        assert len(results) >= 1


# ============================================
# should_initiate_skinship
# ============================================

class TestInitiativeSkinship:
    def test_no_config_returns_false(self):
        """INITIATIVE_CONFIG=None → False"""
        mob = _create_mob()
        assert mob.should_initiate_skinship(1) is False


# ============================================
# get_romance_reaction
# ============================================

class TestRomanceReaction:
    def test_hug_during(self):
        """hug:during 반응 텍스트 반환"""
        mob = _create_mob()
        text = mob.get_romance_reaction("hug", "during")
        assert text is not None
        assert isinstance(text, str)
        assert len(text) > 0

    def test_head_pat_start(self):
        """head_pat:start 반응 텍스트 반환"""
        mob = _create_mob()
        text = mob.get_romance_reaction("head_pat", "start")
        assert text is not None

    def test_ecstasy(self):
        """ecstasy:start 반응 텍스트 반환"""
        mob = _create_mob()
        text = mob.get_romance_reaction("ecstasy", "start")
        assert text is not None

    def test_unknown_action(self):
        """정의되지 않은 액션 → None (크래시 아님)"""
        mob = _create_mob()
        text = mob.get_romance_reaction("nonexistent_action", "start")
        # None 또는 빈 문자열이어야 에러 없음
        assert text is None or text == ""

    def test_penetration_reactions(self):
        """삽입 행위 반응 모두 존재"""
        mob = _create_mob()
        # 즉시형 삽입 → :start, 토글형 허리흔들기 → :during
        penetration_checks = [
            ("vaginal_insert", "start"),
            ("anal_insert", "start"),
            ("thrust_gentle", "during"),
            ("thrust_normal", "during"),
            ("thrust_rough", "during"),
        ]
        for action, timing in penetration_checks:
            text = mob.get_romance_reaction(action, timing)
            assert text is not None, \
                f"Missing reaction: {action}:{timing}"


# ============================================
# is_first_meet / mark_first_meet_done
# ============================================

class TestFirstMeet:
    def test_is_first_meet_true_initially(self):
        """진척도 없으면 첫 만남"""
        mob = _create_mob()
        assert mob.is_first_meet(1) is True

    def test_is_first_meet_false_after_mark(self):
        """mark_first_meet_done 후 첫 만남 아님"""
        mob = _create_mob()
        mob.mark_first_meet_done(1)
        assert mob.is_first_meet(1) is False

    def test_mark_sets_progress_key(self):
        """mark_first_meet_done이 올바른 prop 키 설정"""
        mob = _create_mob(name="테스트")
        mob.mark_first_meet_done(1)
        val = morld.get_unit_prop(1, "관계:테스트:진척도")
        assert val == 1


# ============================================
# on_meet_player (통합)
# ============================================

class TestOnMeetPlayer:
    def test_first_meet_no_crash(self):
        """첫 만남 시 on_meet_player 크래시 없음"""
        mob = _create_mob()
        result = mob.on_meet_player(1)
        # generator 반환 (첫 만남 핸들러)
        assert result is not None
        assert hasattr(result, '__next__')
        # 소진
        list(result)

    def test_subsequent_meet_returns_none(self):
        """두 번째 만남 시 None 반환 (이벤트 없음)"""
        mob = _create_mob()
        # 첫 만남 처리
        gen = mob.on_meet_player(1)
        list(gen)
        # 두 번째 만남
        result = mob.on_meet_player(1)
        assert result is None


# ============================================
# 데이트 관련 메서드 fallback
# ============================================

class TestDateFallbacks:
    def test_get_date_accept_text(self):
        """get_date_accept_text fallback"""
        mob = _create_mob()
        if hasattr(mob, 'get_date_accept_text'):
            text = mob.get_date_accept_text()
            assert isinstance(text, str)

    def test_get_date_reject_text(self):
        """get_date_reject_text fallback"""
        mob = _create_mob()
        if hasattr(mob, 'get_date_reject_text'):
            text = mob.get_date_reject_text("low_affection")
            assert isinstance(text, str)


# ============================================
# build_describe_rules / build_focus_rules 빌더
# ============================================

class TestBuilders:
    def test_build_describe_rules_stoic(self):
        """stoic 아키타입 describe rules 생성"""
        rules = build_describe_rules("stoic", default_text="서 있다.")
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_build_focus_rules_stoic(self):
        """stoic 아키타입 focus rules 생성"""
        rules = build_focus_rules("stoic", activities=[], default_text="바라본다.")
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_all_archetypes_have_rules(self):
        """5개 아키타입 모두 describe/focus rules 생성 가능"""
        archetypes = ["stoic", "gentle", "cheerful", "timid", "cold"]
        for arch in archetypes:
            desc = build_describe_rules(arch, default_text="test")
            focus = build_focus_rules(arch, activities=[], default_text="test")
            assert isinstance(desc, list), f"{arch} describe failed"
            assert isinstance(focus, list), f"{arch} focus failed"
            assert len(desc) > 0, f"{arch} describe empty"
            assert len(focus) > 0, f"{arch} focus empty"


# ============================================
# ROMANCE_SOUND_PROFILE getattr 안전성
# ============================================

class TestSoundProfile:
    def test_getattr_access(self):
        """getattr로 접근 시 기본값 반환"""
        mob = _create_mob()
        profile = getattr(mob, 'ROMANCE_SOUND_PROFILE', None)
        assert profile is not None
        assert isinstance(profile["levels"], list)
        assert isinstance(profile["ecstasy"], int)

    def test_subclass_can_override(self):
        """서브클래스에서 오버라이드 가능"""
        class CustomNPC(Character):
            ROMANCE_SOUND_PROFILE = {"levels": [10, 20, 30], "ecstasy": 70}

        npc = CustomNPC()
        assert npc.ROMANCE_SOUND_PROFILE["ecstasy"] == 70


# ============================================
# 기타 안전성 테스트
# ============================================

class TestMiscSafety:
    def test_stealth_reactions_none_safe(self):
        """STEALTH_REACTIONS None → get_stealth_success_reaction 안전"""
        mob = _create_mob()
        result = mob.get_stealth_success_reaction(1)
        assert result is None

    def test_gift_preferences_default(self):
        """GIFT_PREFERENCES 기본값으로 선물 시스템 동작"""
        mob = _create_mob()
        prefs = mob.GIFT_PREFERENCES
        assert prefs["liked_categories"] == []
        assert prefs["favorite_items"] == []

    def test_romance_discovery_reactions_none(self):
        """ROMANCE_DISCOVERY_REACTIONS None → 안전"""
        mob = _create_mob()
        assert mob.ROMANCE_DISCOVERY_REACTIONS is None

    def test_sexual_orientation_default(self):
        """sexual_orientation 기본값"""
        mob = _create_mob()
        assert mob.sexual_orientation == "bisexual"

    def test_hearing_type_default(self):
        """hearing_type 기본값"""
        mob = _create_mob()
        assert mob.hearing_type == "normal"

    def test_requires_condom_default(self):
        """requires_condom 기본값 False"""
        mob = _create_mob()
        assert mob.requires_condom is False

    def test_reaction_profile_default(self):
        """REACTION_PROFILE 기본값 None"""
        mob = _create_mob()
        assert mob.REACTION_PROFILE is None

    def test_sexual_preferences_default(self):
        """SEXUAL_PREFERENCES 기본값 None"""
        mob = _create_mob()
        assert mob.SEXUAL_PREFERENCES is None

    def test_equip_change_reactions_default(self):
        """EQUIP_CHANGE_REACTIONS 기본값 None"""
        mob = _create_mob()
        assert mob.EQUIP_CHANGE_REACTIONS is None


# ============================================
# on_bed_awake / on_bed_sleeping 기본 구현
# ============================================

class TestBedReactions:
    def test_on_bed_awake_high_affection(self):
        """깨어있을 때 높은 호감도 반응"""
        mob = _create_mob()
        morld.register_unit(1, "Player")

        class FakeBed:
            instance_id = 999
        bed = FakeBed()
        gen = mob.on_bed_awake(bed, 1, 0, 60, 0, mob.instance_id)
        results = list(gen)
        assert len(results) > 0

    def test_on_bed_awake_low_affection(self):
        """깨어있을 때 낮은 호감도 반응"""
        mob = _create_mob()
        morld.register_unit(1, "Player")

        class FakeBed:
            instance_id = 999
        bed = FakeBed()
        gen = mob.on_bed_awake(bed, 1, 0, 20, 0, mob.instance_id)
        results = list(gen)
        assert len(results) > 0

    def test_on_bed_sleeping(self):
        """잠자고 있을 때 기본 반응"""
        mob = _create_mob()
        morld.register_unit(1, "Player")

        class FakeBed:
            instance_id = 999
        bed = FakeBed()
        gen = mob.on_bed_sleeping(bed, 1, 0, 50, mob.instance_id)
        results = list(gen)
        assert len(results) > 0

    def test_subclass_override(self):
        """서브클래스에서 on_bed_awake 오버라이드 가능"""
        class CustomNPC(Character):
            def on_bed_awake(self, bed, player_id, slot, affection, region_id, owner_id):
                yield "custom_awake"

        npc = CustomNPC()
        results = list(npc.on_bed_awake(None, 1, 0, 50, 0, 0))
        assert results == ["custom_awake"]
