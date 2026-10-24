# ReturnGuard

**ReturnGuard — instant, intelligent return evaluation for e-commerce.**

An agent on AWS that hands one decision to **Strands Decider 2B** and the conversation to **Amazon Bedrock**. Decision pattern: `#policy`. Tags: `#strands-decider-2b` `#policy`.

- Video: (add the YouTube/Vimeo link)
- Article: (add the AWS Builder Center link)
- Deployed: run `./kit deploy`

## The project

- **Pitch:** ReturnGuard — instant, intelligent return evaluation for e-commerce.
- **Who it is for:** e-commerce customers who want fast return decisions, and stores that want
  to auto-approve legitimate returns, escalate borderline ones, and reject fraudulent ones
  without a human in the loop for every case.
- **Features:**
  - look up customer accounts, fetch return requests, and check fraud signals through chat;
  - every return decision is classified by Strands Decider 2B against the store's return policy
    before it is submitted;
  - legitimate returns are auto-approved, borderline cases are escalated to a human, and
  fraud-risk returns are rejected — all with a live decision panel showing why;
  - deployed on Amazon Bedrock AgentCore Runtime.
- **The decision handed to Strands Decider 2B:** before a return decision is submitted, is it a
  legitimate return, a high-value return needing verification, a repeat returner, or fraud?
  (`#policy`)
- **Why a decision model:** the classification runs on every return, so it must be fast, cheap
  and private, and it must return calibrated probabilities the code can branch on.
- **Amazon Bedrock:** the conversation and tool use (Amazon Nova Pro by default).



## How it is built

Strands Agents with Amazon Bedrock for the generative part, the tools in `agent/tools.py`, deployed to Amazon Bedrock AgentCore Runtime, and one decision handed to Strands Decider 2B at a clear seam in the agent's path.

Every Amazon Bedrock model id is set in `.env` (`BEDROCK_MODEL_ID`, and `BEDROCK_SMALL/MEDIUM/LARGE_MODEL_ID` for routing), Amazon Nova by default.



## Reusable decision pattern: return policy classification  (#policy)

The pattern lives in [`agent/decision.py`](agent/decision.py), labelled `REUSABLE DECISION PATTERN`. It contains the typed questions and their options, the wiring that puts the decision in the agent's path, and a note on how to reuse it:

```text
REUSABLE DECISION PATTERN: return policy classification  (#policy)

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
```

Typed questions:

```python
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
```

## Measured

Decider: strands-decider-2b-hobson-v19 (ugmdu). 12 labelled cases, 36 decisions.

| | Strands Decider 2B | skip |
|---|---|---|
| Accuracy | 77.8% | - |
| Latency p50 per decision | 8713 ms | - |
| Latency p95 | 12945 ms | - |
| Cost per 1,000 decisions | $0.0350 | $0.0000 |
| Answered alone at confidence >= 0.7 | 44% | - |
| Accuracy when confident | 87.5% | - |

Reproduce with `./kit bench` (cases in `agent/eval_cases.jsonl`; charts in `submission/bench/`).

## Run it

```bash
./kit setup        # checks your machine and AWS, sets up Strands Decider 2B (local model or hosted API)
./kit demo         # web UI at http://localhost:8501
./kit bench        # the decision vs an Amazon Bedrock LLM
./kit deploy       # Amazon Bedrock AgentCore Runtime
```

Requirements: Python 3.10+, AWS credentials with Amazon Bedrock access, and for deploying, Node 20+ with the AgentCore CLI (`./kit agentcore-cli`).

## Credits

Built with the AWS User Group Madurai Strands Decider hackathon kit (https://github.com/awsugmdu). The kit's reusable library (`decider_kit/`, the demo UI, the video and article tooling, and the Kiro steering, skills and hooks) is the user group's; the agent in `agent/` is mine. Strands Decider: https://github.com/strands-labs/strands-decider (Apache-2.0).

Licence: Apache-2.0 (see LICENSE).
