"""
Friday Vector Memory - Semantic search using ChromaDB.
Enables Friday to remember and retrieve information semantically.
"""
from __future__ import annotations

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime


# ─── Vector Memory Store ────────────────────────────────────#

class VectorMemory:
    """
    Semantic memory using vector embeddings.
    Stores and retrieves information based on meaning, not just keywords.
    """
    
    def __init__(self, collection_name: str = "friday_memory"):
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Create persistent client
            db_path = os.path.join(os.path.dirname(__file__), "friday_memory", "chroma_db")
            os.makedirs(db_path, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"[VectorMemory] Initialized: {self.collection_name}")
            
        except ImportError:
            print("[VectorMemory] chromadb not installed. Run: pip install chromadb")
            self.client = None
            self.collection = None
        except Exception as e:
            print(f"[VectorMemory] Error initializing: {e}")
            self.client = None
            self.collection = None
    
    def is_available(self) -> bool:
        """Check if vector memory is available."""
        return self.collection is not None
    
    def add(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None
    ) -> str:
        """
        Add a text to vector memory.
        Returns the ID of the added item.
        """
        if not self.is_available():
            return "❌ Vector memory not available."
        
        try:
            # Generate ID if not provided
            if id is None:
                import hashlib
                id = hashlib.md5(text.encode()).hexdigest()
            
            # Default metadata
            if metadata is None:
                metadata = {}
            
            metadata["timestamp"] = datetime.now().isoformat()
            metadata["source"] = metadata.get("source", "user")
            
            # Add to collection
            self.collection.add(
                documents=[text],
                metadatas=[metadata],
                ids=[id]
            )
            
            return f"✅ Added to vector memory (ID: {id[:8]}...)"
            
        except Exception as e:
            return f"❌ Error adding to memory: {e}"
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar texts in memory.
        Returns list of {text, metadata, distance, id}
        """
        if not self.is_available():
            return [{"error": "Vector memory not available"}]
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter
            )
            
            # Format results
            formatted = []
            if results and results.get("documents"):
                documents = results["documents"][0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]
                ids = results.get("ids", [[]])[0]
                
                for i, doc in enumerate(documents):
                    formatted.append({
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": distances[i] if i < len(distances) else 1.0,
                        "id": ids[i] if i < len(ids) else None,
                    })
            
            return formatted
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def get_stats(self) -> str:
        """Get statistics about the vector memory."""
        if not self.is_available():
            return "❌ Vector memory not available."
        
        try:
            count = self.collection.count()
            return f"""
### VECTOR MEMORY STATS
**Collection**: {self.collection_name}
**Items**: {count}
**Status**: ✅ Active
"""
        except Exception as e:
            return f"❌ Error getting stats: {e}"
    
    def delete(self, id: str) -> str:
        """Delete an item from memory."""
        if not self.is_available():
            return "❌ Vector memory not available."
        
        try:
            self.collection.delete(ids=[id])
            return f"✅ Deleted item {id[:8]}..."
        except Exception as e:
            return f"❌ Error deleting: {e}"
    
    def clear(self) -> str:
        """Clear all items from memory."""
        if not self.is_available():
            return "❌ Vector memory not available."
        
        try:
            self.client.delete_collection(self.collection_name)
            self._init_chroma()  # Reinitialize
            return "✅ Vector memory cleared."
        except Exception as e:
            return f"❌ Error clearing: {e}"


# ─── Singleton Instance ────────────────────────────────────#

_memory_instance: Optional[VectorMemory] = None

def get_vector_memory() -> VectorMemory:
    """Get or create the global vector memory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = VectorMemory()
    return _memory_instance


# ─── Tool Function for Friday ────────────────────────────────────#

def vector_memory_tool(
    action: str = "search",
    query: str = None,
    text: str = None,
    metadata: str = None,  # JSON string
    n_results: int = 5,
    item_id: str = None,
) -> str:
    """
    Friday tool for vector memory operations.
    Actions: search, add, stats, delete, clear
    """
    memory = get_vector_memory()
    
    if not memory.is_available():
        return "❌ Vector memory not available. Install: pip install chromadb"
    
    if action == "search":
        if not query:
            return "❌ Query required for search."
        results = memory.search(query, n_results=n_results)
        if not results:
            return "No results found."
        if "error" in results[0]:
            return f"❌ {results[0]['error']}"
        
        lines = [f"### SEARCH RESULTS (top {len(results)})", ""]
        for i, r in enumerate(results, 1):
            lines.append(f"**{i}.** {r['text'][:200]}")
            if r.get('metadata'):
                source = r['metadata'].get('source', 'unknown')
                lines.append(f"   Source: {source} | Distance: {r['distance']:.3f}")
            lines.append("")
        
        return "\n".join(lines)
    
    if action == "add":
        if not text:
            return "❌ Text required for add."
        
        meta = {}
        if metadata:
            try:
                meta = json.loads(metadata)
            except:
                pass
        
        return memory.add(text, meta)
    
    if action == "stats":
        return memory.get_stats()
    
    if action == "delete":
        if not item_id:
            return "❌ Item ID required for delete."
        return memory.delete(item_id)
    
    if action == "clear":
        return memory.clear()
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Vector Memory...")
    
    memory = get_vector_memory()
    
    if not memory.is_available():
        print("❌ ChromaDB not available. Install: pip install chromadb")
    else:
        # Test adding
        print("\nAdding test items...")
        print(memory.add("Python is a programming language", {"source": "test"}))
        print(memory.add("LangGraph is a framework for building AI agents", {"source": "test"}))
        print(memory.add("Gemini is Google's AI model", {"source": "test"}))
        
        # Test search
        print("\nSearching for 'AI framework'...")
        results = memory.search("AI framework", n_results=2)
        for r in results:
            print(f"  - {r['text']} (distance: {r['distance']:.3f})")
        
        # Stats
        print("\n" + memory.get_stats())
