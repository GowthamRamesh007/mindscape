import os
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

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_supabase_admin_client: Optional[Client] = None
_supabase_anon_client: Optional[Client] = None

def get_supabase_admin() -> Optional[Client]:
    """Returns the administrative Supabase client using the Service Role Key."""
    global _supabase_admin_client
    if _supabase_admin_client is None and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
        try:
            _supabase_admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        except Exception as e:
            print(f"Warning: Could not initialize Supabase Admin client: {e}")
            return None
    return _supabase_admin_client

def get_supabase_anon() -> Optional[Client]:
    """Returns the public anonymous Supabase client."""
    global _supabase_anon_client
    if _supabase_anon_client is None and SUPABASE_URL and SUPABASE_ANON_KEY:
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
