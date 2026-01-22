import logging
from dataclasses import dataclass

from textblob import TextBlob

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    score: float  # -1.0 to 1.0
    label: str  # 'positive' | 'negative' | 'neutral'


def analyze_sentiment(text: str) -> SentimentResult:
    """
    Analyze sentiment of text using TextBlob.

    Args:
        text: The text to analyze

    Returns:
        SentimentResult with score (-1 to 1) and label
    """
    if not text or not text.strip():
        return SentimentResult(score=0.0, label="neutral")

    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # -1 to 1

    # Classify into labels
    if polarity > 0.1:
        label = "positive"
    elif polarity < -0.1:
        label = "negative"
    else:
        label = "neutral"

    return SentimentResult(score=round(polarity, 4), label=label)
