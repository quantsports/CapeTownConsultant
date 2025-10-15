# Architecture Documentation

## Overview

CapeTownConsultant is a modular, production-ready autonomous assistant built with clean architecture principles. The system is organized into distinct layers with clear separation of concerns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │     CLI      │  │  Streamlit   │  │   API (TBD)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  ASSISTANT INTERFACE                         │
│              (src/interface/assistant.py)                    │
│              - Session management                            │
│              - Cost tracking aggregation                     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   AUTONOMOUS AGENT                           │
│              (src/agent/autonomous.py)                       │
│              - Conversation management                       │
│              - Tool orchestration                            │
│              - Memory extraction                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    TOOL EXECUTOR                             │
│              (src/tools/executor.py)                         │
│              - Tool validation                               │
│              - Tool routing                                  │
│              - Result aggregation                            │
└─────┬────────────────────┬──────────────────┬───────────────┘
      │                    │                  │
┌─────▼─────┐      ┌───────▼───────┐   ┌────▼──────┐
│  SEARCH   │      │    MEMORY     │   │  SERVICES  │
│  ENGINES  │      │   SYSTEMS     │   │            │
└───────────┘      └───────────────┘   └────────────┘
```

## Module Structure

### 1. Configuration (`src/config/`)

**Purpose**: Centralized configuration and environment management

**Files**:
- `settings.py` - All configuration constants and environment variables
- `__init__.py` - Package exports

**Key Features**:
- Environment variable loading
- Directory creation
- API key validation
- Default value management

**Usage**:
```python
from src.config import Config

api_key = Config.OPENAI_API_KEY
threshold = Config.MEMORY_SIMILARITY_THRESHOLD
```

---

### 2. Core Utilities (`src/core/`)

**Purpose**: Fundamental utilities used across the application

**Files**:
- `logging.py` - Structured logging with Loguru
- `models.py` - Data models and enums
- `cache.py` - LRU and persistent caching
- `__init__.py` - Package exports

**Key Components**:

**Logging**:
- KV-style structured logging
- Console + file output
- Automatic rotation and retention

**Models**:
- `ToolType` - Enum of available tools
- `ToolResult` - Standardized tool response
- `Message` - Chat message with metadata
- `CitationManager` - Citation tracking and formatting

**Caching**:
- `LRUCache` - In-memory cache with eviction
- `PersistentEmbeddingCache` - Disk-backed embedding cache

---

### 3. Services (`src/services/`)

**Purpose**: External service integrations and business logic

**Structure**:
```
services/
├── cost_tracker.py      # Cost tracking and budgeting
├── embedding.py         # OpenAI embedding generation
└── search/              # Search engine implementations
    ├── base.py          # Base search interface
    ├── wikipedia.py     # Wikipedia search
    ├── serpapi.py       # SerpAPI search
    ├── google.py        # Google Custom Search
    └── perplexity.py    # Perplexity AI search
```

**Cost Tracker**:
- Per-user cost tracking
- Daily budget limits
- Cost estimation
- Persistent storage

**Embedding Service**:
- OpenAI embedding generation
- Batch processing
- Persistent caching
- Rate limiting

**Search Engines**:
- Unified interface via `BaseSearchEngine`
- Individual implementations for each provider
- Rate limiting per provider
- Cost tracking integration
- Graceful error handling

---

### 4. Memory Systems (`src/memory/`)

**Purpose**: Long-term memory and user profile management

**Files**:
- `vector.py` - Pinecone vector memory
- `profile.py` - User profile persistence
- `unified.py` - Combined memory interface
- `__init__.py` - Package exports

**Vector Memory**:
- Semantic search with Pinecone
- Configurable similarity threshold
- Namespace isolation per user
- Batch upsert operations

**Profile Manager**:
- JSON-based user profiles
- In-memory caching
- Async file operations
- Secure ID hashing

**Unified Memory**:
- Single interface for both systems
- Context aggregation
- Simplified API for agents

---

### 5. Tools (`src/tools/`)

**Purpose**: Tool execution and validation

**Files**:
- `schemas.py` - Tool definitions and validation schemas
- `executor.py` - Tool execution engine
- `__init__.py` - Package exports

**Tool Schemas**:
- JSON schemas for each tool
- OpenAI function definitions
- Parameter validation rules

**Tool Executor**:
- Schema-based validation
- Tool routing
- Error handling
- Result standardization

**Supported Tools**:
1. `web_search` - SerpAPI web search
2. `google_search` - Google Custom Search
3. `perplexity_search` - Perplexity AI
4. `wiki_fetch` - Wikipedia
5. `memory_query` - Search vector memory
6. `memory_upsert` - Store in vector memory
7. `profile_read` - Read user profile
8. `profile_write` - Update user profile

---

### 6. Agent (`src/agent/`)

**Purpose**: Autonomous agent logic

**Files**:
- `autonomous.py` - Main agent implementation
- `__init__.py` - Package exports

**Autonomous Agent**:
- OpenAI chat integration
- Function calling orchestration
- Conversation history management
- Automatic memory extraction
- Cost tracking integration
- Smart context summarization
- Citation aggregation

**Key Methods**:
- `chat()` - Main chat interface
- `_manage_conversation_history()` - Context management
- `_extract_memories()` - Auto-memory extraction
- `clear_history()` - Reset conversation

---

### 7. Interface (`src/interface/`)

**Purpose**: User-facing interfaces

**Files**:
- `assistant.py` - Main assistant wrapper
- `cli.py` - Command-line interface
- `__init__.py` - Package exports

**Assistant Interface**:
- Context manager for resource cleanup
- Simplified API for end users
- Cost aggregation
- Session management

**CLI**:
- Interactive command-line interface
- Commands: exit, clear, config, costs
- User-friendly output formatting
- Error handling

---

## Data Flow

### 1. Chat Request Flow

```
User Input
    ↓
