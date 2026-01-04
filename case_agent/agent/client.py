"""Lightweight client that abstracts local CaseAgent vs remote HTTP agent endpoints.

Used by the GUI and tests so the UI can switch between a local DB-backed agent
or a remote HTTP agent exposed by `case_agent.api.create_app`.
"""

from __future__ import annotations

from typing import Optional


class AgentClient:
    def __init__(self, db_path: Optional[str] = None, api_url: Optional[str] = None):
        self.db_path = db_path
        self.api_url = api_url.rstrip("/") if api_url else None
        self._local_agent = None
        if not self.api_url:
            # lazy import to avoid heavy deps when only using remote mode
            from .agent import CaseAgent

            self._local_agent = CaseAgent(db_path=db_path)

    def _get_json(self, path: str, params: Optional[dict] = None) -> dict:
        if not self.api_url:
            raise RuntimeError("AgentClient: not in remote mode")
        import requests

        url = f"{self.api_url}{path}"
        r = requests.get(url, params=params or {}, timeout=10)
        r.raise_for_status()
        return r.json()

    def answer_query(self, query: str, top_k: int = 10) -> dict:
        if self._local_agent:
            return self._local_agent.answer_query(query, top_k=top_k)
        return self._get_json("/agent/query", params={"query": query, "top_k": top_k})

    def find_mentions(self, query: str) -> list:
        if self._local_agent:
            return self._local_agent.find_mentions(query)
        return self._get_json("/agent/find", params={"query": query}).get("result", [])

    def people_report(self) -> dict:
        if self._local_agent:
            # reuse existing report generator for local case
            from ..reports import generate_extended_report

            rpt = generate_extended_report(self.db_path)
            return {
                "people": rpt.get("people", []),
                "top_subjects": rpt.get("top_subjects", []),
            }
        return self._get_json("/reports/people")
