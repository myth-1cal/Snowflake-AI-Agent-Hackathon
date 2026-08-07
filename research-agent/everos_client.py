import os
from everos_cloud import EverOS
from dotenv import load_dotenv

load_dotenv()

class EverOSClient:
    def __init__(self):
        api_key = os.getenv("EVEROS_API_KEY")
        self.client = EverOS(api_key=api_key)
        self.user_id = os.getenv("USER_ID", "default_user")
        self.session_id = os.getenv("SESSION_ID", "default_session")

    def add_turn(self, user_text, assistant_text):
        """Adds a conversation turn to EverOS memory."""
        messages = [
            {"sender_id": self.user_id, "role": "user", "content": user_text},
            {"sender_id": "assistant", "role": "assistant", "content": assistant_text}
        ]
        return self.client.add(session_id=self.session_id, messages=messages)

    def search_related_memories(self, query, top_k=5):
        """Searches for relevant past episodes and facts."""
        hits = self.client.search(
            query=query, 
            user_id=self.user_id, 
            method="hybrid", 
            top_k=top_k,
            include_profile=True
        )
        
        context_parts = []
        
        # Add profile info if available (background, preferences)
        if hits.profiles:
            profile_str = str(hits.profiles[0].get('profile_data', {}))
            context_parts.append(f"User Profile & Preferences: {profile_str}")
            
        # Add episodic summaries
        if hits.episodes:
            episodes_str = "\n".join([f"- {e.episode}" for e in hits.episodes])
            context_parts.append(f"Past Relevant Discussions:\n{episodes_str}")
            
        return "\n\n".join(context_parts)

    def flush(self):
        """Forces extraction of memories from current session."""
        return self.client.flush(self.session_id)
