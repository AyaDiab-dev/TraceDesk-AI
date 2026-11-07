# TraceDesk AI

**An evidence-driven Agentic AI IT Helpdesk Assistant**

TraceDesk AI is an intelligent IT support assistant that combines retrieval-augmented generation (RAG), LangGraph orchestration, Model Context Protocol (MCP) tools, and human approval to deliver grounded technical support.

Rather than simply generating answers, TraceDesk AI is designed to check trusted company knowledge, consult live helpdesk information, explain the evidence behind its responses, and request explicit employee approval before creating support tickets.

## Key Features

- **Knowledge-grounded assistance:** Retrieves relevant information from the company's official knowledge base, including Markdown and PDF documents.
- **Policy-aware retrieval:** Prioritizes current, authoritative documents and respects superseded knowledge-base entries.
- **Incident-aware troubleshooting:** Consults live service status to identify incidents that may affect the employee.
- **Agentic orchestration:** Uses LangGraph to coordinate request classification, retrieval, tool use, and response generation.
- **MCP integration:** Connects to the simulated helpdesk system for employee lookup, service status, ticket search, and approved ticket operations.
- **Human approval gate:** Prepares ticket drafts and requires explicit approval before creating a ticket.
- **Evidence & Trust Trace:** Presents supporting evidence and relevant decision information without exposing private model reasoning.
- **Conversation experience:** Includes a React interface with employee identification and conversation-related features.
- **Voice assistant:** Includes browser-based speech interaction and wake-phrase handling, subject to browser support and recognition limitations.

## Architecture

```text
Employee
   |
   v
React + Vite Frontend
   |
   v
TraceDesk AI FastAPI Backend (:8000)
   |
   v
LangGraph Agent
   |
   +---- RAG Pipeline
   |       |
   |       +---- Official Knowledge Base
   |       +---- Document Filtering
   |       +---- Embeddings & Retrieval
   |
   +---- MCP Client
   |       |
   |       +---- Employee Directory
   |       +---- Service Status
   |       +---- Historical Tickets
   |
   +---- Ticket Draft
           |
           v
      Employee Approval
           |
           v
      MCP create_ticket
           |
           v
Simulated Helpdesk API (:8102)
```

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Agent orchestration | LangGraph |
| Knowledge retrieval | RAG, embeddings, document retrieval |
| Tool integration | MCP |
| Language models | OpenRouter-compatible model API |
| Evaluation | Scenario-based automated tests and LLM Judge |
| Helpdesk environment | Simulated Nakhla Systems IT Helpdesk |

## Getting Started

### Prerequisites

- Python 3.12
- Node.js and npm compatible with the installed Vite version
- OpenRouter API key

### 1. Clone the repository

```bash
git clone https://github.com/AyaDiab-dev/TraceDesk-AI.git
cd TraceDesk-AI
```

### 2. Set up Python

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure the required API keys and model settings in `.env`.

Never commit `.env` or actual API credentials.

### 3. Start the simulated Helpdesk API

In the first terminal:

```powershell
uvicorn services.helpdesk_api:app --port 8102
```

### 4. Start the TraceDesk AI Backend

In a second terminal, from the repository root with the Python environment activated:

```powershell
uvicorn services.resolveai_api:app --host 127.0.0.1 --port 8000
```

### 5. Start the React Frontend

In a third terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL displayed by Vite (typically `http://localhost:5173`).

During development, Vite proxies `/api` and `/health` requests to `http://127.0.0.1:8000` by default. Set `API_PROXY_TARGET` before starting Vite if the backend uses a different address.

## Evaluation

TraceDesk AI was evaluated using the bootcamp's official Scenario 2 evaluation runner.

| Evaluation | Recorded result |
|---|---|
| Official scenario cases S2-01 through S2-10 | 10/10 passed |
| Additional LLM Judge checks for S2-02, S2-04, S2-08 | 3/3 passed |

These results were collected from individual saved evaluation runs. They do not represent a single combined evaluation run or guarantee performance on hidden tests.

Example:

```powershell
python .\evals\run_evals.py --only S2-05 --out evals/local_s2_05
```

The official evaluation runner and sample scenarios are located in `evals/`.

## Security and Trust

TraceDesk AI follows several important safeguards:

- Ticket creation requires explicit approval.
- A rejected ticket draft must not create a ticket.
- Knowledge-base evidence is checked for authority and document precedence.
- Missing or unsupported information should not be presented as verified fact.
- Live service information is used when relevant to troubleshooting.
- Evidence summaries are separate from private model reasoning.

## Limitations

This is an educational demonstration, not a production IT support platform.

- Nakhla Systems, its employees, incidents, and helpdesk data are simulated.
- Employee identification in the demo must not be treated as production-grade authentication.
- Voice recognition depends on browser capabilities, microphone permissions, and speech recognition accuracy.
- Generated responses and ticket drafts should be reviewed before operational use.
- Passing the provided sample tests does not guarantee passing unseen evaluations.

## Project Structure

