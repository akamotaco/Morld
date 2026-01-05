# assets/items/documents.py - 문서류 (일기장, 오래된 편지, 서재 메모)

from assets.base import Item


class Diary(Item):
    """일기장"""
    unique_id = "diary"
    name = "일기장"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_diary:읽기@inventory"]

    pages = [
        # 표지
        "낡은 가죽 표지의 일기장이다.\n\n금박으로 '1842'라고 새겨져 있다.\n\n페이지를 넘겨본다...",

        # 1페이지
        "[b]1842년 3월 15일[/b]\n\n오늘 이 저택의 열쇠를 받았다.\n\n조부께서 물려주신 이 저택...\n낡았지만 어딘가 기품이 느껴진다.\n\n새로운 시작이다.",

        # 2페이지
        "[b]1842년 5월 22일[/b]\n\n저택 곳곳을 수리하고 있다.\n지하실의 배전함이 고장나서\n전기 기사를 불렀다.\n\n\"빛이 없으면 길도 없다\"라고\n농담처럼 말했더니,\n기사가 웃으며 동의했다.",

        # 3페이지
        "[b]1842년 8월 7일[/b]\n\n이상한 일이 일어나기 시작했다.\n\n밤마다 복도에서 발자국 소리가 들린다.\n아무도 없는데...\n\n신경이 예민해진 탓이겠지.",

        # 4페이지
        "[b]1842년 10월 31일[/b]\n\n더 이상 이곳에 있을 수 없다.\n\n[i]그것[/i]이 나를 쫓고 있다.\n\n정문의 황금열쇠를 금고에 숨겼다.\n비밀번호는 이 저택이 지어진 해.\n\n누군가 이 일기를 발견한다면...\n부디 조심하길.",

        # 마지막 페이지
        "...일기는 여기서 끝나 있다.\n\n이후의 페이지는 전부 찢겨 나갔다.\n\n저택 주인에게 무슨 일이 있었던 걸까.",
    ]


class OldLetter(Item):
    """오래된 편지"""
    unique_id = "old_letter"
    name = "오래된 편지"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_old_letter:읽기@inventory"]

    pages = [
        "누렇게 바랜 봉투 안에 편지가 들어있다.\n\n봉투에는 '에밀리에게'라고 적혀있다.\n\n펼쳐본다...",

        "[b]사랑하는 에밀리에게[/b]\n\n이 편지가 네게 닿을 수 있을지 모르겠구나.\n\n하지만 누군가는 알아야 한다.\n이 저택에서 무슨 일이 일어나고 있는지.",

        "처음에는 발자국 소리였다.\n\n아무도 없는 복도에서 들려오는\n또각또각 거리는 발소리.\n\n처음에는 쥐인 줄 알았다.",

        "그 다음은 그림자였다.\n\n계단 창문에 비치는\n있어서는 안 될 형체.\n\n뒤를 돌아보면 사라져 있었다.",

        "그리고 목소리가 들리기 시작했다.\n\n\"...나...가...\"\n\n무슨 뜻인지 모르겠다.\n나가라는 건지, 무언가를 찾으라는 건지.",

        "황금열쇠를 숨겼다.\n두 조각으로 나누어 이 저택 어딘가에.\n\n누군가 이 편지를 발견한다면\n부디 여기서 빠져나가길 바란다.\n\n그리고... 에밀리에게 전해다오.\n나는 끝까지 그녀를 사랑했다고.",

        "...편지는 여기서 끝나 있다.\n\n서명은 없다.\n잉크가 번져 알아볼 수 없다.\n\n저택 주인은 결국 이 편지를\n보내지 못한 것 같다.",
    ]


class StudyMemo(Item):
    """서재 메모"""
    unique_id = "study_memo"
    name = "서재 메모"
    passive_props = {}
    equip_props = {}
    value = 0
    actions = ["take@container", "script:read_study_memo:읽기@inventory"]

    content = '"서재 문 비밀번호: 2847"'


# ========================================
# 스크립트 함수
# ========================================

def read_diary(context_unit_id):
    """일기장 읽기 - 멀티페이지"""
    return {
        "type": "monologue",
        "pages": Diary.pages,
        "time_consumed": 2,
        "button_type": "ok"
    }


def read_old_letter(context_unit_id):
    """오래된 편지 읽기 - 멀티페이지"""
    return {
        "type": "monologue",
        "pages": OldLetter.pages,
        "time_consumed": 2,
        "button_type": "ok"
    }


def read_study_memo(context_unit_id):
    """서재 메모 읽기"""
    return {
        "type": "monologue",
        "pages": [StudyMemo.content],
        "time_consumed": 0
    }
