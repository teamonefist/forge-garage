"""Structured JSON action parsing and validation for agentic loop missions."""
import json
import re
from dataclasses import dataclass, field

JSON_BLOCK_RE = re.compile(r'```json\s*(.*?)```', re.DOTALL)
RAW_JSON_RE = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)


@dataclass
class Action:
    tool: str
    args: list[str] = field(default_factory=list)
    timeout: int = 300
    thought: str = ""
    objective_progress: str = ""
    next_if_success: str = ""
    next_if_failure: str = ""
    done: bool = False
    delegate_to: str | None = None
    raw_json: dict = field(default_factory=dict)


@dataclass
class ExecutorResult:
    status: str  # complete, failed, blocked
    commands_run: list[dict] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    summary: str = ""
    exit_code: int = 0


def parse_action(response: str) -> Action | None:
    """Extract a structured JSON action from model output.

    Supports:
    - Pure JSON response
    - JSON inside ```json``` fences
    - JSON embedded in prose (first valid object with 'action' or 'tool' key)
    """
    candidates = []

    fenced = JSON_BLOCK_RE.findall(response)
    for block in fenced:
        try:
            candidates.append(json.loads(block.strip()))
        except json.JSONDecodeError:
            continue

    if not candidates:
        try:
            candidates.append(json.loads(response.strip()))
        except json.JSONDecodeError:
            pass

    if not candidates:
        for match in RAW_JSON_RE.finditer(response):
            try:
                obj = json.loads(match.group())
                if "action" in obj or "tool" in obj or "done" in obj:
                    candidates.append(obj)
            except json.JSONDecodeError:
                continue

    if not candidates:
        return None

    obj = candidates[0]

    if obj.get("done", False) and "action" not in obj:
        return Action(tool="", done=True, thought=obj.get("thought", ""),
                      objective_progress=obj.get("objective_progress", ""),
                      raw_json=obj)

    action_data = obj.get("action", obj)
    tool = action_data.get("tool", "")
    if not tool:
        return None

    args = action_data.get("args", [])
    if isinstance(args, str):
        args = args.split()

    return Action(
        tool=tool,
        args=args,
        timeout=action_data.get("timeout", 300),
        thought=obj.get("thought", ""),
        objective_progress=obj.get("objective_progress", ""),
        next_if_success=obj.get("next_if_success", ""),
        next_if_failure=obj.get("next_if_failure", ""),
        done=obj.get("done", False),
        delegate_to=action_data.get("delegate_to"),
        raw_json=obj,
    )


def action_to_command(action: Action) -> str:
    """Convert an Action to a shell command string."""
    parts = [action.tool] + action.args
    return " ".join(parts)


def validate_action(action: Action, whitelist: set, blacklist: set | None = None) -> tuple[bool, str]:
    """Check action against tool whitelist/blacklist."""
    if not action.tool:
        if action.done:
            return True, "mission complete"
        return False, "no tool specified"

    tool_name = action.tool.split("/")[-1].split()[0]

    if blacklist and tool_name in blacklist:
        return False, f"{tool_name} is blacklisted"

    if whitelist and tool_name not in whitelist:
        return False, f"{tool_name} not in whitelist"

    return True, "ok"
