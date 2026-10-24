"""ReturnGuard tools: an e-commerce return system with in-memory data so the demo runs anywhere.

Tools:
  1. lookup_customer       - account age, trust score, total returns, address match
  2. fetch_return_request  - order details, return reason, days since purchase
  3. check_fraud_signals   - address mismatch, new account, multiple accounts
  4. submit_decision       - submits the final return decision (guarded by the policy check)
"""

from __future__ import annotations

from strands import tool

# --- synthetic data --------------------------------------------------------------------------

CUSTOMERS = {
    "C001": {"customer_id": "C001", "name": "Priya",    "account_age_days": 450, "trust_score": 85, "total_returns": 2, "addresses_match": True},
    "C002": {"customer_id": "C002", "name": "Arun",     "account_age_days": 15,  "trust_score": 30, "total_returns": 0, "addresses_match": False},
    "C003": {"customer_id": "C003", "name": "Meena",    "account_age_days": 800, "trust_score": 95, "total_returns": 1, "addresses_match": True},
    "C004": {"customer_id": "C004", "name": "Karthik",   "account_age_days": 120, "trust_score": 45, "total_returns": 8, "addresses_match": True},
    "C005": {"customer_id": "C005", "name": "Divya",    "account_age_days": 300, "trust_score": 70, "total_returns": 3, "addresses_match": True},
    "C006": {"customer_id": "C006", "name": "Rahul",    "account_age_days": 5,   "trust_score": 20, "total_returns": 0, "addresses_match": False},
    "C007": {"customer_id": "C007", "name": "Sneha",    "account_age_days": 200, "trust_score": 65, "total_returns": 4, "addresses_match": True},
    "C008": {"customer_id": "C008", "name": "Vikram",    "account_age_days": 60,  "trust_score": 50, "total_returns": 1, "addresses_match": True},
}

ORDERS = {
    "ORD001": {"order_id": "ORD001", "customer_id": "C001", "item": "trail running shoes",     "amount": 129.00, "status": "delivered", "purchase_date": "2026-09-28"},
    "ORD002": {"order_id": "ORD002", "customer_id": "C002", "item": "premium headphones",      "amount": 349.00, "status": "delivered", "purchase_date": "2026-10-18"},
    "ORD003": {"order_id": "ORD003", "customer_id": "C003", "item": "yoga mat",               "amount": 35.00,  "status": "delivered", "purchase_date": "2026-10-15"},
    "ORD004": {"order_id": "ORD004", "customer_id": "C004", "item": "designer jacket",        "amount": 299.00, "status": "delivered", "purchase_date": "2026-10-10"},
    "ORD005": {"order_id": "ORD005", "customer_id": "C005", "item": "blender",                 "amount": 89.00,  "status": "delivered", "purchase_date": "2026-10-05"},
    "ORD006": {"order_id": "ORD006", "customer_id": "C006", "item": "smartwatch",              "amount": 459.00, "status": "shipped",  "purchase_date": "2026-10-20"},
    "ORD007": {"order_id": "ORD007", "customer_id": "C004", "item": "water bottle",           "amount": 25.00,  "status": "delivered", "purchase_date": "2026-10-13"},
    "ORD008": {"order_id": "ORD008", "customer_id": "C007", "item": "espresso machine",       "amount": 199.00, "status": "delivered", "purchase_date": "2026-10-01"},
    "ORD009": {"order_id": "ORD009", "customer_id": "C008", "item": "desk lamp",              "amount": 45.00,  "status": "delivered", "purchase_date": "2026-10-08"},
    "ORD010": {"order_id": "ORD010", "customer_id": "C001", "item": "fitness tracker",       "amount": 159.00, "status": "delivered", "purchase_date": "2026-10-20"},
    "ORD011": {"order_id": "ORD011", "customer_id": "C008", "item": "gaming monitor",         "amount": 449.00, "status": "delivered", "purchase_date": "2026-10-16"},
    "ORD012": {"order_id": "ORD012", "customer_id": "C003", "item": "cookware set",           "amount": 219.00, "status": "delivered", "purchase_date": "2026-10-19"},
}

