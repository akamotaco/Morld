# events/game_start/prologue.py - 프롤로그 시작 이벤트
#
# 게임 시작 시 캐릭터 생성 흐름

import morld
from events.base import GameStartEvent
from events import registry


@registry.register
class PrologueStart(GameStartEvent):
    """게임 시작 - 캐릭터 생성"""
    once = True

    def handle(self, **ctx):
        from assets.characters.player import NAME_OPTIONS

        # 챕터 0: 프롤로그 (숲 방황)
        morld.set_flag("chapter", 0)

        intro_pages = [
            "......",
            "......의식이 희미하게 떠오른다.",
            "머리가... 아프다.",
            "여기는... 어디지?",
            "기억이... 나지 않는다.",
            "눈앞에 울창한 나무들이 보인다.\n숲 속인 것 같다.",
            "...일단 나 자신에 대해 생각해보자."
        ]

        # 이름 선택 페이지
        name_options = "\n".join([
            f"[url=script:set_name:{name}]{name}[/url]"
            for name in NAME_OPTIONS
        ])
        name_page = f"내 이름은...?\n\n{name_options}"

        return {
            "type": "monologue",
            "pages": intro_pages + [name_page],
            "time_consumed": 0,
            "button_type": "none_on_last"
        }
