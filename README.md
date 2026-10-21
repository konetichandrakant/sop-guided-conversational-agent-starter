# SOP-Guided Insurance Claims Agent

An insurance claims support agent that has to follow a fixed SOP but still hold a natural
conversation. The workflow runs in four phases — verify identity, resolve intent, process
the case, wrap up with an email summary — and the interesting constraint is that the
phases need very different amounts of freedom. Verification is a hard gate: no claim
details leave the system until the caller has matched at least three PII fields. Intent
resolution and case processing, on the other hand, are allowed to interpret messy human
language and answer grounded follow-ups.

## Run it locally

You need Python 3.12+ and an API key. The default setup uses
[OpenRouter](https://openrouter.ai/) (one key, any vendor's model); a plain OpenAI,
Anthropic or Google key works too — see the provider table below.

```powershell
git clone https://github.com/konetichandrakant/sop-guided-conversational-agent-starter.git
cd sop-guided-conversational-agent-starter/backend

python -m venv .venv
.venv\Scripts\activate                 # Windows (source .venv/bin/activate on mac/linux)
pip install -r requirements.txt

copy .env.example .env                 # then paste your key into .env
```

`.env` holds two values — the provider-prefixed model name and your token:

```
MODEL_NAME=openrouter:openai/gpt-4o-mini
MODEL_API_TOKEN=sk-or-v1-...
```

Start the server (from the `backend/` directory — the whole app is one origin):

```powershell
uvicorn api.chat:app --reload
```

Open **http://localhost:8000** — that's the chat UI. The stepper at the top shows the
SOP phase the conversation is in, live. The API it talks to is the same origin
(`POST /chat`); interactive docs are at http://localhost:8000/docs.

If you prefer serving `frontend/` separately (`python -m http.server` inside it, or
opening `index.html` from disk), that works too — the UI then falls back to
`http://localhost:8000` for the API. There is no build step; it's plain HTML/JS.

| MODEL_NAME | package |
|---|---|
| `openrouter:openai/gpt-4o-mini` | `langchain-openai` (already in requirements) |
| `openai:gpt-4o-mini` | `langchain-openai` |
| `anthropic:claude-sonnet-4-5` | `pip install langchain-anthropic` |
| `google_genai:gemini-2.5-pro` | `pip install langchain-google-genai` |

## Run with Docker

Put your key in `backend/.env` first, then:

```
docker compose up --build
```

Open http://localhost:8000. The token is passed to the container as an environment
variable at runtime; it is excluded from the image via `.dockerignore`, so nothing
secret ends up in a layer you might push.

## Trying it

The fixture data is the "database". The callers on file:

- **Margaret Chen** (policy POL-9921, DOB 1985-03-15, SSN last 4: 4472, phone
  +16505212836) — four claims: a denied healthcare claim (CL-2048, missing pathology
  report and office note), a closed healthcare claim, a closed dental claim, and an open
  auto claim.
- **Ma Tian** (policy POL-8836, DOB 1964-09-10, national ID last 4: 6688) — one denied
  healthcare claim missing a diagnosis report.
- **David Chen** is on file as Margaret's son and representative; **Ava Lopez**
  (email ava.lopez@email.com, phone +16503882920) is a second policy holder for testing
  alternate identity fields.

The UI has a button that loads the assignment's demo test case. Beyond it:

- Give only two PII fields — it asks for a third instead of proceeding.
- Give a wrong SSN last-4 — verification fails, still no claim data.
- Say "what is RL?" twice — declined, then a human is offered.
- "Just tell me why my claim was denied, this is ridiculous" before verifying — the
  frustration is acknowledged, the gate is explained, nothing is disclosed.
- After the denial explanation: "what if I can't get the pathology report?", "how do I
  submit it?", "how long does review take?" — answered from the guideline fixture.
- As David: call about Margaret's claim and watch the consent step before any details.
- At wrap-up, accept or skip the email summary — both paths are respected.

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

Every reply the agent produces is structured (`answer` + `phase`), so the UI shows
which SOP phase the conversation is in while you talk.

## Memory across phases

If the caller says "I'm calling about my denied healthcare claim from January" while
still being verified, the agent stays in VERIFY_ID, remembers the hint, and uses it
after verification instead of asking what the call is about. The session history lives
server-side and every message in a session shares it; a new session re-verifies by
design.

## Tests

```
pip install -r requirements-dev.txt
pytest                    # SOP gates at the service layer - deterministic, no API key
pytest tests/test_agent_  # agent behaviour - needs a real key in backend/.env
```

The service tests pin the gates themselves: 3-PII counting (including aliases, and
ID type alone not counting), consent pending/declined/timeout-escalation, claim
search ranking, guideline answers and the email path.

The agent tests run real conversations through DeepEval, covering the assignment's
demo case end to end (verify → remembered intent → grounded denial → document
guidance → email summary), plus partial-PII blocking, alternate identity fields,
out-of-scope refusal with human escalation, the frustration scenario, and the
representative + consent flow. Tool routing is scored exactly — was
`verify_profile` called before any `get_claim`, was `consent` recorded before
disclosure, did `send_email_summary` fire only after agreement — while the
judgement calls (tone, no-disclosure phrasing, grounded answers) go to an LLM
judge. The judge reuses your own `MODEL_NAME` and token, so there's no separate
judge key to configure.

## Benchmarks

`backend/eval/test_outputs.json` is a full reliability report generated by:

```
python eval/run_eval.py          # add --only name1,name2 for a subset,
                                 # --merge-into eval/test_outputs.json to merge it in
```

It runs scripted conversations and records per turn: the input, the output, the SOP
phase, the complete tool-call trace (name, input, output), deterministic gate checks,
and the judge's score of actual vs expected output with its reasoning. The headline
numbers from the latest full run (`openrouter:openai/gpt-4o-mini`, judge = same model):

| Metric | Result |
|---|---|
| Scenarios passed | 5/7 |
| Correctness checks | 24/28 |
| SOP gate violations | 3 |
| LLM-judge average | 0.60 |

The two failing scenarios were diagnosed from the report's traces and fixed: the model
fabricated party ids (`P-123456789` instead of the tool-returned `P9`) and then guessed
denial reasons to cover the empty results, and it recorded a consent decline the caller
never gave. Tool descriptions and the system prompt now pin exact-id reuse and
explicit-only consent answers; the report is how those regressions get caught.

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
  api/         FastAPI app (POST /chat, serves the UI as static files)
  tests/       deterministic gate tests + DeepEval agent suites
  eval/        reliability harness producing test_outputs.json
frontend/      chat UI with the phase stepper
apps/insurance_claims/fixtures/   the sample data the assignment shipped with
```
