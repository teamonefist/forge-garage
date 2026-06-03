#!/usr/bin/env bash
# Forge Garage — Interactive Installer
set -euo pipefail

GARAGE_HOME="${HOME}/.forge-garage"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/src"

# Colors
CYAN='\033[1;36m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
GRAY='\033[0;37m'
BOLD='\033[1m'
RESET='\033[0m'

step_count=0

step() {
    step_count=$((step_count + 1))
    echo ""
    echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
    echo -e "${CYAN}  Крок ${step_count} / Step ${step_count}: $1${RESET}"
    echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
    echo ""
}

explain_ua() {
    echo -e "${GRAY}  [UA] $1${RESET}"
}

explain_en() {
    echo -e "${GRAY}  [EN] $1${RESET}"
}

wait_enter() {
    echo ""
    echo -e "${YELLOW}  Натисніть Enter для продовження / Press Enter to continue...${RESET}"
    read -r
}

fail() {
    echo -e "${RED}  ПОМИЛКА / ERROR: $1${RESET}"
    exit 1
}

ok() {
    echo -e "${GREEN}  OK: $1${RESET}"
}

# ─────────────────────────────────────────────────────────────
# Welcome
# ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}+════════════════════════════════════════════════════��═════+${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|              FORGE GARAGE — INSTALLER                    |${RESET}"
echo -e "${BOLD}|              Встановлення Forge Garage                   |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|  Dual-model AI harness for penetration testing           |${RESET}"
echo -e "${BOLD}|  Двомодельна AI-система для тестування безпеки           |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}+══════════════════════════════════════════════════════════+${RESET}"
echo ""
echo -e "${GRAY}  Installation path: ${GARAGE_HOME}${RESET}"
echo ""
wait_enter

# ─────────────────────────────────────────────────────────────
step "Перевірка системних вимог / System Requirements Check"
# ─────────────────────────────────────────────────────────────

explain_ua "Перевіряємо наявність Python 3.10+, pip, nvidia-smi, та CUDA."
explain_en "Checking for Python 3.10+, pip, nvidia-smi, and CUDA toolkit."
echo ""

# Python
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
        ok "Python ${PY_VER}"
    else
        fail "Python 3.10+ required, found ${PY_VER}"
    fi
else
    fail "Python3 not found. Install python3 first."
fi

# pip
if python3 -m pip --version &>/dev/null; then
    ok "pip $(python3 -m pip --version | awk '{print $2}')"
else
    fail "pip not found. Install python3-pip."
fi

# nvidia-smi
if command -v nvidia-smi &>/dev/null; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader 2>/dev/null | head -1)
    ok "GPU: ${GPU_NAME} (${GPU_MEM})"
else
    echo -e "${YELLOW}  ! nvidia-smi not found. GPU features will be limited.${RESET}"
fi

# curl
if command -v curl &>/dev/null; then
    ok "curl $(curl --version | head -1 | awk '{print $2}')"
else
    fail "curl not found. Install curl."
fi

# sqlite3
if command -v sqlite3 &>/dev/null; then
    ok "sqlite3 $(sqlite3 --version | awk '{print $1}')"
else
    echo -e "${YELLOW}  ! sqlite3 CLI not found (optional, for debugging)${RESET}"
fi

wait_enter

# ─────────────────────────────────────────────────────────────
step "Створення структури директорій / Creating Directory Structure"
# ─────────────────────────────────────────────────────────────

explain_ua "Створюємо основні директорії для роботи системи."
explain_en "Creating the directory tree where the system stores its data."
echo ""
echo -e "${GRAY}  ${GARAGE_HOME}/${RESET}"
echo -e "${GRAY}  ├── lib/          (Python modules)${RESET}"
echo -e "${GRAY}  ├── bin/          (launcher scripts)${RESET}"
echo -e "${GRAY}  ├── i18n/         (language files)${RESET}"
echo -e "${GRAY}  ├── logs/         (runtime logs)${RESET}"
echo -e "${GRAY}  ├── models/       (model symlinks)${RESET}"
echo -e "${GRAY}  ├── sessions/     (saved sessions)${RESET}"
echo -e "${GRAY}  ├── findings/     (exported reports)${RESET}"
echo -e "${GRAY}  ├── skills/       (persona skills)${RESET}"
echo -e "${GRAY}  └── run/          (PID files, state)${RESET}"

