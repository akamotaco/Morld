# think/__init__.py - NPC AI 시스템
#
# 각 NPC의 think() 메서드를 호출하여 경로를 계획합니다.
# MovementSystem은 계획된 경로(PlannedRoute)만 실행합니다.
#
# 사용법:
#   @register_agent_class("lina")
#   class LinaAgent(BaseAgent):
#       def think(self):
#           ...
#
# === DES (Discrete Event Simulation) 호환 규칙 (v0.2.2) ===
#
# think()는 반드시 duration > 0인 job을 삽입해야 함.
# 빈 job list는 DES 루프에서 무한루프를 유발하므로 에러로 간주.
#
# Job action 종류:
#   "stay"  — 현재 위치 대기 (idle, sleep, faint 등 모든 비이동 상태)
#   "move"  — 목표 location으로 이동
#             duration=0으로 삽입 → C#이 이동 시간을 계산하여 자동 설정
#             DES에서 duration 만료 시 NPC를 목표 location에 텔레포트
#             도착 후 think() 재호출 → 미세 위치 조정 가능
#
# 참고: "idle"은 C# MetaAction (플레이어 전용). NPC job에는 "stay" 사용.

import random
import morld

MILLIS_PER_DAY = 86_400_000

# Agent 레지스트리: unit_id -> Agent 인스턴스
_agents = {}

# Agent 팩토리 레지스트리: unique_id -> Agent 클래스
_agent_classes = {}


