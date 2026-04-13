# LuminaIQ

LuminaIQ is an intelligent, educational AI assistant designed to ingest, process, and intuitively serve knowledge from user-uploaded documents. It demonstrates a complete, production-ready Retrieval-Augmented Generation (RAG) system built with a heavy emphasis on seamless user experience and modern semantic search capabilities.

## 🎯 Project Overview & Problem Statement

Modern learners and professionals are overwhelmed by the volume of reading material — PDFs, textbooks, and documentation. While traditional keyword search is primitive, existing AI tools often serve as generic chatbots that lack deep, persistent contextual grounding on *your* specific material.

**LuminaIQ** solves this by letting users create "Projects" into which they can upload study materials. The system chunks and semantically embeds the text, enabling an AI tutor to accurately retrieve relevant passages, generate dynamic quizzes, and provide guided study notes. The problem it targets is moving beyond passive reading into active, AI-assisted learning and knowledge retention.

## 🏗️ System Design & Technical Approach

The architecture is split into a robust backend and a highly interactive frontend:

1. **Frontend (React / Vite)**: A dynamic, app-like interface that prioritizes rich aesthetics and usability. It features a modern Sidebar, a chat interface for the AI Tutor, an Interactive Demo, and floating panels for Pomodoro timers.
2. **Backend (FastAPI)**: Serves native Python endpoints that mediate all operations. It orchestrates user projects, document chunking, background task processing, and prompt assembly.
3. **LLM Engine (LangChain & Together)**: Employs powerful LLMs (e.g., Llama 3) via LangChain to act as the cognitive reasoning engine for chat, summarization, and study material generation.
4. **Vector Database (Endee)**: Powers the semantic core of the application by efficiently indexing and querying high-dimensional vectors to perform accurate RAG operations.

## 🧠 How Endee is Used

**Endee** operates as the exclusive semantic engine and vector database for the entire LuminaIQ system. 

When a user uploads a new document:
1. The backend parses and splits the text into semantic chunks.
2. These chunks are embedded using an embedding model and securely upserted via the Endee Python SDK into dynamically created indexes (e.g., `project_{project_id}`).
3. Endee achieves ultra-fast indexing and scales perfectly for the dynamic creation and destruction of topic clusters without database bloat.
4. During user interaction (e.g., asking a question in the chat or generating a contextual quiz), the LuminaIQ `EndeeRetriever` queries the Endee local docker instance, immediately fetching the top `K` most relevant chunks to feed into the generative pipeline.

We chose Endee for its deterministic chunk handling, powerful filter-based search/deletion features, and lightweight containerized deployment which significantly accelerates the inner-loop development compared to heavier alternatives.

## 🚀 Setup and Execution Instructions

### Prerequisites
- Docker Desktop installed and running.
- Python 3.10+ installed.
- Node.js (v18+) installed.

### 1. Start the Endee Vector Database
Endee runs locally using Docker.
```bash
git clone https://github.com/endeeliq/endee.git  # Update if required to your local Endee manifest location
cd endee
docker compose up -d
```
*Endee will be available at `http://localhost:8080`.*

### 2. Backend Setup
1. Open a new terminal instance and navigate to the backend directory.
2. Provide your API keys in the environment file:
```bash
cd LuminaIQ_Latest/backend
cp .env.example .env
# Edit .env and ensure the following are set:
# ENDEE_URL=http://localhost:8080
# TOGETHER_API_KEY=your_together_api_key
```

3. Install requirements and start the server:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Setup
1. Open a final terminal instance for the React app.
```bash
cd LuminaIQ_Latest/frontend
npm install
npm run dev
```
2. Navigate to the local address provided by Vite (e.g., `http://localhost:5173`) to launch LuminaIQ and begin augmenting your study workflows!
