"""MockMorld - 시나리오03 테스트용 C# API 스텁"""


class MockMorld:
    def __init__(self):
        self.reset()

    def reset(self):
        self._next_id = 1000
        self._regions = {}      # region_id -> {name, describe_text, weather}
        self._locations = {}    # (region_id, location_id) -> {name, is_indoor, length, ...}
        self._gates = {}        # (region_id, location_id, gate_id) -> gate_data
        self._region_gates = [] # [(region_a, loc_a, region_b, loc_b, distance)]
        self._units = {}        # unit_id -> {name, region_id, location_id, type, ...}
        self._items = {}        # item_id -> {name, equip_props, ...}
        self._inventories = {}  # unit_id -> {item_id: count}
        self._jobs = {}         # unit_id -> [job_dicts]
        self._time = 0          # game time in millis
        self._time_frozen = False
        self._logs = []

    def create_id(self, id_type="unit"):
        self._next_id += 1
        return self._next_id

    # === Region/Location/Gate ===
    def add_region(self, region_id, name, describe_text=None, weather=None):
        self._regions[region_id] = {
            "name": name,
            "describe_text": describe_text or {},
            "weather": weather,
        }

    def region_exists(self, region_id):
        return region_id in self._regions

    def get_region_info(self, region_id):
        return self._regions.get(region_id)

    def add_location(self, region_id, location_id, name, is_indoor=True,
                     stay_duration=0, geometry="line", length=0, **kwargs):
        self._locations[(region_id, location_id)] = {
            "name": name,
            "is_indoor": is_indoor,
            "stay_duration": stay_duration,
            "geometry": geometry,
            "length": length,
            **kwargs,
        }

    def get_location_info(self, region_id, location_id):
        return self._locations.get((region_id, location_id))

    def add_gate(self, region_id, location_id, gate_id, x,
                 conn_region, conn_location, arrival_x, **kwargs):
        self._gates[(region_id, location_id, gate_id)] = {
            "x": x,
            "conn_region": conn_region,
            "conn_location": conn_location,
            "arrival_x": arrival_x,
            **kwargs,
        }

    def get_location_gates(self, region_id, location_id):
        result = []
        for (r, l, gid), data in self._gates.items():
            if r == region_id and l == location_id:
                result.append({
                    "gate_id": gid,
                    "x": data["x"],
                    "connected_region": data["conn_region"],
                    "connected_location": data["conn_location"],
                    "arrival_x": data["arrival_x"],
                })
        return result

    def set_location_length(self, region_id, location_id, length):
        key = (region_id, location_id)
        if key in self._locations:
            self._locations[key]["length"] = length

    def remove_location(self, region_id, location_id):
        self._locations.pop((region_id, location_id), None)
        # remove associated gates
        to_remove = [k for k in self._gates if k[0] == region_id and k[1] == location_id]
        for k in to_remove:
            del self._gates[k]

    def add_region_gate(self, region_a, loc_a, region_b, loc_b, distance=0):
        self._region_gates.append((region_a, loc_a, region_b, loc_b, distance))

    def reinitialize_locations(self):
        pass

    # === Unit ===
    def add_unit(self, unit_id, name, region_id, location_id, unit_type="object",
                 actions=None, mood=None, unique_id=None, action_props=None,
                 owner=None, item_visible=False):
        self._units[unit_id] = {
            "name": name,
            "region_id": region_id,
            "location_id": location_id,
            "type": unit_type,
            "actions": actions or [],
            "mood": mood or [],
            "unique_id": unique_id,
            "props": {},
            "owner": owner,
        }
        self._inventories[unit_id] = {}

    def get_unit_info(self, unit_id):
        return self._units.get(unit_id)

    def get_unit_location(self, unit_id):
        u = self._units.get(unit_id)
        if u:
            return (u["region_id"], u["location_id"])
        return None

    def set_unit_location(self, unit_id, region_id, location_id):
        if unit_id in self._units:
            self._units[unit_id]["region_id"] = region_id
            self._units[unit_id]["location_id"] = location_id

    def set_unit_position(self, unit_id, x, y=0):
        if unit_id in self._units:
            self._units[unit_id]["x"] = x
            self._units[unit_id]["y"] = y
        return True

    def get_unit_prop(self, unit_id, key):
        u = self._units.get(unit_id)
        if u:
            return u["props"].get(key)
        return None

    def set_unit_prop(self, unit_id, key, value):
        if unit_id in self._units:
            if value is None:
                self._units[unit_id]["props"].pop(key, None)
            else:
                self._units[unit_id]["props"][key] = value

    def get_unit_props(self, unit_id):
        u = self._units.get(unit_id)
        if u:
            return dict(u["props"])
        return {}

    def set_unit_props(self, unit_id, props_dict):
        if unit_id in self._units:
            self._units[unit_id]["props"].update(props_dict)

    def get_units_at_location(self, region_id, location_id=None, type_filter=None):
        result = []
        for uid, u in self._units.items():
            if u["region_id"] == region_id and u["location_id"] == location_id:
                if type_filter is None or u["type"] == type_filter:
                    result.append(uid)
        return result

    def remove_unit(self, unit_id):
        self._units.pop(unit_id, None)
        self._inventories.pop(unit_id, None)

    # === Item ===
    def add_item(self, item_id, name, equip_props=None, **kwargs):
        self._items[item_id] = {
            "name": name,
            "equip_props": equip_props or {},
            **kwargs,
        }

    def get_item_info(self, item_id):
        return self._items.get(item_id)

    def give_item(self, unit_id, item_id, count=1):
        if unit_id not in self._inventories:
            self._inventories[unit_id] = {}
        inv = self._inventories[unit_id]
        inv[item_id] = inv.get(item_id, 0) + count

    def remove_item(self, unit_id, item_id, count=1):
        if unit_id in self._inventories:
            inv = self._inventories[unit_id]
            if item_id in inv:
                inv[item_id] -= count
                if inv[item_id] <= 0:
                    del inv[item_id]

    def has_item(self, unit_id, item_id, count=1):
        if unit_id in self._inventories:
            return self._inventories[unit_id].get(item_id, 0) >= count
        return False

    def get_unit_inventory(self, unit_id):
        return dict(self._inventories.get(unit_id, {}))

    def get_item_count(self, unit_id, item_uid):
        inv = self._inventories.get(unit_id, {})
        for item_id, count in inv.items():
            info = self._items.get(item_id)
            if info and info.get("unique_id") == item_uid:
                return count
        return 0

    # === Jobs ===
    def insert_job(self, unit_id, job_dict):
        if unit_id not in self._jobs:
            self._jobs[unit_id] = []
        self._jobs[unit_id].append(job_dict)

    def clear_jobs(self, unit_id=None):
        if unit_id is not None:
            self._jobs[unit_id] = []
        else:
            self._jobs.clear()

    def get_current_job(self, unit_id):
        jobs = self._jobs.get(unit_id, [])
        return jobs[0] if jobs else None

    def fill_schedule_jobs_from(self, unit_id, schedule):
        return True

    # === Time ===
    def set_time(self, year, month, day, hour, minute=0):
        self._time = ((year * 365 + month * 30 + day) * 24 + hour) * 3_600_000 + minute * 60_000

    def get_game_time(self):
        return self._time

    def get_time_info(self):
        return {"total_millis": self._time, "hour": (self._time // 3_600_000) % 24}

    def advance_time_des(self, millis):
        self._time += millis

    def set_time_frozen(self, frozen):
        self._time_frozen = frozen

    def is_time_frozen(self):
        return self._time_frozen

    # === Misc ===
    def get_player_id(self):
        return 1

    def clear_world(self):
        self.reset()

    def log(self, msg):
        self._logs.append(msg)
