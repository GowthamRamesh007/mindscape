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

@app.get("/api")
@app.get("/api/")
@app.get("/api/health")
@app.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "MINDSCAPE Reel Contest API",
        "version": "1.0.0",
        "frontend_url": frontend_url or "internal"
    }

@app.get("/api/config/supabase")
def get_supabase_config():
    """Returns the public Supabase configuration (URL and Anon Key only) for client-side direct uploads."""
    config_file = Path(project_root) / "data" / "supabase_config.json"
    supa_url = ""
    supa_anon = ""
    bucket = "mindscape-reels"
    if config_file.is_file():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                supa_url = data.get("supabase_url", "").strip()
                supa_anon = data.get("supabase_anon_key", "").strip()
                bucket = data.get("storage_bucket", "mindscape-reels").strip() or "mindscape-reels"
        except Exception:
            pass

    if not supa_url:
        supa_url = os.getenv("SUPABASE_URL", "").strip()
    if not supa_anon:
        supa_anon = os.getenv("SUPABASE_ANON_KEY", "").strip()

    is_valid = bool(supa_url and "your-project-id" not in supa_url and supa_url.startswith("https://"))
    return {
        "configured": is_valid and bool(supa_anon and "dummy" not in supa_anon),
        "supabase_url": supa_url if is_valid else "",
        "supabase_anon_key": supa_anon if (is_valid and "dummy" not in supa_anon) else "",
        "storage_bucket": bucket
    }

@app.post("/api/config/supabase")
def save_supabase_config(payload: dict):
    """Saves and activates user's Supabase credentials for both frontend direct uploads and backend storage."""
    url = (payload.get("supabase_url") or "").strip()
    anon_key = (payload.get("supabase_anon_key") or "").strip()
    bucket = (payload.get("storage_bucket") or "mindscape-reels").strip() or "mindscape-reels"
    service_role_key = (payload.get("supabase_service_role_key") or "").strip()

    if not url or not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid Supabase URL. Must start with https://")
    if not anon_key or len(anon_key) < 20:
        raise HTTPException(status_code=400, detail="Invalid Supabase Anon Key.")

    from backend.services.supabase_service import update_supabase_credentials
    update_supabase_credentials(url, anon_key, service_role_key=service_role_key if service_role_key else None, bucket=bucket)

    return {
        "success": True,
        "message": "Supabase credentials updated and activated successfully!",
        "configured": True,
        "supabase_url": url,
        "storage_bucket": bucket
    }

# Frontend paths
client_dir = os.path.join(project_root, "client")
client_public = os.path.join(client_dir, "public")
client_src = os.path.join(client_dir, "src")

# Mount public assets (fonts, media/logo, etc.)
candidates_media = [
    os.path.join(project_root, "media"),
    os.path.join(client_dir, "media"),
    os.path.join(client_public, "media"),
    os.path.join(project_root, "mindscape", "media")
]
media_dir = next((p for p in candidates_media if os.path.exists(p)), None)
if media_dir:
    app.mount("/media", StaticFiles(directory=media_dir), name="media")

candidates_fonts = [
    os.path.join(project_root, "fonts"),
    os.path.join(client_dir, "fonts"),
    os.path.join(client_public, "fonts"),
    os.path.join(project_root, "mindscape", "fonts")
]
fonts_dir = next((p for p in candidates_fonts if os.path.exists(p)), None)
if fonts_dir:
    app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")

candidates_src = [
    os.path.join(project_root, "src"),
    client_src,
    os.path.join(project_root, "mindscape", "src")
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
        os.path.join(str(current_file.parent), "portal.html"),
        os.path.join(str(project_root), "portal.html"),
        os.path.join(str(client_dir), "portal.html"),
        os.path.join(str(project_root), "mindscape", "portal.html")
    ]
    portal_file = next((p for p in candidates_portal if os.path.exists(p)), None)
    if portal_file:
        return FileResponse(portal_file)
    return FileResponse(os.path.join(str(client_dir), "portal.html"))

# Serve index.html for frontend routes
@app.get("/")
@app.get("/submit")
@app.get("/about")
@app.get("/register")
@app.get("/prize-pool")
@app.get("/prizes")
@app.get("/faq")
def serve_index():
    candidates_index = [
        os.path.join(str(current_file.parent), "index.html"),
        os.path.join(str(project_root), "index.html"),
        os.path.join(str(client_dir), "index.html"),
        os.path.join(str(project_root), "mindscape", "index.html")
    ]
    index_file = next((p for p in candidates_index if os.path.exists(p)), None)
    if index_file:
        return FileResponse(index_file)
    return FileResponse(os.path.join(str(client_dir), "index.html"))

# Serve 404 error page for unmatched frontend routes
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        if request.url.path.startswith("/api"):
            return JSONResponse(status_code=404, content={"detail": exc.detail or "Not Found"})
        candidates_404 = [
            os.path.join(str(project_root), "404.html"),
            os.path.join(str(current_file.parent), "404.html"),
            os.path.join(str(client_dir), "404.html"),
            os.path.join(str(project_root), "mindscape", "404.html")
        ]
        page_404 = next((p for p in candidates_404 if os.path.exists(p)), None)
        if page_404:
            return FileResponse(page_404, status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
