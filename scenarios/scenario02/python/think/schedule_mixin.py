# think/schedule_mixin.py - 동적 스케줄 해석 Mixin
#
# 동적 스케줄 조건 평가 + 저장소 기반 필요 판정

import morld


class ScheduleResolverMixin:
    """동적 스케줄 조건 평가 및 해석"""

    def _resolve_dynamic_entry(self, entry):
        """동적 스케줄 entry를 조건 평가 후 확정된 entry로 변환"""
        # 이미 해석된 결과가 있으면 반환
        cached = self._activity_state.get("resolved_entry")
        if cached:
            return cached

        skipped = self._activity_state.get("skipped_activities", set())

        for candidate in entry.get("candidates", []):
            activity = candidate["activity"]
            if activity in skipped:
                continue
            condition = candidate.get("condition")
            if condition is None or self._evaluate_condition(condition):
                resolved = dict(entry)
                resolved["activity"] = activity
                # candidate에 장소 정보가 있으면 오버라이드
                for key in ("location_id", "region_id", "x"):
                    if key in candidate:
                        resolved[key] = candidate[key]
                self._activity_state["resolved_entry"] = resolved
                return resolved

        # 모든 조건 불충족 or 전부 skipped → entry 그대로
        return entry

    def _evaluate_condition(self, condition):
        """동적 스케줄 조건 평가 (True=활동 필요)"""
        if condition == "can_cook":
            # 보관소에 재료 2개 이상이면 요리 가능
            return not self._check_storage_need("food_ingredient", None, 2)
        elif condition == "should_clean":
            return self._check_has_pollution()
        elif condition == "need_social":
            try:
                import needs
                return needs.get_max_longing(self.unit_id) >= 50
            except ImportError:
                return False
        elif condition == "need_fuel":
            return self._check_heat_source_needs_fuel()
        return False

    def _check_has_pollution(self):
        """거처 내 오염된 방이 있는지 확인 (True=청소 필요)"""
        try:
            import pollution
        except ImportError:
            return False
        home_region = self._get_home_region()
        # 소유 침대 위치로 건물 판정
        sleep_l = None
        owner = getattr(self, 'owner_unique_id', None)
        if owner:
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
            if beds:
                sleep_l = beds[0]["location_id"]
        for key, data in pollution._location_pollution.items():
            r, l = key
            if r != home_region:
                continue
            if data["current"] <= 0:
                continue
            if sleep_l is not None and not morld.is_same_building(r, l, home_region, sleep_l):
                continue
            return True
        return False

    def _check_heat_source_needs_fuel(self):
        """거처 내 연료 부족 열원 확인"""
        try:
            import fuel
        except ImportError:
            return False
        for uid in fuel.get_sources_in_region(self._get_home_region()):
            if fuel.needs_fuel(uid):
                return True
        return False

    def _check_storage_need(self, category, item_uid, threshold):
        """카테고리 기반 저장소 아이템 부족 여부 (True=부족)

        컨테이너에 need:{item_uid} prop이 있으면 그 값을 기준치로 사용,
        없으면 파라미터 threshold를 fallback으로 사용.
        """
        from think.activities.helpers import resolve_storage_container
        target = resolve_storage_container(self, category)
        if not target:
            return False  # 저장소 없으면 필요 없음
        from assets.objects import get_instance
        obj = get_instance(target["object_id"])
        if not obj:
            return False
        if item_uid:
            # prop 기반 기준치 (우선) → 파라미터 fallback
            prop_threshold = morld.get_unit_prop(target["object_id"], f"need:{item_uid}")
            # 실 API 계약: 부재 시 0 — 0이면 파라미터 threshold로 fallback
            actual_threshold = prop_threshold if prop_threshold else threshold
            return obj.get_item_count(item_uid) < actual_threshold
        else:
            return obj.get_category_item_count(category) < threshold
