# assets/base.py - S04 기본 Asset 클래스
#
# S02의 에셋 자급자족 정책 유지:
# - 하나의 .py 파일 = 하나의 완전한 에셋
# - 파일 추가/삭제만으로 에셋 인식

import morld


class Asset:
    """모든 에셋의 기반 클래스"""
    unique_id = None
    name = "unnamed"
    props = {}


class Character(Asset):
    """캐릭터 기반 클래스 (플레이어/NPC/몬스터 공통)"""

    # 기본 스탯 (S04: 근력/민첩/체력/정신)
    base_str = 10  # 근력
    base_agi = 10  # 민첩
    base_vit = 10  # 체력
    base_mnd = 10  # 정신

    # 클래스
    character_class = None  # "척후", "타격수" 등

    # 특수 존재 여부 (던전의 힘 사용 가능)
    is_special = False

    def get_describe_text(self) -> str:
        return f"{self.name}이(가) 있다."

    def get_focus_text(self) -> str:
        return f"{self.name}."


class Object(Asset):
    """오브젝트 기반 클래스 (시설, 가구 등)"""

    def get_describe_text(self) -> str:
        return f"{self.name}이(가) 놓여 있다."


class Item(Asset):
    """아이템 기반 클래스"""
    weight = 1.0  # 무게
    value = 0     # 가치 (원)
    category = "misc"  # 카테고리
