import streamlit as st
import pandas as pd
import altair as alt
from agent import ResearchMemoryAgent
from snowflake_client import SnowflakeClient

st.set_page_config(page_title="Research Memory Assistant", layout="wide")

def format_usd(value: float) -> str:
    return f"${value:,.6f}"

if "agent" not in st.session_state:
    st.session_state.agent = ResearchMemoryAgent()
    st.session_state.analytics_client = SnowflakeClient()

st.title("📚 Research Memory Assistant")
st.markdown("### A demo UI for EverOS memory, Gemini insights, and Snowflake token analytics.")

tabs = st.tabs(["💬 Research Assistant", "⚡ Token Economy Comparison", "📊 Snowflake Token Analytics Dashboard"])

with tabs[0]:
    st.subheader("Research Assistant")
    user_id = st.text_input("User ID", value="demo_user_1")
    query = st.text_area("Research query", value="How can I speed up transformer KV-cache decoding in PyTorch?", height=130)
    enable_memory = st.checkbox("Enable EverOS Memory Context", value=True)

    if st.button("Search & Explain"):
        with st.spinner("Running query with Gemini and EverOS..."):
            result = st.session_state.agent.run_query(query, user_id=user_id, enable_memory=enable_memory)

        if result.get("error"):
            st.error(result["error"])
        else:
            if result["memory_saved"]:
                st.success("✅ New memory was saved to EverOS.")
            if enable_memory:
                with st.expander("🧠 Retrieved EverOS Memory Context", expanded=False):
                    st.write(result.get("memory_context") or "No memory was returned for this query.")

            with st.expander("📄 Referenced arXiv Papers", expanded=True):
                if result["papers"]:
                    for paper in result["papers"]:
                        st.write(f"**{paper['title']}** ({paper['published']})")
                        st.write(paper['summary'])
                        st.write(f"[View PDF]({paper['url']})")
                        st.markdown("---")
                else:
                    st.info("No arXiv papers were found for this query.")

            st.markdown("### Gemini Answer")
            st.write(result["answer"])

            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            metrics_col1.metric("Prompt Tokens", result["usage"].get("prompt_tokens", 0))
            metrics_col2.metric("Completion Tokens", result["usage"].get("completion_tokens", 0))
            metrics_col3.metric("Total Tokens", result["usage"].get("total_tokens", 0))

            cost_col, latency_col = st.columns(2)
            cost_col.metric("Estimated Cost", format_usd(result.get("cost_usd", 0.0)))
            latency_col.metric("Latency", f"{result.get('latency_ms', 0.0):.0f} ms")

with tabs[1]:
    st.subheader("Token Economy Comparison")
    compare_query = st.text_area("Comparison query", value="What are the best techniques for reducing transformer inference costs?", height=120)
    compare_user_id = st.text_input("Comparison User ID", value="demo_user_1", key="compare_user_id")

    if st.button("Run Side-by-Side Comparison"):
        with st.spinner("Comparing baseline and memory-enabled modes..."):
            compare_result = st.session_state.agent.compare_modes(compare_query, user_id=compare_user_id)

        if compare_result.get("baseline", {}).get("error") or compare_result.get("memory", {}).get("error"):
            st.error("Unable to complete comparison. Please verify your environment and try again.")
        else:
            left, right = st.columns(2)
            with left:
                st.markdown("### Baseline Agent (No Memory)")
                st.metric("Total Tokens", compare_result["baseline"]["usage"].get("total_tokens", 0))
                st.metric("Latency", f"{compare_result['baseline'].get('latency_ms', 0.0):.0f} ms")
                st.metric("Estimated Cost", format_usd(compare_result["baseline"].get("cost_usd", 0.0)))
            with right:
                st.markdown("### EverOS Memory Agent")
                st.metric("Total Tokens", compare_result["memory"]["usage"].get("total_tokens", 0))
                st.metric("Latency", f"{compare_result['memory'].get('latency_ms', 0.0):.0f} ms")
                st.metric("Estimated Cost", format_usd(compare_result["memory"].get("cost_usd", 0.0)))

            st.markdown("### Savings")
            savings_col1, savings_col2 = st.columns(2)
            savings_col1.metric("Token Savings", f"{compare_result.get('token_savings_pct', 0.0):.1f}%")
            savings_col2.metric("USD Cost Savings", format_usd(compare_result.get('cost_savings_usd', 0.0)))

with tabs[2]:
    st.subheader("Snowflake Token Analytics Dashboard")
    analytics = st.session_state.analytics_client.get_comparison_analytics()

    if analytics.get("error"):
        st.error(analytics["error"])
    else:
        st.metric("Total Queries", analytics.get("total_queries", 0))
        st.metric("Avg Tokens per Query", f"{analytics.get('avg_tokens_per_query', 0.0):.1f}")
        st.metric("Avg Cost", format_usd(analytics.get("avg_cost_usd", 0.0)))
        st.metric("Total Tokens Saved", analytics.get("total_tokens_saved", 0))

        chart_data = pd.DataFrame([
            {
                "mode": "No Memory",
                "average_tokens": analytics.get("baseline_tokens", 0) / max(1, analytics.get("baseline_queries", 0)),
                "average_cost": analytics.get("baseline_cost", 0.0) / max(1, analytics.get("baseline_queries", 0)),
            },
            {
                "mode": "Memory",
                "average_tokens": analytics.get("memory_tokens", 0) / max(1, analytics.get("memory_queries", 0)),
                "average_cost": analytics.get("memory_cost", 0.0) / max(1, analytics.get("memory_queries", 0)),
            },
        ])

        st.markdown("#### Average Tokens and Cost by Mode")
        st.bar_chart(chart_data.set_index("mode")[['average_tokens', 'average_cost']])

        st.markdown("#### Query Volume by Mode")
        query_chart = pd.DataFrame([
            {"mode": "No Memory", "queries": analytics.get("baseline_queries", 0)},
            {"mode": "Memory", "queries": analytics.get("memory_queries", 0)},
        ])
        st.bar_chart(query_chart.set_index("mode"))
