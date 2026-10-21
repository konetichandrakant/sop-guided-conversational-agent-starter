from typing import Literal, Optional
from pydantic import BaseModel, Field

# CLAIMS:
# {
# "case_id": "CL-2048",
# "party_id": "P9",
# "case_type": "healthcare",
# "created_at": "2026-01-12",
# "status": "denied",
# "summary": "Healthcare claim denied due to missing pathology report and office note",
# "denial_reason": "the review file did not include the pathology report and the treating provider office note",
# "documents_needed": [
#     "pathology report",
#     "office note"
# ],
# "appeal_deadline": "2026-03-18",
# "expected_reimbursement_amount": "0.00",
# "allowed_max_amount": "1450.00",
# "net_pay": "0.00",
# "net_fee": "1450.00"
# }

class Claim(BaseModel):
    case_id: str = Field(description="Unique identifier of the claim, e.g. CL-2048", pattern="^CL-.+")
    party_id: str = Field(description="Party ID of the policy holder who filed the claim", pattern="^P.+")
    case_type: Literal["healthcare", "dental", "auto"] = Field(description="Category of the claim")
    created_at: str = Field(description="Date the claim was created, YYYY-MM-DD")
    status: Literal["open", "closed", "denied"] = Field(description="Current status of the claim")
    summary: str = Field(description="Brief summary of what the claim is about")
    # non-denied claims have no denial fields in the fixture
    denial_reason: str = Field(default="", description="Reason the claim was denied; empty string if the claim was not denied")
    documents_needed: list[str] = Field(default_factory=list, description="Documents still required to process or appeal the claim, e.g. pathology report, office note")
    appeal_deadline: str = Field(default="", description="Deadline to file an appeal, YYYY-MM-DD; empty string if not applicable")
    expected_reimbursement_amount: str = Field(description="Amount the insurer is expected to pay, e.g. 1450.00. Used in practice management systems (PMS) to compare with actual payments during reconciliation.")
    allowed_max_amount: str = Field(description="Maximum amount an in-network insurer will pay for a covered service, e.g. 1450.00")
    net_pay: str = Field(description="Final amount the insurer actually paid for the claim, e.g. 0.00")
    net_fee: str = Field(description="Fee schedule rate for the billed service adjusted for contractual obligations, e.g. 1450.00")

# what the agent sends into get_claim: party_id comes from verify_profile,
# the rest is optional context from the user's message (Claim is the output)
class ClaimQuery(BaseModel):
    party_id: str = Field(description="Party ID of the policy holder", pattern="^P.+")
    case_id: Optional[str] = Field(default=None, description="One specific case ID if the user named it, e.g. CL-2048", pattern="^CL-.+")
    case_type: Optional[Literal["healthcare", "dental", "auto"]] = Field(default=None, description="Filter by claim category")
    status: Optional[Literal["open", "closed", "denied"]] = Field(default=None, description="Filter by claim status")
    query: Optional[str] = Field(default=None, description="Free text of what the user asks about, e.g. 'denied healthcare claim missing pathology report'")

# POLICYHOLDER ( VERIFICATION ):
# {
# "party_id": "P9",
# "name": "Margaret Chen",
# "policy_number": "POL-9921",
# "dob": "1985-03-15",
# "id_type": "ssn_last4",
# "id_last4": "4472",
# "phone": "+16505212836",
# "email": "margaret@email.com"
# }

# at least 3 PII info (Full name, DOB, Phone, Email, SSN last 4 digits)
class Verification(BaseModel):
    party_id: Optional[str] = Field(default=None, description="Party ID of the policy holder if already known")
    name: Optional[str] = Field(default=None, description="Name of the policy holder")
    policy_number: Optional[str] = Field(default=None, description="Policy number of policy holder")
    dob: Optional[str] = Field(default=None, description="Date of birth of the policy holder")
    id_type: Optional[str] = Field(default=None, description="Type of ID used for verification, e.g. ssn_last4")
    id_last4: Optional[str] = Field(default=None, description="Last 4 digits of the ID")
    phone: Optional[str] = Field(default=None, description="Phone number of the policy holder")
    email: Optional[str] = Field(default=None, description="Email of the policy holder")

# REPRESENTATIVE
# [
#   {
#     "rep_name": "David Chen",
#     "relationship": "son",
#     "buyer_name": "Margaret Chen",
#     "buyer_party_id": "P9"
#   }
# ]

class Representative(BaseModel):
    rep_name: str = Field(description="Name of the representative")
    relationship: str = Field(description="Relationship of the representative to the policy holder, e.g. son")
    buyer_name: str = Field(description="Name of the policy holder the representative is acting for")
    buyer_party_id: str = Field(description="Party id of the policy holder the representative is acting for", pattern="^P.+")
