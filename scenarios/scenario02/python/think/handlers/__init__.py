"""NPC 인터럽트 핸들러 — think/__init__.py에서 분리된 모듈 레벨 핸들러

식사/배변, 체온(추위/더위/착의), 성욕(자위/플레이어탐색), 사회(대화/선물) 핸들러.
BaseAgent 클래스 내부에서 함수명으로 직접 호출됨.
"""
from .eat import _handle_eat, _handle_excretion
from .thermal import _handle_cold, _handle_hot, _handle_clothing, _is_dressed
from .self_comfort import (
    _handle_self_comfort, _handle_seek_player,
    _SELF_COMFORT_COOLDOWN_MS, _SELF_COMFORT_INTERRUPT_COOLDOWN_MS,
)
from .social import (
    _handle_socialize, _handle_gift,
    _find_socialize_target, _find_gift_item, _find_gift_target,
    _SOCIALIZE_COOLDOWN_MS, _SOCIALIZE_SOCIAL_THRESHOLD,
)
