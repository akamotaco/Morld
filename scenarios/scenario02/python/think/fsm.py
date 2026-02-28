# think/fsm.py  - 스택 기반 FSM (Finite State Machine)
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
# 구현 상태:
#   LifeState (root) + GateTransitState (multi-hop)
#   CombatState + FleeState + ResignationState + DesperateState

import morld
import random
from collections import deque

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
    """생활 상태  - FSM root (항상 스택 최하단)

    update()가 항상 False를 반환하여 기존 5-tier think() 로직으로 진행.
    """
    state_type = "life"
    level = LV_LIFE

    def update(self, agent) -> bool:
        return False  # 항상 Life 로직(5-tier)으로 진행


# ── 경로 탐색 ──────────────────────────────────────────────

def _find_gate_x(agent, target):
    """현재 location에서 target으로 연결되는 Gate의 x좌표 탐색.

    Gate가 없으면 RuntimeError (로직 버그).
    """
    npc_name = agent.get_info().get("name", agent.unit_id)
    loc = agent.get_location()
    if not loc:
        raise RuntimeError(
            f"[FSM] _find_gate_x: {npc_name}  - location 없음")
    region_info = morld.get_region_info(loc[0])
    if not region_info:
        raise RuntimeError(
            f"[FSM] _find_gate_x: {npc_name}  - region_info 없음 "
            f"(R{loc[0]})")
    for loc_info in region_info.get("locations", []):
        if loc_info["id"] != loc[1]:
            continue
        gates = loc_info.get("gates", [])
        for gate in gates:
            if (gate["connected_region"] == target["region_id"]
                    and gate["connected_local"] == target["location_id"]):
                return gate["x"]
        # location은 찾았지만 target으로의 gate 없음
        available = [f"R{g['connected_region']}:L{g['connected_local']}(x={g['x']})"
                     for g in gates]
        raise RuntimeError(
            f"[FSM] _find_gate_x: {npc_name}  - Gate 없음 "
            f"(R{loc[0]}:L{loc[1]} → R{target['region_id']}:L{target['location_id']}) "
            f"available_gates={available}")
    # location 자체를 못 찾음
    raise RuntimeError(
        f"[FSM] _find_gate_x: {npc_name}  - location 없음 in region_info "
        f"(R{loc[0]}:L{loc[1]})")


def _find_path(start_region, start_local, target_region, target_local):
    """BFS로 Gate 경유 최단 경로 탐색.

    Returns:
        list of {"region_id": int, "location_id": int}
        시작점 미포함, 최종 목적지 포함.
        예: R2:L5 → R2:L3 → R2:L0 이면 [R2:L3, R2:L0] 반환.

    Raises:
        RuntimeError: 경로 없음 (Gate 미연결).
    """
    start = (start_region, start_local)
    target = (target_region, target_local)
    if start == target:
        return []

    # BFS
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
        f"[FSM] _find_path: 경로 없음 "
        f"(R{start_region}:L{start_local} → "
        f"R{target_region}:L{target_local})")


# ── GateTransitState ───────────────────────────────────────

