"""
Multi-Agent Research System - Complete Streamlit UI
Showcases orchestration, real-time progress, and comprehensive research reports
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import json

import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space

# Add project root to path
project_root = (
    Path(__file__).parent.parent
    if Path(__file__).parent.parent.exists()
    else Path.cwd()
)
sys.path.insert(0, str(project_root))

from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.services.cost_tracker import CostTracker

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/yourusername/research-system",
        "Report a bug": "https://github.com/yourusername/research-system/issues",
        "About": """
        # Multi-Agent Research System v4.0

        An advanced AI research assistant that spawns specialized knowledge workers
        to conduct comprehensive, multi-perspective research.

        **Features:**
        - 9+ Specialized Research Workers
        - Concurrent Execution (2-5x faster)
        - Evidence-Based Reports
        - Citation Management
        - Cost Tracking & Budgets
        """,
    },
)

# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown(
    """
<style>
    /* Main Layout */
    .main {
        padding: 1rem 2rem;
    }

    /* Headers */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    h2, h3 {
        color: #2563eb;
        font-weight: 600;
    }

    /* Cards */
    .info-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .metric-card {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }

    /* Status Indicators */
    .status-active {
        color: #10b981;
        font-weight: 600;
    }

    .status-inactive {
        color: #6b7280;
    }

    .status-warning {
        color: #f59e0b;
        font-weight: 600;
    }

    .status-error {
        color: #ef4444;
        font-weight: 600;
    }

    /* Progress */
    .worker-progress {
        background: #f0f9ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        font-family: monospace;
        font-size: 0.9rem;
    }

    .synthesis-box {
        background: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    /* Research Report */
    .report-section {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .citation {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 0.5rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-radius: 4px;
    }

    /* Worker Badges */
    .worker-badge {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        margin: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
    }

    /* Cost Display */
    .cost-display {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
    }

    .cost-warning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    }

    .cost-danger {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        background: #f3f4f6;
        border-radius: 8px 8px 0 0;
    }

    .stTabs [aria-selected="true"] {
        background: white;
        border-bottom: 3px solid #3b82f6;
    }

    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
    }

    /* Example Queries */
    .example-query {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 0.75rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: all 0.2s;
    }

    .example-query:hover {
        background: #f3f4f6;
        border-color: #3b82f6;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================


def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "assistant": None,
        "messages": [],
        "user_id": "research_user",
        "orchestration_enabled": True,
        "current_workers": [],
        "research_in_progress": False,
        "last_report": None,
        "total_queries": 0,
        "session_cost": 0.0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_cost_status(used: float, limit: float) -> tuple:
    """Get cost status color and class"""
    percentage = (used / limit * 100) if limit > 0 else 0

    if percentage < 50:
        return "🟢", "cost-display", "Good"
    elif percentage < 80:
        return "🟡", "cost-display cost-warning", "Warning"
    else:
        return "🔴", "cost-display cost-danger", "Critical"


async def get_costs_safe(user_id: str) -> dict:
    """Safely fetch cost information"""
    try:
        if st.session_state.assistant:
            return await st.session_state.assistant.get_costs(user_id)
    except Exception as e:
        st.sidebar.warning(f"Cost tracking unavailable: {e}")

    return {
        "total": 0.0,
        "limit": Config.DAILY_BUDGET_LIMIT,
        "remaining": Config.DAILY_BUDGET_LIMIT,
    }


def format_worker_name(worker_type: str) -> str:
    """Format worker type for display"""
    return worker_type.replace("_", " ").title()


# =============================================================================
# SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("# 🔬 Research System")
    st.markdown("**Multi-Agent AI Research**")

    add_vertical_space(1)

    # User Settings
    st.markdown("### 👤 User Settings")
    user_id = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Your unique identifier for tracking",
    )
    if user_id != st.session_state.user_id:
        st.session_state.user_id = user_id
        st.success(f"✓ User ID updated")

    add_vertical_space(1)

    # Orchestration Mode
    st.markdown("### 🎯 Research Mode")

    orchestration_enabled = st.toggle(
        "Multi-Agent Orchestration",
        value=st.session_state.orchestration_enabled,
        help="Enable specialized workers for comprehensive research",
    )

    if orchestration_enabled != st.session_state.orchestration_enabled:
        st.session_state.orchestration_enabled = orchestration_enabled
        if st.session_state.assistant:
            st.session_state.assistant.toggle_orchestration(orchestration_enabled)

    mode_text = (
        "🚀 Multi-Agent Mode" if orchestration_enabled else "⚡ Single Agent Mode"
    )
    mode_color = "status-active" if orchestration_enabled else "status-inactive"
    st.markdown(f'<p class="{mode_color}">{mode_text}</p>', unsafe_allow_html=True)

    if orchestration_enabled:
        st.info("✨ Spawns 1-3 specialized workers for comprehensive research")
    else:
        st.info("⚡ Uses single agent for quick responses")

    add_vertical_space(1)

    # Cost Tracking
    st.markdown("### 💰 Cost Tracking")

    try:
        costs = asyncio.run(get_costs_safe(st.session_state.user_id))
        used = costs["total"]
        limit = costs["limit"]
        remaining = costs["remaining"]
        percentage = (used / limit * 100) if limit > 0 else 0

        icon, css_class, status = get_cost_status(used, limit)

        st.markdown(
            f"""
        <div class="{css_class}">
            <div style="font-size: 2rem;">{icon}</div>
            <div style="font-size: 1.5rem; margin: 0.5rem 0;">${used:.4f}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">
                ${remaining:.4f} remaining of ${limit:.2f}
            </div>
            <div style="margin-top: 0.5rem; opacity: 0.8;">
                {percentage:.1f}% used • {status}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.progress(min(percentage / 100, 1.0))

    except Exception as e:
        st.warning("Cost tracking unavailable")

    add_vertical_space(1)

    # API Status
    st.markdown("### 🔌 API Status")

    status_checks = [
        ("OpenAI", bool(Config.OPENAI_API_KEY)),
        ("Pinecone", bool(Config.PINECONE_API_KEY)),
        ("SerpAPI", bool(Config.SERPAPI_API_KEY)),
        ("Google", bool(Config.GOOGLE_SEARCH_API_KEY)),
        ("KAGI", bool(Config.KAGI_API_KEY)),
    ]

    for name, status in status_checks:
        icon = "✅" if status else "❌"
        st.text(f"{icon} {name}")

    add_vertical_space(1)

    # Session Stats
    st.markdown("### 📊 Session Stats")
    st.metric("Total Queries", st.session_state.total_queries)
    st.metric("Session Cost", f"${st.session_state.session_cost:.4f}")

    add_vertical_space(1)

    # Controls
    st.markdown("### 🎛️ Controls")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_report = None
        if st.session_state.assistant:
            st.session_state.assistant.clear_history()
        st.success("✓ Chat cleared")
        st.rerun()

    if st.button("🔄 Reset Session", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            if key != "assistant":
                del st.session_state[key]
        init_session_state()
        st.success("✓ Session reset")
        st.rerun()

# =============================================================================
# MAIN CONTENT
# =============================================================================

# Header
st.markdown("# 🔬 Multi-Agent Research System")
st.markdown("### Comprehensive AI-Powered Research with Specialized Knowledge Workers")

# Info banner
if st.session_state.orchestration_enabled:
    st.markdown(
        """
    <div class="info-card">
        <h3 style="color: white; margin-top: 0;">🚀 Multi-Agent Orchestration Active</h3>
        <p style="margin-bottom: 0;">
            Your queries will be analyzed and distributed to specialized research workers who
            work concurrently to provide comprehensive, multi-perspective insights. Each worker
            focuses on their domain of expertise, and results are synthesized into cohesive reports.
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )
else:
    st.info(
        "⚡ **Single Agent Mode**: Quick responses from a single general-purpose agent."
    )

