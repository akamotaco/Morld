# linear_dungeon.py — 일자형 던전 (StS식 일방향 + 갈림길)
#
# 구조:
#   - 노드 그래프: 각 노드에 paths(다음 노드 인덱스 리스트) + labels(표시명)
#   - 후퇴 없음. 분기 노드에서는 "마을 귀환" 옵션 항상 추가
#   - 전투 노드는 cleared(승리)되어야 다음으로 진행 가능
#   - 노드별 처리는 외부에서 트리거 (Player 액션 → process/branch_choice)
#
# 설계: docs/design.md — 던전 2종 구성 / 일자형 던전

import random

import morld


# 노드 타입
NODE_BATTLE = "battle"
NODE_REST = "rest"
NODE_BRANCH = "branch"
NODE_EXIT = "exit"
NODE_START = "start"

# 분기 옵션 id 접두
OPTION_RETURN = "return_village"


# 마을 귀환 위치 (던전 입구 오브젝트 위치와 동일: chapter_0.py)
VILLAGE_REGION = 0
VILLAGE_LOCATION = 7
VILLAGE_X = 50

# 리니어 던전 진입 트리거 위치 (chapter_0.py의 "테스트 리니어 던전" location)
ENTRANCE_REGION = 0
ENTRANCE_LOCATION = 12


# ========================================
# 상태
# ========================================

_state = {
    "active": False,
    "nodes": [],
    "index": -1,
    "log": [],
}


def reset():
    _state["active"] = False
    _state["nodes"] = []
    _state["index"] = -1
    _state["log"] = []


# ========================================
# 던전 생성
# ========================================

def generate_nodes(depth: int = 6, *, max_width: int = 3) -> list:
    """STS 스타일 DAG 생성 (레벨 = depth, 레벨당 1~max_width개 방).

    구조:
      - Level 0: START (1방 고정)
      - Level 1 ~ depth-2: 1~max_width개 방 (랜덤 BATTLE/REST)
      - Level depth-1: EXIT (1방 고정)
      - 각 노드는 다음 레벨의 1~2개 노드로 paths 연결 (forward-only DAG)
      - NODE_BRANCH 타입은 별도 사용하지 않음 — paths 길이 ≥ 2면 자동 분기

    노드 dict 필드:
      - id: int                (global index)
      - type: start|battle|rest|exit
      - floor: int             (level = floor)
      - paths: list[int]       (다음 노드 id들)
      - labels: list[str]      (paths별 표시명 — "[전투방]" 등)
    """
    if depth < 3:
        depth = 3  # 최소: START + 1 컨텐츠 + EXIT

    # 1. 레벨별 노드 배치
    levels = []  # levels[i] = [node_id, ...]
    nodes = []

    def _new_node(type_, floor):
        nid = len(nodes)
        nodes.append({
            "id": nid,
            "type": type_,
            "floor": floor,
            "paths": [],
            "labels": [],
        })
        return nid

    # Level 0: START
    levels.append([_new_node(NODE_START, 0)])

    # Level 1 ~ depth-2: 랜덤 너비
    for lvl in range(1, depth - 1):
        width = random.randint(1, max_width)
        row = []
        for _ in range(width):
            t = random.choice([NODE_BATTLE, NODE_REST])
            row.append(_new_node(t, lvl))
        levels.append(row)

    # Level depth-1: EXIT
    levels.append([_new_node(NODE_EXIT, depth - 1)])

    # 2. 노드 간 path 연결 (forward-only, 각 노드 → 다음 레벨 1~2개)
    for lvl in range(len(levels) - 1):
        current = levels[lvl]
        next_level = levels[lvl + 1]
        next_max = min(2, len(next_level))

        # 먼저 각 노드에서 1개씩 랜덤 연결 (reachability 보장용)
        for nid in current:
            target = random.choice(next_level)
            nodes[nid]["paths"].append(target)
            # 일부 노드는 추가 path 하나 더 (branch 생성)
            if len(next_level) >= 2 and random.random() < 0.35:
                alt = random.choice([t for t in next_level if t != target])
                nodes[nid]["paths"].append(alt)

        # 모든 next-level 노드가 최소 1개 이상의 incoming을 갖도록 보강
        incoming = {nid: 0 for nid in next_level}
        for nid in current:
            for p in nodes[nid]["paths"]:
                incoming[p] = incoming.get(p, 0) + 1
        for nid in next_level:
            if incoming[nid] == 0:
                # 임의의 current 노드에 연결
                src = random.choice(current)
                if nid not in nodes[src]["paths"]:
                    nodes[src]["paths"].append(nid)

    # 3. labels 생성 (각 path의 대상 노드 타입 표시)
    type_label = {
        NODE_BATTLE: "전투방",
        NODE_REST: "휴식방",
        NODE_EXIT: "출구",
        NODE_START: "시작방",
    }
    for node in nodes:
        node["labels"] = [f"[{type_label.get(nodes[p]['type'], '?')}]" for p in node["paths"]]

    return nodes


