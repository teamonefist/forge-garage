#!/usr/bin/env python3
"""
Launch fine-tuning jobs on Together.ai for the Forge Garage models.

Base models:
  - Warrior: DeepSeek-R1-Distill-Llama-70B (meta-llama/Llama-3.3-70B-Instruct as base for finetune)
  - Orchestrator: Mistral Small (mistralai/Mistral-Small-24B-Instruct-2501 as proxy for finetune)

Note: Together.ai doesn't support finetuning all models. We use the largest
available base models they support and apply our training data. The fine-tuned
weights get downloaded and converted to GGUF afterward.

Available for fine-tuning on Together.ai (as of May 2026):
  - meta-llama/Meta-Llama-3.1-70B-Instruct
  - meta-llama/Llama-3.3-70B-Instruct
  - Qwen/Qwen2.5-72B-Instruct
  - mistralai/Mistral-Small-24B-Instruct-2501
  - deepseek-ai/DeepSeek-R1-Distill-Llama-70B
"""
import os
import sys
import json
import requests
from pathlib import Path

API_KEY_PATH = Path("/vault/axiom/config/together_api_key")
DATA_DIR = Path("/root/forge-garage/finetune/data")

BASE_URL = "https://api.together.xyz/v1"

# Together.ai fine-tunable models that match our target
WARRIOR_BASE = "deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
ORCHESTRATOR_BASE = "Qwen/Qwen2.5-72B-Instruct"


def get_api_key() -> str:
    if API_KEY_PATH.exists():
        return API_KEY_PATH.read_text().strip()
    key = os.environ.get("TOGETHER_API_KEY")
    if key:
        return key
    print("ERROR: No API key found at", API_KEY_PATH)
    sys.exit(1)


def upload_file(api_key: str, filepath: Path) -> str:
    """Upload training file and return file ID."""
    print(f"  Uploading {filepath.name} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)...")

    resp = requests.post(
        f"{BASE_URL}/files",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": (filepath.name, open(filepath, "rb"), "application/jsonl")},
        data={"purpose": "fine-tune"},
    )

    if resp.status_code != 200:
        print(f"  ERROR uploading: {resp.status_code} {resp.text[:500]}")
        sys.exit(1)

    file_id = resp.json()["id"]
    print(f"  Uploaded: {file_id}")
    return file_id


def create_finetune(api_key: str, model: str, training_file: str, suffix: str, n_epochs: int = 3) -> dict:
    """Create a fine-tuning job."""
    print(f"\n  Creating fine-tune job: {suffix}")
    print(f"  Base model: {model}")
    print(f"  Training file: {training_file}")
    print(f"  Epochs: {n_epochs}")

    body = {
        "training_file": training_file,
        "model": model,
        "suffix": suffix,
        "n_epochs": n_epochs,
        "learning_rate": 1e-5,
        "batch_size": 4,
        "warmup_ratio": 0.1,
    }

    resp = requests.post(
        f"{BASE_URL}/fine-tunes",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )

    if resp.status_code not in (200, 201):
        print(f"  ERROR creating job: {resp.status_code} {resp.text[:500]}")
        return {"error": resp.text}

    result = resp.json()
    print(f"  Job created: {result.get('id', 'unknown')}")
    print(f"  Status: {result.get('status', 'unknown')}")
    return result


def list_finetunes(api_key: str):
    """List existing fine-tune jobs."""
    resp = requests.get(
        f"{BASE_URL}/fine-tunes",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    if resp.status_code == 200:
        return resp.json()
    return {"error": resp.text}


def main():
    api_key = get_api_key()
    print("=== Forge Garage Fine-Tuning Launch ===\n")

    # Check existing jobs
    print("Checking existing fine-tune jobs...")
    existing = list_finetunes(api_key)
    if "data" in existing:
        active = [j for j in existing["data"] if j.get("status") in ("running", "queued", "pending")]
        if active:
            print(f"  WARNING: {len(active)} active jobs already running:")
            for job in active:
                print(f"    - {job.get('id')}: {job.get('model')} ({job.get('status')})")
            print("\n  Proceeding anyway (new jobs will queue)...\n")

    # Upload training files
    print("Step 1: Uploading training data...")
    warrior_file = DATA_DIR / "warrior-training.jsonl"
    orchestrator_file = DATA_DIR / "orchestrator-training.jsonl"

    if not warrior_file.exists() or not orchestrator_file.exists():
        print("ERROR: Training files not found. Run generate_training_data.py first.")
        sys.exit(1)

    warrior_file_id = upload_file(api_key, warrior_file)
    orchestrator_file_id = upload_file(api_key, orchestrator_file)

    # Launch fine-tuning jobs
    print("\nStep 2: Launching fine-tune jobs...")

    warrior_job = create_finetune(
        api_key=api_key,
        model=WARRIOR_BASE,
        training_file=warrior_file_id,
        suffix="forge-warrior-v1",
        n_epochs=3,
    )

    orchestrator_job = create_finetune(
        api_key=api_key,
        model=ORCHESTRATOR_BASE,
        training_file=orchestrator_file_id,
        suffix="forge-orchestrator-v1",
        n_epochs=3,
    )

    # Save job IDs for tracking
    jobs_file = DATA_DIR / "finetune_jobs.json"
    jobs_data = {
        "warrior": {
            "job": warrior_job,
            "file_id": warrior_file_id,
            "base_model": WARRIOR_BASE,
        },
        "orchestrator": {
            "job": orchestrator_job,
            "file_id": orchestrator_file_id,
            "base_model": ORCHESTRATOR_BASE,
        },
    }

    with open(jobs_file, "w") as f:
        json.dump(jobs_data, f, indent=2)

    print(f"\n=== Summary ===")
    print(f"Job IDs saved to: {jobs_file}")
    print(f"")
    print(f"Warrior:")
    print(f"  Base: {WARRIOR_BASE}")
    print(f"  Suffix: forge-warrior-v1")
    print(f"  Status: {warrior_job.get('status', warrior_job.get('error', 'unknown'))}")
    print(f"")
    print(f"Orchestrator:")
    print(f"  Base: {ORCHESTRATOR_BASE}")
    print(f"  Suffix: forge-orchestrator-v1")
    print(f"  Status: {orchestrator_job.get('status', orchestrator_job.get('error', 'unknown'))}")
    print(f"")
    print(f"Monitor: python3 finetune/check_status.py")
    print(f"Expected duration: 2-6 hours per job (depending on queue)")


if __name__ == "__main__":
    main()
