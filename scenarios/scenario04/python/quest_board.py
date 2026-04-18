# quest_board.py — S04 퀘스트 시스템 초기화 + 게시판 퀘스트 정의
#
# engine/quest.py 기반. S04 전용:
#   - 조건: dungeon_cleared (prop), item_count (인벤토리 직접 체크)
#   - 훅: on_dungeon_clear 액션 리스트 (EXIT 도달 시 브로드캐스트)
#   - 액션 타입: give_random_item (랜덤 개수 아이템 지급)
#
# 퀘스트 장소(location) 개념:
#   - 각 퀘스트가 location_key로 진입점(R200의 영구 Location) 참조
#   - 여러 퀘스트가 같은 장소 공유 → Gate ref-count로 관리
#   - 장소별 default_floors → 공유 퀘스트들은 같은 던전 레이아웃 사용

import random
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
# 퀘스트 장소 레지스트리 (진입점 Location + 기본 던전 레이아웃)
# ============================================
#
# loc_id는 linear_dungeon.ENTRANCE_LOCATIONS와 동기화 필수.
# entrance_gate_id는 R0/L7 쪽 Gate ID (4, 5, 6... 장소별 고유).
# back_gate_id는 R200/진입점 → R0/L7 복귀용 (장소별 0 통일).

_QUEST_LOCATIONS = {
    "cave": {
        "loc_id": 1000,
        "entrance_gate_id": 4,
        "entrance_x": 90,
        "arrival_x": 10,
        "back_gate_id": 0,
        "back_x": 0,
        "back_arrival_x": 90,
        "default_floors": [
            {"depth": 6, "max_width": 3, "boss": None},
        ],
    },
    "deep": {
        "loc_id": 1001,
        "entrance_gate_id": 5,
        "entrance_x": 60,
        "arrival_x": 10,
        "back_gate_id": 0,
        "back_x": 0,
        "back_arrival_x": 60,
        "default_floors": [
            {"depth": 5, "max_width": 2, "boss": None},
            {"depth": 5, "max_width": 2, "boss": None},
            {"depth": 5, "max_width": 3, "boss": None},
        ],
    },
    "guardian": {
        "loc_id": 1002,
        "entrance_gate_id": 6,
        "entrance_x": 30,
        "arrival_x": 10,
        "back_gate_id": 0,
        "back_x": 0,
        "back_arrival_x": 30,
        "default_floors": [
            {"depth": 5, "max_width": 2, "boss": None},
            {"depth": 5, "max_width": 2, "boss": None},
            {"depth": 5, "max_width": 2, "boss": {"is_final": False, "tier": 2}},
            {"depth": 5, "max_width": 3, "boss": None},
            {"depth": 6, "max_width": 3, "boss": {"is_final": True, "tier": 3}},
        ],
    },
}

# 역매핑 (loc_id → location_key) — linear_dungeon._on_entrance_reach에서 사용
_LOC_ID_TO_KEY = {cfg["loc_id"]: key for key, cfg in _QUEST_LOCATIONS.items()}


# ============================================
# Gate ref-count (장소별 활성 퀘스트 수)
# ============================================

_location_refcount = {}


def _acquire_location(location_key):
    """장소 참조 증가 — 0→1일 때 Gate 생성."""
    cur = _location_refcount.get(location_key, 0)
    if cur == 0:
        _create_location_gate(location_key)
    _location_refcount[location_key] = cur + 1


def _release_location(location_key):
    """장소 참조 감소 — 1→0일 때 Gate 삭제."""
    cur = _location_refcount.get(location_key, 0)
    if cur <= 0:
        return
    _location_refcount[location_key] = cur - 1
    if _location_refcount[location_key] == 0:
        _remove_location_gate(location_key)


def _create_location_gate(location_key):
    """L7 ↔ R200/진입점 양방향 Gate 생성."""
    cfg = _QUEST_LOCATIONS.get(location_key)
    if cfg is None:
        return
    from linear_dungeon import DUNGEON_REGION_ID
    # L7 → 진입점 (정방향)
    morld.add_gate(0, 7, cfg["entrance_gate_id"], cfg["entrance_x"],
                   DUNGEON_REGION_ID, cfg["loc_id"], cfg["arrival_x"])
    # 진입점 → L7 (복귀)
    morld.add_gate(DUNGEON_REGION_ID, cfg["loc_id"], cfg["back_gate_id"],
                   cfg["back_x"], 0, 7, cfg["back_arrival_x"])


def _remove_location_gate(location_key):
    """양방향 Gate 제거."""
    cfg = _QUEST_LOCATIONS.get(location_key)
    if cfg is None:
        return
    from linear_dungeon import DUNGEON_REGION_ID
    morld.remove_gate(0, 7, cfg["entrance_gate_id"])
    morld.remove_gate(DUNGEON_REGION_ID, cfg["loc_id"], cfg["back_gate_id"])


def get_location_key_by_loc_id(loc_id):
    """R200 내 진입점 Location ID → location_key."""
    return _LOC_ID_TO_KEY.get(loc_id)