def enter(nodes: list = None, depth: int = 6, *, max_width: int = 3):
    """던전 진입 → 첫 노드(START) 활성화."""
    reset()
    _state["nodes"] = nodes if nodes is not None else generate_nodes(depth, max_width=max_width)
    _state["index"] = 0
    _state["active"] = True
    _log(f"[dungeon] Enter linear dungeon — {len(_state['nodes'])} nodes (depth={depth})")
    return get_current_node()


def get_current_node() -> dict:
    if not _state["active"]:
        return None
    idx = _state["index"]
    if 0 <= idx < len(_state["nodes"]):
        return _state["nodes"][idx]
    return None


def is_active() -> bool:
    return _state["active"]


def get_log() -> list:
    return list(_state["log"])


def is_current_cleared() -> bool:
    """현재 노드가 진행 가능 상태인지. 전투 미해결이면 False."""
    node = get_current_node()
    if node is None:
        return False
    if node["type"] == NODE_BATTLE and not node.get("cleared"):
        return False
    return True


# ========================================
# 노드 처리
# ========================================

def process_current_node(*, on_battle=None, on_rest=None) -> dict:
    """현재 노드의 타입별 처리를 실행하고 결과 반환.

    Returns:
        {"node": dict, "result": str|None}
        result는 battle: 'victory'/'defeat'/None / rest: 'rested' / 그 외 None.
    """
    node = get_current_node()
    if node is None:
        return {"node": None, "result": None}

    t = node["type"]
    result = None

    if t == NODE_BATTLE:
        _log(f"[dungeon] Battle node (floor={node['floor']})")
        handler = on_battle or default_battle_handler
        battle_result = handler(node)
        if battle_result is not None:
            result = battle_result.get("result")
            if result == "victory":
                node["cleared"] = True
    elif t == NODE_REST:
        _log(f"[dungeon] Rest node (floor={node['floor']})")
        handler = on_rest or default_rest_handler
        handler(node)
        result = "rested"
    elif t == NODE_BRANCH:
        _log(f"[dungeon] Branch node (floor={node['floor']})")
    elif t == NODE_EXIT:
        _log(f"[dungeon] Exit node (floor={node['floor']})")

    return {"node": node, "result": result}


# ========================================
# 기본 노드 핸들러
# ========================================

def default_battle_handler(node) -> dict:
    """Battle 노드: creature_pool → encounter_handler 연결."""
    floor = node.get("floor", 1)
    try:
        import creature_pool
        import encounter_handler
    except ImportError as e:
        _log(f"[dungeon]   WARN: battle skipped — {e}")
        return None

    enemy_data = creature_pool.generate_encounter(floor)
    if not enemy_data:
        _log(f"[dungeon]   WARN: no enemy data for floor {floor}")
        return None

    result = encounter_handler.start_encounter(enemy_data)
    _log(f"[dungeon]   battle result: {result.get('result')}")
    return result


def default_rest_handler(node) -> None:
    """Rest 노드: 전 파티원 체력/피로 회복."""
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    if player_id is None:
        return
    party = _pg.get_party_of(player_id)
    if party is None:
        return

    try:
        import survival
    except ImportError:
        survival = None

    for uid in party.get_members():
        cur_fatigue = morld.get_unit_prop(uid, "피로:수면") or 0
        morld.set_unit_prop(uid, "피로:수면", max(0, int(cur_fatigue) - 30))
        if survival is not None:
            cur_hp = survival.get_health(uid)
            max_hp = survival.get_max_health(uid)
            survival.set_health(uid, min(max_hp, cur_hp + 20))
    _log(f"[dungeon]   rest applied to {party.get_size()} members")


# ========================================
# 진행
# ========================================

