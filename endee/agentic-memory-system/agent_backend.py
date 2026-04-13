"""
Agentic AI with Memory Retrieval using Endee + LangChain
Tri-domain: Task Automation, Personal Assistant, Research

Architecture:
  User Query -> Embed (Ollama) -> Search Endee -> Retrieve Memories
  -> LangChain Agent (with context) -> Tool Execution -> Store Memory -> Response

SDK versions:
  - langchain >= 1.0  (uses create_agent + StateGraph)
  - langchain-ollama  (ChatOllama + OllamaEmbeddings)
  - endee             (official Endee Python SDK)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import os
import uuid
import json
from datetime import datetime
import logging
import dateparser

# --- Active Reminders Scheduler Setup ---
REMINDERS_FILE = "reminders.json"
ACTIVE_NOTIFICATIONS = []

def load_reminders() -> List[Dict]:
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_reminders(reminders: List[Dict]):
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

async def reminder_scheduler():
    """Background task to poll JSON for elapsed reminders."""
    while True:
        try:
            reminders = load_reminders()
            now = datetime.now()
            pending = []
            triggered_any = False
            
            for r in reminders:
                if r.get("trigger_time"):
                    try:
                        dt = datetime.fromisoformat(r["trigger_time"])
                        # Strip tz if it exists so we can compare with naive local datetime.now()
                        if dt.tzinfo:
                            dt = dt.replace(tzinfo=None)
                        if now >= dt:
                            ACTIVE_NOTIFICATIONS.append(r)
                            logging.getLogger(__name__).info(f"⏰ Reminder Triggered: {r['text']}")
                            triggered_any = True
                        else:
                            pending.append(r)
                    except ValueError:
                        pending.append(r)
                else:
                    pending.append(r)
                    
            if triggered_any:
                save_reminders(pending)
        except Exception as e:
            logging.getLogger(__name__).error(f"Scheduler error: {e}")
        await asyncio.sleep(5)

# LangChain imports — compatible with langchain >= 1.0
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.agents import create_agent         # new StateGraph-based API
from langchain_community.tools import DuckDuckGoSearchRun

web_search_tool = DuckDuckGoSearchRun()

# Official Endee Python SDK
from endee import Endee

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ===========================================================================
# Configuration
# ===========================================================================
OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL",  "http://localhost:11434")
ENDEE_BASE_URL   = os.getenv("ENDEE_BASE_URL",   "http://localhost:8080")
ENDEE_AUTH_TOKEN = os.getenv("ENDEE_AUTH_TOKEN", "")
EMBEDDING_MODEL  = os.getenv("EMBEDDING_MODEL",  "nomic-embed-text")   # 768-dim
LLM_MODEL        = os.getenv("LLM_MODEL",        "nemotron-cascade-2")

INDEX_NAME = "agent_memory"
VECTOR_DIM = 768       # nomic-embed-text output
TOP_K      = 5

# ===========================================================================
# Pydantic Models
# ===========================================================================

class TaskInput(BaseModel):
    query:   str
    context: Optional[str] = None

class MemoryEntry(BaseModel):
    id:        str
    domain:    str
    content:   str
    metadata:  Dict[str, Any]
    timestamp: str

class AgentResponse(BaseModel):
    agent_response:     str
    retrieved_memories: List[Dict]
    action_taken:       str
    memory_id:          Optional[str]

# ===========================================================================
# Ollama LLM + Embeddings
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
# Endee Vector Database Client (Official SDK)
#
# Uses `pip install endee` — the official first-party Python client.
# API docs: https://docs.endee.io/quick-start
#
# Design choices:
#   - cosine distance: best for sentence embeddings (unit-norm vectors)
#   - filter field: scopes retrieval to task/assistant/research domain
#   - meta field: stores arbitrary payload shown in the UI
# ===========================================================================

class EndeeMemoryClient:
    """
    Clean wrapper around the official Endee Python SDK.

    Lifecycle:
      create_index()  → called on startup (idempotent)
      store_memory()  → called after agent uses a store_* tool
      retrieve()      → called before every agent invocation
    """

    def __init__(self):
        self._client = Endee(ENDEE_AUTH_TOKEN) if ENDEE_AUTH_TOKEN else Endee()
        self._client.set_base_url(f"{ENDEE_BASE_URL}/api/v1")
        self._index = None
        logger.info(f"✓ Endee SDK initialised → {ENDEE_BASE_URL}/api/v1")

    def create_index(self):
        """
        Create 'agent_memory' index (idempotent — safe to call on every startup).
        768-dim cosine matches nomic-embed-text output perfectly.
        """
        try:
            self._client.create_index(
                name=INDEX_NAME,
                dimension=VECTOR_DIM,
                space_type="cosine",
            )
            logger.info(f"✓ Endee index created: '{INDEX_NAME}' dim={VECTOR_DIM} cosine")
        except Exception as e:
            logger.warning(f"⚠ Index note (may already exist): {e}")

        # Now get the index handle — wrapped in its own try/except
        try:
            self._index = self._client.get_index(name=INDEX_NAME)
            logger.info(f"✓ Endee index handle acquired: '{INDEX_NAME}'")
        except Exception as e:
            logger.error(f"✗ Could not get index handle: {e}")
            self._index = None

    def store_memory(self, entry: MemoryEntry, vector: List[float]) -> Optional[str]:
        """
        Upsert a memory into Endee.

        filter  → used by Endee's pre-filter engine for domain scoping
        meta    → arbitrary payload returned with results (shown in UI)
        """
        if self._index is None:
            logger.error("✗ Index not ready — cannot store memory")
            return None
        try:
            self._index.upsert([{
                "id":     entry.id,
                "vector": vector,
                "filter": {"domain": entry.domain},
                "meta":   {
                    "domain":    entry.domain,
                    "content":   entry.content,
                    "query":     entry.metadata.get("query", ""),
                    "timestamp": entry.timestamp,
                },
            }])
            logger.info(f"✓ Stored: {entry.id[:8]}… [{entry.domain}]")
            return entry.id
        except Exception as e:
            logger.error(f"✗ store_memory error: {e}")
            return None

    def retrieve(
        self,
        query_vector: List[float],
        domain: Optional[str] = None,
        top_k: int = TOP_K,
    ) -> List[Dict]:
        """
        Semantic similarity search.

        Optionally applies a MongoDB-style filter to scope results
        to a specific domain:  [{"domain": {"$eq": "task"}}]
        """
        if self._index is None:
            return []
        try:
            kwargs: Dict[str, Any] = {
                "vector":          query_vector,
                "top_k":           top_k,
                "include_vectors": False,
            }
            if domain and domain != "general":
                kwargs["filter"] = [{"domain": {"$eq": domain}}]

            raw = self._index.query(**kwargs)
            results = [
                {
                    "id":         item.get("id", ""),
                    "similarity": item.get("similarity", 0.0),
                    "payload":    item.get("meta", {}),
                }
                for item in raw
            ]
            logger.info(f"✓ Retrieved {len(results)} memories (domain={domain or 'all'})")
            return results
        except Exception as e:
            logger.error(f"✗ retrieve error: {e}")
            return []


endee_client = EndeeMemoryClient()

# ===========================================================================
# LangChain Tools — Genuinely Capable Tri-Domain Agent
# ===========================================================================

# ---- TASK AUTOMATION TOOLS ----

@tool
def create_task(
    task_description: str,
    due_date: str = "",
    priority: str = "medium",
    assignee: str = "",
) -> str:
    """Create and store a new task with optional due date, priority, and assignee.

    Use this when the user asks you to schedule, plan, remind, create, 
    add, or track a task, to-do item, deadline, or action item.

    Args:
        task_description: Clear description of what needs to be done.
        due_date: When it's due (e.g. 'tomorrow', '2026-04-15', 'next Monday'). Leave blank if not specified.
        priority: 'low', 'medium', 'high', or 'urgent'.
        assignee: Who is responsible. Leave blank if not specified.
    """
    parts = [f"📋 TASK CREATED: {task_description}"]
    parts.append(f"  Priority: {priority.upper()}")
    if due_date:
        parts.append(f"  Due: {due_date}")
    if assignee:
        parts.append(f"  Assigned to: {assignee}")
    parts.append(f"  Status: PENDING")
    parts.append(f"  Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(parts)


@tool
def update_task_status(
    task_description: str,
    new_status: str = "completed",
) -> str:
    """Update the status of a previously created task.

    Use this when the user says they finished, completed, started, or 
    want to cancel/pause a task.

    Args:
        task_description: Description of the task to update (matches against memory).
        new_status: 'pending', 'in_progress', 'completed', 'cancelled', or 'paused'.
    """
    return f"✅ TASK STATUS UPDATE: '{task_description}' → {new_status.upper()} at {datetime.now().strftime('%Y-%m-%d %H:%M')}"


@tool
def create_reminder(
    reminder_text: str,
    when: str = "",
) -> str:
    """Create a reminder for the user. Stored in long-term memory so the agent
    can surface it in future conversations.

    Use this when the user says "remind me", "don't let me forget", etc.

    Args:
        reminder_text: What to be reminded about.
        when: When the reminder should trigger (e.g. 'tomorrow morning', 'before the meeting').
    """
    trigger_time_iso = None
    if when:
        parsed_dt = dateparser.parse(when, settings={'PREFER_DATES_FROM': 'future'})
        if parsed_dt:
            # Strip timezone for easy naive local comparisons
            trigger_time_iso = parsed_dt.replace(tzinfo=None).isoformat()
            
    if trigger_time_iso:
        reminders = load_reminders()
        reminders.append({
            "id": str(uuid.uuid4()),
            "text": reminder_text,
            "trigger_time": trigger_time_iso,
            "created": datetime.now().isoformat()
        })
        save_reminders(reminders)
        
    time_str = f" (Trigger: {when})" if when else ""
    return f"🔔 REMINDER SET{time_str}: {reminder_text} — Created {datetime.now().strftime('%Y-%m-%d %H:%M')}"


# ---- PERSONAL ASSISTANT TOOLS ----

@tool
def store_preference(
    preference_key: str,
    preference_value: str,
) -> str:
    """Store a user preference or personal fact in long-term memory.

    Use this when the user shares something personal about themselves: 
    favorite things, habits, dietary restrictions, preferred styles, etc.

    Args:
        preference_key: Category of the preference (e.g. 'favorite_color', 'diet', 'music_taste', 'work_hours').
        preference_value: The actual preference value.
    """
    return f"💡 PREFERENCE STORED: {preference_key} = {preference_value}"


@tool
def store_note(
    note_content: str,
    category: str = "general",
) -> str:
    """Store a general note, thought, journal entry, or piece of information.

    Use this for anything the user wants to remember that isn't a task 
    or a research finding — personal notes, ideas, observations, logs, 
    meeting notes, diary entries, etc.

    Args:
        note_content: The note or information to remember.
        category: 'general', 'idea', 'meeting', 'journal', 'schedule', or 'contact'.
    """
    return f"📝 NOTE STORED [{category.upper()}]: {note_content} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"


@tool
def store_contact(
    name: str,
    details: str,
) -> str:
    """Store contact information or details about a person.

    Use when the user mentions someone by name and provides details 
    (phone, email, role, relationship, birthday, etc.).

    Args:
        name: The person's name.
        details: Details about this person (role, email, phone, relationship, etc.).
    """
    return f"👤 CONTACT STORED: {name} — {details}"


# ---- RESEARCH ASSISTANT TOOLS ----

@tool
def store_research_finding(
    title: str,
    finding: str,
    source: str = "",
    topic: str = "",
    relevance: str = "medium",
) -> str:
    """Store a research finding, fact, data point, or insight.

    Use this when the user shares or discusses factual information, 
    statistics, research results, technical knowledge, or discoveries 
    that should be preserved for future reference.

    Args:
        title: Short title summarising the finding.
        finding: Detailed description of the finding or insight.
        source: Where this came from (paper, URL, person, experiment). Leave blank if unknown.
        topic: The research topic or field this belongs to.
        relevance: 'low', 'medium', 'high', or 'critical'.
    """
    parts = [f"🔬 RESEARCH FINDING: {title}"]
    parts.append(f"  Detail: {finding}")
    if source:
        parts.append(f"  Source: {source}")
    if topic:
        parts.append(f"  Topic: {topic}")
    parts.append(f"  Relevance: {relevance.upper()}")
    parts.append(f"  Recorded: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(parts)


@tool
def store_summary(
    title: str,
    summary: str,
    source: str = "",
) -> str:
    """Store a summary of an article, paper, video, book, or conversation.

    Use when the user asks you to summarise something and wants to 
    keep the summary for later.

    Args:
        title: Title of the thing being summarised.
        summary: The summary text.
        source: URL, book name, or other source identifier.
    """
    src_str = f" (from: {source})" if source else ""
    return f"📄 SUMMARY STORED{src_str}: {title}\n{summary}\n— {datetime.now().strftime('%Y-%m-%d %H:%M')}"


@tool
def search_internet(query: str) -> str:
    """Search the internet for real-time information, news, fact-checking, or current events.
    
    Use this STRICTLY when the user asks you to 'search the web', 'look up', 'news', or retrieve information you don't know.

    Args:
        query: Specific search query to look up on DuckDuckGo.
    """
    try:
        results = web_search_tool.invoke(query)
        return f"🌐 INTERNET SEARCH RESULTS for '{query}':\n{results}"
    except Exception as e:
        return f"🌐 INTERNET SEARCH FAILED: {str(e)}"

TOOLS = [
    # Task Automation
    create_task, update_task_status, create_reminder,
    # Personal Assistant
    store_preference, store_note, store_contact,
    # Research Assistant
    store_research_finding, store_summary, search_internet,
]

# Map tool names → domain for memory storage routing
TOOL_DOMAIN_MAP = {
    "create_task":             "task",
    "update_task_status":      "task",
    "create_reminder":         "task",
    "store_preference":        "assistant",
    "store_note":              "assistant",
    "store_contact":           "assistant",
    "store_research_finding":  "research",
    "store_summary":           "research",
    "search_internet":         "research",
}

# ===========================================================================
# LangChain Agent (new StateGraph-based API — langchain >= 1.0)
# ===========================================================================

SYSTEM_PROMPT = """You are **Endee OS**, a helpful, highly intelligent AI assistant with persistent long-term memory powered by Endee DB.

