-- ==========================================================
-- MINDSCAPE — Seed Data & Admin Configuration Helper
-- ==========================================================

-- Initialize competition settings (Deadlines: 7 Oct 2026 & 8 Nov 2026 IST)
INSERT INTO public.competition_settings (
    id,
    registration_deadline,
    submission_deadline,
    is_registration_active,
    is_submission_active,
    scores_published
)
VALUES (
    1,
    '2026-10-07 23:59:59+05:30',
    '2026-11-08 23:59:59+05:30',
    true,
    true,
    false
)
ON CONFLICT (id) DO UPDATE
SET registration_deadline = EXCLUDED.registration_deadline,
    submission_deadline = EXCLUDED.submission_deadline;

-- Helper SQL command to grant admin role to any user:
-- Replace 'YOUR_ADMIN_EMAIL@domain.com' with the email address of your registered account.
-- UPDATE public.profiles SET is_admin = TRUE WHERE email = 'YOUR_ADMIN_EMAIL@domain.com';
