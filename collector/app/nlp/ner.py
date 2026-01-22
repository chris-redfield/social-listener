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
        logger.info("Loading spaCy model: en_core_web_sm")
        _nlp_model = spacy.load("en_core_web_sm")
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


# Entity types we care about for social media monitoring
RELEVANT_ENTITY_TYPES = {
    "PERSON",  # People, including fictional
    "ORG",  # Companies, agencies, institutions
    "GPE",  # Countries, cities, states (Geo-Political Entity)
    "PRODUCT",  # Objects, vehicles, foods, etc.
    "EVENT",  # Named events
    "WORK_OF_ART",  # Titles of books, songs, etc.
    "LOC",  # Non-GPE locations
    "FAC",  # Buildings, airports, highways, etc.
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
