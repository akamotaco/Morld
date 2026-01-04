# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 플래그 관리
# - 위치별/만남별 핸들러 라우팅

from .handlers import on_event_list

# C#에서 호출하는 메인 진입점
__all__ = ['on_event_list']
