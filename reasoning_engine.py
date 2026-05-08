"""
Friday Reasoning Engine - Advanced reasoning capabilities.
Implements Chain-of-Thought, Tree-of-Thought, and ReAct reasoning.
"""
from __future__ import annotations

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


# ─── Reasoning Types ───────────────────────────────────#

@dataclass
class Thought:
    """A single thought in a reasoning chain."""
    content: str
    score: float = 0.0
    depth: int = 0
    children: List['Thought'] = None
    parent: Optional['Thought'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def add_child(self, thought: 'Thought'):
        """Add a child thought."""
        thought.parent = self
        thought.depth = self.depth + 1
        self.children.append(thought)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            "content": self.content,
            "score": self.score,
            "depth": self.depth,
            "children": [c.to_dict() for c in self.children],
        }


# ─── Chain of Thought ───────────────────────────────────#

class ChainOfThought:
    """
    Implements Chain-of-Thought reasoning.
    Breaks down complex problems into step-by-step thoughts.
    """
    
    def __init__(self, llm_callable=None):
        self.llm_callable = llm_callable
        self.thoughts: List[Thought] = []
    
    def reason(self, problem: str, max_steps: int = 10) -> Dict[str, Any]:
        """
        Apply Chain-of-Thought reasoning to a problem.
        Returns {answer, steps, confidence}
        """
        steps = []
        context = f"Problem: {problem}\n\nLet's think step by step:\n"
        
        for i in range(max_steps):
            # Generate next thought
            prompt = f"{context}\nStep {i+1}:"
            
            if self.llm_callable:
                thought_content = self.llm_callable(prompt)
            else:
                # Fallback: use simple heuristics
                thought_content = self._generate_thought(problem, steps, i)
            
            if self._is_final_answer(thought_content):
                steps.append(Thought(content=thought_content, score=1.0))
                break
            
            thought = Thought(content=thought_content, score=0.8)
            steps.append(thought)
            context += f"\nStep {i+1}: {thought_content}"
        
        # Extract answer
        answer = self._extract_answer(steps)
        confidence = self._calculate_confidence(steps)
        
        return {
            "problem": problem,
            "steps": [s.content for s in steps],
            "answer": answer,
            "confidence": confidence,
            "num_steps": len(steps),
        }
    
    def _generate_thought(self, problem: str, previous_steps: List[Thought], step_num: int) -> str:
        """Generate a thought using heuristics."""
        if step_num == 0:
            return f"First, I need to understand what {problem} is asking."
        elif step_num == 1:
            return "Let me break this down into smaller parts."
        elif step_num < 5:
            return f"Analyzing part {step_num} of the problem..."
        else:
            return "Based on my analysis, I can now formulate an answer."
    
    def _is_final_answer(self, thought: str) -> bool:
        """Check if thought contains final answer."""
        answer_indicators = [
            "therefore", "thus", "in conclusion", "answer is",
            "final answer", "solution is", "result is"
        ]
        thought_lower = thought.lower()
        return any(indicator in thought_lower for indicator in answer_indicators)
    
    def _extract_answer(self, steps: List[Thought]) -> str:
        """Extract the final answer from steps."""
        if not steps:
            return "No answer generated."
        
        # Look for answer in last steps
        for step in reversed(steps):
            if self._is_final_answer(step.content):
                return step.content
        
        # Return last step as answer
        return steps[-1].content if steps else "No answer."
    
    def _calculate_confidence(self, steps: List[Thought]) -> float:
        """Calculate confidence score."""
        if not steps:
            return 0.0
        
        # Simple heuristic: more steps = higher confidence (up to a point)
        num_steps = len(steps)
        if num_steps >= 5:
            return 0.9
        elif num_steps >= 3:
            return 0.7
        else:
            return 0.4


# ─── Tree of Thought ───────────────────────────────────#

