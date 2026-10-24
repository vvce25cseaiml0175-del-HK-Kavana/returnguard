"""REUSABLE DECISION PATTERN: return policy classification  (#policy)

ReturnGuard evaluates e-commerce return requests. Before the agent submits a return decision,
Strands Decider 2B classifies the request against the store's written return policy and returns
one of three actions: auto-approve, escalate to a human reviewer, or reject for fraud risk.

What it does
    Before `submit_decision` runs, the decider reads the full conversation (which includes tool
    results from the customer lookup, return request fetch and fraud-signal check) and answers
    three typed questions about the return:
    - category (choice): which return policy category fits this case?
    - violates_policy (noul): does the return break the store's return policy?
    - risk_level (score): how serious is the risk if this return is auto-approved?
    The probabilities map to a verdict: allow (auto-approve), review (escalate), block (reject).

Typed questions and options
    See QUESTIONS below. The choice options are the policy categories (standard_return,
    high_value_return, repeat_returner, fraud_suspected), each with a one-line definition. The
    noul question asks whether the return violates the policy (with the policy text embedded).
    The score question rates the risk on five levels: none, low, medium, high, critical.

Wiring
    `ReturnPolicyGuard` is a Strands `InterventionHandler`; agent/agent.py passes it to the Agent:
        Agent(..., interventions=[ReturnPolicyGuard(decider)])
    It only inspects `submit_decision`; read-only tools (lookups, fraud checks) run untouched.
    If the agent retries a guided call unchanged, the retry is denied (Guide must converge).

How to reuse it
    Copy this file, change POLICY to your own policy text, CATEGORIES to your own taxonomy, and
    reword the three questions for your domain. Thresholds are in `decide()`: change them there,
    in code you own. The `before_tool_call` method builds the state from the conversation; update
    the GUARDED_TOOLS set if your action tool has a different name.
"""

from __future__ import annotations

import json
from typing import Any

from strands.interventions import Deny, Guide, InterventionHandler, Proceed

from decider_kit import Decider

PATTERN_TAG = "#policy"
GUARDED_TOOL = "submit_decision"

POLICY = """\
E-commerce Return Policy:
1. Returns are accepted within 30 days of purchase for items in resalable condition.
2. High-value items (over $200) require additional verification before auto-approval.
3. Customers with 5 or more returns in the past 12 months are flagged for manual review.
4. Returns are rejected if fraud indicators are present: mismatched shipping and billing
   addresses, accounts less than 30 days old requesting high-value returns, or return reasons
   that are inconsistent with the order.
5. Items marked as delivered less than 48 hours ago should be reviewed for early return claims."""

CATEGORIES = {
    "standard_return": "a normal return with a valid reason, within the 30-day window, from a customer with a clean return history and no fraud indicators",
    "high_value_return": "a return for an item valued over $200 that warrants extra verification before auto-approval, even from an otherwise clean customer",
    "repeat_returner": "the customer has 5 or more past returns, which warrants manual review regardless of the current return's legitimacy",
    "fraud_suspected": "fraud indicators are present: mismatched addresses, a very new account with a high-value return, excessive past returns, or a suspicious return reason",
}

QUESTIONS = {
    "category": Decider.choice(
        "Which return policy category does this return case fall under?",
        CATEGORIES,
    ),
    "violates_policy": Decider.noul(
        f"Does this return request violate the store's return policy?\n\nPolicy:\n{POLICY}",
        {
            "true": "the return breaks at least one policy rule: outside the 30-day window, fraud indicators present, excessive past returns, high-value item needing verification, or a return reason inconsistent with the order",
            "false": "the return complies with the policy: valid reason, within the window, clean customer history, and no fraud indicators",
        },
    ),
    "risk_level": Decider.score(
        "How serious is the risk to the store if this return is auto-approved without human review?",
        ["none", "low", "medium", "high", "critical"],
    ),
}


