# linear_dungeon.py — 일자형 던전 (파이프라인 테스트용)
#
# 구조:
#   - 노드 리스트 (battle / rest / branch / exit)
#   - 각 노드 도달 시 처리 → 분기 선택 → 다음 노드
#   - 분기는 파티 다수결 (party_vote)
#   - 항상 "마을 귀환" 선택지 포함 (후퇴 없음, 귀환은 별도 옵션)
#   - 마지막 노드 도달 or 귀환 선택 → 마을 복귀
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
OPTION_NEXT = "next"
OPTION_RETURN = "return_village"


# 마을 귀환 위치 (기본: 마을 광장 근처 구호소)
VILLAGE_REGION = 0
VILLAGE_LOCATION = 5
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

def generate_nodes(length: int = 5, *, branch_rate: float = 0.4) -> list:
    """기본 노드 시퀀스 생성.

    마지막은 EXIT로 끝남. 중간은 battle/rest/branch 중 랜덤.
    """
    nodes = []
    for i in range(length - 1):
        r = random.random()
        if r < branch_rate:
            nodes.append({"type": NODE_BRANCH, "floor": i + 1})
        elif r < branch_rate + 0.5:
            nodes.append({"type": NODE_BATTLE, "floor": i + 1})
        else:
            nodes.append({"type": NODE_REST, "floor": i + 1})
    nodes.append({"type": NODE_EXIT, "floor": length})
    return nodes


def enter(nodes: list = None, length: int = 5):
    """던전 진입 → 첫 노드 활성화."""
    reset()
    _state["nodes"] = nodes if nodes is not None else generate_nodes(length)
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


# ========================================
# 노드 처리 + 전진
# ========================================

def process_current_node(*, on_battle=None, on_rest=None):
    """현재 노드의 타입별 처리를 실행.

    on_battle/on_rest 콜백이 주어지면 호출.
    콜백이 None이면 기본 처리(default_battle/default_rest)를 시도 (의존성 import).
    EXIT/BRANCH는 여기서 처리하지 않음 (caller가 branch_decision/exit_to_village 호출).
    """
    node = get_current_node()
    if node is None:
        return None

    t = node["type"]
    if t == NODE_BATTLE:
        _log(f"[dungeon] Battle node (floor={node['floor']})")
        handler = on_battle or default_battle_handler
        handler(node)
    elif t == NODE_REST:
        _log(f"[dungeon] Rest node (floor={node['floor']})")
        handler = on_rest or default_rest_handler
        handler(node)
    elif t == NODE_BRANCH:
        _log(f"[dungeon] Branch node (floor={node['floor']})")
    elif t == NODE_EXIT:
        _log(f"[dungeon] Exit node (floor={node['floor']})")
    return node


# ========================================
# 기본 노드 핸들러
# ========================================

def default_battle_handler(node) -> dict:
    """Battle 노드: creature_pool → encounter_handler 연결.

    의존성이 테스트 환경에 없을 수 있으므로 import 실패/ 빈 데이터는 경고만."""
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
        # 피로 감소
        cur_fatigue = morld.get_unit_prop(uid, "피로:수면") or 0
        morld.set_unit_prop(uid, "피로:수면", max(0, int(cur_fatigue) - 30))
        # 체력 회복
        if survival is not None:
            cur_hp = survival.get_health(uid)
            max_hp = survival.get_max_health(uid)
            survival.set_health(uid, min(max_hp, cur_hp + 20))
    _log(f"[dungeon]   rest applied to {party.get_size()} members")


def advance_to_next():
    """비분기/비종료 노드에서 다음 노드로 단순 전진."""
    node = get_current_node()
    if node is None or node["type"] == NODE_EXIT:
        return None
    _state["index"] += 1
    return get_current_node()


# ========================================
# 분기 선택 (다수결)
# ========================================

def make_branch_decision(player_choice: str = None, npc_choice_fn=None) -> dict:
    """분기 노드에서 다수결 투표 → 결과 반영.

    옵션은 현재 고정: [OPTION_NEXT, OPTION_RETURN].
    확장 시 분기별 복수 경로 지원.

    Returns: party_vote 결과 dict + 추가 "action" 키
      action: "continue" (다음 노드) / "return" (마을 귀환)
    """
    node = get_current_node()
    if node is None or node["type"] != NODE_BRANCH:
        raise RuntimeError("not at branch node")

    import party_vote
    options = [OPTION_NEXT, OPTION_RETURN]
    # player_choice 기본값: NEXT (전진 지향)
    if player_choice is None:
        player_choice = OPTION_NEXT

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
        _state["index"] += 1
        result["action"] = "continue"

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
