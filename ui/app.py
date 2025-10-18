"""
CapeTownConsultant - Advanced Showcase UI
Production-ready Streamlit application showcasing all system capabilities
Version: 4.0 - Full Feature Showcase
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import streamlit as st
from contextlib import asynccontextmanager
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import core modules
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.services.cost_tracker import CostTracker
from src.workers.templates import WorkerType, WorkerTemplates

# ============================================================================
# Page Configuration
# ============================================================================

st.set_page_config(
    page_title="CapeTownConsultant – Advanced AI Research Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Custom Styling
# ============================================================================

st.markdown(
    """
<style>
    /* Main container */
    .main {
        padding: 2rem 1rem;
    }

    /* Headers */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        border-bottom: 3px solid #3b82f6;
        padding-bottom: 0.5rem;
    }

    h2, h3 {
        color: #1e40af;
        font-weight: 600;
    }

    /* Feature cards */
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .feature-title {
        font-size: 1.25rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .feature-description {
        font-size: 0.95rem;
        opacity: 0.9;
    }

    /* Worker badges */
    .worker-badge {
        display: inline-block;
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        margin: 0.25rem;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    /* Tool indicators */
    .tool-indicator {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        padding: 0.35rem 0.75rem;
        border-radius: 0.5rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
    }

    /* Progress container */
    .progress-container {
        background: #f0f9ff;
        border-left: 4px solid #3b82f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-family: 'Monaco', 'Courier New', monospace;
    }

    /* Status indicators */
    .status-success {
        color: #10b981;
        font-weight: 600;
    }

    .status-error {
        color: #ef4444;
        font-weight: 600;
    }

    .status-warning {
        color: #f59e0b;
        font-weight: 600;
    }

    /* Metrics cards */
    .metrics-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #cbd5e1;
        margin: 0.75rem 0;
    }

    /* Chat messages */
    .user-message {
        background: #f1f5f9;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }

    .assistant-message {
        background: #f0fdf4;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }

    /* Streaming animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .streaming {
        animation: pulse 2s ease-in-out infinite;
    }

    /* Memory items */
    .memory-item {
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0.5rem;
    }

    /* Info panels */
    .info-panel {
        background: #ecfdf5;
        border: 1px solid #10b981;
        padding: 1.25rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    /* Citation */
    .citation {
        font-size: 0.85rem;
        color: #64748b;
        font-style: italic;
        margin-top: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# Async Helper Functions
# ============================================================================


def run_async(coro, timeout: Optional[float] = 120.0):
    """
    Safely run async code in Streamlit
    Handles event loop conflicts and timeouts
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new event loop for nested async
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(asyncio.wait_for(coro, timeout=timeout))
        else:
            return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
    except asyncio.TimeoutError:
        st.error(f"⏱️ Operation timed out after {timeout} seconds")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


# ============================================================================
# Session State Initialization
# ============================================================================


def init_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "assistant" not in st.session_state:
        st.session_state.assistant = None

    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    if "orchestration_enabled" not in st.session_state:
        st.session_state.orchestration_enabled = True

    if "worker_history" not in st.session_state:
        st.session_state.worker_history = []

    if "tool_usage" not in st.session_state:
        st.session_state.tool_usage = {}

    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0

    if "cost_data" not in st.session_state:
        st.session_state.cost_data = {"total_cost": 0.0, "queries_by_type": {}}


# ============================================================================
# Assistant Management
# ============================================================================


@asynccontextmanager
async def get_assistant():
    """Context manager for assistant lifecycle"""
    assistant = None
    try:
        assistant = AutonomousAssistant(
            enable_orchestration=st.session_state.orchestration_enabled
        )
        await assistant.__aenter__()
        yield assistant
    finally:
        if assistant:
            try:
                await assistant.__aexit__(None, None, None)
            except:
                pass


# ============================================================================
# UI Components
# ============================================================================


def render_header():
    """Render application header"""
    st.markdown(
        """
    # 🧠 CapeTownConsultant - Advanced AI Research Assistant

    ### 🚀 Multi-Agent Orchestration System with Specialized Knowledge Workers
    """
    )

    st.markdown("---")


def render_feature_showcase():
    """Render feature showcase panel"""
    st.sidebar.markdown("## 🎯 Key Features")

    features = [
        (
            "🤖",
            "Multi-Agent Orchestration",
            "Specialized workers collaborate on complex tasks",
        ),
        ("🔍", "Multi-Source Search", "Wikipedia, SerpAPI, Google, Perplexity"),
        ("🧠", "Vector Memory", "Semantic memory with auto-extraction"),
        ("👤", "User Profiles", "Persistent preferences and context"),
        ("💰", "Cost Tracking", "Budget monitoring per user"),
        ("⚡", "Concurrent Execution", "Parallel worker processing"),
    ]

    for icon, title, desc in features:
        st.sidebar.markdown(
            f"""
        <div style="background: #f8fafc; padding: 0.75rem; border-left: 3px solid #3b82f6; border-radius: 0.5rem; margin: 0.5rem 0;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #1e40af;">
                {icon} {title}
            </div>
            <div style="font-size: 0.85rem; color: #64748b; margin-top: 0.25rem;">
                {desc}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_worker_showcase():
    """Render specialized workers showcase"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 👥 Specialized Workers")

    workers = [
        (WorkerType.MENU_PLANNER, "🍽️", "Menu Planning"),
        (WorkerType.COST_ANALYST, "💵", "Cost Analysis"),
        (WorkerType.OPERATIONS_EXPERT, "⚙️", "Operations"),
        (WorkerType.MARKETING_ADVISOR, "📢", "Marketing"),
        (WorkerType.HR_ADVISOR, "👔", "HR & Staffing"),
    ]

    for worker_type, icon, name in workers:
        template = WorkerTemplates.get_template(worker_type)
        st.sidebar.markdown(
            f"""
        <div style="background: #ecfdf5; padding: 0.5rem; border-radius: 0.5rem; margin: 0.35rem 0;">
            <div style="font-weight: 600; color: #059669;">
                {icon} {name}
            </div>
            <div style="font-size: 0.75rem; color: #064e3b; margin-top: 0.15rem;">
                {len(template.get('tools', []))} tools available
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_system_status():
    """Render system status panel"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("## ⚙️ System Status")

    # Configuration status
    config_status = {
        "OpenAI": bool(Config.OPENAI_API_KEY),
        "Pinecone": bool(Config.PINECONE_API_KEY),
        "SerpAPI": bool(Config.SERPAPI_API_KEY),
        "Google Search": bool(Config.GOOGLE_SEARCH_API_KEY),
        "Perplexity": bool(Config.PERPLEXITY_API_KEY),
    }

    for service, available in config_status.items():
        status = "✅" if available else "❌"
        color = "#10b981" if available else "#ef4444"
        st.sidebar.markdown(
            f"""
        <div style="display: flex; justify-content: space-between; padding: 0.25rem 0;">
            <span style="color: #334155;">{service}</span>
            <span style="color: {color}; font-weight: 600;">{status}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # Orchestration toggle
    st.sidebar.markdown("---")
    orchestration = st.sidebar.checkbox(
        "🎭 Multi-Agent Orchestration",
        value=st.session_state.orchestration_enabled,
        help="Enable parallel worker execution for complex queries",
    )

    if orchestration != st.session_state.orchestration_enabled:
        st.session_state.orchestration_enabled = orchestration
        st.sidebar.success(
            f"Orchestration {'enabled' if orchestration else 'disabled'}!"
        )


def render_statistics():
    """Render usage statistics"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📊 Session Statistics")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        st.metric(
            "Queries",
            st.session_state.total_queries,
            help="Total queries in this session",
        )

    with col2:
        st.metric(
            "Workers Used",
            len(st.session_state.worker_history),
            help="Total worker executions",
        )

    if st.session_state.cost_data["total_cost"] > 0:
        st.sidebar.metric(
            "Est. Cost",
            f"${st.session_state.cost_data['total_cost']:.4f}",
            help="Estimated API costs",
        )


def render_chat_interface():
    """Render main chat interface"""
    st.markdown("## 💬 Research Assistant")

    # Display example queries
    with st.expander("💡 Example Queries (Click to use)", expanded=False):
        examples = [
            "🔍 Simple Query: What is the history of Cape Town?",
            "🎭 Complex Query: Design a restaurant business plan with menu, cost analysis, and marketing strategy",
            "📊 Analysis: Analyze startup costs for a small café including equipment, staffing, and inventory",
            "🍽️ Menu Planning: Create a seasonal menu with wine pairings and cost breakdown",
            "💼 Multi-Domain: How can I improve restaurant operations and reduce food costs?",
        ]

        cols = st.columns(2)
        for i, example in enumerate(examples):
            with cols[i % 2]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    # Extract query text (after emoji and label)
                    query_text = example.split(": ", 1)[1]
                    st.session_state.pending_query = query_text
                    st.rerun()

    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Show metadata if available
                if "metadata" in message and message["metadata"]:
                    metadata = message["metadata"]

                    # Show workers used
                    if "workers" in metadata and metadata["workers"]:
                        st.markdown("**Workers:**")
                        workers_html = "".join(
                            [
                                f'<span class="worker-badge">{w}</span>'
                                for w in metadata["workers"]
                            ]
                        )
                        st.markdown(workers_html, unsafe_allow_html=True)

                    # Show tools used
                    if "tools" in metadata and metadata["tools"]:
                        st.markdown("**Tools:**")
                        tools_html = "".join(
                            [
                                f'<span class="tool-indicator">{t}</span>'
                                for t in metadata["tools"]
                            ]
                        )
                        st.markdown(tools_html, unsafe_allow_html=True)

                    # Show execution time
                    if "execution_time" in metadata:
                        st.caption(
                            f"⏱️ Execution time: {metadata['execution_time']:.2f}s"
                        )

    # Chat input
    if prompt := st.chat_input(
        "Ask me anything about research, business, or use our specialized workers..."
    ):
        handle_user_query(prompt)
    elif hasattr(st.session_state, "pending_query"):
        # Handle example query click
        prompt = st.session_state.pending_query
        del st.session_state.pending_query
        handle_user_query(prompt)


def handle_user_query(prompt: str):
    """Handle user query submission"""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.total_queries += 1

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        progress_placeholder = st.empty()

        # Show processing indicator
        progress_placeholder.markdown(
            """
        <div class="progress-container streaming">
            🔄 Processing your query...
        </div>
        """,
            unsafe_allow_html=True,
        )

        start_time = time.time()

        # Call assistant
        async def get_response():
            async with get_assistant() as assistant:
                return await assistant.chat(prompt, st.session_state.user_id)

        response = run_async(get_response())
        execution_time = time.time() - start_time

        # Clear progress indicator
        progress_placeholder.empty()

        if response:
            # Display response
            response_placeholder.markdown(response)

            # Prepare metadata
            metadata = {
                "execution_time": execution_time,
                "mode": (
                    "orchestration"
                    if st.session_state.orchestration_enabled
                    else "traditional"
                ),
            }

            # Extract worker info if orchestration was used
            if st.session_state.orchestration_enabled and "SPECIALISTS:" in response:
                # Parse workers from response
                workers = []
                if "Menu" in response or "recipe" in response.lower():
                    workers.append("Menu Planner")
                if "cost" in response.lower() or "price" in response.lower():
                    workers.append("Cost Analyst")
                if "marketing" in response.lower():
                    workers.append("Marketing Advisor")
                if "operation" in response.lower():
                    workers.append("Operations Expert")
                if "HR" in response or "staffing" in response.lower():
                    workers.append("HR Advisor")

                if workers:
                    metadata["workers"] = workers
                    st.session_state.worker_history.extend(workers)

                    # Show workers used
                    st.markdown("**🤖 Workers Used:**")
                    workers_html = "".join(
                        [f'<span class="worker-badge">{w}</span>' for w in workers]
                    )
                    st.markdown(workers_html, unsafe_allow_html=True)

            # Show execution time
            st.caption(f"⏱️ Completed in {execution_time:.2f} seconds")

            # Add to chat history
            st.session_state.messages.append(
                {"role": "assistant", "content": response, "metadata": metadata}
            )
        else:
            response_placeholder.error("Failed to generate response. Please try again.")


def render_analytics_tab():
    """Render analytics and insights tab"""
    st.markdown("## 📊 Analytics & Insights")

    if st.session_state.total_queries == 0:
        st.info("👋 No queries yet! Start chatting to see analytics.")
        return

    # Session overview
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Queries",
            st.session_state.total_queries,
            help="Total number of queries in this session",
        )

    with col2:
        st.metric(
            "Worker Executions",
            len(st.session_state.worker_history),
            help="Total number of worker executions",
        )

    with col3:
        avg_workers = len(st.session_state.worker_history) / max(
            st.session_state.total_queries, 1
        )
        st.metric(
            "Avg Workers/Query", f"{avg_workers:.1f}", help="Average workers per query"
        )

    with col4:
        mode = (
            "Orchestration" if st.session_state.orchestration_enabled else "Traditional"
        )
        st.metric("Current Mode", mode, help="Current execution mode")

    # Worker usage breakdown
    if st.session_state.worker_history:
        st.markdown("---")
        st.markdown("### 👥 Worker Usage Distribution")

        from collections import Counter

        worker_counts = Counter(st.session_state.worker_history)

        # Create bar chart data
        chart_data = {
            "Worker": list(worker_counts.keys()),
            "Executions": list(worker_counts.values()),
        }

        import pandas as pd

        df = pd.DataFrame(chart_data)
        st.bar_chart(df.set_index("Worker"))

    # Query history
    st.markdown("---")
    st.markdown("### 💬 Query History")

    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            with st.expander(
                f"Query #{(i//2)+1}: {msg['content'][:50]}...", expanded=False
            ):
                st.markdown(f"**User:** {msg['content']}")

                # Find corresponding assistant response
                if i + 1 < len(st.session_state.messages):
                    assistant_msg = st.session_state.messages[i + 1]
                    st.markdown(f"**Assistant:** {assistant_msg['content'][:200]}...")

                    if "metadata" in assistant_msg:
                        st.json(assistant_msg["metadata"])


def render_documentation_tab():
    """Render documentation and help tab"""
    st.markdown("## 📚 Documentation & Help")

    st.markdown(
        """
    ### 🎯 About This System

    CapeTownConsultant is an advanced AI research assistant featuring:

    - **Multi-Agent Orchestration**: Complex queries are automatically distributed to specialized workers
    - **Specialized Workers**: Domain experts in menu planning, cost analysis, operations, marketing, and HR
    - **Concurrent Execution**: Workers process tasks in parallel for faster results
    - **Vector Memory**: Semantic memory system remembers important context
    - **Multi-Source Search**: Integrates Wikipedia, Google, SerpAPI, and Perplexity

    ### 🤖 Execution Modes

    #### Traditional Mode
    - Single agent handles all queries
    - Best for simple, focused questions
    - Faster for straightforward tasks

    #### Orchestration Mode (Recommended)
    - Automatically engages multiple specialized workers
    - Best for complex, multi-faceted questions
    - Provides comprehensive, expert-level analysis
    - Workers execute concurrently for efficiency

    ### 💡 Tips for Best Results

    1. **Be Specific**: The more details you provide, the better the response
    2. **Use Complex Queries**: Orchestration shines with multi-domain questions
    3. **Ask Follow-ups**: The system maintains conversation context
    4. **Try Different Workers**: Experiment with domain-specific questions

    ### 🔧 System Architecture

    ```
    User Query
        ↓
    Orchestrator (decides routing)
        ↓
    ┌─────────┬─────────┬─────────┐
    │ Worker 1│ Worker 2│ Worker 3│ (Parallel)
    └─────────┴─────────┴─────────┘
        ↓
    Synthesis Layer
        ↓
    Final Response
    ```

    ### 📖 Example Queries

    **Simple (Traditional Mode)**:
    - "What is machine learning?"
    - "Who founded Microsoft?"
    - "Define blockchain"

    **Complex (Orchestration Mode)**:
    - "Create a complete business plan for a restaurant including menu, costs, and marketing"
    - "Analyze the startup costs and ongoing expenses for a small café"
    - "Design a seasonal menu with wine pairings and detailed cost breakdown"

    ### 🎓 Worker Capabilities

    - **Menu Planner**: Recipe development, seasonal menus, wine pairings, dietary accommodations
    - **Cost Analyst**: Pricing strategies, margin analysis, ROI calculations, budget planning
    - **Operations Expert**: Workflow optimization, inventory management, supplier relations
    - **Marketing Advisor**: Brand strategy, social media, promotions, customer acquisition
    - **HR Advisor**: Hiring strategies, training programs, scheduling, team management

    ### ⚙️ Configuration

    The system requires at minimum an OpenAI API key. Additional services enhance capabilities:
    - Pinecone: Enables vector memory
    - SerpAPI/Google: Enhanced web search
    - Perplexity: Advanced research capabilities

    ### 🐛 Troubleshooting

    **Response is slow?**
    - Orchestration involves multiple workers; expect 10-30s for complex queries
    - Check system status in sidebar

    **Workers not activating?**
    - Ensure orchestration mode is enabled
    - Try more complex, multi-domain questions

    **API errors?**
    - Verify API keys in .env file
    - Check rate limits and quotas

    ### 📞 Support

    For issues or questions, refer to the project documentation or check logs at `cache/logs/app.log`
    """
    )


# ============================================================================
# Main Application
# ============================================================================


def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()

    # Render header
    render_header()

    # Render sidebar components
    render_feature_showcase()
    render_worker_showcase()
    render_system_status()
    render_statistics()

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Analytics", "📚 Documentation"])

    with tab1:
        render_chat_interface()

    with tab2:
        render_analytics_tab()

    with tab3:
        render_documentation_tab()

    # Footer
    st.markdown("---")
    st.markdown(
        """
    <div style="text-align: center; color: #64748b; padding: 1rem;">
        🧠 CapeTownConsultant v4.0 | Advanced Multi-Agent Research Assistant
    </div>
    """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
