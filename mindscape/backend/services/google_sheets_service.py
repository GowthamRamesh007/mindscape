import csv
import io
import time
import urllib.request
from typing import List, Dict, Optional

GOOGLE_SHEET_ID = "11Kw2JYF4mztp71KQw_Y3A6FZ_bTtxE-2LWxxVYVhSUE"
CACHE_TTL_SECONDS = 30  # 30-second TTL cache for real-time responsiveness & rate safety

_teams_cache = {
    "timestamp": 0,
    "data": []
}

def fetch_registered_teams_from_sheet(force_refresh: bool = False) -> List[Dict[str, str]]:
    """
    Fetches registered teams from the official Google Form responses Google Sheet.
    Includes team name, representative name, phone, email, college/institution,
    city, title, and language. Cached for 30s.
    """
    global _teams_cache
    now = time.time()
    if not force_refresh and _teams_cache["data"] and (now - _teams_cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _teams_cache["data"]

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MindscapeBackend/1.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(content)))
        if not rows:
            return _teams_cache["data"]

        headers = [h.strip() for h in rows[0]]

        # Find team name column (handles the exact column header or any variation containing Team Name)
        team_idx = None
        for i, h in enumerate(headers):
            if "team name" in h.lower():
                team_idx = i
                break

        def find_idx(keywords):
            for i, h in enumerate(headers):
                for k in keywords:
                    if k.lower() in h.lower():
                        return i
            return None

        name_idx = find_idx(["Full Name", "Representative Name"])
        phone_idx = find_idx(["Mobile", "Phone"])
        email_idx = find_idx(["Email"])
        inst_idx = find_idx(["College", "Institution", "School", "Organization"])
        city_idx = find_idx(["City", "Location"])
        title_idx = find_idx(["Title of the Reel", "Reel Title"])
        lang_idx = find_idx(["Language of Your Reel", "Language"])

        parsed = []
        seen = set()
        for row in rows[1:]:
            if team_idx is not None and team_idx < len(row):
                t_name = row[team_idx].strip()
                if t_name and t_name.lower() not in seen:
                    seen.add(t_name.lower())
                    parsed.append({
                        "team_name": t_name,
                        "representative_name": row[name_idx].strip() if name_idx and name_idx < len(row) else "",
                        "phone": row[phone_idx].strip() if phone_idx and phone_idx < len(row) else "",
                        "email": row[email_idx].strip() if email_idx and email_idx < len(row) else "",
                        "institution": row[inst_idx].strip() if inst_idx and inst_idx < len(row) else "",
                        "city": row[city_idx].strip() if city_idx and city_idx < len(row) else "",
                        "title": row[title_idx].strip() if title_idx and title_idx < len(row) else "",
                        "language": row[lang_idx].strip() if lang_idx and lang_idx < len(row) else "Tamil"
                    })

        _teams_cache["timestamp"] = now
        _teams_cache["data"] = parsed
        return parsed
    except Exception as e:
        print(f"Warning: Failed to fetch Google Sheet: {e}")
        return _teams_cache["data"]

def is_team_registered(team_name: str) -> bool:
    """Checks if the given team name exists in the registered teams list (case-insensitive)."""
    if not team_name:
        return False
    teams = fetch_registered_teams_from_sheet()
    if not teams:
        # If sheet fetch failed, don't hard-block valid users
        return True
    target = team_name.strip().lower()
    return any(t["team_name"].strip().lower() == target for t in teams)

def get_team_registration(team_name: str) -> Optional[Dict[str, str]]:
    """Returns registration details for a team name, if found."""
    if not team_name:
        return None
    teams = fetch_registered_teams_from_sheet()
    target = team_name.strip().lower()
    for t in teams:
        if t["team_name"].strip().lower() == target:
            return t
    return None
