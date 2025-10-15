"""
Enhanced Streamlit Frontend for CapeTownConsultant v3.0
Compatible with modular architecture
Features: Cost tracking, Memory inspection, Profile management, Tool analytics
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

import streamlit as st

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from modular structure
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.services.cost_tracker import CostTracker
from src.memory.profile import ProfileManager
from src.memory.vector import VectorMemory
from src.services.embeddings import EmbeddingService

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CapeTownConsultant – AI Assistant v3.0",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourusername/capetown-consultant',
        'Report a bug': "https://github.com/yourusername/capetown-consultant/issues",
        'About': "# CapeTownConsultant v3.0\nAutonomous AI Assistant with Memory"
    }
)

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 2rem 1rem;
    }

    /* Headers */
    h1, h2, h3 {
        color: #1e3a8a;
        font-weight: 600;
    }

    /* Cost badge */
    .cost-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        font-weight: 600;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    /* Status indicators */
    .status-good {
        color: #10b981;
        font-weight: 600;
    }
    .status-warning {
        color: #f59e0b;
        font-weight: 600;
    }
    .status-error {
        color: #ef4444;
        font-weight: 600;
    }

    /* Info cards */
    .info-card {
        background: #f8fafc;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    /* Tool badge */
    .tool-badge {
        display: inline-block;
        background: #e0e7ff;
        color: #4338ca;
        padding: 0.25rem 0.75rem;
        border-radius: 0.5rem;
        font-size: 0.875rem;
        margin: 0.25rem;
        font-weight: 500;
    }

    /* Memory item */
    .memory-item {
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0.375rem;
    }

    /* Chat message styling */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }

    /* Sidebar */
    .css-1d391kg {
        padding: 2rem 1rem;
    }

    /* Metrics */
    .stMetric {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
    }

    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.3s;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def status_icon(flag: bool) -> str:
    """Return status icon based on flag"""
    return "✅" if flag else "❌"


def get_cost_status_class(used: float, limit: float) -> str:
    """Get CSS class based on usage percentage"""
    if limit == 0:
        return "status-good"
    percentage = (used / limit * 100)
    if percentage < 50:
        return "status-good"
    elif percentage < 80:
        return "status-warning"
    else:
        return "status-error"


async def get_costs_safe(assistant, user_id: str) -> dict:
    """Safely get costs with error handling"""
    try:
        return await assistant.get_costs(user_id)
    except Exception as e:
        st.error(f"Error fetching costs: {e}")
        return {
            "total": 0.0,
            "limit": Config.DAILY_BUDGET_LIMIT,
            "remaining": Config.DAILY_BUDGET_LIMIT
        }


async def search_memories(user_id: str, query: str = "user information") -> List[Dict]:
    """Search user memories"""
    try:
        cost_tracker = CostTracker()
        embedding_service = EmbeddingService(cost_tracker=cost_tracker)
        vector_memory = VectorMemory(embedding_service)

        namespace = f"user:{user_id}"
        result = await vector_memory.query(query, namespace, top_k=10, user_id=user_id)

        if result.success:
            return result.data.get("matches", [])
        return []
    except Exception as e:
        st.error(f"Error searching memories: {e}")
        return []


async def get_user_profile(user_id: str) -> Dict:
    """Get user profile"""
    try:
        profile_manager = ProfileManager()
        return await profile_manager.read(user_id)
    except Exception as e:
        st.error(f"Error reading profile: {e}")
        return {}


async def update_user_profile(user_id: str, data: Dict) -> bool:
    """Update user profile"""
    try:
        profile_manager = ProfileManager()
        return await profile_manager.write(user_id, data)
    except Exception as e:
        st.error(f"Error updating profile: {e}")
        return False


# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------

def init_session_state():
    """Initialize session state variables"""
    defaults = {
        "assistant": None,
        "assistant_initialized": False,
        "cost_tracker": None,
        "messages": [],
        "user_id": "web_user",
        "session_start": datetime.now(),
        "total_queries": 0,
        "show_costs": Config.ENABLE_COST_TRACKING,
        "auto_refresh_costs": True,
        "show_debug": False,
        "selected_tab": "chat",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize assistant if not done
    if not st.session_state.assistant_initialized:
        try:
            cost_tracker = CostTracker()
            st.session_state.cost_tracker = cost_tracker
            st.session_state.assistant = asyncio.run(
                AutonomousAssistant(cost_tracker=cost_tracker).__aenter__()
            )
            st.session_state.assistant_initialized = True
        except Exception as e:
            st.session_state.assistant = None
            st.session_state.assistant_initialized = False


init_session_state()

# -----------------------------------------------------------------------------
# Sidebar - Navigation & Controls
# -----------------------------------------------------------------------------

with st.sidebar:
    # Header
    st.markdown("# 🧠 CapeTownConsultant")
    st.caption("v3.0 – Modular Architecture")

    st.divider()

    # Navigation
    st.subheader("📍 Navigation")
    selected_view = st.radio(
        "Select View",
        ["💬 Chat", "🧠 Memory", "👤 Profile", "⚙️ Settings", "📊 Analytics"],
        label_visibility="collapsed"
    )

    st.divider()

    # Cost Tracking
    if Config.ENABLE_COST_TRACKING and st.session_state.assistant_initialized:
        st.subheader("💰 Cost Tracking")

        try:
            costs = asyncio.run(get_costs_safe(
                st.session_state.assistant,
                st.session_state.user_id
            ))

            used = costs["total"]
            limit = costs["limit"]
            remaining = costs["remaining"]
            percentage = (used / limit * 100) if limit > 0 else 0

            # Display metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Used", f"${used:.4f}")
            with col2:
                st.metric("Remaining", f"${remaining:.4f}")

            # Progress bar
            st.progress(min(percentage / 100, 1.0))

            status_class = get_cost_status_class(used, limit)
            st.markdown(f'<p class="{status_class}">{percentage:.1f}% of ${limit:.2f}</p>',
                        unsafe_allow_html=True)

            if st.button("🔄 Refresh Costs", use_container_width=True):
                st.rerun()

        except Exception as e:
            st.warning(f"Cost tracking unavailable: {e}")

    st.divider()

    # User Management
    st.subheader("👤 User")
    user_id_input = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Your unique identifier for memory and cost tracking"
    )

    if user_id_input != st.session_state.user_id:
        st.session_state.user_id = user_id_input
        st.success(f"Switched to: {user_id_input}")
        st.rerun()

    st.divider()

    # Configuration Status
    st.subheader("🔧 API Status")
    status = Config.validate_required_keys()

    status_items = [
        ("OpenAI", status['openai']),
        ("Pinecone", status['pinecone']),
        ("SerpAPI", status['serpapi']),
        ("Google", status['google_search']),
        ("Perplexity", status['perplexity']),
    ]

    for name, configured in status_items:
        icon = "✅" if configured else "❌"
        st.text(f"{icon} {name}")

    st.divider()

    # Session Controls
    st.subheader("🎛️ Controls")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            try:
                if st.session_state.assistant:
                    st.session_state.assistant.clear_history()
                st.session_state.messages = []
                st.success("Chat cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Session Stats
    with st.expander("📊 Session Stats"):
        duration = (datetime.now() - st.session_state.session_start).total_seconds() / 60
        st.metric("Duration", f"{duration:.1f} min")
        st.metric("Queries", st.session_state.total_queries)
        st.metric("Messages", len(st.session_state.messages))

# -----------------------------------------------------------------------------
# Main Content Area
# -----------------------------------------------------------------------------

# Chat View
if selected_view == "💬 Chat":
    st.title("💬 Chat with Assistant")
    st.markdown("Ask questions, get research, and let the assistant use tools automatically.")

    # Check if OpenAI is configured
    if not Config.OPENAI_API_KEY:
        st.error("🚨 OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file.")
        st.stop()

    # Warning if not initialized
    if not st.session_state.assistant_initialized:
        st.warning("⚠️ Assistant initialization failed. Running in ephemeral mode (slower).")

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your message...", key="chat_input"):
        # Increment counter
        st.session_state.total_queries += 1

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking and researching..."):
                try:
                    if st.session_state.assistant:
                        response = asyncio.run(
                            st.session_state.assistant.chat(
                                prompt,
                                user_id=st.session_state.user_id
                            )
                        )
                    else:
                        # Fallback to ephemeral
                        async def ephemeral_chat():
                            cost_tracker = CostTracker()
                            async with AutonomousAssistant(cost_tracker=cost_tracker) as assistant:
                                return await assistant.chat(prompt, st.session_state.user_id)


                        response = asyncio.run(ephemeral_chat())

                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})

                    # Auto-refresh costs
                    if st.session_state.auto_refresh_costs and Config.ENABLE_COST_TRACKING:
                        st.rerun()

                except ValueError as e:
                    error_msg = str(e)
                    if "budget" in error_msg.lower() or "limit" in error_msg.lower():
                        st.error(f"🚨 {error_msg}")
                        st.info("💡 Wait until tomorrow for budget reset, or adjust DAILY_BUDGET_LIMIT.")
                    else:
                        st.error(f"❌ {error_msg}")

                except Exception as e:
                    st.error(f"❌ Error: {e}")

# Memory View
elif selected_view == "🧠 Memory":
    st.title("🧠 Memory Explorer")
    st.markdown("View and search your conversation memories stored in the vector database.")

    # Search interface
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(
            "Search memories",
            placeholder="e.g., preferences, goals, interests",
            help="Search for specific memories using semantic search"
        )
    with col2:
        st.write("")  # Spacer
        st.write("")  # Spacer
        search_button = st.button("🔍 Search", use_container_width=True)

    if search_button or search_query:
        query = search_query or "user information and preferences"

        with st.spinner("Searching memories..."):
            memories = asyncio.run(search_memories(st.session_state.user_id, query))

        if memories:
            st.success(f"Found {len(memories)} memories")

            for i, memory in enumerate(memories, 1):
                with st.expander(f"Memory {i} (Score: {memory['score']:.3f})"):
                    st.markdown(f"**Text:** {memory['text']}")

                    metadata = memory.get('metadata', {})
                    if metadata:
                        st.json(metadata)

                    timestamp = memory.get('timestamp', 'Unknown')
                    st.caption(f"Stored: {timestamp}")
        else:
            st.info("No memories found. Start chatting to build your memory!")

    # Memory Statistics
    st.divider()
    st.subheader("📊 Memory Statistics")

    col1, col2, col3 = st.columns(3)

    with col1:
        memories = asyncio.run(search_memories(st.session_state.user_id))
        st.metric("Total Memories", len(memories))

    with col2:
        st.metric("Threshold", f"{Config.MEMORY_SIMILARITY_THRESHOLD:.2f}")

    with col3:
        auto_extract = "Enabled" if Config.AUTO_MEMORY_EXTRACTION else "Disabled"
        st.metric("Auto-Extract", auto_extract)

# Profile View
elif selected_view == "👤 Profile":
    st.title("👤 User Profile")
    st.markdown("Manage your persistent user profile and preferences.")

    # Load profile
    profile = asyncio.run(get_user_profile(st.session_state.user_id))

    # Display current profile
    st.subheader("Current Profile")

    if profile:
        for key, value in profile.items():
            col1, col2, col3 = st.columns([2, 3, 1])
            with col1:
                st.text_input("Key", value=key, disabled=True, key=f"key_{key}")
            with col2:
                st.text_input("Value", value=str(value), disabled=True, key=f"val_{key}")
            with col3:
                if st.button("🗑️", key=f"del_{key}"):
                    del profile[key]
                    if asyncio.run(update_user_profile(st.session_state.user_id, profile)):
                        st.success(f"Deleted {key}")
                        st.rerun()
    else:
        st.info("No profile data. Add some information below.")

    st.divider()

    # Add new profile data
    st.subheader("Add/Update Information")

    col1, col2, col3 = st.columns([2, 3, 1])

    with col1:
        new_key = st.text_input("Key", placeholder="e.g., name, role, preference")

    with col2:
        new_value = st.text_input("Value", placeholder="e.g., John, Chef, Italian food")

    with col3:
        st.write("")  # Spacer
        st.write("")  # Spacer
        if st.button("➕ Add", use_container_width=True):
            if new_key and new_value:
                if asyncio.run(update_user_profile(st.session_state.user_id, {new_key: new_value})):
                    st.success(f"Added: {new_key} = {new_value}")
                    st.rerun()
            else:
                st.warning("Please provide both key and value")

    # Quick presets
    st.divider()
    st.subheader("Quick Presets")

    presets = {
        "Restaurant Owner": {
            "role": "restaurant_owner",
            "industry": "hospitality",
            "interests": "culinary_trends,menu_design,staff_management"
        },
        "Chef": {
            "role": "chef",
            "industry": "culinary",
            "interests": "recipes,techniques,ingredients"
        },
        "Consultant": {
            "role": "consultant",
            "industry": "business",
            "interests": "strategy,operations,analytics"
        }
    }

    preset_col1, preset_col2, preset_col3 = st.columns(3)

    for i, (name, data) in enumerate(presets.items()):
        col = [preset_col1, preset_col2, preset_col3][i]
        with col:
            if st.button(f"📋 {name}", use_container_width=True):
                if asyncio.run(update_user_profile(st.session_state.user_id, data)):
                    st.success(f"Applied {name} preset")
                    st.rerun()

# Settings View
elif selected_view == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")

    # API Configuration
    st.subheader("🔌 API Configuration")

    status = Config.validate_required_keys()

    config_data = [
        ("OpenAI", status['openai'], "Required", "Chat & Embeddings"),
        ("Pinecone", status['pinecone'], "Optional", "Vector Memory"),
        ("SerpAPI", status['serpapi'], "Optional", "Web Search"),
        ("Google Search", status['google_search'], "Optional", "Alternative Search"),
        ("Perplexity", status['perplexity'], "Optional", "Complex Analysis"),
    ]

    for name, configured, requirement, description in config_data:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 3])

        with col1:
            st.text(name)
        with col2:
            if configured:
                st.markdown('<span class="status-good">✅ Active</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="status-error">❌ Missing</span>', unsafe_allow_html=True)
        with col3:
            st.text(requirement)
        with col4:
            st.caption(description)

    st.divider()

    # Application Settings
    st.subheader("⚙️ Application Settings")

    settings_col1, settings_col2 = st.columns(2)

    with settings_col1:
        st.metric("Daily Budget", f"${Config.DAILY_BUDGET_LIMIT:.2f}")
        st.metric("Memory Threshold", f"{Config.MEMORY_SIMILARITY_THRESHOLD:.2f}")
        st.metric("Max History", Config.MAX_CONVERSATION_HISTORY)
        st.metric("Chat Model", Config.CHAT_MODEL)

    with settings_col2:
        st.metric("Embedding Model", Config.EMBEDDING_MODEL)
        st.metric("Summary Model", Config.SUMMARY_MODEL)
        auto_mem = "Enabled" if Config.AUTO_MEMORY_EXTRACTION else "Disabled"
        st.metric("Auto-Memory", auto_mem)
        cost_track = "Enabled" if Config.ENABLE_COST_TRACKING else "Disabled"
        st.metric("Cost Tracking", cost_track)

    st.divider()

    # Rate Limits
    st.subheader("⏱️ Rate Limits")

    rate_col1, rate_col2, rate_col3 = st.columns(3)

    with rate_col1:
        st.metric("OpenAI", f"{Config.OPENAI_RPM} RPM")
    with rate_col2:
        st.metric("SerpAPI", f"{Config.SERPAPI_RPM} RPM")
    with rate_col3:
        st.metric("Perplexity", f"{Config.PERPLEXITY_RPM} RPM")

    st.divider()

    # Cost Information
    st.subheader("💰 Cost Reference")

    st.markdown("""
    | Operation | Cost |
    |-----------|------|
    | GPT-4o Input | $2.50 / 1M tokens |
    | GPT-4o Output | $10.00 / 1M tokens |
    | GPT-4o-mini Input | $0.15 / 1M tokens |
    | GPT-4o-mini Output | $0.60 / 1M tokens |
    | Embeddings | $0.02 / 1M tokens |
    | SerpAPI | $0.002 / search |
    | Google Search | $0.005 / search |
    | Perplexity | $0.001 / request |
    | Wikipedia | Free ✨ |
    """)

# Analytics View
elif selected_view == "📊 Analytics":
    st.title("📊 Analytics & Insights")

    # Session Analytics
    st.subheader("📈 Session Analytics")

    duration = (datetime.now() - st.session_state.session_start).total_seconds()
    duration_min = duration / 60

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Duration", f"{duration_min:.1f} min")
    with col2:
        st.metric("Total Queries", st.session_state.total_queries)
    with col3:
        st.metric("Messages", len(st.session_state.messages))
    with col4:
        avg_time = (duration / st.session_state.total_queries) if st.session_state.total_queries > 0 else 0
        st.metric("Avg Time/Query", f"{avg_time:.1f}s")

    st.divider()

    # Cost Analytics
    if Config.ENABLE_COST_TRACKING:
        st.subheader("💰 Cost Analytics")

        costs = asyncio.run(get_costs_safe(
            st.session_state.assistant,
            st.session_state.user_id
        ))

        cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)

        with cost_col1:
            st.metric("Total Cost", f"${costs['total']:.4f}")
        with cost_col2:
            st.metric("Budget Limit", f"${costs['limit']:.2f}")
        with cost_col3:
            st.metric("Remaining", f"${costs['remaining']:.4f}")
        with cost_col4:
            percentage = (costs['total'] / costs['limit'] * 100) if costs['limit'] > 0 else 0
            st.metric("Usage", f"{percentage:.1f}%")

    st.divider()

    # Memory Analytics
    st.subheader("🧠 Memory Analytics")

    memories = asyncio.run(search_memories(st.session_state.user_id))

    mem_col1, mem_col2, mem_col3 = st.columns(3)

    with mem_col1:
        st.metric("Stored Memories", len(memories))
    with mem_col2:
        avg_score = sum(m['score'] for m in memories) / len(memories) if memories else 0
        st.metric("Avg Relevance", f"{avg_score:.3f}")
    with mem_col3:
        st.metric("Threshold", f"{Config.MEMORY_SIMILARITY_THRESHOLD:.2f}")

    # Memory timeline
    if memories:
        st.divider()
        st.subheader("📅 Recent Memories")

        for memory in memories[:5]:
            timestamp = memory.get('timestamp', 'Unknown')
            score = memory['score']
            text = memory['text']

            st.markdown(f"""
            <div class="memory-item">
                <strong>Score: {score:.3f}</strong> | {timestamp}<br>
                {text}
            </div>
            """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.session_state.assistant_initialized:
        st.caption("🟢 Assistant: Active")
    else:
        st.caption("🟡 Assistant: Ephemeral Mode")

with footer_col2:
    if Config.ENABLE_COST_TRACKING:
        st.caption("💰 Cost Tracking: Enabled")
    else:
        st.caption("💰 Cost Tracking: Disabled")

with footer_col3:
    if Config.AUTO_MEMORY_EXTRACTION:
        st.caption("🧠 Auto-Memory: Active")
    else:
        st.caption("🧠 Auto-Memory: Disabled")

# Version info
st.caption("CapeTownConsultant v3.0 – Modular Architecture")