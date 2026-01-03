# objects/furniture.py - 가구 오브젝트

FURNITURE = [
    # === 거실 (location 1) ===
    {
        "id": 50,
        "name": "벽난로",
        "regionId": 0,
        "locationId": 1,
        "type": "object",
        "actions": ["script:fireplace_look:살펴보기"],
        "appearance": {
            "default": "돌로 만들어진 오래된 벽난로. 저녁이면 불이 피워진다.",
            "저녁": "따뜻한 불꽃이 타오르고 있다.",
            "밤": "잔잔한 불씨가 남아 있다."
        }
    },
    {
        "id": 51,
        "name": "낡은 소파",
        "regionId": 0,
        "locationId": 1,
        "type": "object",
        "actions": ["script:sofa_sit:앉기"],
        "appearance": {
            "default": "오래 사용해서 닳았지만 여전히 푹신한 소파."
        }
    },
    {
        "id": 52,
        "name": "책장",
        "regionId": 0,
        "locationId": 1,
        "type": "object",
        "actions": ["script:bookshelf_look:살펴보기"],
        "appearance": {
            "default": "벽면을 따라 놓인 큰 책장. 다양한 책이 꽂혀 있다."
        }
    },

    # === 식당 (location 3) ===
    {
        "id": 53,
        "name": "긴 식탁",
        "regionId": 0,
        "locationId": 3,
        "type": "object",
        "actions": ["script:table_look:살펴보기"],
        "appearance": {
            "default": "여섯 명이 앉을 수 있는 긴 나무 식탁. 잘 닦여 있다."
        }
    },

    # === 주방 (location 2) ===
    {
        "id": 54,
        "name": "아궁이",
        "regionId": 0,
        "locationId": 2,
        "type": "object",
        "actions": ["script:stove_look:살펴보기"],
        "appearance": {
            "default": "요리에 사용하는 큰 아궁이. 항상 따뜻하다."
        }
    },
    {
        "id": 55,
        "name": "찬장",
        "regionId": 0,
        "locationId": 2,
        "type": "object",
        "actions": ["script:cupboard_look:살펴보기"],
        "appearance": {
            "default": "그릇과 조리도구가 정리된 찬장."
        }
    },

    # === 욕실 (location 4) ===
    {
        "id": 56,
        "name": "나무 욕조",
        "regionId": 0,
        "locationId": 4,
        "type": "object",
        "actions": ["script:bath_use:목욕하기"],
        "appearance": {
            "default": "큰 나무 욕조. 따뜻한 물을 받아 목욕할 수 있다."
        }
    },
    {
        "id": 57,
        "name": "세면대",
        "regionId": 0,
        "locationId": 4,
        "type": "object",
        "actions": ["script:washbasin_use:세수하기"],
        "appearance": {
            "default": "도자기로 만든 세면대. 깨끗하게 관리되어 있다."
        }
    },

    # === 창고 (location 5) ===
    {
        "id": 58,
        "name": "선반",
        "regionId": 0,
        "locationId": 5,
        "type": "object",
        "actions": ["script:shelf_look:살펴보기"],
        "appearance": {
            "default": "식량과 보존식품이 정리된 나무 선반."
        }
    },

    # === 주인공 방 (location 6) ===
    {
        "id": 59,
        "name": "침대",
        "regionId": 0,
        "locationId": 6,
        "type": "object",
        "actions": ["script:bed_sleep:잠자기", "script:bed_rest:누워있기"],
        "appearance": {
            "default": "작지만 편안해 보이는 침대. 깨끗한 이불이 깔려 있다."
        }
    },
    {
        "id": 60,
        "name": "작은 책상",
        "regionId": 0,
        "locationId": 6,
        "type": "object",
        "actions": ["script:desk_look:살펴보기"],
        "appearance": {
            "default": "작은 나무 책상. 서랍이 하나 달려 있다."
        }
    },
    {
        "id": 61,
        "name": "거울",
        "regionId": 0,
        "locationId": 6,
        "type": "object",
        "actions": ["script:mirror_look:거울 보기"],
        "appearance": {
            "default": "벽에 걸린 작은 거울. 내 모습을 비춰볼 수 있다."
        }
    },

    # === 2층 복도 (location 14) ===
    {
        "id": 62,
        "name": "복도 창문",
        "regionId": 0,
        "locationId": 14,
        "type": "object",
        "actions": ["script:window_look:밖을 보기"],
        "appearance": {
            "default": "2층 복도에 있는 큰 창문. 앞마당이 내려다보인다."
        }
    },
    {
        "id": 63,
        "name": "화병",
        "regionId": 0,
        "locationId": 14,
        "type": "object",
        "actions": ["script:vase_look:살펴보기"],
        "appearance": {
            "default": "복도 끝에 놓인 장식용 화병. 마른 꽃이 꽂혀 있다."
        }
    },

    # === 앞마당 (location 12) ===
    {
        "id": 64,
        "name": "정원 벤치",
        "regionId": 0,
        "locationId": 12,
        "type": "object",
        "actions": ["script:bench_sit:앉기"],
        "appearance": {
            "default": "정원에 놓인 나무 벤치. 앉아서 쉴 수 있다."
        }
    },
    {
        "id": 65,
        "name": "우물",
        "regionId": 0,
        "locationId": 12,
        "type": "object",
        "actions": ["script:well_look:들여다보기", "script:well_draw:물 길어올리기"],
        "appearance": {
            "default": "돌로 쌓아 만든 우물. 맑은 물이 고여 있다."
        }
    },

    # === 뒷마당 (location 13) ===
    {
        "id": 66,
        "name": "텃밭",
        "regionId": 0,
        "locationId": 13,
        "type": "object",
        "actions": ["script:garden_look:살펴보기"],
        "appearance": {
            "default": "작은 텃밭. 간단한 채소를 기를 수 있을 것 같다.",
            "봄": "새싹이 돋아나고 있다.",
            "여름": "채소들이 무성하게 자라고 있다.",
            "가을": "수확할 채소가 익어가고 있다.",
            "겨울": "텅 빈 텃밭. 봄을 기다리고 있다."
        }
    },
    {
        "id": 67,
        "name": "빨래 건조대",
        "regionId": 0,
        "locationId": 13,
        "type": "object",
        "actions": ["script:drying_rack_look:살펴보기"],
        "appearance": {
            "default": "뒷마당에 놓인 빨래 건조대. 가끔 빨래가 널려 있다."
        }
    }
]


