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

    # 공용 스케줄: 현재 위치에서 대기 (24시간)
    STAY_SCHEDULE = [
        {"name": "대기", "action": "stay", "start": 0, "end": 86_400_000, "activity": "대기"}
    ]

    def __init__(self, unit_id):
        self.unit_id = unit_id
        self.schedule_stack = [None]  # [0]은 기본 스케줄 자리 (서브클래스에서 설정)

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

    def _resolve_sleep_location(self):
        """수면 장소를 우선순위에 따라 결정

        우선순위:
            1. 자기 소유 침대 (sleep_location)
            2. 현재 위치의 비어있는 침대
            3. 실내 노숙 (현재 위치가 실내면 그대로)
            4. 야외 노숙

        Returns:
            dict: {"region_id", "location_id", "x", "bed_object_id", "rough"} or None
        """
        # 1순위: 자기 소유 침대
        if self.sleep_location:
            bed = self._find_bed_at(
                self.sleep_location["region_id"],
                self.sleep_location["location_id"])
            if bed:
                return {**self.sleep_location, "bed_object_id": bed}

        # 2순위: 현재 위치의 비어있는 침대
        loc = self.get_location()
        if loc:
            bed = self._find_bed_at(loc[0], loc[1])
            if bed:
                return {"region_id": loc[0], "location_id": loc[1],
                        "x": None, "bed_object_id": bed}

        # 3순위: 실내 노숙
        if loc:
            loc_info = morld.get_location_info(loc[0], loc[1])
            if loc_info and loc_info.get("is_indoor"):
                return {"region_id": loc[0], "location_id": loc[1],
                        "x": None, "bed_object_id": None, "rough": True}

        # 4순위: 야외 노숙
        if loc:
            return {"region_id": loc[0], "location_id": loc[1],
                    "x": None, "bed_object_id": None, "rough": True}

        return None

    def _find_bed_at(self, region_id, location_id):
        """특정 Location에서 빈 슬롯이 있는 침대 찾기

        Returns:
            object_id (int) or None
        """
        objects = morld.get_objects_at_location(region_id, location_id)
        for obj_id in objects:
            props = morld.get_unit_props(obj_id)
            if props.get("posture") != "lie":
                continue
            # 빈 슬롯 확인
            seated_by = morld.get_unit_props_by_type(obj_id, "seated_by")
            for slot, occupant in seated_by.items():
                if occupant == -1:
                    return obj_id
        return None

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
    # think() 기본 구현
    # ========================================

    def think(self):
        """
        AI 로직 실행 - 서브클래스에서 오버라이드

        기본 구현: 수면 시간대 확인 후 스케줄 기반 fill

        Returns:
            None 또는 계획된 경로
        """
        schedule = self.get_current_schedule()
        if not schedule:
            return None

        # 수면 시간대 확인
        is_sleep, sleep_entry = self._is_sleep_time()
        if is_sleep:
            self._handle_sleep()
            return None

        # 수면 시간이 아님 → 앉거나 누워있으면 일어나기
        self._ensure_standing()

        # 일반 스케줄 실행
        self.fill_schedule_jobs_from(schedule)
        return None


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
