# assets/locations/vehicles.py - 차량 Location (밀폐형 탈것)
#
# Region 1 (차량 전용 Region) 사용
# - Location 0: 낡은 자동차 (old_car)
#
# 자동차는 밀폐형 탈것으로 Location 타입
# - 별도의 Region(Region 1)에 속함
# - RegionEdge로 외부 Location과 연결
# - 운전 시 RegionEdge의 LocationA(외부 Region 쪽)가 변경됨
# - 자동차 Location 자체는 변하지 않음
# - 탑승자들은 자동차 Location에 계속 머무름

from assets.base import Location
from assets.objects.vehicles import CarDriverSeat, CarPassengerSeat, CarTrunk


class OldCar(Location):
    """
    낡은 자동차 - 주차장에서 발견

    밀폐형 탈것 (Location 타입)
    - 항상 실내 취급
    - 외부 정보 차단 (날씨 등)
    - 운전석에서 "운전" 액션으로 이동
    """
    unique_id = "old_car"
    name = "낡은 자동차"
    is_indoor = True
    stay_duration = 0
    describe_text = {
        "default": "오래된 세단형 자동차. 시동이 걸릴지 모르겠다."
    }

    def instantiate(self, location_id: int, region_id: int):
        """
        자동차 생성 + 내부 오브젝트 배치

        Unit ID 할당:
        - 운전석: 231
        - 조수석: 232
        - 트렁크: 233
        """
        super().instantiate(location_id, region_id)

        # 내부 오브젝트 배치 (바닥 대신)
        self.add_object(CarDriverSeat(), 231)
        self.add_object(CarPassengerSeat(), 232)
        self.add_object(CarTrunk(), 233)
