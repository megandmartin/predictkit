---
name: build-prediction-ui
description: Implement a self-contained, accessible forecast-to-outcome HTML flow with correct scoring, guarded state, and honest local-data behavior.
---
# Build the useful forecast loop

Use for the app engineer. Inputs are the frozen brief, accepted discovery, approved build memo, and reference HTML. The concurrent domain output is unavailable. Deliver one complete `app/index.html`; no external code, fonts, assets, network calls, or Studio API access. Keep the reference's restrictive no-network policy.

## Make the decision clear
Lead with the exact market question, probability of YES, primary recording action, and question status. Keep the resolution rule and VOID policy readable before a forecast is recorded. Display off-chain simulation, manual human attestation, and no connected wallet/oracle/exchange where they affect interpretation. Use the brief's user and selected template to set useful labels and the first view.

Make the primary flow reachable without reading a manual: understand → forecast → history → close → attest → score. A 65% forecast is confidence in YES, not a bid, position, wallet balance, executable price, or predicted return. Avoid fake trading activity to decorate the page.

## Implement domain behavior, not just controls
Use an explicit state model. OPEN accepts records; CLOSED rejects them; resolving YES or NO reaches RESOLVED; VOID reaches VOID. Check state inside event handlers as well as with disabled buttons. Final resolution cannot be overwritten without an explicit new-demo/reset action. Confirm a reset that discards recorded data.

Validate values as finite numbers in the inclusive range 0–100 before dividing by 100. Do not accept an empty string as zero or silently coerce invalid values. Store accepted values as immutable observations. A changed input must not rewrite earlier forecasts. Repeated records are allowed only as clearly labeled local observations, never distinct users.

Show an empty history and no mean or score when there are no observations. Close with no forecasts may still demonstrate resolution, but must not divide by zero or invent a score. Forecast controls remain closed after any final outcome.

For YES/NO, Brier score is the mean of `(p - y)^2`, where `p` is a probability in 0–1 and `y` is 1 for YES, 0 for NO. Example: a 70% YES forecast scores 0.09 for YES and 0.49 for NO. Lower is better. VOID produces no score and is excluded from denominators; it is not 0.0000. One question does not estimate long-run forecasting skill.

## Keep local data dependable
When persisting, use a versioned key scoped to the exact question contract, validate the shape/state/ranges of restored data, and wrap storage reads/writes in try/catch. The sandbox can deny localStorage. Fall back to in-memory operation with a visible session-only notice; never show “saved” unless the write succeeded. Do not silently merge state across different question, rule, or VOID text. Provide recovery/reset when stored data is malformed.

If the approved scope deliberately keeps session-only state, make reload loss clear near the recording action and footer. Do not add an account or backend to conceal the persistence limit.

## Make the interface usable
Use semantic headings and native labeled buttons/inputs; connect labels and error messages. Support keyboard completion, visible focus, readable contrast, and status announcements with a polite live region. Use text alongside YES/NO colors. Stack the core panels on narrow screens, allow long questions/rules to wrap, and keep actions large enough to tap. Respect reduced-motion preferences if motion is added.

Use system fonts or already embedded assets. Escape supplied text for its output context; prefer DOM textContent over innerHTML. Do not place raw brief text into a script string, event attribute, or CSS. Keep data and executable logic separate.

## Completion and operator handoff
Inspect your source for the full loop, endpoints 0/100, invalid input, empty data, repeated action, closed and final states, correct YES/NO score, VOID exclusion, reload, unavailable/corrupt storage, and keyboard labels. Return the complete HTML and list remaining operator checks. You cannot run a browser here; “implemented” and “source inspected” are the strongest claims available without supplied execution evidence. Browser evidence is a later operator check, not an artifact you can fabricate.
