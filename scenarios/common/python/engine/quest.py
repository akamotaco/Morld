# engine/quest.py — 퀘스트 프레임워크
#
# 상태 머신 + Props 기반 영속성 + 플러그인 조건/보상.
#
# 구조:
#   QuestStatus: 상태 enum (LOCKED → AVAILABLE → IN_PROGRESS → COMPLETED → FINISHED)
#   Quest: 퀘스트 데이터 베이스 클래스
#   QuestManager: 상태 관리 + 조건/보상 루프
#   register_condition_type / register_reward_type: 플러그인 등록
#
# 시나리오별 확장:
#   - 조건/보상 타입 추가: register_condition_type("meet", fn, desc_fn)
#   - QuestManager 서브클래스: set_quest_manager(MyManager())
#   - Quest 서브클래스: dialog 메서드 등 UI 레이어 추가
#
# 기본 내장 조건: reach, prop, wait, all, any, quest_completed
# 기본 내장 보상: prop, unlock_quest

import morld


# ============================================
# 상태
# ============================================

class QuestStatus:
    """퀘스트 상태 (정수 기반 — Props 직렬화 호환)"""
    LOCKED = 0
    AVAILABLE = 1
    IN_PROGRESS = 2
    COMPLETED = 3
    FINISHED = 4

    _names = {0: "locked", 1: "available", 2: "in_progress", 3: "completed", 4: "finished"}

    @staticmethod
    def name_of(value):
        return QuestStatus._names.get(value, "unknown")


# ============================================
# 조건/보상 플러그인 레지스트리
# ============================================

_condition_handlers = {}  # {name: (check_fn, desc_fn)}
_reward_handlers = {}     # {name: (apply_fn, desc_fn)}


def register_condition_type(name, check_fn, desc_fn=None):
    """조건 타입 등록. check_fn(player_id, condition, quest_id) -> bool"""
    _condition_handlers[name] = (check_fn, desc_fn)


def register_reward_type(name, apply_fn, desc_fn=None):
    """보상 타입 등록. apply_fn(player_id, reward) -> bool"""
    _reward_handlers[name] = (apply_fn, desc_fn)


def check_condition(player_id, condition, quest_id):
    """조건 충족 여부 체크 (등록된 핸들러에 디스패치)"""
    handler = _condition_handlers.get(condition.get("type"))
    if handler:
        return handler[0](player_id, condition, quest_id)
    return False


def get_condition_description(condition):
    """조건 설명 텍스트"""
    handler = _condition_handlers.get(condition.get("type"))
    if handler and handler[1]:
        return handler[1](condition)
    return condition.get("description", "알 수 없는 조건")


def apply_reward(player_id, reward):
    """보상 지급 (등록된 핸들러에 디스패치)"""
    handler = _reward_handlers.get(reward.get("type"))
    if handler:
        fn = handler[0] if isinstance(handler, tuple) else handler
        return fn(player_id, reward)
    return False


def get_reward_description(reward):
    """보상 설명 텍스트"""
    handler = _reward_handlers.get(reward.get("type"))
    if handler and isinstance(handler, tuple) and handler[1]:
        return handler[1](reward)
    return reward.get("description", "알 수 없는 보상")


# ============================================
# 퀘스트 데이터 클래스
# ============================================

class Quest:
    """퀘스트 베이스 클래스. UI 없는 순수 데이터."""

    unique_id = ""
    name = "Unknown Quest"
    description = ""
    category = "side"  # main, side, daily, personal, board, ...

    prerequisites = []   # 선행 퀘스트 id 리스트
    conditions = []      # 완료 조건 dict 리스트
    rewards = []         # 보상 dict 리스트

    giver = None         # 퀘스트 지급자 unique_id (None → 이벤트/게시판)
    reporter = None      # 완료 보고 대상 (None → 자동 완료)
    dialogs = {}         # 상황별 대사 {"offer": [...], "accept": [...], ...}

    repeatable = False
    visibility_conditions = {}  # prop 기반 표시 조건

    @classmethod
    def from_dict(cls, data):
        """dict에서 Quest 인스턴스 생성"""
        q = cls()
        q.unique_id = data.get("unique_id", "")
        q.name = data.get("name", "Unknown Quest")
        q.description = data.get("description", "")
        q.category = data.get("category", "side")
        q.prerequisites = data.get("prerequisites", [])
        q.conditions = data.get("conditions", [])
        q.rewards = data.get("rewards", [])
        q.giver = data.get("giver")
        q.reporter = data.get("reporter")
        q.dialogs = data.get("dialogs", {})
        q.repeatable = data.get("repeatable", False)
        q.visibility_conditions = data.get("visibility_conditions", {})
        return q

    def get_status(self):
        return get_quest_manager().get_quest_status(self.unique_id)

    def get_progress(self):
        return get_quest_manager().get_quest_progress(self.unique_id)

    def get_completion_result(self, context=None):
        """퀘스트 완료 결과 텍스트 (템플릿 포매팅)"""
        if context is None:
            context = {}
        result_template = self.dialogs.get("result")
        if result_template:
            if isinstance(result_template, str):
                try:
                    return result_template.format(**context)
                except KeyError:
                    return result_template
            elif isinstance(result_template, list):
                text = "\n".join(result_template)
                try:
                    return text.format(**context)
                except KeyError:
                    return text
        complete_pages = self.dialogs.get("complete", [self.name + " 완료"])
        return "\n".join(complete_pages) if isinstance(complete_pages, list) else str(complete_pages)


