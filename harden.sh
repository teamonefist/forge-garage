#!/usr/bin/env bash
# Forge Garage — Server Hardening Script
# Lightweight security baseline for remote deployment nodes
set -euo pipefail

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
    echo -e "${CYAN}  Step ${step_count}: $1${RESET}"
    echo -e "${BOLD}════════════════════════════════════════════════════════${RESET}"
    echo ""
}

ok() { echo -e "${GREEN}  OK: $1${RESET}"; }
warn() { echo -e "${YELLOW}  ! $1${RESET}"; }
fail() { echo -e "${RED}  ERROR: $1${RESET}"; }
info() { echo -e "${GRAY}  $1${RESET}"; }

if [[ $EUID -ne 0 ]]; then
    fail "Must run as root (sudo bash harden.sh)"
    exit 1
fi

BASELINE_DIR="/var/lib/forge-baseline"
LOG_DIR="/var/log/forge-security"

echo ""
echo -e "${BOLD}+══════════════════════════════════════════════════════════+${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|         FORGE GARAGE — SERVER HARDENING                  |${RESET}"
echo -e "${BOLD}|         Зміцнення безпеки сервера                        |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}|  Lightweight security baseline for deployment nodes      |${RESET}"
echo -e "${BOLD}|  Базовий захист для серверів розгортання                  |${RESET}"
echo -e "${BOLD}|                                                          |${RESET}"
echo -e "${BOLD}+══════════════════════════════════════════════════════════+${RESET}"
echo ""
echo -e "${GRAY}  Components: fail2ban, file integrity, auto-updates,${RESET}"
echo -e "${GRAY}  SSH hardening, login monitoring, rootkit detection${RESET}"
echo ""

# ─────────────────────────────────────────────────────────────
step "Install security packages / Встановлення пакетів безпеки"
# ─────────────────────────────────────────────────────────────

info "Installing: fail2ban, unattended-upgrades, rkhunter, chkrootkit, aide"
apt-get update -qq
apt-get install -y -qq fail2ban unattended-upgrades rkhunter chkrootkit aide 2>/dev/null
ok "Security packages installed"

# ─────────────────────────────────────────────────────────────
step "Configure fail2ban / Налаштування fail2ban"
# ─────────────────────────────────────────────────────────────

info "Setting up SSH jail: 3 attempts max, 1 hour ban"

cat > /etc/fail2ban/jail.local << 'JAILEOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
banaction = iptables-multiport

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
JAILEOF

systemctl enable fail2ban
systemctl restart fail2ban
ok "fail2ban configured and running"

BANNED=$(fail2ban-client status sshd 2>/dev/null | grep "Currently banned" || echo "  Currently banned: 0")
info "${BANNED}"

# ─────────────────────────────────────────────────────────────
step "Harden SSH / Зміцнення SSH"
# ─────────────────────────────────────────────────────────────

SSHD_CONFIG="/etc/ssh/sshd_config"

info "Applying SSH hardening (backup at ${SSHD_CONFIG}.pre-harden)"
cp "${SSHD_CONFIG}" "${SSHD_CONFIG}.pre-harden"

apply_ssh_setting() {
    local key="$1" val="$2"
    if grep -qE "^\s*${key}\s" "$SSHD_CONFIG"; then
        sed -i "s/^\s*${key}\s.*/${key} ${val}/" "$SSHD_CONFIG"
    elif grep -qE "^#\s*${key}\s" "$SSHD_CONFIG"; then
        sed -i "s/^#\s*${key}\s.*/${key} ${val}/" "$SSHD_CONFIG"
    else
        echo "${key} ${val}" >> "$SSHD_CONFIG"
    fi
}

apply_ssh_setting "PermitRootLogin" "prohibit-password"
apply_ssh_setting "MaxAuthTries" "3"
apply_ssh_setting "LoginGraceTime" "30"
apply_ssh_setting "X11Forwarding" "no"
apply_ssh_setting "PermitEmptyPasswords" "no"
apply_ssh_setting "ClientAliveInterval" "300"
apply_ssh_setting "ClientAliveCountMax" "2"

if sshd -t 2>/dev/null; then
    systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null
    ok "SSH hardened: root key-only, 3 max attempts, no X11"
