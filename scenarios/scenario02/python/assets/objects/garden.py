# assets/objects/garden.py - 텃밭 오브젝트
#
# GardenBed: 씨앗 심기, 물 주기, 비료 주기, 수확 등 텃밭 상호작용

import morld
import ui
from assets.base import Object

DEFAULT_FURROW_COUNT = 4


class GardenBed(Object):
    """
    텃밭 오브젝트

    이랑(furrow)에 씨앗을 심고, 수분/비료를 관리하여 작물을 키운다.
    수분/비료는 텃밭 단위(공유), 씨앗/성장은 이랑 단위(개별).
    """
    unique_id = "garden_bed"
    name = "텃밭"
    actions = [
        "call:look:살펴보기",
        "call:plant:씨 심기",
        "call:water:물 주기",
        "call:fertilize:비료 주기",
        "call:harvest:수확하기",
        "call:remove_plant:식물 제거",
        "call:debug_props:(디버그) 속성 보기#",
    ]
    focus_text = {"default": "잘 정돈된 텃밭이다. 이랑이 줄지어 나 있다."}

    def __init__(self, furrow_count=None):
        super().__init__()
        self._init_furrow_count = furrow_count or DEFAULT_FURROW_COUNT

    def instantiate(self, instance_id: int, region_id: int, location_id: int, x: float, y: float = 0):
        super().instantiate(instance_id, region_id, location_id, x, y)

        # 이랑수 초기화
        import garden
        furrow_count = morld.get_unit_prop(instance_id, garden.PROP_FURROW_COUNT)
        if not furrow_count:
            morld.set_unit_prop(instance_id, garden.PROP_FURROW_COUNT, self._init_furrow_count)

        # 생장 시스템 등록
        garden.register_garden(instance_id)

    def get_focus_text(self):
        import garden

        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT)
        moisture = morld.get_unit_prop(self.instance_id, garden.PROP_MOISTURE)
        fertilizer = morld.get_unit_prop(self.instance_id, garden.PROP_FERTILIZER)

        if not furrow_count:
            return "빈 텃밭이다."

        # 이랑 상태 요약
        planted = 0
        harvestable = 0
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if seed_code:
                planted += 1
                growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
                if growth >= garden.MAX_GROWTH:
                    harvestable += 1

        moisture_text = garden.get_moisture_text(moisture)
        parts = [f"텃밭 — 이랑 {furrow_count}개"]
        if planted > 0:
            parts.append(f"재배 중 {planted}개")
        if harvestable > 0:
            parts.append(f"수확 가능 {harvestable}개")
        parts.append(f"수분: {moisture_text}")
        if fertilizer > 0:
            parts.append(f"비료: {fertilizer}")

        return " | ".join(parts)

    # ========================================
    # 살펴보기
    # ========================================

    def look(self):
        import garden

        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT)
        moisture = morld.get_unit_prop(self.instance_id, garden.PROP_MOISTURE)
        fertilizer = morld.get_unit_prop(self.instance_id, garden.PROP_FERTILIZER)

        if not furrow_count:
            yield ui.dialog("빈 텃밭이다. 이랑이 없다.")
            return

        lines = ["[b]텃밭 상태[/b]", ""]
        lines.append(f"  수분: {garden.get_moisture_text(moisture)} ({moisture}/100)")
        lines.append(f"  비료: {fertilizer}/100")
        lines.append("")

        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if not seed_code:
                lines.append(f"  이랑 {i + 1}: [color=gray](비어있음)[/color]")
            else:
                growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
                name = garden.get_seed_name(seed_code)
                stage = garden.get_growth_stage_text(growth)
                lines.append(f"  이랑 {i + 1}: {name} — {stage} ({growth}%)")

        yield ui.dialog("\n".join(lines))

    # ========================================
    # 씨 심기
    # ========================================

    def plant(self):
        import garden
        from assets.registry import get_or_create_item_id

        player_id = morld.get_player_id()

        # 빈 이랑 찾기
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0
        empty_furrows = []
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if not seed_code:
                empty_furrows.append(i)

        if not empty_furrows:
            yield ui.dialog("빈 이랑이 없다. 식물을 제거하거나 밭을 넓혀야 한다.")
            return

        # 인벤토리에서 씨앗 찾기
        inventory = morld.get_unit_inventory(player_id)
        seeds = []
        if inventory:
            for item_id, count in inventory.items():
                info = morld.get_item_info(item_id)
                if info and info.get("category") == "seed":
                    unique_id = info.get("unique_id", "")
                    code = garden.SEED_CODE_MAP.get(unique_id, 0)
                    if code:
                        seeds.append({
                            "item_id": item_id,
                            "unique_id": unique_id,
                            "name": info.get("name", "씨앗"),
                            "code": code,
                            "count": count,
                        })

        if not seeds:
            yield ui.dialog("씨앗이 없다.")
            return

        # 씨앗 선택 → 이랑 선택
        state = {"seed": None, "furrow": None}

        def build_seed_menu():
            lines = ["어떤 씨앗을 심을까?", ""]
            for s in seeds:
                lines.append(f"  [url=@proc:seed:{s['code']}]{s['name']}[/url] [color=gray](x{s['count']})[/color]")
            lines.append("")
            lines.append("[url=@ret:cancel]취소[/url]")
            return "\n".join(lines)

        def build_furrow_menu():
            lines = [f"{garden.get_seed_name(state['seed'])} 씨앗을 어디에 심을까?", ""]
            for fi in empty_furrows:
                lines.append(f"  [url=@proc:furrow:{fi}]이랑 {fi + 1}[/url]")
            lines.append("")
            lines.append("[url=@proc:back]◀ 뒤로[/url]")
            return "\n".join(lines)

        def on_select(action):
            if action == "init":
                return None
            if action == "back":
                state["seed"] = None
                return build_seed_menu()
            if action.startswith("seed:"):
                code = int(action[5:])
                state["seed"] = code
                return build_furrow_menu()
            if action.startswith("furrow:"):
                fi = int(action[7:])
                state["furrow"] = fi
                return True
            return None

        yield ui.dialog(build_seed_menu(), autofill="off", proc=on_select, result=state)

        if state["seed"] and state["furrow"] is not None:
            code = state["seed"]
            fi = state["furrow"]
            seed_info = garden.SEED_REGISTRY.get(code)
            if not seed_info:
                return

            # 씨앗 소비
            seed_item_id = get_or_create_item_id(seed_info["seed_unique_id"])
            if seed_item_id and morld.has_item(player_id, seed_item_id):
                morld.lost_item(player_id, seed_item_id, 1)

                # prop 설정
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{fi}", code)
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{fi}", 0)

                yield ui.dialog(f"{seed_info['name']} 씨앗을 {fi + 1}번째 이랑에 심었다.")
                morld.advance_time_des(10 * 60_000)

    # ========================================
    # 물 주기
    # ========================================

    def water(self):
        import garden
        from assets.items.garden_items import PROP_WATER_AMOUNT

        player_id = morld.get_player_id()

        # 물 아이템 찾기 (물:양 > 0)
        water_items = self._find_water_containers(player_id)

        if not water_items:
            yield ui.dialog("물이 없다. 물뿌리개나 물통에 물을 받아와야 한다.")
            return

        moisture = morld.get_unit_prop(self.instance_id, garden.PROP_MOISTURE)
        if moisture >= garden.MAX_MOISTURE:
            yield ui.dialog("텃밭에 이미 물이 충분하다.")
            return

        # 물 아이템이 하나면 바로 사용, 여러 개면 선택
        if len(water_items) == 1:
            container = water_items[0]
        else:
            state = {"selected": None}

            def on_select(action):
                if action == "init":
                    return None
                for wi in water_items:
                    if str(wi["id"]) == action:
                        state["selected"] = wi
                        return True
                return None

            lines = ["어떤 도구로 물을 줄까?", ""]
            for wi in water_items:
                lines.append(f"  [url=@proc:{wi['id']}]{wi['name']}[/url] [color=gray](물 {wi['water']}/{wi['capacity']})[/color]")
            lines.append("")
            lines.append("[url=@ret:cancel]취소[/url]")

            yield ui.dialog("\n".join(lines), autofill="off", proc=on_select, result=state)
            container = state.get("selected")

        if not container:
            return

        # 물 주기 실행
        new_moisture = min(garden.MAX_MOISTURE, moisture + garden.WATERING_AMOUNT)
        morld.set_unit_prop(self.instance_id, garden.PROP_MOISTURE, new_moisture)

        # 물 감소
        new_water = container["water"] - 1
        morld.set_unit_prop(container["id"], PROP_WATER_AMOUNT, new_water)

        moisture_text = garden.get_moisture_text(new_moisture)
        if new_water > 0:
            yield ui.dialog([
                "텃밭에 물을 주었다.",
                f"수분: {moisture_text} ({new_moisture}/100)",
            ])
        else:
            yield ui.dialog([
                "텃밭에 물을 주었다.",
                f"수분: {moisture_text} ({new_moisture}/100)",
                f"{container['name']}의 물이 다 떨어졌다.",
            ])
        morld.advance_time_des(10 * 60_000)

    def _find_water_containers(self, player_id):
        """인벤토리에서 물이 든 용기 검색 (can:water prop 기반)"""
        from assets.registry import get_unique_id, get_item_class
        from assets.items.garden_items import PROP_WATER_AMOUNT

        result = []
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
            water = morld.get_unit_prop(item_id, PROP_WATER_AMOUNT)
            if water <= 0:
                continue
            uid = get_unique_id(item_id)
            item_cls = get_item_class(uid) if uid else None
            capacity = getattr(item_cls, "water_capacity", 1) if item_cls else 1
            result.append({
                "id": item_id,
                "unique_id": uid or "",
                "name": info.get("name", f"아이템#{item_id}"),
                "water": water,
                "capacity": capacity,
            })
        return result

    # ========================================
    # 비료 주기
    # ========================================

    def fertilize(self):
        import garden
        from assets.registry import get_or_create_item_id

        player_id = morld.get_player_id()
        fertilizer_id = get_or_create_item_id("fertilizer")

        if not fertilizer_id or not morld.has_item(player_id, fertilizer_id):
            yield ui.dialog("비료가 없다.")
            return

        current = morld.get_unit_prop(self.instance_id, garden.PROP_FERTILIZER)
        if current >= garden.MAX_FERTILIZER:
            yield ui.dialog("텃밭에 이미 비료가 충분하다.")
            return

        # 비료 소비
        morld.lost_item(player_id, fertilizer_id, 1)

        new_fertilizer = min(garden.MAX_FERTILIZER, current + garden.FERTILIZER_AMOUNT)
        morld.set_unit_prop(self.instance_id, garden.PROP_FERTILIZER, new_fertilizer)

        yield ui.dialog([
            "텃밭에 비료를 뿌렸다.",
            f"비료: {new_fertilizer}/100",
            "작물이 더 빨리 자랄 것이다.",
        ])
        morld.advance_time_des(10 * 60_000)

    # ========================================
    # 수확
    # ========================================

    def harvest(self):
        import garden

        player_id = morld.get_player_id()
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0

        # 수확 가능한 이랑 찾기
        harvestable = []
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if not seed_code:
                continue
            growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
            if growth >= garden.MAX_GROWTH:
                harvestable.append(i)

        if not harvestable:
            yield ui.dialog("수확할 작물이 없다.")
            return

        # 모든 수확 가능 이랑 수확
        results = []
        for fi in harvestable:
            result = garden.do_harvest(self.instance_id, fi, player_id)
            if result:
                results.append(result)

        # 결과 메시지
        lines = ["수확했다!", ""]
        for r in results:
            line = f"  {r['crop_name']} {r['crop_count']}개"
            if r.get("seed_name"):
                line += f" + {r['seed_name']} {r['seed_count']}개"
            lines.append(line)

        yield ui.dialog(lines)
        morld.advance_time_des(20 * 60_000)

    # ========================================
    # 식물 제거
    # ========================================

    def remove_plant(self):
        import garden

        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0

        # 식물이 있는 이랑 찾기
        planted = []
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if seed_code:
                growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
                name = garden.get_seed_name(seed_code)
                stage = garden.get_growth_stage_text(growth)
                planted.append({"index": i, "name": name, "stage": stage, "growth": growth})

        if not planted:
            yield ui.dialog("제거할 식물이 없다.")
            return

        state = {"furrow": None}

        def on_select(action):
            if action == "init":
                return None
            if action.startswith("furrow:"):
                state["furrow"] = int(action[7:])
                return True
            return None

        lines = ["어떤 식물을 제거할까? (씨앗은 돌아오지 않습니다)", ""]
        for p in planted:
            lines.append(f"  [url=@proc:furrow:{p['index']}]이랑 {p['index'] + 1}: {p['name']} — {p['stage']} ({p['growth']}%)[/url]")
        lines.append("")
        lines.append("[url=@ret:cancel]취소[/url]")

        yield ui.dialog("\n".join(lines), autofill="off", proc=on_select, result=state)

        if state["furrow"] is not None:
            fi = state["furrow"]
            name = garden.get_seed_name(
                morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{fi}")
            )
            morld.set_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{fi}", 0)
            morld.set_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{fi}", 0)

            yield ui.dialog(f"이랑 {fi + 1}의 {name}을(를) 뽑아냈다.")
            morld.advance_time_des(5 * 60_000)

    # ========================================
    # NPC 전용 메서드 (non-generator)
    # ========================================

    def needs_water(self):
        """텃밭에 물이 필요한지 (수분 < 50)"""
        import garden
        moisture = morld.get_unit_prop(self.instance_id, garden.PROP_MOISTURE)
        return moisture < 50

    def has_harvestable(self):
        """수확 가능한 작물이 있는지"""
        import garden
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if seed_code:
                growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
                if growth >= garden.MAX_GROWTH:
                    return True
        return False

    def has_empty_furrow(self):
        """빈 이랑이 있는지"""
        import garden
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if not seed_code:
                return True
        return False

    def npc_water(self, npc_id):
        """NPC 물주기 — 수분 증가 (도구 물 소모 없음)"""
        import garden
        moisture = morld.get_unit_prop(self.instance_id, garden.PROP_MOISTURE)
        new_moisture = min(garden.MAX_MOISTURE, moisture + garden.WATERING_AMOUNT)
        morld.set_unit_prop(self.instance_id, garden.PROP_MOISTURE, new_moisture)

    def npc_harvest(self, npc_id):
        """NPC 수확 — 성숙 작물 수확 후 NPC 인벤토리에 지급

        Returns:
            int: 수확한 이랑 수
        """
        import garden
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0
        harvested = 0
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if not seed_code:
                continue
            growth = morld.get_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}")
            if growth >= garden.MAX_GROWTH:
                garden.do_harvest(self.instance_id, i, npc_id)
                harvested += 1
        return harvested

    def npc_plant(self, npc_id, seed_code):
        """NPC 씨 심기 — 첫 번째 빈 이랑에 심기

        Returns:
            bool: 성공 여부
        """
        import garden
        from assets.registry import get_or_create_item_id

        seed_info = garden.SEED_REGISTRY.get(seed_code)
        if not seed_info:
            return False

        # NPC가 씨앗을 가지고 있는지 확인
        seed_item_id = get_or_create_item_id(seed_info["seed_unique_id"])
        if not seed_item_id or not morld.has_item(npc_id, seed_item_id):
            return False

        # 빈 이랑 찾기
        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0
        for i in range(furrow_count):
            if not morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}"):
                # 심기
                morld.lost_item(npc_id, seed_item_id, 1)
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}", seed_code)
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}", 0)
                return True
        return False

    def npc_fertilize(self, npc_id):
        """NPC 비료 주기 (non-generator)

        Returns:
            bool: 성공 여부
        """
        import garden
        from assets.registry import get_or_create_item_id

        fertilizer_id = get_or_create_item_id("fertilizer")
        if not fertilizer_id or not morld.has_item(npc_id, fertilizer_id):
            return False

        current = morld.get_unit_prop(self.instance_id, garden.PROP_FERTILIZER)
        if current >= garden.MAX_FERTILIZER:
            return False

        morld.lost_item(npc_id, fertilizer_id, 1)
        new_val = min(garden.MAX_FERTILIZER, current + garden.FERTILIZER_AMOUNT)
        morld.set_unit_prop(self.instance_id, garden.PROP_FERTILIZER, new_val)
        return True

    def npc_remove_plant(self, npc_id, furrow_index=None):
        """NPC 식물 제거 (non-generator)

        Args:
            furrow_index: 제거할 이랑 인덱스 (None이면 첫 번째 식물)
        Returns:
            bool: 성공 여부
        """
        import garden

        furrow_count = morld.get_unit_prop(self.instance_id, garden.PROP_FURROW_COUNT) or 0

        if furrow_index is not None:
            if furrow_index < 0 or furrow_index >= furrow_count:
                return False
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{furrow_index}")
            if not seed_code:
                return False
            morld.set_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{furrow_index}", 0)
            morld.set_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{furrow_index}", 0)
            return True

        # 첫 번째 심어진 이랑 제거
        for i in range(furrow_count):
            seed_code = morld.get_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}")
            if seed_code:
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_SEED_PREFIX}:{i}", 0)
                morld.set_unit_prop(self.instance_id, f"{garden.PROP_GROWTH_PREFIX}:{i}", 0)
                return True
        return False