add_vertical_space(1)

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(
    ["💬 Research Chat", "📊 Available Workers", "📚 Example Queries", "⚙️ System Info"]
)

# =============================================================================
# TAB 1: RESEARCH CHAT
# =============================================================================

with tab1:
    # Display chat messages
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

                # Show metadata if available
                if "metadata" in message:
                    meta = message["metadata"]

                    with st.expander("📋 Research Details", expanded=False):
                        col1, col2, col3 = st.columns(3)

                        if "workers_used" in meta:
                            with col1:
                                st.markdown("**Workers Used:**")
                                for worker in meta["workers_used"]:
                                    st.markdown(
                                        f'<span class="worker-badge">{format_worker_name(worker)}</span>',
                                        unsafe_allow_html=True,
                                    )

                        if "execution_time" in meta:
                            with col2:
                                st.metric(
                                    "Execution Time", f"{meta['execution_time']:.2f}s"
                                )

                        if "sources" in meta and meta["sources"]:
                            with col3:
                                st.metric("Sources", len(meta["sources"]))

                        if "citations" in meta and meta["citations"]:
                            st.markdown("**📚 Citations:**")
                            for citation in meta["citations"][:5]:  # Show first 5
                                st.markdown(
                                    f'<div class="citation">📖 {citation}</div>',
                                    unsafe_allow_html=True,
                                )

    # Chat input
    if prompt := st.chat_input("Enter your research question..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_container = st.empty()
            progress_container = st.container()

            try:
                # Initialize assistant if needed
                if not st.session_state.assistant:
                    with st.spinner("Initializing research system..."):
                        st.session_state.assistant = asyncio.run(
                            AutonomousAssistant(
                                openai_api_key=Config.OPENAI_API_KEY,
                                enable_orchestration=st.session_state.orchestration_enabled,
                            ).__aenter__()
                        )

                # Show progress
                if st.session_state.orchestration_enabled:
                    with progress_container:
                        st.markdown(
                            '<div class="worker-progress">🔍 Analyzing query complexity...</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<div class="worker-progress">🧠 Selecting specialized workers...</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            '<div class="worker-progress">⚡ Executing workers concurrently...</div>',
                            unsafe_allow_html=True,
                        )

                # Get response
                with st.spinner("Conducting research..."):
                    start_time = datetime.now()

                    response = asyncio.run(
                        st.session_state.assistant.chat(
                            prompt, user_id=st.session_state.user_id
                        )
                    )

                    execution_time = (datetime.now() - start_time).total_seconds()

                # Display response
                response_container.markdown(response)

                # Add synthesis notification
                if st.session_state.orchestration_enabled:
                    with progress_container:
                        st.markdown(
                            '<div class="synthesis-box">✨ <strong>Results synthesized</strong> from multiple specialized workers</div>',
                            unsafe_allow_html=True,
                        )

                # Update stats
                st.session_state.total_queries += 1

                # Get updated costs
                costs = asyncio.run(get_costs_safe(st.session_state.user_id))
                st.session_state.session_cost = costs["total"]

                # Store message with metadata
                message_data = {
                    "role": "assistant",
                    "content": response,
                    "metadata": {
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat(),
                        "orchestration_used": st.session_state.orchestration_enabled,
                    },
                }

                st.session_state.messages.append(message_data)
                st.session_state.last_report = response

                st.success(f"✓ Research completed in {execution_time:.2f}s")

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)

