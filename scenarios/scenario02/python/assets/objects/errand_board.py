# assets/objects/errand_board.py - 일일 심부름 게시판
#
# 현관에 배치되어 일일 납품 퀘스트를 표시하고 수락/납품 기능 제공
# container 기능으로 납품할 아이템을 직접 넣어서 납품
#
# 사용법:
#   from assets.objects.errand_board import ErrandBoard
#   board = ErrandBoard()
#   loc.add_object(board, instance_id)

import morld
from assets.base import Object
from quest import quest_manager, QuestStatus


# 일일 납품 퀘스트 unique_id 목록
DAILY_DELIVERY_QUESTS = [
    "daily_deliver_herb",
    "daily_deliver_log",
    "daily_deliver_food",
    "daily_deliver_berry",
    "daily_deliver_mushroom",
]


class ErrandBoard(Object):
    """
    일일 심부름 게시판

    - focus 시 일일 납품 퀘스트 리스트 표시
    - 퀘스트 수락 및 납품 기능
    - container에 아이템을 넣어 납품 (어떤 아이템이 납품될지 명확히 선택)
    """
    unique_id = "errand_board"
    name = "심부름 게시판"
    item_visible = True  # 인벤토리에 아이템이 있으면 개수 표시
    actions = [
        "call:view_errands*:의뢰 보기",
        "container#",  # 납품할 아이템 넣기 - 인벤토리 있을 때만 표시
        "call:put:납품 아이템 넣기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "저택 현관에 붙어있는 심부름 게시판. 여러 의뢰가 적힌 종이들이 붙어 있다."}

    def get_focus_text(self) -> str:
        """게시판 포커스 시 의뢰 목록 표시"""
        return self._render_errand_list()

    def _render_errand_list(self, message: str = None) -> str:
        """의뢰 목록 렌더링"""
        lines = []
        lines.append("[b]일일 심부름 게시판[/b]")
        lines.append("")

        # 메시지가 있으면 표시
        if message:
            lines.append(f"[color=yellow]{message}[/color]")
            lines.append("")

        # 게시판에 넣어둔 아이템 표시
        board_inv = self._get_board_inventory_by_unique()
        if board_inv:
            lines.append("[color=cyan]납품 대기 아이템:[/color]")
            from quest.conditions import _get_item_name
            for unique_id, count in board_inv.items():
                item_name = _get_item_name(unique_id)
                lines.append(f"  - {item_name} x{count}")
            lines.append("")

        for quest_id in DAILY_DELIVERY_QUESTS:
            quest = quest_manager._get_quest_instance(quest_id)
            if not quest:
                continue

            status = quest_manager.get_quest_status(quest_id)
            reward_text = self._get_reward_text(quest)

            if status == QuestStatus.LOCKED or status == QuestStatus.AVAILABLE:
                # 수락 가능
                lines.append(f"  ○ {quest.description} ({reward_text})")
                lines.append(f"    [url=@proc:accept:{quest_id}]수락[/url]")
            elif status == QuestStatus.IN_PROGRESS:
                # 진행 중 - 납품 가능 여부 체크 (게시판 인벤토리 기준)
                progress = quest_manager.get_quest_progress(quest_id)
                if progress.get("all_met"):
                    lines.append(f"  [color=lime]✓[/color] {quest.description} ({reward_text}) - 완료!")
                else:
                    # 게시판 인벤토리에서 납품 가능한 아이템 체크
                    can_deliver, deliver_info = self._check_can_deliver_from_board(quest)
                    if can_deliver:
                        lines.append(f"  → {quest.description} ({reward_text})")
                        lines.append(f"    [url=@proc:deliver:{quest_id}]납품하기[/url]")
                    else:
                        # 필요 아이템 표시
                        required_text = self._get_required_items_text(quest)
                        lines.append(f"  → {quest.description} ({reward_text})")
                        lines.append(f"    [color=gray]{required_text}[/color]")
            elif status == QuestStatus.COMPLETED:
                # 보상 수령 대기
                lines.append(f"  [color=lime]✓[/color] {quest.description} ({reward_text})")
                lines.append(f"    [url=@proc:claim:{quest_id}]보상 받기[/url]")
            elif status == QuestStatus.FINISHED:
                # 오늘 완료됨
                lines.append(f"  [color=gray]✓ {quest.description} (완료)[/color]")

        if not any(quest_manager.get_quest_status(q) != QuestStatus.FINISHED
                   for q in DAILY_DELIVERY_QUESTS):
            lines.append("")
            lines.append("[color=gray]오늘의 모든 의뢰를 완료했습니다.[/color]")

        lines.append("")
        lines.append("[url=@finish]닫기[/url]")

        return "\n".join(lines)

    def _get_reward_text(self, quest) -> str:
        """보상 텍스트 생성"""
        for reward in quest.rewards:
            if reward.get("type") == "coin":
                return f"{reward.get('value', 0)}코인"
        return "보상"

    def _get_board_inventory_by_unique(self) -> dict:
        """게시판 인벤토리를 unique_id 기반으로 반환"""
        if not self._instantiated:
            return {}

        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            return {}

        inv_by_unique = {}
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            unique_id = info.get("unique_id") if info else None
            if unique_id:
                inv_by_unique[unique_id] = inv_by_unique.get(unique_id, 0) + count

        return inv_by_unique

    def _check_can_deliver_from_board(self, quest) -> tuple:
        """
        게시판 인벤토리에서 납품 가능 여부 체크

        Returns:
            (can_deliver: bool, deliver_info: dict)
        """
        board_inv = self._get_board_inventory_by_unique()
        if not board_inv:
            return False, {}

        # 조건에서 deliver 타입 찾기
        for cond in quest.conditions:
            if cond.get("type") == "deliver":
                item_unique = cond.get("item")
                required = cond.get("count", 1)
                if board_inv.get(item_unique, 0) >= required:
                    return True, {"item": item_unique, "count": required}
            elif cond.get("type") == "any":
                # any 조건 내의 deliver 체크
                for sub_cond in cond.get("conditions", []):
                    if sub_cond.get("type") == "deliver":
                        item_unique = sub_cond.get("item")
                        required = sub_cond.get("count", 1)
                        if board_inv.get(item_unique, 0) >= required:
                            return True, {"item": item_unique, "count": required}

        return False, {}

    def _get_required_items_text(self, quest) -> str:
        """필요 아이템 텍스트 생성"""
        from quest.conditions import _get_item_name

        required_items = []

        for cond in quest.conditions:
            if cond.get("type") == "deliver":
                item_unique = cond.get("item")
                required = cond.get("count", 1)
                item_name = _get_item_name(item_unique)
                required_items.append(f"{item_name} {required}개")
            elif cond.get("type") == "any":
                # any 조건: 여러 아이템 중 하나
                any_items = []
                for sub_cond in cond.get("conditions", []):
                    if sub_cond.get("type") == "deliver":
                        item_unique = sub_cond.get("item")
                        required = sub_cond.get("count", 1)
                        item_name = _get_item_name(item_unique)
                        any_items.append(f"{item_name} {required}개")
                if any_items:
                    required_items.append(f"({' 또는 '.join(any_items)})")

        if required_items:
            return "필요: " + ", ".join(required_items)
        return "재료 부족"

    def view_errands(self):
        """의뢰 보기 액션 - proc 패턴으로 다이얼로그 내 액션 처리"""
        state = {"message": None}

        def handle_action(action):
            if action == "init":
                return None  # 초기 텍스트 유지

            # action 형식: "accept:quest_id", "deliver:quest_id", "claim:quest_id"
            parts = action.split(":", 1)
            if len(parts) != 2:
                return None

            action_type, quest_id = parts

            if action_type == "accept":
                return self._do_accept_quest(quest_id, state)
            elif action_type == "deliver":
                return self._do_deliver_item(quest_id, state)
            elif action_type == "claim":
                return self._do_claim_reward(quest_id, state)

            return None

        text = self._render_errand_list()
        yield morld.dialog(text, autofill="off", proc=handle_action)

    def _do_accept_quest(self, quest_id: str, state: dict) -> str:
        """퀘스트 수락 (proc 콜백용)"""
        if quest_manager.accept_quest(quest_id):
            quest = quest_manager._get_quest_instance(quest_id)
            state["message"] = f"'{quest.name}' 의뢰를 수락했습니다."
        else:
            state["message"] = "의뢰를 수락할 수 없습니다."
        return self._render_errand_list(state["message"])

    def _do_deliver_item(self, quest_id: str, state: dict) -> str:
        """게시판 인벤토리에서 아이템 납품 (proc 콜백용)"""
        from quest.conditions import record_deliver, _get_item_name

        player_id = morld.get_player_id()
        quest = quest_manager._get_quest_instance(quest_id)
        if not quest:
            state["message"] = "의뢰를 찾을 수 없습니다."
            return self._render_errand_list(state["message"])

        # 게시판 인벤토리에서 납품 가능한 아이템 찾기
        can_deliver, deliver_info = self._check_can_deliver_from_board(quest)
        if not can_deliver:
            state["message"] = "게시판에 납품할 재료가 없습니다. 아이템을 먼저 넣어주세요."
            return self._render_errand_list(state["message"])

        item_unique = deliver_info["item"]
        required_count = deliver_info["count"]

        # 게시판 인벤토리에서 아이템 소비
        inventory = morld.get_unit_inventory(self.instance_id)
        consumed = 0
        for item_id, count in list(inventory.items()):
            info = morld.get_item_info(item_id)
            if info and info.get("unique_id") == item_unique:
                to_consume = min(count, required_count - consumed)
                morld.lost_item(self.instance_id, item_id, to_consume)
                consumed += to_consume
                if consumed >= required_count:
                    break

        # 납품 기록
        record_deliver(player_id, "errand_board", item_unique, quest_id, required_count)

        # 아이템 이름 조회
        item_name = _get_item_name(item_unique)

        # 퀘스트 완료 체크
        if quest_manager.check_quest_conditions(quest_id):
            state["message"] = f"{item_name} {required_count}개 납품 완료! 보상을 받으세요."
        else:
            state["message"] = f"{item_name} {required_count}개를 납품했습니다."

        return self._render_errand_list(state["message"])

    def _do_claim_reward(self, quest_id: str, state: dict) -> str:
        """보상 수령 (proc 콜백용)"""
        if quest_manager.claim_reward(quest_id):
            quest = quest_manager._get_quest_instance(quest_id)
            reward_text = self._get_reward_text(quest)
            state["message"] = f"'{quest.name}' 보상 {reward_text}을(를) 받았습니다."
        else:
            state["message"] = "보상을 받을 수 없습니다."
        return self._render_errand_list(state["message"])
