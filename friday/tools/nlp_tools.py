"""
NLP & ML tools
Libraries: spacy, nltk, textblob, sentence-transformers, gensim, transformers
"""
import asyncio
import json
from typing import Any

HAS_SPACY = False
HAS_NLTK = False
HAS_TEXTBLOB = False
HAS_SENTENCE_TF = False
HAS_GENSIM = False
HAS_TRANSFORMERS = False
try:
    import spacy
    HAS_SPACY = True
except ImportError:
    pass
try:
    import nltk
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    HAS_NLTK = True
except ImportError:
    pass
try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    pass
try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TF = True
except ImportError:
    pass
try:
    from gensim.summarization import summarize
    HAS_GENSIM = True
except ImportError:
    pass
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    pass


async def sentiment_analysis(text: str) -> dict[str, Any]:
    if HAS_TEXTBLOB:
        try:
            blob = TextBlob(text)
            return {"polarity": blob.sentiment.polarity, "subjectivity": blob.sentiment.subjectivity,
                    "sentiment": "positive" if blob.sentiment.polarity > 0 else "negative" if blob.sentiment.polarity < 0 else "neutral"}
        except Exception as e:
            return {"error": str(e)}
    if HAS_TRANSFORMERS:
        try:
            classifier = await asyncio.get_event_loop().run_in_executor(None, lambda: pipeline("sentiment-analysis"))
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: classifier(text[:512]))
            return {"label": result[0]["label"], "score": result[0]["score"], "engine": "transformers"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "textblob or transformers not installed"}


async def extract_entities(text: str) -> dict[str, Any]:
    if HAS_SPACY:
        try:
            nlp = await asyncio.get_event_loop().run_in_executor(None, lambda: spacy.load("en_core_web_sm"))
            doc = await asyncio.get_event_loop().run_in_executor(None, lambda: nlp(text[:100000]))
            entities = [{"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char} for ent in doc.ents]
            return {"entities": entities, "count": len(entities), "engine": "spacy"}
        except Exception as e:
            return {"error": str(e)}
    if HAS_NLTK:
        try:
            tokens = word_tokenize(text)
            tagged = nltk.pos_tag(tokens)
            chunks = nltk.ne_chunk(tagged)
            entities = []
            for chunk in chunks:
                if hasattr(chunk, "label"):
                    entities.append({"text": " ".join(c[0] for c in chunk), "label": chunk.label()})
            return {"entities": entities, "count": len(entities), "engine": "nltk"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "spacy or nltk not installed"}


async def summarize_text(text: str, ratio: float = 0.3) -> dict[str, Any]:
    if HAS_GENSIM:
        try:
            summary = await asyncio.get_event_loop().run_in_executor(None, lambda: summarize(text, ratio=ratio))
            return {"summary": summary, "original_length": len(text), "summary_length": len(summary), "engine": "gensim"}
        except Exception as e:
            return {"error": str(e)}
    if HAS_TRANSFORMERS:
        try:
            summarizer = await asyncio.get_event_loop().run_in_executor(None, lambda: pipeline("summarization"))
            result = await asyncio.get_event_loop().run_in_executor(None, lambda: summarizer(text[:1024], max_length=150, min_length=30))
            return {"summary": result[0]["summary_text"], "engine": "transformers"}
        except Exception as e:
            return {"error": str(e)}
    # Simple extractive fallback
    sentences = text.split(".")
    mid = max(1, len(sentences) // 2)
    summary = ". ".join(sentences[:mid])
    return {"summary": summary, "engine": "simple", "note": "gensim or transformers for better results"}


async def tokenize_text(text: str, engine: str = "nltk") -> dict[str, Any]:
    words = []
    sentences = []
    if engine == "nltk" and HAS_NLTK:
        try:
            words = word_tokenize(text)
            sentences = sent_tokenize(text)
        except Exception:
            pass
    elif HAS_SPACY:
        try:
            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text[:50000])
            words = [t.text for t in doc]
            sentences = [s.text for s in doc.sents]
        except Exception:
            pass
    else:
        words = text.split()
        sentences = text.split(".")
    return {"words": len(words), "sentences": len(sentences), "unique_words": len(set(w.lower() for w in words)),
            "sample_words": words[:50], "sample_sentences": [s.strip() for s in sentences[:10] if s.strip()]}


async def compute_embeddings(texts: list[str]) -> dict[str, Any]:
    if not HAS_SENTENCE_TF:
        return {"error": "sentence-transformers not installed"}
    try:
        model = await asyncio.get_event_loop().run_in_executor(None, lambda: SentenceTransformer("all-MiniLM-L6-v2"))
        embeddings = await asyncio.get_event_loop().run_in_executor(None, lambda: model.encode(texts).tolist())
        return {"embeddings": embeddings, "dimensions": len(embeddings[0]) if embeddings else 0, "count": len(embeddings)}
    except Exception as e:
        return {"error": str(e)}


async def classify_text(text: str, labels: list[str] | None = None) -> dict[str, Any]:
    if not HAS_TRANSFORMERS:
        return {"error": "transformers not installed"}
    try:
        classifier = await asyncio.get_event_loop().run_in_executor(None, lambda: pipeline("zero-shot-classification"))
        labels = labels or ["technology", "sports", "politics", "entertainment", "science", "business", "health"]
        result = await asyncio.get_event_loop().run_in_executor(None, lambda: classifier(text[:512], labels))
        return {"text": text[:100], "labels": result["labels"], "scores": [float(s) for s in result["scores"]],
                "top_label": result["labels"][0], "top_score": float(result["scores"][0])}
    except Exception as e:
        return {"error": str(e)}
