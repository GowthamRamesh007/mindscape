import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# Ensure import paths work regardless of whether started from mindscape or backend directory
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(current_file.parent) not in sys.path:
    sys.path.insert(0, str(current_file.parent))

try:
    from backend.routes.competition import router as competition_router
    from backend.routes.teams import router as teams_router
    from backend.routes.submissions import router as submissions_router
    from backend.routes.admin import router as admin_router
except ModuleNotFoundError:
    from routes.competition import router as competition_router
    from routes.teams import router as teams_router
    from routes.submissions import router as submissions_router
    from routes.admin import router as admin_router

load_dotenv()

app = FastAPI(
    title="MINDSCAPE Reel Contest API",
    description="Backend API for MINDSCAPE — Reel Making Contest on Mobile Phone Addiction",
    version="1.0.0"
)

# CORS Configuration with Vercel Service Binding support
# Reads bound FRONTEND_URL injected by Vercel Services
frontend_url = os.getenv("FRONTEND_URL", "").rstrip("/")
default_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "http://localhost:8000"
]

cors_origins_env = os.getenv("CORS_ORIGINS", "")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] if cors_origins_env else default_origins

if frontend_url and frontend_url not in origins:
    origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(competition_router)
app.include_router(teams_router)
app.include_router(submissions_router)
app.include_router(admin_router)

@app.get("/api/health")
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "MINDSCAPE Reel Contest API",
        "version": "1.0.0",
        "frontend_url": frontend_url or "internal"
    }

# Frontend paths
client_dir = os.path.join(project_root, "client")
client_public = os.path.join(client_dir, "public")
client_src = os.path.join(client_dir, "src")

# Mount public assets (fonts, media/logo, etc.)
candidates_media = [
    os.path.join(project_root, "media"),
    os.path.join(client_dir, "media"),
    os.path.join(client_public, "media")
]
media_dir = next((p for p in candidates_media if os.path.exists(p)), None)
if media_dir:
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

candidates_fonts = [
    os.path.join(project_root, "fonts"),
    os.path.join(client_dir, "fonts"),
    os.path.join(client_public, "fonts")
]
fonts_dir = next((p for p in candidates_fonts if os.path.exists(p)), None)
if fonts_dir:
    app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")

candidates_src = [
    os.path.join(project_root, "src"),
    client_src
]
src_dir = next((p for p in candidates_src if os.path.exists(p)), None)
if src_dir:
    app.mount("/src", StaticFiles(directory=src_dir), name="src")

# Serve dedicated authenticated portal
@app.get("/portal")
@app.get("/portal.html")
@app.get("/admin")
def serve_portal():
    candidates_portal = [
        os.path.join(project_root, "portal.html"),
        os.path.join(client_dir, "portal.html")
    ]
    portal_file = next((p for p in candidates_portal if os.path.exists(p)), None)
    if portal_file:
        return FileResponse(portal_file)
    return FileResponse(os.path.join(client_dir, "index.html"))

# Serve index.html at root
@app.get("/")
@app.get("/submit")
def serve_index():
    candidates_index = [
        os.path.join(project_root, "index.html"),
        os.path.join(client_dir, "index.html")
    ]
    index_file = next((p for p in candidates_index if os.path.exists(p)), None)
    if index_file:
        return FileResponse(index_file)
    return {"message": "MINDSCAPE Reel Contest API online"}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
