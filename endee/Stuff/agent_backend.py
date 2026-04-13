"""
Agentic AI with Memory Retrieval using Endee + LangChain
Tri-domain: Task Automation, Personal Assistant, Research

Architecture:
  User Query -> Embed (Ollama) -> Search Endee -> Retrieve Memories
  -> LangChain Agent (with context) -> Tool Execution -> Store Memory -> Response
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import httpx
import os
import uuid
from datetime import datetime
import logging

# LangChain imports
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ===========================================================================
# Configuration — all values sourced from .env with sensible defaults
# ===========================================================================
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ENDEE_BASE_URL = os.getenv("ENDEE_BASE_URL", "http://localhost:8080")
EMBEDDING_MODEL = "nomic-embed-text"   # 768-dim, fast, reliable
LLM_MODEL = "glm-5"                   # Fallback: mistral, llama2, neural-chat

# ===========================================================================
# Pydantic Models
# ===========================================================================

class TaskInput(BaseModel):
    """Incoming query from the frontend."""
    query: str
    domain: str = "general"          # task | assistant | research
    context: Optional[str] = None

class MemoryEntry(BaseModel):
    """Single memory record to persist in Endee."""
    id: str
    domain: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str

class AgentResponse(BaseModel):
    """Response returned to the frontend after agent processing."""
    agent_response: str
    retrieved_memories: List[Dict]
    action_taken: str                # responded | responded_and_stored
    memory_id: Optional[str]

# ===========================================================================
# Ollama LLM + Embedding Initialization
# ===========================================================================

try:
    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=LLM_MODEL,
        temperature=0.7,
        keep_alive="5m",
    )
    embeddings = OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model=EMBEDDING_MODEL,
    )
    logger.info(f"✓ Ollama connected — LLM: {LLM_MODEL} | Embeddings: {EMBEDDING_MODEL}")
except Exception as e:
    logger.error(f"✗ Ollama connection failed: {e}")
    raise

# ===========================================================================
# Endee Vector Database Client
#
# Why Endee?
#   - Native semantic similarity search (cosine distance)
#   - Payload-based metadata filtering (domain, timestamp, etc.)
#   - Lightweight, self-hosted — no external API keys needed
#   - Fast upsert/search for real-time agent memory
# ===========================================================================

class EndeeClient:
    """Async wrapper around the Endee REST API for memory operations."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.index_name = "agent_memory"
        self.client: httpx.AsyncClient = None  # Initialized in lifespan

    async def _ensure_client(self):
        """Lazy-init the httpx client if not already created."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=30)

    async def close(self):
        """Gracefully close the httpx client on shutdown."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    async def create_index(self):
        """
        Create the 'agent_memory' index on startup.

        Vector size = 768 to match nomic-embed-text output dimensions.
        Distance metric = cosine for semantic similarity ranking.
        Idempotent: 409 (conflict) means the index already exists — safe to ignore.
        """
        await self._ensure_client()
        try:
            payload = {
                "index_name": self.index_name,
                "vector_size": 768,      # nomic-embed-text output dimensions
                "distance": "cosine",    # Best for semantic similarity
            }
            resp = await self.client.post(f"{self.base_url}/indexes", json=payload)
            if resp.status_code in [200, 201, 409]:
                logger.info(f"✓ Endee index ready: {self.index_name}")
            else:
                logger.warning(f"⚠ Index creation status: {resp.status_code} — {resp.text}")
        except Exception as e:
            logger.error(f"✗ Endee index creation failed: {e}")

    async def store_memory(self, memory_entry: MemoryEntry, vector: List[float]) -> Optional[str]:
        """
        Upsert a memory record with its embedding vector into Endee.

        The payload stores the full content, domain tag, and metadata
        so we can filter and display results on the frontend.
        """
        await self._ensure_client()
        try:
            payload = {
                "index_name": self.index_name,
                "id": memory_entry.id,
                "vector": vector,
                "payload": {
                    "domain": memory_entry.domain,
                    "content": memory_entry.content,
                    "metadata": memory_entry.metadata,
                    "timestamp": memory_entry.timestamp,
                },
            }
            resp = await self.client.post(f"{self.base_url}/upsert", json=payload)
            if resp.status_code in [200, 201]:
                logger.info(f"✓ Memory stored: {memory_entry.id[:8]}... [{memory_entry.domain}]")
                return memory_entry.id
            else:
                logger.error(f"✗ Store failed ({resp.status_code}): {resp.text}")
                return None
        except Exception as e:
            logger.error(f"✗ Endee store_memory error: {e}")
            return None

    async def retrieve_memories(
        self, query: str, domain: Optional[str] = None, top_k: int = 5
    ) -> List[Dict]:
        """
        Semantic similarity search against the Endee index.

        Flow:
          1. Embed the query text using Ollama (nomic-embed-text)
          2. Send the query vector to Endee /search
          3. Optionally filter by domain
          4. Return top-K most similar memories with payloads
        """
        await self._ensure_client()
        try:
            # Step 1: Generate query embedding via Ollama (run in thread pool to avoid blocking)
            query_vector = await asyncio.to_thread(embeddings.embed_query, query)

            # Step 2: Build Endee search request
            search_payload = {
                "index_name": self.index_name,
                "query_vector": query_vector,
                "limit": top_k,
                "with_payload": True,
            }

            # Step 3: Apply domain filter if specified
            if domain and domain != "general":
                search_payload["filter"] = {"domain": domain}

            # Step 4: Execute search
            resp = await self.client.post(f"{self.base_url}/search", json=search_payload)

            if resp.status_code == 200:
                results = resp.json().get("results", [])
                logger.info(
                    f"✓ Retrieved {len(results)} memories for: '{query[:50]}...'"
                )
                return results
            else:
                logger.warning(f"⚠ Endee search status: {resp.status_code}")
                return []
        except Exception as e:
            logger.error(f"✗ Endee retrieve_memories error: {e}")
            return []

