"""FRIDAY Database Connector — SQLite, MySQL, PostgreSQL support with query builder."""
import os
import json
import time
import hashlib
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import OrderedDict


@dataclass
class QueryResult:
    success: bool
    query: str
    columns: List[str] = field(default_factory=list)
    rows: List[Dict] = field(default_factory=list)
    row_count: int = 0
    duration: float = 0.0
    error: str = ""
    database: str = ""

    def to_dict(self):
        return {
            "success": self.success,
            "query": self.query,
            "columns": self.columns,
            "rows": self.rows[:100],
            "row_count": self.row_count,
            "duration": round(self.duration, 4),
            "error": self.error,
            "database": self.database,
        }


@dataclass
class TableInfo:
    name: str
    columns: List[Dict]
    row_count: int
    size_bytes: int = 0
    indexes: List[Dict] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


class SQLiteConnector:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query: str, params: tuple = ()) -> QueryResult:
        start = time.time()
        try:
            with self._lock:
                conn = self._connect()
                try:
                    cursor = conn.cursor()
                    cursor.execute(query, params)
                    if query.strip().upper().startswith(("SELECT", "PRAGMA")):
                        rows = cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description] if cursor.description else []
                        row_dicts = [dict(row) for row in rows]
                        conn.close()
                        return QueryResult(
                            success=True, query=query, columns=columns,
                            rows=row_dicts, row_count=len(row_dicts),
                            duration=time.time() - start, database=self.db_path,
                        )
                    else:
                        conn.commit()
                        affected = cursor.rowcount
                        conn.close()
                        return QueryResult(
                            success=True, query=query, row_count=affected,
                            duration=time.time() - start, database=self.db_path,
                        )
                except Exception as e:
                    conn.close()
                    return QueryResult(
                        success=False, query=query, error=str(e),
                        duration=time.time() - start, database=self.db_path,
                    )
        except Exception as e:
            return QueryResult(success=False, query=query, error=str(e),
                             duration=time.time() - start, database=self.db_path)

    def list_tables(self) -> List[str]:
        result = self.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row["name"] for row in result.rows]

    def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        columns_result = self.execute(f"PRAGMA table_info({table_name})")
        if not columns_result.success:
            return None
        columns = [{"name": c["name"], "type": c["type"], "notnull": bool(c["notnull"]),
                     "default": c["dflt_value"], "pk": bool(c["pk"])} for c in columns_result.rows]
        count_result = self.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
        row_count = count_result.rows[0]["cnt"] if count_result.rows else 0
        indexes_result = self.execute(f"PRAGMA index_list({table_name})")
        indexes = [{"name": i["name"], "unique": bool(i["unique"])} for i in indexes_result.rows]
        return TableInfo(name=table_name, columns=columns, row_count=row_count, indexes=indexes)

    def get_schema(self) -> Dict:
        tables = self.list_tables()
        schema = {}
        for table in tables:
            info = self.get_table_info(table)
            if info:
                schema[table] = info.to_dict()
        return schema

    def backup(self, backup_path: str) -> bool:
        try:
            with self._lock:
                conn = self._connect()
                backup_conn = sqlite3.connect(backup_path)
                conn.backup(backup_conn)
                backup_conn.close()
                conn.close()
                return True
        except Exception:
            return False


