# events/reach/front_yard.py - 앞마당 도착 이벤트
#
# 플레이어가 앞마당에 도착하면 쓰러짐

from events.base import ReachEvent
from events import registry


@registry.register
class FrontYardCollapse(ReachEvent):
    """앞마당 도착 - 쓰러짐"""
    region_id = 0
    location_id = 12
    once = True

    def handle(self, **ctx):
        collapse_pages = [
            "저 앞에... 건물이 보인다.",
            "저택인가? 드디어 사람이 사는 곳을 찾았다.",
            "하지만... 몸이 말을 듣지 않는다.",
            "배가 고프고... 너무 지쳤다.",
            "눈앞이... 흐려진다...",
            "......",
            "(의식을 잃었다)"
        ]

        return {
            "type": "monologue",
            "pages": collapse_pages,
            "time_consumed": 0,
            "button_type": "ok",
            "done_callback": "after_collapse"
        }
