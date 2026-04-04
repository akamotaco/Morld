# chapters/__init__.py - 챕터 관리 모듈 (S04)
#
# S02 구조를 기반으로 단순화.
# S04는 단일 챕터 (마을+던전) 구조이지만, 확장성을 위해 챕터 시스템 유지.

import morld

# 현재 로드된 챕터
_current_chapter = None

# Limbo region 상수 (운반 시스템용 — Gate 없는 격리 공간)
LIMBO_REGION = 99
LIMBO_LOCATION = 0


def load_chapter(chapter_name: str, preserve_player: bool = True):
    """
    챕터 로드

    Args:
        chapter_name: 챕터 이름 (예: "chapter_0")
        preserve_player: True면 플레이어 데이터 유지
    """
    global _current_chapter

    print(f"[chapters] Loading chapter: {chapter_name}")

    # 1. 기존 데이터 초기화 (첫 로드가 아니면)
    if _current_chapter is not None:
        morld.clear_world()

    # 2. 전체 시스템 리셋
    import temperature, humidity, pollution, survival
    import erosion, economy, morale, trust, quirk
    import party, npc_generator, dungeon
    import building, business, taming, corrosion, carry
    import world_knowledge, reputation

    # 환경
    temperature.reset()
    humidity.reset()
    pollution.reset()

    # 생존/경제
    survival.reset()
    economy.reset()

    # 파티/NPC
    party.reset()
    npc_generator.reset()
    morale.reset()
    trust.reset()
    quirk.reset()

    # 던전
    dungeon.reset()
    erosion.reset()

    # 경영
    building.reset()
    business.reset()
    taming.reset()
    corrosion.reset()
    carry.reset()

    # 세계관
    world_knowledge.reset()
    reputation.reset()

    # 3. Limbo region 생성 (운반 시스템)
    morld.add_region(LIMBO_REGION, "limbo")
    morld.add_location(LIMBO_REGION, LIMBO_LOCATION, "limbo", length=1)

    # 4. 챕터 모듈 동적 import
    try:
        chapter_module = __import__(f"chapters.{chapter_name}", fromlist=[chapter_name])
    except ImportError as e:
        print(f"[chapters] ERROR: Failed to import chapter '{chapter_name}': {e}")
        raise

    # 5. 챕터 초기화
    if hasattr(chapter_module, 'initialize'):
        chapter_module.initialize()
    else:
        print(f"[chapters] WARNING: Chapter '{chapter_name}' has no initialize() function")

    # 6. EventSystem 위치 재초기화
    morld.reinitialize_locations()

    # 7. 현재 챕터 기록
    _current_chapter = chapter_name

    print(f"[chapters] Chapter '{chapter_name}' loaded successfully.")


def get_current_chapter() -> str:
    """현재 로드된 챕터 이름 반환"""
    return _current_chapter
