# assets/characters/operator.py - 오퍼레이터 (플레이어)
#
# 플레이어 = 통신실(노란 선 안쪽)에 상주하는 관리자.
# unique_id="player" 등록 시 C#이 PlayerId를 자동 설정하여
# (script_system_data_api.cs:1112) CRT 콘솔 등 오브젝트 액션이
# 표준 Look/액션 파이프라인으로 노출된다.
#
# S03은 원격 지휘 시나리오 — 오퍼레이터는 통신실 밖으로 나갈 일이 없지만,
# 플레이어 유닛 자체는 존재한다 (infra-unification-plan §2-2).

from assets.base import Character


class Operator(Character):
    """오퍼레이터 — 플레이어 캐릭터 (통신실 상주)"""
    unique_id = "player"
    name = "오퍼레이터"
    type = "male"
    describe_text = {
        "default": "관제 임무를 수행하는 오퍼레이터.",
    }
    props = {
        "세력": "플레이어",
    }
    actions = []

    DESCRIBE_RULES = [
        ({}, "CRT 모니터 앞에 앉아 있는 오퍼레이터."),
    ]
    FOCUS_RULES = [
        ({}, "지급받은 관리자 제복. 아직 몸에 익지 않았다."),
    ]
