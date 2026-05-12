import os
from pathlib import Path
import sys

import uvicorn


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    os.environ.setdefault("MANUAL_RATING_SESSION_SECRET", "manual-rating-dev-secret")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(
        "backend.app.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        app_dir=str(root),
    )


if __name__ == "__main__":
    main()
