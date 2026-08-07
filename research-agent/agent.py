import time
from everos_client import EverOSClient
from gemini_client import GeminiClient
from arxiv_client import ArxivClient
from snowflake_client import SnowflakeClient
import prompts

class ResearchMemoryAgent:
    def __init__(self):
        self.everos = EverOSClient()
        self.gemini = GeminiClient()
        self.arxiv = ArxivClient()
        self.snowflake = SnowflakeClient()

    def _estimate_cost(self, usage):
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        return (prompt_tokens * 0.000000075) + (completion_tokens * 0.00000030)

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
        baseline = self.run_query(query, user_id=user_id, enable_memory=False)
        memory = self.run_query(query, user_id=user_id, enable_memory=True)

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
