#!/usr/bin/env python3
"""
Gurthang — Download LoRA adapter from Fireworks AI, convert to GGUF, merge.

Steps:
  1. Download: Fetch final phase LoRA adapter via Fireworks signed URLs
  2. Convert: safetensors -> GGUF via convert_lora_to_gguf.py
  3. Merge:   Apply LoRA GGUF to abliterated Llama 3.3 70B base

Usage:
  python3 download_and_merge.py --download   # Download adapter
  python3 download_and_merge.py --convert    # Convert to GGUF
  python3 download_and_merge.py --merge      # Merge with abliterated base
  python3 download_and_merge.py --all        # All three steps
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

API_KEY = None
BASE_URL = "https://api.fireworks.ai/v1"
ACCOUNT_ID = "kristophkortryk"

STATE_FILE = Path("/vault/axiom/training/gurthang/gurthang_state.json")
LORA_DIR = Path("/vault/axiom/training/gurthang/gurthang-lora")
GGUF_LORA = Path("/vault/axiom/training/gurthang/gurthang-lora-f16.gguf")
CONVERT_SCRIPT = Path("/root/llama-cpp-tools/convert_lora_to_gguf.py")

ABLITERATED_BASE = "huihui-ai/Llama-3.3-70B-Instruct-abliterated"
ABLITERATED_GGUF_REPO = "bartowski/Llama-3.3-70B-Instruct-abliterated-GGUF"
BASE_GGUF_DIR = Path("/vault/axiom/models/llama-3.3-70b-abliterated")
MERGED_OUTPUT = Path("/vault/axiom/models/gurthang-70b-Q4_K_M.gguf")


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
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def get_final_model():
    with open(STATE_FILE) as f:
        state = json.load(f)

    for phase_num in [3, 2, 1]:
        phase = state.get("phases", {}).get(str(phase_num), {})
        model = phase.get("output_model")
        if model and phase.get("status") == "COMPLETED":
            print(f"Using Phase {phase_num} output: {model}")
            return model

    print("ERROR: No completed phase found. Run training first.")
    sys.exit(1)


def download_adapter():
    model_id = get_final_model()
    print(f"\nGetting download URLs for {model_id}...")

    url = f"{BASE_URL}/{model_id}:getDownloadEndpoint"
    resp = requests.get(url, headers=headers())
    if resp.status_code != 200:
        print(f"ERROR: HTTP {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    data = resp.json()
    LORA_DIR.mkdir(parents=True, exist_ok=True)

    file_urls = data.get("filenameToSignedUrls")
    if file_urls:
        print(f"Downloading {len(file_urls)} files...")
        for filepath, signed_url in file_urls.items():
            filename = filepath.split("/")[-1]
            local_path = LORA_DIR / filename
            print(f"  {filename}...", end=" ", flush=True)
            file_resp = requests.get(signed_url, stream=True)
            if file_resp.status_code != 200:
                print(f"ERROR: HTTP {file_resp.status_code}")
                continue
            total = int(file_resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(local_path, "wb") as f:
                for chunk in file_resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
            sz = downloaded / 1024 / 1024
            print(f"{sz:.1f} MB")
    else:
        download_url = data.get("downloadEndpoint") or data.get("url") or data.get("signedUrl")
        if not download_url:
            print(f"ERROR: No download URL in response: {json.dumps(data)[:500]}")
            sys.exit(1)

        print("Downloading adapter archive...")
        resp = requests.get(download_url, stream=True)
        if resp.status_code != 200:
            print(f"ERROR downloading: HTTP {resp.status_code}")
            sys.exit(1)

        total = int(resp.headers.get("Content-Length", 0))
        content_type = resp.headers.get("Content-Type", "")

        if "tar" in content_type or download_url.endswith((".tar.gz", ".tgz")):
            tar_path = LORA_DIR / "adapter.tar.gz"
            downloaded = 0
            with open(tar_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        print(f"\r  {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB", end="", flush=True)
            print()
            subprocess.run(["tar", "xzf", str(tar_path), "-C", str(LORA_DIR)], check=True)
            tar_path.unlink()
        else:
            safetensors_path = LORA_DIR / "adapter_model.safetensors"
            downloaded = 0
            with open(safetensors_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        print(f"\r  {downloaded / 1024 / 1024:.1f} / {total / 1024 / 1024:.1f} MB", end="", flush=True)
            print()

    adapter_config = LORA_DIR / "adapter_config.json"
    if adapter_config.exists():
        with open(adapter_config) as f:
            cfg = json.load(f)
        if not cfg.get("base_model_name_or_path"):
            cfg["base_model_name_or_path"] = "meta-llama/Llama-3.3-70B-Instruct"
            with open(adapter_config, "w") as f:
                json.dump(cfg, f, indent=2)
            print("Fixed adapter_config.json: set base_model_name_or_path")

    print(f"\nAdapter downloaded to {LORA_DIR}")
    for f in sorted(LORA_DIR.rglob("*")):
        if f.is_file():
            sz = f.stat().st_size / 1024 / 1024
            print(f"  {f.relative_to(LORA_DIR)}: {sz:.1f} MB" if sz > 1 else f"  {f.relative_to(LORA_DIR)}: {f.stat().st_size / 1024:.1f} KB")


def convert_to_gguf():
    print("\nConverting LoRA adapter to GGUF...")

    if not CONVERT_SCRIPT.exists():
        result = subprocess.run(
            ["find", "/root", "-name", "convert_lora_to_gguf.py", "-maxdepth", "4"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            script = Path(result.stdout.strip().split("\n")[0])
        else:
            print("ERROR: convert_lora_to_gguf.py not found")
            sys.exit(1)
    else:
        script = CONVERT_SCRIPT

    print(f"Using: {script}")
    cmd = [
        sys.executable, str(script),
        "--outfile", str(GGUF_LORA),
        "--outtype", "f16",
        str(LORA_DIR),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: Conversion failed")
        print(result.stderr[-1000:])
        sys.exit(1)

    sz = GGUF_LORA.stat().st_size / 1024 / 1024
    print(f"GGUF adapter: {GGUF_LORA} ({sz:.0f} MB)")


def download_base_gguf():
    BASE_GGUF_DIR.mkdir(parents=True, exist_ok=True)
    q4_pattern = "Llama-3.3-70B-Instruct-abliterated-Q4_K_M.gguf"

    existing = list(BASE_GGUF_DIR.glob("*Q4_K_M*"))
    if existing:
        print(f"Base GGUF already exists: {existing[0]}")
        return existing[0]

    split_files = sorted(BASE_GGUF_DIR.glob("*Q4_K_M*.gguf-*"))
    if split_files:
        print(f"Base GGUF splits already exist: {len(split_files)} files")
        return split_files[0]

    print(f"\nDownloading abliterated base model from HuggingFace...")
    print(f"  Repo: {ABLITERATED_GGUF_REPO}")
    print(f"  Quant: Q4_K_M")

    try:
        result = subprocess.run(
            ["huggingface-cli", "download", ABLITERATED_GGUF_REPO,
             "--include", f"*Q4_K_M*",
             "--local-dir", str(BASE_GGUF_DIR)],
            capture_output=True, text=True, timeout=7200
        )
        if result.returncode != 0:
            print(f"ERROR: HF download failed")
            print(result.stderr[-500:])
            sys.exit(1)
    except subprocess.TimeoutExpired:
        print("ERROR: Download timed out (2h)")
        sys.exit(1)

    downloaded = list(BASE_GGUF_DIR.glob("*Q4_K_M*"))
    if downloaded:
        total_sz = sum(f.stat().st_size for f in downloaded) / 1024 / 1024 / 1024
        print(f"Downloaded {len(downloaded)} files ({total_sz:.1f} GB)")
        return downloaded[0]
    else:
        print("ERROR: No Q4_K_M files found after download")
        sys.exit(1)


def merge_adapter():
    print("\n" + "=" * 60)
    print("GURTHANG MERGE — LoRA + Abliterated Base")
    print("=" * 60)

    if not GGUF_LORA.exists():
        print(f"ERROR: LoRA GGUF not found: {GGUF_LORA}")
        print("Run --convert first")
        sys.exit(1)

    base_path = download_base_gguf()

    split_files = sorted(BASE_GGUF_DIR.glob("*Q4_K_M*.gguf*"))
    if len(split_files) > 1:
        base_model_arg = str(split_files[0]).replace("-00001-of-", "-*-of-")
        first_split = split_files[0]
    else:
        base_model_arg = str(base_path)
        first_split = base_path

    print(f"\nBase model: {base_model_arg}")
    print(f"LoRA adapter: {GGUF_LORA}")
    print(f"Output: {MERGED_OUTPUT}")

    MERGED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    export_lora = None
    for name in ["llama-export-lora", "export-lora"]:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        if result.returncode == 0:
            export_lora = result.stdout.strip()
            break

    if not export_lora:
        for search_path in ["/root/llama.cpp/build", "/usr/local/bin", "/root/llama-cpp-tools"]:
            result = subprocess.run(
                ["find", search_path, "-name", "llama-export-lora", "-type", "f"],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                export_lora = result.stdout.strip().split("\n")[0]
                break

    if export_lora:
        print(f"\nUsing llama-export-lora: {export_lora}")
        cmd = [
            export_lora,
            "-m", str(first_split),
            "-o", str(MERGED_OUTPUT),
            "--lora", str(GGUF_LORA),
        ]
        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            print(f"ERROR: Merge failed")
            print(result.stderr[-1000:])
            sys.exit(1)
    else:
        print("\nllama-export-lora not found. Using Python PEFT merge...")
        merge_with_peft()
        return

    sz = MERGED_OUTPUT.stat().st_size / 1024 / 1024 / 1024
    print(f"\nMerged model: {MERGED_OUTPUT} ({sz:.1f} GB)")
    print("Gurthang forged. The Iron of Death is ready.")


def merge_with_peft():
    print("Merging via PEFT + HuggingFace Transformers...")
    print(f"  Base: {ABLITERATED_BASE}")
    print(f"  Adapter: {LORA_DIR}")

    merge_script = f"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import subprocess, sys

print("Loading base model (this takes a while for 70B)...")
base = AutoModelForCausalLM.from_pretrained(
    "{ABLITERATED_BASE}",
    torch_dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
)
tokenizer = AutoTokenizer.from_pretrained("{ABLITERATED_BASE}")

print("Loading LoRA adapter...")
model = PeftModel.from_pretrained(base, "{LORA_DIR}")

print("Merging weights...")
merged = model.merge_and_unload()

merged_hf = "{LORA_DIR.parent}/gurthang-merged-hf"
print(f"Saving merged HF model to {{merged_hf}}...")
merged.save_pretrained(merged_hf)
tokenizer.save_pretrained(merged_hf)

print("Converting merged model to GGUF Q4_K_M...")
convert_script = "/root/llama-cpp-tools/convert_hf_to_gguf.py"
cmd = [
    sys.executable, convert_script,
    merged_hf,
    "--outfile", "{MERGED_OUTPUT}",
    "--outtype", "q4_k_m",
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print(f"GGUF conversion failed, trying f16...")
    cmd[-1] = "f16"
    cmd[-3] = str("{MERGED_OUTPUT}").replace("Q4_K_M", "f16")
    subprocess.run(cmd, check=True)

print("Done!")
"""
    script_path = LORA_DIR.parent / "_merge_peft.py"
    with open(script_path, "w") as f:
        f.write(merge_script)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, timeout=7200
    )
    if result.returncode != 0:
        print(f"ERROR: PEFT merge failed")
        print(result.stdout[-500:])
        print(result.stderr[-500:])
        sys.exit(1)

    print(result.stdout[-500:])
    print("Gurthang forged via PEFT merge.")


def main():
    parser = argparse.ArgumentParser(description="Gurthang — Download, Convert, Merge")
    parser.add_argument("--download", action="store_true", help="Download LoRA from Fireworks")
    parser.add_argument("--convert", action="store_true", help="Convert to GGUF")
    parser.add_argument("--merge", action="store_true", help="Merge with abliterated base")
    parser.add_argument("--all", action="store_true", help="All three steps")
    args = parser.parse_args()

    if not any([args.download, args.convert, args.merge, args.all]):
        parser.print_help()
        sys.exit(0)

    load_api_key()

    if args.all or args.download:
        download_adapter()
    if args.all or args.convert:
        convert_to_gguf()
    if args.all or args.merge:
        merge_adapter()


if __name__ == "__main__":
    main()
