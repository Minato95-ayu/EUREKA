from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    service_name: str
    host: str
    port: int
    output_root: Path
    api_key: str | None
    max_query_length: int


def load_settings() -> Settings:
    module_root = Path(__file__).resolve().parent
    output_root = Path(os.getenv("EUREKA_3D_OUTPUT_ROOT", module_root / "generated")).resolve()
    api_key = os.getenv("EUREKA_3D_API_KEY")
    return Settings(
        service_name=os.getenv("EUREKA_3D_SERVICE_NAME", "eureka-3d-object-maker"),
        host=os.getenv("EUREKA_3D_HOST", "0.0.0.0"),
        port=int(os.getenv("EUREKA_3D_PORT", "8093")),
        output_root=output_root,
        api_key=api_key if api_key else None,
        max_query_length=int(os.getenv("EUREKA_3D_MAX_QUERY_LENGTH", "160")),
    )


settings = load_settings()

