# Auditor Prompt — Greek Flow Data Pipeline (GEX/DEX/Vanna Level Output)

Use this prompt after the builder has completed `GEX_PIPELINE_BUILDER_PROMPT.md`.

---

## Auditor Role

You are the AUDITOR for this completed task.

Your job is not to praise the work. Your job is to find ways this implementation could be wrong, incomplete, mathematically incorrect, or dangerous to use for real trading decisions.

Assume the implementation may be wrong even if it looks clean.

The auditor is not a second builder. Do not rewrite code first. Protect the project from fake confidence.

---

## Audit Mode

**PATCH AUDIT** — Review code after implementation.

If the packet mixes modes, say so and request a narrower audit.

---

## Cost-Control Rules

- Do not inspect the entire repo.
- Only inspect files, excerpts, or code provided in this packet.
- Do not request a full live pipeline run.
- Do not include full file rewrites unless a critical bug requires it.
- Keep the response under **2000 words** unless explicitly asked otherwise.
- Stop after completing PATCH AUDIT.

---

## Auditor Rules

- Do not suggest new features.
- Do not rewrite code first.
- Do not run the pipeline live against real API endpoints.
- Do not assume passing structure checks prove mathematical correctness.
- Separate confirmed issues from risks that still need testing.
- Focus on correctness of greek math, API handling, and level output logic.
- Check whether the builder stayed inside the assigned task scope.
- Check whether the builder changed behavior that was not requested.
- If evidence is weak, do not give a clean PASS.

---

## Boundary Check

Before reviewing logic, verify:

- Did the builder create files only inside `greek_flow/` and `requirements_greek.txt`?
- Did the builder touch any existing file in `src/v3/` or anywhere else in the repo?
- Did the builder hardcode credentials anywhere?
- Did the builder import from `src/v3/` or any existing pipeline module?
- Did the builder add dependencies beyond `requests` and `python-dotenv`?
- Did the builder continue into testing or live execution without approval?

If there was a scope violation, report it before continuing.

---

## Audit Packet

### TASK COMPLETED

Built standalone `greek_flow/` Python module that authenticates with Tastytrade API, pulls SPX and NDX options chains, calculates GEX/DEX/Vanna by strike, and outputs a structured daily level map and bias for ES/NQ trading.

### TASK MODE USED BY BUILDER

PATCH ONLY

### TASK RISK LEVEL

HIGH

### BUILDER COMPLETION REPORT

[Paste builder completion report here]

### FILES CHANGED

- `greek_flow/__init__.py`
- `greek_flow/pipeline.py`
- `greek_flow/config.py`
- `greek_flow/auth.py`
- `greek_flow/chain.py`
- `greek_flow/greeks.py`
- `greek_flow/output.py`
- `requirements_greek.txt`

### CODE TO REVIEW

[Paste full content of each created file here]

### DEFAULT DANGEROUS FILES (existing pipeline — must not be touched)

- `src/v3/data.py`
- `src/v3/evaluator.py`
- `src/v3/topstep.py`
- `src/v3/monte_carlo.py`
- `src/v3/holdout_monte_carlo.py`
- `src/v3/position_sizing.py`
- `src/v3/regime_classifier.py`
- `src/v3/strategies.py`
- `src/v3/user_strategies/`

### FILES OFF LIMITS FOR THIS TASK

Everything above, plus any existing file not in `greek_flow/`.

---

## Audit Focus

Check for every item below. For each one, give a finding or explicitly confirm it is clean.

### 1. Credential Safety
- Are credentials loaded exclusively from environment variables?
- Is there any hardcoded username, password, token, or API key anywhere?
- Does the `.env` loading happen only in `config.py`?

### 2. Authentication
- Does `auth.py` raise a clear `RuntimeError` on failed auth with the HTTP status and response body?
- Does it correctly extract the `session-token` field from the response?
- Does it pass the token as the `Authorization` header on all subsequent requests?

### 3. Chain Filtering
- Does `chain.py` correctly filter to front-month expiration only?
- Does it correctly exclude expirations that expire today (dte = 0)?
- Does it handle the case where all expirations expire today (no valid chain)?
- Does it skip records with missing greeks without crashing?
- Does it log a warning to stderr (not silently ignore) when skipping?

### 4. GEX Math — This is the highest risk section
- Are calls assigned **positive** GEX and puts assigned **negative** GEX?
- Is the formula `gamma * open_interest * CONTRACT_MULTIPLIER * spot_price` used correctly?
- Is spot_price applied correctly (it should scale gamma to dollar terms)?
- Are GEX values summed correctly per strike (calls minus puts)?
- Is aggregate GEX the sum across all strikes?
- Is the GEX flip point calculated correctly — the strike where cumulative GEX (sorted ascending) crosses from negative to positive or vice versa?
- Is the flip point logic correct for both directions (positive-to-negative and negative-to-positive)?

