"""Background VRAM monitor for ComfyUI process trees.

Silently logs per-second VRAM samples to ~/vramlogs/ as CSV.
Tracks peak VRAM across the session.
"""
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional


VRAMLOGS_DIR = Path.home() / "vramlogs"


def _get_descendant_pids(root_pid: int) -> set[int]:
    """Get all descendant PIDs of root_pid using pgrep (recursive BFS)."""
    pids = {root_pid}
    queue = [root_pid]
    while queue:
        parent = queue.pop()
        try:
            result = subprocess.run(
                ["pgrep", "-P", str(parent)],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    child = int(line.strip())
                    if child not in pids:
                        pids.add(child)
                        queue.append(child)
        except (subprocess.TimeoutExpired, ValueError, OSError):
            pass
    return pids


def _get_gpu_vram_per_pid() -> dict[int, int]:
    """Query nvidia-smi for per-PID VRAM usage. Returns dict of PID -> MiB."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,used_gpu_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return {}
        vram = {}
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                try:
                    vram[int(parts[0])] = int(parts[1])
                except ValueError:
                    pass
        return vram
    except (subprocess.TimeoutExpired, OSError):
        return {}


def _get_gpu_total_vram() -> int:
    """Query nvidia-smi for total GPU memory in MiB. Returns 0 on failure."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return 0
        return int(result.stdout.strip().split("\n")[0].strip())
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return 0


class VramMonitor:
    """Background VRAM monitor that logs to ~/vramlogs/ as CSV.

    Usage:
        monitor = VramMonitor(process.pid, env_name="sam3dobjects")
        monitor.start()
        # ... run main loop ...
        peak = monitor.stop()  # returns peak VRAM in MiB
    """

    def __init__(self, root_pid: int, env_name: str = "unknown", interval: float = 1.0):
        self._root_pid = root_pid
        self._env_name = env_name
        self._interval = interval
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._peak_mib = 0
        self._total_mib = _get_gpu_total_vram()
        self._log_path: Optional[Path] = None
        self._log_file = None

    @property
    def peak_mib(self) -> int:
        return self._peak_mib

    @property
    def total_mib(self) -> int:
        return self._total_mib

    @property
    def log_path(self) -> Optional[Path]:
        return self._log_path

    def start(self):
        """Start the background monitoring thread."""
        if self._total_mib == 0:
            return
        # Set up log file
        VRAMLOGS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = VRAMLOGS_DIR / f"{self._env_name}_{ts}.csv"
        self._log_file = open(self._log_path, "w")
        self._log_file.write("timestamp,tree_vram_mib,total_vram_mib,num_gpu_processes,peak_vram_mib\n")
        self._log_file.flush()

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> int:
        """Stop the monitor. Returns peak VRAM in MiB."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self._log_file:
            self._log_file.close()
            self._log_file = None
        return self._peak_mib

    def _run(self):
        """Poll loop: sample VRAM every interval seconds."""
        while not self._stop_event.wait(self._interval):
            try:
                self._sample()
            except Exception:
                pass

    def _sample(self):
        """Take one VRAM sample and write to CSV."""
        tree_pids = _get_descendant_pids(self._root_pid)
        vram_map = _get_gpu_vram_per_pid()

        tree_mib = 0
        num_procs = 0
        for pid in tree_pids:
            if pid in vram_map:
                tree_mib += vram_map[pid]
                num_procs += 1

        if tree_mib > self._peak_mib:
            self._peak_mib = tree_mib

        if self._log_file:
            ts = datetime.now().isoformat(timespec="milliseconds")
            self._log_file.write(f"{ts},{tree_mib},{self._total_mib},{num_procs},{self._peak_mib}\n")
            self._log_file.flush()
