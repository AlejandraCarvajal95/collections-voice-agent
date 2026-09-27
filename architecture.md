# System Architecture: Collections Voice Agent

## Overview

The system has three layers. Each layer has a clear responsibility and a clear place where you configure it.

```
┌─────────────────────────────────────────────────────────┐
│                     VAPI PLATFORM                       │
│                                                         │
│  ┌─────────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │   System     │  │  Tools   │  │  Call Settings      │  │
│  │   Prompt     │  │  Config  │  │  (per-call API)     │  │
│  └──────┬──────┘  └────┬─────┘  └─────────┬──────────┘  │
│         │              │                  │              │
│         │   Liquid      │   POST webhook   │   JSON       │
│         │   variables   │   on tool call   │   payload    │
│         │   injected    │                  │   at dial    │
│         │   at runtime  │                  │   time       │
└─────────┼──────────────┼──────────────────┼──────────────┘
          │              │                  │
          │              ▼                  │
          │    ┌──────────────────┐         │
          │    │  YOUR BACKEND    │         │
          │    │  (FastAPI)       │         │
          │    │                  │         │
          │    │  /record-payment │         │
          │    │  /set-promise    │         │
          │    │  /flag-dnc       │         │
          │    │  /flag-dispute   │         │
          │    └──────────────────┘         │
          │              │                  │
          │              ▼                  │
          │    ┌──────────────────┐         │
          │    │  ACCOUNT DATA    │◄────────┘
          │    │  (JSON / DB)     │
          │    │                  │
          │    │  Consumer info   │
          │    │  Account flags   │
          │    │  Balance data    │
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

A lightweight Python server that Vapi calls when the LLM decides to use a tool. You deploy it to a free host (Railway or Render) so it has a public URL.

### Endpoints

| Endpoint | When Vapi calls it | What it does | Returns to Vapi |
|---|---|---|---|
| `POST /record-payment` | Consumer agrees to pay now | Logs the payment (amount, method, date) | `{ "status": "success", "confirmation_number": "PAY-20240920-001" }` |
| `POST /set-promise` | Consumer commits to a future date | Logs the promise (amount, date) | `{ "status": "success", "promise_date": "2024-09-27", "amount": 435.00 }` |
| `POST /flag-dnc` | Consumer says "stop calling me" | Sets the do-not-call flag on the account | `{ "status": "success", "message": "Account flagged as do-not-call" }` |
| `POST /flag-dispute` | Consumer says "I don't owe this" | Sets the dispute flag, triggers validation letter process | `{ "status": "success", "message": "Dispute noted, validation letter will be sent" }` |

### How the webhook flow works

```
1. Consumer says: "I'd like to pay the full amount today"
2. Vapi STT transcribes it
3. LLM reads the prompt + transcript → decides to call `record_payment`
4. Vapi sends POST to YOUR server:
   {
     "message": {
       "toolCalls": [{
         "function": {
           "name": "record_payment",
           "arguments": { "amount": 1247.83, "method": "phone" }
         }
       }]
     }
   }
5. Your server processes it, returns JSON result
6. Vapi feeds the result back to the LLM
7. LLM generates a spoken response: "I've recorded your payment of 
   twelve hundred forty-seven dollars and eighty-three cents. 
   Your confirmation number is PAY-20240920-001."
8. Vapi TTS speaks it to the consumer
```

### Tool definitions in Vapi (what you enter in the Dashboard)

Each tool needs a definition. Example for `record_payment`:

```json
{
  "type": "function",
  "function": {
    "name": "record_payment",
    "description": "Use this tool when the consumer agrees to make a payment right now. Call it with the payment amount and method.",
    "parameters": {
      "type": "object",
      "properties": {
        "amount": {
          "type": "number",
          "description": "The dollar amount the consumer agreed to pay (e.g., 435.00)"
        },
        "method": {
          "type": "string",
          "description": "How the payment is being made (e.g., 'phone', 'online', 'check')"
        }
      },
      "required": ["amount"]
    }
  },
  "messages": [
    {
      "type": "request-start",
      "content": "Let me note that payment on your account."
    }
  ],
  "server": {
    "url": "https://your-backend.railway.app/record-payment"
  }
}
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

## Configuration you do NOT need

Things that might seem necessary but aren't for this demo:

- **No database server** — a JSON file or Python dict is fine for 4 test accounts
- **No authentication on your webhook** — for the demo, open endpoints are acceptable. In production you'd validate Vapi's server secret header
- **No CI/CD pipeline** — deploy manually to Railway/Render
- **No frontend/UI** — everything is configured in Vapi's Dashboard and tested via phone calls
- **No Vapi SDK** — you can use the Dashboard for everything. The API is only needed if you want to trigger calls programmatically (optional)
