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
NODE_ELITE = "elite"       # 강력한 적
NODE_CAMP = "camp"         # 긴 휴식
NODE_TREASURE = "treasure" # 보물방 (현재는 빈 처리, 향후 보상)
NODE_EVENT = "event"       # 이벤트방 (현재는 빈 처리, 향후 이벤트 트리거)
NODE_EMPTY = "empty"       # 빈 방 (이벤트 없음)
NODE_UNKNOWN = "unknown"   # 미지의 방 (진입 시 랜덤 공개)
NODE_BOSS = "boss"         # 보스방 (중간/최종 겸용 — boss_config로 구분)

# 컨텐츠 노드 타입 분포 (generate_nodes의 가중 랜덤)
# STS 참고: Monster ~45%, Event ~22%, Elite ~16%, Rest ~12%, Shop ~3%
_CONTENT_TYPE_WEIGHTS = [
    (NODE_BATTLE, 40),
    (NODE_REST, 12),
    (NODE_ELITE, 8),
    (NODE_CAMP, 5),
    (NODE_TREASURE, 8),
    (NODE_EVENT, 10),
    (NODE_EMPTY, 7),
    (NODE_UNKNOWN, 10),
]

# UNKNOWN 공개 시 실제로 바뀔 수 있는 타입 풀 (UNKNOWN/START/EXIT 제외)
_UNKNOWN_REVEAL_WEIGHTS = [
    (NODE_BATTLE, 40),
    (NODE_REST, 12),
    (NODE_ELITE, 8),
    (NODE_CAMP, 5),
    (NODE_TREASURE, 10),
    (NODE_EVENT, 15),
    (NODE_EMPTY, 10),
]

# 노드별 소모 시간 (ms) — 수정 가능
_MS_MIN = 60_000
_MS_HOUR = 3_600_000
NODE_TIME_COST = {
    NODE_BATTLE:   15 * _MS_MIN,
    NODE_ELITE:    30 * _MS_MIN,
    NODE_BOSS:     60 * _MS_MIN,
    NODE_REST:     2 * _MS_HOUR,
    NODE_CAMP:     8 * _MS_HOUR,
    NODE_TREASURE: 10 * _MS_MIN,
    NODE_EVENT:    10 * _MS_MIN,
    NODE_EMPTY:    10 * _MS_MIN,
    NODE_UNKNOWN:  0,  # 공개 후 실제 타입으로 소모됨
    NODE_START:    0,
    NODE_EXIT:     0,
    NODE_BRANCH:   0,
}

# 방 타입 → 라벨 매핑 (UI 표시용)
NODE_LABELS = {
    NODE_BATTLE:   "전투방",
    NODE_REST:     "휴식방",
    NODE_ELITE:    "엘리트 전투방",
    NODE_BOSS:     "보스방",
    NODE_CAMP:     "캠프",
    NODE_TREASURE: "보물방",
    NODE_EVENT:    "이벤트방",
    NODE_EMPTY:    "빈방",
    NODE_UNKNOWN:  "???",
    NODE_EXIT:     "출구",
    NODE_START:    "시작방",
}

# 방 타입 → family (인접 제약용)
# STS 참고:
#   - rest(REST/CAMP): 같은 family 연속 금지
#   - event(TREASURE/EVENT/EMPTY): 같은 family 연속 금지
#   - elite: 자기 자신과만 연속 금지 (type-level, combat family BATTLE은 자유)
#   - combat(BATTLE): 제약 없음 → 전투 클러스터 허용
NODE_FAMILIES = {
    NODE_BATTLE:   "combat",
    NODE_ELITE:    "combat",
    NODE_BOSS:     "combat",
    NODE_REST:     "rest",
    NODE_CAMP:     "rest",
    NODE_TREASURE: "event",
    NODE_EVENT:    "event",
    NODE_EMPTY:    "event",
    NODE_UNKNOWN:  "unknown",
}

# 연속 배치 금지 family — 자기 family가 부모 family에 있으면 재롤
_NO_CONSECUTIVE_FAMILIES = {"rest", "event"}

# 연속 배치 금지 type — 자기 type이 부모 type들에 있으면 재롤 (family 무관)
_NO_CONSECUTIVE_TYPES = {NODE_ELITE}

# 분기 옵션 id 접두
OPTION_RETURN = "return_village"


