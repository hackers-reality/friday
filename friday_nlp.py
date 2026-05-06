"""
Friday NLP - Natural Language Processing.
Text analysis, sentiment analysis, NER, summarization, translation.
"""
from __future__ import annotations

import os
import sys
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


# ─── Text Analysis ────────────────────────────#

class TextAnalyzer:
    """Analyze text using various NLP techniques."""
    
    def __init__(self):
        self.nltk_available = self._check_nltk()
        self.spacy_available = self._check_spacy()
        
    def _check_nltk(self) -> bool:
        try:
            import nltk
            self.nltk = nltk
            return True
        except ImportError:
            return False
    
    def _check_spacy(self) -> bool:
        try:
            import spacy
            self.spacy = spacy
            return True
        except ImportError:
            return False
    
    def analyze_basic(self, text: str) -> Dict[str, Any]:
        """Basic text analysis without external libraries."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        word_count = len(words)
        sentence_count = len(sentences)
        avg_word_length = sum(len(w) for w in words) / max(len(words), 1)
        avg_sentence_length = word_count / max(sentence_count, 1)
        
        # Simple readability (Flesch-Kincaid simplified)
        score = 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_word_length / 4.5
        score = max(0, min(100, score))
        
        if score >= 70:
            readability = "Easy"
        elif score >= 50:
            readability = "Medium"
        else:
            readability = "Difficult"
        
        return {
            "success": True,
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2),
            "readability_score": round(score, 2),
            "readability_level": readability,
        }
    
    def tokenize(self, text: str) -> Dict[str, Any]:
        """Tokenize text."""
        if self.nltk_available:
            try:
                from nltk.tokenize import word_tokenize
                tokens = word_tokenize(text)
                return {
                    "success": True,
                    "tokens": tokens,
                    "count": len(tokens),
                    "method": "nltk",
                }
            except:
                pass
        
        # Fallback: simple split
        tokens = re.findall(r'\b\w+\b', text)
        return {
            "success": True,
            "tokens": tokens,
            "count": len(tokens),
            "method": "regex",
        }
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities (simplified)."""
        # Simple regex-based NER
        entities = []
        
        # Dates
        date_pattern = r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
        for match in re.finditer(date_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "DATE",
                "start": match.start(),
                "end": match.end(),
            })
        
        # Emails
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for match in re.finditer(email_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "EMAIL",
                "start": match.start(),
                "end": match.end(),
            })
        
        # URLs
        url_pattern = r'https?://[^\s]+'
        for match in re.finditer(url_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "URL",
                "start": match.start(),
                "end": match.end(),
            })
        
        # Capitalized words (potential names/orgs)
        cap_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        for match in re.finditer(cap_pattern, text):
            entities.append({
                "text": match.group(),
                "label": "ENTITY",
                "start": match.start(),
                "end": match.end(),
            })
        
        return {
            "success": True,
            "entities": entities,
            "count": len(entities),
        }


# ─── Sentiment Analysis ────────────────────────────#

class SentimentAnalyzer:
    """Sentiment analysis (simplified)."""
    
    # Simple word lists for sentiment
    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "happy", "joy", "love", "like", "best", "awesome", "brilliant",
        "positive", "perfect", "superb", "outstanding", "incredible",
    }
    
    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "poor", "worst",
        "hate", "dislike", "sad", "angry", "negative", "disgusting",
        "failure", "wrong", "broken", "useless",
    }
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        words = re.findall(r'\b\w+\b', text.lower())
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        
        total = positive_count + negative_count
        
        if total == 0:
            sentiment = "neutral"
            score = 0.0
        elif positive_count > negative_count:
            sentiment = "positive"
            score = positive_count / total
        else:
            sentiment = "negative"
            score = negative_count / total
        
        return {
            "success": True,
            "sentiment": sentiment,
            "score": round(score, 2),
            "positive_words": positive_count,
            "negative_words": negative_count,
            "total_words": len(words),
        }
    
    def analyze_advanced(self, text: str) -> Dict[str, Any]:
        """Advanced sentiment (uses NLTK if available)."""
        if TextAnalyzer().nltk_available:
            try:
                from nltk.sentiment import SentimentIntensityAnalyzer
                analyzer = SentimentIntensityAnalyzer()
                scores = analyzer.polarity_scores(text)
                
                if scores["compound"] >= 0.05:
                    sentiment = "positive"
                elif scores["compound"] <= -0.05:
                    sentiment = "negative"
                else:
                    sentiment = "neutral"
                
                return {
                    "success": True,
                    "sentiment": sentiment,
                    "compound": scores["compound"],
                    "positive": scores["pos"],
                    "neutral": scores["neu"],
                    "negative": scores["neg"],
                    "method": "vader",
                }
            except:
                pass
        
        # Fallback to simple
        return self.analyze(text)


