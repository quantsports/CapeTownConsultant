### CapeTownConsultant — DOCS.md

#### Overview
CapeTownConsultant is an asynchronous, production-ready autonomous assistant offering research, web search, memory, user profiles, and cost tracking. It exposes:
- A CLI entry point in `main.py` (`async def main()`)
- A Streamlit UI in `streamlit_app.py`

Core services are modular and degrade gracefully when API keys are missing. Cost tracking, rate limiting, retries, caching, and citations are built-in.

---

### Objectives
- Provide an autonomous assistant that can plan, call tools, and synthesize answers.
- Minimize cost with budgeting, low-cost-first tool selection, and caching.
- Persist useful user information across sessions (profiles, vector memory).
- Surface citations for transparency when using external sources.
- Offer both a simple CLI and a rich Streamlit front-end.

---

### Capabilities
- Chat with tool-use via OpenAI function calling (`gpt-4o`, `gpt-4o-mini` for summaries).
- Web research:
  - `web_search` via SerpAPI
  - `google_search` via Google Custom Search
  - `perplexity_search` for complex synthesis
  - `wiki_fetch` via async Wikipedia API
- Memory:
  - Vector memory in Pinecone (optional) using OpenAI embeddings
  - Auto memory extraction from conversation (configurable)
  - User profiles persisted to disk
- Cost tracking with daily budgets, per-operation estimates, and usage reporting.
- Rate limiting for external providers and robust retries with exponential backoff.
- Persistent disk cache for embeddings to reduce repeated costs and latency.
- Citations included in final responses.

---

### Architecture and Primary Components

- `Config` (central configuration)
  - Loads from environment (e.g., `OPENAI_API_KEY`, `PINECONE_API_KEY`, `SERPAPI_API_KEY`, `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID`, `PERPLEXITY_API_KEY`).
  - Models: `EMBEDDING_MODEL="text-embedding-3-small"`, `CHAT_MODEL="gpt-4o"`, `SUMMARY_MODEL="gpt-4o-mini"`.
  - Rate limits: `OPENAI_RPM`, `SERPAPI_RPM`, `PERPLEXITY_RPM`.
  - Cost/budget: `ENABLE_COST_TRACKING`, `DAILY_BUDGET_LIMIT`.
  - Memory threshold: `MEMORY_SIMILARITY_THRESHOLD`.
  - Paths: `PROFILE_DIR`, `CONVERSATION_DIR`, `CACHE_DIR`, `EMBEDDING_CACHE_DIR`.

- `CostTracker`
  - Estimates, checks, and records per-user costs to `./cache/costs/<hash>_<date>.json`.
  - Supports operations like `gpt-4o-input`, `gpt-4o-output`, `embedding`, `serpapi`, `google-search`, `perplexity`.
  - Enforces daily budgets; returns `{total, limit, remaining}`.

- `CitationManager`
  - Collects unique URLs, assigns reference numbers, and formats a Sources section.

- `PersistentEmbeddingCache` + `LRUCache`
  - Disk-backed and in-memory embedding caches keyed by content hash to avoid repeated costs.

- `EmbeddingService`
  - Async OpenAI embeddings with caching, rate limiting, retries, and cost recording.

- `SearchEngine` (async context manager)
  - Shared `httpx.AsyncClient` and `AsyncWikipediaSearch`.
  - Tools:
    - `serpapi_search` (low cost, default web search)
    - `google_search` (fallback/alternative)
    - `perplexity_search` (high cost, complex synthesis)
    - `wiki_fetch` (free, encyclopedic)
  - Provider-specific rate limiters and cost recording.

- `VectorMemory`
  - Optional Pinecone index creation and use (`assistant-memory`, cosine metric).
  - `query(text, namespace, top_k, filter)` returns matches above `MEMORY_SIMILARITY_THRESHOLD`.
  - `upsert(items, namespace)` batches embed + upsert with metadata and timestamps.

- `ProfileManager`
  - Disk-based per-user JSON profile with read/write and in-memory cache.

- `UnifiedMemorySystem`
  - Combines `ProfileManager` and `VectorMemory` to assemble context for the agent.

- `ToolExecutor` (async context manager)
  - Validates tool calls against schemas.
  - Wires tool names to concrete implementations (`SearchEngine`, `VectorMemory`, `ProfileManager`).
  - Always returns `ToolResult` with `success`, `data`, `error`, `citations`, `source`, `cost`.