# 마을 귀환 위치 (던전 입구 오브젝트 위치와 동일: chapter_0.py)
VILLAGE_REGION = 0
VILLAGE_LOCATION = 7
VILLAGE_X = 50

# 리니어 던전 전용 영구 Region (chapter init 시 1회 생성, 던전 수명과 무관하게 유지)
# 마을(R0)과 감각 격리 + Region 객체 누수 방지 (remove_region API 없음)
DUNGEON_REGION_ID = 200
_region_initialized = False

# 퀘스트별 진입점 Location (영구 생성, R200 내 고정 ID — 동적 노드는 id 0~N)
# quest_board의 _QUEST_LOCATIONS와 loc_id 동기화 필수.
ENTRANCE_LOCATIONS = [
    # (loc_id, name, length)
    (1000, "동굴 입구",         150),  # cave
    (1001, "깊은 동굴 입구",    150),  # deep
    (1002, "수호수 둥지 입구",  200),  # guardian
]
_ENTRANCE_LOC_IDS = {loc_id for (loc_id, _, _) in ENTRANCE_LOCATIONS}

# 노드 타입별 Location 길이
_NODE_LENGTH = {
    NODE_START: 100,
    NODE_BATTLE: 300,
    NODE_ELITE: 300,
    NODE_BOSS: 400,
    NODE_REST: 150,
    NODE_CAMP: 200,
    NODE_TREASURE: 150,
    NODE_EVENT: 150,
    NODE_EMPTY: 100,
    NODE_UNKNOWN: 150,
    NODE_EXIT: 100,
}


# ========================================
# 상태
# ========================================

_state = {
    "active": False,
    "nodes": [],
    "index": -1,
    "log": [],
    "region_id": None,        # 사실상 DUNGEON_REGION_ID 고정
    "floors_config": [],      # [{"depth", "max_width", "boss"}, ...]
    "floor_index": 0,         # 현재 층 (0-indexed)
    "location_ids": [],       # 현재 활성 Location ID들 (cleanup 대상)
}


def reset():
    was_active = _state["active"]

    # 던전 활성 중이면 먼저 Location 정리 (Gate 자동 정리)
    if was_active:
        clear_floor_locations()

    _state["active"] = False
    _state["nodes"] = []
    _state["index"] = -1
    _state["log"] = []
    _state["region_id"] = None
    _state["floors_config"] = []
    _state["floor_index"] = 0
    _state["location_ids"] = []

    # 던전 퇴장: 파티 이탈 잠금 해제 + DungeonState pop
    if was_active:
        player_id = morld.get_player_id()
        if player_id is not None:
            morld.modify_prop(player_id, "can:dismiss_from_party", 1)
        _pop_dungeon_state_from_party()


# ========================================
# FSM: 파티원 DungeonState 관리
# ========================================

def _move_party_to_node(region_id, node_id):
    """파티 전원을 던전 Region 내 특정 노드(Location)로 이동"""
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is not None:
        for uid in party.get_members():
            morld.set_unit_location(uid, region_id, node_id, x=10)
    elif player_id is not None:
        morld.set_unit_location(player_id, region_id, node_id, x=10)


def _push_dungeon_state_to_party():
    """파티원 NPC에 DungeonState push (Agent 등록된 경우에만)"""
    from engine import think as _think
    from engine import party_group as _pg
    from engine.fsm_dungeon import DungeonState

    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is None:
        return
    for uid in party.get_members():
        if uid == player_id:
            continue
        agent = _think.get_agent(uid)
        if agent and hasattr(agent, '_fsm_push'):
            agent._fsm_push(DungeonState())


def _switch_party_to_explore():
    """파티원 NPC를 DungeonExploreState로 전환 (이동/탐색 구간)"""
    from engine import think as _think
    from engine import party_group as _pg
    from engine.fsm_dungeon import DungeonExploreState

    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is None:
        return
    for uid in party.get_members():
        if uid == player_id:
            continue
        agent = _think.get_agent(uid)
        if agent and hasattr(agent, '_fsm_push'):
            # DungeonExploreState(lv=6) push → 기존 DungeonState(lv=8)가 있으면 유지
            # (레벨이 낮으므로 auto-pop 안 됨, 스택에 공존)
            # 먼저 기존 dungeon 상태를 정리하고 explore로 교체
            agent._fsm_pop_by_type("dungeon")
            agent._fsm_pop_by_type("dungeon_explore")
            agent._fsm_push(DungeonExploreState())


