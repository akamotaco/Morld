# world/__init__.py - 월드 초기화 (지형 + 인스턴스)
#
# 역할:
# 1. 지형 데이터 초기화 (Region, Location, Edge)
# 2. 시간 설정
# 3. 캐릭터/오브젝트/아이템 인스턴스화

# Region별 배치 모듈
from . import mansion


def initialize_terrain():
    """지형 데이터 초기화 - 저택 Region"""
    mansion.initialize_terrain()


def initialize_time():
    """게임 시간 초기화"""
    mansion.initialize_time()


def instantiate_all():
    """모든 인스턴스 생성 (캐릭터, 오브젝트, 아이템)"""
    mansion.instantiate()
    print("[world] All instances created")
