import re
import subprocess
import uuid
import json
import requests
from pathlib import Path
from dataclasses import dataclass, field

from . import db, i18n


@dataclass
class PersonaConfig:
    name: str
    port: int
    max_tokens: int = 4096
    context_length: int = 32768
    tools_whitelist: set = field(default_factory=set)
    system_prompt: str = ""


EXEC_TAG_RE = re.compile(r'<exec(?:\s+timeout="(\d+)")?>(.*?)</exec>', re.DOTALL)
TASK_WARRIOR_RE = re.compile(r'<task-warrior>(.*?)</task-warrior>', re.DOTALL)
FINDING_RE = re.compile(
    r'<finding\s+severity="([^"]+)"\s+target="([^"]*)">(.*?)</finding>', re.DOTALL
)

BANNED_PATTERNS = [
    re.compile(r'rm\s+-rf\s+/'),
    re.compile(r'mkfs\.'),
    re.compile(r'dd\s+if=.*of=/dev/'),
    re.compile(r'\bshutdown\b'),
    re.compile(r'\breboot\b'),
    re.compile(r'\bhalt\b'),
    re.compile(r'\bpoweroff\b'),
]

OUTPUT_TRUNCATE = 50000
DEFAULT_TIMEOUT = 300
MAX_ITERATIONS = 15


def generate_session_id() -> str:
    return uuid.uuid4().hex[:12]


def validate_command(cmd: str, persona: PersonaConfig) -> tuple[bool, str]:
    for pat in BANNED_PATTERNS:
        if pat.search(cmd):
            return False, i18n.t("cmd_banned", pattern=pat.pattern)

    binary = cmd.strip().split()[0] if cmd.strip() else ""
    binary = binary.split("/")[-1]

    if binary and binary not in persona.tools_whitelist:
        return False, i18n.t("cmd_not_whitelisted", cmd=binary, persona=persona.name)

    return True, ""


def execute_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, int]:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=Path.home()
        )
        output = result.stdout + result.stderr
        if len(output) > OUTPUT_TRUNCATE:
            output = output[:OUTPUT_TRUNCATE] + f"\n[truncated at {OUTPUT_TRUNCATE} chars]"
        return output, result.returncode
    except subprocess.TimeoutExpired:
        return i18n.t("timeout", sec=timeout), -1
    except Exception as e:
        return f"Error: {e}", -1


def check_health(port: int) -> bool:
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def query_model(persona: PersonaConfig, messages: list[dict], system_prompt: str,
                backend_url: str | None = None, json_mode: bool = False) -> str:
    base = backend_url or f"http://127.0.0.1:{persona.port}"
    url = f"{base}/v1/chat/completions"
    body = {
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": persona.max_tokens,
        "temperature": 0.3,
        "top_p": 0.9,
        "stop": ["</s>", "<|im_end|>", "<|end|>"],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(url, json=body, timeout=600)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.ConnectionError:
        return i18n.t("model_offline", persona=persona.name)
    except requests.exceptions.Timeout:
        return i18n.t("model_timeout", persona=persona.name)
    except Exception as e:
        return f"[Error querying {persona.name}: {e}]"


def query_model_streaming(persona: PersonaConfig, messages: list[dict], system_prompt: str):
    url = f"http://127.0.0.1:{persona.port}/v1/chat/completions"
    body = {
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": persona.max_tokens,
        "temperature": 0.3,
        "top_p": 0.9,
        "stream": True,
        "stop": ["</s>", "<|im_end|>", "<|end|>"],
    }
    try:
        resp = requests.post(url, json=body, timeout=600, stream=True)
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            content = delta.get("content", "")
            if content:
                yield content
    except requests.exceptions.ConnectionError:
        yield i18n.t("model_offline", persona=persona.name)
    except Exception as e:
        yield f"[Error: {e}]"


def agent_loop(
    persona: PersonaConfig,
    user_message: str,
    session_id: str,
    history: list[dict],
    on_output=None,
    on_exec=None,
) -> str:
    messages = list(history)
    messages.append({"role": "user", "content": user_message})

    full_response = ""
    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        response = query_model(persona, messages, persona.system_prompt)
        full_response += response

        if on_output:
            on_output(response)

        exec_matches = list(EXEC_TAG_RE.finditer(response))
        if not exec_matches:
            break

        exec_results = []
        for match in exec_matches:
            timeout = int(match.group(1)) if match.group(1) else DEFAULT_TIMEOUT
            cmd = match.group(2).strip()

            valid, reason = validate_command(cmd, persona)
            if not valid:
                result_text = f"BLOCKED: {reason}"
                returncode = -1
            else:
                if on_exec:
                    on_exec(cmd)
                result_text, returncode = execute_command(cmd, timeout)

                conn = db.get_connection()
                conn.execute(
                    "INSERT INTO garage_command_log (session_id, persona, command, output_chars, return_code, duration_sec) VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, persona.name, cmd, len(result_text), returncode, 0)
                )
                conn.commit()
                conn.close()

            exec_results.append(f"$ {cmd}\n{result_text}")

        exec_output = "\n---\n".join(exec_results)
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"[Command output]\n{exec_output}"})

    findings = FINDING_RE.findall(full_response)
    if findings:
        conn = db.get_connection()
        for severity, target, desc in findings:
            conn.execute(
                "INSERT INTO garage_findings (session_id, severity, target, title, description, source_persona) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, severity, target, desc[:80], desc, persona.name)
            )
        conn.commit()
        conn.close()

    return full_response
