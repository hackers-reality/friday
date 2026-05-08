"""
Friday Distributed Computing - Parallel processing and clustering.
MapReduce, distributed tasks, cluster management.
"""
from __future__ import annotations

import os
import json
import time
import math
import queue
import threading
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field


# ─── Task ───────────────────────────────────#

@dataclass
class DistributedTask:
    """A task for distributed execution."""
    task_id: str
    function: str  # Function name or serialized
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Any = None
    error: Optional[str] = None
    submitted_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "function": self.function,
            "args": self.args,
            "kwargs": self.kwargs,
            "status": self.status,
            "result": str(self.result)[:100] if self.result else None,
            "error": self.error,
            "duration": (self.completed_at - self.submitted_at) if self.completed_at else None,
        }


# ─── Worker Node ───────────────────────────────────#

class WorkerNode:
    """A worker in the distributed system."""
    
    def __init__(self, node_id: str, host: str = "localhost", port: int = 0):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.status = "idle"  # idle, busy, offline
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.last_heartbeat = time.time()
        self.capabilities: List[str] = ["python"]
        
    def execute_task(self, task: DistributedTask) -> Any:
        """Execute a task (simplified - local execution)."""
        try:
            # In reality, would use RPC/HTTP
            # Here we just simulate
            self.status = "busy"
            task.status = "running"
            
            # Simulate work
            time.sleep(0.1)
            
            # Mock result
            result = f"Result from {self.node_id} for {task.task_id}"
            
            task.result = result
            task.status = "completed"
            task.completed_at = time.time()
            self.tasks_completed += 1
            self.status = "idle"
            
            return result
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed += 1
            self.status = "idle"
            raise
    
    def heartbeat(self):
        """Update heartbeat."""
        self.last_heartbeat = time.time()
        
    def is_alive(self, timeout: float = 30.0) -> bool:
        """Check if worker is alive."""
        return (time.time() - self.last_heartbeat) < timeout
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "alive": self.is_alive(),
        }


# ─── Cluster Manager ───────────────────────────────────#

class ClusterManager:
    """Manages a cluster of worker nodes."""
    
    def __init__(self, cluster_id: str = "default"):
        self.cluster_id = cluster_id
        self.workers: Dict[str, WorkerNode] = {}
        self.task_queue: queue.Queue[DistributedTask] = queue.Queue()
        self.completed_tasks: Dict[str, DistributedTask] = {}
        self.failed_tasks: Dict[str, DistributedTask] = {}
        self._running = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
    def add_worker(self, node: WorkerNode) -> bool:
        """Add a worker to the cluster."""
        if node.node_id in self.workers:
            return False
        self.workers[node.node_id] = node
        return True
    
    def remove_worker(self, node_id: str) -> bool:
        """Remove a worker."""
        if node_id not in self.workers:
            return False
        del self.workers[node_id]
        return True
    
    def submit_task(self, task: DistributedTask):
        """Submit a task for execution."""
        self.task_queue.put(task)
        
    def get_available_worker(self) -> Optional[WorkerNode]:
        """Get an idle worker."""
        for worker in self.workers.values():
            if worker.status == "idle" and worker.is_alive():
                return worker
        return None
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        with ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
            while self._running:
                try:
                    task = self.task_queue.get(timeout=1.0)
                    
                    worker = self.get_available_worker()
                    if not worker:
                        # No workers available, re-queue
                        self.task_queue.put(task)
                        time.sleep(0.5)
                        continue
                    
                    # Submit to worker (simulated)
                    future = executor.submit(worker.execute_task, task)
                    
                    # Check result
                    try:
                        result = future.result(timeout=60)
                        self.completed_tasks[task.task_id] = task
                    except Exception as e:
                        self.failed_tasks[task.task_id] = task
                        
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"[Cluster] Scheduler error: {e}")
    
    def start(self):
        """Start the cluster."""
        if self._running:
            return
        self._running = True
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self._scheduler_thread.start()
        print(f"[Cluster] Started: {self.cluster_id}")
    
    def stop(self):
        """Stop the cluster."""
        self._running = False
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        print(f"[Cluster] Stopped: {self.cluster_id}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get cluster status."""
        total_workers = len(self.workers)
        alive = sum(1 for w in self.workers.values() if w.is_alive())
        idle = sum(1 for w in self.workers.values() if w.status == "idle")
        
        return {
            "cluster_id": self.cluster_id,
            "total_workers": total_workers,
            "alive_workers": alive,
            "idle_workers": idle,
            "busy_workers": total_workers - idle,
            "pending_tasks": self.task_queue.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "running": self._running,
        }


# ─── MapReduce ───────────────────────────────────#

class MapReduce:
    """MapReduce implementation."""
    
    def __init__(self, num_reducers: int = 3):
        self.num_reducers = num_reducers
        
    def _map_phase(
        self,
        data: List[Any],
        map_func: Callable[[Any], Tuple[str, Any]]
    ) -> Dict[str, List[Any]]:
        """Execute map phase."""
        intermediate: Dict[str, List[Any]] = {}
        
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(map_func, data))
            
        for key, value in results:
            if key not in intermediate:
                intermediate[key] = []
            intermediate[key].append(value)
            
        return intermediate
    
    def _reduce_phase(
        self,
        intermediate: Dict[str, List[Any]],
        reduce_func: Callable[[str, List[Any]], Any]
    ) -> Dict[str, Any]:
        """Execute reduce phase."""
        results = {}
        
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(reduce_func, key, values): key
                for key, values in intermediate.items()
            }
            
            for future in futures:
                key = futures[future]
                results[key] = future.result()
            
        return results
    
    def execute(
        self,
        data: List[Any],
        map_func: Callable[[Any], Tuple[str, Any]],
        reduce_func: Callable[[str, List[Any]], Any]
    ) -> Dict[str, Any]:
        """Execute MapReduce job."""
        print(f"[MapReduce] Starting with {len(data)} items...")
        
        # Map
        print("[MapReduce] Map phase...")
        intermediate = self._map_phase(data, map_func)
        print(f"[MapReduce] Map complete: {len(intermediate)} keys")
        
        # Reduce
        print("[MapReduce] Reduce phase...")
        results = self._reduce_phase(intermediate, reduce_func)
        print(f"[MapReduce] Reduce complete: {len(results)} results")
        
        return results


