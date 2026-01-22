import logging
from dataclasses import dataclass

from LeIA import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# Global analyzer instance (loaded once)
_sentiment_analyzer = None


def get_sentiment_analyzer():
    """Get or load the sentiment analyzer (singleton pattern)."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        logger.info("Loading LeIA sentiment analyzer (Portuguese lexicon-based)")
        _sentiment_analyzer = SentimentIntensityAnalyzer()
        logger.info("Sentiment analyzer loaded successfully")
    return _sentiment_analyzer


@dataclass
class SentimentResult:
    score: float  # -1.0 to 1.0
    label: str  # 'positive' | 'negative' | 'neutral'


def analyze_sentiment(text: str) -> SentimentResult:
    """
    Analyze sentiment of text using LeIA (Portuguese lexicon-based).

    LeIA is a Portuguese adaptation of VADER sentiment analysis.

    Args:
        text: The text to analyze

    Returns:
        SentimentResult with score (-1 to 1) and label
    """
    if not text or not text.strip():
        return SentimentResult(score=0.0, label="neutral")

    analyzer = get_sentiment_analyzer()
    scores = analyzer.polarity_scores(text)

    # LeIA returns: {'neg': 0.0, 'neu': 0.5, 'pos': 0.5, 'compound': 0.5}
    # compound is the normalized score from -1 to 1
    compound = scores["compound"]

    # Classify based on compound score (VADER thresholds)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return SentimentResult(score=round(compound, 4), label=label)
