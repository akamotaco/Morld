# assets/items/materials.py - 자재 아이템
#
# 크래프팅에 사용되는 기본 재료들
# - Log: 통나무 (나무 벌목) → 도끼로 나무판 가공 가능
# - Branch: 나뭇가지 (나무에서 줍기)
# - Plank: 나무판 (통나무 가공)
# - Cord: 끈 (풀 등에서 채집)
# - Feather: 깃털 (새 사냥 등)

import morld
from assets.base import Item
from assets.registry import get_item_class


class Log(Item):
    """
    통나무 - 크래프팅 재료

    도끼(passive) 보유 시 "나무판으로 가공" 액션 활성화
    통나무 1개 → 나무판 3개
    """
    unique_id = "log"
    name = "통나무"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 10
    actions = [
        "take@container",
        "call:look:살펴보기@inventory",
        "call:process:나무판으로 가공@inventory"  # can:chop 필요 (도끼 보유)
    ]

    # 가공 설정
    PLANK_COUNT = 3  # 통나무 1개 → 나무판 3개
    PROCESS_TIME = 10  # 가공 시간 10분

    def look(self):
        """통나무 살펴보기"""
        yield morld.dialog([
            "단단한 통나무다.",
            "도끼가 있으면 나무판으로 가공할 수 있을 것 같다."
        ])

    def process(self):
        """
        통나무를 나무판으로 가공 (can:chop 필요)

        도끼 보유 확인은 can:chop 액션 필터링으로 처리됨
        """
        player_id = morld.get_player_id()

        yield morld.dialog("통나무를 나무판으로 가공한다...")
        morld.advance_time(self.PROCESS_TIME)

        # 나무판 아이템 ID 조회 또는 생성
        plank_id = morld.get_item_id_by_unique("plank")
        if plank_id is None:
            plank_class = get_item_class("plank")
            if plank_class:
                plank_item = plank_class()
                plank_id = morld.create_id("item")
                plank_item.instantiate(plank_id)
            else:
                yield morld.dialog("나무판을 만들었지만, 무언가 잘못됐다.")
                return

        # 통나무 1개 소모
        morld.lost_item(player_id, self.instance_id, 1)

        # 나무판 지급
        morld.give_item(player_id, plank_id, self.PLANK_COUNT)

        yield morld.dialog([
            f"나무판 {self.PLANK_COUNT}개를 만들었다!",
            "다양한 제작에 쓸 수 있겠다."
        ])


class Branch(Item):
    """나뭇가지 - 크래프팅 재료"""
    unique_id = "branch"
    name = "나뭇가지"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나뭇가지 살펴보기"""
        yield morld.dialog([
            "마른 나뭇가지다.",
            "불쏘시개나 간단한 도구 재료로 쓸 수 있다."
        ])


class Plank(Item):
    """나무판 - 크래프팅 재료 (통나무 가공)"""
    unique_id = "plank"
    name = "나무판"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 5
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """나무판 살펴보기"""
        yield morld.dialog([
            "반듯하게 다듬어진 나무판이다.",
            "건축이나 도구 제작에 쓸 수 있다."
        ])


class Cord(Item):
    """끈 - 크래프팅 재료 (활, 덫 등 제작용)"""
    unique_id = "cord"
    name = "끈"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 3
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """끈 살펴보기"""
        yield morld.dialog([
            "질긴 식물 줄기로 엮은 끈이다.",
            "활이나 덫을 만드는 데 쓸 수 있다."
        ])


class Feather(Item):
    """깃털 - 크래프팅 재료 (화살 등 제작용)"""
    unique_id = "feather"
    name = "깃털"
    category = "material"
    passive_props = {}
    equip_props = {}
    value = 2
    actions = ["take@container", "call:look:살펴보기@inventory"]

    def look(self):
        """깃털 살펴보기"""
        yield morld.dialog([
            "새의 깃털이다.",
            "화살 깃으로 쓸 수 있겠다."
        ])