# ─── Distributed Lock ───────────────────────────────────#

class DistributedLock:
    """Simple distributed lock (simulated)."""
    
    def __init__(self, lock_id: str):
        self.lock_id = lock_id
        self._lock = threading.Lock()
        self._owner: Optional[str] = None
        
    def acquire(self, worker_id: str, timeout: float = 10.0) -> bool:
        """Acquire the lock."""
        acquired = self._lock.acquire(timeout=timeout)
        if acquired:
            self._owner = worker_id
        return acquired
    
    def release(self, worker_id: str) -> bool:
        """Release the lock."""
        if self._owner != worker_id:
            return False
        self._owner = None
        self._lock.release()
        return True
    
    def get_owner(self) -> Optional[str]:
        return self._owner


# ─── Singleton Cluster ───────────────────────────────────#

_clusters: Dict[str, ClusterManager] = {}

def get_cluster(cluster_id: str = "default") -> ClusterManager:
    """Get or create a cluster."""
    if cluster_id not in _clusters:
        _clusters[cluster_id] = ClusterManager(cluster_id)
    return _clusters[cluster_id]


# ─── Tool Function for Friday ────────────────────────────────────#

def distributed_tool(
    action: str = "status",
    cluster_id: str = "default",
    node_id: str = None,
    task_id: str = None,
) -> str:
    """
    Friday tool for distributed computing.
    Actions: status, add_worker, submit_task, mapreduce, lock
    """
    if action == "status":
        cluster = get_cluster(cluster_id)
        status = cluster.get_status()
        
        lines = [f"### CLUSTER: {cluster_id.upper()}", ""]
        lines.append(f"**Workers**: {status['alive_workers']}/{status['total_workers']} alive")
        lines.append(f"**Idle**: {status['idle_workers']}")
        lines.append(f"**Busy**: {status['busy_workers']}")
        lines.append(f"**Pending Tasks**: {status['pending_tasks']}")
        lines.append(f"**Completed**: {status['completed_tasks']}")
        lines.append(f"**Failed**: {status['failed_tasks']}")
        return "\n".join(lines)
    
    if action == "add_worker":
        if not node_id:
            return "[FAIL] node_id required."
        
        cluster = get_cluster(cluster_id)
        worker = WorkerNode(node_id)
        if cluster.add_worker(worker):
            return f"[OK] Added worker: {node_id}"
        return f"[FAIL] Worker already exists: {node_id}"
    
    if action == "submit_task":
        if not task_id:
            return "[FAIL] task_id required."
        
        cluster = get_cluster(cluster_id)
        task = DistributedTask(task_id, "default_func")
        cluster.submit_task(task)
        return f"[OK] Task {task_id} submitted."
    
    if action == "mapreduce":
        if not task_id:  # Reuse param for data JSON
            return "[FAIL] data (as JSON) required in task_id."
        
        try:
            data = json.loads(task_id)
        except:
            return "[FAIL] Invalid data format. Use JSON array."
        
        # Example map/reduce for word count
        def map_func(doc):
            words = doc.lower().split()
            for word in words:
                return (word, 1)
        
        def reduce_func(key, values):
            return sum(values)
        
        mr = MapReduce()
        results = mr.execute(data, map_func, reduce_func)
        
        lines = ["### MAPREDUCE RESULTS", ""]
        for key, value in sorted(results.items()):
            lines.append(f"**{key}**: {value}")
        return "\n".join(lines)
    
    if action == "lock":
        if not task_id or not node_id:  # Reuse params
            return "[FAIL] lock_id (task_id) and worker_id required."
        
        lock = DistributedLock(task_id)
        if "acquire" in node_id:
            acquired = lock.acquire("worker1")
            return f"{'[OK]' if acquired else '[FAIL]'} Lock {task_id} acquired."
        elif "release" in node_id:
            released = lock.release("worker1")
            return f"{'[OK]' if released else '[FAIL]'} Lock {task_id} released."
        return f"Unknown lock action: {node_id}"
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Distributed Computing...\n")
    
    # Test cluster
    cluster = get_cluster("test")
    
    print("--- Adding Workers ---")
    print(distributed_tool("add_worker", node_id="worker1"))
    print(distributed_tool("add_worker", node_id="worker2"))
    
    print("\n--- Cluster Status ---")
    print(distributed_tool("status"))
    
    print("\n--- Submit Task ---")
    print(distributed_tool("submit_task", task_id="task1"))
    
    print("\n--- MapReduce (Word Count) ---")
    data = ["hello world", "hello friday", "world of ai"]
    print(distributed_tool("mapreduce", task_id=json.dumps(data)))