# Initialize the Endee client singleton
endee = EndeeClient(ENDEE_BASE_URL)

# ===========================================================================
# LangChain Tools — Actions the Agent Can Take
#
# The agent decides *autonomously* whether to invoke these tools
# based on the user's query and retrieved memory context.
# ===========================================================================

@tool
def store_task(task_description: str, status: str = "pending", priority: str = "medium") -> str:
    """Store a task in long-term memory.

    Args:
        task_description: What needs to be done
        status: One of 'pending', 'in_progress', 'completed'
        priority: One of 'low', 'medium', 'high'

    Returns:
        Confirmation with generated memory ID
    """
    memory_id = str(uuid.uuid4())
    return f"Task scheduled for storage: {memory_id} | {task_description} [{priority}/{status}]"

@tool
def store_note(note_content: str, category: str = "general") -> str:
    """Store a personal note or preference in long-term memory.

    Args:
        note_content: The note or preference to remember
        category: One of 'general', 'schedule', 'preference', 'insight'

    Returns:
        Confirmation with generated memory ID
    """
    memory_id = str(uuid.uuid4())
    return f"Note scheduled for storage: {memory_id} | [{category}] {note_content}"

@tool
def store_research_finding(
    finding: str, source: Optional[str] = None, relevance: str = "medium"
) -> str:
    """Store a research finding or insight in long-term memory.

    Args:
        finding: The research insight or discovery
        source: Where this finding came from (optional)
        relevance: One of 'low', 'medium', 'high'

    Returns:
        Confirmation with generated memory ID
    """
    memory_id = str(uuid.uuid4())
    source_info = f" (source: {source})" if source else ""
    return f"Finding scheduled for storage: {memory_id} | [{relevance}] {finding}{source_info}"

tools = [store_task, store_note, store_research_finding]

# ===========================================================================
# LangChain Agent Configuration
# ===========================================================================

system_prompt = """You are a multi-domain AI agent with long-term memory powered by Endee vector database.

Your domains:
1. **Task Automation**: Manage tasks (create, track, complete). Recall similar past tasks.
2. **Personal Assistant**: Store notes, preferences, schedules. Recall personal context.
3. **Research Assistant**: Store findings, insights, sources. Recall research patterns.

When responding:
- First, consider what memories might be relevant (the system will retrieve them).
- Use retrieved memories to provide context-aware, personalized responses.
- Decide if you should store new information (use the appropriate tool).
- Be concise but informative.
- Acknowledge relevant past memories in your response.

Available tools: store_task, store_note, store_research_finding

IMPORTANT: Only use a tool when the user is clearly providing new information to store.
If the user is asking a question, respond directly using retrieved memories as context."""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=5,
    handle_parsing_errors=True,   # Gracefully handle malformed tool calls
)

# ===========================================================================
# FastAPI Application with Lifespan
# ===========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    # Startup: initialize Endee index and verify connectivity
    await endee.create_index()
    logger.info("✓ Agent system initialized — ready for queries")
    yield
    # Shutdown: gracefully close httpx client
    await endee.close()
    logger.info("✓ Shutdown complete — httpx client closed")


