# engine/fsm_dungeon.py — DungeonState (던전 진행 중 행동 차단)
#
# 리니어 던전 진행 시 파티원 NPC에게 push → 일반 생활(5-tier) 차단.
# 던전 퇴장 시 pop → 생활 복원.
#
# 레벨: LV_DUNGEON = 8 (LV_COMBAT=10 미만 → 전투 발생 시 전투가 우선)

import morld
from engine.fsm import FSMState

LV_DUNGEON = 8


class DungeonState(FSMState):
    """던전 진행 중 — 일반 생활 차단 + 리더 실신 시 구출 판정.

    update() → True: 하위 로직 (식사/산책/스케줄) 완전 차단.
    리더(플레이어) 실신 감지 → "dungeon:구출의사" prop 설정.
    던전 퇴장 시 agent._fsm_pop() 또는 _fsm_pop_by_type("dungeon")으로 해제.
    """
    state_type = "dungeon"
    level = LV_DUNGEON

    def enter(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 진입")
        # 구출 의사 초기화
        morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 0)

    def update(self, agent):
        # 리더(플레이어) 실신 체크
        player_id = morld.get_player_id()
        if player_id is not None:
            fainted = morld.get_unit_prop(player_id, "상태:실신")
            if fainted:
                # 이 NPC가 생존 상태면 구출 의사 표명
                my_fainted = morld.get_unit_prop(agent.unit_id, "상태:실신")
                if not my_fainted:
                    morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 1)
                    agent._insert_idle_job("구출 준비", 300_000)
                    agent._action_taken = True
                    return True

        # 일반 던전 대기
        agent._insert_idle_job("던전 대기", 600_000)
        agent._action_taken = True
        return True

    def exit(self, agent):
        # 구출 의사 prop 정리
        morld.set_unit_prop(agent.unit_id, "dungeon:구출의사", 0)
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 해제")