mkdir -p "${GARAGE_HOME}"/{lib,bin,i18n,logs,models,sessions,findings,skills/{orchestrator,warrior},run}
ok "Directories created"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Встановлення Python залежностей / Installing Python Dependencies"
# ─────────────────────────────────────────────────────────────

explain_ua "Створюємо віртуальне середовище Python та встановлюємо бібліотеки."
explain_en "Creating a Python virtual environment and installing required libraries."
explain_ua "Бібліотеки: pyyaml (налаштування), requests (HTTP до моделей)."
explain_en "Libraries: pyyaml (settings parsing), requests (HTTP to model backends)."
echo ""

if [[ ! -d "${GARAGE_HOME}/venv" ]]; then
    python3 -m venv "${GARAGE_HOME}/venv"
    ok "Virtual environment created"
else
    ok "Virtual environment exists"
fi

source "${GARAGE_HOME}/venv/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet pyyaml requests
ok "Dependencies installed"
deactivate

wait_enter

# ─────────────────────────────────────────────────────────────
step "Перевірка llama-server / Checking llama-server"
# ─────────────────────────────────────────────────────────────

explain_ua "llama-server — це серверна частина для запуску моделей (з llama.cpp)."
explain_en "llama-server is the inference backend that serves the AI models (from llama.cpp)."
explain_ua "Він надає OpenAI-сумісний API на локальних портах."
explain_en "It exposes an OpenAI-compatible API on local ports."
echo ""

if command -v llama-server &>/dev/null; then
    LLAMA_PATH=$(which llama-server)
    ok "llama-server found at: ${LLAMA_PATH}"
else
    echo -e "${YELLOW}  ! llama-server not found in PATH${RESET}"
    echo ""
    explain_ua "Вам потрібно встановити llama.cpp. Рекомендовані способи:"
    explain_en "You need to install llama.cpp. Recommended methods:"
    echo ""
    echo -e "${GRAY}  Option 1: Build from source (recommended for H100):${RESET}"
    echo -e "${GRAY}    git clone https://github.com/ggml-org/llama.cpp${RESET}"
    echo -e "${GRAY}    cd llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build -j${RESET}"
    echo -e "${GRAY}    sudo cp build/bin/llama-server /usr/local/bin/${RESET}"
    echo ""
    echo -e "${GRAY}  Option 2: Pre-built binary (check releases page)${RESET}"
    echo ""
    echo -e "${RED}  Install llama-server before running forge-garage.${RESET}"
fi

wait_enter

# ─────────────────────────────────────────────────────────────
step "Розміщення моделей / Model Placement"
# ─────────────────────────────────────────────────────────────

explain_ua "Система використовує два GGUF-файли моделей: Оркестратор та Воїн."
explain_en "The system uses two GGUF model files: Orchestrator and Warrior."
explain_ua "Оркестратор (119B MoE) — планування та координація завдань."
explain_en "Orchestrator (119B MoE) — task planning and coordination."
explain_ua "Воїн (70B) — виконання offensive-задач, code generation."
explain_en "Warrior (70B) — offensive execution, code generation."
echo ""
echo -e "${GRAY}  Recommended models:${RESET}"
echo -e "${GRAY}  Orchestrator: Huihui-Mistral-Small-4-119B-abliterated (Q4_K_M, ~73GB)${RESET}"
echo -e "${GRAY}  Warrior:      DeepSeek-R1-Distill-Llama-70B-abliterated (Q8_0, ~75GB)${RESET}"
echo ""

ORCH_MODEL=""
WAR_MODEL=""

echo -e "${CYAN}  Enter path to Orchestrator GGUF file:${RESET}"
echo -e "${GRAY}  (or press Enter to set later in config.yml)${RESET}"
read -r -p "  > " ORCH_MODEL

echo ""
echo -e "${CYAN}  Enter path to Warrior GGUF file:${RESET}"
echo -e "${GRAY}  (or press Enter to set later in config.yml)${RESET}"
read -r -p "  > " WAR_MODEL

if [[ -n "${ORCH_MODEL}" && -f "${ORCH_MODEL}" ]]; then
    ln -sf "${ORCH_MODEL}" "${GARAGE_HOME}/models/orchestrator.gguf"
    ok "Orchestrator model linked"
elif [[ -n "${ORCH_MODEL}" ]]; then
    echo -e "${YELLOW}  ! File not found: ${ORCH_MODEL}. Set in config.yml later.${RESET}"
    ORCH_MODEL="${GARAGE_HOME}/models/orchestrator.gguf"
else
    ORCH_MODEL="${GARAGE_HOME}/models/orchestrator.gguf"
