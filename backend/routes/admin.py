from fastapi import APIRouter, HTTPException, Header, Query
from typing import Optional, List

try:
    from backend.models.schemas import ScoreSubmissionRequest, StatusUpdateRequest
    from backend.services.supabase_service import get_supabase_admin, get_supabase_anon, verify_jwt_token, verify_is_admin
except ModuleNotFoundError:
    from models.schemas import ScoreSubmissionRequest, StatusUpdateRequest
    from services.supabase_service import get_supabase_admin, get_supabase_anon, verify_jwt_token, verify_is_admin

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.get("/overview")
def get_admin_overview(authorization: Optional[str] = Header(None)):
    """Returns overview KPI metrics for the competition."""
    supabase = get_supabase_admin() or get_supabase_anon()
    if not supabase:
        return {
            "total_participants": 0,
            "total_teams": 0,
            "total_submissions": 0,
            "pending_submissions": 0,
            "accepted_submissions": 0,
            "rejected_submissions": 0
        }

    try:
        teams_res = supabase.table("teams").select("id", count="exact").execute()
        submissions_res = supabase.table("submissions").select("id, submission_status", count="exact").execute()

        total_teams = teams_res.count or 0
        total_submissions = submissions_res.count or 0

        pending_count = 0
        accepted_count = 0
        rejected_count = 0

        if submissions_res.data:
            for sub in submissions_res.data:
                status = sub.get("submission_status")
                if status in ["submitted", "under_review", "uploaded"]:
                    pending_count += 1
                elif status == "accepted":
                    accepted_count += 1
                elif status == "rejected":
                    rejected_count += 1

        return {
            "total_participants": total_teams * 3, # Average 3 members per team
            "total_teams": total_teams,
            "total_submissions": total_submissions,
            "pending_submissions": pending_count,
            "accepted_submissions": accepted_count,
            "rejected_submissions": rejected_count
        }
    except Exception as e:
        return {
            "total_participants": 0,
            "total_teams": 0,
            "total_submissions": 0,
            "pending_submissions": 0,
            "accepted_submissions": 0,
            "rejected_submissions": 0
        }

@router.get("/submissions")
def get_admin_submissions(
    status: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """Lists all reel submissions with team info, metadata, and scores."""
    supabase = get_supabase_admin() or get_supabase_anon()
    if not supabase:
        return {"submissions": [], "total": 0}

    try:
        query = supabase.table("submissions").select("*, judges_scores(*)")
        if status:
            query = query.eq("submission_status", status)
        if language:
            query = query.eq("language", language)
        res = query.order("submitted_at", desc=True).execute()

        submissions = res.data or []
        if search:
            search_lower = search.lower()
            submissions = [
                s for s in submissions
                if search_lower in s.get("title", "").lower()
                or search_lower in s.get("team_name", "").lower()
                or search_lower in s.get("institution", "").lower()
            ]

        return {"submissions": submissions, "total": len(submissions)}
    except Exception as e:
        return {"submissions": [], "total": 0}

@router.get("/submissions/{submission_id}/signed-url")
def get_signed_url(submission_id: str, authorization: Optional[str] = Header(None)):
    """Generates a signed URL or direct storage URL for playing the reel."""
    supabase = get_supabase_admin() or get_supabase_anon()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database service not configured.")

    try:
        sub = supabase.table("submissions").select("file_path").eq("id", submission_id).single().execute()
        if not sub.data:
            raise HTTPException(status_code=404, detail="Submission not found.")

        file_path = sub.data["file_path"]
        
        # Try signed URL
        try:
            signed_res = supabase.storage.from_("mindscape-reels").create_signed_url(file_path, 3600)
            if signed_res:
                url = signed_res.get("signedUrl") or signed_res.get("signedURL")
                if url:
                    return {"signed_url": url}
        except Exception:
            pass

        # Public URL fallback
        public_url = supabase.storage.from_("mindscape-reels").get_public_url(file_path)
        return {"signed_url": public_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Signed URL error: {str(e)}")

@router.post("/submissions/{submission_id}/review")
def review_submission(submission_id: str, payload: StatusUpdateRequest, authorization: Optional[str] = Header(None)):
    """Updates submission status (accepted / rejected / under_review) and reviewer notes."""
    supabase = get_supabase_admin() or get_supabase_anon()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database service not configured.")

    try:
        update_data = {
            "submission_status": payload.status,
            "reviewer_notes": payload.reviewer_notes,
            "reviewed_at": "now()"
        }
        res = supabase.table("submissions").update(update_data).eq("id", submission_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Submission not found.")

        return {"success": True, "message": f"Submission status updated to {payload.status}."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review error: {str(e)}")

@router.post("/submissions/{submission_id}/score")
def score_submission(submission_id: str, payload: ScoreSubmissionRequest, authorization: Optional[str] = Header(None)):
    """Records judge scores according to the official judging rubric (out of 60)."""
    supabase = get_supabase_admin() or get_supabase_anon()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database service not configured.")

    try:
        overall = round(
            payload.relevance_score +
            payload.creativity_score +
            payload.impact_score +
            payload.storytelling_score +
            payload.execution_score,
            2
        )

        score_data = {
            "submission_id": submission_id,
            "relevance_score": payload.relevance_score,
            "creativity_score": payload.creativity_score,
            "impact_score": payload.impact_score,
            "storytelling_score": payload.storytelling_score,
            "execution_score": payload.execution_score,
            "overall_score": overall,
            "comments": payload.comments
        }

        res = supabase.table("judges_scores").insert(score_data).execute()
        return {"success": True, "score": res.data[0] if res.data else score_data, "total_score": overall}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring error: {str(e)}")
