# Requirements: ReturnGuard

## User stories

1. As an e-commerce customer, I want to submit a return request and get an instant decision
   (auto-approve, escalate, or reject), so I don't wait days for a manual review when my return
   is clearly legitimate.
2. As the store, I want returns auto-approved only when they are safe, escalated when they need
   a human, and rejected when fraud is likely, so I protect revenue without blocking good
   customers.
3. As a store operator, I want the decision criteria to be transparent and configurable, so I can
   audit why each return was handled the way it was.

## Acceptance criteria (EARS)

- WHEN the agent proposes `submit_decision`, THE agent SHALL ask Strands Decider 2B to classify
  the return request against the store's return policy BEFORE the tool runs.
- IF the decider finds no policy violation (P < 0.4) and low risk, THEN the return SHALL be
  auto-approved (Proceed).
- IF the decider finds a likely policy violation (P >= 0.7) or high/critical risk, THEN the
  return SHALL be rejected (Guide the agent to inform the customer).
- WHILE the decider is uncertain (0.4 <= P < 0.7) or the risk is medium, THEN the return SHALL
  be escalated to a human reviewer (Guide the agent to inform the customer).
- IF the decider is low-confidence (confidence < 0.6), THEN the return SHALL be escalated rather
  than auto-approved.
- IF the agent retries the same `submit_decision` call unchanged after being guided, THEN the
  call SHALL be denied.
- THE agent SHALL use Amazon Bedrock (Amazon Nova Pro by default) for the conversation.
- THE agent SHALL gather customer data, return request details, and fraud signals via tools
  before the policy check runs.
