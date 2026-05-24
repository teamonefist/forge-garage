import subprocess


def get_gpu_stats() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {"error": "nvidia-smi failed"}
        line = result.stdout.strip().split("\n")[0]
        parts = [p.strip() for p in line.split(",")]
        return {
            "utilization_pct": int(parts[0]),
            "memory_used_mb": int(parts[1]),
            "memory_total_mb": int(parts[2]),
            "temperature_c": int(parts[3]),
        }
    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError, ValueError):
        return {"error": "unavailable"}


def format_status(stats: dict) -> str:
    if "error" in stats:
        return "GPU: ?"
    used_gb = stats["memory_used_mb"] / 1024
    total_gb = stats["memory_total_mb"] / 1024
    return f"GPU: {stats['utilization_pct']}% | {used_gb:.0f}/{total_gb:.0f}GB | {stats['temperature_c']}°C"
