import time
from everos_client import EverOSClient
from gemini_client import GeminiClient
from arxiv_client import ArxivClient
from snowflake_client import SnowflakeClient
import prompts

class ResearchAgent:
    def __init__(self):
        self.everos = EverOSClient()
        self.gemini = GeminiClient()
        self.arxiv = ArxivClient()
        self.snowflake = SnowflakeClient()

    def handle_query(self, user_query):
        start_time = time.time()
        
        # 1. Retrieve relevant memories from EverOS
        # This reduces token usage by only pulling what's needed
        memory_context = self.everos.search_related_memories(user_query)
        
        # 2. Search arXiv for fresh papers
        # (For the hackathon, we'll use the user query directly or refine it)
        papers = self.arxiv.search_papers(user_query)
        paper_context = self.arxiv.format_papers_for_prompt(papers)
        
        # 3. Build the personalized system prompt
        system_prompt = prompts.SYSTEM_PROMPT.format(
            memory_context=memory_context,
            paper_context=paper_context
        )
        
        # 4. Generate answer with Gemini
        answer, usage = self.gemini.generate_response(system_prompt, user_query)
        
        # 5. Store the turn in EverOS (Async background extraction)
        self.everos.add_turn(user_query, answer)
        
        # 6. Log metrics to Snowflake for "Token Economy" visualization
        latency = (time.time() - start_time) * 1000
        self.snowflake.log_usage(
            session_id=self.everos.session_id,
            query=user_query,
            tokens=usage,
            latency_ms=latency
        )
        
        return {
            "answer": answer,
            "papers": papers,
            "usage": usage,
            "latency": latency
        }
