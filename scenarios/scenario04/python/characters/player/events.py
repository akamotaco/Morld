# characters/player/events.py - 플레이어 전용 이벤트

import morld
from characters.player.data import NAME_OPTIONS, AGE_OPTIONS, BODY_OPTIONS, EQUIPMENT_OPTIONS

# 캐릭터 생성 임시 저장소
_creation_data = {
    "name": None,
    "age": None,
    "body": None,
    "equipment": None
}

# 챕터 상수
CHAPTER_PROLOGUE = 0  # 숲 방황
CHAPTER_MANSION = 1   # 저택 생활


def get_current_chapter():
    """현재 챕터 반환"""
    return morld.get_flag("chapter") or 0


def is_prologue():
    """프롤로그 챕터인지 확인"""
    return get_current_chapter() == CHAPTER_PROLOGUE


def is_mansion_life():
    """저택 생활 챕터인지 확인"""
    return get_current_chapter() >= CHAPTER_MANSION


def get_player_name():
    """플레이어 이름 반환 (Python 내부 저장소에서)"""
    return _creation_data.get("name") or "???"


def on_game_start():
    """게임 시작 이벤트 - 캐릭터 설정"""
    # 챕터 0: 프롤로그 (숲 방황)
    morld.set_flag("chapter", 0)

    intro_pages = [
        "......",
        "......의식이 희미하게 떠오른다.",
        "머리가... 아프다.",
        "여기는... 어디지?",
        "기억이... 나지 않는다.",
        "눈앞에 울창한 나무들이 보인다.\n숲 속인 것 같다.",
        "...일단 나 자신에 대해 생각해보자."
    ]

    # 이름 선택 페이지
    name_options = "\n".join([
        f"[url=script:set_name:{name}]{name}[/url]"
        for name in NAME_OPTIONS
    ])
    name_page = f"내 이름은...?\n\n{name_options}"

    return {
        "type": "monologue",
        "pages": intro_pages + [name_page],
        "time_consumed": 0,
        "button_type": "none_on_last"
    }


def set_name(context_unit_id, name):
    """이름 설정"""
    _creation_data["name"] = name

    # 나이 선택 페이지
    age_options = "\n".join([
        f"[url=script:set_age:{opt['value']}]{opt['label']}[/url]"
        for opt in AGE_OPTIONS
    ])
    age_page = f"그래, 나는 {name}.\n\n내 나이는...?\n\n{age_options}"

    return {
        "type": "monologue",
        "pages": [age_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_age(context_unit_id, age_str):
    """나이 설정"""
    age = int(age_str)
    _creation_data["age"] = age

    # 신체 선택 페이지
    body_options = "\n".join([
        f"[url=script:set_body:{opt['value']}]{opt['label']}[/url]"
        for opt in BODY_OPTIONS
    ])
    body_page = f"내 체격은...?\n\n{body_options}"

    return {
        "type": "monologue",
        "pages": [body_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_body(context_unit_id, body_type):
    """신체 설정"""
    _creation_data["body"] = body_type

    # 장비 선택 페이지
    equip_options = "\n".join([
        f"[url=script:set_equipment:{opt['id']}]{opt['label']}[/url]\n  - {opt['desc']}"
        for opt in EQUIPMENT_OPTIONS
    ])
    equip_page = f"손에 뭔가 익숙한 감각이...\n\n{equip_options}"

    return {
        "type": "monologue",
        "pages": [equip_page],
        "time_consumed": 0,
        "button_type": "none"
    }


def set_equipment(context_unit_id, equip_id):
    """장비 설정 및 캐릭터 생성 완료"""
    _creation_data["equipment"] = equip_id

    # 플레이어 데이터 적용
    player_id = morld.get_player_id()

    # 나이는 정수로 저장 가능
    morld.set_flag("player_age", _creation_data["age"])

    # 신체 타입을 인덱스로 저장 (0=왜소, 1=보통, 2=장신, 3=거구)
    body_index = {"왜소": 0, "보통": 1, "장신": 2, "거구": 3}.get(_creation_data["body"], 1)
    morld.set_flag("player_body", body_index)

    # 이름을 인덱스로 저장 (NAME_OPTIONS 인덱스)
    name_index = NAME_OPTIONS.index(_creation_data["name"]) if _creation_data["name"] in NAME_OPTIONS else 0
    morld.set_flag("player_name_index", name_index)

    # 장비 지급
    for opt in EQUIPMENT_OPTIONS:
        if opt["id"] == equip_id:
            for item_id, count in opt["items"]:
                morld.give_item(player_id, item_id, count)
            break

    # 신체/나이에 따른 태그 설정 (향후 morld.set_unit_tag() 필요)

    # 완료 메시지 - 숲에서 방황 시작
    name = _creation_data["name"]

    completion_pages = [
        f"그래... 나는 {name}.",
        "기억은 아직 희미하지만...\n적어도 나 자신이 누구인지는 알겠다.",
        "...여기가 어디지? 깊은 숲 속인 것 같다.",
        "일단 움직여서 사람이 있는 곳을 찾아야겠다."
    ]

    return {
        "type": "monologue",
        "pages": completion_pages,
        "time_consumed": 5,
        "button_type": "ok"
    }


def on_reach_front_yard():
    """앞마당 도착 이벤트 - 쓰러짐"""
    name = get_player_name()

    collapse_pages = [
        "저 앞에... 건물이 보인다.",
        "저택인가? 드디어 사람이 사는 곳을 찾았다.",
        "하지만... 몸이 말을 듣지 않는다.",
        "배가 고프고... 너무 지쳤다.",
        "눈앞이... 흐려진다...",
        "......",
        "(의식을 잃었다)"
    ]

    return {
        "type": "monologue",
        "pages": collapse_pages,
        "time_consumed": 0,
        "button_type": "ok",
        "done_callback": "after_collapse"
    }


def after_collapse(context_unit_id):
    """쓰러진 후 - 구조되어 방에서 깨어남"""
    player_id = morld.get_player_id()
    name = get_player_name()

    # 플레이어를 주인공 방으로 이동
    morld.set_unit_location(player_id, 0, 6)  # 저택(0), 주인공 방(6)

    # 시간 경과 (저녁이 되었다고 가정)
    morld.advance_time(180)  # 3시간 경과

    wakeup_pages = [
        "......",
        "......응...?",
        "눈을 떠보니 낯선 천장이 보인다.",
        "부드러운 침대 위에 누워 있다.",
        "...여기는 어디지?",
        "분명 숲에서 쓰러졌는데...",
        "누군가 나를 이곳으로 옮겨준 모양이다.",
        "몸 상태가 많이 나아진 것 같다.\n잠시 쉬었던 것 같다.",
        "일단 일어나서 여기가 어딘지 알아봐야겠다."
    ]

    # 챕터 1: 저택 생활 시작 - NPC 로드
    morld.set_flag("chapter", 1)
    load_chapter_1_npcs()

    return {
        "type": "monologue",
        "pages": wakeup_pages,
        "time_consumed": 0,
        "button_type": "ok"
    }


def load_chapter_1_npcs():
    """챕터 1에서 NPC들을 로드"""
    from characters import initialize_npcs
    initialize_npcs()


# === 호환성을 위한 빈 함수 (scenario03에서 사용) ===

def job_select(context_unit_id, job_type=None):
    """직업 선택 (이 시나리오에서는 사용 안 함)"""
    return None


def job_confirm(context_unit_id, job_type=None):
    """직업 확정 (이 시나리오에서는 사용 안 함)"""
    return None
