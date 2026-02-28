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
        self._locations = {}
        self._regions = {}
        self._gates = {}
        self._next_id = 1000
        self._player_id = 1
        self._time = 0
        self._time_frozen = False
        self._logs = []
        self._events = []
        self._moods = []
        self._jobs = {}
        self._quest_conditions = []

    # ========================================
    # 테스트 셋업 헬퍼 (morld API 아님)
    # ========================================

    def register_unit(self, unit_id, name="NPC", props=None,
                      location=(0, 0), gender="female",
                      is_creature=False, is_object=False):
        """테스트용 유닛 등록"""
        r, l = location
        self._units[unit_id] = {
            "info": {
                "name": name, "type": gender,
                "activity": None, "mood": [],
                "is_traveling": False,
                "region_id": r, "location_id": l,
                "is_object": is_object,
                "is_creature": is_creature,
            },
            "props": dict(props or {}),
            "location": location,
            "inventory": {},
        }

    def register_location(self, region_id, location_id, **kwargs):
        """테스트용 location 등록"""
        key = (region_id, location_id)
        self._locations[key] = {
            "weather": kwargs.get("weather"),
            "is_indoor": kwargs.get("is_indoor", True),
        }

    def register_item(self, item_id, name="아이템", equip_props=None):
        """테스트용 아이템 등록"""
        self._items[item_id] = {
            "name": name,
            "equip_props": equip_props or {},
        }

    def add_to_inventory(self, unit_id, item_id, count=1):
        """테스트용 인벤토리 추가"""
        u = self._units.get(unit_id)
        if u:
            u["inventory"][item_id] = u["inventory"].get(item_id, 0) + count

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

    def clear_player_meetings(self):
        """은신 해제 시 만남 상태 초기화 (mock: no-op)"""
        pass

    def get_unit_props_by_type(self, unit_id, prop_type):
        """prop_type 접두사로 시작하는 props 반환 (접두사 제거)"""
        u = self._units.get(unit_id)
        if not u:
            return None
        prefix = prop_type + ":"
        result = {}
        for k, v in u["props"].items():
            if k.startswith(prefix):
                result[k[len(prefix):]] = v
        return result if result else None

    # ========================================
    # morld API — Unit 정보
    # ========================================

    def get_unit_info(self, unit_id):
        u = self._units.get(unit_id)
        return dict(u["info"]) if u else None

    def get_unit_location(self, unit_id):
        u = self._units.get(unit_id)
        return u["location"] if u else None

    def get_characters_at_location(self, region, location):
        return [uid for uid, u in self._units.items()
                if u["location"] == (region, location) and u.get("type") != "object"]

    def get_units_at_location(self, region_or_location, location=None, type_filter=None):
        # 1-arg: location_id only (region 무시, location_id 일치하면 반환)
        # 2-arg: (region_id, location_id) 쌍으로 매칭
        if location is None:
            loc_id = region_or_location
            result = []
            for uid, u in self._units.items():
                if u["location"][1] != loc_id:
                    continue
                utype = u["info"].get("type", "")
                if type_filter == "character" and utype == "object":
                    continue
                if type_filter == "object" and utype != "object":
                    continue
                result.append(uid)
            return result
        result = []
        for uid, u in self._units.items():
            if u["location"] != (region_or_location, location):
                continue
            utype = u["info"].get("type", "")
            if type_filter == "character" and utype == "object":
                continue
            if type_filter == "object" and utype != "object":
                continue
            result.append(uid)
        return result

    def get_player_id(self):
        return self._player_id

    def get_unit_inventory(self, unit_id):
        u = self._units.get(unit_id)
        return dict(u["inventory"]) if u else {}

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

    def get_game_time(self):
        return self._time

    def advance_time_des(self, millis):
        self._time += millis

    def is_time_frozen(self):
        return self._time_frozen

    def get_current_time(self):
        return self._time

    def register_script(self, func):
        """데코레이터: 스크립트 함수 등록 (테스트에서는 no-op)"""
        return func

    # ========================================
    # morld API — Job 시스템
    # ========================================

    def insert_job(self, unit_id, job_dict):
        """DES job 삽입 (기록용)"""
        if unit_id not in self._jobs:
            self._jobs[unit_id] = []
        self._jobs[unit_id].append(dict(job_dict))

    def get_current_job(self, unit_id):
        """현재 작업 정보 반환 (마지막 삽입된 job)"""
        jobs = self._jobs.get(unit_id)
        return jobs[-1] if jobs else None

    def get_all_jobs(self, unit_id):
        """테스트용: 모든 삽입된 job 반환"""
        return list(self._jobs.get(unit_id, []))

    def clear_jobs(self, unit_id=None):
        """테스트용: job 기록 초기화"""
        if unit_id is None:
            self._jobs.clear()
        else:
            self._jobs.pop(unit_id, None)

    def resolve_sleep_target(self, unit_id, region_id, location_id,
                             owner_unique=""):
        """수면 위치 해석 (C# resolve_sleep_target 모사)"""
        return {
            "region_id": region_id,
            "location_id": location_id,
            "x": 0,
            "bed_object_id": None,
            "rough": False,
        }

    # ========================================
    # morld API — NPC / UI
    # ========================================

    def set_npc_job(self, unit_id, action, duration, target=None):
        pass

    def add_action_log(self, text):
        self._logs.append(text)

    def queue_event(self, event_type, actor_id, args=None):
        self._events.append((event_type, actor_id, args))

    def lost_item(self, unit_id, item_id, count=1):
        u = self._units.get(unit_id)
        if u and item_id in u["inventory"]:
            u["inventory"][item_id] -= count
            if u["inventory"][item_id] <= 0:
                del u["inventory"][item_id]

    def add_unit_mood(self, unit_id, mood):
        self._moods.append((unit_id, mood))

    def pop_to_situation(self):
        pass

    # ========================================
    # morld API — Character 지원 확장
    # ========================================

    def add_unit(self, unit_id, name, region_id, location_id,
                 unit_type, actions=None, mood=None,
                 unique_id=None, action_props=None, owner=None):
        """유닛 생성 (Character.instantiate에서 호출)"""
        self._units[unit_id] = {
            "info": {
                "name": name, "type": unit_type,
                "activity": None, "mood": mood or [],
                "is_traveling": False,
                "region_id": region_id, "location_id": location_id,
            },
            "props": {},
            "location": (region_id, location_id),
            "inventory": {},
        }

    def set_unit_props(self, unit_id, props_dict):
        """복수 prop 일괄 설정"""
        u = self._units.get(unit_id)
        if u:
            u["props"].update(props_dict)

    def get_location_info(self, region_id, location_id):
        """location 정보 반환"""
        key = (region_id, location_id)
        if key in self._locations:
            return dict(self._locations[key])
        return {"weather": None, "is_indoor": True}

    def give_item(self, unit_id, item_id, count=1):
        """유닛에 아이템 지급"""
        u = self._units.get(unit_id)
        if u:
            u["inventory"][item_id] = u["inventory"].get(item_id, 0) + count

    def remove_item(self, unit_id, item_id, count=1):
        """유닛에서 아이템 제거"""
        u = self._units.get(unit_id)
        if u and item_id in u["inventory"]:
            u["inventory"][item_id] -= count
            if u["inventory"][item_id] <= 0:
                del u["inventory"][item_id]

    def has_item(self, unit_id, item_id, count=1):
        """아이템 보유 확인 (count 지정 시 해당 수량 이상 보유 여부)"""
        u = self._units.get(unit_id)
        if u:
            return u["inventory"].get(item_id, 0) >= count
        return False

    def set_unit_location(self, unit_id, region_id, location_id):
        """유닛 위치 설정"""
        u = self._units.get(unit_id)
        if u:
            u["location"] = (region_id, location_id)
            u["info"]["region_id"] = region_id
            u["info"]["location_id"] = location_id

    def check_quest_condition(self, condition_type, *args):
        """퀘스트 조건 체크 (no-op)"""
        self._quest_conditions.append((condition_type, args))

    def dialog(self, content, **kwargs):
        """다이얼로그 표시 (테스트에서는 content 반환)"""
        return content

    def sit_on(self, unit_id, target_id, slot=0):
        """앉기 (테스트에서는 항상 성공)"""
        return True

    def stand_up(self, unit_id):
        """일어서기 (seated_on 해제)"""
        u = self._units.get(unit_id)
        if u:
            # seated_on:* prop 모두 제거
            to_remove = [k for k in u["props"] if k.startswith("seated_on:")]
            for k in to_remove:
                del u["props"][k]

    def is_same_building(self, r1, l1, r2, l2):
        """같은 건물 판정 (테스트에서는 항상 True)"""
        return True

    def get_equipped_items(self, unit_id):
        """장착 아이템 목록 반환 (테스트에서는 빈 리스트)"""
        u = self._units.get(unit_id)
        if u:
            return list(u.get("equipped", []))
        return []

    # ========================================
    # morld API — Terrain (Region/Location/Gate)
    # ========================================

    def add_region(self, region_id, name):
        """region 생성"""
        self._regions[region_id] = {"name": name}

    def add_location(self, region_id, location_id, name, **kwargs):
        """location 생성 (build.py 호환)"""
        key = (region_id, location_id)
        self._locations[key] = {
            "name": name,
            "length": kwargs.get("length", 1),
            "owner": kwargs.get("owner", ""),
            "is_indoor": kwargs.get("indoor", True),
            "weather": kwargs.get("weather"),
        }

    def add_gate(self, region_id, location_id, gate_id,
                 x, conn_region, conn_location, arrival_x):
        """gate 생성"""
        key = (region_id, location_id)
        if key not in self._gates:
            self._gates[key] = []
        self._gates[key].append({
            "gate_id": gate_id,
            "x": x,
            "connected_region": conn_region,
            "connected_location": conn_location,
            "arrival_x": arrival_x,
        })

    def region_exists(self, region_id):
        """region 존재 여부 확인"""
        return region_id in self._regions

    def get_region_info(self, region_id):
        """region 정보 반환 (locations + gates 포함)"""
        if region_id not in self._regions:
            return None
        locations = []
        for (r, l), info in self._locations.items():
            if r == region_id:
                loc_data = {"id": l, **info}
                # Gate 포함 (C# API 키 형식: connected_local)
                raw_gates = self._gates.get((r, l), [])
                loc_data["gates"] = [
                    {
                        "x": g["x"],
                        "connected_region": g["connected_region"],
                        "connected_local": g["connected_location"],
                    }
                    for g in raw_gates
                ]
                locations.append(loc_data)
        return {"name": self._regions[region_id]["name"], "locations": locations}

    def get_location_gates(self, region_id, location_id):
        """location의 gate 목록 반환"""
        key = (region_id, location_id)
        return list(self._gates.get(key, []))

    def set_location_length(self, region_id, location_id, length):
        """location length 설정"""
        key = (region_id, location_id)
        if key in self._locations:
            self._locations[key]["length"] = length
            return True
        return False

    def remove_location(self, region_id, location_id):
        """location + 관련 gate 제거"""
        key = (region_id, location_id)
        if key not in self._locations:
            return False
        # 이 location의 gate 제거
        self._gates.pop(key, None)
        # 다른 location에서 이 location을 가리키는 gate 제거
        for other_key in list(self._gates):
            self._gates[other_key] = [
                g for g in self._gates[other_key]
                if not (g["connected_region"] == region_id
                        and g["connected_location"] == location_id)
            ]
        self._locations.pop(key)
        return True

    def remove_unit(self, unit_id):
        """유닛 제거"""
        self._units.pop(unit_id, None)

    def create_id(self, id_type="unit"):
        """순차 ID 생성"""
        self._next_id += 1
        return self._next_id

    def set_unit_position(self, unit_id, x, y=0):
        """유닛 X 좌표 설정"""
        u = self._units.get(unit_id)
        if u:
            u["info"]["x"] = x
            u["info"]["y"] = y
            return True
        return False

    def reinitialize_locations(self):
        """챕터 로드 후 위치 재초기화 (no-op)"""
        pass
