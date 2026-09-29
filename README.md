# Collections Voice Agent

A pre-charge-off collections voice agent built with Vapi (voice AI platform), FastAPI, and a live demo dashboard. The agent calls consumers with past-due credit card accounts, handles identity verification, delivers the Mini-Miranda disclosure, and resolves calls through payment, promise-to-pay, or a compliant exit — all while enforcing FDCPA and Reg F rules in real time.

---

## See it live

**Dashboard**: [https://collections-voice-agent.onrender.com/dashboard](https://collections-voice-agent.onrender.com/dashboard)

> The backend runs on Render's free tier and sleeps after ~15 minutes of inactivity. If the dashboard doesn't load immediately, wait 20–30 seconds and refresh — it's waking up.

The dashboard shows 4 test accounts in different compliance states:
- **James Carter** — standard account, callable
- **Maria Lopez** — has an active promise-to-pay on file
- **David Kim** — near the Reg F frequency cap (6/7 calls)
- **Sarah Brooks** — blocked (cease-and-desist + do-not-call flags active)

Click **Check Compliance** to see the pre-call gate in action, or **Start Call** to speak with the agent live (requires a microphone). After each call, the account card updates and a log entry appears at the bottom with the transcript and outcome.

**API docs (Swagger UI)**: [https://collections-voice-agent.onrender.com/docs](https://collections-voice-agent.onrender.com/docs)

---

## Project structure

```
collections-voice-agent/
├── main.py                    # FastAPI app — single webhook endpoint + all routes
├── compliance.py              # Pre-call compliance checks (FDCPA + Reg F)
├── call_handler.py            # End-of-call report handler + call log writer
├── data.py                    # Account data operations (load, save, find, reset)
├── tools/                     # Tool handlers (.py) — one per Vapi tool
├── data/
│   ├── accounts.json          # 4 test accounts with flags and balances
│   └── call_logs.json         # Call history (written after each call)
├── dashboard/
│   └── index.html             # Demo dashboard (single HTML page)
└── vapi_agent_config/
    ├── system_prompt.md       # System prompt (paste into Vapi Dashboard)
    ├── assistant_config.md    # All Vapi Dashboard settings documented
    └── tools/                 # Tool parameter schemas (paste into Vapi UI)
```

---

## API routes

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/dashboard` | Demo dashboard UI |
| `GET` | `/docs` | Swagger API docs |
| `GET` | `/health` | Health check |
| `GET` | `/accounts` | All 4 test accounts with current state |
| `GET` | `/call/logs` | Call history |
| `POST` | `/call/check` | Pre-call compliance check — body: `{"account_number": "CH7723849"}` |
| `POST` | `/call/start` | Increment call attempt counter — called after a call is confirmed to start |
| `POST` | `/vapi/webhook` | Vapi tool calls + end-of-call reports (called by Vapi, not manually) |
| `GET` | `/config` | Vapi credentials for the dashboard (requires `X-Dashboard-Token` header) |
| `POST` | `/data/reset` | Reset accounts and call logs to original demo state |

---

## Run it yourself

### What you need

- **Python 3.11+**
- A **[Vapi](https://vapi.ai)** account (free tier works)
- A cloud host with a public URL for the webhook (e.g., [Render](https://render.com))

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `VAPI_PUBLIC_KEY` | Yes | Vapi public key (from Vapi Dashboard → Account) |
| `VAPI_ASSISTANT_ID` | Yes | ID of the Vapi assistant you create |
| `DASHBOARD_TOKEN` | Yes | Any static string — used to protect the `/config` endpoint |
| `TRANSFER_NUMBER` | No | Phone number for live call transfers (E.164 format, e.g. `+15551234567`) |

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/AlejandraCarvajal95/collections-voice-agent
cd collections-voice-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables (or create a .env file)
export VAPI_PUBLIC_KEY=your_key
export VAPI_ASSISTANT_ID=your_assistant_id
export DASHBOARD_TOKEN=any_string_you_choose

# 4. Run the server
uvicorn main:app --host 0.0.0.0 --port 8000
```

The dashboard will be at `http://localhost:8000/dashboard`.

### Set up the Vapi assistant

The agent's configuration lives in `vapi_agent_config/`:

1. Create a new assistant in the [Vapi Dashboard](https://dashboard.vapi.ai)
2. Paste the contents of `vapi_agent_config/system_prompt.md` into the System Prompt field
3. Configure the model, voice, and transcriber settings as documented in `vapi_agent_config/assistant_config.md`
4. Create the 5 custom tools using the parameter schemas in `vapi_agent_config/tools/` — set the server URL to your backend's `/vapi/webhook` endpoint
5. Set your backend's public URL as the Server URL under Advanced settings
6. Copy the assistant ID into the `VAPI_ASSISTANT_ID` environment variable

---

## Key design decisions

- **Vapi over Retell AI and Bland.ai** — chosen after comparing the three main voice AI platforms. Vapi's prompt-first philosophy and clean webhook contract align with a prompt engineering workflow. Bland's Pathways shifts focus to a visual node builder, which undercuts prompt engineering. Retell AI was the backup; near-equivalent feature set.

- **GPT-4o Mini over GPT-4o** — at $0.01/min versus ~$0.06/min, GPT-4o Mini delivers comparable quality for structured, tool-calling workflows where the prompt does the heavy lifting. Temperature set to 0 for deterministic compliance behavior.

- **Deepgram Nova 3 for transcription** — 2.7% word error rate on English phone audio, with intelligent turn-taking to prevent the agent from interrupting mid-sentence. Keywords (Chase, Sapphire, Freedom) tuned to reduce misrecognition of brand names.

- **FDCPA and Reg F compliance read from primary sources** — all compliance rules (calling hours, Mini-Miranda, cease-and-desist, frequency cap, attorney redirect, dispute handling) were implemented directly from the FTC statute text and CFPB's Regulation F, not from summaries. See [`resources.md`](resources.md).

- **Flag-driven compliance** — the agent's behavior is fully determined by boolean flags on the account (`cease_and_desist`, `has_attorney`, `active_dispute`, etc.). The same prompt and the same backend work for any account. Adding a new compliance rule means adding a flag, not rewriting the prompt.

- **Server-side pre-call gate** — compliance is enforced in the backend before Vapi is ever contacted. The dashboard cannot start a blocked call even if JavaScript is bypassed.

- **Single webhook endpoint** — Vapi sends all tool calls and end-of-call reports to `POST /vapi/webhook`. The backend routes by function name via a `TOOL_HANDLERS` dictionary. Adding a new tool means adding one handler file — the webhook never changes.

- **Dynamic variable injection** — every call passes account data as Liquid variables (`{{consumer_first_name}}`, `{{past_due_amount}}`, etc.) into the system prompt via `assistantOverrides.variableValues`. The prompt is always the same template; the data changes per call.
