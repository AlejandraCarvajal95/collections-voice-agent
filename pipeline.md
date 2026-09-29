# Pipeline: Voice Agent Take-Home Assignment

## Timeline: Friday → Sunday/Monday
**Goal**: Notify readiness by Sunday night or Monday morning.

---

## Phase 1: Platform Research & Selection - DONE
**Output**: [platform-decision.md](platform-decision.md) — Vapi selected.

---

## Phase 2: Collections Regulations + Conversation Flow - DONE
**Output**: [compliance-and-flow.md](compliance-and-flow.md) — FDCPA, Reg F, state rules, flag-driven compliance gate, 7-state conversation flow.

---

## Phase 3: System Prompt Design - DONE
**What**: Write the full system prompt following Vapi's 6-section structure.
**Where**: Write locally as `system-prompt.md`, then paste into Vapi Dashboard → Assistants → System Prompt.

### Steps

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

## Phase 4: Custom Tools + Backend - DONE
**What**: Build a FastAPI server with a single webhook endpoint that routes 5 tool calls + server-side compliance logic + call logging.
**Where**: Code locally → deploy to cloud for a public URL.
**Output**: `main.py`, `data.py`, `tools/` folder with handlers and Vapi JSON definitions, demo dashboard.

### Steps

**4.1 — Design tool schemas** ✅
5 custom tools, each with a `.py` handler and `.json` Vapi definition in `tools/`:

1. `record_payment` — when consumer agrees to pay now ✅
2. `set_promise_to_pay` — when consumer commits to a future payment date ✅
3. `flag_do_not_call` — when consumer says "stop calling me" ✅
4. `flag_dispute` — when consumer says "I don't owe this" ✅
5. `flag_attorney` — when consumer reveals attorney representation mid-call ✅

Plus Vapi's built-in `transferCall` for call transfers (not a custom tool).

**4.2 — Build FastAPI server** ✅
- Single `POST /vapi/webhook` endpoint routes all tool calls by function name via `TOOL_HANDLERS` dictionary
- `data.py` shared module for account data operations (load, save, find)
- Account data as JSON file (`accounts.json`) — 4 test accounts matching the assignment
- Each handler returns clean JSON with only what the LLM needs to speak

**4.3 — Pre-call compliance check** ✅
- `POST /call/check` — reads account flags, returns allowed/blocked + reason
- Checks in severity order: cease_and_desist, do_not_call, has_attorney, call_attempts >= 7 (Reg F), calling hours 8am-9pm (FDCPA)
- Real timezone-aware calling hours using `zoneinfo` — maps all 50 states + DC to IANA timezones
- If allowed → increments `call_attempts_last_7_days` (call counter)
- Pydantic model for Swagger UI form rendering

**4.4 — End-of-call handler (server-side, not a tool)** ✅
- Handles Vapi's `end-of-call-report` event in the `/vapi/webhook` endpoint
- Updates `last_contact_date` on the account
- Stores a structured call log record: call ID, timestamp, account number, outcome, compliance actions taken, transcript, duration
- `GET /call/logs` endpoint to retrieve all call logs
- Required for compliance auditing — proves Mini-Miranda delivery, calling hours, identity verification, and flag actions

**4.4b — Additional validations** ✅
- Promise-to-pay date validation: rejects past or today's dates (defense in depth — system prompt also instructs LLM to check)
- English-only language guardrail added to system prompt
- Test endpoints on separate `test` branch for Swagger UI manual testing

**4.5 — Demo dashboard (minimal HTML)** ✅
- Single HTML page served at `/dashboard` (in `dashboard/` folder)
- 4 account cards showing all account data, flags, and compliance status
- "Check Compliance" button runs pre-call check live (shows allowed/blocked + reason)
- "Start Call" button has placeholder — **Vapi Web SDK wiring happens in Phase 5.3**
- "Reset Demo Data" restores accounts + call logs to original state
- Call logs panel at the bottom (auto-refreshes)
- CORS enabled for cross-origin access
- Data snapshot on startup for reliable demo resets

**4.6 — Deploy** ✅
- Deployed to Render (free tier)
- Public URL: `https://collections-voice-agent.onrender.com`
- Dashboard: `/dashboard` | API docs: `/docs` | Webhook: `/vapi/webhook`

---

## Phase 5: Integration - DONE
**What**: Wire everything together in Vapi's Dashboard and connect to the demo dashboard.
**Where**: Vapi Dashboard (web UI) + demo dashboard.

### Steps

**5.1 — Create Vapi Assistant** ✅
- Model: GPT-4o Mini Cluster ($0.01/min, temp 0)
- Transcriber: Deepgram Nova 3 (2.7% WER, English, turn-taking ON, denoising ON)
- Voice: Vapi v2 — Godfrey (professional, male, speed 1.0, office background)
- System prompt + first message pasted

