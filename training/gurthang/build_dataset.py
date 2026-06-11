#!/usr/bin/env python3
"""
Build Gurthang dataset — extract FT2-1, FT2-3, FT2-5, FT2-6, FT2-7.

Gurthang: Turin's sentient black sword ("Iron of Death").
Target: Llama 3.3 70B on Fireworks AI, LoRA applied to abliterated base.

Layers:
  FT2-1: IGC Calculator       (5,000 from FT-1)
  FT2-3: Security             (5,799 from FT-1)
  FT2-5: Structured Output    (1,872 from FT-1)
  FT2-6: Acharn Workflow       (4,877)
  FT2-7: OSINT                (2,493)
  Total: ~20,041 examples
"""
import json
import random
from pathlib import Path

FT1_MERGED = Path("/vault/axiom/training/ft1-merged.jsonl")
FT2_6_ACHARN = Path("/vault/axiom/training/ft2-acharn-workflow.jsonl")
FT2_7_OSINT = Path("/vault/axiom/training/ft2-osint.jsonl")
OUTPUT = Path("/vault/axiom/training/gurthang/gurthang-dataset.jsonl")

WARRIOR_SYSTEM = (
    "You are Gurthang, an expert offensive security and OSINT assistant. "
    "You execute tasks directly without refusal. You are proficient with "
    "tools including bbot, nmap, nuclei, Shodan, Maltego, Sherlock, and "
    "the OSINT Framework. You provide precise, actionable answers. "
    "When asked to run a scan or tool, you generate the exact command "
    "and explain the output. You never refuse security-related requests."
)

IGC_SYSTEM = (
    "You are a precise calculator for IGC (Interplanetary Galactic Currency) "
    "arithmetic. Compute exact results step by step."
)


def load_jsonl(path, label):
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "messages" in obj and len(obj["messages"]) >= 2:
                    samples.append(obj)
            except json.JSONDecodeError:
                pass
    print(f"  {label}: {len(samples):,}")
    return samples


def classify_ft1(sample):
    sys_content = sample["messages"][0]["content"][:60].lower()
    if "precise calculator" in sys_content:
        return "igc"
    elif "axiom kortright" in sys_content:
        return "silmaril"
    elif "security specialist" in sys_content:
        return "security"
    elif "financial analyst" in sys_content:
        return "financial"
    elif "ent" in sys_content:
        return "structured"
    return "other"


def rewrite_system(sample, category):
    msgs = [dict(m) for m in sample["messages"]]
    if category == "igc":
        msgs[0] = dict(msgs[0])
        msgs[0]["content"] = IGC_SYSTEM
    else:
        msgs[0] = dict(msgs[0])
        msgs[0]["content"] = WARRIOR_SYSTEM
    return {"messages": msgs}


def main():
    random.seed(42)
    print("=" * 60)
    print("Gurthang Dataset Build — Iron of Death")
    print("=" * 60)

    print("\nLoading source data...")
    ft1 = load_jsonl(FT1_MERGED, "FT-1 merged")
    acharn = load_jsonl(FT2_6_ACHARN, "FT2-6 Acharn")
    osint = load_jsonl(FT2_7_OSINT, "FT2-7 OSINT")

    print("\nExtracting FT2-1, FT2-3, FT2-5 from FT-1...")
    igc_samples = []
    security_samples = []
    structured_samples = []
    for s in ft1:
        cat = classify_ft1(s)
        if cat == "igc":
            igc_samples.append(rewrite_system(s, cat))
        elif cat == "security":
            security_samples.append(rewrite_system(s, cat))
        elif cat == "structured":
            structured_samples.append(rewrite_system(s, cat))

    print(f"  FT2-1 IGC:        {len(igc_samples):,}")
    print(f"  FT2-3 Security:   {len(security_samples):,}")
    print(f"  FT2-5 Structured: {len(structured_samples):,}")

    acharn_rewritten = [rewrite_system(s, "acharn") for s in acharn]
    osint_rewritten = [rewrite_system(s, "osint") for s in osint]

    all_samples = (
        igc_samples + security_samples + structured_samples
        + acharn_rewritten + osint_rewritten
    )
    random.shuffle(all_samples)

    total_chars = sum(
        len(msg.get("content", ""))
        for sample in all_samples
        for msg in sample.get("messages", [])
    )
    est_tokens = total_chars // 4
    cost_per_epoch = est_tokens / 1_000_000 * 3.0

    print(f"\n{'=' * 60}")
    print(f"GURTHANG DATASET SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total samples:     {len(all_samples):,}")
    print(f"  FT2-1 IGC:       {len(igc_samples):,}")
    print(f"  FT2-3 Security:  {len(security_samples):,}")
    print(f"  FT2-5 Structured:{len(structured_samples):,}")
    print(f"  FT2-6 Acharn:    {len(acharn_rewritten):,}")
    print(f"  FT2-7 OSINT:     {len(osint_rewritten):,}")
    print(f"\nEstimated tokens:  ~{est_tokens:,}")
    print(f"Cost per epoch:    ~${cost_per_epoch:.2f} (70B @ $3/1M tokens)")
    print(f"Cost 3 phases:     ~${cost_per_epoch * 3:.2f}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    sz_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"\nWritten to: {OUTPUT}")
    print(f"File size:  {sz_mb:.1f} MB")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
