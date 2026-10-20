"""
SOP gate tests at the service and tool layer.
Deterministic, fast, no API key needed.
"""

import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.schemas import Verification
from services import consent as consent_service
from services.claims import get_by_case_id, get_by_ids, search_claims
from services.email import send_summary
from services.guidelines import get_claim_guidance
from services.representative import find_representative
from services.verification import verify_policyholder


class TestVerification:
    def test_needs_three_matching_fields(self):
        record, matched = verify_policyholder(Verification(name="Margaret Chen", dob="1985-03-15"))
        assert record is None and matched == 2

        record, matched = verify_policyholder(
            Verification(name="Margaret Chen", dob="1985-03-15", phone="+16505212836")
        )
        assert record is not None and record["party_id"] == "P9" and matched == 3

    def test_aliases_count_as_matches(self):
        record, matched = verify_policyholder(
            Verification(name="Yaven Li", phone="+16505212830", email="yawen.li@example.com")
        )
        assert record is not None and record["party_id"] == "P13" and matched == 3

    def test_id_type_without_last4_does_not_count(self):
        record, matched = verify_policyholder(
            Verification(name="Margaret Chen", dob="1985-03-15", id_type="ssn_last4")
        )
        assert record is None and matched == 2

    def test_wrong_last4_does_not_verify(self):
        record, matched = verify_policyholder(
            Verification(name="Margaret Chen", dob="1985-03-15", id_type="ssn_last4", id_last4="0000")
        )
        assert record is None and matched == 2


class TestConsent:
    def test_pending_until_answered(self):
        result = consent_service.get_consent(uuid4().hex)
        assert result["status"] == "pending" and not result["escalate_to_human"]

    def test_grant_and_decline(self):
        granted = uuid4().hex
        assert consent_service.record_consent(granted, True)["status"] == "approved"
        assert consent_service.get_consent(granted)["status"] == "approved"

        declined = uuid4().hex
        assert consent_service.record_consent(declined, False)["status"] == "declined"

    def test_unanswered_consent_times_out_to_human(self):
        party = uuid4().hex
        for _ in range(5):
            result = consent_service.get_consent(party)
        assert result["status"] == "pending" and result["escalate_to_human"]


class TestClaimsRepository:
    def test_non_denied_claims_use_schema_defaults(self):
        claim = get_by_case_id("CL-2011")
        assert claim.status == "closed"
        assert claim.denial_reason == "" and claim.documents_needed == []

    def test_unknown_case(self):
        assert get_by_case_id("CL-9999") is None

    def test_search_ranks_relevant_denial_first(self):
        results = search_claims("P9", query="denied healthcare claim missing pathology report")
        assert results[0].case_id == "CL-2048"

    def test_structured_filters(self):
        assert [c.case_id for c in search_claims("P9", case_type="auto", status="open")] == ["CL-2102"]
        assert get_by_ids("P1") == []


class TestGuidelines:
    def test_submission_method_answer(self):
        bundle = get_claim_guidance(get_by_case_id("CL-2048"), "how do I submit the documents?")
        assert "portal" in bundle["followup_answer"].lower()

    def test_processing_time_answer(self):
        bundle = get_claim_guidance(get_by_case_id("CL-2048"), "how long does it take once I submit?")
        assert "less than a week" in bundle["followup_answer"]

    def test_unavailable_document_alternatives(self):
        bundle = get_claim_guidance(get_by_case_id("CL-2048"), None)
        assert "replacement copy" in bundle["followup_answer"]
        pathology = next(d for d in bundle["documents_needed"] if d["document"] == "pathology report")
        assert "hospital" in pathology["if_unavailable"] or "lab" in pathology["if_unavailable"]

    def test_guidance_tool_unknown_case(self):
        from agent.tools import get_claim_guidance as guidance_tool

        result = json.loads(guidance_tool.invoke({"case_id": "CL-9999"}))
        assert result["message"].startswith("No claim found")


class TestRepresentative:
    def test_find_by_name(self):
        reps = find_representative("David Chen")
        assert [(r.buyer_party_id, r.relationship) for r in reps] == [("P9", "son")]

    def test_narrowed_by_buyer(self):
        assert find_representative("David Chen", buyer_name="Margaret Chen")
        assert find_representative("David Chen", buyer_name="Someone Else") == []

    def test_unknown_representative(self):
        assert find_representative("Nobody Here") == []


class TestEmailSummary:
    def test_sends_to_policyholder_on_file(self):
        result = send_summary("P9", "Claim CL-2048 denied; send pathology report by 2026-03-18.")
        assert result["sent"] is True and result["to"] == "margaret@email.com"

    def test_unknown_party(self):
        assert send_summary("P999", "summary")["sent"] is False
