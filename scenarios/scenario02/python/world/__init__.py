# world/__init__.py - 월드 모듈
#
# 역할:
# - 지형 데이터 정의 및 초기화
# - 시간 설정
# - 아이템/오브젝트/캐릭터 인스턴스화

from . import mansion


def initialize_world():
    """월드 초기화 (지형 + 시간)"""
    mansion.initialize_terrain()
    mansion.initialize_time()


def instantiate_player():
    """플레이어만 인스턴스화 (챕터 0용)"""
    mansion.instantiate_player()


def instantiate_npcs():
    """NPC들만 인스턴스화 (챕터 1 전환 시)"""
    mansion.instantiate_npcs()


def instantiate_all():
    """모든 유닛 인스턴스화 (플레이어 + NPC + 오브젝트 + 아이템)"""
    mansion.instantiate()
