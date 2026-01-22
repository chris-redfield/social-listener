#!/usr/bin/env python3
"""Test what entity labels spaCy Portuguese model actually uses."""
import spacy

nlp = spacy.load("pt_core_news_sm")

# Test with sample Portuguese text
test_texts = [
    "Lula e Bolsonaro discutiram sobre o Brasil em Brasília.",
    "A Netflix lançou uma nova série sobre São Paulo.",
    "O presidente visitou a Petrobras no Rio de Janeiro.",
]

print("Entity labels found by pt_core_news_sm:")
print("=" * 50)

all_labels = set()
for text in test_texts:
    doc = nlp(text)
    print(f"\nText: {text}")
    for ent in doc.ents:
        print(f"  '{ent.text}' -> {ent.label_}")
        all_labels.add(ent.label_)

print("\n" + "=" * 50)
print(f"All unique labels found: {all_labels}")
print("\nModel's available labels:")
print(nlp.get_pipe("ner").labels)
