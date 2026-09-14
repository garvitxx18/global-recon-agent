from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .prompts import AGENT_INSTRUCTION
from .tools import (
    approve_recon_plan,
    discover_recon_plan,
    get_dataset,
    get_dataset_profile,
    get_recon_plan,
    get_recon_results,
    get_recon_run,
    start_recon_run,
    update_recon_plan,
)

MODEL = "gemini-2.5-flash"

root_agent = LlmAgent(
    name="global_recon",
    model=MODEL,
    description=(
        "Chat assistant that uses Global Recon APIs to profile two datasets, "
        "run Java reconciliation, and explain the break report."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=get_dataset),
        FunctionTool(func=get_dataset_profile),
        FunctionTool(func=discover_recon_plan),
        FunctionTool(func=get_recon_plan),
        FunctionTool(func=update_recon_plan),
        FunctionTool(func=approve_recon_plan),
        FunctionTool(func=start_recon_run),
        FunctionTool(func=get_recon_run),
        FunctionTool(func=get_recon_results),
    ],
)