def _switch_party_to_dungeon():
    """파티원 NPC를 DungeonState로 전환 (이벤트 처리 구간)"""
    from engine import think as _think
    from engine import party_group as _pg
    from engine.fsm_dungeon import DungeonState

    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is None:
        return
    for uid in party.get_members():
        if uid == player_id:
            continue
        agent = _think.get_agent(uid)
        if agent and hasattr(agent, '_fsm_push'):
            agent._fsm_pop_by_type("dungeon_explore")
            agent._fsm_pop_by_type("dungeon")
            agent._fsm_push(DungeonState())


def _pop_dungeon_state_from_party():
    """파티원 NPC에서 던전 관련 State 모두 pop"""
    from engine import think as _think
    from engine import party_group as _pg

    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is None:
        return
    for uid in party.get_members():
        if uid == player_id:
            continue
        agent = _think.get_agent(uid)
        if agent and hasattr(agent, '_fsm_pop_by_type'):
            agent._fsm_pop_by_type("dungeon")
            agent._fsm_pop_by_type("dungeon_explore")


# ========================================
# 물리 공간 빌더
# ========================================

def initialize():
    """chapter init 시 1회 호출 — 영구 던전 Region 생성 + registry 등록.

    같은 Region을 던전 수명과 무관하게 유지:
      - 감각 격리 (R0 마을 != R200 던전)
      - Region 객체 누수 방지 (remove_region API 없음)
      - 던전 진입/종료 = Location 생성/제거로 관리

    챕터 전환 시 morld.clear_world()로 Region이 삭제되므로
    모듈 플래그(_region_initialized)는 chapter_reset()으로 리셋 후 호출.
    """
    global _region_initialized
    if _region_initialized:
        return
    from engine import region_registry
    morld.add_region(DUNGEON_REGION_ID, "리니어 던전",
                     {"default": "던전 내부. 바깥 세상과 단절되어 있다."},
                     "맑음")
    region_registry.register_dynamic(DUNGEON_REGION_ID)

    # 퀘스트별 진입점 Location 영구 생성 (동적 노드 id와 겹치지 않도록 1000+)
    for loc_id, name, length in ENTRANCE_LOCATIONS:
        morld.add_location(DUNGEON_REGION_ID, loc_id, name,
                           length=length, indoor=True)

    _region_initialized = True
    print("[dungeon] Permanent dungeon Region R"
          + str(DUNGEON_REGION_ID) + " initialized with "
          + str(len(ENTRANCE_LOCATIONS)) + " entrance locations")


def chapter_reset():
    """챕터 전환 시 호출 — 진행 중인 던전 상태 + Region 플래그 초기화.

    load_chapter에서 morld.clear_world()가 Region을 쓸어낸 직후 호출 필요.
    이후 initialize()로 R200을 재생성.
    """
    global _region_initialized
    # 진행 중 던전 정리 (Location 제거 시도 — Region이 이미 날아갔을 수 있음, 무시)
    try:
        reset()
    except Exception:
        pass
    _state["location_ids"] = []
    _state["active"] = False
    _region_initialized = False


def build_floor_locations(nodes):
    """현재 층의 노드 그래프 → Location + Gate 생성 (DUNGEON_REGION_ID 안).

    노드당 1 Location, DAG paths → 단방향 Gate.
    생성된 Location ID는 _state["location_ids"]에 누적.
    """
    for node in nodes:
        nid = node["id"]
        label = NODE_LABELS.get(node["type"], "방")
        length = _NODE_LENGTH.get(node["type"], 150)
        morld.add_location(DUNGEON_REGION_ID, nid, label,
                           length=length, indoor=True)
        _state["location_ids"].append(nid)

    # Gate 생성 (forward-only)
    gate_counter = 0
    for node in nodes:
        for target_id in node["paths"]:
            src_length = _NODE_LENGTH.get(node["type"], 150)
            morld.add_gate(DUNGEON_REGION_ID, node["id"], gate_counter,
                           max(0, src_length - 10),
                           DUNGEON_REGION_ID, target_id, 10)
            gate_counter += 1

    floor = _state["floor_index"] + 1
    total = max(1, len(_state["floors_config"]))
    _log("[dungeon] Built floor " + str(floor) + "/" + str(total)
         + " — " + str(len(nodes)) + " locations, "
         + str(gate_counter) + " gates")


