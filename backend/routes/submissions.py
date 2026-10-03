from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from typing import Optional
import json
import uuid
import shutil
import re
from pathlib import Path
from datetime import datetime

try:
    from backend.models.schemas import (
        VideoVerificationRequest,
        VideoVerificationResponse,
        DirectReelUploadRequest
    )
    from backend.services.deadline_service import is_submission_open
    from backend.services.video_service import validate_video_metadata
    from backend.services.supabase_service import get_supabase_admin, get_supabase_anon
except ModuleNotFoundError:
    from models.schemas import (
        VideoVerificationRequest,
        VideoVerificationResponse,
        DirectReelUploadRequest
    )
    from services.deadline_service import is_submission_open
    from services.video_service import validate_video_metadata
    from services.supabase_service import get_supabase_admin, get_supabase_anon

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

ARCHIVE_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ARCHIVE_FILE = ARCHIVE_DIR / "submissions_archive.json"
CLIENT_PUBLIC_MEDIA = Path(__file__).resolve().parent.parent.parent / "client" / "public" / "media" / "submissions"

# Safe initialization for read-only serverless environments
try:
    CLIENT_PUBLIC_MEDIA.mkdir(parents=True, exist_ok=True)
except Exception:
    CLIENT_PUBLIC_MEDIA = Path("/tmp") / "media" / "submissions"
    try:
        CLIENT_PUBLIC_MEDIA.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

try:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    ARCHIVE_DIR = Path("/tmp") / "data"
    ARCHIVE_FILE = ARCHIVE_DIR / "submissions_archive.json"
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

def _load_local_archive():
    if not ARCHIVE_FILE.exists():
        return []
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_local_archive(item: dict):
    try:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        items = _load_local_archive()
        items.insert(0, item)
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)
    except Exception as e:
        print(f"Local archive save note: {e}")

def normalize_submission(item: dict) -> dict:
    """Ensures file_path is web-streamable by the portal player."""
    fp = item.get("file_path", "")
    fn = item.get("file_name", "")
    if fp and not fp.startswith("http") and not fp.startswith("/"):
        clean_name = Path(fp).name
        item["file_path"] = f"/media/submissions/{clean_name}"
    elif not fp and fn:
        item["file_path"] = f"/media/submissions/{Path(fn).name}"
    return item

@router.get("")
def list_submissions():
    """Lists all submitted reels stored in the Supabase backend archive."""
    all_subs = []
    seen_ids = set()

    # 1. Supabase attempt
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase:
        try:
            res = supabase.table("submissions").select("*").order("created_at", desc=True).execute()
            if res.data:
                for row in res.data:
                    row_id = str(row.get("id") or row.get("submission_id"))
                    seen_ids.add(row_id)
                    all_subs.append(normalize_submission(row))
        except Exception as e:
            print(f"Supabase fetch note: {e}")

    # 2. Local archive merge
    local_items = _load_local_archive()
    for row in local_items:
        row_id = str(row.get("id") or row.get("submission_id"))
        if row_id not in seen_ids:
            seen_ids.add(row_id)
            all_subs.append(normalize_submission(row))

    return {"submissions": all_subs}

@router.post("")
def create_submission(payload: dict):
    """Stores video reel submission into Supabase backend archive."""
    sub_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"
    sub_data = {
        "id": sub_id,
        "submission_id": sub_id,
        "team_name": payload.get("team_name", "").strip(),
        "representative_name": payload.get("representative_name", "Registered Participant").strip(),
        "representative_email": payload.get("email", "").strip().lower(),
        "representative_phone": payload.get("phone", "").strip(),
        "institution": payload.get("institution", "College / Independent").strip(),
        "title": payload.get("title", "").strip(),
        "description": payload.get("description", "Reel video submission").strip(),
        "language": payload.get("language", "Tamil").strip(),
        "file_path": payload.get("file_path", ""),
        "file_name": payload.get("file_name", "reel.mp4"),
        "file_size": payload.get("file_size", 0),
        "duration": payload.get("duration", 30.0),
        "width": payload.get("width", 1080),
        "height": payload.get("height", 1920),
        "aspect_ratio": "9:16",
        "submission_status": "submitted",
        "created_at": datetime.utcnow().isoformat()
    }

    # Store locally
    _save_local_archive(sub_data)

    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase:
        try:
            res = supabase.table("submissions").insert(sub_data).execute()
            if res.data:
                sub_id = res.data[0]["id"]
        except Exception as e:
            print(f"Supabase sync note: {e}")

    return {
        "success": True,
        "message": "Reel successfully uploaded and stored in Supabase archive!",
        "submission_id": str(sub_id)
    }

@router.post("/verify-video", response_model=VideoVerificationResponse)
def verify_video(payload: VideoVerificationRequest):
    """Performs server-side validation of reel metadata before/after storage upload."""
    result = validate_video_metadata(
        file_name=payload.file_name,
        file_size=payload.file_size,
        duration=payload.duration,
        width=payload.width,
        height=payload.height
    )
    return VideoVerificationResponse(**result)

