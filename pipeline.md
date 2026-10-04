# Pipeline: Voice Agent Take-Home Assignment

---

## Phase 1: Platform Research & Selection
**Output**: [platform-decision.md](platform-decision.md) — Vapi selected.

---

## Phase 2: Collections Regulations + Conversation Flow
**Output**: [compliance-and-flow.md](compliance-and-flow.md) — FDCPA, Reg F, state rules, flag-driven compliance gate, 7-state conversation flow.

---

## Phase 3: System Prompt Design

**3.1 — Identity & Personality**
- Agent name, role (collections specialist for Chase credit cards), tone (professional, calm, empathetic but firm)
- Identity lock to prevent jailbreaking
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 1

**3.2 — Response Guidelines**
- Max 1-2 sentences per turn
- One question at a time
- Money/dates/phone numbers in spoken form
- No markdown, no lists
- Pacing with commas and periods
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 2

**3.3 — Guardrails**
- Content safety (no personal/political/religious topics)
- Collections-specific: never threaten arrest, never misrepresent debt, never give legal/financial advice, never discuss debt with third parties
- Pre-response safety check
- Abuse handling: warn once → end call
- Jailbreak protection
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 3

**3.4 — Context (Liquid variables)**
- Current date/time via Liquid: `{{ "now" | date: "%A, %B %d, %Y, %I:%M %p" }}`
- All account data as variables: `{{consumer_first_name}}`, `{{past_due_amount}}`, `{{consumer_state}}`, all compliance flags
- These get injected per call via the API — see [architecture.md](architecture.md) Layer 1
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 4

**3.5 — Workflow (convert compliance-and-flow.md states)**
- Translate the 7-state flow from [compliance-and-flow.md](compliance-and-flow.md) Part C into Vapi's step-by-step numbered format
- Include all exit paths (cease-and-desist, attorney, dispute, frequency cap)
- Include objection handling
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 5

**3.6 — Few-shot examples (minimum 3)**
- Happy path: consumer verifies → Mini-Miranda → agrees to pay → tool call → confirmation
- Edge case: consumer disputes debt → agent triggers dispute tool
- Error recovery: tool failure → agent retries → offers transfer
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 6

**3.7 — Error handling**
- Unclear input: retry once → offer transfer
- Tool failure: retry once → offer transfer
- Out-of-scope: redirect politely
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Section 9

**3.8 — Voice formatting & human feel**
- Spoken form rules for money, dates, phone numbers
- Disfluency calibration: professional level (e.g., "let me see", "one moment") — not casual
- Energy matching: match consumer pace
- Turn budget: ~7-12 turns
- Reference: [vapi-prompt-reference.md](vapi-prompt-reference.md) Sections 12-13

---

## Phase 4: Custom Tools + Backend
**Output**: `main.py`, `data.py`, `tools/` folder with handlers and Vapi JSON definitions, demo dashboard.

**4.1 — Tool schemas**
5 custom tools, each with a `.py` handler and `.json` Vapi definition in `tools/`:

1. `record_payment` — when consumer agrees to pay now
2. `set_promise_to_pay` — when consumer commits to a future payment date
3. `flag_do_not_call` — when consumer says "stop calling me"
4. `flag_dispute` — when consumer says "I don't owe this"
5. `flag_attorney` — when consumer reveals attorney representation mid-call

Plus Vapi's built-in `transferCall` for call transfers (not a custom tool).

**4.2 — FastAPI server**
- Single `POST /vapi/webhook` endpoint routes all tool calls by function name via `TOOL_HANDLERS` dictionary
- `data.py` shared module for account data operations (load, save, find)
- Account data as JSON file (`accounts.json`) — 4 test accounts matching the assignment
- Each handler returns clean JSON with only what the LLM needs to speak

**4.3 — Pre-call compliance check**
- `POST /call/check` — reads account flags, returns allowed/blocked + reason
- Checks in severity order: cease_and_desist, do_not_call, has_attorney, call_attempts >= 7 (Reg F), calling hours 8am-9pm (FDCPA)
- Real timezone-aware calling hours using `zoneinfo` — maps all 50 states + DC to IANA timezones
- Pydantic model for Swagger UI form rendering

**4.4 — End-of-call handler**
- Handles Vapi's `end-of-call-report` event in the `/vapi/webhook` endpoint
- Updates `last_contact_date` on the account
- Stores a structured call log record: call ID, timestamp, account number, outcome, compliance actions taken, transcript, duration
- `GET /call/logs` endpoint to retrieve all call logs

**4.4b — Additional validations**
- Promise-to-pay date validation: rejects past or today's dates
- English-only language guardrail added to system prompt

**4.5 — Demo dashboard**
- Single HTML page served at `/dashboard`
- 4 account cards showing all account data, flags, and compliance status
- "Check Compliance" button runs pre-call check live
- "Start Call" button wired to Vapi Web SDK
- "Reset Demo Data" restores accounts + call logs to original state
- Call logs panel at the bottom
- CORS enabled, data snapshot on startup for reliable demo resets

**4.6 — Deploy**
- Deployed to Render (free tier)
- Public URL: `https://collections-voice-agent.onrender.com`
- Dashboard: `/dashboard` | API docs: `/docs` | Webhook: `/vapi/webhook`

---

## Phase 5: Integration

