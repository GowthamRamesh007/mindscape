-- ==========================================================
-- MINDSCAPE — Row Level Security (RLS) & Storage Policies
-- ==========================================================

CREATE OR REPLACE FUNCTION public.is_admin(user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = user_id AND is_admin = TRUE
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Enable RLS
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.judges_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.competition_settings ENABLE ROW LEVEL SECURITY;

-- 1. Profiles
DROP POLICY IF EXISTS "Public profiles read for admins or self" ON public.profiles;
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;

CREATE POLICY "Users can view own profile"
    ON public.profiles FOR SELECT
    USING (auth.uid() = id OR public.is_admin(auth.uid()));

CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- 2. Teams (Allows submission creation & admin reading)
DROP POLICY IF EXISTS "Allow team insert" ON public.teams;
DROP POLICY IF EXISTS "Allow team view" ON public.teams;

CREATE POLICY "Allow team insert"
    ON public.teams FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow team view"
    ON public.teams FOR SELECT
    USING (true);

-- 3. Submissions
DROP POLICY IF EXISTS "Allow submission insert" ON public.submissions;
DROP POLICY IF EXISTS "Allow submission view" ON public.submissions;
DROP POLICY IF EXISTS "Admins can update submissions" ON public.submissions;

CREATE POLICY "Allow submission insert"
    ON public.submissions FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow submission view"
    ON public.submissions FOR SELECT
    USING (true);

CREATE POLICY "Admins can update submissions"
    ON public.submissions FOR UPDATE
    USING (public.is_admin(auth.uid()));

-- 4. Consent Records
DROP POLICY IF EXISTS "Allow consent insert" ON public.consent_records;
DROP POLICY IF EXISTS "Allow consent view" ON public.consent_records;

CREATE POLICY "Allow consent insert"
    ON public.consent_records FOR INSERT
    WITH CHECK (true);

CREATE POLICY "Allow consent view"
    ON public.consent_records FOR SELECT
    USING (true);

-- 5. Judges Scores
DROP POLICY IF EXISTS "Admins manage scores" ON public.judges_scores;
DROP POLICY IF EXISTS "Public read scores if published" ON public.judges_scores;

CREATE POLICY "Admins manage scores"
    ON public.judges_scores FOR ALL
    USING (public.is_admin(auth.uid()));

-- 6. Competition Settings
DROP POLICY IF EXISTS "Anyone can view competition settings" ON public.competition_settings;
DROP POLICY IF EXISTS "Admins can update competition settings" ON public.competition_settings;

CREATE POLICY "Anyone can view competition settings"
    ON public.competition_settings FOR SELECT
    USING (true);

CREATE POLICY "Admins can update competition settings"
    ON public.competition_settings FOR ALL
    USING (public.is_admin(auth.uid()));

-- ==========================================================
-- STORAGE BUCKET & POLICIES (Bucket: mindscape-reels)
-- ==========================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'mindscape-reels',
    'mindscape-reels',
    true, -- Allows direct playback and preview
    104857600, -- 100MB limit
    ARRAY['video/mp4', 'video/quicktime', 'video/x-m4v']
)
ON CONFLICT (id) DO UPDATE
SET public = true,
    file_size_limit = 104857600,
    allowed_mime_types = ARRAY['video/mp4', 'video/quicktime', 'video/x-m4v'];

DROP POLICY IF EXISTS "Allow public reel uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow public reel access" ON storage.objects;

CREATE POLICY "Allow public reel uploads"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id = 'mindscape-reels');

CREATE POLICY "Allow public reel access"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'mindscape-reels');
