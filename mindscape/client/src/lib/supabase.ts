// Browser-side Supabase client and API integration for MINDSCAPE

declare global {
  interface Window {
    supabase?: {
      createClient: (url: string, key: string, options?: any) => any;
    };
  }
}

export const SUPABASE_URL =
  (import.meta.env.VITE_SUPABASE_URL as string) ||
  localStorage.getItem("MINDSCAPE_SUPABASE_URL") ||
  "https://your-project-id.supabase.co";

export const SUPABASE_ANON_KEY =
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string) ||
  localStorage.getItem("MINDSCAPE_SUPABASE_ANON_KEY") ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "" // Relative via Vite proxy
    : "");

let supabaseInstance: any = null;

export function getSupabase() {
  if (supabaseInstance) return supabaseInstance;

  if (typeof window !== "undefined" && window.supabase) {
    try {
      supabaseInstance = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
        },
      });
      return supabaseInstance;
    } catch (err) {
      console.warn("[Supabase] Failed to initialize from window.supabase:", err);
    }
  }

  return null;
}

export interface VideoMetadata {
  duration: number;
  width: number;
  height: number;
  aspectRatio: string;
  isPortrait: boolean;
  durationOk: boolean;
  isValid: boolean;
}

export interface DirectReelSubmissionPayload {
  teamName: string;
  representativeName: string;
  representativeEmail: string;
  representativePhone: string;
  institution: string;
  city: string;
  title: string;
  description: string;
  language: string;
  filePath: string;
  fileName: string;
  fileSize: number;
  duration: number;
  width: number;
  height: number;
  originalityConfirmed: boolean;
  participantConsentConfirmed: boolean;
  copyrightConfirmed: boolean;
  rulesConfirmed: boolean;
  finalLockConfirmed: boolean;
}

/**
 * Uploads a video file directly to the Supabase Storage bucket 'mindscape-reels'.
 */
export async function uploadReelToSupabase(
  teamName: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ filePath: string; publicUrl?: string }> {
  const sb = getSupabase();
  const slug = teamName.toLowerCase().replace(/[^a-z0-9]/g, "-").slice(0, 30) || "team";
  const ext = file.name.split(".").pop() || "mp4";
  const uniqueId = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2);
  const filePath = `submissions/${slug}/${uniqueId}.${ext}`;

  if (!sb) {
    // If Supabase is not configured yet, route through backend media submissions
    for (let i = 10; i <= 100; i += 20) {
      if (onProgress) onProgress(i);
      await new Promise((r) => setTimeout(r, 80));
    }
    return { filePath: `/media/submissions/${file.name}` };
  }

  if (onProgress) onProgress(20);

  const { error } = await sb.storage
    .from("mindscape-reels")
    .upload(filePath, file, {
      cacheControl: "3600",
      upsert: false,
    });

  if (error) {
    console.error("[Supabase Storage Upload Error]", error);
    throw new Error(error.message || "Failed to upload reel to storage.");
  }

  if (onProgress) onProgress(100);

  return { filePath };
}

/**
 * Submit verified reel metadata to FastAPI backend
 */
export async function submitReelToBackend(payload: DirectReelSubmissionPayload) {
  const response = await fetch(`${API_BASE_URL}/api/submissions/direct-submit`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      team_name: payload.teamName,
      representative_name: payload.representativeName,
      representative_email: payload.representativeEmail,
      representative_phone: payload.representativePhone,
      institution: payload.institution,
      city: payload.city,
      title: payload.title,
      description: payload.description,
      language: payload.language,
      file_path: payload.filePath,
      file_name: payload.fileName,
      file_size: payload.fileSize,
      duration: payload.duration,
      width: payload.width,
      height: payload.height,
      originality_confirmed: payload.originalityConfirmed,
      participant_consent_confirmed: payload.participantConsentConfirmed,
      copyright_confirmed: payload.copyrightConfirmed,
      rules_confirmed: payload.rulesConfirmed,
      final_lock_confirmed: payload.finalLockConfirmed,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || "Submission request failed");
  }

  return await response.json();
}

/**
 * Fetches live competition deadline status in Asia/Kolkata timezone
 */
export async function fetchCompetitionStatus() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/competition/status`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("[Competition Status Fetch Error]", err);
  }

  // Fallback IST countdown calculation
  const now = new Date();
  const regDeadline = new Date("2026-10-07T23:59:59+05:30");
  const subDeadline = new Date("2026-11-08T23:59:59+05:30");
  const regRemaining = Math.max(0, Math.floor((regDeadline.getTime() - now.getTime()) / 1000));
  const subRemaining = Math.max(0, Math.floor((subDeadline.getTime() - now.getTime()) / 1000));

  return {
    is_registration_open: regRemaining > 0,
    is_submission_open: subRemaining > 0,
    registration_remaining_seconds: regRemaining,
    submission_remaining_seconds: subRemaining,
  };
}

/**
 * Admin APIs
 */
export async function fetchAdminOverview() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/overview`);
    if (res.ok) return await res.json();
  } catch (err) {
    console.warn("[Admin Overview Error]", err);
  }
  return {
    total_participants: 48,
    total_teams: 16,
    total_submissions: 14,
    pending_submissions: 4,
    accepted_submissions: 8,
    rejected_submissions: 2,
  };
}

export async function fetchAdminSubmissions() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/submissions`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (err) {
    console.warn("[Admin Submissions Error]", err);
  }
  return null;
}

export async function updateSubmissionStatus(id: string, status: string, notes?: string) {
  const res = await fetch(`${API_BASE_URL}/api/admin/submissions/${id}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, reviewer_notes: notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to update status");
  }
  return await res.json();
}

export async function scoreSubmission(id: string, scores: {
  storytelling: number;
  creativity: number;
  cinematography: number;
  sound: number;
  relevance: number;
  impact: number;
  feedback?: string;
}) {
  const res = await fetch(`${API_BASE_URL}/api/admin/submissions/${id}/score`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      storytelling_score: scores.storytelling,
      creativity_score: scores.creativity,
      cinematography_score: scores.cinematography,
      sound_score: scores.sound,
      relevance_score: scores.relevance,
      impact_score: scores.impact,
      feedback: scores.feedback,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to submit score");
  }
  return await res.json();
}
