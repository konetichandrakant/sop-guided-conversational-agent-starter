"""Claims repository over the fixtures JSON."""

import json
import re
from pathlib import Path
from typing import Literal, Optional

from agent.schemas import Claim

CLAIMS_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "claims.json"
)


def _load_all() -> list[Claim]:
    with open(CLAIMS_FIXTURE, "r", encoding="utf-8") as file:
        rows = json.load(file)
    return [Claim.model_validate(row) for row in rows]


def get_by_ids(party_id: str, case_id: Optional[str] = None) -> list[Claim]:
    claims = [claim for claim in _load_all() if claim.party_id == party_id]

    if case_id is not None:
        claims = [claim for claim in claims if claim.case_id == case_id]

    return claims


def get_by_case_id(case_id: str) -> Optional[Claim]:
    return next((claim for claim in _load_all() if claim.case_id == case_id), None)


def _searchable_text(claim: Claim) -> str:
    parts = [claim.summary, claim.denial_reason, claim.case_type, *claim.documents_needed]
    return " ".join(parts).lower()


def _match_score(claim: Claim, query: str) -> int:
    # keyword scoring; swap for embedding similarity if this ever needs real semantic search
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
