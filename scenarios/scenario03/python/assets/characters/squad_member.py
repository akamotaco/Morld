# assets/characters/squad_member.py - 분대원 기본 클래스
#
# Echo 시리즈 에이전트의 기본 캐릭터 클래스.
# unique_id는 "echo_{nn}" 패턴 (예: echo_01, echo_02).
# 동적 생성을 지원하기 위해 인스턴스별 unique_id를 설정한다.

from assets.base import Character


# Echo 시리즈 역할별 기본 props
ROLE_PROPS = {
    "assault": {
        "역할": "돌격",
        "vita": 6,
        "sapientia": 3,
    },
    "support": {
        "역할": "화력 지원",
        "vita": 5,
        "sapientia": 4,
    },
    "sniper": {
        "역할": "저격",
        "vita": 4,
        "sapientia": 5,
    },
    "medic": {
        "역할": "의무병",
        "vita": 3,
        "sapientia": 7,
    },
}


class SquadMember(Character):
    """분대원 — Echo 시리즈 에이전트

    동적 생성 시 unique_id, name, role을 인스턴스별로 설정.

    Usage:
        npc = SquadMember()
        npc.configure("echo_01", "Echo-01", "assault")
        npc_id = morld.create_id("unit")
        npc.instantiate(npc_id, region_id, location_id)
    """
    unique_id = "squad_member"
    name = "에이전트"
    type = "male"
    describe_text = {
        "default": "전투복 차림의 에이전트. 무표정하게 서 있다.",
    }
    props = {
        "세력": "소속없음",
    }
    actions = [
        "call:talk:대화",
    ]

    DESCRIBE_RULES = [
        ({}, "전투복 차림의 에이전트."),
    ]
    FOCUS_RULES = [
        ({}, "규격화된 전투복. 시리얼 번호가 가슴에 새겨져 있다."),
    ]

    def configure(self, unique_id, name, role="assault"):
        """인스턴스별 설정 (instantiate 전에 호출)

        Args:
            unique_id: 고유 식별자 (예: "echo_01")
            name: 표시 이름 (예: "Echo-01")
            role: 역할 ("assault", "support", "sniper", "medic")
        """
        self.unique_id = unique_id
        self.name = name
        # 역할별 props 병합
        role_props = ROLE_PROPS.get(role, {})
        self.props = dict(self.props)  # 클래스 속성 복사
        self.props.update(role_props)
        self.props["세력"] = "플레이어"

    def talk(self):
        """분대원과 대화"""
        import ui
        yield ui.dialog("명령을 기다리고 있습니다.")
