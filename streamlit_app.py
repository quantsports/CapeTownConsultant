"""
Enhanced Streamlit Frontend for Autonomous Assistant v3.0
Compatible with: Cost tracking, Auto-memory, Persistent cache, Structured logging
"""

import asyncio
import os
from datetime import datetime

import streamlit as st

from main import AutonomousAssistant, Config, CostTracker

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="CapeTownConsultant — Autonomous Assistant v3.0",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stAlert {margin-top: 1rem;}
    .cost-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        font-weight: 600;
        text-align: center;
        margin: 0.5rem 0;
    }
    .status-good {color: #10b981;}
    .status-warning {color: #f59e0b;}
    .status-error {color: #ef4444;}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def _status_icon(flag: bool) -> str:
    """Return status icon based on flag"""
    return "✅" if flag else "❌"


def _get_cost_status_color(used: float, limit: float) -> str:
    """Get color based on usage percentage"""
    percentage = (used / limit * 100) if limit > 0 else 0
    if percentage < 50:
        return "good"
    elif percentage < 80:
        return "warning"
    else:
        return "error"


async def _get_costs_safe(assistant, user_id: str) -> dict:
    """Safely get costs with error handling"""
    try:
        return await assistant.get_costs(user_id)
    except Exception as e:
        st.error(f"Error fetching costs: {e}")
        return {"total": 0.0, "limit": Config.DAILY_BUDGET_LIMIT, "remaining": Config.DAILY_BUDGET_LIMIT}


def _init_session_state():
    """Initialize session state variables"""
    if "assistant" not in st.session_state:
        try:
            # Create cost tracker and assistant
            cost_tracker = CostTracker()
            st.session_state.cost_tracker = cost_tracker
            st.session_state.assistant = asyncio.run(
                AutonomousAssistant(cost_tracker=cost_tracker).__aenter__()
            )
            st.session_state.assistant_initialized = True
        except RuntimeError:
            # Fallback for environments with existing event loop
            st.session_state.assistant = None
            st.session_state.assistant_initialized = False
        except Exception as e:
            st.error(f"Failed to initialize assistant: {e}")
            st.session_state.assistant = None
            st.session_state.assistant_initialized = False

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "user_id" not in st.session_state:
        st.session_state.user_id = "web_user"

    if "session_start" not in st.session_state:
        st.session_state.session_start = datetime.now()

    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0

    if "show_costs" not in st.session_state:
        st.session_state.show_costs = Config.ENABLE_COST_TRACKING

    if "auto_refresh_costs" not in st.session_state:
        st.session_state.auto_refresh_costs = True


_init_session_state()

# -----------------------------------------------------------------------------
# Sidebar - Configuration & Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🧠 CapeTownConsultant")
    st.caption("v3.0 — Enhanced with cost tracking & auto-memory")

    # -----------------------------------------------------------------------------
    # Cost Tracking Section
    # -----------------------------------------------------------------------------
    if Config.ENABLE_COST_TRACKING and st.session_state.assistant_initialized:
        st.subheader("💰 Cost Tracking")

        try:
            costs = asyncio.run(_get_costs_safe(
                st.session_state.assistant,
                st.session_state.user_id
            ))

            # Display cost metrics
            used = costs["total"]
            limit = costs["limit"]
            remaining = costs["remaining"]
            percentage = (used / limit * 100) if limit > 0 else 0

            # Cost badge with gradient
            st.markdown(f"""
                <div class="cost-badge">
                    ${used:.4f} / ${limit:.2f}
                    <br>
                    <small>{percentage:.1f}% used • ${remaining:.4f} remaining</small>
                </div>
            """, unsafe_allow_html=True)

            # Progress bar
            status_color = _get_cost_status_color(used, limit)
            if status_color == "good":
                st.progress(percentage / 100, text="✅ Good")
            elif status_color == "warning":
                st.progress(percentage / 100, text="⚠️ Warning")
            else:
                st.progress(percentage / 100, text="🚨 High Usage")

            # Cost breakdown in expander
            with st.expander("📊 Cost Breakdown"):
                st.caption("**Approximate costs per operation:**")
                st.markdown("""
                - GPT-4o: $2.50 / 1M input tokens
                - GPT-4o: $10.00 / 1M output tokens
                - Embeddings: $0.02 / 1M tokens
                - SerpAPI: $0.002 per search
                - Google: $0.005 per search
                - Perplexity: $0.001 per request
                - Wikipedia: Free ✨
                """)

                if st.button("🔄 Refresh Costs", use_container_width=True):
                    st.rerun()

        except Exception as e:
            st.warning(f"Cost tracking unavailable: {e}")

    st.divider()

    # -----------------------------------------------------------------------------
    # API Configuration Status
    # -----------------------------------------------------------------------------
    st.subheader("⚙️ Configuration")

    # API Keys Status
    with st.expander("🔑 API Keys", expanded=False):
        st.markdown(f"""
        **Search & AI:**
        - OpenAI: {_status_icon(bool(Config.OPENAI_API_KEY))}
        - Pinecone: {_status_icon(bool(Config.PINECONE_API_KEY))}
        - SerpAPI: {_status_icon(bool(Config.SERPAPI_API_KEY))}
        - Google Search: {_status_icon(bool(Config.GOOGLE_SEARCH_API_KEY and Config.GOOGLE_SEARCH_ENGINE_ID))}
        - Perplexity: {_status_icon(bool(Config.PERPLEXITY_API_KEY))}
        """)

    # Feature Status
    with st.expander("✨ Features", expanded=True):
        st.markdown(f"""
        **Active Features:**
        - Cost Tracking: {_status_icon(Config.ENABLE_COST_TRACKING)}
        - Auto-Memory: {_status_icon(Config.AUTO_MEMORY_EXTRACTION)}
        - Persistent Cache: {_status_icon(True)}
        - Structured Logging: {_status_icon(True)}

        **Thresholds:**
        - Memory Similarity: `{Config.MEMORY_SIMILARITY_THRESHOLD}`
        - Daily Budget: `${Config.DAILY_BUDGET_LIMIT:.2f}`
        - Max History: `{Config.MAX_CONVERSATION_HISTORY} messages`
        """)

    st.divider()

    # -----------------------------------------------------------------------------
    # User Settings
    # -----------------------------------------------------------------------------
    st.subheader("👤 User Settings")

    user_id_input = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Unique identifier for cost tracking and memory",
        key="user_id_input"
    )

    if user_id_input != st.session_state.user_id:
        st.session_state.user_id = user_id_input
        st.info(f"User ID changed to: `{user_id_input}`")

    st.divider()

    # -----------------------------------------------------------------------------
    # Session Controls
    # -----------------------------------------------------------------------------
    st.subheader("🎛️ Session Controls")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ Clear Chat", use_container_width=True, help="Clear conversation history"):
            try:
                if st.session_state.get("assistant"):
                    st.session_state.assistant.clear_history()
                st.session_state.messages = []
                st.success("Chat cleared!")
                st.rerun()
            except Exception as e:
                st.error(f"Clear failed: {e}")

    with col2:
        if st.button("🔄 Reset Session", use_container_width=True, type="secondary", help="Restart assistant"):
            try:
                if st.session_state.get("assistant"):
                    asyncio.run(st.session_state.assistant.__aexit__(None, None, None))
            except Exception:
                pass

            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            st.success("Session reset!")
            st.rerun()

    # Session Statistics
    with st.expander("📈 Session Stats"):
        duration = (datetime.now() - st.session_state.session_start).total_seconds() / 60
        st.metric("Session Duration", f"{duration:.1f} min")
        st.metric("Total Queries", st.session_state.total_queries)
        st.metric("Messages", len(st.session_state.messages))
        st.caption(f"Started: {st.session_state.session_start.strftime('%H:%M:%S')}")

    st.divider()

    # -----------------------------------------------------------------------------
    # About Section
    # -----------------------------------------------------------------------------
    with st.expander("ℹ️ About This App"):
        st.markdown("""
        **Autonomous Assistant v3.0**

        **New in v3.0:**
        - 💰 Cost tracking with budget limits
        - 🧠 Automatic memory extraction
        - 💾 Persistent embedding cache
        - 📊 Structured logging
        - 🔄 Smart conversation management

        **Tools Available:**
        - 🌐 Web Search (SerpAPI, Google)
        - 🤖 Perplexity AI (complex queries)
        - 📚 Wikipedia (free, encyclopedic)
        - 🧠 Vector Memory (Pinecone)
        - 👤 User Profiles (persistent)

        **How to Use:**
        1. Ask questions naturally
        2. Tools are selected automatically
        3. Sources are cited in responses
        4. Important facts are stored automatically

        **Cost Optimization:**
        - Wikipedia tried first (free)
        - Web search for most queries (cheap)
        - Perplexity only for complex analysis

        Configure API keys in `.env` file.
        """)

# -----------------------------------------------------------------------------
# Main Chat Area
# -----------------------------------------------------------------------------
st.title("🧠 CapeTownConsultant")
st.markdown("""
Ask questions, research topics, or manage your preferences. I'll use the most appropriate tools 
and cite sources when needed. Your important information is automatically remembered.
""")

# Warning if assistant failed to initialize
if not st.session_state.assistant_initialized:
    st.warning("⚠️ Assistant initialization failed. Running in ephemeral mode (slower).")

# Check if OpenAI is configured
if not Config.OPENAI_API_KEY:
    st.error("🚨 OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file.")
    st.stop()

# Display chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
prompt = st.chat_input("Type your message…", key="chat_input")

if prompt:
    # Increment query counter
    st.session_state.total_queries += 1

    # Echo user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    response_text: str = ""

    try:
        if st.session_state.get("assistant") is not None:
            # Use persistent assistant
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking and researching..."):
                    response_text = asyncio.run(
                        st.session_state.assistant.chat(
                            prompt,
                            user_id=st.session_state.user_id
                        )
                    )
                    st.markdown(response_text)
        else:
            # Fallback: ephemeral assistant per request
            with st.chat_message("assistant"):
                with st.spinner("🤔 Thinking and researching..."):
                    async def _ephemeral_chat() -> str:
                        cost_tracker = CostTracker()
                        async with AutonomousAssistant(cost_tracker=cost_tracker) as tmp_assistant:
                            return await tmp_assistant.chat(
                                prompt,
                                user_id=st.session_state.user_id
                            )


                    response_text = asyncio.run(_ephemeral_chat())
                    st.markdown(response_text)

        # Store assistant response
        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text
        })

        # Auto-refresh costs after query if enabled
        if st.session_state.auto_refresh_costs and Config.ENABLE_COST_TRACKING:
            st.rerun()

    except ValueError as e:
        # Handle budget exceeded errors gracefully
        error_msg = str(e)
        if "budget" in error_msg.lower() or "limit" in error_msg.lower():
            st.error(f"🚨 {error_msg}")
            st.info("💡 Tip: Wait until tomorrow for budget reset, or adjust DAILY_BUDGET_LIMIT in Config.")

            # Show current costs
            if st.session_state.get("assistant"):
                try:
                    costs = asyncio.run(_get_costs_safe(
                        st.session_state.assistant,
                        st.session_state.user_id
                    ))
                    st.metric("Today's Usage", f"${costs['total']:.4f} / ${costs['limit']:.2f}")
                except Exception:
                    pass
        else:
            st.error(f"❌ Error: {error_msg}")

    except Exception as e:
        st.error(f"❌ Unexpected error: {e}")
        st.info("💡 Try resetting the session or check your API keys.")

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.assistant_initialized:
        st.caption("🟢 Assistant: Active")
    else:
        st.caption("🟡 Assistant: Ephemeral Mode")

with col2:
    if Config.ENABLE_COST_TRACKING:
        st.caption("💰 Cost Tracking: Enabled")
    else:
        st.caption("💰 Cost Tracking: Disabled")

with col3:
    if Config.AUTO_MEMORY_EXTRACTION:
        st.caption("🧠 Auto-Memory: Active")
    else:
        st.caption("🧠 Auto-Memory: Disabled")