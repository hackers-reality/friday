"""Command Chaining for Friday - Multi-step workflow execution."""

import json
import re
from typing import List, Dict, Any, Optional

class CommandChainer:
    """Execute multi-step command workflows."""
    
    def __init__(self):
        self.workflows = {}
        self.execution_history = []
    
    def parse_chain(self, command: str) -> List[Dict[str, Any]]:
        """Parse a chained command into steps.
        
        Supports:
        - Sequential: cmd1 && cmd2 && cmd3
        - Piped: cmd1 | cmd2 | cmd3
        - Conditional: cmd1 || cmd2
        - Templated: search for {result1} in next command
        """
        steps = []
        
        # Split by && (sequential) or || (conditional)
        if '&&' in command:
            parts = command.split('&&')
            for part in parts:
                part = part.strip()
                if part:
                    steps.append({
                        'command': part.strip(),
                        'type': 'sequential',
                        'depends_on': len(steps) - 1 if steps else None
                    })
        elif '||' in command:
            parts = command.split('||')
            for i, part in enumerate(parts):
                part = part.strip()
                if part:
                    steps.append({
                        'command': part.strip(),
                        'type': 'conditional',
                        'depends_on': i - 1 if i > 0 else None
                    })
        elif '|' in command:
            # Piped commands
            parts = command.split('|')
            for i, part in enumerate(parts):
                part = part.strip()
                if part:
                    steps.append({
                        'command': part.strip(),
                        'type': 'pipe',
                        'depends_on': i - 1 if i > 0 else None
                    })
        else:
            steps.append({
                'command': command,
                'type': 'single',
                'depends_on': None
            })
        
        return steps
    
    def execute_chain(self, chain: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a chained command."""
        steps = self.parse_chain(chain)
        results = []
        context = context or {}
        
        for i, step in enumerate(steps):
            cmd = step['command']
            
            # Replace templates with previous results
            for j in range(i):
                placeholder = f"{{result{j}}}"
                if placeholder in cmd and j < len(results):
                    cmd = cmd.replace(placeholder, str(results[j].get('output', '')))
            
            # Execute step
            result = self._execute_step(cmd, context)
            results.append(result)
            
            # Check conditional
            if step['type'] == 'conditional' and result.get('success'):
                break  # Stop if first command succeeded
            
            # Update context
            context[f'result{i}'] = result.get('output', '')
        
        return {
            'success': all(r.get('success') for r in results),
            'steps': len(results),
            'results': results
        }
    
    def _execute_step(self, command: str, context: Dict) -> Dict[str, Any]:
        """Execute a single step."""
        # This is a placeholder - actual execution will call Friday's tools
        return {
            'command': command,
            'success': True,
            'output': f"Executed: {command}",
            'context': context
        }
    
    def save_workflow(self, name: str, chain: str) -> str:
        """Save a workflow for later use."""
        self.workflows[name] = {
            'chain': chain,
            'steps': self.parse_chain(chain)
        }
        return f"Workflow '{name}' saved with {len(self.workflows[name]['steps'])} steps"
    
    def load_workflow(self, name: str) -> Optional[Dict]:
        """Load a saved workflow."""
        return self.workflows.get(name)
    
    def list_workflows(self) -> str:
        """List all saved workflows."""
        if not self.workflows:
            return "No workflows saved"
        return "\n".join(f"- {name}: {len(w['steps'])} steps" for name, w in self.workflows.items())
    
    def execute_workflow(self, name: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a saved workflow."""
        workflow = self.load_workflow(name)
        if not workflow:
            return {'success': False, 'error': f"Workflow '{name}' not found"}
        return self.execute_chain(workflow['chain'], context)


# Global instance
chainer = CommandChainer()


def chain_commands(chain: str) -> str:
    """Execute a chained command.
    
    Examples:
    - "search Python && open https://python.org"
    - "get weather | tell me about the weather"
    - "try this || try that"
    """
    result = chainer.execute_chain(chain)
    if result['success']:
        outputs = [r.get('output', '') for r in result['results']]
        return f"Chain executed ({result['steps']} steps):\n" + "\n".join(outputs)
    else:
        return f"Chain failed: {result}"


def save_workflow(name: str, chain: str) -> str:
    """Save a command chain as a reusable workflow."""
    return chainer.save_workflow(name, chain)


def list_workflows() -> str:
    """List all saved workflows."""
    return chainer.list_workflows()


def run_workflow(name: str) -> str:
    """Execute a saved workflow."""
    result = chainer.execute_workflow(name)
    if result.get('success'):
        return f"Workflow '{name}' executed successfully"
    else:
        return f"Workflow failed: {result.get('error', 'Unknown error')}"
