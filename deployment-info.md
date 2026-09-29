# Deployment Information

## Backend (Render)
- **Service**: Web Service (Python 3)
- **URL**: `https://collections-voice-agent.onrender.com`
- **Branch**: `develop`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Instance**: Free ($0/month)
- **GitHub Repo**: `AlejandraCarvajal95/collections-voice-agent`

## Key Endpoints
| Endpoint | Method | Purpose |
|---|---|---|
| `/dashboard` | GET | Demo dashboard UI |
| `/docs` | GET | Swagger API docs |
| `/vapi/webhook` | POST | Vapi tool calls + end-of-call reports |
| `/call/check` | POST | Pre-call compliance check |
| `/accounts` | GET | List all accounts |
| `/call/logs` | GET | Call history |
| `/data/reset` | POST | Reset demo data to original state |
| `/health` | GET | Health check |

## GitHub Repository
- **Repo**: `https://github.com/AlejandraCarvajal95/collections-voice-agent`
- **Branch**: `develop` (production code)
- **Branch**: `test` (has test endpoints, not deployed)

## Render Auto-Deploy
Render auto-deploys when you push to the `develop` branch on GitHub.
