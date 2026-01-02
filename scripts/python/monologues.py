# monologues.py - 모놀로그 데이터 및 함수
# Pure Python으로 모놀로그 콘텐츠 관리
# 이벤트 기반 스크립트 시스템

import morld

def _get_monologues():
    """모놀로그 데이터 반환 (sharpPy 전역 변수 우회)"""
    return {
        "intro_001": {
            "pages": [
                "여기는... 주민1의 집인가.\n낯선 천장이 보인다.",
                "몸이 무겁다. 머리가 멍하다.\n무슨 일이 있었던 걸까?",
                "일단 일어나서 주변을 살펴봐야겠다."
            ],
            "time_consumed": 5
        }
    }

def get_monologue(monologue_id):
    """모놀로그 데이터 전체 반환"""
    monologues = _get_monologues()
    if monologue_id in monologues:
        return monologues[monologue_id]
    return None

def get_monologue_page(monologue_id, page_index):
    """특정 페이지 텍스트 반환"""
    monologues = _get_monologues()
    if monologue_id in monologues:
        mono = monologues[monologue_id]
        if 0 <= page_index < len(mono["pages"]):
            return mono["pages"][page_index]
    return None

def get_monologue_page_count(monologue_id):
    """모놀로그 페이지 수 반환"""
    monologues = _get_monologues()
    if monologue_id in monologues:
        return len(monologues[monologue_id]["pages"])
    return 0

def get_monologue_time_consumed(monologue_id):
    """모놀로그 완료 시 소요 시간 반환"""
    monologues = _get_monologues()
    if monologue_id in monologues:
        mono = monologues[monologue_id]
        if "time_consumed" in mono:
            return mono["time_consumed"]
    return 0


# === 이벤트 핸들러 ===

def on_event(ev_msg):
    """
    이벤트 핸들러 - C#에서 이벤트 발생 시 호출
    반환값: {"type": "monologue", "pages": [...], "time_consumed": N} 또는 None
    """
    if ev_msg == "ready":
        # 게임 시작 시 인트로 모놀로그 - 데이터 직접 반환
        mono = get_monologue("intro_001")
        if mono:
            # 인트로 페이지 + 직업 선택 페이지 결합
            job_mono = get_job_select_monologue()
            combined_pages = mono["pages"] + job_mono["pages"]
            return {
                "type": "monologue",
                "pages": combined_pages,
                "time_consumed": mono.get("time_consumed", 0)
            }

    return None


# === 직업 선택 시스템 ===

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

def get_job_select_monologue():
    """직업 선택 모놀로그 데이터 반환"""
    return {
        "pages": [
            "잠깐, 나는 누구였지?\n기억이 잘 나지 않는다...",
            "내가 가진 기술은... 뭐였더라?\n\n[url=script:job_select:warrior]검술 - 검과 방패를 다루는 기술[/url]\n[url=script:job_select:mage]마법 - 원소의 힘을 다루는 기술[/url]\n[url=script:job_select:thief]은밀 - 그림자 속에 숨는 기술[/url]"
        ],
        "time_consumed": 0,
        "button_type": "none"  # 선택지가 있는 페이지는 버튼 없음
    }

def job_select(job_type):
    """
    직업 선택 처리 - BBCode script:job_select:xxx 로 호출됨
    플레이어에게 해당 직업의 초기 장비 지급
    """
    if job_type not in JOB_EQUIPMENT:
        return f"알 수 없는 직업: {job_type}"

    job = JOB_EQUIPMENT[job_type]
    player_id = morld.get_player_id()

    # 초기 장비 지급
    for item_id, count in job["items"]:
        morld.give_item(player_id, item_id, count)

    job_name = job["name"]
    return {
        "type": "monologue",
        "pages": [
            f"그래, 나는 {job_name}였다.\n손에 익은 감각이 돌아오는 것 같다.",
            "이제 일어나서 움직여야겠다."
        ],
        "time_consumed": 5
    }
