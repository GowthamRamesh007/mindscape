import os
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Set up logging for gdrive service
logger = logging.getLogger("mindscape.gdrive")

# Robust dotenv loading across project root, .env folder, and backend
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
for _env_path in [
    _project_root / ".env",
    _project_root / ".env" / ".env",
    _project_root / "backend" / ".env",
    Path.cwd() / ".env",
    Path.cwd() / ".env" / ".env"
]:
    if _env_path.is_file():
        load_dotenv(_env_path)
load_dotenv()

# Import project's existing Supabase client helper
try:
    from backend.services.supabase_service import get_supabase_admin, get_supabase_anon
except ModuleNotFoundError:
    from services.supabase_service import get_supabase_admin, get_supabase_anon

# Fallback default Google Drive folder
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "19GL0-JhadO0fRXlRzVS5tFTQ1_2pKbD1").strip()
GDRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{GDRIVE_FOLDER_ID}?usp=sharing"

_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks for resumable video upload

def get_google_drive_credentials() -> Optional[Dict[str, Any]]:
    """
    Retrieves Google Drive OAuth credentials.
    Priority:
    1. Direct environment variables (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN).
    2. Supabase table 'google_drive_connections'.
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    env_refresh = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
    folder_id = os.getenv("GDRIVE_FOLDER_ID", GDRIVE_FOLDER_ID).strip()

    # If refresh token in environment is present, try checking if it works
    if client_id and client_secret and env_refresh:
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": env_refresh,
            "drive_folder_id": folder_id
        }

    # Fallback to Supabase google_drive_connections table
    client = get_supabase_admin() or get_supabase_anon()
    if client:
        try:
            res = client.table("google_drive_connections").select("*").eq("id", True).limit(1).execute()
            if res.data and len(res.data) > 0:
                conn = res.data[0]
                return {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": conn.get("refresh_token"),
                    "drive_folder_id": conn.get("drive_folder_id") or folder_id
                }
            
            res_any = client.table("google_drive_connections").select("*").order("updated_at", desc=True).limit(1).execute()
            if res_any.data and len(res_any.data) > 0:
                conn = res_any.data[0]
                return {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": conn.get("refresh_token"),
                    "drive_folder_id": conn.get("drive_folder_id") or folder_id
                }
        except Exception as e:
            logger.error(f"[GDrive] Failed to fetch Google Drive connection from Supabase: {e}")

    return None

def get_fresh_access_token(refresh_token: str, client_id: Optional[str] = None, client_secret: Optional[str] = None) -> Optional[str]:
    """
    Exchanges the refresh_token for a fresh Google OAuth2 access_token using
    https://oauth2.googleapis.com/token.
    """
    cid = client_id or os.getenv("GOOGLE_CLIENT_ID", "").strip()
    csec = client_secret or os.getenv("GOOGLE_CLIENT_SECRET", "").strip()

    if not cid or not csec:
        logger.error("[GDrive] Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET environment variables.")
        return None

    if not refresh_token:
        logger.error("[GDrive] Missing refresh token for Google OAuth exchange.")
        return None

    token_url = "https://oauth2.googleapis.com/token"
    payload = json.dumps({
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }).encode("utf-8")

    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            access_token = data.get("access_token")
            if access_token:
                return access_token
            logger.error("[GDrive] Token refresh response did not contain access_token.")
    except urllib.error.HTTPError as he:
        # If env refresh token returned 401, check Supabase table as fallback
        logger.warning(f"[GDrive] HTTP error during token refresh (Status {he.code}). Checking DB connection fallback...")
        client = get_supabase_admin() or get_supabase_anon()
        if client:
            try:
                res = client.table("google_drive_connections").select("*").eq("id", True).limit(1).execute()
                if res.data and res.data[0].get("refresh_token") != refresh_token:
                    db_token = res.data[0].get("refresh_token")
                    if db_token:
                        payload2 = json.dumps({
                            "client_id": cid,
                            "client_secret": csec,
                            "refresh_token": db_token,
                            "grant_type": "refresh_token"
                        }).encode("utf-8")
                        req2 = urllib.request.Request(token_url, data=payload2, headers={"Content-Type": "application/json"}, method="POST")
                        with urllib.request.urlopen(req2, timeout=30) as resp2:
                            data2 = json.loads(resp2.read().decode("utf-8"))
                            return data2.get("access_token")
            except Exception as db_err:
                logger.error(f"[GDrive] Fallback token refresh error: {db_err}")
    except Exception as e:
        logger.error(f"[GDrive] Unexpected error during token refresh: {e}")

    return None

def find_file_by_idempotency_key(idempotency_key: str) -> Optional[Dict[str, Any]]:
    """
    Searches the configured Google Drive folder for an existing file
    matching the given idempotency_key stored in appProperties.
    Returns dict with 'file_id', 'drive_url', and 'name' if found, else None.
    """
    if not idempotency_key:
        return None

    creds = get_google_drive_credentials()
    if not creds or not creds.get("refresh_token"):
        return None

    drive_folder_id = creds.get("drive_folder_id") or GDRIVE_FOLDER_ID
    access_token = get_fresh_access_token(creds["refresh_token"], creds.get("client_id"), creds.get("client_secret"))
    if not access_token:
        return None

    # Escape single quotes and backslashes for Drive search query
    safe_key = idempotency_key.replace("\\", "\\\\").replace("'", "\\'")
    q = f"'{drive_folder_id}' in parents and trashed = false and appProperties has {{ key='idempotency_key' and value='{safe_key}' }}"
    encoded_q = urllib.parse.quote(q)
    url = f"https://www.googleapis.com/drive/v3/files?q={encoded_q}&fields=files(id,name,webViewLink,appProperties)&pageSize=1"

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = data.get("files", [])
            if files and len(files) > 0:
                match = files[0]
                file_id = match.get("id")
                web_link = match.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
                return {
                    "file_id": file_id,
                    "name": match.get("name"),
                    "drive_url": web_link,
                    "webViewLink": web_link
                }
    except Exception as e:
        logger.warning(f"[GDrive] Idempotency search note: {e}")

    return None

def _create_resumable_upload_session(
    access_token: str,
    file_name: str,
    mime_type: str,
    file_size: int,
    folder_id: str,
    app_properties: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Initializes a resumable upload session on Google Drive API v3.
    Attaches appProperties for private idempotency metadata.
    Returns the session upload URI.
    """
    init_url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&fields=id,name,webViewLink"
    metadata = {
        "name": file_name,
        "parents": [folder_id]
    }
    if app_properties:
        metadata["appProperties"] = app_properties
    metadata_bytes = json.dumps(metadata).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": mime_type,
        "X-Upload-Content-Length": str(file_size)
    }

    req = urllib.request.Request(
        init_url,
        data=metadata_bytes,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            session_url = resp.headers.get("Location")
            if session_url:
                return session_url
            logger.error("[GDrive] Location header not returned for resumable upload session.")
    except urllib.error.HTTPError as he:
        logger.error(f"[GDrive] HTTP error creating upload session (Status {he.code}).")
    except Exception as e:
        logger.error(f"[GDrive] Error creating resumable upload session: {e}")

    return None

def _upload_chunks_resumable(session_url: str, file_bytes: bytes, mime_type: str) -> Optional[Dict[str, Any]]:
    """
    Uploads file bytes in chunks to the resumable session URL.
    Returns dict with file_id and webViewLink once completed.
    """
    total_size = len(file_bytes)
    offset = 0

    while offset < total_size:
        chunk_end = min(offset + _CHUNK_SIZE, total_size)
        chunk_data = file_bytes[offset:chunk_end]
        chunk_length = len(chunk_data)

        headers = {
            "Content-Type": mime_type,
            "Content-Range": f"bytes {offset}-{chunk_end - 1}/{total_size}",
            "Content-Length": str(chunk_length)
        }

        req = urllib.request.Request(
            session_url,
            data=chunk_data,
            headers=headers,
            method="PUT"
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                # 200 or 201 indicates upload is complete
                if resp.status in (200, 201):
                    res_body = json.loads(resp.read().decode("utf-8"))
                    file_id = res_body.get("id")
                    web_link = res_body.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
                    return {
                        "file_id": file_id,
                        "webViewLink": web_link
                    }
        except urllib.error.HTTPError as he:
            # 308 Resume Incomplete is expected until the final chunk is uploaded
            if he.code == 308:
                range_header = he.headers.get("Range")
                if range_header and "-" in range_header:
                    try:
                        bytes_received = int(range_header.split("-")[1])
                        offset = bytes_received + 1
                    except Exception:
                        offset = chunk_end
                else:
                    offset = chunk_end
                continue
            else:
                logger.error(f"[GDrive] Resumable chunk upload failed with HTTP status {he.code}.")
                return None
        except Exception as e:
            logger.error(f"[GDrive] Resumable upload chunk transmission error: {e}")
            return None

    return None

def upload_file_to_gdrive(
    file_bytes: bytes,
    file_name: str,
    mime_type: str = "video/mp4",
    idempotency_key: Optional[str] = None,
    video_hash: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Uploads a video directly to Google Drive API v3 using configured Google Drive credentials.
    First checks if a file with the given idempotency_key already exists in the folder;
    if so, reuses and returns that file's info without re-uploading.
    Attaches appProperties for idempotency tracking.
    Returns:
    {
        "file_id": file_id,
        "filename": file_name,
        "webViewLink": drive_file_url
    }
    """
    if not file_bytes:
        logger.error("[GDrive] Cannot upload empty file bytes.")
        return None

    # 1. Search Google Drive folder for an existing file with the same idempotency_key
    if idempotency_key:
        existing_drive = find_file_by_idempotency_key(idempotency_key)
        if existing_drive:
            logger.info(f"[GDrive] Idempotent match found in Drive folder: {existing_drive['webViewLink']} (File ID: {existing_drive['file_id']})")
            return {
                "file_id": existing_drive["file_id"],
                "filename": file_name,
                "webViewLink": existing_drive["webViewLink"]
            }

    # 2. Retrieve credentials
    creds = get_google_drive_credentials()
    if not creds or not creds.get("refresh_token"):
        logger.warning("[GDrive] No Google Drive credentials / refresh_token found.")
        return None

    refresh_token = creds["refresh_token"]
    drive_folder_id = creds.get("drive_folder_id") or GDRIVE_FOLDER_ID

    # 3. Exchange refresh_token for a fresh access token
    access_token = get_fresh_access_token(refresh_token, creds.get("client_id"), creds.get("client_secret"))
    if not access_token:
        logger.error("[GDrive] Failed to obtain access token.")
        return None

    # 4. Prepare appProperties for metadata
    app_props = {}
    if idempotency_key:
        app_props["idempotency_key"] = idempotency_key
    if video_hash:
        app_props["video_hash"] = video_hash

    # 5. Create resumable upload session on Google Drive API v3
    session_url = _create_resumable_upload_session(
        access_token=access_token,
        file_name=file_name,
        mime_type=mime_type,
        file_size=len(file_bytes),
        folder_id=drive_folder_id,
        app_properties=app_props if app_props else None
    )

    if not session_url:
        logger.error("[GDrive] Failed to initiate Google Drive resumable upload session.")
        return None

    # 6. Upload file in chunks
    result = _upload_chunks_resumable(session_url, file_bytes, mime_type)
    if not result or not result.get("file_id"):
        logger.error(f"[GDrive] Failed to upload {file_name} to Google Drive folder {drive_folder_id}.")
        return None

    file_id = result["file_id"]
    drive_file_url = result.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
    logger.info(f"[GDrive] Successfully backed up video to Google Drive: {drive_file_url}")
    return {
        "file_id": file_id,
        "filename": file_name,
        "webViewLink": drive_file_url
    }
