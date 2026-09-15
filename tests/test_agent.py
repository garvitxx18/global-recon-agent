from app.global_recon.agent import MODEL, root_agent
from app.global_recon.models import MappingSuggestion


def test_root_agent_is_mapping_only():
    assert root_agent.name == "global_recon"
    assert MODEL == "gemini-2.5-flash"
    assert root_agent.tools == []
    assert root_agent.output_schema is MappingSuggestion
