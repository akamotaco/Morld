# entities/world/base.py - 지형 기본 클래스

import morld
import random
from entities.base import BaseEntity


class Location:
    """장소 정의"""

    def __init__(
        self,
        id: int,
        name: str,
        is_indoor: bool = True,
        stay_duration: int = 0,
        appearance: dict = None
    ):
        self.id = id
        self.name = name
        self.is_indoor = is_indoor
        self.stay_duration = stay_duration
        self.appearance = appearance or {"default": ""}


class Edge:
    """장소 간 연결 정의"""

    def __init__(
        self,
        a: int,
        b: int,
        travel_time: int,
        conditions: dict = None
    ):
        self.a = a
        self.b = b
        self.travel_time = travel_time
        self.conditions = conditions  # 통과 조건 (향후 확장)


class RegionEdge:
    """지역 간 연결 정의"""

    def __init__(
        self,
        location_a: tuple[int, int],  # (region_id, location_id)
        location_b: tuple[int, int],
        travel_time_a_to_b: int = 30,
        travel_time_b_to_a: int = 30
    ):
        self.location_a = location_a
        self.location_b = location_b
        self.travel_time_a_to_b = travel_time_a_to_b
        self.travel_time_b_to_a = travel_time_b_to_a


class BaseRegion(BaseEntity):
    """Region 기본 클래스"""

    ID: int = 0
    NAME: str = ""
    CURRENT_WEATHER: str = "맑음"
    APPEARANCE: dict = {"default": ""}

    # 장소 목록
    LOCATIONS: list[Location] = []

    # 장소 간 연결
    EDGES: list[Edge] = []

    # 날씨 패턴 [(시작시, 종료시, 날씨, 확률), ...]
    WEATHER_PATTERNS: list = []

    def __init__(self):
        self._current_weather = self.CURRENT_WEATHER

    def get_weather(self) -> str:
        """현재 날씨 반환"""
        return self._current_weather

    def set_weather(self, weather: str):
        """날씨 설정"""
        self._current_weather = weather
        morld.set_region_weather(self.ID, weather)

    def update_weather(self, game_time: int):
        """
        시간에 따른 날씨 업데이트

        Args:
            game_time: 현재 시간 (분 단위, 0~1439)
        """
        if not self.WEATHER_PATTERNS:
            return

        hour = game_time // 60

        for start, end, weather, probability in self.WEATHER_PATTERNS:
            if self._in_time_range(hour, start, end):
                if random.random() < probability:
                    if self._current_weather != weather:
                        self.set_weather(weather)
                break

    def _in_time_range(self, hour: int, start: int, end: int) -> bool:
        """시간 범위 체크 (자정 넘김 처리)"""
        if start <= end:
            return start <= hour < end
        else:
            return hour >= start or hour < end

    def register(self):
        """morld에 Region 등록"""
        # Region 등록
        morld.add_region(
            self.ID,
            self.NAME,
            self.APPEARANCE,
            self.CURRENT_WEATHER
        )

        # Location 등록
        for loc in self.LOCATIONS:
            morld.add_location(
                self.ID,
                loc.id,
                loc.name,
                loc.appearance,
                loc.stay_duration,
                loc.is_indoor
            )

        # Edge 등록
        for edge in self.EDGES:
            morld.add_edge(
                self.ID,
                edge.a,
                edge.b,
                edge.travel_time
            )

        print(f"[world] Registered: {self.NAME} (ID: {self.ID}, {len(self.LOCATIONS)} locations)")
