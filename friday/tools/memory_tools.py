"""
Memory & Database tools
Libraries: chromadb, qdrant-client, redis, sqlmodel, pymongo, elasticsearch
"""
import asyncio
import json
import os
from typing import Any

# ── ChromaDB ──
HAS_CHROMA = False
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    pass


_chroma_client = None


def _get_chroma():
    global _chroma_client
    if _chroma_client is None and HAS_CHROMA:
        _chroma_client = chromadb.Client(Settings(persist_directory=os.environ.get("CHROMA_DB_PATH", "chromadb_data")))
    return _chroma_client


async def chroma_create_collection(name: str) -> dict[str, Any]:
    if not HAS_CHROMA:
        return {"error": "chromadb not installed"}
    try:
        client = _get_chroma()
        collection = await asyncio.get_event_loop().run_in_executor(None, lambda: client.create_collection(name=name))
        return {"collection": name, "status": "created"}
    except Exception as e:
        return {"error": str(e)}


async def chroma_add(collection: str, texts: list[str], ids: list[str], metadatas: list[dict] | None = None) -> dict[str, Any]:
    if not HAS_CHROMA:
        return {"error": "chromadb not installed"}
    try:
        coll = _get_chroma().get_collection(collection)
        await asyncio.get_event_loop().run_in_executor(None, lambda: coll.add(documents=texts, ids=ids, metadatas=metadatas))
        return {"collection": collection, "added": len(texts)}
    except Exception as e:
        return {"error": str(e)}


async def chroma_query(collection: str, query_text: str, n_results: int = 5) -> dict[str, Any]:
    if not HAS_CHROMA:
        return {"error": "chromadb not installed"}
    try:
        coll = _get_chroma().get_collection(collection)
        results = await asyncio.get_event_loop().run_in_executor(None, lambda: coll.query(query_texts=[query_text], n_results=n_results))
        return {"collection": collection, "query": query_text,
                "results": [{"id": results["ids"][0][i], "text": results["documents"][0][i][:500],
                            "distance": results["distances"][0][i] if results.get("distances") else None}
                            for i in range(len(results["ids"][0]))]}
    except Exception as e:
        return {"error": str(e)}


async def chroma_list_collections() -> dict[str, Any]:
    if not HAS_CHROMA:
        return {"error": "chromadb not installed"}
    try:
        collections = _get_chroma().list_collections()
        return {"collections": [c.name for c in collections], "count": len(collections)}
    except Exception as e:
        return {"error": str(e)}


# ── Redis ──
HAS_REDIS = False
try:
    import redis as redis_lib
    HAS_REDIS = True
except ImportError:
    pass

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None and HAS_REDIS:
        _redis_client = redis_lib.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    return _redis_client


async def redis_set(key: str, value: str, ttl: int | None = None) -> dict[str, Any]:
    if not HAS_REDIS:
        return {"error": "redis not installed"}
    try:
        r = _get_redis()
        if ttl:
            await asyncio.get_event_loop().run_in_executor(None, lambda: r.setex(key, ttl, value))
        else:
            await asyncio.get_event_loop().run_in_executor(None, lambda: r.set(key, value))
        return {"key": key, "ttl": ttl}
    except Exception as e:
        return {"error": str(e)}


async def redis_get(key: str) -> dict[str, Any]:
    if not HAS_REDIS:
        return {"error": "redis not installed"}
    try:
        r = _get_redis()
        value = await asyncio.get_event_loop().run_in_executor(None, lambda: r.get(key))
        if value is None:
            return {"key": key, "exists": False}
        return {"key": key, "value": value.decode(), "exists": True}
    except Exception as e:
        return {"error": str(e)}


async def redis_delete(key: str) -> dict[str, Any]:
    if not HAS_REDIS:
        return {"error": "redis not installed"}
    try:
        r = _get_redis()
        deleted = await asyncio.get_event_loop().run_in_executor(None, lambda: r.delete(key))
        return {"key": key, "deleted": bool(deleted)}
    except Exception as e:
        return {"error": str(e)}


async def redis_list_keys(pattern: str = "*") -> dict[str, Any]:
    if not HAS_REDIS:
        return {"error": "redis not installed"}
    try:
        r = _get_redis()
        keys = await asyncio.get_event_loop().run_in_executor(None, lambda: r.keys(pattern))
        return {"keys": [k.decode() for k in keys], "count": len(keys)}
    except Exception as e:
        return {"error": str(e)}


# ── MongoDB (pymongo) ──
HAS_MONGO = False
try:
    from pymongo import MongoClient
    HAS_MONGO = True
except ImportError:
    pass


_mongo_client = None


def _get_mongo():
    global _mongo_client
    if _mongo_client is None and HAS_MONGO:
        _mongo_client = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return _mongo_client


async def mongo_find(db: str, collection: str, query: dict | None = None, limit: int = 10) -> dict[str, Any]:
    if not HAS_MONGO:
        return {"error": "pymongo not installed"}
    try:
        q = query or {}
        coll = _get_mongo()[db][collection]
        docs = await asyncio.get_event_loop().run_in_executor(None, lambda: list(coll.find(q).limit(limit)))
        for d in docs:
            d["_id"] = str(d["_id"])
        return {"db": db, "collection": collection, "documents": docs, "count": len(docs)}
    except Exception as e:
        return {"error": str(e)}


async def mongo_insert(db: str, collection: str, document: dict) -> dict[str, Any]:
    if not HAS_MONGO:
        return {"error": "pymongo not installed"}
    try:
        coll = _get_mongo()[db][collection]
        result = await asyncio.get_event_loop().run_in_executor(None, lambda: coll.insert_one(document))
        return {"db": db, "collection": collection, "inserted_id": str(result.inserted_id)}
    except Exception as e:
        return {"error": str(e)}


# ── SQLModel ──
HAS_SQLMODEL = False
try:
    from sqlmodel import SQLModel, create_engine, Session, select
    HAS_SQLMODEL = True
except ImportError:
    pass


async def sqlmodel_query(table: str, condition: str | None = None) -> dict[str, Any]:
    if not HAS_SQLMODEL:
        return {"error": "sqlmodel not installed"}
    # SQLModel requires model classes; this wraps raw SQL as fallback
    import sqlite3
    db_path = os.environ.get("SQLMODEL_DB", "friday_memory/friday.db")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        sql = f"SELECT * FROM {table}"
        if condition:
            sql += f" WHERE {condition}"
        cursor.execute(sql)
        rows = cursor.fetchmany(100)
        cols = [d[0] for d in cursor.description]
        conn.close()
        return {"table": table, "columns": cols, "rows": [dict(zip(cols, r)) for r in rows], "count": len(rows)}
    except Exception as e:
        return {"error": str(e)}


# ── Elasticsearch ──
HAS_ES = False
try:
    from elasticsearch import Elasticsearch
    HAS_ES = True
except ImportError:
    pass


async def elasticsearch_search(index: str, query: dict, limit: int = 10) -> dict[str, Any]:
    if not HAS_ES:
        return {"error": "elasticsearch not installed"}
    try:
        es = Elasticsearch(os.environ.get("ES_URL", "http://localhost:9200"))
        result = await asyncio.get_event_loop().run_in_executor(
            None, lambda: es.search(index=index, body={"query": query, "size": limit}))
        hits = result["hits"]["hits"]
        return {"index": index, "total": result["hits"]["total"]["value"],
                "results": [{**h["_source"], "_id": h["_id"], "_score": h["_score"]} for h in hits]}
    except Exception as e:
        return {"error": str(e)}
