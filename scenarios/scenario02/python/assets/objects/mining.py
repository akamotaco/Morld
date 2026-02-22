# assets/objects/mining.py — 광석 노드 (채광 오브젝트)
#
# OreNode: 채광 가능한 광석 오브젝트
# - can:mine equip_prop (곡괭이) 필요
# - resource:amount 감소 → 광석 아이템 생성
# - 시간 경과 시 자연 재생

import morld
import ui
import events
from assets.base import Object
from assets.registry import get_or_create_item_id

# 등록된 OreNode 인스턴스 (regen 추적용)
_ore_nodes = {}  # {instance_id: {"type": str, "regen_hours": int, "hours_since_regen": int}}

_initialized = False
MILLIS_PER_HOUR = 3_600_000


def _ensure_initialized():
    global _initialized
    if _initialized:
        return
    _initialized = True
    events.subscribe_time_elapsed(_on_time_elapsed, min_interval=MILLIS_PER_HOUR)


def _on_time_elapsed(elapsed_ms):
    """1시간마다 광석 자연 재생"""
    for node_id, info in list(_ore_nodes.items()):
        info["hours_since_regen"] += 1
        if info["hours_since_regen"] >= info["regen_hours"]:
            info["hours_since_regen"] = 0
            # 현재 amount 확인
            current = morld.get_unit_prop(node_id, "resource:amount") or 0
            max_amount = morld.get_unit_prop(node_id, "resource:max") or 0
            if current < max_amount:
                morld.set_unit_prop(node_id, "resource:amount", current + 1)


def register_ore_node(instance_id, resource_type, regen_hours):
    """광석 노드 등록 (regen 추적)"""
    _ensure_initialized()
    _ore_nodes[instance_id] = {
        "type": resource_type,
        "regen_hours": regen_hours,
        "hours_since_regen": 0,
    }


def reset():
    """챕터 전환 시 리셋"""
    global _ore_nodes, _initialized
    _ore_nodes = {}
    _initialized = False


class OreNode(Object):
    """광석 노드 — 채광 가능한 오브젝트 (기본 클래스)"""
    unique_id = "ore_node"
    name = "광석"
    resource_type = "iron_ore"     # 생성할 아이템 unique_id
    initial_amount = 3
    max_amount = 3
    regen_hours = 24
    item_visible = False

    actions = [
        "call:look:살펴보기",
        "call:mine:채광#",
        "call:debug_props:(디버그) 속성 보기#",
    ]

    focus_text = {"default": "광맥이 보인다."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        # props에 자원 정보 설정
        self.props = dict(self.props) if self.props else {}
        self.props["resource:type"] = self.resource_type
        self.props["resource:amount"] = self.initial_amount
        self.props["resource:max"] = self.max_amount
        self.props["resource:regen_hours"] = self.regen_hours
        super().instantiate(instance_id, region_id, location_id, x, y)
        register_ore_node(instance_id, self.resource_type, self.regen_hours)

    def get_focus_text(self):
        amount = morld.get_unit_prop(self.instance_id, "resource:amount") or 0
        if amount <= 0:
            return "광맥이 고갈되었다. 시간이 지나면 다시 생길지도 모른다."
        elif amount == 1:
            return "광석이 거의 남지 않았다. 조금만 더 캘 수 있을 것 같다."
        else:
            return f"광석이 {amount}개 남아 있다."

    def look(self):
        amount = morld.get_unit_prop(self.instance_id, "resource:amount") or 0
        if amount <= 0:
            yield ui.dialog("광맥이 고갈되어 있다.")
        else:
            yield ui.dialog(f"광석이 {amount}개 남아 있다. 곡괭이가 있으면 캘 수 있다.")

    def mine(self):
        """채광 (can:mine equip_prop 필요)"""
        player_id = morld.get_player_id()

        # can:mine 체크
        actual = morld.get_actual_props(player_id)
        if not actual.get("can:mine"):
            yield ui.dialog("곡괭이가 없으면 광석을 캘 수 없다.")
            return

        # 잔량 체크
        amount = morld.get_unit_prop(self.instance_id, "resource:amount") or 0
        if amount <= 0:
            yield ui.dialog("광맥이 고갈되어 있다.")
            return

        # 채광
        morld.set_unit_prop(self.instance_id, "resource:amount", amount - 1)
        item_id = get_or_create_item_id(self.resource_type)
        morld.give_item(player_id, item_id, 1)

        ore_name = morld.get_unit_info(item_id).get("name", self.resource_type)
        yield ui.dialog(f"{ore_name}을(를) 1개 획득했다.")

        # 5분 경과
        morld.advance_time_des(5 * 60_000)


class CopperOreNode(OreNode):
    """구리광석 노드 — 1층/2층 갱도"""
    unique_id = "copper_ore_node"
    name = "구리 광맥"
    resource_type = "copper_ore"
    initial_amount = 5
    max_amount = 5
    regen_hours = 24

    focus_text = {"default": "녹청이 낀 구리 광맥이 보인다."}

    def get_focus_text(self):
        amount = morld.get_unit_prop(self.instance_id, "resource:amount") or 0
        if amount <= 0:
            return "구리 광맥이 고갈되었다."
        return f"녹청이 낀 구리 광맥. 광석이 {amount}개 남아 있다."


class IronOreNode(OreNode):
    """철광석 노드 — 2층/깊은 갱도"""
    unique_id = "iron_ore_node"
    name = "철 광맥"
    resource_type = "iron_ore"
    initial_amount = 3
    max_amount = 3
    regen_hours = 48

    focus_text = {"default": "붉은빛 철 광맥이 보인다."}

    def get_focus_text(self):
        amount = morld.get_unit_prop(self.instance_id, "resource:amount") or 0
        if amount <= 0:
            return "철 광맥이 고갈되었다."
        return f"붉은빛 철 광맥. 광석이 {amount}개 남아 있다."
