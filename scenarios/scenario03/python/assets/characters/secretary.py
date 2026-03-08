# assets/characters/secretary.py - 비서 NPC
#
# 상부 조직의 연락관. 플랫폼에 상주하며 오퍼레이터(플레이어)를 보좌한다.
# 직접 전투/탐사에는 참여하지 않는다.

from assets.base import Character


class Secretary(Character):
    """비서 — 상부 조직의 연락관"""
    unique_id = "secretary"
    name = "???"                    # 시리얼 번호 (추후 결정)
    type = "female"
    describe_text = {
        "default": "단정한 정장 차림. 표정 없는 얼굴로 클립보드를 들고 있다.",
    }
    props = {
        "역할": "비서",
        "세력": "상부",
    }
    actions = [
        "call:talk:대화",
        "call:report:보고 요청",
    ]

    # 대화 규칙 (간단한 데모용)
    DESCRIBE_RULES = [
        ({}, "클립보드를 들고 서 있다."),
    ]
    FOCUS_RULES = [
        ({}, "단정한 정장 차림. 감정을 읽을 수 없는 얼굴이다."),
    ]

    def talk(self):
        """비서와 대화"""
        import ui
        # TODO: 상황별 분기 (퀘스트 진행 상태에 따라)
        yield ui.dialog("필요한 것이 있으시면 말씀하세요.")

    def report(self):
        """현황 보고 요청"""
        import ui
        # TODO: 실제 상황 데이터 기반 보고
        lines = [
            "[b]현황 보고[/b]\n",
            "현재 특이사항 없습니다.",
            "추가 지시를 기다리겠습니다.",
        ]
        yield ui.dialog("\n".join(lines))
