import os
from everos_cloud import EverOS
from dotenv import load_dotenv

load_dotenv()

class EverOSClient:
    def __init__(self):
        api_key = os.getenv("EVEROS_API_KEY")
        self.client = EverOS(api_key=api_key)
        self.default_user_id = os.getenv("USER_ID", "default_user")
        self.session_id = os.getenv("SESSION_ID", "default_session")

    def add_turn(self, user_id, user_text, assistant_text):
        """Adds a conversation turn to EverOS memory."""
        messages = [
            {"sender_id": user_id or self.default_user_id, "role": "user", "content": user_text},
            {"sender_id": "assistant", "role": "assistant", "content": assistant_text}
        ]
        return self.client.add(session_id=self.session_id, messages=messages)

    def add_memory(self, user_id, memory_text):
        """Stores a concise memory fact in EverOS."""
        messages = [
            {"sender_id": user_id or self.default_user_id, "role": "user", "content": f"MEMORY: {memory_text}"}
        ]
        return self.client.add(session_id=self.session_id, messages=messages)

    def search_related_memories(self, query, user_id=None, top_k=3):
        """Searches for relevant past episodes and facts."""
        hits = self.client.search(
            query=query,
            user_id=user_id or self.default_user_id,
            method="hybrid",
            top_k=top_k,
            include_profile=True
        )

        context_parts = []

        profiles = getattr(hits, "profiles", None) or []
        if profiles:
            first_profile = profiles[0]
            if isinstance(first_profile, dict):
                profile_data = first_profile.get("profile_data", {})
            else:
                profile_data = getattr(first_profile, "profile_data", None)
                if profile_data is None and hasattr(first_profile, "__dict__"):
                    profile_data = getattr(first_profile, "__dict__", {})
            context_parts.append(f"User Profile & Preferences: {profile_data}")

        episodes = getattr(hits, "episodes", None) or []
        if episodes:
            episode_lines = []
            for episode in episodes:
                if isinstance(episode, dict):
                    episode_text = episode.get("episode") or episode.get("text") or str(episode)
                else:
                    episode_text = getattr(episode, "episode", None) or getattr(episode, "text", None) or str(episode)
                episode_lines.append(f"- {episode_text}")
            context_parts.append(f"Past Relevant Discussions:\n{'\n'.join(episode_lines)}")

        return "\n\n".join(context_parts)

    def flush(self):
        """Forces extraction of memories from current session."""
        return self.client.flush(self.session_id)
