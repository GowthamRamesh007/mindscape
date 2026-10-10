from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List

try:
    from backend.models.schemas import TeamRegisterRequest, TeamValidationResponse
    from backend.services.deadline_service import is_registration_open
    from backend.services.supabase_service import get_supabase_admin, verify_jwt_token
except ModuleNotFoundError:
    from models.schemas import TeamRegisterRequest, TeamValidationResponse
    from services.deadline_service import is_registration_open
    from services.supabase_service import get_supabase_admin, verify_jwt_token

router = APIRouter(prefix="/api/teams", tags=["Teams"])

@router.post("/validate", response_model=TeamValidationResponse)
def validate_team_data(payload: TeamRegisterRequest):
    """Validates member counts, age rules, and duplicate emails locally."""
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Check Deadline
    if not is_registration_open():
        errors.append("Team registration has closed (Deadline was 7 October 2026).")

    # 2. Check Team Member Counts (2 to 5)
    member_count = len(payload.members)
    if member_count < 2:
        errors.append("A team must have at least 2 members.")
    elif member_count > 5:
        errors.append("A team cannot have more than 5 members.")

    # 3. Check Age and Duplicate Emails inside team
    seen_emails = set()
    for idx, m in enumerate(payload.members):
        if m.age < 18:
            errors.append(f"Member {idx + 1} ({m.full_name}) is under 18 years old. All participants must be 18 or above.")
        
        email_clean = m.email.strip().lower()
        if email_clean in seen_emails:
            errors.append(f"Duplicate email '{m.email}' found inside team members list.")
        seen_emails.add(email_clean)

    return TeamValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

@router.post("/register")
def register_team(payload: TeamRegisterRequest, authorization: Optional[str] = Header(None)):
    """Registers a team and its members into Supabase with server-side validation."""
    user = verify_jwt_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to register a team.")

    if not is_registration_open():
        raise HTTPException(status_code=400, detail="Team registration deadline has passed.")

    if len(payload.members) < 2 or len(payload.members) > 5:
        raise HTTPException(status_code=400, detail="Team must have between 2 and 5 members.")

    supabase = get_supabase_admin()
    if not supabase:
        raise HTTPException(status_code=500, detail="Database service not configured.")

    try:
        # Check if representative already has a team
        existing_rep = supabase.table("teams").select("id").eq("representative_id", user["id"]).execute()
        if existing_rep.data and len(existing_rep.data) > 0:
            raise HTTPException(status_code=400, detail="You have already registered a team as a representative.")

        # Check if team name already exists
        existing_name = supabase.table("teams").select("id").eq("team_name", payload.team_name.strip()).execute()
        if existing_name.data and len(existing_name.data) > 0:
            raise HTTPException(status_code=400, detail="Team name is already taken. Please choose another name.")

        # Check if any member email is already registered in any team
        member_emails = [m.email.strip().lower() for m in payload.members]
        for email in member_emails:
            existing_member = supabase.table("team_members").select("id, team_id").eq("email", email).execute()
            if existing_member.data and len(existing_member.data) > 0:
                raise HTTPException(status_code=400, detail=f"Member email '{email}' is already enrolled in another team.")

        # Insert Team
        team_res = supabase.table("teams").insert({
            "team_name": payload.team_name.strip(),
            "representative_id": user["id"],
            "institution": payload.institution.strip(),
            "city": payload.city.strip(),
            "status": "registered"
        }).execute()

        if not team_res.data:
            raise HTTPException(status_code=500, detail="Failed to create team record.")

        team_id = team_res.data[0]["id"]

        # Insert Team Members
        members_data = []
        for idx, m in enumerate(payload.members):
            members_data.append({
                "team_id": team_id,
                "user_id": user["id"] if idx == 0 else None,
                "full_name": m.full_name.strip(),
                "email": m.email.strip().lower(),
                "phone": m.phone.strip(),
                "age": m.age,
                "institution": m.institution.strip(),
                "role": m.role.strip() or ("Team Leader" if idx == 0 else "Member")
            })

        supabase.table("team_members").insert(members_data).execute()

        return {
            "success": True,
            "message": "Team registered successfully.",
            "team": team_res.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@router.get("/registered")
def get_registered_teams():
    """Returns list of registered teams directly from Google Form response sheet."""
    try:
        from backend.services.google_sheets_service import fetch_registered_teams_from_sheet
    except ModuleNotFoundError:
        from services.google_sheets_service import fetch_registered_teams_from_sheet
    teams = fetch_registered_teams_from_sheet()
    return {"teams": teams, "count": len(teams)}

