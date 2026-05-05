"""
Friday Database - Data persistence and storage.
SQLite, JSON, key-value stores, vector databases, and query engines.
"""
from __future__ import annotations__

import os
import json
import sqlite3
import threading
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
import shutil
import tempfile


# ─── SQLite Database ────────────────────────────#

class SQLiteDB:
    """SQLite database operations."""
    
    def __init__(self, db_path: str = "friday.db"):
        self.db_path = db_path
        self.connection = None
        self.lock = threading.Lock()
        
    def connect(self) -> Dict[str, Any]:
        """Connect to database."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            return {"success": True, "db": self.db_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute(self, query: str, params: Tuple = None) -> Dict[str, Any]:
        """Execute a query."""
        with self.lock:
            if not self.connection:
                self.connect()
            
            try:
                cursor = self.connection.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                self.connection.commit()
                
                return {
                    "success": True,
                    "lastrowid": cursor.lastrowid,
                    "rowcount": cursor.rowcount,
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def query(self, query: str, params: Tuple = None) -> Dict[str, Any]:
        """Query database and return results."""
        with self.lock:
            if not self.connection:
                self.connect()
            
            try:
                cursor = self.connection.cursor()
                
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                
                results = []
                for row in rows:
                    results.append(dict(zip(columns, row)))
                
                return {
                    "success": True,
                    "results": results,
                    "count": len(results),
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    def create_table(self, table_name: str, columns: Dict[str, str]) -> Dict[str, Any]:
        """Create a table."""
        columns_def = ", ".join([f"{name} {type_}" for name, type_ in columns.items()])
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})"
        return self.execute(query)
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a row."""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        return self.execute(query, tuple(data.values()))
    
    def update(self, table_name: str, data: Dict[str, Any], where: str, where_params: Tuple = None) -> Dict[str, Any]:
        """Update rows."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + (where_params or ())
        return self.execute(query, params)
    
    def delete(self, table_name: str, where: str, where_params: Tuple = None) -> Dict[str, Any]:
        """Delete rows."""
        query = f"DELETE FROM {table_name} WHERE {where}"
        return self.execute(query, where_params)
    
    def backup(self, backup_path: str = None) -> Dict[str, Any]:
        """Backup database."""
        backup_path = backup_path or f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(self.db_path, backup_path)
            return {"success": True, "backup": backup_path}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── JSON Database ────────────────────────────#

class JSONDB:
    """Simple JSON file database."""
    
    def __init__(self, file_path: str = "friday.json"):
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        self.load()
        
    def load(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, "r") as f:
                    self.data = json.load(f)
            else:
                self.data = {}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def save(self) -> Dict[str, Any]:
        """Save data to JSON file."""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key."""
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any) -> Dict[str, Any]:
        """Set value for key."""
        self.data[key] = value
        return self.save()
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete key."""
        if key in self.data:
            del self.data[key]
            return self.save()
        return {"success": False, "error": "Key not found."}
    
    def list_keys(self) -> List[str]:
        """List all keys."""
        return list(self.data.keys())
    
    def search(self, query: str) -> Dict[str, Any]:
        """Search for keys containing query."""
        results = {}
        for key, value in self.data.items():
            if query.lower() in key.lower():
                results[key] = value
        return results


# ─── Key-Value Store (In-Memory with Persistence) ────────────────────────────#

class KeyValueStore:
    """Simple key-value store with optional persistence."""
    
    def __init__(self, persist_path: str = None):
        self.store: Dict[str, Any] = {}
        self.persist_path = persist_path
        self.lock = threading.Lock()
        
        if persist_path and os.path.exists(persist_path):
            self.load()
    
    def put(self, key: str, value: Any) -> Dict[str, Any]:
        """Store a key-value pair."""
        with self.lock:
            self.store[key] = {
                "value": value,
                "timestamp": datetime.now().isoformat(),
            }
            self._persist()
            return {"success": True}
    
    def get(self, key: str) -> Dict[str, Any]:
        """Get value by key."""
        with self.lock:
            if key in self.store:
                return {
                    "success": True,
                    "value": self.store[key]["value"],
                    "timestamp": self.store[key]["timestamp"],
                }
            else:
                return {"success": False, "error": "Key not found."}
    
    def delete(self, key: str) -> Dict[str, Any]:
        """Delete a key."""
        with self.lock:
            if key in self.store:
                del self.store[key]
                self._persist()
                return {"success": True}
            else:
                return {"success": False, "error": "Key not found."}
    
    def keys(self, prefix: str = None) -> List[str]:
        """List all keys, optionally filtered by prefix."""
        with self.lock:
            if prefix:
                return [k for k in self.store.keys() if k.startswith(prefix)]
            return list(self.store.keys())
    
    def _persist(self):
        """Persist to disk if path is set."""
        if self.persist_path:
            try:
                with open(self.persist_path, "w") as f:
                    json.dump(self.store, f, indent=2)
            except:
                pass
    
    def load(self):
        """Load from disk."""
        if self.persist_path and os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r") as f:
                    self.store = json.load(f)
            except:
                self.store = {}


# ─── Vector Database (Simplified) ────────────────────────────#

class SimpleVectorDB:
    """Simplified vector database for embeddings."""
    
    def __init__(self, db_path: str = "vectors.json"):
        self.db_path = db_path
        self.vectors: Dict[str, Dict] = {}
        self.load()
    
    def load(self):
        """Load vectors from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r") as f:
                    self.vectors = json.load(f)
            except:
                self.vectors = {}
    
    def save(self):
        """Save vectors to disk."""
        try:
            with open(self.db_path, "w") as f:
                json.dump(self.vectors, f, indent=2)
        except Exception as e:
            print(f"Error saving vectors: {e}")
    
    def add(self, id_: str, vector: List[float], metadata: Dict = None) -> Dict[str, Any]:
        """Add a vector to the database."""
        self.vectors[id_] = {
            "vector": vector,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.save()
        return {"success": True, "id": id_}
    
    def get(self, id_: str) -> Dict[str, Any]:
        """Get vector by ID."""
        if id_ in self.vectors:
            return {"success": True, "data": self.vectors[id_]}
        return {"success": False, "error": "ID not found."}
    
    def delete(self, id_: str) -> Dict[str, Any]:
        """Delete vector by ID."""
        if id_ in self.vectors:
            del self.vectors[id_]
            self.save()
            return {"success": True}
        return {"success": False, "error": "ID not found."}
    
    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(v1, v2))
        magnitude1 = sum(a * a for a in v1) ** 0.5
        magnitude2 = sum(b * b for b in v2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict]:
        """Search for similar vectors."""
        similarities = []
        
        for id_, data in self.vectors.items():
            similarity = self.cosine_similarity(query_vector, data["vector"])
            similarities.append({
                "id": id_,
                "similarity": similarity,
                "metadata": data["metadata"],
            })
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        
        return similarities[:top_k]
    
    def list_all(self) -> List[str]:
        """List all vector IDs."""
        return list(self.vectors.keys())


