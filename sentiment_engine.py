import os
import csv
from datetime import datetime, timezone

import torch
from transformers import AutoTokenizer
from transformers import AutoModelForSequenceClassification
from scipy.special import softmax

MODEL = "cardiffnlp/twitter-roberta-base-sentiment"

# Where sentiment history is logged. Override with the SENTIMENT_LOG_PATH env
# var if you want it written somewhere else (e.g. a shared volume).
LOG_PATH = os.environ.get("SENTIMENT_LOG_PATH", "sentiment_log.csv")
LOG_FIELDS = ["timestamp", "character_id", "text", "label", "negative", "neutral", "positive"]


class SentimentAnalysis:
    def __init__(self):
        """
        Initialize the sentiment analysis model and tokenizer.

        Responsibilities:
        - Load the pretrained tokenizer and sentiment classification model.
        - Detect whether a CUDA-enabled GPU is available.
        - Move the model to the appropriate device (GPU or CPU).
        - Initialize instance variables used throughout the sentiment pipeline.

        Attributes Created:
        - MODEL (str): Hugging Face model identifier.
        - tokenizer: Tokenizer used to preprocess text.
        - model: Pretrained sentiment classification model.
        - device (str): Execution device ('cuda' or 'cpu').
        - text (str | None): Stores the most recently analyzed text.
        """
        self.MODEL = MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL)
        self.text = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self._ensure_log_file()

    def _ensure_log_file(self):
        """Create the log file with a header row if it doesn't exist yet."""
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                writer.writeheader()

    def _log(self, text, scores_dict, label, character_id):
        """Append one tracked sentiment record to the CSV log."""
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "character_id": character_id or "",
            "text": text,
            "label": label,
            "negative": float(scores_dict["negative"]),
            "neutral": float(scores_dict["neutral"]),
            "positive": float(scores_dict["positive"]),
        }
        try:
            with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
                writer.writerow(row)
        except Exception as e:
            print(f"[sentiment_engine] failed to write log: {e}")

    def user_text(self, text: str, character_id: str = None):
        """
        Analyze user-provided text for sentiment.

        Parameters:
        - text (str):
            The input text to be evaluated.
        - character_id (str, optional):
            Which character the message was sent to, for logging.

        Side Effects:
        - Stores the text in self.text.
        - Executes the sentiment analysis pipeline by calling
            polarity_scores().

        Returns:
        - None
        """
        self.text = text
        self.polarity_scores(text, character_id=character_id)

    def polarity_scores(self, text: str, character_id: str = None):
        """
        Compute sentiment probabilities for the supplied text and log the result.

        Process:
        1. Tokenize the input text.
        2. Move tokenized tensors to the configured device.
        3. Perform model inference without gradient tracking.
        4. Convert model logits into probabilities using softmax.
        5. Classify the dominant sentiment.
        6. Append the result to the sentiment log (see LOG_PATH).
        7. Return all sentiment probabilities.

        Parameters:
        - text (str):
            Text to analyze.
        - character_id (str, optional):
            Which character the message was sent to, for logging.

        Returns:
        - dict:
            Dictionary containing sentiment probabilities:
            {
                'negative': float,
                'neutral': float,
                'positive': float
            }

        Notes:
        - Probability values range from 0 to 1.
        - The probabilities sum to approximately 1.
        """
        encode_text = self.tokenizer(text, return_tensors="pt")
        encode_text = {k: v.to(self.device) for k, v in encode_text.items()}
        with torch.no_grad():
            output = self.model(**encode_text)
        scores = output.logits[0].cpu().numpy()
        scores = softmax(scores)
        scores_dict = {
            "negative": float(scores[0]),
            "neutral": float(scores[1]),
            "positive": float(scores[2]),
        }
        label = self.classify(scores_dict)
        self._log(text, scores_dict, label, character_id)
        return scores_dict

    def classify(self, scores: dict):
        """
        Determine the sentiment label with the highest probability.

        Parameters:
        - scores (dict):
            Dictionary containing sentiment probabilities produced
            by polarity_scores().

        Returns:
        - str: the predicted sentiment label ('negative', 'neutral', or 'positive').
        """
        predicted_emotion = max(scores, key=scores.get)
        return predicted_emotion