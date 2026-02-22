# assets/characters/monster.py — 생물(Creature) 캐릭터 Asset
#
# Monster(Character) 기본 클래스 + 구체 서브클래스
# - type = "creature" → C# UnitType.Creature
# - 전투:세력 — 세력(faction) 기반 적대 판별
# - DROP_TABLE: 스폰 시 인벤토리에 아이템 생성 (사망 후 루팅)
# - HARVEST_TABLE: 시체에서 도구로 수확하는 소재 (props 기반)
# - BATTLE_BEHAVIOR: think Tier 3 전투 AI 파라미터
# - SCHEDULE: 종별 라이프사이클 (순찰/휴식/수면/복귀)

import morld
from assets.base import Character
from assets.registry import register_item


class Monster(Character):
    """생물 기본 클래스 — Character 서브클래스"""
    type = "creature"
    owner = None

    props = {
        "전투:세력": "야생",
        "생존:체력": 30,
        "생존:최대체력": 30,
        "전투:공격력": 5,
        "전투:방어력": 2,
        "전투:명중": 70,
        "전투:회피": 10,
        "전투:치명타": 3,
        "전투:사거리": 60,
        "전투:공격속도": 1.0,
        "전투:감지거리": 100,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 60,
        "retreat_threshold": 0.2,
    }

    # 포커스 시 공격 + 교미 (수간 모드 ON 시 교미 표시)
    actions = ["call:attack:공격#", "call:mate:교미#"]

    # 성별 분포: [(gender_str, weight), ...] 또는 None (무성 고정)
    GENDER_DISTRIBUTION = None

    # 인벤토리 드롭 테이블
    # 형식: [{"item": "unique_id", "chance": 0.0~1.0, "count": int or (min,max)}]
    DROP_TABLE = []

    # 소재 수확 테이블 (시체에서 도구로 수확)
    # 형식: {"소재:키": {"item": "unique_id", "name": "표시명",
    #                    "tool_prop": "날붙이", "time_ms": 10000}}
    HARVEST_TABLE = {}

    # 전투 대사 (서브클래스에서 오버라이드)
    COMBAT_LINES = {
        "discover": [],       # 적 발견 시
        "attack": [],         # 공격 시
        "hit": [],            # 피격 시
        "low_hp": [],         # 체력 낮을 때 (≤30%)
        "death": [],          # 사망 시
        "flee": [],           # 도주 시
    }

    # describe/focus 규칙 (서브클래스에서 오버라이드)
    DESCRIBE_RULES = None
    FOCUS_RULES = None

    # 기본 스케줄 (서브클래스에서 오버라이드)
    SCHEDULE = [
        {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
    ]

    def _populate_inventory(self):
        """스폰 시 드롭 테이블 기반 인벤토리 생성"""
        import random
        from assets.registry import get_or_create_item_id

        for entry in self.DROP_TABLE:
            if random.random() > entry["chance"]:
                continue
            count = entry["count"]
            if isinstance(count, tuple):
                count = random.randint(count[0], count[1])
            item_id = get_or_create_item_id(entry["item"])
            morld.give_item(self.instance_id, item_id, count)

    def mate(self):
        """플레이어 → 생물체 교미 (bestiality)"""
        import settings
        import survival
        import combat
        import romance
        from romance_mode import MODE_FORCED

        if not settings.is_bestiality_enabled():
            morld.add_action_log("수간 모드가 꺼져 있다.")
            return

        # 생물체가 무력화 상태인지 확인
        target_id = self.instance_id
        if not (survival.is_npc_fainted(target_id) or
                combat.is_paralyzed(target_id) or
                combat.is_web_bound(target_id)):
            morld.add_action_log("상대가 반항하고 있다. 무력화가 필요하다.")
            return

        # 로맨스 세션 시작 (forced mode, bestiality)
        player_id = morld.get_player_id()
        yield from romance.start_romance(
            player_id, target_id,
            mode=MODE_FORCED,
            is_bestiality=True,
        )


class Wolf(Monster):
    """늑대 — 숲 지역 서식, 공격적"""
    unique_id = "wolf"
    name = "늑대"
    GENDER_DISTRIBUTION = [("male", 0.5), ("female", 0.5)]
    harassment_chance = 0.4  # 공격적, 무력화 대상에 적극적

    props = {
        **Monster.props,
        "전투:세력": "늑대",
        "생존:체력": 40,
        "생존:최대체력": 40,
        "전투:공격력": 8,
        "전투:방어력": 3,
        "전투:명중": 75,
        "전투:회피": 15,
        "전투:사거리": 70,
        "전투:감지거리": 120,
        # 수확 가능 소재 (props에 수량 등록)
        "소재:가죽": 2,
        "소재:이빨": 1,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.2,
    }

    DROP_TABLE = [
        {"item": "meat", "chance": 0.8, "count": (1, 2)},
    ]

    HARVEST_TABLE = {
        "소재:가죽": {
            "item": "wolf_pelt",
            "name": "늑대 가죽",
            "tool_prop": "날붙이",
            "time_ms": 10_000,
        },
        "소재:이빨": {
            "item": "wolf_fang",
            "name": "늑대 이빨",
            "tool_prop": "날붙이",
            "time_ms": 5_000,
        },
    }

    COMBAT_LINES = {
        "discover": ["늑대가 이빨을 드러내며 으르렁거린다.", "늑대가 낮은 자세로 접근한다."],
        "attack": ["늑대가 날카로운 이빨로 물어뜯는다!", "늑대가 발톱으로 할퀸다!"],
        "hit": ["늑대가 비명을 지른다!", "늑대가 고통스럽게 울부짖는다."],
        "low_hp": ["늑대가 절뚝거리며 으르렁거린다.", "피투성이 늑대가 이빨을 드러낸다."],
        "death": ["늑대가 쓰러져 움직이지 않는다."],
        "flee": ["늑대가 꼬리를 내리고 도주한다!"],
    }

    describe_text = {"default": "회색 털의 늑대."}
    focus_text = {"default": "야생 늑대가 경계하고 있다."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "{name}의 시체가 쓰러져 있다."),
        ({"hp_ratio": 0.3}, "피투성이 {name}(이)가 가쁜 숨을 쉬고 있다."),
        ({"독": True}, "{name}(이)가 독에 중독되어 몸을 떨고 있다."),
        ({}, "{name}(이)가 주변을 경계하고 있다."),
    ]

    FOCUS_RULES = [
        ({"hp_ratio": 0.3}, "[color=red]심각한 부상[/color] — 피를 흘리며 위협적으로 으르렁거린다."),
        ({"독": True}, "[color=purple]중독[/color] — 몸을 떨고 있다."),
        ({}, "날카로운 이빨과 발톱을 가진 야생 늑대."),
    ]

    # 늑대 스케줄 — 박명박모성 (새벽/저녁 활동)
    SCHEDULE = [
        {"name": "수면",  "start": 0,          "end": 18_000_000,  "activity": "수면"},   # 00:00-05:00
        {"name": "순찰",  "start": 18_000_000,  "end": 43_200_000,  "activity": "순찰"},  # 05:00-12:00
        {"name": "휴식",  "start": 43_200_000,  "end": 54_000_000,  "activity": "휴식"},  # 12:00-15:00
        {"name": "순찰",  "start": 54_000_000,  "end": 75_600_000,  "activity": "순찰"},  # 15:00-21:00
        {"name": "복귀",  "start": 75_600_000,  "end": 82_800_000,  "activity": "복귀"},  # 21:00-23:00
        {"name": "수면",  "start": 82_800_000,  "end": 86_400_000,  "activity": "수면"},  # 23:00-24:00
    ]


