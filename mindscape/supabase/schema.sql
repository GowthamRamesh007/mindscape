-- ==========================================================
-- MINDSCAPE — Reel Making Contest on Mobile Phone Addiction
-- Supabase PostgreSQL Schema Definition
-- ==========================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==========================================================
-- 1. PROFILES TABLE (Mirrors auth.users)
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    age INTEGER CHECK (age >= 18),
    institution TEXT,
    city TEXT,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_is_admin ON public.profiles(is_admin);

-- ==========================================================
-- 2. TEAMS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_name TEXT NOT NULL,
    representative_name TEXT NOT NULL,
    representative_email TEXT NOT NULL,
    representative_phone TEXT NOT NULL,
    representative_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    institution TEXT NOT NULL,
    city TEXT DEFAULT 'Chennai',
    status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('registered', 'submitted', 'locked', 'under_review', 'accepted', 'rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_status ON public.teams(status);
CREATE INDEX IF NOT EXISTS idx_teams_institution ON public.teams(institution);
CREATE INDEX IF NOT EXISTS idx_teams_rep_email ON public.teams(representative_email);

-- ==========================================================
-- 3. SUBMISSIONS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES public.teams(id) ON DELETE CASCADE,
    team_name TEXT NOT NULL,
    representative_name TEXT NOT NULL,
    representative_email TEXT NOT NULL,
    representative_phone TEXT NOT NULL,
    institution TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    language TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size BIGINT NOT NULL, -- in bytes
    duration NUMERIC(6, 2) NOT NULL, -- in seconds (25 to 45)
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    aspect_ratio TEXT NOT NULL DEFAULT '9:16',
    submission_status TEXT NOT NULL DEFAULT 'submitted' CHECK (submission_status IN ('uploaded', 'submitted', 'under_review', 'accepted', 'rejected')),
    reviewer_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_team ON public.submissions(team_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON public.submissions(submission_status);
CREATE INDEX IF NOT EXISTS idx_submissions_rep_email ON public.submissions(representative_email);

-- ==========================================================
-- 4. CONSENT RECORDS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL UNIQUE REFERENCES public.submissions(id) ON DELETE CASCADE,
    originality_confirmed BOOLEAN NOT NULL DEFAULT TRUE,
    participant_consent_confirmed BOOLEAN NOT NULL DEFAULT TRUE,
    copyright_confirmed BOOLEAN NOT NULL DEFAULT TRUE,
    rules_confirmed BOOLEAN NOT NULL DEFAULT TRUE,
    final_lock_confirmed BOOLEAN NOT NULL DEFAULT TRUE,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================
-- 5. JUDGES SCORES TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.judges_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES public.submissions(id) ON DELETE CASCADE,
    judge_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    judge_name TEXT DEFAULT 'Jury Member',
    relevance_score NUMERIC(4, 2) NOT NULL CHECK (relevance_score BETWEEN 0 AND 10),
    creativity_score NUMERIC(4, 2) NOT NULL CHECK (creativity_score BETWEEN 0 AND 10),
    impact_score NUMERIC(4, 2) NOT NULL CHECK (impact_score BETWEEN 0 AND 10),
    storytelling_score NUMERIC(4, 2) NOT NULL CHECK (storytelling_score BETWEEN 0 AND 10),
    execution_score NUMERIC(4, 2) NOT NULL CHECK (execution_score BETWEEN 0 AND 10),
    overall_score NUMERIC(5, 2) NOT NULL CHECK (overall_score BETWEEN 0 AND 60),
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_judges_scores_submission ON public.judges_scores(submission_id);

-- ==========================================================
-- 6. COMPETITION SETTINGS TABLE
-- ==========================================================
CREATE TABLE IF NOT EXISTS public.competition_settings (
    id INT PRIMARY KEY DEFAULT 1,
    google_form_url TEXT NOT NULL DEFAULT 'https://forms.gle/mindscape2026',
    registration_deadline TIMESTAMPTZ NOT NULL DEFAULT '2026-10-07 23:59:59+05:30',
    submission_deadline TIMESTAMPTZ NOT NULL DEFAULT '2026-11-08 23:59:59+05:30',
    is_registration_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_submission_active BOOLEAN NOT NULL DEFAULT TRUE,
    scores_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ==========================================================
-- 7. AUTOMATIC PROFILE CREATION TRIGGER
-- ==========================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, email, phone, age, institution, city, is_admin)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', 'Participant'),
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'phone', ''),
        COALESCE((NEW.raw_user_meta_data->>'age')::INTEGER, 18),
        COALESCE(NEW.raw_user_meta_data->>'institution', 'Not Specified'),
        COALESCE(NEW.raw_user_meta_data->>'city', 'Chennai'),
        COALESCE((NEW.raw_user_meta_data->>'is_admin')::BOOLEAN, FALSE)
    )
    ON CONFLICT (id) DO UPDATE
    SET full_name = EXCLUDED.full_name,
        updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Trigger for updating timestamp
CREATE OR REPLACE FUNCTION public.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_modtime BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
CREATE TRIGGER update_teams_modtime BEFORE UPDATE ON public.teams FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
CREATE TRIGGER update_submissions_modtime BEFORE UPDATE ON public.submissions FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
CREATE TRIGGER update_judges_scores_modtime BEFORE UPDATE ON public.judges_scores FOR EACH ROW EXECUTE FUNCTION public.update_timestamp();
