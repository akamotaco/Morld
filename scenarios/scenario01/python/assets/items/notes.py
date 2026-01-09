# assets/items/notes.py - 쪽지류 (쪽지1, 쪽지2, 쪽지3)

import morld
from assets.base import Item


class Note1(Item):
    """쪽지 1"""
    unique_id = "note1"
    name = "쪽지 1"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "call:read:읽기@inventory"]

    content = '''"빛이 없으면 길도 없다"

"첫 번째는 불꽃 속에,
두 번째는 차가운 곳에,
세 번째와 네 번째는 벽에 걸린 눈 속에."'''

    def read(self):
        """쪽지 1 읽기 - Generator 기반 인스턴스 메서드"""
        yield morld.dialog([self.content])


class Note2(Item):
    """쪽지 2"""
    unique_id = "note2"
    name = "쪽지 2"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "call:read:읽기@inventory"]

    content = '''"화장대 서랍을 열고 싶다면
숫자를 찾아라.

불꽃이 처음이요,
냉기가 다음이요,
그림이 마지막이니라."'''

    def read(self):
        """쪽지 2 읽기 - Generator 기반 인스턴스 메서드"""
        yield morld.dialog([self.content])


class Note3(Item):
    """쪽지 3"""
    unique_id = "note3"
    name = "쪽지 3"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "call:read:읽기@inventory"]

    content = '''"연도를 기억하라 - 1842"'''

    def read(self):
        """쪽지 3 읽기 - Generator 기반 인스턴스 메서드"""
        yield morld.dialog([self.content])
