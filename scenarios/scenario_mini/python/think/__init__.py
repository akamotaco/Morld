# think/__init__.py — C# 규약: `import think; think.think_all()`
#
# 엔진 레지스트리를 그대로 재수출한다. 시나리오 확장이 필요 없으면
# 이 파일이 전부다 (S03/S02는 여기에 자체 BaseAgent 확장을 얹는다).

from engine.think import (  # noqa: F401
    _agents, _agent_classes,
    register_agent, unregister_agent, get_agent, get_all_agents,
    think_all, clear_all, clear_agents,
    register_agent_class, create_agent_for, get_registered_agent_ids,
    reset,
)
from engine.think_base import BaseAgent  # noqa: F401

# 캐릭터 AI 자동 등록 (캐릭터 표준 ③ — think/agents/)
from think import agents as _character_agents  # noqa: F401,E402
