# quest/__init__.py — S02 퀘스트 시스템
#
# engine/quest.py의 코어 프레임워크를 기반으로 S02 전용 확장:
#   - Quest: dialog 메서드 (offer/complete/progress)
#   - S02QuestManager: 표시 조건, 완료 컨텍스트, 이벤트 연동
#   - UI: render_quest_ui, show_quest_ui
#   - 초기화: register_character_quests, initialize_quest_system
#
# 하위 호환: 기존 `from quest import quest_manager, QuestStatus` 등 모두 동작.

import morld
import ui
from ui_style import style_success, style_muted, style_highlight, style_info

# 엔진 코어 임포트
from engine.quest import (
    QuestStatus,
    Quest as _EngineQuest,
    QuestManager as _EngineQuestManager,
    register_quest,
    register_quest_instance,
    get_quest_class,
    get_all_quest_classes,
    get_quest_manager,
    set_quest_manager,
    check_condition,
    get_condition_description,
    apply_reward,
    get_reward_description,
)


# ============================================
# S02 Quest — dialog 메서드 추가
# ============================================

class Quest(_EngineQuest):
    """S02 Quest — NPC dialog 메서드 포함"""

    def offer_dialog(self):
        """퀘스트 제안 다이얼로그 (Generator)"""
        offer_pages = self.dialogs.get("offer", ["퀘스트: " + self.name])
        choice_text = "\n".join(offer_pages) + "\n\n"
        choice_text += "[url=@ret:accept]수락[/url]  "
        choice_text += "[url=@ret:decline]거절[/url]"
        result = yield ui.dialog(choice_text, autofill="off")
        if result == "accept":
            accept_pages = self.dialogs.get("accept", ["퀘스트를 수락했습니다."])
            yield ui.dialog(accept_pages)
        else:
            decline_pages = self.dialogs.get("decline", ["퀘스트를 거절했습니다."])
            yield ui.dialog(decline_pages)
        return result

    def complete_dialog(self):
        """퀘스트 완료 다이얼로그 (Generator)"""
        complete_pages = self.dialogs.get("complete", ["'" + self.name + "' 퀘스트 완료!"])
        yield ui.dialog(complete_pages)

    def progress_dialog(self):
        """퀘스트 진행 중 다이얼로그 (Generator)"""
        progress_pages = self.dialogs.get("progress", ["퀘스트 진행 중..."])
        yield ui.dialog(progress_pages)


# ============================================
# S02 QuestManager — 확장
# ============================================