class Bat(Monster):
    """박쥐 — 폐광산 1층, 빠르고 회피 높지만 약함"""
    unique_id = "bat"
    name = "박쥐"
    # GENDER_DISTRIBUTION = None → 무성 (기본값)

    props = {
        **Monster.props,
        "전투:세력": "박쥐",
        "생존:체력": 15,
        "생존:최대체력": 15,
        "전투:공격력": 3,
        "전투:방어력": 1,
        "전투:명중": 65,
        "전투:회피": 25,
        "전투:치명타": 5,
        "전투:사거리": 50,
        "전투:감지거리": 80,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "nearest",
        "preferred_range": 50,
        "retreat_threshold": 0.3,
    }

    DROP_TABLE = [
        {"item": "meat", "chance": 0.5, "count": 1},
    ]

    COMBAT_LINES = {
        "discover": ["박쥐가 날카롭게 울며 날아온다.", "어둠 속에서 박쥐의 눈이 빛난다."],
        "attack": ["박쥐가 날카로운 이빨로 덤벼든다!", "박쥐가 빠르게 스쳐 지나간다!"],
        "hit": ["박쥐가 끽 소리를 지른다!", "박쥐가 비틀거린다."],
        "low_hp": ["박쥐의 비행이 불안정해진다."],
        "death": ["박쥐가 바닥에 떨어진다."],
        "flee": ["박쥐가 어둠 속으로 사라진다!"],
    }

    describe_text = {"default": "어둠 속에서 날개짓하는 박쥐."}
    focus_text = {"default": "작지만 날카로운 이빨을 가진 박쥐."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "{name}의 시체가 바닥에 떨어져 있다."),
        ({"hp_ratio": 0.3}, "상처 입은 {name}(이)가 불안정하게 날고 있다."),
        ({}, "{name}(이)가 어둠 속에서 날개짓하고 있다."),
    ]

    FOCUS_RULES = [
        ({"hp_ratio": 0.3}, "[color=red]심각한 부상[/color] — 비행이 불안정하다."),
        ({}, "작지만 빠른 박쥐. 어둠 속에서 움직인다."),
    ]

    # 박쥐 스케줄 — 야행성
    SCHEDULE = [
        {"name": "수면",  "start": 0,          "end": 64_800_000,  "activity": "수면"},   # 00:00-18:00
        {"name": "순찰",  "start": 64_800_000,  "end": 82_800_000,  "activity": "순찰"},  # 18:00-23:00
        {"name": "복귀",  "start": 82_800_000,  "end": 86_400_000,  "activity": "복귀"},  # 23:00-24:00
    ]