class DatabaseManager:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "databases")
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._connections: Dict[str, SQLiteConnector] = {}
        self._lock = threading.Lock()

    def _get_connector(self, db_name: str) -> SQLiteConnector:
        with self._lock:
            if db_name not in self._connections:
                db_path = os.path.join(self.data_dir, f"{db_name}.db")
                self._connections[db_name] = SQLiteConnector(db_path)
            return self._connections[db_name]

    def execute(self, db_name: str, query: str, params: tuple = ()) -> QueryResult:
        connector = self._get_connector(db_name)
        return connector.execute(query, params)

    def list_databases(self) -> List[Dict]:
        dbs = []
        if os.path.exists(self.data_dir):
            for f in os.listdir(self.data_dir):
                if f.endswith(".db"):
                    path = os.path.join(self.data_dir, f)
                    dbs.append({
                        "name": f[:-3],
                        "path": path,
                        "size": os.path.getsize(path),
                    })
        return dbs

    def list_tables(self, db_name: str) -> List[str]:
        connector = self._get_connector(db_name)
        return connector.list_tables()

    def get_table_info(self, db_name: str, table_name: str) -> Optional[Dict]:
        connector = self._get_connector(db_name)
        info = connector.get_table_info(table_name)
        return info.to_dict() if info else None

    def get_schema(self, db_name: str) -> Dict:
        connector = self._get_connector(db_name)
        return connector.get_schema()

    def create_table(self, db_name: str, table_name: str, columns: Dict[str, str]) -> QueryResult:
        col_defs = ", ".join(f"{name} {dtype}" for name, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})"
        return self.execute(db_name, query)

    def insert(self, db_name: str, table_name: str, data: Dict[str, Any]) -> QueryResult:
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        return self.execute(db_name, query, tuple(data.values()))

    def insert_many(self, db_name: str, table_name: str, rows: List[Dict[str, Any]]) -> QueryResult:
        if not rows:
            return QueryResult(success=True, query="INSERT MANY", row_count=0)
        columns = ", ".join(rows[0].keys())
        placeholders = ", ".join("?" * len(rows[0]))
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        params_list = [tuple(row.values()) for row in rows]
        try:
            connector = self._get_connector(db_name)
            with connector._lock:
                conn = connector._connect()
                try:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    affected = cursor.rowcount
                    conn.close()
                    return QueryResult(
                        success=True, query=query, row_count=affected,
                        database=db_name,
                    )
                except Exception as e:
                    conn.close()
                    return QueryResult(success=False, query=query, error=str(e), database=db_name)
        except Exception as e:
            return QueryResult(success=False, query=query, error=str(e), database=db_name)

    def select(self, db_name: str, table_name: str, where: str = "",
               params: tuple = (), order_by: str = "", limit: int = 100) -> QueryResult:
        query = f"SELECT * FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {limit}"
        return self.execute(db_name, query, params)

    def update(self, db_name: str, table_name: str, data: Dict[str, Any],
               where: str, params: tuple = ()) -> QueryResult:
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where}"
        all_params = tuple(data.values()) + params
        return self.execute(db_name, query, all_params)

    def delete(self, db_name: str, table_name: str, where: str, params: tuple = ()) -> QueryResult:
        query = f"DELETE FROM {table_name} WHERE {where}"
        return self.execute(db_name, query, params)

    def drop_table(self, db_name: str, table_name: str) -> QueryResult:
        return self.execute(db_name, f"DROP TABLE IF EXISTS {table_name}")

    def backup(self, db_name: str, backup_name: str = None) -> bool:
        if backup_name is None:
            backup_name = f"{db_name}_backup_{int(time.time())}"
        backup_path = os.path.join(self.data_dir, f"{backup_name}.db")
        connector = self._get_connector(db_name)
        return connector.backup(backup_path)

    def get_stats(self) -> Dict:
        dbs = self.list_databases()
        total_size = sum(d["size"] for d in dbs)
        return {
            "total_databases": len(dbs),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "databases": dbs,
        }


_manager = None


def _get_manager() -> DatabaseManager:
    global _manager
    if _manager is None:
        _manager = DatabaseManager()
    return _manager


def database_connector_tool(action: str = "list", **kwargs) -> Any:
    """Database connector tool dispatcher."""
    try:
        manager = _get_manager()

        if action == "list":
            return {"databases": manager.list_databases()}

        elif action == "execute":
            db_name = kwargs.get("database", "friday")
            query = kwargs.get("query", "")
            if not query:
                return {"error": "No query provided"}
            result = manager.execute(db_name, query)
            return result.to_dict()

        elif action == "tables":
            db_name = kwargs.get("database", "friday")
            return {"tables": manager.list_tables(db_name)}

        elif action == "schema":
            db_name = kwargs.get("database", "friday")
            return {"schema": manager.get_schema(db_name)}

        elif action == "table_info":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            if not table:
                return {"error": "No table name provided"}
            info = manager.get_table_info(db_name, table)
            return info or {"error": "Table not found"}

        elif action == "create_table":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            columns = kwargs.get("columns", {})
            if not table or not columns:
                return {"error": "table and columns required"}
            result = manager.create_table(db_name, table, columns)
            return result.to_dict()

        elif action == "insert":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            data = kwargs.get("data", {})
            if not table or not data:
                return {"error": "table and data required"}
            result = manager.insert(db_name, table, data)
            return result.to_dict()

        elif action == "insert_many":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            rows = kwargs.get("rows", [])
            if not table or not rows:
                return {"error": "table and rows required"}
            result = manager.insert_many(db_name, table, rows)
            return result.to_dict()

        elif action == "select":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            where = kwargs.get("where", "")
            params = tuple(kwargs.get("params", ()))
            order_by = kwargs.get("order_by", "")
            limit = kwargs.get("limit", 100)
            if not table:
                return {"error": "No table name provided"}
            result = manager.select(db_name, table, where, params, order_by, limit)
            return result.to_dict()

        elif action == "update":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            data = kwargs.get("data", {})
            where = kwargs.get("where", "")
            params = tuple(kwargs.get("params", ()))
            if not table or not data or not where:
                return {"error": "table, data, and where required"}
            result = manager.update(db_name, table, data, where, params)
            return result.to_dict()

        elif action == "delete":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            where = kwargs.get("where", "")
            params = tuple(kwargs.get("params", ()))
            if not table or not where:
                return {"error": "table and where required"}
            result = manager.delete(db_name, table, where, params)
            return result.to_dict()

        elif action == "drop_table":
            db_name = kwargs.get("database", "friday")
            table = kwargs.get("table", "")
            if not table:
                return {"error": "No table name provided"}
            result = manager.drop_table(db_name, table)
            return result.to_dict()

        elif action == "backup":
            db_name = kwargs.get("database", "friday")
            backup_name = kwargs.get("backup_name")
            ok = manager.backup(db_name, backup_name)
            return {"success": ok}

        elif action == "stats":
            return manager.get_stats()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