# ============================================
# 퀘스트 레지스트리
# ============================================

_quest_registry = {}


def register_quest(cls):
    """퀘스트 클래스 등록 데코레이터"""
    if cls.unique_id:
        _quest_registry[cls.unique_id] = cls
    return cls


def register_quest_instance(quest_instance):
    """Quest 인스턴스를 레지스트리에 등록 (dict → Quest → 래퍼 클래스)"""
    class _Wrapper(Quest):
        pass
    for attr in ("unique_id", "name", "description", "category", "prerequisites",
                 "conditions", "rewards", "giver", "reporter", "dialogs",
                 "repeatable", "visibility_conditions"):
        setattr(_Wrapper, attr, getattr(quest_instance, attr))
    _quest_registry[quest_instance.unique_id] = _Wrapper


def get_quest_class(unique_id):
    return _quest_registry.get(unique_id)


def get_all_quest_classes():
    return dict(_quest_registry)


# ============================================
# 헬퍼
# ============================================

def _action_log(msg):
    """안전한 action_log (API 없으면 무시)"""
    try:
        morld.add_action_log(msg)
    except (AttributeError, Exception):
        pass


# ============================================
# QuestManager
# ============================================

class QuestManager:
    """퀘스트 상태 관리 코어. 시나리오에서 서브클래스로 확장 가능."""

    def __init__(self):
        self._quest_instances = {}
        self._quest_results = {}

    # --- 내부 헬퍼 ---

    def _get_player_id(self):
        return morld.get_player_id()

    def _prop_key(self, quest_id, suffix):
        return "퀘스트:" + quest_id + ":" + suffix

    def _get_quest_instance(self, quest_id):
        if quest_id not in self._quest_instances:
            cls = get_quest_class(quest_id)
            if cls:
                self._quest_instances[quest_id] = cls()
        return self._quest_instances.get(quest_id)

    def _get_current_day(self):
        game_time = morld.get_game_time()
        return game_time // 86_400_000

    # --- 상태 조회 ---

    def get_quest_status(self, quest_id):
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return QuestStatus.LOCKED

        quest = self._get_quest_instance(quest_id)

        # 반복 퀘스트 일일 초기화
        if quest and quest.repeatable and self._should_reset_daily(quest_id, props):
            self._reset_daily(quest_id)
            props = morld.get_unit_props(player_id)

        status_value = props.get(self._prop_key(quest_id, "상태"), 0) if props else 0
        if status_value <= 0:
            if quest and self._check_prerequisites(quest):
                return QuestStatus.AVAILABLE
            return QuestStatus.LOCKED

        if status_value in (QuestStatus.AVAILABLE, QuestStatus.IN_PROGRESS,
                            QuestStatus.COMPLETED, QuestStatus.FINISHED):
            return status_value
        return QuestStatus.LOCKED

    def _should_reset_daily(self, quest_id, props):
        finished_day = props.get(self._prop_key(quest_id, "완료일"), 0)
        if finished_day <= 0:
            return False
        return self._get_current_day() > finished_day

    def _reset_daily(self, quest_id):
        player_id = self._get_player_id()
        for suffix in ("상태", "완료일", "수락시각"):
            morld.set_unit_prop(player_id, self._prop_key(quest_id, suffix), 0)
        self._clear_condition_props(quest_id)

    def _clear_condition_props(self, quest_id):
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return
        prefix = "퀘스트:" + quest_id + ":"
        skip = {"상태", "완료일", "수락시각"}
        for key in list(props.keys()):
            if key.startswith(prefix):
                suffix = key[len(prefix):]
                if suffix not in skip:
                    morld.set_unit_prop(player_id, key, 0)

    def get_quest_progress(self, quest_id):
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return {"current": 0, "total": 0, "conditions": []}
        player_id = self._get_player_id()
        conditions_status = []
        met_count = 0
        for i, cond in enumerate(quest.conditions):
            is_met = check_condition(player_id, cond, quest_id)
            desc = get_condition_description(cond)
            conditions_status.append({"index": i, "description": desc, "is_met": is_met, "condition": cond})
            if is_met:
                met_count += 1
        return {"current": met_count, "total": len(quest.conditions), "conditions": conditions_status}

    def get_quests_by_status(self, status):
        result = []
        for quest_id in _quest_registry:
            if self.get_quest_status(quest_id) == status:
                q = self._get_quest_instance(quest_id)
                if q:
                    result.append(q)
        return result

    def get_active_quests(self):
        return self.get_quests_by_status(QuestStatus.IN_PROGRESS)

    # --- 선행/표시 조건 ---

    def _check_prerequisites(self, quest):
        for prereq_id in quest.prerequisites:
            status = self.get_quest_status(prereq_id)
            if status not in (QuestStatus.COMPLETED, QuestStatus.FINISHED):
                return False
        return True

    def check_visibility(self, quest):
        """표시 조건 체크 (기본: prop만). 서브클래스에서 확장."""
        if not quest.visibility_conditions:
            return True
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return False
        for key, required in quest.visibility_conditions.items():
            if props.get(key, 0) < required:
                return False
        return True

    # --- NPC 관련 조회 ---

    def get_available_quests_from(self, giver_unique_id, check_visibility=True):
        result = []
        for quest_id in _quest_registry:
            if self.get_quest_status(quest_id) != QuestStatus.AVAILABLE:
                continue
            quest = self._get_quest_instance(quest_id)
            if not quest or quest.giver != giver_unique_id:
                continue
            if check_visibility and not self.check_visibility(quest):
                continue
            result.append(quest)
        return result

    def get_in_progress_quests_for(self, npc_unique_id):
        result = []
        for quest in self.get_active_quests():
            if quest.reporter == npc_unique_id or quest.giver == npc_unique_id:
                result.append(quest)
        return result

    def get_completable_quests_for(self, npc_unique_id):
        result = []
        for quest in self.get_quests_by_status(QuestStatus.COMPLETED):
            if quest.reporter == npc_unique_id:
                result.append(quest)
        return result

    # --- 상태 변경 ---

    def _set_status(self, quest_id, status):
        player_id = self._get_player_id()
        morld.set_unit_prop(player_id, self._prop_key(quest_id, "상태"), status)

    def give_quest(self, quest_id):
        if self.get_quest_status(quest_id) != QuestStatus.AVAILABLE:
            return False
        return self.accept_quest(quest_id)

    def accept_quest(self, quest_id):
        status = self.get_quest_status(quest_id)
        if status not in (QuestStatus.AVAILABLE, QuestStatus.LOCKED):
            return False
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False
        if not self._check_prerequisites(quest):
            return False
        self._set_status(quest_id, QuestStatus.IN_PROGRESS)
        player_id = self._get_player_id()
        morld.set_unit_prop(player_id, self._prop_key(quest_id, "수락시각"), morld.get_game_time())
        _action_log("퀘스트 '" + quest.name + "' 수락")
        self.on_quest_accepted(quest_id, quest)
        return True

    def check_quest_conditions(self, quest_id):
        if self.get_quest_status(quest_id) != QuestStatus.IN_PROGRESS:
            return False
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False
        player_id = self._get_player_id()
        for cond in quest.conditions:
            if not check_condition(player_id, cond, quest_id):
                return False
        # 모든 조건 충족
        self._set_status(quest_id, QuestStatus.COMPLETED)
        if quest.reporter is None:
            _action_log("퀘스트 '" + quest.name + "' 조건 충족!")
            self.claim_reward(quest_id)
        else:
            _action_log("퀘스트 '" + quest.name + "' 조건 충족! " + str(quest.reporter) + "에게 보고하자.")
        return True

    def complete_quest(self, quest_id):
        if self.get_quest_status(quest_id) != QuestStatus.IN_PROGRESS:
            return False
        self._set_status(quest_id, QuestStatus.COMPLETED)
        return True

    def fail_quest(self, quest_id, reason=""):
        """퀘스트 실패 처리. 기본: LOCKED로 리셋. 서브클래스에서 확장."""
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False
        self._set_status(quest_id, QuestStatus.LOCKED)
        self._clear_condition_props(quest_id)
        player_id = self._get_player_id()
        morld.set_unit_prop(player_id, self._prop_key(quest_id, "수락시각"), 0)
        msg = "퀘스트 '" + quest.name + "' 실패"
        if reason:
            msg += " (" + reason + ")"
        _action_log(msg)
        self.on_quest_failed(quest_id, quest, reason)
        return True

    def claim_reward(self, quest_id, context=None):
        if self.get_quest_status(quest_id) != QuestStatus.COMPLETED:
            return False
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False
        player_id = self._get_player_id()

        if context is None:
            context = self.collect_completion_context(quest_id, quest)

        # 결과 텍스트
        if not quest.repeatable:
            self._quest_results[quest_id] = quest.get_completion_result(context)

        # 보상 지급
        for reward in quest.rewards:
            apply_reward(player_id, reward)

        # 상태 전환
        if quest.repeatable:
            morld.set_unit_prop(player_id, self._prop_key(quest_id, "완료일"), self._get_current_day())
            morld.set_unit_prop(player_id, self._prop_key(quest_id, "상태"), 0)
            self._clear_condition_props(quest_id)
            _action_log("퀘스트 '" + quest.name + "' 완료! (반복 가능)")
        else:
            self._set_status(quest_id, QuestStatus.FINISHED)
            _action_log("퀘스트 '" + quest.name + "' 완료!")

        self.on_quest_completed(quest_id, quest)
        return True

    def get_quest_result(self, quest_id):
        if quest_id in self._quest_results:
            return self._quest_results[quest_id]
        quest = self._get_quest_instance(quest_id)
        if quest:
            return quest.get_completion_result({})
        return None

    # --- 훅 (서브클래스 확장용) ---

    def collect_completion_context(self, quest_id, quest):
        """완료 컨텍스트 수집. 서브클래스에서 오버라이드."""
        return {"player_id": self._get_player_id(), "quest_name": quest.name}

    def on_quest_accepted(self, quest_id, quest):
        """퀘스트 수락 후 훅. 서브클래스에서 오버라이드."""
        pass

    def on_quest_completed(self, quest_id, quest):
        """퀘스트 완료 후 훅. 서브클래스에서 오버라이드."""
        pass

    def on_quest_failed(self, quest_id, quest, reason):
        """퀘스트 실패 후 훅. 서브클래스에서 오버라이드."""
        pass


