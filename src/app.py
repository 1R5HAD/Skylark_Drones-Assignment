import re
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent import BIAgent

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BoardWise — BI Agent",
    page_icon="🛸",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — dark glassmorphism theme with animated accents ──────────────
st.markdown("""
<style>
/* ── Import Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Root variables ── */
:root {
    --bg-primary:    #0f1117;
    --bg-surface:    rgba(25, 28, 38, 0.85);
    --bg-glass:      rgba(40, 44, 60, 0.45);
    --accent-1:      #6c63ff;
    --accent-2:      #00d4aa;
    --accent-3:      #ff6b9d;
    --text-primary:  #e8eaf0;
    --text-muted:    #9ca3b4;
    --border-subtle: rgba(255,255,255,0.06);
    --glow-accent:   rgba(108,99,255,0.25);
}

/* ── Base ── */
html, body, .stApp {
    font-family: 'Inter', sans-serif !important;
}
.stApp {
    background: var(--bg-primary) !important;
}

/* ── Animated gradient strip at top ── */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, var(--accent-1), var(--accent-2), var(--accent-3), var(--accent-1));
    background-size: 300% 100%;
    animation: gradient-slide 6s ease infinite;
    z-index: 9999;
}
@keyframes gradient-slide {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #141722 0%, #0f1117 100%) !important;
    border-right: 1px solid var(--border-subtle) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown li {
    color: var(--text-muted) !important;
    font-size: 0.88rem !important;
}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--text-primary) !important;
    letter-spacing: 0.02em;
}

/* Sidebar button */
section[data-testid="stSidebar"] .stButton > button {
    background: linear-gradient(135deg, var(--accent-1), #8b7cff) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.2rem !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.03em;
    transition: all 0.3s cubic-bezier(.4,0,.2,1) !important;
    box-shadow: 0 4px 15px rgba(108,99,255,0.25) !important;
    width: 100%;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(108,99,255,0.4) !important;
}

/* Sidebar divider */
section[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
    margin: 1.2rem 0 !important;
}

/* ── Chat bubbles ── */
.stChatMessage {
    border-radius: 16px !important;
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.75rem !important;
    border: 1px solid var(--border-subtle) !important;
    animation: msg-appear 0.35s ease-out;
    backdrop-filter: blur(12px);
}
@keyframes msg-appear {
    0% { opacity: 0; transform: translateY(12px); }
    100% { opacity: 1; transform: translateY(0); }
}

/* User messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, rgba(108,99,255,0.12), rgba(108,99,255,0.04)) !important;
    border-left: 3px solid var(--accent-1) !important;
}

/* Assistant messages */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--bg-glass) !important;
    border-left: 3px solid var(--accent-2) !important;
}

/* ── Chat input ── */
.stChatInput {
    border-radius: 14px !important;
}
.stChatInput > div {
    border: 1px solid var(--border-subtle) !important;
    border-radius: 14px !important;
    background: var(--bg-surface) !important;
    transition: border-color 0.3s ease, box-shadow 0.3s ease !important;
}
.stChatInput > div:focus-within {
    border-color: var(--accent-1) !important;
    box-shadow: 0 0 0 3px var(--glow-accent) !important;
}
.stChatInput textarea {
    color: var(--text-primary) !important;
    font-family: 'Inter', sans-serif !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: var(--accent-2) !important;
}

/* ── Success toast ── */
.stSuccess {
    background: rgba(0,212,170,0.08) !important;
    border: 1px solid rgba(0,212,170,0.3) !important;
    border-radius: 10px !important;
    color: var(--accent-2) !important;
}

/* ── Error toast ── */
.stAlert[data-baseweb="notification"] {
    border-radius: 10px !important;
}

/* ── Hero container ── */
.hero-section {
    text-align: center;
    padding: 3rem 1.5rem 2rem;
    animation: hero-fade 0.8s ease-out;
}
@keyframes hero-fade {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
.hero-section .hero-icon {
    font-size: 3.5rem;
    margin-bottom: 0.5rem;
    display: inline-block;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
}
.hero-section h1 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6c63ff, #00d4aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0.3rem 0 0.6rem;
}
.hero-section .hero-subtitle {
    color: #9ca3b4;
    font-size: 0.95rem;
    line-height: 1.6;
    max-width: 520px;
    margin: 0 auto;
}

/* ── Prompt chip pills ── */
.prompt-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
    margin-top: 1.5rem;
}
.prompt-chips .chip {
    background: rgba(108,99,255,0.08);
    border: 1px solid rgba(108,99,255,0.2);
    color: #b0abff;
    padding: 0.45rem 0.9rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
    cursor: default;
    transition: all 0.25s ease;
}
.prompt-chips .chip:hover {
    background: rgba(108,99,255,0.15);
    border-color: rgba(108,99,255,0.4);
    transform: translateY(-1px);
}

/* ── Sidebar status badge ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.7rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.status-badge.online {
    background: rgba(0,212,170,0.12);
    color: #00d4aa;
    border: 1px solid rgba(0,212,170,0.25);
}
.status-badge .pulse-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #00d4aa;
    animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,212,170,0.4); }
    50% { box-shadow: 0 0 0 5px rgba(0,212,170,0); }
}

/* ── Board info cards in sidebar ── */
.board-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border-subtle);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    margin-bottom: 0.5rem;
    transition: background 0.25s ease;
}
.board-card:hover {
    background: rgba(255,255,255,0.06);
}
.board-card .board-icon {
    font-size: 1.1rem;
    margin-right: 0.4rem;
}
.board-card .board-name {
    font-weight: 600;
    font-size: 0.85rem;
    color: #e8eaf0;
}
.board-card .board-desc {
    font-size: 0.78rem;
    color: #7a8296;
    margin-top: 0.2rem;
}

/* ── Footer ── */
.sidebar-footer {
    color: #5a6275;
    font-size: 0.72rem;
    text-align: center;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border-subtle);
}

/* ── Status container tweaks ── */
[data-testid="stStatusWidget"] {
    border-radius: 12px !important;
    border: 1px solid var(--border-subtle) !important;
}

/* ── Thinking expander ── */
[data-testid="stExpander"] {
    border: 1px solid var(--border-subtle) !important;
    border-radius: 12px !important;
    background: rgba(108,99,255,0.03) !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    color: var(--text-muted) !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _render_thinking_expander(tool_log: list[dict]):
    """Render an expandable section showing the agent's tool-call steps."""
    n = len(tool_log)
    with st.expander(f"🧠 Agent reasoning — {n} step{'s' if n != 1 else ''}", expanded=False):
        for i, step in enumerate(tool_log, 1):
            name = step["name"]
            args = step["args"]
            result = step["result"]

            if name == "get_data_summary":
                board = args.get("board", "?")
                rows_m = re.search(r"rows:\s*(\d+)", result)
                cols_m = re.search(r"columns:\s*(\d+)", result)
                rows_n = rows_m.group(1) if rows_m else "?"
                cols_n = cols_m.group(1) if cols_m else "?"
                st.markdown(
                    f"**Step {i} · 📊 Data Summary** — `{board}` "
                    f"({rows_n} rows, {cols_n} columns)"
                )
            elif name == "run_analysis":
                st.markdown(f"**Step {i} · 🐍 Analysis**")
                st.code(args.get("code", ""), language="python")
                if result and not result.startswith("Error"):
                    preview = result[:500]
                    if len(result) > 500:
                        preview += "\n… (truncated)"
                    st.caption("Output:")
                    st.code(preview, language="text")
                elif result and result.startswith("Error"):
                    st.error(result)
            else:
                st.markdown(f"**Step {i} · 🔧 `{name}`**")

            if i < n:
                st.divider()


# ── Session state init ───────────────────────────────────────────────────────
if "agent" not in st.session_state:
    try:
        st.session_state.agent = BIAgent()
        st.session_state.error = None
    except Exception as e:
        st.session_state.agent = None
        st.session_state.error = str(e)

if "messages" not in st.session_state:
    st.session_state.messages = []  # Anthropic-format history
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []  # what we render (text + optional tool_log)

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 0.3rem;">
        <span style="font-size:1.8rem;">🛸</span>
        <div style="font-size:1.1rem; font-weight:700; color:#e8eaf0; margin-top:0.15rem;
                    letter-spacing:0.03em;">BoardWise <span style="font-size:0.7rem;font-weight:400;color:#9ca3b4;">BI Agent</span></div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.get("agent"):
        st.markdown("""
        <div style="text-align:center; margin-bottom:0.8rem;">
            <span class="status-badge online">
                <span class="pulse-dot"></span>
                AGENT ONLINE
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🔄  Refresh data from monday.com", use_container_width=True):
        if st.session_state.agent:
            st.session_state.agent.refresh_data()
            st.success("✓ Cache cleared — next question will fetch live data.")

    st.markdown("---")

    st.markdown("##### 📋 Connected Boards")
    st.markdown("""
    <div class="board-card">
        <span class="board-icon">📦</span>
        <span class="board-name">Work Orders</span>
        <div class="board-desc">Project execution, status, billing & collection</div>
    </div>
    <div class="board-card">
        <span class="board-icon">💼</span>
        <span class="board-name">Deals</span>
        <div class="board-desc">Sales pipeline, deal stage, value & probability</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown(
        "<div class='sidebar-footer'>"
        "Data is fetched from monday.com on first use<br>and cached until refreshed."
        "</div>",
        unsafe_allow_html=True,
    )

# ── Error gate ───────────────────────────────────────────────────────────────
if st.session_state.error:
    st.error(
        "Agent failed to initialize: "
        f"{st.session_state.error}\n\nCheck MONDAY_API_TOKEN and GEMINI_API_KEY are set."
    )
    st.stop()

# ── Welcome hero (shown only when no messages yet) ──────────────────────────
if not st.session_state.display_messages:
    st.markdown("""
    <div class="hero-section">
        <div class="hero-icon">🛸</div>
        <h1>BoardWise <span style="font-size:1.2rem;font-weight:400;color:#9ca3b4;">BI Agent</span></h1>
        <div class="hero-subtitle">
            Ask anything about your pipeline, deal flow, project execution, sectors,
            or billing — powered by live monday.com data.
        </div>
        <div class="prompt-chips">
            <span class="chip">📊 Pipeline by sector</span>
            <span class="chip">💰 Revenue this quarter</span>
            <span class="chip">⏳ Stuck deals</span>
            <span class="chip">📈 Work order completion</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Chat history ─────────────────────────────────────────────────────────────
for m in st.session_state.display_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("tool_log"):
            _render_thinking_expander(m["tool_log"])

# ── Chat input & response ───────────────────────────────────────────────────
if prompt := st.chat_input("e.g. How's our pipeline looking for the energy sector this quarter?"):
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        tool_log: list[dict] = []

        with st.status("🔍 Analysing the boards…", expanded=True) as status:

            def _on_tool_call(name: str, args: dict, result: str):
                tool_log.append({"name": name, "args": args, "result": result})
                step = len(tool_log)

                if name == "get_data_summary":
                    board = args.get("board", "?")
                    rows_m = re.search(r"rows:\s*(\d+)", result)
                    cols_m = re.search(r"columns:\s*(\d+)", result)
                    rows_n = rows_m.group(1) if rows_m else "?"
                    cols_n = cols_m.group(1) if cols_m else "?"
                    st.markdown(
                        f"➜ **Step {step}** · 📊 Fetched `{board}` board "
                        f"— {rows_n} rows, {cols_n} columns"
                    )
                elif name == "run_analysis":
                    first_line = args.get("code", "").split("\n")[0][:60]
                    st.markdown(f"➜ **Step {step}** · 🐍 `{first_line}…`")
                else:
                    st.markdown(f"➜ **Step {step}** · 🔧 `{name}`")

                status.update(label=f"🔧 Step {step}: {name}…")

            try:
                reply, updated_history = st.session_state.agent.ask(
                    st.session_state.messages,
                    on_tool_call=_on_tool_call,
                )
                st.session_state.messages = updated_history
            except Exception as e:
                reply = f"Something went wrong answering that: {e}"

            if tool_log:
                status.update(
                    label=f"✅ Completed — {len(tool_log)} tool call{'s' if len(tool_log) != 1 else ''}",
                    state="complete",
                    expanded=False,
                )
            else:
                status.update(label="✅ Done", state="complete", expanded=False)

        st.markdown(reply)

        if tool_log:
            _render_thinking_expander(tool_log)

    st.session_state.display_messages.append({
        "role": "assistant",
        "content": reply,
        "tool_log": tool_log if tool_log else None,
    })
