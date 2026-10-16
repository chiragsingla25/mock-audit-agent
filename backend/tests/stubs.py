"""Scripted stub chat models for graph tests. No network."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class StubChat(BaseChatModel):
    respond: Any                       # (messages) -> AIMessage
    delay: float = 0.0
    cost: float = 0.0
    log: Any = None                    # shared call log (untyped so pydantic does not copy it)
    model_name: str = "stub"

    @property
    def _llm_type(self) -> str:
        return "stub"

    def bind_tools(self, tools, **kwargs):
        return self

    def _result(self, messages) -> ChatResult:
        msg = self.respond(messages)
        msg.response_metadata = {"cost": self.cost, "model_name": self.model_name}
        msg.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
        self.log.append(self.model_name)
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._result(messages)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.delay:
            await asyncio.sleep(self.delay)
        return self._result(messages)


def _block(text: str, name: str):
    m = re.search(rf"{name}[^\n]*:\n(.*?)(?:\n\n[A-Z][A-Za-z_ ]+[:(]|\Z)", text, re.DOTALL)
    return json.loads(m.group(1)) if m else None


def _call(name: str, args: dict, i: int = 1) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{name}_{i}", "type": "tool_call"}])


class TooManyRequestsResponseError(Exception):
    """Same class name as the OpenRouter SDK's 429 error."""


class TesterScript:
    __test__ = False
    """Raises every candidate except `dismiss` record ids; flags judgment items in `flag`."""

    def __init__(self, dismiss=(), flag=(), fail=(), slow=(), invalid_first=False, always_invalid=(),
                 fail_on_revise=False, dismiss_on_revise=False, bogus_cites=(), transient_once=()):
        self.dismiss, self.flag, self.fail, self.slow = set(dismiss), set(flag), set(fail), set(slow)
        self.invalid_first, self.always_invalid = invalid_first, set(always_invalid)
        self.fail_on_revise, self.dismiss_on_revise = fail_on_revise, dismiss_on_revise
        self.bogus_cites, self.transient_once, self.raised_transient = set(bogus_cites), set(transient_once), set()
        self.messages: dict[str, str] = {}             # control id → the human message it was given

    def __call__(self, messages) -> AIMessage:
        system = next(m.content for m in messages if isinstance(m, SystemMessage))
        cid = re.search(r"testing control (C\d+)", system).group(1)
        if cid in self.fail:
            raise RuntimeError(f"stub tester exploded on {cid}")
        if cid in self.transient_once and cid not in self.raised_transient:
            self.raised_transient.add(cid)
            raise TooManyRequestsResponseError("429 upstream rate limit (stub)")
        human = next(m.content for m in messages if isinstance(m, HumanMessage))
        self.messages.setdefault(cid, human)
        cands = _block(human, "CANDIDATES_JSON") or []
        judgment = _block(human, "JUDGMENT_STEPS_JSON") or []
        revise = _block(human, "REVISE_JSON")
        if revise and self.fail_on_revise:
            raise RuntimeError("stub tester failed during revise")
        tools = [m for m in messages if isinstance(m, ToolMessage)]
        if not tools:                                  # look at one record first, like a real tester
            if cands:
                c = cands[0]["citations"][0]
                return _call("get_record", {"source": c["source"], "record_id": c["record_id"]})
            return _call("read_policy", {"name": "x"})
        retries = [t for t in tools if "failed validation" in str(t.content)]
        if cid in self.always_invalid or (self.invalid_first and not retries):
            return _call("TesterOutput", {"decisions": [{"candidate_id": "x", "decision": "raise", "reason": "r",
                                                         "citations": []}]}, 9 + len(retries))
        decisions, findings, by_step = [], [], {}
        for c in cands:
            dismiss = c["record_id"] in self.dismiss or bool(revise and self.dismiss_on_revise)
            decisions.append({"candidate_id": c["candidate_id"], "decision": "dismiss" if dismiss else "raise",
                              "reason": "documented explanation" if dismiss else "no valid explanation",
                              "citations": c["citations"]})
            if not dismiss:
                by_step.setdefault(c["test_step"], []).append(c)
        prefix = "revised: " if revise else ""
        for step, cs in by_step.items():
            findings.append({"test_step": step, "candidate_ids": [c["candidate_id"] for c in cs],
                             "condition": f"{prefix}{len(cs)} exceptions in {step}", "criteria": "policy",
                             "effect": "risk", "recommendation": "fix it",
                             "citations": ([{"source": "hr_roster", "record_id": "E-DOES-NOT-EXIST"}]
                                           if cid in self.bogus_cites else [x for c in cs for x in c["citations"]])})
        for j in judgment:
            bad = [i for i in j["items"] if i in self.flag]
            if bad and not (revise and self.dismiss_on_revise):
                findings.append({"test_step": j["test_step"], "candidate_ids": [], "condition": f"{prefix}{bad} fail",
                                 "criteria": j["requirement"], "effect": "risk", "recommendation": "fix it",
                                 "citations": [{"source": j["source"], "record_id": i} for i in bad]})
        if revise and not self.dismiss_on_revise:   # also try to rewrite a finding that wasn't asked for; code must ignore it
            findings.append({"test_step": "completeness", "candidate_ids": [], "condition": "SHOULD NOT APPEAR",
                             "criteria": "x", "effect": "x", "recommendation": "x",
                             "citations": [{"source": "hr_roster", "record_id": "E1001"}]})
        return _call("TesterOutput", {"decisions": decisions, "findings": findings})