def get_floors_config_for_location(location_key):
    """해당 장소의 활성 퀘스트 기준 floors_config 조회.

    같은 장소 퀘스트들은 동일 default_floors 공유 (설계 원칙).
    활성 퀘스트가 없으면 None.
    """
    # 활성 퀘스트가 하나라도 있으면 장소의 default_floors 사용
    mgr = get_quest_manager()
    has_active = False
    for quest in mgr.get_active_quests():
        if quest.category != "board":
            continue
        if _get_quest_data(quest.unique_id, "location") == location_key:
            has_active = True
            break
    if not has_active:
        return None
    return list(_QUEST_LOCATIONS[location_key]["default_floors"])


# ============================================
# 게시판 퀘스트 정의
# ============================================

_BOARD_QUESTS = [
    # 동굴 탐사 — 단층, EXIT 도달로 완료
    {
        "unique_id": "board_dungeon_explore",
        "name": "동굴 탐사",
        "description": "동굴을 탐사하고 끝까지 도달하라.",
        "category": "board",
        "conditions": [{"type": "dungeon_cleared"}],
        "rewards": [],
        "repeatable": True,
        "location": "cave",
    },
    # 동굴 이끼 수집 — 인벤토리 3개 보유 + 게시판 보고 방식
    # 1회 클리어당 1~2개 랜덤 지급 → 2~3회 반복 필요 → 게시판 "확인" 시 이끼 소비
    {
        "unique_id": "board_cave_moss",
        "name": "동굴 이끼 수집",
        "description": "동굴 내부에서 자라는 이끼를 3개 채집해 게시판에 보고하라.",
        "category": "board",
        "conditions": [
            {"type": "item_count", "item": "cave_moss", "min_count": 3},
        ],
        "rewards": [],
        "repeatable": True,
        "location": "cave",
        "reporter": "quest_board",   # 게시판 focus → 보고 방식
        "on_confirm": [
            {"type": "consume_item", "item": "cave_moss", "count": 3},
        ],
        "on_dungeon_clear": [
            {"type": "give_random_item", "item": "cave_moss",
             "min": 1, "max": 2},
        ],
    },
    # 심층 탐사 — 3층 탐사
    {
        "unique_id": "board_deep_exploration",
        "name": "심층 탐사",
        "description": "동굴 더 깊은 곳까지 내려가 탐사한 뒤 귀환하라.",
        "category": "board",
        "conditions": [{"type": "dungeon_cleared"}],
        "rewards": [],
        "repeatable": True,
        "location": "deep",
    },
    # 수호수 토벌 — 5층, 최종 보스 (즉시 클리어)
    {
        "unique_id": "board_guardian_hunt",
        "name": "수호수 토벌",
        "description": "동굴 최하층의 수호수를 처치하라. 중간층에도 강적이 도사린다.",
        "category": "board",
        "conditions": [{"type": "dungeon_cleared"}],
        "rewards": [],
        "repeatable": True,
        "location": "guardian",
    },
]


# ============================================
# S04 조건 타입
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


def _check_item_count(player_id, condition, quest_id):
    """인벤토리에 특정 아이템 min_count 이상 보유"""
    item_unique = condition.get("item")
    min_count = int(condition.get("min_count", 1))
    if not item_unique:
        return False
    item_id = morld.get_item_id_by_unique(item_unique)
    if item_id is None:
        return False
    inv = morld.get_unit_inventory(player_id) or {}
    return inv.get(item_id, 0) >= min_count


def _desc_item_count(condition):
    item_unique = condition.get("item", "")
    min_count = int(condition.get("min_count", 1))
    item_id = morld.get_item_id_by_unique(item_unique)
    item_name = item_unique
    if item_id is not None:
        info = morld.get_item_info(item_id)
        if info and info.get("name"):
            item_name = info["name"]
    return item_name + " " + str(min_count) + "개 확보"


# ============================================
# on_dungeon_clear 액션 핸들러
# ============================================

_CLEAR_ACTION_HANDLERS = {}


def register_clear_action(name, handler):
    """on_dungeon_clear 액션 타입 등록. handler(player_id, action, quest_id)."""
    _CLEAR_ACTION_HANDLERS[name] = handler


def _action_give_random_item(player_id, action, quest_id):
    """랜덤 개수 아이템 지급 (min~max)"""
    item_unique = action.get("item")
    if not item_unique:
        return
    mn = int(action.get("min", 1))
    mx = int(action.get("max", 1))
    count = random.randint(mn, mx)
    if count <= 0:
        return
    # morld.give_item은 item_id(int) 요구 — unique_id → id 변환
    # 기존 C# 등록 우선, 없으면 registry에서 새로 생성
    item_id = morld.get_item_id_by_unique(item_unique)
    if item_id is None:
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(item_unique)
    if item_id is None:
        print("[quest_board] give_random_item: unknown item " + item_unique)
        return
    morld.give_item(player_id, item_id, count)
    print("[quest_board] Clear reward: " + str(count) + "x " + item_unique
          + " → quest=" + quest_id)