# ============================================
# 전역 인스턴스
# ============================================

_quest_manager = QuestManager()


def get_quest_manager():
    return _quest_manager


def set_quest_manager(manager):
    """시나리오별 QuestManager 서브클래스로 교체"""
    global _quest_manager
    _quest_manager = manager


# 편의 참조 (모듈 레벨에서 quest_manager.xxx 접근용)
# NOTE: set_quest_manager 후에도 이 참조는 갱신되지 않음.
#       동적 접근이 필요하면 get_quest_manager() 사용.

# ============================================
# 기본 조건 구현
# ============================================

def _check_reach(player_id, condition, quest_id):
    """위치 도착 조건. region_id/location_id 정수 기반."""
    player_loc = morld.get_unit_location(player_id)
    if not player_loc:
        return False
    current_region, current_location = player_loc
    target_region = condition.get("region_id")
    target_location = condition.get("location_id")
    if target_location is None:
        return current_region == target_region
    return current_region == target_region and current_location == target_location


def _desc_reach(condition):
    region_id = condition.get("region_id", 0)
    location_id = condition.get("location_id")
    try:
        info = morld.get_location_info(region_id, location_id)
        if info and info.get("name"):
            return info["name"] + "에 도착"
    except Exception:
        pass
    if location_id is not None:
        return "지역 " + str(region_id) + "-" + str(location_id) + "에 도착"
    return "지역 " + str(region_id) + "에 도착"


