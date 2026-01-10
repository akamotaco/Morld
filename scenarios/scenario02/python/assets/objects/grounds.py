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
    focus_text = {"default": "잘 닦인 나무 바닥."}


class GroundStone(Object):
    unique_id = "ground_stone"
    name = "돌 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "차갑고 단단한 돌 바닥."}


class GroundMarble(Object):
    unique_id = "ground_marble"
    name = "대리석 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "우아하게 빛나는 대리석 바닥."}


class GroundTile(Object):
    unique_id = "ground_tile"
    name = "타일 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "깨끗하게 관리된 타일 바닥."}


# ========================================
# 실외 바닥
# ========================================

class GroundDirt(Object):
    unique_id = "ground_dirt"
    name = "흙바닥"
    actions = ["putinobject"]
    focus_text = {"default": "부드러운 흙바닥."}


class GroundGrass(Object):
    unique_id = "ground_grass"
    name = "잔디"
    actions = ["putinobject"]
    focus_text = {"default": "푸른 잔디가 깔려 있다."}


class GroundForest(Object):
    unique_id = "ground_forest"
    name = "숲 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "낙엽과 이끼가 덮인 숲 바닥."}


class GroundRocky(Object):
    unique_id = "ground_rocky"
    name = "바위투성이 땅"
    actions = ["putinobject"]
    focus_text = {"default": "울퉁불퉁한 바위와 자갈이 깔려 있다."}


# ========================================
# 도시 바닥 (황폐화된 도시)
# ========================================

class GroundAsphalt(Object):
    unique_id = "ground_asphalt"
    name = "아스팔트 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "금이 간 아스팔트. 잡초가 틈새로 자라나 있다."}


class GroundConcrete(Object):
    unique_id = "ground_concrete"
    name = "콘크리트 바닥"
    actions = ["putinobject"]
    focus_text = {"default": "버려진 건물의 콘크리트 바닥. 먼지가 쌓여 있다."}