class S02QuestManager(_EngineQuestManager):
    """S02 전용 QuestManager 확장"""

    def check_visibility(self, quest):
        """표시 조건 — 아이템 분기 추가"""
        if not quest.visibility_conditions:
            return True
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return False
        for key, required in quest.visibility_conditions.items():
            if key.startswith("아이템:"):
                item_id = key.split(":", 1)[1]
                count = morld.get_item_count(player_id, item_id)
                if count < required:
                    return False
            else:
                if props.get(key, 0) < required:
                    return False
        return True

    def collect_completion_context(self, quest_id, quest):
        """완료 컨텍스트 — meet/talk/reach 정보 수집"""
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id) or {}
        context = {"player_id": player_id, "quest_name": quest.name}
        for cond in quest.conditions:
            cond_type = cond.get("type")
            if cond_type == "meet":
                target = cond.get("target")
                if target:
                    npc_name = self._get_npc_name(target)
                    context["met_npc"] = npc_name or target
                    context["met_npc_id"] = target
            elif cond_type == "meet_anyone":
                for key, value in props.items():
                    if key.startswith("관계:") and key.endswith(":진척도") and value >= 1:
                        context["met_npc"] = key.split(":")[1]
                        break
            elif cond_type == "reach":
                location_name = cond.get("location_name")
                if location_name:
                    context["reached_location"] = location_name
                elif cond.get("region_id") is not None and cond.get("location_id") is not None:
                    context["reached_location"] = "(" + str(cond["region_id"]) + ", " + str(cond["location_id"]) + ")"
            elif cond_type == "talk":
                target = cond.get("target")
                if target:
                    context["talked_npc"] = self._get_npc_name(target) or target
        return context

    def _get_npc_name(self, unique_id):
        """NPC unique_id → 이름 조회"""
        try:
            from assets import characters
            for char_cls in characters.get_all_character_classes():
                if hasattr(char_cls, 'unique_id') and char_cls.unique_id == unique_id:
                    return char_cls.name
        except Exception:
            pass
        return None

    # --- 이벤트 연동 ---

    def check_reach_conditions(self, region_id, location_id):
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def check_meet_conditions(self, unit_id, other_id):
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def update_collect_condition(self, item_unique_id, count):
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def update_deliver_condition(self, target_unique_id, item_unique_id):
        player_id = self._get_player_id()
        for quest in self.get_active_quests():
            for cond in quest.conditions:
                if cond.get("type") != "deliver":
                    continue
                if cond.get("target") != target_unique_id:
                    continue
                if cond.get("item") != item_unique_id:
                    continue
                cond_key = self._prop_key(quest.unique_id,
                    "deliver:" + target_unique_id + ":" + item_unique_id)
                current = (morld.get_unit_props(player_id) or {}).get(cond_key, 0)
                morld.set_unit_prop(player_id, cond_key, current + 1)
            self.check_quest_conditions(quest.unique_id)


# ============================================
# 전역 인스턴스
# ============================================

quest_manager = S02QuestManager()
set_quest_manager(quest_manager)


# ============================================
# UI 렌더링
# ============================================

def render_quest_ui(selected_quest_id=None, debug_mode=False):
    """퀘스트 UI 렌더링"""
    lines = ["[b]퀘스트[/b]", ""]

    if selected_quest_id:
        quest = quest_manager._get_quest_instance(selected_quest_id)
        if quest:
            status = quest_manager.get_quest_status(selected_quest_id)
            lines.append("[b]" + quest.name + "[/b]")
            lines.append("")
            if status == QuestStatus.FINISHED:
                result_text = quest_manager.get_quest_result(selected_quest_id)
                if result_text:
                    lines.append("[기록]")
                    lines.append(result_text)
                else:
                    lines.append(quest.description)
                lines.append("")
            else:
                lines.append(quest.description)
                lines.append("")
                progress = quest_manager.get_quest_progress(selected_quest_id)
                lines.append("[조건]")
                for cond_info in progress["conditions"]:
                    cond_status = style_success("✓") if cond_info["is_met"] else style_muted("○")
                    lines.append("  " + cond_status + " " + cond_info["description"])
                lines.append("")
            lines.append("[url=@proc:back]← 목록으로[/url]")
            return "\n".join(lines)

    in_progress = quest_manager.get_quests_by_status(QuestStatus.IN_PROGRESS)
    if in_progress:
        lines.append(style_highlight("[진행 중]"))
        for quest in in_progress:
            lines.append("  [url=@proc:select:" + quest.unique_id + "]" + quest.name + "[/url]")
        lines.append("")

    completed = quest_manager.get_quests_by_status(QuestStatus.COMPLETED)
    if completed:
        lines.append(style_success("[완료 - 보상 수령 가능]"))
        for quest in completed:
            if quest.reporter:
                lines.append("  [b]" + quest.name + "[/b] - " + quest.reporter + "에게 보고")
            else:
                lines.append("  [url=@proc:claim:" + quest.unique_id + "]" + quest.name + " (수령)[/url]")
        lines.append("")

    finished = [q for q in quest_manager.get_quests_by_status(QuestStatus.FINISHED) if not q.repeatable]
    if finished:
        finished_items = []
        for quest in finished:
            finished_items.append("  [url=@proc:select:" + quest.unique_id + "]" + style_muted(quest.name) + "[/url]")
        finished_content = "\n".join(finished_items)
        lines.append("[toggle key=finished]" + style_muted("완료된 퀘스트 (" + str(len(finished)) + ")") + "[content]" + finished_content + "[/toggle]")
        lines.append("")

    if debug_mode:
        available = quest_manager.get_quests_by_status(QuestStatus.AVAILABLE)
        if available:
            lines.append(style_info("[수락 가능 - DEBUG]"))
            for quest in available:
                if quest.giver:
                    lines.append("  " + quest.name + " - " + quest.giver + "에게서")
                else:
                    lines.append("  " + quest.name)
            lines.append("")

    if not in_progress and not completed:
        lines.append(style_muted("진행 중인 퀘스트가 없습니다."))
        lines.append("")

    lines.append("[url=@finish]닫기[/url]")
    return "\n".join(lines)


