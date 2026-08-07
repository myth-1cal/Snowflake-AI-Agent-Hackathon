import arxiv

class ArxivClient:
    def __init__(self):
        self.client = arxiv.Client()

    def search_papers(self, query, max_results=3):
        """Searches arXiv for papers and returns simplified data."""
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        papers = []
        for result in self.client.results(search):
            papers.append({
                "title": result.title,
                "summary": result.summary.replace("\n", " "),
                "url": result.pdf_url,
                "authors": [a.name for a in result.authors],
                "published": result.published.strftime("%Y-%m-%d"),
                "abstract": result.summary.replace("\n", " "),
                "arxiv_id": self._normalize_arxiv_id(result.entry_id),
            })
        return papers

    def fetch_paper_details(self, arxiv_id, max_retries=1):
        normalized = self._normalize_arxiv_id(arxiv_id)
        search = arxiv.Search(id_list=[normalized])
        results = list(self.client.results(search))
        if not results:
            return None
        result = results[0]
        return {
            "title": result.title,
            "authors": [a.name for a in result.authors],
            "published": result.published.strftime("%Y-%m-%d"),
            "abstract": result.summary.replace("\n", " "),
            "url": result.entry_id,
            "full_text": result.summary.replace("\n", " "),
            "arxiv_id": normalized,
        }

    def format_papers_for_prompt(self, papers):
        """Formats paper list into a string for the LLM."""
        formatted = ""
        for i, p in enumerate(papers):
            formatted += f"Paper {i+1}: {p['title']}\n"
            formatted += f"Authors: {', '.join(p['authors'])}\n"
            formatted += f"Summary: {p['summary']}\n\n"
        return formatted

    def _normalize_arxiv_id(self, value):
        if not value:
            return ""
        text = str(value).strip()
        if text.startswith("http"):
            parts = text.rstrip("/").split("/")
            if "abs" in parts:
                return parts[parts.index("abs") + 1]
            return parts[-1]
        if text.startswith("arxiv:"):
            return text.replace("arxiv:", "", 1)
        if text.startswith("abs:"):
            return text.replace("abs:", "", 1)
        return text
