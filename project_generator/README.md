# Multi-Agent Research System

A sophisticated multi-agent orchestration system that dynamically spawns specialized knowledge workers to conduct comprehensive research tasks.

## Features

- **Multi-Agent Orchestration**: Dynamically spawns 1-5 specialized workers based on query complexity
- **13 Specialized Workers**: Research Analyst, Scientific Researcher, Technical Analyst, Literature Reviewer, and more
- **Concurrent Execution**: Workers run in parallel for 2-5x faster responses
- **Intelligent Synthesis**: LLM-powered result aggregation and conflict resolution
- **Evidence-Based**: Source tracking, credibility scoring, and citation management
- **Cost Tracking**: Built-in API cost monitoring and budget limits
- **Dual Mode**: Supports both orchestration and traditional single-agent modes

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key (required)
- Pinecone API key (optional, for vector memory)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/research-system.git
cd research-system
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.template .env
# Edit .env and add your API keys
```

5. Run the system:
```bash
python -m src.interface.cli
```

## Usage

### Command Line Interface
```bash
# Start interactive CLI
python -m src.interface.cli

# Example queries
> What are the latest breakthroughs in quantum computing?
> Compare machine learning frameworks for production use
> Analyze recent trends in renewable energy adoption
```

### Python API
```python
import asyncio
from src.interface.assistant import AutonomousAssistant

async def main():
    async with AutonomousAssistant(
        api_key="your_openai_key",
        enable_orchestration=True
    ) as assistant:
        
        response = await assistant.chat(
            "What are the latest developments in AI?",
            user_id="researcher_1"
        )
        
        print(response)

asyncio.run(main())
```

## Architecture