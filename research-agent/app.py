import streamlit as st
import pandas as pd
import altair as alt
from agent import ResearchMemoryAgent
from snowflake_client import SnowflakeClient
from project_store import ProjectStore

st.set_page_config(page_title="Research Memory Assistant", layout="wide")

def format_usd(value: float) -> str:
    return f"${value:,.6f}"

if "agent" not in st.session_state:
    st.session_state.agent = ResearchMemoryAgent()
    st.session_state.analytics_client = SnowflakeClient()
    st.session_state.project_store = ProjectStore()

st.title("📚 Research Memory Assistant")
st.markdown("### A project-based research workspace for ingesting arXiv papers into EverOS memory.")

tabs = st.tabs(["🧠 Project Workspace", "⚡ Token Economy Comparison", "📊 Snowflake Token Analytics Dashboard"])

with tabs[0]:
    st.subheader("Project Setup")
    user_id = st.text_input("User ID", value="demo_user_1")
    project_title = st.text_input("Project title", value="Interpretability research sprint")
    research_area = st.text_area("Research area", value="sparse autoencoders for interpretability", height=80)
    arxiv_input = st.text_area("arXiv links or IDs", value="https://arxiv.org/abs/2401.12345\n2401.67890", height=100)

    if st.button("Create Project & Ingest Papers"):
        if not project_title.strip() or not research_area.strip() or not arxiv_input.strip():
            st.warning("Please provide a title, research area, and at least one arXiv link or ID.")
        else:
            parsed_links = st.session_state.project_store.parse_arxiv_links(arxiv_input)
            if not parsed_links:
                st.warning("Could not parse any arXiv IDs from the input.")
            else:
                project = st.session_state.project_store.create_project(project_title, research_area, parsed_links)
                st.session_state.current_project_id = project["id"]
                st.session_state.current_project = project
                st.success(f"Project created: {project['title']}")

                with st.spinner("Ingesting papers into memory..."):
                    ingest_result = st.session_state.agent.ingest_project_papers(
                        project_id=project["id"],
                        arxiv_ids=parsed_links,
                        research_area=research_area,
                        user_id=user_id,
                    )

                st.session_state.current_project = ingest_result.get("project", project)
                st.session_state.project_store.update_project(project["id"], **st.session_state.current_project)

                if ingest_result.get("errors"):
                    st.warning("Some papers could not be ingested:")
                    for error in ingest_result["errors"]:
                        st.caption(error)

                st.session_state.project_ready = True

    if st.session_state.get("current_project"):
        project = st.session_state.current_project
        st.markdown("---")
        st.subheader(f"{project.get('title', 'Project')}")
        st.caption(f"Research area: {project.get('research_area', '')}")

        if project.get("papers"):
            st.markdown("### Ingested Papers")
            for paper in project["papers"]:
                with st.expander(f"📄 {paper.get('title','Untitled')}", expanded=False):
                    st.write(f"**Authors:** {', '.join(paper.get('authors', []))}")
                    st.write(f"**Published:** {paper.get('published', 'Unknown')}")
                    st.write(f"**Summary:** {paper.get('summary', '')}")
                    st.write(f"**arXiv:** {paper.get('url', '')}")
                    if paper.get("abstract"):
                        st.write(f"**Abstract:** {paper['abstract']}")

        if project.get("suggestions"):
            st.markdown("### Suggested Related Papers")
            for suggestion in project["suggestions"]:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{suggestion.get('title', 'Untitled')}**")
                    st.write(f"{suggestion.get('authors', [])}")
                    st.write(suggestion.get('reason', ''))
                with col2:
                    if st.button("Add", key=f"add_{suggestion.get('id', '')}"):
                        with st.spinner("Adding suggested paper..."):
                            updated = st.session_state.agent.add_related_paper_to_project(
                                project_id=project["id"],
                                paper_id=suggestion.get("id"),
                                user_id=user_id,
                            )
                        st.session_state.current_project = updated
                        st.session_state.project_store.update_project(project["id"], **updated)
                        st.experimental_rerun()

        if not project.get("papers"):
            st.info("Create a project and ingest papers to start building the project memory.")

with tabs[1]:
    st.subheader("Token Economy Comparison")
    compare_query = st.text_area("Comparison query", value="What are the best techniques for reducing transformer inference costs?", height=120)
    compare_user_id = st.text_input("Comparison User ID", value="demo_user_1", key="compare_user_id")

    if st.button("Run Side-by-Side Comparison"):
        with st.spinner("Comparing baseline and memory-enabled modes..."):
            compare_result = st.session_state.agent.compare_modes(compare_query, user_id=compare_user_id)

        if compare_result.get("baseline", {}).get("error") or compare_result.get("memory", {}).get("error"):
            st.error("Comparison could not complete fully. The agent still returned a response, but one of the runs failed.")
            if compare_result.get("baseline", {}).get("error"):
                st.caption(f"Baseline error: {compare_result['baseline']['error']}")
            if compare_result.get("memory", {}).get("error"):
                st.caption(f"Memory error: {compare_result['memory']['error']}")
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
        st.warning(analytics["error"])
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
