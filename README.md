# MINDSCAPE
### Mental Health Awareness Through Digital Creativity

Mindscape is a digital platform developed for a mobile phone addiction awareness reel-making competition. The initiative encourages participants to communicate mental health awareness, digital well-being, empathy, and responsible smartphone usage through creative video content.

The platform provides a centralized space for event information, participant registration, reel submissions, and competition-related updates.

---

## Technology Stack

<p align="left">
  <img src="https://img.shields.io/badge/Frontend-HTML5%20%7C%20CSS3%20%7C%20JavaScript-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Backend-Python%20%7C%20FastAPI-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/Database-Supabase-3ECF8E?style=flat-square" />
  <img src="https://img.shields.io/badge/Storage-Google%20Drive-4285F4?style=flat-square" />
  <img src="https://img.shields.io/badge/Deployment-Vercel-black?style=flat-square" />
</p>

## Project Overview

Mindscape was developed as a web-based event management and submission platform with a focus on accessibility, responsive design, and reliable video handling.

The application brings together the major activities of the competition through a single interface.

### Key Features

**1. Landing Page**
- Event introduction and competition information.
- Visual presentation of the initiative.
- Participating institutions and club showcase.
- Important announcements and submission information.

**2. About Section**
- Background and objectives of Mindscape.
- Mental health awareness and digital well-being information.
- Event and organising institution details.

**3. Participant Registration**
- Integration with the event registration form.
- Centralized participant registration workflow.

**4. Reel Submission System**
- Video submission through the website.
- File format and file-size validation.
- Direct browser-to-Supabase video uploads.
- Google Drive backup through resumable uploads.
- Submission metadata storage and verification.
- Upload progress and submission status handling.

**5. FAQ and Prize Pool**
- Frequently asked questions for participants.
- Presentation of competition prizes and winner information.

**6. Organiser Portal**
- Dedicated interface for organisers.
- Access to submission-related information.

---

## System Architecture

Mindscape uses a combination of cloud services to handle participant submissions and video storage.

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | HTML, CSS, JavaScript | User interface and participant interactions |
| Backend | Python, FastAPI | API handling, validation and upload coordination |
| Database | Supabase | Submission metadata and records |
| Primary Video Storage | Supabase Storage | Submitted reel files |
| Backup Storage | Google Drive API | Secondary video storage |
| Hosting | Vercel | Website and backend deployment |

### Video Upload Workflow

The submission system uses a direct-to-cloud upload approach to avoid transferring large video files through the hosting platform.

1. The frontend requests upload authorization from the FastAPI backend.
2. The backend validates participant registration and prepares the upload sessions.
3. The browser uploads the video directly to Supabase Storage.
4. Google Drive backup is handled through sequential 4 MB chunks relayed by the backend to a Google Drive resumable upload session.
5. The backend finalizes the submission and stores the corresponding metadata.
6. The uploaded files and submission records are verified.

This architecture reduces the amount of binary data passing through Vercel Functions and supports larger video submissions within the configured limits.

---

## Backend Implementation

The backend is developed using Python and FastAPI.

Its responsibilities include:

- Participant and registration validation.
- Upload session preparation.
- Supabase signed upload URL generation.
- Google Drive OAuth 2.0 integration.
- Google Drive resumable upload coordination.
- Chunk-based upload relay.
- Submission finalization.
- Database record management.

### Cloud Integration

**Supabase**
- Database integration for submission records.
- Storage bucket management.
- Signed upload URL generation.
- Submission metadata verification.

**Google Drive**
- OAuth 2.0 authorization.
- Refresh-token-based access token generation.
- Resumable video uploads.
- Secondary backup storage.

---

## Deployment

The application is deployed using Vercel and connected to a GitHub repository for source-code management and deployment updates.

The project uses environment variables to manage sensitive credentials and service configurations.

External services are integrated through their respective APIs, keeping authentication credentials on the backend.

---

## Security and Reliability

- Sensitive API credentials are maintained through environment variables.
- Google OAuth credentials are handled server-side.
- Participant submissions undergo backend validation.
- Signed upload URLs are used for controlled Supabase uploads.
- Chunk-based Google Drive uploads help avoid large request-body limitations.
- Submission finalization maintains the relationship between uploaded files and database records.

---

## Project Objective

The primary objective of Mindscape is to combine digital creativity with mental health awareness through a functional web platform.

Beyond presenting event information, the project demonstrates the practical integration of frontend development, backend API design, cloud storage, database management, OAuth authentication, and deployment workflows.

---

## Author

**Gowtham Ramesh**

Project Developer

GitHub: [GowthamRamesh007](https://github.com/GowthamRamesh007)

---

*Mindscape — Encouraging awareness through creativity and responsible digital engagement.*
