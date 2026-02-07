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

import random
import morld

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

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self.schedule_stack = [None]  # [0]은 기본 스케줄 자리 (서브클래스에서 설정)
        # Activity 상태 (think에서 단일 행동 계획용)
        self._current_activity = None   # 현재 수행 중인 activity entry
        self._activity_target = None    # resolve된 장소 정보
        self._arrived = False           # 목표 장소 도착 여부

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
            # 침대 없거나 노숙이면 그냥 대기 (이동 안 함)
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
            # 도착 — 목욕 중 (별도 오브젝트 조작 없음, 그냥 대기)
            pass
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
        AI 로직 실행 — 매 step마다 호출

        모든 행동 결정이 여기서 처리됨:
        1. 목욕/수면 시간대 → 기존 핸들러
        2. 현재 시간대 activity 확인
        3. activity 변경 감지 → 상태 리셋
        4. 장소 결정 (고정 or resolver)
        5. 미도착 → 이동 (insert_job)
        6. 도착 → 환경 체크 (조명 등)
        7. 도착 → 행동 실행 (채집, 벌목 등)
        """
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

        # 2. 현재 activity 확인
        entry = self._get_current_activity(schedule)
        if entry is None:
            return None

        # 3. activity 변경 감지 → 상태 리셋
        if self._current_activity is not entry:
            self._current_activity = entry
            self._activity_target = None
            self._arrived = False

        # 4. 장소 결정
        target = self._resolve_target(entry)
        if target is None:
            return None

        # 5. 위치 체크: 도착 여부
        loc = self.get_location()
        at_target = (loc and loc[0] == target["region_id"]
                     and loc[1] == target["location_id"])

        # 6. 미도착 → 이동
        if not at_target:
            self._arrived = False
            info = self.get_info()
            if not info.get("is_moving"):
                # 사냥/순찰: location length 내 랜덤 위치
                target_x = target.get("x", 0)
                length = target.get("length", 0)
                if length > 0 and target_x == 0:
                    target_x = random.randint(0, length)

                morld.insert_job(self.unit_id, {
                    "name": entry.get("name", entry.get("activity", "이동")),
                    "action": "move",
                    "region_id": target["region_id"],
                    "location_id": target["location_id"],
                    "target_x": target_x,
                    "duration": 0,
                })
            return None

        # 7. 도착 → 환경 체크 (최초 1회)
        if not self._arrived:
            self._arrived = True
            self._check_environment(loc[0], loc[1])

        # 8. 도착 → 행동 실행
        activity = entry.get("activity", "대기")
        self._execute_activity(activity, target)
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
        """환경 인식: 어두운 실내면 조명 켜기 (도착 시 1회 호출)"""
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

        # 모든 조명이 꺼져있으면 하나 켜기
        if light_objects and not any_light_on:
            props = morld.get_unit_props_by_type(self.unit_id, "can")
            if props and props.get("toggle_switch", 0) > 0:
                obj = get_instance(light_objects[0])
                if obj and hasattr(obj, "npc_toggle_switch"):
                    obj.npc_toggle_switch(self.unit_id, target_state=1)

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
