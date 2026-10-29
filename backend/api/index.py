import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if os.getenv("VERCEL") or not os.access(backend_dir, os.W_OK):
    os.environ.setdefault("HOTFIX_KEYS_DIR", "/tmp/keys")
    tmp_db = Path("/tmp/hotfix_mvp.db")
    seed_db = backend_dir / "hotfix_mvp.db"
    if not tmp_db.exists() and seed_db.exists():
        try:
            import shutil
            tmp_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(seed_db, tmp_db)
            os.environ["HOTFIX_DB_PATH"] = str(tmp_db)
        except Exception:
            pass

from app.main import create_application

app = create_application()
