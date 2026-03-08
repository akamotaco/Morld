# events/tutorial.py - 건축 튜토리얼 이벤트 (Step 4~6)
#
# BuildTutorialEvent: 비서가 건축 시스템 설명 (탐색 퀘스트 완료 후)
# ReinforcementEvent: 에이전트 4명 + 건축 자재 도착

import morld
import ui


def handle_build_tutorial():
    """Step 4: 건축 시스템 튜토리얼

    트리거: 플랫폼 탐색 퀘스트 완료 후 비서 대화
    """
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "현재 플랫폼에는 기본적인 공간밖에 없습니다.\n"
        "+침실, 보관소 등을 건설해야 합니다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "건축 메뉴에서 건설할 위치와 종류를 지정하세요.\n"
        "+실제 건설은 에이전트들이 수행합니다.",
    )
    yield ui.dialog(
        "[b]비서[/b]\n\n"
        "아직 에이전트가 없으니... 곧 도착할 겁니다.",
    )


def handle_reinforcement():
    """Step 5: 에이전트 증원 도착

    트리거: Step 4 완료 후 시간 경과 또는 이벤트
    """
    yield ui.dialog(
        "승강장에서 지저철 도착 소리가 울린다.",
    )

    # 에이전트 4명 동적 생성
    agent_defs = [
        {"unique_id": "echo_01", "name": "Echo-01", "role": "assault"},
        {"unique_id": "echo_02", "name": "Echo-02", "role": "support"},
        {"unique_id": "echo_03", "name": "Echo-03", "role": "sniper"},
        {"unique_id": "echo_04", "name": "Echo-04", "role": "medic"},
    ]

    from assets.characters.squad_member import SquadMember
    from think.agents.squad_agent import SquadMemberAgent
    from think import register_agent

    for agent_def in agent_defs:
        npc = SquadMember()
        npc.configure(agent_def["unique_id"], agent_def["name"], agent_def["role"])
        npc_id = morld.create_id("unit")
        npc.instantiate(npc_id, 0, 0)  # 승강장(R0, L0)에 배치

        agent = SquadMemberAgent(npc_id)
        register_agent(npc_id, agent)

    # 건축 자재 배달
    from assets.items.materials import MetalPipe, ConcreteBlock, Plank, Wire

    materials = [
        (Plank, 20),
        (ConcreteBlock, 15),
        (MetalPipe, 10),
        (Wire, 8),
    ]

    for item_cls, count in materials:
        item = item_cls()
        item_id = morld.create_id("item")
        item.instantiate(item_id)
        # TODO: 승강장 바닥에 배치 (ground 시스템 연동)
        # ground.ensure_ground_at(0, 0, 100)
        # morld.give_item(ground_id, item_id, count)

    # 비서 소개
    lines = [
        "[b]비서[/b]\n\n",
        "증원 에이전트 4명이 도착했습니다.\n",
        "+Echo 시리즈... 표준 모델입니다.\n",
    ]
    for ad in agent_defs:
        lines.append(f"+  {ad['name']} -- {ad['role']}\n")
    lines.append("건축 자재도 함께 도착했습니다.\n")
    lines.append("+이제 건설을 시작할 수 있습니다.")

    yield ui.dialog("".join(lines))
