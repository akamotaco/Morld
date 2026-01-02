# monologues.py - 모놀로그 데이터 및 함수
# Pure Python으로 모놀로그 콘텐츠 관리

# 전역 변수 대신 함수 내부에서 데이터 정의 (sharpPy 전역 스코프 테스트)

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
