#!/usr/bin/env python3
"""
API server for the Streamlit chat app (app.py).

Receives a chat message + character id, generates a reply via model_chat.Character
(backed by Ollama), runs sentiment analysis on the user's message via
sentiment_engine.SentimentAnalysis, and returns both in one JSON response.

Usage:
  python main.py

Endpoints:
  GET  /api/characters
      -> {"characters": [{id, name, tagline, color, avatarInitial, description}, ...]}

  POST /api/chat
      body: {"characterId": "<key in CHARACTERS>", "message": "..."}
      -> {"reply": "...", "sentiment": {"label": "...", "scores": {...}}}
"""

import os
import logging

from flask import Flask, request, jsonify

from characters import CHARACTERS
from model_chat import Character
from sentiment_engine import SentimentAnalysis

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# The sentiment model is heavy to load, so load it once at startup and reuse it.
_sentiment = SentimentAnalysis()

# Character chat sessions, keyed by characterId, so conversation history persists
# across requests within the life of the server process.
_chat_sessions = {}


def _get_character(character_id):
    if character_id not in _chat_sessions:
        _chat_sessions[character_id] = Character(character_id)
    return _chat_sessions[character_id]


def _character_card(character_id, meta):
    name = meta.get("name", character_id)
    prompt = meta.get("prompt", "")
    tagline = next((line.strip() for line in prompt.splitlines() if line.strip()), "")
    color = "#" + format(abs(hash(character_id)) % (256 ** 3), "06x")
    return {
        "id": character_id,
        "name": name,
        "tagline": tagline,
        "color": color,
        "avatarInitial": name[0].upper() if name else character_id[:1].upper(),
        "description": prompt.strip()[:240],
    }


@app.route("/api/characters", methods=["GET"])
def characters_endpoint():
    cards = [_character_card(key, meta) for key, meta in CHARACTERS.items()]
    return jsonify({"characters": cards})


@app.route("/api/chat", methods=["POST"])
def chat_endpoint():
    data = request.get_json(force=True, silent=True) or {}

    character_id = data.get("characterId")
    message = data.get("message", "").strip()

    if not character_id:
        return jsonify({"error": "characterId is required"}), 400
    if character_id not in CHARACTERS:
        return jsonify({"error": f"Unknown characterId '{character_id}'"}), 400
    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        character = _get_character(character_id)
        reply = character.chat(message)
    except Exception:
        app.logger.exception("Model chat failed for character '%s'", character_id)
        return jsonify({"error": "Model error"}), 500

    try:
        scores = _sentiment.polarity_scores(message, character_id=character_id)
        label = max(scores, key=scores.get)
    except Exception:
        app.logger.exception("Sentiment analysis failed")
        scores, label = {"negative": 0.0, "neutral": 1.0, "positive": 0.0}, "neutral"

    return jsonify({
        "reply": reply,
        "sentiment": {"label": label, "scores": scores},
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.logger.info("Starting chat API on http://0.0.0.0:%s", port)
    app.run(host="0.0.0.0", port=port)