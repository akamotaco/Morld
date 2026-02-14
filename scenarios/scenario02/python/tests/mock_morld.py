# mock_morld.py — morld C# API 인메모리 구현체
"""
morld 모듈의 핵심 API를 순수 Python dict 기반으로 모사.
sys.modules['morld']에 주입하여 모든 import morld가 이 모듈을 사용.

사용법:
    import sys
    from mock_morld import MockMorld
    mock = MockMorld()
    sys.modules['morld'] = mock
"""


class MockMorld:
    def __init__(self):
        self.reset()

    def reset(self):
        self._units = {}
        self._items = {}
        self._player_id = 1
        self._time = 0
        self._time_frozen = False
        self._logs = []
        self._events = []
        self._moods = []

    # ========================================
    # 테스트 셋업 헬퍼 (morld API 아님)
    # ========================================

    def register_unit(self, unit_id, name="NPC", props=None,
                      location=(0, 0), gender="female"):
        """테스트용 유닛 등록"""
        self._units[unit_id] = {
            "info": {"name": name, "type": gender},
            "props": dict(props or {}),
            "location": location,
            "inventory": [],
        }

    def register_item(self, item_id, name="아이템", equip_props=None):
        """테스트용 아이템 등록"""
        self._items[item_id] = {
            "name": name,
            "equip_props": equip_props or {},
        }

    def add_to_inventory(self, unit_id, item_id):
        """테스트용 인벤토리 추가"""
        u = self._units.get(unit_id)
        if u:
            u["inventory"].append(item_id)

    # ========================================
    # morld API — Property 조작
    # ========================================

    def get_unit_prop(self, unit_id, key):
        u = self._units.get(unit_id)
        return u["props"].get(key) if u else None

    def get_unit_props(self, unit_id):
        u = self._units.get(unit_id)
        return dict(u["props"]) if u else None

    def set_unit_prop(self, unit_id, key, value):
        u = self._units.get(unit_id)
        if u:
            u["props"][key] = value

    def modify_prop(self, unit_id, key, delta):
        u = self._units.get(unit_id)
        if u:
            u["props"][key] = u["props"].get(key, 0) + delta

    def clear_prop(self, unit_id, key):
        u = self._units.get(unit_id)
        if u:
            u["props"].pop(key, None)

    # ========================================
    # morld API — Unit 정보
    # ========================================

    def get_unit_info(self, unit_id):
        u = self._units.get(unit_id)
        return dict(u["info"]) if u else None

    def get_unit_location(self, unit_id):
        u = self._units.get(unit_id)
        return u["location"] if u else None

    def get_units_at_location(self, region, location):
        return [uid for uid, u in self._units.items()
                if u["location"] == (region, location)]

    def get_player_id(self):
        return self._player_id

    def get_unit_inventory(self, unit_id):
        u = self._units.get(unit_id)
        return list(u["inventory"]) if u else []

    # ========================================
    # morld API — Item 정보
    # ========================================

    def get_item_info(self, item_id):
        if item_id in self._items:
            return dict(self._items[item_id])
        return None

    # ========================================
    # morld API — 시간 / 게임 상태
    # ========================================

    def get_time(self):
        return self._time

    def advance_time_des(self, millis):
        self._time += millis

    def is_time_frozen(self):
        return self._time_frozen

    # ========================================
    # morld API — NPC / UI (no-op)
    # ========================================

    def set_npc_job(self, unit_id, action, duration, target=None):
        pass

    def add_action_log(self, text):
        self._logs.append(text)

    def queue_event(self, event_type, actor_id, args=None):
        self._events.append((event_type, actor_id, args))

    def lost_item(self, unit_id, item_id):
        u = self._units.get(unit_id)
        if u and item_id in u["inventory"]:
            u["inventory"].remove(item_id)

    def add_unit_mood(self, unit_id, mood):
        self._moods.append((unit_id, mood))

    def pop_to_situation(self):
        pass