# ─── Database Tool for Friday ────────────────────────────#

def database_tool(
    action: str = "status",
    db_type: str = "sqlite",
    query: str = None,
    data: Dict = None,
    key: str = None,
    table: str = None,
) -> str:
    """
    Friday tool for database operations.
    Actions: status, sqlite_query, sqlite_insert, json_get, json_set,
            kv_put, kv_get, vector_add, vector_search
    """
    if action == "status":
        lines = ["### DATABASE STATUS", ""]
        lines.append("**Available Backends**:")
        lines.append("  - SQLite (sqlite3)")
        lines.append("  - JSON file database")
        lines.append("  - Key-Value store (in-memory + persist)")
        lines.append("  - Vector database (simplified)")
        return "\n".join(lines)
    
    if action == "sqlite_query":
        if not query:
            return "❌ Query required."
        db = SQLiteDB()
        result = db.query(query)
        if result["success"]:
            preview = json.dumps(result["results"][:5], indent=2)
            return f"### SQLITE QUERY\n\nFound {result['count']} rows:\n{preview}"
        else:
            return f"❌ Query error: {result.get('error', 'Unknown')}"
    
    if action == "sqlite_insert":
        if not table or not data:
            return "❌ Table and data required."
        db = SQLiteDB()
        result = db.insert(table, data)
        return f"### SQLITE INSERT\n\n{'✅ Inserted' if result['success'] else f'❌ {result.get(\"error\", \"Unknown\")}'}"
    
    if action == "json_get":
        if not key:
            return "❌ Key required."
        db = JSONDB()
        value = db.get(key)
        return f"### JSON GET\n\n**{key}**: {json.dumps(value, indent=2)[:200]}"
    
    if action == "json_set":
        if not key or data is None:
            return "❌ Key and data required."
        db = JSONDB()
        result = db.set(key, data)
        return f"### JSON SET\n\n{'✅ Set' if result['success'] else f'❌ {result.get(\"error\", \"Unknown\")}'}"
    
    if action == "kv_put":
        if not key or data is None:
            return "❌ Key and value required."
        kv = KeyValueStore()
        result = kv.put(key, data)
        return f"### KV PUT\n\n{'✅ Stored' if result['success'] else '❌ Error'}"
    
    if action == "kv_get":
        if not key:
            return "❌ Key required."
        kv = KeyValueStore()
        result = kv.get(key)
        if result["success"]:
            return f"### KV GET\n\n**{key}**: {json.dumps(result['value'], indent=2)[:200]}"
        else:
            return f"❌ {result.get('error', 'Unknown')}"
    
    if action == "vector_add":
        if not key or not data:
            return "❌ ID and vector required."
        vdb = SimpleVectorDB()
        result = vdb.add(key, data)
        return f"### VECTOR ADD\n\n{'✅ Added' if result['success'] else '❌ Error'}"
    
    if action == "vector_search":
        if not data:
            return "❌ Query vector required."
        vdb = SimpleVectorDB()
        results = vdb.search(data, top_k=5)
        preview = json.dumps(results, indent=2)[:500]
        return f"### VECTOR SEARCH\n\nResults:\n{preview}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Database...\n")
    
    # Test JSON DB
    print("--- JSON Database ---")
    print(database_tool("json_set", key="test", data={"message": "Hello from Friday"}))
    print(database_tool("json_get", key="test"))
    
    # Test SQLite
    print("\n--- SQLite ---")
    print(database_tool("sqlite_query", query="SELECT sqlite_version() as version"))
