# Quick Start Guide

## TL;DR (Assuming Ollama + Endee Already Running)

```bash
# Terminal 1: Backend
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python agent_backend.py

# Terminal 2: Frontend (new terminal)
npm install
npm start

# Open: http://localhost:3000
```

---

## Full Setup From Scratch

### Prerequisites Check

```bash
python3 --version   # needs 3.10+
node --version      # needs 16+
docker --version    # for Endee (required)
```

### Step 1: Start Endee (Vector Database)

```bash
# Pull and run the official Endee Docker image
docker run \
  --ulimit nofile=100000:100000 \
  -p 8080:8080 \
  -v ./endee-data:/data \
  --name endee-server \
  --restart unless-stopped \
  endeeio/endee-server:latest

# Verify (open in browser or curl)
curl http://localhost:8080/api/v1/health
```

### Step 2: Start Ollama + Pull Models

```bash
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest
docker exec -it ollama ollama pull glm-5
docker exec -it ollama ollama pull nomic-embed-text
curl http://localhost:11434/api/tags   # verify
```

### Step 3: Setup the Agentic System

```bash
cd endee/agentic-memory-system
chmod +x setup.sh && ./setup.sh   # Linux/macOS
# OR
setup.bat                          # Windows
```

### Step 4: Start Services

```bash
# Terminal 1 — Backend (must see "Endee index ready")
source venv/bin/activate
python agent_backend.py

# Terminal 2 — Frontend
npm start
```

### Step 5: Test

1. Open **http://localhost:3000**
2. Select domain (Tasks / Assistant / Research)
3. Submit: `"I need to schedule a team meeting tomorrow"`
4. Observe: agent responds AND stores the memory in Endee

---

## Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `ENDEE_BASE_URL` | `http://localhost:8080` | Endee server URL |
| `ENDEE_AUTH_TOKEN` | *(empty)* | Set if Endee started with `NDD_AUTH_TOKEN` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_MODEL` | `glm-5` | Reasoning model (fallback: `mistral`, `llama3`) |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model (768-dim) |
| `PORT` | `3000` | Express server port |
| `BACKEND_URL` | `http://localhost:8000` | FastAPI URL (used by Express) |

---

## Verification Checklist

- [ ] Endee running on `:8080` (`curl http://localhost:8080/api/v1/health`)
- [ ] Ollama running on `:11434` (`curl http://localhost:11434/api/tags`)
- [ ] glm-5 model pulled
- [ ] nomic-embed-text model pulled
- [ ] Backend started (`curl http://localhost:8000/health`)  
- [ ] Frontend started and loads at `http://localhost:3000`
- [ ] Can submit a query and see an agent response
- [ ] Second similar query retrieves the first memory

---

## Common Issues

| Symptom | Fix |
|---------|-----|
| `endee` package not found | `pip install endee` in your venv |
| `Connection refused :8080` | Start Endee: `docker start endee-server` |
| `Connection refused :11434` | Start Ollama: `docker start ollama` |
| `Model not found` | Pull models: `docker exec ollama ollama pull glm-5` |
| Slow responses | Enable GPU for Ollama (`--gpus all` flag) |

---

Good luck! 🚀