class Spider(Monster):
    """거미 — 폐광산 2층/깊은 갱도, 공격적"""
    unique_id = "spider"
    name = "거미"
    GENDER_DISTRIBUTION = [("female", 0.7), ("male", 0.3)]
    harassment_chance = 0.5  # 웹 속박 대상에 높은 확률

    props = {
        **Monster.props,
        "전투:세력": "거미",
        "생존:체력": 50,
        "생존:최대체력": 50,
        "전투:공격력": 6,
        "전투:방어력": 4,
        "전투:명중": 75,
        "전투:회피": 10,
        "전투:치명타": 8,
        "전투:사거리": 70,
        "전투:감지거리": 100,
        "전투:독공격": 30,       # 명중 시 30% 확률로 독
        "전투:거미줄공격": 25,   # 명중 시 25% 확률로 거미줄 결박
        # 수확 가능 소재
        "소재:독낭": 1,
        "소재:거미줄": 2,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.15,
    }

    HARVEST_TABLE = {
        "소재:독낭": {
            "item": "spider_venom",
            "name": "거미독",
            "tool_prop": "날붙이",
            "time_ms": 8_000,
        },
        "소재:거미줄": {
            "item": "spider_silk",
            "name": "거미줄",
            "tool_prop": None,
            "time_ms": 3_000,
        },
    }

    COMBAT_LINES = {
        "discover": ["거미가 다리를 세우며 위협한다.", "거미줄 위에서 거미가 다가온다."],
        "attack": ["거미가 독니로 물어뜯는다!", "거미가 거미줄을 뿜는다!"],
        "hit": ["거미가 끽끽거리며 뒤로 물러난다!", "거미의 다리에서 체액이 흐른다."],
        "low_hp": ["거미가 몸을 웅크리며 독을 뿜을 준비를 한다."],
        "death": ["거미가 다리를 접으며 쓰러진다."],
        "flee": ["거미가 벽을 타고 도주한다!"],
    }

    describe_text = {"default": "거대한 거미가 거미줄 사이에서 기다리고 있다."}
    focus_text = {"default": "독과 거미줄을 가진 위험한 거미."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "{name}의 시체가 다리를 접은 채 쓰러져 있다."),
        ({"hp_ratio": 0.3}, "상처 입은 {name}(이)가 독니를 드러내고 있다."),
        ({"독": True}, "{name}(이)가 자신의 독에 중독되어 몸부림친다."),
        ({}, "{name}(이)가 거미줄 위에서 먹잇감을 기다리고 있다."),
    ]

    FOCUS_RULES = [
        ({"hp_ratio": 0.3}, "[color=red]심각한 부상[/color] — 체액을 흘리며 위협적으로 독니를 드러낸다."),
        ({"독": True}, "[color=purple]중독[/color] — 자신의 독에 오염되어 있다."),
        ({}, "독니와 거미줄을 가진 거대한 거미. 매복형 포식자다."),
    ]

    # 거미 스케줄 — 매복형, 주야 순찰
    SCHEDULE = [
        {"name": "순찰",  "start": 0,          "end": 43_200_000,  "activity": "순찰"},   # 00:00-12:00
        {"name": "휴식",  "start": 43_200_000,  "end": 57_600_000,  "activity": "휴식"},  # 12:00-16:00
        {"name": "순찰",  "start": 57_600_000,  "end": 86_400_000,  "activity": "순찰"},  # 16:00-24:00
    ]


