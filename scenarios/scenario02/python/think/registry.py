# think/registry.py - Agent 레지스트리 및 관리 함수
#
# 모듈 레벨 Agent 등록/조회/삭제 + 팩토리
# think/__init__.py에서 re-export됨.

import morld

# Agent 레지스트리: unit_id -> Agent 인스턴스
_agents = {}

# Agent 팩토리 레지스트리: unique_id -> Agent 클래스
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


def get_all_agents() -> dict:
    """등록된 모든 Agent 딕셔너리 반환 (unit_id -> Agent)"""
    return dict(_agents)


def think_all():
    """
    모든 등록된 Agent의 think() 호출

    C#의 ThinkSystem에서 호출됩니다.
    MovementSystem 실행 전에 호출되어 경로를 계획합니다.
    """
    if len(_agents) > 0:
        print(f"[think_all] Processing {len(_agents)} agents")
    for unit_id, agent in _agents.items():
        try:
            agent.think()
        except Exception as e:
            import traceback
            info = agent.get_info()
            name = info.get("name", str(unit_id)) if info else str(unit_id)
            print(f"[think] EXCEPTION in {name}(id={unit_id}): {e}")
            traceback.print_exc()
            # 예외 발생 시에도 safety net job 보장 (DES 무한루프 방지)
            try:
                agent._insert_idle_job("에러복구", agent._get_action_duration("safety_net"))
            except Exception:
                morld.insert_job(unit_id, {
                    "name": "에러복구",
                    "action": "stay",
                    "duration": 600_000,  # 10분 fallback
                })


def clear_all():
    """모든 Agent 제거"""
    _agents.clear()


def clear_agents():
    """모든 Agent 제거 (챕터 전환용 alias)"""
    _agents.clear()
    print("[think] All agents cleared.")


# ========================================
# 데코레이터 기반 자동 등록
# ========================================

def register_agent_class(unique_id):
    """
    데코레이터: Agent 클래스를 unique_id에 등록

    사용법:
        @register_agent_class("lina")
        class LinaAgent(BaseAgent):
            def think(self):
                ...
    """
    def decorator(cls):
        _agent_classes[unique_id] = cls
        return cls
    return decorator


def create_agent_for(unique_id, unit_id):
    """
    unique_id에 해당하는 Agent 인스턴스 생성

    Args:
        unique_id: 캐릭터 고유 ID (예: "lina")
        unit_id: 인스턴스 ID (정수)

    Returns:
        Agent 인스턴스 또는 None
    """
    if unique_id in _agent_classes:
        return _agent_classes[unique_id](unit_id)
    return None


def get_registered_agent_ids():
    """등록된 Agent unique_id 목록 반환"""
    return list(_agent_classes.keys())