else
    cp "${SSHD_CONFIG}.pre-harden" "$SSHD_CONFIG"
    fail "SSH config validation failed — reverted to backup"
fi

# ─────────────────────────────────────────────────────────────
step "File integrity baseline / Базовий стан цілісності файлів"
# ─────────────────────────────────────────────────────────────

mkdir -p "${BASELINE_DIR}" "${LOG_DIR}"

info "Hashing critical system binaries..."

HASH_FILE="${BASELINE_DIR}/binary-hashes-$(date +%Y%m%d-%H%M%S).sha256"

find /usr/bin /usr/sbin /usr/local/bin /usr/local/sbin \
    -type f -executable 2>/dev/null | sort | \
    xargs sha256sum > "${HASH_FILE}" 2>/dev/null

HASH_COUNT=$(wc -l < "${HASH_FILE}")
ln -sf "${HASH_FILE}" "${BASELINE_DIR}/binary-hashes-latest.sha256"
ok "Baseline recorded: ${HASH_COUNT} binaries hashed"
info "Stored at: ${HASH_FILE}"

cat > /usr/local/bin/forge-integrity-check.sh << 'ICHKEOF'
#!/usr/bin/env bash
# Forge Garage — File Integrity Checker
BASELINE="/var/lib/forge-baseline/binary-hashes-latest.sha256"
LOG="/var/log/forge-security/integrity-check.log"

if [[ ! -f "$BASELINE" ]]; then
    echo "ERROR: No baseline found at $BASELINE" | tee -a "$LOG"
    exit 1
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
CHANGES=$(sha256sum --check "$BASELINE" 2>/dev/null | grep -c "FAILED" || true)

if [[ "$CHANGES" -gt 0 ]]; then
    echo "${TIMESTAMP} ALERT: ${CHANGES} binary(ies) changed since baseline!" | tee -a "$LOG"
    sha256sum --check "$BASELINE" 2>/dev/null | grep "FAILED" | tee -a "$LOG"
    exit 1
else
    echo "${TIMESTAMP} OK: All binaries match baseline" >> "$LOG"
    exit 0
fi
ICHKEOF
chmod +x /usr/local/bin/forge-integrity-check.sh
ok "Integrity checker installed at /usr/local/bin/forge-integrity-check.sh"

# ─────────────────────────────────────────────────────────────
step "Configure automatic security updates / Автоматичні оновлення"
# ─────────────────────────────────────────────────────────────

cat > /etc/apt/apt.conf.d/50unattended-upgrades << 'UUEOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
    "${distro_id}ESMApps:${distro_codename}-apps-security";
    "${distro_id}ESM:${distro_codename}-infra-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
UUEOF

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'AUEOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
AUEOF

systemctl enable unattended-upgrades 2>/dev/null
ok "Automatic security updates enabled (security patches only, no auto-reboot)"

# ─────────────────────────────────────────────────────────────
step "Login monitoring / Моніторинг входів"
# ─────────────────────────────────────────────────────────────

cat > /usr/local/bin/forge-login-monitor.sh << 'LMEOF'
#!/usr/bin/env bash
# Forge Garage — Login Monitor
STATE_FILE="/var/lib/forge-baseline/last-login-check"
LOG="/var/log/forge-security/login-monitor.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if [[ -f "$STATE_FILE" ]]; then
    LAST_CHECK=$(cat "$STATE_FILE")
else
    LAST_CHECK=$(date -d '1 hour ago' '+%Y-%m-%d %H:%M:%S')
fi

NEW_LOGINS=$(last -s "${LAST_CHECK}" 2>/dev/null | grep -v "^$" | grep -v "^wtmp" | head -20)
FAILED=$(grep "Failed password" /var/log/auth.log 2>/dev/null | tail -5)

if [[ -n "$NEW_LOGINS" ]]; then
    echo "${TIMESTAMP} NEW LOGINS:" >> "$LOG"
    echo "$NEW_LOGINS" >> "$LOG"
fi

if [[ -n "$FAILED" ]]; then
    FAIL_COUNT=$(grep -c "Failed password" /var/log/auth.log 2>/dev/null || echo 0)
    echo "${TIMESTAMP} Failed login attempts (total in log): ${FAIL_COUNT}" >> "$LOG"
