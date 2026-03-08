# world/train.py - 지저철 내부 Region (시나리오03)
#
# Region 1: 지저철 내부
# - 객차 (L0): 이동 중 대기/대화 공간, len=150

import morld

REGION_ID = 1

REGION = {
    "id": REGION_ID,
    "name": "지저철",
    "describe_text": {"default": "낡은 지하철 객차. 좌석 대부분이 뜯겨져 있다."},
}


def initialize_terrain():
    """지저철 Region 지형 초기화"""
    # Region 등록
    r = REGION
    morld.add_region(r["id"], r["name"], r["describe_text"])

    # Location 등록
    _initialize_locations()

    print(f"[train] Region {REGION_ID} initialized: 1 location")


def _initialize_locations():
    """지저철 Location 초기화"""
    from assets.locations.train_locations import TrainCar

    car = TrainCar()
    car.instantiate(0, REGION_ID)
