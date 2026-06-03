"""Context window management for agentic loop missions.

Maintains a rolling summary of mission progress, findings, and decisions
so the reasoning engine stays within context limits across many iterations.
"""
import json
from dataclasses import dataclass, field

MAX_VERBATIM_DECISIONS = 5
MAX_TOOL_OUTPUT_CHARS = 8000
SUMMARY_TARGET_CHARS = 2000


@dataclass
class Decision:
    iteration: int
    thought: str
    tool: str
    args: list[str]
    outcome: str  # success, failed, blocked
    result_summary: str


@dataclass
class ContextAccumulator:
    objective: str
    decisions: list[Decision] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    rolling_summary: str = ""
    iteration: int = 0
    last_tool_output: str = ""

    def record_decision(self, thought: str, tool: str, args: list[str],
                        outcome: str, result_summary: str):
        self.iteration += 1
        self.decisions.append(Decision(
            iteration=self.iteration,
            thought=thought,
            tool=tool,
            args=args,
            outcome=outcome,
            result_summary=result_summary,
        ))
        self._compact_decisions()

    def record_finding(self, severity: str, target: str, description: str):
        self.findings.append({
            "severity": severity,
            "target": target,
            "description": description,
            "iteration": self.iteration,
        })

    def set_last_output(self, output: str):
        if len(output) > MAX_TOOL_OUTPUT_CHARS:
            self.last_tool_output = (
                output[:MAX_TOOL_OUTPUT_CHARS]
                + f"\n[truncated — {len(output)} chars total]"
            )
        else:
            self.last_tool_output = output

    def build_prompt(self) -> str:
        """Assemble the context window for the reasoning engine."""
        sections = []

        sections.append(f"OBJECTIVE: {self.objective}")
        sections.append(f"ITERATION: {self.iteration + 1}")

        if self.rolling_summary:
            sections.append(f"PROGRESS SUMMARY:\n{self.rolling_summary}")

        if self.findings:
            finding_lines = []
            for f in self.findings[-10:]:
                finding_lines.append(
                    f"  [{f['severity'].upper()}] {f['target']}: {f['description'][:120]}"
                )
            sections.append(f"FINDINGS ({len(self.findings)} total):\n" + "\n".join(finding_lines))

        recent = self.decisions[-MAX_VERBATIM_DECISIONS:]
        if recent:
            decision_lines = []
            for d in recent:
                cmd = f"{d.tool} {' '.join(d.args)}" if d.args else d.tool
                decision_lines.append(
                    f"  #{d.iteration} [{d.outcome}] {cmd}\n"
                    f"    Thought: {d.thought[:200]}\n"
                    f"    Result: {d.result_summary[:300]}"
                )
            sections.append("RECENT DECISIONS:\n" + "\n".join(decision_lines))

        if self.last_tool_output:
            sections.append(f"LAST TOOL OUTPUT:\n{self.last_tool_output}")

        sections.append(
            "Respond with a JSON action. Set done=true if the objective is met.\n"
            "Schema: {\"thought\": \"...\", \"action\": {\"tool\": \"...\", \"args\": [...], "
            "\"timeout\": N}, \"objective_progress\": \"...\", \"done\": false, "
            "\"next_if_success\": \"...\", \"next_if_failure\": \"...\"}"
        )

        return "\n\n".join(sections)

    def _compact_decisions(self):
        """Summarize old decisions to keep context manageable."""
        if len(self.decisions) <= MAX_VERBATIM_DECISIONS:
            return

        old = self.decisions[:-MAX_VERBATIM_DECISIONS]
        summary_parts = []
        if self.rolling_summary:
            summary_parts.append(self.rolling_summary)

        for d in old:
            cmd = f"{d.tool} {' '.join(d.args)}" if d.args else d.tool
            summary_parts.append(
                f"Step {d.iteration}: {cmd} -> {d.outcome}. {d.result_summary[:150]}"
            )

        self.rolling_summary = "\n".join(summary_parts)
        if len(self.rolling_summary) > SUMMARY_TARGET_CHARS:
            self.rolling_summary = self.rolling_summary[-SUMMARY_TARGET_CHARS:]

        self.decisions = self.decisions[-MAX_VERBATIM_DECISIONS:]

    def to_dict(self) -> dict:
        return {
            "objective": self.objective,
            "iteration": self.iteration,
            "rolling_summary": self.rolling_summary,
            "findings": self.findings,
            "decisions": [
                {
                    "iteration": d.iteration, "thought": d.thought,
                    "tool": d.tool, "args": d.args,
                    "outcome": d.outcome, "result_summary": d.result_summary,
                }
                for d in self.decisions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextAccumulator":
        acc = cls(
            objective=data["objective"],
            iteration=data.get("iteration", 0),
            rolling_summary=data.get("rolling_summary", ""),
            findings=data.get("findings", []),
        )
        for d in data.get("decisions", []):
            acc.decisions.append(Decision(**d))
        return acc
