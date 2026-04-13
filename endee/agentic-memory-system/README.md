# 🧠 Agentic AI Memory System with Endee

A **production-grade agentic AI system** that combines long-term semantic memory retrieval with LLM reasoning using **Endee Vector Database** as the memory backbone.

**Three integrated domains:** Task Automation · Personal Assistant · Research Assistant.

---

## Overview

### What This Is

A fully functional **AI agent** that:

- **Retrieves relevant memories** from Endee vector database before reasoning
- **Executes actions** (store tasks, notes, research findings) using LangChain tools
- **Maintains context** across multiple queries using semantic similarity search
- **Operates across three domains** with a unified memory architecture

### Architecture

```
┌────────────────────────────────────────────┐
│        Node.js Frontend (Express)          │
│  - Query input (task / assistant / research)│
│  - Real-time response display              │
│  - Memory retrieval visualisation          │
└───────────────┬────────────────────────────┘
                │ HTTP (JSON)
┌───────────────▼────────────────────────────┐
│       FastAPI Backend (Python)             │
│  - LangChain agent orchestration           │
│  - Tool-calling for memory actions         │
│  - Official Endee Python SDK integration   │
└──────────┬────────────────┬───────────────┘
           │                │
┌──────────▼──────┐  ┌──────▼──────────────┐
│  Ollama          │  │  Endee Vector DB    │
│  - GLM-5 LLM     │  │  - Memory storage   │
│  - nomic-embed   │  │  - Semantic search  │
│    (768-dim)     │  │  - Domain filtering │
└──────────────────┘  └─────────────────────┘
```

### Query Processing Flow

```
User Query
    ↓
Embed Query (Ollama nomic-embed-text → 768-dim vector)
    ↓
Search Endee (cosine similarity, optional domain filter)
    ↓
Retrieve Top-5 Most Relevant Memories
    ↓
Build Context → Pass Query + Memories → LangChain Agent
    ↓
Agent Reasons: Respond Only? Or Store New Memory?
    ↓
Execute Tool (if needed) → Embed Response → Upsert into Endee
    ↓
Return Response + Retrieved Memories + Action Metadata
```

---

## Features

✅ **Official Endee SDK** — Uses `pip install endee`, the first-party Python client  
✅ **Semantic Memory Retrieval** — Search by meaning, not keywords  
✅ **Tri-Domain Support** — Tasks, personal context, research findings  
✅ **Tool-Based Autonomy** — Agent decides when to store memories  
✅ **Domain Filtering** — Scoped retrieval per conversation domain  
✅ **Production Stack** — FastAPI, LangChain 0.3.x, Endee, Ollama  
✅ **Premium Dark UI** — Glassmorphic, animated, fully responsive  
✅ **Docker Support** — Full docker-compose for all services  
✅ **Extensible** — Easy to add new tools and domains  

---

## Setup & Installation

### Prerequisites

- **Docker** (required for Endee; also optional for Ollama)
- **Python 3.10+**
- **Node.js 18+**

### Step 1: Start Endee

Endee is the vector database that stores all agent memories.

**Quickest (Docker Hub image):**
```bash
docker run \
  --ulimit nofile=100000:100000 \
  -p 8080:8080 \
  -v ./endee-data:/data \
  --name endee-server \
  --restart unless-stopped \
  endeeio/endee-server:latest
```

**Or build from the forked repo source:**
```bash
# From the endee/ repo root (Linux / macOS only)
chmod +x ./install.sh ./run.sh
./install.sh --release --avx2    # Intel/AMD — use --neon for Apple Silicon
./run.sh
```

**Verify Endee is running:**
```bash
curl http://localhost:8080/api/v1/health
```

### Step 2: Start Ollama

```bash
# Docker (easiest)
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest
docker exec -it ollama ollama pull glm-5
docker exec -it ollama ollama pull nomic-embed-text

# Verify
curl http://localhost:11434/api/tags
```

