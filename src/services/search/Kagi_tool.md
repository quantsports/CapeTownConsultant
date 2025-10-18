# Kagi FastGPT Integration Guide

## 🎯 Overview

Kagi FastGPT is now fully integrated into the CapeTown Consultant system. It provides AI-powered search with LLM synthesis backed by a real search engine - think ChatGPT but with live web search for accuracy.

### Key Features
- ✅ **LLM-Synthesized Answers**: Natural language responses powered by AI
- ✅ **Live Web Search**: Real-time search engine backing for accuracy
- ✅ **Structured References**: Detailed citations with titles, snippets, and URLs
- ✅ **Cost-Effective**: $0.015 per query (1.5¢)
- ✅ **Cached Responses**: Free for repeated queries
- ✅ **Full Integration**: Complete compatibility with existing tools

---

## 📦 Installation

### 1. Files Added/Updated

**New File:**
- `src/services/search/kagi_search.py` - Complete Kagi search implementation

**Updated Files:**
- `src/config/settings.py` - Added KAGI_API_KEY configuration
- `src/services/cost_tracker.py` - Added Kagi cost tracking ($0.015/query)
- `src/services/search/__init__.py` - Exported KagiSearch class
- `.env.example` - Added Kagi API key template

### 2. Get API Key

1. Create a Kagi account at [kagi.com/signup](https://kagi.com/signup?plan_id=trial)
2. Navigate to Settings → Advanced → API portal
   - Or go directly to: [kagi.com/settings?p=api](https://kagi.com/settings?p=api)
3. Click "Generate API Token"
4. Top up API credits at: [kagi.com/settings?p=billing_api](https://kagi.com/settings?p=billing_api)

### 3. Configure Environment

Add to your `.env` file:

```bash
# Kagi FastGPT API
KAGI_API_KEY=your_kagi_api_token_here
```

### 4. Verify Installation

```python
from src.config import Config

# Check if Kagi is configured
if Config.is_configured("kagi"):
    print("✅ Kagi FastGPT is configured!")
else:
    print("❌ Kagi API key not found")
```

---

## 🚀 Usage Examples

### Basic Usage

```python
import asyncio
from src.services.search.kagi_search import KagiSearch
from src.services.cost_tracker import CostTracker

async def basic_search():
    cost_tracker = CostTracker()
    
    async with KagiSearch(cost_tracker=cost_tracker) as kagi:
        result = await kagi.search(
            query="What are the latest developments in Python 3.13?",
            user_id="demo_user"
        )
        
        if result.success:
            data = result.data
            print("Answer:", data["answer"])
            print("\nReferences:")
            for ref in data["references"]:
                print(f"  - {ref['title']}")
                print(f"    {ref['url']}")
        else:
            print("Error:", result.error)

asyncio.run(basic_search())
```

### With Caching Control

```python
async def cached_search():
    async with KagiSearch() as kagi:
        # First call - hits API
        result1 = await kagi.search(
            query="Python 3.13 features",
            allow_cache=True
        )
        
        # Second call - returns cached (free!)
        result2 = await kagi.search(
            query="Python 3.13 features",
            allow_cache=True
        )
        
        print(f"Cost: ${result1.cost:.3f}")  # $0.015
        print(f"Tokens: {result1.data['tokens']}")
```

### Budget-Aware Usage

```python
async def budget_aware_search():
    cost_tracker = CostTracker()
    
    async with KagiSearch(cost_tracker=cost_tracker) as kagi:
        # Check budget before search
        user_id = "budget_user"
        
        has_budget = await cost_tracker.check_budget(
            user_id,
            "kagi-search",
            1
        )
        
        if has_budget:
            result = await kagi.search(
                query="AI developments 2025",
                user_id=user_id
            )
            print("Search completed:", result.success)
        else:
            print("Budget exceeded for today")
```

### Extracting Citations

```python
async def get_citations():
    async with KagiSearch() as kagi:
        result = await kagi.search("Quantum computing breakthroughs")
        
        if result.success:
            # Access citations directly
            citations = result.citations
            print(f"Found {len(citations)} sources")
            
            # Access detailed references
            references = result.data["references"]
            for i, ref in enumerate(references, 1):
                print(f"\n[{i}] {ref['title']}")
                print(f"    Snippet: {ref['snippet'][:100]}...")
                print(f"    URL: {ref['url']}")
```

---

## 🔧 Integration with Existing Tools

### Adding to ToolExecutor

If you have a custom tool executor, integrate Kagi:

```python
from src.services.search.kagi_search import KagiSearch
from src.tools.executor import ToolExecutor

class CustomToolExecutor(ToolExecutor):
    async def __aenter__(self):
        await super().__aenter__()
        
        # Initialize Kagi search
        self.kagi_search = KagiSearch(cost_tracker=self.cost_tracker)
        await self.kagi_search.__aenter__()
        
        return self
    
    async def execute_kagi_search(self, query: str, user_id: str):
        """Execute Kagi search"""
        return await self.kagi_search.search(query, user_id)
```

### Adding to Agent Tools

```python
# In your agent's tool definitions
def get_kagi_tool_definition():
    return {
        "type": "function",
        "function": {
            "name": "kagi_search",
            "description": "Search using Kagi FastGPT - AI-powered search with LLM synthesis. "
                          "Best for: complex questions requiring synthesis, current events, "
                          "technical deep-dives. Cost: $0.015 per query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query or question to answer"
                    },
                    "allow_cache": {
                        "type": "boolean",
                        "description": "Whether to allow cached responses (default: true)",
                        "default": True
                    }
                },
                "required": ["query"]
            }
        }
    }
```

---

## 💰 Cost Management

### Pricing
- **$0.015 per query** (1.5¢)
- **Cached responses are FREE**
- **Web search is always enabled** (currently required by API)

### Cost Tracking

Kagi costs are automatically tracked:

```python
from src.services.cost_tracker import CostTracker

async def check_costs():
    tracker = CostTracker()
    
    # Get user's daily costs
    costs = await tracker.get_user_costs("user_123")
    
    print(f"Total: ${costs['total']:.4f}")
    print(f"Limit: ${costs['limit']:.2f}")
    print(f"Remaining: ${costs['remaining']:.4f}")
```

### Budget Enforcement

The system automatically checks budget before Kagi searches:

```python
# Budget check is automatic in KagiSearch
result = await kagi.search(query, user_id)

if not result.success and "budget" in result.error.lower():
    print("Daily budget exceeded!")
```

---

## 🧪 Testing

### Unit Tests

```python
# tests/test_kagi_search.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.search.kagi_search import KagiSearch

@pytest.mark.asyncio
async def test_kagi_search_success():
    """Test successful Kagi search"""
    kagi = KagiSearch(api_key="test-key")
    
    async with kagi:
        # Mock HTTP client
        kagi.http_client = AsyncMock()
        kagi.http_client.post = AsyncMock(return_value=MagicMock(
            status_code=200,
            json=lambda: {
                "meta": {"id": "test-id", "node": "us-east", "ms": 1000},
                "data": {
                    "output": "Test answer",
                    "tokens": 100,
                    "references": [
                        {
                            "title": "Test Title",
                            "snippet": "Test snippet",
                            "url": "https://example.com"
                        }
                    ]
                }
            }
        ))
        
        result = await kagi.search("test query")
        
        assert result.success
        assert result.data["answer"] == "Test answer"
        assert len(result.citations) == 1
        assert result.cost == 0.015

@pytest.mark.asyncio
async def test_kagi_not_configured():
    """Test error when API key not configured"""
    kagi = KagiSearch(api_key=None)
    
    async with kagi:
        result = await kagi.search("test")
        
        assert not result.success
        assert "not configured" in result.error.lower()

@pytest.mark.asyncio
async def test_kagi_budget_exceeded():
    """Test budget enforcement"""
    from src.services.cost_tracker import CostTracker
    
    tracker = CostTracker()
    # Set very low budget
    tracker.user_costs["test_user"] = 4.99
    tracker.daily_limits["test_user"] = 5.0
    
    kagi = KagiSearch(api_key="test-key", cost_tracker=tracker)
    
    async with kagi:
        result = await kagi.search("test", user_id="test_user")
        
        assert not result.success
        assert "budget" in result.error.lower()
```

### Integration Tests

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_kagi_real_api():
    """Test with real Kagi API (requires KAGI_API_KEY)"""
    import os
    
    api_key = os.getenv("KAGI_API_KEY")
    if not api_key:
        pytest.skip("KAGI_API_KEY not set")
    
    async with KagiSearch(api_key=api_key) as kagi:
        result = await kagi.search("Python 3.13 features")
        
        assert result.success
        assert len(result.data["answer"]) > 0
        assert len(result.citations) > 0
        assert result.data["tokens"] > 0
```

Run tests:

```bash
# Unit tests only
pytest tests/test_kagi_search.py -v

# Include integration tests
pytest tests/test_kagi_search.py -v -m integration
```

---

## 🔍 Comparison with Other Search Tools

| Feature | Kagi | Perplexity | SerpAPI | Google |
|---------|------|------------|---------|--------|
| **AI Synthesis** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Live Search** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Cost per Query** | $0.015 | $0.001/1k tokens | $0.002 | $0.005 |
| **Response Type** | Answer + Refs | Answer + Refs | Search Results | Search Results |
| **Free Caching** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Best For** | Complex synthesis | Quick AI answers | Raw search data | Traditional search |

### When to Use Kagi

**✅ Use Kagi when:**
- Need comprehensive AI-synthesized answers
- Query requires understanding and synthesis
- Want high-quality references with context
- Caching can reduce costs for repeated queries
- Accuracy is critical (backed by live search)

**❌ Consider alternatives when:**
- Need just raw search results (use SerpAPI/Google)
- Budget is extremely tight (use Perplexity at $0.001)
- Query is very simple (use Wikipedia for free)

---

## 📊 Monitoring and Logging

### Log Events

Kagi search emits these structured log events:

```python
# Success
logger.info(
    "kagi_search_success",
    user_id=user_id,
    duration_ms=elapsed,
    tokens=tokens,
    references_count=len(references),
    cached=is_cached
)

# Budget exceeded
logger.warning("kagi_budget_exceeded", user_id=user_id)

# API error
logger.error(
    "kagi_http_error",
    user_id=user_id,
    status=status_code,
    error=error_msg
)

# Insufficient credits
logger.error(
    "kagi_insufficient_credits",
    user_id=user_id,
    error=error_msg
)
```

### Monitoring Queries

```bash
# Check Kagi usage in logs
grep "kagi_search" cache/logs/app.log

# Check for errors
grep "kagi.*error" cache/logs/errors.log

# Monitor costs
grep "kagi_search_success" cache/logs/app.log | wc -l
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "Kagi API key not configured"**

```bash
# Check .env file
cat .env | grep KAGI_API_KEY

# Verify in Python
python -c "from src.config import Config; print(Config.KAGI_API_KEY)"
```

**2. "Insufficient credit to perform this request"**

Top up your Kagi API credits:
1. Visit: https://kagi.com/settings?p=billing_api
2. Add credits to your account
3. Retry your search

**3. "Daily budget limit exceeded"**

```python
# Check current budget usage
from src.services.cost_tracker import CostTracker
tracker = CostTracker()
costs = await tracker.get_user_costs("your_user_id")
print(f"Used: ${costs['total']:.2f} / ${costs['limit']:.2f}")
```

**4. Rate limit errors**

The system has built-in rate limiting (30 requests/minute), but if you hit Kagi's limits:

```python
# Adjust rate limit if needed
kagi._rate_limiter = aiolimiter.AsyncLimiter(20, 60)  # 20/min
```

---

## 🔗 Resources

- **Kagi API Documentation**: https://help.kagi.com/kagi/api/fastgpt.html
- **Get API Key**: https://kagi.com/settings?p=api
- **API Credits**: https://kagi.com/settings?p=billing_api
- **Try FastGPT Web App**: https://kagi.com/fastgpt
- **Support**: support@kagi.com or [Discord](https://kagi.com/discord)

---

## ✅ Quick Start Checklist

- [ ] Get Kagi API key from [kagi.com/settings?p=api](https://kagi.com/settings?p=api)
- [ ] Top up API credits
- [ ] Add `KAGI_API_KEY` to `.env` file
- [ ] Copy new/updated files to your project
- [ ] Test with simple query
- [ ] Integrate into your tools/agents
- [ ] Monitor costs and usage
- [ ] Set appropriate budget limits

---

## 🎉 You're Ready!

Kagi FastGPT is now fully integrated and ready to use. Start with simple queries and gradually integrate it into your agents and workflows!

```python
# Quick test
import asyncio
from src.services.search.kagi_search import KagiSearch

async def test():
    async with KagiSearch() as kagi:
        result = await kagi.search("What's new in AI?")
        print(result.data["answer"])

asyncio.run(test())
```

Happy searching! 🚀