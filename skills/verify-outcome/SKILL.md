---
name: verify-outcome
description: Check a resolution contract or proposed result against supplied evidence, including boundary cases, state transitions, Brier scoring, and VOID handling.
---
# Check the outcome against the contract

Use for domain design and independent review. Only supplied contract text, artifacts, and evidence are available. The domain role has no completed frontend output; the reviewer does. Neither can fetch a source, run code, query a chain, or establish an event by assertion.

## Separate the question from the evidence
Read the immutable question, rule, and VOID policy first. Identify the required source, observation window/timezone, units, comparator, rounding, and authority. Record omissions explicitly. Then compare available evidence to those requirements: identity, timestamp, relevant observation, conflicts, and provenance.

Choose YES only when the event meets the rule; choose NO only when sufficient evidence establishes the rule's negative case. Missing data is not automatically NO. Apply VOID only when its specified condition is met. If the contract is incomplete or evidence conflicts without a precedence rule, withhold a conclusion and identify the exact missing decision. Never add a new rule after seeing an outcome.

Worked cases should use the brief's actual semantics. For strict “above,” equality is not YES. An observation outside the stated window is not interchangeable with one inside. An unvisited URL or model explanation is not an authoritative observation.

## Inspect the simulation mechanics
The expected loop is OPEN → CLOSED → RESOLVED (YES/NO) or VOID. No new forecasts after close; no outcome before close; no silent second resolution. Manual close/attestation is a demonstration control, not independent verification of deadline, source, or authority.

For binary Brier scoring, use probabilities in 0–1 and observed `y` in {0,1}. A 70% forecast gives 0.09 for YES and 0.49 for NO. Mean over recorded forecasts only; empty data gives no score. VOID is excluded and never displayed as a perfect zero score. Distinguish observations from unique participants and score arithmetic from demonstrated calibration.

The domain role specifies these cases and handoff checks. The reviewer traces them through actual HTML/JavaScript, JSON, prose, and supplied deterministic results. Source inspection can find a defect; it cannot prove a rendered or executed flow. A static pass must not overrule a concrete contradiction.

## Report a usable result
State the permitted conclusion, exact supporting location, unresolved evidence, and next check. For defects, give file/section or code expression, user consequence, owner, and correction. Keep actual verification separate from proposed checks. If no defect is visible, say none found within the reviewed scope rather than certifying correctness or security.

A human or program's authority to record a result is separate from evidence that it is correct. This skill grants no settlement permission, wallet access, or power to revise the question contract.
