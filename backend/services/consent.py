"""
Consent store for representative access to a policy holder's claim details.

The status flow comes from the fixture (consent_scenarios.json):
  - default scenario: pending -> approved once the policy holder answers
  - timeout scenario: consent that stays pending across repeated checks
    (5 in the fixture) should escalate to a human representative

In-memory for the demo; a production build would persist consent records
with audit trails instead.
"""

import json
from pathlib import Path

CONSENT_SCENARIOS_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "consent_scenarios.json"
)


def _load_scenarios() -> dict:
    with open(CONSENT_SCENARIOS_FIXTURE, "r", encoding="utf-8") as file:
        return json.load(file)


# How many unanswered checks a pending consent survives before escalation.
def _timeout_checks() -> int:
    return _load_scenarios()["timeout"]["status_sequence"].count("pending")


# buyer_party_id -> {"status": "pending"|"approved"|"declined", "checks": int}
_consents: dict[str, dict] = {}


def record_consent(buyer_party_id: str, granted: bool) -> dict:
    """Record the policy holder's answer to the consent request."""
    _consents[buyer_party_id] = {"status": "approved" if granted else "declined", "checks": 0}
    return _consents[buyer_party_id]


def get_consent(buyer_party_id: str) -> dict:
    """
    Check consent status. Every check while still pending counts toward the
    timeout scenario, so repeated unanswered checks eventually escalate.
    """
    record = _consents.setdefault(buyer_party_id, {"status": "pending", "checks": 0})

    if record["status"] == "pending":
        record["checks"] += 1

    return {
        "buyer_party_id": buyer_party_id,
        "status": record["status"],
        "checks": record["checks"],
        "escalate_to_human": record["status"] == "pending" and record["checks"] >= _timeout_checks(),
    }
