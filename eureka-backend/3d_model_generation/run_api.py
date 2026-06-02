from __future__ import annotations

from pathlib import Path
import sys

import uvicorn

from config import settings


sys.path.insert(0, str(Path(__file__).resolve().parent))
from api import app


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False,
    )