**5.2 — Register tools** ✅
- 5 function tools created and published in Vapi Dashboard
- All pointing to `https://collections-voice-agent.onrender.com/vapi/webhook`
- Request-start messages configured on each tool
- All 5 tools connected to the Alex assistant and published

**5.3 — Connect demo dashboard (complete the "Start Call" button)** ✅
- Vapi Web SDK loaded via ES module import (`jsdelivr +esm` CDN)
- `startCall()` wired: compliance check → if allowed → creates Vapi instance with account variables injected as `assistantOverrides.variableValues`
- API key + assistant ID fetched from `/config` endpoint (token-protected, env vars on Render)
- Live call status shown on card (ringing, connected, ended)
- Auto-refresh account data + call logs after call ends
- `endCall()` button to hang up mid-call
- Reset Demo Data button restores original state

**5.4 — Verify data persistence** ← NEXT
- Make a test call, trigger a tool (e.g., record_payment)
- Check that `accounts.json` was updated
- Confirm the dashboard reflects the change
- Review any issues found during first test call

**5.5 — Corrections from first test round**

- [x] **5.5a — Enable endCall function in Vapi Dashboard**: Enabled `end_call_tool` in Vapi Dashboard. Updated system prompt to explicitly call `end_call_tool` at all 11 exit points (verification failure, abuse, cease-and-desist, voicemail, closing, etc.). Added 2-second wait before hanging up to prevent audio distortion.

- [x] **5.5b — Dashboard: auto-refresh logs after call ends**: Added `cleanupCall()` shared function with triple refresh (2s, 6s, 12s). Fallback polling interval detects agent-side call termination. Status bar shows visible feedback. Log entries fall back to ended_reason + duration when summary is empty.

- [x] **5.5c — Call attempts counter: only increment on actual calls**: Separated `check_compliance` (read-only) from new `increment_call_attempt` function. New `POST /call/start` endpoint called only from the Start Call flow. Check Compliance button no longer inflates the counter.

- [x] **5.5d — Prompt: identity verification failure explanation**: Changed to "For your protection, I'm unable to discuss any account details without verifying your identity. Have a good day." — then calls `end_call_tool`.

- [x] **5.5e — Prompt: don't repeat goodbye if interrupted**: Added instruction in Step 7 closing: "If the consumer interrupts you during the closing, do not repeat the full goodbye. Briefly acknowledge what they said, give a short answer if needed, then say 'Have a good day' and call end_call_tool."

- [x] **5.5f — Real transfer with phone number (Nice to Have from assignment)**: Added `TRANSFER_NUMBER` env var on backend, exposed via `/config` endpoint. Dashboard overrides `callback_number` with the real number when injecting variables into Vapi calls. The system prompt already uses `{{callback_number}}` as the `transferCall` destination. During demo, set `TRANSFER_NUMBER` to the presenter's phone on Render — the agent will ring it live. Manual step: enable `transferCall` built-in tool in Vapi Dashboard.

- [x] **5.5g — Render cold start note**: Free tier sleeps after ~15 min inactivity. No code fix. Demo prep: hit dashboard URL 1-2 min before presenting to wake it up. Interview talking point: "In production, I'd use a paid tier or keep-alive ping."

- [x] **5.5h — Dashboard: show call transcript**: Added expandable "Show Transcript" toggle and "Download" button per log entry. Transcript downloads as `.txt` file with call metadata header. Stored by backend in `call_logs.json`, rendered and downloadable from frontend.

- [x] **5.5i — Dashboard: fix false "Transferred to live agent" message**: The error handler uses `callConnected` as a fallback condition, which shows "Transferred to live agent" on any Vapi error during an active call — even when no transfer occurred. Fix: only show the transfer message when `errorType === 'ejected'`. For all other errors on connected calls, fall through to the default "Call ended" message. File: `dashboard/index.html`, `vapi.on('error', ...)` handler.

---

## Phase 6: Testing & Iteration (~3-4 hours) - DONE
**What**: Test every scenario, try to break the agent, adjust prompt.
**Reference**: [test-scripts.md](test-scripts.md) — 14 test cases with scripts and checklists.

### Test Rounds