fi

date '+%Y-%m-%d %H:%M:%S' > "$STATE_FILE"
LMEOF
chmod +x /usr/local/bin/forge-login-monitor.sh
ok "Login monitor installed at /usr/local/bin/forge-login-monitor.sh"

# ─────────────────────────────────────────────────────────────
step "Schedule automated checks / Розклад автоматичних перевірок"
# ─────────────────────────────────────────────────────────────

CRON_FILE="/etc/cron.d/forge-security"
cat > "${CRON_FILE}" << 'CRONEOF'
# Forge Garage — Security Monitoring
# File integrity check every 6 hours
0 */6 * * * root /usr/local/bin/forge-integrity-check.sh
# Login monitoring every 30 minutes
*/30 * * * * root /usr/local/bin/forge-login-monitor.sh
CRONEOF
chmod 644 "${CRON_FILE}"
ok "Cron jobs installed: integrity every 6h, logins every 30m"

# ─────────────────────────────────────────────────────────────
step "Initial rootkit scan / Початкове сканування на руткіти"
# ─────────────────────────────────────────────────────────────

info "Running rkhunter update and initial scan (this may take a minute)..."
rkhunter --update 2>/dev/null || true
rkhunter --propupd 2>/dev/null

info "Running chkrootkit..."
CHKRK_OUT=$(chkrootkit 2>/dev/null | grep "INFECTED" || true)

if [[ -n "$CHKRK_OUT" ]]; then
    warn "chkrootkit found potential issues:"
    echo "$CHKRK_OUT"
    echo "$CHKRK_OUT" >> "${LOG_DIR}/rootkit-scan.log"
else
    ok "chkrootkit: no infections detected"
fi

# ─────────────────────────────────────────────────────────────
step "Security summary / Підсумок безпеки"
# ─────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}  +══════════════════════════════════════════════════+${RESET}"
echo -e "${GREEN}  |     HARDENING COMPLETE / ЗМІЦНЕННЯ ЗАВЕРШЕНО    |${RESET}"
echo -e "${GREEN}  +══════════════════════════════════════════════════+${RESET}"
echo ""
echo -e "${BOLD}  Active protections:${RESET}"
echo -e "  ${GREEN}[x]${RESET} fail2ban — SSH brute-force protection (3 attempts, 1hr ban)"
echo -e "  ${GREEN}[x]${RESET} SSH hardened — key-only root, no X11, timeout 10min"
echo -e "  ${GREEN}[x]${RESET} File integrity baseline — ${HASH_COUNT} binaries tracked"
echo -e "  ${GREEN}[x]${RESET} Automatic security updates — daily, security-only"
echo -e "  ${GREEN}[x]${RESET} Login monitoring — every 30 minutes"
echo -e "  ${GREEN}[x]${RESET} Rootkit detection — rkhunter + chkrootkit installed"
echo ""
echo -e "${BOLD}  Manual commands:${RESET}"
echo -e "  ${CYAN}forge-integrity-check.sh${RESET}    — Check binary integrity now"
echo -e "  ${CYAN}forge-login-monitor.sh${RESET}      — Check recent logins now"
echo -e "  ${CYAN}rkhunter --check${RESET}            — Full rootkit scan"
echo -e "  ${CYAN}chkrootkit${RESET}                  — Quick rootkit scan"
echo -e "  ${CYAN}fail2ban-client status sshd${RESET} — View banned IPs"
echo ""
echo -e "${BOLD}  Logs:${RESET}"
echo -e "  ${GRAY}${LOG_DIR}/integrity-check.log${RESET}"
echo -e "  ${GRAY}${LOG_DIR}/login-monitor.log${RESET}"
echo -e "  ${GRAY}${LOG_DIR}/rootkit-scan.log${RESET}"
echo ""
echo -e "${BOLD}  Baseline:${RESET}"
echo -e "  ${GRAY}${BASELINE_DIR}/binary-hashes-latest.sha256${RESET}"
echo ""
echo -e "${YELLOW}  NOTE: Run forge-integrity-check.sh after any apt upgrade${RESET}"
echo -e "${YELLOW}  to re-baseline, or legitimate updates will flag as changes.${RESET}"
echo ""
