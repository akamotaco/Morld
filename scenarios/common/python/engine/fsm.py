# engine/fsm.py — 스택 기반 FSM (Finite State Machine) 프레임워크
#
# NPC AI의 행동 컨텍스트를 스택으로 관리.
# - root(index 0)에 LifeState 항상 존재
# - push 시 동일 이상 레벨 자동 pop → change 동작 자연 발생
#
# Pass-Through 스택:
#   update() → True:  "처리 완료, 아래 로직 차단"
#            → False: "스택 유지 + 아래 phase로 위임 (pass-through)"
#
# 시나리오별 확장:
#   - 레벨 상수 정의 (LV_COMBAT=10 등)
#   - FSMState 서브클래스 구현 (CombatState, DungeonState 등)

import morld
import random
from collections import deque


# ============================================
# 레벨 상수 (기본)
# ============================================

LV_LIFE = 0       # 생활 (root, 불변)
LV_TRANSIT = 30   # Gate 이동
LV_HOLD = 40      # Focus 상호작용 동결 (대화/harass/romance — 최상위)


# ============================================
# FSMState 기반 클래스
# ============================================

class FSMState:
    """FSM 상태 기반 클래스"""
    state_type = "base"
    level = -1

    def enter(self, agent):
        """스택에 push될 때 호출"""
        pass

    def update(self, agent):
        """매 think() 호출 시 실행.

        Returns:
            True  = 처리 완료 (하위 로직 차단)
            False = 스택 유지 + 아래 phase로 위임 (pass-through)
        """
        return False

    def exit(self, agent):
        """스택에서 pop될 때 호출"""
        pass

    def __repr__(self):
        return "<" + self.__class__.__name__ + "(lv=" + str(self.level) + ")>"


class LifeState(FSMState):
    """생활 상태 — FSM root (항상 스택 최하단)

    update()가 항상 False를 반환하여 기존 think 로직으로 진행.
    """
    state_type = "life"
    level = LV_LIFE

    def update(self, agent):
        return False


class HoldState(FSMState):
    """Focus 상호작용 중 NPC 동결 (대화/harass/romance 등)

    스택 최상위로 push되며 update()가 항상 True를 반환.
    → 하위 FSM 및 think() 생존/스케줄 로직 전체 차단.
    enter() 시 진행 중 이동/작업을 모두 중단하여 일관된 정지 상태 보장.
    """
    state_type = "hold"
    level = LV_HOLD

    def enter(self, agent):
        # GateTransit 중이었으면 pop — 잔존 시 HoldState pop 후 재개 못 함
        agent._fsm_pop_by_type("gate_transit")
        # 진행 중 job 전부 취소 (이동/작업 중단)
        morld.clear_jobs(agent.unit_id)
        # GateTransit이 설정한 이동중 플래그 확실히 해제
        morld.set_unit_prop(agent.unit_id, "상태:이동중", 0)

    def update(self, agent):
        # 모든 하위 로직 차단 + DES 유지용 idle job 삽입
        agent._action_taken = True
        if morld.get_current_job(agent.unit_id) is None:
            agent._insert_idle_job("focus", 60_000)
        return True


# ============================================
# 경로 탐색 유틸리티
# ============================================

def find_gate_x(agent, target):
    """현재 location에서 target으로 연결되는 Gate의 x좌표 탐색.

    Args:
        agent: Agent (get_location, get_info 제공)
        target: {"region_id": int, "location_id": int}

    Returns: int (gate x좌표)
    Raises: RuntimeError (Gate 없음 — 로직 버그)
    """
    npc_name = agent.get_info().get("name", agent.unit_id)
    loc = agent.get_location()
    if not loc:
        raise RuntimeError(
            "[FSM] find_gate_x: " + str(npc_name) + " - location 없음")
    region_info = morld.get_region_info(loc[0])
    if not region_info:
        raise RuntimeError(
            "[FSM] find_gate_x: " + str(npc_name) + " - region_info 없음 (R" + str(loc[0]) + ")")
    for loc_info in region_info.get("locations", []):
        if loc_info["id"] != loc[1]:
            continue
        gates = loc_info.get("gates", [])
        for gate in gates:
            if (gate["connected_region"] == target["region_id"]
                    and gate["connected_local"] == target["location_id"]):
                return gate["x"]
        available = ["R" + str(g["connected_region"]) + ":L" + str(g["connected_local"])
                     + "(x=" + str(g["x"]) + ")" for g in gates]
        raise RuntimeError(
            "[FSM] find_gate_x: " + str(npc_name) + " - Gate 없음 (R" + str(loc[0])
            + ":L" + str(loc[1]) + " → R" + str(target["region_id"])
            + ":L" + str(target["location_id"]) + ") available=" + str(available))
    raise RuntimeError(
        "[FSM] find_gate_x: " + str(npc_name) + " - location 없음 in region_info")


def find_path(start_region, start_local, target_region, target_local):
    """BFS로 Gate 경유 최단 경로 탐색.

    Returns:
        list of {"region_id": int, "location_id": int}
        시작점 미포함, 최종 목적지 포함.

    Raises: RuntimeError (경로 없음)
    """
    start = (start_region, start_local)
    target = (target_region, target_local)
    if start == target:
        return []

    queue = deque([(start, [])])
    visited = {start}

    while queue:
        (cur_r, cur_l), path = queue.popleft()
        region_info = morld.get_region_info(cur_r)
        if not region_info:
            continue
        for loc_info in region_info.get("locations", []):
            if loc_info["id"] != cur_l:
                continue
            for gate in loc_info.get("gates", []):
                next_r = gate["connected_region"]
                next_l = gate["connected_local"]
                next_node = (next_r, next_l)
                if next_node in visited:
                    continue
                visited.add(next_node)
                hop = {"region_id": next_r, "location_id": next_l}
                new_path = path + [hop]
                if next_node == target:
                    return new_path
                queue.append((next_node, new_path))

    raise RuntimeError(
        "[FSM] find_path: 경로 없음 (R" + str(start_region) + ":L" + str(start_local)
        + " → R" + str(target_region) + ":L" + str(target_local) + ")")


