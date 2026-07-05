# world.py — scenario_mini 지형 + 배치
#
# region 1개(미니 마을) / location 1개(광장) / 유닛 3개(플레이어+NPC 2).
# 파티 초기화와 에이전트 등록까지 여기서 수행한다.

import morld

import think
from assets.characters import Traveler, Mia, Ranger
from engine import party


def build():
    """지형 생성 + 유닛 배치. Returns: {"player","guide","ranger"} unit_id dict"""
    morld.add_region(0, "미니 마을")
    morld.add_location(0, 0, "광장")

    handles = {}

    traveler = Traveler()
    player_id = morld.create_id("unit")
    traveler.instantiate(player_id, 0, 0)  # unique_id="player" → PlayerId 자동
    handles["player"] = player_id

    mia = Mia()
    mia_id = morld.create_id("unit")
    mia.instantiate(mia_id, 0, 0)
    handles["guide"] = mia_id
    handles["guide_asset"] = mia

    ranger = Ranger()
    ranger_id = morld.create_id("unit")
    ranger.instantiate(ranger_id, 0, 0)
    handles["ranger"] = ranger_id
    handles["ranger_asset"] = ranger

    # 파티: 플레이어 솔로 파티 (engine.party — 모집은 request_recruit 경유)
    party.initialize_party(player_id)

    # AI: 캐릭터 표준 ③ 레지스트리에서 에이전트 생성/등록
    agent = think.create_agent_for("mini_guide", mia_id)
    if agent is not None:
        think.register_agent(mia_id, agent)

    return handles