fi

if [[ -n "${WAR_MODEL}" && -f "${WAR_MODEL}" ]]; then
    ln -sf "${WAR_MODEL}" "${GARAGE_HOME}/models/warrior.gguf"
    ok "Warrior model linked"
elif [[ -n "${WAR_MODEL}" ]]; then
    echo -e "${YELLOW}  ! File not found: ${WAR_MODEL}. Set in config.yml later.${RESET}"
    WAR_MODEL="${GARAGE_HOME}/models/warrior.gguf"
else
    WAR_MODEL="${GARAGE_HOME}/models/warrior.gguf"
fi

wait_enter

# ─────────────────────────────────────────────────────────────
step "Створення файлу налаштувань / Generating Settings File"
# ─────────────────────────────────────────────────────────────

explain_ua "Створюємо config.yml з параметрами моделей, портів та дозволених інструментів."
explain_en "Creating config.yml with model paths, ports, and tool whitelists."
explain_ua "Цей файл можна змінити пізніше для точного налаштування."
explain_en "This file can be edited later for fine-tuning settings."
echo ""

# Generate config from template
sed \
    -e "s|__ORCH_MODEL_PATH__|${ORCH_MODEL}|g" \
    -e "s|__WAR_MODEL_PATH__|${WAR_MODEL}|g" \
    "${SRC_DIR}/config.yml.template" > "${GARAGE_HOME}/config.yml"

ok "config.yml created at ${GARAGE_HOME}/config.yml"
echo ""
echo -e "${GRAY}  --- Preview: ---${RESET}"
head -20 "${GARAGE_HOME}/config.yml" | while read -r line; do
    echo -e "${GRAY}  ${line}${RESET}"
done
echo -e "${GRAY}  ...${RESET}"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Створення бази даних / Database Initialization"
# ─────────────────────────────────────────────────────────────

explain_ua "Створюємо SQLite базу даних для зберігання сесій, чатів та знахідок."
explain_en "Creating SQLite database for storing sessions, chats, and findings."
explain_ua "База даних зберігається локально у ${GARAGE_HOME}/garage.db"
explain_en "Database is stored locally at ${GARAGE_HOME}/garage.db"
echo ""

python3 -c "
import sys
sys.path.insert(0, '${SRC_DIR}')
from lib import db
from pathlib import Path
db.init(Path('${GARAGE_HOME}'))
print('  Database initialized with schema.')
"
ok "garage.db created"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Встановлення мовних файлів / Installing Language Files"
# ─────────────────────────────────────────────────────────────

explain_ua "Копіюємо файли перекладу (українська та англійська)."
explain_en "Copying translation files (Ukrainian and English)."
explain_ua "Мову можна змінити командою /language у інтерфейсі."
explain_en "Language can be changed with /language command in the interface."
echo ""

cp "${SRC_DIR}/i18n/uk.json" "${GARAGE_HOME}/i18n/"
cp "${SRC_DIR}/i18n/en.json" "${GARAGE_HOME}/i18n/"
ok "Language files installed"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Копіювання основних скриптів / Copying Core Scripts"
# ─────────────────────────────────────────────────────────────

explain_ua "Копіюємо Python модулі (ядро системи) та shell-скрипти запуску."
explain_en "Copying Python modules (system core) and shell launcher scripts."
echo ""