Or install Ollama locally from [ollama.ai](https://ollama.ai) and pull the same models.

### Step 3: Setup This Project

```bash
cd endee/agentic-memory-system

# Linux / macOS
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

The script:
1. Creates a Python virtual environment
2. Installs all deps (`pip install endee langchain-ollama fastapi ...`)
3. Installs Node.js deps (`npm install`)
4. Creates `.env` from defaults if not present

### Step 4: Start Services

**Terminal 1 — Backend:**
```bash
source venv/bin/activate          # Windows: venv\Scripts\activate
python agent_backend.py
```

Expected output:
```
✓ Ollama connected — LLM: glm-5 | Embeddings: nomic-embed-text
✓ Endee index ready: 'agent_memory' (dim=768, cosine)
✓ Agent system initialised — ready for queries
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 — Frontend:**
```bash
npm start
```

Expected output:
```
✓ Frontend running on http://localhost:3000
  ↳ Backend: http://localhost:8000
```

### Step 5: Open the UI

Navigate to **http://localhost:3000**

---

## Usage

### Domains

| Domain | Button | What to store |
|--------|--------|---------------|
| 📋 **Tasks** | Tasks | Meetings, deadlines, to-dos, project status |
| 🤖 **Assistant** | Assistant | Personal preferences, schedules, notes |
| 🔬 **Research** | Research | Findings, insights, sources, experiments |

### Example Queries

**Task Domain:**
```
"Schedule a backend optimisation review meeting for next Tuesday at 3pm with the infra team"
```

**Assistant Domain:**
```
"I prefer morning stand-ups before 9am and keep my evenings free for deep work"
```

**Research Domain:**
```
"What vector indexing findings did I note about HNSW vs IVFFlat performance?"
```

### What Happens Each Query

1. Your query is embedded (Ollama)
2. Top-5 semantically similar memories are retrieved from Endee (filtered by domain)
3. Agent receives: query + retrieved memory context
4. Agent responds using past context, optionally storing new information
5. If stored: response is embedded and upserted into Endee automatically

---

## System Design

### Endee Integration

This project uses the **official Endee Python SDK**:

```python
from endee import Endee

client = Endee()
client.set_base_url("http://localhost:8080/api/v1")

# Create index
client.create_index(name="agent_memory", dimension=768, space_type="cosine")
index = client.get_index(name="agent_memory")

# Upsert memory
index.upsert([{
    "id": "mem-uuid",
    "vector": [0.123, ...],            # 768-dim embedding
    "filter": {"domain": "task"},     # for domain-scoped queries
    "meta": {"content": "...", "timestamp": "..."}
}])

# Semantic search with optional domain filter
results = index.query(
    vector=[...],
    top_k=5,
    filter=[{"domain": {"$eq": "task"}}]
)
```

### Memory Entry Structure

```python
{
    "id":     "uuid-v4",
    "vector": [0.123, ...],      # 768-dim from nomic-embed-text
    "filter": {"domain": "task | assistant | research"},
    "meta": {
        "domain":    "task",
        "content":   "Query: ...\nResponse: ...",
        "query":     "original user query",
        "timestamp": "2025-04-11T23:30:00"
    }
}
```

### Embedding Model Choice

**`nomic-embed-text`** (via Ollama, runs fully locally):
- Output: **768-dimensional** vectors
- Speed: ~100-200ms per embedding on CPU
- Quality: Strong semantic understanding for English + code
- Size: ~275 MB (reasonable for local use)

### LangChain Agent Tools

```python
@tool
def store_task(task_description, status="pending", priority="medium") -> str:
    """Store a task in agent long-term memory."""

@tool
def store_note(note_content, category="general") -> str:
    """Store a personal note or preference."""

@tool
def store_research_finding(finding, source=None, relevance="medium") -> str:
    """Store a research insight or discovery."""
```

The agent calls these autonomously when the user provides new information.
On pure retrieval queries, no tool is called.

---

## API Reference

### POST `/query`

```json
{
  "query":   "Schedule a backend meeting",
  "domain":  "task",
  "context": "optional extra detail"
}
```

Response:
```json
{
  "agent_response":     "I've noted your meeting...",
  "retrieved_memories": [
    {
      "id":         "mem-uuid",
      "similarity": 0.94,
      "payload":    {"domain": "task", "content": "...", "timestamp": "..."}
    }
  ],
  "action_taken": "responded_and_stored",
  "memory_id":    "new-mem-uuid"
}
```

### GET `/memories?domain=task&limit=10`

Returns the stored memories in the specified domain.

### GET `/health`

Returns service status: Ollama URL, Endee URL, model names, timestamp.

---

## Performance

| Component | Typical Latency |
|-----------|----------------|
| Embed query (Ollama, CPU) | 100–200 ms |
| Endee semantic search (top-5) | 10–50 ms |
| LLM reasoning (GLM-5, CPU) | 2–6 s |
| Store memory (Endee upsert) | 10–50 ms |
| **Total** | **2.2–6.3 s** |

### Optimisation Tips

1. **GPU for Ollama** (cuts LLM + embed time by ~3–5×):
   ```bash
   docker run -d -p 11434:11434 --gpus all ollama/ollama:latest
   ```

2. **Reduce top_k** — change `TOP_K = 5` → `TOP_K = 3` in `agent_backend.py`

3. **Smaller model** — swap `glm-5` → `mistral` (faster reasoning, comparable quality)

4. **Alternative embedding** — swap `nomic-embed-text` → `all-minilm` (smaller, faster)

---

## Troubleshooting

### Backend won't connect to Ollama

```bash
curl http://localhost:11434/api/tags
# If 404: docker restart ollama   OR   ollama serve
```

### Endee index creation fails

```bash
curl http://localhost:8080/api/v1/health
# Check Endee is running on :8080
```

### `endee` package not found

```bash
source venv/bin/activate
pip install endee
```

### Models missing in Ollama

```bash
docker exec -it ollama ollama pull glm-5
docker exec -it ollama ollama pull nomic-embed-text
ollama list   # verify
```

### Slow responses

- Verify GPU is used by Ollama (`nvidia-smi` should show Ollama process)
- Decrease `TOP_K` in `agent_backend.py`
- All services should be on the same machine (no cross-network calls)

---

## Extending the System

### Add a New Tool

In `agent_backend.py`:

```python
@tool
def store_code_snippet(snippet: str, language: str, description: str) -> str:
    """Store a useful code snippet in long-term memory."""
    memory_id = str(uuid.uuid4())
    return f"Snippet stored: {memory_id} | [{language}] {description}"

tools = [store_task, store_note, store_research_finding, store_code_snippet]
```

### Add a New Domain

1. Add a domain button in `public/index.html` (copy the existing pattern)
2. Update `SYSTEM_PROMPT` in `agent_backend.py` with the new domain rules
3. Add a corresponding store tool for that domain

---

## Repository Structure

```
agentic-memory-system/
├── agent_backend.py      # FastAPI + LangChain + official Endee SDK
├── server.js             # Express proxy server
├── public/
│   └── index.html        # Premium dark-themed web UI
├── requirements.txt      # Python deps (includes endee SDK)
├── package.json          # Node.js deps
├── .env                  # Configuration (edit to customise)
├── setup.sh              # One-command setup (Linux / macOS)
├── setup.bat             # One-command setup (Windows)
├── Dockerfile.backend    # Backend container
├── Dockerfile.frontend   # Frontend container
├── docker-compose.yml    # All-in-one compose (Endee + Ollama + app)
├── README.md             # This file
├── QUICKSTART.md         # Condensed startup guide
└── SUBMISSION_CHECKLIST.md
```

---

## What This Demonstrates

✅ **Official SDK usage** — `pip install endee`, not raw HTTP hacking  
✅ **Vector DB integration** — semantic similarity + cosine distance  
✅ **Payload filtering** — MongoDB-style domain scoping via Endee filters  
✅ **Agent autonomy** — tool-calling based on LLM reasoning, not rules  
✅ **Tri-domain architecture** — extensible beyond a single use case  
✅ **Production patterns** — error handling, logging, env-based config  
✅ **Full vertical stack** — browser → Express → FastAPI → Ollama + Endee  

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Vector DB | **Endee** (official `endee` SDK) |
| LLM | **GLM-5** via Ollama |
| Embeddings | **nomic-embed-text** (768-dim) via Ollama |
| Agent | **LangChain 0.3.x** `create_tool_calling_agent` |
| Backend | **FastAPI** + Uvicorn |
| Frontend | **Express** proxy + Vanilla HTML/CSS/JS |
| Containers | **Docker** + Docker Compose |

---

## GitHub

**Repository:** https://github.com/JaiSamyukth/endee/tree/main/agentic-memory-system

---

## License

Apache License 2.0 — same as Endee.

---

**Built with:** Endee · FastAPI · LangChain · Ollama · Express  
