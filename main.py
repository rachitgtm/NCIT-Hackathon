#!/usr/bin/env python3
"""
Simple API server that receives chat messages from the website, runs sentiment
analysis (using sentiment_engine.py if available), optionally forwards the
sentiment record to a Django endpoint, and returns a model reply.

Usage:
  python main.py

The web frontend (website/javascript/style.js) sends POST http://localhost:5000/api/chat
with JSON: { therapist: "Dr. X", message: "..." }

If you have a Django endpoint to store sentiments, set environment variable
DJANGO_SAVE_URL to that endpoint (e.g. http://localhost:8000/api/sentiment/).
"""

import os
import time
import json
import logging
from datetime import datetime

from flask import Flask, request, jsonify, make_response

# Try to import the project's sentiment engine; fall back to a simple rule-based
# estimator if heavy dependencies are not available.
try:
    from sentiment_engine import SentimentAnalysis
    _SENTIMENT_AVAILABLE = True
except Exception as e:
    SentimentAnalysis = None
    _SENTIMENT_AVAILABLE = False
    logging.warning("Sentiment engine import failed: %s", e)

# Optional requests for saving to Django
try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    requests = None
    _REQUESTS_AVAILABLE = False

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

_sentiment = None

# Expose characters from characters.py for the frontend (mindspace app)
try:
    from characters import CHARACTERS as _CHARACTERS
except Exception:
    _CHARACTERS = {}


def _character_card_from(name_key, meta):
    # meta expected to contain at least 'name' and 'prompt'
    display_name = meta.get('name') if isinstance(meta, dict) else str(name_key)
    prompt = meta.get('prompt') if isinstance(meta, dict) else ''
    avatar_initial = display_name[0] if display_name else name_key[0:1]
    # choose a deterministic color based on hash of name_key
    color = "#" + format(abs(hash(name_key)) % (256**3), '06x')
    # find first non-empty line for a short tagline
    tagline = ''
    if prompt:
        for line in prompt.split('\n'):
            clean = line.strip()
            if clean:
                tagline = clean
                break
    description = (prompt.strip()[:240]) if prompt else ''
    return {
        'id': name_key,
        'name': display_name,
        'tagline': tagline,
        'color': color,
        'avatarInitial': avatar_initial.upper(),
        'description': description,
    }


@app.route('/api/characters', methods=['GET'])
def characters_endpoint():
    # Return list shaped for the mindspace frontend
    cards = []
    for k, v in (_CHARACTERS or {}).items():
        try:
            cards.append(_character_card_from(k, v))
        except Exception:
            continue
    resp = jsonify({'characters': cards})
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp


def get_sentiment():
    global _sentiment
    if _sentiment is None:
        if _SENTIMENT_AVAILABLE and SentimentAnalysis is not None:
            app.logger.info("Loading SentimentAnalysis model (this may take a while)...")
            _sentiment = SentimentAnalysis()
        else:
            app.logger.info("Using lightweight fallback sentiment analyzer")
            _sentiment = None
    return _sentiment


def fallback_sentiment(text: str):
    # Very small heuristic: count positive / negative keywords
    negative_words = ["sad", "depress", "unhappy", "miserable", "suicid", "panic", "hopeless", "anx", "overwhelmed", "overwhelm", "worthless"]
    positive_words = ["happy", "good", "better", "great", "ok", "okay", "relieved", "safe", "fine"]
    t = text.lower()
    neg = sum(t.count(w) for w in negative_words)
    pos = sum(t.count(w) for w in positive_words)
    total = pos + neg
    if total == 0:
        # neutral baseline
        scores = {"negative": 0.1, "neutral": 0.8, "positive": 0.1}
    else:
        neg_score = neg / total
        pos_score = pos / total
        neu_score = max(0.0, 1.0 - neg_score - pos_score)
        scores = {"negative": round(neg_score, 3), "neutral": round(neu_score, 3), "positive": round(pos_score, 3)}
    label = max(scores, key=scores.get)
    return scores, label


