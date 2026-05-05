"""
Friday NLP Enhancement - Advanced natural language processing.
Entity extraction, sentiment analysis, text summarization, and more.
"""
from __future__ import annotations

import os
import re
import json
from typing import Dict, List, Any, Optional, Tuple


# ─── Entity Extraction ────────────────────────────────────#

def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract named entities from text.
    Uses pattern matching + optional spaCy for advanced extraction.
    """
    entities = {
        "emails": [],
        "urls": [],
        "phone_numbers": [],
        "dates": [],
        "names": [],
        "locations": [],
        "organizations": [],
    }
    
    # Extract emails
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    entities["emails"] = re.findall(email_pattern, text)
    
    # Extract URLs
    url_pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
    entities["urls"] = re.findall(url_pattern, text)
    
    # Extract phone numbers (basic patterns)
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
    entities["phone_numbers"] = re.findall(phone_pattern, text)
    
    # Extract dates (basic patterns)
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',
        r'\d{4}-\d{1,2}-\d{1,2}',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
    ]
    for pattern in date_patterns:
        entities["dates"].extend(re.findall(pattern, text, re.IGNORECASE))
    
    # Try spaCy for advanced NER
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except IOError:
            return entities  # spaCy model not installed
        
        doc = nlp(text[:100000])  # Limit to prevent memory issues
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                entities["names"].append(ent.text)
            elif ent.label_ in ["GPE", "LOC"]:
                entities["locations"].append(ent.text)
            elif ent.label_ in ["ORG"]:
                entities["organizations"].append(ent.text)
    except ImportError:
        pass  # spaCy not installed
    
    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities


# ─── Text Summarization ────────────────────────────────────#

def summarize_text(text: str, max_sentences: int = 3) -> str:
    """
    Summarize text using extractive summarization.
    Uses frequency-based approach (TextRank-like).
    """
    if not text or len(text) < 100:
        return text
    
    try:
        from nltk.tokenize import sent_tokenize, word_tokenize
        from nltk.corpus import stopwords
        from nltk import download
        from collections import defaultdict
        import math
        
        # Download required NLTK data
        try:
            stopwords.words("english")
        except LookupError:
            download("stopwords", quiet=True)
            download("punkt", quiet=True)
        
        # Tokenize sentences and words
        sentences = sent_tokenize(text)
        if len(sentences) <= max_sentences:
            return text[:500]
        
        # Calculate word frequencies
        stop_words = set(stopwords.words("english"))
        word_freq = defaultdict(int)
        
        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            for word in words:
                if word not in stop_words and word.isalnum():
                    word_freq[word] += 1
        
        # Normalize frequencies
        max_freq = max(word_freq.values()) if word_freq else 1
        for word in word_freq:
            word_freq[word] = word_freq[word] / max_freq
        
        # Score sentences
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            words = word_tokenize(sentence.lower())
            score = sum(word_freq.get(w, 0) for w in words if w.isalnum())
            sentence_scores.append((i, score, sentence))
        
        # Get top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = sentence_scores[:max_sentences]
        top_sentences.sort(key=lambda x: x[0])  # Sort by original order
        
        summary = " ".join(s[2] for s in top_sentences)
        return summary[:1000]
        
    except ImportError:
        # Fallback: simple extract first N sentences
        sentences = re.split(r'[.!?]\s+', text)
        return " ".join(sentences[:max_sentences])[:500]
    except Exception as e:
        return f"Summarization error: {e}"


# ─── Sentiment Analysis ────────────────────────────────────#

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze sentiment of text.
    Returns polarity (-1 to 1) and subjectivity (0 to 1).
    """
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        from nltk import download
        
        try:
            analyzer = SentimentIntensityAnalyzer()
        except LookupError:
            download("vader_lexicon", quiet=True)
            analyzer = SentimentIntensityAnalyzer()
        
        scores = analyzer.polarity_scores(text)
        
        return {
            "positive": scores["pos"],
            "neutral": scores["neu"],
            "negative": scores["neg"],
            "compound": scores["compound"],
            "label": "positive" if scores["compound"] > 0.05 else 
                    "negative" if scores["compound"] < -0.05 else "neutral"
        }
        
    except ImportError:
        # Fallback: simple keyword-based
        positive_words = ["good", "great", "excellent", "happy", "love", "best", "amazing"]
        negative_words = ["bad", "terrible", "awful", "hate", "worst", "horrible"]
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return {"label": "neutral", "compound": 0.0}
        
        compound = (pos_count - neg_count) / total
        return {
            "positive": pos_count / total,
            "negative": neg_count / total,
            "neutral": 0.0,
            "compound": compound,
            "label": "positive" if compound > 0 else "negative" if compound < 0 else "neutral"
        }
    except Exception as e:
        return {"error": str(e)}


