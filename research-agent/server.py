from flask import Flask, jsonify, request, send_from_directory
from agent import ResearchMemoryAgent
from project_store import ProjectStore

app = Flask(__name__, static_folder="web", template_folder="web")
app.config["JSON_SORT_KEYS"] = False

agent = ResearchMemoryAgent()
project_store = ProjectStore()


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/projects")
def list_projects():
    return jsonify(project_store.load_projects())


@app.post("/api/projects")
def create_project():
    payload = request.get_json(silent=True) or {}
    title = (payload.get("title") or "").strip()
    research_area = (payload.get("research_area") or "").strip()
    arxiv_input = (payload.get("arxiv_input") or "").strip()
    user_id = (payload.get("user_id") or "demo_user_1").strip()

    if not title or not research_area or not arxiv_input:
        return jsonify({"error": "Please provide a title, research area, and at least one arXiv link or ID."}), 400

    parsed_links = project_store.parse_arxiv_links(arxiv_input)
    if not parsed_links:
        return jsonify({"error": "Could not parse any arXiv IDs from the input."}), 400

    project = project_store.create_project(title, research_area, parsed_links)
    result = agent.ingest_project_papers(project_id=project["id"], arxiv_ids=parsed_links, research_area=research_area, user_id=user_id)
    updated_project = result.get("project", project)
    project_store.update_project(project["id"], **updated_project)
    return jsonify({"project": updated_project, "errors": result.get("errors", [])})


@app.post("/api/projects/<project_id>/add-papers")
def add_papers(project_id):
    payload = request.get_json(silent=True) or {}
    arxiv_input = (payload.get("arxiv_input") or "").strip()
    user_id = (payload.get("user_id") or "demo_user_1").strip()
    project = project_store.get_project(project_id)

    if not arxiv_input:
        return jsonify({"error": "Please provide at least one arXiv link or ID."}), 400

    parsed_links = project_store.parse_arxiv_links(arxiv_input)
    if not parsed_links:
        return jsonify({"error": "Could not parse any arXiv IDs from the input."}), 400

    result = agent.ingest_project_papers(project_id=project_id, arxiv_ids=parsed_links, research_area=project.get("research_area", ""), user_id=user_id)
    updated_project = result.get("project", project)
    project_store.update_project(project_id, **updated_project)
    return jsonify({"project": updated_project, "errors": result.get("errors", [])})


@app.post("/api/projects/<project_id>/suggestions/<paper_id>")
def add_suggestion(project_id, paper_id):
    project = project_store.get_project(project_id)
    updated_project = agent.add_related_paper_to_project(project_id=project_id, paper_id=paper_id, user_id=project.get("user_id", "demo_user_1"))
    project_store.update_project(project_id, **updated_project)
    return jsonify({"project": updated_project})


@app.post("/api/projects/<project_id>/chat")
def chat(project_id):
    payload = request.get_json(silent=True) or {}
    user_query = (payload.get("user_query") or "").strip()
    user_id = (payload.get("user_id") or "demo_user_1").strip()
    project = project_store.get_project(project_id)
    if not user_query:
        return jsonify({"error": "Please enter a question."}), 400
    reply = agent.chat_with_project_knowledge(project=project, user_query=user_query, user_id=user_id)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
