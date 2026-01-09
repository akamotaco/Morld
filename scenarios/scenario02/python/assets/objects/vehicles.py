# assets/objects/vehicles.py - 탈것 관련 오브젝트
#
# Vehicle 시스템 테스트용 오브젝트 정의
#
# Unit ID 할당:
# - 자전거 (Bicycle): 230
# - 운전석 (CarDriverSeat): 231
# - 조수석 (CarPassengerSeat): 232
# - 트렁크 (CarTrunk): 233

from assets.base import Object


# ========================================
# 자전거 (개방형 탈것 - Object 타입)
# ========================================

class Bicycle(Object):
    """
    자전거 - 뒷마당에 배치

    앞좌석: SittingOn 설정 + driver_seat 효과 (운전 가능)
    뒷좌석: SittingOn 설정만 (탑승만)

    좌석 Prop 시스템:
    - seated_by:front → 앉은 캐릭터 ID (-1이면 빈 좌석)
    - seated_by:rear → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "bicycle"
    name = "자전거"
    actions = [
        "sit@front:앞좌석 앉기",  # driver_seat 효과
        "sit@rear:뒷좌석 앉기",   # 단순 탑승
        "script:debug_props:속성 보기"
    ]
    props = {
        "driver_seat": 1,       # 앞좌석 앉으면 운전 가능
        "seated_by:front": -1,  # 앞좌석 (빈 좌석)
        "seated_by:rear": -1    # 뒷좌석 (빈 좌석)
    }
    focus_text = {"default": "녹이 조금 슬었지만 아직 탈 수 있어 보이는 자전거."}


# ========================================
# 자동차 내부 오브젝트 (밀폐형 탈것의 내부 구성요소)
# ========================================

class CarDriverSeat(Object):
    """
    운전석 - 자동차 Location 내부

    앉으면 운전 가능 (driver_seat Prop)
    - sit@seat:앉기 → 앉으면 운전 메뉴가 나타남
    - script:drive_menu:운전 → 목적지 선택 모놀로그

    좌석 Prop 시스템:
    - seated_by:seat → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "car_driver_seat"
    name = "운전석"
    actions = [
        "sit@seat:앉기",
        "script:drive_menu:운전:운전",  # context_unit_id, display_name
        "script:debug_props:속성 보기"
    ]
    props = {
        "driver_seat": 1,      # 앉으면 운전 가능
        "seated_by:seat": -1   # 좌석 (빈 좌석)
    }
    focus_text = {"default": "낡은 가죽 시트의 운전석. 핸들이 손때가 묻어 있다."}


class CarPassengerSeat(Object):
    """
    조수석 - 자동차 Location 내부

    앉기만 가능, 운전 불가

    좌석 Prop 시스템:
    - seated_by:seat → 앉은 캐릭터 ID (-1이면 빈 좌석)
    """
    unique_id = "car_passenger_seat"
    name = "조수석"
    actions = ["sit@seat:앉기", "script:debug_props:속성 보기"]
    props = {"seated_by:seat": -1}  # 좌석 (빈 좌석)
    focus_text = {"default": "낡은 가죽 시트의 조수석. 편히 앉을 수 있다."}


class CarTrunk(Object):
    """
    트렁크 - 자동차 Location 내부

    인벤토리 보유, 아이템 보관용
    """
    unique_id = "car_trunk"
    name = "트렁크"
    actions = ["script:trunk_look:살펴보기", "script:debug_props:속성 보기"]
    focus_text = {"default": "넓은 트렁크 공간. 물건을 보관할 수 있다."}


# ========================================
# 스크립트 함수
# ========================================

import morld


def trunk_look(context_unit_id):
    """트렁크 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["차 트렁크를 열어보았다.", "물건을 넣거나 꺼낼 수 있겠다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def drive_menu(context_unit_id):
    """
    운전 메뉴 - 목적지 선택

    운전석에 앉아있을 때만 사용 가능.
    morld.can_drive()와 morld.get_drivable_destinations()로 목적지 조회.
    """
    player_id = morld.get_player_id()

    # 운전 가능 여부 확인
    if not morld.can_drive(player_id):
        return {
            "type": "monologue",
            "pages": ["운전석에 앉아야 운전할 수 있다."],
            "time_consumed": 0,
            "button_type": "ok"
        }

    # 목적지 목록 조회
    destinations = morld.get_drivable_destinations(player_id)
    if not destinations:
        return {
            "type": "monologue",
            "pages": ["갈 수 있는 곳이 없다."],
            "time_consumed": 0,
            "button_type": "ok"
        }

    # 목적지 선택 모놀로그 생성
    lines = ["어디로 갈까?\n"]
    for dest in destinations:
        region_id = dest["region_id"]
        location_id = dest["location_id"]
        name = dest["name"]
        travel_time = dest["travel_time"]
        lines.append(f"[url=script:drive_to_destination:{region_id}:{location_id}]{name} ({travel_time}분)[/url]")

    return {
        "type": "monologue",
        "pages": ["\n".join(lines)],
        "time_consumed": 0,
        "button_type": "none"  # 선택지가 있으므로 버튼 없음
    }


def drive_to_destination(context_unit_id, region_id, location_id):
    """
    목적지로 운전

    Args:
        context_unit_id: 컨텍스트 유닛 ID (사용 안함)
        region_id: 목적지 Region ID
        location_id: 목적지 Location ID
    """
    player_id = morld.get_player_id()

    # drive_to API 호출
    result = morld.drive_to(player_id, int(region_id), int(location_id))

    if result["success"]:
        return {
            "type": "monologue",
            "pages": [result["message"]],
            "time_consumed": result["time_consumed"],
            "button_type": "ok"
        }
    else:
        return {
            "type": "monologue",
            "pages": [result["message"]],
            "time_consumed": 0,
            "button_type": "ok"
        }
