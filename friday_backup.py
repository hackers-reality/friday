"""
Friday Backup - Backup and recovery.
File backup, database backup, cloud backup, restore.
"""
from __future__ import annotations

import os
import sys
import json
import shutil
import tarfile
import zipfile
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import tempfile


# ─── File Backup ────────────────────────────#

class FileBackup:
    """Backup files and directories."""
    
    def __init__(self, backup_dir: str = None):
        self.backup_dir = Path(backup_dir) if backup_dir else Path.home() / ".friday" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def backup_file(self, file_path: str, backup_name: str = None) -> Dict[str, Any]:
        """Backup a single file."""
        source = Path(file_path)
        if not source.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"{source.stem}_{timestamp}{source.suffix}"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(source, backup_path)
            
            return {
                "success": True,
                "source": str(source),
                "backup": str(backup_path),
                "size": backup_path.stat().st_size,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def backup_directory(
        self,
        dir_path: str,
        format: str = "zip",
        backup_name: str = None,
    ) -> Dict[str, Any]:
        """Backup a directory."""
        source = Path(dir_path)
        if not source.exists() or not source.is_dir():
            return {"success": False, "error": f"Directory not found: {dir_path}"}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = backup_name or f"{source.name}_{timestamp}"
            
            if format == "zip":
                backup_path = self.backup_dir / f"{backup_name}.zip"
                with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in source.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(source)
                            zipf.write(file_path, arcname)
            
            elif format == "tar":
                backup_path = self.backup_dir / f"{backup_name}.tar.gz"
                with tarfile.open(backup_path, "w:gz") as tarf:
                    tarf.add(str(source), arcname=source.name)
            
            else:
                return {"success": False, "error": f"Unknown format: {format}"}
            
            return {
                "success": True,
                "source": str(source),
                "backup": str(backup_path),
                "size": backup_path.stat().st_size,
                "format": format,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups."""
        backups = []
        for backup_file in self.backup_dir.iterdir():
            if backup_file.is_file():
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size": backup_file.stat().st_size,
                    "modified": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                })
        return sorted(backups, key=lambda x: x["modified"], reverse=True)
    
    def restore_file(self, backup_name: str, restore_path: str = None) -> Dict[str, Any]:
        """Restore a file from backup."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return {"success": False, "error": f"Backup not found: {backup_name}"}
        
        try:
            restore_path = Path(restore_path) if restore_path else Path.cwd() / backup_path.name
            shutil.copy2(backup_path, restore_path)
            
            return {
                "success": True,
                "backup": str(backup_path),
                "restored_to": str(restore_path),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def restore_directory(self, backup_name: str, restore_path: str) -> Dict[str, Any]:
        """Restore a directory from backup."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return {"success": False, "error": f"Backup not found: {backup_name}"}
        
        try:
            restore_dir = Path(restore_path)
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            if backup_path.suffix == ".zip":
                with zipfile.ZipFile(backup_path, "r") as zipf:
                    zipf.extractall(restore_dir)
            
            elif backup_path.suffix in (".tar", ".gz"):
                with tarfile.open(backup_path, "r:*") as tarf:
                    tarf.extractall(restore_dir)
            
            else:
                return {"success": False, "error": "Unknown backup format"}
            
            return {
                "success": True,
                "backup": str(backup_path),
                "restored_to": str(restore_dir),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Database Backup ────────────────────────────#

class DatabaseBackup:
    """Backup databases."""
    
    def backup_sqlite(self, db_path: str, backup_path: str = None) -> Dict[str, Any]:
        """Backup SQLite database."""
        source = Path(db_path)
        if not source.exists():
            return {"success": False, "error": f"Database not found: {db_path}"}
        
        try:
            backup_path = backup_path or f"{source.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            import sqlite3
            source_conn = sqlite3.connect(str(source))
            backup_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(backup_conn)
            
            backup_conn.close()
            source_conn.close()
            
            return {
                "success": True,
                "source": str(source),
                "backup": backup_path,
                "size": Path(backup_path).stat().st_size,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def backup_postgres(self, db_name: str, backup_path: str = None) -> Dict[str, Any]:
        """Backup PostgreSQL database (simplified)."""
        try:
            backup_path = backup_path or f"{db_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            
            cmd = f"pg_dump {db_name} > {backup_path}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "database": db_name,
                    "backup": backup_path,
                }
            else:
                return {"success": False, "error": result.stderr.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Cloud Backup (Simplified) ────────────────────────────#

class CloudBackup:
    """Backup to cloud storage (simplified)."""
    
    def __init__(self, provider: str = "aws"):
        self.provider = provider
        
    def backup_to_s3(self, file_path: str, bucket: str, key: str = None) -> Dict[str, Any]:
        """Backup file to AWS S3."""
        try:
            import boto3
            
            s3 = boto3.client("s3")
            key = key or Path(file_path).name
            
            s3.upload_file(file_path, bucket, key)
            
            return {
                "success": True,
                "file": file_path,
                "bucket": bucket,
                "key": key,
            }
        except ImportError:
            return {"success": False, "error": "boto3 not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def backup_to_gcs(self, file_path: str, bucket: str, blob_name: str = None) -> Dict[str, Any]:
        """Backup file to Google Cloud Storage."""
        try:
            from google.cloud import storage
            
            client = storage.Client()
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(blob_name or Path(file_path).name)
            
            blob.upload_from_filename(file_path)
            
            return {
                "success": True,
                "file": file_path,
                "bucket": bucket,
                "blob": blob.name,
            }
        except ImportError:
            return {"success": False, "error": "google-cloud-storage not available."}
        except Exception as e:
            return {"success": False, "error": str(e)}


# ─── Backup Scheduler ────────────────────────────#

class BackupScheduler:
    """Schedule automatic backups."""
    
    def __init__(self):
        self.scheduled_backups: Dict[str, Dict] = {}
        
    def schedule_backup(
        self,
        name: str,
        source: str,
        schedule_type: str = "daily",
        time: str = "02:00",
    ) -> Dict[str, Any]:
        """Schedule a backup."""
        self.scheduled_backups[name] = {
            "source": source,
            "schedule_type": schedule_type,
            "time": time,
            "created": datetime.now().isoformat(),
            "last_run": None,
            "next_run": None,
        }
        
        return {"success": True, "name": name}
    
    def list_scheduled(self) -> List[Dict[str, Any]]:
        """List scheduled backups."""
        return [
            {"name": name, **config}
            for name, config in self.scheduled_backups.items()
        ]
    
    def remove_scheduled(self, name: str) -> Dict[str, Any]:
        """Remove a scheduled backup."""
        if name in self.scheduled_backups:
            del self.scheduled_backups[name]
            return {"success": True}
        return {"success": False, "error": "Scheduled backup not found."}


# ─── Backup Tool for Friday ────────────────────────────#

def backup_tool(
    action: str = "status",
    target: str = None,
    params: Dict = None,
) -> str:
    """
    Friday tool for backup operations.
    Actions: status, file_backup, dir_backup, list, restore,
            db_backup, cloud_backup, schedule_list
    """
    params = params or {}
    
    if action == "status":
        lines = ["### BACKUP STATUS", ""]
        lines.append("**Available Features**:")
        lines.append("  - File and directory backup")
        lines.append("  - Database backup (SQLite, PostgreSQL)")
        lines.append("  - Cloud backup (S3, GCS)")
        lines.append("  - Scheduled backups")
        return "\n".join(lines)
    
    if action == "file_backup":
        if not target:
            return "[FAIL] File path required."
        backup = FileBackup()
        result = backup.backup_file(target, params.get("backup_name"))
        if result["success"]:
            return f"### FILE BACKUP\n\n[OK] Backed up to {result['backup']}\nSize: {result['size']} bytes"
        else:
            return f"[FAIL] Backup error: {result.get('error', 'Unknown')}"
    
    if action == "dir_backup":
        if not target:
            return "[FAIL] Directory path required."
        backup = FileBackup()
        format_ = params.get("format", "zip")
        result = backup.backup_directory(target, format_)
        if result["success"]:
            return f"### DIRECTORY BACKUP\n\n[OK] Backed up to {result['backup']}\nFormat: {result['format']}\nSize: {result['size']} bytes"
        else:
            return f"[FAIL] Backup error: {result.get('error', 'Unknown')}"
    
    if action == "list":
        backup = FileBackup()
        backups = backup.list_backups()
        lines = [f"### BACKUPS ({len(backups)})", ""]
        for b in backups[:10]:  # Show last 10
            lines.append(f"  - {b['name']} ({b['size']} bytes) - {b['modified'][:19]}")
        return "\n".join(lines)
    
    if action == "restore":
        if not target:
            return "[FAIL] Backup name required."
        backup = FileBackup()
        restore_path = params.get("restore_path")
        result = backup.restore_file(target, restore_path)
        if result["success"]:
            return f"### RESTORE\n\n[OK] Restored to {result['restored_to']}"
        else:
            return f"[FAIL] Restore error: {result.get('error', 'Unknown')}"
    
    if action == "db_backup":
        if not target:
            return "[FAIL] Database path required."
        db_backup = DatabaseBackup()
        result = db_backup.backup_sqlite(target)
        if result["success"]:
            return f"### DATABASE BACKUP\n\n[OK] Backed up to {result['backup']}\nSize: {result['size']} bytes"
        else:
            return f"[FAIL] Backup error: {result.get('error', 'Unknown')}"
    
    if action == "cloud_backup":
        if not target:
            return "[FAIL] File path required."
        provider = params.get("provider", "aws")
        cloud_backup = CloudBackup(provider)
        
        if provider == "aws":
            bucket = params.get("bucket")
            if not bucket:
                return "[FAIL] Bucket name required for AWS."
            result = cloud_backup.backup_to_s3(target, bucket)
        elif provider == "gcs":
            bucket = params.get("bucket")
            if not bucket:
                return "[FAIL] Bucket name required for GCS."
            result = cloud_backup.backup_to_gcs(target, bucket)
        else:
            return f"[FAIL] Unknown provider: {provider}"
        
        if result["success"]:
            return f"### CLOUD BACKUP\n\n[OK] Backed up to {result['bucket']}/{result.get('key', result.get('blob', ''))}"
        else:
            return f"[FAIL] Backup error: {result.get('error', 'Unknown')}"
    
    if action == "schedule_list":
        scheduler = BackupScheduler()
        scheduled = scheduler.list_scheduled()
        lines = [f"### SCHEDULED BACKUPS ({len(scheduled)})", ""]
        for s in scheduled:
            lines.append(f"  - {s['name']}: {s['source']} ({s['schedule_type']} at {s['time']})")
        return "\n".join(lines)
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Friday Backup...\n")
    
    # Test file backup
    print("--- File Backup ---")
    print(backup_tool("file_backup", target="friday_analytics.py"))
    
    # Test list
    print("\n--- List Backups ---")
    print(backup_tool("list"))