class BaseAgent:
    """
    NPC AI 기본 클래스

    각 캐릭터는 이 클래스를 상속받아 think() 메서드를 구현합니다.

    스케줄 스택 구조:
        schedule_stack[0] = 기본 스케줄 (서브클래스에서 set_base_schedule()로 설정)
        schedule_stack[1+] = 임시 스케줄 (push_schedule/pop_schedule로 관리)

        get_current_schedule()은 항상 스택 최상단을 반환합니다.
        pop_schedule()은 [0]을 보호하여 기본 스케줄이 삭제되지 않습니다.

    공용 스케줄:
        STAY_SCHEDULE - 현재 위치에서 대기 (모든 NPC 공통)
    """

    # 공용 스케줄: 현재 위치에서 대기 (24시간, location_id 없음 = 이동 없이 대기)
    STAY_SCHEDULE = [
        {"name": "대기", "start": 0, "end": 86_400_000, "activity": "대기"}
    ]

    # 도구함 정보 (저택 공용)
    TOOL_STORAGE = {"region_id": 0, "location_id": 5, "x": 20}  # 창고 도구함 위치

    # 식량 보관 위치 (서브클래스에서 오버라이드)
    food_storage_location = {"region_id": 0, "location_id": 2, "x": 35}  # 주방 냉장고
    food_storage_unique_id = "kitchen_fridge"

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self.schedule_stack = [None]  # [0]은 기본 스케줄 자리 (서브클래스에서 설정)
        # Activity 상태 (think에서 단일 행동 계획용)
        self._current_activity = None   # 현재 수행 중인 activity entry
        self._activity_target = None    # resolve된 장소 정보
        self._arrived = False           # 목표 장소 도착 여부
        self._activity_phase = "idle"   # 활동 내 단계
        self._activity_state = {}       # 활동별 임시 데이터
        self._action_taken = False      # think() 내 행동 결정 여부 (경고용)
        self._hunger_phase = None       # 식사 단계 (None=배고프지 않음)
        self._tool_memory = {}          # 도구 원래 위치 기억 {item_id: {"container_id", "location"}}

    def set_base_schedule(self, schedule):
        """
        기본 스케줄 설정 (스택[0]에 저장)

        서브클래스의 __init__에서 호출하여 초기 스케줄을 설정합니다.
        날짜별 스케줄 전환 시에도 이 메서드를 사용합니다.

        Args:
            schedule: 스케줄 리스트
        """
        self.schedule_stack[0] = schedule
        morld.clear_jobs(self.unit_id)
        print(f"[think] set_base_schedule unit={self.unit_id}")

    def get_info(self):
        """현재 유닛 정보 조회"""
        return morld.get_unit_info(self.unit_id)

    def get_location(self):
        """현재 위치 (region_id, location_id) 튜플"""
        return morld.get_unit_location(self.unit_id)

    def get_time(self):
        """현재 게임 시간"""
        return morld.get_game_time()

    def find_path(self, to_region, to_location):
        """경로 탐색"""
        loc = self.get_location()
        if loc is None:
            return None
        return morld.find_path(loc[0], loc[1], to_region, to_location, self.unit_id)

    def fill_schedule_jobs_from(self, schedule):
        """
        Python에서 전달한 스케줄로 JobList 채우기

        Args:
            schedule: 스케줄 리스트
                [{"name": str, "region_id": int, "location_id": int,
                  "start": int, "end": int, "activity": str}, ...]

        Returns:
            True 성공, False 실패
        """
        result = morld.fill_schedule_jobs_from(self.unit_id, schedule)
        print(f"[think] fill_schedule unit={self.unit_id}, entries={len(schedule)}, result={result}")
        return result

    def push_schedule(self, schedule):
        """
        스케줄 스택에 push (임시 스케줄로 전환)

        Args:
            schedule: 사용할 스케줄 (예: BaseAgent.STAY_SCHEDULE)

        사용 예:
            agent.push_schedule(BaseAgent.STAY_SCHEDULE)
        """
        self.schedule_stack.append(schedule)
        morld.clear_jobs(self.unit_id)
        print(f"[think] push_schedule unit={self.unit_id}, stack_depth={len(self.schedule_stack)}")

    def pop_schedule(self):
        """
        스케줄 스택에서 pop (이전 스케줄로 복원)

        [0]의 기본 스케줄은 보호되어 삭제되지 않습니다.

        Returns:
            pop된 스케줄 또는 None (기본 스케줄만 남은 경우)
        """
        if len(self.schedule_stack) > 1:
            popped = self.schedule_stack.pop()
            morld.clear_jobs(self.unit_id)
            print(f"[think] pop_schedule unit={self.unit_id}, stack_depth={len(self.schedule_stack)}")
            return popped
        print(f"[think] pop_schedule unit={self.unit_id}, only base schedule remains")
        return None

    def get_current_schedule(self):
        """
        현재 사용해야 할 스케줄 반환 (스택 최상단)

        Returns:
            스케줄 리스트 또는 None
        """
        return self.schedule_stack[-1]

    # ========================================
    # 수면 시스템
    # ========================================

    # 서브클래스에서 오버라이드: 자기 침대 위치
    # 예: {"region_id": 0, "location_id": 8, "x": 120}
    sleep_location = None

    # 서브클래스에서 오버라이드: 목욕 장소
    # 예: {"region_id": 0, "location_id": 4, "x": 15}
    bath_location = None

    def _is_sleep_time(self):
        """현재 시간이 수면 시간대인지 확인

        Returns:
            (bool, entry or None)
        """
        schedule = self.get_current_schedule()
        if not schedule:
            return False, None
        millis = self.get_time()  # int: millis_of_day
        for entry in schedule:
            if entry.get("activity") != "수면":
                continue
            start = entry["start"]
            end = entry["end"]
            if end < start:  # 자정 넘기기
                if millis >= start or millis < end:
                    return True, entry
            else:
                if start <= millis < end:
                    return True, entry
        return False, None

    # 서브클래스에서 오버라이드: NPC의 unique_id (침대 소유자 매칭용)
    owner_unique_id = None

    def _resolve_sleep_location(self):
        """수면 장소를 C# API로 결정

        C# resolve_sleep_target() 우선순위:
            1. pref_location에서 bed_owner가 일치하는 침대 + 빈 슬롯
            2. pref_location에서 아무 빈 침대
            3. pref_location이 실내면 노숙
            4. 현재 위치에서 노숙

        Returns:
            dict: {"region_id", "location_id", "x", "bed_object_id", "rough"} or None
        """
        if not self.sleep_location:
            loc = self.get_location()
            if loc:
                return {"region_id": loc[0], "location_id": loc[1],
                        "x": None, "bed_object_id": None, "rough": True}
            return None

        # can:sleep 체크 - 없으면 에러 (개발 시 누락 방지)
        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("sleep", 0) <= 0:
            info = morld.get_unit_info(self.unit_id)
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            raise RuntimeError(
                f"[think] {name}에게 'can:sleep' prop이 없습니다. "
                f"수면 활동을 하려면 캐릭터에 'can:sleep': 1을 추가하세요."
            )

        owner_unique = self.owner_unique_id or ""
        result = morld.resolve_sleep_target(
            self.unit_id,
            self.sleep_location["region_id"],
            self.sleep_location["location_id"],
            owner_unique
        )
        return result

    def _try_sleep_on_bed(self, bed_object_id):
        """침대에 눕기 시도

        Returns:
            True 성공, False 실패
        """
        # 이미 누워있는지 확인
        seated_on = morld.get_unit_props_by_type(self.unit_id, "seated_on")
        if seated_on:
            return True  # 이미 어딘가에 앉거나 누워있음

        # 빈 슬롯 찾아서 눕기
        seated_by = morld.get_unit_props_by_type(bed_object_id, "seated_by")
        for slot, occupant in seated_by.items():
            if occupant == -1:
                return morld.sit_on(self.unit_id, bed_object_id, slot)
        return False

    def _handle_sleep(self):
        """수면 행동 처리 (think()에서 수면 시간대에 호출)"""
        sleep_info = self._resolve_sleep_location()
        if not sleep_info:
            return

        loc = self.get_location()
        target_region = sleep_info["region_id"]
        target_location = sleep_info["location_id"]

        # 목표 위치에 도착했는지
        if loc and loc[0] == target_region and loc[1] == target_location:
            # 도착 → 침대에 눕기 시도
            bed_id = sleep_info.get("bed_object_id")
            if bed_id:
                self._try_sleep_on_bed(bed_id)
            # sleep job 삽입 (침대든 노숙이든)
            _, sleep_entry = self._is_sleep_time()
            if sleep_entry:
                remaining = self._remaining_millis_in_entry(sleep_entry)
                self._insert_idle_job("sleep", max(remaining, 1))
        else:
            # 이동 필요 → move job 설정
            info = self.get_info()
            if not info.get("is_moving"):
                target_x = sleep_info.get("x", 0)
                morld.insert_job(self.unit_id, {
                    "name": "수면",
                    "action": "move",
                    "region_id": target_region,
                    "location_id": target_location,
                    "target_x": target_x if target_x else 0,
                    "duration": 0,
                })

    def _ensure_standing(self):
        """앉거나 누워있으면 일어나기 (활동 전 상태 정리)

        수면 전용이 아님. 현재 seated 상태인데 seated여야 할 이유가
        없는 상황(예: 수면 시간이 아닌데 누워있음)에서 호출.
        """
        seated_on = morld.get_unit_props_by_type(self.unit_id, "seated_on")
        if seated_on:
            morld.stand_up(self.unit_id)

    # ========================================
    # Job 삽입 헬퍼
    # ========================================

    def _remaining_millis_in_entry(self, entry):
        """스케줄 entry 종료까지 남은 밀리초"""
        millis = self.get_time()
        end = entry["end"]
        start = entry["start"]
        if end < start:  # 자정 넘기기
            if millis >= start:
                return (MILLIS_PER_DAY - millis) + end
            else:
                return end - millis
        else:
            return max(0, end - millis)

    def _insert_idle_job(self, name, duration_millis):
        """stay job 삽입 (NPC가 현재 위치에서 대기)

        duration_millis <= 0이면 삽입하지 않음.
        DES 시뮬레이션에서 빈 job 방지용.
        """
        if duration_millis > 0:
            morld.insert_job(self.unit_id, {
                "name": name,
                "action": "stay",
                "duration": duration_millis,
            })

    # ========================================
    # 목욕 시스템
    # ========================================

    def _is_bath_time(self):
        """현재 시간이 목욕 시간대인지 확인

        Returns:
            (bool, entry or None)
        """
        schedule = self.get_current_schedule()
        if not schedule:
            return False, None
        millis = self.get_time()
        for entry in schedule:
            if entry.get("activity") != "목욕":
                continue
            start = entry["start"]
            end = entry["end"]
            if end < start:  # 자정 넘기기
                if millis >= start or millis < end:
                    return True, entry
            else:
                if start <= millis < end:
                    return True, entry
        return False, None

    def _handle_bath(self):
        """목욕 행동 처리 (think()에서 목욕 시간대에 호출)

        침대와 달리 오브젝트 조작 없음. location 도착만 확인.
        """
        if not self.bath_location:
            return

        # can:bath 체크 - 없으면 에러 (개발 시 누락 방지)
        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("bath", 0) <= 0:
            info = morld.get_unit_info(self.unit_id)
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            raise RuntimeError(
                f"[think] {name}에게 'can:bath' prop이 없습니다. "
                f"목욕 활동을 하려면 캐릭터에 'can:bath': 1을 추가하세요."
            )

        loc = self.get_location()
        target_region = self.bath_location["region_id"]
        target_location = self.bath_location["location_id"]

        if loc and loc[0] == target_region and loc[1] == target_location:
            # 도착 — 목욕 job 삽입
            _, bath_entry = self._is_bath_time()
            if bath_entry:
                remaining = self._remaining_millis_in_entry(bath_entry)
                self._insert_idle_job("목욕", max(remaining, 1))
        else:
            # 이동
            target_x = self.bath_location.get("x", 0)
            morld.insert_job(self.unit_id, {
                "name": "목욕",
                "action": "move",
                "region_id": target_region,
                "location_id": target_location,
                "target_x": target_x,
                "duration": 0,
            })

    # ========================================
    # think() — 모든 행동 결정을 여기서 처리
    # ========================================

    def think(self):
        """
        AI 로직 실행 — 매 step마다 호출 (DES에서는 job 만료 시)

        모든 행동 결정이 여기서 처리됨:
        1. 목욕/수면 시간대 → 기존 핸들러
        2. 현재 시간대 activity 확인
        3. activity 변경 감지 → 상태 리셋
        4. 활동 핸들러 디스패치 (phase-based)

        [DES 규칙] 이 메서드는 반드시 duration > 0인 job을 삽입해야 함.
        stay job: _insert_idle_job() 사용, move job: duration=0 (C#이 자동 계산)
        """
        self._action_taken = False

        # 0. 기절 체크 (최우선 — 아무것도 못함)
        import survival
        if survival.is_npc_fainted(self.unit_id):
            remaining = survival.get_faint_remaining_millis(self.unit_id)
            self._insert_idle_job("fainting", max(remaining, 1))
            self._action_taken = True
            return None

        schedule = self.get_current_schedule()
        if not schedule:
            return None

        # 1. 목욕/수면 (기존 유지)
        is_bath, _ = self._is_bath_time()
        if is_bath:
            self._handle_bath()
            return None
        is_sleep, _ = self._is_sleep_time()
        if is_sleep:
            self._handle_sleep()
            return None
        self._ensure_standing()

        # 1.5. 배고픔 체크 (활동보다 우선)
        if self._check_hunger():
            return None

        # 2. 현재 activity 확인
        entry = self._get_current_activity(schedule)
        if entry is None:
            return None

        # 3. activity 변경 감지 → 상태 리셋
        if self._current_activity is not entry:
            self._current_activity = entry
            self._activity_target = None
            self._arrived = False
            self._activity_phase = "idle"
            self._activity_state = {}

        # 3.5 + 4. 동적 entry 해석 + 디스패치 루프
        # skip 시 idle job 없이 즉시 다음 candidate로 재디스패치
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

        # 경고: 행동 미결정
        if not self._action_taken:
            info = self.get_info()
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            print(f"[think] WARNING: {name} - 행동 미결정 (activity={activity}, phase={self._activity_phase})")

        return None

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
            return {
                "region_id": entry.get("region_id", self._get_home_region()),
                "location_id": entry["location_id"],
                "x": entry.get("x", 0),
            }

        # 동적 탐색 (캐시)
        if self._activity_target is None:
            from think.activity_resolver import resolve_activity_location
            self._activity_target = resolve_activity_location(
                self.unit_id, entry.get("activity"), self._get_home_region()
            )
        return self._activity_target

    def _get_home_region(self):
        """NPC의 홈 region (sleep_location 기준, 없으면 현재 위치)"""
        if self.sleep_location:
            return self.sleep_location.get("region_id", 0)
        loc = self.get_location()
        return loc[0] if loc else 0

    def _check_environment(self, region_id, location_id):
        """환경 인식: 시간대에 따라 조명 켜기/끄기 (도착 시 1회 호출)"""
        from assets.objects import get_location_objects, get_instance

        objects = get_location_objects(region_id, location_id)

        # 조명 오브젝트 찾기
        light_objects = []
        any_light_on = False
        for obj_id in objects:
            light_on = morld.get_unit_prop(obj_id, "light:on")
            if light_on is not None:
                light_objects.append(obj_id)
                if light_on == 1:
                    any_light_on = True

        if not light_objects:
            return

        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("toggle_switch", 0) <= 0:
            return

        millis = self.get_time()
        is_night = millis >= 1080 * 60_000 or millis < 360 * 60_000  # 18:00~06:00

        if is_night and not any_light_on:
            # 밤인데 조명 꺼져있으면 → 켜기
            obj = get_instance(light_objects[0])
            if obj and hasattr(obj, "npc_toggle_switch"):
                obj.npc_toggle_switch(self.unit_id, target_state=1)
        elif not is_night and any_light_on:
            # 낮인데 조명 켜져있으면 → 끄기
            for obj_id in light_objects:
                if morld.get_unit_prop(obj_id, "light:on") == 1:
                    obj = get_instance(obj_id)
                    if obj and hasattr(obj, "npc_toggle_switch"):
                        obj.npc_toggle_switch(self.unit_id, target_state=0)

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

    # ========================================
    # 공용 헬퍼
    # ========================================

    def _is_at(self, target):
        """target의 region_id/location_id에 도착했는지"""
        loc = self.get_location()
        return (loc and loc[0] == target["region_id"]
                and loc[1] == target["location_id"])

    def _on_leaving(self, region_id, location_id):
        """location 떠나기 전 호출 (서브클래스에서 오버라이드)"""
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

    def _move_to(self, target, name="이동"):
        """target으로 이동 job 삽입. 이동 중이면 스킵."""
        info = self.get_info()
        if info.get("is_moving"):
            self._action_taken = True
            return
        # 다른 location으로 이동 시 _on_leaving 호출
        loc = self.get_location()
        if loc and (loc[0] != target["region_id"] or loc[1] != target["location_id"]):
            self._on_leaving(loc[0], loc[1])
        target_x = target.get("x", 0)
        length = target.get("length", 0)
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
    # 기본 활동 핸들러
    # ========================================

    def _handle_default_activity(self, entry):
        """기본 활동 핸들러 (대부분의 활동)

        resolve target → move → env check → execute → idle job
        """
        activity = entry.get("activity", "대기")

        # 1. 장소 결정
        target = self._resolve_target(entry)
        if target is None:
            # 장소 없음 → 현재 위치에서 대기
            remaining = self._remaining_millis_in_entry(entry)
            self._insert_idle_job(entry.get("name", "대기"), max(remaining, 1))
            self._action_taken = True
            return

        # 2. 도착 여부
        if not self._is_at(target):
            # 미도착 → 이동
            self._move_to(target, entry.get("name", "이동"))
            self._arrived = False
        else:
            # 도착 → 환경 체크 + 활동 실행 + idle job
            if not self._arrived:
                self._arrived = True
                self._check_environment(target["region_id"], target["location_id"])
            self._execute_activity(activity, target)
            remaining = self._remaining_millis_in_entry(entry)
            self._insert_idle_job(entry.get("name", "대기"), max(remaining, 1))
            self._action_taken = True

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
            morld.give_item(self.unit_id, item_id, 1)
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

    def _find_lit_indoor_room(self, region_id):
        """조명이 켜진 거처 실내 방 찾기 (소등용)
        거처 = sleep_location과 같은 건물(실내 연결) 내의 방
        """
        from assets.objects import _location_objects

        sleep = getattr(self, "sleep_location", None)
        sleep_r = sleep["region_id"] if sleep else region_id
        sleep_l = sleep["location_id"] if sleep else None

        for (r, l), obj_ids in _location_objects.items():
            if r != region_id:
                continue
            # 거처 필터: sleep_location과 같은 건물인 실내만 대상
            if sleep_l is not None and not morld.is_same_building(r, l, sleep_r, sleep_l):
                continue
            loc_info = morld.get_location_info(r, l)
            if not loc_info or not loc_info.get("is_indoor", False):
                continue
            light_ids = []
            for obj_id in obj_ids:
                if morld.get_unit_prop(obj_id, "light:on") == 1:
                    light_ids.append(obj_id)
            if light_ids:
                return {"region_id": r, "location_id": l, "x": 0, "light_ids": light_ids}
        return None

    def _check_hunger(self):
        """배고픔 확인 → 식사 활동 시작. Returns True if handling hunger."""
        import survival
        if not survival.is_npc_hungry(self.unit_id):
            self._hunger_phase = None
            return False
        # 배고프면 식사 핸들러 실행
        if self._hunger_phase is None:
            self._hunger_phase = "idle"
        _handle_eat(self)
        return True

    # ========================================
    # 동적 스케줄 해석
    # ========================================

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
        if condition == "need_fish":
            return self._check_storage_need("kitchen_fridge", "food_fish", 3)
        elif condition == "need_logs":
            return self._check_storage_need("ingredient_storage", "log", 5)
        elif condition == "need_food":
            return self._check_storage_need(self.food_storage_unique_id, None, 10)
        elif condition == "can_cook":
            # 냉장고에 재료 2개 이상이면 요리 가능
            return not self._check_storage_need(self.food_storage_unique_id, None, 2)
        elif condition == "need_supplies":
            return self._check_storage_need(self.food_storage_unique_id, None, 5)
        return False

    def _check_storage_need(self, storage_uid, item_uid, threshold):
        """저장소 아이템 부족 여부 (True=부족)"""
        from assets.registry import get_instance_id
        from assets.objects import get_instance
        storage_id = get_instance_id(storage_uid)
        if not storage_id:
            return False  # 저장소 없으면 필요 없음
        obj = get_instance(storage_id)
        if not obj:
            return False
        if item_uid:
            return obj.get_item_count(item_uid) < threshold
        else:
            return obj.get_item_count() < threshold


