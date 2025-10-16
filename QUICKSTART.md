# Quick Start Guide - Multi-Agent Orchestration

## 🚀 Installation

```bash
# Clone repository
cd capetown-consultant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your API keys (at minimum OPENAI_API_KEY)
```

## 💬 Basic Usage

### CLI Mode

```bash
# Start the CLI
python main.py

# Available commands:
# - exit      : Exit the application
# - clear     : Clear conversation history
# - config    : Show API configuration
# - costs     : Show usage costs
# - mode      : Toggle orchestration/traditional mode
# - workers   : List available specialists
```

### Python API

```python
import asyncio
from src import AutonomousAssistant

async def main():
    # Create assistant with orchestration enabled
    async with AutonomousAssistant(enable_orchestration=True) as assistant:
        
        # Ask a complex question
        response = await assistant.chat(
            "I want to open a new Italian restaurant. "
            "Help me design the menu, analyze costs, and create a marketing plan.",
            user_id="restaurant_owner"
        )
        print(response)
        
        # Check costs
        costs = await assistant.get_costs("restaurant_owner")
        print(f"\nToday's usage: ${costs['total']:.4f}")

asyncio.run(main())
```

## 🎭 Understanding Orchestration

### When It Activates

**Orchestration Mode** (uses multiple specialists):
```python
# Complex, multi-domain queries
"Design a summer menu with cost analysis and marketing strategy"
"Improve my kitchen operations and train my staff"
"Plan a restaurant opening with budget, menu, and staffing"
```

**Traditional Mode** (single agent):
```python
# Simple, single-domain queries
"What's a good substitute for basil?"
"How do I calculate food cost percentage?"
"What are restaurant health code requirements?"
```

### Manual Control

```python
async with AutonomousAssistant() as assistant:
    # Force orchestration mode
    assistant.toggle_orchestration(True)
    response1 = await assistant.chat("Complex query...")
    
    # Switch to traditional mode
    assistant.toggle_orchestration(False)
    response2 = await assistant.chat("Simple query...")
```

## 🧪 Try the Demos

### Pre-configured Demonstrations

```bash
# Run all demos
python demo_orchestration.py demo

# Compare traditional vs orchestration side-by-side
python demo_orchestration.py compare

# List available workers and their expertise
python demo_orchestration.py workers

# Interactive mode with manual toggle
python demo_orchestration.py interactive
```

### Demo 1: Complex Restaurant Planning

```python
query = """
I want to open a new Italian restaurant in downtown. 
Help me plan the menu, understand the costs, and create 
a marketing strategy.
"""
```

**Output**: 3 specialists (Menu Planner, Cost Analyst, Marketing Strategist) collaborate to provide:
- Menu recommendations with seasonal ingredients
- Cost analysis with pricing strategies
- Marketing plan with social media tactics

### Demo 2: Cost Optimization

```python
query = """
How can I reduce my food costs while maintaining quality? 
I'm currently at 35% food cost.
"""
```

**Output**: Cost Analyst + Operations Expert provide:
- Waste reduction strategies
- Supplier negotiation tips
- Menu engineering recommendations

## 👥 Available Specialists

| Specialist | Focus Areas | Priority |
|------------|-------------|----------|
| **Menu Planner** | Menu design, seasonality, pairings | 1 (High) |
| **Cost Analyst** | COGS, pricing, profit margins | 1 (High) |
| **Operations Expert** | Workflow, equipment, SOPs | 2 (Medium) |
| **Marketing Strategist** | Social media, branding, promotions | 2 (Medium) |
| **Customer Experience** | Service excellence, ambiance | 2 (Medium) |
| **Financial Advisor** | Business planning, funding | 1 (High) |
| **Supplier Specialist** | Procurement, vendor relations | 3 (Lower) |
| **Staff Manager** | HR, training, team culture | 2 (Medium) |
| **General Consultant** | Strategic advice, trends | 1 (High) |

## 🔧 Configuration

### Minimum Setup (Free/Low-Cost)

```env
# .env file
OPENAI_API_KEY=sk-...

# Optional (orchestration works without these)
# PINECONE_API_KEY=...
# SERPAPI_API_KEY=...
```

### Full Setup (All Features)

