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
        morld.set_prop("chapter", 0)

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


@registry.register
class MessageBoxDemo(GameStartEvent):
    """MessageBox API 시범 - 게임 시작 전 알림"""
    once = True
    priority = 100  # PrologueStart보다 먼저 실행

    def handle(self, **ctx):
        # 일반 모놀로그 반환 (제너레이터가 아님)
        # MessageBox 시범은 별도 스크립트 함수로 테스트
        return {
            "type": "monologue",
            "pages": [
                "[b]Morld - MessageBox API 시범[/b]",
                "이 게임에는 새로운 MessageBox API가 구현되었습니다.",
                "Python에서 yield morld.messagebox()를 사용하여\n다이얼로그 결과를 받을 수 있습니다.",
                "[url=script:intro_with_messagebox]MessageBox 테스트하기[/url]\n\n또는 [확인]을 눌러 게임을 시작하세요."
            ],
            "time_consumed": 0,
            "button_type": "ok"
        }


# ========================================
# MessageBox API 시범 - 게임 시작 전 알림
# ========================================
@morld.register_script
def intro_with_messagebox(context_unit_id):
    """
    MessageBox API 시범 함수

    사용법: script:intro_with_messagebox

    yield를 사용하여 다이얼로그 결과를 받음
    """
    # MessageBox 표시 (YESNO 타입)
    result = yield morld.messagebox(
        "Morld",
        "MessageBox API 시범입니다.\n\n게임을 시작하시겠습니까?",
        "YESNO"
    )

    if result == "YES":
        morld.add_action_log("[시스템] 게임을 시작합니다.")
        return {
            "type": "message",
            "message": "게임이 시작되었습니다!"
        }
    else:
        morld.add_action_log("[시스템] 게임 시작이 취소되었습니다.")
        return {
            "type": "message",
            "message": "게임 시작이 취소되었습니다."
        }
