# assets/characters/creatures.py — 던전 생물 정의 (F1~F5 상층)
#
# 변이종: 지상 동물이 던전 침식으로 변이
# 적응종: 던전에서 태어나 적응한 토착종
#
# 참조: docs/creature-system.md

from assets.base import Character
from assets.registry import register_character


# ========================================
# 기반 클래스
# ========================================

class Creature(Character):
    """던전 생물 기반 클래스"""

    # 생물 공통
    faction = "던전:상층"    # 세력 (층별 재정의)
    behavior = "aggressive"  # aggressive/defensive/evasive/ambush/swarm
    spawn_count = (1, 1)     # 출현 수 범위
    aggro_trigger = "sight"  # sight/sound/proximity
    retreat_threshold = 0.2  # HP 비율 이하 → 도주

    # 침식 관련
    erosion_on_hit = 0       # 공격 시 침식 부여량
    erosion_on_death = -1    # 처치 시 침식 변화

    # 드롭
    drop_table = []

    # 전투 대사
    combat_lines = {
        "discover": [],
        "attack": [],
        "death": [],
        "flee": [],
    }

    # 경험치
    exp = 0

    # 리스폰 가능 여부
    respawnable = True

    # 엘리트 여부
    is_elite = False


# ========================================
# 상층 (F1~F5) — 변이종/적응종
# ========================================

@register_character
class BlindRat(Creature):
    """맹목쥐 — 군집형 변이종. 소음 감지, 시각 없음."""
    unique_id = "blind_rat"
    name = "맹목쥐"

    base_str = 2
    base_agi = 12
    base_vit = 3
    base_mnd = 1

    faction = "던전:상층"
    behavior = "swarm"
    spawn_count = (3, 6)
    aggro_trigger = "sound"
    retreat_threshold = 0.3

    erosion_on_hit = 0
    erosion_on_death = 0
    exp = 5

    props = {
        "생존:체력": 8,
        "생존:최대체력": 8,
        "전투:공격력": 2,
        "전투:방어력": 0,
        "전투:감지거리": 50,
        "전투:공격속도": 0.5,
        "세력": "던전:상층",
    }

    drop_table = [
        {"item": "rat_meat", "chance": 0.4, "count": (1, 1)},
    ]

    combat_lines = {
        "discover": ["어둠 속에서 발톱 긁는 소리가 들린다."],
        "attack": ["쥐떼가 일제히 달려든다!"],
        "death": ["쥐가 경련하며 쓰러진��."],
        "flee": ["쥐떼가 사방으로 흩어진다!"],
    }

    def get_describe_text(self):
        return "바닥에서 바스락거리는 소리가 들린다. 눈 없는 쥐떼가 벽을 타고 있다."

    def get_focus_text(self):
        return "눈이 없다. 대신 귀가 비정상적으로 크다. 소리에 반응한다."


@register_character
class Fangdog(Creature):
    """이빨개 — 선공형 변이종. 과잉 발달한 송곳니."""
    unique_id = "fangdog"
    name = "이빨개"

    base_str = 10
    base_agi = 8
    base_vit = 9
    base_mnd = 3

    faction = "던전:상층"
    behavior = "aggressive"
    aggro_trigger = "sight"
    retreat_threshold = 0.15

    erosion_on_hit = 0
    erosion_on_death = -1
    exp = 15

    props = {
        "생존:체력": 35,
        "생존:최대체력": 35,
        "전투:공격력": 7,
        "전투:방어력": 3,
        "전투:감지거리": 80,
        "전투:공격속도": 1.0,
        "세력": "던전:상층",
    }

    drop_table = [
        {"item": "dog_fang", "chance": 0.5, "count": (1, 2)},
        {"item": "tough_hide", "chance": 0.3, "count": (1, 1)},
    ]

    combat_lines = {
        "discover": ["으르렁거리는 소리가 통로를 채운다. 개... 였던 것이 이빨을 드러낸다."],
        "attack": ["이빨개가 과잉 발달한 송곳니로 물어뜯는다!"],
        "death": ["이빨개가 처절한 비명을 지르며 쓰러진다."],
        "flee": ["이빨개가 꼬리를 말고 어둠 속으로 사라진다."],
    }

    def get_describe_text(self):
        return "송곳니가 입 밖으로 튀어나온 개 같은 것이 통로를 어슬렁거린다."

    def get_focus_text(self):
        return "한때 가축견이었을 것이다. 지금은 송곳니가 턱을 뚫고 자라 입을 닫지 못한다."


@register_character
class Petraspider(Creature):
    """석화거미 — 잠복형 변이종. 돌처럼 위장, 실로 포획."""
    unique_id = "petraspider"
    name = "석화거미"

    base_str = 6
    base_agi = 5
    base_vit = 10
    base_mnd = 2

    faction = "던전:상층"
    behavior = "ambush"
    aggro_trigger = "proximity"
    retreat_threshold = 0.1  # 거의 도주 안 함

    erosion_on_hit = 1
    erosion_on_death = -1
    exp = 12

    props = {
        "생존:체력": 25,
        "생존:최대체력": 25,
        "전투:공격력": 5,
        "전투:방어력": 6,
        "전투:감지거리": 30,  # 근접해야 감지
        "전투:공격속도": 1.5,
        "세력": "던전:상층",
    }

    drop_table = [
        {"item": "spider_silk", "chance": 0.6, "count": (1, 2)},
        {"item": "stone_chitin", "chance": 0.2, "count": (1, 1)},
    ]

    combat_lines = {
        "discover": ["바위인 줄 알았던 것이 다리를 편다."],
        "attack": ["석화거미가 끈적한 실을 뿜는다!"],
        "death": ["석화거미가 바스러지며 돌가루가 흩날린다."],
        "flee": [],  # 거의 도주하지 않음
    }

    def get_describe_text(self):
        return ""  # 잠복 중 — 감지 전까지 보이지 않음

    def get_focus_text(self):
        return "돌처럼 보이지만 자세히 보면 관절이 있다. 건드리면 안 될 것 같다."


