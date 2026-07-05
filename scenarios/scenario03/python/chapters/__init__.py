# chapters/__init__.py - 챕터 관리 모듈 (시나리오03)
#
# 역할:
# - 챕터 로드/전환 API 제공
# - 현재 챕터 상태 관리
#
# 시나리오02와 동일 패턴. 시나리오03 전용 시스템만 리셋.

import morld

# 대화 정책: S03 = hybrid (동적 생성 1차 레이어, infra-unification §2-5)
# S03은 python/__init__.py 가 없어 챕터 관리 모듈에서 선언한다.
from engine import dialogue_policy as _dialogue_policy
_dialogue_policy.set_policy(_dialogue_policy.POLICY_HYBRID)

# 현재 로드된 챕터
_current_chapter = None

# Limbo region 상수 (운반 시스템용 — Gate 없는 격리 공간)
LIMBO_REGION = 99
LIMBO_LOCATION = 0


def load_chapter(chapter_name, preserve_player=True):
    """
    챕터 로드

    기존 데이터를 초기화하고 새 챕터의 initialize() 호출

    Args:
        chapter_name: 챕터 이름 (예: "demo")
        preserve_player: True면 플레이어 데이터 유지 (기본값)
    """
    global _current_chapter

    print(f"[chapters] Loading chapter: {chapter_name}")

    # 1. 기존 데이터 초기화 (첫 로드가 아니면)
    if _current_chapter is not None:
        morld.clear_world()

    # 2. 환경 시스템 리셋
    #    시나리오03은 시나리오02의 공유 시스템을 사용하되
    #    필요한 모듈만 리셋
    _reset_systems()

    # 3. Limbo region 생성 (운반 시스템용)
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

    # 6. 챕터별 후처리 (복원 후 추가 설정)
    if hasattr(chapter_module, 'post_restore'):
        chapter_module.post_restore()

    # 7. EventSystem 위치 재초기화
    morld.reinitialize_locations()

    # 8. 현재 챕터 기록
    _current_chapter = chapter_name

    print(f"[chapters] Chapter '{chapter_name}' loaded successfully.")


def _reset_systems():
    """환경 시스템 리셋 (시나리오03용)"""
    # 공유 시스템 리셋 (존재하는 모듈만)
    _safe_reset("temperature")
    _safe_reset("humidity")
    _safe_reset("congestion")
    _safe_reset("sound")
    _safe_reset("fuel")
    _safe_reset("carry")
    _safe_reset("ground")
    _safe_reset("survival")
    _safe_reset("combat")
    _safe_reset("party")
    # TODO: 시나리오03 전용 시스템 리셋 추가


def _safe_reset(module_name):
    """모듈이 존재하면 reset() 호출"""
    try:
        mod = __import__(module_name)
        if hasattr(mod, 'reset'):
            mod.reset()
    except ImportError:
        pass


def get_current_chapter():
    """현재 로드된 챕터 이름 반환"""
    return _current_chapter


def reload_current_chapter():
    """현재 챕터 재로드 (디버그용)"""
    if _current_chapter:
        import sys
        module_name = f"chapters.{_current_chapter}"
        if module_name in sys.modules:
            del sys.modules[module_name]
        load_chapter(_current_chapter)
    else:
        print("[chapters] No chapter loaded yet.")
