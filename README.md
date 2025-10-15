# CapeTownConsultant - Autonomous Personal Assistant v3.0

A production-ready, modular autonomous assistant with web search, vector memory, cost tracking, and persistent storage.

## 🌟 Features

### Core Capabilities
- **🔍 Multi-Source Search**: Wikipedia, SerpAPI, Google Custom Search, Perplexity AI
- **🧠 Vector Memory**: Pinecone-based semantic memory with auto-extraction
- **👤 User Profiles**: Persistent user preferences and metadata
- **💰 Cost Tracking**: Budget limits and usage monitoring per user
- **💾 Persistent Cache**: Disk-backed embedding cache for efficiency
- **📊 Structured Logging**: Comprehensive logging with Loguru
- **⚡ Async Architecture**: High-performance async/await implementation

### Recent Enhancements (v3.0)
- ✅ Configurable similarity thresholds for memory retrieval
- ✅ Cost tracking with daily budget limits
- ✅ Async Wikipedia search
- ✅ Smart conversation summarization
- ✅ Rate limiting per API provider
- ✅ Enhanced tool validation
- ✅ Persistent embedding cache
- ✅ Modular, maintainable architecture

## 📁 Project Structure

```
capetown-consultant/
├── src/
│   ├── config/          # Configuration management
│   ├── core/            # Core utilities (logging, models, cache)
│   ├── services/        # External services (embedding, search, cost tracking)
│   ├── memory/          # Memory systems (vector, profile, unified)
│   ├── tools/           # Tool execution and schemas
│   ├── agent/           # Autonomous agent logic
│   └── interface/       # User interfaces (CLI, assistant)
├── ui/
│   └── streamlit_app.py # Web UI
├── data/                # User data storage
├── cache/               # Caching layer
├── main.py              # CLI entry point
├── requirements.txt     # Dependencies
└── .env                 # API keys (not in repo)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- API keys (at minimum: OpenAI)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd capetown-consultant
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API keys**
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Run the assistant**
```bash
python main.py
```

## 🔑 API Keys

The assistant requires at minimum an OpenAI API key. Other services are optional and enhance functionality:

### Required
- `OPENAI_API_KEY` - For chat and embeddings

### Optional
- `PINECONE_API_KEY` - For vector memory (without it, memory features disabled)
- `SERPAPI_API_KEY` - For web search (recommended)
- `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID` - Alternative web search
- `PERPLEXITY_API_KEY` - For complex analysis queries

Add these to your `.env` file:
```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=...
SERPAPI_API_KEY=...
GOOGLE_SEARCH_API_KEY=...
GOOGLE_SEARCH_ENGINE_ID=...
PERPLEXITY_API_KEY=...
```

## 💻 Usage

### CLI Commands

Start the assistant:
```bash
python main.py
```

Available commands:
- `exit` - Exit the assistant
- `clear` - Clear conversation history
- `config` - Show API configuration status
- `costs` - Show current usage and budget

### Web UI (Streamlit)

```bash
streamlit run ui/streamlit_app.py
```

Features:
- 💬 Interactive chat interface
- 💰 Real-time cost tracking
- 📊 Session statistics
- ⚙️ Configuration overview
- 👤 User management

### Programmatic Usage

```python
import asyncio
from src import AutonomousAssistant

async def main():
    async with AutonomousAssistant() as assistant:
        response = await assistant.chat(
            "What's the weather like today?",
            user_id="my_user"
        )
        print(response)
        
        # Check costs
        costs = await assistant.get_costs("my_user")
        print(f"Today's usage: ${costs['total']:.4f}")

asyncio.run(main())
```

## 🛠️ Configuration

Edit `src/config/settings.py` to customize:

```python
# Memory Settings
MEMORY_SIMILARITY_THRESHOLD = 0.65  # Adjust similarity matching
AUTO_MEMORY_EXTRACTION = True       # Auto-extract user facts

# Cost Tracking
ENABLE_COST_TRACKING = True
DAILY_BUDGET_LIMIT = 5.0            # USD per day

# Rate Limiting
OPENAI_RPM = 50                     # Requests per minute
SERPAPI_RPM = 100
PERPLEXITY_RPM = 20

# Conversation Management
MAX_CONVERSATION_HISTORY = 20       # Messages to retain
```

## 🧪 Development

### Adding New Tools

1. **Define in `ToolType` enum** (`src/core/models.py`)
2. **Add validation schema** (`src/tools/schemas.py`)
3. **Implement service** (in appropriate `src/services/` module)
4. **Add to executor** (`src/tools/executor.py`)
5. **Add function definition** (`src/tools/schemas.py`)

### Project Guidelines

See `PROJECT_GUIDELINES.md` for detailed development standards.

Key principles:
- Graceful degradation for missing API keys
- Return `ToolResult` for all tool operations
- Use rate limiters for external APIs
- Maintain backward compatibility
- Never hard-fail at import time

## 📊 Cost Management

The assistant tracks costs per user with configurable daily limits:

| Operation | Cost |
|-----------|------|
| GPT-4o Input | $2.50 / 1M tokens |
| GPT-4o Output | $10.00 / 1M tokens |
| Embeddings | $0.02 / 1M tokens |
| SerpAPI | $0.002 / search |
| Google Search | $0.005 / search |
| Perplexity | $0.001 / request |
| Wikipedia | Free ✨ |

**Cost Optimization Strategy**:
1. Try Wikipedia first (free)
2. Use web_search for most queries (cheap)
3. Reserve Perplexity for complex analysis (expensive)

## 🔧 Troubleshooting

### Import Errors
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Missing API Keys
- Check `.env` file exists and is properly formatted
- Run `config` command in CLI to verify status
- The app will work with just OpenAI key (other features disabled)

### Rate Limits
- Adjust RPM settings in `Config`
- Monitor logs for rate limit errors
- Consider upgrading API plans

### Memory Issues
- Clear embedding cache: `rm -rf cache/embeddings/*`
- Reduce `CACHE_MAX_SIZE` in config
- Check disk space for cache directory

## 📝 License

[Add your license here]

## 🤝 Contributing

Contributions welcome! Please:
1. Follow existing code structure
2. Add tests for new features
3. Update documentation
4. Follow the guidelines in `PROJECT_GUIDELINES.md`

## 📧 Support

[Add support information]

## 🙏 Acknowledgments

Built with:
- OpenAI GPT-4o
- Pinecone Vector Database
- SerpAPI, Google Search, Perplexity AI
- Loguru, Tenacity, httpx, and more

---

**Version**: 3.0.0  
**Status**: Production Ready ✅