@register_character
class Slimeworm(Creature):
    """점액충 — 수비형 적응종. 느리고 무해. 채취 가능."""
    unique_id = "slimeworm"
    name = "점액충"

    base_str = 3
    base_agi = 2
    base_vit = 15
    base_mnd = 1

    faction = "던전:상층"
    behavior = "defensive"
    aggro_trigger = "proximity"
    retreat_threshold = 0.5  # 쉽게 도주

    erosion_on_hit = 0
    erosion_on_death = -2
    exp = 8

    props = {
        "생존:체력": 40,
        "생존:최대체력": 40,
        "전투:공격력": 3,
        "전투:방어력": 2,
        "전투:감지거리": 20,
        "전투:공격속도": 2.0,  # 매우 느림
        "세력": "던전:상층",
    }

    drop_table = [
        {"item": "slime", "chance": 0.8, "count": (1, 3)},
    ]

    combat_lines = {
        "discover": ["축축한 바닥에서 뭔가 꿈틀거린다."],
        "attack": ["점액충이 느릿하게 몸을 부딪힌다."],
        "death": ["점액충이 터지며 끈적한 액체가 튄다."],
        "flee": ["점액충이 느릿느릿 벽 틈으로 기어간다."],
    }

    def get_describe_text(self):
        return "반투명한 지렁이 같은 것이 벽을 타고 있다. 위험해 보이지는 않는다."

    def get_focus_text(self):
        return "점액으로 뒤덮인 연체 생물. 건드리지 않으면 무해하다. 점액은 소재로 쓸 수 있다."


# ========================================
# 상층 엘리트 (F2~F4)
# ========================================

@register_character
class GreaterPetraspider(Creature):
    """대형 석화거미 — 엘리트. 방 봉쇄, 리스폰 없음."""
    unique_id = "greater_petraspider"
    name = "대형 석화거미"

    base_str = 12
    base_agi = 6
    base_vit = 16
    base_mnd = 3

    faction = "던전:상층"
    behavior = "ambush"
    aggro_trigger = "proximity"
    retreat_threshold = 0.0  # 도주 안 함

    erosion_on_hit = 2
    erosion_on_death = -3
    exp = 30
    respawnable = False
    is_elite = True

    props = {
        "생존:체력": 60,
        "생존:최대체력": 60,
        "전투:공격력": 10,
        "전투:방어력": 10,
        "전투:감지거리": 40,
        "전투:공격속도": 1.8,
        "세력": "던전:상층",
    }

    drop_table = [
        {"item": "spider_silk", "chance": 1.0, "count": (3, 5)},
        {"item": "stone_chitin", "chance": 0.8, "count": (2, 3)},
    ]

    combat_lines = {
        "discover": ["통로를 막고 있는 거대한 바위가... 움직인다."],
        "attack": ["대형 석화거미가 두꺼운 실로 출구를 봉쇄한다!"],
        "death": ["대형 석화거미가 무너지며 통로가 열린다."],
        "flee": [],
    }

    def get_describe_text(self):
        return ""  # 잠복 — 바위로 위장

    def get_focus_text(self):
        return "석화거미의 성체. 통로를 완전히 막을 정도로 크다. 실로 퇴로를 차단한다."


# ========================================
# 상층 보스 (F5)
# ========================================

@register_character
class Plaguedog(Creature):
    """감염견 — F5 보스. 침식 전이 공격."""
    unique_id = "plaguedog"
    name = "감염견"

    base_str = 16
    base_agi = 11
    base_vit = 14
    base_mnd = 5

    faction = "던전:상층"
    behavior = "aggressive"
    aggro_trigger = "sight"
    retreat_threshold = 0.0  # 보스는 도주 안 함

    erosion_on_hit = 5  # 물리면 침식 전이
    erosion_on_death = -5
    exp = 50
    respawnable = False
    is_elite = False  # 보스 (엘리트와 별도)

    props = {
        "생존:체력": 120,
        "생존:최대체력": 120,
        "전투:공격력": 14,
        "전투:방어력": 6,
        "전투:감지거리": 100,
        "전투:공격속도": 0.8,
        "세력": "던전:상층",
        "보스": 1,
    }

    drop_table = [
        {"item": "plague_fang", "chance": 1.0, "count": (1, 1)},
        {"item": "tough_hide", "chance": 1.0, "count": (2, 3)},
        {"item": "infection_gland", "chance": 0.5, "count": (1, 1)},
    ]

    combat_lines = {
        "discover": [
            "악취가 코를 찌른다. 어둠 속에서 거대한 그림자가 나타난다.",
            "핏줄이 드러난 붉은 눈이 이쪽을 노려본다."
        ],
        "attack": [
            "감염견이 검은 침을 흘리며 덮친다!",
            "이빨에서 검은 액체가 뚝뚝 떨어진다!"
        ],
        "death": [
            "감염견이 쓰러지며 몸에서 검은 연기가 피어오른다.",
            "... 어딘가에서 낮은 울음소리가 들린다. 동료를 부르는 걸까."
        ],
        "flee": [],
    }

    def get_describe_text(self):
        return "통로 끝에 거대한 개가 웅크리고 있다. 온몸에 검은 맥이 박동하고 있다."

    def get_focus_text(self):
        return (
            "이빨개의 상위종. 이빨개 무리의 우두머리였던 것 같다. "
            "침식이 깊이 진행되어 물리면 침식이 전이된다. "
            "눈에 아직 슬픔이 남아 있다."
        )
