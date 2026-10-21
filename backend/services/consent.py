"""Consent store for representative access to a policy holder's claim details.

Status flow comes from consent_scenarios.json: pending -> approved when the
policy holder answers; a consent still pending after 5 checks (the timeout
scenario) escalates to a human. In-memory for the demo.
"""

import json
from pathlib import Path

CONSENT_SCENARIOS_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "consent_scenarios.json"
)


def _timeout_checks() -> int:
    with open(CONSENT_SCENARIOS_FIXTURE, "r", encoding="utf-8") as file:
        return json.load(file)["timeout"]["status_sequence"].count("pending")


_consents: dict[str, dict] = {}


def record_consent(buyer_party_id: str, granted: bool) -> dict:
    _consents[buyer_party_id] = {"status": "approved" if granted else "declined", "checks": 0}
    return _consents[buyer_party_id]


def get_consent(buyer_party_id: str) -> dict:
    record = _consents.setdefault(buyer_party_id, {"status": "pending", "checks": 0})

    if record["status"] == "pending":
        record["checks"] += 1

    return {
        "buyer_party_id": buyer_party_id,
        "status": record["status"],
        "checks": record["checks"],
        "escalate_to_human": record["status"] == "pending" and record["checks"] >= _timeout_checks(),
    }