```text
agent/          Agent logic, retrieval, ticket drafting
services/       FastAPI backend and simulated helpdesk services
dataset/        Official knowledge base and evaluation data
frontend/       React and Vite interface
evals/          Scenario evaluation runner and sample cases
tests/          Additional local tests
docs/           Original kit documentation
```

## Acknowledgments

Developed as an Agentic AI Bootcamp final mini-project, Scenario 2: IT Helpdesk Agent.

The simulated helpdesk environment, Nakhla Systems dataset, MCP server, API contract, and evaluation kit were provided as part of the bootcamp materials.

The original kit README is preserved at `docs/ORIGINAL_KIT_README.md`.

**Version:** v1
# IT Helpdesk kit

Everything your agent needs around it, so your week goes into the agent:

- the **dataset** of Nakhla Systems, a fictional software company: 20 knowledge-base documents
  (2 of them PDF-only), 40 historical tickets, 25 employees, a status page;
- the company's **helpdesk API** (simulated system of record, FastAPI, port **8102**);
- an **MCP server** in front of it (stdio, 6 tools);
- a **UI starter**, the **eval runner** and 10 **sample cases**.

You build the agent: retrieval over the knowledge base, the conversation, the approval gate,
your API contract on port 8000. Do not change the simulated systems: the hidden tests run
against the original.

## Quickstart (Windows PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env                                  # then fill in OPENROUTER_API_KEY

uvicorn services.helpdesk_api:app --port 8102           # terminal 1: the helpdesk API
python check_kit.py                                     # terminal 2: must end with "Kit ready."
python dataset/validate_dataset.py                      # optional: dataset consistency
```

macOS/Linux: `python3.12 -m venv .venv`, `source .venv/bin/activate`, `cp .env.example .env`.
Docker instead of uvicorn: `docker compose up --build` (same API on port 8102).

One venv is enough for the kit **and** your agent: `requirements.txt` also pins the course's agent
framework (`langgraph==1.2.10`, `openai==2.52.0`) and `mcp==1.28.1`, the MCP version CrewAI 1.15 needs.
Already have the course's Module 2 venv? `pip install -r requirements.txt` into it works too.

## Layout

| Path | What |
|---|---|
| `dataset/` | knowledge base, tickets, schemas, manifest, precedence rules: start with `dataset/README.md` |
| `services/helpdesk_api.py` | the simulated helpdesk API (system of record) |
| `services/helpdesk_mcp.py` | the MCP server your agent uses (`python -m services.helpdesk_mcp`) |
| `services/data/` | seed data: `employees.json` (directory), `status.json` (status page) |
| `services/Dockerfile`, `docker-compose.yml` | container for the API; add your app to the compose file |
| `ui/app_ui.py` | Gradio starter: chat, sources panel, ticket-draft card with Approve / Reject. Talks only to your API. |
| `evals/` | `cases.sample.jsonl` (10 cases) and `run_evals.py` (the shared runner) |
| `check_kit.py` | smoke test: API health, a keyed REST call, MCP `list_tools` + one read call |

## The helpdesk API (port 8102)

Business endpoints need the header `X-API-Key` (value of `HELPDESK_API_KEY`). Errors are JSON:
`{"error": {"code": "...", "message": "...", "fields": [...]}}` with real HTTP codes.
Interactive docs: http://localhost:8102/docs

| Method | Path | What it does | Errors |
|---|---|---|---|
| GET | `/health` | `{"status": "ok", "service": "helpdesk"}` (no key) | |
| GET | `/api/directory/{email}` | employee: department, office, VIP, contractor, MFA, VPN client and gateway, account status | 401, 404 `employee_not_found` |
| GET | `/api/status` | status page: services and incidents (`active_incidents` lists the ids) | 401 |
| GET | `/api/tickets?requester_email=&q=&status=&limit=` | search the archive and new tickets; `q` = keywords in subject and description; `status` = open, resolved, closed; `limit` 1-50 (default 10) | 401, 422 |
| GET | `/api/tickets/{ticket_id}` | one ticket with notes | 401, 404 `ticket_not_found` |
| POST | `/api/tickets` | create a ticket; body = `dataset/schemas/ticket.schema.json`; header `Idempotency-Key`; returns 201 and the ticket with `ticket_id` IT-2001, IT-2002, ... | 401, 400, 409 `idempotency_conflict`, 422 `validation_error` with `fields` |
| POST | `/api/tickets/{ticket_id}/notes` | add a note `{"note": "..."}`; header `Idempotency-Key` | 401, 404, 409, 422 |

Ticket body rules: `category` from the 8 categories, `priority` P1-P4, `requester_email` must be in
the directory, `department` must match the directory, `attempted_steps` needs at least one step,
every `kb_refs` id must exist (`[]` is allowed when the KB has no answer), optional `affected_users`.
The API sets `assigned_team` from the category and adds `warnings` if you cite a deprecated or draft document.
Same `Idempotency-Key` + same body = the same ticket, never a duplicate.

### Test-only admin endpoints (no key)

They exist for the eval runner and the hidden tests. **Your app must not call them.**

| Method | Path | What it does |
|---|---|---|
| POST | `/admin/reset` | restore the seed data, clear faults, logs and created tickets |
| POST | `/admin/faults` | `{"target": "create_ticket", "mode": "error_503", "count": 1}`: the next `count` calls of that operation fail |
| GET / DELETE | `/admin/faults` | show / clear armed faults |
| GET | `/admin/log` | recent requests: method, path, status, ms, operation |
| GET | `/admin/tickets` | tickets created since the last reset (`?all=1`: archive too) |
| GET | `/admin/notes` | notes added since the last reset |

Fault targets: `create_ticket`, `directory`, `status`, `search_tickets`, `get_ticket`, `add_note`.
Modes: `error_500`, `error_503`, `timeout` (waits 15 s, then 504), `slow` (waits 3 s, then succeeds).

```powershell
curl.exe -X POST http://localhost:8102/admin/faults -H "Content-Type: application/json" `
  -d '{\"target\": \"create_ticket\", \"mode\": \"error_503\", \"count\": 1}'