# =============================================================================
# TAB 2: AVAILABLE WORKERS
# =============================================================================

with tab2:
    st.markdown("## 🧠 Specialized Knowledge Workers")
    st.markdown("Our system can spawn these specialized workers based on your query:")

    add_vertical_space(1)

    workers_info = {
        "🍽️ Menu Planner": {
            "description": "Expert in menu design, recipe development, and dish pairing",
            "capabilities": [
                "Menu Design",
                "Recipe Development",
                "Wine Pairing",
                "Seasonal Planning",
            ],
            "use_cases": [
                "Creating new menus",
                "Dish recommendations",
                "Pairing suggestions",
            ],
        },
        "💰 Cost Analyst": {
            "description": "Specialist in financial analysis, pricing, and cost optimization",
            "capabilities": [
                "Cost Calculation",
                "Pricing Strategy",
                "Margin Analysis",
                "ROI Analysis",
            ],
            "use_cases": ["Budget planning", "Cost optimization", "Pricing decisions"],
        },
        "⚙️ Operations Expert": {
            "description": "Focused on operational efficiency and workflow optimization",
            "capabilities": [
                "Workflow Design",
                "Inventory Management",
                "Supplier Relations",
                "Quality Control",
            ],
            "use_cases": ["Process improvement", "Resource planning", "Supply chain"],
        },
        "📢 Marketing Strategist": {
            "description": "Expert in brand building, customer acquisition, and campaigns",
            "capabilities": [
                "Campaign Design",
                "Brand Strategy",
                "Social Media",
                "Customer Targeting",
            ],
            "use_cases": [
                "Marketing plans",
                "Brand development",
                "Promotional campaigns",
            ],
        },
        "⭐ Customer Experience": {
            "description": "Specialist in service design and customer satisfaction",
            "capabilities": [
                "Service Design",
                "Ambiance Planning",
                "Staff Training",
                "Feedback Analysis",
            ],
            "use_cases": [
                "Service improvement",
                "Experience design",
                "Customer retention",
            ],
        },
        "💼 Financial Advisor": {
            "description": "Expert in business planning, funding, and financial strategy",
            "capabilities": [
                "Business Planning",
                "Funding Strategy",
                "Financial Modeling",
                "Investment Analysis",
            ],
            "use_cases": ["Business plans", "Fundraising", "Financial projections"],
        },
        "📦 Supplier Specialist": {
            "description": "Focused on procurement, vendor management, and sourcing",
            "capabilities": [
                "Vendor Selection",
                "Contract Negotiation",
                "Quality Sourcing",
                "Cost Reduction",
            ],
            "use_cases": ["Supplier selection", "Procurement", "Contract management"],
        },
        "👥 Staff Manager": {
            "description": "Expert in HR, training, and team development",
            "capabilities": [
                "Recruitment",
                "Training Programs",
                "Scheduling",
                "Performance Management",
            ],
            "use_cases": ["Hiring plans", "Training development", "Team building"],
        },
        "🎯 General Consultant": {
            "description": "Strategic advisor providing high-level insights",
            "capabilities": [
                "Strategic Planning",
                "Business Analysis",
                "Problem Solving",
                "General Advice",
            ],
            "use_cases": [
                "Strategic decisions",
                "Complex problems",
                "Overall planning",
            ],
        },
    }

    # Display workers in grid
    cols = st.columns(3)
    for idx, (name, info) in enumerate(workers_info.items()):
        with cols[idx % 3]:
            with st.container():
                st.markdown(f"### {name}")
                st.markdown(f"**{info['description']}**")

                st.markdown("**Capabilities:**")
                for cap in info["capabilities"]:
                    st.markdown(f"• {cap}")

                with st.expander("Use Cases"):
                    for use_case in info["use_cases"]:
                        st.markdown(f"✓ {use_case}")

                add_vertical_space(1)