CLI/UI Interface
    ↓
AutonomousAssistant
    ↓
AutonomousAgent
    ↓
OpenAI API (with function definitions)
    ↓
Tool Call(s) OR Final Answer
    ↓
ToolExecutor (if tool calls)
    ↓
Specific Tool Implementation
    ↓
External API / Storage
    ↓
ToolResult
    ↓
Back to OpenAI (continue loop)
    ↓
Final Answer with Citations
    ↓
User
```

### 2. Memory Flow

```
User Message
    ↓
Agent processes with tools
    ↓
_extract_memories() (automatic)
    ↓
OpenAI extracts facts
    ↓
memory_upsert tool
    ↓
EmbeddingService (batch)
    ↓
VectorMemory.upsert()
    ↓
Pinecone storage
```

### 3. Cost Tracking Flow

```
Tool/API Call
    ↓
CostTracker.check_budget()
    ↓
Execute if under budget
    ↓
CostTracker.record_cost()
    ↓
Update user's daily total
    ↓
Save to disk
```

## Design Patterns

### 1. Context Manager Pattern
- Used for resource management
- Ensures proper cleanup
- Async context managers throughout

### 2. Strategy Pattern
- Search engines implement base interface
- Swappable implementations
- Unified error handling

### 3. Repository Pattern
- ProfileManager for user data
- VectorMemory for embeddings
- Abstraction over storage

### 4. Adapter Pattern
- KvLogger wraps Loguru
- Provides structured logging interface

### 5. Factory Pattern
- ToolExecutor creates appropriate services
- Centralized instantiation

## Error Handling Strategy

### 1. Graceful Degradation
- Missing API keys disable features, not app
- Fallback to alternative services
- Clear error messages

### 2. Retry Logic
- Tenacity for transient failures
- Exponential backoff
- Configurable retry attempts

### 3. Rate Limiting
- AsyncLimiter for each service
- Prevents throttling
- Configurable limits

### 4. Result Standardization
- All tools return `ToolResult`
- Success/failure always clear
- Structured error messages

## Performance Optimizations

### 1. Caching
- Persistent embedding cache
- In-memory LRU cache
- Profile caching

### 2. Batch Operations
- Batch embedding generation
- Reduced API calls

### 3. Async I/O
- Non-blocking operations
- Concurrent tool execution possible
- Async file operations

### 4. Context Management
- Conversation summarization
- Token estimation
- History pruning

## Security Considerations

### 1. API Key Management
- Environment variables only
- Never in code
- .env not in version control

### 2. User Data
- Hashed user IDs for files
- Namespace isolation in Pinecone
- No PII in logs

### 3. Input Validation
- Schema validation for all tools
- Type checking
- Sanitization

## Testing Strategy

### Unit Tests
- Test individual functions
- Mock external services
- Cover edge cases

### Integration Tests
- Test service interactions
- Use test API keys
- Verify data flow

### End-to-End Tests
- Full chat scenarios
- Tool execution chains
- Cost tracking accuracy

## Deployment Considerations

### Environment Setup
1. Python 3.9+ required
2. Virtual environment recommended
3. API keys in .env file
4. Create data directories

### Scaling
- Stateless design enables horizontal scaling
- Per-user namespace isolation
- Rate limiters prevent abuse

### Monitoring
- Structured logging for analysis
- Cost tracking per user
- Error rate monitoring

## Future Extensions

### Potential Additions
1. **Additional Tools**
   - Email integration
   - Calendar management
   - File operations
   - Database queries

2. **Enhanced Memory**
   - Memory consolidation
   - Importance scoring
   - Automatic forgetting

3. **Multi-User**
   - User authentication
   - Shared memories
   - Team workspaces

4. **API Server**
   - FastAPI REST API
   - WebSocket support
   - API key management

5. **Advanced Features**
   - Plugin system
   - Custom tool registration
   - Workflow automation

## Maintenance

### Adding a New Tool

1. **Define enum** (`src/core/models.py`):
```python
class ToolType(str, Enum):
    NEW_TOOL = "new_tool"
```

2. **Add schema** (`src/tools/schemas.py`):
```python
SCHEMAS = {
    "new_tool": {
        "required": ["param"],
        "optional": {"opt_param": str}
    }
}
```

3. **Add function definition** (`src/tools/schemas.py`):
```python
{
    "type": "function",
    "function": {
        "name": "new_tool",
        "description": "...",
        "parameters": {...}
    }
}
```

4. **Implement service** (in appropriate module)

5. **Add to executor** (`src/tools/executor.py`):
```python
elif tool_name == ToolType.NEW_TOOL.value:
    return await self.new_service.execute(...)
```

### Updating Configuration

Edit `src/config/settings.py` and update:
- API endpoints
- Model versions
- Thresholds
- Limits

### Log Analysis

Logs are in `cache/logs/app.log`:
- JSON-parseable format
- Structured key-value pairs
- Rotation at 10MB
- 14-day retention

---

**Version**: 3.0.0  
**Last Updated**: 2024