def clear_floor_locations():
    """현재 층의 모든 Location 제거 (Gate도 자동 정리)."""
    if not _state["location_ids"]:
        return
    for nid in _state["location_ids"]:
        morld.remove_location(DUNGEON_REGION_ID, nid)
    count = len(_state["location_ids"])
    _state["location_ids"] = []
    _log("[dungeon] Cleared " + str(count) + " locations")


# ========================================
# 던전 생성
# ========================================

def generate_floor(depth: int = 6, *, max_width: int = 3, boss: dict = None) -> list:
    """단일 층 노드 그래프 생성. boss 지정 시 마지막 EXIT을 BOSS로 치환.

    Args:
        depth, max_width: generate_nodes와 동일.
        boss: None → EXIT로 종료.
              dict → 마지막 레벨 노드를 BOSS로 치환.
                    {"is_final": bool, "tier": int, "boss_id": str|None}

    Returns: 노드 그래프 (generate_nodes 포맷 + boss 노드 필드).
    """
    nodes = generate_nodes(depth, max_width=max_width)
    if boss is None:
        return nodes

    # 마지막 EXIT 노드를 BOSS로 치환
    for node in nodes:
        if node["type"] == NODE_EXIT:
            node["type"] = NODE_BOSS
            node["boss_config"] = {
                "is_final": bool(boss.get("is_final", False)),
                "tier": int(boss.get("tier", 1)),
                "boss_id": boss.get("boss_id"),
            }
            break

    # 부모 노드들의 라벨을 BOSS로 반영 (치환 후 재계산)
    for node in nodes:
        node["labels"] = [
            f"[{NODE_LABELS.get(nodes[p]['type'], '?')}]"
            for p in node["paths"]
        ]
    return nodes


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

    # Level 1 ~ depth-2: 랜덤 너비 + 가중 랜덤 타입
    for lvl in range(1, depth - 1):
        width = random.randint(1, max_width)
        row = []
        for _ in range(width):
            t = _roll_content_type()
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

    # 2.5. family 충돌 재롤 — STS식 "부모와 같은 family 방지"
    # 컨텐츠 노드만 대상 (START/EXIT 제외).
    _reroll_family_conflicts(nodes)

    # 3. labels 생성 (각 path의 대상 노드 타입 표시)
    for node in nodes:
        node["labels"] = [f"[{NODE_LABELS.get(nodes[p]['type'], '?')}]" for p in node["paths"]]

    return nodes


def _roll_content_type(exclude_families=None, exclude_types=None):
    """컨텐츠 노드 타입 가중 랜덤. 제외 family/type 지원."""
    types = []
    weights = []
    for t, w in _CONTENT_TYPE_WEIGHTS:
        if exclude_types and t in exclude_types:
            continue
        if exclude_families and NODE_FAMILIES.get(t) in exclude_families:
            continue
        types.append(t)
        weights.append(w)
    if not types:
        # 모든 후보 제외되는 edge case — 원래 분포로 fallback
        return random.choices(
            [t for (t, _) in _CONTENT_TYPE_WEIGHTS],
            weights=[w for (_, w) in _CONTENT_TYPE_WEIGHTS],
            k=1,
        )[0]
    return random.choices(types, weights=weights, k=1)[0]


def _reroll_family_conflicts(nodes):
    """각 컨텐츠 노드를 STS 스타일 인접 제약에 맞춰 재롤.

    제약:
      - node.type이 _NO_CONSECUTIVE_TYPES에 있고 부모 type 중 하나와 같음 → 재롤
      - node family가 _NO_CONSECUTIVE_FAMILIES에 있고 부모 family 중 하나와 같음 → 재롤
      - BATTLE은 제약 없음 (연속 허용) → 전투 클러스터 OK

    최대 10회 시도, 실패 시 현재 유지.
    """
    parents = {n["id"]: [] for n in nodes}
    for n in nodes:
        for p in n["paths"]:
            parents[p].append(n["id"])

    content_types = {NODE_BATTLE, NODE_REST, NODE_ELITE, NODE_CAMP,
                     NODE_TREASURE, NODE_EVENT, NODE_EMPTY, NODE_UNKNOWN}

    for node in nodes:
        if node["type"] not in content_types:
            continue
        parent_ids = parents[node["id"]]
        if not parent_ids:
            continue
        parent_types = {nodes[pid]["type"] for pid in parent_ids}
        parent_families = {NODE_FAMILIES.get(t) for t in parent_types}

        if not _has_adjacency_conflict(node["type"], parent_types, parent_families):
            continue

        # 재롤 — 충돌하는 family/type을 피하도록
        forbidden_families = parent_families & _NO_CONSECUTIVE_FAMILIES
        forbidden_types = parent_types & _NO_CONSECUTIVE_TYPES
        for _ in range(10):
            new_type = _roll_content_type(
                exclude_families=forbidden_families,
                exclude_types=forbidden_types,
            )
            if not _has_adjacency_conflict(new_type, parent_types, parent_families):
                node["type"] = new_type
                break