# === 오브젝트 상호작용 스크립트 ===

def fireplace_look(context_unit_id):
    """벽난로 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["돌로 쌓아 만든 오래된 벽난로다.", "저녁이 되면 따뜻한 불이 피워진다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def sofa_sit(context_unit_id):
    """소파에 앉기"""
    return {
        "type": "monologue",
        "pages": ["소파에 앉았다.", "푹신하고 편안하다."],
        "time_consumed": 5,
        "button_type": "ok"
    }


def bookshelf_look(context_unit_id):
    """책장 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["다양한 책이 꽂혀 있다.", "소설, 역사서, 요리책... 장르가 다양하다."],
        "time_consumed": 2,
        "button_type": "ok"
    }


def table_look(context_unit_id):
    """식탁 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["잘 닦인 긴 나무 식탁이다.", "여섯 개의 의자가 가지런히 놓여 있다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def stove_look(context_unit_id):
    """아궁이 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["요리에 사용하는 큰 아궁이다.", "항상 따뜻한 열기가 느껴진다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def cupboard_look(context_unit_id):
    """찬장 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["그릇과 조리도구가 깔끔하게 정리되어 있다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def bath_use(context_unit_id):
    """목욕하기"""
    return {
        "type": "monologue",
        "pages": ["따뜻한 물을 받아 목욕했다.", "몸이 개운해졌다."],
        "time_consumed": 30,
        "button_type": "ok"
    }


def washbasin_use(context_unit_id):
    """세수하기"""
    return {
        "type": "monologue",
        "pages": ["시원한 물로 얼굴을 씻었다.", "정신이 맑아졌다."],
        "time_consumed": 5,
        "button_type": "ok"
    }


def shelf_look(context_unit_id):
    """선반 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["식량과 보존식품이 정리되어 있다.", "장기 보관할 수 있는 것들이 많다."],
        "time_consumed": 2,
        "button_type": "ok"
    }


def bed_sleep(context_unit_id):
    """잠자기"""
    return {
        "type": "monologue",
        "pages": ["침대에 누워 잠을 청했다."],
        "time_consumed": 480,  # 8시간
        "button_type": "ok"
    }


def bed_rest(context_unit_id):
    """누워있기"""
    return {
        "type": "monologue",
        "pages": ["침대에 잠시 누워 쉬었다.", "피로가 조금 풀렸다."],
        "time_consumed": 30,
        "button_type": "ok"
    }


def desk_look(context_unit_id):
    """책상 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["작은 나무 책상이다.", "서랍이 하나 달려 있다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def mirror_look(context_unit_id):
    """거울 보기"""
    return {
        "type": "monologue",
        "pages": ["거울 속에 내 얼굴이 비친다.", "...그래, 이게 나다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def window_look(context_unit_id):
    """창문 밖을 보기"""
    return {
        "type": "monologue",
        "pages": ["2층 창문에서 앞마당이 내려다보인다.", "정원이 한눈에 들어온다."],
        "time_consumed": 2,
        "button_type": "ok"
    }


def vase_look(context_unit_id):
    """화병 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["장식용 화병이다.", "마른 꽃이 꽂혀 있다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def bench_sit(context_unit_id):
    """벤치에 앉기"""
    return {
        "type": "monologue",
        "pages": ["정원 벤치에 앉았다.", "바람이 시원하다."],
        "time_consumed": 10,
        "button_type": "ok"
    }


def well_look(context_unit_id):
    """우물 들여다보기"""
    return {
        "type": "monologue",
        "pages": ["우물 안을 들여다봤다.", "맑은 물이 깊은 곳에서 반짝인다."],
        "time_consumed": 1,
        "button_type": "ok"
    }


def well_draw(context_unit_id):
    """물 길어올리기"""
    return {
        "type": "monologue",
        "pages": ["두레박으로 물을 길어올렸다.", "시원하고 맑은 물이다."],
        "time_consumed": 5,
        "button_type": "ok"
    }


def garden_look(context_unit_id):
    """텃밭 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["작은 텃밭이다.", "간단한 채소를 기를 수 있을 것 같다."],
        "time_consumed": 2,
        "button_type": "ok"
    }


def drying_rack_look(context_unit_id):
    """빨래 건조대 살펴보기"""
    return {
        "type": "monologue",
        "pages": ["빨래 건조대다.", "빨래가 마르면 걷어야 할 것 같다."],
        "time_consumed": 1,
        "button_type": "ok"
    }