# =============================================================================
# TAB 3: EXAMPLE QUERIES
# =============================================================================

with tab3:
    st.markdown("## 📚 Example Research Queries")
    st.markdown("Try these example queries to see the system in action:")

    add_vertical_space(1)

    examples = {
        "🍽️ Restaurant Planning": [
            "Create a comprehensive plan for opening a fine dining Italian restaurant",
            "Design a seasonal menu with cost analysis and wine pairings",
            "Analyze profitability and suggest pricing strategy for a new menu",
        ],
        "📊 Business Strategy": [
            "What are the key success factors for restaurant businesses in 2025?",
            "Compare food delivery platforms and recommend the best option",
            "Create a marketing strategy to increase customer retention by 30%",
        ],
        "⚙️ Operations": [
            "Design an efficient kitchen workflow for a 50-seat restaurant",
            "How can I reduce food waste while maintaining quality?",
            "Create a comprehensive supplier evaluation framework",
        ],
        "💼 Financial Planning": [
            "Analyze startup costs for a quick-service restaurant",
            "What are the most effective cost reduction strategies?",
            "Create a 3-year financial projection for restaurant expansion",
        ],
        "👥 Team Management": [
            "Design a comprehensive staff training program for new hires",
            "What are best practices for reducing employee turnover?",
            "Create an effective scheduling system for variable demand",
        ],
        "🔬 Research & Analysis": [
            "What are the latest trends in sustainable restaurant practices?",
            "Analyze the impact of AI on restaurant operations",
            "Compare different POS systems for restaurants",
        ],
    }

    for category, queries in examples.items():
        st.markdown(f"### {category}")

        for query in queries:
            if st.button(query, key=f"example_{query[:30]}", use_container_width=True):
                # Simulate clicking the chat input
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

        add_vertical_space(1)

