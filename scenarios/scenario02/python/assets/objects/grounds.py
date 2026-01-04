# assets/objects/grounds.py - 바닥 오브젝트
#
# 각 Location에서 참조하는 바닥 오브젝트 정의
# 아이템을 바닥에 놓거나 주울 수 있게 해주는 특수 오브젝트
#
# 사용법:
#   from assets.objects.grounds import GroundGrass
#   self.add_ground(GroundGrass())

from assets.base import Object


# ========================================
# 실내 바닥
# ========================================

class GroundWooden(Object):
    unique_id = "ground_wooden"
    name = "나무 바닥"
    actions = ["putinobject"]
    appearance = {"default": "잘 닦인 나무 바닥."}
    is_visible = True


class GroundStone(Object):
    unique_id = "ground_stone"
    name = "돌 바닥"
    actions = ["putinobject"]
    appearance = {"default": "차갑고 단단한 돌 바닥."}
    is_visible = True


class GroundMarble(Object):
    unique_id = "ground_marble"
    name = "대리석 바닥"
    actions = ["putinobject"]
    appearance = {"default": "우아하게 빛나는 대리석 바닥."}
    is_visible = True


class GroundTile(Object):
    unique_id = "ground_tile"
    name = "타일 바닥"
    actions = ["putinobject"]
    appearance = {"default": "깨끗하게 관리된 타일 바닥."}
    is_visible = True


# ========================================
# 실외 바닥
# ========================================

class GroundDirt(Object):
    unique_id = "ground_dirt"
    name = "흙바닥"
    actions = ["putinobject"]
    appearance = {"default": "부드러운 흙바닥."}
    is_visible = True


class GroundGrass(Object):
    unique_id = "ground_grass"
    name = "잔디"
    actions = ["putinobject"]
    appearance = {"default": "푸른 잔디가 깔려 있다."}
    is_visible = True


class GroundForest(Object):
    unique_id = "ground_forest"
    name = "숲 바닥"
    actions = ["putinobject"]
    appearance = {"default": "낙엽과 이끼가 덮인 숲 바닥."}
    is_visible = True


class GroundRocky(Object):
    unique_id = "ground_rocky"
    name = "바위투성이 땅"
    actions = ["putinobject"]
    appearance = {"default": "울퉁불퉁한 바위와 자갈이 깔려 있다."}
    is_visible = True
