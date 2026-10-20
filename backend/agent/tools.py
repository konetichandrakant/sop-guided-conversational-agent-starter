import json

from langchain_core.tools import tool

from agent.schemas import ClaimQuery, Verification
from services.claims import search_claims
from services.verification import verify_policyholder


@tool(
    description=(
        "Verify the identity of the caller from the PII they provided. "
        "Call this tool only when no party_id is known yet for the caller. "
        "At least 3 PII fields must match exactly among: full name, date of birth, "
        "phone, email, policy number, ID type + last 4 digits. "
        "On success returns the policyholder record including the party_id that get_claim needs."
    )
)
def verify_profile(data: Verification) -> str:
    """Identity check; returns the verified party_id or a failure the agent can act on."""
    record, matched = verify_policyholder(data)

    if record is None:
        return json.dumps(
            {
                "verified": False,
                "matched_pii_fields": matched,
                "message": (
                    f"Verification failed: {matched} of 3 required PII fields matched. "
                    "Ask the user for more identifying information (full name, date of birth, "
                    "phone, email, policy number or ID last 4 digits)."
                ),
            }
        )

    return json.dumps(
        {
            "verified": True,
            "party_id": record["party_id"],
            "name": record["name"],
            "matched_pii_fields": matched,
        }
    )


@tool(
    description=(
        "Fetch the insurance claims of a verified policy holder. "
        "Call this tool only when the caller is already verified and a party_id is known; "
        "otherwise call verify_profile first. "
        "party_id is required. Optional filters: case_id for one specific claim, "
        "case_type (healthcare/dental/auto), status (open/closed/denied), and a free-text "
        "query describing what the user asks about, e.g. 'denied healthcare claim missing "
        "pathology report'. Returns the matching claim records as JSON."
    )
)
def get_claim(data: ClaimQuery) -> str:
    """Claims lookup by party id plus optional filters; returns claim records as JSON."""
    claims = search_claims(
        party_id=data.party_id,
        case_id=data.case_id,
        case_type=data.case_type,
        status=data.status,
        query=data.query,
    )

    if not claims:
        return json.dumps(
            {"message": f"No claims found for party_id {data.party_id} matching the given criteria."}
        )

    return json.dumps([claim.model_dump() for claim in claims])
