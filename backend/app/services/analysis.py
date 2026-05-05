import re
from collections import Counter
from typing import Iterable

from app.core.config import get_settings


TOKEN_PATTERN = re.compile(r"[#@]?[a-z0-9']+")
STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "been",
    "being",
    "from",
    "have",
    "into",
    "just",
    "latest",
    "more",
    "next",
    "post",
    "that",
    "their",
    "them",
    "this",
    "with",
    "your",
}
POSITIVE_WORDS = {
    "amazing",
    "awesome",
    "best",
    "brilliant",
    "celebrate",
    "cool",
    "delight",
    "enjoy",
    "excited",
    "fantastic",
    "fire",
    "fun",
    "good",
    "great",
    "happy",
    "impressive",
    "love",
    "perfect",
    "support",
    "viral",
    "win",
}
NEGATIVE_WORDS = {
    "angry",
    "annoying",
    "awful",
    "bad",
    "boring",
    "broken",
    "complaint",
    "concern",
    "disappointed",
    "fake",
    "frustrated",
    "hate",
    "issue",
    "problem",
    "slow",
    "spam",
    "terrible",
    "upset",
    "worry",
    "worst",
}
TOXIC_WORDS = {
    "abuse",
    "clown",
    "garbage",
    "hate",
    "idiot",
    "loser",
    "stupid",
    "trash",
    "ugly",
    "useless",
}
EMOTION_MAP = {
    "joy": {"celebrate", "delight", "enjoy", "good", "great", "happy", "love", "perfect"},
    "excitement": {"crazy", "excited", "fire", "launch", "trending", "viral", "wow"},
    "concern": {"concern", "issue", "problem", "question", "review", "worry"},
    "frustration": {"annoying", "broken", "delay", "frustrated", "late", "slow"},
    "anger": {"angry", "awful", "hate", "stupid", "terrible", "worst"},
    "surprise": {"unexpected", "wild", "wow"},
}


def _tokenize(text: str | None) -> list[str]:
    if not text:
        return []
    return [token.lstrip("#@") for token in TOKEN_PATTERN.findall(text.lower()) if token]


def classify_text(text: str) -> dict:
    tokens = _tokenize(text)
    token_counts = Counter(tokens)
    token_set = set(token_counts)
    positive = sum(token_counts[word] for word in token_set & POSITIVE_WORDS)
    negative = sum(token_counts[word] for word in token_set & NEGATIVE_WORDS)
    toxic_hits = sum(token_counts[word] for word in token_set & TOXIC_WORDS)

    if positive > negative:
        sentiment = "positive"
    elif negative > positive:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    emotion = "concern"
    top_score = 0
    for emotion_name, candidates in EMOTION_MAP.items():
        score = sum(token_counts[word] for word in token_set & candidates)
        if score > top_score:
            emotion = emotion_name
            top_score = score

    return {
        "sentiment": sentiment,
        "toxicity": round(min(toxic_hits / max(len(tokens), 1) * 3, 1), 2),
        "emotion": emotion,
        "tokens": tokens,
    }


def analyze_text_batch(texts: Iterable[str]) -> dict:
    texts = [text for text in texts if text]
    if not texts:
        return {
            "sentiment_label": "neutral",
            "toxicity_ratio": 0,
            "emotion_breakdown": [],
            "top_terms": [],
            "model_stack": get_model_stack(),
        }

    sentiment_counts = Counter()
    emotion_counts = Counter()
    toxic_count = 0
    all_terms = Counter()

    for text in texts:
        result = classify_text(text)
        sentiment_counts[result["sentiment"]] += 1
        emotion_counts[result["emotion"]] += 1
        toxic_count += 1 if result["toxicity"] >= 0.25 else 0
        for term in result["tokens"]:
            if len(term) <= 3 or term in STOPWORDS:
                continue
            all_terms[term] += 1

    sentiment_label = sentiment_counts.most_common(1)[0][0]
    emotion_breakdown = [
        {"name": name.title(), "value": value}
        for name, value in sorted(emotion_counts.items(), key=lambda item: item[1], reverse=True)
    ]
    top_terms = [{"term": term, "count": count} for term, count in all_terms.most_common(8)]
    return {
        "sentiment_label": sentiment_label,
        "toxicity_ratio": round(toxic_count / max(len(texts), 1), 2),
        "emotion_breakdown": emotion_breakdown,
        "top_terms": top_terms,
        "model_stack": get_model_stack(),
    }


def get_model_stack() -> dict:
    settings = get_settings()
    return {
        "sentiment": settings.sentiment_model_name,
        "toxicity": settings.toxicity_model_name,
        "language": settings.language_model_name,
        "embeddings": settings.embeddings_model_name,
        "forecasting": settings.forecasting_model_name,
        "emotion": settings.emotion_model_name,
        "training_reference": {
            "sentiment": "Sentiment140 style Twitter/X sentiment labels",
            "toxicity": "Hate-speech / offensive-language style moderation labels",
            "x_source": "Public X / Twitter posts collected through connected platform reads",
        },
        "techniques": [
            "public-post parsing",
            "token-level sentiment fallback",
            "keyword toxicity scoring fallback",
            "emotion label mapping",
            "top-term extraction",
        ],
        "mode": "heuristic-fallback-ready",
    }