def _has_adjacency_conflict(node_type, parent_types, parent_families):
    """node_type이 주어진 parent 집합과 인접 제약을 위반하는지."""
    # type-level 제약 (ELITE 같은 것)
    if node_type in _NO_CONSECUTIVE_TYPES and node_type in parent_types:
        return True
    # family-level 제약 (rest, event)
    node_family = NODE_FAMILIES.get(node_type)
    if node_family in _NO_CONSECUTIVE_FAMILIES and node_family in parent_families:
        return True
    return False


def reveal_unknown_node():
    """현재 노드가 UNKNOWN이면 실제 타입으로 공개.

    Returns: 공개된 타입 (UNKNOWN이 아닌 경우 현재 타입 그대로 반환).
    """
    node = get_current_node()
    if node is None or node["type"] != NODE_UNKNOWN:
        return node["type"] if node else None

    types = [t for (t, _) in _UNKNOWN_REVEAL_WEIGHTS]
    weights = [w for (_, w) in _UNKNOWN_REVEAL_WEIGHTS]
    revealed = random.choices(types, weights=weights, k=1)[0]
    node["type"] = revealed
    node["was_unknown"] = True
    return revealed


def enter(floors_config: list = None, *, nodes: list = None,
          depth: int = 6, max_width: int = 3):
    """던전 진입 → 첫 층 Location 생성 + START 활성화.

    Args:
        floors_config: [{"depth", "max_width", "boss"}, ...] per-floor configs.
            boss: None (EXIT 종료) | {"is_final": bool, "tier": int, "boss_id": str|None}
        nodes: 레거시 — 직접 생성한 노드 그래프 (단층). floors_config보다 우선.
        depth, max_width: 레거시 단층 기본값. floors_config/nodes 없을 때.
    """
    reset()

    # 영구 Region 미초기화면 fallback (chapter init 미호출 방어)
    if not _region_initialized:
        initialize()

    # floors_config 정규화 (레거시 단층 경로 포함)
    if floors_config is None and nodes is None:
        floors_config = [{"depth": depth, "max_width": max_width, "boss": None}]
    elif floors_config is None:
        # nodes 직접 지정 — 단층 구성
        floors_config = [{"depth": depth, "max_width": max_width, "boss": None}]

    _state["floors_config"] = floors_config
    _state["floor_index"] = 0
    _state["region_id"] = DUNGEON_REGION_ID

    # 첫 층 생성
    if nodes is None:
        cfg = floors_config[0]
        nodes = generate_floor(
            cfg.get("depth", 6),
            max_width=cfg.get("max_width", 3),
            boss=cfg.get("boss"),
        )
    _state["nodes"] = nodes
    _state["index"] = 0
    _state["active"] = True

    # 물리 공간 생성 (영구 Region 내 Location)
    build_floor_locations(nodes)

    # 파티를 던전 시작 Location으로 이동
    _teleport_party_to_start()

    # 던전 UI: header/footer 표시 + 파티 이탈 잠금
    from engine.ui_base import set_show_header, set_show_footer
    set_show_header(True)
    set_show_footer(True)
    player_id = morld.get_player_id()
    if player_id is not None:
        morld.modify_prop(player_id, "can:dismiss_from_party", -1)

    # 파티원 NPC에 DungeonState push (일반 생활 차단)
    _push_dungeon_state_to_party()

    _log("[dungeon] Enter dungeon — floor 1/"
         + str(len(floors_config))
         + ", " + str(len(nodes)) + " nodes")
    return get_current_node()


def _teleport_party_to_start():
    """파티 전원(또는 플레이어)을 현재 층 START(id=0)로 텔레포트."""
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None
    if party is not None:
        for uid in party.get_members():
            morld.set_unit_location(uid, DUNGEON_REGION_ID, 0, x=10)
    elif player_id is not None:
        morld.set_unit_location(player_id, DUNGEON_REGION_ID, 0, x=10)


