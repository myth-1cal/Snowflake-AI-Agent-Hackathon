import time
from everos_client import EverOSClient
from gemini_client import GeminiClient
from arxiv_client import ArxivClient
from snowflake_client import SnowflakeClient
from project_store import ProjectStore
import prompts

class ResearchMemoryAgent:
    def __init__(self):
        self.everos = EverOSClient()
        self.gemini = GeminiClient()
        self.arxiv = ArxivClient()
        self.snowflake = SnowflakeClient()
        self.project_store = ProjectStore()

    def _estimate_cost(self, usage):
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        return (prompt_tokens * 0.000000075) + (completion_tokens * 0.00000030)

    def _merge_usage(self, base_usage, new_usage):
        merged = {
            "prompt_tokens": base_usage.get("prompt_tokens", 0) + new_usage.get("prompt_tokens", 0),
            "completion_tokens": base_usage.get("completion_tokens", 0) + new_usage.get("completion_tokens", 0),
            "total_tokens": base_usage.get("total_tokens", 0) + new_usage.get("total_tokens", 0),
        }
        return merged

    def summarize_papers(self, paper_texts, user_id="demo_user_1", enable_memory=True):
        start_time = time.time()
        result = {
            "paper_count": 0,
            "user_id": user_id,
            "enable_memory": enable_memory,
            "summaries": [],
            "shared_sources": [],
            "shared_sources_text": "",
            "memory_context": None,
            "memory_saved": False,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "cost_usd": 0.0,
            "latency_ms": 0.0,
            "error": None,
        }

        try:
            cleaned_papers = [paper for paper in paper_texts or [] if isinstance(paper, str) and paper.strip()]
            result["paper_count"] = len(cleaned_papers)

            if not cleaned_papers:
                raise ValueError("Please provide at least one paper excerpt or abstract.")

            if enable_memory:
                memory_context = self.everos.search_related_memories("paper comparison shared themes", user_id=user_id)
                result["memory_context"] = memory_context

            for paper_text in cleaned_papers:
                summary, usage = self.gemini.generate_response(
                    prompts.PAPER_SUMMARY_PROMPT.format(paper_text=paper_text),
                    "Please summarize this paper."
                )
                result["summaries"].append(summary)
                result["usage"] = self._merge_usage(result["usage"], usage or {})

            if len(cleaned_papers) >= 2:
                shared_sources_prompt = prompts.SHARED_SOURCES_PROMPT.format(
                    paper_1=result["summaries"][0],
                    paper_2=result["summaries"][1],
                )
                shared_sources_text, usage = self.gemini.generate_response(
                    shared_sources_prompt,
                    "Extract shared ideas and themes."
                )
                result["shared_sources_text"] = shared_sources_text
                result["usage"] = self._merge_usage(result["usage"], usage or {})
                result["shared_sources"] = [
                    line.strip().lstrip("-•")
                    for line in shared_sources_text.splitlines()
                    if line.strip()
                ]
            else:
                result["shared_sources_text"] = "Not enough paper content to extract shared themes."

            result["cost_usd"] = self._estimate_cost(result["usage"])

            if enable_memory and result["shared_sources"]:
                try:
                    self.everos.add_memory(
                        user_id,
                        f"Shared paper themes: {' | '.join(result['shared_sources'][:3])}"
                    )
                    result["memory_saved"] = True
                except Exception:
                    result["memory_saved"] = False

        except Exception as exc:
            result["error"] = str(exc)

        finally:
            result["latency_ms"] = (time.time() - start_time) * 1000
            try:
                self.snowflake.log_usage(
                    session_id=user_id,
                    query="paper_comparison",
                    tokens=result["usage"],
                    latency_ms=result["latency_ms"],
                    memory_enabled=enable_memory,
                )
            except Exception:
                pass

        return result

    def ingest_project_papers(self, project_id, arxiv_ids, research_area, user_id="demo_user_1"):
        project = self.project_store.get_project(project_id)
        ingested_papers = []
        errors = []

        for index, arxiv_id in enumerate(arxiv_ids, 1):
            try:
                paper_data = self.arxiv.fetch_paper_details(arxiv_id)
                if not paper_data:
                    raise ValueError(f"Could not resolve arXiv paper {arxiv_id}")

                summary, usage = self.gemini.generate_response(
                    prompts.PAPER_SUMMARY_PROMPT.format(paper_text=paper_data.get("abstract", "") or paper_data.get("title", "")),
                    f"Summarize paper {index}"
                )

                paper_record = {
                    "id": f"{arxiv_id}-{len(ingested_papers) + 1}",
                    "title": paper_data.get("title", arxiv_id),
                    "authors": paper_data.get("authors", []),
                    "published": paper_data.get("published", "Unknown"),
                    "summary": summary,
                    "abstract": paper_data.get("abstract", ""),
                    "url": paper_data.get("url", f"https://arxiv.org/abs/{arxiv_id}"),
                    "raw_text": paper_data.get("full_text", paper_data.get("abstract", "")),
                }
                ingested_papers.append(paper_record)

                self.everos.add_memory(user_id, f"Project {project['title']} paper: {paper_record['title']} - {summary[:180]}")
            except Exception as exc:
                errors.append(f"Paper {arxiv_id}: {exc}")

        if ingested_papers:
            project["papers"] = project.get("papers", []) + ingested_papers
            project["status"] = "ingested"
            project["suggestions"] = self._suggest_related_papers(project, ingested_papers)
            self.project_store.update_project(project_id, **project)

        return {"project": project, "errors": errors}

    def add_related_paper_to_project(self, project_id, paper_id, user_id="demo_user_1"):
        project = self.project_store.get_project(project_id)
        suggestions = project.get("suggestions", [])
        selected = next((item for item in suggestions if item.get("id") == paper_id), None)
        if not selected:
            return project

        arxiv_id = selected.get("arxiv_id")
        if not arxiv_id:
            return project

        result = self.ingest_project_papers(project_id, [arxiv_id], project.get("research_area", ""), user_id=user_id)
        updated_project = result.get("project", project)
        updated_project["suggestions"] = [
            item for item in updated_project.get("suggestions", []) if item.get("id") != paper_id
        ]
        self.project_store.update_project(project_id, **updated_project)
        return updated_project

    def _suggest_related_papers(self, project, ingested_papers):
        research_area = project.get("research_area", "")
        combined_text = " ".join([paper.get("summary", "") for paper in ingested_papers])
        suggestions = []

        for paper in self.arxiv.search_papers(research_area or combined_text, max_results=5):
            title = paper.get("title", "")
            if any(existing.get("title") == title for existing in project.get("papers", [])):
                continue
            suggestions.append({
                "id": paper.get("title", "").lower().replace(" ", "-")[:40],
                "arxiv_id": paper.get("arxiv_id", ""),
                "title": title,
                "authors": paper.get("authors", []),
                "reason": f"Relevant to {project.get('research_area', 'the project focus')}",
            })

        return suggestions[:3]

    def chat_with_project_knowledge(self, project, user_query, user_id="demo_user_1"):
        papers = project.get("papers", [])
        if not papers:
            return "Add at least one paper to the project before chatting with the knowledge base."

        paper_context = "\n\n".join([
            f"Paper: {paper.get('title', 'Untitled')}\nAuthors: {', '.join(paper.get('authors', []))}\nSummary: {paper.get('summary', '')}"
            for paper in papers
        ])
        memory_context = self.everos.search_related_memories(user_query, user_id=user_id)
        prompt = prompts.SYSTEM_PROMPT.format(
            memory_context=memory_context or "No memory context available.",
            paper_context=paper_context or "No paper context available."
        )
        answer, usage = self.gemini.generate_response(
            f"Answer the user's question using the project knowledge base below. Keep it concise and cite the papers you use.\n\n{prompt}",
            user_query,
        )
        self.everos.add_turn(user_id, user_query, answer)
        return answer

    def run_query(self, query, user_id="demo_user_1", enable_memory=True):
        start_time = time.time()
        memory_context = ""
        memory_saved = False
        papers = []
        result = {
            "query": query,
            "user_id": user_id,
            "enable_memory": enable_memory,
            "memory_context": None,
            "papers": [],
            "answer": "",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "cost_usd": 0.0,
            "latency_ms": 0.0,
            "memory_saved": False,
            "error": None,
        }

        try:
            if enable_memory:
                memory_context = self.everos.search_related_memories(query, user_id=user_id)
                result["memory_context"] = memory_context

            papers = self.arxiv.search_papers(query)
            result["papers"] = papers
            paper_context = self.arxiv.format_papers_for_prompt(papers)

            system_prompt = prompts.SYSTEM_PROMPT.format(
                memory_context=memory_context or "No memory context available.",
                paper_context=paper_context or "No papers found for this query."
            )

            if enable_memory:
                compact_prompt = f"Answer briefly using the memory and paper context below. Keep it under 120 words.\n\n{system_prompt}"
                answer, usage = self.gemini.generate_response(compact_prompt, query)
            else:
                answer, usage = self.gemini.generate_response(system_prompt, query)
            result["answer"] = answer
            result["usage"] = usage or result["usage"]
            result["cost_usd"] = self._estimate_cost(result["usage"])

            if enable_memory:
                try:
                    self.everos.add_turn(user_id, query, answer)
                    memory_saved = True
                except Exception:
                    memory_saved = False
            result["memory_saved"] = memory_saved

        except Exception as exc:
            result["error"] = str(exc)
            result["answer"] = "Sorry, I could not process your request right now."

        finally:
            result["latency_ms"] = (time.time() - start_time) * 1000
            try:
                self.snowflake.log_usage(
                    session_id=user_id,
                    query=query,
                    tokens=result["usage"],
                    latency_ms=result["latency_ms"],
                    memory_enabled=enable_memory,
                )
            except Exception:
                pass

        return result

    def compare_modes(self, query, user_id="demo_user_1"):
        try:
            baseline = self.run_query(query, user_id=user_id, enable_memory=False)
            memory = self.run_query(query, user_id=user_id, enable_memory=True)
        except Exception as exc:
            return {
                "baseline": {"error": str(exc), "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "cost_usd": 0.0, "latency_ms": 0.0},
                "memory": {"error": str(exc), "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "cost_usd": 0.0, "latency_ms": 0.0},
                "token_savings_pct": 0.0,
                "cost_savings_usd": 0.0,
            }

        baseline_tokens = baseline["usage"].get("total_tokens", 0)
        memory_tokens = memory["usage"].get("total_tokens", 0)
        baseline_cost = baseline.get("cost_usd", 0.0)
        memory_cost = memory.get("cost_usd", 0.0)

        token_savings = 0.0
        cost_savings = baseline_cost - memory_cost
        if baseline_tokens > 0:
            token_savings = max(0.0, (baseline_tokens - memory_tokens) / baseline_tokens * 100)

        return {
            "baseline": baseline,
            "memory": memory,
            "token_savings_pct": token_savings,
            "cost_savings_usd": max(0.0, cost_savings),
        }
