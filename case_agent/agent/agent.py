"""A minimal case agent that answers queries deterministically from the DB.

This agent does NOT call remote services and always cites SHA256 for evidence.
It is intentionally conservative: it returns 'insufficient evidence' when no
clear match is found.
"""
import logging
from typing import List, Dict, Any
from ..db.init_db import init_db, get_session
from ..db.models import EvidenceFile, ExtractedText, Entity
import requests
from ..config import OLLAMA_HOST
from .prompts import FACT_EXTRACTION_PROMPT, SYSTEM_PROMPT
import json

logger = logging.getLogger("case_agent.agent")


class CaseAgent:
    def __init__(self, db_path=None):
        init_db(db_path) if db_path is not None else init_db()
        self.session = get_session()

    def find_mentions(self, query: str) -> List[dict]:
        """Return list of matches with citations and a conservative confidence score."""
        q = query.lower()
        results = []
        texts = self.session.query(ExtractedText).all()
        for t in texts:
            if t.text and q in t.text.lower():
                # find the file
                file_row = self.session.query(EvidenceFile).filter_by(id=t.file_id).first()
                results.append({
                    "file_sha256": file_row.sha256,
                    "path": file_row.path,
                    "page": t.page,
                    "excerpt": t.text[max(0, t.text.lower().find(q) - 100): max(0, t.text.lower().find(q)) + 300],
                    "confidence": "medium",
                })
        if not results:
            return [{"message": "insufficient evidence", "confidence": "low"}]
        return results

    def find_media_mentions(self, query: str) -> List[dict]:
        """Search transcriptions for the query and return cited results.

        Each result includes: file_sha256, path, transcription_id, excerpt, segment (if matched), confidence
        """
        q = query.lower()
        results = []
        from ..db.models import Transcription
        trans = self.session.query(Transcription).all()
        for t in trans:
            text = (t.text or "").lower()
            matched = False
            excerpt = ""
            match_segment = None
            # check full text
            idx = text.find(q)
            if idx != -1:
                start = max(0, idx - 100)
                excerpt = t.text[start: idx + len(q) + 100]
                matched = True
            else:
                # check segments
                for seg in t.segments or []:
                    if q in (seg.get("text") or "").lower():
                        match_segment = {"start": seg.get("start"), "end": seg.get("end"), "text": seg.get("text")}
                        excerpt = seg.get("text")
                        matched = True
                        break
            if matched:
                file_row = self.session.query(EvidenceFile).filter_by(id=t.file_id).first()
                results.append({
                    "file_sha256": file_row.sha256,
                    "path": file_row.path,
                    "transcription_id": t.id,
                    "excerpt": excerpt,
                    "segment": match_segment,
                    "confidence": "medium",
                })
        if not results:
            return [{"message": "insufficient evidence", "confidence": "low"}]
        return results

    def list_entities(self, entity_type: str = None):
        q = self.session.query(Entity)
        if entity_type:
            q = q.filter_by(entity_type=entity_type)
        ents = q.all()
        out = []
        for e in ents:
            out.append({
                "entity_type": e.entity_type,
                "text": e.text,
                "provenance": e.provenance,
                "confidence": getattr(e, 'confidence', 'low'),
            })
        return out

    def answer_query(self, query: str, top_k: int = 10) -> Dict[str, Any]:
        """Answer a query from stored evidence deterministically.

        Returns a JSON-serializable dict with keys:
        - facts: [ {text, sources: [{sha256, path, page}], confidence} ]
        - provenance: list of sources
        - summary: short textual summary (not a hallucination)
        If no matches, returns {'message': 'insufficient evidence', 'confidence': 'low'}
        """
        q = query.lower()
        facts = []
        provenance = set()

        # Search extracted text
        texts = self.session.query(ExtractedText).all()
        for t in texts:
            if t.text and q in t.text.lower():
                file_row = self.session.query(EvidenceFile).filter_by(id=t.file_id).first()
                src = {"sha256": file_row.sha256, "path": file_row.path, "page": t.page}
                provenance.add(file_row.sha256)
                excerpt = t.text[max(0, t.text.lower().find(q) - 100): max(0, t.text.lower().find(q)) + len(q) + 100]
                facts.append({"text": excerpt.strip(), "sources": [src], "confidence": "medium"})

        # Search transcriptions
        from ..db.models import Transcription
        trans = self.session.query(Transcription).all()
        for t in trans:
            if t.text and q in t.text.lower():
                file_row = self.session.query(EvidenceFile).filter_by(id=t.file_id).first()
                src = {"sha256": file_row.sha256, "path": file_row.path}
                provenance.add(file_row.sha256)
                facts.append({"text": (t.text or '').strip()[:300], "sources": [src], "confidence": "low"})
            for seg in t.segments or []:
                if q in (seg.get('text') or '').lower():
                    file_row = self.session.query(EvidenceFile).filter_by(id=t.file_id).first()
                    src = {"sha256": file_row.sha256, "path": file_row.path}
                    provenance.add(file_row.sha256)
                    facts.append({"text": seg.get('text'), "sources": [src], "confidence": "low"})

        if not facts:
            return {"message": "insufficient evidence", "confidence": "low"}

        # Deduplicate and sort by confidence
        seen_texts = set()
        deduped = []
        conf_order = {"high": 3, "medium": 2, "low": 1}
        for f in facts:
            if f['text'] in seen_texts:
                continue
            seen_texts.add(f['text'])
            deduped.append(f)
        deduped.sort(key=lambda x: conf_order.get(x.get('confidence', 'low')), reverse=True)

        result = {"facts": deduped[:top_k], "provenance": list(provenance), "summary": f"Found {len(deduped[:top_k])} matching excerpts for query."}
        return result

    def _call_ollama(self, prompt: str, model: str = "mistral") -> str:
        """Call local Ollama instance and return raw text output.

        This is a best-effort integration. If Ollama is not available or the call
        fails, an exception is raised and caller should handle it.
        """
        url = OLLAMA_HOST.rstrip("/") + "/api/generate"
        payload = {"model": model, "prompt": prompt}
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            # Ollama may return the generated text in resp.text or resp.json(); be flexible
            try:
                data = resp.json()
                # try common keys
                for key in ("output", "results", "text", "content"):
                    if key in data:
                        v = data[key]
                        # If results is a list, join
                        if isinstance(v, list):
                            return "\n".join(map(str, v))
                        return str(v)
                # fallback to full json
                return json.dumps(data)
            except Exception:
                return resp.text
        except Exception as e:
            raise RuntimeError(f"Ollama call failed: {e}")

    def summarize_with_ollama(self, query: str, model: str = "mistral", max_text_chars: int = 3000) -> Dict[str, Any]:
        """Produce a strict JSON facts extraction using Ollama conditioned on local evidence.

        The prompt uses `FACT_EXTRACTION_PROMPT` from prompts.py and includes top matching
        text blocks; the model must return strict JSON with key `facts` per project rules.
        This method validates the returned JSON and returns it; if the returned content
        is not JSON or fails validation, an error dict is returned.
        """
        # Gather candidate text blocks (same as answer_query but limit size)
        snippets = []
        texts = self.session.query(ExtractedText).all()
        for t in texts:
            if t.text:
                snippets.append({"page": t.page, "path": t.provenance.get("path"), "sha256": t.provenance.get("sha256"), "text": t.text[:max_text_chars]})
        # Build prompt: include system-level guardrails and the fact extraction prompt
        prompt_parts = [SYSTEM_PROMPT, FACT_EXTRACTION_PROMPT, f"Query: {query}", "Text blocks:"]
        for s in snippets[:50]:
            prompt_parts.append(f"---\nsource: {s['sha256']} path: {s['path']} page: {s['page']}\n{s['text']}\n---")
        prompt = "\n".join(prompt_parts)

        try:
            raw = self._call_ollama(prompt, model=model)
        except Exception as e:
            return {"error": str(e), "message": "Ollama unavailable or failed"}

        # Try to parse JSON from raw output
        try:
            parsed = json.loads(raw)
            # Validate basic structure
            if not isinstance(parsed, dict) or "facts" not in parsed:
                return {"error": "invalid_format", "raw": raw}
            # Minimal validation of facts
            for f in parsed.get("facts", []):
                if "text" not in f or "sources" not in f:
                    return {"error": "invalid_fact_entry", "raw": raw}
            return parsed
        except Exception:
            # try to extract JSON substring
            try:
                start = raw.find('{')
                end = raw.rfind('}')
                if start != -1 and end != -1:
                    parsed = json.loads(raw[start:end+1])
                    return parsed
            except Exception:
                return {"error": "parse_failed", "raw": raw}

    def full_synopsis(self, model: str = "mistral") -> Dict[str, Any]:
        """Generate a full case synopsis combining top entities, timeline summary and issues.

        Uses local Ollama summarization when available; falls back to a conservative
        local summary if Ollama is unavailable.
        """
        # Build a compact context
        from ..reports import generate_extended_report
        rpt = generate_extended_report(None)
        ctx_parts = []
        ctx_parts.append("Top entities:\n")
        for e in rpt.get('top_entities', [])[:50]:
            ctx_parts.append(f"- {e.get('type')}: {e.get('text')} ({e.get('count')})")
        ctx_parts.append("\nTimeline summary:\n")
        ts = rpt.get('timeline_summary', {})
        ctx_parts.append(f"Earliest: {ts.get('earliest')}\nLatest: {ts.get('latest')}")
        ctx_parts.append("\nIssues:\n")
        issues = rpt.get('issues', {})
        ctx_parts.append(f"Files no text: {len(issues.get('files_no_text', []))}")
        ctx_parts.append(f"PDFs no text: {len(issues.get('pdfs_no_text', []))}")
        ctx_parts.append(f"Media no transcription: {len(issues.get('media_no_transcription', []))}")

        prompt = SYSTEM_PROMPT + "\nFull synopsis request:\n" + "\n".join(ctx_parts)
        try:
            raw = self._call_ollama(prompt, model=model)
            return {"source": "ollama", "summary": raw}
        except Exception as e:
            # fallback conservative summary
            summary = {
                "summary": f"Entities: {len(rpt.get('top_entities', []))}, Events: {rpt.get('counts', {}).get('events')}, Issues: {len(issues)}",
                "issues": issues,
            }
            return {"source": "local", "summary": summary}



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Query the case agent DB")
    parser.add_argument("--find", help="Find mentions of a phrase")
    parser.add_argument("--entities", help="List entity type (e.g., PERSON, DATE)")
    args = parser.parse_args()
    agent = CaseAgent()
    if args.find:
        print(agent.find_mentions(args.find))
    if args.entities:
        print(agent.list_entities(args.entities))