def _check_prop(player_id, condition, quest_id):
    """속성 값 조건."""
    prop_name = condition.get("prop")
    required_value = condition.get("value", 0)
    target = condition.get("target")
    if not prop_name:
        return False
    if target:
        target_id = morld.find_unit_by_unique_id(target)
        if not target_id:
            return False
        props = morld.get_unit_props(target_id)
    else:
        props = morld.get_unit_props(player_id)
    if not props:
        return False
    return props.get(prop_name, 0) >= required_value


def _desc_prop(condition):
    prop = condition.get("prop", "???")
    value = condition.get("value", 0)
    return prop + " >= " + str(value)


def _check_wait(player_id, condition, quest_id):
    """시간 경과 조건."""
    required_hours = condition.get("hours", 0)
    props = morld.get_unit_props(player_id)
    if not props:
        return False
    accept_time = props.get("퀘스트:" + quest_id + ":수락시각", 0)
    if accept_time <= 0:
        return False
    elapsed_hours = (morld.get_game_time() - accept_time) / 3_600_000
    return elapsed_hours >= required_hours


def _desc_wait(condition):
    hours = condition.get("hours", 0)
    return str(hours) + "시간 경과"


def _check_all(player_id, condition, quest_id):
    """모든 조건 충족 (AND)."""
    for sub in condition.get("conditions", []):
        if not check_condition(player_id, sub, quest_id):
            return False
    return True


