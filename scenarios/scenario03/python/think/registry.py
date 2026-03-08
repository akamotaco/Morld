"""Agent 레지스트리 (시나리오03 최소 구현)"""

# unit_id -> agent instance
_agents = {}
# unique_id -> agent class
_agent_classes = {}


def register_agent(unit_id, agent):
    _agents[unit_id] = agent


def unregister_agent(unit_id):
    _agents.pop(unit_id, None)


def get_agent(unit_id):
    return _agents.get(unit_id)


def get_all_agents():
    return dict(_agents)


def think_all():
    for agent in list(_agents.values()):
        agent.think()


def clear_agents():
    _agents.clear()


def clear_all():
    _agents.clear()
    _agent_classes.clear()


def register_agent_class(unique_id):
    def decorator(cls):
        _agent_classes[unique_id] = cls
        return cls
    return decorator


def create_agent_for(unique_id, unit_id):
    cls = _agent_classes.get(unique_id)
    if cls:
        return cls(unit_id)
    return None


def get_registered_agent_ids():
    return list(_agent_classes.keys())