# ========================================
# 인간형 몬스터
# ========================================

class HumanoidCreature(Monster):
    """인간형 몬스터 — 성행위 반응 가능, 아키타입 보유"""
    archetype = "fierce"

    props = {
        **Monster.props,
        "is_humanoid": 1,
    }

    actions = ["call:attack:공격#", "call:mate:교미#"]

    ROMANCE_REACTIONS = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.archetype:
            from assets.base import build_romance_reactions
            self.ROMANCE_REACTIONS = build_romance_reactions(self.archetype)


class Arachne(HumanoidCreature):
    """아라크네 — 거미 여인, 상반신 여성 + 하반신 거미"""
    unique_id = "arachne"
    name = "아라크네"
    archetype = "fierce"
    GENDER_DISTRIBUTION = [("female", 1.0)]
    harassment_chance = 0.5

    props = {
        **HumanoidCreature.props,
        "전투:세력": "유적",
        "생존:체력": 70,
        "생존:최대체력": 70,
        "전투:공격력": 10,
        "전투:방어력": 5,
        "전투:명중": 75,
        "전투:회피": 15,
        "전투:사거리": 80,
        "전투:감지거리": 100,
        "전투:거미줄공격": 30,
        "전투:독공격": 20,
        "소재:거미줄": 3,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "aggressive",
        "target_priority": "nearest",
        "preferred_range": 80,
        "retreat_threshold": 0.15,
    }

    HARVEST_TABLE = {
        "소재:거미줄": {
            "item": "arachne_silk",
            "name": "아라크네의 거미줄",
            "tool_prop": None,
            "time_ms": 5_000,
        },
    }

    COMBAT_LINES = {
        "discover": ["아라크네가 붉은 눈으로 노려본다.", "'사냥감이 걸어왔군.'"],
        "attack": ["아라크네가 날카로운 다리로 찌른다!", "거미줄이 날아온다!"],
        "hit": ["아라크네가 날카로운 비명을 지른다!", "'이 벌레 같은...!'"],
        "low_hp": ["아라크네의 움직임이 느려진다.", "상반신에서 피가 흐른다."],
        "death": ["아라크네가 다리를 접으며 쓰러진다."],
        "flee": ["아라크네가 벽을 타고 후퇴한다!"],
    }

    describe_text = {"default": "상반신은 여인, 하반신은 거대한 거미."}
    focus_text = {"default": "거미줄 사이에서 먹잇감을 노리고 있다."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "{name}의 시체가 다리를 접은 채 쓰러져 있다."),
        ({"hp_ratio": 0.3}, "피투성이 {name}(이)가 위협적으로 다리를 세운다."),
        ({"독": True}, "{name}(이)가 자신의 독에 중독되어 몸부림친다."),
        ({}, "{name}(이)가 거미줄 위에서 먹잇감을 노리고 있다."),
    ]

    FOCUS_RULES = [
        ({"hp_ratio": 0.3}, "[color=red]심각한 부상[/color] — 상반신에서 피가 흐르고 있다."),
        ({}, "상반신은 아름다운 여인, 하반신은 거대한 거미. 8개의 다리가 위협적이다."),
    ]

    SCHEDULE = [
        {"name": "순찰", "start": 0,          "end": 43_200_000, "activity": "순찰"},
        {"name": "휴식", "start": 43_200_000,  "end": 57_600_000, "activity": "휴식"},
        {"name": "순찰", "start": 57_600_000,  "end": 86_400_000, "activity": "순찰"},
    ]


