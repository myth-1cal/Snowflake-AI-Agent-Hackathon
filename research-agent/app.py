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

st.markdown("""
<div style="background: linear-gradient(90deg, #111827 0%, #1f2937 100%); padding: 1.2rem 1.4rem; border-radius: 16px; margin-bottom: 1rem;">
    <h1 style="color: white; margin: 0 0 0.3rem 0; font-size: 1.8rem;">SmartScholar</h1>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "workspace"

nav_col, info_col = st.columns([2, 1])
with nav_col:
    selected = st.radio("", ["Workspace", "Analytics"], horizontal=True, key="nav")
with info_col:
    st.caption("Memory-first research assistant")

if selected == "Workspace":
    st.session_state.active_tab = "workspace"
else:
    st.session_state.active_tab = "analytics"

if st.session_state.active_tab == "workspace":
    st.subheader("Project Workspace")
    left, right = st.columns([1.1, 0.9])

    with left:
        st.markdown("### New project")
        user_id = st.text_input("User ID", value="demo_user_1")
        project_title = st.text_input("Project title", value="Interpretability research sprint")
        research_area = st.text_area("Research area", value="sparse autoencoders for interpretability", height=80)
        arxiv_input = st.text_area("arXiv links or IDs", value="https://arxiv.org/abs/2401.12345\n2401.67890", height=110)

        if st.button("Create Project & Ingest Papers", use_container_width=True):
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

    with right:
        st.markdown("### Project overview")
        if st.session_state.get("current_project"):
            project = st.session_state.current_project
            st.markdown(f"**{project.get('title', 'Project')}**")
            st.caption(f"Research area: {project.get('research_area', '')}")
            st.caption(f"Papers ingested: {len(project.get('papers', []))}")
            st.info("Use this workspace to add papers, explore summaries, and chat with the project knowledge base.")
        else:
            st.info("Create a project on the left to start building your research memory.")

            projects = st.session_state.project_store.load_projects()
            if projects:
                st.markdown("### Recent projects")
                for project in projects[-3:]:
                    st.markdown(f"- **{project.get('title', 'Untitled')}** — {project.get('research_area', '')}")

    if st.session_state.get("current_project"):
        project = st.session_state.current_project
        st.markdown("---")
        st.subheader(f"{project.get('title', 'Project')}")
        st.caption(f"Research area: {project.get('research_area', '')}")

        with st.expander("➕ Add more arXiv papers", expanded=False):
            extra_links = st.text_area("Add more arXiv links or IDs", value="", height=80, key="extra_links")
            if st.button("Add Papers to Project", use_container_width=True):
                if not extra_links.strip():
                    st.warning("Please enter at least one arXiv link or ID.")
                else:
                    parsed_links = st.session_state.project_store.parse_arxiv_links(extra_links)
                    if not parsed_links:
                        st.warning("Could not parse any arXiv IDs from the input.")
                    else:
                        with st.spinner("Adding papers to the project..."):
                            updated = st.session_state.agent.ingest_project_papers(
                                project_id=project["id"],
                                arxiv_ids=parsed_links,
                                research_area=project.get("research_area", ""),
                                user_id=user_id,
                            )
                        st.session_state.current_project = updated.get("project", project)
                        st.session_state.project_store.update_project(project["id"], **st.session_state.current_project)
                        st.rerun()

        if project.get("papers"):
            st.markdown("### Ingested Papers")
            for paper in project["papers"]:
                with st.container():
                    st.markdown(f"#### {paper.get('title','Untitled')}")
                    st.caption(f"Authors: {', '.join(paper.get('authors', []))} • Published: {paper.get('published', 'Unknown')}")
                    st.write(paper.get('summary', ''))
                    if paper.get("abstract"):
                        with st.expander("Show abstract"):
                            st.write(paper["abstract"])
                    st.markdown(f"[Open arXiv]({paper.get('url', '#')})")
                    st.markdown("---")

        if project.get("suggestions"):
            st.markdown("### Suggested Related Papers")
            for suggestion in project["suggestions"]:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{suggestion.get('title', 'Untitled')}**")
                    st.write(f"{suggestion.get('authors', [])}")
                    st.write(suggestion.get('reason', ''))
                with col2:
                    if st.button("Add", key=f"add_{suggestion.get('id', '')}", use_container_width=True):
                        with st.spinner("Adding suggested paper..."):
                            updated = st.session_state.agent.add_related_paper_to_project(
                                project_id=project["id"],
                                paper_id=suggestion.get("id"),
                                user_id=user_id,
                            )
                        st.session_state.current_project = updated
                        st.session_state.project_store.update_project(project["id"], **updated)
                        st.rerun()

        if project.get("papers"):
            st.markdown("---")
            st.subheader("💬 Chat with your knowledge base")
            if "kb_messages" not in st.session_state:
                st.session_state.kb_messages = []

            chat_box = st.container()
            with chat_box:
                for message in st.session_state.kb_messages:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])

                prompt = st.chat_input("Ask about the papers in this project")
            if prompt:
                st.session_state.kb_messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.write(prompt)

                with st.spinner("Searching your knowledge base..."):
                    response = st.session_state.agent.chat_with_project_knowledge(
                        project=project,
                        user_query=prompt,
                        user_id=user_id,
                    )

                st.session_state.kb_messages.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.write(response)
                    st.rerun()

        if not project.get("papers"):
            st.info("Create a project and ingest papers to start building the project memory.")

else:
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
