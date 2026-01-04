# events/location_events.py - 위치 도착 이벤트
#
# 플레이어가 특정 위치에 도착했을 때 발생하는 이벤트

import morld
from .player_creation import get_player_name


def on_reach_front_yard():
    """앞마당 도착 이벤트 - 쓰러짐"""
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


def after_collapse(context_unit_id):
    """쓰러진 후 - 구조되어 방에서 깨어남"""
    player_id = morld.get_player_id()

    # 플레이어를 주인공 방으로 이동
    morld.set_unit_location(player_id, 0, 6)  # 저택(0), 주인공 방(6)

    # 시간 경과 (저녁이 되었다고 가정)
    morld.advance_time(180)  # 3시간 경과

    wakeup_pages = [
        "......",
        "......응...?",
        "눈을 떠보니 낯선 천장이 보인다.",
        "부드러운 침대 위에 누워 있다.",
        "...여기는 어디지?",
        "분명 숲에서 쓰러졌는데...",
        "누군가 나를 이곳으로 옮겨준 모양이다.",
        "몸 상태가 많이 나아진 것 같다.\n잠시 쉬었던 것 같다.",
        "일단 일어나서 여기가 어딘지 알아봐야겠다."
    ]

    # 챕터 1: 저택 생활 시작 - NPC 로드
    morld.set_flag("chapter", 1)
    _load_chapter_1_npcs()

    return {
        "type": "monologue",
        "pages": wakeup_pages,
        "time_consumed": 0,
        "button_type": "ok"
    }


def _load_chapter_1_npcs():
    """챕터 1에서 NPC들을 인스턴스화"""
    from world import instantiate_npcs
    instantiate_npcs()
