# chapters/__init__.py - 챕터 관리 모듈
#
# 역할:
# - 챕터 로드/전환 API 제공
# - 현재 챕터 상태 관리
# - 플레이어 데이터 저장/복원

import morld
from .persistence import (
    save_for_chapter_transition,
    restore_after_chapter_transition,
    has_saved_data,
    save_player_data,
    restore_player_data,
)

# 현재 로드된 챕터
_current_chapter = None

# Limbo region 상수 (운반 시스템용 — Gate 없는 격리 공간)
LIMBO_REGION = 99
LIMBO_LOCATION = 0


def load_chapter(chapter_name: str, preserve_player: bool = True):
    """
    챕터 로드 (Python에서 호출)

    기존 데이터를 초기화하고 새 챕터의 initialize() 호출

    Args:
        chapter_name: 챕터 이름 (예: "chapter_0", "chapter_1")
        preserve_player: True면 플레이어 데이터 유지 (기본값)

    Usage:
        from chapters import load_chapter
        load_chapter("chapter_1")  # 플레이어 데이터 유지
        load_chapter("chapter_0", preserve_player=False)  # 새 게임
    """
    global _current_chapter

    print(f"[chapters] Loading chapter: {chapter_name}")

    # 1. 기존 데이터 저장 (첫 로드가 아니고 preserve_player=True면)
    if _current_chapter is not None and preserve_player:
        save_for_chapter_transition()

    # 2. 기존 데이터 초기화 (첫 로드가 아니면)
    if _current_chapter is not None:
        morld.clear_world()

    # 2.1. 환경 시스템 리셋 (lazy init 모듈들의 챕터 전환 대응)
    #      clear_world() 후 새 챕터 데이터로 재초기화되어야 함
    import temperature, humidity, congestion, sound, garden, needs, pregnancy, gender, fuel
    import carry, ground, stealth, laundry
    temperature.reset()
    humidity.reset()
    congestion.reset()
    sound.reset()
    garden.reset()
    needs.reset()
    pregnancy.reset()
    gender.reset_orientation()
    fuel.reset()
    carry.reset()
    ground.reset()
    stealth.reset()
    laundry.reset()

    # 2.2. Limbo region 생성 (운반 시스템 — 매 챕터 로드마다 재생성)
    morld.add_region(LIMBO_REGION, "limbo")
    morld.add_location(LIMBO_REGION, LIMBO_LOCATION, "limbo", length=1)

    # 3. 챕터 모듈 동적 import
    try:
        chapter_module = __import__(f"chapters.{chapter_name}", fromlist=[chapter_name])
    except ImportError as e:
        print(f"[chapters] ERROR: Failed to import chapter '{chapter_name}': {e}")
        raise

    # 4. 챕터 초기화
    if hasattr(chapter_module, 'initialize'):
        chapter_module.initialize()
    else:
        print(f"[chapters] WARNING: Chapter '{chapter_name}' has no initialize() function")

    # 5. 저장된 플레이어 데이터 복원
    if has_saved_data():
        restore_after_chapter_transition()

    # 5.1. 챕터별 후처리 (복원 후 추가 설정)
    if hasattr(chapter_module, 'post_restore'):
        chapter_module.post_restore()

    # 6. EventSystem 위치 재초기화
    morld.reinitialize_locations()

    # 7. Instance ID 중복 검사
    from assets import validate_instance_ids
    validate_instance_ids()

    # 8. 현재 챕터 기록
    _current_chapter = chapter_name

    print(f"[chapters] Chapter '{chapter_name}' loaded successfully.")


def get_current_chapter() -> str:
    """현재 로드된 챕터 이름 반환"""
    return _current_chapter


def reload_current_chapter():
    """현재 챕터 재로드 (디버그용)"""
    if _current_chapter:
        # 강제로 모듈 캐시 삭제
        import sys
        module_name = f"chapters.{_current_chapter}"
        if module_name in sys.modules:
            del sys.modules[module_name]

        load_chapter(_current_chapter)
    else:
        print("[chapters] No chapter loaded yet.")