class GateTransitState(FSMState):
    """Gate Transit  - cross-location 이동 (multi-hop)

    BFS로 경로를 탐색하여 여러 location을 경유 가능.

    첫 번째 hop:
      approaching  - Gate x좌표로 같은 location 내 이동 (보임)
      transiting   - 상태:이동중=1 + cross-location move job (숨김)

    중간 hop (2번째~):
      transiting만  - 숨김 상태 유지, 즉시 텔레포트

    최종 hop 도착:
      상태:이동중=0 감지 → POP → Life 로직 진행
    """
    state_type = "gate_transit"
    level = LV_TRANSIT

    def __init__(self, target, name="이동"):
        self.target = target    # 최종 목적지 (x/length 포함)
        self.name = name
        self.hops = []          # enter()에서 BFS 계산
        self.hop_index = 0
        self.stage = None       # "approaching" / "transiting"

    def enter(self, agent):
        npc_name = agent.get_info().get("name", agent.unit_id)
        loc = agent.get_location()

        # 행동 로그: 플레이어와 같은 location일 때만 (목격)
        player_id = morld.get_player_id()
        player_loc = morld.get_unit_location(player_id) if player_id else None
        if player_loc and loc and player_loc[0] == loc[0] and player_loc[1] == loc[1]:
            dest_info = morld.get_location_info(
                self.target["region_id"], self.target["location_id"])
            dest_name = dest_info["name"] if dest_info else "알 수 없는 곳"
            morld.add_action_log(f"{npc_name}이(가) {dest_name}(으)로 이동을 시작했다.")

        # BFS 경로 탐색
        self.hops = _find_path(
            loc[0], loc[1],
            self.target["region_id"], self.target["location_id"])

        if not self.hops:
            # 이미 목적지 (cross-location 체크에서 걸러져야 하지만 안전장치)
            print(f"[FSM] {npc_name}: GateTransit - 이미 목적지")
            agent._fsm_pop()
            return

        hop_strs = [f"R{h['region_id']}:L{h['location_id']}" for h in self.hops]
        print(f"[FSM] {npc_name}: GateTransit 경로 = "
              f"R{loc[0]}:L{loc[1]} → {' → '.join(hop_strs)}")

        # 첫 hop: Gate까지 걸어가기 (approaching)
        self._start_approaching(agent)

    def update(self, agent) -> bool:
        if self.stage == "approaching":
            job = morld.get_current_job(agent.unit_id)
            if job is None or job.get("action") != "move":
                # Gate 도달 → transiting 전환
                self._start_transiting(agent)
                agent._action_taken = True
                return True
            # Gate로 이동 중 → job 보존
            agent._action_taken = True
            return True

        # stage == "transiting"
        if not morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            # 현재 hop 도착
            self.hop_index += 1
            if self.hop_index < len(self.hops):
                # 중간 경유지 → 숨김 유지, 다음 hop 즉시 transit
                self._start_transiting(agent)
                agent._action_taken = True
                return True
            # 최종 도착 → 행동 로그 + POP
            npc_name = agent.get_info().get("name", agent.unit_id)
            print(f"[FSM] {npc_name}: GateTransit 도착 → POP")

            # 도착 로그: 플레이어와 같은 location일 때 (목격)
            player_id = morld.get_player_id()
            player_loc = (morld.get_unit_location(player_id)
                          if player_id else None)
            loc = agent.get_location()
            if (player_loc and loc
                    and player_loc[0] == loc[0]
                    and player_loc[1] == loc[1]):
                loc_info = morld.get_location_info(loc[0], loc[1])
                loc_name = loc_info["name"] if loc_info else "이곳"
                morld.add_action_log(
                    f"{npc_name}이(가) {loc_name}에 도착했다.")

            agent._fsm_pop()
            return False  # Life 로직 진행
        # transit 중 → job 보존
        agent._action_taken = True
        return True

    def _start_approaching(self, agent):
        """현재 location에서 첫 hop Gate x좌표로 이동 (가시적)"""
        npc_name = agent.get_info().get("name", agent.unit_id)
        hop = self.hops[self.hop_index]
        gate_x = _find_gate_x(agent, hop)
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
        print(f"[FSM] {npc_name}: GateTransit approaching → "
              f"R{hop['region_id']}:L{hop['location_id']} gate_x={gate_x}")
        agent._action_taken = True

    def _start_transiting(self, agent):
        """cross-location 텔레포트 (숨김)"""
        npc_name = agent.get_info().get("name", agent.unit_id)
        self.stage = "transiting"
        morld.set_unit_prop(agent.unit_id, "상태:이동중", 1)

        hop = self.hops[self.hop_index]
        is_final = (self.hop_index == len(self.hops) - 1)

        if is_final:
            # 최종 목적지: target의 x/length 사용
            target_x = self.target.get("x", 0)
            length = int(self.target.get("length", 0))
        else:
            # 중간 경유지: 정확한 위치 불필요 (숨김 상태)
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
        print(f"[FSM] {npc_name}: GateTransit transiting → "
              f"R{hop['region_id']}:L{hop['location_id']}"
              f"{' (최종)' if is_final else ''}")

    def exit(self, agent):
        # 안전장치: prop 정리 (정상 경로에서는 DES가 이미 해제)
        if morld.get_unit_prop(agent.unit_id, "상태:이동중"):
            morld.set_unit_prop(agent.unit_id, "상태:이동중", 0)

    def __repr__(self):
        hop_info = (f"hop {self.hop_index + 1}/{len(self.hops)}"
                    if self.hops else "no path")
        return (f"<GateTransitState(lv={self.level}, stage={self.stage}, "
                f"{hop_info}) -> "
                f"R{self.target['region_id']}:L{self.target['location_id']}>")


# -- CombatState -----------------------------------------------

