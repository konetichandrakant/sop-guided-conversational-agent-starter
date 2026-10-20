"""
Required-document guideline repository.

Backed by the app fixture (apps/insurance_claims/fixtures/required_document_guideline.json).
Grounds every document/how-to/next-step answer for PROCESS_CASE:
  - what each missing document must contain (document_guidance)
  - what to do when the exact document is unavailable (document_alternative_guidance)
  - follow-up answers for timing, method, format and receipt questions
    (claim_followup_guidance, matched by keyword, with a fallback)
"""

import json
from pathlib import Path
from typing import Optional

from agent.schemas import Claim

GUIDELINE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "apps" / "insurance_claims" / "fixtures" / "required_document_guideline.json"
)


def _load_guideline() -> dict:
    with open(GUIDELINE_FIXTURE, "r", encoding="utf-8") as file:
        return json.load(file)


def get_document_guidance(claim: Claim) -> dict:
    """Per-document requirements and alternatives for a claim's missing documents."""
    guideline = _load_guideline()
    alternatives = guideline["document_alternative_guidance"]

    documents = []
    for name in claim.documents_needed:
        documents.append(
            {
                "document": name,
                "guidance": guideline["document_guidance"].get(name, {}).get("en"),
                "if_unavailable": alternatives.get(name, alternatives["default"])["en"],
            }
        )

    return {
        "case_id": claim.case_id,
        "documents_needed": documents,
        "case_type_guidance": guideline["case_type_guidance"].get(claim.case_type, {}).get("en"),
        "general": guideline["default_guidance"]["en"],
    }


def _match_followup(guideline: dict, question: str) -> Optional[str]:
    """First follow-up template whose keyword phrase appears in the question."""
    text = question.lower()
    for entry in guideline["claim_followup_guidance"]:
        if any(phrase in text for phrase in entry.get("match_any", [])):
            return entry["en"]
    return None


def get_followup_answer(claim: Claim, question: Optional[str] = None) -> str:
    """
    Grounded answer for a follow-up question about a claim's documents.
    Keyword-matched when the question fits a known topic; falls back to the
    missing-materials guidance (claim has outstanding documents) or the
    generic fallback text.
    """
    guideline = _load_guideline()

    answer = _match_followup(guideline, question) if question else None
    if answer is None:
        if claim.documents_needed:
            answer = next(
                entry["en"]
                for entry in guideline["claim_followup_guidance"]
                if entry["topic"] == "missing_required_material_alternatives"
            )
        else:
            answer = guideline["claim_followup_fallback"]["en"]

    return answer.format(
        case_id=claim.case_id,
        documents=", ".join(claim.documents_needed) if claim.documents_needed else "the requested files",
        average_processing_time_after_submission=guideline["claim_followup_settings"][
            "average_processing_time_after_submission"
        ]["en"],
    )


def get_claim_guidance(claim: Claim, question: Optional[str] = None) -> dict:
    """Full guidance bundle for a claim: document requirements + follow-up answer."""
    return {
        **get_document_guidance(claim),
        "followup_answer": get_followup_answer(claim, question),
    }
