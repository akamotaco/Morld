# assets/locations/vehicles.py - 대형 차량 내부 Location
#
# Region 1: 대형 차량 내부
# - Location 0: 버스 내부 (bus_interior)
#
# 대형 차량은 외부 Object + 내부 Location 구조:
# - 외부 Object (OldBus): 운전석, 조수석 — 실외에 배치
# - 내부 Location (BusInterior): 승객 좌석, 화물칸 — 별도 Region
# - RegionGate로 외부↔내부 연결
# - 차량 이동 시 Gate 재연결 (morld.reconnect_interior_gate)

import morld
from assets.base import Location, Object


class BusSeat(Object):
    """버스 좌석 — 내부 승객용"""
    unique_id = "bus_seat"
    name = "버스 좌석"
    actions = ["sit@seat:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"seated_by:seat": -1}
    focus_text = {"default": "낡은 천 시트. 스프링이 좀 빠져 있지만 앉을 수 있다."}


class BusCargo(Object):
    """버스 화물칸 — 아이템 보관"""
    unique_id = "bus_cargo"
    name = "화물칸"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "버스 뒤쪽의 화물 공간. 짐을 실을 수 있다."}

    def look(self):
        import ui
        yield ui.dialog("화물칸을 열어보았다. 물건을 넣거나 꺼낼 수 있겠다.")


class BusInterior(Location):
    """버스 내부 — 대형 차량의 실내 공간

    Region 1, Location 0에 배치.
    좌석 4개 + 화물칸 1개.
    """
    unique_id = "bus_interior"
    name = "버스 내부"
    is_indoor = True
    stay_duration = 0
    geometry = 1  # line
    length = 200
    describe_text = {
        "default": "낡은 버스의 내부. 좌석이 몇 줄 남아 있고, 뒤쪽에 화물 공간이 있다.",
    }

    def instantiate(self, location_id: int, region_id: int):
        super().instantiate(location_id, region_id)

        # 승객 좌석 4개
        for i, x in enumerate([30, 60, 90, 120]):
            seat = BusSeat()
            seat.unique_id = f"bus_seat_{i}"
            seat.name = f"버스 좌석 {i + 1}"
            self.add_object(seat, x=x)

        # 화물칸
        self.add_object(BusCargo(), x=170)
