"""
Run this directly to sanity-check your monday.com connection, independent
of Streamlit and the agent. Prints the actual board name and columns it
fetches for each configured board ID.

Usage (from the src/ folder):
    python diagnose.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

from monday_client import MondayClient

token = os.environ.get("MONDAY_API_TOKEN")
wo_id = os.environ.get("MONDAY_WORK_ORDERS_BOARD_ID")
deals_id = os.environ.get("MONDAY_DEALS_BOARD_ID")

print("=== .env values being used ===")
print(f"MONDAY_API_TOKEN: {'set (' + token[:15] + '...)' if token else 'NOT SET'}")
print(f"MONDAY_WORK_ORDERS_BOARD_ID: {wo_id!r}")
print(f"MONDAY_DEALS_BOARD_ID: {deals_id!r}")
print()

client = MondayClient()

for label, board_id in [("Work Orders", wo_id), ("Deals", deals_id)]:
    print(f"=== Fetching board configured as '{label}' (id={board_id}) ===")
    if not board_id:
        print("  -> No board ID set, skipping.\n")
        continue
    try:
        payload = client.get_board_items(board_id)
        print(f"  Actual board name on monday.com: {payload['board_name']!r}")
        print(f"  Item count: {len(payload['items'])}")
        col_titles = [c['title'] for c in payload['columns']]
        print(f"  Column count: {len(col_titles)}")
        print(f"  Columns: {col_titles}")
    except Exception as e:
        print(f"  ERROR: {e}")
    print()
