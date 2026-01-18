# quest/__init__.py
"""
퀘스트 시스템 모듈

퀘스트의 상태 관리, 조건 체크, 보상 처리를 담당합니다.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
import morld

from .conditions import check_condition, get_condition_description
from .rewards import apply_reward


# ============================================
# 퀘스트 상태
# ============================================

class QuestStatus(Enum):
    """
    퀘스트 상태 (정수 기반)

    morld.set_unit_prop()이 정수만 지원하므로 정수 값 사용.
    """
    LOCKED = 0           # 잠금 (선행 조건 미충족)
    AVAILABLE = 1        # 수락 가능
    IN_PROGRESS = 2      # 진행 중
    COMPLETED = 3        # 완료 (보상 수령 전)
    FINISHED = 4         # 완료 (보상 수령 후)


# ============================================
# 퀘스트 베이스 클래스
# ============================================

class Quest:
    """퀘스트 베이스 클래스"""

    unique_id: str = ""
    name: str = "Unknown Quest"
    description: str = ""
    category: str = "side"  # main, side, daily, personal

    # 선행 조건
    prerequisites: List[str] = []

    # 완료 조건
    conditions: List[dict] = []

    # 보상
    rewards: List[dict] = []

    # 퀘스트 지급자 (None이면 이벤트로 지급)
    giver: Optional[str] = None

    # 퀘스트 완료 보고 대상 (None이면 자동 완료)
    reporter: Optional[str] = None

    # 퀘스트 대화
    dialogs: Dict[str, List[str]] = {}

    # 반복 퀘스트 설정
    repeatable: bool = False  # 반복 가능 여부 (일일 초기화)

    # 표시 조건 (# 마커용) - 조건 충족 시에만 NPC에게서 퀘스트 보임
    # 예: {"호감도:세라": 30} → 세라 호감도 30 이상일 때만 표시
    visibility_conditions: Dict[str, Any] = {}

    @classmethod
    def from_dict(cls, data: dict) -> 'Quest':
        """
        dict에서 Quest 인스턴스 생성

        캐릭터 파일의 CHARACTER_QUESTS에서 사용됩니다.

        Args:
            data: 퀘스트 정의 dict

        Returns:
            Quest 인스턴스
        """
        quest = cls()
        quest.unique_id = data.get("unique_id", "")
        quest.name = data.get("name", "Unknown Quest")
        quest.description = data.get("description", "")
        quest.category = data.get("category", "personal")
        quest.prerequisites = data.get("prerequisites", [])
        quest.conditions = data.get("conditions", [])
        quest.rewards = data.get("rewards", [])
        quest.giver = data.get("giver")
        quest.reporter = data.get("reporter")
        quest.dialogs = data.get("dialogs", {})
        quest.repeatable = data.get("repeatable", False)
        quest.visibility_conditions = data.get("visibility_conditions", {})
        return quest

    def get_status(self) -> QuestStatus:
        """현재 퀘스트 상태 조회"""
        return quest_manager.get_quest_status(self.unique_id)

    def get_progress(self) -> Dict[str, Any]:
        """퀘스트 진행 상황 조회"""
        return quest_manager.get_quest_progress(self.unique_id)

    def offer_dialog(self):
        """퀘스트 제안 다이얼로그 (Generator)"""
        offer_pages = self.dialogs.get("offer", [f"퀘스트: {self.name}"])

        # 수락/거절 선택지 추가
        choice_text = "\n".join(offer_pages) + "\n\n"
        choice_text += "[url=@ret:accept]수락[/url]  "
        choice_text += "[url=@ret:decline]거절[/url]"

        result = yield morld.dialog(choice_text, autofill="off")

        if result == "accept":
            accept_pages = self.dialogs.get("accept", ["퀘스트를 수락했습니다."])
            yield morld.dialog(accept_pages)
        else:
            decline_pages = self.dialogs.get("decline", ["퀘스트를 거절했습니다."])
            yield morld.dialog(decline_pages)

        return result

    def complete_dialog(self):
        """퀘스트 완료 다이얼로그 (Generator)"""
        complete_pages = self.dialogs.get("complete", [f"'{self.name}' 퀘스트 완료!"])
        yield morld.dialog(complete_pages)

    def progress_dialog(self):
        """퀘스트 진행 중 다이얼로그 (Generator)"""
        progress_pages = self.dialogs.get("progress", ["퀘스트 진행 중..."])
        yield morld.dialog(progress_pages)

    def get_completion_result(self, context: Dict[str, Any] = None) -> str:
        """
        퀘스트 완료 결과 텍스트 생성

        서브클래스에서 오버라이드하여 동적 결과 텍스트를 생성합니다.
        context에는 퀘스트 완료 시점의 정보가 담깁니다:
        - met_npc: 만난 NPC 이름 (meet 조건)
        - reached_location: 도착한 장소 이름 (reach 조건)
        - player_id: 플레이어 ID

        Args:
            context: 완료 시점 컨텍스트 정보

        Returns:
            저장될 결과 텍스트 (UI에서 표시)
        """
        # 기본 구현: dialogs의 "result" 키 사용, 없으면 "complete" 사용
        if context is None:
            context = {}

        result_template = self.dialogs.get("result")
        if result_template:
            # 템플릿 문자열이면 context로 포매팅
            if isinstance(result_template, str):
                try:
                    return result_template.format(**context)
                except KeyError:
                    return result_template
            # 리스트면 줄바꿈으로 연결 후 포매팅
            elif isinstance(result_template, list):
                text = "\n".join(result_template)
                try:
                    return text.format(**context)
                except KeyError:
                    return text

        # result가 없으면 complete 다이얼로그 사용
        complete_pages = self.dialogs.get("complete", [f"'{self.name}' 완료"])
        return "\n".join(complete_pages)


# ============================================
# 퀘스트 등록 시스템
# ============================================

_quest_registry: Dict[str, type] = {}


def register_quest(cls):
    """퀘스트 클래스 등록 데코레이터"""
    if cls.unique_id:
        _quest_registry[cls.unique_id] = cls
    return cls


def get_quest_class(unique_id: str) -> Optional[type]:
    """퀘스트 클래스 조회"""
    return _quest_registry.get(unique_id)


def get_all_quest_classes() -> Dict[str, type]:
    """모든 퀘스트 클래스 조회"""
    return dict(_quest_registry)


# ============================================
# 퀘스트 매니저
# ============================================

class QuestManager:
    """퀘스트 상태 관리 클래스"""

    def _get_player_id(self) -> int:
        """플레이어 ID 조회"""
        return morld.get_player_id()

    def _get_prop_key(self, quest_id: str, suffix: str) -> str:
        """퀘스트 관련 prop 키 생성"""
        return f"퀘스트:{quest_id}:{suffix}"

    def _get_quest_instance(self, quest_id: str) -> Optional[Quest]:
        """퀘스트 인스턴스 조회 (캐싱, lazy 초기화)"""
        # lazy 초기화로 모듈 로드 순서 문제 우회
        if not hasattr(self, '_quest_instances'):
            self._quest_instances = {}
        if quest_id not in self._quest_instances:
            quest_cls = get_quest_class(quest_id)
            if quest_cls:
                self._quest_instances[quest_id] = quest_cls()
        return self._quest_instances.get(quest_id)

    # ========================================
    # 상태 조회
    # ========================================

    def _get_current_day(self) -> int:
        """현재 게임 날짜 (일수) 계산"""
        game_time = morld.get_game_time()
        return game_time // 1440  # 1440분 = 24시간

    def _should_reset_daily_quest(self, quest_id: str, quest: Quest) -> bool:
        """일일 퀘스트 초기화 필요 여부 체크"""
        if not quest.repeatable:
            return False

        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return False

        # 완료된 날짜 확인
        finished_day_key = self._get_prop_key(quest_id, "완료일")
        finished_day = props.get(finished_day_key)

        if finished_day is None:
            return False

        current_day = self._get_current_day()
        return current_day > finished_day

    def _reset_daily_quest(self, quest_id: str):
        """일일 퀘스트 상태 초기화"""
        player_id = self._get_player_id()

        # 상태 초기화 (삭제)
        status_key = self._get_prop_key(quest_id, "상태")
        morld.clear_unit_prop(player_id, status_key)

        # 완료일 초기화 (삭제)
        finished_day_key = self._get_prop_key(quest_id, "완료일")
        morld.clear_unit_prop(player_id, finished_day_key)

        # 수락시각 초기화 (삭제)
        time_key = self._get_prop_key(quest_id, "수락시각")
        morld.clear_unit_prop(player_id, time_key)

        # 조건 관련 props 초기화
        self._clear_quest_condition_props(quest_id)

    def _clear_quest_condition_props(self, quest_id: str):
        """퀘스트 조건 관련 props 초기화"""
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return

        # 퀘스트 관련 모든 조건 props 삭제
        prefix = f"퀘스트:{quest_id}:"
        keys_to_clear = [k for k in props.keys() if k.startswith(prefix)]

        for key in keys_to_clear:
            # 상태, 완료일, 수락시각은 이미 처리했으므로 스킵
            suffix = key[len(prefix):]
            if suffix not in ("상태", "완료일", "수락시각"):
                morld.clear_unit_prop(player_id, key)

    def get_quest_status(self, quest_id: str) -> QuestStatus:
        """퀘스트 상태 조회"""
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return QuestStatus.LOCKED

        quest = self._get_quest_instance(quest_id)

        # 반복 퀘스트 일일 초기화 체크
        if quest and self._should_reset_daily_quest(quest_id, quest):
            self._reset_daily_quest(quest_id)
            # props 다시 조회 (초기화 후)
            props = morld.get_unit_props(player_id)

        status_key = self._get_prop_key(quest_id, "상태")
        status_value = props.get(status_key) if props else None

        if status_value is None:
            # 상태가 없으면 선행 조건 체크
            if quest and self._check_prerequisites(quest):
                return QuestStatus.AVAILABLE
            return QuestStatus.LOCKED

        try:
            return QuestStatus(status_value)
        except ValueError:
            return QuestStatus.LOCKED

    def get_quest_progress(self, quest_id: str) -> Dict[str, Any]:
        """퀘스트 진행 상황 조회"""
        quest = self._get_quest_instance(quest_id)
        if not quest:
            return {"current": 0, "total": 0, "conditions": []}

        player_id = self._get_player_id()
        conditions_status = []
        met_count = 0

        for i, cond in enumerate(quest.conditions):
            is_met = check_condition(player_id, cond, quest_id)
            desc = get_condition_description(cond)
            conditions_status.append({
                "index": i,
                "description": desc,
                "is_met": is_met,
                "condition": cond,
            })
            if is_met:
                met_count += 1

        return {
            "current": met_count,
            "total": len(quest.conditions),
            "conditions": conditions_status,
        }

    def get_quests_by_status(self, status: QuestStatus) -> List[Quest]:
        """특정 상태의 퀘스트 목록 조회"""
        result = []
        for quest_id, quest_cls in _quest_registry.items():
            if self.get_quest_status(quest_id) == status:
                quest = self._get_quest_instance(quest_id)
                if quest:
                    result.append(quest)
        return result

    def get_active_quests(self) -> List[Quest]:
        """진행 중인 퀘스트 목록"""
        return self.get_quests_by_status(QuestStatus.IN_PROGRESS)

    def _check_visibility_conditions(self, quest: Quest) -> bool:
        """
        퀘스트 표시 조건 체크

        visibility_conditions의 모든 조건이 충족되어야 True 반환.
        조건이 없으면(빈 dict) True 반환.

        조건 예시:
        - {"관계:세라:호감도": 30} → 세라 호감도가 30 이상
        - {"아이템:fishing_rod": 1} → 낚시대 보유
        """
        if not quest.visibility_conditions:
            return True

        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id)
        if not props:
            return False

        for key, required_value in quest.visibility_conditions.items():
            # 아이템 조건 체크
            if key.startswith("아이템:"):
                item_id = key.split(":", 1)[1]
                count = morld.get_item_count(player_id, item_id)
                if count < required_value:
                    return False
            else:
                # prop 조건 체크
                current_value = props.get(key, 0)
                if current_value < required_value:
                    return False

        return True

    def get_available_quests_from(self, giver_unique_id: str, check_visibility: bool = True) -> List[Quest]:
        """
        특정 NPC로부터 받을 수 있는 퀘스트 목록

        Args:
            giver_unique_id: NPC의 unique_id
            check_visibility: True면 visibility_conditions도 체크 (기본값)
        """
        result = []
        for quest_id, quest_cls in _quest_registry.items():
            quest = self._get_quest_instance(quest_id)
            if not quest:
                continue
            if quest.giver != giver_unique_id:
                continue
            if self.get_quest_status(quest_id) != QuestStatus.AVAILABLE:
                continue
            # 표시 조건 체크 (# 마커 역할)
            if check_visibility and not self._check_visibility_conditions(quest):
                continue
            result.append(quest)
        return result

    def get_in_progress_quests_for(self, npc_unique_id: str) -> List[Quest]:
        """특정 NPC 관련 진행 중 퀘스트 (보고 대상 또는 지급자)"""
        result = []
        for quest in self.get_active_quests():
            if quest.reporter == npc_unique_id or quest.giver == npc_unique_id:
                result.append(quest)
        return result

    def get_completable_quests_for(self, npc_unique_id: str) -> List[Quest]:
        """특정 NPC에게 보고 가능한 완료 퀘스트"""
        result = []
        for quest in self.get_quests_by_status(QuestStatus.COMPLETED):
            if quest.reporter == npc_unique_id:
                result.append(quest)
        return result

    # ========================================
    # 상태 변경
    # ========================================

    def _set_quest_status(self, quest_id: str, status: QuestStatus):
        """퀘스트 상태 설정"""
        player_id = self._get_player_id()
        status_key = self._get_prop_key(quest_id, "상태")
        morld.set_unit_prop(player_id, status_key, status.value)

    def _check_prerequisites(self, quest: Quest) -> bool:
        """선행 조건 체크"""
        for prereq_id in quest.prerequisites:
            status = self.get_quest_status(prereq_id)
            if status not in (QuestStatus.COMPLETED, QuestStatus.FINISHED):
                return False
        return True

    def give_quest(self, quest_id: str) -> bool:
        """퀘스트 지급 (이벤트용)"""
        status = self.get_quest_status(quest_id)
        if status != QuestStatus.AVAILABLE:
            return False
        return self.accept_quest(quest_id)

    def accept_quest(self, quest_id: str) -> bool:
        """퀘스트 수락"""
        status = self.get_quest_status(quest_id)
        if status not in (QuestStatus.AVAILABLE, QuestStatus.LOCKED):
            return False

        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False

        # 선행 조건 체크
        if not self._check_prerequisites(quest):
            return False

        # 상태 변경
        self._set_quest_status(quest_id, QuestStatus.IN_PROGRESS)

        # 수락 시각 기록
        player_id = self._get_player_id()
        time_key = self._get_prop_key(quest_id, "수락시각")
        morld.set_unit_prop(player_id, time_key, morld.get_game_time())

        morld.add_action_log(f"퀘스트 '{quest.name}' 수락")
        return True

    def check_quest_conditions(self, quest_id: str) -> bool:
        """퀘스트 조건 체크 및 완료 처리"""
        status = self.get_quest_status(quest_id)
        if status != QuestStatus.IN_PROGRESS:
            return False

        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False

        player_id = self._get_player_id()

        # 모든 조건 체크
        all_met = True
        for cond in quest.conditions:
            if not check_condition(player_id, cond, quest_id):
                all_met = False
                break

        if all_met:
            # 자동 완료 (reporter가 없으면)
            if quest.reporter is None:
                self._set_quest_status(quest_id, QuestStatus.COMPLETED)
                morld.add_action_log(f"퀘스트 '{quest.name}' 조건 충족!")
                # 자동 보상 지급
                self.claim_reward(quest_id)
            else:
                self._set_quest_status(quest_id, QuestStatus.COMPLETED)
                morld.add_action_log(f"퀘스트 '{quest.name}' 조건 충족! {quest.reporter}에게 보고하자.")
            return True

        return False

    def complete_quest(self, quest_id: str) -> bool:
        """퀘스트 강제 완료"""
        status = self.get_quest_status(quest_id)
        if status != QuestStatus.IN_PROGRESS:
            return False

        self._set_quest_status(quest_id, QuestStatus.COMPLETED)
        return True

    def claim_reward(self, quest_id: str, context: Dict[str, Any] = None) -> bool:
        """
        보상 수령

        Args:
            quest_id: 퀘스트 ID
            context: 완료 컨텍스트 (met_npc, reached_location 등)
        """
        status = self.get_quest_status(quest_id)
        if status != QuestStatus.COMPLETED:
            return False

        quest = self._get_quest_instance(quest_id)
        if not quest:
            return False

        player_id = self._get_player_id()

        # 컨텍스트 수집 (제공되지 않은 경우)
        if context is None:
            context = self._collect_completion_context(quest_id, quest)

        # 결과 텍스트 생성 및 저장 (일반 퀘스트만)
        if not quest.repeatable:
            result_text = quest.get_completion_result(context)
            self._save_quest_result(quest_id, result_text)

        # 보상 지급
        for reward in quest.rewards:
            apply_reward(player_id, reward)

        # 반복 퀘스트는 AVAILABLE로, 일반 퀘스트는 FINISHED로
        if quest.repeatable:
            # 반복 퀘스트: 완료일 기록 후 상태 초기화 (AVAILABLE로 복귀)
            finished_day_key = self._get_prop_key(quest_id, "완료일")
            morld.set_unit_prop(player_id, finished_day_key, self._get_current_day())

            # 상태 prop 삭제 (다음 날 _should_reset_daily_quest에서 처리)
            status_key = self._get_prop_key(quest_id, "상태")
            morld.clear_unit_prop(player_id, status_key)

            # 조건 관련 props 초기화
            self._clear_quest_condition_props(quest_id)

            morld.add_action_log(f"퀘스트 '{quest.name}' 완료! 보상 수령. (내일 다시 수행 가능)")
        else:
            # 일반 퀘스트: FINISHED로 변경
            self._set_quest_status(quest_id, QuestStatus.FINISHED)
            morld.add_action_log(f"퀘스트 '{quest.name}' 완료! 보상 수령.")

        # 다른 퀘스트 해금 체크
        self._check_unlock_quests()

        return True

    def _collect_completion_context(self, quest_id: str, quest: Quest) -> Dict[str, Any]:
        """
        퀘스트 완료 시 컨텍스트 수집

        조건에서 만난 NPC, 도착한 장소 등의 정보를 수집합니다.
        """
        player_id = self._get_player_id()
        props = morld.get_unit_props(player_id) or {}
        context = {"player_id": player_id, "quest_name": quest.name}

        # meet 조건에서 만난 NPC 찾기
        for cond in quest.conditions:
            cond_type = cond.get("type")

            if cond_type == "meet":
                target = cond.get("target")
                if target:
                    # NPC 이름 조회 (unique_id → 이름)
                    npc_name = self._get_npc_name(target)
                    context["met_npc"] = npc_name or target
                    context["met_npc_id"] = target

            elif cond_type == "meet_anyone":
                # 관계:*:진척도 에서 만난 NPC 찾기
                for key, value in props.items():
                    if key.startswith("관계:") and key.endswith(":진척도") and value >= 1:
                        # "관계:밀라:진척도" → "밀라"
                        npc_name = key.split(":")[1]
                        context["met_npc"] = npc_name
                        break

            elif cond_type == "reach":
                region = cond.get("region")
                location = cond.get("location")
                location_name = cond.get("location_name")
                if location_name:
                    context["reached_location"] = location_name
                elif region is not None and location is not None:
                    context["reached_location"] = f"({region}, {location})"

            elif cond_type == "talk":
                target = cond.get("target")
                if target:
                    npc_name = self._get_npc_name(target)
                    context["talked_npc"] = npc_name or target

        return context

    def _get_npc_name(self, unique_id: str) -> Optional[str]:
        """NPC unique_id로 이름 조회"""
        try:
            from assets import characters
            # 인스턴스 ID가 아닌 unique_id로 찾기
            for char_cls in characters.get_all_character_classes():
                if hasattr(char_cls, 'unique_id') and char_cls.unique_id == unique_id:
                    return char_cls.name
        except Exception:
            pass
        return None

    def _save_quest_result(self, quest_id: str, result_text: str):
        """퀘스트 결과 텍스트 저장"""
        # 결과 텍스트는 _quest_results 딕셔너리에 저장 (세션 내 유지)
        if not hasattr(self, '_quest_results'):
            self._quest_results = {}
        self._quest_results[quest_id] = result_text

    def get_quest_result(self, quest_id: str) -> Optional[str]:
        """저장된 퀘스트 결과 텍스트 조회"""
        if not hasattr(self, '_quest_results'):
            self._quest_results = {}

        # 저장된 결과가 있으면 반환
        if quest_id in self._quest_results:
            return self._quest_results[quest_id]

        # 저장된 결과가 없으면 기본 텍스트 생성
        quest = self._get_quest_instance(quest_id)
        if quest:
            return quest.get_completion_result({})

        return None

    def _check_unlock_quests(self):
        """선행 조건 충족으로 해금 가능한 퀘스트 체크"""
        for quest_id, quest_cls in _quest_registry.items():
            status = self.get_quest_status(quest_id)
            if status == QuestStatus.LOCKED:
                quest = self._get_quest_instance(quest_id)
                if quest and self._check_prerequisites(quest):
                    # AVAILABLE로 변경하지 않음 (get_quest_status에서 자동 판단)
                    pass

    # ========================================
    # 조건 업데이트 (이벤트 연동)
    # ========================================

    def check_reach_conditions(self, region_id: int, location_id: int):
        """reach 조건 체크 (on_reach 이벤트에서 호출)"""
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def check_meet_conditions(self, unit_id: int, other_id: int):
        """meet 조건 체크 (on_meet 이벤트에서 호출)"""
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def update_collect_condition(self, item_unique_id: str, count: int):
        """collect 조건 업데이트 (아이템 획득 시 호출)"""
        for quest in self.get_active_quests():
            self.check_quest_conditions(quest.unique_id)

    def update_deliver_condition(self, target_unique_id: str, item_unique_id: str):
        """deliver 조건 업데이트 (아이템 전달 시 호출)"""
        player_id = self._get_player_id()

        for quest in self.get_active_quests():
            for cond in quest.conditions:
                if cond.get("type") != "deliver":
                    continue
                if cond.get("target") != target_unique_id:
                    continue
                if cond.get("item") != item_unique_id:
                    continue

                # 전달 기록
                cond_key = self._get_prop_key(quest.unique_id, f"deliver:{target_unique_id}:{item_unique_id}")
                current = morld.get_unit_props(player_id).get(cond_key, 0)
                morld.set_unit_prop(player_id, cond_key, current + 1)

            self.check_quest_conditions(quest.unique_id)


# ============================================
# 전역 인스턴스
# ============================================

quest_manager = QuestManager()


# ============================================
# UI 렌더링
# ============================================

def render_quest_ui(selected_quest_id: str = None, debug_mode: bool = False) -> str:
    """
    퀘스트 UI 렌더링

    Args:
        selected_quest_id: 선택된 퀘스트 ID (세부 정보 표시)
        debug_mode: True면 수락 가능 퀘스트도 표시 (디버그용)
    """
    lines = ["[b]퀘스트[/b]", ""]

    # 선택된 퀘스트 세부 정보 표시
    if selected_quest_id:
        quest = quest_manager._get_quest_instance(selected_quest_id)
        if quest:
            status = quest_manager.get_quest_status(selected_quest_id)

            lines.append(f"[b]{quest.name}[/b]")
            lines.append("")

            # 완료된 퀘스트는 결과 텍스트 표시
            if status == QuestStatus.FINISHED:
                result_text = quest_manager.get_quest_result(selected_quest_id)
                if result_text:
                    lines.append("[기록]")
                    lines.append(result_text)
                else:
                    lines.append(f"{quest.description}")
                lines.append("")
            else:
                lines.append(f"{quest.description}")
                lines.append("")

                # 진행 상황 표시 (진행 중/완료 대기 퀘스트)
                progress = quest_manager.get_quest_progress(selected_quest_id)
                lines.append("[조건]")
                for cond_info in progress["conditions"]:
                    cond_status = "[color=lime]✓[/color]" if cond_info["is_met"] else "[color=gray]○[/color]"
                    lines.append(f"  {cond_status} {cond_info['description']}")
                lines.append("")

            lines.append("[url=@proc:back]← 목록으로[/url]")
            return "\n".join(lines)

    # 진행 중 퀘스트
    in_progress = quest_manager.get_quests_by_status(QuestStatus.IN_PROGRESS)
    if in_progress:
        lines.append("[color=yellow][진행 중][/color]")
        for quest in in_progress:
            # 클릭하면 세부 정보 표시
            lines.append(f"  [url=@proc:select:{quest.unique_id}]{quest.name}[/url]")
        lines.append("")

    # 완료 퀘스트 (보상 대기)
    completed = quest_manager.get_quests_by_status(QuestStatus.COMPLETED)
    if completed:
        lines.append("[color=lime][완료 - 보상 수령 가능][/color]")
        for quest in completed:
            if quest.reporter:
                lines.append(f"  [b]{quest.name}[/b] - {quest.reporter}에게 보고")
            else:
                lines.append(f"  [url=@proc:claim:{quest.unique_id}]{quest.name} (수령)[/url]")
        lines.append("")

    # 완료된 퀘스트 (접기/펼치기) - 반복 퀘스트는 제외
    finished = [q for q in quest_manager.get_quests_by_status(QuestStatus.FINISHED)
                if not q.repeatable]
    if finished:
        lines.append(f"[url=toggle:finished][color=gray]▶ 완료된 퀘스트 ({len(finished)})[/color][/url]")
        lines.append("[hidden=finished]")
        for quest in finished:
            # 클릭하면 결과 텍스트(기록) 보기
            lines.append(f"  [url=@proc:select:{quest.unique_id}][color=gray]{quest.name}[/color][/url]")
        lines.append("[/hidden=finished]")
        lines.append("")

    # 디버그 모드일 때만 수락 가능 퀘스트 표시
    if debug_mode:
        available = quest_manager.get_quests_by_status(QuestStatus.AVAILABLE)
        if available:
            lines.append("[color=cyan][수락 가능 - DEBUG][/color]")
            for quest in available:
                if quest.giver:
                    lines.append(f"  {quest.name} - {quest.giver}에게서")
                else:
                    lines.append(f"  {quest.name}")
            lines.append("")

    # 퀘스트가 없을 때
    if not in_progress and not completed:
        lines.append("[color=gray]진행 중인 퀘스트가 없습니다.[/color]")
        lines.append("")

    lines.append("[url=@finish]닫기[/url]")

    return "\n".join(lines)


def show_quest_ui(debug_mode: bool = True):
    """
    퀘스트 UI 다이얼로그 표시 (Generator)

    Args:
        debug_mode: True면 수락 가능 퀘스트도 표시
    """
    state = {"refresh": True, "selected": None}

    def proc(action):
        if action == "init" or state.get("refresh"):
            state["refresh"] = False
            return render_quest_ui(state.get("selected"), debug_mode)

        # 퀘스트 선택 (세부 정보 보기)
        if action.startswith("select:"):
            quest_id = action.split(":", 1)[1]
            state["selected"] = quest_id
            return render_quest_ui(quest_id, debug_mode)

        # 목록으로 돌아가기
        if action == "back":
            state["selected"] = None
            return render_quest_ui(None, debug_mode)

        # 보상 수령
        if action.startswith("claim:"):
            quest_id = action.split(":", 1)[1]
            quest_manager.claim_reward(quest_id)
            state["refresh"] = True
            return render_quest_ui(state.get("selected"), debug_mode)

        return None

    yield morld.dialog("", autofill="off", proc=proc, result=state)
    # @finish 클릭 시 다이얼로그 종료, 반환값 없음


# ============================================
# morld API 등록용 함수
# ============================================

def give_quest(quest_id: str) -> bool:
    """morld.give_quest() API"""
    return quest_manager.give_quest(quest_id)


def get_quest_status(quest_id: str) -> str:
    """morld.get_quest_status() API - 상태 이름 반환 (locked, available, in_progress, completed, finished)"""
    return quest_manager.get_quest_status(quest_id).name.lower()


def get_active_quests() -> List[str]:
    """morld.get_active_quests() API"""
    return [q.unique_id for q in quest_manager.get_active_quests()]


def get_quest_progress(quest_id: str) -> Dict[str, Any]:
    """morld.get_quest_progress() API"""
    return quest_manager.get_quest_progress(quest_id)


def complete_quest(quest_id: str) -> bool:
    """morld.complete_quest() API"""
    return quest_manager.complete_quest(quest_id)


def check_quest_conditions(quest_id: str) -> bool:
    """morld.check_quest_conditions() API"""
    return quest_manager.check_quest_conditions(quest_id)


# ============================================
# 캐릭터 퀘스트 자동 등록
# ============================================

def register_character_quests():
    """
    모든 캐릭터의 개인 퀘스트를 등록

    assets/characters에 정의된 캐릭터 클래스의 CHARACTER_QUESTS를
    퀘스트 레지스트리에 등록합니다.

    호출 시점: 시나리오 초기화 후
    """
    from assets.characters import get_all_character_classes

    for char_cls in get_all_character_classes():
        quests_data = char_cls.get_character_quests()
        for quest_data in quests_data:
            # dict를 Quest 인스턴스로 변환
            quest = Quest.from_dict(quest_data)
            if quest.unique_id:
                # 레지스트리에 등록 (클래스 대신 인스턴스를 래핑)
                _register_quest_instance(quest)


def _register_quest_instance(quest_instance: Quest):
    """Quest 인스턴스를 레지스트리에 등록 (내부용)"""
    # 클래스처럼 동작하는 래퍼 생성
    class QuestWrapper(Quest):
        pass

    # 인스턴스 속성을 클래스 속성으로 복사
    QuestWrapper.unique_id = quest_instance.unique_id
    QuestWrapper.name = quest_instance.name
    QuestWrapper.description = quest_instance.description
    QuestWrapper.category = quest_instance.category
    QuestWrapper.prerequisites = quest_instance.prerequisites
    QuestWrapper.conditions = quest_instance.conditions
    QuestWrapper.rewards = quest_instance.rewards
    QuestWrapper.giver = quest_instance.giver
    QuestWrapper.reporter = quest_instance.reporter
    QuestWrapper.dialogs = quest_instance.dialogs
    QuestWrapper.repeatable = quest_instance.repeatable
    QuestWrapper.visibility_conditions = quest_instance.visibility_conditions

    # 레지스트리에 등록
    _quest_registry[quest_instance.unique_id] = QuestWrapper


def initialize_quest_system():
    """
    퀘스트 시스템 초기화

    1. quest/quests/ 폴더의 퀘스트 로드 (import 시 자동 등록)
    2. 캐릭터 개인 퀘스트 등록

    호출 시점: 시나리오 초기화 후
    """
    # quest/quests/ 폴더 import (자동 등록됨)
    from quest import quests  # noqa: F401

    # 캐릭터 개인 퀘스트 등록
    register_character_quests()

    print(f"[Quest] Registered {len(_quest_registry)} quests")
