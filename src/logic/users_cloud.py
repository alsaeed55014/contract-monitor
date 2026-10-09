"""Durable cloud persistence for app users (fixes Streamlit Cloud sleep-reset bug).

Problem: Streamlit Community Cloud puts free apps to sleep after inactivity.
Waking the app (the "Yes, get this app back up!" button in the screenshot)
reboots it from the Git repo, wiping the ephemeral filesystem. Since
users.json is committed to the repo, every password change / new user made
at runtime is LOST on wake-up (the app "reverts" to the old file).

Fix: mirror the users database to a hidden "AppUsers" worksheet inside the
workers Google Spreadsheet (the service account already has access to it via
DBClient). Local users.json stays as a fast cache; the sheet is the source
of truth across restarts. Avatars (hundreds of KB of base64) are NOT synced
— cells are limited to 50k chars — they remain local-only.

NOTE: background only, no UI. The permissions page shows no banner/backup.
"""

import json
from datetime import datetime

WORKSHEET_TITLE = "AppUsers"
HEADER = ["username", "password", "role", "first_name_ar", "father_name_ar",
          "first_name_en", "father_name_en", "permissions", "updated_at"]


def _get_sheet():
    """Returns the AppUsers worksheet (created on first use). Raises on failure."""
    from src.data.db_client import DBClient, WORKERS_SHEET_URL
    import os
    # Optional override: dedicated spreadsheet for users (secret or env var)
    url = WORKERS_SHEET_URL
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            try:
                url = st.secrets.get("USERS_SHEET_URL", url)
            except Exception:
                pass
    except Exception:
        pass
    url = os.environ.get("USERS_SHEET_URL", url)
    client = DBClient().client
    if client is None:
        raise RuntimeError("Google Sheets client unavailable")
    sh = client.open_by_url(url)
    try:
        ws = sh.worksheet(WORKSHEET_TITLE)
    except Exception:
        ws = sh.add_worksheet(title=WORKSHEET_TITLE, rows=200, cols=len(HEADER))
        ws.update("A1", [HEADER])
    return ws


def pull_users():
    """Reads users from the cloud sheet. Returns dict or None on any failure."""
    try:
        ws = _get_sheet()
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return {}
        header = [str(h).strip() for h in values[0]]
        idx = {h: i for i, h in enumerate(header)}
        users = {}
        for row in values[1:]:
            if not row or not str(row[0]).strip():
                continue
            uname = str(row[0]).strip().lower()

            def col(name):
                i = idx.get(name)
                return str(row[i]).strip() if i is not None and i < len(row) else ""

            try:
                perms = json.loads(col("permissions") or "[]")
                if not isinstance(perms, list):
                    perms = []
            except Exception:
                perms = []
            users[uname] = {
                "password": col("password"),
                "role": col("role") or "viewer",
                "first_name_ar": col("first_name_ar"),
                "father_name_ar": col("father_name_ar"),
                "first_name_en": col("first_name_en"),
                "father_name_en": col("father_name_en"),
                "permissions": perms,
                "username": uname,
            }
        return users
    except Exception as e:
        print(f"[USERS_CLOUD] pull failed: {e}")
        return None


def push_users(users):
    """Writes users to the cloud sheet (core fields only, no avatars)."""
    from datetime import datetime as _dt
    try:
        import pytz
        now_s = _dt.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        now_s = _dt.now().strftime("%Y-%m-%d %H:%M")
    ws = _get_sheet()
    rows = [HEADER]
    for uname, u in (users or {}).items():
        if not isinstance(u, dict):
            continue
        rows.append([
            str(uname).lower().strip(),
            str(u.get("password", "")),
            str(u.get("role", "viewer")),
            str(u.get("first_name_ar", "")),
            str(u.get("father_name_ar", "")),
            str(u.get("first_name_en", "")),
            str(u.get("father_name_en", "")),
            json.dumps(u.get("permissions", []), ensure_ascii=False),
            now_s,
        ])
    ws.clear()
    if rows:
        ws.update("A1", rows)
    return True