def show_quest_ui(debug_mode=True):
    """퀘스트 UI 다이얼로그 (Generator)"""
    state = {"refresh": True, "selected": None}

    def proc(action):
        if action == "init" or state.get("refresh"):
            state["refresh"] = False
            return render_quest_ui(state.get("selected"), debug_mode)
        if action.startswith("select:"):
            quest_id = action.split(":", 1)[1]
            state["selected"] = quest_id
            return render_quest_ui(quest_id, debug_mode)
        if action == "back":
            state["selected"] = None
            return render_quest_ui(None, debug_mode)
        if action.startswith("claim:"):
            quest_id = action.split(":", 1)[1]
            quest_manager.claim_reward(quest_id)
            state["refresh"] = True
            return render_quest_ui(state.get("selected"), debug_mode)
        return None

    yield ui.dialog("", autofill="off", proc=proc, result=state)


# ============================================
# morld API 래퍼
# ============================================

def give_quest(quest_id):
    return quest_manager.give_quest(quest_id)


def get_quest_status(quest_id):
    return QuestStatus.name_of(quest_manager.get_quest_status(quest_id))


def get_active_quests():
    return [q.unique_id for q in quest_manager.get_active_quests()]


def get_quest_progress(quest_id):
    return quest_manager.get_quest_progress(quest_id)


def complete_quest(quest_id):
    return quest_manager.complete_quest(quest_id)


def check_quest_conditions(quest_id):
    return quest_manager.check_quest_conditions(quest_id)


# ============================================
# 캐릭터 퀘스트 자동 등록
# ============================================

def _register_quest_instance_s02(quest_instance):
    """Quest 인스턴스를 S02 Quest 기반 래퍼로 등록"""
    from engine.quest import _quest_registry

    class _Wrapper(Quest):
        pass
    for attr in ("unique_id", "name", "description", "category", "prerequisites",
                 "conditions", "rewards", "giver", "reporter", "dialogs",
                 "repeatable", "visibility_conditions"):
        setattr(_Wrapper, attr, getattr(quest_instance, attr))
    _quest_registry[quest_instance.unique_id] = _Wrapper


def register_character_quests():
    """모든 캐릭터의 개인 퀘스트를 등록"""
    from assets.characters import get_all_character_classes
    for char_cls in get_all_character_classes():
        quests_data = char_cls.get_character_quests()
        for quest_data in quests_data:
            quest = Quest.from_dict(quest_data)
            if quest.unique_id:
                _register_quest_instance_s02(quest)


def initialize_quest_system():
    """퀘스트 시스템 초기화"""
    from .conditions import register_s02_conditions
    from .rewards import register_s02_rewards

    # S02 플러그인 등록
    register_s02_conditions()
    register_s02_rewards()

    # quest/quests/ 폴더 import (자동 등록)
    from quest import quests  # noqa: F401

    # 캐릭터 개인 퀘스트 등록
    register_character_quests()

    from engine.quest import _quest_registry
    print("[Quest] Registered " + str(len(_quest_registry)) + " quests")
