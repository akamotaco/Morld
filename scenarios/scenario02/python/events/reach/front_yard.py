# events/reach/front_yard.py - 앞마당 도착 이벤트
#
# 플레이어가 앞마당에 도착하면 쓰러짐 → 챕터 1 전환

import morld
from events.base import ReachEvent
from events import registry


@registry.register
class FrontYardCollapse(ReachEvent):
    """앞마당 도착 - 쓰러짐 → 챕터 1 전환"""
    region_id = 0
    location_id = 12  # 앞마당
    once = True

    def handle(self, **ctx):
        # 쓰러짐 모놀로그
        yield morld.dialog([
            "저 앞에... 건물이 보인다.",
            "저택인가? 드디어 사람이 사는 곳을 찾았다.",
            "하지만... 몸이 말을 듣지 않는다.",
            "배가 고프고... 너무 지쳤다.",
            "눈앞이... 흐려진다...",
            "......",
            "(의식을 잃었다)"
        ])

        # 챕터 1 로드 (전체 지형 + NPC)
        # load_chapter가 플레이어 위치도 설정함 (현관에서 시작)
        from chapters import load_chapter
        load_chapter("chapter_1")

        morld.set_prop("chapter", 1)

        # 시간 경과 (저녁이 되었다고 가정)
        morld.advance_time(180)  # 3시간 경과

        # 깨어남 모놀로그
        yield morld.dialog([
            "......",
            "......응...?",
            "눈을 떠보니 낯선 천장이 보인다.",
            "부드러운 침대 위에 누워 있다.",
            "...여기는 어디지?",
            "분명 숲에서 쓰러졌는데...",
            "누군가 나를 이곳으로 옮겨준 모양이다.",
            "몸 상태가 많이 나아진 것 같다.\n잠시 쉬었던 것 같다.",
            "일단 일어나서 여기가 어딘지 알아봐야겠다."
        ])
