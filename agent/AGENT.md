# Use case

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
