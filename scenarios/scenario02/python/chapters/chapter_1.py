# chapters/chapter_1.py - 정식 챕터 1
#
# 전체 맵: 저택 내부 + 마당 + 야외/숲
# 플레이어 + 모든 NPC
# 기존 world/mansion.py 데이터 재사용

import morld
from world import mansion


def initialize():
    """챕터 1 초기화 (정식 맵)"""
    print("[chapter_1] Initializing main chapter...")

    # 1. 지형 초기화 (기존 mansion.py 재사용)
    mansion.initialize_terrain()

    # 2. 시간 설정 (아침으로 시작)
    morld.set_time(1, 4, 2, 8, 0)  # 1년 4월 2일 아침 8시

    # 3. 플레이어 위치 설정 (현관에서 시작 - 프롤로그 종료 지점)
    _instantiate_player()

    # 4. NPC 인스턴스화 + Agent 등록
    mansion.instantiate_npcs()

    # 5. 음식 아이템 등록 (자연 오브젝트보다 먼저)
    mansion.instantiate_food_items()

    # 6. 자연 오브젝트 인스턴스화 + Agent 등록
    mansion.instantiate_nature_objects()

    print("[chapter_1] Main chapter initialized: full map with NPCs and nature objects")


def post_restore():
    """
    챕터 전환 후 플레이어 데이터 복원 후 호출

    챕터 1부터 생존 시스템 활성화
    """
    player_id = morld.get_player_id()
    if player_id is not None:
        morld.set_unit_prop(player_id, "생존:활성화", 1)
        print("[chapter_1] Survival system enabled")


def _instantiate_player():
    """플레이어 인스턴스화 (주인공 방에서 시작 - 구조 후 깨어남)"""
    from assets.characters.player import Player

    player = Player()
    player_id = morld.create_id("unit")
    player.instantiate(player_id, mansion.REGION_ID, 6)  # 주인공 방에서 시작
