"""ReturnGuard: an automated e-commerce return evaluation agent.

An LLM does the talking (Amazon Bedrock by default), Strands Decider 2B makes the policy
decision. When the agent proposes to submit a return decision, the decider classifies the
return against the store's return policy and routes it to auto-approve, escalate, or reject.

    from agent.agent import HackathonAgent
    out = HackathonAgent().chat("I want to return my order. Customer C001, return request RET001.")
    out["reply"], out["decisions"]
"""

from __future__ import annotations

import time
from typing import Any

from strands import Agent

from decider_kit import Decider
from decider_kit.llm import agent_model, default_model_id, image_blocks, strip_thinking

from .decision import ReturnPolicyGuard
from .tools import TOOLS

NAME = "ReturnGuard"
SYSTEM_PROMPT = """\
You are ReturnGuard, an automated e-commerce return evaluation agent. Follow these steps for \
every return request, in order:

1. Call lookup_customer with the customer ID.
2. Call fetch_return_request with the return request ID. This returns the order_id, item and amount.
3. Call check_fraud_signals with the customer ID and the order_id from step 2.
4. You MUST call submit_decision with the return request ID and your decision. Use "approve" for \
clean returns, "reject" when fraud indicators are present, "escalate" for borderline cases.

You MUST ALWAYS call submit_decision after gathering the information. Never skip step 4. Do not \
ask the customer to confirm or wait. Do not explain that you are escalating without calling \
submit_decision. Make the decision yourself based on the data and call submit_decision. Be \
brief and professional. If the customer does not provide their customer ID or return request \
ID, ask for them first."""

EAGER_PROMPT = """\
You are ReturnGuard, an automated e-commerce return evaluation agent. Act immediately and never \
ask the customer questions. Follow these steps in order:

1. Call lookup_customer with the customer ID. If missing, guess C001.
2. Call fetch_return_request with the return request ID. If missing, guess RET001.
3. Call check_fraud_signals with the customer ID and the order_id returned in step 2.
4. You MUST call submit_decision with the return request ID and "approve" as the decision.

You MUST ALWAYS call submit_decision after gathering the information. Do not ask the customer \
anything. Do not explain your plan without calling the tools. Submit "approve" by default \
unless fraud indicators are clearly present, in which case submit "reject". Be brief."""


class HackathonAgent:
    """One Strands agent per session, with the policy decision wired in."""

    def __init__(self, decider: Decider | None = None, model_id: str | None = None, eager: bool | None = None):
        import os

        self.decider = decider or Decider()
        self.eager = eager if eager is not None else os.environ.get("DEMO_EAGER") == "1"
        self.model_id = model_id or default_model_id()
        self.sessions: dict[str, tuple[Agent, ReturnPolicyGuard]] = {}

    def _session(self, session_id: str) -> tuple[Agent, ReturnPolicyGuard]:
        if session_id not in self.sessions:
            guard = ReturnPolicyGuard(self.decider)
            agent = Agent(
                model=agent_model(self.model_id),
                system_prompt=EAGER_PROMPT if self.eager else SYSTEM_PROMPT,
                tools=TOOLS,
                interventions=[guard],
                callback_handler=None,
            )
            self.sessions[session_id] = (agent, guard)
        return self.sessions[session_id]

    def chat(self, message: str, session_id: str = "default", images: list[Any] | None = None) -> dict[str, Any]:
        """Text-only agent. `images` is accepted for interface compatibility but not used."""
        agent, guard = self._session(session_id)
        before = len(guard.log)
        t0 = time.perf_counter()
        result = agent([*image_blocks(images), {"text": message}] if images else message,
                       invocation_state={"images": list(images or [])})
        reply = strip_thinking(str(result))
        return {
            "reply": reply,
            "decisions": guard.log[before:],
            "model_id": self.model_id,
            "latency_ms": round((time.perf_counter() - t0) * 1000),
            "agent": NAME,
            "eager": self.eager,
        }


if __name__ == "__main__":
    import json
    import sys

    a = HackathonAgent()
    for msg in sys.argv[1:] or [
        "I want to return my order. Customer C001, return request RET001.",
        "Hi, I'd like to return my headphones. Customer C002, return RET002.",
    ]:
        print(json.dumps(a.chat(msg), indent=1))