**Round 1 — First test call corrections (from 5.5)**
- [x] 5.5a — Enable `endCall` function in Vapi Dashboard so the agent can hang up
- [x] 5.5b — Dashboard: auto-refresh logs after call ends (delay for Vapi report)
- [x] 5.5c — Call attempts counter: only increment on actual calls, not compliance checks
- [x] 5.5d — Prompt: explain identity verification failure before hanging up
- [x] 5.5e — Prompt: don't repeat goodbye script if interrupted mid-closing
- [x] 5.5f — Real transfer with phone number (Nice to Have from assignment)
- [x] 5.5g — Render cold start: no code fix, demo prep note
- [x] 5.5h — Dashboard: show call transcript with expandable view + download

**Round 2 — Prompt fixes from systematic testing (Tests 7–18)**
- [x] Fixed `promise_to_pay_exists` routing: embedded check inside Step 4 so agent never skips to collection pitch
- [x] Fixed double exit message on C&D/attorney/dispute: removed speech from Step 5A handlers, exits own their closing message
- [x] Fixed `flag_do_not_call` not being called: C&D exit now requires tool call before speaking
- [x] Fixed agent not hanging up after goodbye: added explicit `end_call_tool` call to all three exits
- [x] Fixed jailbreak exit routing to transfer: Prompt Protection now ends call directly, Out-of-Scope handler explicitly excluded
- [x] Fixed Example 7 missing `end_call_tool`: few-shot now shows tool call after jailbreak goodbye
- [x] Updated all test dates from 2024 → 2026; Maria's promise date updated to October 2026
- [x] Reverted account states to demo values (TX/NY/MA/CA) after late-night testing bypass

### Test Plan (systematic)

**6.1 — Test each compliance path** ✅
- Cease-and-desist account → agent exits immediately ✅
- Attorney-represented account → agent redirects ✅
- Recently contacted account → frequency cap exit ✅
- Active dispute → dispute exit ✅

**6.2 — Test happy paths** ✅
- Full payment → record_payment tool fires → confirmation number spoken ✅
- Promise-to-pay → set_promise tool fires → date confirmed ✅
- Promise reminder flow → soft-touch tone ✅

**6.3 — Stress tests** ✅
- Third party answers → agent does NOT reveal debt info ✅
- Consumer speaks another language → agent offers transfer ✅
- Consumer gets hostile → abuse handling kicks in, call ends ✅
- Consumer attempts jailbreak → refused 3+ times → agent ends call ✅
- Off-topic / persona change attempts → redirected, call ends cleanly ✅

**6.4 — Iterate on prompt** ✅
- All issues found during testing fixed across two commit rounds

---

## Phase 7: Demo Preparation (~1-2 hours)
**What**: Prepare the 2-3 minute walkthrough.

### Steps

**7.1 — Prepare talking points**
- Why Vapi (prompt-first, dynamic injection, webhook tools)
- Why flag-driven compliance (works for any account, not hardcoded)
- Why identity verification before Mini-Miranda
- Why Mini-Miranda is verbatim, not paraphrased
- What you'd change in production (server-side verification, real database, authentication)

**7.2 — Pick demo scenarios**
- Choose 2-3 test accounts that show different paths (e.g., one happy path, one compliance exit)
- Pre-test them to make sure they work cleanly

**7.3 — Anticipate questions**
- "What happens if the consumer is in a state you haven't coded?" → flag-driven system, add state rules as config
- "How would you handle scale?" → the prompt stays the same, backend scales horizontally
- "What if the LLM hallucinates a payment amount?" → guardrail: extract values from tool responses only, never fabricate

---

## Total Estimated: ~18-26 hours across Wednesday → Monday

## Documents

| Document | Purpose | Status |
|---|---|---|
| [pipeline.md](pipeline.md) | This file — project timeline and steps | Done |
| [architecture.md](architecture.md) | System architecture — what goes where | Done |
| [deployment-info.md](deployment-info.md) | Render service URL, endpoints, auto-deploy config | Done |
| [vapi-prompt-reference.md](vapi-prompt-reference.md) | Vapi's official prompt guide | Reference |
| [test-scripts.md](test-scripts.md) | Test cases and checklists for all 18 tests | Done |
| [vapi_agent_config/system_prompt.md](vapi_agent_config/system_prompt.md) | The actual system prompt | Done |
| [vapi_agent_config/assistant_config.md](vapi_agent_config/assistant_config.md) | All Vapi Dashboard settings documented | Done |
| [vapi_agent_config/tools/](vapi_agent_config/tools/) | Tool parameter schemas (pasted into Vapi UI) | Done (5/5) |
| [main.py](main.py) | FastAPI backend — single webhook endpoint | Done |
| [data.py](data.py) | Shared account data operations | Done |
| [tools/](tools/) | Tool handlers (.py) | Done (5/5) |
| [data/accounts.json](data/accounts.json) | 4 test accounts matching assignment data | Done |
| [data/call_logs.json](data/call_logs.json) | Call history persisted after each call | Done |
