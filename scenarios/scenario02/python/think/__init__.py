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
            "romance_last": None,         # 마지막 애정 행위 기억 {partner_id, region_id, location_id, timestamp, mode}
        }

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

    def _check_tier2_reactive(self):
        """Tier 2: 반응형 (위협, 소리) — 미래 확장 포인트

        향후 구현 예정:
        - sound.get_heard_by_category(unit_id, "전투") → 위협 반응
        - 전투/도주 판단
        - 소리에 대한 호기심/경계 반응

        Returns:
            True if action was taken.
        """
        return False

    def _check_tier3_survival(self):
        """Tier 3: 생존 욕구 (배고픔, 추위, 더위)

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
        """성욕 처리: 플레이어 탐색 또는 자위. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory["seek_player_phase"] is not None:
            _handle_seek_player(self)
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

        # 1순위: 플레이어 탐색
        can_seek, target = self._can_seek_player()
        if can_seek:
            self._memory["seek_player_phase"] = "idle"
            self._memory["seek_player_target"] = target
            _handle_seek_player(self)
            return True

        # 2순위: 자위
        private = _resolve_private_location(self)
        if private is not None:
            self._memory["self_comfort_phase"] = "idle"
            _handle_self_comfort(self)
            return True

        return False

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
        """사회욕 인터럽트: 다른 NPC 탐색 → 대화. Returns True if handling."""
        # 진행 중 → 계속
        if self._memory.get("socialize_phase") is not None:
            _handle_socialize(self)
            return True

        # 쿨다운 (1시간)
        last = self._memory.get("socialize_cooldown")
        if last is not None and self.get_time() - last < 3_600_000:
            return False

        # 사회욕 임계치 (70)
        try:
            import needs
            social = needs.get_social(self.unit_id)
        except ImportError:
            return False
        if social < 70:
            return False

        # 대화 대상 탐색 (같은 location의 다른 NPC)
        target_id = _find_socialize_target(self)
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

        # 사회욕 80+ 필요
        try:
            import needs
            social = needs.get_social(self.unit_id)
        except ImportError:
            return False
        if social < 80:
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

        schedule = self.get_current_schedule()
        if schedule:
            # Tier 1: 비자발적 (기절, 수면 중)
            if self._check_tier1_involuntary():
                _tier_reached = 1
            else:
                # Tier 1 통과 → 활동 준비: 앉기/눕기 상태 해제
                self._ensure_standing()

                # Tier 2: 반응형 (미래 확장)
                if self._check_tier2_reactive():
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
                        "socialize_phase", "gift_phase", "childbirth_phase", "maternal_phase"):
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

    _home_region_id = None  # lazy cache (bed_owner prop 기반)

    def _get_home_region(self):
        """NPC의 홈 region (bed_owner prop 기반 침대 탐색, 없으면 현재 위치)"""
        if self._home_region_id is not None:
            return self._home_region_id
        owner = getattr(self, 'owner_unique_id', None)
        if owner:
            from think.facility_resolver import _find_facilities_by_prop
            beds = _find_facilities_by_prop(f"bed_owner:{owner}", 1)
            if beds:
                self._home_region_id = beds[0]["region_id"]
                return self._home_region_id
        loc = self.get_location()
        return loc[0] if loc else 0

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

    def _move_to(self, target, name="이동"):
        """target으로 이동 job 삽입.

        Duration은 C#이 거리/속도 기반으로 동적 계산 (ACTION_DURATION 대상 아님).
        매 호출마다 새 move job을 삽입한다 (InsertJobWithClear가 기존 job 정리).
        이전 step에서 이동 미완료 시에도 새 job으로 갱신되어 정상 동작.
        """
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

    def _do_wander(self, entry):
        """돌아다니기: 랜덤 location 이동 → 10~30분 체류 → 반복

        순찰/산책 공용. home_region 내 랜덤 location을 순회한다.
        남은 시간 5분 미만이면 제자리 대기로 전환.
        """
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
                return needs.get_social(self.unit_id) >= 50
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
    _SELF_COMFORT_COOLDOWN_MS,
    _handle_socialize, _handle_gift,
    _find_socialize_target, _find_gift_item, _find_gift_target,
)
from think.handlers.self_comfort import _resolve_private_location


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
