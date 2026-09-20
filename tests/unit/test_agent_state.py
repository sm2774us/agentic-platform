from agentic_platform.agents.state import AgentRole, AgentState


def test_agent_state_add_message() -> None:
    state = AgentState(task="do the thing")
    state.add(AgentRole.SUPERVISOR, "planning")
    assert state.messages[0].role == AgentRole.SUPERVISOR
    assert state.messages[0].content == "planning"
