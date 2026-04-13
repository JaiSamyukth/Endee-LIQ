# Quick Start Guide

## 1-Minute Setup (Assuming Ollama + Endee Running)

```bash
# Terminal 1: Backend
python -m venv venv
source venv/bin/activate
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
# Python 3.10+
python3 --version

# Node.js 16+
node --version

# Git
git --version
```

### Step 1: Start Endee

**From your forked Endee repo:**

```bash
cd endee
chmod +x install.sh run.sh
./install.sh --release --avx2
./run.sh

# In another terminal, verify:
curl http://localhost:8080/health
```

**Or with Docker:**
```bash
docker-compose up -d
```

### Step 2: Start Ollama

**With Docker (easiest):**
```bash
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest

# Pull models
docker exec -it ollama ollama pull glm-5
docker exec -it ollama ollama pull nomic-embed-text

# Verify
curl http://localhost:11434/api/tags
```

**Or local installation:**
```bash
# Download from https://ollama.ai
ollama pull glm-5
ollama pull nomic-embed-text
```

### Step 3: Setup Agentic System

```bash
# Clone and navigate
git clone https://github.com/JaiSamyukth/endee.git
cd endee
mkdir agentic-memory-system
cd agentic-memory-system

# Copy files (from wherever you cloned them)
cp path/to/agent_backend.py .
cp path/to/requirements.txt .
cp path/to/package.json .
cp path/to/server.js .
cp path/to/.env .
mkdir public
cp path/to/public/index.html public/

# Run setup script
chmod +x setup.sh
./setup.sh
```

### Step 4: Start Services

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python agent_backend.py
```

Expected output:
```
✓ Ollama connected: glm-5 + nomic-embed-text
✓ Endee index ready: agent_memory
INFO:     Started server process [XXXX]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Terminal 2 - Frontend:**
```bash
npm start
```

Expected output:
```
✓ Frontend running on http://localhost:3000
  Backend: http://localhost:8000
```

### Step 5: Test the System

1. Open **http://localhost:3000**
2. You should see the UI
3. Try a query: `"I need to schedule a team meeting tomorrow"`
4. Should get response with retrieved memories

---

## Environment Configuration

Edit `.env` if your services run on different ports:

```env
# Backend
OLLAMA_BASE_URL=http://localhost:11434
ENDEE_BASE_URL=http://localhost:8080

# Frontend
PORT=3000
BACKEND_URL=http://localhost:8000
```

---

## Docker Compose (Optional, All-In-One)

Create `docker-compose.yml` in your agentic-memory-system directory:

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434

  endee:
    build:
      context: ../endee
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - RUST_LOG=info

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - ENDEE_BASE_URL=http://endee:8080
    depends_on:
      - ollama
      - endee

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      - backend

volumes:
  ollama_data:
```

Then:
```bash
docker-compose up
```

---

## Verification Checklist

- [ ] Ollama running on `:11434`
- [ ] Endee running on `:8080`
- [ ] Python venv activated
- [ ] Backend started on `:8000`
- [ ] Frontend started on `:3000`
- [ ] All health checks passing
- [ ] Can submit queries and see responses

---

## Common Issues & Fixes

### "Connection refused" to Ollama
```bash
# Restart Ollama
docker restart ollama
# or
ollama serve
```

### "Connection refused" to Endee
```bash
# From endee directory
./run.sh
```

### "Module not found" errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### Slow responses
- Check GPU acceleration is enabled in Ollama
- Reduce `top_k` in backend (currently 5)
- Ensure all services are on same machine (no network latency)

### Models not found
```bash
docker exec ollama ollama pull glm-5
docker exec ollama ollama pull nomic-embed-text
```

---

## Performance Tips

1. **Use GPU for Ollama:**
   ```bash
   docker run -d -p 11434:11434 --gpus all ollama/ollama:latest
   ```

2. **Increase resource allocation:**
   Edit `docker-compose.yml` or system settings

3. **Cache frequently used embeddings** (future optimization)

4. **Use smaller embedding model** if needed:
   - Change to `all-minilm` (faster, slightly less accurate)

---

## Next Steps

1. ✅ Get system running locally
2. 🧪 Test with various queries
3. 📝 Customize system prompt in `agent_backend.py`
4. 🔧 Add new tools or domains
5. 🚀 Deploy to cloud (AWS EC2, DigitalOcean, etc.)

---

## Cloud Deployment Notes

For production deployment:

1. **Use managed vector DB** (Pinecone, Weaviate) instead of local Endee
2. **Ollama on GPU instance** (AWS g4dn.xlarge or similar)
3. **FastAPI on serverless** (AWS Lambda, Google Cloud Run)
4. **Frontend on CDN** (CloudFlare, AWS CloudFront)
5. **Add authentication** (JWT tokens)
6. **Add rate limiting** (prevent abuse)
7. **Add monitoring** (CloudWatch, DataDog)

---

Good luck! 🚀
