# Glamdring v2: Agentic Offensive Harness

## Problem Statement

Current Glamdring runs single-shot: user sends message → model responds → maybe executes commands → stops.
What we need: autonomous iterative loops like Axiom's ihc.ru bbot workflow — the model plans, executes, analyzes results, decides next steps, and continues until the objective is met or a limit is reached.

## Architecture: Experts-First + Agentic Loop

### GPU Layout (Fangorn 2x RTX 4090)

| GPU | Role | Model | VRAM Usage |
|-----|------|-------|-----------|
| GPU 0 | Reasoning Engine | Qwen3-235B-A22B Q4_K_M via expert-residency | ~12-16 GB (22B active params) |
| GPU 1 | Fast Executor | Qwen3-8B or similar | ~6 GB |

Expert-residency: only active expert slots loaded in VRAM. Inactive experts paged from disk/RAM on demand.
Branch: `moe-expert-residency` at `teamonefist/llama.cpp-experts-first`

### Agentic Loop Design

```
┌─────────────────────────────────────────────────────────┐
│                    MISSION CONTROLLER                     │
│  (Python process — maintains state across iterations)    │
└──────────────┬──────────────────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │  OBJECTIVE QUEUE     │  ← User sets high-level goals
    │  "Map attack surface │    "Find auth bypasses on X"
    │   of 10.0.0.0/24"   │    "Enumerate subdomains of Y"
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  REASONING ENGINE    │  ← GPU 0: Qwen3-235B-A22B
    │  (CoT Planning)      │
    │                      │
    │  Input: objective +  │
    │  accumulated context │
    │  Output: next_action │
    │  structured JSON     │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  ACTION EXECUTOR     │  ← GPU 1: Fast model OR direct shell
    │                      │
    │  - Parse action JSON │
    │  - Execute tool      │
    │  - Capture output    │
    │  - Summarize result  │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │  CONTEXT ACCUMULATOR │
    │                      │
    │  - Rolling summary   │
    │  - Findings DB       │
    │  - Decision history  │
    │  - Prune old context │
    └──────────┬──────────┘
               │
               └────→ Loop back to REASONING ENGINE
                      until: objective_complete OR
                             max_iterations OR
                             user_interrupt
```

### Key Differences from Glamdring v1

| Aspect | v1 (Current) | v2 (Proposed) |
|--------|-------------|---------------|
| Loop driver | Human sends each message | Autonomous until objective met |
| Context | Raw chat history (grows unbounded) | Rolling summary + structured findings |
| Delegation | Tag-based `<task-warrior>` | Structured JSON actions with typed tools |
| Planning | Implicit in model response | Explicit plan → execute → assess cycle |
| Memory | None between sessions | SQLite findings + context snapshots |
| Models | 2x same-size on separate ports | Asymmetric: large reasoner + fast executor |

### Action Schema (Reasoning Engine Output)

```json
{
  "thought": "The nmap scan revealed ports 22, 80, 443. Port 80 returns nginx. I should enumerate directories and check for known vulns on the web services.",
  "action": {
    "tool": "nuclei",
    "args": ["-u", "http://target:80", "-t", "http/misconfiguration/", "-severity", "medium,high,critical"],
    "timeout": 120
  },
  "objective_progress": "20% — initial port scan complete, starting web enumeration",
  "next_if_success": "Analyze nuclei findings, then run ffuf for directory discovery",
  "next_if_failure": "Fall back to manual HTTP probing with curl"
}
```

### Context Window Management

The 235B model has 32K-128K context depending on quantization. To avoid overflow:

1. **Sliding summary**: After each iteration, the fast model (GPU 1) compresses the tool output into a structured summary
2. **Findings accumulate in DB**: Not in context window — queried on demand
3. **Decision log**: Last 5 decisions kept verbatim, older ones summarized
4. **Fresh injection**: Each iteration gets: objective + rolling_summary + last_tool_output + findings_count

### Implementation Plan

Phase 1: Expert-residency llama.cpp build
- Clone teamonefist/llama.cpp-experts-first
- Build with CUDA support for dual 4090
- Test with Qwen3-30B-A3B (smaller MoE, validate the mechanism)
- Benchmark: memory usage, tokens/sec at various N_SLOTS values

Phase 2: Agentic loop core
- New module: `mission_controller.py`
- Structured action schema (JSON mode from llama-server)
- Tool registry with timeout/safety controls
- Context accumulator with rolling summaries

Phase 3: Integration
- Wire reasoning engine (GPU 0) and executor (GPU 1)
- Add objective queue and progress tracking
- Session persistence (resume interrupted missions)
- Telegram reporting (findings → Imladris)

Phase 4: Offensive toolkit
- bbot integration (subdomain enum, web crawl)
- nuclei templates (vuln scanning)
- nmap scripting engine pipelines
- Custom recon chains

## Why This Works

The ihc.ru workflow succeeded because:
1. Strong reasoning decided WHAT to do next (Claude Opus-level CoT)
2. Tool execution happened immediately (shell access)
3. Results fed back for the NEXT decision (iterative)
4. Context accumulated meaningfully (not just raw dumps)

Qwen3-235B-A22B provides #1 — it's one of the strongest open reasoning models.
Expert-residency makes it fit on a single 4090.
The agentic harness provides #2, #3, and #4.

The fast model on GPU 1 handles the "grunt work": summarizing long tool outputs,
parsing structured data, and making quick yes/no decisions that don't need
235B-quality reasoning.
