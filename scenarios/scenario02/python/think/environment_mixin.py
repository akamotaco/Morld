# think/environment_mixin.py - 환경/조명/도구 관리 Mixin
#
# 홈 리전 탐색, 조명 자동 관리, 도구 탐색/장비 관리

import morld


class EnvironmentMixin:
    """NPC 홈 리전, 조명, 도구 관리"""

    _home_region_id = None  # lazy cache (bed_owner prop 기반)

    def _get_home_region(self):
        """NPC의 홈 region — 캐릭터/크리처 분기 (morld API UnitType 기반)

        캐릭터 (is_creature=False):
            bed_owner:{owner} prop → 침대의 region_id
            침대 없으면 RuntimeError (설정 버그)

        크리처 (is_creature=True):
            전투:홈리전 prop → 해당 region_id
            NOTE: get_unit_prop()은 prop 미존재 시 0 반환 (None 아님).
                  전투:홈리전=0은 R0 소속으로 유효.
            fallback: 현재 위치의 region_id
        """
        if self._home_region_id is not None:
            return self._home_region_id
        npc_name = self.get_info().get("name", self.unit_id)

        if self._is_creature:
            # 크리처: 전투:홈리전 prop (spawner가 설정)
            # get_unit_prop()은 prop 없으면 0 반환 → R0 소속으로 유효
            combat_home = morld.get_unit_prop(self.unit_id, "전투:홈리전")
            if combat_home is not None:
                self._home_region_id = int(combat_home)
                return self._home_region_id
            # fallback: 현재 위치
            loc = self.get_location()
            self._home_region_id = loc[0] if loc else 0
            return self._home_region_id
        else:
            # 캐릭터: bed_owner prop 기반
            owner = getattr(self, 'owner_unique_id', None)
            if not owner:
                raise RuntimeError(
                    f"[_get_home_region] {npc_name}: "
                    f"캐릭터인데 owner_unique_id가 없음")
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
            if beds:
                self._home_region_id = beds[0]["region_id"]
                return self._home_region_id
            raise RuntimeError(
                f"[_get_home_region] {npc_name}: "
                f"owner_unique_id='{owner}' 이지만 "
                f"bed_owner:{owner} prop을 가진 침대가 없음")

    # 조명 3-phase 시간 경계 (밀리초)
    _EVENING_START = 1080 * 60_000   # 18:00 — 점등 시작
    _NIGHT_START   = 1260 * 60_000   # 21:00 — 소등 시작
    _MORNING_START = 360 * 60_000    # 06:00 — 소등 시작

    def _should_lights_on(self):
        """현재 시간이 점등 시간대(18:00~21:00)인지 판정"""
        millis = self.get_time()
        return self._EVENING_START <= millis < self._NIGHT_START

    def _check_environment(self, region_id, location_id):
        """환경 인식: 3-phase 시간대에 따라 조명 켜기/끄기 (도착 시 1회 호출)

        소극적 조명 관리:
        - 06:00~18:00 (주간): 켜진 조명 끄기
        - 18:00~21:00 (저녁): 꺼진 조명 켜기
        - 21:00~06:00 (야간): 켜진 조명 끄기
        열원(heat:output)은 토글 대상에서 제외.
        """
        from assets.objects import get_location_objects, get_instance

        objects = get_location_objects(region_id, location_id)

        # 조명 오브젝트 찾기 (열원 제외)
        light_objects = []
        any_light_on = False
        for obj_id in objects:
            light_on = morld.get_unit_prop(obj_id, "light:on")
            if light_on is not None:
                if morld.get_unit_prop(obj_id, "heat:output"):
                    continue  # 열원은 조명 토글 대상 아님
                light_objects.append(obj_id)
                if light_on == 1:
                    any_light_on = True

        if not light_objects:
            return

        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("toggle_switch", 0) <= 0:
            return

        should_on = self._should_lights_on()

        if should_on and not any_light_on:
            # 점등 시간인데 조명 꺼져있으면 → 켜기
            obj = get_instance(light_objects[0])
            if obj and hasattr(obj, "npc_toggle_switch"):
                obj.npc_toggle_switch(self.unit_id, target_state=1)
        elif not should_on and any_light_on:
            # 소등 시간인데 조명 켜져있으면 → 끄기
            for obj_id in light_objects:
                if morld.get_unit_prop(obj_id, "light:on") == 1:
                    obj = get_instance(obj_id)
                    if obj and hasattr(obj, "npc_toggle_switch"):
                        obj.npc_toggle_switch(self.unit_id, target_state=0)

    def _get_home_building_info(self, region_id):
        """소유 침대 위치 기반 건물 정보 조회 (조명 탐색 공용)"""
        sleep_r = region_id
        sleep_l = None
        owner = getattr(self, 'owner_unique_id', None)
        if owner:
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
            if beds:
                sleep_r = beds[0]["region_id"]
                sleep_l = beds[0]["location_id"]
        return sleep_r, sleep_l

    def _find_lit_indoor_room(self, region_id):
        """조명이 켜진 거처 실내 방 찾기 (소등용)

        거처 = 소유 침대와 같은 건물(실내 연결) 내의 방.
        열원(heat:output)은 소등 대상에서 제외.
        다른 유닛이 있는 방은 소등 대상 제외.
        """
        from assets.objects import _location_objects

        sleep_r, sleep_l = self._get_home_building_info(region_id)

        for (r, l), obj_ids in _location_objects.items():
            if r != region_id:
                continue
            if sleep_l is not None and not morld.is_same_building(r, l, sleep_r, sleep_l):
                continue
            loc_info = morld.get_location_info(r, l)
            if not loc_info or not loc_info.get("is_indoor", False):
                continue
            # 점유 체크: 다른 유닛이 있으면 소등 대상 제외
            units_here = morld.get_characters_at_location(r, l)
            if units_here and any(u != self.unit_id for u in units_here):
                continue
            light_ids = []
            for obj_id in obj_ids:
                if morld.get_unit_prop(obj_id, "light:on") == 1:
                    if morld.get_unit_prop(obj_id, "heat:output"):
                        continue  # 열원은 소등 대상 아님
                    light_ids.append(obj_id)
            if light_ids:
                return {"region_id": r, "location_id": l, "x": 0, "light_ids": light_ids}
        return None

    def _find_unlit_indoor_room(self, region_id):
        """조명이 꺼진 거처 실내 방 찾기 (점등용)

        거처 = 소유 침대와 같은 건물(실내 연결) 내의 방.
        열원(heat:output)은 점등 대상에서 제외.
        다른 유닛이 있는 방도 점등 대상에 포함 (점등은 사람 있어도 해야 함).
        """
        from assets.objects import _location_objects

        sleep_r, sleep_l = self._get_home_building_info(region_id)

        for (r, l), obj_ids in _location_objects.items():
            if r != region_id:
                continue
            if sleep_l is not None and not morld.is_same_building(r, l, sleep_r, sleep_l):
                continue
            loc_info = morld.get_location_info(r, l)
            if not loc_info or not loc_info.get("is_indoor", False):
                continue
            # 점등은 점유 체크 안 함 (사람 있는 방도 켜야 함)
            light_ids = []
            for obj_id in obj_ids:
                if morld.get_unit_prop(obj_id, "heat:output"):
                    continue  # 열원은 점등 대상 아님
                light_on = morld.get_unit_prop(obj_id, "light:on")
                if light_on is not None and light_on != 1:
                    light_ids.append(obj_id)
            if light_ids:
                return {"region_id": r, "location_id": l, "x": 0, "light_ids": light_ids}
        return None

    # ========================================
    # 도구 관리 헬퍼
    # ========================================

    def _get_toolbox_id(self):
        """도구함 unit_id 조회"""
        from assets.registry import get_instance_id
        return get_instance_id("toolbox")

    def _has_tool(self, tool_unique_id):
        """도구 소지 확인"""
        from assets.registry import get_or_create_item_id
        item_id = get_or_create_item_id(tool_unique_id)
        if item_id is None:
            return False
        return morld.has_item(self.unit_id, item_id)

    def _pickup_tool(self, tool_unique_id):
        """도구함에서 도구 가져오기"""
        from assets.registry import get_or_create_item_id
        toolbox_id = self._get_toolbox_id()
        item_id = get_or_create_item_id(tool_unique_id)
        if toolbox_id and item_id and morld.has_item(toolbox_id, item_id):
            morld.remove_item(toolbox_id, item_id, 1)
            import inventory as inv_module
            inv_module.safe_give_item(self.unit_id, item_id, 1)
            return True
        return False

    def _return_tool(self, tool_unique_id):
        """도구를 도구함에 반납"""
        from assets.registry import get_or_create_item_id
        toolbox_id = self._get_toolbox_id()
        item_id = get_or_create_item_id(tool_unique_id)
        if toolbox_id and item_id:
            morld.remove_item(self.unit_id, item_id, 1)
            morld.give_item(toolbox_id, item_id, 1)
            return True
        return False

    def _is_tool_available(self, tool_unique_id):
        """도구 사용 가능 여부 (소지 또는 도구함)"""
        if self._has_tool(tool_unique_id):
            return True
        from assets.registry import get_or_create_item_id
        toolbox_id = self._get_toolbox_id()
        item_id = get_or_create_item_id(tool_unique_id)
        if toolbox_id and item_id:
            return morld.has_item(toolbox_id, item_id)
        return False

    def _skip_dynamic_activity(self, entry):
        """동적 활동 건너뛰기 → 다음 candidate로 전환 준비.

        디스패치 루프에서 action_taken 미설정 + return하면
        루프가 즉시 다음 candidate를 re-resolve하여 재디스패치.

        Returns: True(dynamic 성공), False(고정 스케줄)
        """
        if not entry.get("dynamic"):
            return False
        skipped = self._activity_state.get("skipped_activities", set())
        resolved = self._activity_state.get("resolved_entry")
        if resolved:
            skipped.add(resolved.get("activity"))
        self._activity_state.pop("resolved_entry", None)
        self._activity_state["skipped_activities"] = skipped
        self._activity_phase = "idle"
        return True

    # ========================================
    # capability 기반 도구 탐색 (Phase 2)
    # ========================================

    def _find_tool_by_capability(self, capability):
        """capability 기반 도구 탐색 (소유권 우선순위 적용)

        탐색 순서:
        1. NPC 인벤토리 (이미 소지)
        2. 리전 내 컨테이너: 본인 소유 아이템
        3. 리전 내 컨테이너: 무소유 아이템
        타인 소유 아이템은 무시.

        Returns:
            {"item_id", "item_unique_id", "is_own", "source",
             "container_id", "location"} or None
        """
        from assets.registry import get_unique_id, get_item_class

        my_uid = self.owner_unique_id  # NPC unique_id (e.g. "sera")

        # 1. NPC 인벤토리
        inv = morld.get_unit_inventory(self.unit_id)
        if inv:
            for item_id, count in inv.items():
                if count <= 0:
                    continue
                uid = get_unique_id(item_id)
                cls = get_item_class(uid) if uid else None
                if cls and self._item_has_capability(cls, capability):
                    return {"item_id": item_id, "item_unique_id": uid,
                            "is_own": getattr(cls, 'owner', None) == my_uid,
                            "source": "inventory"}

        # 2~3. 리전 내 컨테이너: 본인 소유 먼저, 그 다음 무소유
        home_region = self._get_home_region()
        for owner_filter in (my_uid, None):
            result = self._search_containers_for_tool(
                capability, home_region, owner_filter)
            if result:
                return result

        return None

    def _item_has_capability(self, item_cls, capability):
        """passive_props 또는 equip_props에 capability가 있는지"""
        return ((item_cls.passive_props or {}).get(capability, 0) > 0 or
                (item_cls.equip_props or {}).get(capability, 0) > 0)

    def _search_containers_for_tool(self, capability, region_id, owner_filter):
        """리전 내 컨테이너에서 도구 탐색

        Args:
            capability: 필요 능력 (예: "can:chop")
            region_id: 탐색할 리전
            owner_filter: str=해당 소유자, None=무소유 아이템만
        """
        from assets.registry import get_unique_id, get_item_class
        from assets.objects import _location_objects

        for (r, l), obj_ids in _location_objects.items():
            if r != region_id:
                continue
            for obj_id in obj_ids:
                inv = morld.get_unit_inventory(obj_id)
                if not inv:
                    continue
                for item_id, count in inv.items():
                    if count <= 0:
                        continue
                    uid = get_unique_id(item_id)
                    cls = get_item_class(uid) if uid else None
                    if not cls:
                        continue
                    if getattr(cls, 'owner', None) != owner_filter:
                        continue
                    if self._item_has_capability(cls, capability):
                        info = morld.get_unit_info(obj_id)
                        return {
                            "item_id": item_id, "item_unique_id": uid,
                            "is_own": owner_filter == self.owner_unique_id,
                            "source": "container",
                            "container_id": obj_id,
                            "location": {"region_id": r, "location_id": l,
                                         "x": info.get("x", 0) if info else 0},
                        }
        return None

    def _set_tool_missing_flag(self, capability):
        """도구 분실 플래그 설정 (예: "도구분실:can:chop")"""
        morld.set_unit_prop(self.unit_id, f"도구분실:{capability}", 1)

    def _clear_tool_missing_flag(self, capability):
        """도구 분실 플래그 해제"""
        morld.clear_prop(self.unit_id, f"도구분실:{capability}")
