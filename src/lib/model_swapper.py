"""Single-GPU model swapper for Forge Garage.

When only one GPU is available, this module manages loading and unloading
models so that only one llama-server instance runs at a time.
"""
import os
import signal
import subprocess
import time
from pathlib import Path

import requests


GARAGE_HOME = Path.home() / ".forge-garage"
RUN_DIR = GARAGE_HOME / "run"
LOG_DIR = GARAGE_HOME / "logs"


def _pid_file(persona: str) -> Path:
    return RUN_DIR / f"{persona}.pid"


def _read_pid(persona: str) -> int | None:
    pf = _pid_file(persona)
    if pf.exists():
        try:
            return int(pf.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _health_ok(port: int) -> bool:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def stop_model(persona: str, port: int) -> bool:
    pid = _read_pid(persona)
    if pid and _is_running(pid):
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            if not _is_running(pid):
                break
            time.sleep(0.5)
        else:
            os.kill(pid, signal.SIGKILL)
            time.sleep(1)
    _pid_file(persona).unlink(missing_ok=True)
    return not _health_ok(port)


def start_model(persona: str, model_path: str, port: int,
                lora_path: str | None = None) -> bool:
    if _health_ok(port):
        return True

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "llama-server",
        "--model", model_path,
        "--port", str(port),
        "--host", "127.0.0.1",
        "--ctx-size", "32768",
        "--n-gpu-layers", "-1",
        "--threads", "8",
        "--parallel", "1",
        "--cont-batching",
        "--flash-attn", "on",
        "--mlock",
    ]
    if lora_path and Path(lora_path).exists():
        cmd.extend(["--lora", lora_path])

    log_file = LOG_DIR / f"{persona}.log"
    with open(log_file, "a") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=lf)

    _pid_file(persona).write_text(str(proc.pid))

    for _ in range(120):
        if _health_ok(port):
            return True
        time.sleep(2)

    return False


def active_persona() -> str | None:
    for name in ("orchestrator", "warrior"):
        pid = _read_pid(name)
        if pid and _is_running(pid):
            return name
    return None


class ModelSwapper:
    def __init__(self, config: dict):
        self.config = config
        orch = config.get("orchestrator", {})
        war = config.get("warrior", {})
        self.orch_port = orch.get("port", 8081)
        self.war_port = war.get("port", 8082)
        self.orch_model = self._expand(orch.get("model_path", ""))
        self.war_model = self._expand(war.get("model_path", ""))
        self.orch_lora = str(GARAGE_HOME / "models" / "forge-orchestrator-lora-f16.gguf")
        self.war_lora = str(GARAGE_HOME / "models" / "forge-warrior-lora-f16.gguf")
        self._current: str | None = active_persona()

    @staticmethod
    def _expand(path: str) -> str:
        return path.replace("~", str(Path.home()))

    @property
    def current(self) -> str | None:
        return self._current

    def ensure_orchestrator(self, on_status=None) -> bool:
        if self._current == "orchestrator" and _health_ok(self.orch_port):
            return True
        if self._current == "warrior":
            if on_status:
                on_status("Unloading Warrior...")
            stop_model("warrior", self.war_port)
        if on_status:
            on_status("Loading Orchestrator (this takes 2-3 minutes)...")
        ok = start_model("orchestrator", self.orch_model, self.orch_port, self.orch_lora)
        if ok:
            self._current = "orchestrator"
        return ok

    def ensure_warrior(self, on_status=None) -> bool:
        if self._current == "warrior" and _health_ok(self.war_port):
            return True
        if self._current == "orchestrator":
            if on_status:
                on_status("Unloading Orchestrator...")
            stop_model("orchestrator", self.orch_port)
        if on_status:
            on_status("Loading Warrior (this takes 2-3 minutes)...")
        ok = start_model("warrior", self.war_model, self.war_port, self.war_lora)
        if ok:
            self._current = "warrior"
        return ok

    def stop_all(self):
        stop_model("orchestrator", self.orch_port)
        stop_model("warrior", self.war_port)
        self._current = None
