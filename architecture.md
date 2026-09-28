# System Architecture: Collections Voice Agent

## Overview

The system has three layers. Each layer has a clear responsibility and a clear place where you configure it.

```
┌──────────────────────────────────────────────────────────────┐
│                     DEMO DASHBOARD                           │
│                                                              │
│  [James Carter] [Maria Lopez] [David Kim] [Sarah Brooks]     │
│       Call ✓        Call ✓       Call ✓      BLOCKED ✗        │
│                                                              │
│  Click "Call" → compliance check → Vapi Web SDK starts call  │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                     VAPI PLATFORM                       │
│                                                         │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │   System     │  │  Tools   │  │  Web SDK Call       │  │
│  │   Prompt     │  │  Config  │  │  (variables from    │  │
│  │              │  │  (5 tools)│  │   dashboard)        │  │
│  └──────┬──────┘  └────┬─────┘  └─────────┬──────────┘  │
│         │   Liquid      │   POST webhook   │              │
│         │   variables   │   on tool call   │              │
│         │   injected    │                  │              │
└─────────┼──────────────┼──────────────────┼──────────────┘
          │              │                  │
          │              ▼                  │
          │    ┌──────────────────────┐     │
          │    │  YOUR BACKEND        │     │
          │    │  (FastAPI)           │     │
          │    │                      │     │
          │    │  POST /vapi/webhook  │     │
          │    │  POST /call/check    │     │
          │    │  GET  /accounts      │     │
          │    └──────────────────────┘     │
          │              │                  │
          │              ▼                  │
          │    ┌──────────────────┐         │
          │    │  accounts.json   │◄────────┘
          │    │                  │
          │    │  4 test accounts │
          │    │  flags + balances│
          │    └──────────────────┘
          │
          ▼
┌──────────────────────────────────┐
│         THE LIVE CALL            │
│                                  │
│  STT (speech-to-text)            │
│    → LLM processes with prompt   │
│      → TTS (text-to-speech)      │
│        → Consumer hears response │
└──────────────────────────────────┘
```

---

## Layer 1: Vapi Platform (Dashboard + API)

This is where you configure the assistant. You interact with it in two ways: the **Vapi Dashboard** (web UI) and the **Vapi API** (programmatic calls).

### What you configure in the Vapi Dashboard

| Thing | Where in Dashboard | What it does |
|---|---|---|
| **System prompt** | Assistants → your assistant → System Prompt | The full 6-section prompt (identity, guidelines, guardrails, context, workflow, examples). This is where 80% of your prompt engineering work lives. |
| **LLM model** | Assistants → Model | Choose the model (e.g., GPT-4o, Claude). Affects response quality and latency. |
| **Voice / TTS** | Assistants → Voice | Choose the voice engine and voice (e.g., ElevenLabs, PlayHT, Deepgram). Affects how the agent sounds. |
| **STT (transcription)** | Assistants → Transcriber | Choose the speech-to-text engine (e.g., Deepgram). Affects how well it understands the consumer. |
| **Tools (function definitions)** | Assistants → Tools | Define each tool: name, description, parameters, and the webhook URL your backend exposes. Also set `request-start` messages here. |
| **End-of-call report** | Assistants → Advanced | Configure what Vapi sends you after the call ends (transcript, summary, etc.). |
| **First message** | Assistants → First Message | The very first thing the agent says when the call connects. Can also be handled in the prompt workflow. |
| **Server URL** | Assistants → Advanced → Server URL | A single URL where Vapi sends ALL server events (tool calls, call status, end-of-call). Your FastAPI server. |

### What you configure via the Vapi API (per-call)

When you **initiate an outbound call**, you send a POST to Vapi's API with a JSON payload. This is where dynamic data injection happens.

```json
POST https://api.vapi.ai/call/phone
{
  "assistantId": "your-assistant-id",
  "customer": {
    "number": "+15551234567",
    "name": "Consumer Name"
  },
  "assistantOverrides": {
    "variableValues": {
      "account_number": "CH7723849",
      "consumer_first_name": "James",
      "consumer_last_name": "Carter",
      "consumer_dob": "1985-03-15",
      "consumer_state": "TX",
      "product_type": "Sapphire Credit Card",
      "last_4_digits": "3849",
      "total_balance": "3847.22",
      "past_due_amount": "189.00",
      "minimum_payment": "94.50",
      "days_past_due": "60",
      "missed_payments": 2,
      "cease_and_desist": false,
      "do_not_call": false,
      "has_attorney": false,
      "active_dispute": false,
      "promise_to_pay_exists": false,
      "promise_to_pay_date": null,
      "promise_to_pay_amount": null,
      "last_contact_date": "2024-09-01",
      "call_attempts_last_7_days": 0,
      "callback_number": "+18005551234",
      "department": "Credit Card Services"
    }
  }
}
```

These values become available in the system prompt as Liquid variables: `{{consumer_first_name}}`, `{{past_due_amount}}`, etc.

**This is how you avoid hardcoding.** The prompt is always the same — the data changes per call.

---

## Layer 2: Your Backend (FastAPI Server)

A lightweight Python server that Vapi calls when the LLM decides to use a tool. Deployed to a free host (Railway or Render) for a public URL.

