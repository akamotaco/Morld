# characters/player/events.py - 플레이어 전용 이벤트

import morld

# 직업별 초기 장비 정의 (아이템 ID)
JOB_EQUIPMENT = {
    "warrior": {
        "name": "검사",
        "items": [
            (10, 1),   # 철검 x1
            (11, 1),   # 나무 방패 x1
            (12, 1),   # 가죽 갑옷 x1
            (13, 1),   # 철 투구 x1
            (1, 3),    # 체력 포션 x3
            (40, 5),   # 마른 빵 x5
            (41, 1),   # 물통 x1
            (42, 1),   # 동전 주머니 x1
        ]
    },
    "mage": {
        "name": "마법사",
        "items": [
            (20, 1),   # 참나무 지팡이 x1
            (21, 1),   # 마법사 로브 x1
            (23, 1),   # 마법서: 불꽃 x1
            (22, 5),   # 마나 포션 x5
            (1, 2),    # 체력 포션 x2
            (40, 3),   # 마른 빵 x3
            (41, 1),   # 물통 x1
            (42, 1),   # 동전 주머니 x1
        ]
    },
    "thief": {
        "name": "도적",
        "items": [
            (30, 1),   # 단검 x1
            (32, 1),   # 경장갑 x1
            (34, 1),   # 그림자 망토 x1
            (33, 3),   # 자물쇠 따개 x3
            (31, 5),   # 투척용 나이프 x5
            (1, 2),    # 체력 포션 x2
            (40, 3),   # 마른 빵 x3
            (41, 1),   # 물통 x1
            (42, 1),   # 동전 주머니 x1
        ]
    }
}

# 직업별 축복 메시지
JOB_BLESSINGS = {
    "warrior": {
        "pages": [
            "강인한 힘과 용기가 네 무기다.",
            "적의 칼날에도 굴하지 않는 강철 같은 의지를,",
            "그리고 약자를 지키는 따뜻한 마음을 잊지 마라.",
            "검사여, 네 길에 승리가 함께하기를."
        ]
    },
    "mage": {
        "pages": [
            "지혜와 마나가 네 힘이다.",
            "원소의 속삭임에 귀 기울이고,",
            "진리를 향한 탐구를 게을리하지 마라.",
            "마법사여, 네 주문에 빛이 함께하기를."
        ]
    },
    "thief": {
        "pages": [
            "민첩함과 기지가 네 무기다.",
            "그림자 속에서 기회를 엿보고,",
            "필요할 때 과감히 행동하라.",
            "도적이여, 네 발걸음에 행운이 함께하기를."
        ]
    }
}


def on_game_start():
    """게임 시작 이벤트 - 인트로 + 직업 선택"""
    intro_pages = [
        "여기는... 주민1의 집인가.\n낯선 천장이 보인다.",
        "몸이 무겁다. 머리가 멍하다.\n무슨 일이 있었던 걸까?",
        "일단 일어나서 주변을 살펴봐야겠다."
    ]

    job_select_pages = [
        "잠깐, 나는 누구였지?\n기억이 잘 나지 않는다...",
        "내가 가진 기술은... 뭐였더라?\n\n[url=script:job_select:warrior]검술 - 검과 방패를 다루는 기술[/url]\n[url=script:job_select:mage]마법 - 원소의 힘을 다루는 기술[/url]\n[url=script:job_select:thief]은밀 - 그림자 속에 숨는 기술[/url]"
    ]

    return {
        "type": "monologue",
        "pages": intro_pages + job_select_pages,
        "time_consumed": 5,
        "button_type": "ok"
    }


def job_select(context_unit_id, job_type):
    """
    직업 선택 처리 - BBCode script:job_select:xxx 로 호출됨
    확인 질문을 표시하고, 승낙 시 job_confirm 호출
    """
    if job_type not in JOB_EQUIPMENT:
        return {"type": "message", "message": f"알 수 없는 직업: {job_type}"}

    job = JOB_EQUIPMENT[job_type]
    job_name = job["name"]

    # YesNo 확인 다이얼로그 반환
    return {
        "type": "monologue",
        "pages": [f"{job_name}의 길을 선택하시겠습니까?"],
        "time_consumed": 0,
        "button_type": "yesno",
        "done_callback": f"job_confirm:{job_type}",
        "cancel_callback": None
    }


def job_confirm(context_unit_id, job_type):
    """직업 최종 확정 - 아이템 지급 및 축복 메시지 표시"""
    if job_type not in JOB_EQUIPMENT:
        return {"type": "message", "message": f"알 수 없는 직업: {job_type}"}

    job = JOB_EQUIPMENT[job_type]
    player_id = morld.get_player_id()

    # 초기 장비 지급
    for item_id, count in job["items"]:
        morld.give_item(player_id, item_id, count)

    job_name = job["name"]

    # 축복 메시지 로드
    blessing_pages = JOB_BLESSINGS.get(job_type, {}).get("pages", [
        "새로운 여정이 시작된다.",
        "행운을 빈다.",
        "이제 일어나서 움직여야겠다."
    ])

    # 확정 메시지 + 축복 메시지
    confirm_pages = [
        f"그래, 나는 {job_name}였다.\n손에 익은 감각이 돌아오는 것 같다."
    ]

    return {
        "type": "monologue",
        "pages": confirm_pages + blessing_pages,
        "time_consumed": 5
    }
