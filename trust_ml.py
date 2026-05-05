"""Trust Tier Machine Learning for Friday."""

import json
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

class TrustML:
    """Machine Learning for dynamic trust tier evolution."""
    
    def __init__(self):
        self.interaction_features = []
        self.trust_scores = defaultdict(float)
        self.learning_rate = 0.01
        self.feature_weights = {
            'request_complexity': 0.3,
            'success_rate': 0.4,
            'time_of_day': 0.1,
            'sentiment': 0.2
        }
    
    def extract_features(self, interaction: Dict[str, Any]) -> Dict[str, float]:
        """Extract features from an interaction."""
        features = {}
        
        # Request complexity (0-1)
        command = interaction.get('command', '')
        complexity = min(1.0, len(command.split()) / 20)
        features['request_complexity'] = complexity
        
        # Success rate (0-1)
        history = interaction.get('history', [])
        if history:
            successes = sum(1 for h in history if h.get('success'))
            features['success_rate'] = successes / len(history)
        else:
            features['success_rate'] = 0.5
        
        # Time of day feature (0-1, where 0.5 is midday)
        hour = time.localtime().tm_hour
        features['time_of_day'] = abs(hour - 12) / 12
        
        # Sentiment (0-1, where 1 is positive)
        sentiment = interaction.get('sentiment', 'neutral')
        features['sentiment'] = {'positive': 1.0, 'neutral': 0.5, 'negative': 0.0}.get(sentiment, 0.5)
        
        return features
    
    def predict_trust_score(self, user: str, features: Dict[str, float]) -> float:
        """Predict trust score for a user based on features."""
        base_score = self.trust_scores.get(user, 0.5)
        
        # Weighted feature contribution
        contrib = 0.0
        for name, value in features.items():
            weight = self.feature_weights.get(name, 0.1)
            contrib += weight * value
        
        # Update score with learning rate
        new_score = base_score + self.learning_rate * (contrib - base_score)
        self.trust_scores[user] = new_score
        return new_score
    
    def update_trust_tier(self, user: str, score: float) -> str:
        """Update trust tier based on score."""
        if score >= 0.8:
            return "trusted"
        elif score >= 0.6:
            return "familiar"
        elif score >= 0.4:
            return "known"
        else:
            return "new"
    
    def learn_from_interaction(self, user: str, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Learn from a new interaction and update trust."""
        # Extract features
        features = self.extract_features(interaction)
        
        # Predict current trust score
        score = self.predict_trust_score(user, features)
        
        # Update tier
        tier = self.update_trust_tier(user, score)
        
        # Store interaction
        self.interaction_features.append({
            'user': user,
            'features': features,
            'score': score,
            'tier': tier,
            'timestamp': time.time()
        })
        
        return {
            'user': user,
            'trust_score': score,
            'trust_tier': tier,
            'features': features
        }
    
    def get_user_profile(self, user: str) -> Dict[str, Any]:
        """Get ML-enhanced user profile."""
        score = self.trust_scores.get(user, 0.5)
        tier = self.update_trust_tier(user, score)
        
        # Get interaction history
        user_interactions = [i for i in self.interaction_features if i['user'] == user]
        
        return {
            'user': user,
            'trust_score': score,
            'trust_tier': tier,
            'interaction_count': len(user_interactions),
            'feature_weights': self.feature_weights,
            'last_updated': time.time()
        }
    
    def adjust_weights(self, feedback: Dict[str, float]):
        """Adjust feature weights based on feedback."""
        for feature, adjustment in feedback.items():
            if feature in self.feature_weights:
                self.feature_weights[feature] = max(0.0, min(1.0, self.feature_weights[feature] + adjustment))


# Global instance
trust_ml = TrustML()


def learn_trust(user: str, command: str, success: bool = True, sentiment: str = "neutral") -> str:
    """Learn from an interaction to update trust ML model."""
    interaction = {
        'command': command,
        'history': [{'success': success}],
        'sentiment': sentiment
    }
    result = trust_ml.learn_from_interaction(user, interaction)
    return json.dumps(result, indent=2)


def get_trust_profile(user: str) -> str:
    """Get ML-enhanced trust profile for a user."""
    profile = trust_ml.get_user_profile(user)
    return json.dumps(profile, indent=2)


def adjust_trust_weights(feedback_json: str) -> str:
    """Adjust trust ML weights based on feedback.
    
    Example feedback_json: {"request_complexity": 0.05, "success_rate": -0.02}
    """
    try:
        feedback = json.loads(feedback_json)
        trust_ml.adjust_weights(feedback)
        return "Weights adjusted successfully"
    except Exception as e:
        return f"Error adjusting weights: {e}"
