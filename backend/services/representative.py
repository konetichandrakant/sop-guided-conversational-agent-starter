"""Representative repository over the fixtures JSON."""

import json
from pathlib import Path
from typing import Optional

from agent.schemas import Representative

REPRESENTATIVES_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "representatives.json"
)


def _load_all() -> list[Representative]:
    with open(REPRESENTATIVES_FIXTURE, "r", encoding="utf-8") as file:
        rows = json.load(file)
    return [Representative.model_validate(row) for row in rows]


def find_representative(
    rep_name: str,
    buyer_name: Optional[str] = None,
    buyer_party_id: Optional[str] = None,
) -> list[Representative]:
    reps = [rep for rep in _load_all() if rep.rep_name.lower() == rep_name.strip().lower()]

    if buyer_party_id is not None:
        reps = [rep for rep in reps if rep.buyer_party_id == buyer_party_id]
    if buyer_name is not None:
        reps = [rep for rep in reps if rep.buyer_name.lower() == buyer_name.strip().lower()]

    return reps
