# objects/grounds.py - 바닥 오브젝트 자동 생성

from world import REGIONS

GROUND_ID_START = 100


def get_ground_objects():
    """world.py의 REGIONS를 기반으로 바닥 오브젝트 자동 생성"""
    grounds = []
    ground_id = GROUND_ID_START

    for region in REGIONS:
        region_id = region["id"]
        for location in region["locations"]:
            location_id = location["id"]
            grounds.append({
                "id": ground_id,
                "name": "바닥",
                "comment": f"ground_{region_id}_{location_id}",
                "type": "object",
                "regionId": region_id,
                "locationId": location_id,
                "actions": ["putinobject"],
                "scheduleStack": []
            })
            ground_id += 1

    return grounds


def get_ground_id(region_id, location_id):
    """특정 위치의 바닥 오브젝트 ID 반환"""
    ground_id = GROUND_ID_START
    for region in REGIONS:
        rid = region["id"]
        for location in region["locations"]:
            lid = location["id"]
            if rid == region_id and lid == location_id:
                return ground_id
            ground_id += 1
    return None
