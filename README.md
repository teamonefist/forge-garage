# Forge Garage

Dual-model AI harness for penetration testing and security research.
Two abliterated LLMs work together: an **Orchestrator** (planning, analysis, coordination)
and a **Warrior** (offensive execution, scanning, exploitation).

## System Requirements

- **OS**: Linux (Ubuntu 22.04+, Debian 12+, or similar)
- **GPU**: NVIDIA H100 NVL (~188GB VRAM) or equivalent
- **RAM**: 64GB+ system RAM
- **Storage**: ~200GB free for models
- **Software**: Python 3.10+, pip, CUDA toolkit, llama.cpp (llama-server)

## Recommended Models

| Role | Base Model | LoRA Fine-tune | Quantization | VRAM |
|------|-----------|---------------|-------------|------|
| Orchestrator | Qwen2.5-72B-Instruct (abliterated) | forge-orchestrator-lora-f16.gguf | Q8_0 | ~77 GB |
| Warrior | DeepSeek-R1-Distill-Llama-70B (abliterated) | forge-warrior-lora-f16.gguf | Q8_0 | ~75 GB |

**Total VRAM usage: ~152 GB** (leaves ~36GB for KV cache)

The system uses **base GGUF models + LoRA adapters** loaded at runtime.
LoRA adapters add <2GB VRAM overhead each.

### Download base models

```bash
pip install huggingface-hub

# Orchestrator base (Qwen2.5-72B, abliterated, ~77GB at Q8_0)
huggingface-cli download bartowski/Qwen2.5-72B-Instruct-abliterated-GGUF \
  --include "*Q8_0*" --local-dir ~/models/

# Warrior base (DeepSeek R1 Distill 70B, abliterated, ~75GB at Q8_0)
huggingface-cli download bartowski/huihui-ai_DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF \
  --include "*Q8_0*" --local-dir ~/models/
```

### Install LoRA adapters

The LoRA adapters are included in this package under `adapters/`:

```bash
# Copy LoRA files to model directory
cp adapters/forge-orchestrator-lora-f16.gguf ~/.forge-garage/models/
cp adapters/forge-warrior-lora-f16.gguf ~/.forge-garage/models/
```

The launcher scripts automatically detect and load LoRA adapters if present in
`~/.forge-garage/models/`. They use llama-server's `--lora` flag.

## Installation

```bash
chmod +x install.sh
./install.sh
```

The installer walks through each step interactively with explanations
in both Ukrainian and English. Press Enter after each step to continue.

## Usage

```bash
# Start everything (model backends + TUI)
forge-garage

# Or manage backends separately:
forge-garage-start    # Start model servers only
forge-garage-stop     # Stop model servers
forge-garage-status   # Check system status

# Start TUI only (if backends already running)
forge-garage --tui-only
```

## Interface Commands

| Command | Description |
|---------|-------------|
| `/help` | Show command list |
| `/language [uk\|en]` | Toggle or set language (Ukrainian/English) |
| `/persona [name]` | Switch active persona (Orchestrator/Warrior) |
| `/status` | Show backend health status |
| `/findings` | List security findings from current session |
| `/session [new\|list]` | Manage sessions |
| `/clear` | Clear screen |
| `/quit` | Exit |

## Architecture

```
User Input
    |
    v
[Orchestrator] ──── plans, analyzes, coordinates
    |
    | <task-warrior>{...}</task-warrior>
    v
[Warrior] ──── scans, exploits, generates code
    |
    | results
    v
[Orchestrator] ──── synthesizes results for user
    |
    v
User Output
```

### Communication

- Both models run as separate llama-server instances (ports 8081/8082)
- They communicate through an SQLite message bus
- The Orchestrator dispatches tasks to the Warrior via structured JSON
- The Warrior returns results which the Orchestrator synthesizes

### Tool Safety

Each persona has a whitelist of allowed commands:

- **Orchestrator**: Shell basics, programming languages, git, network read-only (curl, dig, ping)
- **Warrior**: Full offensive toolkit (nmap, sqlmap, hydra, nuclei, impacket, hashcat, etc.)

Dangerous patterns are banned for both: `rm -rf /`, `mkfs`, `dd of=/dev/`, `shutdown`, `reboot`

### Data Storage

All data is stored locally in `~/.forge-garage/`:

- `garage.db` — SQLite database (sessions, chat history, findings, command log)
- `logs/` — Runtime logs for each model backend
- `findings/` — Exported security findings

## Building llama.cpp for H100

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=90
cmake --build build --config Release -j $(nproc)
sudo cp build/bin/llama-server /usr/local/bin/
```

The `-DCMAKE_CUDA_ARCHITECTURES=90` flag optimizes for H100 (Hopper architecture).

## Troubleshooting

**Models won't load:**
- Check VRAM: `nvidia-smi`
- Check logs: `~/.forge-garage/logs/orchestrator.log`
- Ensure model paths in config.yml are correct

**Slow inference:**
- Verify all layers are on GPU: check for "offloaded X/X layers" in logs
- Ensure `--flash-attn` is supported (requires CUDA 12+)
- Consider reducing `--ctx-size` if VRAM is tight

**Permission denied:**
- All files should be owned by your user (no root needed)
- Run `chmod +x ~/.forge-garage/bin/*` if scripts aren't executable

## File Structure

```
~/.forge-garage/
├── config.yml          # Main settings
├── garage.db           # SQLite database
├── venv/               # Python virtual environment
├── lib/                # Python modules
│   ├── __init__.py
│   ├── app.py          # TUI application
│   ├── commands.py     # Slash command dispatcher
│   ├── db.py           # Database layer
│   ├── garage_core.py  # Core agent loop + validation
│   ├── gpu_monitor.py  # nvidia-smi integration
│   ├── i18n.py         # Internationalization
│   ├── orchestrator_harness.py
│   └── warrior_harness.py
├── bin/                # Launcher scripts
│   ├── forge-garage
│   ├── forge-garage-start
│   ├── forge-garage-stop
│   └── forge-garage-status
├── i18n/               # Language files
│   ├── uk.json
│   └── en.json
├── logs/               # Runtime logs
├── models/             # Model files/symlinks
├── sessions/           # Saved session state
├── findings/           # Exported reports
├── skills/             # Persona skill files
└── run/                # PID files
```

## License

Apache 2.0
