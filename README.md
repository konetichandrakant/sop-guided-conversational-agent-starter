# SOP-Guided Insurance Claims Agent

A claims support agent that follows a fixed SOP while talking naturally. The workflow
runs in four phases — VERIFY_ID → RESOLVE_INTENT → PROCESS_CASE → POST_PROCESS — and
each phase gets a different amount of freedom: verification is a hard gate (no claim
details until the caller matches at least 3 PII fields), while intent resolution and
case processing may interpret messy language and answer grounded follow-ups.

## What does what

| Phase | What happens |
|---|---|
| VERIFY_ID | Caller matches 3+ PII fields (name, DOB, phone, email, policy number, or ID type + last 4). A representative is identified by name and additionally needs the policy holder's recorded consent. Nothing about claims is disclosed until this passes. |
| RESOLVE_INTENT | Uses what the caller already said (even a hint dropped during verification, like "my denied January claim") or asks what the call is about, then pulls the matching claim. |
| PROCESS_CASE | Answers only from the claim records and the document guideline fixture. Free phrasing, grounded facts. |
| POST_PROCESS | Offers an email summary (what was discussed, claim outcome, next steps); the caller sends it or skips it. |

The gates live in the tools, not just the prompt: `verify_profile` only returns a
`party_id` after 3 exact matches, `get_claim` needs that id, `consent` must read
`approved` before a representative sees anything, and every reply reports its phase —
the stepper in the UI shows where the conversation is in real time.

```
backend/
  agent/       agent loop, system prompt (the SOP), tools, pydantic schemas
  services/    claim/policyholder/representative lookups, consent store,
               document guidelines, email summary - all over JSON fixtures
  schema/      API request/response models
  api/         FastAPI app (POST /chat) - also serves the UI
  tests/       service gate tests + DeepEval agent suites
  eval/        reliability harness -> test_outputs.json
frontend/      chat UI with the live phase stepper
apps/insurance_claims/fixtures/   the sample data
```

## Run the application locally

Python 3.12+ and an OpenRouter API key (create one at https://openrouter.ai).

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env     # paste your key into MODEL_API_TOKEN
uvicorn api.chat:app --reload
```

Open **http://localhost:8000** — that is the chat UI, served by the same app it talks
to (API docs at `/docs`). Other providers work by changing `MODEL_NAME` in `.env`
(`openai:gpt-4o-mini`, `anthropic:claude-sonnet-4-5`, ...).

Docker, with the key already in `backend/.env`:

```
docker compose up --build     # open http://localhost:8000
```

## Who you can call as

| Caller | Details to use |
|---|---|
| Margaret Chen | policy POL-9921, DOB 1985-03-15, SSN last 4: 4472, phone +16505212836 — has a denied healthcare claim (CL-2048), a closed healthcare claim, a closed dental claim and an open auto claim |
| Ma Tian | policy POL-8836, DOB 1964-09-10, national ID last 4: 6688 — one denied claim missing a diagnosis report |
| Ava Lopez | email ava.lopez@email.com, phone +16503882920 — for testing identity verification without DOB/SSN |
| David Chen | Margaret's son — registered representative, triggers the consent flow |

## What to ask, and what to expect

**The full demo case** — paste this first:

> I'm the policyholder. My name is Margaret Chen, policy POL-9921. I'm calling about
> my denied healthcare claim from January. DOB is 1985-03-15, SSN last four is 4472.

Expect: identity verified from that one message, no re-asking what the call is about,
and an answer along the lines of *"Your healthcare claim CL-2048 was denied because
the review file did not include the pathology report and the treating provider office
note"* — with the appeal deadline. The stepper advances past Verify identity.

Follow-ups worth trying, each with what a correct agent does:

| You say | Expect |
|---|---|
| (give only name + DOB, then ask about a claim) | A request for one more identifying detail — and no claim information yet |
| ...SSN last four is 0000 | Verification fails, still no claim information |
| What if I can't get the pathology report? | Advice from the guideline: request a replacement copy from the hospital/lab/provider, or submit the closest substitute with a note |
| How do I submit it? / How long does review take? | Member portal first; review usually takes less than a week after resubmission |
| What is RL? | Polite refusal to answer the off-topic question, steered back to the claim |
| (repeat the off-topic question) | An offer to connect you with a human representative |
| This is ridiculous, just tell me why my claim was denied (before verifying) | Empathy, an explanation of why verification is required, no disclosure |
| Hi, I'm David Chen, Margaret Chen's son — why was her claim denied? | The consent question first; claim details only after consent is recorded |
| Okay, that's all I needed. Thanks. | An offer to email a conversation summary — your choice to send or skip |

## Tests

```powershell
pip install -r requirements-dev.txt
pytest                     # SOP gates at the service layer - deterministic, no API key
pytest tests/test_agent_   # agent behaviour - real conversations, needs the key

python eval/run_eval.py    # scripted scenarios -> backend/eval/test_outputs.json
```

## What's mocked

- Email sending records the summary to the address on file; nothing leaves the machine.
- Sessions and consent records are in-memory and reset on restart.
- The database is the JSON fixtures; claim search is keyword scoring.
