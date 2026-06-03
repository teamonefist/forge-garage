import threading
from pathlib import Path
from . import i18n, db
from .garage_core import check_health


class CommandDispatcher:
    def __init__(self, config: dict, garage_home: Path):
        self.config = config
        self.garage_home = garage_home
        self._active_mission = None
        self._mission_thread = None

    def dispatch(self, raw_input: str, session_id: str) -> tuple[str, bool]:
        if not raw_input.startswith("/"):
            return "", False

        parts = raw_input[1:].split(None, 1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        handler = getattr(self, f"cmd_{cmd}", None)
        if handler:
            return handler(args, session_id), True
        return i18n.t("cmd_unknown", cmd=cmd), True

    def cmd_help(self, args: str, session_id: str) -> str:
        return i18n.t("help_text")

    def cmd_language(self, args: str, session_id: str) -> str:
        current = i18n.current()
        if not args:
            new_lang = "en" if current == "uk" else "uk"
        elif args.lower() in ("uk", "ua", "ukrainian", "українська"):
            new_lang = "uk"
        elif args.lower() in ("en", "english", "англійська"):
            new_lang = "en"
        else:
            return i18n.t("language_invalid")

        i18n.set_language(new_lang)
        self.config["language"] = new_lang
        return i18n.t("language_changed", lang=new_lang)

    def cmd_persona(self, args: str, session_id: str) -> str:
        if not args:
            return i18n.t("persona_current", name=self.config.get("active_persona", "Orchestrator"))
        name = args.strip().capitalize()
        if name not in ("Orchestrator", "Warrior"):
            return i18n.t("persona_invalid")
        self.config["active_persona"] = name
        return i18n.t("persona_switched", name=name)

    def cmd_status(self, args: str, session_id: str) -> str:
        orch_port = self.config.get("orchestrator", {}).get("port", 8081)
        war_port = self.config.get("warrior", {}).get("port", 8082)
        orch_ok = check_health(orch_port)
        war_ok = check_health(war_port)
        return i18n.t("status_report",
                      orch_status="online" if orch_ok else "offline",
                      war_status="online" if war_ok else "offline")

    def cmd_findings(self, args: str, session_id: str) -> str:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT severity, target, description, created_at FROM garage_findings WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        ).fetchall()
        conn.close()

        if not rows:
            return i18n.t("no_findings")

        lines = [i18n.t("findings_header", count=len(rows))]
        for row in rows:
            lines.append(f"  [{row['severity'].upper()}] {row['target']}: {row['description'][:100]}")
        return "\n".join(lines)

    def cmd_clear(self, args: str, session_id: str) -> str:
        return "\033[2J\033[H"

    def cmd_session(self, args: str, session_id: str) -> str:
        if args.strip() == "new":
            return "__NEW_SESSION__"
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT session_id, started_at, message_count FROM garage_sessions ORDER BY started_at DESC LIMIT 10"
        ).fetchall()
        conn.close()
        if not rows:
            return i18n.t("no_sessions")
        lines = [i18n.t("sessions_header")]
        for row in rows:
            marker = " <-" if row["session_id"] == session_id else ""
            lines.append(f"  {row['session_id']} | {row['started_at']} | {row['message_count']} msgs{marker}")
        return "\n".join(lines)

    def cmd_mission(self, args: str, session_id: str) -> str:
        if not args:
            return i18n.t("mission_usage") if "mission_usage" in i18n._strings else (
                "Usage: /mission <objective>\nStarts an autonomous mission that loops until the objective is met."
            )

        if self._active_mission and self._active_mission.status == "running":
            return "A mission is already running. Use /mission-stop first."

        from .mission_controller import Mission, MissionConfig, run_mission
        from .warrior_harness import build_warrior
        from .orchestrator_harness import build_orchestrator

        orch_port = self.config.get("orchestrator", {}).get("port", 8081)
        orch_tools = set(self.config.get("orchestrator", {}).get("tools", []))
        persona = build_orchestrator(orch_port, orch_tools)

        mc = MissionConfig(
            max_iterations=20,
            reasoning_persona=persona,
        )

        self._active_mission = Mission(
            objective=args.strip(),
            session_id=session_id,
            config=mc,
        )

        def _run():
            result = run_mission(self._active_mission)
            self._mission_result = result

        self._mission_thread = threading.Thread(target=_run, daemon=True)
        self._mission_thread.start()
        return f"Mission started: {args.strip()}\nUse /mission-status to check progress, /mission-stop to halt."

    def cmd_mission_status(self, args: str, session_id: str) -> str:
        if not self._active_mission:
            conn = db.get_connection()
            rows = conn.execute(
                "SELECT id, objective, status, iterations, started_at FROM garage_missions "
                "ORDER BY started_at DESC LIMIT 5"
            ).fetchall()
            conn.close()
            if not rows:
                return "No missions found."
            lines = ["Recent missions:"]
            for row in rows:
                lines.append(f"  #{row['id']} [{row['status']}] {row['objective'][:60]} ({row['iterations']} iters)")
            return "\n".join(lines)

        m = self._active_mission
        ctx = m.context
        return (
            f"Mission: {m.objective}\n"
            f"Status: {m.status}\n"
            f"Iteration: {ctx.iteration}\n"
            f"Findings: {len(ctx.findings)}\n"
            f"Last tool: {ctx.decisions[-1].tool if ctx.decisions else 'none'}"
        )

    def cmd_mission_stop(self, args: str, session_id: str) -> str:
        if not self._active_mission or self._active_mission.status != "running":
            return "No active mission to stop."
        self._active_mission.request_stop()
        return "Stop requested. Mission will halt after current iteration."

    def cmd_quit(self, args: str, session_id: str) -> str:
        return "__QUIT__"