# ============================================
# 던전 클리어 브로드캐스트 (linear_dungeon.exit_to_village "cleared_end"에서 호출)
# ============================================

def on_dungeon_clear():
    """던전 1회 클리어 — 모든 활성 게시판 퀘스트에 알림.

    1. dungeon_cleared prop 설정 (탐사형 퀘스트 조건 충족)
    2. on_dungeon_clear 액션 실행 (수집형 보상 지급)
    3. 조건 재평가 → 충족 시 자동 완료
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return
    mgr = get_quest_manager()
    for quest in mgr.get_active_quests():
        if quest.category != "board":
            continue
        qid = quest.unique_id
        # 1. dungeon_cleared prop
        morld.set_unit_prop(player_id, "퀘스트:" + qid + ":던전클리어", 1)
        # 2. 훅 액션 실행
        actions = _get_quest_data(qid, "on_dungeon_clear") or []
        for action in actions:
            atype = action.get("type")
            handler = _CLEAR_ACTION_HANDLERS.get(atype)
            if handler is None:
                print("[quest_board] Unknown clear action type: " + str(atype))
                continue
            handler(player_id, action, qid)
        # 3. 조건 재평가
        mgr.check_quest_conditions(qid)


# 기존 API 호환: 단일 퀘스트에 대한 mark (향후 제거 가능)
def mark_dungeon_cleared(quest_id=None):
    """DEPRECATED: on_dungeon_clear()로 대체. 하위 호환용."""
    on_dungeon_clear()


# ============================================
# S04 QuestManager
# ============================================

class S04QuestManager(QuestManager):

    def on_quest_accepted(self, quest_id, quest):
        if quest.category == "board":
            location_key = _get_quest_data(quest_id, "location")
            if location_key is None:
                print("[quest_board] WARN: quest " + quest_id + " has no location")
                return
            _acquire_location(location_key)
            print("[quest_board] Quest accepted: " + quest_id
                  + " at '" + location_key + "' (refcount="
                  + str(_location_refcount.get(location_key, 0)) + ")")

    def on_quest_completed(self, quest_id, quest):
        if quest.category == "board":
            location_key = _get_quest_data(quest_id, "location")
            if location_key is not None:
                _release_location(location_key)
            # 이 퀘스트의 던전클리어 prop 초기화 (반복 퀘스트 재진입 시 깨끗한 상태)
            player_id = morld.get_player_id()
            if player_id is not None:
                morld.set_unit_prop(player_id, "퀘스트:" + quest_id + ":던전클리어", 0)
            print("[quest_board] Quest completed: " + quest_id)

    def on_quest_failed(self, quest_id, quest, reason):
        if quest.category == "board":
            location_key = _get_quest_data(quest_id, "location")
            if location_key is not None:
                _release_location(location_key)
            player_id = morld.get_player_id()
            if player_id is not None:
                morld.set_unit_prop(player_id, "퀘스트:" + quest_id + ":던전클리어", 0)
            print("[quest_board] Quest failed (" + reason + "): " + quest_id)


# ============================================
# 내부 헬퍼
# ============================================

def _get_quest_data(quest_id, key):
    """퀘스트 정의에서 추가 데이터 조회 (location, on_dungeon_clear 등)"""
    for qdata in _BOARD_QUESTS:
        if qdata["unique_id"] == quest_id:
            return qdata.get(key)
    return None


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
    """현재 진행 중인 게시판 퀘스트 중 첫 번째 (없으면 None)"""
    mgr = get_quest_manager()
    for quest in mgr.get_active_quests():
        if quest.category == "board":
            return quest
    return None


def has_active_board_quest():
    return get_active_board_quest() is not None


def get_active_board_quests():
    """현재 진행 중인 모든 게시판 퀘스트 리스트"""
    mgr = get_quest_manager()
    return [q for q in mgr.get_active_quests() if q.category == "board"]


# ============================================
# 초기화
# ============================================

def initialize():
    """S04 퀘스트 시스템 초기화. 챕터 init에서 호출."""
    # S04 QuestManager 설정
    mgr = S04QuestManager()
    set_quest_manager(mgr)

    # S04 조건 등록
    register_condition_type("dungeon_cleared",
                            _check_dungeon_cleared, _desc_dungeon_cleared)
    register_condition_type("item_count",
                            _check_item_count, _desc_item_count)

    # on_dungeon_clear 액션 타입 등록
    register_clear_action("give_random_item", _action_give_random_item)

    # 게시판 퀘스트 등록
    for qdata in _BOARD_QUESTS:
        q = Quest.from_dict(qdata)
        register_quest_instance(q)

    # ref-count 초기화
    _location_refcount.clear()

    # 시간초과 체크 구독 (1시간 간격)
    subscribe_time_elapsed(_on_time_elapsed, min_interval=3_600_000)

    print("[quest_board] Initialized — " + str(len(_BOARD_QUESTS)) + " board quests, "
          + str(len(_QUEST_LOCATIONS)) + " locations")


def reset():
    """챕터 전환 시 리셋"""
    from engine.quest import reset as _engine_reset
    _engine_reset()
    _location_refcount.clear()
