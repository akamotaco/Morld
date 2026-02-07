# lighting.py - 조명/밝기 시스템
#
# Location 밝기 계산:
# - 실외: Region 시간대별 밝기 × 날씨 보정
# - 실내: max(창문 밝기, 고정 조명, 휴대 광원)
#
# 밝기 범위: 0.0 (암흑) ~ 1.0 (대낮)

import morld

# ========================================
# 시간대별 기본 밝기 (야외)
# ========================================
#
# | 시간대 | 시간 | 밝기 |
# |--------|------|------|
# | 새벽 | 05:00~07:00 | 0.3 |
# | 아침 | 07:00~09:00 | 0.7 |
# | 낮 | 09:00~17:00 | 1.0 |
# | 저녁 | 17:00~19:00 | 0.7 |
# | 황혼 | 19:00~21:00 | 0.3 |
# | 밤 | 21:00~05:00 | 0.1 |

TIME_BRIGHTNESS = [
    # (start_hour, end_hour, brightness)
    (5, 7, 0.3),    # 새벽
    (7, 9, 0.7),    # 아침
    (9, 17, 1.0),   # 낮
    (17, 19, 0.7),  # 저녁
    (19, 21, 0.3),  # 황혼
]
DEFAULT_NIGHT_BRIGHTNESS = 0.1  # 밤 (21:00~05:00)


# ========================================
# 날씨 보정 계수
# ========================================

WEATHER_MODIFIER = {
    "맑음": 1.0,
    "흐림": 0.7,
    "비": 0.5,
    "눈": 0.5,
    "폭풍": 0.3,
}
DEFAULT_WEATHER_MODIFIER = 1.0


# ========================================
# 조명 오브젝트 밝기 값
# ========================================
#
# light:value prop에서 가져옴
# 기본값은 아래 테이블 참조

LIGHT_DEFAULTS = {
    "형광등": 0.8,
    "전등": 0.5,
    "촛불": 0.3,
    "벽난로": 0.4,
    "랜턴": 0.4,
    "횃불": 0.5,
    "발광석": 0.2,
}


# ========================================
# 밝기 계산 함수
# ========================================

def get_time_brightness() -> float:
    """
    현재 시간대의 기본 밝기 반환 (야외 기준)

    Returns:
        float: 0.0 ~ 1.0
    """
    time_info = morld.get_time_info()
    if not time_info:
        return 1.0  # fallback

    hour = time_info.get("hour", 12)

    # 시간대 검색
    for start, end, brightness in TIME_BRIGHTNESS:
        if start <= hour < end:
            return brightness

    # 밤 (21:00~05:00)
    return DEFAULT_NIGHT_BRIGHTNESS


def get_weather_modifier() -> float:
    """
    현재 날씨의 밝기 보정 계수 반환

    Returns:
        float: 0.0 ~ 1.0
    """
    time_info = morld.get_time_info()
    if not time_info:
        return 1.0

    weather = time_info.get("weather", "맑음")
    return WEATHER_MODIFIER.get(weather, DEFAULT_WEATHER_MODIFIER)


def get_outdoor_brightness() -> float:
    """
    실외 밝기 계산: 시간대 밝기 × 날씨 보정

    Returns:
        float: 0.0 ~ 1.0
    """
    return get_time_brightness() * get_weather_modifier()


def get_location_light_sources(region_id: int, location_id: int) -> list:
    """
    Location 내 조명 오브젝트의 밝기 목록 반환

    창문: Region 밝기 전달
    고정 조명: light:on=1인 경우만

    Args:
        region_id: Region ID
        location_id: Location ID

    Returns:
        list[float]: 밝기 값 목록
    """
    light_sources = []

    # Location 내 오브젝트 조회
    objects = morld.get_objects_at_location(region_id, location_id)
    if objects is None:
        return light_sources

    outdoor_brightness = get_outdoor_brightness()

    for obj_id in objects:
        # 창문: Region 밝기 전달
        if morld.get_unit_prop(obj_id, "light:window") == 1:
            light_sources.append(outdoor_brightness)
            continue

        # 조명: on 상태 확인
        if morld.get_unit_prop(obj_id, "light:on") == 1:
            light_value = morld.get_unit_prop(obj_id, "light:value")
            if light_value is not None and light_value > 0:
                # prop은 정수 (×10 저장): 4 → 0.4, 8 → 0.8
                light_sources.append(light_value / 10.0)

    return light_sources


def get_player_portable_light() -> float:
    """
    플레이어가 켠 휴대 광원의 밝기 반환

    Returns:
        float: 휴대 광원 밝기 (없으면 0.0)
    """
    player_id = morld.get_player_id()
    if player_id is None:
        return 0.0

    # 장착된 아이템 확인
    equipped = morld.get_equipped_items(player_id)
    if equipped is None:
        return 0.0

    for item_id in equipped:
        # 휴대 가능 광원인지 확인
        if morld.get_unit_prop(item_id, "light:portable") != 1:
            continue

        # 켜져 있는지 확인
        if morld.get_unit_prop(item_id, "light:on") != 1:
            continue

        # 밝기 반환
        light_value = morld.get_unit_prop(item_id, "light:value")
        if light_value is not None and light_value > 0:
            return light_value

    return 0.0


def get_location_brightness(region_id: int = None, location_id: int = None) -> float:
    """
    Location의 현재 밝기 계산

    실외: Region 밝기 (시간대 × 날씨)
    실내: max(창문, 조명, 휴대 광원)

    Args:
        region_id: Region ID (None이면 플레이어 위치)
        location_id: Location ID (None이면 플레이어 위치)

    Returns:
        float: 0.0 ~ 1.0
    """
    # 플레이어 위치 사용
    if region_id is None or location_id is None:
        player_id = morld.get_player_id()
        if player_id is None:
            return 1.0

        player_loc = morld.get_unit_location(player_id)
        if player_loc is None:
            return 1.0

        region_id, location_id = player_loc

    # Location 정보 가져오기
    location_info = morld.get_location_info(region_id, location_id)
    if location_info is None:
        return 1.0

    is_indoor = location_info.get("is_indoor", True)

    # 실외: Region 밝기 직접 적용
    if not is_indoor:
        return get_outdoor_brightness()

    # 실내: max(창문, 조명, 휴대 광원)
    light_sources = get_location_light_sources(region_id, location_id)

    # 휴대 광원 추가
    portable_light = get_player_portable_light()
    if portable_light > 0:
        light_sources.append(portable_light)

    # 실내 기본 밝기: 조명이 전혀 없을 때의 밝기 (0.0 = 암흑)
    if light_sources:
        return max(light_sources)
    else:
        return 0.0


def get_brightness_level(brightness: float = None) -> str:
    """
    밝기 수치를 레벨 이름으로 변환 (UI 표시용)

    Args:
        brightness: 밝기 (None이면 현재 위치 밝기)

    Returns:
        str: "밝음", "어두움", "암흑"
    """
    if brightness is None:
        brightness = get_location_brightness()

    if brightness >= 0.6:
        return "밝음"
    elif brightness >= 0.2:
        return "어두움"
    else:
        return "암흑"


# ========================================
# 은신 시스템 연동
# ========================================

def get_detection_brightness() -> float:
    """
    발각 판정용 밝기 반환

    은신 시스템에서 사용:
    detection_rate = 밝기 × 자세계수 × 엄폐계수 × NPC감지력

    Returns:
        float: 0.0 ~ 1.0
    """
    return get_location_brightness()