def _log_fsm(tag, agent, detail, phase=None):
    """FSM 디버그 로그 (전투 계열 공용)"""
    info = morld.get_unit_info(agent.unit_id)
    name = info.get("name", "?") if info else "?"
    phase_str = f" phase={phase}" if phase else ""
    print(f"[{tag}] {name}(id={agent.unit_id}){phase_str} | {detail}")


def _check_incapacitated(agent):
    """기절/탈진/사망 체크. 해당 시 idle job 삽입 + True 반환.

    Returns:
        "dead"      - 사망 (호출자가 pop 해야 함)
        "fainted"   - 기절 (idle job 삽입됨)
        "exhausted" - 탈진 (idle job 삽입됨)
        None        - 정상
    """
    import survival as _surv

    if morld.get_unit_prop(agent.unit_id, "상태:사망"):
        return "dead"
    if _surv.is_npc_fainted(agent.unit_id):
        remain = _surv.get_faint_remaining_millis(agent.unit_id)
        agent._insert_idle_job("기절", max(remain, 1_000))
        agent._action_taken = True
        return "fainted"
    if _surv.is_npc_exhausted(agent.unit_id):
        remain = _surv.get_exhaustion_remaining_millis(agent.unit_id)
        agent._insert_idle_job("탈진", max(remain, 1_000))
        agent._action_taken = True
        return "exhausted"
    return None


class CombatState(FSMState):
    """전투 상태 - engaging/attacking

    스택 위치: [LifeState, CombatState]
    하위 State: FleeState, ResignationState, DesperateState (LV_COMBAT_SUB)
    """
    state_type = "combat"
    level = LV_COMBAT

    def __init__(self, target_id):
        self.target_id = target_id
        self.phase = "engaging"   # engaging / attacking
        self.last_enemy_ms = 0
        self.discovered = False

    def enter(self, agent):
        import combat as _combat
        self.last_enemy_ms = agent.get_time()
        if not self.discovered:
            _combat._emit_combat_line(agent.unit_id, "discover")
            self.discovered = True
        _log_fsm("combat", agent, "전투 개시", self.phase)

    def update(self, agent) -> bool:
        import combat as _combat
        import survival as _surv

        # 기절/탈진/사망 처리
        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True  # 기절/탈진 - 전투 유지, 대기

        behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})

        # 대상 유효성 검증 -> 무효 시 새 적 탐색
        if self.target_id and not agent._is_valid_combat_target(self.target_id):
            self.target_id = None
        if not self.target_id:
            self.target_id = agent._scan_nearest_enemy()
        if self.target_id:
            self.last_enemy_ms = agent.get_time()

        # 적 없음 -> 전투 종료 판정
        if not self.target_id:
            if agent._should_end_combat(self.last_enemy_ms):
                _log_fsm("combat", agent, "전투 종료 (3-조건 충족)", self.phase)
                agent._fsm_pop()
                agent._insert_idle_job("전투 종료", 2_000)
                agent._action_taken = True
                return False
            agent._insert_idle_job("경계", 5_000)
            agent._action_taken = True
            return True

        # HP 기반 후퇴 -> FleeState push
        style = behavior.get("combat_style", "aggressive")
        if style != "aggressive":
            threshold = behavior.get("retreat_threshold", 0.2)
            my_hp = _surv.get_health(agent.unit_id)
            my_max = _surv.get_max_health(agent.unit_id)
            if my_hp <= my_max * threshold:
                _combat._emit_combat_line(agent.unit_id, "flee")
                _log_fsm("combat", agent,
                         "HP 기반 후퇴 -> FleeState push", self.phase)
                agent._fsm_push(FleeState())
                agent._action_taken = True
                return True

        # -- engaging: 사거리 접근 --
        if self.phase == "engaging":
            if _combat.is_in_range(agent.unit_id, self.target_id):
                self.phase = "attacking"
                _log_fsm("combat", agent, "사거리 진입 -> attacking", self.phase)
                # fall through to attacking
            else:
                target_loc = morld.get_unit_location(self.target_id)
                if target_loc:
                    target_info = agent._make_location_target(
                        target_loc[0], target_loc[1])
                    if target_info:
                        agent._move_to(target_info, "교전")
                    else:
                        agent._insert_idle_job("대상 이탈", 2_000)
                else:
                    agent._insert_idle_job("대상 이탈", 2_000)
                agent._action_taken = True
                return True

        # -- attacking: 공격 실행 --
        if self.phase == "attacking":
            # 사거리 이탈 -> engaging 전환
            if not _combat.is_in_range(agent.unit_id, self.target_id):
                self.phase = "engaging"
                _log_fsm("combat", agent,
                         "사거리 이탈 -> engaging", self.phase)
                return self.update(agent)

            result = _combat.execute_attack(agent.unit_id, self.target_id)
            if result.get("message"):
                morld.add_action_log(result["message"])

            if result.get("target_fainted"):
                if agent._should_end_combat(self.last_enemy_ms):
                    _log_fsm("combat", agent,
                             "전투 승리 (3-조건 충족)", self.phase)
                    agent._fsm_pop()
                    agent._insert_idle_job("전투 승리", 3_000)
                    agent._action_taken = True
                    return False
                agent._insert_idle_job("경계", 5_000)
            else:
                speed = (_combat.get_combat_stat(
                    agent.unit_id, "전투:공격속도") or 1.0)
                duration = int(agent.COMBAT_ATTACK_DURATION / speed)
                agent._insert_idle_job("공격", max(1_000, duration))
            agent._action_taken = True
            return True

        return True

    def exit(self, agent):
        _log_fsm("combat", agent, "전투 상태 초기화", self.phase)

    def __repr__(self):
        return (f"<CombatState(lv={self.level}, phase={self.phase}, "
                f"target={self.target_id})>")


