"""
The BI agent itself: an LLM tool-use loop over two data sources
(Work Orders, Deals) pulled live from monday.com.

Uses Groq's free API (OpenAI-compatible) running Llama 3.3 70B, so this
runs at zero cost. Swap GROQ_API_KEY / MODEL / base_url below if you'd
rather point this at Anthropic, OpenAI, or Gemini's OpenAI-compat
endpoint later -- the tool-use loop itself is standard OpenAI-style
function calling and doesn't need to change.

Design (kept deliberately simple):
- Two tools only.
  1. get_data_summary(board) -> schema, row count, null %, sample rows,
     and data-quality caveats. Lets the model see what it's working
     with before analyzing, and is what it uses to flag caveats to
     the user unprompted.
  2. run_analysis(code) -> executes short pandas snippets against the
     cached, cleaned DataFrame(s) and returns the printed result. This
     is what lets the agent answer arbitrary founder questions
     (revenue, sector cuts, cross-board joins) without us hand-coding
     a query for every possible question.
- Boards are fetched from monday.com once per process and cached in
  memory (`_board_cache`); refresh_data() clears it.
"""

from __future__ import annotations
import io
import json
import contextlib
import os
import pandas as pd
from openai import OpenAI, BadRequestError

from monday_client import MondayClient
from normalize import normalize_board

# Groq's free, OpenAI-compatible endpoint. Get a key at console.groq.com
# (no credit card needed).
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

BOARD_IDS = {
    "work_orders": os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID"),
    "deals": os.environ.get("MONDAY_DEALS_BOARD_ID"),
}

SYSTEM_PROMPT = """You are a business intelligence analyst for Skylark Drones, a drone-services \
company. Founders and executives ask you questions about two live monday.com boards:

- "work_orders": project execution data (status, sector, dates, billing/collection amounts).
- "deals": sales pipeline data (deal stage, status, sector, deal value, probability).

Ground rules:
1. Always call get_data_summary for a board before analyzing it if you haven't already \
   this conversation, so you know its real columns and data-quality issues -- do not assume \
   column names.
2. Use run_analysis (pandas) to compute real numbers. Never invent or estimate figures.
3. The data is genuinely messy (missing dates, blank amounts, inconsistent sector labels). \
   When a caveat from get_data_summary is relevant to your answer, say so briefly instead of \
   silently ignoring it.
4. If a founder's question is ambiguous (e.g. "this quarter" with no year, "pipeline" meaning \
   open deals vs. all deals), ask one clarifying question rather than guessing silently -- \
   unless a reasonable default is obvious, in which case state the assumption and proceed.
5. Answer in plain business language with the supporting number, not just raw tables. Insight \
   over data dump.
6. You are read-only. You never suggest writing back to monday.com.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_data_summary",
            "description": (
                "Fetch (or use cached) data for a board and return its schema, row count, "
                "missing-data percentages per column, a few sample rows, and any data-quality "
                "caveats detected during cleaning."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "board": {"type": "string", "enum": ["work_orders", "deals"]},
                },
                "required": ["board"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": (
                "Run a short pandas snippet against the cleaned board DataFrame(s). "
                "Available variables: `work_orders` and `deals` (pandas DataFrames, only "
                "populated for boards you've already loaded via get_data_summary). "
                "Assign your final answer to a variable named `result` (a DataFrame, Series, "
                "scalar, or string) -- it will be captured and returned to you."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python/pandas code. Must set `result`."},
                },
                "required": ["code"],
            },
        },
    },
]


class BIAgent:
    def __init__(self, groq_api_key: str | None = None):
        api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to your environment or .env file.")
        self.client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)
        self.monday = MondayClient()
        self._board_cache: dict[str, pd.DataFrame] = {}
        self._caveats: dict[str, list[str]] = {}

    def refresh_data(self):
        self._board_cache.clear()
        self._caveats.clear()

    def _load_board(self, board: str) -> tuple[pd.DataFrame, list[str]]:
        if board in self._board_cache:
            return self._board_cache[board], self._caveats[board]
        board_id = BOARD_IDS.get(board)
        if not board_id:
            raise RuntimeError(
                f"No board id configured for '{board}'. Set MONDAY_{board.upper()}_BOARD_ID."
            )
        payload = self.monday.get_board_items(board_id)
        df, caveats = normalize_board(payload)
        self._board_cache[board] = df
        self._caveats[board] = caveats
        return df, caveats

    # ---- tool implementations ----

    def _tool_get_data_summary(self, board: str) -> str:
        df, caveats = self._load_board(board)
        null_pct = (df.isna().mean() * 100).round(1)
        lines = [
            f"Board: {board}  |  rows: {len(df)}  |  columns: {len(df.columns)}",
            "",
            "Columns (dtype, % missing):",
        ]
        for col in df.columns:
            lines.append(f"  - {col}: {df[col].dtype}, {null_pct[col]}% missing")
        lines.append("")
        lines.append("Sample rows:")
        lines.append(df.head(3).to_string())
        if caveats:
            lines.append("")
            lines.append("Data-quality caveats:")
            for c in caveats:
                lines.append(f"  - {c}")
        return "\n".join(lines)

    def _tool_run_analysis(self, code: str) -> str:
        local_env = {"pd": pd}
        # populate any boards already loaded so cross-board joins work
        for board, df in self._board_cache.items():
            local_env[board] = df

        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, {"__builtins__": __builtins__, "pd": pd}, local_env)
        except Exception as e:
            return f"Error running analysis: {type(e).__name__}: {e}"

        result = local_env.get("result", None)
        printed = stdout.getvalue()
        parts = []
        if printed.strip():
            parts.append(printed.strip())
        if result is not None:
            parts.append(str(result))
        if not parts:
            return "Code ran but did not set `result` or print anything."
        return "\n".join(parts)

    def _run_tool(self, name: str, tool_input: dict) -> str:
        if name == "get_data_summary":
            return self._tool_get_data_summary(tool_input["board"])
        if name == "run_analysis":
            return self._tool_run_analysis(tool_input["code"])
        return f"Unknown tool: {name}"

    # ---- main entry point ----

    def ask(self, conversation: list[dict]) -> tuple[str, list[dict]]:
        """
        conversation: list of {"role": "user"|"assistant", "content": ...} in OpenAI format
        (no system message included -- it's added here each call).
        Returns (final_text_reply, updated_conversation_without_system_message).
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(conversation)
        malformed_retry_used = False

        while True:
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=2000,
                )
            except BadRequestError as e:
                if "tool_use_failed" in str(e) and not malformed_retry_used:
                    # Model emitted a malformed function call. Nudge it once and retry
                    # rather than surfacing a raw API error to the user.
                    malformed_retry_used = True
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Your last response wasn't a valid tool call. Please retry, "
                                "calling exactly one tool with correctly formatted JSON arguments."
                            ),
                        }
                    )
                    continue
                raise
            msg = response.choices[0].message
            messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                return msg.content or "", messages[1:]  # drop system message before returning

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                output = self._run_tool(tc.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": output}
                )
