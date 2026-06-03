"""Autonomous mission controller for the Garage agentic loop.

Drives the plan-execute-assess cycle: the reasoning engine plans the next
action, the executor runs it, and the context accumulator tracks progress.
The loop continues until the objective is met, max iterations reached,
or the operator interrupts.
"""
import json
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import db
from .garage_core import (
    PersonaConfig, validate_command, execute_command, query_model,
    FINDING_RE,
)
from .action_schema import Action, parse_action, action_to_command, validate_action
from .context_accumulator import ContextAccumulator


@dataclass
class MissionConfig:
    max_iterations: int = 20
    reasoning_persona: PersonaConfig | None = None
    executor_persona: PersonaConfig | None = None
    on_iteration: Callable | None = None  # callback(iteration, action, result)
    on_finding: Callable | None = None     # callback(finding_dict)
    on_complete: Callable | None = None    # callback(mission)


class Mission:
    def __init__(self, objective: str, session_id: str, config: MissionConfig):
        self.objective = objective
        self.session_id = session_id
        self.config = config
        self.mission_id: str = ""
        self.status: str = "pending"  # pending, running, completed, failed, stopped
        self.context = ContextAccumulator(objective=objective)
        self.started_at: float = 0.0
        self.completed_at: float = 0.0
        self._stop_requested = threading.Event()

    def request_stop(self):
        self._stop_requested.set()

    @property
    def should_stop(self) -> bool:
        return self._stop_requested.is_set()


def _create_mission_record(mission: Mission) -> str:
    conn = db.get_connection()
    cursor = conn.execute(
        "INSERT INTO garage_missions (session_id, objective, status) VALUES (?, ?, ?)",
        (mission.session_id, mission.objective, "running"),
    )
    mission_id = str(cursor.lastrowid)
    conn.commit()
    conn.close()
    return mission_id


def _record_step(mission: Mission, iteration: int, thought: str,
                 action_json: str, result_summary: str, status: str):
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO garage_mission_steps "
        "(mission_id, iteration, thought, action_json, result_summary, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (mission.mission_id, iteration, thought, action_json, result_summary, status),
    )
    conn.commit()
    conn.close()


def _update_mission_status(mission: Mission):
    conn = db.get_connection()
    conn.execute(
        "UPDATE garage_missions SET status = ?, iterations = ?, "
        "context_snapshot = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (mission.status, mission.context.iteration,
         json.dumps(mission.context.to_dict()), mission.mission_id),
    )
    conn.commit()
    conn.close()


def _record_finding(mission: Mission, severity: str, target: str, description: str):
    mission.context.record_finding(severity, target, description)
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO garage_findings (session_id, severity, target, description, source_persona) "
        "VALUES (?, ?, ?, ?, ?)",
        (mission.session_id, severity, target, description, "mission"),
    )
    conn.commit()
    conn.close()
    if mission.config.on_finding:
        mission.config.on_finding({"severity": severity, "target": target, "description": description})


def run_mission(mission: Mission) -> str:
    """Execute the autonomous plan-execute-assess loop.

    Returns a summary string of what was accomplished.
    """
    config = mission.config
    persona = config.reasoning_persona
    if not persona:
        return "[Error: no reasoning persona configured]"

    mission.started_at = time.time()
    mission.status = "running"
    mission.mission_id = _create_mission_record(mission)

    results_log = []

    for iteration in range(1, config.max_iterations + 1):
        if mission.should_stop:
            mission.status = "stopped"
            results_log.append(f"[Stopped by operator at iteration {iteration}]")
            break

        prompt = mission.context.build_prompt()
        messages = [{"role": "user", "content": prompt}]

        response = query_model(persona, messages, persona.system_prompt)
        if response.startswith("[Error"):
            mission.status = "failed"
            results_log.append(f"[Model error at iteration {iteration}: {response}]")
            break

        action = parse_action(response)
        if not action:
            results_log.append(f"[Iteration {iteration}: no valid action parsed from response]")
            mission.context.record_decision(
                thought="(unparseable response)",
                tool="none", args=[],
                outcome="failed",
                result_summary="Could not parse JSON action from model response",
            )
            _record_step(mission, iteration, response[:500], "{}", "parse failure", "failed")
            continue

        if action.done:
            mission.status = "completed"
            results_log.append(f"[Mission complete at iteration {iteration}]: {action.thought}")
            _record_step(mission, iteration, action.thought, "{}", "objective met", "completed")
            break

        valid, reason = validate_action(action, persona.tools_whitelist)
        if not valid:
            mission.context.record_decision(
                thought=action.thought, tool=action.tool, args=action.args,
                outcome="blocked", result_summary=f"Blocked: {reason}",
            )
            _record_step(mission, iteration, action.thought,
                         json.dumps(action.raw_json), f"blocked: {reason}", "blocked")
            results_log.append(f"[Iteration {iteration}: {action.tool} blocked — {reason}]")
            continue

        cmd = action_to_command(action)
        output, returncode = execute_command(cmd, timeout=action.timeout)
        outcome = "success" if returncode == 0 else "failed"

        conn = db.get_connection()
        conn.execute(
            "INSERT INTO garage_command_log (session_id, persona, command, output_chars, return_code, duration_sec) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mission.session_id, "mission", cmd, len(output), returncode, 0),
        )
        conn.commit()
        conn.close()

        result_summary = output[:500] if output else "(no output)"
        mission.context.set_last_output(output)
        mission.context.record_decision(
            thought=action.thought, tool=action.tool, args=action.args,
            outcome=outcome, result_summary=result_summary,
        )

        for m in FINDING_RE.finditer(response):
            _record_finding(mission, m.group(1), m.group(2), m.group(3))

        _record_step(mission, iteration, action.thought,
                     json.dumps(action.raw_json), result_summary, outcome)

        results_log.append(
            f"[Iteration {iteration}] {action.tool} -> {outcome} "
            f"({len(output)} chars output)"
        )

        if config.on_iteration:
            config.on_iteration(iteration, action, output)

    else:
        mission.status = "completed"
        results_log.append(f"[Max iterations ({config.max_iterations}) reached]")

    mission.completed_at = time.time()
    _update_mission_status(mission)

    if config.on_complete:
        config.on_complete(mission)

    duration = mission.completed_at - mission.started_at
    summary_lines = [
        f"Mission: {mission.objective}",
        f"Status: {mission.status}",
        f"Iterations: {mission.context.iteration}/{config.max_iterations}",
        f"Findings: {len(mission.context.findings)}",
        f"Duration: {duration:.1f}s",
        "",
    ] + results_log

    return "\n".join(summary_lines)


def resume_mission(mission_id: str, session_id: str, config: MissionConfig) -> Mission | None:
    """Resume an interrupted mission from its last checkpoint."""
    conn = db.get_connection()
    row = conn.execute(
        "SELECT objective, status, context_snapshot FROM garage_missions WHERE id = ?",
        (mission_id,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    mission = Mission(
        objective=row["objective"],
        session_id=session_id,
        config=config,
    )
    mission.mission_id = mission_id

    snapshot = row["context_snapshot"]
    if snapshot:
        mission.context = ContextAccumulator.from_dict(json.loads(snapshot))

    return mission
