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
    allowed_origins: list[str]


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
        allowed_origins=parse_csv(
            os.getenv(
                "EUREKA_3D_ALLOWED_ORIGINS",
                "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
            )
        ),
    )


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


settings = load_settings()