def render_return_context(messages: list[dict[str, Any]], last: int = 24) -> str:
    """Render the conversation including tool calls and results for the policy decider."""
    lines: list[str] = []
    for m in messages[-last:]:
        role = m.get("role", "?")
        content = m.get("content", [])
        if isinstance(content, str):
            lines.append(f"{role}: {content}")
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("text"):
                lines.append(f"{role}: {block['text']}")
            elif block.get("type") == "toolUse":
                name = block.get("name", "?")
                inp = json.dumps(block.get("input", {}))
                lines.append(f"tool_call: {name}({inp})")
            elif block.get("type") == "toolResult":
                for sub in block.get("content", []):
                    if isinstance(sub, dict) and "text" in sub:
                        lines.append(f"tool_result: {sub['text']}")
    return "\n".join(lines) or "(no conversation yet)"


class ReturnPolicyGuard(InterventionHandler):
    name = "return-policy-guard"

    def __init__(
        self,
        decider: Decider,
        block_at: float = 0.7,
        review_at: float = 0.4,
        unsure_confidence: float = 0.6,
    ):
        self.decider = decider
        self.block_at = block_at
        self.review_at = review_at
        self.unsure_confidence = unsure_confidence
        self.log: list[dict[str, Any]] = []
        self._guided: set[str] = set()

    def before_invocation(self, event, **kwargs):
        self._guided.clear()
        return Proceed()

    def before_tool_call(self, event, **kwargs):
        name = event.tool_use["name"]
        if name != GUARDED_TOOL:
            return Proceed()
        args = event.tool_use.get("input") or {}
        sig = f"{name}:{json.dumps(args, sort_keys=True)}"
        if sig in self._guided:
            self.log.append({"pattern": PATTERN_TAG, "tool": name, "args": args, "verdict": "deny", "reason": "retried a guided call"})
            return Deny(reason="This exact decision was already rejected. Do not submit the same decision again.")
        state = (
            "A customer-service conversation about an e-commerce return request, then the return "
            "decision the assistant wants to submit.\n\n"
            f"--- CONVERSATION ---\n{render_return_context(event.agent.messages)}\n\n"
            f"--- PROPOSED DECISION ---\ntool: {name}\narguments: {json.dumps(args)}"
        )
        a = self.decider.ask(state, QUESTIONS)
        rec = self.decide(a, name, args)
        self.log.append(rec)
        verdict = rec["verdict"]
        if verdict == "allow":
            return Proceed()
        if verdict == "review":
            self._guided.add(sig)
            return Guide(feedback="This return needs human review. Do not submit a decision. Tell the customer their return request is being escalated to a human reviewer who will contact them shortly.")
        if verdict == "block":
            self._guided.add(sig)
            return Guide(feedback="This return is rejected. Do not submit a decision. Tell the customer their return has been rejected due to policy violations or fraud risk, and they can contact support for more details.")
        return Proceed()

    def decide(self, a: dict[str, Any], tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Turn decider probabilities into a verdict: allow, review, or block."""
        p_violation = a["violates_policy"].p_yes or 0.0
        violation_conf = a["violates_policy"].confidence or 0.0
        risk = a["risk_level"].label or "none"
        category = a["category"].label or "standard_return"

        if p_violation >= self.block_at:
            verdict = "block"
        elif risk == "critical" and p_violation >= self.review_at:
            verdict = "block"
        elif p_violation >= self.review_at or risk in ("medium", "high") or category in ("high_value_return", "repeat_returner"):
            verdict = "review"
        elif violation_conf < self.unsure_confidence and p_violation >= 0.2:
            # low confidence on a non-trivial violation probability: escalate
            verdict = "review"
        else:
            verdict = "allow"

        return {
            "pattern": PATTERN_TAG,
            "tool": tool,
            "args": args,
            "category": category,
            "p_violation": round(p_violation, 3),
            "violation_confidence": round(violation_conf, 3),
            "risk_level": risk,
            "verdict": verdict,
            "decider_ms": round(self.decider.last_latency_ms or 0),
        }
