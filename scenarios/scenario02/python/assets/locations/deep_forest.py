# assets/locations/deep_forest.py - 숲 깊은 곳

from assets.base import Location


class DeepForest(Location):
    unique_id = "deep_forest"
    name = "숲 깊은 곳"
    is_indoor = False
    ground_type = "GroundForest"
    stay_duration = 0
    length = 1800  # Pi-World: 숲 깊은 곳 길이
    describe_text = {
        "default": "울창한 나무들 사이. 낮에도 어둑하고 길을 잃기 쉽다.",
        "낮": "나뭇잎 사이로 간간이 빛이 스며든다.",
        "밤": "칠흑같이 어둡다. 부엉이 소리가 들린다.",
        "날씨:비": "빗물이 나뭇잎을 타고 흘러내린다.",
        "날씨:눈": "눈이 쌓여 숲이 고요하다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """숲 깊은 곳 생성"""
        super().instantiate(location_id, region_id)
