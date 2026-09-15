from google.adk.agents import LlmAgent
from google.genai import types

from .models import MappingSuggestion
from .prompts import AGENT_INSTRUCTION

MODEL = "gemini-2.5-flash"

root_agent = LlmAgent(
    name="global_recon",
    model=MODEL,
    description="Suggests recon join keys and field mappings as JSON. Java owns MATCHED / BREAK.",
    instruction=AGENT_INSTRUCTION,
    output_schema=MappingSuggestion,
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
)
