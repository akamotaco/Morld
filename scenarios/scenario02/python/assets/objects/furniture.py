# assets/objects/furniture.py - 실내 가구 오브젝트
#
# OOP call: 패턴 적용
# - actions: ["call:메서드명:표시명"] 형식
# - 각 클래스가 인스턴스 메서드로 동작 구현
#
# 사용법:
#   from assets.objects.furniture import Fireplace
#   fireplace = Fireplace()
#   loc.add_object(fireplace, instance_id)

import morld
import ui
import temperature
import humidity
from assets.base import Object
from ui_style import style_muted


# ========================================
# 물 받기 공용 헬퍼
# ========================================

def _fill_water_container(source_name: str):
    """
    물 용기에 물 채우기 (세면대/싱크대/수도꼭지 공용)

    인벤토리에서 can:water prop이 있는 물 용기를 찾아 물을 가득 채운다.
    """
    from assets.registry import get_unique_id, get_item_class
    from assets.items.garden_items import PROP_WATER_AMOUNT

    player_id = morld.get_player_id()

    # 물 용기 찾기 (can:water passive_prop 기반)
    containers = []
    inventory = morld.get_unit_inventory(player_id)
    for item_id, count in (inventory or {}).items():
        if count <= 0:
            continue
        info = morld.get_item_info(item_id)
        if not info:
            continue
        passive = info.get("passive_props") or {}
        if passive.get("can:water", 0) <= 0:
            continue
        uid = get_unique_id(item_id)
        item_cls = get_item_class(uid) if uid else None
        capacity = getattr(item_cls, "water_capacity", 1) if item_cls else 1
        current = morld.get_unit_prop(item_id, PROP_WATER_AMOUNT)
        name = info.get("name", f"아이템#{item_id}")
        containers.append({
            "id": item_id,
            "name": name,
            "capacity": capacity,
            "current": current,
        })

    if not containers:
        yield ui.dialog("물을 담을 도구가 없다. 물뿌리개나 물통이 필요하다.")
        return

    # 이미 가득 찬 것 제외
    fillable = [c for c in containers if c["current"] < c["capacity"]]
    if not fillable:
        yield ui.dialog("물 용기가 이미 가득 차 있다.")
        return

    # 하나면 바로 채우기, 여러 개면 선택
    if len(fillable) == 1:
        target = fillable[0]
    else:
        state = {"selected": None}

        def on_select(action):
            if action == "init":
                return None
            for c in fillable:
                if str(c["id"]) == action:
                    state["selected"] = c
                    return True
            return None

        lines = ["어떤 용기에 물을 받을까?", ""]
        for c in fillable:
            lines.append(f"  [url=@proc:{c['id']}]{c['name']}[/url] " + style_muted(f"({c['current']}/{c['capacity']})"))
        lines.append("")
        lines.append("[url=@ret:cancel]취소[/url]")

        yield ui.dialog("\n".join(lines), autofill="off", proc=on_select, result=state)
        target = state.get("selected")

    if not target:
        return

    # 물 채우기
    morld.set_unit_prop(target["id"], PROP_WATER_AMOUNT, target["capacity"])

    yield ui.dialog([
        f"{source_name}에서 {target['name']}에 물을 가득 담았다.",
        f"물: {target['capacity']}/{target['capacity']}",
    ])
    morld.advance_time_des(5 * 60_000)


def _npc_fill_water_container(npc_id):
    """NPC 인벤토리의 물 용기에 물 채우기 (non-generator 공용 헬퍼)

    Returns:
        bool: 채운 용기가 있으면 True
    """
    from assets.registry import get_unique_id, get_item_class
    from assets.items.garden_items import PROP_WATER_AMOUNT

    inventory = morld.get_unit_inventory(npc_id)
    if not inventory:
        return False

    filled = False
    for item_id, count in inventory.items():
        if count <= 0:
            continue
        info = morld.get_item_info(item_id)
        if not info:
            continue
        passive = info.get("passive_props") or {}
        if passive.get("can:water", 0) <= 0:
            continue
        uid = get_unique_id(item_id)
        item_cls = get_item_class(uid) if uid else None
        capacity = getattr(item_cls, "water_capacity", 1) if item_cls else 1
        current = morld.get_unit_prop(item_id, PROP_WATER_AMOUNT)
        if current < capacity:
            morld.set_unit_prop(item_id, PROP_WATER_AMOUNT, capacity)
            filled = True
    return filled


# ========================================
# 거실 오브젝트
# ========================================

