# assets/objects/appliances.py - 가전 오브젝트 (세탁기, 건조기)
#
# 워크플로우:
#   1. 빨래 넣기 (put) — 의류만 (put_filter=["clothing"])
#   2. 작동 시작 (start) — 가전:상태=1, 가전:남은시간 설정
#   3. 시간 경과 — laundry.py에서 매시간 업데이트
#   4. 완료 (가전:상태=2) — 효과 적용 (오염도/젖음 제거)
#   5. 빨래 꺼내기 (take_laundry)
#
# 작동 중에는 넣기/꺼내기 불가

import morld
import ui
from assets.base import Object


class WashingMachine(Object):
    """세탁기 — 의류의 오염도(오염:수치)를 제거"""
    unique_id = "washing_machine"
    name = "세탁기"
    put_filter = ["clothing"]

    actions = [
        "call:look:살펴보기",
        "call:put:빨래 넣기",
        "call:start_wash:세탁 시작",
        "call:take_laundry:빨래 꺼내기",
    ]

    focus_text = {"default": "세탁기."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        super().instantiate(instance_id, region_id, location_id, x, y)
        import laundry
        laundry.register_machine(instance_id, "washer")

    def get_focus_text(self):
        import laundry
        return laundry.get_machine_focus_text(self.instance_id, "washer")

    def look(self):
        yield ui.dialog(self.get_focus_text())

    def put(self):
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            yield ui.dialog("세탁기가 작동 중이다.")
            return
        yield from super().put()

    def start_wash(self):
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            yield ui.dialog("이미 작동 중이다.")
            return
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            yield ui.dialog("빨래가 들어있지 않다.")
            return
        laundry.start_machine(self.instance_id, "washer")
        yield ui.dialog("세탁을 시작했다.")

    def take_laundry(self):
        import laundry
        state = laundry.get_machine_state(self.instance_id)
        if state == 1:
            remaining = laundry.get_remaining_time(self.instance_id)
            yield ui.dialog(f"아직 세탁 중이다. (남은 시간: {remaining}분)")
            return
        if state != 2:
            yield ui.dialog("꺼낼 빨래가 없다.")
            return
        player_id = morld.get_player_id()
        inv = morld.get_unit_inventory(self.instance_id)
        import inventory as inv_module
        for item_id in list(inv.keys()):
            morld.lost_item(self.instance_id, item_id)
            inv_module.safe_give_item(player_id, item_id)
        laundry.reset_machine(self.instance_id)
        yield ui.dialog("세탁된 빨래를 꺼냈다.")

    # NPC 전용 메서드 (non-generator)

    def npc_load_laundry(self, npc_id, item_ids):
        """NPC 의류 아이템 목록을 세탁기에 넣기"""
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            return False
        for item_id in item_ids:
            if morld.has_item(npc_id, item_id):
                morld.remove_item(npc_id, item_id, 1)
                morld.give_item(self.instance_id, item_id, 1)
        return True

    def npc_start(self, npc_id):
        """NPC 세탁 시작"""
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            return False
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            return False
        laundry.start_machine(self.instance_id, "washer")
        return True

    def npc_unload_laundry(self, npc_id):
        """NPC 완료된 빨래 꺼내기"""
        import laundry
        state = laundry.get_machine_state(self.instance_id)
        if state != 2:
            return False
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            laundry.reset_machine(self.instance_id)
            return True
        import inventory as inv_module
        for item_id in list(inv.keys()):
            morld.lost_item(self.instance_id, item_id)
            inv_module.safe_give_item(npc_id, item_id)
        laundry.reset_machine(self.instance_id)
        return True


class Dryer(Object):
    """건조기 — 의류의 젖음(습도:젖음)을 제거"""
    unique_id = "dryer"
    name = "건조기"
    put_filter = ["clothing"]

    actions = [
        "call:look:살펴보기",
        "call:put:빨래 넣기",
        "call:start_dry:건조 시작",
        "call:take_laundry:빨래 꺼내기",
    ]

    focus_text = {"default": "건조기."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        super().instantiate(instance_id, region_id, location_id, x, y)
        import laundry
        laundry.register_machine(instance_id, "dryer")

    def get_focus_text(self):
        import laundry
        return laundry.get_machine_focus_text(self.instance_id, "dryer")

    def look(self):
        yield ui.dialog(self.get_focus_text())

    def put(self):
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            yield ui.dialog("건조기가 작동 중이다.")
            return
        yield from super().put()

    def start_dry(self):
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            yield ui.dialog("이미 작동 중이다.")
            return
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            yield ui.dialog("빨래가 들어있지 않다.")
            return
        laundry.start_machine(self.instance_id, "dryer")
        yield ui.dialog("건조를 시작했다.")

    def take_laundry(self):
        import laundry
        state = laundry.get_machine_state(self.instance_id)
        if state == 1:
            remaining = laundry.get_remaining_time(self.instance_id)
            yield ui.dialog(f"아직 건조 중이다. (남은 시간: {remaining}분)")
            return
        if state != 2:
            yield ui.dialog("꺼낼 빨래가 없다.")
            return
        player_id = morld.get_player_id()
        inv = morld.get_unit_inventory(self.instance_id)
        import inventory as inv_module
        for item_id in list(inv.keys()):
            morld.lost_item(self.instance_id, item_id)
            inv_module.safe_give_item(player_id, item_id)
        laundry.reset_machine(self.instance_id)
        yield ui.dialog("건조된 빨래를 꺼냈다.")

    # NPC 전용 메서드 (non-generator)

    def npc_load_laundry(self, npc_id, item_ids):
        """NPC 의류 아이템 목록을 건조기에 넣기"""
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            return False
        for item_id in item_ids:
            if morld.has_item(npc_id, item_id):
                morld.remove_item(npc_id, item_id, 1)
                morld.give_item(self.instance_id, item_id, 1)
        return True

    def npc_start(self, npc_id):
        """NPC 건조 시작"""
        import laundry
        if laundry.is_machine_busy(self.instance_id):
            return False
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            return False
        laundry.start_machine(self.instance_id, "dryer")
        return True

    def npc_unload_laundry(self, npc_id):
        """NPC 완료된 빨래 꺼내기"""
        import laundry
        state = laundry.get_machine_state(self.instance_id)
        if state != 2:
            return False
        inv = morld.get_unit_inventory(self.instance_id)
        if not inv:
            laundry.reset_machine(self.instance_id)
            return True
        import inventory as inv_module
        for item_id in list(inv.keys()):
            morld.lost_item(self.instance_id, item_id)
            inv_module.safe_give_item(npc_id, item_id)
        laundry.reset_machine(self.instance_id)
        return True
