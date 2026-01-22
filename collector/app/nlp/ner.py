import logging
from dataclasses import dataclass

import spacy

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_nlp_model = None


def get_ner_model():
    """Get or load the spaCy NER model (singleton pattern)."""
    global _nlp_model
    if _nlp_model is None:
        logger.info("Loading spaCy model: pt_core_news_sm (Portuguese)")
        _nlp_model = spacy.load("pt_core_news_sm")
        logger.info("spaCy model loaded successfully")
    return _nlp_model


@dataclass
class EntityResult:
    text: str  # Original text as found
    normalized_text: str  # Lowercase normalized text
    entity_type: str  # PERSON, ORG, GPE, PRODUCT, etc.
    start_pos: int
    end_pos: int
    confidence: float  # spaCy doesn't provide confidence, so we use 1.0


# Entity types from pt_core_news_sm (Portuguese model)
# Note: Portuguese model uses different labels than English models
RELEVANT_ENTITY_TYPES = {
    "PER",   # People (Portuguese model uses PER, not PERSON)
    "ORG",   # Companies, agencies, institutions
    "LOC",   # Locations (includes cities, countries, places - GPE equivalent)
    "MISC",  # Miscellaneous (products, works of art, events, etc.)
}


def extract_entities(text: str) -> list[EntityResult]:
    """
    Extract named entities from text using spaCy.

    Args:
        text: The text to analyze

    Returns:
        List of EntityResult objects
    """
    if not text or not text.strip():
        return []

    nlp = get_ner_model()
    doc = nlp(text)

    entities = []
    for ent in doc.ents:
        # Filter to relevant entity types
        if ent.label_ not in RELEVANT_ENTITY_TYPES:
            continue

        # Skip very short entities (likely noise)
        if len(ent.text.strip()) < 2:
            continue

        entities.append(
            EntityResult(
                text=ent.text,
                normalized_text=ent.text.lower().strip(),
                entity_type=ent.label_,
                start_pos=ent.start_char,
                end_pos=ent.end_char,
                confidence=1.0,  # spaCy doesn't provide confidence scores
            )
        )

    return entities
