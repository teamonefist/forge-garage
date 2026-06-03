#!/usr/bin/env python3
"""
Launch v2 fine-tuning jobs on Together.ai for Fangorn deployment.

v2 models:
  - Warrior: DeepSeek-R1-Distill-Llama-70B (Grond replacement, 6560 samples)
  - Orchestrator: Qwen2.5-72B-Instruct (Glamdring replacement, 5970 samples)

Enhancements over v1:
  - CVE exploitation mapping (144 samples)
  - CVE database querying (40 samples)
  - IGC calculator patterns (200+ samples per model)
  - Advanced exploitation chains (multi-step)
  - Iterative bbot workflows
  - Structured JSON agentic task dispatch
  - Scope management and OSINT correlation
"""
import os
import sys
import json
from pathlib import Path

API_KEY_PATH = Path("/vault/axiom/config/together_api_key")
DATA_DIR = Path("/root/forge-garage/finetune/data")

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


def main():
    api_key = get_api_key()
    os.environ["TOGETHER_API_KEY"] = api_key

    try:
        import together
    except ImportError:
        print("Installing together SDK...")
        os.system("pip install together -q")
        import together

    client = together.Together()
    print("=== Forge Garage v2 Fine-Tuning Launch ===\n")

    # Check existing jobs
    print("Checking existing fine-tune jobs...")
    jobs_resp = client.fine_tuning.list()
    jobs_list = jobs_resp.data if hasattr(jobs_resp, 'data') else []
    active = [j for j in jobs_list if getattr(j, 'status', '') in ("running", "queued", "pending")]
    if active:
        print(f"  WARNING: {len(active)} active jobs already running:")
        for job in active:
            print(f"    - {job.id}: {job.model} ({job.status})")
        print()

    # Upload training files
    warrior_file = DATA_DIR / "warrior-v2-training.jsonl"
    orch_file = DATA_DIR / "orchestrator-v2-training.jsonl"

    if not warrior_file.exists() or not orch_file.exists():
        print("ERROR: v2 training files not found. Run generate_v2_training_data.py first.")
        sys.exit(1)

    print(f"Step 1: Uploading training data...")
    print(f"  Warrior: {warrior_file.name} ({warrior_file.stat().st_size / 1024 / 1024:.1f} MB)")
    warrior_upload = client.files.upload(file=str(warrior_file), purpose="fine-tune")
    warrior_file_id = warrior_upload.id
    print(f"  Uploaded: {warrior_file_id}")

    print(f"  Orchestrator: {orch_file.name} ({orch_file.stat().st_size / 1024 / 1024:.1f} MB)")
    orch_upload = client.files.upload(file=str(orch_file), purpose="fine-tune")
    orch_file_id = orch_upload.id
    print(f"  Uploaded: {orch_file_id}")

    # Launch fine-tune jobs
    print(f"\nStep 2: Launching v2 fine-tune jobs...")

    # Warrior v2
    print(f"\n  [Warrior v2]")
    print(f"  Base: {WARRIOR_BASE}")
    print(f"  Samples: 6560")
    print(f"  Config: LoRA r=64, alpha=128, epochs=2, lr=1e-5, batch=8")
    warrior_job = client.fine_tuning.create(
        training_file=warrior_file_id,
        model=WARRIOR_BASE,
        suffix="forge-warrior-v2",
        n_epochs=2,
        learning_rate=1e-5,
        batch_size=8,
        lora=True,
        lora_r=64,
        lora_alpha=128,
        warmup_ratio=0.1,
    )
    print(f"  Job ID: {warrior_job.id}")
    print(f"  Status: {warrior_job.status}")

    # Orchestrator v2
    print(f"\n  [Orchestrator v2]")
    print(f"  Base: {ORCHESTRATOR_BASE}")
    print(f"  Samples: 5970")
    print(f"  Config: LoRA r=64, alpha=128, epochs=2, lr=1e-5, batch=8")
    orch_job = client.fine_tuning.create(
        training_file=orch_file_id,
        model=ORCHESTRATOR_BASE,
        suffix="forge-orchestrator-v2",
        n_epochs=2,
        learning_rate=1e-5,
        batch_size=8,
        lora=True,
        lora_r=64,
        lora_alpha=128,
        warmup_ratio=0.1,
    )
    print(f"  Job ID: {orch_job.id}")
    print(f"  Status: {orch_job.status}")

    # Save job tracking data
    jobs_data = {
        "version": "v2",
        "warrior": {
            "job_id": warrior_job.id,
            "file_id": warrior_file_id,
            "base_model": WARRIOR_BASE,
            "suffix": "forge-warrior-v2",
            "samples": 6560,
            "enhancements": ["cve_exploitation", "cve_database", "igc_calculator", "advanced_chains", "bbot_workflows"],
        },
        "orchestrator": {
            "job_id": orch_job.id,
            "file_id": orch_file_id,
            "base_model": ORCHESTRATOR_BASE,
            "suffix": "forge-orchestrator-v2",
            "samples": 5970,
            "enhancements": ["task_dispatch", "cve_research", "scope_management", "igc_calculator"],
        },
    }

    jobs_file = DATA_DIR / "finetune_v2_jobs.json"
    with open(jobs_file, "w") as f:
        json.dump(jobs_data, f, indent=2)

    print(f"\n{'='*50}")
    print(f"v2 Fine-Tune Jobs Launched Successfully")
    print(f"{'='*50}")
    print(f"\nJob IDs saved to: {jobs_file}")
    print(f"\nWarrior v2:      {warrior_job.id} ({warrior_job.status})")
    print(f"Orchestrator v2: {orch_job.id} ({orch_job.status})")
    print(f"\nMonitor: python3 finetune/check_v2_status.py")
    print(f"Expected duration: 2-4 hours per job")


if __name__ == "__main__":
    main()