# -- FleeState -------------------------------------------------

class FleeState(FSMState):
    """도주 상태 - 안전 구역 이동 + 정비

    스택 위치: [LifeState, CombatState, FleeState]
    pop 후 CombatState로 복귀 (re-engage 또는 전투 종료)
    포위 시 ResignationState/DesperateState push (동일 레벨 -> FleeState auto-pop)
    """
    state_type = "flee"
    level = LV_COMBAT_SUB

    def __init__(self):
        self.flee_target = None
        self.phase = "fleeing"   # fleeing / regrouping

    def enter(self, agent):
        _log_fsm("flee", agent, "도주 개시", self.phase)

    def update(self, agent) -> bool:
        import combat as _combat
        import survival as _surv

        # 기절/탈진 -> 대기 (도주 상태 유지)
        status = _check_incapacitated(agent)
        if status == "dead":
            # 사망 -> 도주 해제, CombatState도 곧 해제됨
            agent._fsm_pop()
            return False
        if status:
            return True

        if self.phase == "fleeing":
            return self._update_fleeing(agent, _combat, _surv)

        if self.phase == "regrouping":
            return self._update_regrouping(agent, _combat, _surv)

        return True

    def _update_fleeing(self, agent, _combat, _surv):
        """도주 이동 처리"""
        if not self.flee_target:
            self.flee_target = agent._pick_safe_location()
            if self.flee_target:
                _log_fsm("flee", agent,
                         f"도주 목적지: R{self.flee_target['region_id']}"
                         f"L{self.flee_target['location_id']}", self.phase)
            else:
                # 안전 구역 없음
                if agent._is_surrounded():
                    self._resolve_surrounded(agent)
                else:
                    _log_fsm("flee", agent,
                             "안전 구역 없음 -> 강제 전투", self.phase)
                    agent._fsm_pop()  # FleeState pop
                    top = agent._fsm_top()
                    if hasattr(top, 'phase'):
                        top.phase = "attacking"
                    agent._insert_idle_job("후퇴 실패", 2_000)
                    agent._action_taken = True
                return True  # push/pop 완료

        # 도착 확인
        my_loc = agent.get_location()
        at_target = (my_loc
                     and my_loc[0] == self.flee_target["region_id"]
                     and my_loc[1] == self.flee_target["location_id"])

        if at_target:
            # 도착했는데 적이 있으면 포위 판정
            if _combat.has_enemies_at_location(
                    agent.unit_id, my_loc[0], my_loc[1]):
                if agent._is_surrounded():
                    self._resolve_surrounded(agent)
                    return True
                # 다른 안전 구역 재탐색
                self.flee_target = None
                _log_fsm("flee", agent,
                         "도착지에 적 -> 재탐색", self.phase)
                agent._insert_idle_job("후퇴", 2_000)
                agent._action_taken = True
                return True

            # 안전 도착 -> regrouping
            self.phase = "regrouping"
            _log_fsm("flee", agent, "안전 구역 도착 -> 정비", self.phase)
            return self._update_regrouping(agent, _combat, _surv)

        # 이동 중
        agent._move_to(self.flee_target, "후퇴")
        agent._action_taken = True
        return True

    def _update_regrouping(self, agent, _combat, _surv):
        """정비 (HP 회복 대기)"""
        behavior = getattr(agent, 'BATTLE_BEHAVIOR', {})
        style = behavior.get("combat_style", "aggressive")

        # 적 재감지 (aggressive/defensive -> re-engage, evasive -> 무시)
        enemy_id = agent._scan_nearest_enemy()
        if enemy_id and style != "evasive":
            _log_fsm("flee", agent, "적 재감지 -> re-engage", self.phase)
            agent._fsm_pop()  # FleeState pop
            top = agent._fsm_top()
            if hasattr(top, 'target_id'):
                top.target_id = enemy_id
                top.phase = "engaging"
            return False

        # HP 회복 완료 판정
        my_hp = _surv.get_health(agent.unit_id)
        my_max = _surv.get_max_health(agent.unit_id)
        if my_hp >= my_max * agent.COMBAT_REGROUP_HP_THRESHOLD:
            _log_fsm("flee", agent, "정비 완료 (HP 회복) -> pop", self.phase)
            agent._fsm_pop()
            return False  # CombatState로 복귀

        agent._insert_idle_job("정비", 30_000)
        agent._action_taken = True
        return True

    def _resolve_surrounded(self, agent):
        """포위 시 체념/필사 결정

        ResignationState/DesperateState는 동일 레벨(LV_COMBAT_SUB=20)이므로
        push 시 FleeState가 auto-pop됨.
        """
        if random.random() < agent.COMBAT_DESPERATE_CHANCE:
            _log_fsm("flee", agent, "포위 -> 필사의 저항", self.phase)
            agent._fsm_push(DesperateState())
        else:
            _log_fsm("flee", agent, "포위 -> 체념", self.phase)
            agent._fsm_push(ResignationState())
        agent._action_taken = True

    def exit(self, agent):
        _log_fsm("flee", agent, "도주 종료", self.phase)

    def __repr__(self):
        return (f"<FleeState(lv={self.level}, phase={self.phase}, "
                f"target={self.flee_target})>")


