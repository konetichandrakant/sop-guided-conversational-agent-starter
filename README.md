# SOP-Guided Insurance Claims Agent

An insurance claims support agent that has to follow a fixed SOP but still hold a natural
conversation. The workflow runs in four phases — verify identity, resolve intent, process
the case, wrap up with an email summary — and the interesting constraint is that the
phases need very different amounts of freedom. Verification is a hard gate: no claim
details leave the system until the caller has matched at least three PII fields. Intent
resolution and case processing, on the other hand, are allowed to interpret messy human
language and answer grounded follow-ups.

## Where the SOP is actually enforced

The rules live in two places, and the second one matters more.

The system prompt describes the phases, the tone, the memory rules and the soft
behaviors (empathy, de-escalation, staying in scope). But a prompt can be talked around,
so the gates are also enforced in the tool layer, where the model can't bypass them:

| Gate | What enforces it |
|---|---|
| No claim data before identity is proven | `verify_profile` only returns a `party_id` after 3+ exact PII matches (counted in the service, alias-aware), and `get_claim` needs that `party_id` to find anything |
| Representatives don't get claim data on their own ID | `find_representative` only identifies the caller; `consent` must show `approved` (policy holder's answer) before disclosure, and a consent that stays pending across checks comes back with `escalate_to_human` |
| Answers are grounded, not invented | claim facts come from `get_claim`; document/submission/timing answers come from `get_claim_guidance`, which reads the required-document guideline fixture verbatim |
| Out of scope | prompt refuses after checking scope; two pushes later it offers a human transfer |

Every reply the agent produces is structured (`answer` + `phase`), so the test UI shows
which SOP phase the conversation is in while you talk.

## Memory across phases

If the caller says "I'm calling about my denied healthcare claim from January" while
still being verified, the agent stays in VERIFY_ID, remembers the hint, and uses it
after verification instead of asking what the call is about. The session history lives
server-side and every message in a session shares it.

## Setup

You need Python 3.12+ and an API key for a model provider.

```
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

copy .env.example .env            # then put your key in it
```

`.env` holds two values:

```
MODEL_NAME=openai:gpt-4o-mini
MODEL_API_TOKEN=sk-...
```

The provider is whatever prefix you put on `MODEL_NAME`. With OpenAI the preinstalled
`langchain-openai` is enough; for another provider install its package and change the
prefix:

| MODEL_NAME | package |
|---|---|
| `openai:gpt-4o-mini` | `langchain-openai` (already in requirements) |
| `anthropic:claude-sonnet-4-5` | `pip install langchain-anthropic` |
| `google_genai:gemini-2.5-pro` | `pip install langchain-google-genai` |

Start the API:

```
uvicorn api.chat:app --reload
```

Then open `frontend/index.html` in a browser (or `python -m http.server` inside
`frontend/` and use that URL). The UI is plain HTML/JS, no build step.

## Trying it

The fixture data is the "database". Two callers exist with real claim history:

- **Margaret Chen** (policy POL-9921, DOB 1985-03-15, SSN last 4: 4472, phone
  +16505212836) — four claims: a denied healthcare claim (CL-2048, missing pathology
  report and office note), a closed healthcare claim, a closed dental claim, and an open
  auto claim.
- **Ma Tian** (policy POL-8836, DOB 1964-09-10, national ID last 4: 6688) — one denied
  healthcare claim missing a diagnosis report.
- **David Chen** is on file as Margaret's son and representative.

The UI has a button that loads the assignment's demo test case. Things worth trying
beyond it:

- Give only two PII fields — it asks for a third instead of proceeding.
- Say "what is RL?" twice — it declines and then offers a human.
- "Just tell me why my claim was denied, this is ridiculous" before verifying — it
  acknowledges the frustration, explains why verification exists, and still doesn't
  disclose.
- After the denial explanation: "what if I can't get the pathology report?", "how do I
  submit it?", "how long does review take?" — all answered from the guideline fixture.
- As David: call about Margaret's claim and see the consent step before any details.
- At wrap-up, accept or skip the email summary.

## What's mocked (on purpose)

- **Email sending** records the summary with a timestamp to the address on file; nothing
  actually leaves the machine.
- **Sessions and consent records** are in-memory and reset on restart. Fine for a demo;
  both sit behind small service functions, so swapping in Redis or a table doesn't touch
  the agent.
- **The database** is the JSON fixtures under `apps/insurance_claims/fixtures`.
- **Claim search** over free text is keyword scoring. The function is one small
  `_match_score`, documented as the swap point for real embedding search.

## Layout

```
backend/
  agent/       agent loop, system prompt, tools, pydantic schemas
  services/    repositories and business logic (claims, verification, consent,
               representatives, guidelines, email) over the fixtures
  schema/      API request/response models
  api/         FastAPI app (POST /chat)
frontend/      chat UI with the phase stepper
apps/insurance_claims/fixtures/   the sample data the assignment shipped with
```
