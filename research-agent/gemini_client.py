import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        # Using 1.5 Flash for speed and cost-efficiency (free tier)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def generate_response(self, system_prompt, user_prompt):
        """Generates a response using the Gemini model."""
        full_prompt = f"{system_prompt}\n\nUser: {user_prompt}"
        response = self.model.generate_content(full_prompt)
        
        # Logic to extract token usage (Gemini returns this in metadata)
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total_tokens": response.usage_metadata.total_token_count
        }
        
        return response.text, usage