@router.post("/direct-submit")
def direct_submit_reel(payload: DirectReelUploadRequest):
    """Direct reel submission after Google Form registration."""
    if not is_submission_open():
        raise HTTPException(status_code=400, detail="Reel submission deadline has passed (8 November 2026).")

    # Server-side validation
    validation = validate_video_metadata(
        file_name=payload.file_name,
        file_size=payload.file_size,
        duration=payload.duration,
        width=payload.width,
        height=payload.height
    )
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail="Video validation failed: " + "; ".join(validation["errors"])
        )

    if not (
        payload.originality_confirmed and
        payload.participant_consent_confirmed and
        payload.copyright_confirmed and
        payload.rules_confirmed and
        payload.final_lock_confirmed
    ):
        raise HTTPException(status_code=400, detail="All legal and ethical confirmations must be accepted.")

    submission_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"

    sub_data = {
        "id": submission_id,
        "submission_id": submission_id,
        "team_name": payload.team_name.strip(),
        "representative_name": (payload.representative_name or "Registered Team").strip(),
        "representative_email": (payload.representative_email or "participant@mindscape.org").strip().lower(),
        "representative_phone": (payload.representative_phone or "").strip(),
        "institution": (payload.institution or "College / Institution").strip(),
        "city": (payload.city or "Chennai").strip(),
        "title": payload.title.strip(),
        "description": (payload.description or "Reel video submission for Mindscape 2026").strip(),
        "language": payload.language.strip(),
        "file_path": payload.file_path,
        "file_name": payload.file_name,
        "file_size": payload.file_size,
        "duration": payload.duration,
        "width": payload.width,
        "height": payload.height,
        "aspect_ratio": "9:16",
        "submission_status": "submitted",
        "created_at": datetime.utcnow().isoformat()
    }

    # Normalize file path so it's streamable
    sub_data = normalize_submission(sub_data)

    # Save to persistent local backend archive
    _save_local_archive(sub_data)

    # Also sync to Supabase if connected
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase:
        try:
            team_data = {
                "team_name": sub_data["team_name"],
                "representative_name": sub_data["representative_name"],
                "representative_email": sub_data["representative_email"],
                "representative_phone": sub_data["representative_phone"],
                "institution": sub_data["institution"],
                "city": sub_data["city"],
                "status": "submitted"
            }
            supabase.table("teams").insert(team_data).execute()
            supabase.table("submissions").insert(sub_data).execute()
        except Exception as e:
            print(f"Supabase sync note: {e}")

    return {
        "success": True,
        "message": "Reel successfully uploaded and stored in Supabase archive!",
        "submission_id": submission_id,
        "file_path": sub_data["file_path"]
    }

@router.post("/direct-submit-upload")
async def direct_submit_upload(
    video_file: UploadFile = File(...),
    team_name: str = Form(...),
    title: str = Form(...),
    language: str = Form("Tamil"),
    representative_name: Optional[str] = Form("Registered Team"),
    representative_email: Optional[str] = Form("participant@mindscape.org"),
    representative_phone: Optional[str] = Form(""),
    institution: Optional[str] = Form("College / Institution"),
    city: Optional[str] = Form("Chennai"),
    description: Optional[str] = Form("Reel video submission for Mindscape 2026"),
    duration: float = Form(30.0),
    width: int = Form(1080),
    height: int = Form(1920)
):
    """Direct multipart video upload saving to public media submissions and Supabase archive."""
    if not is_submission_open():
        raise HTTPException(status_code=400, detail="Reel submission deadline has passed (8 November 2026).")

    orig_name = Path(video_file.filename).name if video_file.filename else "reel.mp4"
    safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', orig_name)
    file_id = uuid.uuid4().hex[:8]
    stored_filename = f"{file_id}_{safe_name}"

    file_size = 0
    try:
        CLIENT_PUBLIC_MEDIA.mkdir(parents=True, exist_ok=True)
        file_dest = CLIENT_PUBLIC_MEDIA / stored_filename
        with open(file_dest, "wb") as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        file_size = file_dest.stat().st_size
    except Exception as e:
        print(f"Local file write note: {e}")
    relative_url = f"/media/submissions/{stored_filename}"
    submission_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"

    sub_data = {
        "id": submission_id,
        "submission_id": submission_id,
        "team_name": team_name.strip(),
        "representative_name": (representative_name or "Registered Team").strip(),
        "representative_email": (representative_email or "participant@mindscape.org").strip().lower(),
        "representative_phone": (representative_phone or "").strip(),
        "institution": (institution or "College / Institution").strip(),
        "city": (city or "Chennai").strip(),
        "title": title.strip(),
        "description": (description or "Reel video submission for Mindscape 2026").strip(),
        "language": language.strip(),
        "file_path": relative_url,
        "file_name": orig_name,
        "file_size": file_size,
        "duration": duration,
        "width": width,
        "height": height,
        "aspect_ratio": "9:16",
        "submission_status": "submitted",
        "created_at": datetime.utcnow().isoformat()
    }

    _save_local_archive(sub_data)

    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase:
        try:
            team_data = {
                "team_name": sub_data["team_name"],
                "representative_name": sub_data["representative_name"],
                "representative_email": sub_data["representative_email"],
                "representative_phone": sub_data["representative_phone"],
                "institution": sub_data["institution"],
                "city": sub_data["city"],
                "status": "submitted"
            }
            supabase.table("teams").insert(team_data).execute()
            supabase.table("submissions").insert(sub_data).execute()
        except Exception as e:
            print(f"Supabase sync note: {e}")

    return {
        "success": True,
        "message": "Reel successfully uploaded and stored in Supabase archive!",
        "submission_id": submission_id,
        "file_path": relative_url
    }
