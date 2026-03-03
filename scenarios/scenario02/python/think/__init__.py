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

# ========================================
# 레지스트리 re-export (하위 호환)
# ========================================
from think.registry import (
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
)

# ========================================
# Mixin imports
# ========================================
from think.combat_mixin import CombatMixin
from think.interrupt_mixin import InterruptMixin
from think.movement_mixin import MovementMixin
from think.environment_mixin import EnvironmentMixin
from think.schedule_mixin import ScheduleResolverMixin


class BaseAgent(
    CombatMixin,
    InterruptMixin,
    MovementMixin,
    EnvironmentMixin,
    ScheduleResolverMixin,
):
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

    # (보관소는 storage:{category} prop 기반 동적 탐색 — resolve_storage_container)

    _action_duration_overrides = {}  # 서브클래스에서 오버라이드 가능

    def __getattr__(self, name):
        """BaseAgent에 없는 속성 → Character asset에서 조회 (composition delegation)"""
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            from assets.characters import get_instance
            char = get_instance(self.unit_id)
        except ImportError:
            raise AttributeError(name)
        if char is not None:
            return getattr(char, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    @property
    def _is_creature(self):
        """morld API 기반 creature 판정 (C# UnitType)"""
        info = morld.get_unit_info(self.unit_id)
        return bool(info.get("is_creature", False)) if info else False

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
        # === FSM 스택 (행동 컨텍스트 관리) ===
        from think.fsm import LifeState
        self._fsm_stack = [LifeState()]  # root: 생활 (항상 존재, pop 불가)
        # === 지속 기억 (활동 간 유지, 향후 세이브/로드 대상) ===
        self._memory = {
            "hunger_phase": None,   # 식사 단계 (None/idle/going_to_storage/taking_food/eating)
            "cold_phase": None,     # 방한 단계 (None/idle/going/taking/equipping)
            "cold_last_attempt": None,  # 마지막 추위 대응 시도 시각 (밀리초)
            "hot_phase": None,      # 더위 단계 (None/idle/unequipping/storing)
            "clothing_phase": None,   # 착의 단계 (None/idle/going/taking/equipping)
            "clothing_last_attempt": None,  # 마지막 착의 시도 시각 (밀리초)
            "excretion_phase": None,  # 배변 단계 (None/idle/going/using)
            "excretion_target": None, # 동적 탐색된 화장실 위치
            "self_comfort_phase": None,   # 자위 단계 (None/idle/going/performing)
            "self_comfort_cooldown": None, # 마지막 자위/탐색 시각 (밀리초)
            "seek_player_phase": None,    # 플레이어 탐색 단계 (None/idle/going)
            "seek_player_target": None,   # 탐색 대상 위치
            "childbirth_phase": None,     # 출산 단계 (None/idle/going/laboring/recovery)
            "childbirth_target": None,    # 출산 장소
            "childbirth_child_id": None,  # 출산된 아이 unit_id
            "last_child_id": None,        # 마지막 출산 아이 unit_id
            "maternal_phase": None,       # 모성 단계 (None/idle/going/interacting)
            "maternal_target": None,      # 아이 위치
            "socialize_phase": None,      # 대화 단계 (None/idle/going/talking)
            "socialize_target_id": None,  # 대화 대상 NPC unit_id
            "socialize_cooldown": None,   # 마지막 대화 시각 (밀리초)
            "gift_phase": None,           # 선물 단계 (None/idle/going/giving)
            "gift_target_id": None,       # 선물 대상 NPC unit_id
            "gift_item_id": None,         # 선물할 아이템 ID
            "gift_cooldown": None,        # 마지막 선물 시각 (밀리초)
            "npc_intimacy_phase": None,   # NPC-NPC 성행위 단계 (None/idle/going/performing/finishing)
            "npc_intimacy_partner": None, # 성행위 파트너 NPC unit_id
            "npc_intimacy_mode": None,    # "consensual" / "forced" / None
            "npc_intimacy_cooldown": None, # 마지막 성행위 시각 (밀리초)
            "romance_last": None,         # 마지막 애정 행위 기억 {partner_id, region_id, location_id, timestamp, mode}
            "laundry_phase": None,        # 빨래 단계 (None/going_to_washer/loading/waiting_wash/collecting_wash/going_to_dryer/loading_dry/waiting_dry/collecting_dry)
            "laundry_washer": None,       # 세탁기 위치 {region_id, location_id, x, object_id}
            "laundry_dryer": None,        # 건조기 위치
            "laundry_items": None,        # 세탁 중인 아이템 ID 목록 (re-equip용)
            "laundry_cooldown": None,     # 마지막 빨래 시각 (밀리초) — 쿨다운 3시간
            # 전투: FSM 상태로 이관 (CombatState/FleeState/ResignationState/DesperateState)
            "combat_discovered": False,   # 발견 대사 중복 방지 (CombatState에서 관리하지만 하위 호환용)
        }

    # ========================================
    # FSM 스택 관리
    # ========================================

    def _fsm_push(self, state):
        """FSM 상태를 스택에 push.

        동일 이상 레벨의 기존 State를 자동 pop한 뒤 push.
        이를 통해 change(pop→push) 동작이 자연 발생한다.
        """
        # 동일 이상 레벨 자동 pop
        while self._fsm_stack[-1].level >= state.level:
            self._fsm_pop()
        self._fsm_stack.append(state)
        state.enter(self)

    def _fsm_pop(self):
        """FSM 스택 최상위 상태를 pop (exit() 호출).

        스택이 비거나 빈 상태에서 pop 시 에러 — 로직 버그 감지용.
        """
        if len(self._fsm_stack) <= 1:
            info = self.get_info()
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            raise RuntimeError(
                f"[FSM] {name} — 스택 비어짐 (pop 불가). stack={self._fsm_stack}")
        state = self._fsm_stack.pop()
        state.exit(self)
        return state

    def _fsm_top(self):
        """FSM 스택 최상위 상태 반환"""
        return self._fsm_stack[-1]

    # ========================================
    # 스케줄 관리
    # ========================================

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
    # 인벤토리 선호 비율 (소프트 가이드)
    # ========================================

    # 카테고리별 우선순위 (높을수록 보존 우선, 서브클래스에서 오버라이드)
    _inventory_priority = {
        "tool": 80, "clothing": 70, "food": 60,
        "food_ingredient": 50, "drink_ingredient": 50,
        "material": 40, "seed": 30,
        "garden_tool": 30, "garden_supply": 30,
        "trinket": 10, "flower": 10,
    }

    def _find_droppable_item(self):
        """
        인벤토리에서 가장 낮은 priority 아이템 찾기 (장착 아이템 제외).

        Returns:
            (item_id, count) 또는 None (드롭 가능한 아이템 없음)
        """
        inventory = morld.get_unit_inventory(self.unit_id)
        if not inventory:
            return None

        equipped = morld.get_equipped_items(self.unit_id) if hasattr(morld, 'get_equipped_items') else []
        equipped_set = set(equipped) if equipped else set()

        from assets.items import get_unique_id, get_item_class

        lowest_priority = 999
        lowest_item = None

        for item_id, count in inventory.items():
            if count <= 0:
                continue
            if item_id in equipped_set:
                continue

            # 카테고리 조회
            uid = get_unique_id(item_id)
            if not uid:
                continue
            cls = get_item_class(uid)
            category = getattr(cls, 'category', None) if cls else None
            priority = self._inventory_priority.get(category, 0)

            if priority < lowest_priority:
                lowest_priority = priority
                lowest_item = (item_id, count)

        return lowest_item

    def _ensure_slot_for(self, item_id):
        """
        슬롯 확보: 빈 곳 있으면 True, 없으면 lowest priority 드롭 후 True.
        드롭 불가능하면 False.

        Args:
            item_id: 추가할 아이템 ID

        Returns:
            bool — True if slot is available
        """
        import inventory as inv_module

        if inv_module.has_free_slot(self.unit_id, item_id):
            return True

        # 드롭 대상 찾기
        droppable = self._find_droppable_item()
        if droppable is None:
            return False

        drop_id, drop_count = droppable
        import ground as ground_module
        morld.lost_item(self.unit_id, drop_id)
        ground_module.drop_item_at(self.unit_id, drop_id, drop_count)
        print(f"[think] _ensure_slot_for: unit={self.unit_id} dropped item={drop_id} x{drop_count} (priority swap)")
        return True

    # ========================================
    # 수면 시스템
    # ========================================

    # (시설 탐색은 facility_resolver를 통한 prop 기반 동적 탐색)

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

    def _is_already_sleeping(self):
        """침대에 누운 상태 + 수면 시간 → 비자발적 수면 (tier 1)

        seated_on prop 존재 = 침대에 눕혀있음.
        수면 시간이면 인터럽트 불가 (기절과 동일 계층).

        Returns:
            (bool, entry or None)
        """
        seated_on = morld.get_unit_props_by_type(self.unit_id, "seated_on")
        if not seated_on:
            return False, None
        is_sleep, entry = self._is_sleep_time()
        if is_sleep:
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
        # bed_owner prop 기반 침대 탐색
        owner_unique = self.owner_unique_id or ""
        bed_loc = None
        if owner_unique:
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner_unique}", 1)
            if beds:
                bed_loc = beds[0]

        if not bed_loc:
            # 소유 침대 없음 → 현재 위치에서 노숙
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

        result = morld.resolve_sleep_target(
            self.unit_id,
            bed_loc["region_id"],
            bed_loc["location_id"],
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
            # 침대도 못 찾고 현재 위치도 없음 → 최소 idle
            self._insert_idle_job("sleep", self._get_action_duration("sleep_fallback"))
            self._action_taken = True
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
            # 수면 시작 → 기억 처리 (aftermath 감소 + 긍정 기억 활성화)
            self._process_memory_on_sleep()
            # sleep job 삽입 (침대든 노숙이든)
            _, sleep_entry = self._is_sleep_time()
            if sleep_entry:
                remaining = self._remaining_millis_in_entry(sleep_entry)
                self._insert_idle_job("sleep", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            else:
                # 피로 인터럽트 등 비스케줄 수면 — 2시간 단위
                self._insert_idle_job("sleep", self._get_action_duration("sleep_default"))
            self._action_taken = True
        else:
            # 이동 필요 → move job 설정 (항상 삽입)
            target_x = sleep_info.get("x", 0)
            morld.insert_job(self.unit_id, {
                "name": "수면",
                "action": "move",
                "region_id": target_region,
                "location_id": target_location,
                "target_x": target_x if target_x else 0,
                "duration": 0,
            })
            self._action_taken = True

    def _process_memory_on_sleep(self):
        """수면 시작 시 기억 처리.

        1) aftermath 단계 감소:
           음수 prop = 이미 표시됨 → abs - 1 → 양수(대기) 또는 0(해제)
           양수 prop = 미표시 대기 → 변경 없음

        2) 긍정 기억 활성화:
           -1 (수면 전 대기) → 1 (활성, on_meet 대상)
        """
        # aftermath 단계 감소
        for prop_key in ("상태:강제피해", "상태:무의식피해", "상태:시간정지피해", "상태:수간피해"):
            value = morld.get_unit_prop(self.unit_id, prop_key)
            if value is not None and value < 0:
                new_stage = abs(value) - 1
                morld.set_unit_prop(self.unit_id, prop_key, max(new_stage, 0))

        # 긍정 기억 활성화 (-1 → 1)
        pos_mem = morld.get_unit_prop(self.unit_id, "기억:긍정기억")
        if pos_mem is not None and pos_mem == -1:
            morld.set_unit_prop(self.unit_id, "기억:긍정기억", 1)

        # 몽정 체크 (P anatomy + 정액 만수, 연애 모드 ON 시만)
        try:
            import settings
            if settings.is_romance_enabled():
                import semen as semen_mod
                if semen_mod.get_semen(self.unit_id) >= semen_mod.SEMEN_MAX:
                    semen_mod.process_wet_dream(self.unit_id)
        except ImportError:
            pass

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

    def _get_action_duration(self, key):
        """행동 소요시간 조회 — 캐릭터 오버라이드 우선, 없으면 테이블 기본값"""
        if key in self._action_duration_overrides:
            return self._action_duration_overrides[key]
        from think.activities.helpers import ACTION_DURATION
        return ACTION_DURATION.get(key, ACTION_DURATION["abort"])

    def _do_instant_action(self, job_name, duration_key):
        """고정 시간 행동 수행 — idle job 삽입 + action_taken 설정

        Args:
            job_name: DES job 이름 (디버그/UI 표시용)
            duration_key: ACTION_DURATION 테이블 키
        """
        duration = self._get_action_duration(duration_key)
        self._insert_idle_job(job_name, duration)
        self._action_taken = True

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

        facility_resolver로 가용 욕실 탐색 (점유 감지 포함).
        모든 욕실 점유 시: 시간 여유 있으면 대기 후 재탐색, 없으면 목욕 포기.
        """
        from think.facility_resolver import resolve_bath

        # can:bath 체크 - 없으면 에러 (개발 시 누락 방지)
        props = morld.get_unit_props_by_type(self.unit_id, "can")
        if not props or props.get("bath", 0) <= 0:
            info = morld.get_unit_info(self.unit_id)
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            raise RuntimeError(
                f"[think] {name}에게 'can:bath' prop이 없습니다. "
                f"목욕 활동을 하려면 캐릭터에 'can:bath': 1을 추가하세요."
            )

        target = resolve_bath(self)
        if target is None:
            # 모든 욕실 점유 또는 없음 → 대기/포기
            _, bath_entry = self._is_bath_time()
            if bath_entry:
                remaining = self._remaining_millis_in_entry(bath_entry)
                if remaining > 10 * 60_000:
                    # 10분 이상 남음 → 5분 대기 후 재탐색
                    self._insert_idle_job("목욕대기", self._get_action_duration("bath_wait"))
                else:
                    # 10분 미만 → 목욕 포기, 남은 시간 대기
                    self._insert_idle_job("대기", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            else:
                self._insert_idle_job("대기", self._get_action_duration("brief"))
            return

        target_region = target["region_id"]
        target_location = target["location_id"]

        loc = self.get_location()
        if loc and loc[0] == target_region and loc[1] == target_location:
            # 도착 — 체온/젖음/청결/정액 효과 + 목욕 job 삽입
            import temperature
            import humidity
            temperature.warm_character(self.unit_id, 2.0)
            humidity.dry_unit(self.unit_id, 100)
            try:
                import needs
                needs.set_cleanliness(self.unit_id, 0)
            except ImportError:
                pass
            try:
                import romance
                romance.clear_all_semen(self.unit_id)
            except ImportError:
                pass
            _, bath_entry = self._is_bath_time()
            if bath_entry:
                remaining = self._remaining_millis_in_entry(bath_entry)
                self._insert_idle_job("목욕", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            else:
                # 청결 인터럽트 등 비스케줄 목욕 — 30분
                self._insert_idle_job("목욕", self._get_action_duration("bath"))
        else:
            # 이동
            target_x = target.get("x", 0)
            morld.insert_job(self.unit_id, {
                "name": "목욕",
                "action": "move",
                "region_id": target_region,
                "location_id": target_location,
                "target_x": target_x,
                "duration": 0,
            })

    # ========================================
    # think() — 5-Tier 우선순위 계층 기반 AI 결정
    # ========================================
    #
    # Tier 1: 비자발적 (Involuntary)  — 기절, 이미 수면 중
    # Tier 2: 반응형  (Reactive)      — [미래] 위협/소리 반응
    # Tier 3: 생존    (Survival)      — 배고픔, 추위, 더위
    # Tier 4: 쾌적    (Comfort)       — 목욕, 취침 이동
    # Tier 5: 일상    (Routine)       — 스케줄 기반 활동
    #
    # [DES 규칙] 모든 경로에서 반드시 duration > 0인 job을 삽입해야 함.

    def think(self):
        """
        AI 로직 실행 — 매 step마다 호출 (DES에서는 job 만료 시)

        5-Tier 우선순위 계층:
        [1] Involuntary: 기절, 이미 수면 중 (인터럽트 불가)
        [2] Reactive: 위협/소리 반응 (미래 확장)
        [3] Survival: 배고픔, 추위, 더위
        [4] Comfort: 목욕, 취침 이동
        [5] Routine: 스케줄 기반 활동

        [DES 규칙] 이 메서드는 반드시 duration > 0인 job을 삽입해야 함.
        stay job: _insert_idle_job() 사용, move job: duration=0 (C#이 자동 계산)
        """
        self._action_taken = False
        _tier_reached = 0  # 도달한 최고 tier (디버그용)

        # idle flavor 클리어 (flavored idle에서만 재설정됨)
        from think.idle_flavors import clear_flavor
        clear_flavor(self.unit_id)

        # FSM 스택: 최상위 State가 처리하면 하위 로직 차단
        if self._fsm_stack:
            top = self._fsm_stack[-1]
            if top.update(self):
                return None  # State가 처리 완료
            # update() False = State가 pop됨 → 아래 Life 로직 진행

        # Tier -1: 운반 중 (Limbo에 있음)
        import carry
        if carry.is_being_carried(self.unit_id):
            self._handle_being_carried()
            return None

        # NPC 성행위 파트너 (이니시에이터가 관리 중) → 건너뛰기
        if morld.get_unit_prop(self.unit_id, "상태:NPC성행위중"):
            # 이니시에이터가 아닌 파트너는 대기만
            if self._memory.get("npc_intimacy_phase") is None:
                self._insert_idle_job("대기", 60_000)
                return None

        # 플레이어 로맨스 세션 중 → 생존 인터럽트 차단
        if morld.get_unit_prop(self.unit_id, "상태:로맨스중"):
            self._insert_idle_job("대기", 60_000)
            return None

        # Tier 0: 결박
        import restraint
        if restraint.is_restrained(self.unit_id):
            if restraint.is_lower_restrained(self.unit_id):
                self._handle_restrained()  # 하체 포함 → 이동 불가
                return None
            else:
                self._handle_upper_restrained()  # 상체만 → 이동 가능
                return None

        schedule = self.get_current_schedule()
        if schedule:
            # Tier 1: 비자발적 (기절, 수면 중)
            if self._check_tier1_involuntary():
                _tier_reached = 1
            else:
                # Tier 1 통과 → 활동 준비: 앉기/눕기 상태 해제
                self._ensure_standing()

                # Tier 2: 반응형 — 전투 > 결박된 동료 > 탈진자 간호 > 소리 반응
                if self._check_combat_threat():
                    _tier_reached = 2
                elif self._check_restrained_nearby():
                    _tier_reached = 2
                elif self._check_exhausted_nearby():
                    _tier_reached = 2
                elif self._check_tier2_reactive():
                    _tier_reached = 2
                # Tier 3: 생존
                elif self._check_tier3_survival():
                    _tier_reached = 3
                # Tier 4: 쾌적
                elif self._check_tier4_comfort():
                    _tier_reached = 4
                else:
                    # Tier 5: 일과
                    _tier_reached = 5
                    self._check_tier5_routine()

        # safety net: 어떤 경로든 job 미삽입 시 idle job 보장
        if not self._action_taken:
            info = self.get_info()
            name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
            cause = "schedule=None" if not schedule else f"tier={_tier_reached}"
            # 진행 중인 인터럽트 상태 수집
            active_phases = []
            for key in ("hunger_phase", "cold_phase", "hot_phase", "clothing_phase",
                        "excretion_phase", "self_comfort_phase", "seek_player_phase",
                        "socialize_phase", "gift_phase", "laundry_phase",
                        "childbirth_phase", "maternal_phase",
                        "restrained_phase", "rescue_phase", "sound_reaction_phase"):
                val = self._memory.get(key)
                if val is not None:
                    active_phases.append(f"{key}={val}")
            phase_info = ", ".join(active_phases) if active_phases else "none"
            print(f"[think] WARNING: {name} 행동 미결정 — {cause}, phases=[{phase_info}]")
            self._insert_idle_job("할 일 없음", self._get_action_duration("safety_net"))

        return None


# Note: 자원 생성은 이벤트 기반(resource_agent.py)으로 처리됨
# think/__init__.py에서 import하지 않음 (순환 참조 방지)
# mansion.py에서 register_resource_object()를 직접 호출
