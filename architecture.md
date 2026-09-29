# System Architecture: Collections Voice Agent

## Overview

The system has four layers. Each layer has a clear responsibility and a clear place where it is configured.

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
│  ┌─────────────┐  ┌───────────┐  ┌────────────────────┐  │
│  │   System     │  │  Tools    │  │  Web SDK Call       │  │
│  │   Prompt     │  │  Config   │  │  (variables from    │  │
│  │              │  │  (7 tools)│  │   dashboard)        │  │
│  └──────┬──────┘  └─────┬─────┘  └─────────┬──────────┘  │
│         │   Liquid      │   POST webhook   │              │
│         │   variables   │   on tool call   │              │
│         │   injected    │                  │              │
└─────────┼──────────────┼──────────────────┼──────────────┘
          │              │                  │
          │              ▼                  │
          │    ┌──────────────────────┐     │
          │    │  BACKEND             │     │
          │    │  (FastAPI)           │     │
          │    │                      │     │
          │    │  POST /vapi/webhook  │     │
          │    │  POST /call/check    │     │
          │    │  GET  /accounts      │     │
          │    └──────────────────────┘     │
          │              │                  │
          │              ▼                  │
          │    ┌────────────────────────┐  │
          │    │  data/accounts.json    │◄─┘
          │    │                        │
          │    │  4 test accounts       │
          │    │  flags + balances      │
          │    └────────────────────────┘
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

The assistant is configured through the **Vapi Dashboard** (web UI). Per-call data is injected via the **Vapi API** each time the dashboard initiates a call.

### Vapi Dashboard settings

| Setting | What it does |
|---|---|
| **System prompt** | The full 6-section prompt (identity, guidelines, guardrails, context, workflow, examples). All settings documented in `vapi_agent_config/assistant_config.md`. |
| **LLM model** | GPT-4o Mini, temperature 0. Affects response quality and latency. |
| **Voice / TTS** | Godfrey (Vapi, male, natural/professional). Affects how the agent sounds. |
| **STT (transcription)** | Deepgram Nova 3, intelligent turn taking ON. Affects how well it understands the consumer. |
| **Tools** | 5 custom tools + 2 built-in (end call, transfer). Each tool has a name, description, parameter schema, and webhook URL. |
| **Server URL** | Single URL where Vapi sends all server events (tool calls, end-of-call reports). Points to the FastAPI backend. |

### Per-call data injection (Vapi API)

Each call is initiated with a POST to Vapi's API. This is how dynamic account data is injected — the prompt stays the same, the data changes per call.

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

## Layer 2: Backend (FastAPI Server)

A lightweight Python server that Vapi calls when the LLM decides to use a tool. Deployed to Render for a public URL.

A single webhook endpoint (`POST /vapi/webhook`) routes all tool calls by function name via a `TOOL_HANDLERS` dictionary. Adding a new tool = add a handler file + register it in the dictionary. The webhook never changes.

### Tool Handlers

5 custom tools with backend handlers + 2 Vapi built-in tools (no backend required):

| Tool | Parameters | What it writes to `data/accounts.json` |
|---|---|---|
| `record_payment` | account_number, amount, method | Reduces `past_due_amount`, returns confirmation number |
| `set_promise_to_pay` | account_number, amount, date | Sets `promise_to_pay_exists/date/amount` |
| `flag_do_not_call` | account_number | Sets `do_not_call` → true (FDCPA §1692c(c)) |
| `flag_dispute` | account_number | Sets `active_dispute` → true (FDCPA §1692g) |
| `flag_attorney` | account_number | Sets `has_attorney` → true (FDCPA §1692c(a)(2)) |
| `end_call_tool` | *(none)* | Built-in Vapi End Call — no backend handler |
| `transfer_call_tool` | *(none)* | Built-in Vapi Transfer Call — no backend handler |

Each custom tool has a `.py` handler in the backend. Parameter schemas (pasted into Vapi UI) are in `vapi_agent_config/tools/`.

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
4. Vapi sends POST to the backend:
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
5. Backend routes by function name → handler processes it
6. Returns: { "results": [{ "toolCallId": "call_abc123", "result": "{...}" }] }
7. Vapi feeds the result back to the LLM
8. LLM speaks the confirmation aloud to the consumer.
```

---

## Layer 3: Account Data (JSON or Simple DB)

For the demo, a simple JSON file on the FastAPI server holds the test accounts with all their flags. Call history is persisted to a second JSON file.

In production, this would connect to the client's CRM or collections management system. For the demo, JSON files are perfect — they show the architecture without unnecessary infrastructure.

### Data flow summary

```
data/accounts.json → Vapi API call (variableValues) → Liquid variables in prompt → LLM context
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

| Work Item | Where | File/Location |
|---|---|---|
| System prompt | Vapi Dashboard (source in repo) | `vapi_agent_config/system_prompt.md` |
| Tool parameter schemas | Vapi Dashboard (source in repo) | `vapi_agent_config/tools/*.json` |
| All Vapi Dashboard settings | Reference doc | `vapi_agent_config/assistant_config.md` |
| FastAPI server code | Deployed to Render | `main.py`, `tools/*.py` |
| Account test data | JSON file on server | `data/accounts.json` |
| Call history / logs | JSON file on server | `data/call_logs.json` |
| Per-call data injection | Vapi API (initiated by dashboard) | `dashboard/index.html` |

---

## Layer 4: Demo Dashboard (Minimal HTML)

A single HTML page that serves as the demo interface during the evaluation call.

### Features

- 4 account cards showing consumer name, account status, compliance flags, and financial details
- **Check Compliance** button → runs pre-call compliance check without starting a call
- **Start Call** button → triggers compliance check, then starts the Vapi Web SDK call with that account's variables injected
- If blocked → shows reason (e.g., "Call blocked: cease-and-desist flag active")
- After the call → account card updates live to reflect any changes (flags set, promise recorded, payment logged)
- **Call Logs** section at the bottom → shows all past calls with timestamp, account, outcome, and links to show transcript or download the end-of-call report

### Why a dashboard instead of using Vapi's Dashboard directly

Vapi's Dashboard test call always uses the same variable values configured in the assistant. To switch accounts, you'd have to manually edit variables each time — slow and error-prone during a live demo. The Web SDK lets the dashboard inject different account data per call automatically.