class Fireplace(Object):
    unique_id = "fireplace"
    name = "벽난로"
    actions = [
        "call:look:살펴보기",
        "call:toggle_switch:불 끄기",
        "call:toggle_switch:불 피우기",
        "call:load_fuel:연료 넣기",
        "call:check_fuel:연료 확인",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "light:on": 1,
        "light:value": 4,       # 0.4 (정수 prop → lighting.py에서 /10 변환)
        "heat:output": 15,      # +15°C (light:on 상태일 때)
        "heat:depth": 1,        # 인접 1칸까지 영향
        "heat:fuel": 24,        # 초기 연료 24시간
        "heat:fuel_max": 36,    # 최대 연료 36시간
        "heat:fuel_mode": 1,    # 소비형 (1=소비, 0/없음=무한)
    }
    focus_text = {
        "default": "돌로 만들어진 오래된 벽난로. 저녁이면 불이 피워진다.",
        "저녁": "따뜻한 불꽃이 타오르고 있다.",
        "밤": "잔잔한 불씨가 남아 있다."
    }

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        super().instantiate(instance_id, region_id, location_id, x, y)
        try:
            import temperature
            temperature.register_heat_source(instance_id, region_id, location_id)
        except Exception as e:
            print(f"[Fireplace] heat source registration failed: {e}")
        try:
            import fuel
            fuel.register_fuel_source(instance_id, region_id, location_id)
        except Exception as e:
            print(f"[Fireplace] fuel source registration failed: {e}")

    def get_available_actions(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        base = [
            "call:load_fuel:연료 넣기",
            "call:check_fuel:연료 확인",
            "call:look:살펴보기",
            "call:debug_props:(디버그) 속성 보기#",
        ]
        if is_on:
            return ["call:toggle_switch:불 끄기"] + base
        else:
            return ["call:toggle_switch:불 피우기"] + base

    def look(self):
        """벽난로 살펴보기"""
        import fuel
        level = fuel.get_fuel_level(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        lines = ["돌로 쌓아 만든 오래된 벽난로다."]
        if is_on:
            lines.append(f"따뜻한 불꽃이 타오르고 있다. (연료: {level}시간)")
        else:
            lines.append("불이 꺼져 있다. 연료가 필요하다.")
        yield ui.dialog(lines)
        morld.advance_time_des(1 * 60_000)

    def toggle_switch(self):
        """벽난로 불 켜기/끄기"""
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        if is_on:
            morld.set_unit_prop(self.instance_id, "light:on", 0)
            yield ui.dialog("벽난로의 불을 껐다.")
        else:
            import fuel
            if fuel.get_fuel_level(self.instance_id) <= 0:
                yield ui.dialog("연료가 없어서 불을 피울 수 없다.")
                return
            morld.set_unit_prop(self.instance_id, "light:on", 1)
            yield ui.dialog("벽난로에 불을 피웠다.")
        morld.advance_time_des(1 * 60_000)

    def npc_toggle_switch(self, npc_id, target_state=None):
        """NPC 조명 토글 (non-generator)"""
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = target_state if target_state is not None else (0 if is_on else 1)
        if new_state == 1:
            import fuel
            if fuel.get_fuel_level(self.instance_id) <= 0:
                return is_on  # 연료 없으면 점화 불가
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        return new_state

    def load_fuel(self):
        """플레이어가 연료를 넣기"""
        import fuel
        from assets.registry import get_unique_id
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        fuel_items = []
        for item_id, count in (inventory or {}).items():
            if count <= 0:
                continue
            uid = get_unique_id(item_id)
            if uid in fuel.FUEL_VALUES:
                info = morld.get_item_info(item_id)
                name = info.get("name", uid) if info else uid
                fuel_items.append({"item_id": item_id, "unique_id": uid,
                                   "name": name, "count": count})
        if not fuel_items:
            yield ui.dialog("연료로 쓸 수 있는 아이템이 없다.")
            return
        total_added = 0
        for fi in fuel_items:
            added = fuel.npc_load_fuel(player_id, self.instance_id,
                                       fi["unique_id"], fi["count"])
            total_added += added
        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        yield ui.dialog([
            f"{self.name}에 연료를 넣었다. (+{total_added}시간)",
            f"연료: {level}/{max_fuel}시간",
        ])
        morld.advance_time_des(2 * 60_000)

    def check_fuel(self):
        """연료 상태 확인"""
        import fuel
        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        state = "켜짐" if is_on else "꺼짐"
        yield ui.dialog([f"{self.name} ({state})", f"연료: {level}/{max_fuel}시간"])

    def npc_load_fuel(self, npc_id, item_uid, count=1):
        """NPC 연료 장전 (non-generator)"""
        import fuel
        return fuel.npc_load_fuel(npc_id, self.instance_id, item_uid, count)


# ========================================
# 조명 오브젝트
# ========================================

class Window(Object):
    """창문 - 실외 밝기를 실내로 전달"""
    unique_id = "window"
    name = "창문"
    props = {"light:window": 1}
    actions = ["call:look:밖을 보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "밖이 내다보이는 창문."}

    def look(self):
        yield ui.dialog(["창문 밖을 내다본다."])
        morld.advance_time_des(1 * 60_000)


class WallLamp(Object):
    """벽등 - 저택 실내 기본 조명 (밝기 0.5)"""
    unique_id = "wall_lamp"
    name = "벽등"
    props = {"light:on": 1, "light:value": 5}
    actions = ["call:toggle_switch:끄기", "call:toggle_switch:켜기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "벽에 걸린 기름등."}

    def get_available_actions(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        base = ["call:debug_props:(디버그) 속성 보기#"]
        if is_on:
            return ["call:toggle_switch:끄기"] + base
        else:
            return ["call:toggle_switch:켜기"] + base

    def toggle_switch(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = 0 if is_on else 1
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        yield ui.dialog("등을 켰다." if new_state else "등을 껐다.")
        morld.advance_time_des(1 * 60_000)

    def npc_toggle_switch(self, npc_id, target_state=None):
        """NPC 조명 토글 (non-generator)"""
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = target_state if target_state is not None else (0 if is_on else 1)
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        return new_state


class Candelabra(Object):
    """촛대 - 식탁/복도용 (밝기 0.3)"""
    unique_id = "candelabra"
    name = "촛대"
    props = {"light:on": 1, "light:value": 3}
    actions = ["call:toggle_switch:끄기", "call:toggle_switch:켜기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "촛대."}

    def get_available_actions(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        base = ["call:debug_props:(디버그) 속성 보기#"]
        if is_on:
            return ["call:toggle_switch:끄기"] + base
        else:
            return ["call:toggle_switch:켜기"] + base

    def toggle_switch(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = 0 if is_on else 1
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        if new_state:
            yield ui.dialog("촛불을 켰다.")
        else:
            yield ui.dialog("촛불을 껐다.")
        morld.advance_time_des(1 * 60_000)

    def npc_toggle_switch(self, npc_id, target_state=None):
        """NPC 조명 토글 (non-generator)"""
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = target_state if target_state is not None else (0 if is_on else 1)
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        return new_state


class OilLamp(Object):
    """기름등 - 오두막/은신처용 (밝기 0.4)"""
    unique_id = "oil_lamp"
    name = "기름등"
    props = {"light:on": 1, "light:value": 4}
    actions = ["call:toggle_switch:끄기", "call:toggle_switch:켜기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "기름을 넣어 쓰는 낡은 등."}

    def get_available_actions(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        base = ["call:debug_props:(디버그) 속성 보기#"]
        if is_on:
            return ["call:toggle_switch:끄기"] + base
        else:
            return ["call:toggle_switch:켜기"] + base

    def toggle_switch(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = 0 if is_on else 1
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        yield ui.dialog("등을 켰다." if new_state else "등을 껐다.")
        morld.advance_time_des(1 * 60_000)

    def npc_toggle_switch(self, npc_id, target_state=None):
        """NPC 조명 토글 (non-generator)"""
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        new_state = target_state if target_state is not None else (0 if is_on else 1)
        morld.set_unit_prop(self.instance_id, "light:on", new_state)
        return new_state


class OldSofa(Object):
    unique_id = "old_sofa"
    name = "낡은 소파"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture:sit": 1,
        "posture_slots": 1,
        "seated_by:seat": -1,
    }
    focus_text = {"default": "오래 사용해서 닳았지만 여전히 푹신한 소파."}


class LivingSofa(Object):
    """
    앉을 수 있는 거실 소파 (3인용)
    """
    unique_id = "living_sofa"
    name = "거실 소파"
    actions = [
        "call:sit:앉기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "posture:sit": 1,
        "posture_slots": 3,
        "seated_by:left": -1,
        "seated_by:center": -1,
        "seated_by:right": -1,
    }
    focus_text = {"default": "푹신하고 넓은 거실 소파. 편하게 앉아 쉴 수 있다."}


class Bookshelf(Object):
    unique_id = "bookshelf"
    name = "책장"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "벽면을 따라 놓인 큰 책장. 다양한 책이 꽂혀 있다."}

    def look(self):
        """책장 살펴보기"""
        yield ui.dialog([
            "다양한 책이 꽂혀 있다.",
            "소설, 역사서, 요리책... 장르가 다양하다."
        ])
        morld.advance_time_des(2 * 60_000)


# ========================================
# 식당 오브젝트
# ========================================

class DiningTable(Object):
    unique_id = "dining_table"
    name = "긴 식탁"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    props = {"cover:level": 2}  # COVER_HALF
    focus_text = {"default": "여섯 명이 앉을 수 있는 긴 나무 식탁. 잘 닦여 있다."}

    def look(self):
        """식탁 살펴보기"""
        yield ui.dialog([
            "잘 닦인 긴 나무 식탁이다.",
            "여섯 개의 의자가 가지런히 놓여 있다."
        ])
        morld.advance_time_des(1 * 60_000)


class DiningChair(Object):
    """
    앉을 수 있는 식탁 의자 (4인용)
    """
    unique_id = "dining_chair"
    name = "식탁 의자"
    actions = [
        "call:sit:앉기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    props = {
        "posture:sit": 1,
        "posture_slots": 4,
        "seated_by:1": -1,
        "seated_by:2": -1,
        "seated_by:3": -1,
        "seated_by:4": -1,
    }
    focus_text = {"default": "식탁 주변에 놓인 나무 의자들. 앉아서 식사할 수 있다."}


# ========================================
# 주방 오브젝트
# ========================================

class Stove(Object):
    """
    조리 가능한 아궁이 (열원 + 연료 소비형)

    컨테이너 패턴 + 조리 기능 + 난방 기능:
    - open: 재료 넣기/빼기 (인벤토리 조회)
    - cook: 레시피 매칭 후 조리 (연료 필요)
    - put_filter: food_ingredient 카테고리 아이템만 넣을 수 있음
    - load_fuel: 연료 투입 (나무조각/나뭇가지/통나무)
    """
    unique_id = "stove"
    name = "아궁이"
    put_filter = ["food_ingredient"]  # 음식 재료만 넣을 수 있음
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:재료 넣기",
        "call:cook:조리하기",
        "call:load_fuel:연료 넣기",
        "call:check_fuel:연료 확인",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "light:on": 1,
        "light:value": 3,       # 0.3 (아궁이 불꽃)
        "heat:output": 10,      # +10°C (주방 규모)
        "heat:depth": 0,        # 주방에만 영향
        "heat:fuel": 18,        # 초기 연료 18시간
        "heat:fuel_max": 24,    # 최대 연료 24시간
        "heat:fuel_mode": 1,    # 소비형
    }
    focus_text = {"default": "요리에 사용하는 큰 아궁이."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        super().instantiate(instance_id, region_id, location_id, x, y)
        if self.props.get("heat:output"):
            try:
                import temperature
                temperature.register_heat_source(instance_id, region_id, location_id)
            except Exception as e:
                print(f"[{self.name}] heat source registration failed: {e}")
        if self.props.get("heat:fuel_mode"):
            try:
                import fuel
                fuel.register_fuel_source(instance_id, region_id, location_id)
            except Exception as e:
                print(f"[{self.name}] fuel source registration failed: {e}")

    def get_available_actions(self):
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        base = [
            "call:look:살펴보기",
            "container#",
            "call:put:재료 넣기",
            "call:load_fuel:연료 넣기",
            "call:check_fuel:연료 확인",
            "call:debug_props:(디버그) 속성 보기#",
        ]
        if is_on:
            return ["call:cook:조리하기"] + base
        else:
            return base  # 꺼져 있으면 조리 불가

    def look(self):
        """아궁이 살펴보기"""
        import fuel as fuel_mod
        level = fuel_mod.get_fuel_level(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        lines = [f"요리에 사용하는 큰 {self.name}다."]
        if is_on:
            lines.append(f"따뜻한 열기가 느껴진다. (연료: {level}시간)")
        else:
            lines.append("불이 꺼져 있다. 연료를 넣어야 한다.")
        yield ui.dialog(lines)
        morld.advance_time_des(1 * 60_000)

    def load_fuel(self):
        """플레이어가 연료를 넣기"""
        import fuel
        from assets.registry import get_unique_id
        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)
        fuel_items = []
        for item_id, count in (inventory or {}).items():
            if count <= 0:
                continue
            uid = get_unique_id(item_id)
            if uid in fuel.FUEL_VALUES:
                info = morld.get_item_info(item_id)
                name = info.get("name", uid) if info else uid
                fuel_items.append({"item_id": item_id, "unique_id": uid,
                                   "name": name, "count": count})
        if not fuel_items:
            yield ui.dialog("연료로 쓸 수 있는 아이템이 없다.")
            return
        total_added = 0
        for fi in fuel_items:
            added = fuel.npc_load_fuel(player_id, self.instance_id,
                                       fi["unique_id"], fi["count"])
            total_added += added
        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        yield ui.dialog([
            f"{self.name}에 연료를 넣었다. (+{total_added}시간)",
            f"연료: {level}/{max_fuel}시간",
        ])
        morld.advance_time_des(2 * 60_000)

    def check_fuel(self):
        """연료 상태 확인"""
        import fuel
        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        state = "켜짐" if is_on else "꺼짐"
        yield ui.dialog([f"{self.name} ({state})", f"연료: {level}/{max_fuel}시간"])

    def npc_load_fuel(self, npc_id, item_uid, count=1):
        """NPC 연료 장전 (non-generator)"""
        import fuel
        return fuel.npc_load_fuel(npc_id, self.instance_id, item_uid, count)

    def cook(self):
        """조리 실행 - 결과물은 플레이어 인벤토리로 바로 지급"""
        # 연료 체크
        fuel_mode = morld.get_unit_prop(self.instance_id, "heat:fuel_mode")
        if fuel_mode:
            is_on = morld.get_unit_prop(self.instance_id, "light:on")
            if not is_on:
                yield ui.dialog("불이 꺼져 있다. 연료를 넣어야 한다.")
                return
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield ui.dialog("재료가 없다.")
            return

        # unique_id 기반으로 변환
        inv_uniques = {}
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            unique_id = info.get("unique_id")
            if unique_id:
                inv_uniques[unique_id] = inv_uniques.get(unique_id, 0) + count

        # 레시피 매칭
        result = find_matching_recipe(inv_uniques)
        if not result:
            yield ui.dialog("이 재료로는 만들 수 있는 것이 없다.")
            return

        recipe_id, recipe, max_count = result

        # 재료 소비 (item_id 찾아서 소비)
        for unique_id, needed in recipe["ingredients"].items():
            consumed = 0
            for item_id, count in list(inventory.items()):
                info = morld.get_item_info(item_id)
                if info.get("unique_id") == unique_id and consumed < needed:
                    to_consume = min(count, needed - consumed)
                    morld.lost_item(self.instance_id, item_id, to_consume)
                    consumed += to_consume

        # 결과물 생성 → 플레이어 인벤토리로 바로 지급
        result_unique, result_count = recipe["result"]
        result_id = morld.get_item_id_by_unique(result_unique)

        if result_id is None:
            item_class = get_item_class(result_unique)
            if item_class:
                result_item = item_class()
                result_id = morld.create_id("item")
                result_item.instantiate(result_id)

        if result_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, result_id, result_count)

        # 플레이어 통계: 요리 횟수
        morld.set_unit_prop(player_id, "통계:요리횟수",
                            (morld.get_unit_prop(player_id, "통계:요리횟수") or 0) + 1)

        # 시간 경과 및 메시지
        yield ui.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time_des(recipe["cook_time"] * 60_000)

    def npc_cook(self, npc_id):
        """NPC 요리 (non-generator). NPC 인벤토리 재료로 조리 → 결과물 NPC에게 지급."""
        # 연료 체크
        fuel_mode = morld.get_unit_prop(self.instance_id, "heat:fuel_mode")
        if fuel_mode:
            is_on = morld.get_unit_prop(self.instance_id, "light:on")
            if not is_on:
                return False

        from recipes import find_matching_recipe
        from assets.registry import get_or_create_item_id, get_unique_id

        # NPC 인벤토리에서 재료 확인
        inventory = morld.get_unit_inventory(npc_id)
        if not inventory:
            return False

        inv_uniques = {}
        for item_id, count in inventory.items():
            uid = get_unique_id(item_id)
            if uid:
                inv_uniques[uid] = inv_uniques.get(uid, 0) + count

        result = find_matching_recipe(inv_uniques)
        if not result:
            return False

        recipe_id, recipe, max_count = result

        # 재료 소비
        for unique_id, needed in recipe["ingredients"].items():
            item_id = get_or_create_item_id(unique_id)
            if item_id:
                morld.remove_item(npc_id, item_id, needed)

        # 결과물 생성
        result_unique, result_count = recipe["result"]
        result_id = get_or_create_item_id(result_unique)
        if result_id:
            import inventory as inv_module
            inv_module.safe_give_item(npc_id, result_id, result_count)

        return True


class Kettle(Object):
    """
    음료 제조용 주전자

    컨테이너 패턴 + 음료 제조 기능:
    - open: 재료 넣기/빼기 (인벤토리 조회)
    - brew: 레시피 매칭 후 음료 제조
    - put_filter: drink_ingredient 카테고리 아이템만 넣을 수 있음
    """
    unique_id = "kettle"
    name = "주전자"
    put_filter = ["drink_ingredient"]  # 음료 재료만 넣을 수 있음
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:재료 넣기",
        "call:brew:끓이기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "물을 끓이거나 차를 우릴 수 있는 주전자."}

    def look(self):
        """주전자 살펴보기"""
        yield ui.dialog([
            "물을 끓이거나 차를 우릴 수 있는 주전자다.",
            "아궁이 위에 올려두면 사용할 수 있다."
        ])
        morld.advance_time_des(1 * 60_000)

    def brew(self):
        """음료 제조 - 결과물은 플레이어 인벤토리로 바로 지급"""
        from recipes import find_matching_recipe, RECIPES
        from assets.registry import get_item_class

        player_id = morld.get_player_id()

        # 현재 재료 확인
        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            yield ui.dialog("재료가 없다.")
            return

        # unique_id 기반으로 변환
        inv_uniques = {}
        for item_id, count in inventory.items():
            info = morld.get_item_info(item_id)
            unique_id = info.get("unique_id")
            if unique_id:
                inv_uniques[unique_id] = inv_uniques.get(unique_id, 0) + count

        # 레시피 매칭
        result = find_matching_recipe(inv_uniques)
        if not result:
            yield ui.dialog("이 재료로는 만들 수 있는 것이 없다.")
            return

        recipe_id, recipe, max_count = result

        # 재료 소비 (item_id 찾아서 소비)
        for unique_id, needed in recipe["ingredients"].items():
            consumed = 0
            for item_id, count in list(inventory.items()):
                info = morld.get_item_info(item_id)
                if info.get("unique_id") == unique_id and consumed < needed:
                    to_consume = min(count, needed - consumed)
                    morld.lost_item(self.instance_id, item_id, to_consume)
                    consumed += to_consume

        # 결과물 생성 → 플레이어 인벤토리로 바로 지급
        result_unique, result_count = recipe["result"]
        result_id = morld.get_item_id_by_unique(result_unique)

        if result_id is None:
            item_class = get_item_class(result_unique)
            if item_class:
                result_item = item_class()
                result_id = morld.create_id("item")
                result_item.instantiate(result_id)

        if result_id:
            import inventory as inv_module
            inv_module.safe_give_item(player_id, result_id, result_count)

        # 플레이어 통계: 요리 횟수
        morld.set_unit_prop(player_id, "통계:요리횟수",
                            (morld.get_unit_prop(player_id, "통계:요리횟수") or 0) + 1)

        # 시간 경과 및 메시지
        yield ui.dialog(f"{recipe['name']}을(를) 만들었다!")
        morld.advance_time_des(recipe["cook_time"] * 60_000)

    def npc_brew(self, npc_id):
        """NPC 음료 제조 (non-generator). 주전자 인벤토리 재료 → 레시피 매칭 → NPC 지급."""
        from recipes import find_matching_recipe
        from assets.registry import get_or_create_item_id, get_unique_id

        inventory = morld.get_unit_inventory(self.instance_id)
        if not inventory:
            return False

        inv_uniques = {}
        for item_id, count in inventory.items():
            uid = get_unique_id(item_id)
            if uid:
                inv_uniques[uid] = inv_uniques.get(uid, 0) + count

        result = find_matching_recipe(inv_uniques)
        if not result:
            return False

        recipe_id, recipe, max_count = result

        # 재료 소비 (주전자에서)
        for unique_id, needed in recipe["ingredients"].items():
            item_id = get_or_create_item_id(unique_id)
            if item_id:
                morld.lost_item(self.instance_id, item_id, needed)

        # 결과물 → NPC 인벤토리
        result_unique, result_count = recipe["result"]
        result_id = get_or_create_item_id(result_unique)
        if result_id:
            import inventory as inv_module
            inv_module.safe_give_item(npc_id, result_id, result_count)

        return True


class Cupboard(Object):
    unique_id = "cupboard"
    name = "찬장"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "그릇과 조리도구가 정리된 찬장."}

    def look(self):
        """찬장 살펴보기"""
        yield ui.dialog(["그릇과 조리도구가 깔끔하게 정리되어 있다."])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 욕실 오브젝트
# ========================================

class Bathtub(Object):
    unique_id = "bathtub"
    name = "나무 욕조"
    actions = ["call:use:목욕하기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "action:bath": 1,
    }
    focus_text = {"default": "큰 나무 욕조. 따뜻한 물을 받아 목욕할 수 있다."}

    def use(self):
        """목욕하기"""
        player_id = morld.get_player_id()
        humidity.dry_unit(player_id, 100)
        temperature.warm_character(player_id, 2.0)
        try:
            import romance
            romance.clear_all_semen(player_id)
        except ImportError:
            pass
        yield ui.dialog([
            "따뜻한 물을 받아 목욕했다.",
            "몸이 개운해졌다."
        ])
        morld.advance_time_des(30 * 60_000)

    def npc_use(self, npc_id):
        """NPC 목욕 (non-generator) — 건조+보온+정액제거"""
        humidity.dry_unit(npc_id, 100)
        temperature.warm_character(npc_id, 2.0)
        try:
            import romance
            romance.clear_all_semen(npc_id)
        except ImportError:
            pass
        return True


class Washbasin(Object):
    unique_id = "washbasin"
    name = "세면대"
    actions = ["call:use:세수하기", "call:fill:물 받기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "도자기로 만든 세면대. 깨끗하게 관리되어 있다."}

    def use(self):
        """세수하기"""
        yield ui.dialog([
            "시원한 물로 얼굴을 씻었다.",
            "정신이 맑아졌다."
        ])
        morld.advance_time_des(5 * 60_000)

    def fill(self):
        """물 받기 - 물뿌리개/물통에 물 채우기"""
        yield from _fill_water_container(self.name)

    def npc_fill(self, npc_id):
        """NPC 물 받기 (non-generator)"""
        return _npc_fill_water_container(npc_id)


class KitchenSink(Object):
    """싱크대 - 주방 세척 및 물 받기"""
    unique_id = "kitchen_sink"
    name = "싱크대"
    actions = ["call:use:세수하기", "call:fill:물 받기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "주방 싱크대. 수도꼭지에서 물이 나온다."}

    def use(self):
        """세수하기"""
        yield ui.dialog([
            "싱크대에서 물로 얼굴을 씻었다.",
            "정신이 맑아졌다."
        ])
        morld.advance_time_des(5 * 60_000)

    def fill(self):
        """물 받기 - 물뿌리개/물통에 물 채우기"""
        yield from _fill_water_container(self.name)

    def npc_fill(self, npc_id):
        """NPC 물 받기 (non-generator)"""
        return _npc_fill_water_container(npc_id)


class WaterTap(Object):
    """수도꼭지 - 도시 물 공급 시설"""
    unique_id = "water_tap"
    name = "수도꼭지"
    actions = ["call:look:살펴보기", "call:fill:물 받기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "녹슨 수도꼭지. 틀면 아직 물이 나온다."}

    def look(self):
        yield ui.dialog([
            "녹슨 수도꼭지다.",
            "수압은 약하지만 물은 나온다."
        ])
        morld.advance_time_des(1 * 60_000)

    def fill(self):
        """물 받기 - 물뿌리개/물통/물병에 물 채우기"""
        yield from _fill_water_container(self.name)

    def npc_fill(self, npc_id):
        """NPC 물 받기 (non-generator)"""
        return _npc_fill_water_container(npc_id)


class DrumBath(Object):
    """간이 드럼통 욕조 - 도심 은신처용 (열원 겸용, 연료 소비형)"""
    unique_id = "drum_bath"
    name = "간이 드럼통 욕조"
    actions = [
        "call:use:목욕하기",
        "call:load_fuel:연료 넣기",
        "call:check_fuel:연료 확인",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    props = {
        "action:bath": 1,
        "light:on": 1,
        "heat:output": 5,
        "heat:depth": 0,
        "heat:fuel": 6,         # 초기 연료 6시간
        "heat:fuel_max": 12,    # 최대 연료 12시간
        "heat:fuel_mode": 1,    # 소비형
    }
    focus_text = {"default": "큰 드럼통을 잘라 만든 간이 욕조. 물을 데워 쓸 수 있다."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        super().instantiate(instance_id, region_id, location_id, x, y)
        temperature.register_heat_source(instance_id, region_id, location_id)
        try:
            import fuel
            fuel.register_fuel_source(instance_id, region_id, location_id)
        except Exception as e:
            print(f"[DrumBath] fuel source registration failed: {e}")

    def use(self):
        """목욕하기"""
        player_id = morld.get_player_id()
        humidity.dry_unit(player_id, 100)
        temperature.warm_character(player_id, 2.0)
        try:
            import romance
            romance.clear_all_semen(player_id)
        except ImportError:
            pass
        yield ui.dialog([
            "드럼통에 데운 물을 받아 몸을 씻었다.",
            "좁지만... 없는 것보단 낫다."
        ])
        morld.advance_time_des(20 * 60_000)

    def npc_use(self, npc_id):
        """NPC 목욕 (non-generator) — 건조+보온+정액제거"""
        humidity.dry_unit(npc_id, 100)
        temperature.warm_character(npc_id, 2.0)
        try:
            import romance
            romance.clear_all_semen(npc_id)
        except ImportError:
            pass
        return True

    def load_fuel(self):
        """플레이어가 연료를 넣기"""
        import fuel
        from assets.registry import get_unique_id

        player_id = morld.get_player_id()
        inventory = morld.get_unit_inventory(player_id)

        fuel_items = []
        for item_id, count in (inventory or {}).items():
            if count <= 0:
                continue
            uid = get_unique_id(item_id)
            if uid in fuel.FUEL_VALUES:
                info = morld.get_item_info(item_id)
                name = info.get("name", uid) if info else uid
                fuel_items.append({"item_id": item_id, "unique_id": uid,
                                   "name": name, "count": count})

        if not fuel_items:
            yield ui.dialog("연료로 쓸 수 있는 나뭇가지나 통나무가 없다.")
            return

        total_added = 0
        for fi in fuel_items:
            added = fuel.npc_load_fuel(player_id, self.instance_id,
                                       fi["unique_id"], fi["count"])
            total_added += added

        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        yield ui.dialog([
            f"욕조 아래에 연료를 넣었다. (+{total_added}시간)",
            f"연료: {level}/{max_fuel}시간",
        ])
        morld.advance_time_des(2 * 60_000)

    def check_fuel(self):
        """연료 상태 확인"""
        import fuel
        level = fuel.get_fuel_level(self.instance_id)
        max_fuel = fuel.get_fuel_max(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        state = "켜짐" if is_on else "꺼짐"
        yield ui.dialog([
            f"간이 드럼통 욕조 ({state})",
            f"연료: {level}/{max_fuel}시간",
        ])

    def npc_load_fuel(self, npc_id, item_uid, count=1):
        """NPC 연료 장전 (non-generator)"""
        import fuel
        return fuel.npc_load_fuel(npc_id, self.instance_id, item_uid, count)


# ========================================
# 창고 오브젝트
# ========================================

class CraftingTable(Object):
    """
    제작대 - 복잡한 아이템 제작 가능

    crafting_recipes.py의 workbench=True 레시피 사용
    """
    unique_id = "crafting_table"
    name = "제작대"
    actions = ["call:look:살펴보기", "call:craft:제작하기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "도구와 재료를 다룰 수 있는 튼튼한 작업대."}

    def look(self):
        """제작대 살펴보기"""
        yield ui.dialog([
            "튼튼한 나무로 만든 작업대다.",
            "복잡한 물건을 제작할 수 있다."
        ])
        morld.advance_time_des(1 * 60_000)

    def craft(self):
        """제작대에서 제작하기"""
        from crafting_recipes import get_workbench_recipes
        from crafting import open_craft_menu
        yield from open_craft_menu(get_workbench_recipes(), "제작대")

    def npc_craft(self, npc_id, recipe_id):
        """NPC 제작 (non-generator). 재료 확인 → 소비 → 결과물 지급."""
        from crafting_recipes import get_recipe
        from assets.registry import get_or_create_item_id

        recipe = get_recipe(recipe_id)
        if not recipe:
            return False

        # 재료 확인
        inv = morld.get_unit_inventory(npc_id)
        if not inv:
            return False
        for mat_uid, needed in recipe["materials"].items():
            mat_id = get_or_create_item_id(mat_uid)
            available = inv.get(mat_id, 0) if mat_id else 0
            if available < needed:
                return False

        # 재료 소비
        for mat_uid, needed in recipe["materials"].items():
            mat_id = get_or_create_item_id(mat_uid)
            if mat_id:
                morld.remove_item(npc_id, mat_id, needed)

        # 결과물 생성
        result_uid = recipe.get("result_id", recipe_id)
        result_id = get_or_create_item_id(result_uid)
        result_count = recipe.get("result_count", 1)
        if result_id:
            import inventory as inv_module
            inv_module.safe_give_item(npc_id, result_id, result_count)
        return True


# ========================================
# 소형 가구
# ========================================

class WoodenStool(Object):
    unique_id = "wooden_stool"
    name = "나무 의자"
    actions = ["call:sit:앉기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture:sit": 1,
        "posture_slots": 1,
        "seated_by:seat": -1,
    }
    focus_text = {"default": "튼튼한 나무 의자. 앉아서 쉴 수 있다."}


# ========================================
# 침실 오브젝트 (주인공 방)
# ========================================

class Bed(Object):
    unique_id = "bed"
    name = "침대"
    actions = ["call:lie_down:눕기", "call:sleep:잠자기", "call:debug_props:(디버그) 속성 보기#"]
    props = {
        "posture:lie": 1,
        "posture_slots": 2,
        "seated_by:left": -1,
        "seated_by:right": -1,
        "action:sleep": 1,
    }
    focus_text = {"default": "작지만 편안해 보이는 침대. 깨끗한 이불이 깔려 있다."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        """bed_owner가 설정되어 있으면 props에 bed_owner:{name} = 1 추가 (복수 소유자 지원)"""
        bed_owner = getattr(self, 'bed_owner', None)
        if bed_owner:
            # 클래스 변수 보호를 위해 인스턴스별 복사
            self.props = dict(self.props) if self.props else {}
            owners = bed_owner if isinstance(bed_owner, list) else [bed_owner]
            for owner in owners:
                self.props[f"bed_owner:{owner}"] = 1
        super().instantiate(instance_id, region_id, location_id, x, y)

    def _find_owner_unit(self, region_id, location_id, owner_unique):
        """방 주인 캐릭터가 같은 Location에 있으면 unit_id 반환"""
        unit_ids = morld.get_characters_at_location(region_id, location_id)
        for uid in unit_ids:
            info = morld.get_unit_info(uid)
            if info and info.get("unique_id") == owner_unique:
                return uid
        return None

    def _get_affection(self, owner_id, player_id):
        """캐릭터의 플레이어에 대한 호감도 조회"""
        owner_props = morld.get_unit_props(owner_id)
        player_info = morld.get_unit_info(player_id)
        player_name = player_info.get("name", "주인공")
        return owner_props.get(f"관계:{player_name}:호감", 0)

    def _is_sleeping_on_this_bed(self, owner_id):
        """주인이 이 침대에 누워있는지 확인 (seated_by 슬롯에 owner_id가 있으면 수면 중)"""
        seated_by = morld.get_unit_props_by_type(self.instance_id, "seated_by")
        for slot_name, occupant_id in seated_by.items():
            if occupant_id == owner_id:
                return True
        return False

    def lie_down(self):
        """눕기 - 방 주인이 있으면 캐릭터별 반응"""
        player_id = morld.get_player_id()

        # 빈 슬롯 확인
        slot = self._find_empty_slot()
        if slot is None:
            yield ui.dialog(["자리가 없다."])
            return

        # 방 주인 확인
        player_info = morld.get_unit_info(player_id)
        region_id = player_info["region_id"]
        location_id = player_info["location_id"]
        loc_info = morld.get_location_info(region_id, location_id)
        owner_unique = loc_info.get("owner") if loc_info else None

        # 주인공 방이거나 공용 방이면 → 침대 자체의 소유자 확인
        if not owner_unique or owner_unique == "player":
            # 침대 인스턴스에 owner_unique가 설정된 경우 (공유 공간용)
            bed_owner = getattr(self, 'bed_owner', None)
            if bed_owner:
                owner_unique = bed_owner
            else:
                success = morld.sit_on(player_id, self.instance_id, slot)
                if success:
                    yield ui.dialog([f"{self.name}에 누웠다."])
                return

        # 방 주인이 같은 방에 있는지 확인
        owner_id = self._find_owner_unit(region_id, location_id, owner_unique)

        if owner_id is None:
            # 주인 부재 - 그냥 눕기
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                yield ui.dialog([f"{self.name}에 몰래 누웠다."])
            return

        # 주인이 이 침대에서 자고 있는지 확인
        owner_sleeping = self._is_sleeping_on_this_bed(owner_id)
        affection = self._get_affection(owner_id, player_id)

        # 캐릭터 인스턴스를 통해 반응 위임
        from assets.characters import get_instance
        character = get_instance(owner_id)

        if character and hasattr(character, 'on_bed_awake'):
            if owner_sleeping:
                yield from character.on_bed_sleeping(self, player_id, slot, affection, owner_id)
            else:
                yield from character.on_bed_awake(self, player_id, slot, affection, region_id, owner_id)
        else:
            # 기타 캐릭터 - 기본 반응
            owner_info = morld.get_unit_info(owner_id)
            owner_name = owner_info.get("name", "누군가") if owner_info else "누군가"
            success = morld.sit_on(player_id, self.instance_id, slot)
            if success:
                if owner_sleeping:
                    yield ui.dialog([
                        f"{owner_name}(이)가 자고 있다.",
                        "조심스럽게 옆에 누웠다."
                    ])
                else:
                    yield ui.dialog([f"{self.name}에 누웠다."])

    # 캐릭터별 침대 반응은 각 캐릭터 파일로 이동:
    # - assets/characters/sera.py: on_bed_awake(), on_bed_sleeping()
    # - assets/characters/mila.py: on_bed_awake(), on_bed_sleeping()
    # - assets/characters/lina.py: on_bed_awake(), on_bed_sleeping()
    # - assets/characters/yuki.py: on_bed_awake(), on_bed_sleeping()
    # - assets/characters/ella.py: on_bed_awake(), on_bed_sleeping()

    def sleep(self):
        """잠자기"""
        yield ui.dialog(["침대에 누워 잠을 청했다."])
        morld.advance_time_des(480 * 60_000)  # 8시간 (DES: NPC 자율 행동)


class SleepingBag(Bed):
    """침낭 - 침대와 동일한 기능, 2인용"""
    unique_id = "sleeping_bag"
    name = "침낭"
    focus_text = {"default": "바닥에 펼쳐진 침낭. 좁지만 잠은 잘 수 있다."}


class SmallDesk(Object):
    unique_id = "small_desk"
    name = "작은 책상"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "작은 나무 책상. 서랍이 하나 달려 있다."}

    def look(self):
        """책상 살펴보기"""
        yield ui.dialog([
            "작은 나무 책상이다.",
            "서랍이 하나 달려 있다."
        ])
        morld.advance_time_des(1 * 60_000)


class Mirror(Object):
    unique_id = "mirror"
    name = "거울"
    actions = ["call:look:거울 보기", "call:debug_self_props:(디버그) 나를 돌아보기#", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "벽에 걸린 작은 거울. 내 모습을 비춰볼 수 있다."}

    def look(self):
        """거울 보기"""
        yield ui.dialog([
            "거울 속에 내 얼굴이 비친다.",
            "...그래, 이게 나다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 옷장 오브젝트
# ========================================

class Wardrobe(Object):
    """
    옷장 - 의류 보관 및 관리

    컨테이너 패턴:
    - container: 옷 넣기/빼기 (인벤토리 조회)
    - put_filter: clothing 카테고리 아이템만 넣을 수 있음
    - storage:clothing: NPC 동적 보관 대상
    """
    unique_id = "wardrobe"
    name = "옷장"
    put_filter = ["clothing"]  # 의류만 넣을 수 있음
    props = {
        "storage:clothing": 1,
    }
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:put:옷 넣기",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "옷을 보관할 수 있는 나무 옷장."}

    def instantiate(self, instance_id, region_id, location_id, x=None, y=None):
        """wardrobe_owner가 설정되어 있으면 props에 wardrobe_owner:{name} = 1 추가 (복수 소유자 지원)"""
        wardrobe_owner = getattr(self, 'wardrobe_owner', None)
        if wardrobe_owner:
            self.props = dict(self.props) if self.props else {}
            owners = wardrobe_owner if isinstance(wardrobe_owner, list) else [wardrobe_owner]
            for owner in owners:
                self.props[f"wardrobe_owner:{owner}"] = 1
        super().instantiate(instance_id, region_id, location_id, x, y)

    def look(self):
        """옷장 살펴보기"""
        yield ui.dialog([
            "큰 나무 옷장이다.",
            "옷을 넣거나 꺼낼 수 있다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 상점/편의점 오브젝트
# ========================================

class Shelf(Object):
    """
    선반 - 물건 보관 및 진열

    컨테이너 패턴:
    - container: 물건 넣기/빼기 (인벤토리 조회)
    - item_visible: True (아이템 개수 표시)
    """
    unique_id = "shelf"
    name = "선반"
    item_visible = True  # 아이템 개수 표시
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "물건을 놓을 수 있는 선반."}

    def look(self):
        """선반 살펴보기"""
        yield ui.dialog([
            "물건을 진열할 수 있는 선반이다.",
            "남은 물건이 있는지 확인해 볼 수 있다."
        ])
        morld.advance_time_des(1 * 60_000)


class Refrigerator(Object):
    """
    냉장고 - 음료 및 음식 보관

    컨테이너 패턴:
    - container: 물건 넣기/빼기 (인벤토리 조회)
    - item_visible: True (아이템 개수 표시)
    """
    unique_id = "refrigerator"
    name = "냉장고"
    item_visible = True  # 아이템 개수 표시
    actions = [
        "call:look:살펴보기",
        "container#",  # C# 기본 컨테이너 UI 사용 - 인벤토리 있을 때만 표시
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "낡은 냉장고. 전기가 안 들어와 그냥 보관함으로 쓰인다."}

    def look(self):
        """냉장고 살펴보기"""
        yield ui.dialog([
            "낡은 냉장고다.",
            "전기가 들어오지 않아 차갑지 않지만, 음료가 남아있을지도 모른다."
        ])
        morld.advance_time_des(1 * 60_000)


class KitchenFridge(Refrigerator):
    """주방 냉장고 - NPC가 식료품을 보관하는 용도"""
    unique_id = "kitchen_fridge"
    props = {
        "storage:food": 1,
        "storage:food_ingredient": 1,
        "storage:drink_ingredient": 1,
        "need:food_fish": 3,
        "need:log": 5,
        "세력": "숲속 저택",
    }
    focus_text = {"default": "주방에 놓인 낡은 냉장고. 식료품 보관에 쓰인다."}

    def look(self):
        yield ui.dialog([
            "주방에 놓인 낡은 냉장고다.",
            "전기는 들어오지 않지만, 식료품을 보관하는 데 쓰고 있다."
        ])
        morld.advance_time_des(1 * 60_000)


class IngredientStorage(Object):
    """재료 보관함 - 목재, 재료 보관"""
    unique_id = "ingredient_storage"
    name = "재료 보관함"
    item_visible = True
    props = {
        "storage:material": 1,
        "storage:seed": 1,
        "storage:garden_supply": 1,
        "need:log": 5,
        "need:wood_chip": 8,
        "세력": "숲속 저택",
    }
    actions = [
        "call:look:살펴보기",
        "container#",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "목재와 재료를 보관하는 나무 선반."}

    def look(self):
        yield ui.dialog([
            "목재와 각종 재료를 보관하는 선반이다.",
            "통나무와 나뭇가지가 정리되어 있다."
        ])
        morld.advance_time_des(1 * 60_000)


class FoodStorage(Object):
    """식량 보관함 - 은신처용 식량 보관"""
    unique_id = "food_storage"
    name = "식량 보관함"
    item_visible = True
    props = {
        "storage:food": 1,
        "storage:food_ingredient": 1,
        "storage:drink_ingredient": 1,
        "storage:material": 1,
        "need:food_fish": 3,
        "need:branch": 6,
        "need:log": 3,
        "세력": "도시",
    }
    actions = [
        "call:look:살펴보기",
        "container#",
        "call:debug_props:(디버그) 속성 보기#"
    ]
    focus_text = {"default": "은신처에 마련된 간이 식량 보관함."}

    def look(self):
        yield ui.dialog([
            "나무 상자로 만든 간이 식량 보관함이다.",
            "비상 식량이 조금 들어있다."
        ])
        morld.advance_time_des(1 * 60_000)


class PortableStove(Stove):
    """간이 화로 - 은신처용 조리 도구 + 보온 (연료 소비형)

    Stove를 상속받아 instantiate(temperature+fuel 등록), load_fuel, check_fuel,
    npc_load_fuel 등 연료 관련 메서드를 공유합니다.
    """
    unique_id = "portable_stove"
    name = "간이 화로"
    props = {
        "light:on": 1,
        "light:value": 2,       # 0.2 (약한 불빛)
        "heat:output": 8,       # +8°C (Fireplace=15 대비 소규모)
        "heat:depth": 0,        # 해당 location에만 영향
        "heat:fuel": 12,        # 초기 연료 12시간
        "heat:fuel_max": 24,    # 최대 연료 24시간
        "heat:fuel_mode": 1,    # 소비형 (1=소비, 0/없음=무한)
    }
    focus_text = {"default": "은신처에 놓인 간이 화로. 간단한 조리가 가능하다."}

    def look(self):
        import fuel as fuel_mod
        level = fuel_mod.get_fuel_level(self.instance_id)
        is_on = morld.get_unit_prop(self.instance_id, "light:on") == 1
        lines = ["연탄과 냄비로 만든 간이 화로다.", "간단한 조리 정도는 할 수 있다."]
        if is_on:
            lines.append(f"은은한 온기가 느껴진다. (연료: {level}시간)")
        else:
            lines.append("불이 꺼져 있다. 연료가 필요하다.")
        yield ui.dialog(lines)
        morld.advance_time_des(1 * 60_000)


# ========================================
# 2층 복도 오브젝트
# ========================================

class CorridorWindow(Object):
    unique_id = "corridor_window"
    name = "복도 창문"
    props = {"light:window": 1}
    actions = ["call:look:밖을 보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "2층 복도에 있는 큰 창문. 앞마당이 내려다보인다."}

    def look(self):
        """창문 밖을 보기"""
        yield ui.dialog([
            "2층 창문에서 앞마당이 내려다보인다.",
            "정원이 한눈에 들어온다."
        ])
        morld.advance_time_des(2 * 60_000)


class Vase(Object):
    unique_id = "vase"
    name = "화병"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "복도 끝에 놓인 장식용 화병. 마른 꽃이 꽂혀 있다."}

    def look(self):
        """화병 살펴보기"""
        yield ui.dialog([
            "장식용 화병이다.",
            "마른 꽃이 꽂혀 있다."
        ])
        morld.advance_time_des(1 * 60_000)


# ========================================
# 장식 오브젝트
# ========================================

class OldDoll(Object):
    """
    낡은 인형 - 귀여운 곰 인형
    owner는 instantiate 시 지정 (예: 세라 방에서 sera 소유로 배치)
    """
    unique_id = "old_doll"
    name = "낡은 인형"
    actions = ["call:look:살펴보기", "call:debug_props:(디버그) 속성 보기#"]
    focus_text = {"default": "작고 낡은 곰 인형. 누군가 소중히 다뤄온 흔적이 보인다."}

    def look(self):
        """인형 살펴보기"""
        yield ui.dialog([
            "작은 곰 인형이다.",
            "오래되어 색이 바랬지만, 깨끗하게 관리되어 있다.",
            "...누가 이런 걸 두고 있는 걸까?"
        ])
        morld.advance_time_des(1 * 60_000)