# =============================================================================
# TAB 4: SYSTEM INFO
# =============================================================================

with tab4:
    st.markdown("## ⚙️ System Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏗️ Architecture")
        st.markdown(
            """
        **Multi-Agent Orchestration System**

        - **Decision Engine**: Analyzes query complexity
        - **Worker Selection**: Chooses appropriate specialists
        - **Concurrent Execution**: Workers run in parallel
        - **Synthesis**: LLM combines results intelligently
        - **Cost Optimization**: Shared context reduces redundant API calls
        """
        )

        st.markdown("### 📈 Performance")
        st.markdown(
            """
        - **Speed**: 2-5x faster with orchestration
        - **Quality**: Multi-perspective comprehensive reports
        - **Accuracy**: Specialist domain expertise
        - **Cost**: Optimized through parallel execution
        """
        )

    with col2:
        st.markdown("### 🛠️ Features")

        features = [
            ("Multi-Agent Orchestration", st.session_state.orchestration_enabled),
            ("Cost Tracking", Config.ENABLE_COST_TRACKING),
            ("Auto-Memory", Config.AUTO_MEMORY_EXTRACTION),
            ("Citation Management", True),
            ("Persistent Cache", True),
            ("Structured Logging", True),
        ]

        for feature, enabled in features:
            icon = "✅" if enabled else "❌"
            st.markdown(f"{icon} **{feature}**")

        add_vertical_space(1)

        st.markdown("### ⚙️ Configuration")
        st.markdown(
            f"""
        - **Memory Similarity**: `{Config.MEMORY_SIMILARITY_THRESHOLD}`
        - **Daily Budget**: `${Config.DAILY_BUDGET_LIMIT:.2f}`
        - **Max History**: `{Config.MAX_CONVERSATION_HISTORY} messages`
        - **OpenAI Model**: `{Config.CHAT_MODEL}`
        """
        )

    add_vertical_space(2)

    st.markdown("### 📝 How It Works")

    st.markdown(
        """
    #### Query Processing Flow:

    1. **Analysis**: Query is analyzed for complexity and domain requirements
    2. **Worker Selection**: System selects 1-3 specialized workers based on query
    3. **Concurrent Execution**: Workers execute research tasks in parallel
    4. **Tool Usage**: Workers use search, memory, and analysis tools
    5. **Synthesis**: LLM combines worker outputs into cohesive report
    6. **Formatting**: Final response includes citations and metadata

    #### Orchestration Triggers:

    Orchestration is activated when queries have:
    - Length > 100 characters
    - Multiple questions (2+)
    - Multiple action keywords (analyze, design, plan, etc.)
    - Multiple domains (menu, cost, operations, etc.)
    - Complexity indicators ("comprehensive", "detailed", etc.)

    Simple queries use single-agent mode for faster responses.
    """
    )

    add_vertical_space(1)

    # System health check
    st.markdown("### 🏥 System Health")

    health_checks = {
        "OpenAI API": bool(Config.OPENAI_API_KEY),
        "Assistant Initialized": st.session_state.assistant is not None,
        "Orchestration Available": st.session_state.orchestration_enabled,
        "Cost Tracking": Config.ENABLE_COST_TRACKING,
        "Memory System": bool(Config.PINECONE_API_KEY),
        "Search Services": bool(Config.SERPAPI_API_KEY or Config.GOOGLE_SEARCH_API_KEY),
    }

    cols = st.columns(3)
    for idx, (check, status) in enumerate(health_checks.items()):
        with cols[idx % 3]:
            if status:
                st.success(f"✅ {check}")
            else:
                st.warning(f"⚠️ {check}")

# =============================================================================
# FOOTER
# =============================================================================

add_vertical_space(2)
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #6b7280; font-size: 0.9rem;">
    <p>Multi-Agent Research System v4.0 | Built with Streamlit</p>
    <p>Powered by OpenAI GPT-4 • Specialized Knowledge Workers • Concurrent Execution</p>
</div>
""",
    unsafe_allow_html=True,
)
