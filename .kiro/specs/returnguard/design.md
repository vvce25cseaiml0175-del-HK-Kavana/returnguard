# Design: ReturnGuard

## Overview

ReturnGuard is an e-commerce return evaluation agent. A customer submits a return request; the
agent gathers customer account data, return request details, and fraud signals via tools, then
Strands Decider 2B classifies the return against the store's return policy before any decision is
submitted. The verdict routes the return to one of three outcomes: auto-approve, escalate to a
human reviewer, or reject for fraud risk.

## Decision pattern: #policy

- **Seam:** `InterventionHandler.before_tool_call` (`agent/decision.py: ReturnPolicyGuard`),
  only for `submit_decision`.
- **State:** the conversation (including tool results from lookups) followed by the proposed
  decision, rendered as `--- RETURN EVALUATION --- ... --- PROPOSED DECISION ---`.
- **Questions:** `category` (choice), `violates_policy` (noul), `risk_level` (score).
  - `category`: standard_return, high_value_return, repeat_returner, fraud_suspected.
  - `violates_policy`: does the return break the store's return policy?
  - `risk_level`: none, low, medium, high, critical (how serious is the risk if auto-approved).
- **Policy thresholds (in `decide()`):**
  - P(violation) >= 0.7: reject (block).
  - risk == critical AND P(violation) >= 0.4: reject (block).
  - P(violation) >= 0.4 OR risk in (medium, high) OR category in (high_value_return, repeat_returner):
    escalate (review).
  - Low confidence (P_violation confidence < 0.6) with P(violation) >= 0.2: escalate.
  - Otherwise: auto-approve (allow).
  - A retried guided call: Deny (convergence).

## Tools

1. `lookup_customer(customer_id)` — account age, trust score, total returns, address match.
2. `fetch_return_request(request_id)` — order details, return reason, days since purchase.
3. `check_fraud_signals(customer_id, order_id)` — address mismatch, new account, multiple accounts.
4. `submit_decision(request_id, decision)` — submits the final decision (guarded by the policy check).

## Data

Synthetic sample return scenarios generated locally (inline mock data in `agent/tools.py`).
Six customers, six orders, eight return requests covering all three outcomes plus near-miss cases.

## Agent

- **LLM:** Amazon Bedrock (Amazon Nova Pro by default); UGM cloud for local building.
- **System prompt:** gather data, then propose a decision. Brief and professional.
- **Wiring:** `Agent(model=..., tools=TOOLS, interventions=[ReturnPolicyGuard(decider)])`.
