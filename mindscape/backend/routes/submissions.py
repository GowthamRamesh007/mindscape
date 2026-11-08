from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from typing import Optional
import json
import uuid
import shutil
import re
import hashlib
from pathlib import Path
from datetime import datetime

try:
    from backend.models.schemas import (
        VideoVerificationRequest,
        VideoVerificationResponse,
        DirectReelUploadRequest,
        PrepareDirectUploadRequest,
        FinalizeDirectUploadRequest
    )
    from backend.services.deadline_service import is_submission_open
    from backend.services.video_service import validate_video_metadata
    from backend.services.supabase_service import (
        get_supabase_admin,
        get_supabase_anon,
        upload_file_to_supabase_storage,
        create_signed_supabase_upload,
        verify_supabase_storage_object
    )
    from backend.services.google_sheets_service import is_team_registered, get_team_registration, verify_team_registration
    from backend.services.gdrive_service import (
        upload_file_to_gdrive,
        create_client_resumable_upload_session,
        verify_gdrive_file,
        find_file_by_idempotency_key,
        GDRIVE_FOLDER_URL,
        GDRIVE_FOLDER_ID
    )
except ModuleNotFoundError:
    from models.schemas import (
        VideoVerificationRequest,
        VideoVerificationResponse,
        DirectReelUploadRequest,
        PrepareDirectUploadRequest,
        FinalizeDirectUploadRequest
    )
    from services.deadline_service import is_submission_open
    from services.video_service import validate_video_metadata
    from services.supabase_service import (
        get_supabase_admin,
        get_supabase_anon,
        upload_file_to_supabase_storage,
        create_signed_supabase_upload,
        verify_supabase_storage_object
    )
    from services.google_sheets_service import is_team_registered, get_team_registration, verify_team_registration
    from services.gdrive_service import (
        upload_file_to_gdrive,
        create_client_resumable_upload_session,
        verify_gdrive_file,
        find_file_by_idempotency_key,
        GDRIVE_FOLDER_URL,
        GDRIVE_FOLDER_ID
    )

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

_project_root = Path(__file__).resolve().parent.parent.parent
ARCHIVE_DIR = _project_root / "data"
ARCHIVE_FILE = ARCHIVE_DIR / "submissions_archive.json"

# Both root media and client media locations
MEDIA_DIRS = [
    _project_root / "media" / "submissions",
    _project_root / "client" / "public" / "media" / "submissions"
]
for md in MEDIA_DIRS:
    try:
        md.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
