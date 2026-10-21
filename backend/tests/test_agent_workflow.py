"""End-to-end agent tests: the assignment demo case and the representative consent flow."""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

import common

pytestmark = pytest.mark.skipif(not common.HAS_MODEL_KEY, reason="MODEL_API_TOKEN not set in backend/.env")

ASSIGNMENT_PROMPT = (
    "I'm the policyholder. My name is Margaret Chen, policy POL-9921. "
    "I'm calling about my denied healthcare claim from January. "
    "DOB is 1985-03-15, SSN last four is 4472."
)

EXPECTED_DENIAL = (
    "Claim CL-2048 (healthcare, created 2026-01-12) has status denied. "
    "The review file did not include the pathology report and the treating provider office note. "
    "Documents still needed: pathology report, office note. Appeal deadline: 2026-03-18."
)


def test_assignment_case_end_to_end():
    session = common.new_session()

    first = common.turn(session, ASSIGNMENT_PROMPT)
    assert "verify_profile" in first["tools"]
    assert first["phase"] in ("RESOLVE_INTENT", "PROCESS_CASE")

    second_prompt = "Yes - so why was it denied?"
    second = common.turn(session, second_prompt)
    if "get_claim" not in second["tools"]:
        second = common.turn(session, "Please pull up my denied healthcare claim and tell me why it was denied.")
    assert second["phase"] == "PROCESS_CASE"
    assert "pathology" in second["answer"].lower()

    assert_test(
        LLMTestCase(
            input=second_prompt,
            actual_output=second["answer"],
            expected_output=EXPECTED_DENIAL,
        ),
        [
            common.judge_eval(
                "Grounded denial reason",
                "The output states the claim was denied because the review file lacked the "
                "pathology report and the treating provider office note, consistent with the "
                "expected facts. It must not invent other reasons.",
                threshold=0.7,
                with_expected=True,
            ),
            common.judge_eval(
                "Uses remembered intent",
                "The output does not ask what the call is about or which claim is meant; it "
                "directly discusses the denied healthcare claim the caller already mentioned "
                "before verification.",
            ),
        ],
    )

    third_prompt = "What if I can't get the pathology report?"
    third = common.turn(session, third_prompt)
    assert "get_claim_guidance" in third["tools"]
    assert third["phase"] == "PROCESS_CASE"
    lowered = third["answer"].lower()
    assert any(word in lowered for word in ("replacement", "hospital", "lab", "provider"))

    assert_test(
        LLMTestCase(input=third_prompt, actual_output=third["answer"]),
        [
            common.judge_eval(
                "Grounded alternative advice",
                "The output advises getting a replacement copy from the hospital, lab or "
                "treating provider, or submitting the closest readable substitute, rather than "
                "inventing policy or promising re-approval.",
            ),
        ],
    )

    fourth_prompt = "Okay, that's all I needed. Thanks."
    fourth = common.turn(session, fourth_prompt)
    assert fourth["phase"] == "POST_PROCESS"

    assert_test(
        LLMTestCase(input=fourth_prompt, actual_output=fourth["answer"]),
        [
            common.judge_eval(
                "Offers email summary as a choice",
                "The output offers to email a summary of the conversation covering what was "
                "discussed, the claim status/outcome and next steps, and makes clear the caller "
                "can decline.",
            ),
        ],
    )

    fifth_prompt = "Yes, please send the email."
    fifth = common.turn(session, fifth_prompt)
    assert "send_email_summary" in fifth["tools"]

    assert_test(
        LLMTestCase(input=fifth_prompt, actual_output=fifth["answer"]),
        [
            common.judge_eval(
                "Confirms the summary email",
                "The output confirms the summary email was sent and the recap covers what was "
                "discussed, the claim outcome and the next steps (submitting the missing "
                "documents before the appeal deadline).",
            ),
        ],
    )


def test_representative_needs_consent():
    session = common.new_session()

    first_prompt = (
        "Hi, I'm David Chen, Margaret Chen's son. "
        "Why was her healthcare claim CL-2048 denied?"
    )
    first = common.turn(session, first_prompt)

    assert "find_representative" in first["tools"]
    assert "get_claim" not in first["tools"]
    assert first["phase"] in ("VERIFY_ID", "RESOLVE_INTENT")
    lowered = first["answer"].lower()
    assert "pathology" not in lowered and "office note" not in lowered

    assert_test(
        LLMTestCase(input=first_prompt, actual_output=first["answer"]),
        [
            common.judge_eval(
                "No disclosure without consent",
                "The output does not reveal claim details. It explains that the policy holder's "
                "consent is needed before her claim information can be shared.",
            ),
        ],
    )

    second_prompt = "Yes - mom is right here and she says you can share it."
    second = common.turn(session, second_prompt)
    if "get_claim" not in second["tools"]:
        second = common.turn(session, "Great, please go ahead and tell me why the claim was denied.")
    assert "consent" in second["tools"]
    assert "get_claim" in second["tools"]
    assert second["tools"].index("consent") < second["tools"].index("get_claim")
    assert "pathology" in second["answer"].lower()

    assert_test(
        LLMTestCase(
            input=second_prompt,
            actual_output=second["answer"],
            expected_output=EXPECTED_DENIAL,
        ),
        [
            common.judge_eval(
                "Grounded denial after consent",
                "The output explains the denial consistent with the expected facts: the missing "
                "pathology report and treating provider office note.",
                threshold=0.7,
                with_expected=True,
            ),
        ],
    )
