import sys
import json
import yaml
from pathlib import Path
from datetime import datetime

from . import i18n, db
from .garage_core import (
    generate_session_id, agent_loop, check_health,
    TASK_WARRIOR_RE, PersonaConfig
)
from .orchestrator_harness import build_orchestrator
from .warrior_harness import build_warrior
from .commands import CommandDispatcher
from .gpu_monitor import format_status, get_gpu_stats
from .model_swapper import ModelSwapper

CYAN = "\033[1;36m"
RED = "\033[1;31m"
YELLOW = "\033[1;33m"
MAGENTA = "\033[1;35m"
GRAY = "\033[0;37m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


class GarageApp:
    def __init__(self, garage_home: Path):
        self.garage_home = garage_home
        self.config = self._load_config()
        self.session_id = generate_session_id()
        self.history: list[dict] = []
        self.running = True
        self.active_persona = "Orchestrator"
        self.harness_state = "idle"

        lang = self.config.get("language", "uk")
        i18n.init(garage_home, lang)
        db.init(garage_home)

        self.orchestrator = self._build_orchestrator()
        self.warrior = self._build_warrior()
        self.commands = CommandDispatcher(self.config, garage_home)
        self.swapper = ModelSwapper(self.config)

        self._init_session()

    def _load_config(self) -> dict:
        config_path = self.garage_home / "config.yml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _build_orchestrator(self) -> PersonaConfig:
        orch_cfg = self.config.get("orchestrator", {})
        tools = set()
        for tool_list in self.config.get("orchestrator_tools", {}).values():
            tools.update(tool_list)
        return build_orchestrator(
            port=orch_cfg.get("port", 8081),
            tools=tools,
            context_length=orch_cfg.get("context_length", 32768),
        )

    def _build_warrior(self) -> PersonaConfig:
        war_cfg = self.config.get("warrior", {})
        tools = set()
        for tool_list in self.config.get("warrior_tools", {}).values():
            tools.update(tool_list)
        return build_warrior(
            port=war_cfg.get("port", 8082),
            tools=tools,
            context_length=war_cfg.get("context_length", 32768),
        )

    def _init_session(self):
        conn = db.get_connection()
        conn.execute(
            "INSERT INTO garage_sessions (session_id, last_activity, message_count) VALUES (?, ?, 0)",
            (self.session_id, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def _swap_status(self, msg: str):
        print(f"\n{YELLOW}  [SWAP] {msg}{RESET}")

    def _status_line(self) -> str:
        now = datetime.now().strftime("%H:%M:%S")
        lang_indicator = i18n.t("language_indicator")
        gpu = format_status(get_gpu_stats())
        loaded = self.swapper.current or "none"
        persona_state = f"Active: {self.active_persona} | Loaded: {loaded}"

        conn = db.get_connection()
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM garage_findings WHERE session_id = ?",
            (self.session_id,)
        ).fetchone()
        conn.close()
        findings_count = row["cnt"] if row else 0

        return f"{DIM}{now} | {lang_indicator} | {gpu} | {persona_state} | findings: {findings_count}{RESET}"

    def _print_welcome(self):
        print(f"\n{BOLD}{'=' * 60}{RESET}")
        print(f"{BOLD}  {i18n.t('welcome')}{RESET}")
        print(f"{BOLD}{'=' * 60}{RESET}")
        print(f"{GRAY}  {i18n.t('session_started', id=self.session_id)}{RESET}")
        print(f"{GRAY}  Single-GPU mode: models swap automatically{RESET}")

        loaded = self.swapper.current
        if loaded:
            print(f"{GRAY}  Currently loaded: {loaded}{RESET}")
        else:
            print(f"{GRAY}  No model loaded — will load on first query{RESET}")

        print(f"{GRAY}  {i18n.t('help_hint')}{RESET}")
        print(f"{BOLD}{'─' * 60}{RESET}\n")

    def _ensure_model(self, persona_name: str) -> bool:
        if persona_name == "Orchestrator":
            return self.swapper.ensure_orchestrator(on_status=self._swap_status)
        else:
            return self.swapper.ensure_warrior(on_status=self._swap_status)

    def _handle_warrior_dispatch(self, orchestrator_response: str):
        matches = TASK_WARRIOR_RE.findall(orchestrator_response)
        for task_json_str in matches:
            try:
                task = json.loads(task_json_str)
            except json.JSONDecodeError:
                task = {"objective": task_json_str}

            print(f"\n{MAGENTA}  [{i18n.t('warrior_dispatch')}]{RESET}")
            print(f"{MAGENTA}  -> {task.get('objective', '?')}{RESET}\n")

            if not self._ensure_model("Warrior"):
                print(f"{RED}  [ERROR] Failed to load Warrior model{RESET}")
                return "[Warrior model failed to load]"

            self.harness_state = "working"
            warrior_msg = (
                f"TASK FROM ORCHESTRATOR:\n"
                f"Objective: {task.get('objective', '')}\n"
                f"Context: {task.get('context', '')}\n"
                f"Constraints: {task.get('constraints', 'none')}"
            )

            def on_warrior_output(text):
                for line in text.split("\n"):
                    print(f"{RED}  {line}{RESET}")

            def on_warrior_exec(cmd):
                print(f"{DIM}  $ {cmd}{RESET}")

            warrior_result = agent_loop(
                self.warrior, warrior_msg, self.session_id,
                [], on_output=on_warrior_output, on_exec=on_warrior_exec
            )

            self.harness_state = "idle"
            return warrior_result
        return None

    def run(self):
        self._print_welcome()

        while self.running:
            try:
                print(f"\n{self._status_line()}")
                persona_color = CYAN if self.active_persona == "Orchestrator" else RED
                prompt = f"{persona_color}[{self.active_persona[0]}]{RESET} > "
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                cmd_response, handled = self.commands.dispatch(user_input, self.session_id)
                if handled:
                    if cmd_response == "__QUIT__":
                        print(f"\n{GRAY}{i18n.t('goodbye')}{RESET}")
                        self.running = False
                        break
                    elif cmd_response == "__NEW_SESSION__":
                        self.session_id = generate_session_id()
                        self.history = []
                        self._init_session()
                        print(f"{GRAY}{i18n.t('session_started', id=self.session_id)}{RESET}")
                        continue
                    else:
                        print(f"{GRAY}{cmd_response}{RESET}")
                        continue

                print(f"{YELLOW}  {user_input}{RESET}")

                if not self._ensure_model(self.active_persona):
                    print(f"{RED}  [ERROR] Failed to load {self.active_persona} model{RESET}")
                    continue

                persona = self.orchestrator if self.active_persona == "Orchestrator" else self.warrior
                persona_color = CYAN if self.active_persona == "Orchestrator" else RED
                self.harness_state = "thinking"

                def on_output(text):
                    for line in text.split("\n"):
                        print(f"{persona_color}  {line}{RESET}")

                def on_exec(cmd):
                    print(f"{DIM}  $ {cmd}{RESET}")

                response = agent_loop(
                    persona, user_input, self.session_id,
                    self.history, on_output=on_output, on_exec=on_exec
                )

                self.harness_state = "idle"

                warrior_result = self._handle_warrior_dispatch(response)
                if warrior_result:
                    if not self._ensure_model("Orchestrator"):
                        print(f"{RED}  [ERROR] Failed to reload Orchestrator{RESET}")
                    else:
                        print(f"\n{CYAN}  [{i18n.t('warrior_result')}]{RESET}")
                        synth_msg = f"Warrior completed the task. Results:\n{warrior_result}\n\nSynthesize for the user."
                        self.harness_state = "thinking"
                        synth = agent_loop(
                            self.orchestrator, synth_msg, self.session_id,
                            self.history, on_output=on_output, on_exec=on_exec
                        )
                        self.harness_state = "idle"

                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": response})

                conn = db.get_connection()
                conn.execute(
                    "INSERT INTO garage_chat (session_id, role, from_persona, kind, content) VALUES (?, 'human', 'human', 'message', ?)",
                    (self.session_id, user_input)
                )
                conn.execute(
                    "INSERT INTO garage_chat (session_id, role, from_persona, kind, content) VALUES (?, 'assistant', ?, 'message', ?)",
                    (self.session_id, self.active_persona.lower(), response)
                )
                conn.execute(
                    "UPDATE garage_sessions SET last_activity = ?, message_count = message_count + 1 WHERE session_id = ?",
                    (datetime.now().isoformat(), self.session_id)
                )
                conn.commit()
                conn.close()

            except KeyboardInterrupt:
                print(f"\n{GRAY}{i18n.t('goodbye')}{RESET}")
                self.running = False
            except EOFError:
                self.running = False


def main():
    garage_home = Path.home() / ".forge-garage"
    if not garage_home.exists():
        print("Error: ~/.forge-garage not found. Run install.sh first.")
        sys.exit(1)
    app = GarageApp(garage_home)
    app.run()


if __name__ == "__main__":
    main()
