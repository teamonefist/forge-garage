#!/usr/bin/env bash
# Forge Garage — Post-Install Extras
# Verifies model downloads, updates config.yml, copies adapters,
# builds llama.cpp with CUDA, and copies updated source files.
set -euo pipefail

GARAGE_HOME="${HOME}/.forge-garage"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="${REPO_DIR}/models"

CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
GRAY='\033[0;37m'
BOLD='\033[1m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; }
info() { echo -e "  ${CYAN}→${RESET} $1"; }

echo -e "\n${BOLD}=== Forge Garage — Post-Install Extras ===${RESET}\n"

# ─────────────────────────────────────────────────────────────
echo -e "${BOLD}[1/5] Checking model downloads${RESET}\n"
# ─────────────────────────────────────────────────────────────

WARRIOR_MODEL="${MODELS_DIR}/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf"
ORCH_SHARD_1="${MODELS_DIR}/qwen2.5-72b-instruct-q4_k_m-00001-of-00012.gguf"

MISSING=0

if [[ -f "$WARRIOR_MODEL" ]]; then
    SIZE=$(stat -c%s "$WARRIOR_MODEL" 2>/dev/null || stat -f%z "$WARRIOR_MODEL" 2>/dev/null)
    if (( SIZE > 1000000000 )); then
        ok "Warrior model: $(numfmt --to=iec $SIZE)"
    else
        fail "Warrior model exists but too small ($(numfmt --to=iec $SIZE)) — download may be incomplete"
        MISSING=1
    fi
else
    fail "Warrior model not found"
    MISSING=1
fi

SHARD_COUNT=0
for i in $(seq -w 1 12); do
    f="${MODELS_DIR}/qwen2.5-72b-instruct-q4_k_m-000${i}-of-00012.gguf"
    if [[ -f "$f" ]]; then
        SIZE=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
        if (( SIZE > 100000000 )); then
            SHARD_COUNT=$((SHARD_COUNT + 1))
        fi
    fi
done

if (( SHARD_COUNT == 12 )); then
    ok "Orchestrator model: all 12 shards present"
else
    fail "Orchestrator model: ${SHARD_COUNT}/12 shards found"
    MISSING=1
fi

if (( MISSING == 1 )); then
    echo ""
    echo -e "${YELLOW}  Some models are missing or incomplete. Download them:${RESET}"
    echo ""
    echo "  # Warrior (single file, ~42GB):"
    echo "  wget -c -O models/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf \\"
    echo "    \"https://huggingface.co/bartowski/DeepSeek-R1-Distill-Llama-70B-GGUF/resolve/main/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf\""
    echo ""
    echo "  # Orchestrator (12 shards, ~42GB total):"
    echo "  for i in \$(seq -w 1 12); do"
    echo "    wget -c -O \"models/qwen2.5-72b-instruct-q4_k_m-000\${i}-of-00012.gguf\" \\"
    echo "      \"https://huggingface.co/Qwen/Qwen2.5-72B-Instruct-GGUF/resolve/main/qwen2.5-72b-instruct-q4_k_m-000\${i}-of-00012.gguf\""
    echo "  done"
    echo ""
    read -rp "  Continue anyway? [y/N] " ans
    [[ "$ans" =~ ^[Yy] ]] || exit 1
fi

# ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[2/5] Updating config.yml${RESET}\n"
# ─────────────────────────────────────────────────────────────

CONFIG="${GARAGE_HOME}/config.yml"

if [[ ! -f "$CONFIG" ]]; then
    fail "config.yml not found at ${CONFIG} — run install.sh first"
    exit 1
fi

cp "$CONFIG" "${CONFIG}.bak-$(date +%Y%m%d-%H%M%S)"
ok "Backed up config.yml"

python3 << PYEOF
import yaml

config_path = "${CONFIG}"
with open(config_path) as f:
    config = yaml.safe_load(f)

config["orchestrator"]["model_path"] = "${MODELS_DIR}/qwen2.5-72b-instruct-q4_k_m-00001-of-00012.gguf"
config["warrior"]["model_path"] = "${MODELS_DIR}/DeepSeek-R1-Distill-Llama-70B-Q4_K_M.gguf"

