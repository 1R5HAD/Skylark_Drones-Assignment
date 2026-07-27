import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agent import BIAgent

st.set_page_config(page_title="Skylark BI Agent", page_icon="🛸", layout="centered")
st.title("🛸 Skylark Drones — BI Agent")
st.caption("Ask about pipeline, execution, sectors, or billing across the Deals and Work Orders boards.")

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
    st.session_state.display_messages = []  # what we render (text only)

with st.sidebar:
    st.subheader("Session")
    if st.button("🔄 Refresh data from monday.com"):
        if st.session_state.agent:
            st.session_state.agent.refresh_data()
            st.success("Cache cleared — next question re-fetches live data.")
    st.markdown("---")
    st.markdown(
        "**Boards**\n- Work Orders (execution)\n- Deals (pipeline)\n\n"
        "Data is fetched from monday.com on first use each session and cached until refreshed."
    )

if st.session_state.error:
    st.error(
        "Agent failed to initialize: "
        f"{st.session_state.error}\n\nCheck MONDAY_API_TOKEN and GROQ_API_KEY are set."
    )
    st.stop()

for m in st.session_state.display_messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("e.g. How's our pipeline looking for the energy sector this quarter?"):
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Digging through the boards..."):
            try:
                reply, updated_history = st.session_state.agent.ask(st.session_state.messages)
                st.session_state.messages = updated_history
            except Exception as e:
                reply = f"Something went wrong answering that: {e}"
        st.markdown(reply)

    st.session_state.display_messages.append({"role": "assistant", "content": reply})
