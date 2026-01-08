# events/base.py - 이벤트 기본 클래스 (scenario01)
#
# 이벤트 타입별 기본 클래스 정의
# 각 이벤트 파일에서 상속받아 사용


class GameEvent:
    """이벤트 기본 클래스"""
    once = False  # True면 일회성 이벤트
    priority = 0  # 높을수록 먼저 처리
    is_dialog_event = False  # True면 다이얼로그 이벤트 (시간 경과 가능)

    def should_trigger(self, **context) -> bool:
        """트리거 조건 (오버라이드 가능)"""
        return True

    def handle(self, **context):
        """이벤트 처리 (오버라이드 필수)"""
        raise NotImplementedError


class GameStartEvent(GameEvent):
    """게임 시작 이벤트"""
    pass


class ReachEvent(GameEvent):
    """위치 도착 이벤트"""
    region_id = None   # None이면 모든 region
    location_id = None  # None이면 모든 location

    def should_trigger(self, region_id, location_id, **ctx) -> bool:
        if self.region_id is not None and self.region_id != region_id:
            return False
        if self.location_id is not None and self.location_id != location_id:
            return False
        return True


class MeetEvent(GameEvent):
    """유닛 만남 이벤트 (플레이어 포함)"""
    target_unit = None  # unique_id (None이면 모든 유닛)

    def should_trigger(self, unit_ids, **ctx) -> bool:
        if self.target_unit is None:
            return True
        # registry에서 instance_id 조회 후 비교
        from assets import registry
        target_id = registry.get_instance_id(self.target_unit)
        return target_id is not None and target_id in unit_ids


class DialogEvent(MeetEvent):
    """다이얼로그 이벤트 (플레이어와 대화)

    - is_dialog_event = True
    - handle()에서 yield morld.dialog() 사용 가능
    - morld.dialog() 파라미터:
      - text_or_pages: str 또는 list - 필수
      - autofill: "next" (기본), "book", "scroll", "off"
      - proc: @proc:값 클릭 시 호출될 콜백
      - result: @finish 시 반환할 값
    """
    is_dialog_event = True


class NpcMeetEvent(GameEvent):
    """NPC 간 만남 이벤트 (플레이어 미포함)

    - is_dialog_event = False (시간 경과 없음)
    - 플레이어가 없는 상태에서 NPC들끼리 만났을 때
    - handle()에서는 상태 변경만 수행 (morld.set_npc_job 등)
    """
    is_dialog_event = False
    npc_a = None  # unique_id
    npc_b = None  # unique_id

    def should_trigger(self, unit_ids, player_id=None, **ctx) -> bool:
        # 플레이어가 포함되어 있으면 NPC 간 이벤트가 아님
        if player_id is not None and player_id in unit_ids:
            return False

        # npc_a, npc_b가 모두 있는지 확인
        from assets import registry
        a_id = registry.get_instance_id(self.npc_a) if self.npc_a else None
        b_id = registry.get_instance_id(self.npc_b) if self.npc_b else None

        if a_id is None or b_id is None:
            return False

        return a_id in unit_ids and b_id in unit_ids
