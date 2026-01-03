# objects/furniture.py - 거울, 의자 등 가구

FURNITURE = [
    {
        "id": 12,
        "name": "거울",
        "comment": "mirror_0_0",
        "type": "object",
        "regionId": 0,
        "locationId": 0,
        "actions": ["script:mirror_look:보기"],
        "scheduleStack": []
    },
    {
        "id": 13,
        "name": "거울",
        "comment": "mirror_0_2",
        "type": "object",
        "regionId": 0,
        "locationId": 2,
        "actions": ["script:mirror_look:보기"],
        "scheduleStack": []
    }
]


# === 오브젝트 상호작용 스크립트 ===

def mirror_look(context_unit_id):
    """
    거울 보기 - 자신의 얼굴을 살펴보는 모놀로그
    """
    return {
        "type": "monologue",
        "pages": [
            "거울 속에 내 얼굴이 비친다.\n익숙하면서도 낯선 느낌이다.",
            "...그래, 이게 나다.\n잠시 멍하니 자신을 바라본다."
        ],
        "time_consumed": 1,
        "button_type": "ok"
    }
