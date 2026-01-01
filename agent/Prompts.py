# Compatibility shim — import canonical prompts from the case_agent package
from case_agent.agent.prompts import FACT_EXTRACTION_PROMPT, SYSTEM_PROMPT, EVENT_PROMPT

__all__ = ["FACT_EXTRACTION_PROMPT", "SYSTEM_PROMPT", "EVENT_PROMPT"]
