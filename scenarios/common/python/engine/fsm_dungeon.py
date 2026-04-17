# engine/fsm_dungeon.py — DungeonState (던전 진행 중 행동 차단)
#
# 리니어 던전 진행 시 파티원 NPC에게 push → 일반 생활(5-tier) 차단.
# 던전 퇴장 시 pop → 생활 복원.
#
# 레벨: LV_DUNGEON = 8 (LV_COMBAT=10 미만 → 전투 발생 시 전투가 우선)

import morld
from engine.fsm import FSMState

LV_DUNGEON = 8
LV_DUNGEON_EXPLORE = 6


class DungeonState(FSMState):
    """던전 이벤트 진행 중 — 일반 생활 완전 차단 + 리더 실신 구출.

    update() → True: 하위 로직 (식사/산책/스케줄) 완전 차단.
    전투/휴식 등 노드 이벤트 처리 중에 push.
    """
    state_type = "dungeon"
    level = LV_DUNGEON

    def enter(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 진입")
        morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 0)

    def update(self, agent):
        # 리더(플레이어) 실신 체크
        player_id = morld.get_player_id()
        if player_id is not None:
            fainted = morld.get_unit_prop(player_id, "상태:실신")
            if fainted:
                my_fainted = morld.get_unit_prop(agent.unit_id, "상태:실신")
                if not my_fainted:
                    morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 1)
                    agent._insert_idle_job("구출 준비", 300_000)
                    agent._action_taken = True
                    return True

        agent._insert_idle_job("던전 대기", 600_000)
        agent._action_taken = True
        return True

    def exit(self, agent):
        morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 0)
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 해제")


class DungeonExploreState(FSMState):
    """던전 탐색 중 — 감각/판단 허용 (pass-through).

    update() → False: 하위 로직(_on_think)으로 위임.
    NPC가 소리를 듣거나 상황을 판단하는 등 자율 행동 가능.
    노드 이벤트(전투 등) 시작 시 DungeonState가 push되면
    레벨(8 > 6)로 DungeonExploreState가 자동 pop.
    """
    state_type = "dungeon_explore"
    level = LV_DUNGEON_EXPLORE

    def enter(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonExploreState 진입")

    def update(self, agent):
        # pass-through → _on_think (감각 수집, 판단 등)
        return False

    def exit(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonExploreState 해제")