**5.1 — Create Vapi Assistant**
- Model: GPT-4o Mini Cluster ($0.01/min, temp 0)
- Transcriber: Deepgram Nova 3 (2.7% WER, English, turn-taking ON, denoising ON)
- Voice: Vapi v2 — Godfrey (professional, male, speed 1.0, office background)
- System prompt + first message pasted

**5.2 — Register tools**
- 5 function tools created and published in Vapi Dashboard
- All pointing to `https://collections-voice-agent.onrender.com/vapi/webhook`
- Request-start messages configured on each tool
- All 5 tools connected to the assistant and published

**5.3 — Connect demo dashboard**
- Vapi Web SDK loaded via ES module import (jsdelivr +esm CDN)
- `startCall()` wired: compliance check → if allowed → creates Vapi instance with account variables injected as `assistantOverrides.variableValues`
- API key + assistant ID fetched from `/config` endpoint (token-protected, env vars on Render)
- Live call status shown on card (ringing, connected, ended)
- Auto-refresh account data + call logs after call ends

**5.4 — Corrections from test rounds**

- [x] **5.4a** — Enabled `end_call_tool` in Vapi Dashboard. Updated system prompt to explicitly call it at all 11 exit points.
- [x] **5.4b** — Dashboard: auto-refresh logs after call ends (triple refresh at 2s, 6s, 12s).
- [x] **5.4c** — Call attempts counter: separated `check_compliance` (read-only) from `increment_call_attempt`. New `POST /call/start` endpoint called only from the Start Call flow.
- [x] **5.4d** — Prompt: identity verification failure now explains before hanging up.
- [x] **5.4e** — Prompt: agent does not repeat goodbye if interrupted mid-closing.
- [x] **5.4f** — Real transfer with phone number: `TRANSFER_NUMBER` env var exposed via `/config`, injected as `callback_number` in variable values.
- [x] **5.4g** — Render cold start: no code fix. Demo prep: hit dashboard URL before presenting.
- [x] **5.4h** — Dashboard: expandable transcript toggle and download button per log entry.
- [x] **5.4i** — Dashboard: fixed false "Transferred to live agent" message — now only shown when `errorType === 'ejected'`.

---

## Phase 6: Testing & Iteration
**Reference**: [test-scripts.md](test-scripts.md) — 14 test cases with scripts and checklists.

**Round 1 — First test call corrections (from 5.4)**
- All items in 5.4a–5.4i resolved.

**Round 2 — Prompt fixes from systematic testing**
- [x] Fixed `promise_to_pay_exists` routing: embedded check inside Step 4 so agent never skips to collection pitch
- [x] Fixed double exit message on C&D/attorney/dispute: exits own their closing message
- [x] Fixed `flag_do_not_call` not being called: C&D exit now requires tool call before speaking
- [x] Fixed agent not hanging up after goodbye: explicit `end_call_tool` call at all exits
- [x] Fixed jailbreak exit routing to transfer: Prompt Protection ends call directly
- [x] Fixed Example 7 missing `end_call_tool`: few-shot now shows tool call after jailbreak goodbye
- [x] Updated all test dates to 2026; Maria's promise date updated to October 2026
- [x] Reverted account states to demo values after testing

**Test coverage**

- Cease-and-desist, attorney, frequency cap, active dispute exits
- Full payment → `record_payment` tool → confirmation number spoken
- Promise-to-pay → `set_promise_to_pay` tool → date confirmed
- Third party answers → agent does not reveal debt info
- Consumer speaks another language → agent offers transfer
- Consumer gets hostile → abuse handling → call ends
- Consumer attempts jailbreak → refused → agent ends call

---

## Phase 7: Demo Preparation

**Talking points**
- Why Vapi (prompt-first, dynamic injection, webhook tools)
- Why flag-driven compliance (works for any account, not hardcoded)
- Why identity verification before Mini-Miranda
- Why Mini-Miranda is verbatim, not paraphrased
- What you'd change in production (server-side verification, real database, authentication)

**Demo scenarios**
- James Carter — standard collection call (happy path)
- Maria Lopez — active PTP (existing promise acknowledged)
- David Kim — recent contact (compliance passes, agent adapts)
- Sarah Brooks — BLOCKED before Vapi dials (compliance gate demo)

---

## Documents

| Document | Purpose |
|---|---|
| [pipeline.md](pipeline.md) | This file — project phases and steps |
| [architecture.md](architecture.md) | System architecture — what goes where |
| [deployment-info.md](deployment-info.md) | Render service URL, endpoints, auto-deploy config |
| [vapi-prompt-reference.md](vapi-prompt-reference.md) | Vapi's official prompt guide |
| [test-scripts.md](test-scripts.md) | Test cases and checklists |
| [vapi_agent_config/system_prompt.md](vapi_agent_config/system_prompt.md) | The actual system prompt |
| [vapi_agent_config/assistant_config.md](vapi_agent_config/assistant_config.md) | All Vapi Dashboard settings documented |
| [vapi_agent_config/tools/](vapi_agent_config/tools/) | Tool parameter schemas (pasted into Vapi UI) |
| [main.py](main.py) | FastAPI backend — single webhook endpoint |
| [data.py](data.py) | Shared account data operations |
| [tools/](tools/) | Tool handlers (.py) |
| [data/accounts.json](data/accounts.json) | 4 test accounts matching assignment data |
| [data/call_logs.json](data/call_logs.json) | Call history persisted after each call |