# -- ResignationState -------------------------------------------

class ResignationState(FSMState):
    """체념 - 반격/이동 불가, 적 전멸 시 pop

    pop 후 CombatState가 전투 종료 판정을 수행.
    """
    state_type = "resignation"
    level = LV_COMBAT_SUB

    def enter(self, agent):
        _log_fsm("resignation", agent, "체념 시작")

    def update(self, agent) -> bool:
        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        # 적 전멸 체크
        enemy_id = agent._scan_nearest_enemy()
        if enemy_id is None:
            _log_fsm("resignation", agent, "적 전멸 -> pop")
            agent._fsm_pop()
            return False  # CombatState로 복귀
        agent._insert_idle_job("체념", 10_000)
        agent._action_taken = True
        return True

    def exit(self, agent):
        _log_fsm("resignation", agent, "체념 종료")

    def __repr__(self):
        return f"<ResignationState(lv={self.level})>"


# -- DesperateState ---------------------------------------------

class DesperateState(FSMState):
    """필사의 저항 - 도주 불가, 적에게 공격 지속

    pop 후 CombatState가 전투 종료 판정을 수행.
    """
    state_type = "desperate"
    level = LV_COMBAT_SUB

    def __init__(self):
        self.target_id = None

    def enter(self, agent):
        _log_fsm("desperate", agent, "필사의 저항 시작")

    def update(self, agent) -> bool:
        import combat as _combat

        status = _check_incapacitated(agent)
        if status == "dead":
            agent._fsm_pop()
            return False
        if status:
            return True

        # 대상 유효성 -> 무효 시 새 적 탐색
        if self.target_id and not agent._is_valid_combat_target(self.target_id):
            self.target_id = None
        if not self.target_id:
            self.target_id = agent._scan_nearest_enemy()
        if not self.target_id:
            _log_fsm("desperate", agent, "적 전멸 -> pop")
            agent._fsm_pop()
            return False

        result = _combat.execute_attack(agent.unit_id, self.target_id)
        if result.get("message"):
            morld.add_action_log(result["message"])
        speed = (_combat.get_combat_stat(
            agent.unit_id, "전투:공격속도") or 1.0)
        duration = int(agent.COMBAT_ATTACK_DURATION / speed)
        agent._insert_idle_job("필사", max(1_000, duration))
        agent._action_taken = True
        return True

    def exit(self, agent):
        _log_fsm("desperate", agent, "필사의 저항 종료")

    def __repr__(self):
        return f"<DesperateState(lv={self.level}, target={self.target_id})>"