# ========================================
# 활동 핸들러 (모듈화 — think/activities/)
# ========================================

from think.activities import ACTIVITY_HANDLERS as _ACTIVITY_HANDLERS
from think.activities.helpers import find_npc_food as _find_npc_food
from think.activities.helpers import find_food_in_container as _find_food_in_container


# ========================================
# 식사 핸들러 (배고픔 인터럽트)
# ========================================

def _handle_eat(agent):
    """식사: 인벤토리 확인 → 식량 보관 이동 → 음식 가져오기 → 식사"""
    phase = agent._hunger_phase

    if phase == "idle":
        # 인벤토리에 음식이 있으면 바로 식사
        food = _find_npc_food(agent.unit_id)
        if food:
            agent._hunger_phase = "eating"
            _handle_eat(agent)
            return
        # 없으면 식량 보관소로 이동
        agent._hunger_phase = "going_to_storage"
        _handle_eat(agent)
        return

    elif phase == "going_to_storage":
        target = agent.food_storage_location
        if agent._is_at(target):
            agent._hunger_phase = "taking_food"
            agent._action_taken = True
        else:
            agent._move_to(target, "식사")

    elif phase == "taking_food":
        from assets.registry import get_instance_id
        from assets.objects import get_instance
        storage_id = get_instance_id(agent.food_storage_unique_id)
        if storage_id:
            obj = get_instance(storage_id)
            if obj:
                food_uid = _find_food_in_container(storage_id)
                if food_uid:
                    obj.npc_take_item(agent.unit_id, food_uid, 1)
                    agent._hunger_phase = "eating"
                    agent._action_taken = True
                    return
        # 음식 없음 → 포기
        agent._hunger_phase = None
        agent._action_taken = True

    elif phase == "eating":
        food = _find_npc_food(agent.unit_id)
        if food:
            import survival
            survival.npc_eat(agent.unit_id, food["satiety"])
            morld.remove_item(agent.unit_id, food["item_id"], 1)
        agent._hunger_phase = None
        agent._action_taken = True



