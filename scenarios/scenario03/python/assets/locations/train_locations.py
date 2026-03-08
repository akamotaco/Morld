# assets/locations/train_locations.py - 지저철 Location 클래스
#
# Region 1: 지저철 내부
# - TrainCar: 객차 (이동 중 대기/대화)

from assets.base import Location


class TrainCar(Location):
    """지저철 객차 — 이동 중 대기/대화 공간"""
    unique_id = "train_car"
    name = "객차"
    is_indoor = True
    ground_type = "GroundConcrete"
    length = 150
    describe_text = {
        "default": "낡은 플라스틱 좌석 몇 개가 남아 있다. 천장의 손잡이가 덜렁거린다.",
    }
