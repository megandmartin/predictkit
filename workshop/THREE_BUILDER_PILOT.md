# Three-builder pilot — independent local rehearsal

Prepared 28 September 2026. This protocol measures whether three new builders can use the packaged local product without coaching. It is not a live-AI or Solana workshop certification. No participants have been recruited or observed yet.

## Host preparation

Use one SHA-256-identified starter ZIP for all three participants. Verify fresh extraction, `python3 predictkit.py doctor`, the scripted rehearsal and export verification first. Supply only this packet and `START_HERE.md`. Participants need Python 3.11+ and a browser; rehearsal needs no key, account or wallet. Use separate folders. Give each participant 45 minutes. Record only participant IDs B01–B03; ask before recording, quoting or publishing.

## Participant task card

You are prototyping a prediction app for a real user you understand. Start the downloaded project using the start guide. Create a brief containing your user, problem, current alternative, difference, one yes/no question, a resolution source/deadline and a VOID rule. Run the rehearsal and inspect the decision memo before approving it.

Find the role responsible for market rules and identify its primary skill. Preview your generated app, record a 70% forecast, close the question, resolve YES and find its Brier score. Start a fresh demo and resolve VOID. Explain how the two outcomes affect scoring. Export the draft ZIP and use the provided verification command. Identify which model, chain and user-success claims remain unproven. Stop when you believe you are done, or when you cannot proceed.

After exporting, run this from the source folder, replacing the example path with the actual downloaded ZIP path (drag the ZIP into Terminal to insert its path if needed):

```sh
python3 predictkit.py verify-pack /absolute/path/to/predictkit-run-pack.zip
```

## Completion rubric, declared before observation

| Requirement | Observable pass |
|---|---|
| Start | Homepage and Studio open from the downloaded folder |
| Personalize | Participant's own question/rules appear in the app and JSON |
| Approve | Participant can name what the exact memo authorizes |
| Inspect roles | Finds Market designer, `specify-market`, and an actual output |
| Use app | 70% YES produces 0.0900; VOID is excluded; reset works |
| Export | Eleven artifacts exported and whole-pack integrity passes |
| Understand limits | Correctly identifies scripted rehearsal and missing chain/live proof |

Independent completion requires all seven within 45 minutes with zero host task instructions. A request for help is logged; any task-specific hint makes it an assisted attempt, even if completed. Accessibility or equipment setup support is recorded separately, never concealed. A blocked, abandoned or timed-out attempt remains in the denominator.

## Observation sheet

Use one row per participant in `PILOT_RESULTS.csv`. Log the first blocking step and exact interface wording, elapsed time, task-specific hints, completion checks and the participant's explanation of limits. Leave all result cells blank until observed. Record each of the seven checks and `independent_complete` as `1` for pass or `0` for fail, `task_hints` as a nonnegative integer, and elapsed time in minutes. After each attempt, ask: What did you think the agents did? Where did you hesitate? What output would make this worth using again? Do not suggest desired answers.

## Review checkpoint

Report independent completions as x/3 and assisted completions separately. Publish no speed/quality comparisons without a baseline. Fix repeated blockers before repeating with new participants. A provisional local onboarding pass requires 3/3 independent completions, no misunderstood live/chain claims and no critical defect. Three successes are small-sample usability evidence, not demand or market validation. Live/chain pilot gates remain additional.