def register_agent(unit_id, agent):
    """Agent 등록"""
    _agents[unit_id] = agent


def unregister_agent(unit_id):
    """Agent 등록 해제"""
    if unit_id in _agents:
        del _agents[unit_id]


def get_agent(unit_id):
    """Agent 조회"""
    return _agents.get(unit_id)


def think_all():
    """
    모든 등록된 Agent의 think() 호출

    C#의 ThinkSystem에서 호출됩니다.
    MovementSystem 실행 전에 호출되어 경로를 계획합니다.
    """
    if len(_agents) > 0:
        print(f"[think_all] Processing {len(_agents)} agents")
    for unit_id, agent in _agents.items():
        try:
            agent.think()
        except Exception as e:
            print(f"[think] Error in agent {unit_id}: {e}")


def clear_all():
    """모든 Agent 제거"""
    _agents.clear()


def clear_agents():
    """모든 Agent 제거 (챕터 전환용 alias)"""
    _agents.clear()
    print("[think] All agents cleared.")


# ========================================
# 데코레이터 기반 자동 등록
# ========================================

def register_agent_class(unique_id):
    """
    데코레이터: Agent 클래스를 unique_id에 등록

    사용법:
        @register_agent_class("lina")
        class LinaAgent(BaseAgent):
            def think(self):
                ...
    """
    def decorator(cls):
        _agent_classes[unique_id] = cls
        return cls
    return decorator


def create_agent_for(unique_id, unit_id):
    """
    unique_id에 해당하는 Agent 인스턴스 생성

    Args:
        unique_id: 캐릭터 고유 ID (예: "lina")
        unit_id: 인스턴스 ID (정수)

    Returns:
        Agent 인스턴스 또는 None
    """
    if unique_id in _agent_classes:
        return _agent_classes[unique_id](unit_id)
    return None


def get_registered_agent_ids():
    """등록된 Agent unique_id 목록 반환"""
    return list(_agent_classes.keys())


# Note: 자원 생성은 이벤트 기반(resource_agent.py)으로 처리됨
# think/__init__.py에서 import하지 않음 (순환 참조 방지)
# mansion.py에서 register_resource_object()를 직접 호출