# ============================================
# GateTransitState — cross-location 이동
# ============================================

class GateTransitState(FSMState):
    """Gate Transit — cross-location 이동 (multi-hop BFS)

    첫 hop: approaching(Gate까지 이동) → transiting(텔레포트)
    중간 hop: transiting만 (숨김)
    최종 hop: 도착 → pop
    """
    state_type = "gate_transit"
    level = LV_TRANSIT

    def __init__(self, target, name="이동"):
        self.target = target
        self.name = name
        self.hops = []
        self.hop_index = 0
        self.stage = None

    def enter(self, agent):
        npc_name = agent.get_info().get("name", agent.unit_id)
        loc = agent.get_location()

        # 행동 로그
        player_id = morld.get_player_id()
        player_loc = morld.get_unit_location(player_id) if player_id else None
        if player_loc and loc and player_loc[0] == loc[0] and player_loc[1] == loc[1]:
            dest_info = morld.get_location_info(
                self.target["region_id"], self.target["location_id"])
            dest_name = dest_info["name"] if dest_info else "알 수 없는 곳"
            try:
                morld.add_action_log(str(npc_name) + "이(가) " + dest_name + "(으)로 이동을 시작했다.")
            except (AttributeError, Exception):
                pass

        self.hops = find_path(
            loc[0], loc[1],
            self.target["region_id"], self.target["location_id"])

        if not self.hops:
            print("[FSM] " + str(npc_name) + ": GateTransit - 이미 목적지")
            agent._fsm_pop()
            return

        hop_strs = ["R" + str(h["region_id"]) + ":L" + str(h["location_id"]) for h in self.hops]
        print("[FSM] " + str(npc_name) + ": GateTransit 경로 = R" + str(loc[0])
              + ":L" + str(loc[1]) + " → " + " → ".join(hop_strs))

        self._start_approaching(agent)

    def update(self, agent):
        if self.stage == "approaching":
            job = morld.get_current_job(agent.unit_id)
            if job is None or job.get("action") != "move":
                self._start_transiting(agent)
                agent._action_taken = True
                return True
            agent._action_taken = True
            return True

        # transiting
        if not morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            self.hop_index += 1
            if self.hop_index < len(self.hops):
                self._start_transiting(agent)
                agent._action_taken = True
                return True
            # 최종 도착
            npc_name = agent.get_info().get("name", agent.unit_id)
            print("[FSM] " + str(npc_name) + ": GateTransit 도착 → POP")

            # 도착 로그
            player_id = morld.get_player_id()
            player_loc = morld.get_unit_location(player_id) if player_id else None
            loc = agent.get_location()
            if player_loc and loc and player_loc[0] == loc[0] and player_loc[1] == loc[1]:
                loc_info = morld.get_location_info(loc[0], loc[1])
                loc_name = loc_info["name"] if loc_info else "이곳"
                try:
                    morld.add_action_log(str(npc_name) + "이(가) " + loc_name + "에 도착했다.")
                except (AttributeError, Exception):
                    pass

            agent._fsm_pop()
            return False
        agent._action_taken = True
        return True

    def _start_approaching(self, agent):
        npc_name = agent.get_info().get("name", agent.unit_id)
        hop = self.hops[self.hop_index]
        gate_x = find_gate_x(agent, hop)
        self.stage = "approaching"

        loc = agent.get_location()
        morld.insert_job(agent.unit_id, {
            "name": self.name,
            "action": "move",
            "region_id": loc[0],
            "location_id": loc[1],
            "target_x": gate_x,
            "duration": 0,
        })
        print("[FSM] " + str(npc_name) + ": GateTransit approaching → R"
              + str(hop["region_id"]) + ":L" + str(hop["location_id"])
              + " gate_x=" + str(gate_x))
        agent._action_taken = True

    def _start_transiting(self, agent):
        npc_name = agent.get_info().get("name", agent.unit_id)
        self.stage = "transiting"
        morld.set_unit_prop(agent.unit_id, "상태:이동중", 1)

        hop = self.hops[self.hop_index]
        is_final = (self.hop_index == len(self.hops) - 1)

        if is_final:
            target_x = self.target.get("x", 0)
            length = int(self.target.get("length", 0))
        else:
            target_x = 0
            length = 0

        if length > 0 and target_x == 0:
            target_x = random.randint(0, length)

        morld.insert_job(agent.unit_id, {
            "name": self.name,
            "action": "move",
            "region_id": hop["region_id"],
            "location_id": hop["location_id"],
            "target_x": target_x,
            "duration": 0,
        })
        is_final_str = " (최종)" if is_final else ""
        print("[FSM] " + str(npc_name) + ": GateTransit transiting → R"
              + str(hop["region_id"]) + ":L" + str(hop["location_id"]) + is_final_str)

    def exit(self, agent):
        if morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            morld.set_unit_prop(agent.unit_id, "상태:이동중", 0)

    def __repr__(self):
        hop_info = ("hop " + str(self.hop_index + 1) + "/" + str(len(self.hops))
                    if self.hops else "no path")
        return ("<GateTransitState(lv=" + str(self.level) + ", stage=" + str(self.stage)
                + ", " + hop_info + ") -> R" + str(self.target["region_id"])
                + ":L" + str(self.target["location_id"]) + ">")


def reset():
    """모듈 상태 초기화 — pi-world reset 계약 (가변 전역 없음, 규약 준수용)"""
    pass
