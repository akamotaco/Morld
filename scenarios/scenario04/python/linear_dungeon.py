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

# 분기 옵션 id 접두
OPTION_RETURN = "return_village"


# 마을 귀환 위치 (던전 입구 오브젝트 위치와 동일: chapter_0.py)
VILLAGE_REGION = 0
VILLAGE_LOCATION = 7
VILLAGE_X = 50


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

def generate_nodes(length: int = 5, *, branch_count: int = 1) -> list:
    """노드 그래프 생성. 메인 라인 + 사이드 분기 합류식.

    구조: 0 → 1 → 2 → ... → (length-1: EXIT)
    branch_count 만큼 메인 노드 중 일부가 BRANCH 타입이 되어, 사이드 노드 1개를
    거친 뒤 메인의 다음 노드로 다시 합류한다.

    노드 dict 필드:
      - id: int (인덱스)
      - type: str (battle/rest/branch/exit)
      - floor: int
      - paths: list[int]   (다음 노드 후보 id들. branch면 길이 ≥ 2)
      - labels: list[str]  (paths의 표시명. paths와 같은 길이)
      - side: bool         (사이드 노드 표시, 선택)
    """
    # 1. 메인 라인 생성 (길이 length, 마지막은 EXIT)
    nodes = []
    for i in range(length - 1):
        nodes.append({
            "id": i,
            "type": NODE_BATTLE if i % 2 == 0 else NODE_REST,
            "floor": i + 1,
            "paths": [i + 1],
            "labels": ["계속"],
        })
    nodes.append({
        "id": length - 1,
        "type": NODE_EXIT,
        "floor": length,
        "paths": [],
        "labels": [],
    })

    # 2. 분기 삽입: 메인 중간 노드를 BRANCH로 만들고 사이드 노드 추가
    main_count = length - 1
    if main_count >= 3 and branch_count > 0:
        # 분기 가능 위치: 1 ~ main_count-2 (양 끝 제외)
        candidates = list(range(1, main_count - 1))
        random.shuffle(candidates)
        for branch_pos in candidates[:branch_count]:
            branch_node = nodes[branch_pos]
            next_main = branch_pos + 1
            # 사이드 노드를 끝에 추가 (인덱스 = len(nodes))
            side_id = len(nodes)
            side_type = random.choice([NODE_BATTLE, NODE_REST])
            side_node = {
                "id": side_id,
                "type": side_type,
                "floor": branch_node["floor"],
                "paths": [next_main],   # 사이드도 다시 메인 합류
                "labels": ["메인 복귀"],
                "side": True,
            }
            nodes.append(side_node)
            # 메인 노드를 BRANCH로 변환
            branch_node["type"] = NODE_BRANCH
            branch_node["paths"] = [next_main, side_id]
            branch_node["labels"] = ["정면 길", "옆길"]

    return nodes


def enter(nodes: list = None, length: int = 5, *, branch_count: int = 1):
    """던전 진입 → 첫 노드 활성화."""
    reset()
    _state["nodes"] = nodes if nodes is not None else generate_nodes(length, branch_count=branch_count)
    _state["index"] = 0
    _state["active"] = True
    _log(f"[dungeon] Enter linear dungeon — {len(_state['nodes'])} nodes")
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
    """모든 파티원을 마을로 이동."""
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None

    if party is not None:
        for uid in party.get_members():
            morld.set_unit_location(uid, VILLAGE_REGION, VILLAGE_LOCATION, x=VILLAGE_X)
    elif player_id is not None:
        morld.set_unit_location(player_id, VILLAGE_REGION, VILLAGE_LOCATION, x=VILLAGE_X)

    _log(f"[dungeon] Exit to village — reason={reason}")
    reset()


# ========================================
# 내부
# ========================================

def _log(msg: str):
    _state["log"].append(msg)
    print(msg)
