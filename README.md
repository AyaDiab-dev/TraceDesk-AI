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
- **Conversational Voice Assistant:** Goes beyond traditional speech-to-text by introducing a wake-phrase-driven, hands-free interaction experience. Employees can call TraceDesk AI by name to initiate a voice conversation, speak their IT support requests naturally, and receive spoken responses through browser-based speech recognition and text-to-speech. The feature is designed to make technical support feel more immediate, accessible, and conversational, while remaining subject to browser support and speech-recognition limitations.

## Beyond Text: Conversational Voice Experience

TraceDesk AI introduces a voice-first interaction layer designed to make IT support feel like a natural conversation rather than a traditional chatbot.

Instead of relying exclusively on typing and clicking, employees can interact with the assistant through a combination of voice activation, spoken requests, and audible responses.

**Voice interaction highlights:**

- **Wake-phrase activation:** Designed to recognize a call to TraceDesk AI and initiate voice interaction without requiring a typed message.
- **Natural spoken requests:** Employees can describe technical problems conversationally instead of filling out rigid forms.
- **Spoken AI responses:** Text-to-speech allows the assistant to communicate its answers aloud.
- **Conversation-oriented experience:** Voice interaction is integrated into the same support workflow as knowledge retrieval, incident checks, and ticket assistance.
- **Trust and control:** Voice interaction does not bypass the human approval requirement for ticket creation.

**Implementation note:** The voice experience uses browser-based speech capabilities. Wake-phrase recognition and continuous interaction depend on browser support, microphone permissions, and recognition accuracy. It is an experimental interaction feature rather than a guaranteed always-on voice service.
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

## How to Use TraceDesk AI

### Demo Walkthrough

1. Start the simulated Helpdesk API, TraceDesk AI backend, and React frontend as described above.
2. Open the frontend URL in your browser.
3. Click **Get Started** on the landing page.
4. On the Employee Identification screen, enter the following employee email from the simulated Nakhla Systems dataset:

   `samir.nassar@nakhla.example`

5. After successful identification, use the Agent Workspace to submit an IT support question.

   Example:

   `My VPN shows NX-503. What should I do?`

6. Review the agent's response and any supporting information displayed in **Evidence & Trust Trace**.
7. For requests that require a support ticket, review the proposed ticket draft and choose **Approve** or **Reject**.
8. Explore the available conversation history, ticket-related views, and knowledge-base information.

### How the Agent Works

TraceDesk AI uses LangGraph to orchestrate the support workflow.

- **Request understanding:** The agent analyzes the employee's request and determines the appropriate processing path.
- **Knowledge retrieval:** RAG retrieves relevant information from the official knowledge base, prioritizing current and authoritative documents.
- **Live helpdesk information:** MCP tools provide access to supported helpdesk operations, including employee information, service status, and tickets.
- **Response generation:** The agent combines relevant evidence to generate a grounded response.
- **Evidence and trust:** The interface presents supporting information and relevant decision details.
- **Ticket approval:** When a support ticket is needed, the agent prepares a draft. Ticket creation requires explicit employee approval before the action is executed.

The agent is designed to avoid presenting unsupported information as verified and to preserve employee control over ticket creation.

## Configuration Notes

Create a local `.env` file using `.env.example` and configure the environment before starting the services.

| Setting | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | API key used to access the configured language and embedding models |
| `MODEL` | Chat model used by the agent |
| `EMBEDDING_MODEL` | Embedding model used for knowledge retrieval |
| `HELPDESK_API_KEY` | Shared API key for the simulated Helpdesk API, MCP server, and application |
| `HELPDESK_API_URL` | Simulated Helpdesk API address, defaulting to `http://localhost:8102` |
| `APP_URL` | TraceDesk AI backend address, defaulting to `http://localhost:8000` |
| `JUDGE_MODEL` | Optional model used for LLM Judge evaluation |

Keep API credentials private. Never commit `.env` or real secrets to version control.

## Troubleshooting

| Problem | Suggested check |
|---|---|
| Frontend cannot communicate with the agent | Confirm that the FastAPI backend is running on port `8000` and the Vite proxy is configured correctly |
| Helpdesk information is unavailable | Confirm that the simulated Helpdesk API is running on port `8102` and the shared API key matches |
| Language-model requests fail | Verify `OPENROUTER_API_KEY`, the configured model identifiers, and API access |
| Employee identification fails | Use an email present in the simulated employee directory and confirm that the Helpdesk service is reachable |
| Voice interaction does not work | Check browser speech-recognition support and microphone permissions |
| Evaluation fails to connect | Confirm that the required services are running and that `APP_URL` points to the correct backend |

## Demo Scope

TraceDesk AI is a local educational demonstration built on the bootcamp's simulated helpdesk environment. Its employee directory, knowledge base, service incidents, and ticket operations use the provided training data.

The employee identification flow is intended for demonstration purposes and does not replace production authentication or authorization.

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
