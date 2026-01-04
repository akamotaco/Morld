# events/base.py - 이벤트 기본 클래스
#
# 이벤트 타입별 기본 클래스 정의
# 각 이벤트 파일에서 상속받아 사용


class GameEvent:
    """이벤트 기본 클래스"""
    once = False  # True면 일회성 이벤트
    priority = 0  # 높을수록 먼저 처리

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
    """유닛 만남 이벤트"""
    target_unit = None  # unique_id (None이면 모든 유닛)

    def should_trigger(self, unit_ids, **ctx) -> bool:
        if self.target_unit is None:
            return True
        # registry에서 instance_id 조회 후 비교
        from assets import registry
        target_id = registry.get_instance_id(self.target_unit)
        return target_id is not None and target_id in unit_ids
