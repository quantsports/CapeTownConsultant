# Complete Project Structure

## 📁 Directory Tree

```
capetown-consultant/
│
├── src/                                    # Main source code
│   ├── __init__.py                        # Package root exports
│   │
│   ├── config/                            # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py                    # All config constants & env vars
│   │
│   ├── core/                              # Core utilities
│   │   ├── __init__.py
│   │   ├── logging.py                     # Structured logging (Loguru)
│   │   ├── models.py                      # Data models & enums
│   │   └── cache.py                       # LRU & persistent cache
│   │
│   ├── services/                          # External services
│   │   ├── __init__.py
│   │   ├── cost_tracker.py                # Cost tracking & budgeting
│   │   ├── embedding.py                   # OpenAI embeddings
│   │   │
│   │   └── search/                        # Search engines
│   │       ├── __init__.py
│   │       ├── base.py                    # Base search interface
│   │       ├── wikipedia.py               # Wikipedia search
│   │       ├── serpapi.py                 # SerpAPI search
│   │       ├── google.py                  # Google Custom Search
│   │       └── perplexity.py              # Perplexity AI search
│   │
│   ├── memory/                            # Memory systems
│   │   ├── __init__.py
│   │   ├── vector.py                      # Pinecone vector memory
│   │   ├── profile.py                     # User profiles (JSON)
│   │   └── unified.py                     # Combined memory interface
│   │
│   ├── tools/                             # Tool execution
│   │   ├── __init__.py
│   │   ├── schemas.py                     # Tool schemas & validation
│   │   └── executor.py                    # Tool execution engine
│   │
│   ├── agent/                             # Autonomous agent
│   │   ├── __init__.py
│   │   └── autonomous.py                  # Main agent logic
│   │
│   └── interface/                         # User interfaces
│       ├── __init__.py
│       ├── assistant.py                   # Main assistant wrapper
│       └── cli.py                         # Command-line interface
│
├── ui/                                    # Web interfaces
│   └── streamlit_app.py                   # Streamlit web UI
│
├── data/                                  # User data (auto-created)
│   ├── profiles/                          # User profile storage
│   └── conversations/                     # Conversation history
│
├── cache/                                 # Caching layer (auto-created)
│   ├── embeddings/                        # Persistent embedding cache
│   ├── costs/                             # Cost tracking data
│   └── logs/                              # Application logs
│
├── tests/                                 # Test suite (not implemented)
│   └── (test files go here)
│
├── main.py                                # CLI entry point
├── requirements.txt                       # Python dependencies
├── .env.example                           # Example environment config
├── .gitignore                             # Git ignore rules
│
├── README.md                              # User documentation
├── ARCHITECTURE.md                        # Architecture details
├── PROJECT_GUIDELINES.md                  # Development guidelines
└── PROJECT_STRUCTURE.md                   # This file
```

## 📄 File Descriptions

### Configuration Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/config/settings.py` | All configuration constants | `Config` class |
| `src/config/__init__.py` | Package exports | `Config` |

### Core Utilities

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/core/logging.py` | Structured logging setup | `logger`, `KvLogger` |
| `src/core/models.py` | Data models and enums | `ToolType`, `ToolResult`, `Message`, `CitationManager` |
| `src/core/cache.py` | Caching implementations | `LRUCache`, `PersistentEmbeddingCache` |
| `src/core/__init__.py` | Package exports | All core utilities |

### Services Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/services/cost_tracker.py` | Cost tracking system | `CostTracker` |
| `src/services/embedding.py` | Embedding generation | `EmbeddingService` |
| `src/services/search/base.py` | Base search interface | `BaseSearchEngine` |
| `src/services/search/wikipedia.py` | Wikipedia integration | `WikipediaSearch` |
| `src/services/search/serpapi.py` | SerpAPI integration | `SerpAPISearch` |
| `src/services/search/google.py` | Google Search integration | `GoogleSearch` |
| `src/services/search/perplexity.py` | Perplexity AI integration | `PerplexitySearch` |

### Memory Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/memory/vector.py` | Pinecone vector memory | `VectorMemory` |
| `src/memory/profile.py` | User profile management | `ProfileManager` |
| `src/memory/unified.py` | Unified memory interface | `UnifiedMemorySystem` |

### Tools Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/tools/schemas.py` | Tool schemas and definitions | `ToolSchemas` |
| `src/tools/executor.py` | Tool execution engine | `ToolExecutor` |

### Agent Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/agent/autonomous.py` | Main agent implementation | `AutonomousAgent` |

### Interface Layer

| File | Purpose | Key Exports |
|------|---------|-------------|
| `src/interface/assistant.py` | Main assistant wrapper | `AutonomousAssistant` |
| `src/interface/cli.py` | CLI implementation | `run_cli`, `main` |

### UI Layer

| File | Purpose | Tech Stack |
|------|---------|------------|
| `ui/streamlit_app.py` | Web interface | Streamlit |

### Root Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment template |
| `README.md` | User documentation |
| `ARCHITECTURE.md` | Technical architecture |
| `PROJECT_GUIDELINES.md` | Development standards |

## 🔧 Module Dependencies

### Dependency Graph

```
main.py
  └── src/interface/cli.py
        └── src/interface/assistant.py
              └── src/agent/autonomous.py
                    ├── src/tools/executor.py
                    │     ├── src/services/search/*
                    │     ├── src/services/embedding.py
                    │     ├── src/memory/vector.py
                    │     ├── src/memory/profile.py
                    │     └── src/memory/unified.py
                    ├── src/services/cost_tracker.py
                    └── src/tools/schemas.py

All modules depend on:
  ├── src/config/settings.py
  ├── src/core/logging.py
  ├── src/core/models.py
  └── src/core/cache.py
```

