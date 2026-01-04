# events/__init__.py - 이벤트 핸들러 패키지
#
# 역할:
# - 게임 이벤트 처리 (game_start, on_reach, on_meet)
# - 스크립트 함수 라우팅 (npc_talk 등)
# - 캐릭터 생성 함수 위임

from .handlers import (
    on_event_list,
    # 스크립트 함수들
    npc_talk,
    set_name,
    set_age,
    set_body,
    set_equipment,
    after_collapse,
)

# C#에서 호출하는 메인 진입점
__all__ = [
    'on_event_list',
    'npc_talk',
    'set_name',
    'set_age',
    'set_body',
    'set_equipment',
    'after_collapse',
]