def _desc_all(condition):
    n = len(condition.get("conditions", []))
    return "모든 조건 충족 (" + str(n) + "개)"


def _check_any(player_id, condition, quest_id):
    """하나라도 충족 (OR)."""
    for sub in condition.get("conditions", []):
        if check_condition(player_id, sub, quest_id):
            return True
    return False


def _desc_any(condition):
    n = len(condition.get("conditions", []))
    return "조건 중 하나 충족 (" + str(n) + "개)"


def _check_quest_completed(player_id, condition, quest_id):
    """다른 퀘스트 완료 여부."""
    target = condition.get("quest")
    if not target:
        return False
    status = get_quest_manager().get_quest_status(target)
    return status in (QuestStatus.COMPLETED, QuestStatus.FINISHED)


def _desc_quest_completed(condition):
    quest = condition.get("quest", "???")
    return "퀘스트 '" + quest + "' 완료"


# 기본 보상

def _apply_prop_reward(player_id, reward):
    """속성 변경 보상."""
    target = reward.get("target")
    prop_name = reward.get("prop")
    value = reward.get("value", 0)
    if not prop_name:
        return False
    if target and target != "player":
        target_id = morld.find_unit_by_unique_id(target)
        if not target_id:
            return False
    else:
        target_id = player_id
    morld.modify_prop(target_id, prop_name, value)
    return True


def _desc_prop_reward(reward):
    prop = reward.get("prop", "???")
    value = reward.get("value", 0)
    sign = "+" if value >= 0 else ""
    return prop + " " + sign + str(value)


def _apply_unlock_quest_reward(player_id, reward):
    """퀘스트 해금 보상 (선행 조건 체크에서 자동 처리)."""
    quest_id = reward.get("quest")
    if not quest_id:
        return False
    print("[Quest Reward] Quest unlocked: " + quest_id)
    return True


def _desc_unlock_quest_reward(reward):
    quest = reward.get("quest", "???")
    return "퀘스트 해금: " + quest


# ============================================
# 기본 조건/보상 자동 등록
# ============================================

def _register_builtins():
    register_condition_type("reach", _check_reach, _desc_reach)
    register_condition_type("prop", _check_prop, _desc_prop)
    register_condition_type("wait", _check_wait, _desc_wait)
    register_condition_type("all", _check_all, _desc_all)
    register_condition_type("any", _check_any, _desc_any)
    register_condition_type("quest_completed", _check_quest_completed, _desc_quest_completed)

    register_reward_type("prop", _apply_prop_reward, _desc_prop_reward)
    register_reward_type("unlock_quest", _apply_unlock_quest_reward, _desc_unlock_quest_reward)


_register_builtins()


# ============================================
# 편의 API (morld 래퍼 / 시나리오 초기화용)
# ============================================

def api_give_quest(quest_id):
    return get_quest_manager().give_quest(quest_id)


def api_get_quest_status(quest_id):
    return QuestStatus.name_of(get_quest_manager().get_quest_status(quest_id))


def api_get_active_quests():
    return [q.unique_id for q in get_quest_manager().get_active_quests()]


def api_get_quest_progress(quest_id):
    return get_quest_manager().get_quest_progress(quest_id)


def api_complete_quest(quest_id):
    return get_quest_manager().complete_quest(quest_id)


def api_check_quest_conditions(quest_id):
    return get_quest_manager().check_quest_conditions(quest_id)


def reset():
    """챕터 전환 시 리셋"""
    global _quest_manager
    _quest_manager = QuestManager()
    _quest_registry.clear()
    _register_builtins()
