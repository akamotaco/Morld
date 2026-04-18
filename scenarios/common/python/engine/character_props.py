# character_props.py — 캐릭터 권한(can:) prop 세트
#
# 시나리오 Player/NPC가 아래 세트를 **병합(dict unpacking)** 해서 사용.
# 계층:
#   COMMON_ACTION   = 모든 캐릭터 공통 (NPC + 플레이어)
#   COMMON_LEADER   = 파티 지휘권 보유 (플레이어 + 리더 NPC)
#   + 시나리오/캐릭터별 고유 props
#
# 사용 예:
#   from engine.character_props import COMMON_ACTION_PROPS, COMMON_LEADER_PROPS
#
#   class Player(Character):
#       props = {**COMMON_ACTION_PROPS, **COMMON_LEADER_PROPS,
#                "can:browse_quests": 1, ...}
#
#   class NpcA(Character):
#       props = {**COMMON_ACTION_PROPS, "성격": "탐욕", ...}


# 모든 캐릭터 공통 기본 행동
# (NPC도 자율행동 중 아이템 줍기/내려놓기 필요)
COMMON_ACTION_PROPS = {
    "can:putinobject": 1,   # 오브젝트/바닥에 아이템 넣기
    "can:take_item": 1,     # 컨테이너/바닥에서 아이템 가져가기
}


# 파티 지휘권 (플레이어 + 리더 NPC)
# 통솔/명령 권한을 가진 캐릭터가 보유
COMMON_LEADER_PROPS = {
    "can:invite_to_party": 1,       # 파티 초대
    "can:dismiss_from_party": 1,    # 파티 이탈 지시
    "can:dungeon_proceed": 1,       # 던전 노드 진행 결정
}