curl.exe -X POST http://localhost:8102/admin/reset
```

## The MCP server (stdio)

Your app starts it as a subprocess and talks MCP over stdin/stdout. It calls the REST API, so
its state is the state the tests see. Tool errors come back as `{"ok": false, "error": {...}}`.

| Tool | Use it to |
|---|---|
| `lookup_employee(email)` | get department, VIP, contractor, MFA, VPN client version and gateway **before** applying department rules or choosing a priority |
| `get_service_status()` | check for an active incident **before** troubleshooting or drafting a ticket |
| `search_tickets(query=None, requester_email=None, status=None, limit=5)` | the requester's ticket history (your long-term memory) and similar past cases |
| `create_ticket(subject, description, category, priority, requester_email, department, attempted_steps, kb_refs, idempotency_key, affected_users=1)` | **write**: only from your approval step, after the employee approved this exact draft |
| `get_ticket(ticket_id)` | one ticket with its notes |
| `add_ticket_note(ticket_id, note)` | **write**: add information to the employee's own ticket |

```python
import os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

params = StdioServerParameters(command=sys.executable, args=["-m", "services.helpdesk_mcp"],
                               env=dict(os.environ))   # pass env on, or the server will not see your .env values
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("lookup_employee", {"email": "tariq.hamdan@nakhla.example"})
```

The knowledge base is **not** an MCP tool: ingestion, chunking, embeddings and retrieval over
`dataset/knowledge_base/` (Markdown and PDF) are yours to build, for example OpenRouter
`openai/text-embedding-3-small` with a numpy cosine store, or Chroma.

## The approval gate

Keep `create_ticket` (and `add_ticket_note`) **out of the model's tool list**. The model drafts a
ticket; your API returns it as `pending_action` (`type: "create_ticket"`); only `POST /api/approve`
calls `create_ticket` over MCP with exactly that payload and `idempotency_key = action_id`.
Show only the `ticket_id` the API returned. A rejected draft writes nothing.

## Environment variables

| Variable | Default | Used by |
|---|---|---|
| `HELPDESK_API_KEY` | `dev-key-change-me` | API, MCP server, check_kit (must be the same everywhere) |
| `HELPDESK_API_URL` | `http://localhost:8102` | MCP server, check_kit, your app |
| `HELPDESK_TODAY` | real today | API: date of new tickets and of the status page (`YYYY-MM-DD`) |
| `HELPDESK_TIMEOUT_S` | `20` | MCP server: seconds before a call to the API gives up |
| `HELPDESK_MCP_LOG_LEVEL` | `WARNING` | MCP server log level on stderr |
| `HELPDESK_DATA_DIR`, `HELPDESK_DATASET_DIR` | `services/data`, `dataset` | API seed files |
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `MODEL`, `EMBEDDING_MODEL` | see `.env.example` | your agent |
| `APP_URL` | `http://localhost:8000` | UI starter, eval runner |

The API and the MCP server also read the kit's `.env` (without overriding variables you already set).

## UI starter and evals

```powershell
python ui/app_ui.py                          # http://localhost:7860, talks to APP_URL
python evals/run_evals.py                    # the 10 sample cases against your app on :8000
python evals/run_evals.py --only S2-05 -v    # one case, every turn
```

The case format and the API contract are described in the mini-project's `common/CONTRACT.md`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `check_kit.py`: API not answering | start `uvicorn services.helpdesk_api:app --port 8102` from this folder |
| 401 `unauthorized` | the same `HELPDESK_API_KEY` for the API, the MCP server and your app |
| MCP tool returns `unreachable` | the API is not running, or `HELPDESK_API_URL` is wrong (in Docker use the service name) |
| Everything fails with 503 | a fault is still armed: `curl.exe -X DELETE http://localhost:8102/admin/faults` |
| Ticket ids keep growing | `POST /admin/reset` restores the seed state (tests do this before every case) |
