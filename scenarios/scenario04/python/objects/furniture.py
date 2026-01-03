# objects/furniture.py - 가구 오브젝트

FURNITURE = [
    # 향후 가구 추가
]


# === 오브젝트 상호작용 스크립트 ===

def mirror_look(context_unit_id):
    """거울 보기"""
    return {
        "type": "monologue",
        "pages": [
            "거울 속에 내 얼굴이 비친다.",
            "...그래, 이게 나다."
        ],
        "time_consumed": 1,
        "button_type": "ok"
    }
