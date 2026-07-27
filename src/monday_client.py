"""
Thin wrapper around the monday.com GraphQL v2 API.

Read-only: only queries used, no mutations. Handles pagination via
next_items_page and retries on rate-limit / complexity errors with
exponential backoff.
"""

import os
import time
import requests

MONDAY_API_URL = "https://api.monday.com/v2"

FIRST_PAGE_QUERY = """
query ($boardId: [ID!]) {
  boards(ids: $boardId) {
    name
    columns { id title type }
    items_page(limit: 100) {
      cursor
      items {
        id
        name
        column_values { id text value column { title } }
      }
    }
  }
}
"""

NEXT_PAGE_QUERY = """
query ($cursor: String!) {
  next_items_page(limit: 100, cursor: $cursor) {
    cursor
    items {
      id
      name
      column_values { id text value column { title } }
    }
  }
}
"""


class MondayAPIError(RuntimeError):
    pass


class MondayClient:
    def __init__(self, api_token: str | None = None):
        self.token = api_token or os.environ.get("MONDAY_API_TOKEN")
        if not self.token:
            raise MondayAPIError(
                "MONDAY_API_TOKEN is not set. Add it to your environment or .env file."
            )
        self.headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        }

    def _post(self, query: str, variables: dict | None = None, retries: int = 4) -> dict:
        last_err = None
        for attempt in range(retries):
            resp = requests.post(
                MONDAY_API_URL,
                json={"query": query, "variables": variables or {}},
                headers=self.headers,
                timeout=30,
            )
            try:
                data = resp.json()
            except ValueError:
                raise MondayAPIError(f"Non-JSON response from monday.com (status {resp.status_code})")

            if "errors" in data:
                msg = str(data["errors"])
                last_err = msg
                if "ComplexityException" in msg or "rate limit" in msg.lower() or "Minute limit" in msg:
                    time.sleep(2 ** attempt)
                    continue
                raise MondayAPIError(f"monday.com API error: {msg}")
            return data["data"]
        raise MondayAPIError(f"monday.com API: exceeded retries. Last error: {last_err}")

    def get_board_items(self, board_id: str | int) -> dict:
        """Fetch all items and column metadata for a board, following pagination."""
        data = self._post(FIRST_PAGE_QUERY, {"boardId": [str(board_id)]})
        boards = data.get("boards") or []
        if not boards:
            raise MondayAPIError(f"Board {board_id} not found or not accessible with this token.")
        board = boards[0]
        board_name = board["name"]
        columns = board["columns"]
        items = list(board["items_page"]["items"])
        cursor = board["items_page"]["cursor"]

        while cursor:
            page_data = self._post(NEXT_PAGE_QUERY, {"cursor": cursor})
            page = page_data["next_items_page"]
            items.extend(page["items"])
            cursor = page["cursor"]

        return {"board_id": str(board_id), "board_name": board_name, "columns": columns, "items": items}
