from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "EUREKA"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    AUTH_REQUIRED: bool = False
    MAX_REQUEST_BODY_BYTES: int = 2 * 1024 * 1024
    
    # Ollama settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT: int = 300
    DEFAULT_GENERATION_MODEL: str = "llama3"
    GENERATOR_TEMPERATURE: float = 0.1
    
    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost/eureka"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24

    # API limit settings
    MAX_AI_PROMPT_CHARS: int = 4000
    MAX_OBJECT_QUERY_CHARS: int = 120
    MAX_UPLOAD_FILES: int = 4
    MAX_UPLOAD_FILE_BYTES: int = 5 * 1024 * 1024
    MAX_SIMULATION_STEPS: int = 5000
    MAX_SIMULATION_PARTICLES: int = 250
    MAX_SIMULATION_TIME_STEP: float = 0.05
    RATE_LIMIT_PER_MINUTE: int = 120
    
    # CORS settings
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://eureka.io"
    ]
    
    # Gemini API settings
    GEMINI_API_KEY: str = ""

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_mode(cls, value):
        """Accept deployment words that sometimes arrive through shared env vars."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return value

    @field_validator("AUTH_REQUIRED", mode="before")
    @classmethod
    def parse_auth_required(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return value
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings():
    return Settings()