```env
# Required
OPENAI_API_KEY=sk-...

# Optional but recommended
PINECONE_API_KEY=...        # Vector memory
SERPAPI_API_KEY=...         # Web search
GOOGLE_SEARCH_API_KEY=...   # Alternative search
GOOGLE_SEARCH_ENGINE_ID=... # Google CSE ID
PERPLEXITY_API_KEY=...      # Complex analysis

# Settings (optional)
DAILY_BUDGET_LIMIT=5.0
MEMORY_SIMILARITY_THRESHOLD=0.65
AUTO_MEMORY_EXTRACTION=True
```

## 📊 Example Outputs

### Simple Query (Traditional Mode)

```
You: What's the food cost formula?

🤖 Assistant:

Food Cost Percentage = (Cost of Goods Sold / Total Food Sales) × 100

For example, if your COGS is $3,500 and sales are $10,000:
($3,500 / $10,000) × 100 = 35%

💰 Usage: $0.0042 / $5.00
```

### Complex Query (Orchestration Mode)

```
You: Design a summer menu and analyze costs

🤖 Assistant:

# 🎯 Strategic Consultation

Based on your summer menu requirements, here's a comprehensive 
strategy combining culinary design and financial analysis...

[Detailed synthesis from multiple specialists]

======================================================================

## 👥 Specialist Insights

### Menu Planner
*Confidence: 90%*

1. Focus on fresh, seasonal produce (tomatoes, zucchini, peaches)
2. Design 3-course structure: light appetizers, grilled mains, fruit-based desserts
3. Include 2-3 vegetarian options for dietary diversity
...

### Cost Analyst
*Confidence: 85%*

1. Target 28-32% food cost for summer menu items
2. Price salads at 3.5x ingredient cost
3. Leverage seasonal pricing for 15-20% savings
...

======================================================================

## 📚 Sources

[1] https://example.com/seasonal-ingredients
[2] https://example.com/menu-pricing-strategies

======================================================================

*Analysis by 2 specialist(s) • Orchestrated consultation • 2025-10-16*

💰 Usage: $0.0187 / $5.00
```

## 🎯 Common Use Cases

### 1. Menu Development
```python
"Create a fall menu for an upscale bistro with local ingredients"
```
**Specialists**: Menu Planner, Cost Analyst

### 2. Business Planning
```python
"I need a business plan for opening a café. Budget: $200k"
```
**Specialists**: Financial Advisor, Operations Expert, Cost Analyst

### 3. Marketing Campaign
```python
"Design a social media campaign for my restaurant reopening"
```
**Specialists**: Marketing Strategist, Customer Experience

### 4. Operations Improvement
```python
"How can I improve kitchen efficiency and reduce wait times?"
```
**Specialists**: Operations Expert, Staff Manager

### 5. Cost Reduction
```python
"Analyze my costs and recommend ways to improve profitability"
```
**Specialists**: Cost Analyst, Supplier Specialist, Operations Expert

## 🐛 Troubleshooting

### Issue: "OpenAI API not configured"
```bash
# Solution: Add API key to .env
echo "OPENAI_API_KEY=sk-..." >> .env
```

### Issue: Workers not activating
```python
# Check if query is complex enough
# Try forcing orchestration:
assistant.toggle_orchestration(True)
```

### Issue: Budget limit reached
```env
# Increase daily budget in .env
DAILY_BUDGET_LIMIT=10.0
```

### Issue: Slow response
```python
# Reduce number of workers
from src.workers.templates import WorkerType

await orchestrator.orchestrate(
    query="...",
    max_workers=2  # Instead of default 3
)
```

## 📚 Next Steps

1. **Read Full Documentation**: [ORCHESTRATION_README.md](ORCHESTRATION_README.md)
2. **Explore Examples**: Run `python demo_orchestration.py demo`
3. **Customize Workers**: See [ORCHESTRATION_README.md#customization](ORCHESTRATION_README.md)
4. **Join Development**: Check [PROJECT_GUIDELINES.md](PROJECT_GUIDELINES.md)

## 💡 Tips

- **Start Simple**: Test with traditional mode first
- **Build Profiles**: Use memory system for personalized responses
- **Monitor Costs**: Check usage regularly with `costs` command
- **Iterate**: Refine queries for better worker selection
- **Combine Tools**: Workers can use web search, memory, and more

## 🆘 Support

- **Logs**: Check `cache/logs/app.log` for debugging
- **Issues**: Review error messages in output
- **Documentation**: Full guides in `/docs` folder

---

**Ready to consult! Start with `python main.py` or `python demo_orchestration.py demo`** 🍽️🎭