"""LLM Manager for Friday - Multi-LLM switching support."""

import os
import json
from typing import Optional, Dict, Any

class LLMManager:
    """Manages multiple LLM backends for Friday."""
    
    def __init__(self):
        self.current_llm = "gemini"
        self.available_llms = {
            "gemini": {
                "name": "Gemini 3.1 Flash Live",
                "model_id": "gemini-3.1-flash-live-preview",
                "type": "realtime",
                "available": True
            },
            "claude": {
                "name": "Claude 3.5 Sonnet",
                "model_id": "claude-3-5-sonnet-20241022",
                "type": "chat",
                "available": bool(os.getenv("ANTHROPIC_API_KEY"))
            },
            "chatgpt": {
                "name": "ChatGPT 4o",
                "model_id": "gpt-4o",
                "type": "chat",
                "available": bool(os.getenv("OPENAI_API_KEY"))
            },
            "local": {
                "name": "Local LLM (Ollama)",
                "model_id": "llama3.2",
                "type": "chat",
                "available": self._check_ollama()
            }
        }
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running locally."""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            return resp.status_code == 200
        except:
            return False
    
    def switch_llm(self, llm_name: str) -> Dict[str, Any]:
        """Switch to a different LLM backend."""
        if llm_name not in self.available_llms:
            return {"success": False, "error": f"Unknown LLM: {llm_name}"}
        
        llm_config = self.available_llms[llm_name]
        if not llm_config["available"]:
            return {"success": False, "error": f"{llm_name} is not available. Check API keys."}
        
        self.current_llm = llm_name
        return {"success": True, "llm": llm_name, "config": llm_config}
    
    def get_current_llm(self) -> str:
        """Get the current LLM name."""
        return self.current_llm
    
    def get_available_llms(self) -> Dict[str, Any]:
        """Get all available LLMs."""
        return self.available_llms
    
    def query(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        """Query the current LLM with a prompt."""
        if self.current_llm == "gemini":
            return self._query_gemini(prompt, system, **kwargs)
        elif self.current_llm == "claude":
            return self._query_claude(prompt, system, **kwargs)
        elif self.current_llm == "chatgpt":
            return self._query_openai(prompt, system, **kwargs)
        elif self.current_llm == "local":
            return self._query_ollama(prompt, system, **kwargs)
        else:
            return f"Unknown LLM: {self.current_llm}"
    
    def _query_gemini(self, prompt: str, system: Optional[str], **kwargs) -> str:
        """Query Gemini (placeholder - handled by friday_live.py)."""
        return "Gemini queries handled by friday_live.py"
    
    def _query_claude(self, prompt: str, system: Optional[str], **kwargs) -> str:
        """Query Claude via Anthropic API."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            messages = [{"role": "user", "content": prompt}]
            response = client.messages.create(
                model=self.available_llms["claude"]["model_id"],
                max_tokens=4096,
                system=system or "",
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            return f"Claude error: {e}"
    
    def _query_openai(self, prompt: str, system: Optional[str], **kwargs) -> str:
        """Query OpenAI ChatGPT."""
        try:
            import openai
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=self.available_llms["chatgpt"]["model_id"],
                messages=messages,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"ChatGPT error: {e}"
    
    def _query_ollama(self, prompt: str, system: Optional[str], **kwargs) -> str:
        """Query local Ollama instance."""
        try:
            import requests
            payload = {
                "model": self.available_llms["local"]["model_id"],
                "prompt": prompt,
                "system": system or "",
                "stream": False
            }
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
            return resp.json().get("response", "No response")
        except Exception as e:
            return f"Ollama error: {e}"


# Global instance
llm_manager = LLMManager()


def switch_llm(llm_name: str) -> str:
    """Switch LLM backend."""
    result = llm_manager.switch_llm(llm_name)
    if result["success"]:
        return f"Switched to {result['config']['name']}"
    else:
        return f"Failed to switch: {result['error']}"


def list_llms() -> str:
    """List available LLMs."""
    llms = llm_manager.get_available_llms()
    result = "Available LLMs:\n"
    for name, config in llms.items():
        status = "✓" if config["available"] else "✗"
        result += f"  {status} {name}: {config['name']}\n"
    return result
