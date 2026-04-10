from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    # Gemini 1.5 Flash — most widely available free tier
    # Alternatives: gemini-2.0-flash, gemini-1.5-flash-8b (lightest)
    model_name: str = "gemini-1.5-flash"
    max_pdf_size_mb: int = 50
    max_batch_size: int = 10
    upload_dir: str = "uploads"

    model_config = {"env_file": ".env"}


settings = Settings()