wt = config.get("warrior_tools", {})
sub = wt.get("subdomain", [])
if "multiping" not in sub:
    sub.append("multiping")
    wt["subdomain"] = sub
    config["warrior_tools"] = wt

with open(config_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

print("  Model paths and warrior tools updated.")
PYEOF

ok "config.yml updated with correct model paths + multiping"

# ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[3/5] Copying adapters and updated source files${RESET}\n"
# ─────────────────────────────────────────────────────────────

# Adapters
for adapter in forge-orchestrator-lora-f16.gguf forge-warrior-lora-f16.gguf; do
    SRC="${REPO_DIR}/adapters/${adapter}"
    DST="${GARAGE_HOME}/models/${adapter}"
    if [[ -f "$SRC" ]]; then
        cp "$SRC" "$DST"
        ok "Adapter: ${adapter}"
    else
        info "Adapter not found: ${SRC} (check git lfs pull)"
    fi
done

# Python modules
cp "${REPO_DIR}"/src/lib/*.py "${GARAGE_HOME}/lib/"
ok "Python modules updated"

# Bin scripts
cp "${REPO_DIR}"/src/bin/* "${GARAGE_HOME}/bin/"
chmod +x "${GARAGE_HOME}"/bin/*
ok "Launcher scripts updated"

# i18n
cp "${REPO_DIR}"/src/i18n/*.json "${GARAGE_HOME}/i18n/" 2>/dev/null || true
ok "Language files updated"

# ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[4/5] Building llama.cpp with CUDA${RESET}\n"
# ─────────────────────────────────────────────────────────────

if command -v llama-server &>/dev/null; then
    ok "llama-server already installed: $(which llama-server)"
    read -rp "  Rebuild anyway? [y/N] " rebuild
    if [[ ! "$rebuild" =~ ^[Yy] ]]; then
        echo "  Skipping build."
        SKIP_BUILD=1
    else
        SKIP_BUILD=0
    fi
else
    SKIP_BUILD=0
fi

if (( SKIP_BUILD == 0 )); then
    BUILD_DIR="/tmp/llama-cpp-build"
    info "Cloning llama.cpp to ${BUILD_DIR}..."

    rm -rf "$BUILD_DIR"
    git clone --depth 1 https://github.com/ggml-org/llama.cpp "$BUILD_DIR"

    info "Building with CUDA support (this takes a few minutes)..."
    cd "$BUILD_DIR"
    cmake -B build -DGGML_CUDA=ON
    cmake --build build -j"$(nproc)"

    info "Installing binaries..."
    sudo cp build/bin/llama-server /usr/local/bin/
    sudo cp build/bin/llama-cli /usr/local/bin/
    sudo chmod +x /usr/local/bin/llama-server /usr/local/bin/llama-cli

    cd "$REPO_DIR"
    rm -rf "$BUILD_DIR"

    ok "llama-server installed to /usr/local/bin/"
    llama-server --version 2>&1 | head -1 || true
fi

# ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}[5/5] Verification${RESET}\n"
# ─────────────────────────────────────────────────────────────

echo "  Config model paths:"
python3 -c "
import yaml
c = yaml.safe_load(open('${CONFIG}'))
print('    Orchestrator:', c['orchestrator']['model_path'])
print('    Warrior:', c['warrior']['model_path'])
wt = c.get('warrior_tools', {}).get('subdomain', [])
print('    multiping in warrior tools:', 'multiping' in wt)
"

echo ""
echo "  Adapters in ${GARAGE_HOME}/models/:"
ls -lh "${GARAGE_HOME}/models/"*lora* 2>/dev/null || echo "    (none found)"

echo ""
if command -v llama-server &>/dev/null; then
    ok "llama-server: $(which llama-server)"
else
    fail "llama-server not found in PATH"
fi

echo -e "\n${GREEN}${BOLD}=== All done! ===${RESET}\n"
echo -e "  Launch with: ${CYAN}forge-garage${RESET}"
echo -e "  Or manually: ${CYAN}forge-garage-start orchestrator${RESET}"
echo ""
