---
name: specify-market
description: Define a forecast question's exact meaning, resolution cases, and VOID boundaries without changing its approved contract.
---
# Specify a forecast contract

Use for product, architecture, and domain work. The frozen brief is the source of truth for `market_question`, `resolution_rule`, and `void_policy`. Preserve those strings in generated contracts and visible app copy. Recommend clarifications separately; no role can silently rewrite the brief.

## Make ambiguity visible
Extract only what is supplied: event and subject; observation window and timezone; closing policy; authoritative source; units; comparator; rounding; attesting authority; dispute window; and finality. Distinguish forecast closing from event observation and later result publication. A future time must not be invented to fill a missing field.

Use a short unresolved-decisions list for absent details. Avoid “standard rules apply” or an unnamed AI oracle. If the rule is “strictly above 100,” equality at 100 is NO; if it is “at least 100,” equality is YES. Rounding before comparison may change the result and must come from the contract, not convenience.

## Work the decision cases
Describe one supported YES case, one supported NO case, and the supplied policy's VOID case using the actual question. Include an equality, missing-source, delayed-publication, or conflicting-source case if it affects this event.

A missing observation is not evidence for NO. It is also not automatically VOID: apply the stated VOID rule; otherwise withhold resolution and identify the missing decision. If the brief lacks enough detail to choose a case, explain the ambiguity instead of making the case seem resolved.

## Match the local implementation
This run is a browser simulation: OPEN accepts forecasts; CLOSED rejects new ones; a human records YES, NO, or VOID; the final state is RESOLVED or VOID. A manual close control does not prove a real deadline was enforced. Attesting a result does not establish the underlying event.

The domain JSON contains `question`, `resolution_rule`, `void_policy`, `mode: "offchain-simulation"`, and `outcomes: ["YES", "NO", "VOID"]`. It declares semantics; it does not fetch evidence, enforce an oracle, issue assets, or settle money. Product and architect describe this contract; only the domain role emits the JSON file.

Forecasts are probabilities between 0 and 1, often entered as 0–100 percent. A mean forecast summarizes local observations and is not an executable trade price, liquidity measure, or guarantee. YES/NO can be scored after resolution; VOID must be excluded rather than scored as zero, one, or a perfect forecast.

## Handoff
Supply the immutable text, case analysis, unresolved choices, and a short human verification procedure. Distinguish current manual behavior from any proposed future automated adapter. Never claim that current sources or event outcomes were verified without provided evidence.
