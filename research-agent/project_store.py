import json
import re
from pathlib import Path
from typing import List, Dict, Any


class ProjectStore:
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path or "projects.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def load_projects(self) -> List[Dict[str, Any]]:
        return json.loads(self.storage_path.read_text(encoding="utf-8"))

    def save_projects(self, projects: List[Dict[str, Any]]) -> None:
        self.storage_path.write_text(json.dumps(projects, indent=2), encoding="utf-8")

    def create_project(self, title: str, research_area: str, arxiv_links: List[str]) -> Dict[str, Any]:
        projects = self.load_projects()
        project = {
            "id": str(len(projects) + 1),
            "title": title.strip(),
            "research_area": research_area.strip(),
            "arxiv_links": arxiv_links,
            "papers": [],
            "suggestions": [],
            "status": "created",
        }
        projects.append(project)
        self.save_projects(projects)
        return project

    def update_project(self, project_id: str, **updates) -> Dict[str, Any]:
        projects = self.load_projects()
        for project in projects:
            if project.get("id") == project_id:
                project.update(updates)
                self.save_projects(projects)
                return project
        raise KeyError(f"Project {project_id} not found")

    def get_project(self, project_id: str) -> Dict[str, Any]:
        for project in self.load_projects():
            if project.get("id") == project_id:
                return project
        raise KeyError(f"Project {project_id} not found")

    def parse_arxiv_links(self, raw_links: str) -> List[str]:
        tokens = re.split(r"\s+", raw_links.strip())
        ids = []
        for token in tokens:
            if not token:
                continue
            token = token.strip().rstrip("/")
            if token.startswith("http"):
                match = re.search(r"(?:abs|pdf)/([^/]+)", token)
                if match:
                    ids.append(match.group(1))
                else:
                    ids.append(token.split("/")[-1])
            else:
                cleaned = token.replace("abs:", "")
                cleaned = cleaned.replace("arxiv:", "")
                cleaned = cleaned.replace(",", "")
                if cleaned:
                    ids.append(cleaned)
        return ids
