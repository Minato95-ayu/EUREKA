from __future__ import annotations

from pathlib import Path
import sys

import uvicorn


sys.path.insert(0, str(Path(__file__).resolve().parent))
from api import app


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8093,
        reload=False,
    )
