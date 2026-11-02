import csv
import io
import time
import urllib.request
from typing import List, Dict, Optional, Any

GOOGLE_SHEET_ID = "11Kw2JYF4mztp71KQw_Y3A6FZ_bTtxE-2LWxxVYVhSUE"
CACHE_TTL_SECONDS = 30  # 30-second cache TTL for responsive validation without hammering Google servers
MAX_CACHE_GRACE_SECONDS = 300  # 5-minute fallback cache grace window if Google is temporarily unreachable

class RegistrationVerificationError(Exception):
    """Raised when Google Form registration responses cannot be fetched or verified."""
    pass

_teams_cache: Dict[str, Any] = {
    "timestamp": 0,
    "data": [],
    "last_error": None
}

def normalize_team_name(name: Optional[str]) -> str:
    """
    Normalizes a team name for safe comparison:
    - Trims leading and trailing whitespace
    - Collapses multiple contiguous spaces into a single space
    - Converts to lowercase
    """
    if not name:
        return ""
    return " ".join(str(name).strip().lower().split())

def fetch_registered_teams_from_sheet(force_refresh: bool = False) -> List[Dict[str, str]]:
    """
    Fetches the authoritative list of registered teams exclusively from the official
    Google Form responses spreadsheet.
    
    If the fetch fails and no valid cache exists, it fails closed by raising
    RegistrationVerificationError rather than returning an empty or fabricated list.
    """
    global _teams_cache
    now = time.time()
    
    # Check fresh cache
    if not force_refresh and _teams_cache["data"] and (now - _teams_cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _teams_cache["data"]

    url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MindscapeRegistrationValidator/2.0",
                "Accept": "text/csv,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")

        rows = list(csv.reader(io.StringIO(content)))
        if not rows:
            raise RegistrationVerificationError("Google Form responses spreadsheet returned empty content.")

        headers = [h.strip() for h in rows[0]]

        # Find team name column (specifically matching 'team name')
        team_idx = None
        for i, h in enumerate(headers):
            if "team name" in h.lower():
                team_idx = i
                break
        if team_idx is None and len(headers) > 7:
            team_idx = 7

        def find_idx(keywords: List[str]) -> Optional[int]:
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
                raw_team_name = row[team_idx].strip()
                norm = normalize_team_name(raw_team_name)
                if norm and norm not in seen:
                    seen.add(norm)
                    parsed.append({
                        "team_name": raw_team_name,
                        "normalized_name": norm,
                        "representative_name": row[name_idx].strip() if name_idx and name_idx < len(row) else "",
                        "phone": row[phone_idx].strip() if phone_idx and phone_idx < len(row) else "",
                        "email": row[email_idx].strip().lower() if email_idx and email_idx < len(row) else "",
                        "institution": row[inst_idx].strip() if inst_idx and inst_idx < len(row) else "",
                        "city": row[city_idx].strip() if city_idx and city_idx < len(row) else "Chennai",
                        "title": row[title_idx].strip() if title_idx and title_idx < len(row) else "Mindscape Reel",
                        "language": row[lang_idx].strip() if lang_idx and lang_idx < len(row) else "Tamil"
                    })

        _teams_cache["timestamp"] = now
        _teams_cache["data"] = parsed
        _teams_cache["last_error"] = None
        return parsed

    except Exception as e:
        _teams_cache["last_error"] = str(e)
        # If we have recent data within grace period and not explicitly forcing refresh, fallback to it
        if _teams_cache["data"] and not force_refresh and (now - _teams_cache["timestamp"]) < MAX_CACHE_GRACE_SECONDS:
            return _teams_cache["data"]
        # Fail closed: never treat failed fetch as valid empty list
        raise RegistrationVerificationError(f"Failed to fetch authoritative Google Form registration sheet: {e}")

def verify_team_registration(team_name: Optional[str]) -> Dict[str, Any]:
    """
    Strict server-side verification of team name against authoritative Google Form responses.
    Returns:
    {
        "is_registered": bool,
        "team": Optional[Dict[str, str]],
        "normalized_name": str,
        "error": Optional[str],
        "service_unavailable": bool
    }
    """
    norm = normalize_team_name(team_name)
    if not norm:
        return {
            "is_registered": False,
            "team": None,
            "normalized_name": "",
            "error": "This team is not registered for Mindscape. Please complete the official registration form first.",
            "service_unavailable": False
        }

    try:
        registered_teams = fetch_registered_teams_from_sheet()
    except RegistrationVerificationError as e:
        return {
            "is_registered": False,
            "team": None,
            "normalized_name": norm,
            "error": f"Registration verification service is currently unavailable. Submissions are temporarily blocked: {e}",
            "service_unavailable": True
        }
    except Exception as e:
        return {
            "is_registered": False,
            "team": None,
            "normalized_name": norm,
            "error": f"Registration verification failed: {e}",
            "service_unavailable": True
        }

    for t in registered_teams:
        if normalize_team_name(t.get("team_name", "")) == norm:
            return {
                "is_registered": True,
                "team": t,
                "normalized_name": norm,
                "error": None,
                "service_unavailable": False
            }

    return {
        "is_registered": False,
        "team": None,
        "normalized_name": norm,
        "error": "This team is not registered for Mindscape. Please complete the official registration form first.",
        "service_unavailable": False
    }

def is_team_registered(team_name: Optional[str]) -> bool:
    """Checks if team_name is verified against official Google Form registrations."""
    return verify_team_registration(team_name)["is_registered"]

def get_team_registration(team_name: Optional[str]) -> Optional[Dict[str, str]]:
    """Returns registration details for a verified team, or None."""
    return verify_team_registration(team_name)["team"]