# ─── Keyword Extraction ────────────────────────────────────#

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract key phrases from text using TF-IDF-like approach.
    """
    try:
        from nltk.tokenize import word_tokenize
        from nltk.corpus import stopwords
        from collections import Counter
        import math
        
        # Tokenize and clean
        words = word_tokenize(text.lower())
        stop_words = set(stopwords.words("english"))
        
        # Filter: alphabetic, not stopword, length > 2
        filtered = [
            w for w in words 
            if w.isalpha() and w not in stop_words and len(w) > 2
        ]
        
        # Count frequencies
        word_counts = Counter(filtered)
        
        # Return top N
        return [word for word, count in word_counts.most_common(top_n)]
        
    except ImportError:
        # Fallback: simple word frequency
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        from collections import Counter
        return [w for w, c in Counter(words).most_common(top_n)]


# ─── Language Detection ────────────────────────────────────#

def detect_language(text: str) -> Dict[str, Any]:
    """
    Detect the language of text.
    Uses langdetect if available, otherwise basic heuristics.
    """
    try:
        from langdetect import detect, detect_langs
        lang = detect(text)
        langs = detect_langs(text)
        
        return {
            "language": lang,
            "confidence": max(l.prob for l in langs),
            "alternatives": [(l.lang, l.prob) for l in langs[:3]]
        }
    except ImportError:
        # Very basic heuristic
        if re.search(r'[а-яА-Я]', text):
            return {"language": "ru", "method": "heuristic"}
        elif re.search(r'[\u4e00-\u9fff]', text):
            return {"language": "zh", "method": "heuristic"}
        elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):
            return {"language": "ja", "method": "heuristic"}
        else:
            return {"language": "en", "method": "heuristic (default)"}
    except Exception as e:
        return {"error": str(e)}


# ─── Text Classification ────────────────────────────────────#

def classify_text(text: str, categories: List[str] = None) -> Dict[str, float]:
    """
    Classify text into categories.
    Uses keyword matching (can be enhanced with ML models).
    """
    if not categories:
        categories = [
            "technology", "sports", "politics", "business", 
            "entertainment", "science", "health", "education"
        ]
    
    # Keyword dictionaries
    category_keywords = {
        "technology": ["computer", "software", "hardware", "AI", "programming", "tech", "digital"],
        "sports": ["game", "team", "player", "score", "match", "tournament", "win", "lose"],
        "politics": ["government", "election", "president", "law", "policy", "vote", "congress"],
        "business": ["company", "market", "stock", "profit", "revenue", "CEO", "industry"],
        "entertainment": ["movie", "music", "actor", "film", "show", "TV", "celebrity"],
        "science": ["research", "study", "experiment", "discovery", "theory", "scientist"],
        "health": ["medical", "doctor", "hospital", "disease", "treatment", "health", "patient"],
        "education": ["school", "university", "student", "teacher", "learn", "education", "class"],
    }
    
    text_lower = text.lower()
    scores = {}
    
    for category in categories:
        keywords = category_keywords.get(category, [])
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        scores[category] = score / len(keywords) if keywords else 0
    
    # Normalize
    max_score = max(scores.values()) if scores else 1
    if max_score > 0:
        scores = {k: v / max_score for k, v in scores.items()}
    
    return scores


# ─── Tool Function for Friday ────────────────────────────────────#

def nlp_tool(
    action: str = "entities",
    text: str = None,
    target: str = None,  # Can be URL or file path
    max_sentences: int = 3,
    categories: str = None,  # JSON list
) -> str:
    """
    Friday tool for NLP operations.
    Actions: entities, summarize, sentiment, keywords, language, classify
    """
    if not text and not target:
        return "❌ Text or target (URL/file) required."
    
    # Get text from target if provided
    if not text and target:
        if target.startswith("http"):
            try:
                from web_scraper import simple_scrape
                text = simple_scrape(target)
            except:
                return f"❌ Could not fetch from {target}"
        elif os.path.exists(target):
            with open(target, 'r', encoding='utf-8') as f:
                text = f.read()
    
    if not text:
        return "❌ No text to process."
    
    if action == "entities":
        entities = extract_entities(text)
        lines = ["### ENTITIES EXTRACTED", ""]
        for key, values in entities.items():
            if values:
                lines.append(f"**{key.replace('_', ' ').title()}**: {len(values)}")
                for v in values[:5]:
                    lines.append(f"  - {v}")
                lines.append("")
        return "\n".join(lines)
    
    if action == "summarize":
        summary = summarize_text(text, max_sentences)
        return f"### SUMMARY\n\n{summary}"
    
    if action == "sentiment":
        result = analyze_sentiment(text)
        if "error" in result:
            return f"❌ {result['error']}"
        return f"""### SENTIMENT ANALYSIS
**Label**: {result['label'].upper()}
**Compound**: {result['compound']:.3f}
**Positive**: {result['positive']:.2%}
**Neutral**: {result['neutral']:.2%}
**Negative**: {result['negative']:.2%}"""
    
    if action == "keywords":
        keywords = extract_keywords(text)
        return f"### KEYWORDS\n" + ", ".join(keywords)
    
    if action == "language":
        result = detect_language(text)
        return f"""### LANGUAGE DETECTION
**Language**: {result.get('language', 'unknown')}
**Method**: {result.get('method', 'langdetect')}
**Confidence**: {result.get('confidence', 'N/A')}"""
    
    if action == "classify":
        cats = json.loads(categories) if categories else None
        scores = classify_text(text, cats)
        lines = ["### TEXT CLASSIFICATION", ""]
        for cat, score in sorted(scores.items(), key=lambda x: -x[1]):
            lines.append(f"**{cat.title()}**: {score:.2%}")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing NLP Enhancement...\n")
    
    test_text = """
    Apple Inc. announced a new product today. CEO Tim Cook revealed the latest iPhone 
    at their headquarters in Cupertino. This is great news for technology fans!
    Contact us at info@apple.com or visit https://apple.com for more details.
    The event was amazing and everyone was happy about the new features.
    """
    
    print("--- Entity Extraction ---")
    print(nlp_tool("entities", text=test_text))
    
    print("\n--- Summarization ---")
    print(nlp_tool("summarize", text=test_text * 5, max_sentences=2))
    
    print("\n--- Sentiment Analysis ---")
    print(nlp_tool("sentiment", text=test_text))
