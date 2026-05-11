"""
Friday Reinforcement Learning - Self-improving from interactions.
Learns from successes/failures to improve future responses.
"""
from __future__ import annotations

import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# ─── Experience ───────────────────────────────────#

class Experience:
    """A single experience (state, action, reward, next_state)."""
    
    def __init__(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        context: Dict[str, Any] = None
    ):
        self.state = state
        self.action = action
        self.reward = reward
        self.next_state = next_state
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "next_state": self.next_state,
            "context": self.context,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        return cls(
            data["state"],
            data["action"],
            data["reward"],
            data["next_state"],
            data.get("context"),
        )


# ─── Q-Learning Agent ───────────────────────────────────#

class QLearningAgent:
    """Q-Learning agent for learning optimal actions."""
    
    def __init__(self, learning_rate: float = 0.1, discount: float = 0.95, epsilon: float = 0.1):
        self.lr = learning_rate
        self.discount = discount
        self.epsilon = epsilon  # Exploration rate
        self.q_table: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
    def get_state_key(self, state: str) -> str:
        """Convert state to a hashable key."""
        # Simple: use first 100 chars
        return state[:100].lower().replace(" ", "_")
    
    def choose_action(self, state: str, available_actions: List[str]) -> str:
        """Choose an action using epsilon-greedy policy."""
        state_key = self.get_state_key(state)
        
        # Exploration
        if np.random.random() < self.epsilon:
            return np.random.choice(available_actions)
        
        # Exploitation
        q_values = self.q_table[state_key]
        if not q_values:
            return np.random.choice(available_actions)
        
        # Get best action
        best_action = max(available_actions, key=lambda a: q_values.get(a, 0.0))
        return best_action
    
    def learn(self, experience: Experience):
        """Update Q-value based on experience."""
        state_key = self.get_state_key(experience.state)
        next_state_key = self.get_state_key(experience.next_state)
        
        # Current Q-value
        current_q = self.q_table[state_key][experience.action]
        
        # Max Q-value for next state
        next_q_values = self.q_table[next_state_key]
        max_next_q = max(next_q_values.values()) if next_q_values else 0.0
        
        # Q-learning update
        new_q = current_q + self.lr * (
            experience.reward + self.discount * max_next_q - current_q
        )
        
        self.q_table[state_key][experience.action] = new_q
    
    def get_best_action(self, state: str, available_actions: List[str]) -> Tuple[str, float]:
        """Get best action and its Q-value."""
        state_key = self.get_state_key(state)
        q_values = self.q_table[state_key]
        
        best_action = max(available_actions, key=lambda a: q_values.get(a, 0.0))
        best_q = q_values.get(best_action, 0.0)
        
        return best_action, best_q
    
    def save(self, path: str):
        """Save Q-table to file."""
        data = {s: dict(a) for s, a in self.q_table.items()}
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path: str):
        """Load Q-table from file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.q_table = defaultdict(
                lambda: defaultdict(float),
                {s: defaultdict(float, a) for s, a in data.items()}
            )
        except FileNotFoundError:
            pass


# ─── Policy Gradient Agent (REINFORCE) ───────────────────────────────────#

class PolicyGradientAgent:
    """Policy Gradient agent using REINFORCE algorithm."""
    
    def __init__(self, learning_rate: float = 0.01):
        self.lr = learning_rate
        self.policy: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.episode_data: List[Experience] = []
        
    def get_state_key(self, state: str) -> str:
        return state[:100].lower().replace(" ", "_")
    
    def get_policy_prob(self, state: str, action: str) -> float:
        """Get probability of action given state."""
        state_key = self.get_state_key(state)
        logits = self.policy[state_key]
        
        if not logits:
            return 1.0 / max(len(logits), 1)
        
        # Softmax
        max_logit = max(logits.values())
        exp_logits = {a: np.exp(v - max_logit) for a, v in logits.items()}
        total = sum(exp_logits.values())
        
        return exp_logits.get(action, 0.0) / total if total > 0 else 0.0
    
    def choose_action(self, state: str, available_actions: List[str]) -> str:
        """Choose action based on policy probabilities."""
        state_key = self.get_state_key(state)
        
        # Initialize if needed
        if state_key not in self.policy:
            for action in available_actions:
                self.policy[state_key][action] = 0.0
        
        # Get probabilities
        probs = []
        for action in available_actions:
            prob = self.get_policy_prob(state_key, action)
            if prob == 0:
                prob = 0.01  # Small probability
            probs.append(prob)
        
        # Normalize
        total = sum(probs)
        probs = [p / total for p in probs]
        
        return np.random.choice(available_actions, p=probs)
    
    def record_episode(self, experiences: List[Experience]):
        """Record an episode for learning."""
        self.episode_data.extend(experiences)
    
    def update_policy(self):
        """Update policy using REINFORCE."""
        if not self.episode_data:
            return
        
        # Calculate returns
        returns = []
        G = 0
        for exp in reversed(self.episode_data):
            G = exp.reward + 0.99 * G  # Discount factor 0.99
            returns.insert(0, G)
        
        # Normalize returns
        returns = np.array(returns)
        if returns.std() > 0:
            returns = (returns - returns.mean()) / returns.std()
        
        # Update policy
        for exp, G in zip(self.episode_data, returns):
            state_key = self.get_state_key(exp.state)
            if state_key not in self.policy:
                continue
            
            # Gradient ascent
            for action in self.policy[state_key]:
                if action == exp.action:
                    self.policy[state_key][action] += self.lr * G
                else:
                    self.policy[state_key][action] -= self.lr * G * 0.1
        
        self.episode_data = []


# ─── Learning Manager ───────────────────────────────────#

class LearningManager:
    """Manages all learning agents."""
    
    def __init__(self, storage_path: str = "friday_memory/learning"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.ql_agent = QLearningAgent()
        self.pg_agent = PolicyGradientAgent()
        
        self.experiences: List[Experience] = []
        self.load_all()
        
    def load_all(self):
        """Load all learned models."""
        self.ql_agent.load(self.storage_path / "q_table.json")
        
    def save_all(self):
        """Save all learned models."""
        self.ql_agent.save(self.storage_path / "q_table.json")
        
    def add_experience(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        context: Dict[str, Any] = None
    ):
        """Add a new experience."""
        exp = Experience(state, action, reward, next_state, context)
        self.experiences.append(exp)
        
        # Learn
        self.ql_agent.learn(exp)
        
        # Save periodically
        if len(self.experiences) % 100 == 0:
            self.save_all()
    
    def get_best_action(self, state: str, available_actions: List[str]) -> str:
        """Get best action for a state."""
        return self.ql_agent.choose_action(state, available_actions)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            "total_experiences": len(self.experiences),
            "states_learned": len(self.ql_agent.q_table),
            "q_table_saved": (self.storage_path / "q_table.json").exists(),
        }


# ─── Singleton ───────────────────────────────────#

_manager: Optional[LearningManager] = None

def get_learning_manager() -> LearningManager:
    global _manager
    if _manager is None:
        _manager = LearningManager()
    return _manager


# ─── Tool Function for Friday ───────────────────────────────────#

def learning_tool(
    action: str = "stats",
    state: str = None,
    action_taken: str = None,
    reward: float = 0.0,
    next_state: str = None,
    available_actions: str = None,  # JSON list
) -> str:
    """
    Friday tool for reinforcement learning.
    Actions: stats, learn, best_action, save, reset
    """
    manager = get_learning_manager()
    
    if action == "stats":
        stats = manager.get_stats()
        lines = ["### LEARNING STATISTICS", ""]
        lines.append(f"**Total Experiences**: {stats['total_experiences']}")
        lines.append(f"**States Learned**: {stats['states_learned']}")
        lines.append(f"**Model Saved**: {'[OK]' if stats['q_table_saved'] else '[FAIL]'}")
        return "\n".join(lines)
    
    if action == "learn":
        if not state or not action_taken or not next_state:
            return "[FAIL] state, action_taken, and next_state required."
        
        manager.add_experience(state, action_taken, reward, next_state)
        return f"[OK] Learned: {action_taken} → reward {reward}"
    
    if action == "best_action":
        if not state or not available_actions:
            return "[FAIL] state and available_actions (JSON list) required."
        
        try:
            actions = json.loads(available_actions)
        except:
            return "[FAIL] available_actions must be JSON list."
        
        best = manager.get_best_action(state, actions)
        return f"[OK] Best action for state: {best}"
    
    if action == "save":
        manager.save_all()
        return "[OK] Learning data saved."
    
    if action == "reset":
        manager.experiences = []
        manager.ql_agent.q_table = defaultdict(lambda: defaultdict(float))
        manager.save_all()
        return "[OK] Learning reset."
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Reinforcement Learning...\n")
    
    manager = get_learning_manager()
    
    # Simulate learning
    print("--- Learning Simulation ---")
    states = ["user_asks_weather", "user_asks_time", "user_asks_joke"]
    actions = ["search_web", "check_system", "tell_joke"]
    
    for i in range(20):
        state = np.random.choice(states)
        action = np.random.choice(actions)
        reward = np.random.uniform(-1, 1)
        next_state = np.random.choice(states)
        
        manager.add_experience(state, action, reward, next_state)
        print(f"Step {i+1}: {state} → {action}, reward={reward:.2f}")
    
    print("\n--- Stats ---")
    print(learning_tool("stats"))
    
    print("\n--- Best Action ---")
    print(learning_tool("best_action", state="user_asks_weather", 
                        available_actions=json.dumps(actions)))
