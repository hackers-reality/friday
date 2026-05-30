"""
NLP Pipeline for Memory Knowledge Graph - entity extraction, concept analysis,
sentiment detection, and semantic similarity using spaCy + sentence-transformers.
"""

from __future__ import annotations
import re
from typing import Any

# Lazy imports - these are heavy and only needed when the pipeline is actually used
_SPACY_MODEL = "en_core_web_sm"


class Entity:
    """Represents an extracted entity from text."""
    def __init__(self, text: str, label: str, start: int, end: int):
        self.text = text
        self.label = label  # PERSON, ORG, GPE, PRODUCT, EVENT, WORK_OF_ART, etc.
        self.start = start
        self.end = end

    def to_dict(self) -> dict:
        return {"text": self.text, "label": self.label, "start": self.start, "end": self.end}


class NLPPipeline:
    """NLP pipeline for entity/concept extraction, sentiment, and semantic similarity."""

    def __init__(self):
        self._nlp = None
        self._embedder = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        try:
            import spacy
            self._nlp = spacy.load(_SPACY_MODEL)
        except (ImportError, OSError):
            self._nlp = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            self._embedder = None

        self._loaded = True

    def extract_entities(self, text: str) -> list[dict]:
        self._ensure_loaded()
        if not self._nlp or not text.strip():
            return []

        doc = self._nlp(text)
        entities = []
        seen = set()
        for ent in doc.ents:
            key = (ent.text.lower(), ent.label_)
            if key not in seen:
                seen.add(key)
                entities.append(Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                ).to_dict())
        return entities

    def extract_concepts(self, text: str) -> list[str]:
        self._ensure_loaded()
        if not self._nlp or not text.strip():
            return []

        doc = self._nlp(text)
        concepts = set()

        # Noun chunks as concepts
        for chunk in doc.noun_chunks:
            word = chunk.text.strip().lower()
            if len(word) > 2 and not word.isspace():
                concepts.add(word)

        # Key lemmatized nouns
        for token in doc:
            if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 2:
                concepts.add(token.lemma_.lower())

        # Filter stopwords
        stopwords = {"the", "a", "an", "this", "that", "these", "those", "i", "you", "it", "we", "they", "he", "she"}
        return [c for c in concepts if c not in stopwords][:20]

    def get_sentiment(self, text: str) -> str:
        if not text.strip():
            return "neutral"
        try:
            from textblob import TextBlob
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            if polarity > 0.1:
                return "positive"
            elif polarity < -0.1:
                return "negative"
            return "neutral"
        except ImportError:
            # Fallback: simple keyword-based
            positive = {"good", "great", "awesome", "love", "excellent", "amazing", "happy", "wonderful", "best", "fantastic"}
            negative = {"bad", "terrible", "awful", "hate", "horrible", "worst", "sad", "angry", "ugly", "disgusting"}
            words = set(text.lower().split())
            if words & positive:
                return "positive"
            if words & negative:
                return "negative"
            return "neutral"

    def semantic_similarity(self, text_a: str, text_b: str) -> float:
        self._ensure_loaded()
        if not self._embedder:
            return 0.0
        emb = self._embedder.encode([text_a, text_b])
        import numpy as np
        sim = np.dot(emb[0], emb[1]) / (np.linalg.norm(emb[0]) * np.linalg.norm(emb[1]) + 1e-8)
        return float(sim)

    def classify_concept_type(self, concept: str) -> str:
        keywords = {
            "music": {"music", "song", "spotify", "playlist", "album", "artist", "genre", "rock", "pop", "jazz"},
            "tech": {"code", "python", "javascript", "programming", "computer", "software", "app", "api", "github", "ai", "data", "algorithm"},
            "food": {"food", "eat", "restaurant", "cafe", "cuisine", "pizza", "burger", "coffee", "pasta"},
            "location": {"pune", "mumbai", "delhi", "city", "place", "home", "office", "area", "street", "road", "india"},
            "people": {"friend", "family", "boss", "colleague", "team", "person", "people"},
            "projects": {"project", "feature", "build", "create", "design", "task", "goal"},
        }
        cl = concept.lower()
        for category, words in keywords.items():
            if cl in words or any(w in cl for w in words):
                return category
        # Use spaCy NER if available
        self._ensure_loaded()
        if self._nlp:
            doc = self._nlp(cl)
            for ent in doc.ents:
                if ent.label_ == "GPE":
                    return "location"
                if ent.label_ == "PERSON":
                    return "people"
        return "general"

    def extract_temporal(self, text: str) -> list[str]:
        self._ensure_loaded()
        if not self._nlp or not text.strip():
            return []

        doc = self._nlp(text)
        temporals = []
        for ent in doc.ents:
            if ent.label_ in ("TIME", "DATE"):
                temporals.append(ent.text)

        # Also detect relative temporals
        relative_patterns = [
            r"\b(today|yesterday|tomorrow)\b",
            r"\b(this\s+(morning|afternoon|evening|week|month))\b",
            r"\b(last\s+(night|week|month|year))\b",
            r"\b(next\s+(week|month|year))\b",
        ]
        for pattern in relative_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                if isinstance(m, tuple):
                    temporals.append(" ".join(m))
                else:
                    temporals.append(m)

        return list(set(temporals))

    def extract_action_verbs(self, text: str) -> list[str]:
        self._ensure_loaded()
        if not self._nlp or not text.strip():
            return []

        doc = self._nlp(text)
        verbs = set()
        for token in doc:
            if token.pos_ == "VERB":
                verbs.add(token.lemma_.lower())
        return list(verbs)

    def get_dependency_triples(self, text: str) -> list[dict]:
        """Extract subject-verb-object triples from dependency parse."""
        self._ensure_loaded()
        if not self._nlp or not text.strip():
            return []

        doc = self._nlp(text)
        triples = []

        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                subj = None
                obj = None
                for child in token.children:
                    if child.dep_ in ("nsubj", "nsubjpass"):
                        subj = child.text
                    elif child.dep_ in ("dobj", "pobj", "attr"):
                        obj = child.text
                if subj and obj:
                    triples.append({
                        "subject": subj,
                        "verb": token.lemma_,
                        "object": obj,
                    })

        return triples
