"""FRIDAY Backup System — automated backups with rotation, compression, and restore."""
import os
import json
import time
import shutil
import hashlib
import threading
import zipfile
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class BackupEntry:
    backup_id: str
    name: str
    source_path: str
    backup_path: str
    created_at: float
    size_bytes: int = 0
    compressed: bool = True
    checksum: str = ""
    status: str = "completed"
    error: str = ""
    metadata: Dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class BackupSchedule:
    name: str
    source_path: str
    interval_hours: int
    max_backups: int = 10
    compressed: bool = True
    enabled: bool = True
    last_run: float = 0.0
    next_run: float = 0.0

    def to_dict(self):
        return asdict(self)


class BackupSystem:
    def __init__(self, backup_dir: str = None, data_dir: str = None):
        if backup_dir is None:
            backup_dir = os.path.join(os.path.expanduser("~"), ".friday", "backups")
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".friday", "backup_config")

        self.backup_dir = backup_dir
        self.data_dir = data_dir
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        self._backups: Dict[str, BackupEntry] = {}
        self._schedules: Dict[str, BackupSchedule] = {}
        self._lock = threading.Lock()

        self._load_backups()
        self._load_schedules()

    def _backups_file(self) -> str:
        return os.path.join(self.data_dir, "backups.json")

    def _schedules_file(self) -> str:
        return os.path.join(self.data_dir, "schedules.json")

    def _load_backups(self):
        if os.path.exists(self._backups_file()):
            try:
                with open(self._backups_file(), "r") as f:
                    data = json.load(f)
                for bid, bdata in data.items():
                    self._backups[bid] = BackupEntry(**bdata)
            except Exception:
                pass

    def _save_backups(self):
        try:
            data = {bid: b.to_dict() for bid, b in self._backups.items()}
            with open(self._backups_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _load_schedules(self):
        if os.path.exists(self._schedules_file()):
            try:
                with open(self._schedules_file(), "r") as f:
                    data = json.load(f)
                for name, sdata in data.items():
                    self._schedules[name] = BackupSchedule(**sdata)
            except Exception:
                pass

    def _save_schedules(self):
        try:
            data = {name: s.to_dict() for name, s in self._schedules.items()}
            with open(self._schedules_file(), "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def _calculate_checksum(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""

    def _get_dir_size(self, path: str) -> int:
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
        except Exception:
            pass
        return total

    def create_backup(self, name: str, source_path: str, compressed: bool = True,
                     metadata: Dict = None) -> Dict:
        if not os.path.exists(source_path):
            return {"error": f"Source path not found: {source_path}"}

        backup_id = f"backup-{int(time.time())}-{hashlib.md5(name.encode()).hexdigest()[:6]}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name}_{timestamp}"

        if compressed:
            backup_path = os.path.join(self.backup_dir, f"{backup_name}.zip")
            try:
                with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    if os.path.isfile(source_path):
                        zf.write(source_path, os.path.basename(source_path))
                    else:
                        for root, dirs, files in os.walk(source_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, source_path)
                                zf.write(file_path, arcname)
                size = os.path.getsize(backup_path)
            except Exception as e:
                return {"error": str(e)}
        else:
            backup_path = os.path.join(self.backup_dir, backup_name)
            try:
                if os.path.isfile(source_path):
                    shutil.copy2(source_path, backup_path)
                else:
                    shutil.copytree(source_path, backup_path)
                size = self._get_dir_size(backup_path)
            except Exception as e:
                return {"error": str(e)}

        checksum = self._calculate_checksum(backup_path) if os.path.isfile(backup_path) else ""

        entry = BackupEntry(
            backup_id=backup_id,
            name=name,
            source_path=source_path,
            backup_path=backup_path,
            created_at=time.time(),
            size_bytes=size,
            compressed=compressed,
            checksum=checksum,
            metadata=metadata or {},
        )

        with self._lock:
            self._backups[backup_id] = entry
            self._save_backups()

        return entry.to_dict()

    def restore_backup(self, backup_id: str, restore_path: str = None) -> Dict:
        entry = self._backups.get(backup_id)
        if not entry:
            return {"error": f"Backup not found: {backup_id}"}

        if restore_path is None:
            restore_path = entry.source_path

        try:
            if entry.compressed and entry.backup_path.endswith(".zip"):
                os.makedirs(restore_path, exist_ok=True)
                with zipfile.ZipFile(entry.backup_path, "r") as zf:
                    zf.extractall(restore_path)
            else:
                if os.path.isfile(entry.backup_path):
                    os.makedirs(os.path.dirname(restore_path), exist_ok=True)
                    shutil.copy2(entry.backup_path, restore_path)
                else:
                    if os.path.exists(restore_path):
                        shutil.rmtree(restore_path)
                    shutil.copytree(entry.backup_path, restore_path)

            return {"success": True, "restored_to": restore_path}
        except Exception as e:
            return {"error": str(e)}

    def delete_backup(self, backup_id: str) -> bool:
        entry = self._backups.get(backup_id)
        if not entry:
            return False

        try:
            if os.path.exists(entry.backup_path):
                if os.path.isfile(entry.backup_path):
                    os.remove(entry.backup_path)
                else:
                    shutil.rmtree(entry.backup_path)
        except Exception:
            pass

        with self._lock:
            if backup_id in self._backups:
                del self._backups[backup_id]
                self._save_backups()
            return True

    def list_backups(self, name: str = None) -> List[Dict]:
        with self._lock:
            backups = list(self._backups.values())
        if name:
            backups = [b for b in backups if b.name == name]
        return [b.to_dict() for b in sorted(backups, key=lambda b: b.created_at, reverse=True)]

    def add_schedule(self, schedule: BackupSchedule):
        with self._lock:
            if schedule.next_run == 0:
                schedule.next_run = time.time() + schedule.interval_hours * 3600
            self._schedules[schedule.name] = schedule
            self._save_schedules()

    def remove_schedule(self, name: str) -> bool:
        with self._lock:
            if name in self._schedules:
                del self._schedules[name]
                self._save_schedules()
                return True
            return False

    def list_schedules(self) -> List[Dict]:
        with self._lock:
            return [s.to_dict() for s in self._schedules.values()]

    def run_schedules(self) -> List[Dict]:
        now = time.time()
        results = []
        with self._lock:
            for name, schedule in self._schedules.items():
                if schedule.enabled and schedule.next_run <= now:
                    result = self.create_backup(
                        schedule.name, schedule.source_path, schedule.compressed
                    )
                    schedule.last_run = now
                    schedule.next_run = now + schedule.interval_hours * 3600
                    results.append(result)

                    backups = [b for b in self._backups.values() if b.name == name]
                    if len(backups) > schedule.max_backups:
                        oldest = sorted(backups, key=lambda b: b.created_at)[:-schedule.max_backups]
                        for b in oldest:
                            self.delete_backup(b.backup_id)

            self._save_schedules()
        return results

    def get_stats(self) -> Dict:
        with self._lock:
            backups = list(self._backups.values())
            total_size = sum(b.size_bytes for b in backups)
            return {
                "total_backups": len(backups),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "schedules": len(self._schedules),
                "backup_dir": self.backup_dir,
            }


_system = None


def _get_system() -> BackupSystem:
    global _system
    if _system is None:
        _system = BackupSystem()
    return _system


def backup_system_tool(action: str = "list", **kwargs) -> Any:
    """Backup system tool dispatcher."""
    try:
        system = _get_system()

        if action == "create":
            name = kwargs.get("name", "")
            source = kwargs.get("source", "")
            compressed = kwargs.get("compressed", True)
            if not name or not source:
                return {"error": "name and source required"}
            return system.create_backup(name, source, compressed)

        elif action == "restore":
            backup_id = kwargs.get("backup_id", "")
            restore_path = kwargs.get("restore_path")
            if not backup_id:
                return {"error": "backup_id required"}
            return system.restore_backup(backup_id, restore_path)

        elif action == "delete":
            backup_id = kwargs.get("backup_id", "")
            if not backup_id:
                return {"error": "backup_id required"}
            ok = system.delete_backup(backup_id)
            return {"success": ok}

        elif action == "list":
            name = kwargs.get("name")
            return {"backups": system.list_backups(name)}

        elif action == "add_schedule":
            schedule_data = kwargs.get("schedule", {})
            schedule = BackupSchedule(**schedule_data)
            system.add_schedule(schedule)
            return {"success": True}

        elif action == "remove_schedule":
            name = kwargs.get("name", "")
            ok = system.remove_schedule(name)
            return {"success": ok}

        elif action == "schedules":
            return {"schedules": system.list_schedules()}

        elif action == "run_schedules":
            results = system.run_schedules()
            return {"executed": len(results), "results": results}

        elif action == "stats":
            return system.get_stats()

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e)}
