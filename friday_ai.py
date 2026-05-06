"""
Friday AI - LLM integration and AI capabilities.
Support for OpenAI, Anthropic, local models, embeddings, and AI agents.
"""
from __future__ import annotations

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional, Generator
from datetime import datetime
from pathlib import Path
import base64


# ─── LLM Providers ────────────────────────────#

class OpenAIProvider:
    """OpenAI API provider."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"
        self.available = self.api_key is not None
        
    def chat(
        self,
        messages: List[Dict],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Chat completion."""
        if not self.available:
            return {
                "success": False,
                "error": "OpenAI API key not set. Set OPENAI_API_KEY environment variable.",
            }
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data["choices"][0]["message"]["content"],
                    "model": model,
                    "usage": data.get("usage", {}),
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                }
        except ImportError:
            return {"success": False, "error": "Requests library not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def complete(
        self,
        prompt: str,
        model: str = "text-davinci-003",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Text completion."""
        if not self.available:
            return {
                "success": False,
                "error": "OpenAI API key not set.",
            }
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": model,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            response = requests.post(
                f"{self.base_url}/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data["choices"][0]["text"],
                    "model": model,
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def embed(self, text: str, model: str = "text-embedding-ada-002") -> Dict[str, Any]:
        """Create embeddings."""
        if not self.available:
            return {"success": False, "error": "OpenAI API key not set."}
        
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": model,
                "input": text,
            }
            
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=payload,
                timeout=30,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "embedding": data["data"][0]["embedding"],
                    "model": model,
                }
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class AnthropicProvider:
    """Anthropic Claude API provider."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1"
        self.available = self.api_key is not None
        
    def chat(
        self,
        messages: List[Dict],
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """Chat completion with Claude."""
        if not self.available:
            return {
                "success": False,
                "error": "Anthropic API key not set. Set ANTHROPIC_API_KEY environment variable.",
            }
        
        try:
            import requests
            
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            
            # Convert messages to Anthropic format
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            
            payload = {
                "model": model,
                "prompt": f"{prompt}\n\nAssistant:",
                "max_tokens_to_sample": max_tokens,
            }
            
            response = requests.post(
                f"{self.base_url}/complete",
                headers=headers,
                json=payload,
                timeout=60,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data["completion"],
                    "model": model,
                }
            else:
                return {
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


class LocalLLMProvider:
    """Local LLM provider (e.g., LLaMA, Mistral via llama-cpp or ollama)."""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available = True  # Assume available, check on request
        
    def chat(
        self,
        messages: List[Dict],
        model: str = "llama2",
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Chat with local LLM (Ollama format)."""
        try:
            import requests
            
            # Try Ollama API format
            payload = {
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": temperature,
                },
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("message", {}).get("content", ""),
                    "model": model,
                }
            else:
                return {
                    "success": False,
                    "error": f"Local LLM error: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate(
        self,
        prompt: str,
        model: str = "llama2",
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """Generate text with local LLM."""
        try:
            import requests
            
            payload = {
                "model": model,
                "prompt": prompt,
                "options": {
                    "temperature": temperature,
                },
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120,
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "model": model,
                }
            else:
                return {
                    "success": False,
                    "error": f"Local LLM error: {response.status_code}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── AI Agent ────────────────────────────#

class AIAgent:
    """AI agent with tool usage capabilities."""
    
    def __init__(self, llm_provider: str = "openai", **kwargs):
        self.llm_provider = llm_provider
        self.llm = self._get_provider(llm_provider, **kwargs)
        self.tools: Dict[str, callable] = {}
        self.conversation: List[Dict] = []
        
    def _get_provider(self, provider: str, **kwargs):
        """Get LLM provider instance."""
        if provider == "openai":
            return OpenAIProvider(api_key=kwargs.get("api_key"))
        elif provider == "anthropic":
            return AnthropicProvider(api_key=kwargs.get("api_key"))
        elif provider == "local":
            return LocalLLMProvider(base_url=kwargs.get("base_url", "http://localhost:11434"))
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def register_tool(self, name: str, func: callable):
        """Register a tool for the agent to use."""
        self.tools[name] = func
    
    def chat(self, message: str, system_prompt: str = None) -> Dict[str, Any]:
        """Chat with the agent."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        messages.extend(self.conversation)
        
        # Add user message
        messages.append({"role": "user", "content": message})
        
        # Get response
        result = self.llm.chat(messages)
        
        if result["success"]:
            # Add to conversation
            self.conversation.append({"role": "user", "content": message})
            self.conversation.append({"role": "assistant", "content": result["response"]})
            
            # Keep conversation manageable
            if len(self.conversation) > 20:
                self.conversation = self.conversation[-20:]
        
        return result
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation = []


# ─── Embeddings and Similarity ────────────────────────────#

class EmbeddingEngine:
    """Text embeddings and similarity search."""
    
    def __init__(self, provider: str = "openai", **kwargs):
        self.provider = provider
        if provider == "openai":
            self.client = OpenAIProvider(api_key=kwargs.get("api_key"))
        else:
            self.client = None
    
    def embed(self, text: str) -> Dict[str, Any]:
        """Create embedding for text."""
        if self.provider == "openai" and self.client:
            return self.client.embed(text)
        else:
            # Simple fallback: bag-of-characters embedding
            vec = [0] * 256
            for char in text:
                vec[ord(char) % 256] += 1
            # Normalize
            total = sum(vec)
            if total > 0:
                vec = [v / total for v in vec]
            return {"success": True, "embedding": vec}
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        
        if not emb1["success"] or not emb2["success"]:
            return 0.0
        
        vec1 = emb1["embedding"]
        vec2 = emb2["embedding"]
        
        # Cosine similarity
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot / (mag1 * mag2)


# ─── Friday AI Tool ────────────────────────────#

def ai_tool(
    action: str = "status",
    message: str = None,
    model: str = None,
    provider: str = "openai",
    system_prompt: str = None,
) -> str:
    """
    Friday tool for AI operations.
    Actions: status, chat, complete, embed, similarity, local_chat
    """
    if action == "status":
        lines = ["### AI STATUS", ""]
        lines.append("**Available Providers**:")
        lines.append("  - OpenAI (GPT-3.5, GPT-4)")
        lines.append("  - Anthropic (Claude)")
        lines.append("  - Local LLM (Ollama, LLaMA)")
        lines.append("")
        lines.append("**Features**:")
        lines.append("  - Chat completions")
        lines.append("  - Text embeddings")
        lines.append("  - Semantic similarity")
        lines.append("  - AI Agent with tools")
        return "\n".join(lines)
    
    if action == "chat":
        if not message:
            return "❌ Message required."
        
        provider_instance = None
        if provider == "openai":
            provider_instance = OpenAIProvider()
        elif provider == "anthropic":
            provider_instance = AnthropicProvider()
        elif provider == "local":
            provider_instance = LocalLLMProvider()
        else:
            return f"❌ Unknown provider: {provider}"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        result = provider_instance.chat(messages, model=model or "gpt-3.5-turbo")
        
        if result["success"]:
            return f"### AI CHAT\n\n**Response**:\n{result['response']}"
        else:
            return f"❌ Chat error: {result.get('error', 'Unknown')}"
    
    if action == "complete":
        if not message:
            return "❌ Prompt required."
        
        openai = OpenAIProvider()
        result = openai.complete(message, model=model or "text-davinci-003")
        
        if result["success"]:
            return f"### COMPLETION\n\n**Response**:\n{result['response']}"
        else:
            return f"❌ Completion error: {result.get('error', 'Unknown')}"
    
    if action == "embed":
        if not message:
            return "❌ Text required."
        
        engine = EmbeddingEngine()
        result = engine.embed(message)
        
        if result["success"]:
            vec_preview = result["embedding"][:10]
            return f"### EMBEDDING\n\n**Preview** (first 10 dims): {vec_preview}\n**Dimensions**: {len(result['embedding'])}"
        else:
            return f"❌ Embedding error: {result.get('error', 'Unknown')}"
    
    if action == "similarity":
        if not message or ":" not in message:
            return "❌ Format: text1:text2"
        
        text1, text2 = message.split(":", 1)
        engine = EmbeddingEngine()
        sim = engine.similarity(text1.strip(), text2.strip())
        
        return f"### SIMILARITY\n\n**Text 1**: {text1.strip()[:50]}...\n**Text 2**: {text2.strip()[:50]}...\n**Similarity**: {sim:.4f}"
    
    if action == "local_chat":
        if not message:
            return "❌ Message required."
        
        local = LocalLLMProvider()
        messages = [{"role": "user", "content": message}]
        result = local.chat(messages, model=model or "llama2")
        
        if result["success"]:
            return f"### LOCAL AI CHAT\n\n**Response**:\n{result['response']}"
        else:
            return f"❌ Local chat error: {result.get('error', 'Unknown')}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday AI...\n")
    
    # Test status
    print("--- AI Status ---")
    print(ai_tool("status"))
    
    # Test embedding
    print("\n--- Embedding ---")
    print(ai_tool("embed", message="Hello, Friday!"))