class Succubus(HumanoidCreature):
    """서큐버스 — 유혹하는 음마, 유적 심층 보스"""
    unique_id = "succubus"
    name = "서큐버스"
    archetype = "seductive"
    GENDER_DISTRIBUTION = [("female", 1.0)]
    harassment_chance = 0.7

    props = {
        **HumanoidCreature.props,
        "전투:세력": "유적",
        "생존:체력": 100,
        "생존:최대체력": 100,
        "전투:공격력": 8,
        "전투:방어력": 4,
        "전투:명중": 85,
        "전투:회피": 20,
        "전투:치명타": 10,
        "전투:사거리": 70,
        "전투:감지거리": 120,
        "전투:마비공격": 25,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "nearest",
        "preferred_range": 70,
        "retreat_threshold": 0.1,
    }

    DROP_TABLE = [
        {"item": "succubus_horn", "chance": 0.5, "count": 1},
    ]

    COMBAT_LINES = {
        "discover": ["'후후... 손님이 찾아왔네.'", "서큐버스가 유혹적인 미소를 짓는다."],
        "attack": ["서큐버스의 손톱이 빛난다!", "'아프게 하진 않을게~'"],
        "hit": ["서큐버스가 고통스러운 표정을 짓는다.", "'앗... 거칠구나.'"],
        "low_hp": ["'꽤... 하는걸...'", "서큐버스의 날개가 떨린다."],
        "death": ["서큐버스가 쓰러지며 날개를 접는다."],
        "flee": ["서큐버스가 날개를 펼쳐 후퇴한다!"],
    }

    describe_text = {"default": "박쥐 날개를 가진 아름다운 여인."}
    focus_text = {"default": "매혹적인 눈빛으로 바라보고 있다."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "{name}의 시체가 날개를 접은 채 쓰러져 있다."),
        ({"hp_ratio": 0.3}, "상처 입은 {name}(이)가 위험한 미소를 짓고 있다."),
        ({}, "{name}(이)가 매혹적인 눈빛으로 바라보고 있다."),
    ]

    FOCUS_RULES = [
        ({"hp_ratio": 0.3}, "[color=red]심각한 부상[/color] — 날개에서 피가 떨어지고 있다."),
        ({}, "박쥐 날개와 뿔을 가진 아름다운 여인. 위험한 매력을 풍긴다."),
    ]

    SCHEDULE = [
        {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
    ]


# ========================================
# 기생형 몬스터
# ========================================

class ParasiticCreature(Monster):
    """기생형 몬스터 — 전투 + 기생 부착 가능"""
    parasite_item_class = None   # 부착할 기생 아이템 unique_id
    parasitize_chance = 0.3

    props = {
        **Monster.props,
        "is_parasitic": 1,
    }

    COMBAT_LINES = {
        "discover": ["기묘한 생물체가 꿈틀거린다."],
        "attack": ["생물체가 달려든다!"],
        "hit": ["생물체가 끈적한 체액을 흘린다."],
        "death": ["생물체가 축 늘어진다."],
    }


class BreastParasiteCreature(ParasiticCreature):
    """가슴 기생체 몬스터"""
    unique_id = "breast_parasite_creature"
    name = "가슴 기생충"
    parasite_item_class = "breast_parasite"
    parasitize_chance = 0.4

    props = {
        **ParasiticCreature.props,
        "전투:세력": "기생",
        "생존:체력": 20,
        "생존:최대체력": 20,
        "전투:공격력": 3,
        "전투:방어력": 1,
        "전투:명중": 60,
        "전투:회피": 20,
        "전투:사거리": 40,
        "전투:감지거리": 60,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "nearest",
        "preferred_range": 40,
        "retreat_threshold": 0.3,
    }

    COMBAT_LINES = {
        "discover": ["흐물흐물한 생물체가 가슴 쪽을 향해 꿈틀거린다."],
        "attack": ["생물체가 촉수를 뻗는다!"],
        "hit": ["생물체가 움츠러든다."],
        "death": ["생물체가 축 늘어져 움직이지 않는다."],
    }

    describe_text = {"default": "반투명한 촉수 생물체."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "축 늘어진 {name}의 잔해."),
        ({}, "반투명한 촉수 {name}(이)가 꿈틀거리고 있다."),
    ]

    SCHEDULE = [
        {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
    ]


class GenitalParasiteCreature(ParasiticCreature):
    """음부 기생체 몬스터"""
    unique_id = "genital_parasite_creature"
    name = "음부 기생충"
    parasite_item_class = "genital_parasite"
    parasitize_chance = 0.3

    props = {
        **ParasiticCreature.props,
        "전투:세력": "기생",
        "생존:체력": 25,
        "생존:최대체력": 25,
        "전투:공격력": 4,
        "전투:방어력": 2,
        "전투:명중": 65,
        "전투:회피": 15,
        "전투:사거리": 40,
        "전투:감지거리": 60,
    }

    BATTLE_BEHAVIOR = {
        "combat_style": "evasive",
        "target_priority": "nearest",
        "preferred_range": 40,
        "retreat_threshold": 0.3,
    }

    COMBAT_LINES = {
        "discover": ["끈적한 생물체가 하반신을 향해 기어온다."],
        "attack": ["생물체가 촉수를 뻗어 감싸려 한다!"],
        "hit": ["생물체가 끈적한 액체를 분비한다."],
        "death": ["생물체가 녹아내리듯 축 늘어진다."],
    }

    describe_text = {"default": "끈적한 촉수를 가진 생물체."}

    DESCRIBE_RULES = [
        ({"hp_ratio": 0.0}, "녹아내린 {name}의 잔해."),
        ({}, "끈적한 촉수를 가진 {name}(이)가 꿈틀거리고 있다."),
    ]

    SCHEDULE = [
        {"name": "순찰", "start": 0, "end": 86_400_000, "activity": "순찰"},
    ]


# ========================================
# 기타
# ========================================

class TrainingDummy(Character):
    """훈련용 허수아비 — 반격 없음, HP 999"""
    unique_id = "training_dummy"
    name = "허수아비"
    type = "character"
    owner = None

    props = {
        "생존:체력": 999,
        "생존:최대체력": 999,
        "전투:방어력": 0,
        "전투:회피": 0,
    }

    actions = ["call:attack:공격#"]
    # BATTLE_BEHAVIOR 없음 → think에서 전투 안 함
