"""
Configuration centralisée pour LEXO v1
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # Application
    APP_NAME: str = "LEXO v1"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lexo:password@localhost:5432/lexo_dev?ssl=false"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # JWT
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OCR & ML
    OCR_MODELS_PATH: str = "../ml_models/ocr_models"
    MISTRAL_MODEL_PATH: str = "../ml_models/mistral_7b_mlx"
    EMBEDDINGS_MODEL_PATH: str = "../ml_models/embeddings"
    
    # ChromaDB
    CHROMA_PATH: str = "../data/chromadb"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".txt"]
    UPLOAD_PATH: str = "~/Documents/LEXO_v1/OCR"
    
    # Email (pour notifications)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    
    @field_validator("CORS_ORIGINS")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Instance globale des settings
settings = Settings()