def build_reply(therapist: str, label: str, scores: dict, message: str) -> str:
    # Simple templated replies — replace with model-based responses later.
    therapist_fragment = f" {therapist}" if therapist else ""
    neg = scores.get("negative", 0)
    pos = scores.get("positive", 0)
    neu = scores.get("neutral", 0)

    if label == "negative" or neg >= 0.55:
        return (f"I'm sorry you're having a hard time.{therapist_fragment} "
                "If you're in immediate danger, please reach out to local emergency services. "
                "Otherwise, try to take a few slow breaths — would you like a few grounding tips or to book a session? ")
    if label == "neutral" and neu >= 0.6:
        return (f"Thanks for sharing. {therapist_fragment} can help explore this further — "
                "would you like to tell me a bit more or book a session? ")
    # positive or default
    return (f"Thanks for sharing — it's good to hear some hopeful things. {therapist_fragment} "
            "If you'd like, you can continue talking here or book a session for deeper support.")


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat_endpoint():
    # Basic CORS support for local dev
    if request.method == "OPTIONS":
        resp = make_response()
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return resp

    data = request.get_json(force=True, silent=True) or {}

    # If caller provided a characterId, proxy to model_chat.Character and stream the model reply
    character_id = data.get("characterId") or data.get("characterId")
    user_message = data.get("message") or data.get("text") or ""

    if character_id:
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        try:
            from model_chat import Character
            char = Character(character_id)
            # Generate full reply (model_chat currently returns full text)
            reply = char.chat(user_message)
        except Exception as e:
            app.logger.exception("Model chat failed: %s", e)
            return jsonify({"error": "Model error", "detail": str(e)}), 500

        # Stream the reply in small chunks so frontend can render progressively
        def generate():
            chunk_size = 64
            for i in range(0, len(reply), chunk_size):
                yield reply[i : i + chunk_size]
                time.sleep(0.01)
        from flask import Response
        return Response(generate(), mimetype="text/plain", headers={"Access-Control-Allow-Origin": "*"})

    # Fallback behavior: sentiment + templated reply (keeps old API for the website quick chat)
    therapist = data.get("therapist") or data.get("therapist_name") or ""
    message = user_message
    user = data.get("user") or data.get("user_id") or None

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Analyze sentiment
    engine = get_sentiment()
    try:
        if engine is not None:
            scores = engine.polarity_scores(message)
            label = max(scores, key=scores.get)
        else:
            scores, label = fallback_sentiment(message)
    except Exception as e:
        app.logger.exception("Sentiment analysis failed: %s", e)
        scores, label = fallback_sentiment(message)

    reply = build_reply(therapist, label, scores, message)

    # Attempt to save to Django endpoint if configured
    django_url = os.environ.get("DJANGO_SAVE_URL")
    if django_url:
        payload = {
            "therapist": therapist,
            "user": user,
            "message": message,
            "sentiment": scores,
            "label": label,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        try:
            if _REQUESTS_AVAILABLE and requests is not None:
                r = requests.post(django_url, json=payload, timeout=5)
                app.logger.info("Saved sentiment to Django, status=%s", r.status_code)
            else:
                import urllib.request
                req = urllib.request.Request(django_url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    app.logger.info("Saved sentiment to Django, status=%s", resp.status)
        except Exception as e:
            app.logger.warning("Failed to save to Django endpoint %s: %s", django_url, e)

    response = {"reply": reply, "label": label, "scores": scores}
    resp = jsonify(response)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


if __name__ == "__main__":
    # Run development server on port 5000
    port = int(os.environ.get("PORT", 5000))
    app.logger.info("Starting chat API on http://0.0.0.0:%s", port)
    # When sentiment engine loads it may print/log for a while; run normally.
    app.run(host="0.0.0.0", port=port, debug=True)
