import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise ValueError("GOOGLE_API_KEY is missing or still set to a placeholder value.")

        genai.configure(api_key=api_key)
        self.model_names = ["gemini-3.5-flash"]
        self.model = None

        for model_name in self.model_names:
            try:
                self.model = genai.GenerativeModel(model_name)
                break
            except Exception:
                continue

        if self.model is None:
            raise RuntimeError("Unable to initialize a Gemini model with the configured API key.")

    def generate_response(self, system_prompt, user_prompt):
        """Generates a response using the Gemini model."""
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}"

        last_error = None
        for model_name in self.model_names:
            try:
                response = self.model.generate_content(full_prompt)
                usage_metadata = getattr(response, "usage_metadata", None)
                usage = {
                    "prompt_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
                    "completion_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
                    "total_tokens": getattr(usage_metadata, "total_token_count", 0) or 0,
                }
                return response.text, usage
            except Exception as exc:
                last_error = exc
                if "404" in str(exc) or "not found" in str(exc).lower() or "unsupported" in str(exc).lower():
                    continue
                raise

        raise RuntimeError(f"Gemini request failed: {last_error}")
