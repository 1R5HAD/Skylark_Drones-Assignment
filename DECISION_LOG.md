# Decision Log — Skylark Drones BI Agent

## Key Assumptions

- **Column types stay loose on purpose.** The assignment says column
  types don't need to be perfect on import, so the agent treats every
  monday.com column as text and does its own cleaning (dates, amounts)
  in `normalize.py` rather than trusting native Date/Number column
  types. This makes the agent tolerant of however the CSVs actually
  got imported.
- **"Energy sector" has no exact match in the sample data.** The
  closest sector label is "Renewables." Rather than hardcoding that
  mapping, the agent discovers real sector values at query time via
  `get_data_summary` and either states the mapping it used or asks
  for clarification — so it doesn't silently guess on a founder's
  actual wording.
- **"Pipeline" is ambiguous** (open deals only vs. all deals; this
  quarter vs. all time). The system prompt instructs the agent to
  state a reasonable default and proceed, or ask one clarifying
  question, rather than guessing silently — per the assignment's
  explicit "document assumptions and proceed" guidance.
- **Blank/missing values are never treated as zero.** A blank
  "Amount Collected" means unknown, not $0. Coercion failures become
  `NaN`, and columns with >40% missingness are surfaced to the model
  as caveats it's expected to mention when relevant.
- **Read-only is a hard boundary**, not just an API scope choice —
  it's also enforced in the system prompt ("never suggest writing
  back to monday.com") so the agent doesn't casually offer to update
  a board it can only read.

## Trade-offs Chosen and Why

- **General-purpose `run_analysis` (pandas-via-exec) instead of a
  fixed set of query functions.** Founder questions are open-ended
  ("pipeline for energy this quarter," "which deals are stuck," "work
  order completion rate") and cross-board. Hand-coding a query per
  question doesn't scale and always misses the next question. Giving
  the model `pandas` access to cleaned DataFrames trades sandbox
  safety for coverage — acceptable for a single-tenant, founder-facing
  internal tool over read-only data, explicitly **not** acceptable
  as-is for a multi-tenant or untrusted-input product (see below).
- **Two tools only** (`get_data_summary`, `run_analysis`), not one
  per board or one per metric. Fewer tools means less prompt surface
  to get wrong and forces the model to always check real columns and
  null rates before computing anything, instead of assuming a schema.
- **Gemini 3.5 Flash-Lite over Groq (Llama 3.3 70B).** The project
  started on Groq; development hit Groq's daily token cap during
  testing because the tool-use loop replays full conversation history
  every turn. Switched to Gemini's free tier for more daily headroom
  at zero cost — a testability/deliverable-reliability trade-off, not
  a claim that Gemini reasons better. The client setup is isolated to
  six constants in `agent.py`, so swapping providers later (Anthropic,
  OpenAI) doesn't touch the tool-use loop, which is standard
  OpenAI-style function calling.
- **In-memory caching per session, not a persistent store.** Boards
  are fetched once per Streamlit session and cached; a sidebar
  "Refresh data" button clears it. This avoids hitting monday.com's
  API on every message, at the cost of possibly-stale data mid-session
  until refreshed — reasonable for a demo/prototype, not for a
  production tool with concurrent editors.
- **Stray "header echo" rows are dropped, not flagged for review.**
  Rows where ≥3 cells duplicate their own column header (a common
  artifact of pasting data into monday.com) are auto-dropped, since
  they're never real records — but the count dropped is surfaced as a
  caveat so it's auditable rather than silently vanishing.

## How "Leadership Updates" Was Interpreted

The assignment leaves this open. Rather than bolting on a separate
"generate report" button, the agent's existing conversational ability
was extended to cover it: system-prompt rule 5 ("answer in plain
business language with the supporting number, not just raw tables —
insight over data dump") means a founder can ask "give me a leadership
update on pipeline health and stalled work orders" as an ordinary
conversational turn, and the agent produces a narrative summary with
supporting figures and caveats rather than a raw table dump. This
keeps the interaction model consistent (one conversational surface)
instead of a second, disconnected export feature — the trade-off is
there's no one-click PDF/slide export, since the assignment's
6-hour timeline made a second UI surface a lower priority than
strengthening data resilience and query handling.

## What I'd Do Differently With More Time

- **Sandbox `run_analysis`.** Executing model-generated code via
  `exec()` is fine for a single-tenant internal tool but is the first
  thing to change for anything production-facing — e.g. a restricted
  execution environment (subprocess with resource limits, or a
  proper sandboxed interpreter), an allow-list of pandas operations,
  or moving to pre-approved parameterized query templates for common
  question shapes while keeping `run_analysis` as a fallback for
  novel questions.
- **Persist the board cache** (e.g. Redis or a lightweight DB) so
  data survives across sessions/restarts and multiple users don't
  each trigger a full re-fetch, with a shorter TTL-based refresh
  instead of a manual button.
- **Confirm the malformed-tool-call retry path against Gemini
  directly.** The `BadRequestError` handling in `agent.py` still
  checks for Groq's `tool_use_failed` error string as a leftover from
  the provider switch; this needs to be verified (or replaced) against
  Gemini's actual error format rather than assumed.
- **Add lightweight automated tests** for `normalize.py` (header-echo
  detection, amount/date coercion on edge cases) instead of relying on
  manual testing against the sample CSVs — normalization correctness
  is the part of this system most likely to silently misbehave on
  data shapes not seen during the 6-hour build.
- **A structured leadership-update export** (e.g. a formatted
  markdown/PDF snapshot of the current conversation's key numbers)
  once the conversational interpretation above was validated as
  useful, rather than relying solely on chat scrollback.
