#!/usr/bin/env python3
"""
Gurthang Fine-Tuning Pipeline — Llama 3.3 70B on Fireworks AI.

Progressive Batching (3 phases):
  Phase 1: batch=8,  lr=2e-5   (explore)
  Phase 2: batch=16, lr=1.4e-5 (refine, warm-start from P1)
  Phase 3: batch=32, lr=1e-5   (polish, warm-start from P2)

Usage:
  python3 launch_gurthang.py --upload       # Upload dataset only
  python3 launch_gurthang.py --phase 1      # Launch phase 1
  python3 launch_gurthang.py --phase 2      # Launch phase 2 (after P1)
  python3 launch_gurthang.py --phase 3      # Launch phase 3 (after P2)
  python3 launch_gurthang.py --status       # Check all job statuses
  python3 launch_gurthang.py --auto         # Full auto: upload + all 3 phases
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

API_KEY = None
BASE_URL = "https://api.fireworks.ai/v1"
ACCOUNT_ID = None

BASE_MODEL = "accounts/fireworks/models/llama-v3p3-70b-instruct"
DATASET_PATH = Path("/vault/axiom/training/gurthang/gurthang-dataset.jsonl")
STATE_FILE = Path("/vault/axiom/training/gurthang/gurthang_state.json")

PHASES = {
    1: {"epochs": 1, "batch_size": 8,  "lr": 2e-5,   "suffix": "gurthang-p1-explore"},
    2: {"epochs": 1, "batch_size": 16, "lr": 1.4e-5, "suffix": "gurthang-p2-refine"},
    3: {"epochs": 1, "batch_size": 32, "lr": 1e-5,   "suffix": "gurthang-p3-polish"},
}


def load_api_key():
    global API_KEY
    keys_path = Path("/root/.openclaw/api-keys.json")
    if keys_path.exists():
        with open(keys_path) as f:
            keys = json.load(f)
        if "fireworks_ai" in keys:
            API_KEY = keys["fireworks_ai"]["key"]
            return
    API_KEY = os.environ.get("FIREWORKS_API_KEY")
    if not API_KEY:
        print("ERROR: No Fireworks AI API key found")
        sys.exit(1)


def headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def get_account_id():
    global ACCOUNT_ID
    resp = requests.get(f"{BASE_URL}/accounts", headers=headers())
    if resp.status_code == 200:
        data = resp.json()
        accounts = data.get("accounts", [])
        if accounts:
            name = accounts[0].get("name", "")
            ACCOUNT_ID = name.split("/")[-1] if "/" in name else name
            print(f"Account: {ACCOUNT_ID}")
            return
    ACCOUNT_ID = "kristophkortryk"
    print(f"Using default account: {ACCOUNT_ID}")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"dataset_id": None, "phases": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def upload_dataset():
    state = load_state()
    if state.get("dataset_id"):
        print(f"Dataset already uploaded: {state['dataset_id']}")
        return state["dataset_id"]

    example_count = sum(1 for _ in open(DATASET_PATH))
    print(f"Uploading dataset: {DATASET_PATH}")
    print(f"  Size: {DATASET_PATH.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"  Examples: {example_count:,}")

    dataset_id = f"gurthang-{int(time.time())}"

    print(f"Step 1: Creating dataset metadata '{dataset_id}'...")
    create_url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/datasets"
    create_body = {
        "datasetId": dataset_id,
        "dataset": {"userUploaded": {}, "exampleCount": str(example_count)},
    }
    resp = requests.post(create_url, headers=headers(), json=create_body)
    if resp.status_code not in (200, 201):
        print(f"Create FAILED: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    print(f"Step 2: Uploading file...")
    upload_url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/datasets/{dataset_id}:upload"
    with open(DATASET_PATH, "rb") as f:
        resp = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {API_KEY}"},
            files={"file": (DATASET_PATH.name, f, "application/jsonl")},
        )

    if resp.status_code in (200, 201):
        full_id = f"accounts/{ACCOUNT_ID}/datasets/{dataset_id}"
        print(f"Upload OK: {full_id}")
        state["dataset_id"] = full_id
        save_state(state)
        return full_id
    else:
        print(f"Upload FAILED: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)


def launch_phase(phase_num, force=False):
    state = load_state()
    phase_key = str(phase_num)
    phase_cfg = PHASES[phase_num]

    if not force and phase_key in state.get("phases", {}) and state["phases"][phase_key].get("job_id"):
        job_id = state["phases"][phase_key]["job_id"]
        print(f"Phase {phase_num} already launched: {job_id}")
        return job_id

    dataset_id = state.get("dataset_id")
    if not dataset_id:
        print("ERROR: No dataset uploaded. Run --upload first.")
        sys.exit(1)

    if phase_num == 1:
        base = BASE_MODEL
    else:
        prev_key = str(phase_num - 1)
        prev_phase = state.get("phases", {}).get(prev_key, {})
        prev_model = prev_phase.get("output_model")
        if not prev_model:
            print(f"ERROR: Phase {phase_num - 1} has no output model. Run phase {phase_num - 1} first.")
            sys.exit(1)
        base = prev_model

    print(f"\nLaunching Phase {phase_num}:")
    print(f"  Base model:  {base}")
    print(f"  Dataset:     {dataset_id}")
    print(f"  Batch size:  {phase_cfg['batch_size']}")
    print(f"  LR:          {phase_cfg['lr']}")
    print(f"  Epochs:      {phase_cfg['epochs']}")
    print(f"  Suffix:      {phase_cfg['suffix']}")

    url = f"{BASE_URL}/accounts/{ACCOUNT_ID}/supervisedFineTuningJobs"
    payload = {
        "dataset": dataset_id,
        "epochs": phase_cfg["epochs"],
        "learningRate": phase_cfg["lr"],
        "batchSizeSamples": phase_cfg["batch_size"],
        "loraRank": 32,
        "displayName": f"Gurthang Phase {phase_num} - {phase_cfg['suffix']}",
    }
    if phase_num == 1:
        payload["baseModel"] = base
    else:
        payload["warmStartFrom"] = base

    resp = requests.post(url, headers=headers(), json=payload)

    if resp.status_code in (200, 201):
        data = resp.json()
        job_name = data.get("name", "unknown")
        model_name = data.get("modelId") or data.get("model_id", phase_cfg["suffix"])
        print(f"  Job launched: {job_name}")

        if "phases" not in state:
            state["phases"] = {}
        state["phases"][phase_key] = {
            "job_id": job_name,
            "model_id": model_name,
            "base_model": base,
            "status": "RUNNING",
            "launched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "config": phase_cfg,
        }
        save_state(state)
        return job_name
    else:
        print(f"  Launch FAILED: {resp.status_code}")
        print(f"  {resp.text[:500]}")
        sys.exit(1)


def check_job_status(job_id):
    resp = requests.get(f"{BASE_URL}/{job_id}", headers=headers())
    if resp.status_code == 200:
        return resp.json()
    return None


def check_all_status():
    state = load_state()
    print(f"\nDataset: {state.get('dataset_id', 'NOT UPLOADED')}")
    print()

    for phase_num in [1, 2, 3]:
        phase_key = str(phase_num)
        phase_data = state.get("phases", {}).get(phase_key, {})

        if not phase_data:
            print(f"Phase {phase_num}: NOT STARTED")
            continue

        job_id = phase_data.get("job_id", "")
        if job_id:
            job_info = check_job_status(job_id)
            if job_info:
                status = job_info.get("state", job_info.get("status", "UNKNOWN"))
                output_model = job_info.get("outputModel", job_info.get("modelId", ""))
                print(f"Phase {phase_num}: {status}")
                print(f"  Job: {job_id}")
                print(f"  Model: {output_model}")

                if status in ("COMPLETED", "SUCCEEDED", "JOB_STATE_COMPLETED"):
                    phase_data["status"] = "COMPLETED"
                    if output_model:
                        phase_data["output_model"] = output_model
                    save_state(state)
                elif status in ("FAILED", "CANCELLED"):
                    phase_data["status"] = status
                    save_state(state)
            else:
                print(f"Phase {phase_num}: {phase_data.get('status', 'UNKNOWN')} (API error)")
        else:
            print(f"Phase {phase_num}: {phase_data.get('status', 'NO JOB')}")
        print()


def wait_for_phase(phase_num, poll_interval=120):
    state = load_state()
    phase_key = str(phase_num)
    phase_data = state.get("phases", {}).get(phase_key, {})
    job_id = phase_data.get("job_id")

    if not job_id:
        print(f"Phase {phase_num} has no job to wait for")
        return False

    print(f"\nWaiting for Phase {phase_num}: {job_id}")
    start = time.time()

    while True:
        job_info = check_job_status(job_id)
        if job_info:
            status = job_info.get("state", job_info.get("status", "UNKNOWN"))
            elapsed = (time.time() - start) / 60

            if status in ("COMPLETED", "SUCCEEDED", "JOB_STATE_COMPLETED"):
                output_model = job_info.get("outputModel", job_info.get("modelId", ""))
                cost_info = job_info.get("estimatedCost", {})
                if isinstance(cost_info, dict):
                    cost = f"${float(cost_info.get('units', 0)) + float(cost_info.get('nanos', 0)) / 1e9:.2f}"
                else:
                    cost = str(cost_info)
                print(f"\n  Phase {phase_num} COMPLETED in {elapsed:.1f}m")
                print(f"  Model: {output_model}")
                print(f"  Cost: {cost}")

                state = load_state()
                state["phases"][phase_key]["status"] = "COMPLETED"
                if output_model:
                    state["phases"][phase_key]["output_model"] = output_model
                save_state(state)
                return True

            elif status in ("FAILED", "CANCELLED"):
                print(f"\n  Phase {phase_num} {status} after {elapsed:.1f}m")
                reason = job_info.get("error", job_info.get("failure_reason", "unknown"))
                print(f"  Reason: {reason}")
                state = load_state()
                state["phases"][phase_key]["status"] = status
                save_state(state)
                return False

            print(f"  [{elapsed:6.1f}m] {status}...", end="\r")

        time.sleep(poll_interval)


def auto_run():
    print("=" * 60)
    print("GURTHANG — Full Auto Pipeline")
    print("  Iron of Death — Llama 3.3 70B Fine-Tune")
    print("=" * 60)

    dataset_id = upload_dataset()
    print(f"\nDataset ready: {dataset_id}")

    for phase_num in [1, 2, 3]:
        print(f"\n{'=' * 40}")
        print(f"PHASE {phase_num} of 3")
        print(f"{'=' * 40}")

        launch_phase(phase_num)

        if not wait_for_phase(phase_num):
            print(f"\nPipeline STOPPED at Phase {phase_num}")
            sys.exit(1)

    print(f"\n{'=' * 60}")
    print("ALL 3 PHASES COMPLETE")
    print(f"{'=' * 60}")

    state = load_state()
    final_model = state["phases"]["3"].get("output_model", "unknown")
    print(f"Final model: {final_model}")
    print(f"\nNext: Download adapter and merge with abliterated base")
    print(f"  python3 /vault/axiom/training/gurthang/download_and_merge.py")


def main():
    parser = argparse.ArgumentParser(description="Gurthang Fine-Tuning Pipeline")
    parser.add_argument("--upload", action="store_true", help="Upload dataset")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3], help="Launch specific phase")
    parser.add_argument("--status", action="store_true", help="Check all statuses")
    parser.add_argument("--auto", action="store_true", help="Full auto pipeline")
    args = parser.parse_args()

    load_api_key()
    get_account_id()

    if args.upload:
        upload_dataset()
    elif args.phase:
        launch_phase(args.phase)
    elif args.status:
        check_all_status()
    elif args.auto:
        auto_run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
