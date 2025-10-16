"""
Enhanced Streamlit Frontend with Phase 2 Features
- Streaming responses with progress
- Concurrent tool execution (automatic)
- Smart cache statistics
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List
from pathlib import Path

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import Phase 2 enhanced modules
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.services.cost_tracker import CostTracker

# Phase 2: Import cache warmer
try:
    from src.services.cache_warmer import SmartEmbeddingService

    CACHE_WARMER_AVAILABLE = True
except ImportError:
    CACHE_WARMER_AVAILABLE = False

# Page config (same as before)
st.set_page_config(
    page_title="CapeTownConsultant – AI Assistant v3.1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS (same as before, with additions for streaming)
st.markdown("""
<style>
    /* Existing styles... */
    .main { padding: 2rem 1rem; }
    h1, h2, h3 { color: #1e3a8a; font-weight: 600; }

    /* Phase 2: Streaming progress */
    .progress-container {
        background: #f0f9ff;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-family: monospace;
    }

    .tool-indicator {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        margin: 0.25rem;
        font-size: 0.875rem;
    }

    /* Streaming animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .streaming {
        animation: pulse 2s ease-in-out infinite;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# Helper Functions
# ============================================================================

async def get_costs_safe(assistant, user_id: str) -> dict:
    """Safely get costs"""
    try:
        return await assistant.get_costs(user_id)
    except Exception as e:
        st.error(f"Error fetching costs: {e}")
        return {
            "total": 0.0,
            "limit": Config.DAILY_BUDGET_LIMIT,
            "remaining": Config.DAILY_BUDGET_LIMIT
        }


# ============================================================================
# Session State
# ============================================================================

def init_session_state():
    """Initialize session state"""
    defaults = {
        "assistant": None,
        "assistant_initialized": False,
        "cost_tracker": None,
        "messages": [],
        "user_id": "web_user",
        "session_start": datetime.now(),
        "total_queries": 0,
        "streaming_enabled": True,  # Phase 2: Enable streaming by default
        "show_progress": True,  # Phase 2: Show tool progress
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize assistant
    if not st.session_state.assistant_initialized:
        try:
            cost_tracker = CostTracker()
            st.session_state.cost_tracker = cost_tracker

            # Use new event loop to avoid conflicts
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                st.session_state.assistant = loop.run_until_complete(
                    AutonomousAssistant(
                        cost_tracker=cost_tracker,
                        enable_streaming=True
                    ).__aenter__()
                )
                st.session_state.assistant_initialized = True
            finally:
                loop.close()
        except Exception as e:
            st.session_state.assistant = None
            st.session_state.assistant_initialized = False


init_session_state()

# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown("# 🧠 CapeTownConsultant")
    st.caption("v3.1 – Phase 2 Enhanced")
    st.divider()

    # Navigation
    st.subheader("📍 Navigation")
    selected_view = st.radio(
        "Select View",
        ["💬 Chat", "⚙️ Settings", "📊 Performance"],
        label_visibility="collapsed"
    )

    st.divider()

    # Cost tracking
    if Config.ENABLE_COST_TRACKING and st.session_state.assistant_initialized:
        st.subheader("💰 Cost Tracking")
        try:
            costs = asyncio.run(get_costs_safe(
                st.session_state.assistant,
                st.session_state.user_id
            ))

            used = costs["total"]
            limit = costs["limit"]
            percentage = (used / limit * 100) if limit > 0 else 0

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Used", f"${used:.4f}")
            with col2:
                st.metric("Remaining", f"${costs['remaining']:.4f}")

            st.progress(min(percentage / 100, 1.0))

            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        except Exception as e:
            st.warning(f"Cost tracking unavailable: {e}")

    st.divider()

    # User management
    st.subheader("👤 User")
    user_id_input = st.text_input(
        "User ID",
        value=st.session_state.user_id,
        help="Your unique identifier"
    )
    if user_id_input != st.session_state.user_id:
        st.session_state.user_id = user_id_input
        st.success(f"Switched to: {user_id_input}")
        st.rerun()

    st.divider()

    # Phase 2: Streaming controls
    st.subheader("🎛️ Phase 2 Features")
    st.session_state.streaming_enabled = st.checkbox(
        "Enable Streaming",
        value=st.session_state.streaming_enabled,
        help="Show progress as assistant works"
    )
    st.session_state.show_progress = st.checkbox(
        "Show Tool Progress",
        value=st.session_state.show_progress,
        help="Display which tools are being used"
    )

    st.divider()

    # Session controls
    st.subheader("🎛️ Controls")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear", use_container_width=True):
            if st.session_state.assistant:
                st.session_state.assistant.clear_history()
            st.session_state.messages = []
            st.success("Cleared!")
            st.rerun()
    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# ============================================================================
# Main Content
# ============================================================================

if selected_view == "💬 Chat":
    st.title("💬 Chat with Enhanced Assistant")
    st.markdown("**Phase 2 Features**: Concurrent tool execution, streaming responses, smart caching")

    # Check OpenAI configuration
    if not Config.OPENAI_API_KEY:
        st.error("🚨 OpenAI API key not configured.")
        st.stop()

    # Warning if not initialized
    if not st.session_state.assistant_initialized:
        st.warning("⚠️ Assistant in ephemeral mode (slower).")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your message..."):
        st.session_state.total_queries += 1

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            if st.session_state.streaming_enabled and st.session_state.assistant:
                # Phase 2: Streaming response
                response_placeholder = st.empty()
                chunks = []

                try:
                    # Phase 2: Enhanced streaming with activity & controls
                    cancel_key = f"cancel_{st.session_state.total_queries}"
                    st.session_state[cancel_key] = False

                    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1,1,2])
                    with ctrl_col1:
                        if st.button("⏹️ Stop", key=f"stop_{st.session_state.total_queries}"):
                            st.session_state[cancel_key] = True
                    with ctrl_col2:
                        ttft_placeholder = st.empty()
                    with ctrl_col3:
                        copy_placeholder = st.empty()

                    response_placeholder = st.empty()
                    activity_placeholder = st.container()
                    citations_placeholder = st.container()

                    chunks = []
                    content_chunks: List[str] = []
                    tool_state: Dict[str, str] = {}
                    tools_running = False
                    first_token_time = None

                    def render_activity():
                        if not tool_state:
                            return
                        items = []
                        for name, status in tool_state.items():
                            icon = "⏳" if status == "running" else "✅"
                            items.append(f"<span class='tool-indicator'>{icon} {name}</span>")
                        activity_placeholder.markdown(
                            f"<div class='progress-container'><strong>Tool activity:</strong><br>{' '.join(items)}</div>",
                            unsafe_allow_html=True
                        )

                    def render_content():
                        response_placeholder.markdown(
                            f"<div class='{'streaming' if st.session_state.show_progress else ''}'>{''.join(content_chunks)}</div>",
                            unsafe_allow_html=True
                        )

                    def parse_and_render_citations(final_text: str) -> str:
                        # Extract citations section and render as links
                        splitter = "\n\n---\n\n**Sources:**\n"
                        if splitter not in final_text:
                            return final_text
                        body, cites = final_text.split(splitter, 1)
                        links = []
                        for line in cites.splitlines():
                            line = line.strip()
                            if not line:
                                continue
                            # Expect format: [n] url
                            parts = line.split('] ')
                            if len(parts) == 2 and parts[1].startswith('http'):
                                url = parts[1]
                                links.append(url)
                        if links:
                            # Render citations bar
                            items = "".join([f"<li><a href='{u}' target='_blank' rel='noopener noreferrer'>{u}</a></li>" for u in links])
                            citations_placeholder.markdown(
                                f"<div class='info-card'><strong>Sources</strong><ul>{items}</ul></div>",
                                unsafe_allow_html=True
                            )
                        return body

                    start_time = datetime.now()

                    async def stream_response():
                        global first_token_time, tools_running
                        async for chunk in st.session_state.assistant.chat_stream(
                                prompt,
                                user_id=st.session_state.user_id
                        ):
                            if st.session_state.get(cancel_key):
                                break

                            if first_token_time is None:
                                first_token_time = datetime.now()
                                ttft = (first_token_time - start_time).total_seconds()
                                ttft_placeholder.caption(f"TTFT: {ttft:.2f}s")

                            chunks.append(chunk)

                            # Parse activity vs content
                            if chunk.startswith("🔧 "):
                                # Tools starting
                                tools_running = True
                                # Parse tool names after colon
                                try:
                                    names_part = chunk.split(":", 1)[1]
                                    for name in [n.strip() for n in names_part.split(',') if n.strip()]:
                                        tool_state[name] = "running"
                                except Exception:
                                    pass
                                render_activity()
                                continue
                            if chunk.startswith("✅ "):
                                # Mark all tools complete
                                for k in list(tool_state.keys()):
                                    tool_state[k] = "done"
                                tools_running = False
                                render_activity()
                                continue
                            if chunk.startswith("🤔"):
                                # Thinking line -> render as subtle status
                                activity_placeholder.markdown(
                                    f"<div class='progress-container streaming'>{chunk}</div>",
                                    unsafe_allow_html=True
                                )
                                continue

                            # Regular content
                            content_chunks.append(chunk)
                            render_content()

                    asyncio.run(stream_response())

                    # Final display without animation
                    full_response = "".join(content_chunks) if content_chunks else "".join(chunks)
                    # Extract and show citations separately
                    cleaned = parse_and_render_citations(full_response)
                    response_placeholder.markdown(cleaned or full_response)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": cleaned or full_response
                    })
                    copy_placeholder.button("📋 Copy answer", on_click=lambda: st.session_state.update({"_copy": cleaned or full_response}))

                    # Auto-refresh costs if enabled
                    if Config.ENABLE_COST_TRACKING:
                        st.rerun()

                except ValueError as e:
                    error_msg = str(e)
                    if "budget" in error_msg.lower():
                        st.error(f"🚨 {error_msg}")
                        st.info("💡 Wait for budget reset or adjust limit")
                    else:
                        st.error(f"❌ {error_msg}")
                except Exception as e:
                    st.error(f"❌ Error: {e}")

            else:
                # Non-streaming response
                with st.spinner("🤔 Thinking..."):
                    try:
                        if st.session_state.assistant:
                            response = asyncio.run(
                                st.session_state.assistant.chat(
                                    prompt,
                                    user_id=st.session_state.user_id
                                )
                            )
                        else:
                            # Ephemeral fallback
                            async def ephemeral_chat():
                                cost_tracker = CostTracker()
                                async with AutonomousAssistant(cost_tracker=cost_tracker) as asst:
                                    return await asst.chat(prompt, st.session_state.user_id)


                            response = asyncio.run(ephemeral_chat())

                        st.markdown(response)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response
                        })

                        if Config.ENABLE_COST_TRACKING:
                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Error: {e}")


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
            st.markdown("✅ Active" if configured else "❌ Missing")
        with col3:
            st.text(requirement)
        with col4:
            st.caption(description)

    st.divider()

    # Phase 2 Settings
    st.subheader("⚡ Phase 2 Features")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Concurrent Execution", "✅ Enabled")
        st.caption("Tools run in parallel for 2-3x speed")
    with col2:
        st.metric("Smart Caching", "✅ Available" if CACHE_WARMER_AVAILABLE else "❌ Not Available")
        st.caption("Pre-loads frequent embeddings")

    st.info("💡 Phase 2 enhancements are automatically active when available")


elif selected_view == "📊 Performance":
    st.title("📊 Performance Analytics")

    # Session stats
    st.subheader("📈 Session Statistics")
    duration = (datetime.now() - st.session_state.session_start).total_seconds() / 60

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Duration", f"{duration:.1f} min")
    with col2:
        st.metric("Queries", st.session_state.total_queries)
    with col3:
        avg = (duration / st.session_state.total_queries * 60) if st.session_state.total_queries > 0 else 0
        st.metric("Avg Response", f"{avg:.1f}s")

    st.divider()

    # Phase 2 Performance
    st.subheader("⚡ Phase 2 Enhancements")

    st.markdown("""
    **Active Optimizations:**
    - 🔄 **Concurrent Tool Execution**: Multiple tools run simultaneously
    - 📦 **Smart Caching**: Frequently used embeddings pre-loaded
    - 📡 **Streaming Responses**: Progressive display of results

    **Expected Improvements:**
    - 2-3x faster when using multiple tools
    - 50-70% reduction in embedding latency for cached queries
    - Better user experience with progress indicators
    """)

    if CACHE_WARMER_AVAILABLE:
        st.divider()
        st.subheader("🗄️ Cache Statistics")
        try:
            # Lazy-init smart embedding service in session for stats only
            if 'smart_embed' not in st.session_state:
                st.session_state.smart_embed = SmartEmbeddingService(api_key=Config.OPENAI_API_KEY)
            smart = st.session_state.smart_embed
            stats = smart.get_cache_stats()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Unique Queries", stats.get("total_unique_queries", 0))
            with c2:
                st.metric("Total Accesses", stats.get("total_accesses", 0))
            with c3:
                st.markdown("Top Queries:")
                top_list = stats.get("top_10_queries", [])[:5]
                if top_list:
                    for i, q in enumerate(top_list, 1):
                        st.caption(f"{i}. {q}")
                else:
                    st.caption("No data yet")

            colA, colB = st.columns(2)
            with colA:
                if st.button("🔄 Refresh Cache Stats"):
                    st.rerun()
            with colB:
                warm_now = st.text_input("Warm specific queries (comma-separated)", key="warm_inputs")
                if st.button("🔥 Warm Now"):
                    texts = [t.strip() for t in warm_now.split(',') if t.strip()]
                    if texts:
                        # Run an async warm in a safe, minimal way
                        async def do_warm():
                            await smart.cache_warmer.warm_cache(texts=texts, user_id=st.session_state.user_id)
                        asyncio.run(do_warm())
                        st.success("Warming queued/completed")
                        st.rerun()
        except Exception as e:
            st.info(f"Cache stats unavailable: {e}")

# ============================================================================
# Footer
# ============================================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    if st.session_state.assistant_initialized:
        st.caption("🟢 Assistant: Active")
    else:
        st.caption("🟡 Assistant: Ephemeral")

with footer_col2:
    st.caption("⚡ Phase 2: Enhanced")

with footer_col3:
    if st.session_state.streaming_enabled:
        st.caption("📡 Streaming: ON")
    else:
        st.caption("📡 Streaming: OFF")

st.caption("CapeTownConsultant v3.1 – Concurrent | Cached | Streaming")