app = FastAPI(
    title="Agentic Memory System",
    description="Tri-domain AI agent with long-term memory via Endee vector DB",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend proxy and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# FastAPI Endpoints
# ===========================================================================

@app.get("/health")
async def health():
    """Health check endpoint — returns service connection status."""
    return {
        "status": "ok",
        "ollama": OLLAMA_BASE_URL,
        "endee": ENDEE_BASE_URL,
        "model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "timestamp": datetime.now().isoformat(),
    }

@app.post("/query", response_model=AgentResponse)
async def process_query(task_input: TaskInput):
    """
    Main agent endpoint — the core agentic loop:

      1. Retrieve relevant memories from Endee (semantic search)
      2. Build context-enriched prompt for the LangChain agent
      3. Agent reasons and optionally invokes tools
      4. If a tool was used, embed and store the new memory in Endee
      5. Return response, retrieved memories, and action metadata
    """
    try:
        logger.info(f"📨 Query received: '{task_input.query[:100]}' [{task_input.domain}]")

        # ── Step 1: Retrieve relevant memories from Endee ──
        retrieved_memories = await endee.retrieve_memories(
            query=task_input.query,
            domain=task_input.domain,
            top_k=5,
        )

        # ── Step 2: Build memory context for the agent ──
        memory_context = ""
        if retrieved_memories:
            memory_context = "\n\nRelevant past memories:\n"
            for i, mem in enumerate(retrieved_memories, 1):
                payload = mem.get("payload", {})
                memory_context += f"{i}. {payload.get('content', 'N/A')}\n"

        # ── Step 3: Run the LangChain agent with context ──
        agent_input = {
            "input": f"{task_input.query}\n{memory_context}",
            "chat_history": [],
        }
        # Run sync agent executor in thread pool to avoid blocking the event loop
        result = await asyncio.to_thread(agent_executor.invoke, agent_input)
        agent_response = result.get("output", "No response generated")

        # ── Step 4: Determine if a tool was used → store memory ──
        memory_id = None
        action_taken = "responded"

        # Check if the agent invoked any store_* tools
        intermediate_steps = result.get("intermediate_steps", [])
        if any("store_" in str(step) for step in intermediate_steps):
            action_taken = "responded_and_stored"
            memory_id = str(uuid.uuid4())

            # Create and persist the memory entry
            memory_entry = MemoryEntry(
                id=memory_id,
                domain=task_input.domain,
                content=f"Query: {task_input.query}\nResponse: {agent_response}",
                metadata={
                    "query": task_input.query,
                    "domain": task_input.domain,
                    "retrieved_count": len(retrieved_memories),
                    "timestamp": datetime.now().isoformat(),
                },
                timestamp=datetime.now().isoformat(),
            )

            # Embed the response and upsert into Endee (run in thread pool)
            response_vector = await asyncio.to_thread(embeddings.embed_query, agent_response)
            await endee.store_memory(memory_entry, response_vector)

        logger.info(f"✓ Query processed — action: {action_taken}")

        return AgentResponse(
            agent_response=agent_response,
            retrieved_memories=retrieved_memories,
            action_taken=action_taken,
            memory_id=memory_id,
        )

    except Exception as e:
        logger.error(f"✗ Query processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories")
async def list_memories(domain: Optional[str] = None, limit: int = 10):
    """
    List stored memories — performs a broad semantic search
    to surface recent/relevant memories from the specified domain.
    """
    try:
        memories = await endee.retrieve_memories(
            query="all memories",
            domain=domain,
            top_k=limit,
        )
        return {"memories": memories, "count": len(memories)}
    except Exception as e:
        logger.error(f"✗ List memories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """
    Delete a specific memory from Endee.

    Note: Delete support depends on Endee version.
    This endpoint is provided for forward compatibility.
    """
    try:
        await endee._ensure_client()
        resp = await endee.client.delete(
            f"{endee.base_url}/points/{endee.index_name}/{memory_id}"
        )
        if resp.status_code in [200, 204]:
            return {"deleted": memory_id, "status": "success"}
        return {"deleted": memory_id, "status": f"endee_status_{resp.status_code}"}
    except Exception as e:
        logger.warning(f"Delete not supported or failed: {e}")
        return {"deleted": memory_id, "status": "pending_endee_delete_support"}

# ===========================================================================
# Entry Point
# ===========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)