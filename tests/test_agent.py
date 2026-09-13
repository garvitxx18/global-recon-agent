from app.global_recon.agent import MODEL, root_agent


def test_root_agent_is_configured():
    assert root_agent.name == "global_recon"
    assert MODEL == "gemini-2.5-flash"
    assert len(root_agent.tools) == 16
