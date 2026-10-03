from fastapi import APIRouter

try:
    from backend.services.deadline_service import get_competition_deadline_status
    from backend.services.supabase_service import get_supabase_admin, get_supabase_anon
except ModuleNotFoundError:
    from services.deadline_service import get_competition_deadline_status
    from services.supabase_service import get_supabase_admin, get_supabase_anon

router = APIRouter(prefix="/api/competition", tags=["Competition"])

@router.get("/status")
def get_status():
    """Returns official deadline status and current IST timestamp."""
    deadline_status = get_competition_deadline_status()

    # Attempt to fetch dynamic status from Supabase if configured
    supabase = get_supabase_admin() or get_supabase_anon()
    if supabase:
        try:
            res = supabase.table("competition_settings").select("*").eq("id", 1).single().execute()
            if res.data:
                deadline_status["settings"] = res.data
        except Exception:
            pass

    return deadline_status