- `AutonomousAgent` (async context manager)
  - Manages conversation, chooses tools via OpenAI function calling, aggregates citations, enforces iteration caps, summarizes when needed, extracts memories, and appends usage data.

- `AutonomousAssistant`
  - Thin wrapper around `AutonomousAgent` for a simple interface used by CLI and Streamlit.

---

### Execution Flow

#### CLI (`main.py`)
1. `async def main()` prints a header and supported commands: `exit`, `clear`, `config`, `costs`.
2. Creates an `AutonomousAssistant` and enters its async context.
3. Loop:
   - Read user input.
   - Handle commands:
     - `exit`: show final cost and exit
     - `clear`: clear conversation history
     - `costs`: show today’s usage
     - `config`: show provider key availability
   - Otherwise, call `assistant.chat(user_input, user_id)` and print the response.

#### Streamlit (`streamlit_app.py`)
- Page setup, CSS, and session-state initialization.
- Attempts to instantiate a persistent `AutonomousAssistant` within the app session; falls back to ephemeral per-request assistant if needed.
- Sidebar shows:
  - Cost tracking badge, progress, and breakdown (auto-refresh optional)
  - API key availability
  - Feature flags and thresholds
  - User ID input (affects profiles, memory, and costs)
  - Session controls: clear chat, reset session
  - Session stats and About section
- Main area:
  - Displays message history
  - `st.chat_input` → on submit: append user message, call `assistant.chat`, display assistant reply, append to history, optionally rerun to refresh costs.
- Gracefully notifies if `OPENAI_API_KEY` is missing and halts interaction.

---

### Core Runtime Behavior of `AutonomousAgent`
- Conversation state: in-memory list of messages (`system`, `user`, `assistant`, `tool`).
- Tooling contract sent to OpenAI via `_get_function_definitions()` with guidance on when and how to use tools, including cost hints:
  - `web_search` (low cost, default)
  - `google_search` (medium cost)
  - `perplexity_search` (high cost; complex synthesis only)
  - `wiki_fetch` (free; try first for encyclopedic facts)
  - `memory_query`/`memory_upsert` and `profile_read`/`profile_write`
- Each tool call is validated and executed by `ToolExecutor`. Results are appended as `tool` messages and citations collected.
- Manages iteration to avoid infinite loops and summarizes long histories using `SUMMARY_MODEL` as needed.
- After finalizing an answer, appends formatted citations and, if enabled, cost summary for the day.
- Auto memory extraction: scans recent messages for personal facts/preferences and stores them via `memory_upsert` (configurable with `AUTO_MEMORY_EXTRACTION`).

---

### Primary Functions and Classes (Cheat Sheet)
- `Config`: central constants and environment wiring.
- `CostTracker`: `check_budget()`, `record_cost()`, `get_user_costs()`.
- `EmbeddingService`: `embed()`, `embed_batch()` with disk cache.
- `SearchEngine`: `serpapi_search()`, `google_search()`, `perplexity_search()`, `wiki_fetch()`.
- `VectorMemory`: `query()`, `upsert()`; uses `EmbeddingService` and Pinecone.
- `ProfileManager`: `read()`, `write()`.
- `UnifiedMemorySystem`: `get_context()` collects profile + vector matches.
- `ToolExecutor`: `validate_tool_call()`, `execute()`; owns `SearchEngine`, `VectorMemory`, `ProfileManager`.
- `AutonomousAgent`: `_get_function_definitions()`, `_summarize_conversation()`, `_manage_conversation_history()`, `_extract_memories()`, `chat()`.
- `AutonomousAssistant`: `chat()`, `get_costs()`, `clear_history()`.
- CLI entry: `async def main()`.

---

### Cost Tracking
- Per-operation cost table used to estimate and record usage.
- Budget gate before expensive operations (`check_budget`); raises or returns errors that the UI handles gracefully.
- Storage per-user per-day under `./cache/costs` with MD5-hashed user ID.
- Streamlit UI displays costs and progress; CLI has `costs` and end-of-session usage summary.

---

### Rate Limiting and Reliability
- `aiolimiter.AsyncLimiter` per provider (OpenAI, SerpAPI, Perplexity).
- `tenacity.retry` with exponential backoff wraps external calls.
- `httpx.AsyncClient` with HTTP/2 and tuned connection limits for search operations.

---

### Citations
- Tool methods populate `citations` with URLs.
- `AutonomousAgent` aggregates and formats sources at the end of the reply, e.g.,
  - Sources listed as `[1]`, `[2]` with full URLs under a separator.

---

