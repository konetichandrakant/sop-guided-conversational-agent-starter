"""
Claims repository.

Backed by the app fixture (apps/insurance_claims/fixtures/claims.json).
The functions below are the repository interface the agent tools call:

  - get_by_ids()    exact lookups: always by party_id, narrowed by case_id
  - search_claims() id lookup + structured filters + free-text search

In production these same functions would run against a real database
(exact id lookups) and a search index or embeddings store (free-text
matching) instead of the fixture file.
"""

import json
import re
from pathlib import Path
from typing import Literal, Optional

from agent.schemas import Claim

CLAIMS_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "claims.json"
)


def _load_all() -> list[Claim]:
    """Repository read: parse every fixture row and validate it into a Claim model."""
    with open(CLAIMS_FIXTURE, "r", encoding="utf-8") as file:
        rows = json.load(file)
    return [Claim.model_validate(row) for row in rows]


def get_by_ids(party_id: str, case_id: Optional[str] = None) -> list[Claim]:
    """Exact lookup by party_id, optionally narrowed down to a single case_id."""
    claims = [claim for claim in _load_all() if claim.party_id == party_id]

    if case_id is not None:
        claims = [claim for claim in claims if claim.case_id == case_id]

    return claims


def get_by_case_id(case_id: str) -> Optional[Claim]:
    """Exact lookup of a single claim by its case_id, across all policy holders."""
    return next((claim for claim in _load_all() if claim.case_id == case_id), None)


def _searchable_text(claim: Claim) -> str:
    """Every free-text field of the claim, lowercased, for search to look at."""
    parts = [claim.summary, claim.denial_reason, claim.case_type, *claim.documents_needed]
    return " ".join(parts).lower()


def _match_score(claim: Claim, query: str) -> int:
    """
    Keyword score of a claim against the user's free-text request.

    Stand-in for real semantic search: counts how many query tokens appear in
    the claim's text fields. Swap this for an embedding/vector similarity
    search over the claim summary in production - the call site stays the same.
    """
    tokens = [token for token in re.split(r"\W+", query.lower()) if token]
    text = _searchable_text(claim)
    return sum(1 for token in tokens if token in text)


def search_claims(
    party_id: str,
    case_id: Optional[str] = None,
    case_type: Optional[Literal["healthcare", "dental", "auto"]] = None,
    status: Optional[Literal["open", "closed", "denied"]] = None,
    query: Optional[str] = None,
) -> list[Claim]:
    """
    Find claims for a policy holder in three steps:
      1. exact id lookup (party_id, and case_id when given)
      2. structured filters (case_type, status)
      3. keyword search over summary / denial reason / documents (query)

    Claims that match the query text rank above the rest; when nothing
    matches the query, the id-filtered claims are returned unranked.
    """
    claims = get_by_ids(party_id, case_id)

    if case_type is not None:
        claims = [claim for claim in claims if claim.case_type == case_type]

    if status is not None:
        claims = [claim for claim in claims if claim.status == status]

    if query:
        scored = [(claim, _match_score(claim, query)) for claim in claims]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        matched = [claim for claim, score in scored if score > 0]
        if matched:
            claims = matched

    return claims
