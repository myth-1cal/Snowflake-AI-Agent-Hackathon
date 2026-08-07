import streamlit as st
import pandas as pd
import altair as alt
from agent import ResearchAgent

st.set_page_config(page_title="EverOS Research Assistant", layout="wide")

# Initialize Agent in Session State
if "agent" not in st.session_state:
    st.session_state.agent = ResearchAgent()
    st.session_state.chat_history = []
    st.session_state.metrics_log = []

st.title("📚 Research Memory Assistant")
st.markdown("### Leveraging EverOS for Personalized, Token-Efficient Research")

# Sidebar for Analytics
with st.sidebar:
    st.header("📊 Token Economy Dashboard")
    if st.session_state.metrics_log:
        df = pd.DataFrame(st.session_state.metrics_log)
        st.metric("Total Tokens Used", df["total_tokens"].sum())
        st.metric("Estimated Cost (USD)", f"${df['cost'].sum():.6f}")
        
        # Latency Chart
        chart = alt.Chart(df).mark_line().encode(
            x='index',
            y='latency',
            tooltip=['index', 'latency']
        ).properties(title="Latency (ms) over Turns")
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Start chatting to see analytics.")
        
    if st.button("Flush EverOS Memory"):
        with st.spinner("Consolidating memories..."):
            st.session_state.agent.everos.flush()
            st.success("Memory flushed & updated!")

# Main Chat Interface
chat_container = st.container()

with chat_container:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

user_input = st.chat_input("Ask about a research topic...")

if user_input:
    # 1. Display User Message
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # 2. Run Agent
    with st.spinner("Agent is searching and thinking..."):
        result = st.session_state.agent.handle_query(user_input)
        
    # 3. Display Assistant Answer
    with st.chat_message("assistant"):
        st.markdown(result["answer"])
        
        # Show Paper Sources
        if result["papers"]:
            with st.expander("📄 Sources (arXiv)"):
                for p in result["papers"]:
                    st.write(f"**{p['title']}** ({p['published']})")
                    st.write(p['summary'][:200] + "...")
                    st.write(f"[Link]({p['url']})")
    
    # 4. Update Metrics & History
    st.session_state.chat_history.append({"role": "assistant", "content": result["answer"]})
    
    # Log for UI Dashboard
    st.session_state.metrics_log.append({
        "total_tokens": result["usage"]["total_tokens"],
        "cost": (result["usage"]["prompt_tokens"] * 0.000000075) + (result["usage"]["completion_tokens"] * 0.00000030),
        "latency": result["latency"],
        "index": len(st.session_state.metrics_log)
    })
    
    st.rerun()