### Data Persistence and Paths
- Profiles: `./data/profiles/<hash>.json` via `ProfileManager`.
- Conversations: directory reserved in `Config.CONVERSATION_DIR` (history is kept in memory during runtime; summarization reduces token usage).
- Embedding cache: `./cache/embeddings/<hash>.json`.
- Cost files: `./cache/costs/<hash>_<date>.json`.

---

### Environment Variables
Set in `.env` or environment:
- `OPENAI_API_KEY` — required for chat and embeddings.
- `PINECONE_API_KEY` — optional; enables vector memory.
- `SERPAPI_API_KEY` — optional; enables `web_search`.
- `GOOGLE_SEARCH_API_KEY`, `GOOGLE_SEARCH_ENGINE_ID` — optional; enables `google_search`.
- `PERPLEXITY_API_KEY` — optional; enables `perplexity_search`.
- Optional tuning: `LOG_LEVEL`, rate limit overrides.

Behavior on missing keys: related tools degrade gracefully and return structured errors without crashing import or runtime.

---

### Running the Project

#### CLI
```
python -m main
# or
python main.py
```
Commands during a session: `exit`, `clear`, `config`, `costs`.

#### Streamlit App
```
streamlit run streamlit_app.py
```
Notes:
- The UI requires `OPENAI_API_KEY` to proceed.
- Costs auto-refresh after each query if enabled.
- Change `User ID` in the sidebar to separate profiles/memory/costs.

---

### Tool Schemas and Validation
`ToolExecutor.TOOL_SCHEMAS` defines required/optional parameters for each tool. Calls are validated before execution to ensure correctness and clear error messages. Example schema entries:
- `web_search`: required `query`, optional `num`
- `memory_upsert`: required `items` (array of `{text, meta?}`)
- `profile_write`: required `data` (object)

---

### Error Handling
- Tool methods never raise unhandled exceptions; they return `ToolResult(success=False, error=...)`.
- Agent catches and logs errors, returning user-friendly messages.
- Streamlit displays actionable tips for budget and configuration issues; CLI shows structured status.

---

### Security and Privacy Considerations
- User identifiers are hashed for file names.
- Only minimal profile fields are stored, as provided or extracted.
- External calls only made when necessary and budget allows.

---

### Limitations
- Pinecone-dependent vector memory; without `PINECONE_API_KEY`, memory tools return structured errors and the assistant continues functioning.
- Embedding model and chat model are currently OpenAI; swapping providers requires corresponding changes.
- Cost estimates are approximations; actual provider billing may vary slightly.

---

### Extending the System (Adding a Tool)
Follow the repository’s guidelines:
1. Add tool name to `ToolType`.
2. Implement/extend the concrete method (e.g., in `SearchEngine`).
3. Add schema in `ToolExecutor.TOOL_SCHEMAS` and a branch in `ToolExecutor.execute`.
4. Add function definition JSON in `AutonomousAgent._get_function_definitions()`.
5. Apply rate limiting and retries; populate `citations` where relevant.
6. Return `ToolResult` with clear `error` messages on misconfigurations.

---

### Quick Examples

#### Programmatic usage
```python
import asyncio
from main import AutonomousAssistant

async def run():
    async with AutonomousAssistant() as assistant:
        print(await assistant.chat("What happened in Cape Town last week?", user_id="demo"))
        costs = await assistant.get_costs("demo")
        print(costs)

asyncio.run(run())
```

#### Memory upsert via tool (conceptual inside agent)
```json
{
  "tool": "memory_upsert",
  "arguments": {
    "items": [
      {"text": "User prefers hiking in Table Mountain", "meta": {"type": "preference"}}
    ]
  }
}
```

---

### Requirements
See `requirements.txt`. Core libraries include `openai`, `httpx`, `tenacity`, `aiolimiter`, `streamlit`, `pinecone`, `tiktoken`, `loguru`, `numpy`, `pandas`, `chromadb` (optional), and testing/tools such as `pytest`, `ruff`, `black`.

---

### File Map
- `main.py` — Core backend: configuration, services, tools, agent, and CLI.
- `streamlit_app.py` — Streamlit UI: session state, sidebar controls, chat interface.
- `requirements.txt` — Python dependencies.

---

### Notes
- Logging via `loguru` to console and `./cache/logs/app.log`.
- All external operations respect `Config.MAX_RETRIES` and `Config.TIMEOUT_SECONDS`.
- Conversations are pruned/summarized to respect `Config.MAX_CONVERSATION_HISTORY`.
