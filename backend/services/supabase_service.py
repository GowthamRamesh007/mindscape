import os
import json
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Robust dotenv loading across project root, .env folder, and backend
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent.parent
for _env_path in [
    _project_root / ".env",
    _project_root / ".env" / ".env",
    _project_root / ".env" / ".env.local",
    _project_root / ".env" / ".env.production",
    _project_root / "backend" / ".env",
    Path.cwd() / ".env"
]:
    if _env_path.is_file():
        load_dotenv(_env_path)
load_dotenv()

CONFIG_FILE = _project_root / "data" / "supabase_config.json"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

def load_persisted_config():
    global SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
    if CONFIG_FILE.is_file():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("supabase_url"):
                    SUPABASE_URL = data["supabase_url"].strip()
                if data.get("supabase_anon_key"):
                    SUPABASE_ANON_KEY = data["supabase_anon_key"].strip()
                if data.get("supabase_service_role_key"):
                    SUPABASE_SERVICE_ROLE_KEY = data["supabase_service_role_key"].strip()
        except Exception as e:
            print(f"Error loading persisted Supabase config: {e}")

load_persisted_config()

def update_supabase_credentials(url: str, anon_key: str, service_role_key: Optional[str] = None, bucket: Optional[str] = None):
    global SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
    global _supabase_admin_client, _supabase_anon_client

    SUPABASE_URL = url.strip()
    SUPABASE_ANON_KEY = anon_key.strip()
    if service_role_key:
        SUPABASE_SERVICE_ROLE_KEY = service_role_key.strip()

    os.environ["SUPABASE_URL"] = SUPABASE_URL
    os.environ["SUPABASE_ANON_KEY"] = SUPABASE_ANON_KEY
    if service_role_key:
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = SUPABASE_SERVICE_ROLE_KEY

    _supabase_admin_client = None
    _supabase_anon_client = None

    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "supabase_url": SUPABASE_URL,
        "supabase_anon_key": SUPABASE_ANON_KEY,
        "storage_bucket": bucket or "mindscape-reels"
    }
    if SUPABASE_SERVICE_ROLE_KEY and "dummy" not in SUPABASE_SERVICE_ROLE_KEY:
        payload["supabase_service_role_key"] = SUPABASE_SERVICE_ROLE_KEY

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Also update backend/.env if it exists
    env_file = _project_root / "backend" / ".env"
    if env_file.is_file():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            content = re.sub(r'SUPABASE_URL=.*', f'SUPABASE_URL={SUPABASE_URL}', content)
            content = re.sub(r'SUPABASE_ANON_KEY=.*', f'SUPABASE_ANON_KEY={SUPABASE_ANON_KEY}', content)
            if service_role_key and "dummy" not in service_role_key:
                content = re.sub(r'SUPABASE_SERVICE_ROLE_KEY=.*', f'SUPABASE_SERVICE_ROLE_KEY={SUPABASE_SERVICE_ROLE_KEY}', content)
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"Note updating backend/.env: {e}")

    # Proactively ensure storage bucket exists
    ensure_storage_bucket(bucket or "mindscape-reels")

def is_valid_supabase_config() -> bool:
    """Checks if valid non-placeholder Supabase credentials are configured."""
    return bool(
        SUPABASE_URL 
        and "your-project-id" not in SUPABASE_URL 
        and SUPABASE_URL.startswith("https://")
    )

_supabase_admin_client: Optional[Client] = None
_supabase_anon_client: Optional[Client] = None

def ensure_storage_bucket(bucket: str = "mindscape-reels") -> bool:
    """Ensures the storage bucket exists in Supabase and is public."""
    client = get_supabase_admin() or get_supabase_anon()
    if not client:
        return False
    try:
        # Check if bucket exists
        buckets = client.storage.list_buckets()
        existing = [b.name for b in buckets if hasattr(b, 'name')]
        if bucket not in existing:
            admin = get_supabase_admin()
            if admin:
                admin.storage.create_bucket(bucket, options={"public": True})
                print(f"[Supabase] Created public storage bucket: {bucket}")
                return True
        return True
    except Exception as e:
        print(f"[Supabase] Storage bucket check note: {e}")
        return False

def upload_file_to_supabase_storage(file_bytes: bytes, file_name: str, content_type: str = "video/mp4", bucket: str = "mindscape-reels") -> Optional[str]:
    """Uploads video file binary to Supabase Storage bucket and returns the public CDN URL."""
    client = get_supabase_admin() or get_supabase_anon()
    if not client:
        return None

    storage_path = f"reels/{file_name}"
    candidate_buckets = [bucket, "mindscape-reels", "reels", "submissions", "videos", "public"]
    seen = set()
    unique_buckets = [b for b in candidate_buckets if not (b in seen or seen.add(b))]

    for b in unique_buckets:
        try:
            client.storage.from_(b).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            # Fetch public URL
            pub_res = client.storage.from_(b).get_public_url(storage_path)
            if pub_res:
                print(f"[Supabase Storage] Uploaded to bucket '{b}': {pub_res}")
                return pub_res
        except Exception as e:
            err_str = str(e).lower()
            if "bucket not found" in err_str:
                admin = get_supabase_admin()
                if admin:
                    try:
                        admin.storage.create_bucket(b, options={"public": True})
                        client.storage.from_(b).upload(
                            path=storage_path,
                            file=file_bytes,
                            file_options={"content-type": content_type, "upsert": "true"}
                        )
                        pub_res = client.storage.from_(b).get_public_url(storage_path)
                        if pub_res:
                            return pub_res
                    except Exception:
                        pass
            continue
    return None

def get_supabase_admin() -> Optional[Client]:
    """Returns the administrative Supabase client using the Service Role Key."""
    global _supabase_admin_client
    if not is_valid_supabase_config() or not SUPABASE_SERVICE_ROLE_KEY or "dummy" in SUPABASE_SERVICE_ROLE_KEY:
        return None
    if _supabase_admin_client is None:
        try:
            _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase Admin client: {e}")
            return None
    return _supabase_admin_client

def get_supabase_anon() -> Optional[Client]:
    """Returns the public anonymous Supabase client."""
    global _supabase_anon_client
    if not is_valid_supabase_config() or not SUPABASE_ANON_KEY or "dummy" in SUPABASE_ANON_KEY:
        return None
    if _supabase_anon_client is None:
        try:
            _supabase_anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase Anon client: {e}")
            return None
    return _supabase_anon_client

def verify_jwt_token(auth_header: Optional[str]) -> Optional[dict]:
    """Extracts and verifies JWT token from Authorization header using Supabase Auth."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    client = get_supabase_admin() or get_supabase_anon()
    if not client:
        return None
    try:
        user_response = client.auth.get_user(token)
        if user_response and user_response.user:
            return {
                "id": user_response.user.id,
                "email": user_response.user.email,
                "user_metadata": user_response.user.user_metadata
            }
    except Exception as e:
        print(f"Token verification error: {e}")
    return None

def verify_is_admin(user_id: str) -> bool:
    """Verifies if the given user has is_admin = true in profiles table."""
    client = get_supabase_admin()
    if not client:
        return False
    try:
        res = client.table("profiles").select("is_admin").eq("id", user_id).single().execute()
        if res.data:
            return bool(res.data.get("is_admin", False))
    except Exception as e:
        print(f"Admin verification error: {e}")
    return False
