# assets/locations/__init__.py - Location 클래스 모듈
#
# 방 탈출 시나리오의 모든 Location 클래스를 정의

from assets.locations.basement import Basement
from assets.locations.storage import Storage
from assets.locations.living_room import LivingRoom
from assets.locations.kitchen import Kitchen
from assets.locations.corridor_1f import Corridor1F
from assets.locations.stairs import Stairs
from assets.locations.bedroom import Bedroom
from assets.locations.study import Study
from assets.locations.corridor_2f import Corridor2F
from assets.locations.entrance_hall import EntranceHall

__all__ = [
    "Basement",
    "Storage",
    "LivingRoom",
    "Kitchen",
    "Corridor1F",
    "Stairs",
    "Bedroom",
    "Study",
    "Corridor2F",
    "EntranceHall",
]
