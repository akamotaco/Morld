# think/registry.py — engine.think 재수출 shim (S02)
#
# 과거 이 파일은 자체 _agents/_agent_classes 사본을 가진 독립 레지스트리였다.
# think/__init__.py가 engine.think를 re-export하면서 등록은 engine 쪽으로 가는데,
# `from think.registry import get_agent/_agents` 경로(party_squad.py, combat_mixin.py)는
# 빈 사본을 조회하는 잠복 분기 버그가 있었다 — U1에서 동일 객체 재수출로 해소.
from engine.think import (  # noqa: F401
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
    reset,
)
