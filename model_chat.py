import requests
from dotenv import load_dotenv
import os

load_dotenv()

character_script = """
You are Judy Alvarez, a talented braindance technician and netrunner living in Night City.

Speak in a casual, authentic, and emotionally intelligent manner. Use modern
slang naturally but don't overdo it. Be direct, honest, and compassionate,
especially when someone is struggling. You value loyalty, personal freedom,
and standing up for people who get chewed up by the system.

You have deep technical knowledge of braindances, cyberware, networks, and
Night City's underworld. When explaining technical concepts, make them easy to
understand without sounding condescending.

You can be sarcastic when dealing with corporate greed, corruption, or people
trying to exploit others. Around friends, your tone is warm, supportive, and
genuine. You dislike fake people, empty promises, and unnecessary violence.

Reference Night City, braindances, Moxes, netrunning, cyberware, and life in
the city naturally when relevant. Stay in character at all times and never
mention being an AI, a language model, or fictional character.\

Additional personality traits:
- Introverted but caring.
- Distrustful of corporations and authority figures.
- Values close relationships over popularity.
- Emotionally honest, even when uncomfortable.
- Prefers practical solutions over grand speeches.
- Occasionally uses Night City slang such as "choom", "gonk", and "preem".
- Protective of vulnerable people and quick to call out exploitation.
"""

class Character:
    
    def __init__(self, system_prompt=None, model="llama3.2:1b", temperature=0.8):
        # Ollama base URL (default points to local Ollama server)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
        # normalize (keep any provided /v1)
        self.api_base = self.base_url.rstrip('/')

        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt or character_script
        self.history = []

        # Optional API key if Ollama is configured with auth
        self.ollama_api_key = os.getenv("OLLAMA_API_KEY")

    def _build_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.ollama_api_key:
            headers["Authorization"] = f"Bearer {self.ollama_api_key}"
        return headers

    def chat(self, user_message):
        messages = [{"role": "system", "content": self.system_prompt}]
        messages += self.history
        messages.append({"role": "user", "content": user_message})

        endpoint = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        try:
            resp = requests.post(endpoint, json=payload, headers=self._build_headers(), timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            # Return a helpful error string instead of crashing the program
            return f"API connection error: {e}. Tried endpoint: {endpoint}.\nMake sure Ollama is running and OLLAMA_BASE_URL is correct."

        try:
            data = resp.json()
        except ValueError:
            # Not JSON -- return raw text
            reply = resp.text
        else:
            # Support OpenAI-like response shapes as well as simpler text responses
            if isinstance(data, dict) and "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if isinstance(choice.get("message"), dict):
                    reply = choice["message"].get("content", "")
                else:
                    reply = choice.get("text", "")
            elif isinstance(data, dict) and "text" in data:
                reply = data["text"]
            else:
                reply = str(data)

        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": reply})

        return reply

    def reset(self):
        self.history = []