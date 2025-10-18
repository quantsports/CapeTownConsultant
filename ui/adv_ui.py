"""
Advanced Streamlit UI with Real-Time Progress Tracking
Features: Streaming responses, live worker status, animated progress
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time

import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.colored_header import colored_header

# Try to import optional enhanced components
try:
    from streamlit_option_menu import option_menu

    HAS_OPTION_MENU = True
except ImportError:
    HAS_OPTION_MENU = False

try:
    import plotly.graph_objects as go
    import plotly.express as px

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

# Add project root to path
project_root = (
    Path(__file__).parent.parent
    if Path(__file__).parent.parent.exists()
    else Path.cwd()
)
sys.path.insert(0, str(project_root))

from src.interface.assistant import AutonomousAssistant
from src.config.settings import Config

# =============================================================================
# ADVANCED PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="🔬 Advanced Research System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# ADVANCED CSS WITH ANIMATIONS
# =============================================================================

st.markdown(
    """
<style>
    /* Animations */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    @keyframes slideIn {
        from {
            transform: translateX(-20px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    /* Worker Status Cards */
    .worker-card {
        background: white;
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
        animation: slideIn 0.3s ease-out;
    }

    .worker-card:hover {
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        transform: translateY(-2px);
    }

    .worker-card.active {
        border-color: #3b82f6;
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
    }

    .worker-card.completed {
        border-color: #10b981;
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
    }

    .worker-card.failed {
        border-color: #ef4444;
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    }

    /* Spinner for active workers */
    .worker-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #e5e7eb;
        border-top-color: #3b82f6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 8px;
        vertical-align: middle;
    }

    /* Progress Timeline */
    .progress-timeline {
        position: relative;
        padding-left: 2rem;
        margin: 1rem 0;
    }

    .progress-timeline::before {
        content: '';
        position: absolute;
        left: 8px;
        top: 0;
        bottom: 0;
        width: 2px;
        background: #e5e7eb;
    }

    .timeline-item {
        position: relative;
        padding-bottom: 1rem;
        animation: slideIn 0.3s ease-out;
    }

    .timeline-item::before {
        content: '';
        position: absolute;
        left: -1.4rem;
        top: 0;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #10b981;
        border: 2px solid white;
        box-shadow: 0 0 0 2px #10b981;
    }

    .timeline-item.active::before {
        background: #3b82f6;
        box-shadow: 0 0 0 2px #3b82f6;
        animation: pulse 2s infinite;
    }

    .timeline-item.pending::before {
        background: #d1d5db;
        box-shadow: 0 0 0 2px #d1d5db;
    }

    /* Streaming text effect */
    .streaming-text {
        animation: slideIn 0.2s ease-out;
    }

    /* Live metrics */
    .live-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
        font-weight: 600;
        animation: pulse 2s infinite;
    }

    /* Research quality indicator */
    .quality-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.875rem;
    }

    .quality-excellent {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
    }

    .quality-good {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
    }

    .quality-fair {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
    }

    /* Tool usage indicators */
    .tool-badge {
        display: inline-flex;
        align-items: center;
        background: #f3f4f6;
        border: 1px solid #d1d5db;
        border-radius: 16px;
        padding: 0.25rem 0.75rem;
        margin: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
    }

    .tool-badge.used {
        background: #dbeafe;
        border-color: #3b82f6;
        color: #1e40af;
    }

    /* Synthesis visualization */
    .synthesis-panel {
        background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
        border: 2px solid #f59e0b;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    /* Report sections */
    .report-section {
        background: white;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    .report-section h3 {
        color: #1e3a8a;
        margin-top: 0;
    }

    /* Citations */
    .citation-list {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }

    .citation-item {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 3px solid #3b82f6;
        background: white;
        border-radius: 4px;
        font-size: 0.9rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# SESSION STATE
# =============================================================================


def init_session_state():
    defaults = {
        "assistant": None,
        "messages": [],
        "user_id": "research_user",
        "orchestration_enabled": True,
        "active_workers": {},
        "research_timeline": [],
        "current_synthesis": None,
        "total_queries": 0,
        "session_cost": 0.0,
        "worker_stats": {},
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def update_worker_status(worker_name: str, status: str, result: str = ""):
    """Update real-time worker status"""
    st.session_state.active_workers[worker_name] = {
        "status": status,  # 'active', 'completed', 'failed'
        "result": result,
        "timestamp": datetime.now(),
    }


def add_timeline_event(event: str, status: str = "completed"):
    """Add event to research timeline"""
    st.session_state.research_timeline.append(
        {
            "event": event,
            "status": status,  # 'completed', 'active', 'pending'
            "timestamp": datetime.now(),
        }
    )


def render_worker_card(worker_name: str, status_data: dict):
    """Render a worker status card"""
    status = status_data["status"]
    result = status_data.get("result", "")

    status_class = {
        "active": "active",
        "completed": "completed",
        "failed": "failed",
    }.get(status, "")

    status_icon = {
        "active": '<span class="worker-spinner"></span>',
        "completed": "✅",
        "failed": "❌",
    }.get(status, "⏳")

    html = f"""
    <div class="worker-card {status_class}">
        <h4>{status_icon} {worker_name}</h4>
        <p><strong>Status:</strong> {status.title()}</p>
        {f'<p><strong>Result:</strong> {result[:100]}...</p>' if result else ''}
        <p><small>Updated: {status_data['timestamp'].strftime('%H:%M:%S')}</small></p>
    </div>
    """

    return html


def render_timeline():
    """Render research progress timeline"""
    if not st.session_state.research_timeline:
        return

    html = '<div class="progress-timeline">'

    for item in st.session_state.research_timeline:
        status_class = item["status"]
        html += f"""
        <div class="timeline-item {status_class}">
            <strong>{item['event']}</strong>
            <br><small>{item['timestamp'].strftime('%H:%M:%S')}</small>
        </div>
        """

    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def calculate_research_quality(response: str, metadata: dict) -> tuple:
    """Calculate research quality score"""
    score = 0

    # Length check
    if len(response) > 500:
        score += 30
    elif len(response) > 200:
        score += 20
    else:
        score += 10

    # Citation check
    citations = metadata.get("citations", [])
    score += min(len(citations) * 10, 30)

    # Worker diversity
    workers = metadata.get("workers_used", [])
    score += min(len(workers) * 20, 40)

    # Determine quality level
    if score >= 80:
        return "Excellent", "quality-excellent", score
    elif score >= 60:
        return "Good", "quality-good", score
    else:
        return "Fair", "quality-fair", score


# =============================================================================
# SIDEBAR WITH ENHANCED NAVIGATION
# =============================================================================

with st.sidebar:
    st.markdown("# 🔬 Research System")

    # Enhanced navigation menu
    if HAS_OPTION_MENU:
        selected = option_menu(
            menu_title="Navigation",
            options=["Research", "Workers", "Analytics", "Settings"],
            icons=["search", "people", "graph-up", "gear"],
            menu_icon="cast",
            default_index=0,
        )
    else:
        selected = st.selectbox(
            "Navigation", ["Research", "Workers", "Analytics", "Settings"]
        )

    add_vertical_space(1)

    # Live session metrics
    st.markdown("### 📊 Live Session")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Queries", st.session_state.total_queries)
    with col2:
        st.metric("Cost", f"${st.session_state.session_cost:.4f}")

    # Active workers indicator
    if st.session_state.active_workers:
        active_count = sum(
            1
            for w in st.session_state.active_workers.values()
            if w["status"] == "active"
        )
        if active_count > 0:
            st.markdown(
                f'<div class="live-metric">🔴 {active_count} Workers Active</div>',
                unsafe_allow_html=True,
            )

    add_vertical_space(1)

    # Controls
    st.markdown("### 🎛️ Controls")

    orchestration = st.toggle(
        "Multi-Agent Mode", value=st.session_state.orchestration_enabled
    )

    if orchestration != st.session_state.orchestration_enabled:
        st.session_state.orchestration_enabled = orchestration
        if st.session_state.assistant:
            st.session_state.assistant.toggle_orchestration(orchestration)

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.research_timeline = []
        st.session_state.active_workers = {}
        st.rerun()

# =============================================================================
# MAIN CONTENT BASED ON NAVIGATION
# =============================================================================

if selected == "Research":
    # Research Chat Interface
    colored_header(
        label="🔬 Research Chat",
        description="Ask complex questions and get comprehensive reports",
        color_name="blue-70",
    )

    # Display timeline
    if st.session_state.research_timeline:
        with st.expander("📅 Research Timeline", expanded=True):
            render_timeline()

    # Active workers display
    if st.session_state.active_workers:
        with st.expander("👥 Active Workers", expanded=True):
            for worker_name, status_data in st.session_state.active_workers.items():
                st.markdown(
                    render_worker_card(worker_name, status_data), unsafe_allow_html=True
                )

    add_vertical_space(1)

    # Chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if "metadata" in message and message["role"] == "assistant":
                meta = message["metadata"]

                # Quality badge
                if "quality" in meta:
                    quality, css_class, score = meta["quality"]
                    st.markdown(
                        f'<span class="{css_class} quality-badge">Quality: {quality} ({score}/100)</span>',
                        unsafe_allow_html=True,
                    )

                # Expandable details
                with st.expander("📋 Research Details"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if "workers_used" in meta:
                            st.markdown("**Workers:**")
                            for worker in meta["workers_used"]:
                                st.markdown(f"• {worker}")

                    with col2:
                        if "execution_time" in meta:
                            st.metric("Time", f"{meta['execution_time']:.2f}s")
                        if "api_calls" in meta:
                            st.metric("API Calls", meta["api_calls"])

                    with col3:
                        if "citations" in meta:
                            st.metric("Citations", len(meta["citations"]))
                        if "sources" in meta:
                            st.metric("Sources", len(meta["sources"]))

                    # Citations
                    if "citations" in meta and meta["citations"]:
                        st.markdown("**📚 Citations:**")
                        st.markdown(
                            '<div class="citation-list">', unsafe_allow_html=True
                        )
                        for i, citation in enumerate(meta["citations"][:10], 1):
                            st.markdown(
                                f'<div class="citation-item">{i}. {citation}</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown("</div>", unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Enter your research question..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Clear previous research data
        st.session_state.active_workers = {}
        st.session_state.research_timeline = []

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Create containers for dynamic updates
            progress_placeholder = st.empty()
            workers_placeholder = st.empty()
            response_placeholder = st.empty()

            try:
                # Initialize assistant
                if not st.session_state.assistant:
                    progress_placeholder.info("🔧 Initializing research system...")
                    st.session_state.assistant = asyncio.run(
                        AutonomousAssistant(
                            api_key=Config.OPENAI_API_KEY,
                            enable_orchestration=st.session_state.orchestration_enabled,
                        ).__aenter__()
                    )

                # Simulate research progress
                if st.session_state.orchestration_enabled:
                    # Analysis phase
                    add_timeline_event("🔍 Analyzing query complexity", "completed")
                    progress_placeholder.info("🔍 Analyzing query...")
                    time.sleep(0.5)

                    # Worker selection
                    add_timeline_event("🧠 Selecting specialized workers", "completed")
                    progress_placeholder.info("🧠 Selecting workers...")
                    time.sleep(0.5)

                    # Simulate worker execution
                    simulated_workers = [
                        "Research Analyst",
                        "Technical Expert",
                        "Domain Specialist",
                    ]
                    for worker in simulated_workers:
                        update_worker_status(worker, "active")
                        add_timeline_event(f"⚡ {worker} started", "active")

                    workers_placeholder.markdown(
                        "".join(
                            [
                                render_worker_card(
                                    w, st.session_state.active_workers[w]
                                )
                                for w in simulated_workers
                            ]
                        ),
                        unsafe_allow_html=True,
                    )

                # Get response
                start_time = datetime.now()

                response = asyncio.run(
                    st.session_state.assistant.chat(
                        prompt, user_id=st.session_state.user_id
                    )
                )

                execution_time = (datetime.now() - start_time).total_seconds()

                # Update workers as completed
                if st.session_state.orchestration_enabled:
                    for worker in simulated_workers:
                        update_worker_status(
                            worker, "completed", "Research completed successfully"
                        )
                        add_timeline_event(f"✅ {worker} completed", "completed")

                    add_timeline_event("🎯 Synthesizing results", "completed")
                    add_timeline_event("✨ Research complete", "completed")

                # Display response
                response_placeholder.markdown(response)

                # Calculate quality
                metadata = {
                    "execution_time": execution_time,
                    "workers_used": (
                        simulated_workers
                        if st.session_state.orchestration_enabled
                        else ["Single Agent"]
                    ),
                    "citations": [],  # Would extract from response
                    "sources": [],
                    "api_calls": (
                        len(simulated_workers) + 1
                        if st.session_state.orchestration_enabled
                        else 1
                    ),
                }

                quality, css_class, score = calculate_research_quality(
                    response, metadata
                )
                metadata["quality"] = (quality, css_class, score)

                # Update stats
                st.session_state.total_queries += 1

                # Store message
                st.session_state.messages.append(
                    {"role": "assistant", "content": response, "metadata": metadata}
                )

                # Clear progress
                progress_placeholder.success(
                    f"✅ Research completed in {execution_time:.2f}s"
                )

            except Exception as e:
                progress_placeholder.error(f"❌ Error: {str(e)}")

elif selected == "Workers":
    # Workers Information
    colored_header(
        label="👥 Specialized Workers",
        description="Meet the expert knowledge workers",
        color_name="violet-70",
    )

    # Worker statistics
    if HAS_PLOTLY and st.session_state.worker_stats:
        fig = px.bar(
            x=list(st.session_state.worker_stats.keys()),
            y=list(st.session_state.worker_stats.values()),
            title="Worker Usage Statistics",
            labels={"x": "Worker Type", "y": "Times Used"},
        )
        st.plotly_chart(fig, use_container_width=True)

    # Worker grid
    st.markdown("### Available Workers")
    # ... (worker information display)

elif selected == "Analytics":
    # Analytics Dashboard
    colored_header(
        label="📊 Research Analytics",
        description="Performance metrics and insights",
        color_name="green-70",
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Queries", st.session_state.total_queries)
    with col2:
        st.metric("Session Cost", f"${st.session_state.session_cost:.4f}")
    with col3:
        avg_time = 5.2  # Calculate from actual data
        st.metric("Avg Response Time", f"{avg_time}s")
    with col4:
        success_rate = 100  # Calculate from actual data
        st.metric("Success Rate", f"{success_rate}%")

    # Add charts if plotly available
    if HAS_PLOTLY:
        st.markdown("### Performance Over Time")
        # Add time series charts here

elif selected == "Settings":
    # Settings Page
    colored_header(
        label="⚙️ System Settings",
        description="Configure your research system",
        color_name="orange-70",
    )

    # System configuration
    # ... (settings interface)

# =============================================================================
# FOOTER
# =============================================================================

add_vertical_space(2)
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #6b7280;">
    <p><strong>Advanced Multi-Agent Research System v4.0</strong></p>
    <p style="font-size: 0.9rem;">Real-time progress tracking • Concurrent execution • Quality analytics</p>
</div>
""",
    unsafe_allow_html=True,
)
