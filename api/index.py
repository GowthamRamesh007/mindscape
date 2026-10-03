import sys
from pathlib import Path

# Add project root and mindscape/backend directory to sys.path
root_dir = Path(__file__).resolve().parent.parent
mindscape_dir = root_dir / "mindscape"
backend_dir = mindscape_dir / "backend"
for p in [str(root_dir), str(mindscape_dir), str(backend_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from backend.main import app
