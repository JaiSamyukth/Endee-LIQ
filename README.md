# Endee-LIQ

<p align="center">
  <img src="https://img.shields.io/badge/Endee-Vector%20Database-success?style=for-the-badge" alt="Endee">
  <img src="https://img.shields.io/badge/LuminaAI-AI%20Tutor-blueviolet?style=for-the-badge" alt="LuminaAI">
  <img src="https://img.shields.io/badge/License-Apache%202.0-orange?style=for-the-badge" alt="License">
</p>

<p align="center">
  <strong>A complete AI-powered ecosystem featuring a high-performance vector database, intelligent educational assistant, and agentic memory system.</strong>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Endee - Vector Database](#endee---vector-database)
- [LuminaIQ - AI Educational Assistant](#luminaiq---ai-educational-assistant)
- [Agentic Memory System](#agentic-memory-system)
- [Architecture Diagram](#architecture-diagram)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Endee-LIQ is a comprehensive AI ecosystem built around **Endee**, a high-performance open-source vector database written in C++. This monorepo contains:

1. **Endee Core** - A production-grade vector database optimized for AI search, RAG, and semantic retrieval workloads
2. **LuminaIQ** - An intelligent educational AI assistant that uses RAG to help students learn from uploaded documents
3. **Agentic Memory System** - An AI agent with long-term semantic memory powered by Endee

---

## Project Structure

```
Endee-LIQ/
├── endee/                          # High-performance vector database (C++)
│   ├── src/                       # Core database implementation
│   ├── tests/                     # Test suites
│   ├── docs/                      # Documentation
│   ├── infra/                     # Docker configuration
│   ├── CMakeLists.txt            # Build configuration
│   └── README.md                  # Endee documentation
│
├── LuminaIQ/                      # AI Educational Assistant
│   ├── frontend/                  # React + TypeScript UI
│   │   ├── src/                   # React components
│   │   ├── package.json          # Frontend dependencies
│   │   └── vite.config.ts        # Vite configuration
│   │
│   ├── backend/                   # FastAPI Python backend
│   │   ├── services/              # Business logic services
│   │   ├── models/                # Data models
│   │   ├── utils/                 # Utility functions
│   │   ├── config/                # Configuration
│   │   └── requirements.txt       # Python dependencies
│   │
│   └── README.md                  # LuminaIQ documentation
│
└── endee/
    └── agentic-memory-system/     # AI Agent with Memory
        ├── agent_backend.py       # FastAPI + LangChain agent
        ├── server.js             # Express frontend server
        ├── public/               # Web UI
        ├── requirements.txt      # Python dependencies
        ├── package.json          # Node.js dependencies
        ├── docker-compose.yml    # Container orchestration
        └── README.md             # Agentic system documentation
```

---

## Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | Latest | Container runtime |
| Python | 3.10+ | Backend services |
| Node.js | 18+ | Frontend development |
| CMake | 3.20+ | Building Endee (optional) |

### One-Command Setup (Docker Recommended)

```bash
# Clone the repository
git clone https://github.com/endeeliq/Endee-LIQ.git
cd Endee-LIQ

# Start all services with Docker Compose
cd endee
docker compose up -d
```

This starts:
- Endee vector database at `http://localhost:8080`
- Ollama (if using agentic memory system)
- All application services

---

## Endee - Vector Database

<p align="center">
  <img src="docs/assets/logo-dark.svg" height="60" alt="Endee">
</p>

**Endee** is a high-performance open-source vector database built for AI search and retrieval workloads.

### Key Features

- **Blazing Fast Vector Search** - Optimized SIMD operations (AVX2, AVX512, NEON, SVE2)
- **Hybrid Retrieval** - Supports both dense and sparse vector search
- **Payload Filtering** - MongoDB-style filters for metadata-aware retrieval
- **Production Ready** - Backup/restore, logging, authentication
- **Zero Dependencies** - Self-contained C++ implementation
- **Multiple Deployment Options** - Docker, local build, or cloud

### Performance

| Metric | Value |
|--------|-------|
| Search Latency | < 10ms for 1M vectors |
| Indexing Speed | 100K+ vectors/second |
| Memory Usage | ~2GB per 1M vectors |
| Filtered Search | Sub-5ms with indexes |

### Supported Platforms

| Architecture | SIMD Target | Use Case |
|-------------|-------------|----------|
| Intel/AMD x86 | AVX2 | Desktop & laptop |
| Intel/AMD x86 | AVX512 | Server & workstation |
| Apple Silicon | NEON | M1/M2/M3/M4 Macs |
| ARM Server | SVE2 | ARMv9 servers |

### Quick Start - Docker

```bash
# Pull and run the latest image
docker run \
  --ulimit nofile=100000:100000 \
  -p 8080:8080 \
  -v ./endee-data:/data \
  --name endee-server \
  --restart unless-stopped \
  endeeio/endee-server:latest
```

Access the dashboard at: **http://localhost:8080**

### Quick Start - Local Build (Linux/macOS)

```bash
# Clone and build
git clone https://github.com/endee-io/endee.git
cd endee

# Make scripts executable
chmod +x ./install.sh ./run.sh

# Build (use --neon for Apple Silicon)
./install.sh --release --avx2

# Run
./run.sh
```

### API Usage Example

```python
from endee import Endee

# Connect to Endee
client = Endee()
client.set_base_url("http://localhost:8080/api/v1")

# Create an index
client.create_index(name="my_index", dimension=768, space_type="cosine")
index = client.get_index(name="my_index")

# Add vectors
index.upsert([
    {"id": "doc1", "vector": [0.1, 0.2, ...], "meta": {"text": "Hello world"}},
    {"id": "doc2", "vector": [0.3, 0.4, ...], "meta": {"text": "AI is great"}}
])

# Search
results = index.query(vector=[0.1, 0.2, ...], top_k=5)
print(results)
```

For full documentation, see [Endee Documentation](./endee/docs/getting-started.md)

---

## LuminaIQ - AI Educational Assistant

<p align="center">
  <img src="https://img.shields.io/badge/RAG-Enabled-success?style=flat-square">
  <img src="https://img.shields.io/badge/Chat-AI%20Tutor-blueviolet?style=flat-square">
  <img src="https://img.shields.io/badge/Quiz-Generator-orange?style=flat-square">
</p>

**LuminaIQ** is an intelligent educational AI assistant that ingests, processes, and serves knowledge from user-uploaded documents.

### Features

- **Project-Based Learning** - Create projects, upload study materials
- **Semantic Document Search** - Find relevant passages instantly
- **AI Tutor** - Ask questions and get contextual answers
- **Dynamic Quiz Generation** - Test your knowledge
- **Smart Notes** - Auto-generated study notes
- **Flashcards** - Spaced repetition learning
- **Mind Maps** - Visual knowledge representation
- **Pomodoro Timer** - Focus timer with break reminders
- **Gamification** - XP, streaks, and achievements
- **Advanced Analytics** - Track learning progress

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React + Vite)                  │
│   Dashboard • Chat • Quiz • Notes • Flashcards • Mindmaps  │
└───────────────────────────┬───────────────────────────────────┘
                            │ REST API
┌───────────────────────────▼───────────────────────────────────┐
│                     Backend (FastAPI + Python)                │
│   Auth • Projects • Documents • RAG • LLM • Gamification    │
└───────────────────────────┬───────────────────────────────────┘
                            │ Endee SDK
┌───────────────────────────▼───────────────────────────────────┐
│              Endee Vector Database (Docker)                  │
│   Semantic Search • Chunk Storage • Index Management       │
└─────────────────────────────────────────────────────────────┘
```

### Setup

#### 1. Start Endee

```bash
cd endee
docker compose up -d
```

#### 2. Backend Setup

```bash
cd LuminaIQ/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup

```bash
cd LuminaIQ/frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Endee Configuration
ENDEE_URL=http://localhost:8080

# LLM API (Together.ai)
TOGETHER_API_KEY=your_api_key_here

# Supabase (optional - for cloud features)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Key Services

| Service | File | Description |
|---------|------|-------------|
| RAG Service | `services/rag_service.py` | Retrieval-augmented generation |
| Embedding Service | `services/embedding_service.py` | Document embedding |
| LLM Service | `services/llm_service.py` | Language model integration |
| Quiz Service | `services/mcq_service.py` | Quiz generation |
| Notes Service | `services/notes_service.py` | Study notes generation |

For detailed documentation, see [LuminaIQ README](./LuminaIQ/README.md)

---

## Agentic Memory System

<p align="center">
  <img src="https://img.shields.io/badge/LangChain-Agent-green?style=flat-square">
  <img src="https://img.shields.io/badge/Ollama-LLM-yellowgreen?style=flat-square">
  <img src="https://img.shields.io/badge/Domain-Filtering-red?style=flat-square">
</p>

A **production-grade AI agent** that combines long-term semantic memory with LLM reasoning.

### Features

- **Semantic Memory Retrieval** - Search by meaning, not keywords
- **Tool-Based Autonomy** - Agent decides when to store memories
- **Three Domains** - Tasks, Personal, Research
- **Domain Filtering** - Scoped retrieval per conversation
- **Docker Support** - Full containerized deployment

### Architecture

```
┌────────────────────────────────────────────┐
│        Node.js Frontend (Express)          │
│  - Query input • Real-time display        │
│  - Domain selection • Memory visualization │
└───────────────┬────────────────────────────┘
                │ HTTP
┌───────────────▼────────────────────────────┐
│       FastAPI Backend (Python)             │
│  - LangChain agent orchestration           │
│  - Tool-calling for memory actions         │
│  - Endee Python SDK integration            │
└──────────┬────────────────┬───────────────┘
            │                │
┌──────────▼──────┐  ┌──────▼──────────────┐
│  Ollama          │  │  Endee Vector DB    │
│  - GLM-5 LLM     │  │  - Memory storage   │
│  - nomic-embed   │  │  - Semantic search │
└──────────────────┘  └─────────────────────┘
```

### Setup

#### 1. Start Endee

```bash
docker run -p 8080:8080 endeeio/endee-server:latest
```

#### 2. Start Ollama

```bash
# Pull required models
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest
docker exec -it ollama ollama pull glm-5
docker exec -it ollama ollama pull nomic-embed-text
```

#### 3. Setup This Project

```bash
cd endee/agentic-memory-system

# Linux/macOS
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

#### 4. Start Services

```bash
# Terminal 1 - Backend
source venv/bin/activate
python agent_backend.py

# Terminal 2 - Frontend
npm start
```

Open **http://localhost:3000**

### Query Examples

| Domain | Example Query |
|--------|---------------|
| Tasks | "Schedule a backend review meeting for next Tuesday at 3pm" |
| Assistant | "I prefer morning stand-ups before 9am" |
| Research | "What did I note about HNSW vs IVFFlat performance?" |

For detailed documentation, see [Agentic Memory README](./endee/agentic-memory-system/README.md)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Endee-LIQ Ecosystem                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                   │
│  │    LuminaIQ     │    │ Agentic Memory  │                   │
│  │ Educational AI  │    │     System      │                   │
│  └────────┬────────┘    └────────┬────────┘                   │
│           │                      │                              │
│           └──────────┬───────────┘                             │
│                      │                                           │
│              ┌───────▼───────┐                                  │
│              │  Endee SDK   │                                   │
│              └───────┬───────┘                                  │
│                      │                                           │
│  ┌───────────────────▼───────────────────────────────────┐     │
│  │                    Endee Vector Database                │     │
│  │  ┌─────────────────────────────────────────────────┐  │     │
│  │  │  Index Management • Vector Search • Filtering   │  │     │
│  │  │  Sparse Retrieval • Backup/Restore • Auth       │  │     │
│  │  └─────────────────────────────────────────────────┘  │     │
│  │                                                          │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │     │
│  │  │ AVX2/512 │ │   NEON   │ │   SVE2   │ │ SIMD SS  │  │     │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │     │
│  └───────────────────────────────────────────────────────┘     │
│                      │                                           │
│              ┌───────▼───────┐                                  │
│              │   C++ Core   │                                   │
│              │  Performance │                                   │
│              └─────────────┘                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Core - Endee

| Component | Technology |
|-----------|------------|
| Language | C++ (C++17) |
| Build System | CMake |
| Optimization | SIMD (AVX2/512, NEON, SVE2) |
| Database | MDBX (LMDB fork) |
| Web Server | Crow (C++ HTTP) |
| Serialization | MsgPack |

### LuminaIQ

| Component | Technology |
|-----------|------------|
| Frontend | React 18 + TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Backend | FastAPI (Python) |
| Database | Supabase (PostgreSQL) |
| Vector DB | Endee |
| LLM | Together.ai (Llama 3) |
| Embeddings | nomic-embed-text |

### Agentic Memory System

| Component | Technology |
|-----------|------------|
| Frontend | Express + Vanilla JS |
| Backend | FastAPI + Python |
| Agent | LangChain 0.3.x |
| LLM | Ollama (GLM-5) |
| Embeddings | Ollama (nomic-embed-text) |
| Vector DB | Endee |

---

## Installation

### Clone the Repository

```bash
git clone https://github.com/endeeliq/Endee-LIQ.git
cd Endee-LIQ
```

### Docker (Recommended)

All services can be started with Docker:

```bash
# Endee only
cd endee
docker compose up -d

# Agentic Memory System
cd endee/agentic-memory-system
docker compose up -d
```

### Manual Setup

See individual component README files:
- [Endee Setup](./endee/docs/getting-started.md)
- [LuminaIQ Setup](./LuminaIQ/README.md)
- [Agentic Memory Setup](./endee/agentic-memory-system/README.md)

---

## Contributing

We welcome contributions from the community!

### Ways to Contribute

1. **Report Bugs** - Open an issue with detailed reproduction steps
2. **Feature Requests** - Suggest new functionality
3. **Pull Requests** - Submit fixes and improvements
4. **Documentation** - Improve guides and examples
5. **Testing** - Help test and validate features

### Development Guidelines

- Follow existing code style and conventions
- Write tests for new features
- Update documentation accordingly
- Ensure all CI checks pass

### Contact

- **Discord**: [Join our community](https://discord.gg/5HFGqDZQE3)
- **Website**: [endee.io](https://endee.io)
- **Email**: [enterprise@endee.io](mailto:enterprise@endee.io)

---

## License

<p align="center">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License">
</p>

All components in this repository are licensed under the **Apache License 2.0**.

- **Endee**: Apache 2.0 - See [LICENSE](./endee/LICENSE)
- **LuminaIQ**: Apache 2.0
- **Agentic Memory System**: Apache 2.0

### Trademark

"Endee" and the Endee logo are trademarks of Endee Labs. The Apache License 2.0 does not grant permission to use these marks without prior written permission.

---

## Related Links

| Resource | URL |
|----------|-----|
| Endee GitHub | https://github.com/endee-io/endee |
| Endee Documentation | https://docs.endee.io |
| Endee Blog | https://endee.io/blog |
| LuminaIQ Demo | (Local) http://localhost:5173 |
| Agentic System Demo | (Local) http://localhost:3000 |

---

<p align="center">
  <strong>Built with ❤️ using Endee Vector Database</strong>
</p>