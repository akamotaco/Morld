# assets/characters/squad_member.py - 분대원 기본 클래스
#
# Echo 시리즈 에이전트의 기본 캐릭터 클래스.
# unique_id는 "echo_{nn}" 패턴 (예: echo_01, echo_02).
# 동적 생성을 지원하기 위해 인스턴스별 unique_id를 설정한다.

from assets.base import Character


# Echo 시리즈 역할별 기본 props
# 생존:체력 = 30 + vita*5 (규격품 초기치). 인간성은 1-based (0=미추적, 실질 하한 1).
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


def base_hp_for_vita(vita):
    """vita 기반 규격 체력"""
    return 30 + int(vita) * 5


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

    def configure(self, unique_id, name, role="assault", humanity=100,
                  archetype=None, stat_overrides=None):
        """인스턴스별 설정 (instantiate 전에 호출)

        Args:
            unique_id: 고유 식별자 (예: "echo_01")
            name: 표시 이름 (예: "Echo-01")
            role: 역할 ("assault", "support", "sniper", "medic")
            humanity: 인간성 초기치 (재보급 개체는 전임자 트라우마 계승으로 감소)
            archetype: 개체 아키타입 (recruit_pool 제조 편차 — 미지정 시
                       역할 고정 매핑 폴백, npc_dialogue.member_archetype 참조)
            stat_overrides: 스탯 덮어쓰기 dict (예: {"vita": 7}) — 체력은
                       최종 vita 기준으로 재계산
        """
        self.unique_id = unique_id
        self.name = name
        # 역할별 props 병합
        role_props = ROLE_PROPS.get(role, {})
        self.props = dict(self.props)  # 클래스 속성 복사
        self.props.update(role_props)
        if stat_overrides:
            self.props.update(stat_overrides)
        self.props["세력"] = "플레이어"
        vita = self.props.get("vita", 5)
        hp = base_hp_for_vita(vita)
        self.props["생존:체력"] = hp
        self.props["생존:체력max"] = hp
        # 인간성: 0=미추적과 구분하기 위해 하한 1 (prop 계약: 부재=0)
        self.props["인간성"] = max(1, int(humanity))
        # 아키타입: 문자열 prop — hybrid 대사 톤의 개체 차이 (부재=0 → 폴백)
        if archetype:
            self.archetype = archetype
            self.props["아키타입"] = archetype

    def talk(self):
        """분대원과 대화"""
        import ui
        yield ui.dialog("명령을 기다리고 있습니다.")
