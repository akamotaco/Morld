# think/movement_mixin.py - 이동 + 활동 디스패치 + Tier 5 Mixin
#
# 이동 job 삽입, 배회, 기본 활동 핸들러, Tier 5 스케줄 루틴

import random
import morld


class MovementMixin:
    """이동, 활동 디스패치, 배회, Tier 5 루틴"""

    # ========================================
    # 공용 헬퍼
    # ========================================

    def _is_at(self, target):
        """target의 region_id/location_id에 도착했는지"""
        loc = self.get_location()
        return (loc and loc[0] == target["region_id"]
                and loc[1] == target["location_id"])

    def on_leave(self, region_id, location_id):
        """location 떠날 때 호출 (C# OnLeave 이벤트 → events 핸들러 경유)"""
        pass

    def _turn_off_lights_here(self, region_id, location_id):
        """현재 위치의 모든 조명 끄기"""
        from assets.objects import get_location_objects, get_instance

        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("toggle_switch", 0) <= 0:
            return

        objects = get_location_objects(region_id, location_id)
        for obj_id in objects:
            if morld.get_unit_prop(obj_id, "light:on") == 1:
                obj = get_instance(obj_id)
                if obj and hasattr(obj, "npc_toggle_switch"):
                    obj.npc_toggle_switch(self.unit_id, target_state=0)

    def _transit_auto_eat(self):
        """Gate 이동 전 긴급 식사: HP < 50% 또는 배고픔 → 인벤토리 음식 소비"""
        import survival
        from think.activities.helpers import find_npc_food

        hp = survival.get_health(self.unit_id)
        max_hp = survival.get_max_health(self.unit_id)
        hungry = survival.is_npc_hungry(self.unit_id)

        if (max_hp > 0 and hp < max_hp * 0.5) or hungry:
            food = find_npc_food(self.unit_id)
            if food:
                if max_hp > 0 and hp < max_hp * 0.5:
                    hp_recover = max(5, food["satiety"] // 2)
                    survival.add_health(self.unit_id, hp_recover)
                survival.npc_eat(self.unit_id, food["satiety"])
                morld.remove_item(self.unit_id, food["item_id"], 1)

    def _move_to(self, target, name="이동"):
        """target으로 이동 job 삽입.

        Duration은 C#이 거리/속도 기반으로 동적 계산 (ACTION_DURATION 대상 아님).
        매 호출마다 새 move job을 삽입한다 (InsertJobWithClear가 기존 job 정리).
        이전 step에서 이동 미완료 시에도 새 job으로 갱신되어 정상 동작.

        Cross-location 이동(Gate 통과) 시:
        - FSM: GateTransitState push (think 차단 + prop + job + 행동 로그)
        - 이동 전 긴급 식사 (인벤토리)
        """
        loc = self.get_location()
        is_cross_location = (
            loc is not None and
            (loc[0] != target["region_id"] or loc[1] != target["location_id"])
        )

        if is_cross_location:
            self._transit_auto_eat()
            # FSM: GateTransitState push (enter에서 prop + job + action_log 처리)
            from think.fsm import GateTransitState
            self._fsm_push(GateTransitState(target, name))
            # _action_taken은 enter()에서 설정됨
        else:
            # 동일 location 이동: 기존 move job 있으면 보존 (매 step 리셋 방지)
            job = morld.get_current_job(self.unit_id)
            if job and job.get("action") == "move":
                self._action_taken = True
                return

            target_x = target.get("x", 0)
            length = int(target.get("length", 0))
            if length > 0 and target_x == 0:
                target_x = random.randint(0, length)
            morld.insert_job(self.unit_id, {
                "name": name,
                "action": "move",
                "region_id": target["region_id"],
                "location_id": target["location_id"],
                "target_x": target_x,
                "duration": 0,
            })
            self._action_taken = True

    # ========================================
    # think() 헬퍼 메서드
    # ========================================

    def _get_current_activity(self, schedule):
        """현재 시간에 해당하는 스케줄 entry 반환 (수면/목욕 제외)

        Args:
            schedule: 스케줄 리스트

        Returns:
            entry dict 또는 None
        """
        millis = self.get_time()
        for entry in schedule:
            activity = entry.get("activity", "")
            if activity in ("수면", "목욕"):
                continue
            start = entry["start"]
            end = entry["end"]
            if end < start:  # 자정 넘기기
                if millis >= start or millis < end:
                    return entry
            else:
                if start <= millis < end:
                    return entry
        return None

    def _resolve_target(self, entry):
        """장소 결정: 스케줄에 location 있으면 사용, 없으면 resolver

        Args:
            entry: 스케줄 entry dict

        Returns:
            {"region_id": int, "location_id": int, "x": int} 또는 None
        """
        if "location_id" in entry:
            # 고정 장소 모드
            result = {
                "region_id": entry.get("region_id", self._get_home_region()),
                "location_id": entry["location_id"],
                "x": entry.get("x", 0),
            }
            return result

        # 동적 탐색 (캐시)
        if self._activity_target is None:
            home = self._get_home_region()
            from think.activity_resolver import resolve_activity_location
            self._activity_target = resolve_activity_location(
                self.unit_id, entry.get("activity"), home
            )
        return self._activity_target

    def _execute_activity(self, activity, target):
        """activity별 행동 실행 (서브클래스에서 오버라이드 가능)"""
        if activity == "채집":
            self._do_gather(target)

    def _do_gather(self, target):
        """채집: ResourceObject에서 자원 수집"""
        from assets.objects import get_location_objects, get_instance

        objects = get_location_objects(target["region_id"], target["location_id"])
        for obj_id in objects:
            obj = get_instance(obj_id)
            if obj and hasattr(obj, "npc_take_resource"):
                taken = obj.npc_take_resource(self.unit_id, count=1)
                if taken > 0:
                    return

    def _get_display_name(self, entry):
        """스케줄 항목의 표시용 이름 (동적 활동 포함)"""
        name = entry.get("name", "대기")
        activity = entry.get("activity")
        if activity and name != activity:
            return f"{name}:{activity}"
        return name

    # ========================================
    # 기본 활동 핸들러
    # ========================================

    # 돌아다니기가 필요한 활동 (순찰/산책 = 한 곳에 머물지 않고 이동)
    _WANDER_ACTIVITIES = frozenset({"순찰", "산책"})

    def _handle_default_activity(self, entry):
        """기본 활동 핸들러 (대부분의 활동)

        resolve target → move → env check → execute → idle job.
        순찰/산책: 돌아다니기 (target 도착 후에도 지역 내 이동 반복).
        기타 활동 + target=None: 제자리 대기.
        """
        activity = entry.get("activity", "대기")
        is_wander = activity in self._WANDER_ACTIVITIES

        # 1. 장소 결정
        target = self._resolve_target(entry)

        if target is None:
            if is_wander:
                # 순찰/산책: 목표 없이도 돌아다니기
                self._do_wander(entry)
            else:
                # 기타 활동: 목표 없으면 제자리 대기
                remaining = self._remaining_millis_in_entry(entry)
                self._insert_idle_job(self._get_display_name(entry), max(remaining, 1))
                self._action_taken = True
            return

        # 2. 도착 여부
        if not self._is_at(target):
            # 미도착 → 이동
            self._move_to(target, self._get_display_name(entry))
            self._arrived = False
        else:
            # 도착 → 환경 체크
            if not self._arrived:
                self._arrived = True
                self._check_environment(target["region_id"], target["location_id"])

            if is_wander:
                # 순찰/산책: 도착 후 지역 내 돌아다니기
                self._do_wander(entry)
            else:
                # 기타 활동: 실행 후 스케줄 끝까지 대기
                self._execute_activity(activity, target)
                remaining = self._remaining_millis_in_entry(entry)
                self._insert_idle_job(self._get_display_name(entry), max(remaining, 1))
                self._action_taken = True

    def _do_wander(self, entry=None):
        """돌아다니기: 랜덤 location 이동 → 10~30분 체류 → 반복

        순찰/산책 공용. home_region 내 랜덤 location을 순회한다.
        남은 시간 5분 미만이면 제자리 대기로 전환.
        entry=None이면 24시간 순찰 합성 엔트리 사용.
        """
        if entry is None:
            entry = {"name": "배회", "start": 0, "end": 86_400_000, "activity": "순찰"}
        remaining = self._remaining_millis_in_entry(entry)
        display = self._get_display_name(entry)

        # 남은 시간 5분 미만 → 제자리 대기
        if remaining < 5 * 60_000:
            self._insert_idle_job(display, max(remaining, 1))
            self._action_taken = True
            return

        wander_target = self._activity_state.get("wander_target")
        if wander_target is not None:
            if self._is_at(wander_target):
                # 도착 → 10~30분 체류 후 다음 이동
                self._activity_state.pop("wander_target", None)
                rest = min(random.randint(10, 30) * 60_000, remaining)
                self._insert_idle_job(display, max(rest, 1))
                self._action_taken = True
            else:
                self._move_to(wander_target, display)
        else:
            # 새 목적지 선택
            wander_loc = self._pick_wander_location()
            if wander_loc:
                self._activity_state["wander_target"] = wander_loc
                self._move_to(wander_loc, display)
            else:
                self._insert_idle_job(display, max(remaining, 1))
                self._action_taken = True

    def _pick_wander_location(self):
        """home_region 내 랜덤 location 선택 (산책용)"""
        home_region = self._get_home_region()
        cur_loc = self.get_location()
        if not cur_loc:
            return None

        region_info = morld.get_region_info(home_region)
        if not region_info or "locations" not in region_info:
            return None

        candidates = []
        for loc_info in region_info["locations"]:
            lid = loc_info["id"]
            if cur_loc[0] == home_region and cur_loc[1] == lid:
                continue  # 현재 위치 제외
            candidates.append(lid)

        if not candidates:
            return None

        target_lid = random.choice(candidates)
        return {"region_id": home_region, "location_id": target_lid}

    # ========================================
    # Tier 5: 일상 (스케줄 기반 활동)
    # ========================================

    def _check_tier5_routine(self):
        """Tier 5: 일상 (스케줄 기반 활동 디스패치)

        activity 조회 → 변경 감지 → 동적 entry 해석 → 핸들러 디스패치.

        Returns:
            True if action was taken.
        """
        from think.activities import ACTIVITY_HANDLERS as _ACTIVITY_HANDLERS

        schedule = self.get_current_schedule()
        if not schedule:
            return False

        entry = self._get_current_activity(schedule)
        if entry is None:
            return False

        # activity 변경 감지 → 상태 리셋
        if self._current_activity is not entry:
            self._current_activity = entry
            self._activity_target = None
            self._arrived = False
            self._activity_phase = "idle"
            self._activity_state = {}

        # 동적 entry 해석 + 디스패치 루프
        original_entry = entry
        while True:
            if original_entry.get("dynamic"):
                entry = self._resolve_dynamic_entry(original_entry)

            activity = entry.get("activity", "대기")
            handler = _ACTIVITY_HANDLERS.get(activity)
            if handler:
                handler(self, entry)
            else:
                self._handle_default_activity(entry)

            if self._action_taken:
                break

            if not original_entry.get("dynamic"):
                break

            # 동적 entry 핸들러가 action 없이 return → 자동 스킵
            resolved = self._activity_state.get("resolved_entry")
            if not resolved:
                break  # candidate 소진 → "할 일 없음" 폴백
            self._skip_dynamic_activity(original_entry)

        # 핸들러가 action을 생성하지 못한 경우 → "할 일 없음" 대기
        if not self._action_taken:
            remaining = self._remaining_millis_in_entry(entry)
            self._insert_idle_job("할 일 없음", max(remaining, 1))
            self._action_taken = True

        return self._action_taken