def advance_to_next_floor():
    """다음 층으로 전환 — 현재 층 Location 정리 + 다음 층 생성 + 파티 이동."""
    if not has_next_floor():
        _log("[dungeon] advance_to_next_floor blocked — no next floor")
        return False

    # 현재 층 정리
    clear_floor_locations()

    # 다음 층 생성
    _state["floor_index"] += 1
    cfg = _state["floors_config"][_state["floor_index"]]
    nodes = generate_floor(
        cfg.get("depth", 6),
        max_width=cfg.get("max_width", 3),
        boss=cfg.get("boss"),
    )
    _state["nodes"] = nodes
    _state["index"] = 0
    build_floor_locations(nodes)

    # 파티 이동
    _teleport_party_to_start()
    _switch_party_to_explore()

    _log("[dungeon] Advanced to floor " + str(_state["floor_index"] + 1)
         + "/" + str(len(_state["floors_config"]))
         + " — " + str(len(nodes)) + " nodes")
    return True


def has_next_floor() -> bool:
    """현재 층 다음에 층이 더 있는가."""
    return _state["floor_index"] + 1 < len(_state["floors_config"])


def get_floor_info() -> tuple:
    """(current_floor_1idx, total_floors) 반환."""
    total = max(1, len(_state["floors_config"]))
    return (_state["floor_index"] + 1, total)


def is_on_boss_node() -> bool:
    """현재 노드가 BOSS 타입인가."""
    node = get_current_node()
    return node is not None and node["type"] == NODE_BOSS


def is_on_final_boss() -> bool:
    """현재 노드가 최종 보스(is_final=True)인가."""
    node = get_current_node()
    if node is None or node["type"] != NODE_BOSS:
        return False
    boss_cfg = node.get("boss_config") or {}
    return bool(boss_cfg.get("is_final"))


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
    """현재 노드가 진행 가능 상태인지. 전투(일반/엘리트/보스) 미해결이면 False."""
    node = get_current_node()
    if node is None:
        return False
    if node["type"] in (NODE_BATTLE, NODE_ELITE, NODE_BOSS) and not node.get("cleared"):
        return False
    return True


# ========================================
# 노드 처리
# ========================================

