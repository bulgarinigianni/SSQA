from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str = ""
    # Gemini 2.0 Flash — free tier, 1M token context window
    model_name: str = "gemini-2.0-flash"
    max_pdf_size_mb: int = 50
    max_batch_size: int = 10
    upload_dir: str = "uploads"

    model_config = {"env_file": ".env"}


settings = Settings()
