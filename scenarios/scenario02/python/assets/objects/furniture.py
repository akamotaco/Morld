# assets/objects/furniture.py - 실내 가구 오브젝트

from assets import registry

# ========================================
# 거실 오브젝트
# ========================================

FIREPLACE = {
    "unique_id": "fireplace",
    "name": "벽난로",
    "actions": ["script:fireplace_look:살펴보기"],
    "appearance": {
        "default": "돌로 만들어진 오래된 벽난로. 저녁이면 불이 피워진다.",
        "저녁": "따뜻한 불꽃이 타오르고 있다.",
        "밤": "잔잔한 불씨가 남아 있다."
    }
}

OLD_SOFA = {
    "unique_id": "old_sofa",
    "name": "낡은 소파",
    "actions": ["script:sofa_sit:앉기"],
    "appearance": {"default": "오래 사용해서 닳았지만 여전히 푹신한 소파."}
}

BOOKSHELF = {
    "unique_id": "bookshelf",
    "name": "책장",
    "actions": ["script:bookshelf_look:살펴보기"],
    "appearance": {"default": "벽면을 따라 놓인 큰 책장. 다양한 책이 꽂혀 있다."}
}

# ========================================
# 식당 오브젝트
# ========================================

DINING_TABLE = {
    "unique_id": "dining_table",
    "name": "긴 식탁",
    "actions": ["script:table_look:살펴보기"],
    "appearance": {"default": "여섯 명이 앉을 수 있는 긴 나무 식탁. 잘 닦여 있다."}
}

# ========================================
# 주방 오브젝트
# ========================================

STOVE = {
    "unique_id": "stove",
    "name": "아궁이",
    "actions": ["script:stove_look:살펴보기"],
    "appearance": {"default": "요리에 사용하는 큰 아궁이. 항상 따뜻하다."}
}

CUPBOARD = {
    "unique_id": "cupboard",
    "name": "찬장",
    "actions": ["script:cupboard_look:살펴보기"],
    "appearance": {"default": "그릇과 조리도구가 정리된 찬장."}
}

# ========================================
# 욕실 오브젝트
# ========================================

BATHTUB = {
    "unique_id": "bathtub",
    "name": "나무 욕조",
    "actions": ["script:bath_use:목욕하기"],
    "appearance": {"default": "큰 나무 욕조. 따뜻한 물을 받아 목욕할 수 있다."}
}

WASHBASIN = {
    "unique_id": "washbasin",
    "name": "세면대",
    "actions": ["script:washbasin_use:세수하기"],
    "appearance": {"default": "도자기로 만든 세면대. 깨끗하게 관리되어 있다."}
}

# ========================================
# 창고 오브젝트
# ========================================

STORAGE_SHELF = {
    "unique_id": "storage_shelf",
    "name": "선반",
    "actions": ["script:shelf_look:살펴보기"],
    "appearance": {"default": "식량과 보존식품이 정리된 나무 선반."}
}

# ========================================
# 침실 오브젝트 (주인공 방)
# ========================================

BED = {
    "unique_id": "bed",
    "name": "침대",
    "actions": ["script:bed_sleep:잠자기", "script:bed_rest:누워있기"],
    "appearance": {"default": "작지만 편안해 보이는 침대. 깨끗한 이불이 깔려 있다."}
}

SMALL_DESK = {
    "unique_id": "small_desk",
    "name": "작은 책상",
    "actions": ["script:desk_look:살펴보기"],
    "appearance": {"default": "작은 나무 책상. 서랍이 하나 달려 있다."}
}

MIRROR = {
    "unique_id": "mirror",
    "name": "거울",
    "actions": ["script:mirror_look:거울 보기"],
    "appearance": {"default": "벽에 걸린 작은 거울. 내 모습을 비춰볼 수 있다."}
}

# ========================================
# 2층 복도 오브젝트
# ========================================

CORRIDOR_WINDOW = {
    "unique_id": "corridor_window",
    "name": "복도 창문",
    "actions": ["script:window_look:밖을 보기"],
    "appearance": {"default": "2층 복도에 있는 큰 창문. 앞마당이 내려다보인다."}
}

VASE = {
    "unique_id": "vase",
    "name": "화병",
    "actions": ["script:vase_look:살펴보기"],
    "appearance": {"default": "복도 끝에 놓인 장식용 화병. 마른 꽃이 꽂혀 있다."}
}


def register():
    """실내 가구 Asset 등록"""
    # 거실
    registry.register_object(FIREPLACE)
    registry.register_object(OLD_SOFA)
    registry.register_object(BOOKSHELF)
    # 식당
    registry.register_object(DINING_TABLE)
    # 주방
    registry.register_object(STOVE)
    registry.register_object(CUPBOARD)
    # 욕실
    registry.register_object(BATHTUB)
    registry.register_object(WASHBASIN)
    # 창고
    registry.register_object(STORAGE_SHELF)
    # 침실
    registry.register_object(BED)
    registry.register_object(SMALL_DESK)
    registry.register_object(MIRROR)
    # 2층 복도
    registry.register_object(CORRIDOR_WINDOW)
    registry.register_object(VASE)


# ========================================
# 스크립트 함수
# ========================================

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
