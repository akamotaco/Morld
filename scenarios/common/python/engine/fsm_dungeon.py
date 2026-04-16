# engine/fsm_dungeon.py — DungeonState (던전 진행 중 행동 차단)
#
# 리니어 던전 진행 시 파티원 NPC에게 push → 일반 생활(5-tier) 차단.
# 던전 퇴장 시 pop → 생활 복원.
#
# 레벨: LV_DUNGEON = 8 (LV_COMBAT=10 미만 → 전투 발생 시 전투가 우선)

from engine.fsm import FSMState

LV_DUNGEON = 8


class DungeonState(FSMState):
    """던전 진행 중 — 일반 생활 차단, 대기만 수행.

    update() → True: 하위 로직 (식사/산책/스케줄) 완전 차단.
    던전 퇴장 시 agent._fsm_pop() 또는 _fsm_pop_by_type("dungeon")으로 해제.
    """
    state_type = "dungeon"
    level = LV_DUNGEON

    def enter(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 진입")

    def update(self, agent):
        # 던전 중: 대기만 (10분)
        agent._insert_idle_job("던전 대기", 600_000)
        agent._action_taken = True
        return True

    def exit(self, agent):
        print("[FSM] " + str(agent.get_name()) + ": DungeonState 해제")