class SkepticScript:
    """decide(finding_id, round) -> keep | revise | reject."""

    def __init__(self, decide: Callable[[str, int], str] | None = None, silent=()):
        self.decide = decide or (lambda fid, rnd: "keep")
        self.silent = set(silent)                     # finding ids for which the model never answers
        self.seen: dict[str, int] = {}
        self.payloads: list[dict] = []

    def __call__(self, messages) -> AIMessage:
        payload = json.loads(next(m.content for m in messages if isinstance(m, HumanMessage)))
        self.payloads.append(payload)
        fid = payload["finding"]["finding_id"]
        if fid in self.silent:
            return AIMessage(content="still reasoning about it...")
        rnd = self.seen.get(fid, 0)
        self.seen[fid] = rnd + 1
        return _call("SkepticOutput", {"decision": self.decide(fid, rnd), "reason": f"stub verdict r{rnd}", "checks_failed": []})


class StubModels:
    def __init__(self, tester: TesterScript | None = None, skeptic: SkepticScript | None = None,
                 cost: float = 0.0, slow: dict | None = None, fallback: SkepticScript | None = None):
        self.tester_script = tester or TesterScript()
        self.skeptic_script = skeptic or SkepticScript()
        self.fallback_script = fallback or SkepticScript()
        self.cost, self.slow = cost, slow or {}
        self.log: list[str] = []

    def tester(self):
        script = self.tester_script

        def respond(messages):
            return script(messages)
        delay = 0.0
        return _Slow(respond=respond, cost=self.cost, log=self.log, model_name="stub-tester", slow=self.slow, delay=delay)

    def skeptic(self):
        return StubChat(respond=self.skeptic_script, cost=self.cost, log=self.log, model_name="stub-skeptic")

    def skeptic_fallback(self):
        return StubChat(respond=self.fallback_script, cost=self.cost, log=self.log, model_name="stub-skeptic-fallback")


class _Slow(StubChat):
    """Tester stub that sleeps for controls listed in `slow` (control id → seconds)."""
    slow: Any = None

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        system = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        m = re.search(r"testing control (C\d+)", system)
        if m and m.group(1) in (self.slow or {}):
            await asyncio.sleep(self.slow[m.group(1)])
        return self._result(messages)
