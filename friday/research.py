"""Autonomous Research Optimization for Friday."""

import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

class AutonomousResearch:
    """Optimizes research process with autonomous decision-making."""
    
    def __init__(self):
        self.search_history = []
        self.source_cache = {}
        self.quality_threshold = 0.6  # Minimum quality score for sources
    
    def analyze_topic(self, topic: str) -> Dict[str, Any]:
        """Analyze a topic to determine research strategy."""
        # Extract key concepts
        words = re.findall(r'\b\w+\b', topic.lower())
        key_concepts = [w for w in words if len(w) > 3][:5]
        
        # Determine research depth based on topic complexity
        complexity = self._assess_complexity(topic)
        suggested_depth = min(5, max(2, complexity))
        
        return {
            'key_concepts': key_concepts,
            'complexity_score': complexity,
            'suggested_depth': suggested_depth,
            'search_queries': self._generate_queries(topic, key_concepts),
            'expected_sources': suggested_depth * 5
        }
    
    def _assess_complexity(self, topic: str) -> int:
        """Assess topic complexity (1-5)."""
        score = 1
        # Technical terms increase complexity
        tech_terms = ['algorithm', 'architecture', 'framework', 'implementation', 'optimization']
        for term in tech_terms:
            if term in topic.lower():
                score += 1
        # Multiple concepts increase complexity
        concepts = len(re.findall(r'\b\w+\b', topic))
        if concepts > 5:
            score += 1
        return min(5, score)
    
    def _generate_queries(self, topic: str, concepts: List[str]) -> List[str]:
        """Generate optimized search queries."""
        queries = [topic]
        if concepts:
            queries.append(f"{topic} tutorial")
            queries.append(f"{topic} examples")
            queries.append(f"{' '.join(concepts[:3])} best practices")
        return queries[:5]
    
    def evaluate_source(self, url: str, content: str) -> float:
        """Evaluate source quality (0.0 - 1.0)."""
        if url in self.source_cache:
            return self.source_cache[url]
        
        score = 0.0
        # Length check
        if len(content) > 1000:
            score += 0.3
        # Key concept presence
        words = set(re.findall(r'\b\w+\b', content.lower()))
        topic_words = set(re.findall(r'\b\w+\b', url.lower()))
        overlap = len(words.intersection(topic_words)) / max(len(topic_words), 1)
        score += overlap * 0.4
        # Has code/examples
        if '```' in content or '<code>' in content:
            score += 0.3
        
        score = min(1.0, score)
        self.source_cache[url] = score
        return score
    
    def synthesize_findings(self, sources: List[Dict], topic: str) -> str:
        """Autonomously synthesize research findings."""
        if not sources:
            return "No sources to synthesize"
        
        # Sort by quality
        sorted_sources = sorted(sources, key=lambda x: x.get('quality', 0), reverse=True)
        
        # Build synthesis
        synthesis = f"# Research Synthesis: {topic}\n\n"
        synthesis += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        synthesis += f"**Sources analyzed:** {len(sources)}\n\n"
        synthesis += "---\n\n"
        
        # Key findings
        synthesis += "## Key Findings\n\n"
        for i, source in enumerate(sorted_sources[:5], 1):
            synthesis += f"{i}. {source.get('title', 'Untitled')}\n"
            synthesis += f"   - Quality: {source.get('quality', 0):.2f}\n"
            synthesis += f"   - URL: {source.get('url', 'N/A')}\n\n"
        
        # Recommendations
        synthesis += "## Recommendations\n\n"
        synthesis += self._generate_recommendations(sorted_sources, topic)
        
        return synthesis
    
    def _generate_recommendations(self, sources: List[Dict], topic: str) -> str:
        """Generate actionable recommendations."""
        if not sources:
            return "No recommendations available."
        
        recs = []
        recs.append(f"1. Start with {sources[0].get('title', 'top source')} for foundational knowledge.")
        if len(sources) > 3:
            recs.append(f"2. Explore {len(sources)} sources for comprehensive understanding.")
        recs.append(f"3. Consider practical implementation after reviewing theoretical sources.")
        return "\n".join(recs)
    
    def optimize_research(self, topic: str, depth: int = 3) -> Dict[str, Any]:
        """Optimize research strategy for a topic."""
        analysis = self.analyze_topic(topic)
        
        strategy = {
            'topic': topic,
            'depth': max(depth, analysis['suggested_depth']),
            'queries': analysis['search_queries'],
            'expected_sources': analysis['expected_sources'],
            'key_concepts': analysis['key_concepts'],
            'quality_threshold': self.quality_threshold
        }
        
        return strategy


# Global instance
researcher = AutonomousResearch()


def optimize_research(topic: str, depth: int = 3) -> str:
    """Optimize research strategy for a topic."""
    strategy = researcher.optimize_research(topic, depth)
    return json.dumps(strategy, indent=2)


def analyze_topic(topic: str) -> str:
    """Analyze a topic for research planning."""
    analysis = researcher.analyze_topic(topic)
    return json.dumps(analysis, indent=2)


def synthesize_research(sources_json: str) -> str:
    """Synthesize research findings from sources JSON."""
    try:
        sources = json.loads(sources_json)
        return researcher.synthesize_findings(sources, "research topic")
    except Exception as e:
        return f"Error synthesizing: {e}"