## 🚀 Quick Start Guide

### 1. Initial Setup

```bash
# Clone and enter directory
cd capetown-consultant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### 2. Run the Application

**CLI Mode**:
```bash
python main.py
```

**Web UI Mode**:
```bash
streamlit run ui/streamlit_app.py
```

**Programmatic Usage**:
```python
import asyncio
from src import AutonomousAssistant

async def main():
    async with AutonomousAssistant() as assistant:
        response = await assistant.chat("Hello!", "user_123")
        print(response)

asyncio.run(main())
```

### 3. Verify Configuration

In CLI, type:
```
config
```

This shows which API keys are configured.

## 📦 Dependencies

### Core Dependencies
- `openai` - OpenAI API client
- `pinecone-client` - Vector database
- `python-dotenv` - Environment management
- `loguru` - Logging
- `tenacity` - Retry logic
- `httpx` - Async HTTP client
- `aiofiles` - Async file operations
- `aiolimiter` - Rate limiting

### UI Dependencies
- `streamlit` - Web interface

### Development Dependencies
- `pytest` - Testing framework
- `black` - Code formatting
- `ruff` - Linting
- `mypy` - Type checking

## 🔑 Environment Variables

Required in `.env`:

```bash
# Required
OPENAI_API_KEY=sk-...

# Optional (features degrade gracefully if missing)
PINECONE_API_KEY=...
SERPAPI_API_KEY=...
GOOGLE_SEARCH_API_KEY=...
GOOGLE_SEARCH_ENGINE_ID=...
PERPLEXITY_API_KEY=...

# Settings
LOG_LEVEL=INFO
```

## 🎯 Key Features by Module

### Config Module
✅ Centralized settings  
✅ Environment variable management  
✅ Auto-directory creation  
✅ API key validation  

### Core Module
✅ Structured logging  
✅ Data models  
✅ LRU caching  
✅ Persistent caching  

### Services Module
✅ Cost tracking & budgeting  
✅ Embedding generation  
✅ Multi-provider search  
✅ Rate limiting  

### Memory Module
✅ Vector semantic search  
✅ User profiles  
✅ Unified interface  
✅ Auto-extraction  

### Tools Module
✅ Schema validation  
✅ Tool routing  
✅ Error handling  
✅ 8 built-in tools  

### Agent Module
✅ Conversation management  
✅ Tool orchestration  
✅ Context summarization  
✅ Auto-memory extraction  

### Interface Module
✅ CLI interface  
✅ Web UI (Streamlit)  
✅ Programmatic API  
✅ Session management  

## 📊 Lines of Code

| Module | Files | Approx. Lines |
|--------|-------|---------------|
| Config | 2 | 150 |
| Core | 4 | 400 |
| Services | 8 | 900 |
| Memory | 4 | 400 |
| Tools | 3 | 350 |
| Agent | 2 | 350 |
| Interface | 3 | 250 |
| UI | 1 | 400 |
| **Total** | **27** | **~3,200** |

## 🧪 Testing Strategy

### Unit Tests (Planned)
- `tests/test_config.py` - Configuration validation
- `tests/test_core.py` - Core utilities
- `tests/test_services.py` - Service integrations
- `tests/test_memory.py` - Memory systems
- `tests/test_tools.py` - Tool execution
- `tests/test_agent.py` - Agent logic

### Integration Tests (Planned)
- End-to-end chat flows
- Tool execution chains
- Cost tracking accuracy
- Memory persistence

## 🔄 Version History

- **v3.0.0** - Modular refactoring (current)
  - Separated concerns into modules
  - Enhanced error handling
  - Improved maintainability
  
- **v2.0.0** - Enhanced features
  - Cost tracking
  - Auto-memory extraction
  - Persistent cache
  
- **v1.0.0** - Initial release
  - Basic chat functionality
  - Tool integration
  - Memory system

## 📝 Development Workflow

### Adding a Feature

1. **Identify the layer** (services, memory, tools, etc.)
2. **Create/modify module** in appropriate directory
3. **Update schemas** if adding a tool
4. **Add to executor** if adding a tool
5. **Update docs** (README, ARCHITECTURE)
6. **Write tests** (when test suite exists)
7. **Test manually** via CLI or UI

### Code Style

- Use type hints
- Follow PEP 8
- Document with docstrings
- Keep functions small
- Use async/await consistently

### Commit Guidelines

```bash
feat: Add new search provider
fix: Correct cost calculation
docs: Update architecture diagram
refactor: Simplify tool execution
test: Add memory system tests
```

## 🆘 Troubleshooting

### Import Errors
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Missing Directories
Run once to create:
```python
from src.config import Config
Config.ensure_directories()
```

### API Key Issues
Check configuration:
```bash
python -c "from src.config import Config; print(Config.validate_required_keys())"
```

## 📚 Additional Resources

- **README.md** - User guide and quick start
- **ARCHITECTURE.md** - Detailed technical documentation
- **PROJECT_GUIDELINES.md** - Development standards
- **In-code docstrings** - Function-level documentation

---

**Project**: CapeTownConsultant  
**Version**: 3.0.0  
**Status**: Production Ready ✅  
**Lines**: ~3,200  
**Modules**: 27  
**Architecture**: Modular, Async, Production-Ready