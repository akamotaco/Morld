"""Agent 테스트"""
import morld


class _T:
    def __init__(self):
        morld.reset()
        from think.registry import clear_all
        clear_all()


class TestSecretaryAgent(_T):
    def test_create(self):
        from think.agents.secretary_agent import SecretaryAgent
        morld.add_unit(100, "비서", 0, 2, "male", [], [], "secretary")
        agent = SecretaryAgent(100)
        assert agent.unit_id == 100

    def test_think(self):
        from think.agents.secretary_agent import SecretaryAgent
        morld.add_unit(100, "비서", 0, 2, "male", [], [], "secretary")
        agent = SecretaryAgent(100)
        agent.think()
        # Should have inserted a job (not crash)
        job = morld.get_current_job(100)
        assert job is not None, "SecretaryAgent.think() should insert a job"


class TestSquadMemberAgent(_T):
    def test_create(self):
        from think.agents.squad_agent import SquadMemberAgent
        morld.add_unit(200, "Echo-01", 0, 0, "male", [], [], "echo_01")
        agent = SquadMemberAgent(200)
        assert agent.unit_id == 200

    def test_think_inserts_job(self):
        from think.agents.squad_agent import SquadMemberAgent
        morld.add_unit(200, "Echo-01", 0, 0, "male", [], [], "echo_01")
        agent = SquadMemberAgent(200)
        agent.think()
        # Should not crash, should insert idle job
        job = morld.get_current_job(200)
        assert job is not None, "SquadMemberAgent.think() should insert a job"


class TestAgentRegistry(_T):
    def test_register_and_get(self):
        from think import register_agent, get_agent
        from think.agents.secretary_agent import SecretaryAgent
        morld.add_unit(100, "비서", 0, 2, "male", [], [], "secretary")
        agent = SecretaryAgent(100)
        register_agent(100, agent)
        retrieved = get_agent(100)
        assert retrieved is agent

    def test_clear_agents(self):
        from think import register_agent, get_agent, clear_agents
        from think.agents.secretary_agent import SecretaryAgent
        morld.add_unit(100, "비서", 0, 2, "male", [], [], "secretary")
        agent = SecretaryAgent(100)
        register_agent(100, agent)
        clear_agents()
        assert get_agent(100) is None
