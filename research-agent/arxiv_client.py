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
                "published": result.published.strftime("%Y-%m-%d")
            })
        return papers

    def format_papers_for_prompt(self, papers):
        """Formats paper list into a string for the LLM."""
        formatted = ""
        for i, p in enumerate(papers):
            formatted += f"Paper {i+1}: {p['title']}\n"
            formatted += f"Authors: {', '.join(p['authors'])}\n"
            formatted += f"Summary: {p['summary']}\n\n"
        return formatted
