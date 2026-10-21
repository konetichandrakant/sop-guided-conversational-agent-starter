"""Mock email sender: records the summary to the policy holder's address on file."""

import json
from datetime import datetime
from pathlib import Path

from services.verification import _load_all as load_policyholders

_SENT_SUMMARIES: list[dict] = []


def send_summary(party_id: str, summary: str) -> dict:
    policyholder = next((row for row in load_policyholders() if row.get("party_id") == party_id), None)

    if policyholder is None:
        return {"sent": False, "message": f"No policy holder found for party_id {party_id}."}

    record = {
        "to": policyholder.get("email"),
        "party_id": party_id,
        "summary": summary,
        "sent_at": datetime.now().isoformat(timespec="seconds"),
    }
    _SENT_SUMMARIES.append(record)

    return {"sent": True, **record}
