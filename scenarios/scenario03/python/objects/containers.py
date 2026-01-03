# objects/containers.py - 상자, 책상 등 컨테이너

CONTAINERS = [
    {
        "id": 10,
        "name": "나무 상자",
        "comment": "object_wooden_box",
        "type": "object",
        "regionId": 0,
        "locationId": 1,
        "actions": ["open", "putinobject"],
        "scheduleStack": []
    },
    {
        "id": 11,
        "name": "오래된 책상",
        "comment": "object_old_desk",
        "type": "object",
        "regionId": 1,
        "locationId": 2,
        "actions": ["open", "examine"],
        "scheduleStack": []
    }
]
