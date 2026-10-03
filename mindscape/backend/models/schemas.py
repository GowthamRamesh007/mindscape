from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class MemberSchema(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    age: int = Field(..., ge=18, description="Participant must be 18 years or older")
    institution: str = Field(..., min_length=2, max_length=150)
    role: str = Field(default="Member", max_length=50)

class TeamRegisterRequest(BaseModel):
    team_name: str = Field(..., min_length=2, max_length=120)
    institution: str = Field(..., min_length=2, max_length=150)
    city: str = Field(default="Chennai", min_length=2, max_length=100)
    members: List[MemberSchema] = Field(..., min_length=1, max_length=5)

class TeamValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []

class VideoVerificationRequest(BaseModel):
    file_name: str
    file_size: int
    duration: float = Field(..., ge=1.0)
    width: int
    height: int
    language: Optional[str] = "Tamil"

class VideoVerificationResponse(BaseModel):
    valid: bool
    duration_valid: bool
    resolution_valid: bool
    aspect_ratio_valid: bool
    aspect_ratio: str
    errors: List[str] = []
    warnings: List[str] = []

class DirectReelUploadRequest(BaseModel):
    team_name: str = Field(..., min_length=2, max_length=120)
    representative_name: Optional[str] = "Registered Team"
    representative_email: Optional[str] = "participant@mindscape.org"
    representative_phone: Optional[str] = "0000000000"
    institution: Optional[str] = "Registered Institution"
    city: Optional[str] = "Chennai"
    title: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = "Reel video submission for Mindscape 2026"
    language: str = Field(default="Tamil", max_length=50)
    file_path: str
    file_name: str
    file_size: int
    duration: float = Field(..., ge=20.0, le=50.0)
    width: int
    height: int
    aspect_ratio: str = "9:16"
    originality_confirmed: bool = True
    participant_consent_confirmed: bool = True
    copyright_confirmed: bool = True
    rules_confirmed: bool = True
    final_lock_confirmed: bool = True

class ScoreSubmissionRequest(BaseModel):
    relevance_score: float = Field(..., ge=0, le=10)
    creativity_score: float = Field(..., ge=0, le=10)
    impact_score: float = Field(..., ge=0, le=10)
    storytelling_score: float = Field(..., ge=0, le=10)
    execution_score: float = Field(..., ge=0, le=10)
    comments: Optional[str] = None

class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(submitted|under_review|accepted|rejected)$")
    reviewer_notes: Optional[str] = None

class CompetitionStatusResponse(BaseModel):
    current_time_ist: str
    registration_deadline: str
    submission_deadline: str
    is_registration_open: bool
    is_submission_open: bool
    days_to_registration_deadline: int
    days_to_submission_deadline: int
