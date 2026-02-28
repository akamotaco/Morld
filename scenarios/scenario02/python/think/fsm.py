# think/fsm.py — 스택 기반 FSM (Finite State Machine)
#
# NPC AI의 행동 컨텍스트를 스택으로 관리.
# - 스택 root(index 0)에 LifeState 항상 존재
# - 스택이 비거나 빈 상태에서 pop 시 에러 (로직 버그 감지)
# - push 시 동일 이상 레벨 자동 pop → change 동작 자연 발생
# - 레벨 간격 10 단위 (사이 삽입 여유)
#
# 레벨 계층:
#   LV_LIFE       =  0  생활 (root, 불변)
#   LV_COMBAT     = 10  전투
#   LV_COMBAT_SUB = 20  전투 하위 (도주/체념/필사)
#   LV_TRANSIT    = 30  Gate 이동 (어디서든 push, 아무것도 pop 안 함)
#
# 현재 구현: LifeState (root) + GateTransitState
# 향후 확장: CombatState, FleeState, ResignState, DesperateState

import morld
import random

# === 레벨 상수 ===
LV_LIFE = 0
LV_COMBAT = 10
LV_COMBAT_SUB = 20
LV_TRANSIT = 30


class FSMState:
    """FSM 상태 기반 클래스"""
    state_type = "base"
    level = -1  # 서브클래스에서 반드시 오버라이드

    def enter(self, agent):
        """스택에 push될 때 호출"""
        pass

    def update(self, agent) -> bool:
        """매 think() 호출 시 실행.

        Returns:
            True  = 처리 완료 (하위 로직 차단)
            False = 이 State가 pop됨, 하위 로직 진행
        """
        return False

    def exit(self, agent):
        """스택에서 pop될 때 호출"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}(lv={self.level})>"


class LifeState(FSMState):
    """생활 상태 — FSM root (항상 스택 최하단)

    update()가 항상 False를 반환하여 기존 5-tier think() 로직으로 진행.
    """
    state_type = "life"
    level = LV_LIFE

    def update(self, agent) -> bool:
        return False  # 항상 Life 로직(5-tier)으로 진행


class GateTransitState(FSMState):
    """Gate Transit — cross-location 이동 중 think() 차단

    enter(): 상태:이동중=1 설정, 행동 로그, move job 삽입
    update(): 이동 완료(상태:이동중=0) 감지 시 pop → Life 진행
    exit(): 안전장치 prop 정리
    """
    state_type = "gate_transit"
    level = LV_TRANSIT

    def __init__(self, target, name="이동"):
        self.target = target
        self.name = name

    def enter(self, agent):
        morld.set_unit_prop(agent.unit_id, "상태:이동중", 1)

        # 행동 로그: 플레이어와 같은 location일 때만 (목격)
        player_id = morld.get_player_id()
        player_loc = morld.get_unit_location(player_id) if player_id else None
        loc = agent.get_location()
        if player_loc and loc and player_loc[0] == loc[0] and player_loc[1] == loc[1]:
            dest_info = morld.get_location_info(
                self.target["region_id"], self.target["location_id"])
            dest_name = dest_info["name"] if dest_info else "알 수 없는 곳"
            my_name = agent.get_info()["name"]
            morld.add_action_log(f"{my_name}이(가) {dest_name}(으)로 이동을 시작했다.")

        # Move job 삽입 (duration=0 → C#이 거리/속도 기반 계산)
        target_x = self.target.get("x", 0)
        length = int(self.target.get("length", 0))
        if length > 0 and target_x == 0:
            target_x = random.randint(0, length)
        morld.insert_job(agent.unit_id, {
            "name": self.name,
            "action": "move",
            "region_id": self.target["region_id"],
            "location_id": self.target["location_id"],
            "target_x": target_x,
            "duration": 0,
        })
        agent._action_taken = True
        print(f"[FSM] {agent.get_info().get('name', agent.unit_id)}: "
              f"GateTransitState ENTER → {self.target['region_id']}:{self.target['location_id']}")

    def update(self, agent) -> bool:
        # DES step 5가 텔레포트 완료 시 상태:이동중=0 으로 설정
        if not morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            print(f"[FSM] {agent.get_info().get('name', agent.unit_id)}: "
                  f"GateTransitState 도착 → POP")
            agent._fsm_pop()  # 도착 → pop
            return False       # Life 로직 진행
        # 이동 중 → job 보존, 아무것도 안 함
        agent._action_taken = True
        return True

    def exit(self, agent):
        # 안전장치: prop 정리 (정상 경로에서는 DES가 이미 해제)
        if morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            morld.set_unit_prop(agent.unit_id, "상태:이동중", 0)

    def __repr__(self):
        return (f"<GateTransitState(lv={self.level}) → "
                f"R{self.target['region_id']}:L{self.target['location_id']}>")
