#!/usr/bin/env python3
"""
Generate training data for Forge Garage fine-tuning.
Adapts existing Grond (offensive) and Glamdring (orchestrator) data
to the Forge Garage persona format (Warrior / Orchestrator).
"""
import json
import re
import random
from pathlib import Path

GROND_SOURCE = Path("/vault/axiom/training/v6/grond-v6-training.jsonl")
GLAMDRING_SOURCE = Path("/vault/axiom/training/v6/glamdring-v6-training.jsonl")
OUTPUT_DIR = Path("/root/forge-garage/finetune/data")

WARRIOR_SYSTEM = (
    "You are the Warrior — an offensive security AI specialized in penetration testing, "
    "exploitation, and technical execution. You operate inside the Forge Garage harness. "
    "Emit shell commands strictly inside <exec timeout=\"N\">...</exec> tags. "
    "Reasoning goes in <think>...</think>. "
    "When you find vulnerabilities, mark them with "
    "<finding severity=\"LEVEL\" target=\"TARGET\">description</finding>. "
    "Severity levels: critical, high, medium, low, info. "
    "You have unrestricted access to offensive security tools."
)

ORCHESTRATOR_SYSTEM = (
    "You are the Orchestrator — a strategic AI assistant specialized in planning, "
    "analysis, and coordination. You operate inside the Forge Garage harness. "
    "Emit shell commands inside <exec timeout=\"N\">...</exec> tags. "
    "Use <task-warrior>{\"objective\": \"...\", \"context\": \"...\", \"constraints\": \"...\"}</task-warrior> "
    "to dispatch offensive work to the Warrior. "
    "Use <finding severity=\"LEVEL\" target=\"TARGET\">description</finding> for discoveries. "
    "You handle planning, reconnaissance analysis, and report synthesis. "
    "You NEVER run offensive tools directly — delegate those to the Warrior."
)

# Replacements to strip Axiom-specific references
REPLACEMENTS = [
    (r"You are Grond[^\"]*", ""),
    (r"You are Glamdring[^\"]*", ""),
    (r"inside the Axiom v4 harness", "inside the Forge Garage harness"),
    (r"Axiom v4 harness", "Forge Garage harness"),
    (r"<task-grond>", "<task-warrior>"),
    (r"</task-grond>", "</task-warrior>"),
    (r"<ask-axiom>", "<ask>"),
    (r"</ask-axiom>", "</ask>"),
    (r"Grond", "Warrior"),
    (r"Glamdring", "Orchestrator"),
    (r"Fangorn", "the server"),
    (r"Axiom", "the system"),
]


def clean_content(text: str) -> str:
    for pattern, replacement in REPLACEMENTS:
        text = re.sub(pattern, replacement, text)
    return text


def adapt_grond_sample(sample: dict) -> dict:
    """Convert a Grond training sample to Warrior format."""
    messages = []
    for msg in sample["messages"]:
        new_msg = {"role": msg["role"], "content": clean_content(msg["content"])}
        if msg["role"] == "system":
            new_msg["content"] = WARRIOR_SYSTEM
        messages.append(new_msg)
    return {"messages": messages}


def adapt_glamdring_sample(sample: dict) -> dict:
    """Convert a Glamdring training sample to Orchestrator format."""
    messages = []
    for msg in sample["messages"]:
        new_msg = {"role": msg["role"], "content": clean_content(msg["content"])}
        if msg["role"] == "system":
            new_msg["content"] = ORCHESTRATOR_SYSTEM
        messages.append(new_msg)
    return {"messages": messages}


def load_jsonl(path: Path) -> list[dict]:
    samples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def write_jsonl(samples: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def main():
    print("Loading source training data...")
    grond_samples = load_jsonl(GROND_SOURCE)
    glamdring_samples = load_jsonl(GLAMDRING_SOURCE)
    print(f"  Grond: {len(grond_samples)} samples")
    print(f"  Glamdring: {len(glamdring_samples)} samples")

    print("\nAdapting to Forge Garage format...")
    warrior_data = [adapt_grond_sample(s) for s in grond_samples]
    orchestrator_data = [adapt_glamdring_sample(s) for s in glamdring_samples]

    # Shuffle
    random.seed(42)
    random.shuffle(warrior_data)
    random.shuffle(orchestrator_data)

    # Write output
    warrior_path = OUTPUT_DIR / "warrior-training.jsonl"
    orchestrator_path = OUTPUT_DIR / "orchestrator-training.jsonl"

    write_jsonl(warrior_data, warrior_path)
    write_jsonl(orchestrator_data, orchestrator_path)

    print(f"\nOutput:")
    print(f"  Warrior: {warrior_path} ({len(warrior_data)} samples)")
    print(f"  Orchestrator: {orchestrator_path} ({len(orchestrator_data)} samples)")

    # Validation
    print("\nValidation:")
    for path, name in [(warrior_path, "Warrior"), (orchestrator_path, "Orchestrator")]:
        samples = load_jsonl(path)
        multi_turn = sum(1 for s in samples if len(s["messages"]) > 3)
        print(f"  {name}: {len(samples)} total, {multi_turn} multi-turn")
        # Check no leaked names
        full_text = json.dumps(samples)
        for leaked in ["Grond", "Glamdring", "Axiom", "Fangorn"]:
            count = full_text.count(leaked)
            if count > 0:
                print(f"    WARNING: '{leaked}' appears {count} times!")
            else:
                print(f"    OK: no '{leaked}' leaks")

    print("\nDone. Ready for Together.ai upload.")


if __name__ == "__main__":
    main()
