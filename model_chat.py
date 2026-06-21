import os
from ollama import Client

_host_env = (
    os.getenv("OLLAMA_HOST")
    or os.getenv("OLLAMA_BASE_URL")
    or "http://127.0.0.1:11434"
)

if _host_env.endswith("/v1"):
    _host_env = _host_env[:-3]

client = Client(host=_host_env)

from characters import CHARACTERS
from typing import Optional

# Lazy sentiment loader to avoid heavy initialization at import time
_sentiment = None

def _get_sentiment():
    global _sentiment
    if _sentiment is None:
        try:
            from sentiment_engine import SentimentAnalysis
            _sentiment = SentimentAnalysis()
        except Exception:
            _sentiment = None
    return _sentiment


class Character:
    def __init__(
        self,
        character_name,
        model="llama3.2:1b",
        temperature=0.8,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        if character_name not in CHARACTERS:
            raise ValueError(
                f"Unknown character '{character_name}'. "
                f"Available: {list(CHARACTERS.keys())}"
            )

        self.character_name = character_name
        self.system_prompt = CHARACTERS[character_name]["prompt"]

        self.model = model
        self.temperature = temperature
        self.history = []
        self.session_id = session_id
        self.user_id = user_id
        # empathy_bias accumulates recent negative signals to nudge tone
        self.empathy_bias = 0.0

    def chat(self, user_message, session_id: Optional[str] = None, user_id: Optional[str] = None):
        # prefer explicit args, fall back to instance values
        session_id = session_id or self.session_id
        user_id = user_id or self.user_id

        # run sentiment analysis if available and update empathy bias
        sentiment = _get_sentiment()
        try:
            if sentiment is not None and isinstance(user_message, str):
                scores = sentiment.polarity_scores(user_message, character_id=session_id or self.character_name)
                # delta positive->negative; increase bias when negative outweighs positive
                delta = scores.get("negative", 0.0) - scores.get("positive", 0.0)
                # scaled update; small positive drift when negative dominates
                self.empathy_bias = min(1.0, max(0.0, self.empathy_bias + (delta * 0.5)))
        except Exception:
            # sentiment model failed — continue without it
            pass

        # assemble messages. If empathy_bias is high, add an extra system instruction
        messages = []
        if self.empathy_bias > 0.25:
            empathy_instruction = (
                "Prioritize empathic, validating, and emotionally-attuned responses. "
                "Reflect the user's feelings, acknowledge distress, offer grounding and small next steps, "
                "and avoid technical jargon or overly playful tone until the user signals they're ready."
            )
            messages.append({"role": "system", "content": empathy_instruction})

        # core persona prompt
        messages.append({"role": "system", "content": self.system_prompt})

        # include prior conversation history so context persists
        messages.extend(self.history)

        # append user's message
        messages.append({"role": "user", "content": user_message})

        response = client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": self.temperature
            }
        )

        reply = response.get("message", {}).get("content", "")

        # persist the exchange for future context
        self.history.extend([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": reply},
        ])

        # also persist session/user info on the instance for future calls
        if session_id:
            self.session_id = session_id
        if user_id:
            self.user_id = user_id

        return reply

    def reset(self):
        self.history.clear()
        self.empathy_bias = 0.0