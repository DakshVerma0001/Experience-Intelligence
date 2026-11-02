"""Fake local LLM provider for tests - never calls a real network service.
Returns canned, schema-valid JSON so the extraction/enrichment pipeline can be
exercised deterministically without requiring a running Ollama instance."""
from __future__ import annotations

import json

from app.ai.base import LLMProvider, LLMResponse


class FakeLLMProvider(LLMProvider):
    model = "fake-local-model"

    def is_available(self) -> tuple[bool, str]:
        return True, "Fake provider always available."

    def generate(self, prompt: str, *, temperature: float = 0.1) -> LLMResponse:
        if "SCHEMA:" in prompt and '"keywords"' in prompt:
            return LLMResponse(raw_text=self._keywords_response(prompt), model=self.model)
        if '"summary"' in prompt:
            return LLMResponse(raw_text=json.dumps({"summary": self._fake_summary(prompt)}), model=self.model)
        return LLMResponse(raw_text=self._extraction_response(prompt), model=self.model)

    def _extraction_response(self, prompt: str) -> str:
        text = prompt.lower()
        data = {
            "project_name": None,
            "short_form": None,
            "client_type": "Government" if "government" in text or "nabard" in text else None,
            "project_status": "Ongoing" if "ongoing" in text else ("Completed" if "completed" in text else None),
            "client_name": None,
            "project_description": "AI-generated description based on the source segment." if len(text) > 20 else None,
            "actual_services": "System design, development, and implementation services." if "gis" in text or "erp" in text else None,
            "associated_consultants": None,
            "senior_professional_staff": None,
            "country": "India" if "india" in text else None,
            "state_ut": None,
            "confidence": 0.9,
        }
        if "nabard" in text:
            data["client_name"] = "NABARD"
        if "pacs" in text:
            data["project_name"] = "National Level PACS Software Vendor"
        return json.dumps(data)

    def _keywords_response(self, prompt: str) -> str:
        text = prompt.lower()
        keywords = []
        if "gis" in text:
            keywords.append({"keyword": "GIS", "category": "Technology", "description": "Geographic Information System.", "aliases": []})
        if "erp" in text:
            keywords.append({"keyword": "ERP", "category": "Technology", "description": "Enterprise Resource Planning.", "aliases": []})
        if "pacs" in text:
            keywords.append({"keyword": "PACS", "category": "Domain", "description": "Primary Agricultural Credit Societies.", "aliases": []})
        if not keywords:
            keywords.append({"keyword": "Consulting", "category": "Service", "description": "General consulting services.", "aliases": []})
        return json.dumps({"keywords": keywords})

    def _fake_summary(self, prompt: str) -> str:
        return "Government sector digital transformation project delivering system design and implementation services."
