import sys
from pathlib import Path

# Robust sys.path configuration for Vercel Serverless environment
root_dir = Path(__file__).resolve().parent.parent
candidates = [
    root_dir,
    root_dir / "backend",
    root_dir / "mindscape",
    root_dir / "mindscape" / "backend"
]
for p in candidates:
    if p.exists() and str(p) not in sys.path:
        sys.path.insert(0, str(p))

try:
    from backend.main import app
except ModuleNotFoundError:
    import main as app_module
    app = app_module.app
