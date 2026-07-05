# think/registry.py — engine.think 재수출 shim (S03)
# 과거 자체 레지스트리 사본 → U1에서 engine 정본으로 단일화.
# `from think.registry import ...` 기존 import 경로 호환용.
from engine.think import (  # noqa: F401
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
    reset,
)