# ─── Text Summarization ────────────────────────────#

class TextSummarizer:
    """Summarize text (simplified)."""
    
    def summarize(self, text: str, num_sentences: int = 3) -> Dict[str, Any]:
        """Summarize text by extracting key sentences."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= num_sentences:
            return {
                "success": True,
                "summary": text,
                "method": "none_needed",
                "sentence_count": len(sentences),
            }
        
        # Score sentences by word frequency
        word_freq = {}
        words = re.findall(r'\b\w+\b', text.lower())
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Score each sentence
        sentence_scores = []
        for i, sentence in enumerate(sentences):
            score = 0
            sent_words = re.findall(r'\b\w+\b', sentence.lower())
            for word in sent_words:
                score += word_freq.get(word, 0)
            sentence_scores.append((i, score, sentence))
        
        # Get top sentences
        top_sentences = sorted(sentence_scores, key=lambda x: x[1], reverse=True)[:num_sentences]
        top_sentences = sorted(top_sentences, key=lambda x: x[0])  # Sort by original order
        
        summary = " ".join(s[2] for s in top_sentences)
        
        return {
            "success": True,
            "summary": summary,
            "method": "frequency",
            "original_sentences": len(sentences),
            "summary_sentences": len(top_sentences),
        }


# ─── Language Detection ────────────────────────────#

class LanguageDetector:
    """Detect language of text (simplified)."""
    
    def __init__(self):
        # Simple character-based detection
        self.language_patterns = {
            "en": r'[a-zA-Z\s\.,!?\'"]+',
            "es": r'[a-zA-Záéíóúñ¿¡\s\.,!?]+',
            "fr": r'[a-zA-Zàâçéèêëîïôùûüÿ\s\.,!?]+',
            "de": r'[a-zA-Zäöüß\s\.,!?]+',
            "it": r'[a-zA-Zàèéìòù\s\.,!?]+',
            "pt": r'[a-zA-Záâãçéêíóôõú\s\.,!?]+',
            "ru": r'[а-яА-Я\s\.,!?]+',
            "zh": r'[\u4e00-\u9fff\s\.,!?]+',
            "ja": r'[\u3040-\u30ff\u4e00-\u9fff\s\.,!?]+',
            "ar": r'[\u0600-\u06ff\s\.,!?]+',
        }
    
    def detect(self, text: str) -> Dict[str, Any]:
        """Detect language of text."""
        scores = {}
        
        for lang, pattern in self.language_patterns.items():
            matches = re.findall(pattern, text)
            score = sum(len(m) for m in matches)
            if score > 0:
                scores[lang] = score
        
        if not scores:
            return {
                "success": True,
                "language": "unknown",
                "confidence": 0.0,
            }
        
        # Get best match
        best_lang = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[best_lang] / total
        
        return {
            "success": True,
            "language": best_lang,
            "confidence": round(confidence, 2),
            "scores": scores,
        }


# ─── Keyword Extraction ────────────────────────────#

class KeywordExtractor:
    """Extract keywords from text."""
    
    def extract(self, text: str, num_keywords: int = 5) -> Dict[str, Any]:
        """Extract keywords using TF-IDF (simplified)."""
        words = re.findall(r'\b\w{3,}\b', text.lower())
        
        # Remove stop words (simple list)
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "shall", "can", "need", "dare",
        }
        
        filtered = [w for w in words if w not in stop_words]
        
        # Count frequencies
        word_freq = {}
        for word in filtered:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        keywords = [{"word": w, "count": c} for w, c in sorted_words[:num_keywords]]
        
        return {
            "success": True,
            "keywords": keywords,
            "total_words": len(words),
            "unique_words": len(word_freq),
        }


# ─── NLP Tool for Friday ────────────────────────────#

def nlp_tool(
    action: str = "status",
    text: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for NLP operations.
    Actions: status, analyze, tokenize, entities, sentiment,
            summarize, language, keywords
    """
    params = params or {}
    
    if action == "status":
        analyzer = TextAnalyzer()
        lines = ["### NLP STATUS", ""]
        lines.append(f"**NLTK Available**: {'✅' if analyzer.nltk_available else '❌'}")
        lines.append(f"**spaCy Available**: {'✅' if analyzer.spacy_available else '❌'}")
        lines.append("")
        lines.append("**Available Features**:")
        lines.append("  - Text analysis (readability, stats)")
        lines.append("  - Tokenization")
        lines.append("  - Named Entity Recognition (simplified)")
        lines.append("  - Sentiment analysis")
        lines.append("  - Text summarization")
        lines.append("  - Language detection")
        lines.append("  - Keyword extraction")
        return "\n".join(lines)
    
    if action == "analyze":
        if not text:
            return "❌ Text required."
        analyzer = TextAnalyzer()
        result = analyzer.analyze_basic(text)
        if result["success"]:
            return f"""### TEXT ANALYSIS
**Words**: {result['word_count']}
**Sentences**: {result['sentence_count']}
**Avg Word Length**: {result['avg_word_length']}
**Avg Sentence Length**: {result['avg_sentence_length']}
**Readability**: {result['readability_level']} ({result['readability_score']})"""
        else:
            return f"❌ Analysis error: {result.get('error', 'Unknown')}"
    
    if action == "tokenize":
        if not text:
            return "❌ Text required."
        analyzer = TextAnalyzer()
        result = analyzer.tokenize(text)
        if result["success"]:
            preview = ", ".join(result["tokens"][:20])
            return f"### TOKENIZATION\n\n**Tokens** ({result['count']}): {preview}..."
        else:
            return f"❌ Tokenization error: {result.get('error', 'Unknown')}"
    
    if action == "entities":
        if not text:
            return "❌ Text required."
        analyzer = TextAnalyzer()
        result = analyzer.extract_entities(text)
        if result["success"]:
            lines = [f"### NAMED ENTITIES ({result['count']})", ""]
            for entity in result["entities"][:10]:
                lines.append(f"  - {entity['text']} ({entity['label']})")
            return "\n".join(lines)
        else:
            return f"❌ NER error: {result.get('error', 'Unknown')}"
    
    if action == "sentiment":
        if not text:
            return "❌ Text required."
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(text)
        if result["success"]:
            return f"""### SENTIMENT ANALYSIS
**Sentiment**: {result['sentiment'].upper()}
**Score**: {result['score']}
**Positive Words**: {result['positive_words']}
**Negative Words**: {result['negative_words']}"""
        else:
            return f"❌ Sentiment error: {result.get('error', 'Unknown')}"
    
    if action == "summarize":
        if not text:
            return "❌ Text required."
        num_sentences = params.get("num_sentences", 3)
        summarizer = TextSummarizer()
        result = summarizer.summarize(text, num_sentences)
        if result["success"]:
            return f"""### SUMMARIZATION
**Original Sentences**: {result['original_sentences']}
**Summary Sentences**: {result['summary_sentences']}

**Summary**:
{result['summary']}"""
        else:
            return f"❌ Summarization error: {result.get('error', 'Unknown')}"
    
    if action == "language":
        if not text:
            return "❌ Text required."
        detector = LanguageDetector()
        result = detector.detect(text)
        if result["success"]:
            return f"""### LANGUAGE DETECTION
**Language**: {result['language']}
**Confidence**: {result['confidence']}"""
        else:
            return f"❌ Detection error: {result.get('error', 'Unknown')}"
    
    if action == "keywords":
        if not text:
            return "❌ Text required."
        num_keywords = params.get("num_keywords", 5)
        extractor = KeywordExtractor()
        result = extractor.extract(text, num_keywords)
        if result["success"]:
            lines = [f"### KEYWORDS ({result['total_words']} words, {result['unique_words']} unique)", ""]
            for kw in result["keywords"]:
                lines.append(f"  - {kw['word']}: {kw['count']} occurrences")
            return "\n".join(lines)
        else:
            return f"❌ Keyword extraction error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday NLP...\n")
    
    # Test text analysis
    print("--- Text Analysis ---")
    print(nlp_tool("analyze", text="This is a great example! It works wonderfully and is amazing."))
    
    # Test sentiment
    print("\n--- Sentiment ---")
    print(nlp_tool("sentiment", text="I love this product. It is absolutely fantastic!"))