# CORE IDENTITY & CAPABILITIES
You can chat generally, answer questions, and perform specific actions using TOOLS. You must sound natural, helpful, and concise.

# TOOL USAGE STRICT RULES - CRITICAL!
1. **GREETINGS & GENERAL CHAT**: NEVER use ANY tools if the user says "hi", "chat normally", "hello", "what's up", or asks general questions. Just respond warmly using plain text!
2. **ONLY USE TOOLS WHEN EXPLICITLY REQUESTED**: Do not call `create_task`, `create_reminder`, or any storage tool unless the user specifically asks you to "schedule", "remind", "store", or "remember" something.
3. **DO NOT INVENT TASKS**: If the user does not explicitly request a new task, DO NOT create one.
4. **INTERNET SEARCH**: Use the `search_internet` tool ONLY if the user asks you to search the web, get the latest news, or find current information.

# MEMORY RETRIEVAL (CONTEXT)
You will receive "Relevant past memories" at the end of the user's message. 
Do NOT assume these memories mean the user wants to take action on them right now. They are just background context from the past. Only reference them if absolutely relevant to the CURRENT user statement.
"""

# create_agent returns a CompiledStateGraph — invoke with message list
agent_graph = create_agent(
    model=llm,
    tools=TOOLS,
    system_prompt=SYSTEM_PROMPT,
)

def run_agent(query: str, memory_context: str) -> tuple[str, str]:
    """
    Run the LangChain agent synchronously.
    Returns (response_text, tool_name_or_None).
    """
    user_message = f"{query}\n\n{memory_context}" if memory_context else query
    inputs = {"messages": [{"role": "user", "content": user_message}]}
    result = agent_graph.invoke(inputs)

    # The new API returns a dict with 'messages' list
    messages = result.get("messages", [])
    # Last message is the final AI response
    final_msg = messages[-1] if messages else None
    response_text = (
        final_msg.content if final_msg and hasattr(final_msg, "content")
        else "No response generated."
    )

    # Detect which tool(s) were called
    from langchain_core.messages import ToolMessage
    tool_name = None
    for m in messages:
        if isinstance(m, ToolMessage):
            tool_name = getattr(m, "name", None)

    return response_text, tool_name

# ===========================================================================
# FastAPI Application
# ===========================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await asyncio.to_thread(endee_client.create_index)
    except Exception as e:
        logger.error(f"⚠ Endee startup issue (will retry on first query): {e}")
        
    asyncio.create_task(reminder_scheduler())
    logger.info("✓ Agentic Memory System ready + Chron Scheduler active")
    yield
    logger.info("✓ Shutdown complete")


app = FastAPI(
    title="Agentic Memory System",
    description="Tri-domain AI agent with long-term memory via Endee vector DB",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================================================
# Endpoints
# ===========================================================================

@app.get("/health")
async def health():
    return {
        "status":          "ok",
        "ollama":          OLLAMA_BASE_URL,
        "endee":           ENDEE_BASE_URL,
        "model":           LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "index":           INDEX_NAME,
        "endee_connected": endee_client._index is not None,
        "timestamp":       datetime.now().isoformat(),
    }


@app.get("/notifications/poll")
async def poll_notifications():
    global ACTIVE_NOTIFICATIONS
    if not ACTIVE_NOTIFICATIONS:
        return {"notifications": []}
        
    to_send = ACTIVE_NOTIFICATIONS[:]
    ACTIVE_NOTIFICATIONS.clear()
    return {"notifications": to_send}


@app.post("/query", response_model=AgentResponse)
async def process_query(task_input: TaskInput):
    """
    Agentic loop:
      1. Embed query (Ollama)
      2. Retrieve top-K memories from Endee (global search)
      3. Build context string → run LangChain agent
      4. If agent used a store_* tool → embed response → upsert into Endee
      5. Return response + memories + action metadata
    """
    try:
        logger.info(f"📨 Query: '{task_input.query[:100]}'")

        # Lazy-reconnect to Endee if the index handle was lost
        if endee_client._index is None:
            try:
                await asyncio.to_thread(endee_client.create_index)
            except Exception:
                logger.warning("⚠ Endee still unavailable — continuing without memory")

        # Step 1: Embed
        query_vector: List[float] = await asyncio.to_thread(
            embeddings.embed_query, task_input.query
        )

        # Step 2: Retrieve from Endee (Global search)
        retrieved = await asyncio.to_thread(
            endee_client.retrieve,
            query_vector,
            None,
            TOP_K,
        )

        # Step 3: Build memory context
        ctx = ""
        if retrieved:
            ctx = "\n\nRelevant past memories:\n"
            for i, mem in enumerate(retrieved, 1):
                p = mem.get("payload", {})
                ctx += f"{i}. [{p.get('domain','N/A')}] {p.get('content','N/A')}\n"

        # Step 4: Run agent
        response_text, tool_name = await asyncio.to_thread(
            run_agent, task_input.query, ctx
        )

        # Step 5: Store if tool was called
        memory_id   = None
        action_taken = "responded"

        if tool_name:
            action_taken = "responded_and_stored"
            memory_id    = str(uuid.uuid4())

            # Route domain based on which tool the LLM invoked
            domain = TOOL_DOMAIN_MAP.get(tool_name, "general")

            entry = MemoryEntry(
                id        = memory_id,
                domain    = domain,
                content   = f"Query: {task_input.query}\nResponse: {response_text}",
                metadata  = {
                    "query":           task_input.query,
                    "domain":          domain,
                    "tool_used":       tool_name,
                    "retrieved_count": len(retrieved),
                    "timestamp":       datetime.now().isoformat(),
                },
                timestamp = datetime.now().isoformat(),
            )
            resp_vector: List[float] = await asyncio.to_thread(
                embeddings.embed_query, response_text
            )
            await asyncio.to_thread(endee_client.store_memory, entry, resp_vector)

        logger.info(f"✓ Done — action: {action_taken}")
        return AgentResponse(
            agent_response     = response_text,
            retrieved_memories = retrieved,
            action_taken       = action_taken,
            memory_id          = memory_id,
        )

    except Exception as e:
        logger.error(f"✗ Query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories")
async def list_memories(domain: Optional[str] = None, limit: int = 10):
    try:
        v: List[float] = await asyncio.to_thread(
            embeddings.embed_query, "memory recall list"
        )
        memories = await asyncio.to_thread(endee_client.retrieve, v, domain, limit)
        return {"memories": memories, "count": len(memories)}
    except Exception as e:
        logger.error(f"✗ List memories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
