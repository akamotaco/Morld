# quest_board.py — S04 퀘스트 시스템 초기화 + 게시판 퀘스트 정의
#
# engine/quest.py 기반. S04 전용 조건: dungeon_cleared.
# 게시판(L7)에서 수락 → 리니어 던전 생성 → 클리어/시간초과 → 종료.

import morld
from engine.quest import (
    Quest, QuestStatus, QuestManager,
    register_quest, register_quest_instance,
    register_condition_type,
    get_quest_manager, set_quest_manager,
)
from engine.event_core import subscribe_time_elapsed


# ============================================
# 시간 제한 (시간초과 판정용)
# ============================================

QUEST_TIME_LIMIT_HOURS = 168  # 7일


# ============================================
# S04 퀘스트 정의 (게시판용)
# ============================================

_BOARD_QUESTS = [
    {
        "unique_id": "board_dungeon_explore",
        "name": "동굴 탐사",
        "description": "던전을 탐사하고 끝까지 도달하라.",
        "category": "board",
        "conditions": [{"type": "dungeon_cleared"}],
        "rewards": [],
        "repeatable": True,
        # 던전 Gate 정보: 수락 시 생성, 종료 시 삭제
        "gate": {
            "region": 0, "loc": 7, "gate_id": 4, "x": 90,
            "conn_region": 0, "conn_loc": 12, "arrival_x": 0,
            "back_gate_id": 0, "back_x": 0, "back_arrival_x": 90,
        },
        "dungeon": {"depth": 6, "max_width": 3},
    },
]


# ============================================
# S04 조건: dungeon_cleared
# ============================================

def _check_dungeon_cleared(player_id, condition, quest_id):
    """던전 클리어 여부 (prop 기반)"""
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    key = "퀘스트:" + quest_id + ":던전클리어"
    return props.get(key, 0) >= 1


def _desc_dungeon_cleared(condition):
    return "던전 끝까지 도달"


def mark_dungeon_cleared(quest_id):
    """던전 클리어 시 호출 (linear_dungeon.exit_to_village에서)"""
    player_id = morld.get_player_id()
    if player_id is None:
        return
    key = "퀘스트:" + quest_id + ":던전클리어"
    morld.set_unit_prop(player_id, key, 1)

    # 조건 재평가 → 자동 완료
    mgr = get_quest_manager()
    mgr.check_quest_conditions(quest_id)


# ============================================
# S04 QuestManager
# ============================================

class S04QuestManager(QuestManager):

    def on_quest_accepted(self, quest_id, quest):
        if quest.category == "board":
            # 던전 생성
            dungeon_cfg = _get_quest_data(quest_id, "dungeon") or {}
            import linear_dungeon
            if not linear_dungeon.is_active():
                linear_dungeon.enter(
                    depth=dungeon_cfg.get("depth", 6),
                    max_width=dungeon_cfg.get("max_width", 3))
            # Gate 생성
            _create_quest_gate(quest_id)
            print("[quest_board] Dungeon + gate created for quest: " + quest_id)

    def on_quest_completed(self, quest_id, quest):
        if quest.category == "board":
            import linear_dungeon
            linear_dungeon.reset()
            _remove_quest_gate(quest_id)
            print("[quest_board] Quest completed, gate removed: " + quest_id)

    def on_quest_failed(self, quest_id, quest, reason):
        if quest.category == "board":
            import linear_dungeon
            linear_dungeon.reset()
            _remove_quest_gate(quest_id)
            print("[quest_board] Quest failed (" + reason + "), gate removed: " + quest_id)


# ============================================
# 시간초과 체크 (매 시간)
# ============================================

# ============================================
# Gate 동적 생성/삭제
# ============================================

def _get_quest_data(quest_id, key):
    """퀘스트 정의에서 추가 데이터 조회 (gate, dungeon 등)"""
    for qdata in _BOARD_QUESTS:
        if qdata["unique_id"] == quest_id:
            return qdata.get(key)
    return None


def _create_quest_gate(quest_id):
    """퀘스트의 Gate 정보로 양방향 Gate 생성"""
    gate = _get_quest_data(quest_id, "gate")
    if not gate:
        return
    # 정방향: 던전 입구 → 퀘스트 던전
    morld.add_gate(gate["region"], gate["loc"], gate["gate_id"], gate["x"],
                   gate["conn_region"], gate["conn_loc"], gate["arrival_x"])
    # 역방향: 퀘스트 던전 → 던전 입구
    morld.add_gate(gate["conn_region"], gate["conn_loc"], gate["back_gate_id"],
                   gate["back_x"], gate["region"], gate["loc"], gate["back_arrival_x"])


def _remove_quest_gate(quest_id):
    """퀘스트의 Gate 양방향 삭제"""
    gate = _get_quest_data(quest_id, "gate")
    if not gate:
        return
    morld.remove_gate(gate["region"], gate["loc"], gate["gate_id"])
    morld.remove_gate(gate["conn_region"], gate["conn_loc"], gate["back_gate_id"])


# ============================================
# 시간초과 체크 (매 시간)
# ============================================

def _on_time_elapsed(millis):
    """매 시간 호출 — 게시판 퀘스트 시간초과 체크"""
    mgr = get_quest_manager()
    for quest in mgr.get_active_quests():
        if quest.category != "board":
            continue
        player_id = morld.get_player_id()
        if player_id is None:
            continue
        props = morld.get_unit_props(player_id)
        if not props:
            continue
        accept_time = props.get("퀘스트:" + quest.unique_id + ":수락시각", 0)
        if accept_time <= 0:
            continue
        elapsed_hours = (morld.get_game_time() - accept_time) / 3_600_000
        if elapsed_hours >= QUEST_TIME_LIMIT_HOURS:
            mgr.fail_quest(quest.unique_id, reason="시간초과")


# ============================================
# 헬퍼: 활성 게시판 퀘스트 조회
# ============================================

def get_active_board_quest():
    """현재 진행 중인 게시판 퀘스트 (없으면 None)"""
    mgr = get_quest_manager()
    for quest in mgr.get_active_quests():
        if quest.category == "board":
            return quest
    return None


def has_active_board_quest():
    return get_active_board_quest() is not None


# ============================================
# 초기화
# ============================================

def initialize():
    """S04 퀘스트 시스템 초기화. 챕터 init에서 호출."""
    # S04 QuestManager 설정
    mgr = S04QuestManager()
    set_quest_manager(mgr)

    # S04 조건 등록
    register_condition_type("dungeon_cleared", _check_dungeon_cleared, _desc_dungeon_cleared)

    # 게시판 퀘스트 등록
    for qdata in _BOARD_QUESTS:
        q = Quest.from_dict(qdata)
        register_quest_instance(q)

    # 시간초과 체크 구독 (1시간 간격)
    subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)

    print("[quest_board] Initialized — " + str(len(_BOARD_QUESTS)) + " board quests")


def reset():
    """챕터 전환 시 리셋"""
    from engine.quest import reset as _engine_reset
    _engine_reset()
