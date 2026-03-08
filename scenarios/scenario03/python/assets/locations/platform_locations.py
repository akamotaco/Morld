# assets/locations/platform_locations.py - 플랫폼 Location 클래스들
#
# Region 0: 플랫폼 (베이스캠프)
# - Station: 승강장 (지저철 정차/탑승)
# - PlatformCorridor: 중앙 통로 (이동 허브)
# - CommRoom: 통신실 (플레이어 CRT 시점)

from assets.base import Location


class Station(Location):
    """승강장 — 지저철 정차 위치"""
    unique_id = "station"
    name = "승강장"
    is_indoor = True
    ground_type = "GroundConcrete"
    length = 200
    describe_text = {
        "default": "콘크리트 벽과 녹슨 레일. 형광등 몇 개가 간헐적으로 깜빡인다.",
        "밤": "비상등만이 승강장 끝을 희미하게 비추고 있다.",
    }

    def instantiate(self, location_id, region_id):
        super().instantiate(location_id, region_id)
        # 지저철 정차 위치 — Gate로 연결 (오브젝트 없음)


class PlatformCorridor(Location):
    """중앙 통로 — 이동 허브, 건축 분기점"""
    unique_id = "platform_corridor"
    name = "중앙 통로"
    is_indoor = True
    ground_type = "GroundConcrete"
    length = 100
    describe_text = {
        "default": "갈라진 타일 바닥. 벽면에 배관이 노출되어 있다.",
    }


class CommRoom(Location):
    """통신실 — 플레이어 CRT 시점, 비서 상주"""
    unique_id = "comm_room"
    name = "통신실"
    is_indoor = True
    ground_type = "GroundConcrete"
    length = 40
    describe_text = {
        "default": "CRT 모니터 여러 대가 벽면을 채우고 있다. 대부분 꺼져 있다.",
    }

    def instantiate(self, location_id, region_id):
        super().instantiate(location_id, region_id)
        # CRT 콘솔은 demo.py에서 별도 배치