# Copy Python lib
cp "${SRC_DIR}"/lib/*.py "${GARAGE_HOME}/lib/"
ok "Python modules copied to ${GARAGE_HOME}/lib/"

# Copy bin scripts
cp "${SRC_DIR}"/bin/* "${GARAGE_HOME}/bin/"
chmod +x "${GARAGE_HOME}"/bin/*
ok "Launcher scripts copied to ${GARAGE_HOME}/bin/"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Додавання до PATH / Adding to PATH"
# ─────────────────────────────────────────────────────────────

explain_ua "Додаємо ${GARAGE_HOME}/bin до PATH для зручного запуску."
explain_en "Adding ${GARAGE_HOME}/bin to PATH for convenient launching."
echo ""

PATH_LINE="export PATH=\"\${HOME}/.forge-garage/bin:\${PATH}\""
ADDED=false

if [[ -f "${HOME}/.bashrc" ]]; then
    if ! grep -q "forge-garage/bin" "${HOME}/.bashrc" 2>/dev/null; then
        echo "" >> "${HOME}/.bashrc"
        echo "# Forge Garage" >> "${HOME}/.bashrc"
        echo "${PATH_LINE}" >> "${HOME}/.bashrc"
        ok "Added to ~/.bashrc"
        ADDED=true
    else
        ok "Already in ~/.bashrc"
        ADDED=true
    fi
fi

if [[ -f "${HOME}/.zshrc" ]]; then
    if ! grep -q "forge-garage/bin" "${HOME}/.zshrc" 2>/dev/null; then
        echo "" >> "${HOME}/.zshrc"
        echo "# Forge Garage" >> "${HOME}/.zshrc"
        echo "${PATH_LINE}" >> "${HOME}/.zshrc"
        ok "Added to ~/.zshrc"
        ADDED=true
    else
        ok "Already in ~/.zshrc"
        ADDED=true
    fi
fi

if [[ "${ADDED}" == "false" ]]; then
    echo -e "${YELLOW}  Could not detect shell config. Add manually:${RESET}"
    echo -e "${YELLOW}  ${PATH_LINE}${RESET}"
fi

export PATH="${GARAGE_HOME}/bin:${PATH}"

wait_enter

# ─────────────────────────────────────────────────────────────
step "Тестовий запуск / Smoke Test"
# ─────────────────────────────────────────────────────────────

explain_ua "Перевіряємо, що Python модулі завантажуються без помилок."
explain_en "Verifying that Python modules load without errors."
echo ""

source "${GARAGE_HOME}/venv/bin/activate"
PYTHONPATH="${GARAGE_HOME}/lib" python3 -c "
from lib import i18n, db, garage_core
from lib.orchestrator_harness import build_orchestrator
from lib.warrior_harness import build_warrior
from lib.commands import CommandDispatcher
from lib.gpu_monitor import get_gpu_stats
from pathlib import Path

# Test i18n
i18n.init(Path('${GARAGE_HOME}'), 'uk')
assert i18n.t('welcome') != '[welcome]', 'i18n failed'

# Test settings loading
import yaml
config = yaml.safe_load(open('${GARAGE_HOME}/config.yml'))
assert 'orchestrator' in config, 'settings missing orchestrator'
assert 'warrior' in config, 'settings missing warrior'

print('  All modules loaded successfully.')
print('  i18n: ' + i18n.t('welcome'))
print('  Settings: OK')
print('  GPU monitor: ' + str(get_gpu_stats()))
"
deactivate

if [[ $? -eq 0 ]]; then
    ok "Smoke test passed"
else
    echo -e "${RED}  Smoke test FAILED. Check errors above.${RESET}"
fi

wait_enter

# ─────────────────────────────────────────────────────────────
step "Готово! / Installation Complete!"
# ─────────────────────────────────────────────────────────────

echo -e "${GREEN}"
echo "  +══════════════════════════════════════════════════+"
echo "  |        ВСТАНОВЛЕННЯ ЗАВЕРШЕНО!                   |"
echo "  |        INSTALLATION COMPLETE!                    |"
echo "  +══════════════════════════════════════════════════+"
echo -e "${RESET}"
echo ""
echo -e "${BOLD}  How to use:${RESET}"
echo ""
echo -e "  ${CYAN}forge-garage${RESET}          — Start full system (backends + TUI)"
echo -e "  ${CYAN}forge-garage-start${RESET}    — Start model backends only"
echo -e "  ${CYAN}forge-garage-stop${RESET}     — Stop model backends"
echo -e "  ${CYAN}forge-garage-status${RESET}   — Check system status"
echo ""
echo -e "${BOLD}  Next steps:${RESET}"
echo ""
echo -e "  1. Download GGUF models:"
echo -e "     ${GRAY}Orchestrator: huihui-ai/Huihui-Mistral-Small-4-119B-2603-BF16-abliterated-GGUF${RESET}"
echo -e "     ${GRAY}Warrior: bartowski/huihui-ai_DeepSeek-R1-Distill-Llama-70B-abliterated-GGUF${RESET}"
echo ""
echo -e "  2. Edit model paths in settings:"
echo -e "     ${GRAY}nano ${GARAGE_HOME}/config.yml${RESET}"
echo ""
echo -e "  3. Build llama.cpp with CUDA:"
echo -e "     ${GRAY}git clone https://github.com/ggml-org/llama.cpp${RESET}"
echo -e "     ${GRAY}cd llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build -j${RESET}"
echo ""
echo -e "  4. Launch: ${CYAN}forge-garage${RESET}"
echo ""
echo -e "${GRAY}  Reload shell: source ~/.bashrc (or ~/.zshrc)${RESET}"
echo ""