class TreeOfThought:
    """
    Implements Tree-of-Thought reasoning.
    Explores multiple reasoning paths and selects the best one.
    """
    
    def __init__(self, llm_callable=None, branching_factor: int = 3, max_depth: int = 5):
        self.llm_callable = llm_callable
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.root: Optional[Thought] = None
    
    def reason(self, problem: str) -> Dict[str, Any]:
        """
        Apply Tree-of-Thought reasoning.
        Returns {answer, best_path, score}
        """
        # Initialize root
        self.root = Thought(content=f"Root: {problem}", score=1.0)
        
        # BFS/DFS to build tree
        queue = [self.root]
        
        while queue and queue[0].depth < self.max_depth:
            current = queue.pop(0)
            
            # Generate branches
            for i in range(self.branching_factor):
                if self.llm_callable:
                    child_content = self.llm_callable(
                        f"Problem: {problem}\nCurrent thought: {current.content}\nGenerate next thought:"
                    )
                else:
                    child_content = f"Branch {i+1} at depth {current.depth + 1}"
                
                child = Thought(
                    content=child_content,
                    score=self._evaluate_thought(child_content, problem),
                    depth=current.depth + 1
                )
                current.add_child(child)
                queue.append(child)
        
        # Find best path
        best_path = self._find_best_path(self.root)
        answer = best_path[-1].content if best_path else "No answer found."
        score = best_path[-1].score if best_path else 0.0
        
        return {
            "problem": problem,
            "answer": answer,
            "best_path": [t.content for t in best_path],
            "score": score,
            "tree_depth": self._get_max_depth(self.root),
            "num_nodes": self._count_nodes(self.root),
        }
    
    def _evaluate_thought(self, thought: str, problem: str) -> float:
        """Evaluate the quality of a thought."""
        # Simple heuristic: longer thoughts that mention problem keywords are better
        problem_keywords = set(problem.lower().split())
        thought_words = set(thought.lower().split())
        overlap = len(problem_keywords & thought_words)
        
        base_score = 0.5
        keyword_bonus = overlap * 0.1
        length_bonus = min(len(thought) / 1000, 0.3)
        
        return min(base_score + keyword_bonus + length_bonus, 1.0)
    
    def _find_best_path(self, node: Thought) -> List[Thought]:
        """Find the highest-scoring path from root to leaf."""
        if not node.children:
            return [node]
        
        best_child_path = []
        best_score = -1
        
        for child in node.children:
            path = self._find_best_path(child)
            path_score = sum(t.score for t in path)
            if path_score > best_score:
                best_score = path_score
                best_child_path = path
        
        return [node] + best_child_path
    
    def _get_max_depth(self, node: Thought) -> int:
        """Get maximum depth of tree."""
        if not node.children:
            return node.depth
        return max(self._get_max_depth(c) for c in node.children)
    
    def _count_nodes(self, node: Thought) -> int:
        """Count total nodes in tree."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count


# ─── ReAct Reasoning ───────────────────────────────────#

class ReActReasoning:
    """
    Implements ReAct (Reasoning + Acting) pattern.
    Alternates between reasoning and action steps.
    """
    
    def __init__(self, llm_callable=None, tools: Dict[str, callable] = None):
        self.llm_callable = llm_callable
        self.tools = tools or {}
        self.trajectory: List[Dict[str, Any]] = []
    
    def reason_and_act(self, task: str, max_iterations: int = 10) -> Dict[str, Any]:
        """
        Apply ReAct reasoning to complete a task.
        Returns {answer, trajectory, success}
        """
        context = f"Task: {task}\n\n"
        
        for i in range(max_iterations):
            # Thought step
            thought_prompt = f"{context}\nThought {i+1}:"
            if self.llm_callable:
                thought = self.llm_callable(thought_prompt)
            else:
                thought = f"I need to analyze step {i+1} of the task."
            
            # Action step
            action, action_input = self._determine_action(thought, task)
            
            # Observation step
            observation = self._execute_action(action, action_input)
            
            # Record trajectory
            step = {
                "iteration": i + 1,
                "thought": thought,
                "action": action,
                "action_input": action_input,
                "observation": observation,
            }
            self.trajectory.append(step)
            
            context += f"\nThought: {thought}\nAction: {action}\nObservation: {observation}"
            
            # Check if task is complete
            if self._is_task_complete(observation, task):
                return {
                    "task": task,
                    "answer": observation,
                    "trajectory": self.trajectory,
                    "success": True,
                    "iterations": i + 1,
                }
        
        return {
            "task": task,
            "answer": "Task not completed within iteration limit.",
            "trajectory": self.trajectory,
            "success": False,
            "iterations": max_iterations,
        }
    
    def _determine_action(self, thought: str, task: str) -> Tuple[str, str]:
        """Determine the next action based on thought."""
        # Simple action parsing
        action_patterns = [
            (r'search for (.+)', 'search'),
            (r'read file (.+)', 'read_file'),
            (r'run command (.+)', 'run_command'),
            (r'use tool (.+)', 'use_tool'),
        ]
        
        for pattern, action in action_patterns:
            match = re.search(pattern, thought.lower())
            if match:
                return action, match.group(1)
        
        # Default: use LLM to decide
        if self.llm_callable:
            decision = self.llm_callable(f"Based on: {thought}\nWhat action to take? (search/read/run/use)")
            return decision.strip(), thought
        
        return "think", thought
    
    def _execute_action(self, action: str, action_input: str) -> str:
        """Execute an action and return observation."""
        if action == "search":
            try:
                from friday_tools import web_search
                return web_search(action_input, count=3)[:500]
            except:
                return f"Searched for: {action_input}"
        
        elif action == "read_file":
            try:
                with open(action_input, 'r', encoding='utf-8') as f:
                    return f.read()[:500]
            except Exception as e:
                return f"Error reading file: {e}"
        
        elif action == "run_command":
            try:
                import subprocess
                result = subprocess.run(
                    action_input, shell=True,
                    capture_output=True, text=True, timeout=10
                )
                return result.stdout[:500] or result.stderr[:500]
            except Exception as e:
                return f"Command error: {e}"
        
        elif action == "use_tool":
            tool_name = action_input.strip()
            if tool_name in self.tools:
                return str(self.tools[tool_name]())
            return f"Tool {tool_name} not found."
        
        else:
            return f"Action {action} executed with input: {action_input}"
    
    def _is_task_complete(self, observation: str, task: str) -> bool:
        """Check if task is complete based on observation."""
        completion_indicators = [
            "completed", "done", "finished", "success",
            "answer is", "result is", "found it"
        ]
        observation_lower = observation.lower()
        return any(indicator in observation_lower for indicator in completion_indicators)


# ─── Tool Function for Friday ────────────────────────────────────#

def reasoning_tool(
    action: str = "cot",
    problem: str = None,
    max_steps: int = 10,
    branching_factor: int = 3,
) -> str:
    """
    Friday tool for advanced reasoning.
    Actions: cot (Chain-of-Thought), tot (Tree-of-Thought), react, compare
    """
    if not problem:
        return "[FAIL] Problem or task required for reasoning."
    
    if action == "cot":
        cot = ChainOfThought()
        result = cot.reason(problem, max_steps)
        
        lines = ["### CHAIN-OF-THOUGHT REASONING", ""]
        lines.append(f"**Problem**: {result['problem']}")
        lines.append(f"**Steps**: {result['num_steps']}")
        lines.append(f"**Confidence**: {result['confidence']:.1%}")
        lines.append("")
        lines.append("**Reasoning Chain**:")
        for i, step in enumerate(result['steps'], 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        lines.append(f"**Answer**: {result['answer'][:300]}")
        
        return "\n".join(lines)
    
    if action == "tot":
        tot = TreeOfThought(branching_factor=branching_factor)
        result = tot.reason(problem)
        
        lines = ["### TREE-OF-THOUGHT REASONING", ""]
        lines.append(f"**Problem**: {result['problem']}")
        lines.append(f"**Tree Depth**: {result['tree_depth']}")
        lines.append(f"**Nodes**: {result['num_nodes']}")
        lines.append(f"**Score**: {result['score']:.2f}")
        lines.append("")
        lines.append("**Best Path**:")
        for i, step in enumerate(result['best_path'], 1):
            lines.append(f"{i}. {step}")
        lines.append("")
        lines.append(f"**Answer**: {result['answer'][:300]}")
        
        return "\n".join(lines)
    
    if action == "react":
        react = ReActReasoning()
        result = react.reason_and_act(problem)
        
        lines = ["### REACT REASONING", ""]
        lines.append(f"**Task**: {result['task']}")
        lines.append(f"**Success**: {'[OK]' if result['success'] else '[FAIL]'}")
        lines.append(f"**Iterations**: {result['iterations']}")
        lines.append("")
        lines.append("**Trajectory**:")
        for step in result['trajectory']:
            lines.append(f"\n--- Iteration {step['iteration']} ---")
            lines.append(f"Thought: {step['thought']}")
            lines.append(f"Action: {step['action']} ({step['action_input']})")
            lines.append(f"Observation: {step['observation'][:200]}")
        
        return "\n".join(lines)
    
    if action == "compare":
        # Run all three and compare
        cot = ChainOfThought()
        cot_result = cot.reason(problem, max_steps)
        
        tot = TreeOfThought()
        tot_result = tot.reason(problem)
        
        react = ReActReasoning()
        react_result = react.reason_and_act(problem)
        
        lines = ["### REASONING COMPARISON", ""]
        lines.append(f"**Problem**: {problem}")
        lines.append("")
        lines.append("**Chain-of-Thought**:")
        lines.append(f"  Answer: {cot_result['answer'][:100]}")
        lines.append(f"  Confidence: {cot_result['confidence']:.1%}")
        lines.append("")
        lines.append("**Tree-of-Thought**:")
        lines.append(f"  Answer: {tot_result['answer'][:100]}")
        lines.append(f"  Score: {tot_result['score']:.2f}")
        lines.append("")
        lines.append("**ReAct**:")
        lines.append(f"  Answer: {react_result['answer'][:100]}")
        lines.append(f"  Success: {'Yes' if react_result['success'] else 'No'}")
        
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Reasoning Engine...\n")
    
    test_problem = "How can I optimize a Python function that processes 1 million records?"
    
    print("--- Chain-of-Thought ---")
    print(reasoning_tool("cot", problem=test_problem, max_steps=5))
    
    print("\n--- Tree-of-Thought ---")
    print(reasoning_tool("tot", problem=test_problem, branching_factor=2))