def advance(target_id: int) -> dict:
    """현재 노드의 paths 중 target_id로 이동.

    Battle 노드는 cleared=True여야 진행 가능.
    target_id가 paths에 없으면 차단.
    """
    node = get_current_node()
    if node is None:
        return {"ok": False, "reason": "inactive"}

    if not is_current_cleared():
        return {"ok": False, "reason": "battle_not_cleared"}

    if target_id not in node["paths"]:
        return {"ok": False, "reason": "invalid_target"}

    _state["index"] = target_id
    return {"ok": True, "node": get_current_node()}


# ========================================
# 분기 선택 (다수결)
# ========================================

def make_branch_decision(player_choice_id: int = None, npc_choice_fn=None) -> dict:
    """분기 노드에서 다수결 투표 → 결과 반영.

    Args:
        player_choice_id: 플레이어가 선택한 path 노드 id (또는 OPTION_RETURN).
                          None이면 paths의 첫 옵션 기본 선택.
        npc_choice_fn: NPC 투표 함수 (voter_id, options) -> option.

    옵션은 현재 노드의 paths + OPTION_RETURN.

    Returns: party_vote 결과 + "action": "advanced"|"return"|"blocked"
    """
    node = get_current_node()
    if node is None or node["type"] != NODE_BRANCH:
        return {"action": "blocked", "reason": "not_at_branch"}

    import party_vote
    # 옵션은 path id (str로 캐스팅) + OPTION_RETURN
    path_options = [str(p) for p in node["paths"]]
    options = path_options + [OPTION_RETURN]

    if player_choice_id is None:
        player_choice = path_options[0]
    elif player_choice_id == OPTION_RETURN:
        player_choice = OPTION_RETURN
    else:
        player_choice = str(player_choice_id)

    result = party_vote.vote_in_player_party(
        options,
        player_choice=player_choice,
        npc_choice_fn=npc_choice_fn,
    )

    winner = result["winner"]
    _log(f"[dungeon] Branch vote: {result['tallies']} → {winner}"
         + (" (tiebreak)" if result["tiebreaker"] else ""))

    if winner == OPTION_RETURN:
        exit_to_village(reason="party_vote")
        result["action"] = "return"
    else:
        # branch 노드는 즉시 통과로 간주 (전투 아님)
        _state["index"] = int(winner)
        result["action"] = "advanced"
        result["new_node"] = get_current_node()

    return result


# ========================================
# 귀환
# ========================================

def exit_to_village(reason: str = "clear"):
    """모든 파티원을 던전 입구(R0/L7)로 이동."""
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None

    reset()

    if party is not None:
        for uid in party.get_members():
            morld.set_unit_location(uid, VILLAGE_REGION, VILLAGE_LOCATION, x=VILLAGE_X)
    elif player_id is not None:
        morld.set_unit_location(player_id, VILLAGE_REGION, VILLAGE_LOCATION, x=VILLAGE_X)

    _log(f"[dungeon] Exit to village — reason={reason}")


def try_auto_enter():
    """리니어 던전 진입 location(R0/L12) on_reach 시 호출 — 비활성이면 자동 진입.

    Returns: True (진입함) / False (스킵 — 이미 활성)
    """
    if _state["active"]:
        return False
    enter(depth=6, max_width=3)
    return True


def _on_entrance_reach(unit_id, region, loc):
    """event_core에 등록되는 on_reach handler — 플레이어 진입 시 던전 시작."""
    if not try_auto_enter():
        return None
    node = get_current_node()
    _log(f"[dungeon] Auto-entered via on_reach — first node={node['type']}")
    return auto_run()


def register_location_handlers():
    """chapter load 시 호출 — 던전 진입 location의 on_reach handler 등록."""
    from engine import event_core
    event_core.subscribe_on_reach(
        ENTRANCE_REGION, ENTRANCE_LOCATION, _on_entrance_reach, player_only=True
    )


def auto_run():
    """던전 종료까지 연속 진행하는 generator.

    on_reach L12로 자동 입장 후 호출 — Player.dungeon_proceed()를 반복 실행하여
    각 노드의 dialog를 yield. 노드가 모두 소진(exit_to_village로 비활성)되면 종료.
    """
    from assets import characters
    player_id = morld.get_player_id()
    if player_id is None:
        return
    p = characters.get_instance(player_id)
    if p is None or not hasattr(p, "dungeon_proceed"):
        return

    # 무한 루프 방지 (던전 길이 + 분기 여유)
    safety = 30
    while _state["active"] and safety > 0:
        safety -= 1
        gen = p.dungeon_proceed()
        if gen is None:
            return
        for item in gen:
            yield item


# ========================================
# 내부
# ========================================

def _log(msg: str):
    _state["log"].append(msg)
    print(msg)
