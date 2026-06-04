#!/usr/bin/env bash
# Forge Garage — Security Diagnostic Script
# Run BEFORE harden.sh to check for signs of compromise
set -uo pipefail

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
    echo -e "${CYAN}  Check ${step_count}: $1${RESET}"
    echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
    echo ""
}

ok() { echo -e "${GREEN}  OK: $1${RESET}"; }
warn() { echo -e "${YELLOW}  WARNING: $1${RESET}"; }
alert() { echo -e "${RED}  ALERT: $1${RESET}"; }
info() { echo -e "${GRAY}  $1${RESET}"; }

ISSUES=0

echo ""
echo -e "${BOLD}+══════════════════════════════════════════════════════════+${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|      FORGE GARAGE — SECURITY DIAGNOSTICS                 |${RESET}"
echo -e "${BOLD}|      Діагностика безпеки сервера                         |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|  Run this BEFORE harden.sh to check for compromise       |${RESET}"
echo -e "${BOLD}|  Запустіть ДО harden.sh для перевірки безпеки            |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}+══════════════════════════════════════════════════════════+${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────
step "Directory listing test / Тест команди ls"
# ─────────────────────────────────────────────────────────────

LS_ROOT=$(ls / 2>/dev/null | wc -l)
LS_ETC=$(ls /etc 2>/dev/null | wc -l)
ECHO_ROOT=$(echo /* | wc -w)

info "ls / returned ${LS_ROOT} entries"
info "ls /etc returned ${LS_ETC} entries"
info "echo /* returned ${ECHO_ROOT} entries (shell glob bypass)"

if [[ "$LS_ROOT" -lt 5 ]]; then
    alert "ls / returned fewer than 5 entries — possible readdir() interception"
    if [[ "$ECHO_ROOT" -gt "$LS_ROOT" ]]; then
        alert "Shell glob shows more entries than ls — STRONG indicator of readdir hook"
    fi
    ISSUES=$((ISSUES + 1))
else
    ok "ls returns normal results"
fi

# ─────────────────────────────────────────────────────────────
step "LD_PRELOAD check / Перевірка LD_PRELOAD"
# ─────────────────────────────────────────────────────────────

if [[ -n "${LD_PRELOAD:-}" ]]; then
    alert "LD_PRELOAD is set: ${LD_PRELOAD}"
    ISSUES=$((ISSUES + 1))
else
    ok "LD_PRELOAD is not set"
fi

if [[ -f /etc/ld.so.preload ]]; then
    PRELOAD_CONTENT=$(cat /etc/ld.so.preload 2>/dev/null)
    if [[ -n "$PRELOAD_CONTENT" ]]; then
        alert "/etc/ld.so.preload contains: ${PRELOAD_CONTENT}"
        ISSUES=$((ISSUES + 1))
    else
        ok "/etc/ld.so.preload exists but is empty"
    fi
else
    ok "/etc/ld.so.preload does not exist"
fi

# ─────────────────────────────────────────────────────────────
step "Core binary integrity / Цілісність системних файлів"
# ─────────────────────────────────────────────────────────────

info "Checking coreutils package integrity..."
DPKG_V=$(dpkg -V coreutils 2>/dev/null || echo "UNAVAILABLE")

if [[ "$DPKG_V" == "UNAVAILABLE" ]]; then
    warn "dpkg -V not available on this system"
elif [[ -n "$DPKG_V" ]]; then
    alert "coreutils package verification FAILED:"
    echo "$DPKG_V"
    ISSUES=$((ISSUES + 1))
else
    ok "coreutils package verification passed"
fi

info "ls binary details:"
LS_PATH=$(which ls 2>/dev/null)
if [[ -n "$LS_PATH" ]]; then
    info "  Path: ${LS_PATH}"
    info "  Type: $(file "$LS_PATH" 2>/dev/null)"
    info "  Hash: $(sha256sum "$LS_PATH" 2>/dev/null)"
    info "  Size: $(stat -c '%s bytes, modified %y' "$LS_PATH" 2>/dev/null)"
fi

# ─────────────────────────────────────────────────────────────
step "Kernel modules / Модулі ядра"
# ─────────────────────────────────────────────────────────────

info "Loaded kernel modules:"
MOD_COUNT=$(lsmod 2>/dev/null | wc -l)
info "  Total modules: ${MOD_COUNT}"

SUSPICIOUS_MODS=$(lsmod 2>/dev/null | grep -iE "hide|hook|root|stealth|inject" || true)
if [[ -n "$SUSPICIOUS_MODS" ]]; then
    alert "Suspicious kernel module names detected:"
    echo "$SUSPICIOUS_MODS"
    ISSUES=$((ISSUES + 1))
else
    ok "No obviously suspicious module names"
fi

UNSIGNED=$(for mod in $(lsmod | awk 'NR>1{print $1}'); do
    modinfo "$mod" 2>/dev/null | grep -q "sig_id" || echo "$mod"
done)
if [[ -n "$UNSIGNED" ]]; then
    info "Unsigned modules (not necessarily malicious):"
    echo "$UNSIGNED" | head -10 | while read m; do info "  - $m"; done
fi

# ─────────────────────────────────────────────────────────────
step "User accounts / Облікові записи"
# ─────────────────────────────────────────────────────────────

info "Users with login shells:"
SHELL_USERS=$(grep -v -E '(nologin|false|sync|halt|shutdown)$' /etc/passwd 2>/dev/null)
echo "$SHELL_USERS" | while read line; do
    info "  $line"
done

info ""
info "Users with UID 0 (root-equivalent):"
ROOT_USERS=$(awk -F: '$3==0{print $1}' /etc/passwd)
echo "$ROOT_USERS" | while read u; do info "  $u"; done
if [[ $(echo "$ROOT_USERS" | wc -l) -gt 1 ]]; then
    alert "Multiple UID-0 accounts detected!"
    ISSUES=$((ISSUES + 1))
fi

info ""
info "Recently modified authorized_keys files (last 30 days):"
RECENT_KEYS=$(find /root /home -name "authorized_keys" -mtime -30 2>/dev/null)
if [[ -n "$RECENT_KEYS" ]]; then
    echo "$RECENT_KEYS" | while read f; do
        warn "  ${f} (modified $(stat -c '%y' "$f" 2>/dev/null))"
    done
else
    ok "No recently modified authorized_keys files"
fi

# ─────────────────────────────────────────────────────────────
step "Network / Мережа"
# ─────────────────────────────────────────────────────────────

info "Listening TCP ports:"
ss -tlnp 2>/dev/null | while read line; do info "  $line"; done

info ""
info "Established connections to external IPs:"
ss -tnp state established 2>/dev/null | grep -v "127.0.0.1" | grep -v "::1" | head -20 | while read line; do
    info "  $line"
done

# ─────────────────────────────────────────────────────────────
step "Recent logins / Останні входи"
# ─────────────────────────────────────────────────────────────

info "Last 20 logins:"
last -20 2>/dev/null | while read line; do info "  $line"; done

info ""
info "Failed login attempts (last 10):"
FAILED=$(grep "Failed password" /var/log/auth.log 2>/dev/null | tail -10)
if [[ -n "$FAILED" ]]; then
    echo "$FAILED" | while read line; do warn "  $line"; done
else
    ok "No failed logins in auth.log"
fi

# ─────────────────────────────────────────────────────────────
step "Recently modified system binaries / Нещодавно змінені файли"
# ─────────────────────────────────────────────────────────────

info "System binaries modified in the last 7 days:"
RECENT_BINS=$(find /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin \
    -type f -mtime -7 2>/dev/null | sort)
if [[ -n "$RECENT_BINS" ]]; then
    echo "$RECENT_BINS" | while read f; do
        warn "  ${f} ($(stat -c '%y' "$f" 2>/dev/null | cut -d. -f1))"
    done
else
    ok "No recently modified system binaries"
fi

# ─────────────────────────────────────────────────────────────
step "Crontabs / Планувальник завдань"
# ─────────────────────────────────────────────────────────────

info "Root crontab:"
crontab -l 2>/dev/null || info "  (empty)"

info ""
info "System cron.d entries:"
ls -la /etc/cron.d/ 2>/dev/null | while read line; do info "  $line"; done

info ""
info "/etc/crontab:"
cat /etc/crontab 2>/dev/null | grep -v "^#" | grep -v "^$" | while read line; do info "  $line"; done

# ─────────────────────────────────────────────────────────────
step "Process tree (top 50) / Дерево процесів"
# ─────────────────────────────────────────────────────────────

ps auxf 2>/dev/null | head -50 | while read line; do info "  $line"; done

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
if [[ "$ISSUES" -eq 0 ]]; then
    echo -e "${GREEN}  RESULT: No obvious indicators of compromise found${RESET}"
    echo -e "${GREEN}  РЕЗУЛЬТАТ: Явних ознак компрометації не виявлено${RESET}"
else
    echo -e "${RED}  RESULT: ${ISSUES} potential issue(s) detected — review above${RESET}"
    echo -e "${RED}  РЕЗУЛЬТАТ: Виявлено ${ISSUES} потенційних проблем — перегляньте вище${RESET}"
fi
echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
echo ""
echo -e "${GRAY}  Save this output: sudo bash diagnose.sh | tee /tmp/diag-$(date +%Y%m%d).txt${RESET}"
echo ""
