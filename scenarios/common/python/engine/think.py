# think.py — NPC AI 레지스트리 및 디스패처
#
# 모든 시나리오 공통 think 시스템.
# - Agent 등록/조회/삭제
# - think_all(): 매 Step 전체 Agent의 think() 호출
# - 데코레이터 기반 Agent 클래스 자동 등록
#
# C# ThinkSystem / advance_time_des에서 호출.

import morld


# Agent 레지스트리: unit_id → Agent 인스턴스
_agents = {}

# Agent 팩토리 레지스트리: unique_id → Agent 클래스
_agent_classes = {}


def register_agent(unit_id, agent):
    """Agent 등록"""
    _agents[unit_id] = agent


def unregister_agent(unit_id):
    """Agent 등록 해제"""
    if unit_id in _agents:
        del _agents[unit_id]


def get_agent(unit_id):
    """Agent 조회"""
    return _agents.get(unit_id)


def get_all_agents():
    """등록된 모든 Agent 딕셔너리 반환 (unit_id → Agent)"""
    return dict(_agents)


def think_all():
    """모든 등록된 Agent의 think() 호출

    C#의 ThinkSystem / advance_time_des에서 호출.
    Agent가 없으면 아무것도 하지 않음.
    """
    for unit_id, agent in _agents.items():
        try:
            agent.think()
        except Exception as e:
            info = agent.get_info() if hasattr(agent, 'get_info') else None
            name = info.get("name", str(unit_id)) if info else str(unit_id)
            print(f"[think] EXCEPTION in {name}(id={unit_id}): {type(e).__name__}: {e}")
            try:
                import traceback
                traceback.print_exc()
            except Exception:
                pass
            # 예외 시 safety net (DES 무한루프 방지)
            try:
                agent._insert_idle_job("에러복구", agent._get_action_duration("safety_net"))
            except Exception:
                morld.insert_job(unit_id, {
                    "name": "에러복구",
                    "action": "stay",
                    "duration": 600_000,
                })


def clear_all():
    """모든 Agent 제거"""
    _agents.clear()


def clear_agents():
    """모든 Agent 제거 (챕터 전환용 alias)"""
    _agents.clear()


# ========================================
# 데코레이터 기반 자동 등록
# ========================================

def register_agent_class(unique_id):
    """데코레이터: Agent 클래스를 unique_id에 등록

    사용법:
        @register_agent_class("lina")
        class LinaAgent(BaseAgent):
            ...
    """
    def decorator(cls):
        _agent_classes[unique_id] = cls
        return cls
    return decorator


def create_agent_for(unique_id, unit_id):
    """unique_id에 해당하는 Agent 인스턴스 생성"""
    if unique_id in _agent_classes:
        return _agent_classes[unique_id](unit_id)
    return None


def get_registered_agent_ids():
    """등록된 Agent unique_id 목록 반환"""
    return list(_agent_classes.keys())


def reset():
    """챕터 전환 초기화"""
    _agents.clear()
    _agent_classes.clear()