RETURN_REQUESTS = {
    "RET001": {"request_id": "RET001", "customer_id": "C001", "order_id": "ORD001", "reason": "defective product - sole came apart after one use",   "days_since_purchase": 25},
    "RET002": {"request_id": "RET002", "customer_id": "C002", "order_id": "ORD002", "reason": "changed my mind, don't want it anymore",             "days_since_purchase": 5},
    "RET003": {"request_id": "RET003", "customer_id": "C003", "order_id": "ORD003", "reason": "wrong size, ordered the wrong dimensions",           "days_since_purchase": 8},
    "RET004": {"request_id": "RET004", "customer_id": "C004", "order_id": "ORD004", "reason": "doesn't fit as expected, sizing was off",            "days_since_purchase": 13},
    "RET005": {"request_id": "RET005", "customer_id": "C005", "order_id": "ORD005", "reason": "product stopped working after two uses",            "days_since_purchase": 18},
    "RET006": {"request_id": "RET006", "customer_id": "C006", "order_id": "ORD006", "reason": "not as described online, features are different",     "days_since_purchase": 3},
    "RET007": {"request_id": "RET007", "customer_id": "C007", "order_id": "ORD008", "reason": "arrived damaged, the machine has a dent",            "days_since_purchase": 22},
    "RET008": {"request_id": "RET008", "customer_id": "C004", "order_id": "ORD007", "reason": "received wrong colour, wanted blue not black",        "days_since_purchase": 10},
    "RET009": {"request_id": "RET009", "customer_id": "C008", "order_id": "ORD009", "reason": "changed mind, found a cheaper option elsewhere",        "days_since_purchase": 15},
    "RET010": {"request_id": "RET010", "customer_id": "C001", "order_id": "ORD010", "reason": "fitness tracker battery dies within a day",          "days_since_purchase": 3},
    "RET011": {"request_id": "RET011", "customer_id": "C008", "order_id": "ORD011", "reason": "changed my mind, decided I don't need a new monitor", "days_since_purchase": 7},
    "RET012": {"request_id": "RET012", "customer_id": "C003", "order_id": "ORD012", "reason": "wrong size, the set is too small for my needs",        "days_since_purchase": 4},
}

DECISIONS: list[dict] = []


@tool
def lookup_customer(customer_id: str) -> dict:
    """Look up a customer's account age, trust score, return history and address match status."""
    c = CUSTOMERS.get(customer_id.strip().upper())
    return dict(c) if c else {"error": f"no customer {customer_id}"}


@tool
def fetch_return_request(request_id: str) -> dict:
    """Fetch return request details: the order, item, amount, return reason and days since purchase."""
    r = RETURN_REQUESTS.get(request_id.strip().upper())
    if not r:
        return {"error": f"no return request {request_id}"}
    o = ORDERS.get(r["order_id"], {})
    return {**r, "item": o.get("item"), "amount": o.get("amount"), "order_status": o.get("status")}


@tool
def check_fraud_signals(customer_id: str, order_id: str) -> dict:
    """Check for fraud indicators: address mismatch, new account, multiple linked accounts."""
    c = CUSTOMERS.get(customer_id.strip().upper())
    if not c:
        return {"error": f"no customer {customer_id}"}
    o = ORDERS.get(order_id.strip().upper())
    if not o:
        return {"error": f"no order {order_id}"}
    indicators = []
    if not c["addresses_match"]:
        indicators.append("shipping and billing addresses do not match")
    if c["account_age_days"] < 30:
        indicators.append(f"account is only {c['account_age_days']} days old")
    if o["amount"] > 200 and c["account_age_days"] < 30:
        indicators.append("high-value return from a very new account")
    if c["total_returns"] >= 5:
        indicators.append(f"customer has {c['total_returns']} past returns (excessive)")
    return {
        "customer_id": customer_id,
        "order_id": order_id,
        "addresses_match": c["addresses_match"],
        "new_account": c["account_age_days"] < 30,
        "account_age_days": c["account_age_days"],
        "total_returns": c["total_returns"],
        "order_amount": o["amount"],
        "fraud_indicators": indicators,
    }


@tool
def submit_decision(request_id: str, decision: str) -> dict:
    """Submit the final return decision: 'approve', 'escalate', or 'reject' (irreversible)."""
    r = RETURN_REQUESTS.get(request_id.strip().upper())
    if not r:
        return {"error": f"no return request {request_id}"}
    DECISIONS.append({"request_id": request_id, "decision": decision, "customer_id": r["customer_id"], "order_id": r["order_id"]})
    return {"submitted": decision, "request_id": request_id}


TOOLS = [lookup_customer, fetch_return_request, check_fraud_signals, submit_decision]
