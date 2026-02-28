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

    # (보관소는 storage:{category} prop 기반 동적 탐색 — resolve_storage_container)

    _is_creature = False             # CreatureAgent에서 True로 오버라이드
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
            # 전투
            "combat_phase": None,         # None/engaging/attacking/retreating/regrouping/resignation/desperate
            "combat_target_id": None,     # 전투 대상 unit_id
            "combat_last_attack_ms": 0,   # 마지막 공격 시각 (밀리초)
            "combat_last_enemy_ms": 0,    # 마지막 적 목격/소리 시각 (밀리초)
            "combat_flee_target": None,   # 도주 목적지 dict (고정)
            "combat_regroup_phase": None, # 정비 단계 (None/recovering)
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
        state.enter(self)
        self._fsm_stack.append(state)

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

    def _check_tier1_involuntary(self):
        """Tier 1: 비자발적 상태 (기절, 수면 중)

        이 상태의 NPC는 어떤 인터럽트도 받지 않음.
        _ensure_standing() 호출 전이므로 침대에 누운 상태 유지.

        Returns:
            True if action was taken.
        """
        # 1a. 기절
        import survival
        if survival.is_npc_fainted(self.unit_id):
            remaining = survival.get_faint_remaining_millis(self.unit_id)
            self._insert_idle_job("fainting", max(remaining, 1))  # 기절 잔여 시간 — survival 시스템 연동
            self._action_taken = True
            return True

        # 1a-2. 탈진
        if survival.is_npc_exhausted(self.unit_id):
            remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
            self._insert_idle_job("exhaustion", max(remaining, 1))
            self._action_taken = True
            return True

        # 1b. 이미 침대에서 자는 중
        already_sleeping, sleep_entry = self._is_already_sleeping()
        if already_sleeping:
            # 추위 기상: 체온이 위험 수준이면 깨어남
            try:
                import temperature
                if temperature.is_cold(self.unit_id, threshold=35.0):
                    # 침대에서 일어남 → tier 3 cold 처리로 이관
                    return False
            except ImportError:
                pass
            remaining = self._remaining_millis_in_entry(sleep_entry)
            self._insert_idle_job("sleep", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            self._action_taken = True
            return True

        return False

    # ========================================
    # 결박 상태 처리 (Tier 0)
    # ========================================

    RESTRAINED_ESCAPE_INTERVAL = 30 * 60 * 1000  # 30분마다 해제 시도

    def _handle_being_carried(self):
        """운반 중 상태 처리 — Limbo에서 대기

        운반자가 들고 있는 동안 idle job만 삽입.
        기절 상태가 해제되면 의식 회복 → 비결박 시 자동 해방.
        """
        import survival
        import carry

        # 기절/탈진 해제 확인
        if not survival.is_npc_fainted(self.unit_id) and not survival.is_npc_exhausted(self.unit_id):
            # 의식 회복 + 행동 가능
            import restraint
            if not restraint.is_lower_restrained(self.unit_id):
                # 비결박 → 자동 해방
                carrier_id = carry.get_carrier(self.unit_id)
                if carrier_id:
                    carry.put_down(carrier_id)
                    info = self.get_info()
                    name = info.get("name", str(self.unit_id)) if info else str(self.unit_id)
                    print(f"[think] {name}: 의식 회복 → 운반에서 해방")
                # 해방 후 일반 think 재호출되므로 여기서는 idle만
                self._insert_idle_job("의식 회복", 60_000)
                self._action_taken = True
                return
            # TODO: 결박 상태 저항 대사 (의식 있음 + 결박 → 운반 계속하되 반응)

        # TODO: 운반 중 NPC 목격 반응 이벤트 발화
        # 운반 중 대기 (1시간)
        self._insert_idle_job("운반 중", 3_600_000)
        self._action_taken = True

    def _handle_restrained(self):
        """결박 상태 처리 — 모든 일상 행동 차단

        3-phase: idle → escaping → waiting
        - idle: 해제 시도 가능 여부 체크
        - escaping: 자력 해제 시도
        - waiting: 대기 (30분마다 재시도). 입 자유 시 소리치기
        """
        import restraint
        import survival

        # 방어: 외부에서 이미 해제된 경우 (구출 등) — 메모리 정리
        if not restraint.is_restrained(self.unit_id):
            self._memory["restrained_phase"] = None
            self._memory.pop("restrained_wait_until", None)
            return

        # 행동불능(기절/탈진/수면) → 탈출 시도 없이 대기
        if survival.is_npc_incapacitated(self.unit_id) or survival.is_npc_sleeping(self.unit_id):
            if survival.is_npc_fainted(self.unit_id):
                remaining = survival.get_faint_remaining_millis(self.unit_id)
                self._insert_idle_job("fainting", max(remaining, 1))
            elif survival.is_npc_exhausted(self.unit_id):
                remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
                self._insert_idle_job("exhaustion", max(remaining, 1))
            else:
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        phase = self._memory.get("restrained_phase", "idle")

        if phase == "idle":
            # 처음 결박됨 or 대기 후 재시도
            self._memory["restrained_phase"] = "escaping"
            self._insert_idle_job("결박 해제 시도", 5 * 60 * 1000)  # 5분 걸림
            self._action_taken = True
            return

        if phase == "escaping":
            if restraint.attempt_self_escape(self.unit_id):
                # 성공: 사지 결박 해제
                restraint.release_self(self.unit_id)
                # 사지 해제 후 입/눈도 해제
                if not restraint.is_restrained(self.unit_id):
                    if restraint.is_gagged(self.unit_id):
                        restraint.release_mouth(self.unit_id)
                    if restraint.is_blindfolded(self.unit_id):
                        restraint.release_eyes(self.unit_id)
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박 해제됨", 1 * 60 * 1000)
            else:
                # 실패: 대기 상태로 전환
                self._memory["restrained_phase"] = "waiting"
                self._memory["restrained_wait_until"] = (
                    self.get_time() + self.RESTRAINED_ESCAPE_INTERVAL
                )
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        if phase == "waiting":
            # 입이 자유로우면 도움 요청
            if not restraint.is_gagged(self.unit_id):
                try:
                    import sound
                    sound.emit_sound(self.unit_id, "scream", 80)
                except ImportError:
                    pass

            # 결박 중 복종 소폭 상승 (+0.5/30분)
            player_id = morld.get_player_id()
            if player_id:
                player_info = morld.get_unit_info(player_id)
                if player_info:
                    pname = player_info.get("name", "주인공")
                    sub_key = f"관계:{pname}:복종"
                    sub_val = morld.get_unit_prop(self.unit_id, sub_key) or 0
                    morld.set_unit_prop(self.unit_id, sub_key,
                                        min(100, sub_val + 0.5))

            wait_until = self._memory.get("restrained_wait_until", 0)
            if self.get_time() >= wait_until:
                # 재시도
                self._memory["restrained_phase"] = "idle"
            self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

    def _handle_upper_restrained(self):
        """상체만 결박 — 이동 가능하지만 손 사용 불가

        이동은 가능하므로 도움을 요청하며 돌아다닌다.
        30분마다 자력 해제를 시도한다.
        """
        import restraint
        import survival

        # 방어: 외부에서 이미 해제된 경우 (구출 등) — 메모리 정리
        if not restraint.is_upper_restrained(self.unit_id):
            self._memory["restrained_phase"] = None
            self._memory.pop("restrained_wait_until", None)
            return

        # 행동불능(기절/탈진/수면) → 탈출 시도 없이 대기
        if survival.is_npc_incapacitated(self.unit_id) or survival.is_npc_sleeping(self.unit_id):
            if survival.is_npc_fainted(self.unit_id):
                remaining = survival.get_faint_remaining_millis(self.unit_id)
                self._insert_idle_job("fainting", max(remaining, 1))
            elif survival.is_npc_exhausted(self.unit_id):
                remaining = survival.get_exhaustion_remaining_millis(self.unit_id)
                self._insert_idle_job("exhaustion", max(remaining, 1))
            else:
                self._insert_idle_job("결박", self.RESTRAINED_ESCAPE_INTERVAL)
            self._action_taken = True
            return

        phase = self._memory.get("restrained_phase", "idle")

        if phase == "idle":
            self._memory["restrained_phase"] = "escaping"
            self._insert_idle_job("결박 해제 시도", 5 * 60 * 1000)
            self._action_taken = True
            return

        if phase == "escaping":
            if restraint.attempt_self_escape(self.unit_id):
                restraint.release_self(self.unit_id)
                if not restraint.is_restrained(self.unit_id):
                    if restraint.is_gagged(self.unit_id):
                        restraint.release_mouth(self.unit_id)
                    if restraint.is_blindfolded(self.unit_id):
                        restraint.release_eyes(self.unit_id)
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박 해제됨", 1 * 60 * 1000)
            else:
                self._memory["restrained_phase"] = "wandering"
                self._memory["restrained_wait_until"] = (
                    self.get_time() + self.RESTRAINED_ESCAPE_INTERVAL
                )
                # 입이 자유로우면 소리치기
                if not restraint.is_gagged(self.unit_id):
                    try:
                        import sound
                        sound.emit_sound(self.unit_id, "scream", 80)
                    except ImportError:
                        pass
                # 이동 가능 — 랜덤 배회
                self._do_wander()
            self._action_taken = True
            return

        if phase == "wandering":
            # 상체 결박 중 복종 소폭 상승 (+0.3/30분)
            player_id = morld.get_player_id()
            if player_id:
                player_info = morld.get_unit_info(player_id)
                if player_info:
                    pname = player_info.get("name", "주인공")
                    sub_key = f"관계:{pname}:복종"
                    sub_val = morld.get_unit_prop(self.unit_id, sub_key) or 0
                    morld.set_unit_prop(self.unit_id, sub_key,
                                        min(100, sub_val + 0.3))

            wait_until = self._memory.get("restrained_wait_until", 0)
            if self.get_time() >= wait_until:
                self._memory["restrained_phase"] = "idle"
                self._insert_idle_job("결박", 1 * 60 * 1000)
            else:
                self._do_wander()
            self._action_taken = True
            return

    # ========================================
    # 전투 위협 감지 + 대응 (Tier 2)
    # ========================================

    COMBAT_ATTACK_DURATION = 6_000       # NPC 근접 공격 시간 (ms)
    COMBAT_END_COOLDOWN = 10 * 60_000    # 전투 종료 쿨다운 10분 (ms), 서브클래스 override 가능
    COMBAT_REGROUP_HP_THRESHOLD = 0.75   # 정비 종료 HP 비율 (75%), 서브클래스 override 가능
    COMBAT_DESPERATE_CHANCE = 0.5        # 포위 시 필사의 저항 확률 (0.0~1.0), 서브클래스 override

    def _check_combat_threat(self) -> bool:
        """전투 위협 감지 + 대응

        Phase machine:
        - engaging: 사거리 밖 이동 → attacking
        - attacking: 공격 실행
        - retreating: 안전 지역으로 이동
        - regrouping: 정비 중 (회복 대기)
        - resignation: 체념 (반격/이동 불가, 적 전멸 시 정비 전환)
        - desperate: 필사의 저항 (도주 불가, 적 전멸 시 정비 전환)

        전투 종료 3-조건 (모두 AND):
        1. 현재 location에 적 없음
        2. 전투 소리 미청취
        3. 마지막 적 목격/소리 + COMBAT_END_COOLDOWN 경과
        """
        import combat as _combat

        behavior = getattr(self, 'BATTLE_BEHAVIOR', None)
        if not behavior:
            return False

        phase = self._memory.get("combat_phase")

        # 진행 중인 전투
        if phase is not None:
            # 체념/필사: 적 전멸 시 정비 전환
            if phase in ("resignation", "desperate"):
                enemy_id = self._scan_nearest_enemy()
                if enemy_id is None:
                    self._log_combat_phase("적 전멸 → 정비 전환")
                    self._memory["combat_phase"] = "regrouping"
                    self._memory["combat_regroup_phase"] = "recovering"
                elif phase == "desperate":
                    self._memory["combat_target_id"] = enemy_id
                    self._memory["combat_last_enemy_ms"] = self.get_time()

            # regrouping/retreating: 적 재감지
            elif phase in ("regrouping", "retreating"):
                enemy_id = self._scan_nearest_enemy()
                if enemy_id is not None:
                    self._memory["combat_last_enemy_ms"] = self.get_time()
                    style = behavior.get("combat_style", "aggressive")
                    if style == "evasive":
                        pass  # 도주형: 적 발견해도 계속 도주/정비
                    else:
                        self._log_combat_phase(f"적 재감지(id={enemy_id}) → engaging")
                        self._memory["combat_phase"] = "engaging"
                        self._memory["combat_target_id"] = enemy_id
                # 전투 종료 판정 (regrouping)
                if phase == "regrouping" and self._should_end_combat():
                    self._log_combat_phase("전투 종료 (3-조건 충족)")
                    self._end_combat()
                    self._insert_idle_job("전투 종료", 2_000)
                    self._action_taken = True
                    return True

            self._handle_combat()
            return True

        # 적 탐색: 같은 location
        enemy_id = self._scan_nearest_enemy()
        if enemy_id is None:
            return False

        # 전투 시작 시간 기록
        self._memory["combat_last_enemy_ms"] = self.get_time()

        # 행동 결정 (combat_style)
        style = behavior.get("combat_style", "aggressive")

        if style == "evasive":
            import survival as _surv
            my_hp = _surv.get_health(self.unit_id)
            my_max = _surv.get_max_health(self.unit_id)
            threshold = behavior.get("retreat_threshold", 0.5)
            if my_hp <= my_max * threshold:
                _combat._emit_combat_line(self.unit_id, "flee")
                self._memory["combat_phase"] = "retreating"
                self._memory["combat_target_id"] = enemy_id
                self._log_combat_phase("도주 개시")
                self._handle_combat()
                return True

        # 전투 개시 — 발견 대사 (최초 1회)
        if not self._memory.get("combat_discovered"):
            _combat._emit_combat_line(self.unit_id, "discover")
            self._memory["combat_discovered"] = True
        self._memory["combat_phase"] = "engaging"
        self._memory["combat_target_id"] = enemy_id
        self._log_combat_phase("전투 개시")
        self._handle_combat()
        return True

    def _scan_nearest_enemy(self):
        """현재 location에서 가장 가까운 적 unit_id 반환 (없으면 None)"""
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return None

        units = morld.get_units_at_location(my_loc[0], my_loc[1])
        enemy_id = None
        enemy_dist = float('inf')

        my_faction = morld.get_unit_prop(self.unit_id, "전투:세력")
        detect_range = morld.get_unit_prop(self.unit_id, "전투:감지거리") or 100

        for uid in units:
            if uid == self.unit_id:
                continue
            if morld.get_unit_prop(uid, "상태:사망"):
                continue
            their_faction = morld.get_unit_prop(uid, "전투:세력")
            is_enemy = _combat.is_faction_hostile(my_faction, their_faction)
            if not is_enemy:
                hostile_to = _combat.is_hostile_to(self.unit_id, uid)
                uid_info = morld.get_unit_info(uid)
                uid_name = uid_info.get("name", "?") if uid_info else "?"
                h = _combat.get_hostility(self.unit_id, uid_name)
                my_info = morld.get_unit_info(self.unit_id)
                my_name = my_info.get("name", "?") if my_info else "?"
                print(f"[DEBUG combat_threat] {my_name}(id={self.unit_id}) vs {uid_name}(id={uid}): faction_hostile=False, hostility={h}, hostile_to={hostile_to}")
                if hostile_to:
                    is_enemy = True
            if is_enemy:
                import survival as _surv
                if _surv.is_npc_fainted(uid):
                    continue
                dist = _combat.get_distance(self.unit_id, uid)
                if dist <= detect_range and dist < enemy_dist:
                    enemy_id = uid
                    enemy_dist = dist

        return enemy_id

    def _should_end_combat(self) -> bool:
        """전투 종료 3-조건 판정 (모두 AND)

        1. 현재 location에 적 없음
        2. 전투 소리 미청취
        3. 마지막 적 목격/소리 + COMBAT_END_COOLDOWN 경과
        """
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return True

        # 조건 1: 현재 location에 적 없음
        if _combat.has_enemies_at_location(self.unit_id, my_loc[0], my_loc[1]):
            self._memory["combat_last_enemy_ms"] = self.get_time()
            return False

        # 조건 2: 전투 소리 미청취
        if _combat.hears_combat_sound(self.unit_id):
            self._memory["combat_last_enemy_ms"] = self.get_time()
            return False

        # 조건 3: 쿨다운 경과
        last_enemy_ms = self._memory.get("combat_last_enemy_ms", 0)
        if self.get_time() - last_enemy_ms < self.COMBAT_END_COOLDOWN:
            return False

        return True

    def _handle_combat(self):
        """BATTLE_BEHAVIOR 기반 전투 행동 (phase machine)

        engaging    → 사거리 밖이면 이동, 안이면 attacking
        attacking   → execute_attack + 대기 job
        retreating  → 안전 지역으로 이동 → regrouping / 포위 시 체념·필사
        regrouping  → 회복 대기 (HP ≥ 75% 또는 전투 종료 시 해제)
        resignation → 체념 (반격·이동 불가, 적 전멸 시 정비 전환)
        desperate   → 필사의 저항 (도주 불가, 적 전멸 시 정비 전환)
        """
        import combat as _combat
        import survival as _surv

        phase = self._memory.get("combat_phase")
        target_id = self._memory.get("combat_target_id")
        behavior = getattr(self, 'BATTLE_BEHAVIOR', {})

        # engaging/attacking: 대상 유효성 검증 (같은 location)
        if phase in ("engaging", "attacking"):
            if target_id is None or not self._is_valid_combat_target(target_id):
                if self._should_end_combat():
                    self._log_combat_phase("전투 종료 (대상 이탈 + 3-조건)")
                    self._end_combat()
                    self._insert_idle_job("전투 종료", 2_000)
                else:
                    self._insert_idle_job("경계", 5_000)
                self._action_taken = True
                return

        # HP 기반 후퇴 판정 (engaging/attacking에서만)
        if phase in ("engaging", "attacking"):
            style = behavior.get("combat_style", "aggressive")
            threshold = behavior.get("retreat_threshold", 0.2)
            my_hp = _surv.get_health(self.unit_id)
            my_max = _surv.get_max_health(self.unit_id)
            if my_hp <= my_max * threshold and style != "aggressive":
                _combat._emit_combat_line(self.unit_id, "flee")
                phase = "retreating"
                self._memory["combat_phase"] = phase
                self._log_combat_phase("HP 기반 후퇴")

        if phase == "engaging":
            if _combat.is_in_range(self.unit_id, target_id):
                self._memory["combat_phase"] = "attacking"
                self._log_combat_phase("사거리 진입 → attacking")
                self._handle_combat()
                return
            target_loc = morld.get_unit_location(target_id)
            if target_loc:
                target_info = self._make_location_target(
                    target_loc[0], target_loc[1])
                if target_info:
                    self._move_to(target_info, "교전")
                    self._action_taken = True
                else:
                    self._end_combat()
                    self._insert_idle_job("대상 이탈", 2_000)
                    self._action_taken = True
            else:
                self._end_combat()
                self._insert_idle_job("대상 이탈", 2_000)
                self._action_taken = True

        elif phase == "attacking":
            self._memory["combat_last_enemy_ms"] = self.get_time()
            result = _combat.execute_attack(self.unit_id, target_id)
            if result.get("message"):
                morld.add_action_log(result["message"])
            if result.get("target_fainted"):
                if self._should_end_combat():
                    self._log_combat_phase("전투 승리 (3-조건 충족)")
                    self._end_combat()
                    self._insert_idle_job("전투 승리", 3_000)
                else:
                    self._insert_idle_job("경계", 5_000)
            else:
                speed = _combat.get_combat_stat(
                    self.unit_id, "전투:공격속도") or 1.0
                duration = int(self.COMBAT_ATTACK_DURATION / speed)
                self._insert_idle_job("공격", max(1_000, duration))
            self._action_taken = True

        elif phase == "retreating":
            flee_target = self._memory.get("combat_flee_target")
            if flee_target is None:
                flee_target = self._pick_safe_location()
                if flee_target:
                    self._memory["combat_flee_target"] = flee_target
                    self._log_combat_phase(
                        f"도주 목적지 결정: R{flee_target['region_id']}L{flee_target['location_id']}")
                else:
                    # 안전 구역 없음 → 포위 판정
                    surrounded = self._is_surrounded()
                    if surrounded:
                        self._resolve_surrounded()
                    else:
                        # 포위는 아니지만 안전 구역 없음 → 강제 전투
                        self._log_combat_phase("안전 구역 없음 → 강제 전투")
                        self._memory["combat_phase"] = "attacking"
                        self._handle_combat()
                    return

            my_loc = self.get_location()
            if my_loc and (my_loc[0] == flee_target["region_id"]
                           and my_loc[1] == flee_target["location_id"]):
                # 도착했는데 적이 있으면 포위 판정
                if _combat.has_enemies_at_location(
                        self.unit_id, my_loc[0], my_loc[1]):
                    self._memory["combat_last_enemy_ms"] = self.get_time()
                    if self._is_surrounded():
                        self._memory.pop("combat_flee_target", None)
                        self._resolve_surrounded()
                        return
                    else:
                        # 다른 안전 구역 재탐색
                        self._memory.pop("combat_flee_target", None)
                        self._log_combat_phase("도착지에 적 → 재탐색")
                        self._insert_idle_job("후퇴", 2_000)
                        self._action_taken = True
                        return
                # 안전 도착 → regrouping
                self._memory["combat_phase"] = "regrouping"
                self._memory["combat_regroup_phase"] = "recovering"
                self._memory.pop("combat_flee_target", None)
                self._log_combat_phase("안전 구역 도착 → 정비")
                self._handle_combat()
                return

            self._move_to(flee_target, "후퇴")
            self._action_taken = True

        elif phase == "regrouping":
            my_hp = _surv.get_health(self.unit_id)
            my_max = _surv.get_max_health(self.unit_id)
            if my_hp >= my_max * self.COMBAT_REGROUP_HP_THRESHOLD:
                self._log_combat_phase("정비 완료 (HP 회복)")
                self._end_combat()
                self._insert_idle_job("정비 완료", 2_000)
                self._action_taken = True
                return
            self._insert_idle_job("정비", 30_000)
            self._action_taken = True

        elif phase == "resignation":
            # 체념: 아무것도 하지 않음 (적 전멸 판정은 _check_combat_threat에서)
            self._insert_idle_job("체념", 10_000)
            self._action_taken = True

        elif phase == "desperate":
            # 필사의 저항: 적에게 공격
            if target_id is None or not self._is_valid_combat_target(target_id):
                # 대상 소실 → 새 적 탐색 (전멸 판정은 _check_combat_threat에서)
                new_enemy = self._scan_nearest_enemy()
                if new_enemy is not None:
                    self._memory["combat_target_id"] = new_enemy
                    target_id = new_enemy
                else:
                    self._insert_idle_job("경계", 5_000)
                    self._action_taken = True
                    return
            self._memory["combat_last_enemy_ms"] = self.get_time()
            result = _combat.execute_attack(self.unit_id, target_id)
            if result.get("message"):
                morld.add_action_log(result["message"])
            speed = _combat.get_combat_stat(
                self.unit_id, "전투:공격속도") or 1.0
            duration = int(self.COMBAT_ATTACK_DURATION / speed)
            self._insert_idle_job("필사", max(1_000, duration))
            self._action_taken = True

        else:
            self._end_combat()
            self._insert_idle_job("전투 종료", 2_000)
            self._action_taken = True

    def _is_valid_combat_target(self, target_id) -> bool:
        """전투 대상이 유효한지 (같은 location + 생존)"""
        import survival as _surv
        info = morld.get_unit_info(target_id)
        if not info:
            return False
        if morld.get_unit_prop(target_id, "상태:사망"):
            return False
        if _surv.is_npc_fainted(target_id):
            return False
        my_loc = morld.get_unit_location(self.unit_id)
        target_loc = morld.get_unit_location(target_id)
        if not my_loc or not target_loc:
            return False
        if my_loc[0] != target_loc[0] or my_loc[1] != target_loc[1]:
            return False
        return True

    def _make_location_target(self, region_id, location_id):
        """(region_id, location_id)를 _move_to용 dict로 변환"""
        region_info = morld.get_region_info(region_id)
        if not region_info:
            return None
        for loc in region_info.get("locations", []):
            if loc["id"] == location_id:
                return {
                    "region_id": region_id,
                    "location_id": location_id,
                    "length": loc.get("length", 0),
                }
        return None

    def _pick_safe_location(self):
        """안전한 도주 location 선택 (1~2 hop, 전투 소리 방향 제외)"""
        import combat as _combat

        my_loc = self.get_location()
        if not my_loc:
            return None

        # 전투 소리가 들리는 location (제외 대상)
        danger_locs = _combat.get_combat_sound_locations(self.unit_id)

        home_region = self._get_home_region()
        region_info = morld.get_region_info(home_region)
        if not region_info or "locations" not in region_info:
            return None

        # Gate 인접 정보로 1-hop 후보 수집
        loc_map = {}
        for loc in region_info["locations"]:
            loc_map[loc["id"]] = loc

        cur_loc_info = loc_map.get(my_loc[1])
        if not cur_loc_info:
            return None

        # 1-hop: 현재 location의 gate 연결
        hop1_ids = set()
        for gate in cur_loc_info.get("gates", []):
            cr = gate.get("connected_region", home_region)
            cl = gate.get("connected_local")
            if cl is not None and cr == home_region:
                if (cr, cl) not in danger_locs:
                    hop1_ids.add(cl)

        # 2-hop: 1-hop location의 gate 연결
        hop2_ids = set()
        for lid in hop1_ids:
            li = loc_map.get(lid)
            if not li:
                continue
            for gate in li.get("gates", []):
                cr = gate.get("connected_region", home_region)
                cl = gate.get("connected_local")
                if cl is not None and cr == home_region:
                    if cl != my_loc[1] and (cr, cl) not in danger_locs:
                        hop2_ids.add(cl)

        # 현재 위치 제외
        hop1_ids.discard(my_loc[1])
        hop2_ids.discard(my_loc[1])
        hop2_ids -= hop1_ids  # 중복 제거

        # 1-hop 우선, 없으면 2-hop
        candidates = list(hop1_ids) or list(hop2_ids)
        if not candidates:
            # 위험 지역 포함해서라도 도망
            candidates = [
                loc["id"] for loc in region_info["locations"]
                if loc["id"] != my_loc[1]
            ]

        if not candidates:
            return None

        target_lid = random.choice(candidates)
        target_loc_info = loc_map.get(target_lid, {})
        return {
            "region_id": home_region,
            "location_id": target_lid,
            "length": target_loc_info.get("length", 0),
        }

    def _end_combat(self):
        """전투 상태 초기화"""
        self._log_combat_phase("전투 상태 초기화")
        self._memory["combat_phase"] = None
        self._memory["combat_target_id"] = None
        self._memory["combat_discovered"] = False
        self._memory.pop("combat_flee_target", None)
        self._memory.pop("combat_regroup_phase", None)
        self._memory.pop("combat_last_enemy_ms", None)

    def _is_surrounded(self) -> bool:
        """포위 판정: 현재 location에 적 존재 + 인접 모든 location에 적 기척

        포위 = (현재 위치에 적) AND (인접 전부에 전투 소리)
        """
        import combat as _combat

        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return False

        # 조건 1: 현재 location에 적 존재
        if not _combat.has_enemies_at_location(
                self.unit_id, my_loc[0], my_loc[1]):
            return False

        # 조건 2: 인접 모든 location에 전투 소리
        danger_locs = _combat.get_combat_sound_locations(self.unit_id)
        home_region = self._get_home_region()
        region_info = morld.get_region_info(home_region)
        if not region_info:
            return True  # 정보 없으면 포위로 간주

        # 현재 location의 인접 gate 목록
        cur_loc_info = None
        for loc in region_info.get("locations", []):
            if loc["id"] == my_loc[1]:
                cur_loc_info = loc
                break
        if not cur_loc_info:
            return True

        adjacent_ids = set()
        for gate in cur_loc_info.get("gates", []):
            cr = gate.get("connected_region", home_region)
            cl = gate.get("connected_local")
            if cl is not None:
                adjacent_ids.add((cr, cl))

        if not adjacent_ids:
            return True  # 인접 location 없음 = 막다른 곳

        # 모든 인접 location에 전투 소리가 들리는지
        for adj in adjacent_ids:
            if adj not in danger_locs:
                return False  # 하나라도 안전하면 포위 아님

        return True

    def _resolve_surrounded(self):
        """포위 시 체념/필사 결정"""
        if random.random() < self.COMBAT_DESPERATE_CHANCE:
            self._memory["combat_phase"] = "desperate"
            self._log_combat_phase("포위 → 필사의 저항")
        else:
            self._memory["combat_phase"] = "resignation"
            self._log_combat_phase("포위 → 체념")
        self._handle_combat()

    def _log_combat_phase(self, detail):
        """전투 페이즈 디버그 로그"""
        info = morld.get_unit_info(self.unit_id)
        name = info.get("name", "?") if info else "?"
        phase = self._memory.get("combat_phase", "None")
        print(f"[combat_phase] {name}(id={self.unit_id}) "
              f"phase={phase} | {detail}")

    # ========================================
    # 결박된 동료 발견 + 해제 (Tier 2)
    # ========================================

    RESCUE_DURATION = 3 * 60 * 1000  # 해제 소요 3분

    def _check_restrained_nearby(self):
        """같은 location에 결박된 비적대 유닛 발견 시 해제 시도

        Returns:
            True if action was taken (해제 진행/완료).
        """
        import restraint

        phase = self._memory.get("rescue_phase")
        if phase is None:
            # 탐색: 같은 location에 결박된 유닛 있는지
            my_loc = morld.get_unit_location(self.unit_id)
            if not my_loc:
                return False
            restrained = restraint.get_restrained_units_at(my_loc[0], my_loc[1])
            target = None
            for uid in restrained:
                if uid != self.unit_id:
                    target = uid
                    break
            if not target:
                return False
            self._memory["rescue_phase"] = "releasing"
            self._memory["rescue_target"] = target
            self._insert_idle_job("구출", self.RESCUE_DURATION)
            self._action_taken = True
            return True

        if phase == "releasing":
            target = self._memory.get("rescue_target")
            if target and restraint.is_restrained(target):
                restraint.release_unit(target)
                # 구출 대상의 restrained 메모리 정리
                from think import _agents
                target_agent = _agents.get(target)
                if target_agent:
                    target_agent._memory["restrained_phase"] = None
                    target_agent._memory.pop("restrained_wait_until", None)
            self._memory.pop("rescue_phase", None)
            self._memory.pop("rescue_target", None)
            self._insert_idle_job("구출 완료", 1 * 60 * 1000)
            self._action_taken = True
            return True

        return False

    # ========================================
    # 탈진자 간호 (Tier 2)
    # ========================================

    _NURSING_REACTIONS = {
        "gentle": ["괜찮아? 좀 쉬어...", "내가 옆에 있을게."],
        "cheerful": ["이런, 무리하면 안 되지!", "금방 나을 거야!"],
        "stoic": ["...쉬어.", "무리하지 마."],
        "timid": ["저, 저기... 괜찮으세요...?", "어, 어떡하지..."],
        "cold": ["...바보.", "쓸데없이 무리해서."],
        "seductive": ["이런 모습도 귀엽네~", "내가 돌봐줄게♡"],
        "fierce": ["뭐야, 벌써 쓰러졌어?", "정신 차려!"],
        "proud": ["...어쩔 수 없지, 간호해주지.", "감사히 여겨."],
        "innocent": ["힘내요! 금방 나을 거예요!", "옆에 있어줄게요!"],
        "devoted": ["주인님, 괜찮으신가요?!", "제가 돌봐드릴게요..."],
    }

    def _check_exhausted_nearby(self):
        """같은 Location에 탈진된 캐릭터 → 간호"""
        import survival as _surv

        # 진행 중 → 계속
        if self._memory.get("nursing_phase") is not None:
            return self._handle_nursing()

        # 쿨다운 (1시간)
        now = self.get_time()
        last = self._memory.get("nursing_cooldown", 0)
        if now - last < 3_600_000:
            return False

        # 같은 Location 탈진자 탐색
        my_loc = morld.get_unit_location(self.unit_id)
        if not my_loc:
            return False
        chars = morld.get_characters_at_location(my_loc[0], my_loc[1])
        target_id = None
        for cid in (chars or []):
            if cid == self.unit_id:
                continue
            if morld.get_unit_prop(cid, "상태:사망"):
                continue
            if _surv.is_npc_exhausted(cid):
                target_id = cid
                break

        if target_id is None:
            return False

        self._memory["nursing_phase"] = "nursing"
        self._memory["nursing_target"] = target_id
        return self._handle_nursing()

    def _handle_nursing(self):
        """간호 실행 — 단일 phase"""
        import survival as _surv

        target_id = self._memory.get("nursing_target")
        if target_id is None:
            self._memory["nursing_phase"] = None
            return False

        if not _surv.is_npc_exhausted(target_id):
            # 대상이 이미 회복됨
            self._memory["nursing_phase"] = None
            self._memory["nursing_target"] = None
            self._memory["nursing_cooldown"] = self.get_time()
            return False

        # 간호 대사
        profile = getattr(self, 'REACTION_PROFILE', None) or {}
        archetype = profile.get("archetype", "stoic")
        texts = self._NURSING_REACTIONS.get(archetype,
                                            self._NURSING_REACTIONS["stoic"])
        import random
        reaction = random.choice(texts)
        morld.add_action_log(f"{self.name}: \"{reaction}\"")

        # HP 소폭 회복 (10)
        target_name = (morld.get_unit_info(target_id) or {}).get("name", "누군가")
        hp = morld.get_unit_prop(target_id, "생존:체력") or 0
        max_hp = morld.get_unit_prop(target_id, "생존:최대체력") or 100
        morld.set_unit_prop(target_id, "생존:체력", min(max_hp, hp + 10))

        # 간호 job (30분)
        self._insert_idle_job(f"{target_name} 간호", 30 * 60_000)

        # 완료
        self._memory["nursing_phase"] = None
        self._memory["nursing_target"] = None
        self._memory["nursing_cooldown"] = self.get_time()
        self._action_taken = True
        return True

    # 소리 반응 상수
    SOUND_REACTION_COOLDOWN = 30 * 60 * 1000      # 30분
    SOUND_REACTION_COOLDOWN_MIN = 5 * 60 * 1000   # 최소 5분

    # 아키타입별 기본 소리 반응 프로필
    # investigate: 소리 원천으로 이동, cautious: 이동 (경계), avoid: 무시, ignore: 완전 무시
    _SOUND_REACTION_DEFAULTS = {
        "stoic":    {"전투": "investigate", "사고": "investigate"},
        "gentle":   {"전투": "cautious",    "사고": "investigate"},
        "cheerful": {"전투": "cautious",    "사고": "investigate"},
        "timid":    {"전투": "avoid",       "사고": "cautious"},
        "cold":     {"전투": "investigate", "사고": "investigate"},
    }

    # 서브클래스에서 오버라이드 가능 (dict: category → reaction)
    _sound_reaction_profile = None

    def _check_tier2_reactive(self):
        """Tier 2: 소리 반응 (비명, 전투, 사고)

        소리를 감지하고 아키타입에 따라 반응:
        - scream(비명): 모든 NPC 조사 (sound_type 레벨 오버라이드)
        - 전투/사고: 아키타입별 investigate/cautious/avoid/ignore

        Returns:
            True if action was taken.
        """
        try:
            import sound
        except ImportError:
            return False

        phase = self._memory.get("sound_reaction_phase")

        # --- phase: investigating (이동 완료 → 현장 확인) ---
        if phase == "investigating":
            self._memory.pop("sound_reaction_phase", None)
            self._memory.pop("sound_reaction_target", None)
            self._insert_idle_job("현장 확인", 1 * 60 * 1000)
            self._action_taken = True
            return True

        # --- 쿨다운 체크 ---
        cooldown = self._memory.get("sound_reaction_cooldown", 0)
        now = self.get_time()
        if now < cooldown:
            # 쿨다운 중 — 긴박한 소리 반복 시 쿨다운 단축
            heard_urgent = sound.get_heard_by_category(self.unit_id, "전투")
            if heard_urgent:
                remaining = cooldown - now
                if remaining > self.SOUND_REACTION_COOLDOWN_MIN:
                    new_cooldown = now + max(
                        self.SOUND_REACTION_COOLDOWN_MIN,
                        remaining // 2)
                    self._memory["sound_reaction_cooldown"] = new_cooldown
            return False

        # --- 소리 수집 ---
        heard_combat = sound.get_heard_by_category(self.unit_id, "전투")
        heard_accident = sound.get_heard_by_category(self.unit_id, "사고")
        all_events = heard_combat + heard_accident
        if not all_events:
            return False

        # 같은 location 소리 제외 (시각으로 이미 확인)
        my_loc = self.get_location()
        remote = [e for e in all_events if e.source_location != my_loc]
        if not remote:
            return False

        # 가장 강한 이벤트
        strongest = max(remote, key=lambda e: e.intensity)

        # 같은 소스에 이미 반응했으면 무시
        prev_source = self._memory.get("sound_reaction_source_id")
        if prev_source == strongest.source_id:
            return False

        # --- 반응 결정 ---
        # scream(비명)은 모든 NPC가 조사 (sound_type 레벨 오버라이드)
        if strongest.sound_type == "scream":
            reaction = "investigate"
        else:
            reaction = self._get_sound_reaction(strongest.category)

        if reaction in ("ignore", "avoid"):
            # 쿨다운 설정 + 소스 기록
            self._memory["sound_reaction_cooldown"] = (
                now + self.SOUND_REACTION_COOLDOWN)
            self._memory["sound_reaction_source_id"] = strongest.source_id
            return False

        # investigate / cautious → 소리 원천으로 이동
        target = {
            "region_id": strongest.source_location[0],
            "location_id": strongest.source_location[1],
        }
        self._memory["sound_reaction_phase"] = "investigating"
        self._memory["sound_reaction_target"] = strongest.source_location
        self._memory["sound_reaction_source_id"] = strongest.source_id
        self._memory["sound_reaction_cooldown"] = (
            now + self.SOUND_REACTION_COOLDOWN)

        self._move_to(target, "소리 조사")
        return True

    def _get_sound_reaction(self, category):
        """아키타입 기반 소리 반응 결정

        Args:
            category: 소리 카테고리 ("전투", "사고" 등)

        Returns:
            "investigate" / "cautious" / "avoid" / "ignore"
        """
        # 서브클래스 오버라이드 우선
        if self._sound_reaction_profile:
            return self._sound_reaction_profile.get(category, "ignore")
        # 아키타입에서 조회
        archetype = "stoic"
        try:
            profile = self.REACTION_PROFILE
            archetype = profile.get("archetype", "stoic")
        except AttributeError:
            pass
        defaults = self._SOUND_REACTION_DEFAULTS.get(archetype, {})
        return defaults.get(category, "ignore")

    def _check_tier3_survival(self):
        """Tier 3: 생존 욕구 (배고픔, 추위, 더위, HP 회복)

        스케줄보다 우선하는 긴급 욕구.
        기존 _check_hunger/_check_cold/_check_hot 그대로 호출.

        Returns:
            True if action was taken.
        """
        if self._check_hunger():
            return True
        if self._check_cold():
            return True
        if self._check_hot():
            return True
        if self._check_hp_recovery():
            return True
        return False

    def _check_hp_recovery(self) -> bool:
        """HP < 50% → 음식 섭취로 HP 회복 (multi-phase)"""
        import survival
        hp = survival.get_health(self.unit_id)
        max_hp = survival.get_max_health(self.unit_id)
        if hp <= 0 or max_hp <= 0 or hp >= max_hp * 0.5:
            # HP 충분하면 진행 중인 phase도 정리
            if self._memory.get("hp_recovery_phase"):
                self._memory["hp_recovery_phase"] = None
                self._memory.pop("hp_recovery_target", None)
            return False
        return self._handle_hp_recovery()

    def _handle_hp_recovery(self) -> bool:
        """HP 회복을 위한 음식 섭취 (multi-phase, _handle_eat 패턴)"""
        import survival
        from think.activities.helpers import (
            find_npc_food, find_food_in_container, resolve_storage_container,
        )
        phase = self._memory.get("hp_recovery_phase")

        # Phase 1: idle — 인벤토리 체크 → storage 탐색
        if phase is None or phase == "idle":
            food = find_npc_food(self.unit_id)
            if food:
                # 이미 소지 중 → 바로 섭취
                hp_recover = max(5, food["satiety"] // 2)
                survival.add_health(self.unit_id, hp_recover)
                survival.npc_eat(self.unit_id, food["satiety"])
                morld.remove_item(self.unit_id, food["item_id"], 1)
                self._do_instant_action("응급 식사", "eat")
                self._memory["hp_recovery_phase"] = None
                return True
            # storage 탐색
            storage = resolve_storage_container(self, "food")
            if not storage:
                storage = resolve_storage_container(self, "food_ingredient")
            if not storage:
                self._memory["hp_recovery_phase"] = None
                return False
            self._memory["hp_recovery_phase"] = "going"
            self._memory["hp_recovery_target"] = storage
            self._move_to(storage, "응급 식사")
            return True

        # Phase 2: going → 도착 시 음식 꺼내기
        if phase == "going":
            target = self._memory.get("hp_recovery_target")
            if target and not self._is_at(target):
                self._move_to(target, "응급 식사")
                return True
            # 도착 — 컨테이너에서 음식 꺼내기
            container_id = target.get("object_id") if target else None
            if container_id:
                food_uid = find_food_in_container(container_id)
                if food_uid:
                    from assets.objects import get_instance
                    obj = get_instance(container_id)
                    if obj and hasattr(obj, 'npc_take_item'):
                        obj.npc_take_item(self.unit_id, food_uid, 1)
            self._memory["hp_recovery_phase"] = "eating"
            self._do_instant_action("음식 꺼내기", "take_item")
            return True

        # Phase 3: eating → 섭취
        if phase == "eating":
            food = find_npc_food(self.unit_id)
            if food:
                hp_recover = max(5, food["satiety"] // 2)
                survival.add_health(self.unit_id, hp_recover)
                survival.npc_eat(self.unit_id, food["satiety"])
                morld.remove_item(self.unit_id, food["item_id"], 1)
            self._do_instant_action("응급 식사", "eat")
            self._memory["hp_recovery_phase"] = None
            self._memory.pop("hp_recovery_target", None)
            return True

        # unknown phase → reset
        self._memory["hp_recovery_phase"] = None
        return False

    def _check_tier4_comfort(self):
        """Tier 4: 쾌적 욕구 (착의, 배변, 피로, 목욕/청결, 취침 이동)

        생존보다 낮은 우선순위.
        착의: 상의/하의 미착용 → _handle_clothing()
        배변: needs 임계치 → _handle_excretion()
        피로: needs 임계치 → _handle_sleep() (비스케줄)
        목욕: 스케줄 OR 청결 임계치 → _handle_bath()
        취침: 스케줄 → _handle_sleep()

        Returns:
            True if action was taken.
        """
        # 4a-pre. 임시노출 정리 (옷매무새)
        if self._check_exposure_recovery():
            return True

        # 4a. 착의 인터럽트
        if self._check_clothing():
            return True

        # 4b. 배변 인터럽트
        if self._check_excretion():
            return True

        # 4c. 피로 인터럽트 (비스케줄 수면)
        if self._check_fatigue():
            return True

        # 4d. 성욕 (플레이어 탐색 → 자위)
        if self._check_arousal():
            return True

        # 4e. 목욕 (스케줄 OR 청결 기반)
        is_bath, _ = self._is_bath_time()
        is_dirty = False
        is_semen_dirty = False
        try:
            import needs
            is_dirty = needs.is_npc_need_bath(self.unit_id)
        except ImportError:
            pass
        try:
            import romance
            is_semen_dirty = romance.get_semen_total(self.unit_id) > 20
        except ImportError:
            pass
        if is_bath or is_dirty or is_semen_dirty:
            self._handle_bath()
            self._action_taken = True
            return True

        # 4e-2. 빨래 (의류 오염도 기반)
        if self._check_laundry():
            return True

        # 4f. 출산 인터럽트 (임신 40주+)
        if self._check_childbirth():
            return True

        # 4g. 모성 인터럽트 (아이 탐색)
        if self._check_maternal():
            return True

        # 4h. 사회욕 (NPC-NPC 대화)
        if self._check_social():
            return True

        # 4h-2. NPC→NPC 선물
        if self._check_gift():
            return True

        # 4i. 취침 이동 (수면 시간이지만 아직 침대 아님)
        # (이미 침대에 누운 경우는 tier 1에서 처리됨)
        is_sleep, _ = self._is_sleep_time()
        if is_sleep:
            self._handle_sleep()
            self._action_taken = True
            return True

        return False

    def _check_excretion(self):
        """배변욕 확인 → 화장실 이동. Returns True if handling."""
        # 이미 진행 중이면 계속
        if self._memory["excretion_phase"] is not None:
            _handle_excretion(self)
            return True

        try:
            import needs
            if not needs.is_npc_need_excretion(self.unit_id):
                return False
        except ImportError:
            return False

        # 화장실 탐색
        from think.facility_resolver import resolve_toilet
        toilet = resolve_toilet(self)
        if not toilet:
            return False

        self._memory["excretion_phase"] = "idle"
        self._memory["excretion_target"] = toilet
        _handle_excretion(self)
        return True

    def _check_fatigue(self):
        """피로로 인한 수면. Returns True if handling.

        스케줄 수면 시간이면 skip (4d에서 처리).
        피로 임계치 초과 시 비스케줄 수면 시작.
        """
        is_sleep, _ = self._is_sleep_time()
        if is_sleep:
            return False  # 스케줄 수면은 4d에서 처리

        try:
            import needs
            if not needs.is_npc_need_sleep(self.unit_id):
                return False
        except ImportError:
            return False

        # 피로로 인한 비스케줄 수면 → _handle_sleep 재사용
        # (fallback duration 2시간이 적용됨)
        self._handle_sleep()
        self._action_taken = True
        return True

    def _check_arousal(self):
        """성욕 처리: 플레이어 탐색 / NPC-NPC 성행위 / 자위. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory["seek_player_phase"] is not None:
            _handle_seek_player(self)
            return True
        if self._memory.get("npc_intimacy_phase") is not None:
            _handle_npc_intimacy(self)
            return True
        if self._memory["self_comfort_phase"] is not None:
            _handle_self_comfort(self)
            return True

        # 쿨다운
        last = self._memory.get("self_comfort_cooldown")
        if last is not None and self.get_time() - last < _SELF_COMFORT_COOLDOWN_MS:
            return False

        # 임계치
        threshold = getattr(self, 'self_comfort_threshold', 80)
        arousal = morld.get_unit_prop(self.unit_id, "상태:성욕") or 0
        if arousal < threshold:
            return False

        # 0순위: 플레이어 탐색 (단둘 → NPC 주도 로맨스)
        can_seek, target = self._can_seek_player()
        if can_seek:
            self._memory["seek_player_phase"] = "idle"
            self._memory["seek_player_target"] = target
            _handle_seek_player(self)
            return True

        # 0.5순위: NPC-NPC 성행위 (합의: 양방향 호감+성욕 / 강제: 단방향+power 우위)
        npc_int_last = self._memory.get("npc_intimacy_cooldown")
        if npc_int_last is None or self.get_time() - npc_int_last >= _NPC_INTIMACY_COOLDOWN_MS:
            partner, mode = _find_npc_lover(self)
            if partner is not None:
                self._memory["npc_intimacy_phase"] = "idle"
                self._memory["npc_intimacy_partner"] = partner
                self._memory["npc_intimacy_mode"] = mode
                _handle_npc_intimacy(self)
                return True

        # 1순위: 유혹 (다른 NPC 있을 때 → 자발적 노출) + NPC→플레이어 성추행
        if self._try_self_exposure():
            return True
        if self._try_harass_player():
            return True

        # 2순위: 자위
        private = _resolve_private_location(self)
        if private is not None:
            self._memory["self_comfort_phase"] = "idle"
            _handle_self_comfort(self)
            return True

        return False

    _SELF_EXPOSURE_COOLDOWN_MS = 3_600_000   # 유혹 쿨다운 1시간
    _SELF_EXPOSURE_CHANCE = 0.5              # 유혹 확률 50%
    _SELF_EXPOSURE_AROUSAL_RELIEF = 10       # 유혹 후 성욕 감소량

    def _try_self_exposure(self):
        """높은 성욕 + 호감 + 다른 NPC 있을 때 → 자발적 옷 들추기 (유혹)"""
        import settings
        if not settings.is_harassment_enabled():
            return False
        player_id = morld.get_player_id()
        if player_id is None or player_id < 0:
            return False
        # 같은 location 확인
        my_loc = morld.get_unit_location(self.unit_id)
        pl_loc = morld.get_unit_location(player_id)
        if not my_loc or not pl_loc or my_loc[:2] != pl_loc[:2]:
            return False
        # 쿨다운
        now = self.get_time()
        last = self._memory.get("self_exposure_cooldown", 0)
        if now - last < self._SELF_EXPOSURE_COOLDOWN_MS:
            return False
        # 다른 NPC가 있을 때만 유혹 (단둘이면 NPC 주도 로맨스가 우선)
        chars = morld.get_characters_at_location(my_loc[0], my_loc[1])
        others = [c for c in (chars or [])
                  if c != self.unit_id and c != player_id]
        if not others:
            return False  # 단둘 → 유혹 대신 플레이어 탐색/성추행 경로
        # 호감 임계치 (INITIATIVE_CONFIG 재활용)
        config = getattr(self, 'INITIATIVE_CONFIG', None)
        if not config:
            return False
        player_name = (morld.get_unit_info(player_id) or {}).get("name", "")
        affection = morld.get_unit_prop(self.unit_id,
                                        f"관계:{player_name}:호감") or 0
        if affection < config.get("affection_threshold", 60):
            return False
        # 이미 노출 상태면 skip
        if (morld.get_unit_prop(self.unit_id, "임시노출:상체") or 0) > 0:
            return False
        if (morld.get_unit_prop(self.unit_id, "임시노출:하체") or 0) > 0:
            return False
        # 확률 판정
        import random
        if random.random() > self._SELF_EXPOSURE_CHANCE:
            self._memory["self_exposure_cooldown"] = now
            return False
        # 자발적 노출 설정 (상체 or 하체 랜덤)
        part = random.choice(["상체", "하체"])
        morld.set_unit_prop(self.unit_id, f"임시노출:{part}", 2)
        morld.set_unit_prop(self.unit_id, "상태:자발적노출", 1)
        # 성욕 감소 (유혹 행위로 약간의 성적 만족감)
        morld.modify_prop(self.unit_id, "상태:성욕",
                          -self._SELF_EXPOSURE_AROUSAL_RELIEF)
        self._memory["self_exposure_cooldown"] = now
        self._do_instant_action("유혹", "seduce")
        return True

    def _try_harass_player(self):
        """NPC가 자발적으로 플레이어를 성추행 (호감 높을 때)"""
        import settings
        if not settings.is_harassment_enabled():
            return False
        player_id = morld.get_player_id()
        if player_id is None or player_id < 0:
            return False
        # 같은 location 확인
        my_loc = morld.get_unit_location(self.unit_id)
        pl_loc = morld.get_unit_location(player_id)
        if not my_loc or not pl_loc or my_loc[:2] != pl_loc[:2]:
            return False
        # 호감 임계치 (환영 모드에서만)
        player_name = (morld.get_unit_info(player_id) or {}).get("name", "")
        affection = morld.get_unit_prop(self.unit_id,
                                        f"관계:{player_name}:호감") or 0
        if affection < 60:
            return False
        # 쿨다운 (2시간)
        now = self.get_time()
        last = self._memory.get("harass_player_cooldown", 0)
        if now - last < 2 * 3_600_000:
            return False
        # 랜덤 액션 선택
        import harassment
        import random
        available = harassment.get_available_actions(self.unit_id, player_id)
        if not available:
            return False
        action_id = random.choice(available)
        result = harassment.execute_action(self.unit_id, player_id,
                                           action_id, is_combat=False)
        action_name = harassment.HARASSMENT_ACTIONS[action_id]["name"]
        morld.add_action_log(f"{self.name}이(가) 당신에게 {action_name}")
        self._memory["harass_player_cooldown"] = now
        self._do_instant_action("성추행", "harass_player")
        return True

    def _check_childbirth(self):
        """출산 인터럽트: 임신 40주+ 또는 출산 진행 중. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("childbirth_phase") is not None:
            from think.activities.childbirth import handle_childbirth
            handle_childbirth(self, None)
            return True

        try:
            import pregnancy
            week = pregnancy.get_pregnancy_week(self.unit_id)
            if week is not None and week >= 40:
                self._memory["childbirth_phase"] = "idle"
                from think.activities.childbirth import handle_childbirth
                handle_childbirth(self, None)
                return True
        except ImportError:
            pass

        return False

    def _check_maternal(self):
        """모성 인터럽트: 아이가 있고 모성 욕구 임계치 초과. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("maternal_phase") is not None:
            from think.activities.childbirth import handle_maternal
            handle_maternal(self, None)
            return True

        # 아이 없으면 스킵
        child_id = self._memory.get("last_child_id")
        if not child_id:
            return False

        # 모성 욕구 임계치 (60)
        maternal = morld.get_unit_prop(self.unit_id, "욕구:모성") or 0
        if maternal < 60:
            return False

        self._memory["maternal_phase"] = "idle"
        from think.activities.childbirth import handle_maternal
        handle_maternal(self, None)
        return True

    def _check_social(self):
        """그리움 인터럽트: 가장 보고싶은 대상 탐색 → 찾아감. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("socialize_phase") is not None:
            _handle_socialize(self)
            return True

        # 쿨다운 (1시간)
        last = self._memory.get("socialize_cooldown")
        if last is not None and self.get_time() - last < 3_600_000:
            return False

        # 가장 그리운 대상 탐색 (그리움 ≥ 70)
        target_id, _ = _find_most_missed(self)
        if target_id is None:
            return False

        self._memory["socialize_phase"] = "idle"
        self._memory["socialize_target_id"] = target_id
        _handle_socialize(self)
        return True

    def _check_gift(self):
        """NPC→NPC 선물 인터럽트. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("gift_phase") is not None:
            _handle_gift(self)
            return True

        # 쿨다운 (24시간)
        last = self._memory.get("gift_cooldown")
        if last is not None and self.get_time() - last < 86_400_000:
            return False

        # 그리움 80+ 필요
        try:
            import needs
            longing = needs.get_max_longing(self.unit_id)
        except ImportError:
            return False
        if longing < 80:
            return False

        # 인벤토리에 선물 가능 아이템 확인
        gift_item_id = _find_gift_item(self)
        if gift_item_id is None:
            return False

        # 같은 region에서 호감 높은 NPC 탐색
        target_id = _find_gift_target(self)
        if target_id is None:
            return False

        self._memory["gift_phase"] = "idle"
        self._memory["gift_target_id"] = target_id
        self._memory["gift_item_id"] = gift_item_id
        _handle_gift(self)
        return True

    def _check_laundry(self):
        """의류 오염도 확인 → 세탁/건조 처리. Returns True if handling."""
        phase = self._memory["laundry_phase"]

        # 이미 진행 중 — waiting 상태는 False 반환 (NPC 자유)
        if phase == "waiting_wash":
            import laundry
            washer = self._memory["laundry_washer"]
            if washer and laundry.get_machine_state(washer["object_id"]) == 2:
                self._memory["laundry_phase"] = "collecting_wash"
                _handle_laundry(self)
                return True
            return False  # 아직 작동 중 → 다른 활동 허용
        if phase == "waiting_dry":
            import laundry
            dryer = self._memory["laundry_dryer"]
            if dryer and laundry.get_machine_state(dryer["object_id"]) == 2:
                self._memory["laundry_phase"] = "collecting_dry"
                _handle_laundry(self)
                return True
            return False  # 아직 건조 중 → 다른 활동 허용
        if phase is not None:
            _handle_laundry(self)
            return True

        # 쿨다운 체크 (3시간)
        cd = self._memory.get("laundry_cooldown")
        if cd is not None:
            elapsed = (self.get_time() or 0) - cd
            if elapsed < 3 * 3_600_000:
                return False

        # 오염된 착용 의류 체크
        dirty_items = _find_dirty_equipped_clothing(self.unit_id)
        if not dirty_items:
            return False

        # 세탁기 탐색
        from think.facility_resolver import resolve_washer
        washer = resolve_washer(self)
        if not washer:
            return False

        self._memory["laundry_phase"] = "going_to_washer"
        self._memory["laundry_washer"] = washer
        self._memory["laundry_items"] = dirty_items
        _handle_laundry(self)
        return True

    def _can_seek_player(self):
        """플레이어 탐색 가능 여부 (INITIATIVE_CONFIG 조건 재사용)"""
        if not self.INITIATIVE_CONFIG:
            return False, None

        # initiative 쿨다운
        props = morld.get_unit_props(self.unit_id)
        if props:
            last = props.get("상태:마지막_주도_시각", -99999)
            cd = self.INITIATIVE_CONFIG.get("cooldown_millis", 480 * 60_000)
            if self.get_time() - last < cd:
                return False, None

        player_id = morld.get_player_id()
        if player_id is None:
            return False, None
        player_info = morld.get_unit_info(player_id)
        if not player_info:
            return False, None

        # 호감/욕망 체크
        player_name = player_info.get("name", "주인공")
        affection = props.get(f"관계:{player_name}:호감", 0) if props else 0
        if affection < self.INITIATIVE_CONFIG.get("affection_threshold", 60):
            return False, None
        desire_th = self.INITIATIVE_CONFIG.get("desire_threshold", 0)
        if desire_th > 0:
            desire = props.get(f"관계:{player_name}:욕망", 0) if props else 0
            if desire < desire_th:
                return False, None

        # 같은 region만 (교차 리전 이동 미지원)
        npc_loc = self.get_location()
        if npc_loc and npc_loc[0] != player_info["region_id"]:
            return False, None

        # 이미 같은 location → on_meet이 처리 (seek 불필요)
        if npc_loc and npc_loc[1] == player_info["location_id"]:
            return False, None

        target = {"region_id": player_info["region_id"],
                  "location_id": player_info["location_id"], "x": 0}
        return True, target

    def _check_tier5_routine(self):
        """Tier 5: 일상 (스케줄 기반 활동 디스패치)

        activity 조회 → 변경 감지 → 동적 entry 해석 → 핸들러 디스패치.

        Returns:
            True if action was taken.
        """
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
            self._insert_idle_job("할 일 없음", max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            self._action_taken = True

        return self._action_taken

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
            # # DEBUG
            # npc_name = self.get_info().get("name", self.unit_id)
            # print(f"[DEBUG _resolve_target] {npc_name}: 고정 → "
            #       f"R{result['region_id']}:L{result['location_id']} "
            #       f"activity={entry.get('activity')} "
            #       f"entry_region={entry.get('region_id', 'NONE')}")
            return result

        # 동적 탐색 (캐시)
        if self._activity_target is None:
            home = self._get_home_region()
            from think.activity_resolver import resolve_activity_location
            self._activity_target = resolve_activity_location(
                self.unit_id, entry.get("activity"), home
            )
            # # DEBUG
            # npc_name = self.get_info().get("name", self.unit_id)
            # print(f"[DEBUG _resolve_target] {npc_name}: 동적 → "
            #       f"{self._activity_target} "
            #       f"activity={entry.get('activity')} home_region={home}")
        return self._activity_target

    _home_region_id = None  # lazy cache (bed_owner prop 기반)

    def _get_home_region(self):
        """NPC의 홈 region — 캐릭터/크리처 분기

        캐릭터 (_is_creature=False):
            bed_owner:{owner} prop → 침대의 region_id
            침대 없으면 RuntimeError (설정 버그)

        크리처 (_is_creature=True):
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
            # # DEBUG: 이동 경로 추적
            # npc_name = self.get_info().get("name", self.unit_id)
            # print(f"[DEBUG _move_to] {npc_name}: "
            #       f"R{loc[0]}:L{loc[1]} → R{target['region_id']}:L{target['location_id']} "
            #       f"name='{name}' phase={getattr(self, '_activity_phase', '?')}")

            self._transit_auto_eat()
            # FSM: GateTransitState push (enter에서 prop + job + action_log 처리)
            from think.fsm import GateTransitState
            self._fsm_push(GateTransitState(target, name))
            # _action_taken은 enter()에서 설정됨
        else:
            # 동일 location 이동: 기존 move job 있으면 보존 (매 step 리셋 방지)
            # NOTE: 상위 tier 인터럽트로 목적지가 바뀔 경우, 기존 job의 목적지가
            #       다를 수 있음. 전투 등은 별도 State에서 처리 예정.
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
                self._insert_idle_job(self._get_display_name(entry), max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
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
                self._insert_idle_job(self._get_display_name(entry), max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
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
            self._insert_idle_job(display, max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
            self._action_taken = True
            return

        wander_target = self._activity_state.get("wander_target")
        if wander_target is not None:
            if self._is_at(wander_target):
                # 도착 → 10~30분 체류 후 다음 이동
                self._activity_state.pop("wander_target", None)
                rest = min(random.randint(10, 30) * 60_000, remaining)
                self._insert_idle_job(display, max(rest, 1))  # 랜덤 체류 시간 — ACTION_DURATION 대상 아님
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
                self._insert_idle_job(display, max(remaining, 1))  # 스케줄 잔여 시간 연동 — ACTION_DURATION 대상 아님
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

    def _check_hunger(self):
        """배고픔 확인 → 식사 활동 시작. Returns True if handling hunger."""
        import survival
        if not survival.is_npc_hungry(self.unit_id):
            self._memory["hunger_phase"] = None
            return False
        # 배고프면 식사 핸들러 실행
        if self._memory["hunger_phase"] is None:
            self._memory["hunger_phase"] = "idle"
        _handle_eat(self)
        return True

    # ========================================
    # 추위/더위 인터럽트
    # ========================================

    COLD_COOLDOWN_MILLIS = 3_600_000  # 추위 대응 실패 후 1시간 쿨다운

    def _check_cold(self):
        """추위/젖음 확인 → 방한 활동 시작. Returns True if handling cold."""
        # 이미 진행 중이면 계속
        if self._memory["cold_phase"] is not None:
            _handle_cold(self)
            return True

        import temperature
        import humidity

        insulation = temperature.get_insulation_total(self.unit_id)

        # 조건 1: 체온 낮고 보온 부족
        cold_trigger = temperature.is_cold(self.unit_id) and insulation < 2

        # 조건 2: 비 맞고 방수 부족
        wet_trigger = False
        if humidity.is_raining():
            wetness = humidity.get_unit_wetness(self.unit_id)
            waterproof = temperature._get_equip_prop_total(self.unit_id, "방수")
            if wetness and wetness > 30 and waterproof < 1:
                wet_trigger = True

        if not (cold_trigger or wet_trigger):
            return False

        # 쿨다운 체크
        last_attempt = self._memory.get("cold_last_attempt")
        if last_attempt is not None:
            current_time = morld.get_game_time()
            if current_time - last_attempt < self.COLD_COOLDOWN_MILLIS:
                return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["cold_phase"] = "idle"
        _handle_cold(self)
        return True

    def _check_hot(self):
        """더위 확인 → 보온 의류 벗기. Returns True if handling hot."""
        # 이미 진행 중이면 계속
        if self._memory["hot_phase"] is not None:
            _handle_hot(self)
            return True

        import temperature
        if not temperature.is_hot(self.unit_id):
            return False
        if temperature.get_insulation_total(self.unit_id) <= 0:
            return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["hot_phase"] = "idle"
        _handle_hot(self)
        return True

    def _find_wardrobe_id(self):
        """옷장 오브젝트 ID 반환 (facility_resolver로 탐색)"""
        from think.facility_resolver import resolve_wardrobe
        result = resolve_wardrobe(self)
        return result["object_id"] if result else None

    # ========================================
    # 착의 인터럽트
    # ========================================

    CLOTHING_COOLDOWN_MILLIS = 3_600_000  # 착의 실패 후 1시간 쿨다운

    def _check_exposure_recovery(self):
        """임시노출 → 옷매무새 정리. Returns True if handling."""
        upper = morld.get_unit_prop(self.unit_id, "임시노출:상체") or 0
        lower = morld.get_unit_prop(self.unit_id, "임시노출:하체") or 0
        if not upper and not lower:
            return False
        import restraint
        if not restraint.can_use_hands(self.unit_id):
            return False
        morld.clear_prop(self.unit_id, "임시노출:상체")
        morld.clear_prop(self.unit_id, "임시노출:하체")
        morld.clear_prop(self.unit_id, "상태:자발적노출")
        self._do_instant_action("옷매무새 정리", "fix_clothes")
        return True

    def _check_clothing(self):
        """착의 확인 → 옷장 이동. Returns True if handling."""
        # 이미 진행 중이면 계속
        if self._memory["clothing_phase"] is not None:
            _handle_clothing(self)
            return True

        # 다른 의류 핸들러 활성 중이면 스킵
        if self._memory["cold_phase"] is not None:
            return False
        if self._memory["hot_phase"] is not None:
            return False

        # 이미 착의 상태면 불필요
        if _is_dressed(self.unit_id):
            return False

        # 쿨다운 체크
        last = self._memory.get("clothing_last_attempt")
        if last is not None:
            current_time = morld.get_game_time()
            if current_time - last < self.CLOTHING_COOLDOWN_MILLIS:
                return False

        # 옷장 접근 가능 여부
        from think.facility_resolver import resolve_wardrobe
        if not resolve_wardrobe(self):
            return False

        self._memory["clothing_phase"] = "idle"
        _handle_clothing(self)
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
            return self._check_storage_need("food_ingredient", "food_fish", 3)
        elif condition == "need_logs":
            return self._check_storage_need("material", "log", 5)
        elif condition == "need_food":
            return self._check_storage_need("food_ingredient", None, 10)
        elif condition == "can_cook":
            # 보관소에 재료 2개 이상이면 요리 가능
            return not self._check_storage_need("food_ingredient", None, 2)
        elif condition == "need_supplies":
            return self._check_storage_need("food", None, 5)
        elif condition == "should_clean":
            return self._check_has_pollution()
        elif condition == "need_social":
            try:
                import needs
                return needs.get_max_longing(self.unit_id) >= 50
            except ImportError:
                return False
        elif condition == "need_wood_chip":
            return self._check_storage_need("material", "wood_chip", 8)
        elif condition == "need_fuel":
            return self._check_heat_source_needs_fuel()
        elif condition == "need_fuel_material":
            return (self._check_storage_need("material", "branch", 6) or
                    self._check_storage_need("material", "log", 3))
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
            actual_threshold = prop_threshold if prop_threshold is not None else threshold
            return obj.get_item_count(item_uid) < actual_threshold
        else:
            return obj.get_category_item_count(category) < threshold


# ========================================
# 활동 핸들러 (모듈화 — think/activities/)
# ========================================

from think.activities import ACTIVITY_HANDLERS as _ACTIVITY_HANDLERS
# ========================================
# 인터럽트 핸들러 (think/handlers/ 에서 분리)
# ========================================
from think.handlers import (
    _handle_eat, _handle_excretion,
    _handle_cold, _handle_hot, _handle_clothing, _is_dressed,
    _handle_self_comfort, _handle_seek_player,
    _handle_npc_intimacy, _find_npc_lover,
    _NPC_INTIMACY_COOLDOWN_MS,
    _SELF_COMFORT_COOLDOWN_MS,
    _handle_socialize, _handle_gift,
    _find_most_missed, _find_gift_item, _find_gift_target,
)
from think.handlers.self_comfort import _resolve_private_location
from think.handlers.laundry import _handle_laundry, _find_dirty_equipped_clothing


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


def get_all_agents() -> dict:
    """등록된 모든 Agent 딕셔너리 반환 (unit_id -> Agent)"""
    return dict(_agents)


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
            import traceback
            info = agent.get_info()
            name = info.get("name", str(unit_id)) if info else str(unit_id)
            print(f"[think] EXCEPTION in {name}(id={unit_id}): {e}")
            traceback.print_exc()
            # 예외 발생 시에도 safety net job 보장 (DES 무한루프 방지)
            try:
                agent._insert_idle_job("에러복구", agent._get_action_duration("safety_net"))
            except Exception:
                morld.insert_job(unit_id, {
                    "name": "에러복구",
                    "action": "stay",
                    "duration": 600_000,  # 10분 fallback
                })


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
