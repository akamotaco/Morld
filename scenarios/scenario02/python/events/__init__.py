# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 스크립트 함수 라우팅 (npc_talk 등)
# - 캐릭터 생성 함수 위임

from .handlers import on_event_list

# C#에서 호출하는 메인 진입점
# - on_event_list: 이벤트 시스템용 (직접 import)
# - 스크립트 함수들: @morld.register_script 데코레이터로 자동 등록
__all__ = ['on_event_list']