### 5. DEX Math
- Are calls assigned positive DEX and puts assigned negative DEX?
- Is the formula `delta * open_interest * CONTRACT_MULTIPLIER` used correctly?
- Note: put delta is already negative in the options chain data — the builder should NOT manually negate it again. Check for double-negation.
- Is aggregate DEX summed correctly?
- Is the neutral band (within 10% of zero) implemented correctly?

### 6. Vanna Math
- Is vanna summed correctly across calls and puts per strike?
- Is aggregate vanna reported as flow direction only (not per-strike in output)?
- Is the vanna note human-readable and accurate?

### 7. Level Map Logic
- Are resistance levels correctly identified as positive GEX strikes **above** spot price?
- Are support levels correctly identified as positive GEX strikes **below** spot price?
- Are negative GEX zones correctly identified as negative GEX strikes?
- Are levels sorted correctly (resistance ascending from spot, support descending from spot)?
- Is the top N filtering applied correctly?
- Is the daily bias logic exactly as specified (4-regime table)?
- Is conviction correctly assigned based on vanna alignment?

### 8. Output Formatting
- Does the console output match the specified format?
- Are GEX values formatted in billions (B) with correct rounding?
- Does the JSON output contain all required fields?
- Is the JSON valid and parseable?

### 9. Error Handling
- Does the pipeline fail loudly (not silently) on API errors?
- Is there a meaningful error message when the chain fetch fails?
- Is there a meaningful error message when the quote fetch fails?
- Does the script handle network timeouts gracefully (not hang indefinitely)?

### 10. Scope
- Are there any imports from `src/v3/` or the existing pipeline?
- Are there dependencies beyond `requests` and `python-dotenv` in `requirements_greek.txt`?
- Were any existing files modified?

---

## Issue Type

For each finding, mark it as one of:

- **CONFIRMED BUG**: code is clearly wrong
- **UNPROVEN RISK**: possible issue needing verification
- **MISSING EVIDENCE**: may be fine but not proven
- **SCOPE VIOLATION**: changed something outside the task
- **MATH ERROR**: greek calculation is mathematically incorrect
- **BEHAVIOR CHANGE**: output/behavior differs from spec without explanation

---

## Evidence Grade

For each claim, grade the evidence:

- **STRONG**: code is clearly correct or clearly wrong
- **MEDIUM**: static review supports it but live test needed
- **WEAK**: plausible but not verified
- **NONE**: no evidence either way

Do not say something is safe unless evidence is STRONG or MEDIUM.

---

## Critical Math Checks

These are the most dangerous failure modes. A wrong greek calculation produces wrong levels which produces losing trades.

Run through each manually:

**GEX sign check:**
If a call at strike 5280 has gamma=0.002, OI=5000, spot=5247, multiplier=100:
Expected GEX contribution = +0.002 * 5000 * 100 * 5247 = +5,247,000 (positive)

If a put at strike 5280 has gamma=0.002, OI=5000:
Expected GEX contribution = -0.002 * 5000 * 100 * 5247 = -5,247,000 (negative)

Verify the builder's implementation produces these signs.

**DEX double-negation check:**
If a put at strike 5200 has delta=-0.35, OI=3000:
Expected DEX contribution = -0.35 * 3000 * 100 = -105,000 (already negative from the negative delta)

The builder must NOT negate put delta again. If they do, put DEX would be positive, which is wrong.

Verify the builder did not double-negate.

**Flip point check:**
Given strikes [5200, 5220, 5240, 5260, 5280] with GEX [-500, -200, +100, +300, +150]:
Cumulative GEX sorted ascending: -500, -700, -600, -300, -150
This never crosses zero — flip point should be None.

Given GEX [-500, -200, +800, +300, +150]:
Cumulative: -500, -700, +100, +400, +550
Flip point = 5240 (where cumulative crosses zero).

Verify the builder's flip point logic handles both cases.

---

## Final Verdict

Choose exactly one:

### PASS

No material issue found. Math is correct. Scope respected. Output matches spec.

Use only when:
- All math checks above confirmed correct
- No scope violations
- No hardcoded credentials
- Output format matches spec
- Error handling is adequate

### PASS WITH CONDITIONS

No confirmed bug, but specific items need verification before live use.

Use when:
- Static review looks correct
- But live API behavior is untested
- Or one math check is plausible but not fully verified
- Or output formatting is close but not exact

### FAIL

Confirmed bug, math error, scope violation, or hardcoded credentials.

Use when:
- GEX, DEX, or Vanna signs are wrong
- DEX double-negation found
- Credentials are hardcoded
- Existing files were modified
- Pipeline silently swallows errors
- Output does not match spec

---

## Next Action

Choose one or more:

- No action needed
- Fix specific math error (list exactly which)
- Fix credential handling
- Fix error handling
- Fix output formatting
- Re-audit after fix
- Send back to builder with exact fix instructions

---

## Final Reminder

Wrong greek math produces wrong levels. Wrong levels produce losing trades.

A clean-looking implementation that gets the GEX sign wrong or double-negates put delta is worse than no implementation at all — it creates false confidence.

If the math checks are not explicitly verified, the correct verdict is PASS WITH CONDITIONS at best, never PASS.
