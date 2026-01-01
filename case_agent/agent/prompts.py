"""Prompt templates for optional local LLM usage.

These prompts are provided as structured templates for advanced users who
run local LLMs; core pipeline behavior remains deterministic and does not
require an LLM. Prompts are kept offline and should not leak sensitive data.
"""

FACT_EXTRACTION_PROMPT = '''
You are a strict evidence extractor. Given the provided text blocks and their provenance, extract explicit facts only. Output must be valid JSON with keys: facts: [ {"text": ..., "sources": [{"sha256": ..., "path": ...}], "confidence": "low|medium|high"} ]

Rules:
- Never invent facts.
- If a fact is uncertain or requires inference, set confidence to "low" and mark as "inference": true.
- Do not access any external resources.
'''

# System-level guardrail prompt for local LLMs
SYSTEM_PROMPT = '''
You are a legal analysis assistant operating on extracted evidence. You must:
- Cite evidence for every claim
- Separate facts from inferences
- Never identify real individuals unless explicitly labeled
- Output structured JSON only
'''

# Event extraction prompt used for structured event generation
EVENT_PROMPT = '''
Given the following evidence text, extract events.

Rules:
- Only extract what is explicitly supported
- Do not speculate
- If actor is unclear, use UNKNOWN

Output format:
{
  "events": [
    {
      "actor": "",
      "action": "",
      "timestamp": "",
      "confidence": "High|Medium|Low"
    }
  ]
}

TEXT:
'''

