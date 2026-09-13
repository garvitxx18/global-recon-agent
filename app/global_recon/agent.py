from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from .prompts import AGENT_INSTRUCTION
from .tools import (
    approve_recon_plan,
    discover_recon_plan,
    get_dataset,
    get_dataset_profile,
    get_dataset_records,
    get_job,
    get_recon_plan,
    get_recon_results,
    get_recon_run,
    get_recon_summary,
    list_comparisons,
    save_comparison,
    start_recon_run,
    update_recon_plan,
    upload_dataset,
    wait_for_recon_job,
)

# Replace this string later with an enterprise model factory if needed.
MODEL = "gemini-2.5-flash"

root_agent = LlmAgent(
    name="global_recon",
    model=MODEL,
    description=(
        "Chat assistant that uses Global Recon APIs to profile two datasets, "
        "suggest a mapping, run Java reconciliation, and explain the break report."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        FunctionTool(func=upload_dataset),
        FunctionTool(func=get_dataset),
        FunctionTool(func=get_dataset_profile),
        FunctionTool(func=get_dataset_records),
        FunctionTool(func=discover_recon_plan),
        FunctionTool(func=get_job),
        FunctionTool(func=wait_for_recon_job),
        FunctionTool(func=get_recon_plan),
        FunctionTool(func=update_recon_plan),
        FunctionTool(func=approve_recon_plan),
        FunctionTool(func=start_recon_run),
        FunctionTool(func=get_recon_run),
        FunctionTool(func=get_recon_summary),
        FunctionTool(func=get_recon_results),
        FunctionTool(func=save_comparison),
        FunctionTool(func=list_comparisons),
    ],
)