def process_current_node(*, on_battle=None, on_rest=None) -> dict:
    """현재 노드의 타입별 처리를 실행하고 결과 반환.

    Returns:
        {"node": dict, "result": str|None, "player_fainted": bool}
        result는 battle: 'victory'/'defeat'/None / rest: 'rested' / 그 외 None.
    """
    # 노드 이벤트 시작 → NPC를 DungeonState(차단)로 전환
    _switch_party_to_dungeon()

    node = get_current_node()
    if node is None:
        return {"node": None, "result": None}

    t = node["type"]
    result = None

    if t in (NODE_BATTLE, NODE_ELITE, NODE_BOSS):
        _log(f"[dungeon] {t.title()} node (floor={node['floor']})")
        handler = on_battle or default_battle_handler
        # ELITE/BOSS: 향후 강적 생성 — 현재는 동일 encounter + 플래그만
        if t == NODE_ELITE:
            node["elite"] = True
        elif t == NODE_BOSS:
            node["boss"] = True
        battle_result = handler(node)
        if battle_result is not None:
            result = battle_result.get("result")
            if result == "victory":
                node["cleared"] = True
    elif t in (NODE_REST, NODE_CAMP):
        _log(f"[dungeon] {t.title()} node (floor={node['floor']})")
        handler = on_rest or default_rest_handler
        # CAMP: 향후 긴 회복 — 현재는 동일 처리
        handler(node)
        result = "rested"
    elif t == NODE_TREASURE:
        _log(f"[dungeon] Treasure node (floor={node['floor']}) — empty (TODO: rewards)")
        # 이벤트 없음 (현재)
    elif t == NODE_EVENT:
        _log(f"[dungeon] Event node (floor={node['floor']}) — empty (TODO: event trigger)")
        # 이벤트 없음 (현재)
    elif t == NODE_EMPTY:
        _log(f"[dungeon] Empty node (floor={node['floor']})")
        # 이벤트 없음
    elif t == NODE_BRANCH:
        _log(f"[dungeon] Branch node (floor={node['floor']})")
    elif t == NODE_EXIT:
        _log(f"[dungeon] Exit node (floor={node['floor']})")

    # 시간 소모
    time_cost = NODE_TIME_COST.get(t, 0)
    if time_cost > 0:
        morld.advance_time_des(time_cost)

    # 시간 경과 후 플레이어 실신 체크
    player_fainted = False
    player_id = morld.get_player_id()
    if player_id is not None and morld.get_unit_prop(player_id, "상태:실신"):
        player_fainted = True

    return {"node": node, "result": result, "player_fainted": player_fainted}


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
    물리 이동: 파티 전원을 다음 Location으로 텔레포트.
    """
    node = get_current_node()
    if node is None:
        return {"ok": False, "reason": "inactive"}

    if not is_current_cleared():
        return {"ok": False, "reason": "battle_not_cleared"}

    if target_id not in node["paths"]:
        return {"ok": False, "reason": "invalid_target"}

    _state["index"] = target_id

    # 물리 이동: 파티 전원을 다음 Location으로
    region_id = _state.get("region_id")
    if region_id is not None:
        _move_party_to_node(region_id, target_id)

    # 이동 후 탐색 모드 (감각/판단 허용)
    _switch_party_to_explore()

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
    """모든 파티원을 귀환시킴.

    reason별 목적지:
    - rescued/all_fainted + 구호소 → 구호소(R0/L5)
    - 그 외 → 던전 입구(R0/L7)
    """
    from engine import party_group as _pg
    player_id = morld.get_player_id()
    party = _pg.get_party_of(player_id) if player_id else None

    reset()

    # 목적지 결정
    dest_region = VILLAGE_REGION
    dest_location = VILLAGE_LOCATION
    dest_x = VILLAGE_X

    if reason in ("rescued", "all_fainted"):
        try:
            import facility
            if facility.has_infirmary():
                dest_location = 5  # 구호소
                dest_x = 50
        except (ImportError, Exception):
            pass

    if party is not None:
        for uid in party.get_members():
            morld.set_unit_location(uid, dest_region, dest_location, x=dest_x)
    elif player_id is not None:
        morld.set_unit_location(player_id, dest_region, dest_location, x=dest_x)

    _log("[dungeon] Exit to village — reason=" + reason
         + " dest=R" + str(dest_region) + ":L" + str(dest_location))

    # 퀘스트 연동: 클리어 시 모든 활성 보드 퀘스트에 브로드캐스트
    # (dungeon_cleared prop 설정 + on_dungeon_clear 훅 실행 + 조건 재평가)
    if reason == "cleared_end":
        try:
            import quest_board
            quest_board.on_dungeon_clear()
        except ImportError:
            pass


def _on_entrance_reach(unit_id, region, loc):
    """event_core에 등록되는 on_reach handler — R200의 진입점 Location 도달 시 호출.

    Location ID로 장소(location_key) 역매핑 → quest_board에서 해당 장소의
    floors_config 조회 → enter() 실행 → auto_run().
    진입점 Gate는 퀘스트 수락 시 ref-count로 생성되므로 도달 = 활성 퀘스트 있음.
    """
    # 진입점이 아니면 무시
    if loc not in _ENTRANCE_LOC_IDS:
        return None

    # 이미 던전 진행 중이면 재입장 (auto_run만 실행)
    if _state["active"]:
        return auto_run()

    try:
        import quest_board
    except ImportError:
        return None

    location_key = quest_board.get_location_key_by_loc_id(loc)
    if location_key is None:
        _log("[dungeon] Entrance loc=" + str(loc) + " has no location_key")
        return None

    # 해당 장소의 활성 퀘스트 → floors_config 조회
    floors_config = quest_board.get_floors_config_for_location(location_key)
    if floors_config is None:
        _log("[dungeon] No active quest for location_key=" + location_key)
        return None

    enter(floors_config=floors_config)

    node = get_current_node()
    _log("[dungeon] Entered via on_reach — location=" + location_key
         + ", floors=" + str(len(floors_config))
         + ", first node=" + (node["type"] if node else "?"))
    return auto_run()


def register_location_handlers():
    """chapter load 시 호출 — 퀘스트별 진입점 Location의 on_reach handler 등록."""
    from engine import event_core
    for loc_id, _, _ in ENTRANCE_LOCATIONS:
        event_core.subscribe_on_reach(
            DUNGEON_REGION_ID, loc_id, _on_entrance_reach, player_only=True
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
