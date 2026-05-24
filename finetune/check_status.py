#!/usr/bin/env python3
"""Check status of Forge Garage fine-tuning jobs on Together.ai."""
import json
import os
import sys
from pathlib import Path

JOBS_FILE = Path("/root/forge-garage/finetune/data/finetune_jobs.json")


def main():
    os.environ['TOGETHER_API_KEY'] = open('/vault/axiom/config/together_api_key').read().strip()

    try:
        import together
    except ImportError:
        print("Error: 'together' package not installed. Run: pip install together")
        sys.exit(1)

    if not JOBS_FILE.exists():
        print("No jobs file found. Run launch_finetune.py first.")
        sys.exit(1)

    with open(JOBS_FILE) as f:
        jobs = json.load(f)

    client = together.Together()
    print("=== Forge Garage Fine-Tune Status ===\n")

    all_complete = True
    for role, data in jobs.items():
        job_id = data.get("job_id")
        if not job_id or job_id == "FAILED":
            print(f"  {role.upper()}: FAILED (no job ID)")
            all_complete = False
            continue

        job = client.fine_tuning.retrieve(id=job_id)

        print(f"  {role.upper()}:")
        print(f"    Job ID: {job_id}")
        print(f"    Base: {data.get('base_model')}")
        print(f"    Status: {job.status}")

        if job.status == "completed":
            output = getattr(job, 'output_name', None) or getattr(job, 'model_output_name', None)
            print(f"    Output model: {output}")
            print(f"    READY for download!")
        elif job.status in ("running", "queued", "pending"):
            all_complete = False
            steps = getattr(job, 'total_steps', None)
            current = getattr(job, 'current_step', None)
            if steps and current:
                pct = (current / steps) * 100
                print(f"    Progress: {current}/{steps} ({pct:.0f}%)")
        elif job.status in ("error", "failed", "user_error"):
            all_complete = False
            error_msg = getattr(job, 'error', 'unknown')
            print(f"    ERROR: {error_msg}")

        print()

    if all_complete:
        print("ALL JOBS COMPLETE. Ready to download and convert to GGUF.")
    else:
        print("Jobs still in progress. Check again later.")


if __name__ == "__main__":
    main()