### Architecture

Single webhook endpoint (`POST /vapi/webhook`) routes all tool calls by function name via a `TOOL_HANDLERS` dictionary. Adding a new tool = add a handler file + register it in the dictionary. The webhook never changes.

### Tool Handlers

| Tool | Parameters | What it writes to `accounts.json` |
|---|---|---|
| `record_payment` | account_number, amount, method | Reduces `past_due_amount`, returns confirmation number |
| `set_promise_to_pay` | account_number, amount, date | Sets `promise_to_pay_exists/date/amount` |
| `flag_do_not_call` | account_number | Sets `do_not_call` → true (FDCPA §1692c(c)) |
| `flag_dispute` | account_number | Sets `active_dispute` → true (FDCPA §1692g) |
| `flag_attorney` | account_number | Sets `has_attorney` → true (FDCPA §1692c(a)(2)) |

Each tool has a `.py` handler and a `.json` Vapi definition in the `tools/` folder.

### Pre-call Compliance Check

`POST /call/check` — server-side gate that runs before any call is initiated:

1. `cease_and_desist == true` → blocked
2. `do_not_call == true` → blocked
3. `has_attorney == true` → blocked
4. `call_attempts_last_7_days >= 7` → blocked (Reg F)
5. Outside 8am-9pm in consumer's state timezone → blocked (FDCPA §1692c(a)(1))

If all checks pass → call is allowed, Vapi Web SDK starts the call with the account's variables.

### How the webhook flow works

```
1. Consumer says: "I'd like to pay the full amount today"
2. Vapi STT transcribes it
3. LLM reads the prompt + transcript → decides to call `record_payment`
4. Vapi sends POST to your server:
   {
     "message": {
       "type": "tool-calls",
       "toolCallList": [{
         "id": "call_abc123",
         "function": {
           "name": "record_payment",
           "arguments": {
             "account_number": "CH7723849",
             "amount": 189.00,
             "method": "phone"
           }
         }
       }]
     }
   }
5. Your server routes by function name → handler processes it
6. Returns: { "results": [{ "toolCallId": "call_abc123", "result": "{...}" }] }
7. Vapi feeds the result back to the LLM
8. LLM speaks: "Your payment of one hundred eighty-nine dollars has been
   recorded. Your confirmation number is PAY-20240920-3849."
```

---

## Layer 3: Account Data (JSON or Simple DB)

For the demo, this can be a simple JSON file or in-memory dictionary on your FastAPI server. It holds the test accounts with all their flags.

In production, this would connect to the client's CRM or collections management system. For the demo, a JSON file is perfect — it shows the architecture without unnecessary infrastructure.

### Data flow summary

```
Account JSON → Vapi API call (variableValues) → Liquid variables in prompt → LLM context
                                                                              │
                                                                    LLM calls tool
                                                                              │
                                                                              ▼
                                                                    FastAPI server
                                                                              │
                                                                    Updates JSON / returns result
                                                                              │
                                                                              ▼
                                                                    Vapi feeds result to LLM
                                                                              │
                                                                    LLM speaks confirmation
```

---

## Where each piece of work lives

| Work Item | Where you do it | File/Location |
|---|---|---|
| System prompt (6 sections) | Write locally, paste into Vapi Dashboard | `system-prompt.md` → Vapi Dashboard |
| Tool definitions (4 tools) | Vapi Dashboard → Tools section | Vapi Dashboard |
| Tool `request-start` messages | Vapi Dashboard → each tool's messages | Vapi Dashboard |
| Voice selection | Vapi Dashboard → Voice | Vapi Dashboard |
| LLM model selection | Vapi Dashboard → Model | Vapi Dashboard |
| FastAPI server code | Write locally, deploy to Railway/Render | `server.py` or `main.py` |
| Account test data | JSON file on your server | `accounts.json` |
| Per-call data injection | Vapi API call or Vapi Dashboard test call | API payload / Dashboard |
| Testing calls | Vapi Dashboard → "Test Call" or real phone | Vapi Dashboard |

---

## Layer 4: Demo Dashboard (Minimal HTML)

A single HTML page that serves as the demo interface during the evaluation call.

### Features

- 4 account cards showing consumer name, key flags, and account status
- "Call" button per card → triggers pre-call compliance check
- If blocked → shows reason (e.g., "Call blocked: cease-and-desist flag active")
- If allowed → starts Vapi Web SDK call with that account's variables injected
- After the call → shows what changed in `accounts.json` (proves persistent data)

### Why a dashboard instead of using Vapi's Dashboard directly

Vapi's Dashboard test call always uses the same variable values configured in the assistant. To switch accounts, you'd have to manually edit variables each time — slow and error-prone during a live demo. The Web SDK lets the dashboard inject different account data per call automatically.

---

## Configuration you do NOT need

Things that might seem necessary but aren't for this demo:

- **No database server** — a JSON file is fine for 4 test accounts
- **No authentication on your webhook** — for the demo, open endpoints are acceptable. In production you'd validate Vapi's server secret header
- **No CI/CD pipeline** — deploy manually to Railway/Render
- **No new client registration** — 4 test accounts cover all compliance scenarios
- **No call recording/transcription storage** — Vapi handles this in its Dashboard
