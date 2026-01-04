# entities/characters/base.py - 캐릭터 기본 클래스

import morld
from entities.base import BaseEntity


class BaseCharacter(BaseEntity):
    """모든 캐릭터의 기본 클래스"""

    # === 서브클래스에서 정의 (정적 데이터) ===
    ID: int = 0
    NAME: str = ""
    TYPE: str = "female"
    START_LOCATION: tuple[int, int] = (0, 0)  # (region_id, location_id)

    # 스탯 (태그)
    TAGS: dict = {}

    # 외관 묘사 (appearance)
    APPEARANCE: dict = {
        "default": ""
    }

    # 행동 가능 목록
    ACTIONS: list = []

    # 상황별 presence text
    PRESENCE_TEXT: dict = {
        "default": "{name}가 있다."
    }

    # 대화 데이터
    DIALOGUES: dict = {
        "default": {"pages": ["..."]}
    }

    # 시간대별 스케줄 [(시작시, 종료시, 활동, 위치), ...]
    SCHEDULE: list = []

    # === 인스턴스 상태 ===
    def __init__(self):
        self._state = "idle"  # idle, moving, waiting
        self._target = None   # 이동 목표 (region_id, location_id)
        self._first_met = False

    # === 시스템 통신 (morld API 래핑) ===
    def get_location(self) -> tuple[int, int]:
        """현재 위치 반환"""
        info = morld.get_unit_info(self.ID)
        if info:
            return (info["region_id"], info["location_id"])
        return self.START_LOCATION

    def get_activity(self) -> str:
        """현재 활동 반환"""
        info = morld.get_unit_info(self.ID)
        if info:
            return info.get("activity")
        return None

    def get_tag(self, tag_name: str) -> int:
        """스탯 값 조회"""
        info = morld.get_unit_info(self.ID)
        if info:
            return info.get("tags", {}).get(tag_name, 0)
        return self.TAGS.get(tag_name, 0)

    def set_tag(self, tag_name: str, value: int):
        """스탯 값 설정"""
        morld.set_unit_tag(self.ID, tag_name, value)

    def get_mood(self) -> list[str]:
        """현재 감정 상태"""
        info = morld.get_unit_info(self.ID)
        if info:
            return info.get("mood", [])
        return []

    def set_mood(self, moods: list[str]):
        """감정 상태 설정"""
        morld.set_unit_mood(self.ID, moods)

    def is_moving(self) -> bool:
        """이동 중인지 확인"""
        info = morld.get_unit_info(self.ID)
        if info:
            return info.get("is_moving", False)
        return False

    # === 행동 명령 ===
    def move_to(self, region_id: int, location_id: int) -> bool:
        """
        이동 명령 - 이미 이동 중이면 무시

        Returns:
            True: 이동 시작됨
            False: 이미 목적지에 있거나 같은 목적지로 이동 중
        """
        current = self.get_location()
        target = (region_id, location_id)

        # 이미 목적지에 있음
        if current == target:
            return False

        # 이미 같은 목적지로 이동 중
        if self._state == "moving" and self._target == target:
            return False

        # 이동 명령 실행
        morld.move_unit(self.ID, region_id, location_id)
        self._state = "moving"
        self._target = target
        return True

    def set_activity(self, activity: str):
        """활동 설정 (appearance 매칭용)"""
        morld.set_unit_activity(self.ID, activity)

    def wait(self, duration: int):
        """대기"""
        morld.wait_unit(self.ID, duration)
        self._state = "waiting"

    # === 행동 결정 (서브클래스에서 오버라이드) ===
    def think(self, game_time: int) -> dict:
        """
        매 Step마다 호출 - 다음 행동 결정

        Args:
            game_time: 현재 시간 (분 단위, 0~1439)

        Returns:
            명령 딕셔너리 또는 None
            예: {"action": "move", "target": (0, 1)}
            예: {"action": "wait", "duration": 30}
            예: {"action": "activity", "activity": "식사"}
        """
        return self.decide(game_time)

    def decide(self, game_time: int) -> dict:
        """
        실제 결정 로직 - 서브클래스에서 구현

        기본 구현: SCHEDULE 기반 스케줄 따르기
        """
        if not self.SCHEDULE:
            return None

        hour = game_time // 60
        current_loc = self.get_location()

        # 시간대별 스케줄 확인
        for start, end, activity, location in self.SCHEDULE:
            if self._in_time_range(hour, start, end):
                # 위치가 다르면 이동
                if current_loc != location:
                    if self.move_to(*location):
                        return {"action": "move", "target": location}
                    return None  # 이미 이동 중

                # 활동 설정
                self.set_activity(activity)
                return {"action": "activity", "activity": activity}

        # 스케줄 외 시간
        self.set_activity(None)
        return None

    def _in_time_range(self, hour: int, start: int, end: int) -> bool:
        """시간 범위 체크 (자정 넘김 처리)"""
        if start <= end:
            return start <= hour < end
        else:  # 22시 ~ 6시 같은 경우
            return hour >= start or hour < end

    # === 이벤트 핸들러 (서브클래스에서 오버라이드) ===
    def on_reach(self, location: tuple[int, int]):
        """목적지 도착 시"""
        self._state = "idle"
        self._target = None

        # 현재 시간에 맞는 스케줄 찾아서 activity 설정
        game_time = morld.get_game_time()
        hour = game_time // 60

        for start, end, activity, loc in self.SCHEDULE:
            if self._in_time_range(hour, start, end) and location == loc:
                self.set_activity(activity)
                return

    def on_meet_player(self) -> dict:
        """플레이어와 만났을 때"""
        return None

    def on_talk(self) -> dict:
        """대화 시작 시"""
        activity = self.get_activity()

        # activity 기반 대화
        if activity and activity in self.DIALOGUES:
            return self.DIALOGUES[activity]

        return self.DIALOGUES.get("default")

    # === 유틸리티 ===
    def freeze(self, duration: int):
        """일정 시간 행동 중지 (대기 스케줄 push)"""
        morld.wait_unit(self.ID, duration)
        self._state = "waiting"

    def get_presence_text(self, region_id: int, location_id: int) -> str:
        """현재 상태에 맞는 presence text 반환"""
        activity = self.get_activity()
        moods = self.get_mood()

        # 우선순위 1: activity
        if activity:
            key = f"activity:{activity}"
            if key in self.PRESENCE_TEXT:
                return self.PRESENCE_TEXT[key].format(name=self.NAME)

        # 우선순위 2: 장소
        loc_key = f"{region_id}:{location_id}"
        if loc_key in self.PRESENCE_TEXT:
            return self.PRESENCE_TEXT[loc_key].format(name=self.NAME)

        # 우선순위 3: mood
        for mood in moods:
            key = f"mood:{mood}"
            if key in self.PRESENCE_TEXT:
                return self.PRESENCE_TEXT[key].format(name=self.NAME)

        # 우선순위 4: 기본값
        return self.PRESENCE_TEXT.get("default", "").format(name=self.NAME)

    # === 시스템 등록 ===
    def register(self):
        """morld에 캐릭터 등록"""
        region_id, location_id = self.START_LOCATION
        morld.add_unit(
            self.ID,
            self.NAME,
            region_id,
            location_id,
            self.TYPE,
            self.ACTIONS,
            self.APPEARANCE,
            []  # mood (빈 상태로 시작)
        )
        if self.TAGS:
            morld.set_unit_tags(self.ID, self.TAGS)

        print(f"[characters] Registered: {self.NAME} (ID: {self.ID})")