CLIENT_PUBLIC_MEDIA = MEDIA_DIRS[0]

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
    team_name = (payload.get("team_name") or "").strip()
    verification = verify_team_registration(team_name)
    if not verification["is_registered"]:
        if verification.get("service_unavailable"):
            raise HTTPException(
                status_code=503,
                detail=verification.get("error") or "Registration verification service is currently unavailable. Submissions are temporarily blocked."
            )
        raise HTTPException(
            status_code=403,
            detail="This team is not registered for Mindscape. Please complete the official registration form first."
        )

    sub_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"
    sub_data = {
        "id": sub_id,
        "submission_id": sub_id,
        "team_name": team_name,
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
@router.post("/direct-submit/")
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

    # Verify team is registered on Google Form
    verification = verify_team_registration(payload.team_name)
    if not verification["is_registered"]:
        if verification.get("service_unavailable"):
            raise HTTPException(
                status_code=503,
                detail=verification.get("error") or "Registration verification service is currently unavailable. Submissions are temporarily blocked."
            )
        raise HTTPException(
            status_code=403,
            detail="This team is not registered for Mindscape. Please complete the official registration form first."
        )

    reg = verification["team"]
    rep_name = (payload.representative_name or (reg.get("representative_name") if reg else "") or "Registered Team").strip()
    rep_email = (payload.representative_email or (reg.get("email") if reg else "") or "participant@mindscape.org").strip().lower()
    rep_phone = (payload.representative_phone or (reg.get("phone") if reg else "") or "").strip()
    inst = (payload.institution or (reg.get("institution") if reg else "") or "College / Institution").strip()
    loc_city = (payload.city or (reg.get("city") if reg else "") or "Chennai").strip()

    submission_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"

    sub_data = {
        "id": submission_id,
        "submission_id": submission_id,
        "team_name": payload.team_name.strip(),
        "representative_name": rep_name,
        "representative_email": rep_email,
        "representative_phone": rep_phone,
        "institution": inst,
        "city": loc_city,
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
                "representative_email": sub_data.get("representative_email") or "participant@mindscape.org",
                "representative_phone": sub_data.get("representative_phone") or "9876543210",
                "institution": sub_data.get("institution") or "College / Institution",
                "city": sub_data.get("city") or "Chennai",
                "status": "submitted"
            }
            supabase.table("teams").insert(team_data).execute()
        except Exception as e:
            print(f"Supabase teams sync note: {e}")

        try:
            sub_insert = {
                "team_name": sub_data["team_name"],
                "representative_name": sub_data["representative_name"],
                "representative_email": sub_data.get("representative_email") or "participant@mindscape.org",
                "representative_phone": sub_data.get("representative_phone") or "9876543210",
                "institution": sub_data.get("institution") or "College / Institution",
                "title": sub_data["title"],
                "description": sub_data.get("description", "Reel video submission"),
                "language": sub_data.get("language", "Tamil"),
                "file_path": sub_data.get("file_path", ""),
                "file_name": sub_data.get("file_name", "reel.mp4"),
                "file_size": sub_data.get("file_size") or 1024,
                "duration": sub_data.get("duration") or 30.0,
                "width": sub_data.get("width") or 1080,
                "height": sub_data.get("height") or 1920,
                "aspect_ratio": "9:16",
                "submission_status": "submitted"
            }
            supabase.table("submissions").insert(sub_insert).execute()
        except Exception as e:
            print(f"Supabase submissions sync note: {e}")

    return {
        "success": True,
        "message": "Reel successfully uploaded and stored in Supabase archive!",
        "submission_id": submission_id,
        "file_path": sub_data["file_path"]
    }

@router.post("/direct-submit-upload")
@router.post("/direct-submit-upload/")
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
    height: int = Form(1920),
    idempotency_key: Optional[str] = Form(None)
):
    """
    Direct multipart video upload saving video binaries EXCLUSIVELY to Google Drive,
    and recording submission metadata in Supabase DB (teams and submissions tables).
    Supabase Storage receives zero video binaries.
    """
    if not is_submission_open():
        raise HTTPException(status_code=400, detail="Reel submission deadline has passed (8 November 2026).")

    # 1. Strict Server-Side Verification against Authoritative Google Form Responses
    verification = verify_team_registration(team_name)
    if not verification["is_registered"]:
        if verification.get("service_unavailable"):
            raise HTTPException(
                status_code=503,
                detail=verification.get("error") or "Registration verification service is currently unavailable. Submissions are temporarily blocked."
            )
        raise HTTPException(
            status_code=403,
            detail="This team is not registered for Mindscape. Please complete the official registration form first."
        )

    reg = verification["team"]
    rep_name = (representative_name if (representative_name and representative_name != "Registered Team") else (reg.get("representative_name") if reg else "") or "Registered Team").strip()
    rep_email = (representative_email if (representative_email and representative_email != "participant@mindscape.org") else (reg.get("email") if reg else "") or "participant@mindscape.org").strip().lower()
    rep_phone = (representative_phone or (reg.get("phone") if reg else "") or "").strip()
    inst = (institution if (institution and institution != "College / Institution") else (reg.get("institution") if reg else "") or "College / Institution").strip()
    loc_city = (city if (city and city != "Chennai") else (reg.get("city") if reg else "") or "Chennai").strip()

    orig_name = Path(video_file.filename).name if video_file.filename else "reel.mp4"
    safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', orig_name)
    file_id = uuid.uuid4().hex[:8]
    stored_filename = f"{file_id}_{safe_name}"

    # 1. Read video binary directly into memory (NO permanent local storage)
    try:
        raw_bytes = await video_file.read()
    except Exception as read_err:
        raise HTTPException(status_code=400, detail=f"Failed to read video file: {read_err}")

    file_size = len(raw_bytes) if raw_bytes else 0

    # 2. Cryptographic SHA-256 hash & stable idempotency key
    video_hash = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes else ""
    clean_team = re.sub(r'[^a-zA-Z0-9]', '_', team_name.strip().lower())
    stable_idempotency_key = f"{clean_team}:{video_hash}"

    # 3. Server-side Video Validation (duration 25s - 45s, 9:16 vertical orientation, file size limit)
    validation = validate_video_metadata(
        file_name=orig_name,
        file_size=file_size,
        duration=duration,
        width=width,
        height=height
    )
    if not validation.get("valid", True):
        raise HTTPException(
            status_code=400,
            detail="Video validation failed: " + "; ".join(validation.get("errors", ["Invalid video"]))
        )

    # 4. Database Idempotency Check (matching team_name and SHA-256 video_hash)
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase and video_hash:
        try:
            existing = (
                supabase.table("submissions")
                .select("*")
                .eq("team_name", team_name.strip())
                .eq("video_hash", video_hash)
                .limit(1)
                .execute()
            )
            if existing.data and len(existing.data) > 0:
                ex_row = existing.data[0]
                existing_url = ex_row.get("gdrive_url") or ex_row.get("file_path")
                print(f"[Submissions] Idempotent DB match found for team '{team_name}' by SHA-256 (ID: {ex_row.get('id')})")
                return {
                    "success": True,
                    "message": "Reel already submitted and backed up (idempotent duplicate request).",
                    "submission_id": str(ex_row.get("id")),
                    "file_path": existing_url,
                    "gdrive_url": existing_url,
                    "gdrive_file_id": ex_row.get("gdrive_file_id"),
                    "video_hash": video_hash,
                    "gdrive_folder_url": GDRIVE_FOLDER_URL
                }
        except Exception as chk_err:
            print(f"Idempotency DB check note: {chk_err}")

    # 5. Dual Upload Pipeline: Google Drive and Supabase Storage
    # Step A: Google Drive Upload
    gdrive_file_url = None
    gdrive_file_id = None
    gdrive_upload_res = None
    if raw_bytes:
        try:
            gdrive_upload_res = upload_file_to_gdrive(
                file_bytes=raw_bytes,
                file_name=f"{clean_team[:20]}_{stored_filename}",
                mime_type=video_file.content_type or "video/mp4",
                idempotency_key=stable_idempotency_key,
                video_hash=video_hash
            )
            if isinstance(gdrive_upload_res, dict):
                gdrive_file_url = gdrive_upload_res.get("webViewLink")
                gdrive_file_id = gdrive_upload_res.get("file_id")
            elif isinstance(gdrive_upload_res, str):
                gdrive_file_url = gdrive_upload_res
        except Exception as ge:
            print(f"Google Drive upload exception in route: {ge}")

    # Enforce Drive upload success
    if not gdrive_file_url:
        raise HTTPException(
            status_code=502,
            detail="Google Drive video upload failed. Please verify connection and try again."
        )

    # Extract Google Drive file ID if not already captured
    if not gdrive_file_id:
        id_match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_file_url) or re.search(r'id=([a-zA-Z0-9_-]+)', gdrive_file_url)
        if id_match:
            gdrive_file_id = id_match.group(1)

    # Step B: Supabase Storage Upload
    supabase_storage_url = None
    try:
        supabase_storage_url = upload_file_to_supabase_storage(
            file_bytes=raw_bytes,
            file_name=f"{clean_team[:20]}_{stored_filename}",
            content_type=video_file.content_type or "video/mp4",
            bucket="mindscape-reels"
        )
    except Exception as sse:
        print(f"Supabase Storage upload note: {sse}")

    # Fallback storage path to Drive URL if Supabase storage is not reachable
    primary_file_path = supabase_storage_url or gdrive_file_url

    submission_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"

    # 6. Record team in Supabase 'teams' table (reusing existing team record if already present)
    team_id = None
    if supabase:
        try:
            existing_tm = (
                supabase.table("teams")
                .select("id")
                .eq("team_name", team_name.strip())
                .limit(1)
                .execute()
            )
            if existing_tm.data and len(existing_tm.data) > 0:
                team_id = existing_tm.data[0].get("id")
                # Update status to submitted if not already
                supabase.table("teams").update({"status": "submitted"}).eq("id", team_id).execute()
            else:
                team_data = {
                    "team_name": team_name.strip(),
                    "representative_name": rep_name,
                    "representative_email": rep_email,
                    "representative_phone": rep_phone,
                    "institution": inst,
                    "city": loc_city,
                    "status": "submitted"
                }
                tm_res = supabase.table("teams").insert(team_data).execute()
                if tm_res.data and len(tm_res.data) > 0:
                    team_id = tm_res.data[0].get("id")
        except Exception as te:
            print(f"Supabase teams record note: {te}")

    # 7. Record metadata in Supabase 'submissions' table (metadata only, zero video binaries)
    sub_insert = {
        "team_name": team_name.strip(),
        "representative_name": rep_name,
        "representative_email": rep_email,
        "representative_phone": rep_phone,
        "institution": inst,
        "title": title.strip(),
        "description": (description or "Reel video submission for Mindscape 2026").strip(),
        "language": language.strip(),
        "file_path": primary_file_path,
        "file_name": orig_name,
        "file_size": file_size,
        "duration": duration,
        "width": width,
        "height": height,
        "aspect_ratio": "9:16",
        "submission_status": "submitted"
    }
    if team_id:
        sub_insert["team_id"] = team_id

    if supabase:
        # First attempt insert with optional gdrive_url, gdrive_file_id, and video_hash columns
        try:
            extended_insert = dict(sub_insert)
            extended_insert["gdrive_url"] = gdrive_file_url
            if gdrive_file_id:
                extended_insert["gdrive_file_id"] = gdrive_file_id
            if video_hash:
                extended_insert["video_hash"] = video_hash
            sub_res = supabase.table("submissions").insert(extended_insert).execute()
            if sub_res.data and len(sub_res.data) > 0:
                submission_id = str(sub_res.data[0].get("id"))
        except Exception as ext_err:
            err_str = str(ext_err).lower()
            if "pgrst204" in err_str or "column" in err_str:
                # If video_hash column is not yet migrated, fall back gracefully
                try:
                    fallback_insert = dict(sub_insert)
                    fallback_insert["gdrive_url"] = gdrive_file_url
                    if gdrive_file_id:
                        fallback_insert["gdrive_file_id"] = gdrive_file_id
                    sub_res = supabase.table("submissions").insert(fallback_insert).execute()
                    if sub_res.data and len(sub_res.data) > 0:
                        submission_id = str(sub_res.data[0].get("id"))
                except Exception:
                    try:
                        sub_res = supabase.table("submissions").insert(sub_insert).execute()
                        if sub_res.data and len(sub_res.data) > 0:
                            submission_id = str(sub_res.data[0].get("id"))
                    except Exception as fallback_err:
                        print(f"Supabase submissions fallback insert note: {fallback_err}")
            else:
                print(f"Supabase submissions insert note: {ext_err}")

    # 8. Persist to local backup archive (metadata only)
    sub_data = {
        "id": submission_id,
        "submission_id": submission_id,
        "team_id": team_id,
        "team_name": team_name.strip(),
        "representative_name": rep_name,
        "representative_email": rep_email,
        "representative_phone": rep_phone,
        "institution": inst,
        "city": loc_city,
        "title": title.strip(),
        "description": (description or "Reel video submission for Mindscape 2026").strip(),
        "language": language.strip(),
        "file_path": primary_file_path,
        "gdrive_url": gdrive_file_url,
        "gdrive_file_id": gdrive_file_id,
        "video_hash": video_hash,
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

    return {
        "success": True,
        "message": "Reel successfully uploaded to Google Drive and Supabase!",
        "submission_id": submission_id,
        "file_id": gdrive_file_id,
        "filename": orig_name,
        "webViewLink": gdrive_file_url,
        "file_path": primary_file_path,
        "supabase_url": supabase_storage_url,
        "gdrive_url": gdrive_file_url,
        "gdrive_file_id": gdrive_file_id,
        "video_hash": video_hash,
        "gdrive_folder_url": GDRIVE_FOLDER_URL
    }

@router.post("/prepare-direct-upload")
@router.post("/prepare-direct-upload/")
def prepare_direct_upload(payload: PrepareDirectUploadRequest):
    """
    Step 1 of Direct-to-Cloud Upload Architecture:
    Authenticates team registration, validates video metadata (25-45s, 9:16), checks idempotency,
    and returns short-lived signed URLs for the browser client to upload directly to:
    1) Supabase Storage (mindscape-reels bucket)
    2) Google Drive (resumable session URL)
    Zero video binaries pass through Vercel Functions.
    """
    if not is_submission_open():
        raise HTTPException(status_code=400, detail="Reel submission deadline has passed (8 November 2026).")

    # 1. Verify Team Registration
    verification = verify_team_registration(payload.team_name)
    if not verification["is_registered"]:
        if verification.get("service_unavailable"):
            raise HTTPException(
                status_code=503,
                detail=verification.get("error") or "Registration verification service is currently unavailable."
            )
        raise HTTPException(
            status_code=403,
            detail="This team is not registered for Mindscape. Please complete the official registration form first."
        )

    # 2. Server-side Video Validation
    validation = validate_video_metadata(
        file_name=payload.file_name,
        file_size=payload.file_size,
        duration=payload.duration,
        width=payload.width,
        height=payload.height
    )
    if not validation.get("valid", True):
        raise HTTPException(
            status_code=400,
            detail="Video validation failed: " + "; ".join(validation.get("errors", ["Invalid video"]))
        )

    clean_team = re.sub(r'[^a-zA-Z0-9]', '_', payload.team_name.strip().lower())
    orig_name = Path(payload.file_name).name if payload.file_name else "reel.mp4"
    safe_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', orig_name)
    file_id = uuid.uuid4().hex[:8]
    stored_filename = f"{clean_team[:20]}_{file_id}_{safe_name}"

    # 3. Check Idempotency via SHA-256
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase and payload.video_hash:
        try:
            existing = (
                supabase.table("submissions")
                .select("*")
                .eq("team_name", payload.team_name.strip())
                .eq("video_hash", payload.video_hash)
                .limit(1)
                .execute()
            )
            if existing.data and len(existing.data) > 0:
                ex_row = existing.data[0]
                return {
                    "already_submitted": True,
                    "submission_id": str(ex_row.get("id")),
                    "file_path": ex_row.get("file_path"),
                    "gdrive_url": ex_row.get("gdrive_url"),
                    "gdrive_file_id": ex_row.get("gdrive_file_id")
                }
        except Exception as chk_err:
            print(f"Idempotency check note: {chk_err}")

    stable_idempotency_key = f"{clean_team}:{payload.video_hash}" if payload.video_hash else None

    # 4. Generate Supabase Storage Signed Upload URL
    supabase_storage_path = f"reels/{stored_filename}"
    supabase_upload_data = create_signed_supabase_upload(storage_path=supabase_storage_path, bucket="mindscape-reels")
    if not supabase_upload_data or not supabase_upload_data.get("signed_url"):
        raise HTTPException(status_code=502, detail="Failed to generate secure Supabase upload session.")

    # 5. Generate Google Drive Resumable Upload Session
    gdrive_session = create_client_resumable_upload_session(
        file_name=stored_filename,
        mime_type=payload.mime_type or "video/mp4",
        file_size=payload.file_size,
        idempotency_key=stable_idempotency_key,
        video_hash=payload.video_hash
    )
    if not gdrive_session:
        raise HTTPException(status_code=502, detail="Failed to initialize Google Drive upload session.")

    return {
        "success": True,
        "already_submitted": False,
        "stored_filename": stored_filename,
        "supabase_upload": {
            "signed_url": supabase_upload_data["signed_url"],
            "storage_path": supabase_storage_path,
            "public_url": supabase_upload_data["public_url"],
            "bucket": "mindscape-reels"
        },
        "gdrive_upload": gdrive_session,
        "team": verification.get("team")
    }

@router.post("/finalize-direct-upload")
@router.post("/finalize-direct-upload/")
def finalize_direct_upload(payload: FinalizeDirectUploadRequest):
    """
    Step 2 of Direct-to-Cloud Upload Architecture:
    Lightweight finalization endpoint that receives only metadata.
    Verifies that the video object was successfully received in Supabase Storage and Google Drive,
    validates metadata, inserts the official submission record into Supabase DB, and returns confirmation.
    """
    if not is_submission_open():
        raise HTTPException(status_code=400, detail="Reel submission deadline has passed (8 November 2026).")

    # 1. Verify Registration
    verification = verify_team_registration(payload.team_name)
    if not verification["is_registered"]:
        raise HTTPException(status_code=403, detail="This team is not registered for Mindscape.")

    reg = verification.get("team")
    rep_name = (payload.representative_name if (payload.representative_name and payload.representative_name != "Registered Team") else (reg.get("representative_name") if reg else "") or "Registered Team").strip()
    rep_email = (payload.representative_email if (payload.representative_email and payload.representative_email != "participant@mindscape.org") else (reg.get("email") if reg else "") or "participant@mindscape.org").strip().lower()
    rep_phone = (payload.representative_phone or (reg.get("phone") if reg else "") or "").strip()
    inst = (payload.institution if (payload.institution and payload.institution != "College / Institution") else (reg.get("institution") if reg else "") or "College / Institution").strip()
    loc_city = (payload.city if (payload.city and payload.city != "Chennai") else (reg.get("city") if reg else "") or "Chennai").strip()

    # 2. Server-side Verification of Uploaded Objects
    # Verify Supabase storage object
    supa_obj = verify_supabase_storage_object(payload.supabase_storage_path, bucket="mindscape-reels")
    if not supa_obj:
        raise HTTPException(
            status_code=400,
            detail="Supabase storage video verification failed. Object not found in storage bucket."
        )

    # Verify Google Drive file
    drive_obj = verify_gdrive_file(payload.gdrive_file_id)
    if not drive_obj:
        raise HTTPException(
            status_code=400,
            detail="Google Drive video verification failed. File not found or trashed."
        )

    gdrive_file_url = drive_obj.get("webViewLink") or payload.gdrive_web_link or f"https://drive.google.com/file/d/{payload.gdrive_file_id}/view"
    primary_file_path = supa_obj.get("public_url") or gdrive_file_url

    # 3. Check for Existing Duplicate Submission by SHA-256
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase and payload.video_hash:
        try:
            existing = (
                supabase.table("submissions")
                .select("*")
                .eq("team_name", payload.team_name.strip())
                .eq("video_hash", payload.video_hash)
                .limit(1)
                .execute()
            )
            if existing.data and len(existing.data) > 0:
                ex_row = existing.data[0]
                return {
                    "success": True,
                    "message": "Reel already submitted and backed up (idempotent duplicate request).",
                    "submission_id": str(ex_row.get("id")),
                    "file_path": ex_row.get("file_path"),
                    "gdrive_url": ex_row.get("gdrive_url"),
                    "gdrive_file_id": ex_row.get("gdrive_file_id"),
                    "video_hash": payload.video_hash,
                    "gdrive_folder_url": GDRIVE_FOLDER_URL
                }
        except Exception as chk_err:
            print(f"Idempotency check note: {chk_err}")

    # 4. Insert or Update Team in 'teams' table
    team_id = None
    if supabase:
        try:
            existing_tm = supabase.table("teams").select("id").eq("team_name", payload.team_name.strip()).limit(1).execute()
            if existing_tm.data and len(existing_tm.data) > 0:
                team_id = existing_tm.data[0].get("id")
                supabase.table("teams").update({"status": "submitted"}).eq("id", team_id).execute()
            else:
                team_data = {
                    "team_name": payload.team_name.strip(),
                    "representative_name": rep_name,
                    "representative_email": rep_email,
                    "representative_phone": rep_phone,
                    "institution": inst,
                    "city": loc_city,
                    "status": "submitted"
                }
                tm_res = supabase.table("teams").insert(team_data).execute()
                if tm_res.data and len(tm_res.data) > 0:
                    team_id = tm_res.data[0].get("id")
        except Exception as te:
            print(f"Supabase teams record note: {te}")

    # 5. Insert Record into 'submissions' Table
    submission_id = f"MS26-{uuid.uuid4().hex[:6].upper()}"
    sub_insert = {
        "team_name": payload.team_name.strip(),
        "representative_name": rep_name,
        "representative_email": rep_email,
        "representative_phone": rep_phone,
        "institution": inst,
        "title": payload.title.strip(),
        "description": (payload.description or "Reel video submission for Mindscape 2026").strip(),
        "language": payload.language.strip(),
        "file_path": primary_file_path,
        "file_name": payload.file_name,
        "file_size": payload.file_size,
        "duration": payload.duration,
        "width": payload.width,
        "height": payload.height,
        "aspect_ratio": "9:16",
        "submission_status": "submitted",
        "gdrive_url": gdrive_file_url,
        "gdrive_file_id": payload.gdrive_file_id,
        "video_hash": payload.video_hash
    }
    if team_id:
        sub_insert["team_id"] = team_id

    if supabase:
        try:
            sub_res = supabase.table("submissions").insert(sub_insert).execute()
            if sub_res.data and len(sub_res.data) > 0:
                submission_id = str(sub_res.data[0].get("id"))
        except Exception as ins_err:
            print(f"Supabase submissions insert error: {ins_err}")
            # Try fallback without video_hash if schema differs
            try:
                fallback_insert = dict(sub_insert)
                fallback_insert.pop("video_hash", None)
                sub_res = supabase.table("submissions").insert(fallback_insert).execute()
                if sub_res.data and len(sub_res.data) > 0:
                    submission_id = str(sub_res.data[0].get("id"))
            except Exception as e2:
                print(f"Fallback insert note: {e2}")

    # 6. Local archive save
    sub_data = dict(sub_insert)
    sub_data["id"] = submission_id
    sub_data["submission_id"] = submission_id
    sub_data["created_at"] = datetime.utcnow().isoformat()
    _save_local_archive(sub_data)

    return {
        "success": True,
        "message": "Reel successfully uploaded to Google Drive and Supabase!",
        "submission_id": submission_id,
        "file_id": payload.gdrive_file_id,
        "filename": payload.file_name,
        "webViewLink": gdrive_file_url,
        "file_path": primary_file_path,
        "supabase_url": supa_obj.get("public_url"),
        "gdrive_url": gdrive_file_url,
        "gdrive_file_id": payload.gdrive_file_id,
        "video_hash": payload.video_hash,
        "gdrive_folder_url": GDRIVE_FOLDER_URL
    }
