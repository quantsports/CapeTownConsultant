"""
CapeTownConsultant - Enhanced Streamlit UI v3.1
Phase 2 Features:
- Streaming responses with progress
- Concurrent tool execution (automatic)
- Smart cache statistics
- Robust error handling and resource management
"""

import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import streamlit as st
from contextlib import asynccontextmanager
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import Phase 2 enhanced modules
from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config
from src.services.cost_tracker import CostTracker

# Phase 2: Import cache warmer
CACHE_WARMER_AVAILABLE = False
try:
    from src.services.cache_warmer import SmartEmbeddingService

    CACHE_WARMER_AVAILABLE = True
except ImportError:
    pass

# ============================================================================
# Configuration & Constants
# ============================================================================

MAX_MESSAGES_HISTORY = 100  # Prevent memory leaks
DEFAULT_TIMEOUT = 120.0  # 2 minutes
STREAM_CHUNK_TIMEOUT = 30.0  # 30 seconds per chunk

# Page config
st.set_page_config(
    page_title="CapeTownConsultant – AI Assistant v3.1",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main { padding: 2rem 1rem; }
    h1, h2, h3 { color: #1e3a8a; font-weight: 600; }

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

    .error-card {
        background: #fee;
        border-left: 4px solid #dc2626;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

    .info-card {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }

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
# Async Helper - Streamlit-Safe Event Loop
# ============================================================================

def run_async(coro, timeout: Optional[float] = None):
    """
    Safely run async code in Streamlit.
    Handles event loop conflicts and provides timeout protection.
    """
    try:
        # Get or create event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run with timeout if specified
        if timeout:
            coro = asyncio.wait_for(coro, timeout=timeout)

        return loop.run_until_complete(coro)
    except asyncio.TimeoutError:
        st.error(f"⏱️ Operation timed out after {timeout}s")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


# ============================================================================
# Assistant Manager - Proper Resource Lifecycle
# ============================================================================

class AssistantManager:
    """Manages assistant lifecycle with proper cleanup"""

    def __init__(self):
        self.assistant: Optional[AutonomousAssistant] = None
        self.cost_tracker: Optional[CostTracker] = None
        self.initialized = False
        self.error: Optional[str] = None

    async def initialize(self) -> bool:
        """Initialize assistant with proper error handling"""
        if self.initialized:
            return True

        try:
            self.cost_tracker = CostTracker()
            self.assistant = await AutonomousAssistant(
                cost_tracker=self.cost_tracker
            ).__aenter__()
            self.initialized = True
            self.error = None
            return True
        except Exception as e:
            self.error = f"Initialization failed: {str(e)}"
            self.initialized = False
            return False

    async def cleanup(self):
        """Properly cleanup resources"""
        if self.assistant:
            try:
                await self.assistant.__aexit__(None, None, None)
            except Exception as e:
                print(f"Cleanup error: {e}")
            finally:
                self.assistant = None
                self.initialized = False

    def is_ready(self) -> bool:
        """Check if assistant is ready"""
        return self.initialized and self.assistant is not None

    async def chat(self, message: str, user_id: str) -> Optional[str]:
        """Send message with error handling"""
        if not self.is_ready():
            return None

        try:
            return await self.assistant.chat(message, user_id)
        except Exception as e:
            self.error = str(e)
            return None

    async def get_costs(self, user_id: str) -> Dict[str, float]:
        """Get costs with fallback"""
        if not self.is_ready():
            return {
                "total": 0.0,
                "limit": Config.DAILY_BUDGET_LIMIT,
                "remaining": Config.DAILY_BUDGET_LIMIT
            }

        try:
            return await self.assistant.get_costs(user_id)
        except Exception:
            return {
                "total": 0.0,
                "limit": Config.DAILY_BUDGET_LIMIT,
                "remaining": Config.DAILY_BUDGET_LIMIT
            }

    def clear_history(self):
        """Clear conversation history"""
        if self.is_ready():
            try:
                self.assistant.clear_history()
            except Exception as e:
                self.error = f"Clear failed: {str(e)}"


# ============================================================================
# Session State Management
# ============================================================================

def init_session_state():
    """Initialize session state with validation"""
    defaults = {
        "assistant_manager": AssistantManager(),
        "messages": [],
        "user_id": "web_user",
        "session_start": datetime.now(),
        "total_queries": 0,
        "streaming_enabled": True,
        "show_progress": True,
        "initialization_attempted": False,
        "last_error": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize assistant on first run
    if not st.session_state.initialization_attempted:
        st.session_state.initialization_attempted = True
        manager: AssistantManager = st.session_state.assistant_manager

        with st.spinner("🔄 Initializing assistant..."):
            success = run_async(manager.initialize(), timeout=30.0)

            if not success:
                st.error(f"⚠️ Failed to initialize: {manager.error}")
                st.info("💡 Assistant will run in ephemeral mode (slower)")


init_session_state()


# ============================================================================
# Helper Functions
# ============================================================================

def trim_message_history():
    """Prevent memory leaks by limiting message history"""
    if len(st.session_state.messages) > MAX_MESSAGES_HISTORY:
        # Keep system messages and recent history
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES_HISTORY:]


def safe_rerun():
    """Safely trigger rerun with debouncing"""
    try:
        st.rerun()
    except Exception:
        pass  # Rerun may fail if triggered too quickly


def render_message(role: str, content: str):
    """Render a chat message with proper formatting"""
    with st.chat_message(role):
        # Split citations if present
        if "\n\n---\n\n**Sources:**\n" in content:
            body, citations = content.split("\n\n---\n\n**Sources:**\n", 1)
            st.markdown(body)

            # Render citations as links
            st.markdown("**Sources:**")
            for line in citations.strip().split('\n'):
                if line.strip() and 'http' in line:
                    # Extract URL
                    parts = line.split('] ', 1)
                    if len(parts) == 2:
                        url = parts[1].strip()
                        st.markdown(f"- [{url}]({url})")
        else:
            st.markdown(content)


# ============================================================================
# Chat Response Handler
# ============================================================================

async def handle_chat_response(prompt: str, user_id: str) -> Optional[str]:
    """Handle chat response with proper error handling"""
    manager: AssistantManager = st.session_state.assistant_manager

    if not manager.is_ready():
        # Fallback to ephemeral mode
        st.warning("⚠️ Using ephemeral mode (no persistent assistant)")
        try:
            cost_tracker = CostTracker()
            async with AutonomousAssistant(cost_tracker=cost_tracker) as assistant:
                return await asyncio.wait_for(
                    assistant.chat(prompt, user_id),
                    timeout=DEFAULT_TIMEOUT
                )
        except asyncio.TimeoutError:
            st.error("⏱️ Request timed out")
            return None
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return None

    # Normal mode with initialized assistant
    try:
        return await asyncio.wait_for(
            manager.chat(prompt, user_id),
            timeout=DEFAULT_TIMEOUT
        )
    except asyncio.TimeoutError:
        st.error("⏱️ Request timed out")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return None


def render_streaming_response(prompt: str, user_id: str):
    """Render streaming response with proper state management"""
    manager: AssistantManager = st.session_state.assistant_manager

    # Check if streaming is available
    if not manager.is_ready() or not hasattr(manager.assistant, 'chat_stream'):
        st.warning("📡 Streaming not available, using standard mode")
        with st.spinner("🤔 Thinking..."):
            response = run_async(handle_chat_response(prompt, user_id))
            if response:
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        return

    # Streaming response
    response_container = st.empty()
    activity_container = st.container()

    # State for streaming
    content_chunks: List[str] = []
    tool_state: Dict[str, str] = {}
    start_time = datetime.now()
    first_token_time: Optional[datetime] = None

    def render_content():
        """Render accumulated content"""
        if content_chunks:
            response_container.markdown(''.join(content_chunks))

    def render_activity():
        """Render tool activity"""
        if not tool_state:
            return

        items = []
        for name, status in tool_state.items():
            icon = "⏳" if status == "running" else "✅"
            items.append(f"<span class='tool-indicator'>{icon} {name}</span>")

        activity_container.markdown(
            f"<div class='progress-container'><strong>Tool activity:</strong><br>{' '.join(items)}</div>",
            unsafe_allow_html=True
        )

    async def process_stream():
        """Process streaming response"""
        nonlocal first_token_time

        try:
            async for chunk in manager.assistant.chat_stream(prompt, user_id=user_id):
                # Track time to first token
                if first_token_time is None:
                    first_token_time = datetime.now()
                    ttft = (first_token_time - start_time).total_seconds()
                    st.caption(f"⚡ First token: {ttft:.2f}s")

                # Parse chunk type
                if chunk.startswith("🔧 "):
                    # Tool execution started
                    try:
                        names_part = chunk.split(":", 1)[1]
                        for name in names_part.split(','):
                            name = name.strip()
                            if name:
                                tool_state[name] = "running"
                    except Exception:
                        pass
                    render_activity()

                elif chunk.startswith("✅ "):
                    # Tools completed
                    for key in tool_state:
                        tool_state[key] = "done"
                    render_activity()

                elif chunk.startswith("🤔"):
                    # Thinking indicator
                    activity_container.markdown(
                        f"<div class='progress-container streaming'>{chunk}</div>",
                        unsafe_allow_html=True
                    )

                else:
                    # Regular content
                    content_chunks.append(chunk)
                    render_content()

            # Final render
            full_response = ''.join(content_chunks)
            render_content()

            return full_response

        except asyncio.TimeoutError:
            st.error("⏱️ Stream timed out")
            return None
        except Exception as e:
            st.error(f"❌ Streaming error: {str(e)}")
            return None

    # Execute streaming
    response = run_async(process_stream(), timeout=DEFAULT_TIMEOUT)

    if response:
        st.session_state.messages.append({"role": "assistant", "content": response})

        # Auto-refresh costs
        if Config.ENABLE_COST_TRACKING:
            safe_rerun()


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.markdown("# 🧠 CapeTownConsultant")
    st.caption("v3.1 – Phase 2 Enhanced")
    st.divider()

    # Status indicator
    manager: AssistantManager = st.session_state.assistant_manager
    if manager.is_ready():
        st.success("🟢 Assistant: Online")
    else:
        st.warning("🟡 Assistant: Ephemeral Mode")
        if manager.error:
            with st.expander("⚠️ Error Details"):
                st.code(manager.error)

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
    if Config.ENABLE_COST_TRACKING and manager.is_ready():
        st.subheader("💰 Cost Tracking")

        costs = run_async(manager.get_costs(st.session_state.user_id), timeout=5.0)
        if costs:
            used = costs.get("total", 0.0)
            limit = costs.get("limit", Config.DAILY_BUDGET_LIMIT)
            remaining = costs.get("remaining", limit - used)
            percentage = (used / limit * 100) if limit > 0 else 0

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Used", f"${used:.4f}")
            with col2:
                st.metric("Remaining", f"${remaining:.4f}")

            st.progress(min(percentage / 100, 1.0))

            if st.button("🔄 Refresh", use_container_width=True):
                safe_rerun()

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
        st.success(f"✓ Switched to: {user_id_input}")

    st.divider()

    # Phase 2 controls
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
        if st.button("🗑️ Clear Chat", use_container_width=True):
            manager.clear_history()
            st.session_state.messages = []
            st.success("✓ Cleared!")
            safe_rerun()

    with col2:
        if st.button("🔄 Reset All", use_container_width=True):
            # Cleanup before reset
            run_async(manager.cleanup(), timeout=5.0)

            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]

            safe_rerun()

# ============================================================================
# Main Content
# ============================================================================

if selected_view == "💬 Chat":
    st.title("💬 Chat with Enhanced Assistant")
    st.markdown("**Phase 2 Features**: Concurrent tool execution, streaming responses, smart caching")

    # Check OpenAI configuration
    if not Config.OPENAI_API_KEY:
        st.error("🚨 OpenAI API key not configured. Please set OPENAI_API_KEY in your .env file.")
        st.stop()

    # Display chat history
    for msg in st.session_state.messages[-50:]:  # Only show last 50 messages
        render_message(msg["role"], msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your message..."):
        st.session_state.total_queries += 1

        # Trim history to prevent memory leaks
        trim_message_history()

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_message("user", prompt)

        # Generate response
        with st.chat_message("assistant"):
            if st.session_state.streaming_enabled:
                render_streaming_response(prompt, st.session_state.user_id)
            else:
                with st.spinner("🤔 Thinking..."):
                    response = run_async(
                        handle_chat_response(prompt, st.session_state.user_id),
                        timeout=DEFAULT_TIMEOUT
                    )

                    if response:
                        st.markdown(response)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response
                        })

                        if Config.ENABLE_COST_TRACKING:
                            safe_rerun()

elif selected_view == "⚙️ Settings":
    st.title("⚙️ Settings & Configuration")

    # API Configuration
    st.subheader("🔌 API Configuration")

    status = Config.validate_required_keys()

    config_data = [
        ("OpenAI", status.get('openai', False), "Required", "Chat & Embeddings"),
        ("Pinecone", status.get('pinecone', False), "Optional", "Vector Memory"),
        ("SerpAPI", status.get('serpapi', False), "Optional", "Web Search"),
        ("Google Search", status.get('google_search', False), "Optional", "Alternative Search"),
        ("Perplexity", status.get('perplexity', False), "Optional", "Complex Analysis"),
    ]

    for name, configured, requirement, description in config_data:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 3])

        with col1:
            st.text(name)
        with col2:
            if configured:
                st.markdown("✅ Active")
            else:
                st.markdown("❌ Missing")
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
        cache_status = "✅ Available" if CACHE_WARMER_AVAILABLE else "❌ Not Available"
        st.metric("Smart Caching", cache_status)
        st.caption("Pre-loads frequent embeddings")

    st.info("💡 Phase 2 enhancements are automatically active when available")

    st.divider()

    # System Info
    st.subheader("🔧 System Information")

    manager: AssistantManager = st.session_state.assistant_manager

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Assistant Status", "Ready" if manager.is_ready() else "Not Ready")
        st.metric("Session Duration", f"{(datetime.now() - st.session_state.session_start).seconds // 60} min")

    with col2:
        st.metric("Total Queries", st.session_state.total_queries)
        st.metric("Messages in History", len(st.session_state.messages))

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
            # Lazy-init smart embedding service
            if 'smart_embed' not in st.session_state:
                st.session_state.smart_embed = SmartEmbeddingService(
                    api_key=Config.OPENAI_API_KEY
                )

            smart = st.session_state.smart_embed
            stats = smart.get_cache_stats()

            c1, c2, c3 = st.columns(3)

            with c1:
                st.metric("Total Unique Queries", stats.get("total_unique_queries", 0))

            with c2:
                st.metric("Total Accesses", stats.get("total_accesses", 0))

            with c3:
                st.markdown("**Top Queries:**")
                top_list = stats.get("top_10_queries", [])[:5]
                if top_list:
                    for i, q in enumerate(top_list, 1):
                        st.caption(f"{i}. {q[:50]}...")
                else:
                    st.caption("No data yet")

            if st.button("🔄 Refresh Cache Stats"):
                safe_rerun()

        except Exception as e:
            st.warning(f"Cache stats unavailable: {str(e)}")

# ============================================================================
# Footer
# ============================================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

manager: AssistantManager = st.session_state.assistant_manager

with footer_col1:
    if manager.is_ready():
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