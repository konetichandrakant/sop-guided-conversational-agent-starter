import json
from typing import Optional

from langchain_core.tools import tool

from agent.schemas import ClaimQuery, Verification
from services.claims import get_by_case_id, search_claims
from services.consent import get_consent, record_consent
from services.email import send_summary
from services.guidelines import get_claim_guidance as build_claim_guidance
from services.representative import find_representative as find_representative_record
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
        "Identify a caller who is a REPRESENTATIVE calling on behalf of a policy holder "
        "(e.g. 'I'm his son, calling about my mother's claim'). "
        "Call this IMMEDIATELY when the caller says they are calling for someone else - before asking "
        "any identity questions; representatives are found by their own name in the registry, not by "
        "the policy holder's PII. "
        "Looks the representative up by name, optionally narrowed by the policy holder's name or party id. "
        "Returns the representative record with buyer_party_id. This only identifies the caller: "
        "claim details may NOT be disclosed to a representative until the consent tool shows approved consent."
    )
)
def find_representative(
    rep_name: str,
    buyer_name: Optional[str] = None,
    buyer_party_id: Optional[str] = None,
) -> str:
    reps = find_representative_record(rep_name, buyer_name, buyer_party_id)

    if not reps:
        return json.dumps(
            {
                "found": False,
                "message": (
                    f"No representative named '{rep_name}' on file"
                    + (f" for policy holder {buyer_name or buyer_party_id}." if buyer_name or buyer_party_id else ".")
                ),
            }
        )

    return json.dumps({"found": True, "representatives": [rep.model_dump() for rep in reps]})


@tool(
    description=(
        "Record or check the policy holder's consent for a representative to receive their claim details. "
        "With granted=true/false, records the policy holder's spoken answer to the consent question - "
        "ONLY when the policy holder explicitly said yes or no; never assume or infer an answer. "
        "If the question has not been answered yet, omit granted to check the current status: pending, approved or declined, plus "
        "escalate_to_human once a pending consent has timed out. "
        "Never disclose claim details to a representative while consent is pending or declined."
    )
)
def consent(buyer_party_id: str, granted: Optional[bool] = None) -> str:
    result = record_consent(buyer_party_id, granted) if granted is not None else get_consent(buyer_party_id)

    if result["status"] == "pending" and result.get("escalate_to_human"):
        result["message"] = "Consent has stayed pending for too long; offer to transfer the caller to a human representative."

    return json.dumps(result)


@tool(
    description=(
        "Fetch the insurance claims of a verified policy holder. "
        "Call this tool only when the caller is already verified and a party_id is known; "
        "otherwise call verify_profile first (or find_representative plus consent for a representative). "
        "party_id is required and must be EXACTLY the id a previous tool returned (e.g. 'P9') - "
        "never invent, shorten or reformat one. "
        "Optional filters: case_id for one specific claim, "
        "case_type (healthcare/dental/auto), status (open/closed/denied), and a free-text "
        "query describing what the user asks about, e.g. 'denied healthcare claim missing "
        "pathology report'. Returns the matching claim records as JSON."
    )
)
def get_claim(data: ClaimQuery) -> str:
    claims = search_claims(
        party_id=data.party_id,
        case_id=data.case_id,
        case_type=data.case_type,
        status=data.status,
        query=data.query,
    )

    if not claims:
        return json.dumps(
            {
                "message": (
                    f"No claims found for party_id '{data.party_id}' matching the given criteria. "
                    "Use the exact party_id returned by verify_profile (e.g. 'P9') and do not guess claim details."
                )
            }
        )

    return json.dumps([claim.model_dump() for claim in claims])


@tool(
    description=(
        "Grounded guidance about a claim's missing documents: what each document must contain, "
        "what to do when the exact document is unavailable, and answers to follow-up questions "
        "like how/when/where to submit, how long review takes, file formats or receipt confirmation. "
        "Use during PROCESS_CASE for any document, submission or next-step question; "
        "answer only from what this returns."
    )
)
def get_claim_guidance(case_id: str, question: Optional[str] = None) -> str:
    claim = get_by_case_id(case_id)

    if claim is None:
        return json.dumps({"message": f"No claim found with case_id {case_id}."})

    return json.dumps(build_claim_guidance(claim, question))


@tool(
    description=(
        "Send the conversation summary email to the verified policy holder. "
        "Call this in POST_PROCESS only after the customer explicitly agreed to receive the email. "
        "party_id must be EXACTLY the id returned by verify_profile (e.g. 'P9') - never invent or reformat one. "
        "The summary must cover what was discussed, the claim status/outcome and the next steps."
    )
)
def send_email_summary(party_id: str, summary: str) -> str:
    return json.dumps(send_summary(party_id, summary))


TOOLS = [verify_profile, find_representative, consent, get_claim, get_claim_guidance, send_email_summary]
