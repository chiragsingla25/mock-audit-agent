"""OpenRouter model factory and the spend guard. Imported only by agent-mode runs."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

# ToolStrategy binds tools with tool_choice="required"; Alibaba rejects that for qwen3.8 in thinking mode.
# Use effort "none": the OpenRouter SDK drops {"enabled": False} (spec Deviations, phase 0).
REASONING = {"effort": "low"}
REASONING_OVERRIDE = {"qwen/qwen3.8-flash": {"effort": "none"}}
SKEPTIC_MAX_TOKENS = 6000
# Skeptic: minimal effort. `effort` doesn't bound DeepSeek on every finding (C6 once used all 12,000 tokens at
# minimal), and a reasoning token budget can't be sent (the SDK's chat request only has effort/summary). So a
# non-reasoning fallback call answers whenever the first call gives no answer (spec Deviations, phase 4).
SKEPTIC_REASONING = {"effort": "minimal"}
SKEPTIC_FALLBACK = {"effort": "none"}
SKEPTIC_FALLBACK_MAX_TOKENS = 2000


class SpendCapExceeded(RuntimeError):
    pass


class Spend:
    """Appends each call's usage.cost to spend.jsonl and enforces the run and project caps."""

    def __init__(self, path: Path, run_id: str, run_cap: float, project_cap: float):
        self.path, self.run_id, self.run_cap, self.project_cap = Path(path), run_id, run_cap, project_cap
        self.run_cost, self.run_tokens, self.calls = 0.0, 0, 0
        self.by_control: dict[str, list[float]] = {}
        if self.path.exists():          # a resumed run continues its own totals (and its cap)
            for line in self.path.read_text().splitlines():
                x = json.loads(line) if line.strip() else {}
                if x.get("run") == run_id:
                    self.run_cost += x["cost"]
                    self.run_tokens += x["tokens"]
                    self.calls += 1
                    c = self.by_control.setdefault(x.get("control", ""), [0.0, 0])
                    c[0] += x["cost"]
                    c[1] += x["tokens"]

    def project_total(self) -> float:
        if not self.path.exists():
            return 0.0
        return sum(json.loads(line)["cost"] for line in self.path.read_text().splitlines() if line.strip())

    def guard(self) -> None:
        if self.run_cost >= self.run_cap:
            raise SpendCapExceeded(f"run spend cap US${self.run_cap:.2f} reached")
        if self.project_total() >= self.project_cap:
            raise SpendCapExceeded(f"project spend cap US${self.project_cap:.2f} reached")

    def record(self, tag: str, control_id: str, model: str, cost: float, tokens: int, reasoning: int) -> None:
        self.run_cost += cost
        self.run_tokens += tokens
        self.calls += 1
        c = self.by_control.setdefault(control_id, [0.0, 0])
        c[0] += cost
        c[1] += tokens
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({"ts": datetime.now(UTC).isoformat(), "run": self.run_id, "tag": tag,
                                "control": control_id, "model": model, "tokens": tokens,
                                "reasoning_tokens": reasoning, "cost": cost}) + "\n")


class SpendCallback(BaseCallbackHandler):
    """Guards before every LLM call and records usage.cost after it."""

    raise_error = True

    def __init__(self, spend: Spend, tag: str, control_id: str):
        self.spend, self.tag, self.control_id = spend, tag, control_id

    def on_chat_model_start(self, *args, **kwargs):
        self.spend.guard()

    def on_llm_end(self, response, **kwargs):
        for gen in response.generations[0]:
            msg = getattr(gen, "message", None)
            meta = getattr(msg, "response_metadata", {}) or {}
            usage = getattr(msg, "usage_metadata", None) or {}
            self.spend.record(self.tag, self.control_id, str(meta.get("model_name", "")), float(meta.get("cost") or 0.0),
                              int(usage.get("total_tokens", 0)),
                              int((usage.get("output_token_details") or {}).get("reasoning", 0)))


class OpenRouterModels:
    """Creates fresh tester / skeptic chat models from env (TESTER_MODEL, SKEPTIC_MODEL)."""

    def __init__(self, tester: str | None = None, skeptic: str | None = None):
        self.tester_name = tester or os.environ["TESTER_MODEL"]
        self.skeptic_name = skeptic or os.environ["SKEPTIC_MODEL"]
        if self.tester_name.split("/")[0] == self.skeptic_name.split("/")[0]:
            raise ValueError("tester and skeptic must be different model families")

    def _make(self, name: str, max_tokens: int | None = None, reasoning: dict | None = None):
        from langchain_openrouter import ChatOpenRouter
        reasoning = reasoning or REASONING_OVERRIDE.get(name, REASONING)
        return ChatOpenRouter(model=name, reasoning=reasoning, temperature=0,
                              max_retries=2, request_timeout=120_000, max_tokens=max_tokens)  # timeout in ms

    def tester(self):
        return self._make(self.tester_name)

    def skeptic(self):
        return self._make(self.skeptic_name, SKEPTIC_MAX_TOKENS, SKEPTIC_REASONING)

    def skeptic_fallback(self):
        return self._make(self.skeptic_name, SKEPTIC_FALLBACK_MAX_TOKENS, SKEPTIC_FALLBACK)
