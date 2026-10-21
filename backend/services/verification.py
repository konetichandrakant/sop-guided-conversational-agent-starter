"""Policyholder verification over the fixtures JSON."""

import json
from pathlib import Path
from typing import Optional

from agent.schemas import Verification

POLICYHOLDERS_FIXTURE = (
    Path(__file__).resolve().parents[2] / "apps" / "insurance_claims" / "fixtures" / "policyholders.json"
)

# at least 3 PII info (Full name, DOB, Phone, Email, SSN last 4 digits)
MIN_PII_MATCHES = 3


def _load_all() -> list[dict]:
    with open(POLICYHOLDERS_FIXTURE, "r", encoding="utf-8") as file:
        return json.load(file)


def _values_with_aliases(record: dict, field: str, aliases_field: str) -> set[str]:
    values = {record.get(field, "")} | set(record.get(aliases_field, []))
    return {str(value).lower() for value in values}


def _count_pii_matches(record: dict, provided: Verification) -> int:
    # id_type alone proves nothing - it only counts together with its id_last4
    matched = 0

    if provided.name and provided.name.lower() in _values_with_aliases(record, "name", "name_aliases"):
        matched += 1
    if provided.dob and provided.dob == record.get("dob"):
        matched += 1
    if provided.phone and provided.phone.lower() in _values_with_aliases(record, "phone", "phone_aliases"):
        matched += 1
    if provided.email and provided.email.lower() in _values_with_aliases(record, "email", "email_aliases"):
        matched += 1
    if provided.policy_number and provided.policy_number == record.get("policy_number"):
        matched += 1
    if (
        provided.id_type
        and provided.id_last4
        and provided.id_type == record.get("id_type")
        and provided.id_last4 == record.get("id_last4")
    ):
        matched += 1

    return matched


def verify_policyholder(data: Verification) -> tuple[Optional[dict], int]:
    best_record: Optional[dict] = None
    best_matches = 0

    for record in _load_all():
        matched = _count_pii_matches(record, data)
        if matched > best_matches:
            best_record, best_matches = record, matched

    if best_matches >= MIN_PII_MATCHES:
        return best_record, best_matches
    return None, best_matches
