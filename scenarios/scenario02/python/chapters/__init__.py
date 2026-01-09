# chapters/__init__.py - 챕터 관리 모듈
#
# 역할:
# - 챕터 로드/전환 API 제공
# - 현재 챕터 상태 관리

import morld

# 현재 로드된 챕터
_current_chapter = None


def load_chapter(chapter_name: str):
    """
    챕터 로드 (Python에서 호출)

    기존 데이터를 초기화하고 새 챕터의 initialize() 호출

    Args:
        chapter_name: 챕터 이름 (예: "chapter_0", "chapter_1")

    Usage:
        from chapters import load_chapter
        load_chapter("chapter_1")
    """
    global _current_chapter

    print(f"[chapters] Loading chapter: {chapter_name}")

    # 1. 기존 데이터 초기화 (첫 로드가 아니면)
    if _current_chapter is not None:
        print(f"[chapters] Clearing previous chapter: {_current_chapter}")
        morld.clear_world()

    # 2. 챕터 모듈 동적 import
    try:
        chapter_module = __import__(f"chapters.{chapter_name}", fromlist=[chapter_name])
    except ImportError as e:
        print(f"[chapters] ERROR: Failed to import chapter '{chapter_name}': {e}")
        raise

    # 3. 챕터 초기화
    if hasattr(chapter_module, 'initialize'):
        chapter_module.initialize()
    else:
        print(f"[chapters] WARNING: Chapter '{chapter_name}' has no initialize() function")

    # 4. EventSystem 위치 재초기화
    morld.reinitialize_locations()

    # 5. 현재 챕터 기록
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
